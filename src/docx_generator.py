"""
Gerador de Relatório Analítico de Área em DOCX EDITÁVEL.

Não usa template separado (mais simples para MVP). Gera o documento
inteiramente em código, com python-docx puro. Resultado é .docx que
abre no Word/LibreOffice e pode ser editado.
"""

import io
from pathlib import Path
from datetime import datetime
from typing import Optional

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL

from schemas import (
    AreaPoligonoFM,
    BingoArea,
    RecomendacaoModalidade,
    QMD,
    ComparativoEvolucao,
    PadraoDisqueDenuncia,
    AcaoRecomendada,
)


# ============================================================
# CORES PADRÃO
# ============================================================

COR_TITULO = RGBColor(0x1E, 0x27, 0x61)
COR_DESTAQUE = RGBColor(0xC6, 0x28, 0x28)
COR_OK = RGBColor(0x2E, 0x7D, 0x32)


# ============================================================
# GERAÇÃO PRINCIPAL
# ============================================================

def gerar_relatorio_docx(
    area: AreaPoligonoFM,
    bingo: BingoArea,
    recomendacao: RecomendacaoModalidade,
    qmd: QMD,
    comparativo_evolucao: Optional[ComparativoEvolucao] = None,
    padroes_disque: Optional[list[PadraoDisqueDenuncia]] = None,
    acoes_outros_orgaos: Optional[list[AcaoRecomendada]] = None,
    heatmap_temporal_png: Optional[bytes] = None,
    grafico_evolucao_png: Optional[bytes] = None,
    output_path: str = "output/relatorio.docx",
) -> str:
    """
    Monta DOCX completo. Retorna path do arquivo gerado.

    O documento é totalmente editável no Word/LibreOffice após gerado.
    """
    doc = Document()

    # ----- estilos basicos -----
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    # ----- TITULO -----
    titulo = doc.add_heading(f"Relatorio Analitico de Area", level=0)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER

    subtitulo = doc.add_paragraph()
    subtitulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitulo.add_run(area.nome_area.upper())
    run.bold = True
    run.font.size = Pt(16)
    run.font.color.rgb = COR_TITULO

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(
        f"CompStat Municipal | Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    ).italic = True

    doc.add_paragraph()

    # ----- 1. IDENTIFICACAO -----
    doc.add_heading("1. Identificacao da area", level=1)
    table = doc.add_table(rows=8, cols=2)
    table.style = "Light Grid"
    items = [
        ("Area FM", area.nome_area),
        ("AISP", area.aisp),
        ("Bairros", ", ".join(area.bairros)),
        ("Base FM", area.base_fm),
        ("Subprefeitura", area.subprefeitura),
        ("DP", area.dp or "-"),
        ("BPM", area.bpm or "-"),
        ("Status", "Ativa" if area.ativo else "Inativa"),
    ]
    for i, (rotulo, valor) in enumerate(items):
        table.rows[i].cells[0].text = rotulo
        table.rows[i].cells[1].text = str(valor)
        # bold no rótulo
        for run in table.rows[i].cells[0].paragraphs[0].runs:
            run.bold = True

    doc.add_paragraph()

    # ----- 2. SCORE / BINGO -----
    doc.add_heading("2. Score de risco (Bingo)", level=1)

    p = doc.add_paragraph()
    p.add_run("Score final: ").bold = True
    run_score = p.add_run(f"{bingo.componentes.score_final:.2f}")
    run_score.bold = True
    run_score.font.size = Pt(14)
    run_score.font.color.rgb = COR_DESTAQUE if bingo.componentes.score_final > 0.5 else COR_TITULO

    doc.add_paragraph(bingo.justificativa)

    # Tabela de componentes (mostra pesos diferenciados)
    doc.add_heading("Composicao do score (pesos diferenciados)", level=2)
    comp_table = doc.add_table(rows=6, cols=4)
    comp_table.style = "Light Grid"
    comp_header = comp_table.rows[0].cells
    comp_header[0].text = "Fonte"
    comp_header[1].text = "Score normalizado"
    comp_header[2].text = "Peso"
    comp_header[3].text = "Contribuicao"
    for c in comp_header:
        for run in c.paragraphs[0].runs:
            run.bold = True

    componentes_data = [
        ("Mancha criminal (oficial)",
         bingo.componentes.score_mancha,
         bingo.componentes.peso_mancha),
        ("RELINT (oficial qualitativo)",
         bingo.componentes.score_relint,
         bingo.componentes.peso_relint),
        ("Fator urbano",
         bingo.componentes.score_fator,
         bingo.componentes.peso_fator),
        ("Disque Denuncia (anonimo)",
         bingo.componentes.score_disque,
         bingo.componentes.peso_disque),
        ("Modus operandi + rotas",
         bingo.componentes.score_modus_rota,
         bingo.componentes.peso_modus),
    ]
    for i, (fonte, score, peso) in enumerate(componentes_data, 1):
        row = comp_table.rows[i].cells
        row[0].text = fonte
        row[1].text = f"{score:.2f}"
        row[2].text = f"{peso:.2f}"
        row[3].text = f"{score * peso:.3f}"

    if bingo.componentes.bonus_faccional > 1.0:
        p_bonus = doc.add_paragraph()
        run = p_bonus.add_run(
            f"Bonus faccional aplicado: x{bingo.componentes.bonus_faccional:.2f} "
            f"(faccoes: {', '.join(bingo.faccoes_envolvidas)})"
        )
        run.italic = True
        run.font.color.rgb = COR_DESTAQUE

    # ----- 3. HEATMAP TEMPORAL -----
    if heatmap_temporal_png:
        doc.add_heading("3. Distribuicao temporal", level=1)
        img_stream = io.BytesIO(heatmap_temporal_png)
        doc.add_picture(img_stream, width=Inches(6.5))

    # ----- 4. RECOMENDACAO DE MODALIDADE FM -----
    doc.add_heading("4. Recomendacao de patrulhamento", level=1)
    doc.add_paragraph(recomendacao.justificativa)

    mod_table = doc.add_table(rows=4, cols=2)
    mod_table.style = "Light Grid"
    mod_data = [
        ("Modalidade principal", recomendacao.modalidade_principal),
        ("Viaturas", str(recomendacao.n_viaturas)),
        ("Motos", str(recomendacao.n_motos)),
        ("Agentes a pe", str(recomendacao.n_agentes_a_pe)),
    ]
    for i, (rotulo, valor) in enumerate(mod_data):
        mod_table.rows[i].cells[0].text = rotulo
        mod_table.rows[i].cells[1].text = valor
        for run in mod_table.rows[i].cells[0].paragraphs[0].runs:
            run.bold = True

    if recomendacao.pontos_intercepcao:
        doc.add_heading("Pontos de interceptacao sugeridos", level=2)
        for i, p in enumerate(recomendacao.pontos_intercepcao, 1):
            doc.add_paragraph(
                f"{i}. ({p.lat:.5f}, {p.lng:.5f}) - {p.descricao or 'sem descricao'}",
                style="List Number",
            )

    # ----- 5. QMD -----
    doc.add_heading("5. Quadro de Missao Diaria (QMD)", level=1)
    doc.add_paragraph(
        f"Data de referencia: {qmd.data_referencia.isoformat()} | "
        f"Horario: {qmd.horario_cobertura} | "
        f"Dias: {', '.join(qmd.dias_cobertura)}"
    )
    p = doc.add_paragraph()
    p.add_run("Modus operandi de atencao: ").bold = True
    p.add_run(qmd.modus_operandi_atencao)

    doc.add_heading("Pontos prioritarios", level=2)
    for i, p in enumerate(qmd.pontos_prioritarios, 1):
        doc.add_paragraph(
            f"{i}. ({p.lat:.5f}, {p.lng:.5f}) - {p.descricao or '-'}",
            style="List Number",
        )

    if qmd.rotas_monitorar:
        doc.add_heading("Rotas de fuga a monitorar", level=2)
        for r in qmd.rotas_monitorar:
            doc.add_paragraph(r, style="List Bullet")

    # ----- 6. EVOLUCAO 90 DIAS -----
    if comparativo_evolucao:
        doc.add_heading("6. Evolucao apos atuacao da FM (90 dias)", level=1)
        p = doc.add_paragraph()
        p.add_run("Classificacao: ").bold = True
        run = p.add_run(comparativo_evolucao.classificacao.upper())
        run.bold = True
        if "melhora" in comparativo_evolucao.classificacao:
            run.font.color.rgb = COR_OK
        elif "piora" in comparativo_evolucao.classificacao:
            run.font.color.rgb = COR_DESTAQUE

        evo_table = doc.add_table(rows=4, cols=3)
        evo_table.style = "Light Grid"
        evo_table.rows[0].cells[0].text = "Indicador"
        evo_table.rows[0].cells[1].text = f"Antes ({comparativo_evolucao.snapshot_antes.data_referencia.isoformat()})"
        evo_table.rows[0].cells[2].text = f"Depois ({comparativo_evolucao.snapshot_depois.data_referencia.isoformat()})"

        evo_data = [
            ("Roubos", comparativo_evolucao.snapshot_antes.total_roubos,
             comparativo_evolucao.snapshot_depois.total_roubos),
            ("Furtos", comparativo_evolucao.snapshot_antes.total_furtos,
             comparativo_evolucao.snapshot_depois.total_furtos),
            ("Score medio", comparativo_evolucao.snapshot_antes.score_medio,
             comparativo_evolucao.snapshot_depois.score_medio),
        ]
        for i, (label, antes_v, depois_v) in enumerate(evo_data, 1):
            evo_table.rows[i].cells[0].text = label
            evo_table.rows[i].cells[1].text = str(antes_v)
            evo_table.rows[i].cells[2].text = str(depois_v)

        doc.add_paragraph()
        doc.add_paragraph(comparativo_evolucao.observacao)

        if grafico_evolucao_png:
            img_stream = io.BytesIO(grafico_evolucao_png)
            doc.add_picture(img_stream, width=Inches(6.5))

    # ----- 7. PADROES DISQUE -----
    if padroes_disque:
        doc.add_heading("7. Padroes detectados no Disque Denuncia", level=1)
        for p in padroes_disque:
            doc.add_heading(
                f"[{p.relevancia.upper()}] {p.tipo_padrao}", level=2
            )
            doc.add_paragraph(p.descricao)
            doc.add_paragraph(
                f"Baseado em {p.n_denuncias} denuncias. Confianca: media.",
                style="Intense Quote",
            )

    # ----- 8. APOIO INTERINSTITUCIONAL -----
    if acoes_outros_orgaos:
        doc.add_heading("8. Acoes de apoio (outros orgaos)", level=1)
        for acao in acoes_outros_orgaos:
            p = doc.add_paragraph()
            p.add_run(f"[{acao.orgao_responsavel}] ").bold = True
            p.add_run(f"({acao.prioridade}, prazo {acao.prazo_sugerido_dias} dias) ")
            p.add_run(acao.descricao_acao)
            p.add_run(f"  [ID: {acao.acao_id}]").italic = True

    # ----- FOOTER -----
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(
        "Documento gerado pela plataforma CompStat IA. "
        "Editavel para ajuste antes da reuniao."
    )
    run.italic = True
    run.font.size = Pt(9)

    # Save
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)
    return output_path
