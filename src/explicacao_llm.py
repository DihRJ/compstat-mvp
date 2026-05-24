"""
Explicação opcional da sugestão de efetivo via Claude (Anthropic API).

Quebra deliberadamente a regra 9 do CLAUDE.md, mas com escopo restrito:
  - Chamada é OPCIONAL (botão na UI)
  - Não substitui a heurística determinística
  - Falha sem chave de API com mensagem clara

Requer:
  - ANTHROPIC_API_KEY como variável de ambiente OU
  - st.secrets["ANTHROPIC_API_KEY"] no Streamlit Cloud
"""

from __future__ import annotations

import os

from schemas import AreaPoligonoFM, BingoArea, RelintEstruturado
from sugestao_efetivo import SugestaoEfetivo


MODEL = "claude-haiku-4-5"


def _get_api_key() -> str | None:
    """Tenta env var primeiro, depois Streamlit secrets."""
    chave = os.environ.get("ANTHROPIC_API_KEY")
    if chave:
        return chave
    try:
        import streamlit as st
        return st.secrets.get("ANTHROPIC_API_KEY")  # type: ignore[no-any-return]
    except Exception:
        return None


def explicar_sugestao_efetivo(
    area: AreaPoligonoFM,
    bingo: BingoArea,
    sugestao: SugestaoEfetivo,
    n_ocorrencias: int,
    relints: list[RelintEstruturado],
) -> str:
    """Pede ao Claude que explique a sugestão em linguagem natural.

    Retorna um parágrafo único voltado para gestor da Prefeitura.
    Levanta RuntimeError se a chave de API não estiver configurada.
    """
    chave = _get_api_key()
    if not chave:
        raise RuntimeError(
            "ANTHROPIC_API_KEY não configurada. "
            "Defina como variável de ambiente local ou como secret no Streamlit Cloud."
        )

    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError(
            "Pacote `anthropic` não instalado. "
            "Adicione `anthropic>=0.40` ao requirements.txt."
        ) from e

    cliente = anthropic.Anthropic(api_key=chave)

    modus_relint = (
        relints[0].modus_operandi_principal[:200]
        if relints else "sem RELINT vinculado"
    )
    faccao = (
        relints[0].orcrim_influencia
        if relints and relints[0].orcrim_influencia else "nenhuma identificada"
    )

    # Breakdown como contexto curto
    breakdown_str = "\n".join(
        f"- {c.rotulo}: {c.detalhe} (+{c.contribuicao})"
        for c in sugestao.componentes
    )

    prompt = f"""Você é um analista da Força Municipal do Rio de Janeiro escrevendo para um gestor.

Dados da área "{area.nome_area}" ({area.aisp}, {area.base_fm}):
- Score de risco: {bingo.componentes.score_final:.2f} (0 a 1)
- Camadas ativas: {bingo.n_camadas_ativas} de 4
- Ocorrências no período: {n_ocorrencias}
- Modus operandi: {modus_relint}
- Facção: {faccao}
- Bairros: {", ".join(area.bairros)}

A heurística calculou {sugestao.efetivo_sugerido} agentes com este breakdown:
{breakdown_str}

Escreva UM PARÁGRAFO ÚNICO (3-5 frases, sem listas, sem títulos) explicando ao gestor por que {sugestao.efetivo_sugerido} agentes faz sentido para esta área e período. Use português brasileiro institucional, evite jargão técnico e cite 2-3 dos fatores mais relevantes. Não use travessões nem emoji."""

    resp = cliente.messages.create(
        model=MODEL,
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )

    # Extrai texto do primeiro bloco
    for bloco in resp.content:
        if hasattr(bloco, "text"):
            return bloco.text.strip()
    return "Sem resposta do modelo."
