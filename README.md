# CompStat IA MVP

Plataforma de inteligência criminal para gestão municipal de segurança pública. Cruza 5 fontes de dados com pesos diferenciados, identifica modus operandi, sugere modalidade de patrulhamento e gera relatórios editáveis para reuniões CompStat.

**Status:** MVP funcional. Construído solo em 3 horas com Claude Code sobre starter kit Python puro.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Streamlit](https://img.shields.io/badge/streamlit-app-FF4B4B.svg)](https://streamlit.io/)

---

## Problema

Cada relatório de área hoje leva **8 horas manuais** para o analista da prefeitura. A equipe cobre 3 a 5 áreas por semana. São **22 áreas prioritárias**. A IA não substitui o analista. Elimina o trabalho mecânico de cruzar planilhas, gerar mapas e digitar pontos prioritários.

## Solução

Pipeline determinístico em Python que recebe os dados oficiais da área e devolve:

1. **Score de risco** (0 a 1) com 5 camadas e pesos diferenciados
2. **Recomendação de patrulhamento** com efetivo distribuído entre viatura, moto e a pé
3. **Pontos de interceptação** geográficos a partir das rotas de fuga do RELINT
4. **QMD** (Quadro de Missão Diária) — ordem de serviço para a base da Força Municipal
5. **Relatório DOCX editável** com heatmap temporal, evolução 90 dias e tabela de componentes
6. **Comparativo antes/depois** para medir impacto da operação

---

## Pesos do score (regra fixa)

| Fonte | Peso | Natureza |
|---|---|---|
| Mancha criminal | **0.40** | Oficial quantitativo |
| RELINT | **0.30** | Oficial qualitativo (3x peso do Disque) |
| Fator urbano | **0.15** | Mapeamento de subprefeituras |
| Disque Denúncia | **0.10** | Anônimo, não verificado |
| Modus + rotas | **0.05** | Amplificação por padrão estruturado |
| Bônus faccional | **× 1.0 a 1.5** | Multiplicativo, por rivalidade na AISP |

> O peso menor do Disque é proposital. Denúncia anônima vale menos que dado oficial verificado.

---

## Features

- **CRUD completo de áreas** (criar, editar, desativar com histórico, excluir permanente)
- **Bônus faccional** automático quando áreas vizinhas têm facções rivais (TCP/CV/ADA/milícia)
- **5 áreas piloto** seedadas (Bangu, Copacabana, Lapa, Méier, Tijuca)
- **280 ocorrências, 5 RELINTs, 19 denúncias, 14 fatores urbanos** sintéticos realistas
- **Snapshots 90 dias** pré-gerados (Bangu -38%, Méier -30%, Copa -22%, Lapa -15%, Tijuca +5% controle)
- **Heatmap interativo** (Folium) e temporal 7×24 (matplotlib)
- **Mapa de câmeras municipais** (CSV de 145 KB integrado)
- **Sem chamadas a LLM no caminho crítico** — 100% determinístico, custo zero por execução

---

## Estrutura

```
compstat-mvp/
├── src/
│   ├── schemas.py           # Pydantic v2 (fechado)
│   ├── seed_data.py         # Gera 5 áreas piloto
│   ├── area_crud.py         # CRUD com exclusão permanente
│   ├── score_engine.py      # Cruzamento 5 camadas + pesos
│   ├── recommendation.py    # Modalidade FM + pontos interceptação
│   ├── qmd_generator.py     # Quadro de Missão Diária
│   ├── evolution.py         # Comparativo 90 dias
│   ├── heatmap.py           # Folium + PNG temporal + barras
│   ├── docx_generator.py    # Relatório editável
│   └── streamlit_app.py     # UI integrada (6 páginas)
├── data/
│   ├── areas.json           # Storage CRUD
│   ├── areas_iniciais.json  # Seed
│   ├── ocorrencias.json     # 280 ocorrências com modus
│   ├── relints.json         # 5 RELINTs com modus + rotas
│   ├── denuncias.json       # 19 denúncias Disque
│   ├── fatores_urbanos.json # 14 fatores
│   ├── snapshots_90d.json   # Antes/depois pré-gerados
│   └── cameras_areas_fm.csv # Câmeras municipais georreferenciadas
├── scripts/
│   └── run_bangu.py         # Pipeline end-to-end para Bangu
├── output/                  # DOCX, PNGs e QMD gerados (gitignored)
├── PASSO_A_PASSO.md         # Roteiro de construção em 3h
├── PITCH.md                 # Roteiro de demo de 5 min
├── PROMPTS.md               # Prompts para Claude Code
└── CLAUDE.md                # Regras invioláveis do projeto
```

---

## Como rodar

### 1. Setup

```bash
git clone https://github.com/DihRJ/compstat-mvp.git
cd compstat-mvp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Streamlit (UI completa, 6 páginas)

```bash
streamlit run src/streamlit_app.py
```

Abre em `http://localhost:8501`. Páginas: Dashboard, Score, Editor, QMD, Evolução, DOCX.

### 3. Pipeline Bangu (end-to-end, sem UI)

```bash
.venv/bin/python scripts/run_bangu.py
```

Gera em `output/`:

- `relatorio_bangu.docx` — relatório completo com heatmap e gráfico de evolução
- `qmd_bangu.md` — preview do QMD em markdown
- `heatmap_bangu.png` — distribuição temporal 7×24
- `evolucao_90d.png` — barras horizontais comparando as 5 áreas

---

## Exemplo: caso Bangu

```
[ranking de score]
  copa_01    Calcadao Copacabana Posto 4  score=0.790  bonus=1.00  camadas=4/4
  bangu_01   Calcadao de Bangu            score=0.770  bonus=1.00  camadas=4/4
  lapa_01    Largo da Lapa                score=0.685  bonus=1.00  camadas=4/4
  meier_01   Dias da Cruz Meier           score=0.585  bonus=1.00  camadas=4/4
  tijuca_01  Praca Saens Pena             score=0.492  bonus=1.00  camadas=4/4

[recomendacao] modalidade=a_pe
  viaturas=1 motos=0 a_pe=20 | efetivo=24
  pontos interceptacao: 2
  horario=20:00-23:00  dias=sex,sab
  justif: 100% das ocorrencias sao 'a_pe' -> modalidade FM 'a_pe';
          2 pontos de interceptacao sugeridos com base em rotas de fuga
          mapeadas em RELINT; presenca de TCP requer postura defensiva.

[evolucao 90d Bangu] roubos=-38.1% furtos=-28.6% score=-22.8%
  -> melhora_significativa
```

---

## Regras invioláveis

Para colaboradores, ver [`CLAUDE.md`](CLAUDE.md). Resumo:

1. Não reescrever `schemas.py`
2. Pesos do score são lei
3. Modus + rotas geram `pontos_intercepcao` automaticamente
4. Foco FM: **roubos e furtos** (não homicídio nem tráfico)
5. CRUD áreas tem 4 operações (incluindo excluir permanente)
6. DOCX é **editável** (não converter para PDF)
7. QMD é o entregável principal

---

## Roadmap

- [ ] Integração com SISPMUC (RJ) para puxar ocorrências reais
- [ ] Mapa de câmeras com sugestão de novas posições por gap analysis
- [ ] Page de comparativo lado a lado para reunião CompStat
- [ ] Export do QMD em PDF para impressão da base
- [ ] Multi-tenancy por município

---

## Stack

Python 3.9+ • Pydantic v2 • Streamlit • Folium • Shapely • python-docx • Matplotlib

---

## Licença

[MIT](LICENSE) © Diego Alves
