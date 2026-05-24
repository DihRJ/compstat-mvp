# PASSO A PASSO MVP 3 HORAS

Construção solo do CompStat IA via Claude Code, com starter kit 90% pronto.

## Visão geral do timing

| Fase | Tempo | O que você faz |
|---|---|---|
| **Setup** | 0:00 - 0:20 | Comandos no terminal, sem Claude Code ainda |
| **Subir Streamlit** | 0:20 - 0:40 | Rodar primeiro e validar que funciona |
| **Caso Bangu via Claude Code** | 0:40 - 1:30 | PROMPT 1 |
| **Ajustes de UI** | 1:30 - 2:15 | PROMPT 2 |
| **DOCX + ensaio** | 2:15 - 2:45 | PROMPT 3 + visual check |
| **Buffer** | 2:45 - 3:00 | Screenshots, vídeo curto, prep pitch |

---

## FASE 1 — Setup (0:00 - 0:20)

Abra o terminal. Copie e cole comando por comando.

```bash
# 1. Criar diretório do projeto
cd ~ && mkdir -p compstat_ia && cd compstat_ia

# 2. Descompactar starter kit (assumindo zip em ~/Downloads)
unzip -o ~/Downloads/compstat_mvp_3h.zip -d ./
cp -r compstat_mvp_3h/* . && rm -rf compstat_mvp_3h

# 3. Ambiente Python
python3 -m venv .venv
source .venv/bin/activate

# 4. Instalar dependências (cerca de 90s)
pip install --upgrade pip
pip install -r requirements.txt

# 5. Gerar dados mockados (5 áreas com perfis realistas do Rio)
python -m src.seed_data

# 6. Inicializar storage de áreas com os 5 polígonos seed
python -c "
from src.area_crud import AreasFMStore
from src.schemas import AreaPoligonoFM
import json
store = AreasFMStore('data/areas.json')
seed = json.loads(open('data/areas_iniciais.json').read())
areas = [AreaPoligonoFM(**a) for a in seed]
n = store.criar_em_lote(areas)
print(f'{n} areas inseridas. Total ativas: {store.contar_ativas()}')
"
```

**Critério de pronto:** comando 6 imprime `5 areas inseridas. Total ativas: 5`. Se algo falhou, leia mensagem antes de continuar.

---

## FASE 2 — Subir Streamlit (0:20 - 0:40)

Antes de chamar Claude Code, confirme que a base funciona:

```bash
# 7. Subir Streamlit
streamlit run src/streamlit_app.py
```

Abra `http://localhost:8501` no navegador. Faça este checklist (5 minutos):

- [ ] **Dashboard** carrega com 4 KPIs e mapa com 5 polígonos coloridos
- [ ] **Score / Bingos** mostra 5 áreas com componentes detalhados (Bangu deve ter score mais alto)
- [ ] **Editor de áreas** lista as 5, tem abas Criar/Editar/Excluir
- [ ] **QMD** seleciona Bangu, mostra ordem de serviço com pontos de interceptação
- [ ] **Evolução 90d** mostra Bangu com queda de roubos (~38%)
- [ ] **Gerar DOCX** baixa um .docx que abre no Word/LibreOffice

Se **TUDO funcionar**: você está em 0:40, vai pra Fase 3 (Claude Code).

Se algo quebrar: ler erro no terminal. 90% dos erros são módulo faltando (`pip install <nome>`).

Para parar Streamlit antes de chamar Claude Code: `Ctrl+C` no terminal.

---

## FASE 3 — Caso Bangu via Claude Code (0:40 - 1:30)

Abra um SEGUNDO terminal (Streamlit pode continuar rodando no primeiro).

```bash
# 8. Instalar Claude Code (se ainda não tiver)
npm install -g @anthropic-ai/claude-code

# 9. Entrar no projeto
cd ~/compstat_ia

# 10. Abrir Claude Code
claude
```

Dentro do Claude Code, cole **PROMPT 1** (próxima seção). O Claude vai:
- Ler todos os arquivos do projeto
- Rodar testes do caso Bangu
- Validar que score, modus, rotas e QMD estão corretos
- Gerar 1 DOCX de Bangu real
- Reportar problemas se houver

---

## FASE 4 — Ajustes de UI (1:30 - 2:15)

Com base no que o Claude reportar, cole **PROMPT 2** para ajustes na Streamlit (provavelmente: melhorar layout do QMD, ajustar cores do mapa, etc).

---

## FASE 5 — DOCX + ensaio (2:15 - 2:45)

Cole **PROMPT 3** para gerar DOCX dos 5 polígonos e validar visualmente.

---

## FASE 6 — Buffer (2:45 - 3:00)

- Tirar screenshots das 6 páginas da Streamlit
- Gravar 30s de vídeo (Loom ou QuickTime) navegando pelo Dashboard + QMD + Evolução
- Ler PITCH_TALKING_POINTS.md (próximo arquivo) em voz alta cronometrado

---

## Comandos úteis durante o desenvolvimento

```bash
# Recarregar Streamlit após mudança em código
# (já tem auto-reload, mas se precisar forçar):
# Ctrl+C, depois rodar de novo

# Limpar dados e refazer seed
rm -rf data/*.json output/*
python -m src.seed_data
python -c "from src.area_crud import AreasFMStore; from src.schemas import AreaPoligonoFM; import json; store = AreasFMStore('data/areas.json'); seed = json.loads(open('data/areas_iniciais.json').read()); store.criar_em_lote([AreaPoligonoFM(**a) for a in seed])"

# Rodar teste rápido do score engine
python -c "
import sys; sys.path.insert(0, 'src')
from area_crud import AreasFMStore
from score_engine import calcular_bingos_todas_areas
from schemas import RelintEstruturado, Ocorrencia, DenunciaDisque, FatorUrbano
import json
areas = AreasFMStore('data/areas.json').listar()
oco = [Ocorrencia(**d) for d in json.loads(open('data/ocorrencias.json').read())]
rel = [RelintEstruturado(**d) for d in json.loads(open('data/relints.json').read())]
fat = [FatorUrbano(**d) for d in json.loads(open('data/fatores_urbanos.json').read())]
den = [DenunciaDisque(**d) for d in json.loads(open('data/denuncias.json').read())]
bingos = calcular_bingos_todas_areas(areas, oco, rel, fat, den)
for b in bingos:
    print(f'{b.nome_area}: {b.componentes.score_final:.2f}')
"
```

---

## Se algo der errado

**`ModuleNotFoundError` ao subir Streamlit**:
```bash
pip install <nome do modulo>
```

**Streamlit não abre o navegador**:
Acesse manualmente: `http://localhost:8501`

**Mapa não renderiza**:
```bash
pip install --upgrade streamlit-folium folium
```

**Claude Code está lento**:
- Use `/clear` entre prompts grandes
- Não cole arquivos inteiros, peça pra ele LER

**Você tem 3h e perdeu 1h corrigindo bug**:
- Pule prompts opcionais
- Use o DOCX gerado direto (não precisa ser perfeito)
- Foque em ter 1 caso (Bangu) funcionando end-to-end
