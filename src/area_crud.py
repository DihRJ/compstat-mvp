"""
CRUD de áreas: criar, listar, editar, EXCLUIR (permanente), desativar.

V5 MVP: pedido do Diego foi "edição, criação e exclusão" - implemento
exclusão de verdade (não só desativar) com confirmação obrigatória.
"""

import json
from pathlib import Path
from typing import Union, Optional
from datetime import datetime
from typing import Optional

from schemas import AreaPoligonoFM

_DEFAULT_AREAS_PATH = Path(__file__).resolve().parent.parent / "data" / "areas.json"


class AreasFMStore:
    """Storage simples em JSON (não GeoJSON, mais fácil para MVP)."""

    def __init__(self, json_path: Union[str, Path] = _DEFAULT_AREAS_PATH):
        self.path = Path(json_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]")

    def listar(self, incluir_inativos: bool = False) -> list[AreaPoligonoFM]:
        dados = self._load()
        areas = [AreaPoligonoFM(**d) for d in dados]
        if not incluir_inativos:
            areas = [a for a in areas if a.ativo]
        return areas

    def obter(self, poligono_id: str) -> Optional[AreaPoligonoFM]:
        for a in self.listar(incluir_inativos=True):
            if a.poligono_id == poligono_id:
                return a
        return None

    def contar_ativas(self) -> int:
        return len(self.listar(incluir_inativos=False))

    def criar(self, area: AreaPoligonoFM) -> str:
        if self.obter(area.poligono_id):
            raise ValueError(
                f"Area com id '{area.poligono_id}' ja existe."
            )
        dados = self._load()
        dados.append(area.model_dump(mode="json"))
        self._save(dados)
        return area.poligono_id

    def criar_em_lote(self, areas: list[AreaPoligonoFM]) -> int:
        """Idempotente: ignora ids já existentes."""
        dados = self._load()
        ids_existentes = {d["poligono_id"] for d in dados}
        novos = 0
        for a in areas:
            if a.poligono_id in ids_existentes:
                continue
            dados.append(a.model_dump(mode="json"))
            novos += 1
        self._save(dados)
        return novos

    def atualizar(
        self,
        poligono_id: str,
        nome_area: Optional[str] = None,
        bairros: Optional[list[str]] = None,
        geometria_wkt: Optional[str] = None,
        observacoes: Optional[str] = None,
        base_fm: Optional[str] = None,
        subprefeitura: Optional[str] = None,
        efetivo_padrao: Optional[int] = None,
    ) -> AreaPoligonoFM:
        area = self.obter(poligono_id)
        if area is None:
            raise ValueError(f"Area '{poligono_id}' nao encontrada.")

        if nome_area:
            area.nome_area = nome_area
        if bairros:
            area.bairros = bairros
        if geometria_wkt:
            area.geometria_wkt = geometria_wkt
        if observacoes is not None:
            area.observacoes = observacoes
        if base_fm:
            area.base_fm = base_fm
        if subprefeitura:
            area.subprefeitura = subprefeitura
        if efetivo_padrao is not None:
            area.efetivo_padrao = efetivo_padrao

        area.atualizado_em = datetime.now()
        self._substituir(area)
        return area

    def desativar(self, poligono_id: str, motivo: Optional[str] = None) -> AreaPoligonoFM:
        """Desativa sem deletar. Para preservação histórica."""
        area = self.obter(poligono_id)
        if area is None:
            raise ValueError(f"Area '{poligono_id}' nao encontrada.")
        area.ativo = False
        area.atualizado_em = datetime.now()
        if motivo:
            area.observacoes = f"DESATIVADO: {motivo} | {area.observacoes or ''}"
        self._substituir(area)
        return area

    def reativar(self, poligono_id: str) -> AreaPoligonoFM:
        area = self.obter(poligono_id)
        if area is None:
            raise ValueError(f"Area '{poligono_id}' nao encontrada.")
        area.ativo = True
        area.atualizado_em = datetime.now()
        self._substituir(area)
        return area

    def excluir(
        self,
        poligono_id: str,
        confirmar: bool = False,
    ) -> bool:
        """
        EXCLUSÃO PERMANENTE. Requer confirmar=True.

        Após excluir, não há recuperação. Para uso ocasional (ex: área
        criada por engano). Para retirar área de circulação mantendo
        histórico, use desativar().
        """
        if not confirmar:
            raise ValueError(
                "Exclusao permanente requer confirmar=True. "
                "Para retirar area de circulacao mantendo historico, use desativar()."
            )
        area = self.obter(poligono_id)
        if area is None:
            raise ValueError(f"Area '{poligono_id}' nao encontrada.")

        dados = self._load()
        dados = [d for d in dados if d["poligono_id"] != poligono_id]
        self._save(dados)
        return True

    # ----- internos -----

    def _load(self) -> list[dict]:
        return json.loads(self.path.read_text(encoding="utf-8") or "[]")

    def _save(self, data: list[dict]) -> None:
        self.path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    def _substituir(self, area: AreaPoligonoFM) -> None:
        dados = self._load()
        for i, d in enumerate(dados):
            if d["poligono_id"] == area.poligono_id:
                dados[i] = area.model_dump(mode="json")
                break
        self._save(dados)
