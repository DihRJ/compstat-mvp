"""
Score engine MVP: cruza 4 fontes com PESOS DIFERENCIADOS + bônus de modus/rotas.

PESOS (importante para o pitch):
  mancha_criminal: 0.40 (dados oficiais quantitativos)
  relint_oficial:  0.30 (RELINT do BPM/FM, OFICIAL qualitativo)
  fator_urbano:    0.15 (mapeamento subprefeituras)
  disque_denuncia: 0.10 (anonimo, não-verificado)
  bonus_modus:     0.05 (amplificacao por modus+rotas conhecidas)

LOGICA DA AMPLIFICAÇÃO:
  Quando o RELINT descreve rotas de fuga + modus operandi, isso AUMENTA
  o score base, porque indica padrão estruturado de crime (mais ação
  organizada, menos crime de oportunidade).
"""

from typing import Optional
from collections import Counter

from schemas import (
    AreaPoligonoFM,
    Ocorrencia,
    RelintEstruturado,
    DenunciaDisque,
    FatorUrbano,
    ComponentesScore,
    BingoArea,
    TipoFaccao,
)


# ============================================================
# NORMALIZADORES (cada fonte vira score 0-1)
# ============================================================

def normalizar_mancha_criminal(
    ocorrencias_area: list[Ocorrencia],
    max_ocorrencias_referencia: int = 100,
) -> float:
    """
    Normaliza volume de ocorrências.
    100+ ocorrências = score 1.0 (saturação).
    """
    n = len(ocorrencias_area)
    return min(n / max_ocorrencias_referencia, 1.0)


def normalizar_relint(relints_area: list[RelintEstruturado]) -> float:
    """
    Score do RELINT:
      - Tem RELINT recente com confiança alta? 0.85
      - Tem RELINT com modus operandi descrito? +0.10
      - Tem rota de fuga mapeada? +0.05
      - Sem RELINT na área? 0.0
    """
    if not relints_area:
        return 0.0

    score = 0.0
    for r in relints_area:
        s = 0.85 if r.confianca == "alta" else (0.60 if r.confianca == "media" else 0.35)
        if r.modus_operandi_principal and len(r.modus_operandi_principal) > 20:
            s += 0.10
        if r.rotas_fuga:
            s += 0.05
        score = max(score, s)  # pega o melhor RELINT
    return min(score, 1.0)


def normalizar_fator_urbano(fatores_area: list[FatorUrbano]) -> float:
    """
    Soma severidades dos fatores ativos.
    Mapping: critica=0.30, alta=0.20, media=0.10, baixa=0.05
    Cap em 1.0.
    """
    pesos = {"critica": 0.30, "alta": 0.20, "media": 0.10, "baixa": 0.05}
    total = sum(pesos.get(f.severidade, 0) for f in fatores_area)
    return min(total, 1.0)


def normalizar_disque(denuncias_area: list[DenunciaDisque]) -> float:
    """
    Volume de denúncias normalizado.
    10+ denúncias = score 1.0 (mas peso geral é só 0.10).
    """
    n = len(denuncias_area)
    return min(n / 10.0, 1.0)


def calcular_bonus_modus_e_rotas(
    relints_area: list[RelintEstruturado],
    ocorrencias_area: list[Ocorrencia],
) -> float:
    """
    Bonus quando o crime na área CONFIRMA o modus operandi descrito no RELINT.
    Isso indica padrão estabelecido (não crime aleatório).

    Heurística simples:
      - RELINT cita modalidade X
      - Mais de 50% das ocorrências têm modalidade X
      - Score: 0.8 (alto bônus)

    Quando há rota de fuga mapeada:
      - +0.2 adicional (geo conhecido facilita interceptação)
    """
    if not relints_area:
        return 0.0

    score = 0.0
    for r in relints_area:
        if not ocorrencias_area:
            continue

        # Modalidades do RELINT
        modalidades_relint = set(r.modalidades_crime)
        modalidades_oco = Counter(o.modalidade_crime for o in ocorrencias_area)
        total_oco = sum(modalidades_oco.values())

        # Quanto das ocorrências bate com modus do RELINT?
        ocorrencias_no_modus = sum(
            count for mod, count in modalidades_oco.items() if mod in modalidades_relint
        )
        pct_confirma_modus = ocorrencias_no_modus / total_oco if total_oco > 0 else 0

        if pct_confirma_modus > 0.5:
            score = max(score, 0.8)
        elif pct_confirma_modus > 0.3:
            score = max(score, 0.5)
        else:
            score = max(score, 0.2)

        if r.rotas_fuga:
            score = min(score + 0.2, 1.0)

    return score


# ============================================================
# FACÇÕES E BÔNUS
# ============================================================

# Matriz simplificada de rivalidades para MVP
RIVALIDADES_BONUS: dict[frozenset, float] = {
    frozenset(["TCP", "CV"]): 1.5,
    frozenset(["TCP", "ADA"]): 1.3,
    frozenset(["CV", "ADA"]): 1.3,
    frozenset(["milicia", "CV"]): 1.5,
    frozenset(["milicia", "TCP"]): 1.4,
    frozenset(["milicia", "ADA"]): 1.4,
}


