"""
Sugestão determinística de efetivo da FM por área.

Heurística multifatorial (sem LLM, replicável, sem custo) que considera:
  - Score do bingo (peso maior)
  - Volume de ocorrências no período analisado
  - Área geográfica do polígono (km²)
  - Severidade dos fatores urbanos ativos
  - Presença de facção e rivalidade (bônus faccional)
  - Modus operandi predominante (a_pe demanda mais cobertura presencial)

Retorna `SugestaoEfetivo` com número sugerido + breakdown explicativo
para o gestor entender de onde veio a recomendação.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections import Counter

from schemas import (
    AreaPoligonoFM,
    BingoArea,
    Ocorrencia,
    RelintEstruturado,
    FatorUrbano,
)


# ============================================================
# CONSTANTES DA HEURÍSTICA
# ============================================================

# Score 0-1 → 0-50 agentes (base)
PESO_SCORE = 50

# Volume: cada 8 ocorrências = +1 agente
DIVISOR_VOLUME = 8
CAP_VOLUME = 15

# Área geográfica: cada km² = +2.5 agentes
PESO_KM2 = 2.5
CAP_AREA = 15

# Severidade dos fatores urbanos
PESOS_FATOR = {
    "critica": 5,
    "alta": 3,
    "media": 1,
    "baixa": 0,
}
CAP_FATORES = 12

# Facção
BONUS_FACCAO_RIVAL = 10  # bonus_faccional > 1.0
BONUS_FACCAO_SIMPLES = 5  # tem facção mas sem rival

# Modus
BONUS_MODUS_A_PE = 5  # cobertura presencial

# Bounds finais
EFETIVO_MIN = 5
EFETIVO_MAX = 120


# ============================================================
# RESULTADO
# ============================================================

@dataclass
class ComponenteSugestao:
    rotulo: str
    detalhe: str
    contribuicao: int


@dataclass
class SugestaoEfetivo:
    efetivo_sugerido: int
    componentes: list[ComponenteSugestao]
    racional_curto: str

    def to_markdown(self) -> str:
        lines = [
            f"### Sugestão: **{self.efetivo_sugerido} agentes**",
            "",
            "| Componente | Detalhe | Contribuição |",
            "|---|---|---:|",
        ]
        for c in self.componentes:
            lines.append(f"| {c.rotulo} | {c.detalhe} | +{c.contribuicao} |")
        lines.append("")
        lines.append(f"_{self.racional_curto}_")
        return "\n".join(lines)


# ============================================================
# CÁLCULO
# ============================================================

def _area_km2(geometria_wkt: str) -> float:
    """Aproximação de área em km² a partir de um polígono WKT em graus.

    Para a região do Rio de Janeiro (~-23° lat): 1° lat ≈ 111 km,
    1° lng ≈ 102 km. Erro tolerável para fins de dimensionamento.
    """
    try:
        from shapely import wkt as shapely_wkt
        geom = shapely_wkt.loads(geometria_wkt)
        area_graus = geom.area
        # Conversão grosseira para km² no Rio
        return area_graus * 111.0 * 102.0
    except Exception:
        return 0.0


def sugerir_efetivo(
    area: AreaPoligonoFM,
    bingo: BingoArea,
    ocorrencias_area: list[Ocorrencia],
    relints_area: list[RelintEstruturado],
    fatores_area: list[FatorUrbano],
) -> SugestaoEfetivo:
    """Calcula sugestão de efetivo com breakdown explicativo."""
    componentes: list[ComponenteSugestao] = []

    # 1. Score base
    score = bingo.componentes.score_final
    contrib_score = round(score * PESO_SCORE)
    componentes.append(ComponenteSugestao(
        rotulo="Score de risco",
        detalhe=f"score {score:.2f} × {PESO_SCORE}",
        contribuicao=contrib_score,
    ))

    # 2. Volume de ocorrências
    n_oco = len(ocorrencias_area)
    contrib_volume = min(CAP_VOLUME, n_oco // DIVISOR_VOLUME)
    if contrib_volume > 0:
        componentes.append(ComponenteSugestao(
            rotulo="Volume criminal",
            detalhe=f"{n_oco} ocorrências no período",
            contribuicao=contrib_volume,
        ))

    # 3. Área geográfica
    km2 = _area_km2(area.geometria_wkt)
    contrib_area = min(CAP_AREA, round(km2 * PESO_KM2))
    if contrib_area > 0:
        componentes.append(ComponenteSugestao(
            rotulo="Cobertura territorial",
            detalhe=f"{km2:.2f} km²",
            contribuicao=contrib_area,
        ))

    # 4. Fatores urbanos
    if fatores_area:
        contrib_fatores = 0
        detalhes: list[str] = []
        for f in fatores_area:
            peso = PESOS_FATOR.get(f.severidade, 0)
            contrib_fatores += peso
            if peso > 0:
                detalhes.append(f"{f.severidade}")
        contrib_fatores = min(CAP_FATORES, contrib_fatores)
        if contrib_fatores > 0:
            sev_counter = Counter(detalhes)
            detalhe_str = ", ".join(
                f"{c}× {s}" for s, c in sev_counter.most_common()
            )
            componentes.append(ComponenteSugestao(
                rotulo="Fatores urbanos",
                detalhe=detalhe_str,
                contribuicao=contrib_fatores,
            ))

    # 5. Facção
    bonus_fac = bingo.componentes.bonus_faccional
    if bonus_fac > 1.0:
        componentes.append(ComponenteSugestao(
            rotulo="Intersecção faccional",
            detalhe=f"multiplicador x{bonus_fac:.2f} entre {', '.join(bingo.faccoes_envolvidas)}",
            contribuicao=BONUS_FACCAO_RIVAL,
        ))
    elif bingo.faccoes_envolvidas:
        componentes.append(ComponenteSugestao(
            rotulo="Presença faccional",
            detalhe=f"{', '.join(bingo.faccoes_envolvidas)} sem rivalidade direta",
            contribuicao=BONUS_FACCAO_SIMPLES,
        ))

    # 6. Modus operandi predominante
    if ocorrencias_area:
        modus_top = Counter(o.modalidade_crime for o in ocorrencias_area).most_common(1)[0]
        if modus_top[0] == "a_pe":
            pct = (modus_top[1] / len(ocorrencias_area)) * 100
            componentes.append(ComponenteSugestao(
                rotulo="Modus 'a pé' predominante",
                detalhe=f"{pct:.0f}% das ocorrências exigem patrulha presencial",
                contribuicao=BONUS_MODUS_A_PE,
            ))

    # Total
    total_bruto = sum(c.contribuicao for c in componentes)
    efetivo_final = max(EFETIVO_MIN, min(EFETIVO_MAX, total_bruto))

    # Racional curto
    if efetivo_final >= 60:
        racional = (
            f"Cenário de alto risco: score {score:.2f}, "
            f"{n_oco} ocorrências e fatores agravantes recomendam "
            f"efetivo reforçado."
        )
    elif efetivo_final >= 30:
        racional = (
            f"Cenário intermediário: score {score:.2f} indica atenção, "
            f"efetivo médio é suficiente para cobertura ostensiva."
        )
    else:
        racional = (
            f"Cenário de menor pressão: score {score:.2f} permite "
            f"efetivo enxuto, ideal para presença preventiva."
        )

    return SugestaoEfetivo(
        efetivo_sugerido=efetivo_final,
        componentes=componentes,
        racional_curto=racional,
    )
