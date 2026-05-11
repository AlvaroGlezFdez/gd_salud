"""Convierte memoria_proyecto.md → memoria_proyecto.pdf con reportlab.

Estilo limpio, tipografía profesional, A4, márgenes ajustados para mantener
el documento en ≤ 10 caras. No requiere LaTeX (las fórmulas se renderizan
como texto en cursiva centrado).
"""
import os
import re
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table,
    TableStyle,
)

SRC = 'memoria_proyecto.md'
DST = 'memoria_proyecto.pdf'

# ── Paleta y estilos ────────────────────────────────────────────────────────
NAVY    = colors.HexColor('#1f4e79')
INK     = colors.HexColor('#1c2833')
SLATE   = colors.HexColor('#2c3e50')
MUTED   = colors.HexColor('#566573')
RULE    = colors.HexColor('#bdc3c7')
SOFT_BG = colors.HexColor('#f4f6f7')
CODE_BG = colors.HexColor('#f0f0f0')

styles = getSampleStyleSheet()

H1 = ParagraphStyle(
    'H1', parent=styles['Heading1'],
    fontName='Helvetica-Bold', fontSize=18, leading=22,
    textColor=INK, alignment=TA_CENTER,
    spaceBefore=0, spaceAfter=4,
)
H2_RULE = ParagraphStyle(
    'H2', parent=styles['Heading2'],
    fontName='Helvetica-Bold', fontSize=12.5, leading=15,
    textColor=NAVY, alignment=TA_LEFT,
    spaceBefore=10, spaceAfter=3,
    borderPadding=(0, 0, 2, 0),
    borderColor=RULE, borderWidth=0,
)
H3 = ParagraphStyle(
    'H3', parent=styles['Heading3'],
    fontName='Helvetica-Bold', fontSize=10.5, leading=13,
    textColor=SLATE,
    spaceBefore=6, spaceAfter=2,
)
BODY = ParagraphStyle(
    'Body', parent=styles['Normal'],
    fontName='Helvetica', fontSize=9.5, leading=12.5,
    textColor=INK, alignment=TA_JUSTIFY,
    spaceAfter=4,
)
LIST_ITEM_STYLE = ParagraphStyle(
    'ListItem', parent=BODY,
    leftIndent=0, spaceAfter=1,
)
MATH = ParagraphStyle(
    'Math', parent=BODY,
    fontName='Times-Italic', fontSize=10.5, leading=13,
    alignment=TA_CENTER,
    spaceBefore=4, spaceAfter=6,
    textColor=INK,
)
QUOTE = ParagraphStyle(
    'Quote', parent=BODY,
    leftIndent=14, rightIndent=4,
    fontName='Helvetica', fontSize=9.5, leading=12,
    textColor=MUTED, alignment=TA_LEFT,
    borderPadding=(4, 6, 4, 6),
    backColor=SOFT_BG,
    spaceBefore=4, spaceAfter=6,
)
SUBTITLE = ParagraphStyle(
    'Subtitle', parent=BODY,
    fontName='Helvetica', fontSize=11, leading=14,
    alignment=TA_CENTER, textColor=MUTED,
    spaceAfter=10,
)

CELL_STYLE = ParagraphStyle(
    'Cell', parent=BODY, fontName='Helvetica',
    fontSize=8.5, leading=10.5, alignment=TA_LEFT,
    spaceAfter=0,
)
CELL_HEADER_STYLE = ParagraphStyle(
    'CellH', parent=CELL_STYLE,
    fontName='Helvetica-Bold', textColor=colors.white,
)


# ── Conversor de markdown inline → reportlab markup ────────────────────────
def escape_xml(s: str) -> str:
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def inline(s: str) -> str:
    """Markdown inline → reportlab Paragraph markup."""
    s = escape_xml(s)
    # `code`  →  fuente monoespaciada con fondo gris
    s = re.sub(r'`([^`]+)`',
               r'<font face="Courier" size="9" backColor="#f0f0f0">\1</font>', s)
    # **bold**
    s = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', s)
    # *italic*  (evita capturar dentro de **bold**)
    s = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'<i>\1</i>', s)
    # [text](url)  →  hipervínculo subrayado azul
    s = re.sub(r'\[([^\]]+)\]\(([^)]+)\)',
               r'<link href="\2" color="#1f4e79"><u>\1</u></link>', s)
    return s


# ── Parser de tablas markdown ───────────────────────────────────────────────
def parse_table(tbl_lines):
    rows = []
    for ln in tbl_lines:
        ln = ln.strip()
        if ln.startswith('|'):
            ln = ln[1:]
        if ln.endswith('|'):
            ln = ln[:-1]
        rows.append([c.strip() for c in ln.split('|')])

    # ¿Hay fila separadora "---|---|..."?
    if len(rows) >= 2 and all(set(c.strip()) <= set('-:') for c in rows[1] if c.strip()):
        header, data = rows[0], rows[2:]
    else:
        header, data = rows[0], rows[1:]

    grid = [[Paragraph(inline(c), CELL_HEADER_STYLE) for c in header]]
    for row in data:
        # Pad row if it's shorter than header
        while len(row) < len(header):
            row.append('')
        grid.append([Paragraph(inline(c), CELL_STYLE) for c in row])

    n_cols = len(header)
    avail = 6.5 * inch
    col_w = [avail / n_cols] * n_cols

    tbl = Table(grid, colWidths=col_w, hAlign='LEFT', repeatRows=1)
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('VALIGN',     (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.white, SOFT_BG]),
        ('LINEBELOW', (0, 0), (-1, 0), 0.6, NAVY),
        ('GRID',      (0, 1), (-1, -1), 0.3, RULE),
        ('LEFTPADDING',  (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING',   (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 3),
    ]))
    return [Spacer(1, 2), tbl, Spacer(1, 5)]


