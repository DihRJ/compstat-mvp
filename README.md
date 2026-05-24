# CompStat IA — Equipe 15

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Streamlit](https://img.shields.io/badge/streamlit-app-FF4B4B.svg)](https://streamlit.io/)
[![Built with Claude](https://img.shields.io/badge/built%20with-Claude%20Code-d97757.svg)](https://claude.com/claude-code)

---

## 🛡️ Equipe

| | |
|---|---|
| **Equipe** | 15 |
| **Tema** | Segurança (Segurança Pública Municipal) |
| **Hackathon** | CompStat-Rio · Anthropic 2026 |

### Membros

- **Diego Alves**
- **Felipe Passos**
- **Lucas Xavier**
- **Amanda Galvão**

---

## 📝 Resumo

**CompStat IA** é uma plataforma de inteligência criminal para a Prefeitura do Rio de Janeiro que automatiza a produção dos relatórios analíticos das **22 áreas prioritárias** da Força Municipal — hoje feitos manualmente em **8 horas por área**.

A solução **cruza 5 fontes oficiais** (mancha criminal, RELINTs, fatores urbanos, Disque Denúncia e modus operandi) com pesos diferenciados, calcula um score de risco por área, sugere modalidade e efetivo de patrulhamento, gera o **Quadro de Missão Diária (QMD)** e produz o **Relatório Analítico de Área** no formato oficial CompStat Municipal pronto para a reunião semanal com o Prefeito.

**Dados reais aplicados:** 8 áreas oficiais da FM, 7.508 ocorrências, 405 denúncias, 842 fatores urbanos, 8 RELINTs, 3.169 pessoas em situação de rua (Censo CPSR), cruzados com 1.628 territórios de domínio criminal.

---

## 🏗️ Arquitetura / Abordagem

### Stack

`Python 3.9` · `Streamlit` · `Folium` · `Pydantic v2` · `python-docx` · `Shapely` · `Matplotlib` · `Anthropic API (opcional)`

### Pipeline determinístico

```
                ┌─────────────────────────┐
   8 áreas FM ─►│   ingestão / parsing    │◄── JSON · CSV · PDF · DOC · DOCX
   (shapefile)  └────────────┬────────────┘
                             │
              ┌──────────────▼──────────────┐
              │  cruzamento de 5 camadas    │
              │  (pesos: 0,40 / 0,30 /      │
              │   0,15 / 0,10 / 0,05)       │
              │  + bônus faccional 1,0–1,5  │
              └──────────────┬──────────────┘
                             │
              ┌──────────────▼──────────────┐
              │  Score · QMD · Recomendação │
              │  Heatmap · Evolução 90d     │
              └──────────────┬──────────────┘
                             │
                ┌────────────▼─────────────┐
                │  Relatório DOCX oficial  │
                │  (Capa · Resumo Exec ·   │
                │   5 seções CompStat)     │
                └──────────────────────────┘
```

### Como Claude foi usado para construir

O sistema inteiro (~1.800 linhas de Python + 11 scripts) foi desenvolvido em sessão única usando **Claude Code (Opus 4.7, contexto 1M)**, com a seguinte divisão de trabalho:

| Tarefa | Claude | Equipe |
|---|---|---|
| Arquitetura inicial e schemas Pydantic | ✅ | revisão |
| Score engine determinístico (lei dos pesos) | ✅ | regras de negócio (briefing) |
| Geração de relatórios DOCX no formato oficial | ✅ | layout do briefing |
| UI Streamlit (7 páginas) | ✅ | direção UX |
| Importação espacial dos dados oficiais (CSV/shapefile/DOCX/PDF) | ✅ | curadoria das fontes |
| 2 rounds de auditoria UX/UI via subagents (UX Researcher + UI Designer) | ✅ | priorização |
| Debug e calibragem (saturação de score, encoding latin-1, parse de hora HH:MM:SS) | ✅ | observação dos bugs |

### Como Claude atua **dentro** da aplicação

A regra padrão é **determinismo total no caminho crítico** (briefing exige reprodutibilidade). Há **um único ponto opcional** onde o LLM é invocado:

🧠 **Botão "Explicar com IA" no QMD** — chama Claude Haiku 4.5 via Anthropic API com prompt estruturado para gerar um parágrafo em linguagem natural justificando a sugestão de efetivo. Funciona apenas se `ANTHROPIC_API_KEY` estiver configurada; o cálculo numérico em si é sempre determinístico (heurística multifatorial em `src/sugestao_efetivo.py`).

Esta separação deliberada garante:
- **Custo zero por execução** no fluxo normal
- **Reprodutibilidade** (mesmo input → mesmo output)
- **Resistência a downtime** da API
- **Auditabilidade** (cada componente do score tem fórmula visível)

---

## 🎯 Score: lei dos pesos

| Fonte | Peso | Natureza |
|---|---|---|
| Mancha criminal | **0,40** | Oficial quantitativo (lat/long de roubos e furtos) |
| RELINT | **0,30** | Oficial qualitativo — **3× o peso do Disque** |
| Fator urbano | **0,15** | Iluminação, vegetação, PSR, calçada, obstáculos |
| Disque Denúncia | **0,10** | Anônimo, não verificado |
| Modus + rotas | **0,05** | Amplificação por padrão estruturado |
| Bônus faccional | **× 1,0 a 1,5** | Multiplicativo, por rivalidade territorial |

> O peso menor do Disque é proposital: denúncia anônima vale menos que dado oficial verificado.

---

## ✨ Features entregues

- ✅ **7 páginas** (Dashboard, Score, Editor, Importar, QMD, Evolução, Relatórios)
- ✅ **8 áreas oficiais** da Força Municipal (shapefile CompStat-Rio)
- ✅ **Editor visual** de polígonos com `folium.Draw` (desenhar área no mapa, salvar em WKT)
- ✅ **Importação multi-formato** (JSON/CSV/PDF/DOCX/TXT) com detecção automática
- ✅ **Periodização** sidebar (7d/30d/60d/90d/Todo/custom) afetando mapa, heatmap e score
- ✅ **Mapa de risco** com heatmap density (Folium HeatMap) + filtros por área e tipo de crime
- ✅ **Layer toggle** para áreas, ocorrências, câmeras e pontos de interceptação
- ✅ **Sugestão de efetivo híbrida** — heurística determinística + botão opcional LLM
- ✅ **Relatório DOCX oficial CompStat** (Capa, Resumo Executivo com 4 perguntas norteadoras, 5 seções, tabela 5×4 de efetivo, plano de ação pré-populado por órgão)
- ✅ **Relatório consolidado** das 8 áreas em um único DOCX
- ✅ **Pacote oficial**: cruzamento com `dominio_territorial.csv` (1.628 territórios) → identificação de facção por área (TCP/CV/milícia)

---

## 🔗 Links

| | |
|---|---|
| **Repositório** | https://github.com/DihRJ/compstat-mvp |
| **URL pública** | _Em preparação para Streamlit Community Cloud_ |
| **Briefing oficial** | [CompStat-Rio Hackathon](https://github.com/CompStat-Rio/claude_impact_lab_compstat_rio) |

---

## 🎥 Vídeo demo

📽️ **[Aguardando publicação — link será adicionado em breve]**

> Demonstração de 60 segundos cobrindo: navegação entre áreas, mapa de risco, geração do relatório DOCX e botão de sugestão IA.

---

## 🚀 Como rodar localmente

```bash
git clone https://github.com/DihRJ/compstat-mvp.git
cd compstat-mvp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# UI interativa (7 páginas)
streamlit run src/streamlit_app.py
# → http://localhost:8501

# OU pipeline CLI end-to-end (área Presidente Vargas como exemplo)
python scripts/run_bangu.py
# Gera output/relatorio_bangu.docx, qmd_bangu.md, heatmap_bangu.png, evolucao_90d.png
```

### Opcional — botão "Explicar com IA"

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
streamlit run src/streamlit_app.py
```

---

## 📂 Estrutura do projeto

```
compstat-mvp/
├── src/
│   ├── schemas.py              # Pydantic v2 (fechado)
│   ├── area_crud.py            # CRUD com exclusão permanente
│   ├── score_engine.py         # Cruzamento 5 camadas + pesos diferenciados
│   ├── recommendation.py       # Modalidade FM + pontos interceptação
│   ├── sugestao_efetivo.py     # Heurística multifatorial de efetivo
│   ├── explicacao_llm.py       # Botão opcional Claude Haiku
│   ├── qmd_generator.py        # Quadro de Missão Diária
│   ├── relatorio_compstat.py   # Geradores no formato oficial
│   ├── docx_generator.py       # DOCX por área + consolidado
│   ├── importador.py           # Multi-formato JSON/CSV/PDF/DOCX
│   ├── evolution.py            # Comparativo 90 dias
│   ├── heatmap.py              # Folium + heatmap density + PNG
│   └── streamlit_app.py        # UI integrada (7 páginas)
├── data/                       # 8 áreas oficiais + dados reais
├── scripts/                    # Importação CompStat-Rio + run end-to-end
├── output/                     # DOCX e PNGs gerados (gitignored)
└── CLAUDE.md                   # Regras invioláveis (lei dos pesos)
```

---

## 📜 Licença

[MIT](LICENSE) · construído por **Equipe 15** com Claude Code

