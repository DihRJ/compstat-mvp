# CompStat IA MVP 3h - Regras para Claude Code

Diego está construindo SOLO em 3 horas. O starter kit em `src/` já implementa 90% da lógica. Sua função: validar, integrar, gerar 1-2 casos reais, ajustar UI.

## Regras invioláveis

1. **Não reescreva schemas.py.** Está fechado. Se faltar campo, peça permissão.

2. **PESOS DIFERENCIADOS DO SCORE são lei** (`score_engine.py`):
   - Mancha criminal: 0.40
   - RELINT (oficial): 0.30 (3x peso do Disque)
   - Fator urbano: 0.15
   - Disque Denúncia (anônimo): 0.10
   - Modus + rotas: 0.05
   - Bônus faccional multiplicativo: 1.0 a 1.5

3. **Modus operandi e rotas de fuga** já entram no cruzamento via `calcular_bonus_modus_e_rotas()` e geram `pontos_intercepcao` em `recommendation.py`. Não duplique essa lógica.

4. **Foco FM: roubos e furtos.** Outros crimes (homicídio, tráfico) NÃO devem virar recomendação de patrulhamento FM.

5. **CRUD áreas tem 4 operações**: criar, editar, desativar (preserva histórico), **excluir permanente** (`area_crud.excluir(confirmar=True)`).

6. **DOCX é EDITÁVEL** (.docx, não PDF). `docx_generator.py` gera. Não converta para PDF.

7. **QMD é entregável principal novo.** `qmd_generator.gerar_qmd()` retorna o objeto. Use `qmd_para_markdown()` para preview.

8. **Snapshots 90 dias estão em `data/snapshots_90d.json`** (pré-gerados realistas: Bangu -38%, Méier -30%, Copa -22%, Lapa -15%, Tijuca +5% controle). Não regenere a não ser que peça.

9. **Sem chamadas Claude SDK no MVP.** Tudo determinístico em Python puro. Economiza tempo e custo.

10. **3 horas total.** Se ficar mais de 20 min num bloqueio, pula e segue.

## Estrutura

```
src/
├── schemas.py           # Pydantic v2 fechado
├── seed_data.py         # Gera 5 áreas piloto realistas
├── area_crud.py         # CRUD com excluir permanente
├── score_engine.py      # Cruzamento 5 camadas + pesos diferenciados
├── recommendation.py    # Sugere modalidade FM (viatura/moto/a pé) + pontos interceptação
├── qmd_generator.py     # Quadro de Missão Diária
├── evolution.py         # Comparativo 90d antes/depois
├── heatmap.py           # Folium choropleth + temporal PNG + barras evolução
├── docx_generator.py    # Relatório editável
└── streamlit_app.py     # UI integrada (6 páginas)

data/
├── areas.json           # Storage CRUD
├── areas_iniciais.json  # Seed
├── ocorrencias.json     # 320 ocorrências com modus
├── relints.json         # 5 RELINTs (1 por área) com modus + rotas
├── denuncias.json       # ~18 denúncias disque
├── fatores_urbanos.json # 13 fatores mapeados
└── snapshots_90d.json   # Antes/depois pré-gerados
```

## Sucesso = critério mínimo

- Streamlit roda em localhost:8501
- 5 páginas funcionam (Dashboard, Score, Editor, QMD, Evolução, DOCX)
- Caso Bangu: score alto, modus a_pe identificado, rota de fuga visível, QMD com pontos prioritários
- 1 DOCX gerado e validado visualmente
- Comparativo 90d mostra Bangu com -38%
