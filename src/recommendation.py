from typing import Optional
"""
Sugestão de modalidade da FM baseada no perfil criminal da área.

LÓGICA:

1. MODUS OPERANDI dos crimes determina modalidade primária:
   - Crime "a pé" -> patrulhamento "a pé" (intercepta na rua)
   - Crime motociclista -> patrulhamento "moto" (acompanha velocidade)
   - Crime "veiculo" -> "viatura" (interceptação)
   - Crime "arrastao" -> "mista" (a pé + viatura no perímetro)

2. ROTAS DE FUGA mapeadas no RELINT -> sugere PONTOS DE INTERCEPTAÇÃO
   onde posicionar viaturas/motos.

3. EFETIVO TOTAL é distribuído entre as 3 modalidades conforme:
   - Volume do crime "a pé" no histórico
   - Existência de rotas de fuga (mais viaturas)
   - Período do dia (noite favorece viatura iluminada)
"""

from collections import Counter
from schemas import (
    BingoArea,
    RelintEstruturado,
    Ocorrencia,
    RecomendacaoModalidade,
    Coordenada,
    ModalidadeFM,
    ModalidadeCrime,
    DiaSemana,
)


# ============================================================
# MAPEAMENTO MODUS -> MODALIDADE FM
# ============================================================

MODUS_PARA_MODALIDADE: dict[ModalidadeCrime, ModalidadeFM] = {
    "a_pe": "a_pe",
    "motocicleta": "moto",
    "veiculo": "viatura",
    "grupo_armado": "mista",
    "arrastao": "mista",
}


def sugerir_modalidade(
    bingo: BingoArea,
    relints_area: list[RelintEstruturado],
    ocorrencias_area: list[Ocorrencia],
    efetivo_total: int,
) -> RecomendacaoModalidade:
    """
    Decide modalidade principal + distribuicao do efetivo entre tipos.

    Args:
        bingo: BingoArea calculado
        relints_area: RELINTs daquela área
        ocorrencias_area: ocorrências históricas da área
        efetivo_total: quantos agentes esta área receberá (vem do alocador)

    Returns:
        RecomendacaoModalidade completo com pontos de interceptação
    """
    # 1. Modalidade predominante das OCORRÊNCIAS
    modalidades_oco = Counter(o.modalidade_crime for o in ocorrencias_area)
    if modalidades_oco:
        modalidade_crime_top = modalidades_oco.most_common(1)[0][0]
        modalidade_fm_principal = MODUS_PARA_MODALIDADE.get(modalidade_crime_top, "mista")
    else:
        modalidade_fm_principal = "a_pe"

    # 2. Modalidade secundária (se houver volume relevante)
    modalidade_fm_secundaria: Optional[ModalidadeFM] = None
    if len(modalidades_oco) >= 2:
        segunda = modalidades_oco.most_common(2)[1][0]
        seg_fm = MODUS_PARA_MODALIDADE.get(segunda, "mista")
        if seg_fm != modalidade_fm_principal:
            modalidade_fm_secundaria = seg_fm

    # 3. Distribuir efetivo total entre tipos
    n_viaturas, n_motos, n_a_pe = _distribuir_efetivo(
        modalidade_fm_principal,
        modalidade_fm_secundaria,
        efetivo_total,
        tem_rotas_fuga=any(r.rotas_fuga for r in relints_area),
    )

    # 4. Coletar pontos de interceptação (das rotas de fuga dos RELINTs)
    pontos_intercepcao: list[Coordenada] = []
    for r in relints_area:
        for rota in r.rotas_fuga:
            # Pegar o último ponto da rota como ponto de interceptação ideal
            if rota.pontos:
                pontos_intercepcao.append(rota.pontos[-1])
            # E um ponto intermediário se houver
            if len(rota.pontos) >= 3:
                meio = len(rota.pontos) // 2
                pontos_intercepcao.append(rota.pontos[meio])

    # 5. Horários e dias predominantes
    if relints_area:
        horario = relints_area[0].horario_pico
        dias = relints_area[0].dias_criticos
    else:
        horario = "18:00-22:00"
        dias = ["sex", "sab"]

    # 6. Justificativa
    justificativa = _montar_justificativa(
        modalidade_fm_principal,
        modalidade_fm_secundaria,
        ocorrencias_area,
        relints_area,
        len(pontos_intercepcao),
    )

    return RecomendacaoModalidade(
        poligono_fm_id=bingo.poligono_fm_id,
        modalidade_principal=modalidade_fm_principal,
        modalidade_secundaria=modalidade_fm_secundaria,
        n_viaturas=n_viaturas,
        n_motos=n_motos,
        n_agentes_a_pe=n_a_pe,
        justificativa=justificativa,
        pontos_intercepcao=pontos_intercepcao,
        horario_recomendado=horario,
        dias_recomendados=dias,
    )


