"""Pipeline end-to-end para o caso Bangu (bangu_01).

Carrega dados -> score -> recomendacao -> QMD -> DOCX -> evolucao 90d.
"""

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from schemas import (
    AreaPoligonoFM,
    Ocorrencia,
    RelintEstruturado,
    DenunciaDisque,
    FatorUrbano,
)
from area_crud import AreasFMStore
from score_engine import calcular_bingos_todas_areas, calcular_bingo_por_area, _agrupar
from recommendation import sugerir_modalidade
from qmd_generator import gerar_qmd, qmd_para_markdown
from docx_generator import gerar_relatorio_docx
from evolution import carregar_snapshots, comparar_todas_areas
from heatmap import gerar_heatmap_temporal, gerar_grafico_evolucao


ALVO = "bangu_01"
EFETIVO = 24  # 2 viaturas + 2 motos + agentes a pe (24 agentes totais)


def _load_json(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    data_dir = ROOT / "data"

    # ---- carga ----
    store = AreasFMStore(json_path=data_dir / "areas.json")
    areas = store.listar(incluir_inativos=False)

    ocorrencias = [Ocorrencia(**d) for d in _load_json(data_dir / "ocorrencias.json")]
    relints = [RelintEstruturado(**d) for d in _load_json(data_dir / "relints.json")]
    fatores = [FatorUrbano(**d) for d in _load_json(data_dir / "fatores_urbanos.json")]
    denuncias = [DenunciaDisque(**d) for d in _load_json(data_dir / "denuncias.json")]

    print(f"[carga] {len(areas)} areas ativas | {len(ocorrencias)} ocorrencias | "
          f"{len(relints)} relints | {len(fatores)} fatores | {len(denuncias)} denuncias")

    area = next((a for a in areas if a.poligono_id == ALVO), None)
    if area is None:
        raise SystemExit(f"Area {ALVO} nao encontrada/ativa.")

    # ---- score (todas as areas, p/ ranking + bonus faccional) ----
    bingos = calcular_bingos_todas_areas(areas, ocorrencias, relints, fatores, denuncias)
    print("\n[ranking de score]")
    for b in bingos:
        print(f"  {b.poligono_fm_id:10s} {b.nome_area:35s} "
              f"score={b.componentes.score_final:.3f} bonus={b.componentes.bonus_faccional:.2f} "
              f"camadas={b.n_camadas_ativas}/4")

    bingo = next(b for b in bingos if b.poligono_fm_id == ALVO)

    # ---- recomendacao ----
    oco_por = _agrupar(ocorrencias, "poligono_fm_id")
    rel_por = _agrupar(relints, "poligono_fm_id")

    rec = sugerir_modalidade(
        bingo=bingo,
        relints_area=rel_por.get(ALVO, []),
        ocorrencias_area=oco_por.get(ALVO, []),
        efetivo_total=EFETIVO,
    )

    print(f"\n[recomendacao] modalidade={rec.modalidade_principal}"
          f" secundaria={rec.modalidade_secundaria}")
    print(f"  viaturas={rec.n_viaturas} motos={rec.n_motos} a_pe={rec.n_agentes_a_pe}"
          f" | total efetivo={rec.n_viaturas*4 + rec.n_motos*2 + rec.n_agentes_a_pe}")
    print(f"  pontos interceptacao: {len(rec.pontos_intercepcao)}")
    print(f"  horario={rec.horario_recomendado} dias={rec.dias_recomendados}")
    print(f"  justif: {rec.justificativa}")

    # ---- QMD ----
    qmd = gerar_qmd(
        area=area,
        bingo=bingo,
        recomendacao=rec,
        relints_area=rel_por.get(ALVO, []),
        acoes_pendentes_outros_orgaos=[],
        data_ref=date.today(),
    )

    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    qmd_md = qmd_para_markdown(qmd)
    (out_dir / "qmd_bangu.md").write_text(qmd_md, encoding="utf-8")
    print(f"\n[QMD] salvo em output/qmd_bangu.md ({len(qmd_md)} chars)")

    # ---- evolucao 90d ----
    snapshots = carregar_snapshots(data_dir / "snapshots_90d.json")
    nome_por = {a.poligono_id: a.nome_area for a in areas}
    comparativos = comparar_todas_areas(snapshots, nome_por)
    comp_bangu = next((c for c in comparativos if c.poligono_fm_id == ALVO), None)
    if comp_bangu:
        print(f"\n[evolucao 90d Bangu] roubos={comp_bangu.variacao_roubos_pct:+.1f}%"
              f" furtos={comp_bangu.variacao_furtos_pct:+.1f}%"
              f" score={comp_bangu.variacao_score_pct:+.1f}%"
              f" -> {comp_bangu.classificacao}")
    else:
        print("\n[evolucao] sem snapshot duplo para Bangu")

    # ---- imagens PNG p/ DOCX ----
    ocorrencias_bangu = oco_por.get(ALVO, [])
    heatmap_png = gerar_heatmap_temporal(ocorrencias_bangu)
    grafico_png = gerar_grafico_evolucao(comparativos) if comparativos else None
    (out_dir / "heatmap_bangu.png").write_bytes(heatmap_png)
    if grafico_png:
        (out_dir / "evolucao_90d.png").write_bytes(grafico_png)
    print(f"\n[imagens] heatmap={len(heatmap_png)}B"
          f" grafico={len(grafico_png) if grafico_png else 0}B")

    # ---- DOCX ----
    docx_path = out_dir / "relatorio_bangu.docx"
    gerar_relatorio_docx(
        area=area,
        bingo=bingo,
        recomendacao=rec,
        qmd=qmd,
        comparativo_evolucao=comp_bangu,
        padroes_disque=None,
        acoes_outros_orgaos=None,
        heatmap_temporal_png=heatmap_png,
        grafico_evolucao_png=grafico_png,
        output_path=str(docx_path),
    )
    print(f"\n[DOCX] salvo em {docx_path.relative_to(ROOT)}"
          f" ({docx_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
