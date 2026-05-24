"""
Geração de heatmaps:
  - Folium choropleth interativo (para Streamlit)
  - PNG estático (para DOCX)
"""

import io
from pathlib import Path
from typing import Optional
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from schemas import AreaPoligonoFM, BingoArea, Ocorrencia, Coordenada


# ============================================================
# HEATMAP FOLIUM (interativo, para Streamlit)
# ============================================================

def construir_mapa_folium(
    areas: list[AreaPoligonoFM],
    bingos: list[BingoArea],
    ocorrencias: Optional[list[Ocorrencia]] = None,
    pontos_intercepcao: Optional[list[Coordenada]] = None,
    centro: tuple[float, float] = (-22.9068, -43.1729),
    zoom: int = 11,
):
    """
    Retorna objeto folium.Map com:
      - Polígonos coloridos por score (vermelho = alto)
      - Marcadores de ocorrências (opcional)
      - Marcadores de pontos de interceptação (opcional)
    """
    try:
        import folium
        from shapely import wkt
    except ImportError as e:
        raise ImportError(f"Para mapa folium: pip install folium shapely. Faltou: {e.name}")

    score_por_id = {b.poligono_fm_id: b.componentes.score_final for b in bingos}

    m = folium.Map(location=centro, zoom_start=zoom, tiles="OpenStreetMap")

    # Adicionar polígonos coloridos por score
    for area in areas:
        if not area.ativo:
            continue
        try:
            geom = wkt.loads(area.geometria_wkt)
            score = score_por_id.get(area.poligono_id, 0)
            cor = _cor_por_score(score)

            if geom.geom_type == "Polygon":
                coords = [[lat, lng] for lng, lat in geom.exterior.coords]
                folium.Polygon(
                    locations=coords,
                    popup=folium.Popup(
                        f"<b>{area.nome_area}</b><br>"
                        f"Score: {score:.2f}<br>"
                        f"AISP: {area.aisp}<br>"
                        f"Base: {area.base_fm}",
                        max_width=300,
                    ),
                    tooltip=f"{area.nome_area} ({score:.2f})",
                    color=cor,
                    weight=2,
                    fill=True,
                    fill_color=cor,
                    fill_opacity=0.6,
                ).add_to(m)
        except Exception:
            continue

    # Adicionar ocorrências (cluster se muitas)
    if ocorrencias:
        try:
            from folium.plugins import MarkerCluster
            cluster = MarkerCluster(name="Ocorrencias").add_to(m)
            for o in ocorrencias[:500]:  # cap em 500 para perf
                folium.CircleMarker(
                    location=[o.coordenada.lat, o.coordenada.lng],
                    radius=3,
                    color="darkred",
                    fill=True,
                    fill_opacity=0.6,
                    popup=f"{o.tipo} ({o.modalidade_crime})",
                ).add_to(cluster)
        except ImportError:
            pass

    # Adicionar pontos de interceptação
    if pontos_intercepcao:
        for p in pontos_intercepcao:
            folium.Marker(
                location=[p.lat, p.lng],
                popup=p.descricao or "Ponto de interceptacao",
                icon=folium.Icon(color="green", icon="flag"),
            ).add_to(m)

    return m


def _cor_por_score(score: float) -> str:
    """Mapa de cor verde -> amarelo -> laranja -> vermelho conforme score."""
    if score < 0.25:
        return "#2E7D32"  # verde
    if score < 0.50:
        return "#FBC02D"  # amarelo
    if score < 0.75:
        return "#EF6C00"  # laranja
    return "#C62828"  # vermelho


# ============================================================
# HEATMAP TEMPORAL (matriz 7x24, para DOCX)
# ============================================================

