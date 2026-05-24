"""
Streamlit app - UI integrada do CompStat IA.

6 páginas:
  1. Dashboard: mapa interativo + KPIs
  2. Score / Bingos: detalhamento de cada área
  3. Editor de áreas: CRUD completo (criar, editar, desativar, excluir)
  4. QMD: ver e baixar Quadro de Missão Diária
  5. Evolução 90d: comparativo antes/depois
  6. DOCX: gerar e baixar relatório editável

Rodar: streamlit run src/streamlit_app.py
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path
from datetime import date, datetime, timedelta
from statistics import mean

import streamlit as st

# Permite rodar via `streamlit run src/streamlit_app.py`
sys.path.insert(0, str(Path(__file__).parent))

# Paths absolutos (funciona em Streamlit Cloud, Docker, scripts)
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

from schemas import (
    AreaPoligonoFM, RelintEstruturado, Ocorrencia, DenunciaDisque, FatorUrbano,
    SnapshotIndicadores, AcaoRecomendada,
)
from area_crud import AreasFMStore
from score_engine import calcular_bingos_todas_areas
from recommendation import sugerir_modalidade
from qmd_generator import gerar_qmd, qmd_para_markdown
from evolution import carregar_snapshots, comparar_todas_areas
from heatmap import construir_mapa_folium, gerar_heatmap_temporal, gerar_grafico_evolucao
from docx_generator import gerar_relatorio_docx
from sugestao_efetivo import sugerir_efetivo, SugestaoEfetivo
from importador import TIPOS_DOCUMENTO, importar, salvar


# ============================================================
# CONFIG GLOBAL + DESIGN TOKENS
# ============================================================

st.set_page_config(
    page_title="CompStat IA",
    page_icon="🛡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    html, body, [class*="css"], .stApp {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                     "Helvetica Neue", Arial, sans-serif;
    }
    h1 {
        color:#1E2761; font-weight:700; font-size:2rem;
        letter-spacing:-0.01em; margin-bottom:.25rem;
    }
    h2 {
        color:#1E2761; font-weight:600; font-size:1.35rem;
        border-bottom:2px solid #1E2761; padding-bottom:.35rem;
        margin-top:1.5rem;
    }
    h3 { color:#1E2761; font-weight:600; font-size:1.1rem; }
    .stTabs [data-baseweb="tab-list"] { gap:4px; border-bottom:1px solid #E0E0E0; }
    .stTabs [aria-selected="true"] {
        color:#1E2761 !important; border-bottom:3px solid #1E2761 !important;
        font-weight:600;
    }
    [data-testid="stMetricValue"] {
        color:#1E2761; font-weight:700; font-size:1.75rem;
    }
    [data-testid="stMetricLabel"] {
        font-size:.78rem; text-transform:uppercase;
        letter-spacing:.04em; color:#555;
    }
    .stButton>button[kind="primary"] {
        background:#1E2761; border-color:#1E2761;
    }
    .stButton>button[kind="primary"]:hover {
        background:#15204D; border-color:#15204D;
    }
    .badge {
        display:inline-block; padding:.15rem .65rem; border-radius:999px;
        font-size:.78rem; font-weight:600; color:#fff;
    }
    .badge-alto   { background:#C62828; }
    .badge-medio  { background:#EF6C00; }
    .badge-baixo  { background:#2E7D32; }
    .badge-neutro { background:#607D8B; }
    .legend-box {
        background:#fff; border:1px solid #E0E0E0; border-radius:6px;
        padding:.6rem .8rem; font-size:.82rem; margin:.5rem 0;
    }
    .legend-row {
        display:flex; align-items:center; gap:.5rem; margin:.15rem 0;
    }
    .legend-sq {
        width:14px; height:14px; border-radius:3px; display:inline-block;
    }
    .institucional {
        border-left:4px solid #1E2761; padding:.4rem .8rem;
        background:#FAFBFD; margin-bottom:.5rem;
    }
    .termo {
        border-bottom:1px dotted #1E2761; cursor:help; color:#1E2761;
        font-weight:500;
    }
    .breadcrumb-area {
        display:flex; align-items:center; gap:.4rem;
        background:#1E2761; color:#fff; padding:.4rem .65rem;
        border-radius:6px; font-size:.78rem; line-height:1.2;
        margin:.4rem 0;
    }
    .empty-state {
        background:#FAFBFD; border:1px dashed #C7CCD9; border-radius:8px;
        padding:1.5rem; text-align:center; color:#555;
    }
    .empty-state .icon { font-size:2rem; margin-bottom:.5rem; }
    .empty-state .titulo {
        font-weight:600; color:#1E2761; font-size:1.05rem;
        margin-bottom:.25rem;
    }
    .footer-inst {
        text-align:center; color:#888; font-size:.75rem;
        padding:1.5rem 0 .5rem; border-top:1px solid #EEE; margin-top:2rem;
    }
    .eyebrow {
        font-size:.72rem; text-transform:uppercase; letter-spacing:.08em;
        color:#888; font-weight:700; margin:1.5rem 0 .5rem;
    }
    .sb-section {
        font-size:.7rem; text-transform:uppercase; letter-spacing:.08em;
        color:#888; font-weight:600; margin:.6rem 0 .25rem;
    }
    .step-pill {
        display:inline-flex; align-items:center; gap:.55rem;
        font-size:.88rem; color:#1E2761; font-weight:600;
        margin:.4rem 0 .5rem;
    }
    .step-num {
        background:#1E2761; color:#fff; width:22px; height:22px;
        border-radius:50%; display:inline-flex; align-items:center;
        justify-content:center; font-size:.72rem;
    }
    .evo-card { border:1px solid #E0E0E0; border-radius:6px;
        padding:1rem; margin-bottom:.65rem; }
    .evo-card-melhora { border-left:4px solid #2E7D32; }
    .evo-card-piora   { border-left:4px solid #C62828; }
    .evo-card-estavel { border-left:4px solid #9E9E9E; }
    footer { visibility:hidden; }
    #MainMenu { visibility:hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HELPERS VISUAIS
# ============================================================

def badge_score(v: float) -> str:
    """Badge HTML colorida por severidade do score."""
    if v > 0.6:
        cls = "badge-alto"
    elif v > 0.3:
        cls = "badge-medio"
    else:
        cls = "badge-baixo"
    return f"<span class='badge {cls}'>{v:.2f}</span>"


def emoji_score(v: float) -> str:
    return "🔴" if v > 0.6 else "🟠" if v > 0.3 else "🟢"


def navegar_para(pagina: str, area_id: str | None = None) -> None:
    """Pula para outra página preservando contexto."""
    st.session_state["pagina"] = pagina
    if area_id is not None:
        st.session_state["area_selecionada"] = area_id
    st.rerun()


# ----- Helpers de design padronizados (QW1/QW2/QW3) -----

GLOSSARIO = {
    "RELINT": "Relatório de Inteligência produzido pelo BPM/FM (fonte oficial qualitativa).",
    "AISP": "Área Integrada de Segurança Pública (divisão geográfica do policiamento estadual).",
    "BPM": "Batalhão da Polícia Militar responsável pela área.",
    "DP": "Delegacia de Polícia responsável pela área.",
    "QMD": "Quadro de Missão Diária — ordem de serviço entregue à base da FM.",
    "Bingo": "Cruzamento de 4+ camadas de risco (mancha, RELINT, fator urbano, Disque) na mesma área.",
    "FM": "Força Municipal — Divisão de Elite da Guarda Municipal do Rio de Janeiro.",
    "PSR": "População em Situação de Rua.",
    "ORCRIM": "Organização Criminosa que exerce influência territorial.",
    "CPSR": "Censo da População em Situação de Rua.",
}


def termo(rotulo: str) -> str:
    """Devolve HTML com tooltip explicativo para termo técnico."""
    desc = GLOSSARIO.get(rotulo.upper())
    if not desc:
        return rotulo
    return f"<abbr class='termo' title='{desc}'>{rotulo}</abbr>"


def header_pagina(
    titulo: str,
    subtitulo: str | None = None,
    com_periodo: bool = True,
) -> None:
    """Cabeçalho consistente para todas as páginas."""
    st.title(titulo)
    if com_periodo and subtitulo:
        st.caption(f"{subtitulo} · Período: **{label_periodo()}**")
    elif com_periodo:
        st.caption(f"Período: **{label_periodo()}**")
    elif subtitulo:
        st.caption(subtitulo)


def empty_state(
    icone: str,
    titulo: str,
    descricao: str,
    cta_label: str | None = None,
    cta_target_pagina: str | None = None,
    key: str | None = None,
) -> None:
    """Empty state amigável com CTA opcional."""
    st.markdown(
        f"<div class='empty-state'>"
        f"<div class='icon'>{icone}</div>"
        f"<div class='titulo'>{titulo}</div>"
        f"<div>{descricao}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    if cta_label and cta_target_pagina:
        if st.button(cta_label, type="primary", key=key or f"empty_cta_{titulo[:20]}"):
            navegar_para(cta_target_pagina)


def secao(titulo: str) -> None:
    """Subtítulo discreto (eyebrow) para sections dentro de uma página."""
    st.markdown(f"<div class='eyebrow'>{titulo}</div>", unsafe_allow_html=True)


def step_label(n: int, titulo: str, ativo: bool = True) -> None:
    """Indicador de etapa numerada para wizards multi-step."""
    cor = "#1E2761" if ativo else "#9E9E9E"
    st.markdown(
        f"<div class='step-pill' style='color:{cor}'>"
        f"<span class='step-num' style='background:{cor}'>{n}</span>"
        f"{titulo}</div>",
        unsafe_allow_html=True,
    )


def render_footer_institucional() -> None:
    """Rodapé discreto com fonte oficial."""
    st.markdown(
        "<div class='footer-inst'>"
        "Secretaria-Geral do CompStat Municipal · Prefeitura do Rio de Janeiro · "
        "Dados: <a href='https://github.com/CompStat-Rio/claude_impact_lab_compstat_rio' "
        "target='_blank' style='color:#888'>CompStat-Rio (público)</a>"
        "</div>",
        unsafe_allow_html=True,
    )


def render_editor_poligono(
    state_key: str,
    wkt_existente: str | None = None,
    map_key: str | None = None,
) -> str | None:
    """Renderiza mapa interativo para desenhar/editar um polígono.

    Salva o WKT do polígono desenhado em `st.session_state[state_key]`
    e retorna o WKT atual (do desenho OU do existente).
    """
    try:
        import folium
        from folium.plugins import Draw
        from streamlit_folium import st_folium
        from shapely import wkt as shapely_wkt
        from shapely.geometry import shape
    except ImportError:
        st.warning(
            "Para desenhar polígono no mapa: "
            "`pip install streamlit-folium folium shapely`"
        )
        return wkt_existente

    # Centro padrão: Rio de Janeiro
    centro = [-22.9068, -43.1729]
    zoom = 12

    # Se há polígono existente, centralizar nele
    if wkt_existente:
        try:
            geom = shapely_wkt.loads(wkt_existente)
            centro = [geom.centroid.y, geom.centroid.x]
            zoom = 14
        except Exception:
            pass

    m = folium.Map(location=centro, zoom_start=zoom, tiles="OpenStreetMap")

    # Mostrar polígono atual (se existir) em destaque
    if wkt_existente:
        try:
            geom = shapely_wkt.loads(wkt_existente)
            if geom.geom_type == "Polygon":
                coords = [[lat, lng] for lng, lat in geom.exterior.coords]
                folium.Polygon(
                    locations=coords,
                    color="#1E2761", weight=2,
                    fill=True, fill_color="#1E2761", fill_opacity=0.2,
                    tooltip="Polígono atual",
                ).add_to(m)
        except Exception:
            pass

    Draw(
        export=False,
        position="topleft",
        draw_options={
            "polygon": {
                "allowIntersection": False,
                "showArea": True,
                "shapeOptions": {"color": "#C62828", "weight": 3},
            },
            "rectangle": {
                "shapeOptions": {"color": "#C62828", "weight": 3},
            },
            "polyline": False,
            "circle": False,
            "marker": False,
            "circlemarker": False,
        },
        edit_options={"edit": True, "remove": True},
    ).add_to(m)

    out = st_folium(
        m, width=None, height=400,
        key=map_key or f"draw_{state_key}",
        returned_objects=["last_active_drawing"],
    )

    if out and out.get("last_active_drawing"):
        try:
            geom = shape(out["last_active_drawing"]["geometry"])
            novo_wkt = geom.wkt
            st.session_state[state_key] = novo_wkt
        except Exception as e:
            st.error(f"Falha ao converter desenho: {e}")

    # WKT corrente (desenhado tem prioridade)
    wkt_corrente = st.session_state.get(state_key) or wkt_existente

    if st.session_state.get(state_key):
        st.success("✓ Polígono capturado do mapa. Preview do WKT:")
        st.code(st.session_state[state_key], language="text")
        if st.button("🗑️ Limpar desenho", key=f"clear_{state_key}"):
            st.session_state.pop(state_key, None)
            st.rerun()

    return wkt_corrente


# ============================================================
# STATE INIT
# ============================================================

PAGINAS = [
    "Dashboard",
    "Score / Bingos",
    "Editor de areas",
    "Importar dados",
    "Quadro de Missao Diaria",
    "Evolucao 90 dias",
    "Relatorios",
]

if "pagina" not in st.session_state:
    st.session_state["pagina"] = "Dashboard"
if "area_selecionada" not in st.session_state:
    st.session_state["area_selecionada"] = None
if "periodo_preset" not in st.session_state:
    st.session_state["periodo_preset"] = "Todo"
if "periodo_inicio" not in st.session_state:
    st.session_state["periodo_inicio"] = None
if "periodo_fim" not in st.session_state:
    st.session_state["periodo_fim"] = None


# ============================================================
# DATA LOADING (cached)
# ============================================================

@st.cache_data(ttl=5)
def carregar_tudo(periodo_inicio: date | None = None, periodo_fim: date | None = None):
    """Carrega todos os dados base + calcula bingos.

    Se `periodo_inicio` ou `periodo_fim` forem passados, filtra
    `Ocorrencia.data_hora` antes de calcular o score.
    """
    store = AreasFMStore(DATA_DIR / "areas.json")
    areas = store.listar()

    def _read(path, model):
        p = DATA_DIR / path
        if not p.exists():
            return []
        return [model(**d) for d in json.loads(p.read_text(encoding="utf-8"))]

    ocorrencias_todas = _read("ocorrencias.json", Ocorrencia)
    relints = _read("relints.json", RelintEstruturado)
    denuncias = _read("denuncias.json", DenunciaDisque)
    fatores = _read("fatores_urbanos.json", FatorUrbano)

    # Filtro de período (apenas em ocorrencias.data_hora)
    if periodo_inicio or periodo_fim:
        def _no_periodo(o: Ocorrencia) -> bool:
            d = o.data_hora.date()
            if periodo_inicio and d < periodo_inicio:
                return False
            if periodo_fim and d > periodo_fim:
                return False
            return True
        ocorrencias = [o for o in ocorrencias_todas if _no_periodo(o)]
    else:
        ocorrencias = ocorrencias_todas

    bingos = calcular_bingos_todas_areas(areas, ocorrencias, relints, fatores, denuncias)

    return {
        "areas": areas,
        "ocorrencias": ocorrencias,
        "ocorrencias_todas": ocorrencias_todas,
        "relints": relints,
        "denuncias": denuncias,
        "fatores": fatores,
        "bingos": bingos,
        "periodo_inicio": periodo_inicio,
        "periodo_fim": periodo_fim,
        "carregado_em": datetime.now(),
    }


# ============================================================
# PERIODIZAÇÃO HELPERS
# ============================================================

PRESETS_DIAS = {
    "7d": 7,
    "30d": 30,
    "60d": 60,
    "90d": 90,
    "Todo": None,
}


def resolver_periodo() -> tuple[date | None, date | None]:
    """Lê session_state e devolve (inicio, fim) efetivos."""
    preset = st.session_state.get("periodo_preset", "Todo")
    if preset == "Custom":
        return (
            st.session_state.get("periodo_inicio"),
            st.session_state.get("periodo_fim"),
        )
    dias = PRESETS_DIAS.get(preset)
    if dias is None:
        return None, None
    hoje = date.today()
    return hoje - timedelta(days=dias), hoje


def label_periodo() -> str:
    """Texto curto para exibir o período corrente."""
    ini, fim = resolver_periodo()
    if ini is None and fim is None:
        return "Todo o histórico"
    return f"{ini:%d/%m/%Y} → {fim:%d/%m/%Y}"


def get_area(areas, pid):
    return next((a for a in areas if a.poligono_id == pid), None)


def get_bingo(bingos, pid):
    return next((b for b in bingos if b.poligono_fm_id == pid), None)


def area_default(areas):
    """Pega a área salva no state OU a primeira disponível."""
    salva = st.session_state.get("area_selecionada")
    if salva and any(a.poligono_id == salva for a in areas):
        return salva
    return areas[0].poligono_id if areas else None


# ============================================================
# SIDEBAR INSTITUCIONAL
# ============================================================

st.sidebar.markdown(
    "<div style='border-left:4px solid #1E2761; padding-left:.6rem'>"
    "<div style='color:#1E2761; font-weight:700; font-size:1.3rem; line-height:1.1'>"
    "CompStat IA</div>"
    "<div style='font-size:.78rem; color:#555'>"
    "Prefeitura do Rio · Forca Municipal</div>"
    "</div>",
    unsafe_allow_html=True,
)
st.sidebar.markdown("")

# Radio respeita session_state via index
idx_atual = PAGINAS.index(st.session_state["pagina"])
pagina_escolhida = st.sidebar.radio(
    "Navegacao", PAGINAS, index=idx_atual, label_visibility="visible",
)
if pagina_escolhida != st.session_state["pagina"]:
    st.session_state["pagina"] = pagina_escolhida
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("**Periodo de analise**")

# Presets
presets = list(PRESETS_DIAS.keys()) + ["Custom"]
preset_idx = presets.index(st.session_state.get("periodo_preset", "Todo"))
preset_escolhido = st.sidebar.radio(
    "Preset", presets, index=preset_idx, horizontal=True,
    label_visibility="collapsed", key="sb_preset_radio",
)
if preset_escolhido != st.session_state["periodo_preset"]:
    st.session_state["periodo_preset"] = preset_escolhido
    if preset_escolhido != "Custom":
        st.session_state["periodo_inicio"] = None
        st.session_state["periodo_fim"] = None
    st.cache_data.clear()
    st.rerun()

# Datas customizadas (visível só quando Custom)
if st.session_state["periodo_preset"] == "Custom":
    hoje = date.today()
    c1, c2 = st.sidebar.columns(2)
    ini = c1.date_input(
        "De", value=st.session_state.get("periodo_inicio") or hoje - timedelta(days=30),
        key="sb_data_inicio",
    )
    fim = c2.date_input(
        "Ate", value=st.session_state.get("periodo_fim") or hoje,
        key="sb_data_fim",
    )
    if ini != st.session_state.get("periodo_inicio") or fim != st.session_state.get("periodo_fim"):
        st.session_state["periodo_inicio"] = ini
        st.session_state["periodo_fim"] = fim
        st.cache_data.clear()
        st.rerun()

st.sidebar.caption(f"📅 {label_periodo()}")

# Breadcrumb da área selecionada (QW7)
_dados_carregados = carregar_tudo(*resolver_periodo())
_area_sel_id = st.session_state.get("area_selecionada")
if _area_sel_id:
    _area_sel = next(
        (a for a in _dados_carregados["areas"] if a.poligono_id == _area_sel_id),
        None,
    )
    if _area_sel:
        st.sidebar.markdown(
            f"<div class='breadcrumb-area'>"
            f"📍 <strong>{_area_sel.nome_area[:30]}</strong>"
            f"</div>",
            unsafe_allow_html=True,
        )

st.sidebar.markdown("---")

# Recarregar + última atualização (microcopy revisto — QW4)
col_rec, col_data = st.sidebar.columns([1, 1])
if col_rec.button("🔄 Atualizar", use_container_width=True,
                  help="Limpa o cache e recarrega os dados do disco."):
    st.cache_data.clear()
    st.rerun()
col_data.caption(f"Atualizado:\n{_dados_carregados['carregado_em']:%H:%M:%S}")

st.sidebar.markdown("---")
st.sidebar.caption(f"v MVP · {date.today():%d/%m/%Y}")


# ============================================================
# PAGINA 1: DASHBOARD
# ============================================================

def render_dashboard():
    header_pagina(
        "Dashboard",
        "Visão executiva das áreas prioritárias da Força Municipal",
    )

    dados = carregar_tudo(*resolver_periodo())
    areas = dados["areas"]
    bingos = dados["bingos"]

    if not areas:
        empty_state(
            "📍",
            "Nenhuma área cadastrada",
            "Cadastre a primeira área da Força Municipal para começar a "
            "visualizar dados, scores e relatórios.",
            cta_label="Cadastrar primeira área",
            cta_target_pagina="Editor de areas",
            key="empty_dash_areas",
        )
        return

    # ===== KPIs no topo =====
    n_alto = sum(1 for b in bingos if b.componentes.score_final > 0.6)
    col1, col2, col3, col4 = st.columns(4)
    col1.container(border=True).metric("Áreas ativas", len(areas))
    col2.container(border=True).metric(
        "Em alerta (score >0,60)", f"{n_alto}/{len(bingos)}",
    )
    col3.container(border=True).metric("Ocorrências", len(dados["ocorrencias"]))
    col4.container(border=True).metric(
        "RELINTs · Denúncias", f"{len(dados['relints'])} · {len(dados['denuncias'])}",
    )

    # ===== Tabs principais =====
    tab_mapa, tab_ranking = st.tabs(["🗺️  Mapa de risco", "🏆  Ranking de áreas"])

    # --------- TAB 1: MAPA ---------
    with tab_mapa:
        # Filtros colapsados (default fechado)
        with st.expander("⚙️ Filtros e camadas", expanded=False):
            f1, f2 = st.columns([3, 2])
            with f1:
                areas_filtradas = st.multiselect(
                    "Áreas visíveis",
                    [a.poligono_id for a in areas],
                    default=[a.poligono_id for a in areas],
                    format_func=lambda i: next(
                        a.nome_area for a in areas if a.poligono_id == i
                    ),
                )
            with f2:
                modo_viz = st.radio(
                    "Visualização das ocorrências",
                    ["🔥 Mapa de calor", "📍 Pins (cluster)"],
                    horizontal=False,
                )

            tipos_disponiveis = sorted({o.tipo for o in dados["ocorrencias"]})
            tipos_filtrados = st.multiselect(
                "Tipos de crime",
                tipos_disponiveis,
                default=tipos_disponiveis,
                format_func=lambda t: t.replace("_", " ").title(),
            )
            st.caption(
                "💡 No mapa, use o controle de camadas no canto superior direito "
                "para alternar Áreas / Ocorrências / Câmeras / Pontos de interceptação."
            )

        # Aplica filtros
        if "areas_filtradas" not in dir():
            areas_filtradas = [a.poligono_id for a in areas]
        if "tipos_filtrados" not in dir():
            tipos_filtrados = sorted({o.tipo for o in dados["ocorrencias"]})
        if "modo_viz" not in dir():
            modo_viz = "🔥 Mapa de calor"

        areas_render = [a for a in areas if a.poligono_id in areas_filtradas]
        bingos_render = [
            b for b in bingos if b.poligono_fm_id in areas_filtradas
        ]
        ocorrencias_render = [
            o for o in dados["ocorrencias"]
            if o.poligono_fm_id in areas_filtradas and o.tipo in tipos_filtrados
        ][:1000]

        # Legenda discreta acima do mapa
        st.markdown(
            "<div style='font-size:.82rem; color:#555; margin:.3rem 0'>"
            "<strong>Faixa de risco:</strong> &nbsp;"
            "<span class='legend-sq' style='background:#2E7D32'></span> Baixo &nbsp;·&nbsp;"
            "<span class='legend-sq' style='background:#EF6C00'></span> Médio &nbsp;·&nbsp;"
            "<span class='legend-sq' style='background:#C62828'></span> Alto"
            "</div>",
            unsafe_allow_html=True,
        )

        try:
            m = construir_mapa_folium(
                areas_render, bingos_render,
                ocorrencias=ocorrencias_render,
                modo_visualizacao="heatmap" if "calor" in modo_viz else "pins",
            )
            from heatmap import adicionar_cameras_ao_mapa, finalizar_mapa
            m = adicionar_cameras_ao_mapa(m)
            m = finalizar_mapa(m)  # 1 único LayerControl com TODOS os layers
            # Renderiza como HTML embutido — bypass do bug do streamlit-folium
            # em st.tabs que cortava a altura do iframe.
            from streamlit.components.v1 import html as components_html
            html_mapa = m.get_root().render()
            components_html(html_mapa, height=640, scrolling=False)
            st.caption(
                f"{len(areas_render)} áreas · {len(ocorrencias_render)} ocorrências no mapa"
            )
        except ImportError as e:
            st.warning(f"Falta dependência: {e}. Instale `streamlit-folium folium`.")

    # --------- TAB 2: RANKING ---------
    with tab_ranking:
        st.caption(
            "Áreas ordenadas por score consolidado. Clique em **Abrir QMD →** "
            "para ver o Quadro de Missão Diária da área."
        )

        for i, b in enumerate(bingos, 1):
            c = b.componentes
            cor_pos = "#C62828" if i == 1 else "#EF6C00" if i <= 3 else "#9E9E9E"
            with st.container(border=True):
                col_pos, col_info, col_acao = st.columns([1, 7, 2])
                col_pos.markdown(
                    f"<div style='font-size:2rem; font-weight:800; "
                    f"color:{cor_pos}; text-align:center; line-height:1'>{i}</div>"
                    f"<div style='font-size:.62rem; color:#888; text-align:center; "
                    f"text-transform:uppercase; letter-spacing:.06em; "
                    f"font-weight:600'>posição</div>",
                    unsafe_allow_html=True,
                )
                col_info.markdown(
                    f"**{b.nome_area}** &nbsp; {badge_score(c.score_final)}"
                    f" &nbsp; <span style='color:#666;font-size:.85rem'>"
                    f"{b.n_camadas_ativas}/4 camadas · bônus x{c.bonus_faccional:.2f}</span>",
                    unsafe_allow_html=True,
                )
                col_info.caption(b.justificativa[:200])
                if col_acao.button(
                    "Abrir QMD →",
                    key=f"goto_qmd_{b.poligono_fm_id}",
                    use_container_width=True,
                ):
                    navegar_para("Quadro de Missao Diaria", b.poligono_fm_id)


# ============================================================
# PAGINA 2: SCORE / BINGOS
# ============================================================

def render_scores():
    header_pagina(
        "Score / Bingos detalhados",
        "Cruzamento de 4 fontes com pesos diferenciados.",
    )

    st.markdown(
        "<div class='institucional'><strong>Lei dos pesos (score):</strong> "
        f"Mancha 0,40 &nbsp;·&nbsp; {termo('RELINT')} 0,30 (3× o peso do Disque) "
        "&nbsp;·&nbsp; Urbano 0,15 &nbsp;·&nbsp; Disque 0,10 "
        "&nbsp;·&nbsp; Modus+rotas 0,05 &nbsp;·&nbsp; Facção x1,0 a x1,5</div>",
        unsafe_allow_html=True,
    )

    dados = carregar_tudo(*resolver_periodo())
    bingos = dados["bingos"]

    if not bingos:
        empty_state(
            "📊", "Nenhuma área com score calculado",
            "Cadastre áreas e importe ocorrências para gerar scores.",
            cta_label="Cadastrar área", cta_target_pagina="Editor de areas",
            key="empty_scores",
        )
        return

    # Comparativo lado a lado (R2-2)
    secao("Comparativo lado a lado")
    tabela_comp = [
        {
            "Área": b.nome_area,
            "Score": b.componentes.score_final,
            "Mancha": b.componentes.score_mancha,
            "RELINT": b.componentes.score_relint,
            "Urbano": b.componentes.score_fator,
            "Disque": b.componentes.score_disque,
            "Modus": b.componentes.score_modus_rota,
            "Bônus": b.componentes.bonus_faccional,
            "Camadas": b.n_camadas_ativas,
        }
        for b in bingos
    ]
    st.dataframe(
        tabela_comp,
        hide_index=True, use_container_width=True,
        column_config={
            "Score":  st.column_config.ProgressColumn("Score",  min_value=0, max_value=1, format="%.2f"),
            "Mancha": st.column_config.ProgressColumn("Mancha", min_value=0, max_value=1, format="%.2f"),
            "RELINT": st.column_config.ProgressColumn("RELINT", min_value=0, max_value=1, format="%.2f"),
            "Urbano": st.column_config.ProgressColumn("Urbano", min_value=0, max_value=1, format="%.2f"),
            "Disque": st.column_config.ProgressColumn("Disque", min_value=0, max_value=1, format="%.2f"),
            "Modus":  st.column_config.ProgressColumn("Modus",  min_value=0, max_value=1, format="%.2f"),
            "Bônus":  st.column_config.NumberColumn(format="x%.2f"),
            "Camadas": st.column_config.NumberColumn(format="%d/4"),
        },
    )

    secao("Drill-down por área")
    # Filtro
    filtro = st.radio(
        "Filtrar",
        ["Todas", "Score alto (>0,60)", "Score medio (0,30-0,60)", "Com faccao"],
        horizontal=True,
        label_visibility="collapsed",
    )

    bingos_visiveis = bingos
    if filtro == "Score alto (>0,60)":
        bingos_visiveis = [b for b in bingos if b.componentes.score_final > 0.6]
    elif filtro == "Score medio (0,30-0,60)":
        bingos_visiveis = [
            b for b in bingos if 0.3 < b.componentes.score_final <= 0.6
        ]
    elif filtro == "Com faccao":
        bingos_visiveis = [b for b in bingos if b.faccoes_envolvidas]

    if not bingos_visiveis:
        st.info("Nenhuma area corresponde ao filtro escolhido.")
        return

    for i, b in enumerate(bingos_visiveis):
        c = b.componentes
        with st.expander(
            f"{emoji_score(c.score_final)} {b.nome_area} "
            f"— Score {c.score_final:.2f} · {b.n_camadas_ativas}/4 camadas",
            expanded=(i == 0),
        ):
            m1, m2, m3 = st.columns(3)
            m1.metric("Score final", f"{c.score_final:.2f}")
            m2.metric("Bonus faccional", f"x{c.bonus_faccional:.2f}")
            m3.metric("Camadas ativas", f"{b.n_camadas_ativas}/4")
            st.progress(min(c.score_final, 1.0))

            st.caption(b.justificativa)

            st.markdown("**Componentes do score**")
            comp_data = [
                {"Fonte": "Mancha criminal", "Score": c.score_mancha,
                 "Peso": c.peso_mancha, "Contrib": c.score_mancha * c.peso_mancha},
                {"Fonte": "RELINT (oficial)", "Score": c.score_relint,
                 "Peso": c.peso_relint, "Contrib": c.score_relint * c.peso_relint},
                {"Fonte": "Fator urbano", "Score": c.score_fator,
                 "Peso": c.peso_fator, "Contrib": c.score_fator * c.peso_fator},
                {"Fonte": "Disque (anonimo)", "Score": c.score_disque,
                 "Peso": c.peso_disque, "Contrib": c.score_disque * c.peso_disque},
                {"Fonte": "Modus + rotas", "Score": c.score_modus_rota,
                 "Peso": c.peso_modus, "Contrib": c.score_modus_rota * c.peso_modus},
            ]
            st.dataframe(
                comp_data,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Score": st.column_config.ProgressColumn(
                        "Score", min_value=0, max_value=1, format="%.2f",
                    ),
                    "Peso": st.column_config.NumberColumn("Peso", format="%.2f"),
                    "Contrib": st.column_config.ProgressColumn(
                        "Contribuicao", min_value=0, max_value=0.4, format="%.3f",
                    ),
                },
            )

            if c.bonus_faccional > 1.0:
                st.warning(
                    f"**Bonus faccional x{c.bonus_faccional:.2f}** — "
                    f"faccoes envolvidas: {', '.join(b.faccoes_envolvidas)}"
                )

            col_qmd, col_docx = st.columns(2)
            if col_qmd.button(
                "Abrir QMD →", key=f"score_qmd_{b.poligono_fm_id}",
                use_container_width=True,
            ):
                navegar_para("Quadro de Missao Diaria", b.poligono_fm_id)
            if col_docx.button(
                "Gerar DOCX →", key=f"score_docx_{b.poligono_fm_id}",
                use_container_width=True,
            ):
                navegar_para("Relatorios", b.poligono_fm_id)


# ============================================================
# PAGINA 3: EDITOR DE AREAS (CRUD)
# ============================================================

def _render_card_area(area: AreaPoligonoFM) -> None:
    """Renderiza area como grid 2 colunas, sem JSON cru."""
    c1, c2 = st.columns(2)
    c1.markdown(
        f"**AISP:** {area.aisp}  \n"
        f"**Base FM:** {area.base_fm}  \n"
        f"**Subprefeitura:** {area.subprefeitura}"
    )
    c2.markdown(
        f"**DP:** {area.dp or '—'}  \n"
        f"**BPM:** {area.bpm or '—'}  \n"
        f"**Bairros:** {', '.join(area.bairros)}"
    )
    if area.observacoes:
        st.caption(area.observacoes)


def _render_excluir(store: AreasFMStore, areas: list) -> None:
    """Excluir com confirmacao por digitacao."""
    st.warning(
        "**Exclusao PERMANENTE.** Para retirar de circulacao mantendo "
        "historico, use **Desativar** na aba Listar.",
        icon="⚠️",
    )

    pid_excluir = st.selectbox(
        "Area a EXCLUIR",
        [a.poligono_id for a in areas],
        format_func=lambda i: next(
            a.nome_area for a in areas if a.poligono_id == i
        ),
        key="excluir_select",
    )
    area_alvo = next(a for a in areas if a.poligono_id == pid_excluir)

    st.markdown(
        f"Digite o nome exato da area para liberar a exclusao: "
        f"**`{area_alvo.nome_area}`**"
    )
    confirmacao_texto = st.text_input(
        "Nome da area", key="confirma_excluir_input",
        placeholder=area_alvo.nome_area,
    )
    pode_excluir = confirmacao_texto.strip() == area_alvo.nome_area

    if st.button(
        "EXCLUIR PERMANENTEMENTE",
        type="primary", disabled=not pode_excluir,
    ):
        try:
            store.excluir(pid_excluir, confirmar=True)
            st.cache_data.clear()
            st.toast(f"Area {area_alvo.nome_area} excluida.", icon="🗑️")
            st.rerun()
        except Exception as e:
            st.error(f"Erro: {e}")


def render_editor():
    header_pagina(
        "Editor de áreas",
        "Cadastre, edite ou desative áreas. Exclusão permanente disponível.",
        com_periodo=False,
    )
    store = AreasFMStore(DATA_DIR / "areas.json")

    aba_listar, aba_criar, aba_editar, aba_excluir = st.tabs([
        "Listar", "Criar nova", "Editar", "Excluir",
    ])

    with aba_listar:
        areas = store.listar(incluir_inativos=True)
        if not areas:
            st.info("Nenhuma area cadastrada. Use **Criar nova**.")
        for area in areas:
            icone = "✅" if area.ativo else "⏸️"
            with st.expander(f"{icone} {area.nome_area} ({area.poligono_id})"):
                _render_card_area(area)
                st.divider()
                col1, col2 = st.columns(2)
                if area.ativo:
                    if col1.button(
                        "Desativar (preserva historico)",
                        key=f"des_{area.poligono_id}",
                        use_container_width=True,
                    ):
                        store.desativar(area.poligono_id, "Desativada via UI")
                        st.cache_data.clear()
                        st.toast(f"{area.nome_area} desativada.", icon="⏸️")
                        st.rerun()
                else:
                    if col1.button(
                        "Reativar",
                        key=f"reat_{area.poligono_id}",
                        use_container_width=True,
                    ):
                        store.reativar(area.poligono_id)
                        st.cache_data.clear()
                        st.toast(f"{area.nome_area} reativada.", icon="✅")
                        st.rerun()
                if col2.button(
                    "Abrir QMD →", key=f"edit_qmd_{area.poligono_id}",
                    use_container_width=True,
                ):
                    navegar_para("Quadro de Missao Diaria", area.poligono_id)

    with aba_criar:
        st.caption("Adicionar nova area prioritaria.")

        with st.expander("🖊️ Desenhar área no mapa (recomendado)", expanded=True):
            st.caption(
                "Use as ferramentas no canto superior esquerdo do mapa para "
                "desenhar um polígono ou retângulo. Você pode editar e "
                "remover o desenho. O WKT é capturado automaticamente."
            )
            wkt_desenhado = render_editor_poligono(
                state_key="wkt_form_criar",
                wkt_existente=None,
                map_key="map_criar",
            )

        with st.expander("ℹ️ O que é WKT? (formato manual)"):
            st.markdown(
                "WKT (Well-Known Text) e o formato padrao OGC para geometria. "
                "Exemplo de polígono fechado (precisa fechar repetindo o "
                "primeiro ponto):"
            )
            st.code(
                "POLYGON((-43.475 -22.880, -43.470 -22.880, "
                "-43.470 -22.875, -43.475 -22.875, -43.475 -22.880))",
                language="text",
            )
            st.caption(
                "Pode extrair de QGIS, geojson.io ou de um GeoJSON existente."
            )

        with st.form("form_criar"):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome da area*")
            aisp = c2.text_input("AISP*", placeholder="ex: AISP 9")
            base = c1.text_input("Base FM*", placeholder="ex: Base Bangu")
            subpref = c2.text_input("Subprefeitura*", placeholder="ex: Zona Oeste")
            dp = c1.text_input("DP")
            bpm = c2.text_input("BPM")
            bairros = st.text_input(
                "Bairros (separados por virgula)*", placeholder="Bangu, Realengo",
            )
            wkt_default = st.session_state.get("wkt_form_criar") or (
                "POLYGON((-43.475 -22.880, -43.470 -22.880, "
                "-43.470 -22.875, -43.475 -22.875, -43.475 -22.880))"
            )
            wkt = st.text_area(
                "Geometria (WKT)*",
                value=wkt_default,
                height=80,
                help="Preenchido automaticamente se você desenhou no mapa acima.",
            )
            efetivo_padrao = st.number_input(
                "Efetivo padrão da FM (nº de agentes)",
                min_value=0, max_value=500, value=25, step=1,
                help="Quantitativo de agentes alocado por padrão. Usado como ponto de partida no QMD e no DOCX.",
            )
            obs = st.text_area("Observacoes")

            if st.form_submit_button("✅ Cadastrar área", type="primary"):
                if not all([nome, aisp, bairros, base, subpref, wkt]):
                    st.error("Preencha todos os campos obrigatorios (*)")
                else:
                    try:
                        area = AreaPoligonoFM(
                            nome_area=nome,
                            aisp=aisp,
                            bairros=[b.strip() for b in bairros.split(",")],
                            base_fm=base,
                            subprefeitura=subpref,
                            dp=dp or None,
                            bpm=bpm or None,
                            geometria_wkt=wkt,
                            efetivo_padrao=int(efetivo_padrao),
                            observacoes=obs or None,
                        )
                        novo_id = store.criar(area)
                        st.cache_data.clear()
                        st.toast(f"Area criada: {novo_id}", icon="✅")
                    except Exception as e:
                        st.error(f"Erro: {e}")

    with aba_editar:
        st.caption("Editar campos de uma area existente.")
        areas_ativas = store.listar()
        if not areas_ativas:
            st.info("Nenhuma area ativa.")
        else:
            pid = st.selectbox(
                "Selecionar area",
                [a.poligono_id for a in areas_ativas],
                format_func=lambda i: next(
                    a.nome_area for a in areas_ativas if a.poligono_id == i
                ),
            )
            area_atual = store.obter(pid)

            with st.expander(
                "🖊️ Redesenhar polígono no mapa (opcional)", expanded=False,
            ):
                st.caption(
                    "O polígono atual aparece em **azul**. Desenhe um novo "
                    "(vermelho) para substituí-lo."
                )
                wkt_redesenhado = render_editor_poligono(
                    state_key=f"wkt_form_editar_{pid}",
                    wkt_existente=area_atual.geometria_wkt,
                    map_key=f"map_editar_{pid}",
                )

            with st.form("form_editar"):
                c1, c2 = st.columns(2)
                novo_nome = c1.text_input("Nome", value=area_atual.nome_area)
                novos_bairros = c2.text_input(
                    "Bairros", value=", ".join(area_atual.bairros),
                )
                novo_efetivo = c1.number_input(
                    "Efetivo padrão da FM",
                    min_value=0, max_value=500,
                    value=int(area_atual.efetivo_padrao), step=1,
                    help="Default usado no QMD e DOCX.",
                )
                wkt_default_edit = (
                    st.session_state.get(f"wkt_form_editar_{pid}")
                    or area_atual.geometria_wkt
                )
                nova_wkt = st.text_area(
                    "Geometria WKT", value=wkt_default_edit, height=80,
                    help="Preenchido automaticamente se você redesenhou no mapa acima.",
                )
                nova_obs = st.text_area(
                    "Observacoes", value=area_atual.observacoes or "",
                )
                if st.form_submit_button("💾 Salvar alterações", type="primary"):
                    try:
                        store.atualizar(
                            poligono_id=pid,
                            nome_area=novo_nome,
                            bairros=[b.strip() for b in novos_bairros.split(",")],
                            geometria_wkt=nova_wkt,
                            efetivo_padrao=int(novo_efetivo),
                            observacoes=nova_obs or None,
                        )
                        st.cache_data.clear()
                        st.toast("Atualizada.", icon="✅")
                    except Exception as e:
                        st.error(f"Erro: {e}")

    with aba_excluir:
        areas = store.listar(incluir_inativos=True)
        if not areas:
            st.info("Nenhuma area cadastrada.")
        else:
            _render_excluir(store, areas)


# ============================================================
# PAGINA 3.5: IMPORTAR DADOS
# ============================================================

def render_importar():
    header_pagina(
        "Importar dados",
        "Adicione novos documentos vinculados a uma área pré-existente.",
        com_periodo=False,
    )
    st.markdown(
        f"Aceita: {termo('RELINT')} · ocorrências · denúncias · fatores urbanos. "
        f"Formatos: JSON, CSV, PDF, DOC, DOCX, TXT.",
        unsafe_allow_html=True,
    )

    store = AreasFMStore(DATA_DIR / "areas.json")
    areas = store.listar()

    if not areas:
        st.warning(
            "Crie pelo menos uma área no **Editor de areas** antes de importar dados.",
            icon="⚠️",
        )
        return

    # ---- seleção obrigatória de área ----
    with st.container(border=True):
        st.markdown("### 1. Selecione a área")
        pid = st.selectbox(
            "Área pré-existente *",
            [a.poligono_id for a in areas],
            format_func=lambda i: f"{next(a.nome_area for a in areas if a.poligono_id == i)} ({i})",
            key="import_area_select",
        )

    # ---- tipo de documento ----
    with st.container(border=True):
        st.markdown("### 2. Tipo de documento")
        tipo = st.radio(
            "Tipo",
            list(TIPOS_DOCUMENTO.keys()),
            format_func=lambda k: TIPOS_DOCUMENTO[k]["rotulo"],
            horizontal=True,
            label_visibility="collapsed",
        )
        cfg = TIPOS_DOCUMENTO[tipo]
        st.caption(
            f"Schema: **{cfg['schema'].__name__}** · "
            f"Formatos aceitos: **{', '.join(cfg['formatos'])}**"
        )

    # ---- upload único (detecção automática pela extensão) ----
    from importador import EXTENSOES_ACEITAS, detectar_formato

    arquivo_up = st.file_uploader(
        "📎 Arraste e solte o arquivo aqui ou clique para selecionar",
        type=EXTENSOES_ACEITAS,
        key=f"upload_{tipo}",
        help=(
            f"Formatos suportados: {', '.join(e.upper() for e in EXTENSOES_ACEITAS)}. "
            f"Para {cfg['rotulo']}, formatos válidos: {', '.join(cfg['formatos'])}."
        ),
    )

    # ---- preview + salvar ----
    if arquivo_up:
        conteudo = arquivo_up.read()
        try:
            formato = detectar_formato(arquivo_up.name)
        except ValueError as e:
            st.error(f"Erro: {e}")
            return

        with st.container(border=True):
            st.markdown(
                f"### 📋 Validação · arquivo `{arquivo_up.name}` "
                f"<span style='font-size:.75rem;color:#666'>(formato {formato})</span>",
                unsafe_allow_html=True,
            )
            try:
                resultado = importar(tipo, pid, formato, conteudo)
            except Exception as e:
                st.error(f"Erro ao processar: {e}")
                return

            c1, c2 = st.columns(2)
            c1.metric("Registros válidos", resultado.n_novos)
            c2.metric("Erros", resultado.n_erros, delta_color="inverse")

            if resultado.erros:
                with st.expander(f"⚠️ {len(resultado.erros)} erro(s) de validação"):
                    for e in resultado.erros:
                        st.code(e, language="text")

            if resultado.preview:
                with st.expander("Preview dos primeiros 5 registros válidos", expanded=True):
                    st.json(resultado.preview)

            if resultado.n_novos > 0:
                if st.button(
                    f"💾 Salvar {resultado.n_novos} registro(s) em "
                    f"data/{TIPOS_DOCUMENTO[tipo]['arquivo']}",
                    type="primary",
                ):
                    try:
                        path_salvo = salvar(resultado, DATA_DIR)
                        st.cache_data.clear()
                        st.toast(
                            f"Importação concluída: {resultado.n_novos} "
                            f"registros adicionados.",
                            icon="✅",
                        )
                        st.success(f"Salvo em: `{path_salvo}`")
                    except Exception as e:
                        st.error(f"Falha ao salvar: {e}")
            else:
                st.error(
                    "Nenhum registro válido. Corrija os erros acima e tente novamente."
                )


# ============================================================
# PAGINA 4: QMD
# ============================================================

def render_qmd():
    header_pagina(
        "Quadro de Missão Diária (QMD)",
        "Ordem de serviço entregue à base da Força Municipal.",
    )
    st.caption(
        "Gerado a partir do score, modus operandi e rotas de fuga "
        "identificadas no RELINT."
    )

    dados = carregar_tudo(*resolver_periodo())
    areas = dados["areas"]
    bingos = dados["bingos"]
    relints = dados["relints"]
    ocorrencias = dados["ocorrencias"]

    if not areas:
        st.info("Nenhuma area cadastrada.")
        return

    pid_default = area_default(areas)
    pid = st.selectbox(
        "Selecionar area",
        [a.poligono_id for a in areas],
        index=[a.poligono_id for a in areas].index(pid_default),
        format_func=lambda i: next(
            a.nome_area for a in areas if a.poligono_id == i
        ),
        key="qmd_select",
    )
    st.session_state["area_selecionada"] = pid

    area = get_area(areas, pid)
    bingo = get_bingo(bingos, pid)
    if not area or not bingo:
        st.error("Area sem dados de score calculados.")
        return

    relints_area = [r for r in relints if r.poligono_fm_id == pid]
    oco_area = [o for o in ocorrencias if o.poligono_fm_id == pid]

    if not relints_area:
        st.warning(
            "Sem RELINT vinculado a esta area. QMD sera gerado apenas com "
            "mancha + fator + disque.",
            icon="⚠️",
        )

    # ----- Sugestão inteligente de efetivo -----
    fatores_area = [f for f in dados["fatores"] if f.poligono_fm_id == pid]
    sugestao = sugerir_efetivo(area, bingo, oco_area, relints_area, fatores_area)

    with st.container(border=True):
        cs1, cs2, cs3 = st.columns([2, 1, 1])
        cs1.markdown(
            f"#### 🤖 Sugestão de efetivo<br>"
            f"<span style='font-size:.85rem;color:#666'>"
            f"Cálculo determinístico a partir dos dados da área e do período.</span>",
            unsafe_allow_html=True,
        )
        cs2.metric("Sugerido", f"{sugestao.efetivo_sugerido}")
        if cs3.button(
            "Aplicar sugestão", key=f"apply_sugestao_{pid}",
            use_container_width=True, type="primary",
        ):
            st.session_state[f"qmd_efetivo_{pid}"] = sugestao.efetivo_sugerido
            st.rerun()

        with st.expander("Como chegamos nesse número"):
            st.markdown(sugestao.to_markdown())
            if st.button(
                "🧠 Explicar com IA (Claude)", key=f"llm_explain_{pid}",
            ):
                st.session_state[f"_explain_request_{pid}"] = True

        if st.session_state.get(f"_explain_request_{pid}"):
            with st.spinner("Consultando Claude..."):
                try:
                    from explicacao_llm import explicar_sugestao_efetivo
                    texto = explicar_sugestao_efetivo(
                        area, bingo, sugestao,
                        n_ocorrencias=len(oco_area),
                        relints=relints_area,
                    )
                    st.info(texto, icon="🧠")
                except RuntimeError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Falha ao consultar Claude: {e}")
            st.session_state[f"_explain_request_{pid}"] = False

    # Slider de efetivo: usa efetivo_padrao da área como ponto de partida.
    efetivo_max = max(80, area.efetivo_padrao * 2)
    key_slider = f"qmd_efetivo_{pid}"

    def _render_slider_efetivo() -> int:
        col_s, col_b = st.columns([3, 1])
        valor = col_s.slider(
            "Efetivo alocado",
            min_value=5, max_value=efetivo_max,
            value=int(area.efetivo_padrao),
            key=key_slider,
            help=f"Padrão atual da área: {area.efetivo_padrao} agentes.",
        )
        if col_b.button(
            "💾 Salvar como padrão", key=f"save_padrao_{pid}",
            use_container_width=True,
            disabled=(valor == area.efetivo_padrao),
        ):
            store = AreasFMStore(DATA_DIR / "areas.json")
            store.atualizar(poligono_id=pid, efetivo_padrao=int(valor))
            st.cache_data.clear()
            st.toast(f"Padrão de {area.nome_area} agora é {valor}.", icon="💾")
            st.rerun()
        return valor

    if hasattr(st, "popover"):
        with st.popover(f"⚙️ Efetivo: {area.efetivo_padrao} (padrão)"):
            efetivo = _render_slider_efetivo()
    else:
        efetivo = _render_slider_efetivo()

    recomendacao = sugerir_modalidade(bingo, relints_area, oco_area, efetivo)
    qmd = gerar_qmd(
        area=area,
        bingo=bingo,
        recomendacao=recomendacao,
        relints_area=relints_area,
        acoes_pendentes_outros_orgaos=[],
        data_ref=date.today(),
    )

    # Cabecalho institucional
    with st.container(border=True):
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.markdown(
            f"### {area.nome_area}<br>"
            f"<span style='font-size:.85rem;color:#666'>"
            f"{area.aisp} · {area.base_fm} · {area.subprefeitura}</span>",
            unsafe_allow_html=True,
        )
        c2.metric("Score", f"{bingo.componentes.score_final:.2f}")
        c3.metric("Efetivo", efetivo)

    md = qmd_para_markdown(qmd)
    st.markdown(md)

    col_md, col_docx = st.columns(2)
    col_md.download_button(
        "Baixar QMD (markdown)",
        data=md,
        file_name=(
            f"QMD_{area.nome_area.replace(' ', '_')}_"
            f"{qmd.data_referencia.isoformat()}.md"
        ),
        mime="text/markdown",
        use_container_width=True,
    )
    if col_docx.button(
        "Gerar DOCX desta area →", type="primary", use_container_width=True,
    ):
        navegar_para("Relatorios", pid)


# ============================================================
# PAGINA 5: EVOLUCAO 90D
# ============================================================

def render_evolucao():
    header_pagina(
        "Evolução após atuação da FM (90 dias)",
        "Comparativo antes/depois de roubos, furtos e score consolidado.",
        com_periodo=False,
    )

    # Aviso explícito sobre origem dos dados (R2-3)
    st.warning(
        "**Dados de antes/depois ainda simulados** para validação metodológica. "
        "Substituir por leitura do DW operacional antes de uso em reunião CompStat.",
        icon="🧪",
    )

    snapshots = carregar_snapshots()
    if not snapshots:
        empty_state(
            "📈", "Sem snapshots históricos",
            "Importe snapshots antes/depois para visualizar a evolução das áreas.",
            cta_label="Importar dados", cta_target_pagina="Importar dados",
            key="empty_evo",
        )
        return

    dados = carregar_tudo(*resolver_periodo())
    nome_por_area = {a.poligono_id: a.nome_area for a in dados["areas"]}
    comparativos = comparar_todas_areas(snapshots, nome_por_area)

    if not comparativos:
        st.info("Snapshots insuficientes para comparação (precisa de antes + depois).")
        return

    # Ordenar por queda de roubos (maior queda primeiro)
    comparativos = sorted(comparativos, key=lambda c: c.variacao_roubos_pct)

    # Periodo comparado (pega o primeiro como referencia)
    s_antes = comparativos[0].snapshot_antes
    s_depois = comparativos[0].snapshot_depois
    st.caption(
        f"**Periodo:** antes {s_antes.data_referencia:%d/%m/%Y} → "
        f"depois {s_depois.data_referencia:%d/%m/%Y}"
    )

    # ----- KPIs consolidados -----
    queda_media = mean(c.variacao_roubos_pct for c in comparativos)
    n_melhora = sum(1 for c in comparativos if c.variacao_roubos_pct < -10)
    n_alerta = sum(1 for c in comparativos if c.variacao_roubos_pct > 10)

    k1, k2, k3 = st.columns(3)
    k1.container(border=True).metric(
        "Queda media de roubos", f"{queda_media:+.1f}%",
        delta_color="inverse" if queda_media != 0 else "off",
    )
    k2.container(border=True).metric(
        "Areas em melhora", f"{n_melhora}/{len(comparativos)}",
    )
    k3.container(border=True).metric(
        "Areas em alerta", f"{n_alerta}/{len(comparativos)}",
    )

    # Destaque maior queda
    melhor = comparativos[0]
    if melhor.variacao_roubos_pct < 0:
        st.success(
            f"🏆 **Maior queda:** {melhor.nome_area} com "
            f"{melhor.variacao_roubos_pct:+.1f}% em roubos."
        )

    secao("Detalhamento por área")
    tab_cards, tab_tabela = st.tabs(["📋 Cards detalhados", "📊 Tabela comparativa"])

    with tab_cards:
        for c in comparativos:
            classif = c.classificacao.replace("_", " ")
            if "melhora" in c.classificacao:
                cls = "evo-card-melhora"
            elif "piora" in c.classificacao:
                cls = "evo-card-piora"
            else:
                cls = "evo-card-estavel"
            with st.container():
                st.markdown(
                    f"<div class='evo-card {cls}'>"
                    f"<strong>{c.nome_area}</strong> &nbsp; "
                    f"<span style='font-size:.8rem; color:#666'>{classif}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                m1, m2, m3 = st.columns(3)
                m1.metric(
                    "Roubos", c.snapshot_depois.total_roubos,
                    f"{c.variacao_roubos_pct:+.1f}%", delta_color="inverse",
                )
                m2.metric(
                    "Furtos", c.snapshot_depois.total_furtos,
                    f"{c.variacao_furtos_pct:+.1f}%", delta_color="inverse",
                )
                m3.metric(
                    "Score", f"{c.snapshot_depois.score_medio:.2f}",
                    f"{c.variacao_score_pct:+.1f}%", delta_color="inverse",
                )
                st.caption(c.observacao)

    with tab_tabela:
        df_evo = [{
            "Área": c.nome_area,
            "Classificação": c.classificacao.replace("_", " "),
            "Roubos (depois)": c.snapshot_depois.total_roubos,
            "Δ Roubos": c.variacao_roubos_pct,
            "Furtos (depois)": c.snapshot_depois.total_furtos,
            "Δ Furtos": c.variacao_furtos_pct,
            "Score (depois)": c.snapshot_depois.score_medio,
            "Δ Score": c.variacao_score_pct,
        } for c in comparativos]
        st.dataframe(
            df_evo, hide_index=True, use_container_width=True,
            column_config={
                "Δ Roubos": st.column_config.NumberColumn(format="%+.1f%%"),
                "Δ Furtos": st.column_config.NumberColumn(format="%+.1f%%"),
                "Δ Score":  st.column_config.NumberColumn(format="%+.1f%%"),
                "Score (depois)": st.column_config.NumberColumn(format="%.2f"),
            },
        )

    secao("Variação consolidada (gráfico)")
    try:
        png = gerar_grafico_evolucao(comparativos)
        st.image(png, use_container_width=True)
    except Exception as e:
        st.error(f"Erro ao gerar gráfico: {e}")


# ============================================================
# PAGINA 6: GERAR DOCX
# ============================================================

def render_relatorios():
    header_pagina(
        "Relatórios",
        "Geração no formato oficial CompStat Municipal — por área ou consolidado.",
    )

    aba_area, aba_geral = st.tabs([
        "📄 Relatório por área",
        "📚 Relatório consolidado (todas as áreas)",
    ])

    with aba_area:
        _render_relatorio_por_area()
    with aba_geral:
        _render_relatorio_consolidado()


def _render_relatorio_por_area():
    """Aba 1: relatório individual de uma área."""
    with st.expander("O que vai no relatório?", expanded=False):
        st.markdown(
            "- **Capa institucional** com período de análise e total de roubos  \n"
            "- **Resumo Executivo** com Score + tabela 4×4 de perguntas norteadoras  \n"
            "- **1. Ocorrências criminais** (identificação, indicadores, top tipos, análise temporal)  \n"
            "- **2. Dinâmica criminal** sintetizada do RELINT e Disque  \n"
            "- **3. Efetivo empregado FM** (tabela 5×4 — efetivo padrão da área usado)  \n"
            "- **4. Fatores de incidência criminal** por órgão  \n"
            "- **5. Plano de ação e responsabilização** pré-populado pela IA"
        )

    dados = carregar_tudo(*resolver_periodo())
    areas = dados["areas"]
    bingos = dados["bingos"]
    relints = dados["relints"]
    ocorrencias = dados["ocorrencias"]
    snapshots = carregar_snapshots()

    if not areas:
        st.info("Nenhuma area cadastrada.")
        return

    pid_default = area_default(areas)
    pid = st.selectbox(
        "Area",
        [a.poligono_id for a in areas],
        index=[a.poligono_id for a in areas].index(pid_default),
        format_func=lambda i: next(
            a.nome_area for a in areas if a.poligono_id == i
        ),
        key="docx_select",
    )
    st.session_state["area_selecionada"] = pid

    area_sel = get_area(areas, pid)
    if not area_sel:
        st.error("Area não encontrada.")
        return

    # Cabeçalho institucional da área selecionada (somente leitura)
    bingo_sel = get_bingo(bingos, pid)
    with st.container(border=True):
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.markdown(
            f"### {area_sel.nome_area}<br>"
            f"<span style='font-size:.85rem;color:#666'>"
            f"{area_sel.aisp} · {area_sel.base_fm} · {area_sel.subprefeitura}</span>",
            unsafe_allow_html=True,
        )
        if bingo_sel:
            c2.metric("Score", f"{bingo_sel.componentes.score_final:.2f}")
        c3.metric("Efetivo no período", area_sel.efetivo_padrao)

    st.caption(
        f"📅 Período de análise: {label_periodo()}. "
        f"Para alterar, use o seletor na barra lateral."
    )

    # Efetivo usado é o `efetivo_padrao` da área (sem slider)
    efetivo = area_sel.efetivo_padrao

    if st.button("📄 Gerar relatório da área", type="primary"):
        with st.status("Gerando relatorio...", expanded=True) as status:
            try:
                area = get_area(areas, pid)
                bingo = get_bingo(bingos, pid)
                relints_area = [r for r in relints if r.poligono_fm_id == pid]
                oco_area = [o for o in ocorrencias if o.poligono_fm_id == pid]
                denuncias_area = [
                    d for d in dados["denuncias"] if d.poligono_fm_id == pid
                ]
                fatores_area = [
                    f for f in dados["fatores"] if f.poligono_fm_id == pid
                ]

                st.write("✓ Calculando recomendacao de patrulhamento")
                recomendacao = sugerir_modalidade(
                    bingo, relints_area, oco_area, efetivo,
                )

                st.write("✓ Sugerindo efetivo pela IA (heurística)")
                sug = sugerir_efetivo(
                    area, bingo, oco_area, relints_area, fatores_area,
                )

                st.write("✓ Montando QMD")
                qmd = gerar_qmd(
                    area, bingo, recomendacao, relints_area, [], date.today()
                )

                st.write("✓ Renderizando heatmap temporal")
                heatmap_png = gerar_heatmap_temporal(oco_area)

                st.write("✓ Calculando comparativo 90 dias")
                snaps_area = [s for s in snapshots if s.poligono_fm_id == pid]
                comparativo = None
                grafico_png = None
                if len(snaps_area) >= 2:
                    snaps_ord = sorted(snaps_area, key=lambda s: s.data_referencia)
                    from evolution import comparar_evolucao
                    comparativo = comparar_evolucao(
                        pid, area.nome_area,
                        snaps_ord[0], snaps_ord[-1],
                    )
                    grafico_png = gerar_grafico_evolucao([comparativo])

                st.write("✓ Renderizando DOCX (formato oficial CompStat)")
                nome_arq = (
                    OUTPUT_DIR / f"relatorio_{pid}_{date.today():%Y%m%d}.docx"
                )
                periodo_ini, periodo_f = resolver_periodo()
                gerar_relatorio_docx(
                    area=area,
                    bingo=bingo,
                    recomendacao=recomendacao,
                    qmd=qmd,
                    ocorrencias_area=oco_area,
                    relints_area=relints_area,
                    denuncias_area=denuncias_area,
                    fatores_area=fatores_area,
                    bingos_todos=bingos,
                    comparativo_evolucao=comparativo,
                    heatmap_temporal_png=heatmap_png,
                    grafico_evolucao_png=grafico_png,
                    efetivo_sugerido=sug.efetivo_sugerido,
                    periodo_inicio=periodo_ini,
                    periodo_fim=periodo_f,
                    output_path=str(nome_arq),
                )

                status.update(
                    label=f"Relatorio gerado ({nome_arq.stat().st_size // 1024} KB)",
                    state="complete", expanded=False,
                )

                with open(nome_arq, "rb") as f:
                    st.download_button(
                        "📄 Baixar DOCX",
                        data=f.read(),
                        file_name=nome_arq.name,
                        mime=(
                            "application/vnd.openxmlformats-officedocument."
                            "wordprocessingml.document"
                        ),
                        type="primary",
                    )
                st.toast("Relatorio pronto.", icon="📄")
            except Exception:
                status.update(label="Falha na geracao", state="error")
                st.error(
                    "Nao foi possivel gerar o relatorio. Acione a equipe de TI."
                )
                # Loga traceback no stderr (visivel apenas no servidor)
                print(traceback.format_exc(), file=sys.stderr)


def _render_relatorio_consolidado():
    """Aba 2: relatório consolidado com todas as áreas ativas."""
    st.markdown(
        "Relatório único cobrindo **todas as áreas ativas** da Força Municipal. "
        "Inclui ranking, indicadores agregados e ficha resumida por área."
    )

    with st.expander("O que vai no relatório consolidado?", expanded=False):
        st.markdown(
            "- **Capa consolidada** com totais gerais  \n"
            "- **Ranking** das áreas por score de risco  \n"
            "- **Indicadores agregados**: roubos, furtos, RELINTs, fatores  \n"
            "- **Ficha resumida de cada área** (identificação + score + top 3 fatores)  \n"
            "- **Plano de ação consolidado** agrupado por órgão responsável  \n"
            "- **Comparativo de evolução 90 dias** com gráfico"
        )

    dados = carregar_tudo(*resolver_periodo())
    areas = dados["areas"]
    bingos = dados["bingos"]

    if not areas:
        st.info("Nenhuma área cadastrada.")
        return

    # Resumo rápido na UI antes de gerar
    st.caption(f"📅 Período: {label_periodo()}")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Áreas", len(areas))
    k2.metric("Ocorrências", len(dados["ocorrencias"]))
    k3.metric("RELINTs", len(dados["relints"]))
    k4.metric("Fatores", len(dados["fatores"]))

    if st.button(
        "📚 Gerar relatório consolidado de todas as áreas", type="primary",
    ):
        from docx_generator import gerar_relatorio_geral_docx
        snapshots = carregar_snapshots()
        nome_por = {a.poligono_id: a.nome_area for a in areas}
        comparativos = comparar_todas_areas(snapshots, nome_por)
        periodo_ini, periodo_f = resolver_periodo()

        with st.status("Gerando relatório consolidado...", expanded=True) as status:
            try:
                st.write("✓ Coletando dados de todas as áreas")
                # Agrupa dados por área
                por_area = {}
                for a in areas:
                    pid = a.poligono_id
                    por_area[pid] = {
                        "area": a,
                        "bingo": get_bingo(bingos, pid),
                        "ocorrencias": [o for o in dados["ocorrencias"] if o.poligono_fm_id == pid],
                        "relints": [r for r in dados["relints"] if r.poligono_fm_id == pid],
                        "denuncias": [d for d in dados["denuncias"] if d.poligono_fm_id == pid],
                        "fatores": [f for f in dados["fatores"] if f.poligono_fm_id == pid],
                    }

                st.write("✓ Calculando sugestões de efetivo para todas as áreas")
                for pid, d in por_area.items():
                    if d["bingo"]:
                        d["sugestao"] = sugerir_efetivo(
                            d["area"], d["bingo"], d["ocorrencias"],
                            d["relints"], d["fatores"],
                        )

                st.write("✓ Compondo gráfico consolidado")
                grafico_png = None
                if comparativos:
                    grafico_png = gerar_grafico_evolucao(comparativos)

                st.write("✓ Renderizando DOCX consolidado")
                nome_arq = (
                    OUTPUT_DIR /
                    f"relatorio_consolidado_{date.today():%Y%m%d}.docx"
                )
                gerar_relatorio_geral_docx(
                    por_area=por_area,
                    bingos_ranking=bingos,
                    comparativos=comparativos,
                    grafico_evolucao_png=grafico_png,
                    periodo_inicio=periodo_ini,
                    periodo_fim=periodo_f,
                    output_path=str(nome_arq),
                )

                status.update(
                    label=f"Consolidado gerado ({nome_arq.stat().st_size // 1024} KB)",
                    state="complete", expanded=False,
                )

                with open(nome_arq, "rb") as f:
                    st.download_button(
                        "📚 Baixar Relatório Consolidado",
                        data=f.read(),
                        file_name=nome_arq.name,
                        mime=(
                            "application/vnd.openxmlformats-officedocument."
                            "wordprocessingml.document"
                        ),
                        type="primary",
                    )
                st.toast("Consolidado pronto.", icon="📚")
            except Exception:
                status.update(label="Falha na geração", state="error")
                st.error("Não foi possível gerar o relatório consolidado.")
                print(traceback.format_exc(), file=sys.stderr)


# ============================================================
# ROUTER
# ============================================================

PAGINA_RENDERS = {
    "Dashboard": render_dashboard,
    "Score / Bingos": render_scores,
    "Editor de areas": render_editor,
    "Importar dados": render_importar,
    "Quadro de Missao Diaria": render_qmd,
    "Evolucao 90 dias": render_evolucao,
    "Relatorios": render_relatorios,
}

PAGINA_RENDERS[st.session_state["pagina"]]()

# Footer institucional (QW6)
render_footer_institucional()
