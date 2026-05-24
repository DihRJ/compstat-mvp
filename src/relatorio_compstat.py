"""
Geração dos blocos analíticos do Relatório Analítico de Área (CompStat Municipal).

Implementa o formato OFICIAL descrito no briefing técnico:
  - Resumo Executivo com 4 perguntas norteadoras
  - Identificação da área e indicadores do período
  - Análise temporal (período/dia crítico)
  - Dinâmica criminal sintetizada do Disque/RELINT
  - Tabela 5×4 do efetivo empregado da FM
  - Tabela de fatores de incidência criminal por órgão
  - Plano de ação e responsabilização pré-populado

A lógica é determinística (heurística). Quando configurada, pode ser
enriquecida com Claude via `explicacao_llm.py` (botão opcional na UI).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from typing import Optional

from schemas import (
    AreaPoligonoFM,
    BingoArea,
    Ocorrencia,
    RelintEstruturado,
    DenunciaDisque,
    FatorUrbano,
    RecomendacaoModalidade,
    ComparativoEvolucao,
    AcaoRecomendada,
    CategoriaFatorUrbano,
    OrgaoMunicipal,
    TipoOcorrencia,
    DiaSemana,
)


# ============================================================
# CONSTANTES OFICIAIS
# ============================================================

TOTAL_EFETIVO_FM = 600  # briefing seção 7.3: total de agentes para as 22 áreas
TOTAL_AREAS_PRIORITARIAS = 22

ROTULO_CATEGORIA: dict[CategoriaFatorUrbano, str] = {
    "iluminacao_deficiente": "Iluminação Pública",
    "vegetacao_obstrutiva": "Vegetação",
    "calcada_obstruida": "Obstrução de via",
    "estacionamento_irregular": "Obstrução de via (estacionamento irregular)",
    "ponto_onibus_inseguro": "Pontos de ônibus inseguros",
    "psr_concentrada": "Pessoas em situação de rua",
    "comercio_irregular": "Comércio irregular",
    "esconderijo": "Esconderijos",
    "lixo_entulho": "Lixo e Entulho",
    "ponto_cego_camera": "Pontos cegos de câmera",
    "outro": "Outros",
}

ROTULO_ORGAO: dict[OrgaoMunicipal, str] = {
    "COMLURB": "Comlurb",
    "SEOP": "SEOP",
    "CET_RIO": "CET-Rio",
    "RIOLUZ": "RioLuz",
    "SECONSERVA": "Seconserva",
    "SMAS": "SMAS",
    "SMS": "SMS",
    "GM_RIO": "GM-Rio",
    "FM": "Força Municipal",
}

ROTULO_TIPO_OCORRENCIA: dict[TipoOcorrencia, str] = {
    "roubo_transeunte": "Roubo a transeunte",
    "roubo_celular": "Roubo de aparelho celular",
    "roubo_coletivo": "Roubo em coletivo",
    "roubo_veiculo": "Roubo de veículo",
    "roubo_comercio": "Roubo a comércio",
    "furto_transeunte": "Furto a transeunte",
    "furto_celular": "Furto de aparelho celular",
    "furto_veiculo": "Furto de veículo",
    "outros": "Outros",
}

ROTULO_DIA: dict[DiaSemana, str] = {
    "dom": "domingo", "seg": "segunda", "ter": "terça",
    "qua": "quarta", "qui": "quinta", "sex": "sexta", "sab": "sábado",
}

ROTULO_MODALIDADE_FM: dict[str, str] = {
    "a_pe": "Patrulhamento a pé",
    "moto": "Patrulhamento motorizado (moto)",
    "viatura": "Patrulhamento de viatura",
    "mista": "Modalidade mista",
}

# Mapeamento categoria de fator → ação sugerida
SUGESTAO_ACAO_POR_CATEGORIA: dict[CategoriaFatorUrbano, str] = {
    "iluminacao_deficiente": "Manutenção de postes apagados e instalação de luminárias/refletores adicionais",
    "vegetacao_obstrutiva": "Poda urgente nos trechos identificados, com manutenção trimestral",
    "calcada_obstruida": "Remoção de estruturas irregulares e ordenamento urbano",
    "estacionamento_irregular": "Repressão a estacionamento irregular e fiscalização contínua",
    "ponto_onibus_inseguro": "Reforço de iluminação e patrulhamento dirigido nos horários de pico",
    "psr_concentrada": "Abordagem e assistência à população em situação de rua",
    "comercio_irregular": "Fiscalização e remoção de comércio irregular nos pontos identificados",
    "esconderijo": "Apresentação de alternativas estruturais para mitigar pontos de ocultação",
    "lixo_entulho": "Retirada de lixo e entulho com cronograma de coleta intensificado",
    "ponto_cego_camera": "Avaliação e instalação de câmeras adicionais para cobertura visual",
    "outro": "Avaliação técnica caso a caso pela secretaria competente",
}


# ============================================================
# IDENTIFICAÇÃO DA ÁREA
# ============================================================

@dataclass
class IdentificacaoArea:
    nome_area: str
    n_trechos_criticos: int
    aisp: str
    base_fm: str
    bairros: str
    subprefeitura: str
    dp: str
    bpm: str
    area_sob_influencia: str


def montar_identificacao(
    area: AreaPoligonoFM,
    relints_area: list[RelintEstruturado],
) -> IdentificacaoArea:
    # Trechos críticos = quantidade de RELINTs distintos + pontos de receptação
    n_trechos = max(
        len(relints_area),
        sum(len(r.pontos_receptacao) for r in relints_area),
    ) or 1

    faccao = next(
        (r.orcrim_influencia for r in relints_area if r.orcrim_influencia),
        None,
    )
    influencia = (
        f"Comunidades próximas sob domínio do {faccao}"
        if faccao else "Sem influência faccional identificada"
    )

    return IdentificacaoArea(
        nome_area=area.nome_area,
        n_trechos_criticos=n_trechos,
        aisp=area.aisp,
        base_fm=area.base_fm,
        bairros="/".join(area.bairros),
        subprefeitura=area.subprefeitura,
        dp=area.dp or "—",
        bpm=area.bpm or "—",
        area_sob_influencia=influencia,
    )


# ============================================================
# INDICADORES DO PERÍODO
# ============================================================

@dataclass
class IndicadoresPeriodo:
    periodo_label: str
    roubos: int
    furtos: int
    total: int
    ranking_pct: str
    posicao_ranking: str
    variacao_anterior: str


def montar_indicadores(
    ocorrencias_area: list[Ocorrencia],
    bingos_todos: list[BingoArea],
    poligono_id: str,
    comparativo: Optional[ComparativoEvolucao],
    periodo_inicio: Optional[date],
    periodo_fim: Optional[date],
) -> IndicadoresPeriodo:
    n_roubos = sum(1 for o in ocorrencias_area if o.tipo.startswith("roubo"))
    n_furtos = sum(1 for o in ocorrencias_area if o.tipo.startswith("furto"))
    total = len(ocorrencias_area)

    # Ranking entre as áreas pelo score
    posicao = next(
        (i + 1 for i, b in enumerate(bingos_todos) if b.poligono_fm_id == poligono_id),
        len(bingos_todos),
    )
    pct = (posicao / max(1, len(bingos_todos))) * 100

    # Período label
    if periodo_inicio and periodo_fim:
        label = f"{periodo_inicio:%d/%m/%Y} a {periodo_fim:%d/%m/%Y}"
    else:
        label = "Todo o histórico"

    # Variação
    if comparativo:
        var = (
            f"Roubos {comparativo.variacao_roubos_pct:+.1f}% · "
            f"Furtos {comparativo.variacao_furtos_pct:+.1f}%"
        )
    else:
        var = "N/A (sem snapshot anterior)"

    return IndicadoresPeriodo(
        periodo_label=label,
        roubos=n_roubos,
        furtos=n_furtos,
        total=total,
        ranking_pct=f"{pct:.1f}%",
        posicao_ranking=f"{posicao}º lugar",
        variacao_anterior=var,
    )


def top_tipos_ocorrencia(
    ocorrencias_area: list[Ocorrencia], n: int = 3,
) -> list[dict]:
    """Top N tipos de ocorrência por volume."""
    contagem = Counter(o.tipo for o in ocorrencias_area)
    top = contagem.most_common(n)
    resultado = []
    for i, (tipo, qtd) in enumerate(top, 1):
        # Última ocorrência desse tipo
        ultimas = sorted(
            (o for o in ocorrencias_area if o.tipo == tipo),
            key=lambda o: o.data_hora, reverse=True,
        )
        data_ultima = (
            ultimas[0].data_hora.strftime("%d/%m/%Y") if ultimas else "—"
        )
        resultado.append({
            "rank": f"{i}º",
            "tipo": ROTULO_TIPO_OCORRENCIA.get(tipo, tipo),
            "qtd": qtd,
            "data_ultima": data_ultima,
            "variacao": "—",
        })
    return resultado


# ============================================================
# ANÁLISE TEMPORAL
# ============================================================

@dataclass
class AnaliseTemporal:
    periodo_predominante: str
    dia_horario_critico: str


def montar_analise_temporal(ocorrencias_area: list[Ocorrencia]) -> AnaliseTemporal:
    if not ocorrencias_area:
        return AnaliseTemporal(
            periodo_predominante="Sem ocorrências no período.",
            dia_horario_critico="N/A",
        )

    horas = Counter(o.hora for o in ocorrencias_area)
    dias = Counter(o.dia_semana for o in ocorrencias_area)

    hora_pico = horas.most_common(1)[0][0]
    hora_min = min(h for h, _ in horas.most_common(5))
    hora_max = max(h for h, _ in horas.most_common(5))

    dia_top = dias.most_common(1)[0][0]

    periodo = (
        f"Todos os dias entre {hora_min:02d}h e {hora_max:02d}h, "
        f"com destaque para o pico concentrado às {hora_pico:02d}h."
    )

    critico = (
        f"{ROTULO_DIA.get(dia_top, dia_top).capitalize()}, "
        f"das {hora_pico:02d}h às {(hora_pico+1) % 24:02d}h."
    )

    return AnaliseTemporal(
        periodo_predominante=periodo,
        dia_horario_critico=critico,
    )


# ============================================================
# DINÂMICA CRIMINAL (síntese qualitativa)
# ============================================================

def montar_dinamica_criminal(
    relints_area: list[RelintEstruturado],
    denuncias_area: list[DenunciaDisque],
    ocorrencias_area: list[Ocorrencia],
) -> dict:
    if not relints_area:
        return {
            "modalidade": "Sem RELINT vinculado.",
            "areas_fuga": "Não mapeadas.",
            "descricao": (
                "Sem RELINT consolidado para a área no período. "
                "Análise depende exclusivamente da mancha quantitativa e "
                "do volume de denúncias do Disque."
            ),
        }

    r0 = relints_area[0]

    # Modalidade predominante (cruza ocorrências × RELINT)
    if ocorrencias_area:
        modalidades = Counter(o.modalidade_crime for o in ocorrencias_area)
        top_mod, qtd_mod = modalidades.most_common(1)[0]
        pct = (qtd_mod / len(ocorrencias_area)) * 100
        modalidade_str = (
            f"{top_mod.replace('_', ' ')} ({pct:.0f}% das ocorrências), "
            f"confirmando o padrão descrito em RELINT."
        )
    else:
        modalidade_str = r0.modus_operandi_principal

    # Áreas de fuga
    if r0.rotas_fuga:
        areas_fuga = "; ".join(rt.descricao for rt in r0.rotas_fuga)
    else:
        areas_fuga = "Não mapeadas no RELINT consolidado."

    # Descrição consolidada
    desc = r0.modus_operandi_principal
    if r0.pontos_receptacao:
        desc += (
            f" Pontos de receptação identificados em "
            f"{len(r0.pontos_receptacao)} locais."
        )
    if r0.orcrim_influencia:
        desc += (
            f" Área sob influência de {r0.orcrim_influencia}, "
            f"recomendando postura defensiva."
        )

    return {
        "modalidade": modalidade_str,
        "areas_fuga": areas_fuga,
        "descricao": desc,
    }


# ============================================================
# EFETIVO EMPREGADO – FORÇA MUNICIPAL (Tabela 5×4)
# ============================================================

@dataclass
class LinhaEfetivo:
    campo: str
    situacao_atual: str
    sugestao: str
    justificativa: str


def montar_tabela_efetivo(
    area: AreaPoligonoFM,
    recomendacao: RecomendacaoModalidade,
    bingo: BingoArea,
    efetivo_sugerido: int,
) -> list[LinhaEfetivo]:
    pct_total = (efetivo_sugerido / TOTAL_EFETIVO_FM) * 100

    return [
        LinhaEfetivo(
            campo="Nº de Agentes por Turno",
            situacao_atual=(
                f"{area.efetivo_padrao} agentes do total de {TOTAL_EFETIVO_FM} "
                f"({(area.efetivo_padrao / TOTAL_EFETIVO_FM) * 100:.1f}%)"
            ),
            sugestao=(
                f"{efetivo_sugerido} agentes ({pct_total:.1f}% do total)"
                if efetivo_sugerido != area.efetivo_padrao else "Manter"
            ),
            justificativa=(
                f"Score de risco {bingo.componentes.score_final:.2f}, "
                f"{bingo.n_camadas_ativas} de 4 camadas ativas."
            ),
        ),
        LinhaEfetivo(
            campo="Locais de Cobertura",
            situacao_atual=area.base_fm,
            sugestao=(
                f"Reforço em {len(recomendacao.pontos_intercepcao)} pontos "
                f"de interceptação"
                if recomendacao.pontos_intercepcao else "Manter área atual"
            ),
            justificativa=(
                "Rotas de fuga mapeadas em RELINT priorizam pontos de "
                "interceptação geográfica."
                if recomendacao.pontos_intercepcao
                else "Sem rotas de fuga consolidadas."
            ),
        ),
        LinhaEfetivo(
            campo="Horário de Cobertura",
            situacao_atual="—",
            sugestao=recomendacao.horario_recomendado,
            justificativa=(
                "Pico criminal concentrado no período recomendado, conforme "
                "análise temporal das ocorrências."
            ),
        ),
        LinhaEfetivo(
            campo="Dias de Cobertura",
            situacao_atual="—",
            sugestao=", ".join(
                ROTULO_DIA.get(d, d) for d in recomendacao.dias_recomendados
            ),
            justificativa="Dias críticos identificados no histórico recente.",
        ),
        LinhaEfetivo(
            campo="Modalidade de Emprego",
            situacao_atual="—",
            sugestao=ROTULO_MODALIDADE_FM.get(
                recomendacao.modalidade_principal,
                recomendacao.modalidade_principal,
            ),
            justificativa=recomendacao.justificativa,
        ),
    ]


# ============================================================
# RESUMO EXECUTIVO – 4 PERGUNTAS NORTEADORAS
# ============================================================

@dataclass
class PerguntaNorteadora:
    pergunta: str
    diagnostico: str
    operacao: str
    observacao: str


def gerar_perguntas_norteadoras(
    area: AreaPoligonoFM,
    bingo: BingoArea,
    recomendacao: RecomendacaoModalidade,
    ocorrencias_area: list[Ocorrencia],
    relints_area: list[RelintEstruturado],
    fatores_area: list[FatorUrbano],
    analise_temporal: AnaliseTemporal,
) -> list[PerguntaNorteadora]:
    perguntas: list[PerguntaNorteadora] = []

    # 1. Rota da FM × locais de maior incidência
    n_pontos = len(recomendacao.pontos_intercepcao)
    n_trechos = max(n_pontos, len(relints_area))
    p1_diag = (
        f"Total de {n_trechos} trechos críticos identificados na área. "
        f"{n_pontos} pontos de interceptação sugeridos a partir das "
        f"rotas de fuga mapeadas."
    ) if n_trechos else (
        "Concentração de ocorrências dispersa; sem trechos críticos isolados."
    )
    p1_op = (
        f"Reforço de patrulhamento concentrado nos pontos de interceptação."
        if n_pontos else f"Manter cobertura padrão em {area.base_fm}."
    )
    perguntas.append(PerguntaNorteadora(
        pergunta="Locais de maior incidência criminal estão coincidindo com a rota da FM?",
        diagnostico=p1_diag,
        operacao=p1_op,
        observacao="Avaliar ajuste pelo gestor.",
    ))

    # 2. Horário × QMD
    perguntas.append(PerguntaNorteadora(
        pergunta="Horário de maior incidência criminal está coincidindo com QMD?",
        diagnostico=f"Maior incidência: {analise_temporal.dia_horario_critico}",
        operacao=f"Sugestão de QMD: {recomendacao.horario_recomendado}",
        observacao="Avaliar alinhamento com escala vigente.",
    ))

    # 3. Dinâmica criminal × modelo de emprego
    modus_top = "indefinido"
    if ocorrencias_area:
        modus_top = Counter(
            o.modalidade_crime for o in ocorrencias_area
        ).most_common(1)[0][0]
    p3_diag = (
        f"Modalidade criminal predominante: {modus_top.replace('_', ' ')}. "
        f"Modelo da FM sugerido: "
        f"{ROTULO_MODALIDADE_FM.get(recomendacao.modalidade_principal, recomendacao.modalidade_principal)}."
    )
    p3_op = (
        f"{recomendacao.n_viaturas} viatura(s) · "
        f"{recomendacao.n_motos} moto(s) · "
        f"{recomendacao.n_agentes_a_pe} a pé."
    )
    perguntas.append(PerguntaNorteadora(
        pergunta="Dinâmica criminal coincide com o modelo de emprego da FM?",
        diagnostico=p3_diag,
        operacao=p3_op,
        observacao="Compatibilidade entre modus e modalidade da FM.",
    ))

    # 4. Fatores urbanos × órgãos
    if fatores_area:
        orgaos_distintos = sorted({f.orgao_responsavel for f in fatores_area})
        p4_diag = (
            f"{len(fatores_area)} fatores ativos envolvendo "
            f"{len(orgaos_distintos)} órgãos: "
            f"{', '.join(ROTULO_ORGAO.get(o, o) for o in orgaos_distintos)}."
        )
    else:
        p4_diag = "Sem fatores urbanos cadastrados para a área no período."
    perguntas.append(PerguntaNorteadora(
        pergunta="Fatores relevantes para o crime estão sendo resolvidos pelos órgãos complementares?",
        diagnostico=p4_diag,
        operacao="Ver Seção 4 e Plano de Ação.",
        observacao="Cobrança formal na reunião CompStat.",
    ))

    return perguntas


# ============================================================
# FATORES DE INCIDÊNCIA CRIMINAL (Seção 4)
# ============================================================

@dataclass
class LinhaFator:
    fator: str
    descricao: str
    responsavel: str


def montar_tabela_fatores(
    fatores_area: list[FatorUrbano],
) -> list[LinhaFator]:
    """Agrupa fatores por categoria, consolidando responsável e descrições."""
    if not fatores_area:
        return []

    # Agrupa por categoria
    por_categoria: dict[CategoriaFatorUrbano, list[FatorUrbano]] = {}
    for f in fatores_area:
        por_categoria.setdefault(f.categoria, []).append(f)

    linhas: list[LinhaFator] = []
    # Ordena por severidade (críticas primeiro)
    ordem_sev = {"critica": 0, "alta": 1, "media": 2, "baixa": 3}
    for categoria, fs in sorted(
        por_categoria.items(),
        key=lambda kv: min(ordem_sev.get(f.severidade, 4) for f in kv[1]),
    ):
        descricoes = [f.descricao for f in fs]
        descricao_consolidada = " ".join(descricoes)
        if len(descricao_consolidada) > 600:
            descricao_consolidada = descricao_consolidada[:597] + "..."

        # Múltiplos órgãos pra uma categoria
        orgaos = sorted({ROTULO_ORGAO.get(f.orgao_responsavel, f.orgao_responsavel) for f in fs})

        linhas.append(LinhaFator(
            fator=ROTULO_CATEGORIA.get(categoria, categoria),
            descricao=descricao_consolidada,
            responsavel=", ".join(orgaos),
        ))

    return linhas


# ============================================================
# PLANO DE AÇÃO E RESPONSABILIZAÇÃO (Seção 5) – PRÉ-POPULADO
# ============================================================

@dataclass
class LinhaPlanoAcao:
    acao: str
    responsavel: str
    prazo: str
    status: str


def montar_plano_acao(
    fatores_area: list[FatorUrbano],
    recomendacao: RecomendacaoModalidade,
    area: AreaPoligonoFM,
    acoes_externas: Optional[list[AcaoRecomendada]] = None,
) -> list[LinhaPlanoAcao]:
    """Pré-popula plano de ação a partir dos fatores e da recomendação FM.

    Cada fator urbano gera 1 ação. A recomendação de patrulhamento gera
    1 ação para a Força Municipal. Ações externas adicionais (vindas
    do `AcaoRecomendada`) são anexadas.
    """
    linhas: list[LinhaPlanoAcao] = []

    # Prazos sugeridos por severidade
    PRAZO_SEV = {
        "critica": "7 dias",
        "alta": "15 dias",
        "media": "30 dias",
        "baixa": "60 dias",
    }

    # Agrupa fatores por categoria para evitar duplicatas
    por_categoria: dict[CategoriaFatorUrbano, list[FatorUrbano]] = {}
    for f in fatores_area:
        por_categoria.setdefault(f.categoria, []).append(f)

    for categoria, fs in por_categoria.items():
        # Pior severidade do grupo dita o prazo
        ordem_sev = {"critica": 0, "alta": 1, "media": 2, "baixa": 3}
        pior_sev = min(fs, key=lambda f: ordem_sev.get(f.severidade, 4)).severidade
        prazo = PRAZO_SEV.get(pior_sev, "30 dias")

        acao_texto = SUGESTAO_ACAO_POR_CATEGORIA.get(
            categoria, f"Intervenção sobre {ROTULO_CATEGORIA.get(categoria, categoria)}"
        )

        orgaos = sorted({ROTULO_ORGAO.get(f.orgao_responsavel, f.orgao_responsavel) for f in fs})

        linhas.append(LinhaPlanoAcao(
            acao=acao_texto,
            responsavel=", ".join(orgaos),
            prazo=prazo,
            status="Pendente",
        ))

    # Ação para a FM (sempre)
    linhas.append(LinhaPlanoAcao(
        acao=(
            f"Patrulhamento dirigido em modalidade "
            f"{ROTULO_MODALIDADE_FM.get(recomendacao.modalidade_principal, recomendacao.modalidade_principal).lower()}, "
            f"horário {recomendacao.horario_recomendado}, "
            f"dias {', '.join(ROTULO_DIA.get(d, d) for d in recomendacao.dias_recomendados)}"
        ),
        responsavel="Força Municipal",
        prazo="Imediato (próximo ciclo CompStat)",
        status="Em programação",
    ))

    # Ações externas adicionais (se houver)
    if acoes_externas:
        for a in acoes_externas:
            linhas.append(LinhaPlanoAcao(
                acao=a.descricao_acao,
                responsavel=ROTULO_ORGAO.get(
                    a.orgao_responsavel, a.orgao_responsavel,
                ),
                prazo=f"{a.prazo_sugerido_dias} dias",
                status="Pendente",
            ))

    return linhas