def gerar_heatmap_temporal(ocorrencias: list[Ocorrencia]) -> bytes:
    """
    Matriz 7 dias x 24 horas com volume de ocorrências.
    Retorna PNG em bytes.
    """
    dias_map = {"dom": 0, "seg": 1, "ter": 2, "qua": 3, "qui": 4, "sex": 5, "sab": 6}
    matrix = np.zeros((7, 24), dtype=int)

    for o in ocorrencias:
        d = dias_map.get(o.dia_semana, 0)
        h = o.hora
        matrix[d, h] += 1

    return _render_matriz_temporal(matrix)


def _render_matriz_temporal(matrix: np.ndarray) -> bytes:
    dias = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sab"]
    horas = [f"{h:02d}" for h in range(24)]

    fig, ax = plt.subplots(figsize=(12, 3))
    im = ax.imshow(matrix, cmap="Reds", aspect="auto")
    ax.set_xticks(range(24))
    ax.set_xticklabels(horas, fontsize=8)
    ax.set_yticks(range(7))
    ax.set_yticklabels(dias, fontsize=9)
    ax.set_xlabel("Hora do dia")
    ax.set_title("Distribuicao temporal de ocorrencias", fontsize=11)

    max_v = matrix.max() if matrix.size > 0 else 1
    for i in range(7):
        for j in range(24):
            if matrix[i, j] >= 0.7 * max_v and matrix[i, j] > 0:
                ax.text(j, i, str(matrix[i, j]),
                        ha="center", va="center",
                        color="white", fontsize=7, weight="bold")

    plt.colorbar(im, ax=ax, label="Ocorrencias")
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ============================================================
# COMPARATIVO DE EVOLUÇÃO (gráfico de barras antes/depois)
# ============================================================

def gerar_grafico_evolucao(comparativos) -> bytes:
    """
    Gráfico de barras horizontal: variação % de roubos por área.
    Verde = melhora, vermelho = piora.
    """
    nomes = [c.nome_area for c in comparativos]
    variacoes = [c.variacao_roubos_pct for c in comparativos]
    cores = ["#2E7D32" if v < 0 else "#C62828" for v in variacoes]

    fig, ax = plt.subplots(figsize=(10, max(4, len(nomes) * 0.4)))
    bars = ax.barh(nomes, variacoes, color=cores)
    ax.axvline(x=0, color="black", linewidth=0.5)
    ax.set_xlabel("Variacao % de roubos (90 dias)")
    ax.set_title("Evolucao apos atuacao da Forca Municipal")

    # Anotar valores
    for bar, v in zip(bars, variacoes):
        x = bar.get_width()
        ax.text(
            x + (1 if x >= 0 else -1),
            bar.get_y() + bar.get_height() / 2,
            f"{v:+.1f}%",
            va="center",
            ha="left" if x >= 0 else "right",
            fontsize=9,
            fontweight="bold",
        )

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


_DEFAULT_CAMERAS_CSV = str(Path(__file__).resolve().parent.parent / "data" / "cameras_areas_fm.csv")


def adicionar_cameras_ao_mapa(m, csv_path: str = _DEFAULT_CAMERAS_CSV):
    """Adiciona câmeras existentes e sugere novas ao mapa folium."""
    import csv, re
    try:
        import folium
    except ImportError:
        return m

    cameras = []
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                match = re.search(r"POINT \(([0-9.\-]+) ([0-9.\-]+)\)", row["geometry"])
                if match:
                    cameras.append({
                        "id": row["id_ponto"],
                        "area": row["nome_area_fm"],
                        "lng": float(match.group(1)),
                        "lat": float(match.group(2)),
                    })
    except FileNotFoundError:
        return m

    # Câmeras existentes: ponto azul
    grupo = folium.FeatureGroup(name=f"Cameras ({len(cameras)})")
    for c in cameras:
        folium.CircleMarker(
            location=[c["lat"], c["lng"]],
            radius=4,
            color="#1565C0",
            fill=True,
            fill_color="#1565C0",
            fill_opacity=0.8,
            popup=f"Camera: {c['area'][:40]}",
            tooltip="Camera ativa",
        ).add_to(grupo)
    grupo.add_to(m)
    folium.LayerControl().add_to(m)
    return m
