"""
Comparativo de evolução: antes vs depois da atuação da FM (90 dias padrão).

Casos de uso:
  - Mostrar que a área X caiu N% de roubos após FM começar a atuar
  - Detectar áreas onde a operação não fez efeito (ajustar abordagem)
  - Métrica de impacto para apresentar à alta gestão

LÓGICA:
  Para cada área, comparar 2 snapshots:
    - snapshot ANTES (data_ref - dias_atras)
    - snapshot DEPOIS (data_ref)
  Variações em roubos, furtos, score.
"""

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Union, Optional
from typing import Optional

from schemas import SnapshotIndicadores, ComparativoEvolucao


def carregar_snapshots(path: Union[str, Path] = "data/snapshots_90d.json") -> list[SnapshotIndicadores]:
    p = Path(path)
    if not p.exists():
        return []
    return [SnapshotIndicadores(**d) for d in json.loads(p.read_text(encoding="utf-8"))]


def comparar_evolucao(
    poligono_id: str,
    nome_area: str,
    snapshot_antes: SnapshotIndicadores,
    snapshot_depois: SnapshotIndicadores,
) -> ComparativoEvolucao:
    """Calcula variação entre 2 snapshots."""
    dias = (snapshot_depois.data_referencia - snapshot_antes.data_referencia).days

    var_roubos = _pct(
        snapshot_antes.total_roubos, snapshot_depois.total_roubos
    )
    var_furtos = _pct(
        snapshot_antes.total_furtos, snapshot_depois.total_furtos
    )
    var_score = _pct(
        snapshot_antes.score_medio, snapshot_depois.score_medio
    )

    # Classificação baseada em variação combinada
    media_var = (var_roubos + var_furtos + var_score) / 3
    if media_var <= -25:
        classif = "melhora_significativa"
    elif media_var <= -10:
        classif = "melhora_leve"
    elif media_var <= 10:
        classif = "estavel"
    elif media_var <= 25:
        classif = "piora_leve"
    else:
        classif = "piora_significativa"

    # Observação textual
    obs = _gerar_observacao(var_roubos, var_furtos, var_score, dias)

    return ComparativoEvolucao(
        poligono_fm_id=poligono_id,
        nome_area=nome_area,
        snapshot_antes=snapshot_antes,
        snapshot_depois=snapshot_depois,
        dias_entre=dias,
        variacao_roubos_pct=round(var_roubos, 1),
        variacao_furtos_pct=round(var_furtos, 1),
        variacao_score_pct=round(var_score, 1),
        classificacao=classif,
        observacao=obs,
    )


def comparar_todas_areas(
    snapshots: list[SnapshotIndicadores],
    nome_por_area: dict[str, str],
) -> list[ComparativoEvolucao]:
    """Compara antes/depois para todas as áreas que têm 2 snapshots."""
    por_area: dict[str, list[SnapshotIndicadores]] = {}
    for s in snapshots:
        por_area.setdefault(s.poligono_fm_id, []).append(s)

    comparativos = []
    for pid, snaps in por_area.items():
        if len(snaps) < 2:
            continue
        snaps_ordenados = sorted(snaps, key=lambda s: s.data_referencia)
        antes = snaps_ordenados[0]
        depois = snaps_ordenados[-1]
        comp = comparar_evolucao(
            poligono_id=pid,
            nome_area=nome_por_area.get(pid, pid),
            snapshot_antes=antes,
            snapshot_depois=depois,
        )
        comparativos.append(comp)

    return sorted(comparativos, key=lambda c: c.variacao_score_pct)


# ============================================================
# HELPERS
# ============================================================

def _pct(antes: float, depois: float) -> float:
    """Variação percentual com proteção contra divisão por zero."""
    if antes == 0:
        return 0.0 if depois == 0 else 100.0
    return ((depois - antes) / antes) * 100


def _gerar_observacao(
    var_roubos: float,
    var_furtos: float,
    var_score: float,
    dias: int,
) -> str:
    """Observação textual sobre a evolução."""
    if var_roubos < -20:
        partes = [f"Reducao expressiva de roubos ({var_roubos:.1f}% em {dias} dias)."]
    elif var_roubos < 0:
        partes = [f"Reducao de roubos ({var_roubos:.1f}%)."]
    elif var_roubos < 10:
        partes = [f"Estavel em roubos ({var_roubos:+.1f}%)."]
    else:
        partes = [f"Aumento de roubos ({var_roubos:+.1f}%) - revisar operacao."]

    if var_furtos < -20:
        partes.append(f"Furtos tambem cairam ({var_furtos:.1f}%).")
    elif var_furtos > 10:
        partes.append(f"Furtos subiram ({var_furtos:+.1f}%) - foco adicional necessario.")

    return " ".join(partes)
