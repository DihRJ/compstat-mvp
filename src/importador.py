"""
Importador de novos documentos (RELINT, Ocorrências, Denúncias, Fatores Urbanos).

Suporta:
  - JSON estruturado (1 objeto ou lista de objetos)
  - CSV (para Ocorrências, Denúncias e Fatores Urbanos)
  - DOCX/TXT (extração de texto para RELINT — campos chave preenchidos manualmente)

Toda importação exige que o usuário selecione uma ÁREA PRÉ-EXISTENTE.
O campo `poligono_fm_id` é injetado automaticamente em cada item.

Validação via Pydantic. Merge nos arquivos data/<tipo>.json.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Any, Optional

from pydantic import ValidationError

from schemas import (
    Ocorrencia,
    RelintEstruturado,
    DenunciaDisque,
    FatorUrbano,
    Coordenada,
)


# ============================================================
# TIPOS SUPORTADOS
# ============================================================

TIPOS_DOCUMENTO = {
    "ocorrencias": {
        "rotulo": "Ocorrências criminais",
        "schema": Ocorrencia,
        "arquivo": "ocorrencias.json",
        "formatos": ["JSON", "CSV"],
    },
    "relints": {
        "rotulo": "RELINT (relatório de inteligência)",
        "schema": RelintEstruturado,
        "arquivo": "relints.json",
        "formatos": ["JSON", "DOCX", "PDF", "TXT"],
    },
    "denuncias": {
        "rotulo": "Denúncias do Disque",
        "schema": DenunciaDisque,
        "arquivo": "denuncias.json",
        "formatos": ["JSON", "CSV"],
    },
    "fatores": {
        "rotulo": "Fatores urbanos",
        "schema": FatorUrbano,
        "arquivo": "fatores_urbanos.json",
        "formatos": ["JSON", "CSV"],
    },
}

EXTENSOES_ACEITAS = ["json", "csv", "docx", "doc", "pdf", "txt"]


def detectar_formato(nome_arquivo: str) -> str:
    """Detecta formato pela extensão do arquivo (case-insensitive)."""
    ext = Path(nome_arquivo).suffix.lower().lstrip(".")
    mapa = {
        "json": "JSON",
        "csv": "CSV",
        "docx": "DOCX",
        "doc": "DOC",
        "pdf": "PDF",
        "txt": "TXT",
    }
    if ext not in mapa:
        raise ValueError(
            f"Extensão '.{ext}' não suportada. "
            f"Aceita: {', '.join(EXTENSOES_ACEITAS)}."
        )
    return mapa[ext]


# ============================================================
# RESULTADO DE IMPORTAÇÃO
# ============================================================

@dataclass
class ResultadoImportacao:
    tipo: str
    n_novos: int
    n_erros: int
    novos_itens: list[Any]
    erros: list[str]
    preview: list[dict]


# ============================================================
# PARSERS POR FORMATO
# ============================================================

def parse_json_bytes(conteudo: bytes) -> list[dict]:
    """Aceita objeto único ou lista de objetos."""
    data = json.loads(conteudo.decode("utf-8"))
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    raise ValueError("JSON deve ser objeto ou lista de objetos.")


def parse_csv_bytes(conteudo: bytes) -> list[dict]:
    """CSV com cabeçalho. Cada linha vira dict."""
    texto = conteudo.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(texto))
    return list(reader)


def parse_pdf_bytes(conteudo: bytes) -> str:
    """Extrai texto de PDF (pypdf)."""
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise RuntimeError("pypdf não instalado.") from e
    reader = PdfReader(io.BytesIO(conteudo))
    textos = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(t for t in textos if t.strip())


def parse_docx_bytes(conteudo: bytes) -> str:
    """Extrai texto de DOCX."""
    try:
        from docx import Document
    except ImportError as e:
        raise RuntimeError("python-docx não instalado.") from e

    doc = Document(io.BytesIO(conteudo))
    paragrafos = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragrafos)


# ============================================================
# COERÇÕES PARA OS SCHEMAS
# ============================================================

def _coerce_coordenada(valor: Any) -> dict:
    """Converte vários formatos para dict {lat, lng}."""
    if isinstance(valor, dict):
        return valor
    if isinstance(valor, str):
        # "lat,lng" ou "lat;lng"
        sep = "," if "," in valor else ";"
        partes = valor.split(sep)
        if len(partes) >= 2:
            return {"lat": float(partes[0]), "lng": float(partes[1])}
    raise ValueError(f"Coordenada inválida: {valor}")


def _coerce_lista(valor: Any) -> list[str]:
    """Converte 'a|b|c' ou ['a','b','c'] em lista de strings."""
    if isinstance(valor, list):
        return [str(x).strip() for x in valor]
    if isinstance(valor, str):
        sep = "|" if "|" in valor else ","
        return [x.strip() for x in valor.split(sep) if x.strip()]
    return []


def _coerce_ocorrencia(d: dict, poligono_id: str) -> dict:
    """Normaliza dict bruto para o schema Ocorrencia."""
    d = dict(d)
    d["poligono_fm_id"] = poligono_id

    # Coordenada
    if "coordenada" not in d:
        if "lat" in d and ("lng" in d or "lon" in d):
            d["coordenada"] = {
                "lat": float(d.pop("lat")),
                "lng": float(d.pop("lng", d.pop("lon", 0))),
            }
        else:
            raise ValueError("Ocorrência precisa de 'coordenada' ou 'lat'/'lng'")
    else:
        d["coordenada"] = _coerce_coordenada(d["coordenada"])

    # data_hora pode vir como string ISO
    if "data_hora" in d and isinstance(d["data_hora"], str):
        d["data_hora"] = datetime.fromisoformat(d["data_hora"].replace("Z", "+00:00"))

    # hora como int
    if "hora" in d:
        d["hora"] = int(d["hora"])

    return d


def _coerce_denuncia(d: dict, poligono_id: str) -> dict:
    d = dict(d)
    d["poligono_fm_id"] = poligono_id
    if "data_recebimento" in d and isinstance(d["data_recebimento"], str):
        d["data_recebimento"] = datetime.fromisoformat(
            d["data_recebimento"].replace("Z", "+00:00")
        )
    if "local_mencionado" in d and d["local_mencionado"]:
        d["local_mencionado"] = _coerce_coordenada(d["local_mencionado"])
    return d


def _coerce_fator(d: dict, poligono_id: str) -> dict:
    d = dict(d)
    d["poligono_fm_id"] = poligono_id
    if "coordenada" in d:
        d["coordenada"] = _coerce_coordenada(d["coordenada"])
    elif "lat" in d and ("lng" in d or "lon" in d):
        d["coordenada"] = {
            "lat": float(d.pop("lat")),
            "lng": float(d.pop("lng", d.pop("lon", 0))),
        }
    return d


def _coerce_relint(d: dict, poligono_id: str) -> dict:
    d = dict(d)
    d["poligono_fm_id"] = poligono_id
    if "data_documento" in d and isinstance(d["data_documento"], str):
        d["data_documento"] = date.fromisoformat(d["data_documento"])
    # Listas separadas por |
    for chave in ("modalidades_crime", "tipos_ocorrencia_alvo", "dias_criticos"):
        if chave in d:
            d[chave] = _coerce_lista(d[chave])
    return d


COERCERS = {
    "ocorrencias": _coerce_ocorrencia,
    "denuncias": _coerce_denuncia,
    "fatores": _coerce_fator,
    "relints": _coerce_relint,
}


# ============================================================
# IMPORTAÇÃO
# ============================================================

def importar(
    tipo: str,
    poligono_id: str,
    formato: str,
    conteudo: bytes,
) -> ResultadoImportacao:
    """Parse + valida + retorna preview (não salva ainda).

    Args:
        tipo: chave de TIPOS_DOCUMENTO
        poligono_id: área pré-existente
        formato: 'JSON' | 'CSV' | 'DOCX' | 'TXT'
        conteudo: bytes do arquivo

    Returns:
        ResultadoImportacao com itens válidos + lista de erros.
    """
    if tipo not in TIPOS_DOCUMENTO:
        raise ValueError(f"Tipo desconhecido: {tipo}")

    cfg = TIPOS_DOCUMENTO[tipo]
    schema = cfg["schema"]
    coercer = COERCERS[tipo]

    # Parse bruto
    fmt = formato.upper()
    if fmt == "JSON":
        registros = parse_json_bytes(conteudo)
    elif fmt == "CSV":
        registros = parse_csv_bytes(conteudo)
    elif fmt in ("DOCX", "PDF", "TXT"):
        # Texto livre: assume RELINT com texto único no campo modus_operandi
        if tipo != "relints":
            raise ValueError(
                f"Formato {fmt} suportado apenas para RELINTs. "
                f"Para {tipo}, use JSON ou CSV."
            )
        if fmt == "DOCX":
            texto = parse_docx_bytes(conteudo)
        elif fmt == "PDF":
            texto = parse_pdf_bytes(conteudo)
        else:  # TXT
            texto = conteudo.decode("utf-8-sig", errors="replace")
        registros = [{
            "autor_orgao": "Importado via upload",
            "data_documento": date.today().isoformat(),
            "modus_operandi_principal": texto[:2000],
            "modalidades_crime": ["a_pe"],
            "tipos_ocorrencia_alvo": ["roubo_transeunte"],
            "horario_pico": "18:00-22:00",
            "dias_criticos": ["sex", "sab"],
            "citacao_fonte": f"Documento importado em {date.today():%d/%m/%Y}",
        }]
    elif fmt == "DOC":
        raise ValueError(
            "Formato .doc não é suportado diretamente. "
            "Abra no Word e salve como .docx, ou exporte como PDF."
        )
    else:
        raise ValueError(f"Formato não suportado: {formato}")

    # Coerção + validação
    novos: list[Any] = []
    erros: list[str] = []
    preview: list[dict] = []

    for i, raw in enumerate(registros, 1):
        try:
            normalizado = coercer(raw, poligono_id)
            obj = schema(**normalizado)
            novos.append(obj)
            preview.append(obj.model_dump(mode="json"))
        except (ValidationError, ValueError, KeyError) as e:
            erros.append(f"Registro {i}: {type(e).__name__}: {e}")

    return ResultadoImportacao(
        tipo=tipo,
        n_novos=len(novos),
        n_erros=len(erros),
        novos_itens=novos,
        erros=erros,
        preview=preview[:5],  # cap em 5 para UI
    )


def salvar(
    resultado: ResultadoImportacao,
    data_dir: Path,
) -> Path:
    """Faz merge dos novos itens no arquivo data/<tipo>.json."""
    if not resultado.novos_itens:
        raise ValueError("Nada para salvar.")

    cfg = TIPOS_DOCUMENTO[resultado.tipo]
    arquivo = data_dir / cfg["arquivo"]

    # Carrega existentes
    existentes = []
    if arquivo.exists():
        existentes = json.loads(arquivo.read_text(encoding="utf-8") or "[]")

    # Acrescenta novos
    novos_dicts = [obj.model_dump(mode="json") for obj in resultado.novos_itens]
    merged = existentes + novos_dicts

    arquivo.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return arquivo
