"""Geração de relatórios em PDF usando ReportLab."""

from datetime import datetime
from io import BytesIO

from reportlab.graphics.charts.barcharts import HorizontalBarChart, VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Largura útil da página A4 com margens de 2 cm
_PAGE_W = A4[0] - 4 * cm  # ≈ 481.9 pt

# ── Paleta base
_VERDE = colors.HexColor("#28965A")
_VERDE_CLARO = colors.HexColor("#f0fdf4")
_VERMELHO = colors.HexColor("#991b1b")
_VERM_CLARO = colors.HexColor("#fef2f2")
_AMARELO = colors.HexColor("#92400e")
_AMAR_CLARO = colors.HexColor("#fffbeb")
_CINZA_CLARO = colors.HexColor("#f8fafc")
_AZUL = colors.HexColor("#1d4ed8")
_AZUL_CLARO = colors.HexColor("#eff6ff")
_HEADER_BG = colors.HexColor("#1e293b")
_SUBHDR_BG = colors.HexColor("#334155")
_LINHA_ALT = colors.HexColor("#f1f5f9")
_TEXTO = colors.HexColor("#1e293b")
_CINZA_TEXTO = colors.HexColor("#475569")

# ── Cores vivas para gráficos
_VERDE_G = colors.HexColor("#22c55e")
_VERM_G = colors.HexColor("#ef4444")
_AMAR_G = colors.HexColor("#f59e0b")
_CINZA_G = colors.HexColor("#94a3b8")

_CORES_STATUS_G = {
    "conforme": _VERDE_G,
    "nao_conforme": _VERM_G,
    "em_andamento": _AMAR_G,
    "nao_se_aplica": _CINZA_G,
}

# Ordem de exibição dos controles no relatório (pior situação primeiro)
_STATUS_PRIORIDADE = {
    "nao_conforme": 0,
    "em_andamento": 1,
    "conforme": 2,
    "nao_se_aplica": 3,
}

# Ordem de exibição das mudanças no comparativo
_DELTA_PRIORIDADE = {"↓ Piorou": 0, "— Novo": 1, "↑ Melhorou": 2, "= Igual": 3}

_STATUS_BG = {
    "Conforme": _VERDE_CLARO,
    "Não Conforme": _VERM_CLARO,
    "Em Andamento": _AMAR_CLARO,
    "Não se Aplica": _CINZA_CLARO,
}
_STATUS_FG = {
    "Conforme": _VERDE,
    "Não Conforme": _VERMELHO,
    "Em Andamento": _AMARELO,
    "Não se Aplica": _CINZA_TEXTO,
}
_DELTA_BG = {
    "↑ Melhorou": _VERDE_CLARO,
    "↓ Piorou": _VERM_CLARO,
    "— Novo": _AZUL_CLARO,
}
_DELTA_FG = {
    "↑ Melhorou": _VERDE,
    "↓ Piorou": _VERMELHO,
    "— Novo": _AZUL,
}


# ── Estilos de texto
def _st(name, **kw) -> ParagraphStyle:
    return ParagraphStyle(name, **kw)


_TITLE = _st(
    "psi_title",
    fontSize=18,
    textColor=colors.white,
    leading=22,
    alignment=TA_LEFT,
    fontName="Helvetica-Bold",
)
_SUB = _st(
    "psi_sub", fontSize=10, textColor=colors.white, leading=14, alignment=TA_LEFT
)
_H2 = _st(
    "psi_h2",
    fontSize=12,
    textColor=_TEXTO,
    leading=16,
    spaceBefore=12,
    spaceAfter=4,
    fontName="Helvetica-Bold",
)
_BODY = _st("psi_body", fontSize=9, textColor=_TEXTO, leading=13)
_META = _st("psi_meta", fontSize=9, textColor=_CINZA_TEXTO, leading=13)
_FOOTER = _st(
    "psi_footer", fontSize=8, textColor=_CINZA_TEXTO, alignment=TA_RIGHT, leading=10
)
_CELL = _st("psi_cell", fontSize=8, textColor=_TEXTO, leading=11, wordWrap="CJK")
_ALERTA_HDR = _st(
    "psi_alerta_hdr",
    fontSize=10,
    textColor=_VERMELHO,
    leading=14,
    fontName="Helvetica-Bold",
    spaceAfter=3,
)
_ALERTA_ITEM = _st(
    "psi_alerta_item", fontSize=8, textColor=_VERMELHO, leading=11, leftIndent=8
)
_INSIGHT = _st("psi_insight", fontSize=9, textColor=_AMARELO, leading=12, spaceAfter=2)
_LEGENDA = _st("psi_legenda", fontSize=7, textColor=_TEXTO, leading=10)
_LEGENDA_SM = _st("psi_legenda_sm", fontSize=7, textColor=_CINZA_TEXTO, leading=10)