# ── Detección de "líneas estructurales" para no meterlas en párrafos ───────
def is_special(line: str) -> bool:
    s = line.lstrip()
    return (
        s.startswith('#') or s.startswith('|') or s.startswith('>')
        or re.match(r'^\s*[-*]\s+', s) is not None
        or re.match(r'^\s*\d+\.\s+', s) is not None
        or s.startswith('$$') or s.startswith('---')
    )


# ── Parser principal ───────────────────────────────────────────────────────
def parse_markdown(text: str):
    flow = []
    lines = text.split('\n')
    i, n = 0, len(lines)

    while i < n:
        line = lines[i].rstrip()

        # blanco
        if not line:
            i += 1
            continue

        # regla horizontal
        if re.match(r'^---+\s*$', line):
            flow.append(Spacer(1, 4))
            i += 1
            continue

        # encabezados
        if line.startswith('# '):
            flow.append(Paragraph(inline(line[2:]), H1))
            i += 1
            continue
        if line.startswith('## '):
            flow.append(Paragraph(inline(line[3:]), H2_RULE))
            i += 1
            continue
        if line.startswith('### '):
            flow.append(Paragraph(inline(line[4:]), H3))
            i += 1
            continue

        # math en bloque (multilínea)
        if line.startswith('$$'):
            buf = [line.removeprefix('$$').removesuffix('$$').strip()]
            if not (line.endswith('$$') and len(line) > 2):
                i += 1
                while i < n and not lines[i].rstrip().endswith('$$'):
                    buf.append(lines[i].strip())
                    i += 1
                if i < n:
                    buf.append(lines[i].rstrip().removesuffix('$$').strip())
            content = ' '.join(b for b in buf if b)
            flow.append(Paragraph(escape_xml(content), MATH))
            i += 1
            continue

        # tabla
        if line.startswith('|'):
            tbl_lines = []
            while i < n and lines[i].lstrip().startswith('|'):
                tbl_lines.append(lines[i])
                i += 1
            flow.extend(parse_table(tbl_lines))
            continue

        # lista con viñetas
        if re.match(r'^\s*[-*]\s+', line):
            items = []
            while i < n and re.match(r'^\s*[-*]\s+', lines[i]):
                content = re.sub(r'^\s*[-*]\s+', '', lines[i])
                items.append(ListItem(
                    Paragraph(inline(content), LIST_ITEM_STYLE),
                    bulletColor=NAVY, leftIndent=12,
                ))
                i += 1
            flow.append(ListFlowable(
                items, bulletType='bullet', leftIndent=14,
                bulletFontName='Helvetica-Bold', bulletFontSize=8,
                spaceAfter=4,
            ))
            continue

        # lista numerada
        if re.match(r'^\s*\d+\.\s+', line):
            items = []
            while i < n and re.match(r'^\s*\d+\.\s+', lines[i]):
                content = re.sub(r'^\s*\d+\.\s+', '', lines[i])
                items.append(ListItem(
                    Paragraph(inline(content), LIST_ITEM_STYLE),
                    leftIndent=14,
                ))
                i += 1
            flow.append(ListFlowable(
                items, bulletType='1', leftIndent=18,
                bulletFontSize=9, spaceAfter=4,
            ))
            continue

        # blockquote (multilínea, soporta líneas con sólo ">")
        if line.startswith('>'):
            buf = []
            while i < n and lines[i].lstrip().startswith('>'):
                content = re.sub(r'^>\s?', '', lines[i])
                buf.append(content)
                i += 1
            text_q = ' '.join(b.strip() for b in buf if b.strip())
            flow.append(Paragraph(inline(text_q), QUOTE))
            continue

        # párrafo (junta líneas hasta blanco o línea especial)
        para_buf = [line]
        i += 1
        while i < n and lines[i].strip() and not is_special(lines[i]):
            para_buf.append(lines[i].rstrip())
            i += 1
        text_p = ' '.join(para_buf)
        flow.append(Paragraph(inline(text_p), BODY))

    return flow


# ── Cabecera y pie de página ───────────────────────────────────────────────
def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 7.5)
    canvas.setFillColor(MUTED)
    # Cabecera
    canvas.drawString(0.7 * inch, A4[1] - 0.4 * inch,
                      'Proyecto Final — Gestión de Datos · UAX')
    canvas.drawRightString(A4[0] - 0.7 * inch, A4[1] - 0.4 * inch,
                           'Álvaro González Fernández')
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.4)
    canvas.line(0.7 * inch, A4[1] - 0.45 * inch,
                A4[0] - 0.7 * inch, A4[1] - 0.45 * inch)
    # Pie
    canvas.drawCentredString(A4[0] / 2, 0.35 * inch, f'· {doc.page} ·')
    canvas.restoreState()


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    base = os.path.dirname(os.path.abspath(__file__))
    src_path = os.path.join(base, SRC)
    dst_path = os.path.join(base, DST)

    with open(src_path, 'r', encoding='utf-8') as f:
        text = f.read()

    flowables = parse_markdown(text)

    doc = SimpleDocTemplate(
        dst_path, pagesize=A4,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.7 * inch,   bottomMargin=0.6 * inch,
        title='Proyecto Final — Gestión de Datos',
        author='Álvaro González Fernández',
        subject='Memoria técnica del proyecto final',
    )
    doc.build(flowables, onFirstPage=header_footer, onLaterPages=header_footer)
    size_kb = os.path.getsize(dst_path) / 1024
    print(f'[OK] Generado: {dst_path}  ({size_kb:.1f} KB)')


if __name__ == '__main__':
    main()