def calcular_bonus_faccional(
    poligono_id: str,
    relints_por_area: dict[str, list[RelintEstruturado]],
    areas: list[AreaPoligonoFM],
) -> tuple[float, list[TipoFaccao]]:
    """
    Retorna (bonus_multiplicador, lista_faccoes_envolvidas).

    Se a área tem facção X e uma área vizinha tem Y rival, aplica bônus.
    Vizinhança: simplificada para "mesma AISP" no MVP.
    """
    relints_da_area = relints_por_area.get(poligono_id, [])
    faccao_propria = next(
        (r.orcrim_influencia for r in relints_da_area if r.orcrim_influencia),
        None,
    )
    if not faccao_propria:
        return 1.0, []

    area_atual = next((a for a in areas if a.poligono_id == poligono_id), None)
    if not area_atual:
        return 1.0, [faccao_propria]

    # Procura faccoes em areas vizinhas (mesma AISP)
    faccoes_vizinhas: set[TipoFaccao] = set()
    for outra_area in areas:
        if outra_area.poligono_id == poligono_id:
            continue
        if outra_area.aisp != area_atual.aisp:
            continue
        for r in relints_por_area.get(outra_area.poligono_id, []):
            if r.orcrim_influencia and r.orcrim_influencia != faccao_propria:
                faccoes_vizinhas.add(r.orcrim_influencia)

    if not faccoes_vizinhas:
        return 1.0, [faccao_propria]

    # Maior bônus aplicável
    bonus_max = 1.0
    for fv in faccoes_vizinhas:
        par = frozenset([faccao_propria, fv])
        if par in RIVALIDADES_BONUS:
            bonus_max = max(bonus_max, RIVALIDADES_BONUS[par])

    return bonus_max, [faccao_propria] + list(faccoes_vizinhas)


# ============================================================
# CÁLCULO CONSOLIDADO POR ÁREA
# ============================================================

def calcular_bingo_por_area(
    area: AreaPoligonoFM,
    ocorrencias_area: list[Ocorrencia],
    relints_area: list[RelintEstruturado],
    fatores_area: list[FatorUrbano],
    denuncias_area: list[DenunciaDisque],
    relints_por_area: dict[str, list[RelintEstruturado]],
    todas_areas: list[AreaPoligonoFM],
) -> BingoArea:
    """
    Função principal: pega TODOS os dados de uma área e devolve BingoArea.
    """
    # Cada fonte vira score 0-1
    s_mancha = normalizar_mancha_criminal(ocorrencias_area)
    s_relint = normalizar_relint(relints_area)
    s_fator = normalizar_fator_urbano(fatores_area)
    s_disque = normalizar_disque(denuncias_area)
    s_modus = calcular_bonus_modus_e_rotas(relints_area, ocorrencias_area)

    # Facção
    bonus_fac, faccoes = calcular_bonus_faccional(
        area.poligono_id, relints_por_area, todas_areas
    )

    componentes = ComponentesScore(
        score_mancha=s_mancha,
        score_relint=s_relint,
        score_fator=s_fator,
        score_disque=s_disque,
        score_modus_rota=s_modus,
        bonus_faccional=bonus_fac,
    )

    # Conta camadas ativas (score > 0.05)
    n_ativas = sum(1 for s in [s_mancha, s_relint, s_fator, s_disque] if s > 0.05)

    # Justificativa textual
    componentes_descricoes = []
    if s_mancha > 0.3:
        componentes_descricoes.append(f"volume criminal alto ({len(ocorrencias_area)} ocorrencias)")
    if s_relint > 0.5:
        componentes_descricoes.append(f"RELINT oficial confirma padrao (peso 0.30)")
    if s_fator > 0.3:
        componentes_descricoes.append(f"{len(fatores_area)} fatores urbanos ativos")
    if s_disque > 0.3:
        componentes_descricoes.append(f"{len(denuncias_area)} denuncias disque")
    if s_modus > 0.5:
        componentes_descricoes.append("modus operandi confirmado por rotas mapeadas")
    if bonus_fac > 1.0:
        componentes_descricoes.append(f"interseccao faccional (x{bonus_fac:.2f})")

    justificativa = (
        f"Score final {componentes.score_final:.2f}. " +
        "Componentes: " + "; ".join(componentes_descricoes) +
        f". Camadas ativas: {n_ativas} de 4."
    )

    return BingoArea(
        poligono_fm_id=area.poligono_id,
        nome_area=area.nome_area,
        componentes=componentes,
        n_camadas_ativas=n_ativas,
        justificativa=justificativa,
        faccoes_envolvidas=faccoes,
    )


def calcular_bingos_todas_areas(
    areas: list[AreaPoligonoFM],
    ocorrencias: list[Ocorrencia],
    relints: list[RelintEstruturado],
    fatores: list[FatorUrbano],
    denuncias: list[DenunciaDisque],
) -> list[BingoArea]:
    """Orquestra cálculo para todas as áreas. Retorna ordenado por score."""
    # Indexar por área
    oco_por = _agrupar(ocorrencias, "poligono_fm_id")
    rel_por = _agrupar(relints, "poligono_fm_id")
    fat_por = _agrupar(fatores, "poligono_fm_id")
    den_por = _agrupar(denuncias, "poligono_fm_id")

    bingos = []
    for area in areas:
        if not area.ativo:
            continue
        bingo = calcular_bingo_por_area(
            area=area,
            ocorrencias_area=oco_por.get(area.poligono_id, []),
            relints_area=rel_por.get(area.poligono_id, []),
            fatores_area=fat_por.get(area.poligono_id, []),
            denuncias_area=den_por.get(area.poligono_id, []),
            relints_por_area=rel_por,
            todas_areas=areas,
        )
        bingos.append(bingo)

    return sorted(bingos, key=lambda b: -b.componentes.score_final)


def _agrupar(lista: list, attr: str) -> dict:
    """Helper para agrupar lista de objetos por atributo."""
    out: dict = {}
    for item in lista:
        key = getattr(item, attr)
        out.setdefault(key, []).append(item)
    return out