# ── Gráficos


def _grafico_pizza(contagem: dict, raio: float = 68) -> Drawing:
    """Pizza de distribuição de status (sem labels embutidos)."""
    ORDEM = ["nao_conforme", "em_andamento", "conforme", "nao_se_aplica"]
    pares = [(k, contagem.get(k, 0)) for k in ORDEM if contagem.get(k, 0) > 0]
    largura = raio * 2 + 20
    altura = raio * 2 + 20
    d = Drawing(largura, altura)
    if not pares:
        return d

    pie = Pie()
    pie.x = 10
    pie.y = 10
    pie.width = raio * 2
    pie.height = raio * 2
    pie.data = [v for _, v in pares]
    pie.labels = [""] * len(pares)
    pie.slices.strokeColor = colors.white
    pie.slices.strokeWidth = 2

    for i, (k, _) in enumerate(pares):
        pie.slices[i].fillColor = _CORES_STATUS_G[k]

    d.add(pie)
    return d


def _legenda_status(contagem: dict) -> Table:
    """Tabela de legenda colorida para o gráfico de pizza."""
    ORDEM = ["nao_conforme", "em_andamento", "conforme", "nao_se_aplica"]
    LABELS = {
        "conforme": "Conforme",
        "nao_conforme": "Não Conforme",
        "em_andamento": "Em Andamento",
        "nao_se_aplica": "Não se Aplica",
    }
    total = sum(contagem.get(k, 0) for k in ORDEM)
    dados = []
    cmds = []
    row_idx = 0
    for k in ORDEM:
        v = contagem.get(k, 0)
        if v == 0:
            continue
        pct = round(v / total * 100, 1) if total else 0
        dados.append(
            [
                "",
                Paragraph(LABELS[k], _LEGENDA),
                Paragraph(f"{v}  ({pct}%)", _LEGENDA_SM),
            ]
        )
        cmds.append(("BACKGROUND", (0, row_idx), (0, row_idx), _CORES_STATUS_G[k]))
        row_idx += 1

    if not dados:
        return Table([[""]])

    t = Table(dados, colWidths=[10, 100, 50])
    cmds += [
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (1, 0), (-1, -1), [colors.white, _LINHA_ALT]),
    ]
    t.setStyle(TableStyle(cmds))
    return t


def _grafico_barras_v(
    labels: list[str], valores: list[float], largura: float = 480, altura: float = 130
) -> Drawing:
    """Barras verticais: evolução da conformidade geral por auditoria."""
    if not valores:
        return Drawing(largura, altura)

    d = Drawing(largura, altura)

    bc = VerticalBarChart()
    bc.x = 35
    bc.y = 25
    bc.width = largura - 55
    bc.height = altura - 45

    bc.data = [valores]
    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.fontSize = 7

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 100
    bc.valueAxis.valueStep = 20
    bc.valueAxis.labels.fontSize = 7

    bc.bars[0].fillColor = _VERDE_G
    bc.bars[0].strokeColor = None

    for i, v in enumerate(valores):
        cor = _VERM_G if v < 50 else (_AMAR_G if v < 75 else _VERDE_G)
        bc.bars[(0, i)].fillColor = cor

    d.add(bc)
    d.add(
        String(
            bc.x + bc.width / 2,
            altura - 8,
            "Evolução da Conformidade Geral (%)",
            fontSize=8,
            fillColor=_TEXTO,
            textAnchor="middle",
        )
    )
    return d