# ============================================================
# DISTRIBUIÇÃO DO EFETIVO
# ============================================================

# Padroes de distribuicao: (frac_a_pe, frac_moto, frac_viatura)
# Cada modalidade tem fator de conversao para efetivo:
#   - 1 viatura = 4 agentes
#   - 1 moto    = 2 agentes
#   - 1 a_pe    = 1 agente

DISTRIBUICOES: dict[ModalidadeFM, tuple[float, float, float]] = {
    "a_pe":    (1.00, 0.00, 0.00),
    "moto":    (0.20, 0.80, 0.00),
    "viatura": (0.20, 0.00, 0.80),
    "mista":   (0.50, 0.25, 0.25),
}


def _distribuir_efetivo(
    principal: ModalidadeFM,
    secundaria: Optional[ModalidadeFM],
    efetivo_total: int,
    tem_rotas_fuga: bool,
) -> tuple[int, int, int]:
    """
    Retorna (n_viaturas, n_motos, n_agentes_a_pe).
    """
    # Distribuicao base
    frac_a_pe, frac_moto, frac_viatura = DISTRIBUICOES[principal]

    # Mistura secundaria a 30%
    if secundaria and secundaria != principal:
        f2_a, f2_m, f2_v = DISTRIBUICOES[secundaria]
        frac_a_pe = 0.7 * frac_a_pe + 0.3 * f2_a
        frac_moto = 0.7 * frac_moto + 0.3 * f2_m
        frac_viatura = 0.7 * frac_viatura + 0.3 * f2_v

    # Rotas de fuga = mais viaturas (interceptacao)
    if tem_rotas_fuga and frac_viatura < 0.4:
        ajuste = 0.15
        frac_viatura += ajuste
        frac_a_pe = max(frac_a_pe - ajuste, 0)

    # Converter fracoes em counts (lembrando da conversao por agente)
    efetivo_a_pe_alvo = int(round(efetivo_total * frac_a_pe))
    efetivo_moto_alvo = int(round(efetivo_total * frac_moto))
    efetivo_viatura_alvo = int(round(efetivo_total * frac_viatura))

    # Garantir soma = efetivo_total (reconciliar arredondamento)
    soma = efetivo_a_pe_alvo + efetivo_moto_alvo + efetivo_viatura_alvo
    if soma < efetivo_total:
        efetivo_a_pe_alvo += efetivo_total - soma
    elif soma > efetivo_total:
        efetivo_a_pe_alvo -= soma - efetivo_total
    efetivo_a_pe_alvo = max(efetivo_a_pe_alvo, 0)

    # Converter efetivo motorizado em N de viaturas/motos
    n_viaturas = efetivo_viatura_alvo // 4  # 4 agentes por viatura
    n_motos = efetivo_moto_alvo // 2        # 2 agentes por moto

    # Resto vira a_pe (não desperdiça agente)
    resto_viatura = efetivo_viatura_alvo - (n_viaturas * 4)
    resto_moto = efetivo_moto_alvo - (n_motos * 2)
    n_a_pe = efetivo_a_pe_alvo + resto_viatura + resto_moto

    return n_viaturas, n_motos, n_a_pe


# ============================================================
# JUSTIFICATIVA
# ============================================================

def _montar_justificativa(
    principal: ModalidadeFM,
    secundaria: Optional[ModalidadeFM],
    ocorrencias: list[Ocorrencia],
    relints: list[RelintEstruturado],
    n_pontos_intercepcao: int,
) -> str:
    """Texto explicando a recomendação para o gestor."""
    partes = []

    if ocorrencias:
        modalidades = Counter(o.modalidade_crime for o in ocorrencias)
        top = modalidades.most_common(1)[0]
        pct = (top[1] / len(ocorrencias)) * 100
        partes.append(
            f"{pct:.0f}% das ocorrencias sao '{top[0]}' -> modalidade FM '{principal}'"
        )

    if secundaria:
        partes.append(f"diversidade no modus operandi exige reforco em '{secundaria}'")

    if relints and any(r.rotas_fuga for r in relints):
        partes.append(
            f"{n_pontos_intercepcao} pontos de interceptacao sugeridos com base "
            f"em rotas de fuga mapeadas em RELINT"
        )

    if relints and relints[0].orcrim_influencia:
        partes.append(f"presenca de {relints[0].orcrim_influencia} requer postura defensiva")

    if not partes:
        return "Recomendacao default na ausencia de dados qualificados."

    return "Recomendacao baseada em: " + "; ".join(partes) + "."
