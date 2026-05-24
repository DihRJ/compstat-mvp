"""Importa as 8 áreas oficiais da Força Municipal a partir do shapefile.

Fonte: https://github.com/CompStat-Rio/claude_impact_lab_compstat_rio/tree/main/sh_area_forca

Estratégia:
  1. Lê o shapefile baixado em /tmp/sh_area_forca/
  2. Converte cada polígono para AreaPoligonoFM com WKT
  3. Faz backup do areas_iniciais.json e areas.json existentes
  4. Substitui pelos 8 polígonos oficiais

Campos não-fornecidos pelo shape (AISP, bairros, base_fm, subprefeitura) ficam
com placeholders editáveis no Editor de áreas.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

SHAPE_BASE = Path("/tmp/sh_area_forca/areas_forca_municipal")
DATA_DIR = ROOT / "data"

# Inferência de subprefeitura por centroide (Rio de Janeiro)
def inferir_subprefeitura(lat: float, lng: float) -> str:
    """Aproximação grosseira baseada em centroide."""
    if lng < -43.45:
        return "Zona Oeste"
    if lat > -22.93 and -43.25 < lng < -43.15:
        return "Centro"
    if lat < -22.97:
        return "Zona Sul"
    if -22.93 < lat < -22.92 and lng > -43.25:
        return "Tijuca/Grande Tijuca"
    if -22.92 < lat < -22.88:
        return "Zona Norte"
    return "A definir"


def slugify(texto: str, max_len: int = 24) -> str:
    """Gera id curto a partir do nome."""
    s = texto.lower()
    s = re.sub(r"[áàâãä]", "a", s)
    s = re.sub(r"[éèêë]", "e", s)
    s = re.sub(r"[íìîï]", "i", s)
    s = re.sub(r"[óòôõö]", "o", s)
    s = re.sub(r"[úùûü]", "u", s)
    s = re.sub(r"ç", "c", s)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")[:max_len]
    return s


def main() -> None:
    import shapefile
    from shapely.geometry import shape

    if not SHAPE_BASE.with_suffix(".shp").exists():
        raise SystemExit(
            f"Shapefile não encontrado em {SHAPE_BASE}.shp. "
            f"Baixe primeiro do repo CompStat-Rio."
        )

    r = shapefile.Reader(str(SHAPE_BASE))
    print(f"[shapefile] {len(r)} polígonos | tipo {r.shapeTypeName}")

    novas_areas: list[dict] = []
    nomes_vistos: set[str] = set()

    for i, rec in enumerate(r.records()):
        atributos = dict(zip([f[0] for f in r.fields[1:]], rec))
        nome = str(atributos.get("nome_subar", f"Area {i+1}")).strip()
        fid = atributos.get("fid", i + 1)

        # Gera ID único
        base_id = slugify(nome, max_len=20)
        poligono_id = f"{base_id}_{fid:02d}"
        if poligono_id in nomes_vistos:
            poligono_id = f"{base_id}_{i+1:02d}_alt"
        nomes_vistos.add(poligono_id)

        geom = shape(r.shape(i).__geo_interface__)
        wkt = geom.wkt
        cy, cx = geom.centroid.y, geom.centroid.x

        area_dict = {
            "poligono_id": poligono_id,
            "nome_area": nome,
            "aisp": "A definir",
            "bairros": ["A definir"],
            "geometria_wkt": wkt,
            "base_fm": f"Base FM {nome.split('-')[0].strip()[:40]}",
            "subprefeitura": inferir_subprefeitura(cy, cx),
            "dp": None,
            "bpm": None,
            "ativo": True,
            "centroide": {"lat": cy, "lng": cx, "descricao": None},
            "efetivo_padrao": 25,
            "criado_em": datetime.now().isoformat(),
            "atualizado_em": datetime.now().isoformat(),
            "observacoes": (
                f"Importada do shapefile oficial CompStat-Rio "
                f"(fid {fid}). Preencher AISP, bairros, DP, BPM no Editor."
            ),
        }
        novas_areas.append(area_dict)

        print(
            f"  ✓ {poligono_id:30s} | {nome[:60]:60s} | "
            f"centroide ({cy:.4f}, {cx:.4f})"
        )

    # Backup
    arquivos = ["areas.json", "areas_iniciais.json"]
    for arq in arquivos:
        origem = DATA_DIR / arq
        if origem.exists():
            backup = DATA_DIR / f"{arq}.backup_5areas_piloto"
            shutil.copy2(origem, backup)
            print(f"  ⚙ backup: {arq} → {backup.name}")

    # Salva
    for arq in arquivos:
        destino = DATA_DIR / arq
        destino.write_text(
            json.dumps(novas_areas, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"  ✓ gravado: {destino}")

    print(f"\n[OK] {len(novas_areas)} áreas oficiais da FM importadas.")
    print("\n⚠️  Os dados sintéticos antigos (ocorrencias.json, relints.json,")
    print("    denuncias.json, fatores_urbanos.json, snapshots_90d.json)")
    print("    continuam apontando para IDs ANTIGOS (bangu_01, copa_01...).")
    print("    Eles ficaram órfãos. Próximo passo: regenerar dados sintéticos")
    print("    para os novos IDs OU importar dados reais via UI 'Importar dados'.")


if __name__ == "__main__":
    main()
