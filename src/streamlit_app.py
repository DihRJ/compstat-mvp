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

import json
import sys
from pathlib import Path
from datetime import date

import streamlit as st

# Permite rodar via `streamlit run src/streamlit_app.py`
sys.path.insert(0, str(Path(__file__).parent))

# Paths absolutos (funciona em Streamlit Cloud, Docker, scripts)
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

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


# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="CompStat IA",
    page_icon="🛡",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stat-card {
        background-color: #F4F4F2;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        border-left: 4px solid #1E2761;
    }
    .stat-num {
        font-size: 32px;
        font-weight: 700;
        color: #1E2761;
    }
    .score-alto { color: #C62828; font-weight: bold; }
    .score-medio { color: #EF6C00; font-weight: bold; }
    .score-baixo { color: #2E7D32; font-weight: bold; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATA LOADING (cached)
# ============================================================

@st.cache_data(ttl=5)
def carregar_tudo():
    """Carrega todos os dados base + calcula bingos."""
    store = AreasFMStore(DATA_DIR / "areas.json")
    areas = store.listar()

    def _read(path, model):
        p = DATA_DIR / path
        if not p.exists():
            return []
        return [model(**d) for d in json.loads(p.read_text(encoding="utf-8"))]

    ocorrencias = _read("ocorrencias.json", Ocorrencia)
    relints = _read("relints.json", RelintEstruturado)
    denuncias = _read("denuncias.json", DenunciaDisque)
    fatores = _read("fatores_urbanos.json", FatorUrbano)

    bingos = calcular_bingos_todas_areas(areas, ocorrencias, relints, fatores, denuncias)

    return {
        "areas": areas,
        "ocorrencias": ocorrencias,
        "relints": relints,
        "denuncias": denuncias,
        "fatores": fatores,
        "bingos": bingos,
    }


def get_area(areas, pid):
    return next((a for a in areas if a.poligono_id == pid), None)


def get_bingo(bingos, pid):
    return next((b for b in bingos if b.poligono_fm_id == pid), None)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.markdown(
    "<h2 style='color: #1E2761; margin-bottom: 0;'>CompStat IA</h2>",
    unsafe_allow_html=True,
)
st.sidebar.caption("Inteligencia criminal municipal")
st.sidebar.markdown("---")

pagina = st.sidebar.radio(
    "Navegacao",
    [
        "Dashboard",
        "Score / Bingos",
        "Editor de areas",
        "Quadro de Missao Diaria",
        "Evolucao 90 dias",
        "Gerar DOCX",
    ],
)

st.sidebar.markdown("---")
if st.sidebar.button("Recarregar dados"):
    st.cache_data.clear()
    st.rerun()


# ============================================================
# PAGINA 1: DASHBOARD
# ============================================================

def render_dashboard():
    st.title("Dashboard")
    dados = carregar_tudo()
    areas = dados["areas"]
    bingos = dados["bingos"]

    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            f"<div class='stat-card'><div class='stat-num'>{len(areas)}</div>"
            f"<div>Areas ativas</div></div>",
            unsafe_allow_html=True,
        )
    with col2:
        total_oco = len(dados["ocorrencias"])
        st.markdown(
            f"<div class='stat-card'><div class='stat-num'>{total_oco}</div>"
            f"<div>Ocorrencias (60d)</div></div>",
            unsafe_allow_html=True,
        )
    with col3:
        n_relints = len(dados["relints"])
        st.markdown(
            f"<div class='stat-card'><div class='stat-num'>{n_relints}</div>"
            f"<div>RELINTs ativos</div></div>",
            unsafe_allow_html=True,
        )
    with col4:
        n_disque = len(dados["denuncias"])
        st.markdown(
            f"<div class='stat-card'><div class='stat-num'>{n_disque}</div>"
            f"<div>Denuncias disque</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.subheader("Mapa de calor por area")
    try:
        from streamlit_folium import st_folium
        m = construir_mapa_folium(areas, bingos, ocorrencias=dados["ocorrencias"][:200])
        from heatmap import adicionar_cameras_ao_mapa
        m = adicionar_cameras_ao_mapa(m)
        st_folium(m, width=None, height=500, returned_objects=[])
    except ImportError:
        st.warning("Para mapa: pip install streamlit-folium folium")

    st.markdown("---")
    st.subheader("Top 5 areas por score")
    top5 = bingos[:5]
    for b in top5:
        c = b.componentes
        cor_class = "score-alto" if c.score_final > 0.6 else "score-medio" if c.score_final > 0.3 else "score-baixo"
        st.markdown(
            f"**{b.nome_area}** - <span class='{cor_class}'>{c.score_final:.2f}</span> "
            f"({b.n_camadas_ativas}/4 camadas ativas)",
            unsafe_allow_html=True,
        )
        st.caption(b.justificativa)
        st.markdown("")


# ============================================================
# PAGINA 2: SCORE / BINGOS DETALHADOS
# ============================================================

def render_scores():
    st.title("Score / Bingos detalhados")
    st.caption(
        "Cruzamento de 4 fontes com pesos diferenciados. "
        "RELINT oficial tem 3x o peso da denuncia anonima."
    )

    dados = carregar_tudo()
    bingos = dados["bingos"]

    for b in bingos:
        c = b.componentes
        with st.expander(
            f"{b.nome_area} | Score {c.score_final:.2f} | {b.n_camadas_ativas}/4 camadas"
        ):
            st.markdown(f"**Justificativa:** {b.justificativa}")

            st.markdown("**Componentes do score:**")
            comp_data = [
                {"Fonte": "Mancha criminal (oficial)", "Score": c.score_mancha, "Peso": c.peso_mancha, "Contrib": c.score_mancha * c.peso_mancha},
                {"Fonte": "RELINT (oficial)", "Score": c.score_relint, "Peso": c.peso_relint, "Contrib": c.score_relint * c.peso_relint},
                {"Fonte": "Fator urbano", "Score": c.score_fator, "Peso": c.peso_fator, "Contrib": c.score_fator * c.peso_fator},
                {"Fonte": "Disque Denuncia (anonimo)", "Score": c.score_disque, "Peso": c.peso_disque, "Contrib": c.score_disque * c.peso_disque},
                {"Fonte": "Modus + rotas", "Score": c.score_modus_rota, "Peso": c.peso_modus, "Contrib": c.score_modus_rota * c.peso_modus},
            ]
            st.dataframe(comp_data, use_container_width=True)

            if c.bonus_faccional > 1.0:
                st.warning(
                    f"Bonus faccional aplicado: x{c.bonus_faccional:.2f} "
                    f"(faccoes envolvidas: {', '.join(b.faccoes_envolvidas)})"
                )


# ============================================================
# PAGINA 3: EDITOR DE AREAS (CRUD)
# ============================================================

def render_editor():
    st.title("Editor de areas")
    store = AreasFMStore(DATA_DIR / "areas.json")

    aba_listar, aba_criar, aba_editar, aba_excluir = st.tabs([
        "Listar", "Criar nova", "Editar", "Excluir",
    ])

    with aba_listar:
        st.caption("Areas ativas no sistema.")
        areas = store.listar(incluir_inativos=True)
        for area in areas:
            icone = "✅" if area.ativo else "❌"
            with st.expander(f"{icone} {area.nome_area} ({area.poligono_id})"):
                st.json(area.model_dump(mode="json"))
                col1, col2 = st.columns(2)
                with col1:
                    if area.ativo:
                        if st.button("Desativar (preserva historico)",
                                      key=f"des_{area.poligono_id}"):
                            store.desativar(area.poligono_id, "Desativada via UI")
                            st.cache_data.clear()
                            st.success(f"{area.nome_area} desativada.")
                            st.rerun()
                    else:
                        if st.button("Reativar",
                                      key=f"reat_{area.poligono_id}"):
                            store.reativar(area.poligono_id)
                            st.cache_data.clear()
                            st.success(f"{area.nome_area} reativada.")
                            st.rerun()

    with aba_criar:
        st.caption("Adicionar nova area prioritaria ao sistema.")
        with st.form("form_criar"):
            nome = st.text_input("Nome da area*")
            aisp = st.text_input("AISP*", placeholder="ex: AISP 9")
            bairros = st.text_input("Bairros (separados por virgula)*",
                                     placeholder="Bangu, Realengo")
            base = st.text_input("Base FM*", placeholder="ex: Base Bangu")
            subpref = st.text_input("Subprefeitura*", placeholder="ex: Zona Oeste")
            dp = st.text_input("DP")
            bpm = st.text_input("BPM")
            wkt = st.text_area(
                "Geometria (WKT)*",
                value="POLYGON((-43.475 -22.880, -43.470 -22.880, -43.470 -22.875, -43.475 -22.875, -43.475 -22.880))",
                height=80,
            )
            obs = st.text_area("Observacoes")

            if st.form_submit_button("Criar area"):
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
                            observacoes=obs or None,
                        )
                        novo_id = store.criar(area)
                        st.cache_data.clear()
                        st.success(f"Area criada com id: {novo_id}")
                    except Exception as e:
                        st.error(f"Erro: {e}")

    with aba_editar:
        st.caption("Editar campos de uma area existente.")
        areas = store.listar()
        if not areas:
            st.info("Nenhuma area ativa.")
        else:
            pid = st.selectbox(
                "Selecionar area",
                [a.poligono_id for a in areas],
                format_func=lambda i: next(a.nome_area for a in areas if a.poligono_id == i),
            )
            area_atual = store.obter(pid)
            with st.form("form_editar"):
                novo_nome = st.text_input("Nome", value=area_atual.nome_area)
                novos_bairros = st.text_input("Bairros", value=", ".join(area_atual.bairros))
                nova_wkt = st.text_area("Geometria WKT", value=area_atual.geometria_wkt, height=80)
                nova_obs = st.text_area("Observacoes", value=area_atual.observacoes or "")
                if st.form_submit_button("Salvar"):
                    try:
                        store.atualizar(
                            poligono_id=pid,
                            nome_area=novo_nome,
                            bairros=[b.strip() for b in novos_bairros.split(",")],
                            geometria_wkt=nova_wkt,
                            observacoes=nova_obs or None,
                        )
                        st.cache_data.clear()
                        st.success("Atualizada.")
                    except Exception as e:
                        st.error(f"Erro: {e}")

    with aba_excluir:
        st.caption("Exclusao PERMANENTE. Para retirar de circulacao mantendo "
                   "historico, use 'Desativar' na aba Listar.")
        areas = store.listar(incluir_inativos=True)
        if not areas:
            st.info("Nenhuma area cadastrada.")
        else:
            pid_excluir = st.selectbox(
                "Area a EXCLUIR",
                [a.poligono_id for a in areas],
                format_func=lambda i: next(a.nome_area for a in areas if a.poligono_id == i),
                key="excluir_select",
            )
            confirmar = st.checkbox("Eu confirmo que quero excluir PERMANENTEMENTE esta area.")
            if st.button("Excluir permanentemente", type="primary"):
                if not confirmar:
                    st.warning("Marque a caixa de confirmacao primeiro.")
                else:
                    try:
                        store.excluir(pid_excluir, confirmar=True)
                        st.cache_data.clear()
                        st.success(f"Area {pid_excluir} excluida permanentemente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")


# ============================================================
# PAGINA 4: QMD
# ============================================================

def render_qmd():
    st.title("Quadro de Missao Diaria (QMD)")
    st.caption(
        "Ordem de servico que cada base da FM recebe. Gerado a partir do "
        "score, modus operandi e rotas de fuga conhecidas."
    )

    dados = carregar_tudo()
    areas = dados["areas"]
    bingos = dados["bingos"]
    relints = dados["relints"]
    ocorrencias = dados["ocorrencias"]

    pid = st.selectbox(
        "Selecionar area",
        [a.poligono_id for a in areas],
        format_func=lambda i: next(a.nome_area for a in areas if a.poligono_id == i),
    )

    area = get_area(areas, pid)
    bingo = get_bingo(bingos, pid)
    if not area or not bingo:
        st.error("Area sem dados.")
        return

    relints_area = [r for r in relints if r.poligono_fm_id == pid]
    oco_area = [o for o in ocorrencias if o.poligono_fm_id == pid]

    efetivo = st.slider("Efetivo alocado para esta area", 5, 80, 25)

    recomendacao = sugerir_modalidade(bingo, relints_area, oco_area, efetivo)
    qmd = gerar_qmd(
        area=area,
        bingo=bingo,
        recomendacao=recomendacao,
        relints_area=relints_area,
        acoes_pendentes_outros_orgaos=[],
        data_ref=date.today(),
    )

    md = qmd_para_markdown(qmd)
    st.markdown(md)

    st.download_button(
        "Baixar QMD em Markdown",
        data=md,
        file_name=f"QMD_{area.nome_area.replace(' ', '_')}_{qmd.data_referencia.isoformat()}.md",
        mime="text/markdown",
    )


# ============================================================
# PAGINA 5: EVOLUCAO 90D
# ============================================================

def render_evolucao():
    st.title("Evolucao apos atuacao da FM (90 dias)")
    st.caption(
        "Comparativo de indicadores antes e depois da atuacao da Forca "
        "Municipal nas areas prioritarias."
    )

    snapshots = carregar_snapshots()
    if not snapshots:
        st.warning("Sem snapshots em data/snapshots_90d.json. Rode `python -m src.seed_data`.")
        return

    dados = carregar_tudo()
    nome_por_area = {a.poligono_id: a.nome_area for a in dados["areas"]}

    comparativos = comparar_todas_areas(snapshots, nome_por_area)

    # Cards de resumo
    st.subheader("Resumo por area")
    for c in comparativos:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(c.nome_area, "")
        col2.metric("Roubos", f"{c.snapshot_depois.total_roubos}", f"{c.variacao_roubos_pct:+.1f}%")
        col3.metric("Furtos", f"{c.snapshot_depois.total_furtos}", f"{c.variacao_furtos_pct:+.1f}%")
        col4.metric("Score", f"{c.snapshot_depois.score_medio:.2f}", f"{c.variacao_score_pct:+.1f}%")
        st.caption(f"**{c.classificacao}**: {c.observacao}")
        st.markdown("---")

    # Gráfico de barras
    st.subheader("Variacao consolidada")
    try:
        png = gerar_grafico_evolucao(comparativos)
        st.image(png)
    except Exception as e:
        st.error(f"Erro ao gerar grafico: {e}")


# ============================================================
# PAGINA 6: GERAR DOCX
# ============================================================

def render_docx():
    st.title("Gerar relatorio DOCX editavel")
    st.caption("DOCX gerado para reuniao do CompStat. Editavel no Word/LibreOffice.")

    dados = carregar_tudo()
    areas = dados["areas"]
    bingos = dados["bingos"]
    relints = dados["relints"]
    ocorrencias = dados["ocorrencias"]
    snapshots = carregar_snapshots()

    pid = st.selectbox(
        "Area",
        [a.poligono_id for a in areas],
        format_func=lambda i: next(a.nome_area for a in areas if a.poligono_id == i),
    )

    efetivo = st.slider("Efetivo alocado", 5, 80, 25)

    if st.button("Gerar DOCX", type="primary"):
        with st.spinner("Gerando..."):
            try:
                area = get_area(areas, pid)
                bingo = get_bingo(bingos, pid)
                relints_area = [r for r in relints if r.poligono_fm_id == pid]
                oco_area = [o for o in ocorrencias if o.poligono_fm_id == pid]

                recomendacao = sugerir_modalidade(bingo, relints_area, oco_area, efetivo)
                qmd = gerar_qmd(
                    area, bingo, recomendacao, relints_area, [], date.today()
                )

                # Heatmap temporal
                heatmap_png = gerar_heatmap_temporal(oco_area)

                # Comparativo
                snaps_area = [s for s in snapshots if s.poligono_fm_id == pid]
                comparativo = None
                grafico_png = None
                if len(snaps_area) >= 2:
                    snaps_ordenados = sorted(snaps_area, key=lambda s: s.data_referencia)
                    from evolution import comparar_evolucao
                    comparativo = comparar_evolucao(
                        pid, area.nome_area,
                        snaps_ordenados[0], snaps_ordenados[-1],
                    )
                    grafico_png = gerar_grafico_evolucao([comparativo])

                nome_arq = f"output/relatorio_{pid}.docx"
                gerar_relatorio_docx(
                    area=area,
                    bingo=bingo,
                    recomendacao=recomendacao,
                    qmd=qmd,
                    comparativo_evolucao=comparativo,
                    heatmap_temporal_png=heatmap_png,
                    grafico_evolucao_png=grafico_png,
                    output_path=nome_arq,
                )

                with open(nome_arq, "rb") as f:
                    st.download_button(
                        "Baixar DOCX",
                        data=f.read(),
                        file_name=Path(nome_arq).name,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                st.success(f"DOCX gerado em {nome_arq}.")
            except Exception as e:
                st.error(f"Erro: {e}")
                import traceback
                st.code(traceback.format_exc())


# ============================================================
# ROUTER
# ============================================================

if pagina == "Dashboard":
    render_dashboard()
elif pagina == "Score / Bingos":
    render_scores()
elif pagina == "Editor de areas":
    render_editor()
elif pagina == "Quadro de Missao Diaria":
    render_qmd()
elif pagina == "Evolucao 90 dias":
    render_evolucao()
elif pagina == "Gerar DOCX":
    render_docx()

st.sidebar.markdown("---")
st.sidebar.caption("CompStat IA - MVP 3h Diego")