def _grafico_comparativo(
    temas: list[str],
    vals_base: list[float],
    vals_atual: list[float],
    largura: float = 480,
    altura: float = 145,
) -> Drawing:
    """Barras agrupadas: base (cinza) vs atual (verde) por tipo de controle."""
    if not temas:
        return Drawing(largura, altura)

    d = Drawing(largura, altura)

    bc = VerticalBarChart()
    bc.x = 35
    bc.y = 35
    bc.width = largura - 55
    bc.height = altura - 55

    bc.data = [vals_base, vals_atual]
    bc.categoryAxis.categoryNames = [t[:14] for t in temas]
    bc.categoryAxis.labels.fontSize = 6
    bc.categoryAxis.labels.angle = 30
    bc.categoryAxis.labels.boxAnchor = "ne"
    bc.categoryAxis.labels.dx = -4

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 100
    bc.valueAxis.valueStep = 25
    bc.valueAxis.labels.fontSize = 7

    bc.bars[0].fillColor = _CINZA_G
    bc.bars[0].strokeColor = None
    bc.bars[1].fillColor = _VERDE_G
    bc.bars[1].strokeColor = None

    d.add(bc)
    d.add(
        String(
            bc.x + bc.width / 2,
            altura - 8,
            "Base (cinza) vs Atual (verde) por Tipo de Controle (%)",
            fontSize=8,
            fillColor=_TEXTO,
            textAnchor="middle",
        )
    )
    return d


# ── Bloco de atenção executiva

# ── Helpers de layout


def _hdr_table(texto_esq: str, texto_dir: str = "") -> Table:
    t = Table(
        [[Paragraph(texto_esq, _TITLE), Paragraph(texto_dir, _SUB)]],
        colWidths=["70%", "30%"],
    )
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _HEADER_BG),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ]
        )
    )
    return t


def _meta_table(pares: list[tuple[str, str]]) -> Table:
    dados = [[Paragraph(k, _META), Paragraph(v, _BODY)] for k, v in pares]
    t = Table(dados, colWidths=["30%", "70%"])
    t.setStyle(
        TableStyle(
            [
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def _section(titulo: str) -> list:
    return [
        Spacer(1, 0.3 * cm),
        Paragraph(titulo, _H2),
        HRFlowable(width="100%", thickness=0.5, color=_VERDE),
    ]


def _tabela_dados(
    cabecalho: list[str],
    linhas: list[list],
    col_widths: list | None = None,
    status_col: int | None = None,
    delta_col: int | None = None,
) -> Table:
    cabecalho_styled = [
        Paragraph(
            c,
            _st(
                f"hdr_{i}",
                fontSize=8,
                textColor=colors.white,
                fontName="Helvetica-Bold",
                alignment=TA_CENTER,
                leading=10,
            ),
        )
        for i, c in enumerate(cabecalho)
    ]
    dados = [cabecalho_styled]
    for row in linhas:
        dados.append([Paragraph(str(cell), _CELL) for cell in row])

    t = Table(dados, colWidths=col_widths, repeatRows=1)

    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), _SUBHDR_BG),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _LINHA_ALT]),
    ]

    if status_col is not None:
        for r_idx, row in enumerate(linhas):
            val = str(row[status_col]) if status_col < len(row) else ""
            bg = _STATUS_BG.get(val)
            fg = _STATUS_FG.get(val)
            if bg:
                style_cmds.append(
                    ("BACKGROUND", (status_col, r_idx + 1), (status_col, r_idx + 1), bg)
                )
            if fg:
                style_cmds.append(
                    ("TEXTCOLOR", (status_col, r_idx + 1), (status_col, r_idx + 1), fg)
                )

    if delta_col is not None:
        for r_idx, row in enumerate(linhas):
            val = str(row[delta_col]) if delta_col < len(row) else ""
            bg = _DELTA_BG.get(val)
            fg = _DELTA_FG.get(val)
            if bg:
                style_cmds.append(
                    ("BACKGROUND", (delta_col, r_idx + 1), (delta_col, r_idx + 1), bg)
                )
            if fg:
                style_cmds.append(
                    ("TEXTCOLOR", (delta_col, r_idx + 1), (delta_col, r_idx + 1), fg)
                )

    t.setStyle(TableStyle(style_cmds))
    return t


