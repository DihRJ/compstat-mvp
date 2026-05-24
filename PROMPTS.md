# 3 prompts para Claude Code

Cole **um por vez**. `/clear` entre eles.

---

## PROMPT 1 (cole após Fase 2 do PASSO_A_PASSO.md - Streamlit já rodando)

```
Olá. Leia CLAUDE.md primeiro.

Tarefa: validar end-to-end o caso de Bangu, que é o caso oficial do briefing.

1. Sem reescrever código, RODE este script no terminal:

   python -c "
   import sys, json
   sys.path.insert(0, 'src')
   from area_crud import AreasFMStore
   from score_engine import calcular_bingos_todas_areas
   from recommendation import sugerir_modalidade
   from qmd_generator import gerar_qmd, qmd_para_markdown
   from schemas import RelintEstruturado, Ocorrencia, DenunciaDisque, FatorUrbano
   from datetime import date

   areas = AreasFMStore('data/areas.json').listar()
   oco = [Ocorrencia(**d) for d in json.loads(open('data/ocorrencias.json').read())]
   rel = [RelintEstruturado(**d) for d in json.loads(open('data/relints.json').read())]
   fat = [FatorUrbano(**d) for d in json.loads(open('data/fatores_urbanos.json').read())]
   den = [DenunciaDisque(**d) for d in json.loads(open('data/denuncias.json').read())]

   bingos = calcular_bingos_todas_areas(areas, oco, rel, fat, den)
   print('=== RANKING ===')
   for b in bingos:
       print(f'  {b.nome_area}: {b.componentes.score_final:.2f} | camadas: {b.n_camadas_ativas}/4')

   bangu = next(b for b in bingos if 'Bangu' in b.nome_area)
   area_bangu = next(a for a in areas if a.poligono_id == bangu.poligono_fm_id)
   rel_bangu = [r for r in rel if r.poligono_fm_id == bangu.poligono_fm_id]
   oco_bangu = [o for o in oco if o.poligono_fm_id == bangu.poligono_fm_id]

   rec = sugerir_modalidade(bangu, rel_bangu, oco_bangu, efetivo_total=40)
   print(f'\\n=== RECOMENDACAO BANGU (efetivo 40) ===')
   print(f'  Modalidade: {rec.modalidade_principal}')
   print(f'  Viaturas: {rec.n_viaturas} | Motos: {rec.n_motos} | A pe: {rec.n_agentes_a_pe}')
   print(f'  Pontos interceptacao: {len(rec.pontos_intercepcao)}')

   qmd = gerar_qmd(area_bangu, bangu, rec, rel_bangu, [], date.today())
   print(f'\\n=== QMD BANGU ===')
   print(qmd_para_markdown(qmd)[:1500])
   "

2. Verifique se:
   - Bangu tem score > 0.6
   - Modalidade recomendada é 'a_pe' (modus operandi do RELINT é "a pé")
   - Pontos de interceptação >= 2 (vem das rotas de fuga do RELINT)
   - QMD lista rotas a monitorar

3. Reporte os resultados. Se algum critério falhou, indique qual e por quê.

NÃO modifique código ainda. Só relate.
```

---

## PROMPT 2 (após validação de Bangu OK)

```
Tarefa: gerar 1 DOCX completo do Bangu e validar visualmente.

1. RODE:

   python -c "
   import sys, json
   sys.path.insert(0, 'src')
   from area_crud import AreasFMStore
   from score_engine import calcular_bingos_todas_areas
   from recommendation import sugerir_modalidade
   from qmd_generator import gerar_qmd
   from evolution import carregar_snapshots, comparar_evolucao
   from heatmap import gerar_heatmap_temporal, gerar_grafico_evolucao
   from docx_generator import gerar_relatorio_docx
   from schemas import RelintEstruturado, Ocorrencia, DenunciaDisque, FatorUrbano
   from datetime import date

   areas = AreasFMStore('data/areas.json').listar()
   oco = [Ocorrencia(**d) for d in json.loads(open('data/ocorrencias.json').read())]
   rel = [RelintEstruturado(**d) for d in json.loads(open('data/relints.json').read())]
   fat = [FatorUrbano(**d) for d in json.loads(open('data/fatores_urbanos.json').read())]
   den = [DenunciaDisque(**d) for d in json.loads(open('data/denuncias.json').read())]

   bingos = calcular_bingos_todas_areas(areas, oco, rel, fat, den)
   bangu = next(b for b in bingos if 'Bangu' in b.nome_area)
   area = next(a for a in areas if a.poligono_id == bangu.poligono_fm_id)
   rel_a = [r for r in rel if r.poligono_fm_id == area.poligono_id]
   oco_a = [o for o in oco if o.poligono_fm_id == area.poligono_id]

   rec = sugerir_modalidade(bangu, rel_a, oco_a, 40)
   qmd = gerar_qmd(area, bangu, rec, rel_a, [], date.today())
   heat = gerar_heatmap_temporal(oco_a)

   snaps = [s for s in carregar_snapshots() if s.poligono_fm_id == area.poligono_id]
   snaps.sort(key=lambda s: s.data_referencia)
   comp = comparar_evolucao(area.poligono_id, area.nome_area, snaps[0], snaps[-1])
   graf = gerar_grafico_evolucao([comp])

   path = gerar_relatorio_docx(
       area=area, bingo=bangu, recomendacao=rec, qmd=qmd,
       comparativo_evolucao=comp,
       heatmap_temporal_png=heat,
       grafico_evolucao_png=graf,
       output_path='output/relatorio_bangu.docx',
   )
   print(f'DOCX gerado: {path}')
   import os
   print(f'Tamanho: {os.path.getsize(path)} bytes')
   "

2. Confirme: output/relatorio_bangu.docx existe e tem mais de 30 KB.

3. (manual) Abra no Word/LibreOffice e veja se:
   - 8 seções aparecem
   - Tabela de pesos do score mostra RELINT 0.30 > Disque 0.10
   - Pontos de interceptação listados
   - Tabela de evolução mostra queda em Bangu
   - Gráfico de barras aparece

4. Se algo estiver feio, sugira UMA mudança específica no docx_generator.py (não múltiplas) e aplique.
```

---

## PROMPT 3 (após DOCX OK, polimento final)

```
Tarefa: polir UI Streamlit para apresentação. NÃO refactore, só ajustes cosméticos.

1. Abra src/streamlit_app.py e veja a função render_dashboard.
2. Sugira 1 ou 2 ajustes visuais pequenos que melhoram impacto do pitch:
   - Ex: trocar emojis dos KPIs por algo mais profissional
   - Ex: adicionar legenda no mapa explicando cores
   - Ex: destacar a área de maior score com badge

3. Aplique APENAS os ajustes que rendem mais impacto. Se em dúvida, não mude.

4. Reinicie o Streamlit (Ctrl+C no outro terminal, depois `streamlit run src/streamlit_app.py`).

5. Tire screenshots de cada uma das 6 páginas. Salve em output/screenshots/.

6. Atualize PROGRESS.md com tempo gasto em cada bloco.
```
