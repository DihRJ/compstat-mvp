"""Gera snapshots_90d.json para as 8 áreas reais.

Como o repo CompStat não fornece série antes/depois, geramos snapshots
sintéticos baseados no volume real de ocorrências, com:
  - Antes: 90 dias atrás
  - Depois: data de referência atual
  - Variação plausível por área (algumas com queda significativa, outras estáveis)

A área âncora para a narrativa de impacto da FM é Presidente Vargas
(maior volume) com queda projetada de -38%, simulando o efeito esperado
da operação.
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

DATA_DIR = ROOT / "data"

# Variação simulada por área (valores plausíveis pós-operação FM)
VARIACOES = {
    "presidente_vargas_ca_20": -38,   # âncora
    "rodoviaria_terminal__02": -30,
    "estacoes_sao_francis_19": -22,
    "metro_botafogo_rua_s_09": -18,
    "praia_de_botafogo_ru_14": -15,
    "rio_sul_12":              -10,
    "jardim_de_alah_10":        -5,
    "campo_grande_estacao_11":  +5,   # controle (sem melhora)
}


def main() -> None:
    areas = json.loads((DATA_DIR / "areas.json").read_text(encoding="utf-8"))
    ocorrencias = json.loads(
        (DATA_DIR / "ocorrencias.json").read_text(encoding="utf-8")
    )

    # Conta roubos/furtos atuais por área
    contagem = {}
    for o in ocorrencias:
        pid = o["poligono_fm_id"]
        d = contagem.setdefault(pid, {"roubos": 0, "furtos": 0})
        if o["tipo"].startswith("roubo"):
            d["roubos"] += 1
        elif o["tipo"].startswith("furto"):
            d["furtos"] += 1

    hoje = date.today()
    antes = hoje - timedelta(days=90)
    snapshots: list[dict] = []

    for a in areas:
        pid = a["poligono_id"]
        atual = contagem.get(pid, {"roubos": 0, "furtos": 0})
        var = VARIACOES.get(pid, -10)  # default -10% se não mapeado

        # "Antes" calculado retroativo (volume atual / (1 + var/100))
        # Se var=-38%: antes = atual / 0.62 → atual era 38% maior antes
        fator = 1 + var / 100
        roubos_antes = int(atual["roubos"] / fator) if fator > 0 else atual["roubos"] * 2
        furtos_antes = int(atual["furtos"] / fator) if fator > 0 else atual["furtos"] * 2

        # Score sintético baseado em volume
        score_atual = min(1.0, (atual["roubos"] + atual["furtos"]) / 250)
        score_antes = min(1.0, (roubos_antes + furtos_antes) / 250)

        # Snapshot antes
        snapshots.append({
            "snapshot_id": f"snap_{pid}_antes",
            "poligono_fm_id": pid,
            "data_referencia": antes.isoformat(),
            "total_roubos": roubos_antes,
            "total_furtos": furtos_antes,
            "score_medio": round(score_antes, 2),
            "ranking_pct": 50.0,
        })
        # Snapshot depois
        snapshots.append({
            "snapshot_id": f"snap_{pid}_depois",
            "poligono_fm_id": pid,
            "data_referencia": hoje.isoformat(),
            "total_roubos": atual["roubos"],
            "total_furtos": atual["furtos"],
            "score_medio": round(score_atual, 2),
            "ranking_pct": 50.0,
        })

        print(f"  {pid:30s} | R {roubos_antes}→{atual['roubos']:3d} "
              f"F {furtos_antes:3d}→{atual['furtos']:3d} "
              f"(var simulado {var:+d}%)")

    # Backup
    import shutil
    origem = DATA_DIR / "snapshots_90d.json"
    if origem.exists():
        backup = DATA_DIR / "snapshots_90d.json.backup_5areas"
        if not backup.exists():
            shutil.copy2(origem, backup)
            print(f"  ⚙ backup: snapshots_90d.json → {backup.name}")

    (DATA_DIR / "snapshots_90d.json").write_text(
        json.dumps(snapshots, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"\n[OK] {len(snapshots)} snapshots gerados para {len(areas)} áreas.")


if __name__ == "__main__":
    main()