def _metricas_table(metricas: list[tuple[str, str]]) -> Table:
    dados = [
        [
            Paragraph(
                v,
                _st(
                    f"mv{i}",
                    fontSize=18,
                    fontName="Helvetica-Bold",
                    textColor=_VERDE if i == 0 else _TEXTO,
                    alignment=TA_CENTER,
                    leading=22,
                ),
            )
            for i, (_, v) in enumerate(metricas)
        ],
        [
            Paragraph(
                k,
                _st(
                    f"mk{i}",
                    fontSize=8,
                    textColor=_CINZA_TEXTO,
                    alignment=TA_CENTER,
                    leading=10,
                ),
            )
            for i, (k, _) in enumerate(metricas)
        ],
    ]
    t = Table(dados, colWidths=[f"{100 // len(metricas)}%" for _ in metricas])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _CINZA_CLARO),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
            ]
        )
    )
    return t


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(_CINZA_TEXTO)
    canvas.drawRightString(
        A4[0] - 2 * cm,
        1.2 * cm,
        f"PSI — Sistema de Conformidade  ·  Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}  ·  Pág. {doc.page}",
    )
    canvas.restoreState()


# ── API pública


def gerar_pdf_auditoria(
    empresa: dict,
    auditoria: dict,
    stats: dict,
    respostas: list[dict],
    tema_filtro: str | None = None,
) -> bytes:
    """
    Gera PDF de relatório de conformidade de uma auditoria.

    empresa   : dict com nome, cnpj, setor, porte, responsavel
    auditoria : dict do get_auditorias() enriquecido
    stats     : saída de calcular_stats(respostas)
    respostas : lista de respostas da auditoria (com controle_nome, tema_nome)
    tema_filtro : se fornecido, filtra controles por tema_id
    """
    from utils.analytics import STATUS_LABEL

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    data_inicio = auditoria["data_inicio"][:10]
    status_txt = (
        "Concluída" if auditoria.get("status") == "concluida" else "Em Andamento"
    )
    norma = auditoria.get("modulo", "—")
    titulo_rel = "Relatório de Conformidade"
    if tema_filtro:
        temas_map = {
            r["tema_id"]: r.get("tema_nome") or r["tema_id"] for r in respostas
        }
        titulo_rel = f"Relatório — {temas_map.get(tema_filtro, tema_filtro)}"

    story = []

    # Cabeçalho
    story.append(_hdr_table(titulo_rel, f"{norma}  ·  {data_inicio}"))
    story.append(Spacer(1, 0.4 * cm))

    # Identificação
    story += _section("Identificação")
    story.append(
        _meta_table(
            [
                ("Empresa", empresa.get("nome", "—")),
                ("CNPJ", empresa.get("cnpj") or "—"),
                ("Setor", empresa.get("setor") or "—"),
                ("Porte", empresa.get("porte") or "—"),
                ("Responsável", empresa.get("responsavel") or "—"),
            ]
        )
    )
    story.append(Spacer(1, 0.2 * cm))
    story.append(
        _meta_table(
            [
                ("Norma", norma),
                ("Início", auditoria["data_inicio"][:10]),
                (
                    "Fim",
                    auditoria["data_fim"][:10] if auditoria.get("data_fim") else "—",
                ),
                ("Status", status_txt),
                (
                    "Respondidos",
                    f"{auditoria['total_respostas']}/{auditoria['total_controles']} controles",
                ),
            ]
        )
    )

    # Conformidade geral — métricas + gráficos
    story += _section("Conformidade Geral")
    cnt = stats["contagem"]
    story.append(
        _metricas_table(
            [
                ("Conformidade Geral", f"{stats['pct_geral']}%"),
                ("Conformes", str(cnt.get("conforme", 0))),
                ("Não Conformes", str(cnt.get("nao_conforme", 0))),
                ("Em Andamento", str(cnt.get("em_andamento", 0))),
                ("Não se Aplica", str(cnt.get("nao_se_aplica", 0))),
            ]
        )
    )
    story.append(Spacer(1, 0.3 * cm))

    # Gráficos: pizza + legenda | barras por tema
    temas_src = stats["temas"]
    pie_d = _grafico_pizza(cnt, raio=68)
    leg_t = _legenda_status(cnt)

    # coluna esquerda: pizza sobre legenda
    col_esq = Table([[pie_d], [leg_t]], colWidths=[210])
    col_esq.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    graficos = Table([[col_esq]], colWidths=[215, 265])
    graficos.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(graficos)
    story.append(Spacer(1, 0.3 * cm))

    # Tabela por tipo de controle — pior primeiro
    story += _section("Conformidade por Tipo de Controle")
    linhas_tema = [
        [
            t["nome"],
            t["aplicaveis"],
            t["conformes"],
            t["nao_conformes"],
            t["em_andamento"],
            t["nao_se_aplica"],
            f"{t['pct']}%",
        ]
        for t in sorted(temas_src, key=lambda t: t["pct"])
    ]
    story.append(
        _tabela_dados(
            [
                "Tipo de Controle",
                "Aplicáveis",
                "Conformes",
                "Não Conf.",
                "Em And.",
                "N/A",
                "% Conf.",
            ],
            linhas_tema,
            col_widths=["32%", "11%", "11%", "11%", "11%", "8%", "12%"],
        )
    )

    # Detalhamento de controles — Não Conforme → Em Andamento → Conforme → N/A
    story += _section("Detalhamento de Controles")
    resps_src = (
        respostas
        if not tema_filtro
        else [r for r in respostas if r["tema_id"] == tema_filtro]
    )
    resps_ord = sorted(resps_src, key=lambda r: _STATUS_PRIORIDADE.get(r["status"], 99))
    linhas_ctrl = [
        [
            r["controle_id"],
            r.get("controle_nome", r["controle_id"])[:80],
            STATUS_LABEL.get(r["status"], r["status"]),
            (r.get("observacao") or "")[:120],
        ]
        for r in resps_ord
    ]
    story.append(
        _tabela_dados(
            ["Controle", "Nome", "Status", "Observação"],
            linhas_ctrl,
            col_widths=["10%", "30%", "15%", "45%"],
            status_col=2,
        )
    )

    story.append(Spacer(1, 0.5 * cm))
    story.append(
        Paragraph(
            f"Relatório gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
            _FOOTER,
        )
    )

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def gerar_pdf_comparativo(
    empresa: dict,
    aud_base: dict,
    aud_atual: dict,
    stats_base: dict,
    stats_atual: dict,
    resps_base: list[dict],
    resps_atual: list[dict],
) -> bytes:
    """Gera PDF de relatório comparativo entre duas auditorias."""
    from utils.analytics import STATUS_LABEL

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    data_b = (aud_base.get("data_fim") or aud_base["data_inicio"])[:10]
    data_a = (aud_atual.get("data_fim") or aud_atual["data_inicio"])[:10]

    story = []

    story.append(
        _hdr_table(
            "Relatório Comparativo de Conformidade",
            f"#{aud_base['id']} vs #{aud_atual['id']}",
        )
    )
    story.append(Spacer(1, 0.4 * cm))

    # Empresa
    story += _section("Empresa")
    story.append(
        _meta_table(
            [
                ("Nome", empresa.get("nome", "—")),
                ("CNPJ", empresa.get("cnpj") or "—"),
                ("Setor", empresa.get("setor") or "—"),
                ("Responsável", empresa.get("responsavel") or "—"),
            ]
        )
    )

    # Auditorias comparadas
    story += _section("Auditorias Comparadas")
    story.append(
        _tabela_dados(
            ["", "Base", "Atual"],
            [
                ["ID", f"#{aud_base['id']}", f"#{aud_atual['id']}"],
                ["Norma", aud_base.get("modulo", "—"), aud_atual.get("modulo", "—")],
                ["Início", aud_base["data_inicio"][:10], aud_atual["data_inicio"][:10]],
                ["Fim", data_b, data_a],
                [
                    "Status",
                    (
                        "Concluída"
                        if aud_base.get("status") == "concluida"
                        else "Em Andamento"
                    ),
                    (
                        "Concluída"
                        if aud_atual.get("status") == "concluida"
                        else "Em Andamento"
                    ),
                ],
                [
                    "Controles resp.",
                    f"{aud_base['total_respostas']}/{aud_base['total_controles']}",
                    f"{aud_atual['total_respostas']}/{aud_atual['total_controles']}",
                ],
            ],
            col_widths=["25%", "37.5%", "37.5%"],
        )
    )

    # Conformidade geral — métricas + gráfico comparativo
    story += _section("Conformidade Geral")
    pb, pa = stats_base["pct_geral"], stats_atual["pct_geral"]
    delta_g = round(pa - pb, 1)
    sinal = "+" if delta_g >= 0 else ""
    story.append(
        _metricas_table(
            [
                ("Conf. Base", f"{pb}%"),
                ("Conf. Atual", f"{pa}%"),
                ("Variação", f"{sinal}{delta_g} pp"),
                ("Conformes Base", str(stats_base["contagem"].get("conforme", 0))),
                ("Conformes Atual", str(stats_atual["contagem"].get("conforme", 0))),
            ]
        )
    )
    story.append(Spacer(1, 0.3 * cm))

    # Gráfico agrupado base vs atual
    temas_b = {t["nome"]: t for t in stats_base["temas"]}
    temas_a = {t["nome"]: t for t in stats_atual["temas"]}
    todos_temas = sorted(set(temas_b) | set(temas_a))
    if todos_temas:
        story.append(
            _grafico_comparativo(
                todos_temas,
                [temas_b[n]["pct"] if n in temas_b else 0.0 for n in todos_temas],
                [temas_a[n]["pct"] if n in temas_a else 0.0 for n in todos_temas],
            )
        )
        story.append(Spacer(1, 0.3 * cm))

    # Evolução por tipo de controle
    story += _section("Evolução por Tipo de Controle")
    linhas_ev = []
    for nome in todos_temas:
        pb_t = temas_b[nome]["pct"] if nome in temas_b else 0.0
        pa_t = temas_a[nome]["pct"] if nome in temas_a else 0.0
        dif = round(pa_t - pb_t, 1)
        s = "+" if dif >= 0 else ""
        linhas_ev.append([nome, f"{pb_t}%", f"{pa_t}%", f"{s}{dif} pp"])
    story.append(
        _tabela_dados(
            ["Tipo de Controle", "Base", "Atual", "Δ (pp)"],
            linhas_ev,
            col_widths=["46%", "18%", "18%", "18%"],
        )
    )

    # Mudanças por controle — Piorou → Novo → Melhorou → Igual
    story += _section("Mudanças por Controle")
    map_b = {r["controle_id"]: r for r in resps_base}
    map_a = {r["controle_id"]: r for r in resps_atual}
    ordem = {"nao_conforme": 0, "em_andamento": 1, "conforme": 2, "nao_se_aplica": -1}

    def _delta(sb, sa):
        if sb is None:
            return "— Novo"
        if ordem.get(sa, -1) > ordem.get(sb, -1):
            return "↑ Melhorou"
        if ordem.get(sa, -1) < ordem.get(sb, -1):
            return "↓ Piorou"
        return "= Igual"

    todos_cids = sorted(set(map_b) | set(map_a))
    linhas_mud = []
    for cid in todos_cids:
        rb = map_b.get(cid)
        ra = map_a.get(cid)
        s_b = rb["status"] if rb else None
        s_a = ra["status"] if ra else None
        ref = ra or rb or {}
        linhas_mud.append(
            [
                ref.get("tema_nome") or ref.get("tema_id", ""),
                cid,
                (ref.get("controle_nome") or cid)[:60],
                STATUS_LABEL.get(s_b, "—") if s_b else "—",
                STATUS_LABEL.get(s_a, "—") if s_a else "—",
                _delta(s_b, s_a),
            ]
        )

    # Pior situação primeiro
    linhas_mud.sort(key=lambda r: _DELTA_PRIORIDADE.get(r[5], 99))

    story.append(
        _tabela_dados(
            ["Tipo de Controle", "ID", "Nome", "Base", "Atual", "Mudança"],
            linhas_mud,
            col_widths=["22%", "8%", "28%", "13%", "13%", "13%"],
            status_col=3,
            delta_col=5,
        )
    )

    story.append(Spacer(1, 0.5 * cm))
    story.append(
        Paragraph(
            f"Relatório gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
            _FOOTER,
        )
    )

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def gerar_pdf_evolucao(
    empresa: dict,
    auds_com_stats: list[tuple[dict, dict]],
) -> bytes:
    """
    Gera PDF de evolução temporal com N auditorias.

    auds_com_stats: lista de (auditoria_dict, stats_dict) em ordem cronológica.
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    story = []
    story.append(
        _hdr_table(
            "Relatório de Evolução de Conformidade",
            empresa.get("nome", ""),
        )
    )
    story.append(Spacer(1, 0.4 * cm))

    story += _section("Empresa")
    story.append(
        _meta_table(
            [
                ("Nome", empresa.get("nome", "—")),
                ("CNPJ", empresa.get("cnpj") or "—"),
                ("Setor", empresa.get("setor") or "—"),
                ("Responsável", empresa.get("responsavel") or "—"),
            ]
        )
    )

    # Tabela resumo + gráfico de evolução
    story += _section("Evolução Geral")
    linhas_ev = []
    for a, st in auds_com_stats:
        data = (a.get("data_fim") or a["data_inicio"])[:10]
        linhas_ev.append(
            [
                f"#{a['id']}",
                a.get("modulo", "—"),
                a["data_inicio"][:10],
                data,
                "Concluída" if a.get("status") == "concluida" else "Em Andamento",
                f"{a['total_respostas']}/{a['total_controles']}",
                f"{st['pct_geral']}%",
            ]
        )
    story.append(
        _tabela_dados(
            ["ID", "Norma", "Início", "Referência", "Status", "Respondidos", "% Conf."],
            linhas_ev,
            col_widths=["7%", "18%", "13%", "13%", "16%", "15%", "12%"],
        )
    )
    story.append(Spacer(1, 0.3 * cm))

    # Gráfico de barras: evolução da conformidade geral
    labels_ev = [
        f"#{a['id']}\n{(a.get('data_fim') or a['data_inicio'])[:7]}"
        for a, _ in auds_com_stats
    ]
    valores_ev = [st["pct_geral"] for _, st in auds_com_stats]
    story.append(_grafico_barras_v(labels_ev, valores_ev, largura=480, altura=130))
    story.append(Spacer(1, 0.3 * cm))

    # Evolução por tema
    story += _section("Evolução por Tipo de Controle")
    todos_temas: list[str] = []
    for _, st in auds_com_stats:
        for t in st["temas"]:
            if t["nome"] not in todos_temas:
                todos_temas.append(t["nome"])

    cabecalho = ["Tipo de Controle"] + [f"#{a['id']}" for a, _ in auds_com_stats]
    linhas_t: list[list] = []
    for nome in todos_temas:
        row = [nome]
        for _, st in auds_com_stats:
            t_map = {t["nome"]: t["pct"] for t in st["temas"]}
            row.append(f"{t_map.get(nome, 0.0)}%")
        linhas_t.append(row)

    n_aud = len(auds_com_stats)
    pct = 100 // (n_aud + 1)
    col_w = [f"{100 - n_aud * pct}%"] + [f"{pct}%" for _ in auds_com_stats]
    story.append(_tabela_dados(cabecalho, linhas_t, col_widths=col_w))

    story.append(Spacer(1, 0.5 * cm))
    story.append(
        Paragraph(
            f"Relatório gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
            _FOOTER,
        )
    )

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
