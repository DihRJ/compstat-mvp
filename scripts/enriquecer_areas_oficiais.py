"""Enriquece areas.json com AISP, bairros, DP e BPM derivados dos CSVs oficiais.

Para cada uma das 8 áreas da FM:
  - Filtra ocorrências (`df_ocorrencias_tratado.csv`) dentro do polígono e
    pega a AISP mais frequente.
  - Filtra denúncias (`disk_denuncia.csv`) dentro do polígono e pega:
      * bairros mais comuns (top 3)
      * BPM mais comum (extraído de `orgaos.nome` quando contém "BPM")
      * DP mais comum (extraído quando contém "DP" ou "Delegacia")
  - Atualiza areas.json e areas_iniciais.json com esses dados.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

DATA_DIR = ROOT / "data"
FONTE_OCO = Path("/tmp/compstat_dados/df_ocorrencias_tratado - Extração 1 .csv")
FONTE_DEN = Path("/tmp/compstat_dados/disk_denuncia.csv")

RE_BPM = re.compile(r"(\d+)[ºo°]?\s*BPM|\bBPM\s*(\d+)", re.IGNORECASE)
RE_DP = re.compile(r"(\d+)[ºo°ªa°]?\s*DP|\bDelegacia\b.*?(\d+)", re.IGNORECASE)


def carregar_areas_geom():
    from shapely import wkt as shapely_wkt
    areas_raw = json.loads((DATA_DIR / "areas.json").read_text(encoding="utf-8"))
    areas = []
    for a in areas_raw:
        poly = shapely_wkt.loads(a["geometria_wkt"])
        minx, miny, maxx, maxy = poly.bounds
        areas.append({
            "raw": a,
            "poly": poly,
            "bbox": (minx, miny, maxx, maxy),
        })
    return areas, areas_raw


def detectar_area(lat, lng, areas):
    from shapely.geometry import Point
    pt = Point(lng, lat)
    for a in areas:
        minx, miny, maxx, maxy = a["bbox"]
        if not (minx <= lng <= maxx and miny <= lat <= maxy):
            continue
        if a["poly"].contains(pt):
            return a["raw"]["poligono_id"]
    return None


def main():
    areas, areas_raw = carregar_areas_geom()
    print(f"[carga] {len(areas)} áreas")

    # ------- AISP a partir de ocorrências -------
    aisp_por_area: dict[str, Counter] = {pid: Counter() for pid in
                                          [a["raw"]["poligono_id"] for a in areas]}
    locf_por_area: dict[str, Counter] = {pid: Counter() for pid in aisp_por_area}

    with open(FONTE_OCO, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                lat = float(row["latitude"])
                lng = float(row["longitude"])
            except (ValueError, KeyError):
                continue
            pid = detectar_area(lat, lng, areas)
            if not pid:
                continue
            aisp_raw = (row.get("aisp") or "").strip()
            if aisp_raw:
                aisp_por_area[pid][aisp_raw] += 1
            locf_raw = (row.get("locf") or "").strip()
            if locf_raw:
                locf_por_area[pid][locf_raw] += 1

    # ------- Bairros, BPM, DP a partir de denúncias -------
    bairro_por_area: dict[str, Counter] = {pid: Counter() for pid in aisp_por_area}
    bpm_por_area: dict[str, Counter] = {pid: Counter() for pid in aisp_por_area}
    dp_por_area: dict[str, Counter] = {pid: Counter() for pid in aisp_por_area}

    with open(FONTE_DEN, encoding="latin-1") as f:
        for row in csv.DictReader(f, delimiter=";"):
            try:
                lat = float((row.get("latitude") or "").replace(",", "."))
                lng = float((row.get("longitude") or "").replace(",", "."))
            except ValueError:
                continue
            pid = detectar_area(lat, lng, areas)
            if not pid:
                continue
            bairro = (row.get("bairro_logradouro") or "").strip().title()
            if bairro:
                bairro_por_area[pid][bairro] += 1

            orgao = (row.get("orgaos.nome") or "").strip().upper()
            m_bpm = RE_BPM.search(orgao)
            if m_bpm:
                num = m_bpm.group(1) or m_bpm.group(2)
                bpm_por_area[pid][f"{num}º BPM"] += 1

            m_dp = RE_DP.search(orgao)
            if m_dp:
                num = m_dp.group(1) or m_dp.group(2)
                dp_por_area[pid][f"{num}ª DP"] += 1

    # ------- Atualiza áreas -------
    print("\n[enriquecimento]")
    for area_dict in areas_raw:
        pid = area_dict["poligono_id"]

        # AISP — top 1
        aisp_top = aisp_por_area[pid].most_common(1)
        if aisp_top:
            area_dict["aisp"] = f"AISP {aisp_top[0][0]}"

        # Bairros — top 3 (combinados)
        bairros_top = bairro_por_area[pid].most_common(3)
        if bairros_top:
            area_dict["bairros"] = [b for b, _ in bairros_top]

        # BPM — top 1
        bpm_top = bpm_por_area[pid].most_common(1)
        if bpm_top:
            area_dict["bpm"] = bpm_top[0][0]

        # DP — top 1
        dp_top = dp_por_area[pid].most_common(1)
        if dp_top:
            area_dict["dp"] = dp_top[0][0]

        # Remove "A definir" residual
        if area_dict.get("aisp") in ("A definir", ""):
            area_dict["aisp"] = "—"

        print(f"  {pid:35s} | AISP {area_dict['aisp']:12s}"
              f" | BPM {area_dict.get('bpm') or '—':10s}"
              f" | DP {area_dict.get('dp') or '—':10s}"
              f" | Bairros: {', '.join(area_dict['bairros'][:3])}")

    # Salva nos dois arquivos
    for nome in ("areas.json", "areas_iniciais.json"):
        path = DATA_DIR / nome
        path.write_text(
            json.dumps(areas_raw, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        print(f"  ✓ {nome} atualizado.")


if __name__ == "__main__":
    main()
