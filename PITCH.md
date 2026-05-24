# PITCH 5 MIN - SOLO

## Estrutura

| Bloco | Tempo | O que mostrar |
|---|---|---|
| Abertura + problema | 0:30 | Slide 1-2 |
| Demo Streamlit | 2:30 | Tela ao vivo |
| Caso Bangu + Evolução | 1:00 | Páginas QMD e Evolução |
| Fechamento | 0:30 | Slide final |
| Sobra para Q&A | 0:30 | – |

---

## 0:00 - 0:30 ABERTURA

> "CompStat IA. Plataforma de inteligência criminal pra Prefeitura do Rio. Sou o Diego."
>
> "Cada relatório de área hoje leva **8 horas** manuais. A equipe cobre 3 a 5 áreas por semana. São 22 áreas prioritárias. **A IA não substitui o analista. Elimina o trabalho mecânico**."

---

## 0:30 - 3:00 DEMO STREAMLIT (mais importante)

### Página 1: Dashboard (30s)

> "5 áreas piloto no mapa. Cores indicam score consolidado. Bangu em vermelho com 0.82, Copacabana laranja, Tijuca verde."

### Página 2: Score / Bingos (40s)

Abra a expansão do Bangu.

> "O score cruza 5 fontes com pesos diferenciados. A **decisão estratégica do MVP**: RELINT do BPM tem peso 0.30, três vezes maior que denúncia anônima do Disque, que tem 0.10. Por quê? RELINT é fonte oficial verificada."
>
> "E aqui o **modus operandi entra no score**: quando o crime confirma o que o RELINT descreveu, ganha bônus adicional. Em Bangu, 80% das ocorrências são 'a pé' como o RELINT previu."

### Página 3: Editor de áreas (20s)

> "CRUD completo. Criar, editar, desativar mantendo histórico, e exclusão permanente com confirmação. Mudou a Prefeitura? Adiciona área nova em 30 segundos."

### Página 4: QMD (40s)

Selecione Bangu, slider 40.

> "QMD: Quadro de Missão Diária. É a **ordem de serviço** que cada base da FM recebe. Olha o que ele traz:"
>
> - "Modalidade recomendada: **a pé** (porque o crime é a pé)"
> - "**Pontos prioritários:** centroide + receptação na Rua São Gonçalo"
> - "**Rotas a monitorar:** calçadão → Cônego Vasconcelos → receptação"
> - "**Modus operandi:** roubos a pé por grupos de 2-3, foco celular, 20h às 23h"

### Página 5: Evolução 90 dias (30s)

> "E aqui o **diferencial pro CompStat**: comparativo antes e depois da atuação. Bangu: roubos caíram 38%. Méier caiu 30%. Copacabana 22%. Tijuca subiu 5% — área que não recebeu reforço, controle natural."

### Página 6: DOCX (20s)

Baixe um já gerado.

> "Tudo isso vai pro DOCX editável. Word, LibreOffice, qualquer um abre. Gestor ajusta antes da reunião do CompStat. 10 minutos, não 8 horas."

---

## 3:00 - 4:00 CASO BANGU + IMPACTO

Volte ao Slide do Bangu (ou mantenha QMD aberto).

> "Antes: 70 roubos noturnos. RELINT do 14 BPM falava do modus, mas era texto solto. Fatores urbanos da subprefeitura (vegetação encobrindo iluminação) ficavam em outra planilha. Disque tinha menções, mas anônimas."
>
> "Depois do cruzamento: score 0.82, modalidade 'a pé', 2 pontos de interceptação na rota de fuga, **ação para Comlurb podar e Rioluz consertar luz**, e queda de 38% em 90 dias."

---

## 4:00 - 4:30 FECHAMENTO

> "30x mais rápido. 5 áreas viraram protocolo, escala pras 22 oficiais. Sistema editável: outras cidades plugam. Sem chamadas Claude no MVP, mas a IA entra na sugestão de QMD textual e padrões do Disque no próximo ciclo."
>
> "**O CompStat municipal não substitui as polícias. Faz o que cabe à Prefeitura: ordenar a cidade**. Obrigado."

---

## Perguntas prováveis

**"Por que RELINT tem peso 3x maior?"**
> Fonte oficial, com autor identificado, validada. Disque é anônima. Não dá pra dar mesmo peso. Mas mantemos Disque no cruzamento porque volume gera padrão.

**"E se a área não tiver RELINT?"**
> Score cai naturalmente porque RELINT é 30% do peso. O sistema vai recomendar **gerar RELINT** como ação prioritária para aquela área.

**"Como você sabe que caiu 38%?"**
> Pra esse MVP, os snapshots são simulados com lógica realista. Em produção, vem do mesmo banco de ocorrências, comparando janelas de 90 dias.

**"O QMD substitui o briefing do comandante?"**
> Não. Alimenta. O comandante recebe o QMD, valida, ajusta. Decisão final é dele.

**"Funciona em São Pedro da Aldeia?"**
> Funciona. Plugue novos polígonos via CRUD, carregue ocorrências da sua cidade, ajuste pesos no `schemas.ComponentesScore`. Mesma arquitetura.

---

## Checklist 30 min antes do pitch

- [ ] Bateria > 60%
- [ ] Streamlit rodando localhost:8501
- [ ] DOCX de Bangu aberto em aba do Word
- [ ] Slides em modo apresentação testado
- [ ] Cronômetro de 5 min no celular
- [ ] Água + bala mentolada
- [ ] Respirar 3 vezes fundo
