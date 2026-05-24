from typing import Optional
"""
QMD - Quadro de Missão Diária.

Documento gerado por área que vai para a base da FM como ordem de serviço.

Equivalente ao Boletim de Briefing das polícias militares: o agente recebe
no início do turno e leva consigo para a operação.

Conteúdo padrão:
  - Área de atuação (polígono + bairros)
  - Efetivo + modalidade
  - Horários e dias
  - Pontos prioritários (3-5 do bingo)
  - Rotas de fuga para monitorar
  - Modus operandi conhecido
  - Apoio interinstitucional esperado
"""

from datetime import date
from schemas import (
    QMD,
    BingoArea,
    RecomendacaoModalidade,
    RelintEstruturado,
    AreaPoligonoFM,
    AcaoRecomendada,
    Coordenada,
    OrgaoMunicipal,
    TipoOcorrencia,
)


# ============================================================
# GERAÇÃO DO QMD
# ============================================================

def gerar_qmd(
    area: AreaPoligonoFM,
    bingo: BingoArea,
    recomendacao: RecomendacaoModalidade,
    relints_area: list[RelintEstruturado],
    acoes_pendentes_outros_orgaos: list[AcaoRecomendada],
    data_ref: Optional[date] = None,
) -> QMD:
    """
    Monta QMD consolidado para a área.

    O QMD é a ordem de serviço que o agente da FM leva para a operação.
    """
    data_ref = data_ref or date.today()

    # Pontos prioritários: centroide + pontos de receptação dos RELINTs
    pontos_prio: list[Coordenada] = []
    if area.centroide:
        pontos_prio.append(area.centroide)

    for r in relints_area:
        for p in r.pontos_receptacao:
            pontos_prio.append(p)
        for p in r.esconderijos:
            pontos_prio.append(p)
        # Adicionar pontos críticos das rotas
        for rota in r.rotas_fuga:
            if rota.pontos:
                pontos_prio.append(rota.pontos[0])  # início da rota

    pontos_prio = pontos_prio[:5]  # cap em 5

    # Rotas a monitorar (descrições legíveis)
    rotas: list[str] = []
    for r in relints_area:
        for rota in r.rotas_fuga:
            rotas.append(rota.descricao)

    # Modus operandi consolidado
    if relints_area:
        modus = " | ".join(r.modus_operandi_principal for r in relints_area[:2])
    else:
        modus = "Sem RELINT disponivel. Operacao deve focar prevencao geral."

    # Facção da área (se houver)
    faccao = next(
        (r.orcrim_influencia for r in relints_area if r.orcrim_influencia),
        None,
    )

    # Tipos de crime alvo (do RELINT ou default roubo/furto)
    tipos_alvo: list[TipoOcorrencia] = []
    if relints_area:
        for r in relints_area:
            tipos_alvo.extend(r.tipos_ocorrencia_alvo)
        # Remover duplicatas
        tipos_alvo = list(set(tipos_alvo))
    else:
        tipos_alvo = ["roubo_transeunte", "roubo_celular", "furto_transeunte"]

    # Apoio interinstitucional (ações pendentes de outros órgãos na área)
    apoio: list[dict] = []
    for acao in acoes_pendentes_outros_orgaos:
        if acao.orgao_responsavel != "FM":
            apoio.append({
                "orgao": acao.orgao_responsavel,
                "acao": acao.descricao_acao[:150],
                "prazo_dias": acao.prazo_sugerido_dias,
                "prioridade": acao.prioridade,
            })
    apoio = apoio[:5]  # cap em 5

    return QMD(
        poligono_fm_id=area.poligono_id,
        nome_area=area.nome_area,
        data_referencia=data_ref,
        base_fm=area.base_fm,
        efetivo_alocado=(
            recomendacao.n_viaturas * 4
            + recomendacao.n_motos * 2
            + recomendacao.n_agentes_a_pe
        ),
        modalidade=recomendacao.modalidade_principal,
        n_viaturas=recomendacao.n_viaturas,
        n_motos=recomendacao.n_motos,
        n_agentes_a_pe=recomendacao.n_agentes_a_pe,
        horario_cobertura=recomendacao.horario_recomendado,
        dias_cobertura=recomendacao.dias_recomendados,
        pontos_prioritarios=pontos_prio if pontos_prio else [Coordenada(lat=0, lng=0)],
        rotas_monitorar=rotas,
        modus_operandi_atencao=modus,
        orcrim_atencao=faccao,
        foco_tipos_crime=tipos_alvo,
        apoio_esperado=apoio,
        observacoes=(
            f"Score do bingo: {bingo.componentes.score_final:.2f}. "
            f"{bingo.justificativa[:200]}"
        ),
    )


# ============================================================
# RENDER EM MARKDOWN (para preview rápido)
# ============================================================

def qmd_para_markdown(qmd: QMD) -> str:
    """Converte QMD em markdown legível para apresentação rápida."""
    lines = [
        f"# QMD - {qmd.nome_area}",
        f"",
        f"**Data:** {qmd.data_referencia.isoformat()} | **Base:** {qmd.base_fm}",
        f"",
        f"## Efetivo",
        f"",
        f"- **Total:** {qmd.efetivo_alocado} agentes",
        f"- **Modalidade principal:** {qmd.modalidade}",
        f"- **Viaturas:** {qmd.n_viaturas}",
        f"- **Motos:** {qmd.n_motos}",
        f"- **A pe:** {qmd.n_agentes_a_pe}",
        f"",
        f"## Operacao",
        f"",
        f"- **Horario:** {qmd.horario_cobertura}",
        f"- **Dias:** {', '.join(qmd.dias_cobertura)}",
        f"- **Foco em:** {', '.join(qmd.foco_tipos_crime)}",
        f"",
        f"## Pontos prioritarios ({len(qmd.pontos_prioritarios)})",
        f"",
    ]
    for i, p in enumerate(qmd.pontos_prioritarios, 1):
        desc = p.descricao or "(sem descricao)"
        lines.append(f"{i}. ({p.lat:.5f}, {p.lng:.5f}) - {desc}")

    if qmd.rotas_monitorar:
        lines.extend([
            f"",
            f"## Rotas de fuga a monitorar ({len(qmd.rotas_monitorar)})",
            f"",
        ])
        for r in qmd.rotas_monitorar:
            lines.append(f"- {r}")

    lines.extend([
        f"",
        f"## Inteligencia",
        f"",
        f"- **Modus operandi:** {qmd.modus_operandi_atencao}",
    ])
    if qmd.orcrim_atencao:
        lines.append(f"- **Faccao na area:** {qmd.orcrim_atencao}")

    if qmd.apoio_esperado:
        lines.extend([
            f"",
            f"## Apoio interinstitucional ({len(qmd.apoio_esperado)})",
            f"",
        ])
        for a in qmd.apoio_esperado:
            lines.append(
                f"- **{a['orgao']}** [{a['prioridade']}, prazo {a['prazo_dias']}d]: "
                f"{a['acao']}"
            )

    if qmd.observacoes:
        lines.extend([
            f"",
            f"## Observacoes",
            f"",
            qmd.observacoes,
        ])

    return "\n".join(lines)
