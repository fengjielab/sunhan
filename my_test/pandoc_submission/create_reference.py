from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_TAB_ALIGNMENT
from docx.oxml.ns import qn
from docx.shared import Cm, Pt


ROOT = Path(__file__).resolve().parent
BASE = ROOT / "reference_base.docx"
OUTPUT = ROOT / "reference.docx"


def set_font(style, east_asia, size, bold=False, latin="Times New Roman"):
    style.font.name = latin
    style.font.size = Pt(size)
    style.font.bold = bold
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.rFonts
    if rfonts is None:
        rfonts = rpr._add_rFonts()
    rfonts.set(qn("w:ascii"), latin)
    rfonts.set(qn("w:hAnsi"), latin)
    rfonts.set(qn("w:eastAsia"), east_asia)


def paragraph_style(styles, name, base="Normal"):
    try:
        style = styles[name]
    except KeyError:
        style = styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
    if base and name != base:
        try:
            style.base_style = styles[base]
        except KeyError:
            pass
    return style


def character_style(styles, name):
    try:
        return styles[name]
    except KeyError:
        return styles.add_style(name, WD_STYLE_TYPE.CHARACTER)


def configure_paragraph(style, alignment=None, line=1.5, before=0, after=0):
    fmt = style.paragraph_format
    if alignment is not None:
        fmt.alignment = alignment
    fmt.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE if line == 1.5 else WD_LINE_SPACING.SINGLE
    fmt.space_before = Pt(before)
    fmt.space_after = Pt(after)
    fmt.widow_control = True
    return style


doc = Document(BASE)
styles = doc.styles

normal = styles["Normal"]
set_font(normal, "宋体", 12)
configure_paragraph(normal, WD_ALIGN_PARAGRAPH.JUSTIFY, 1.5, 0, 0)

for name, size in (("Title", 22), ("Heading 1", 14), ("Heading 2", 12), ("Heading 3", 12)):
    style = styles[name]
    set_font(style, "黑体", size, bold=True)
    if name == "Title":
        configure_paragraph(style, WD_ALIGN_PARAGRAPH.CENTER, 1.0, 22, 22)
    else:
        configure_paragraph(style, WD_ALIGN_PARAGRAPH.LEFT, 1.0, 8, 4)

try:
    caption = styles["Caption"]
    set_font(caption, "宋体", 10.5)
    configure_paragraph(caption, WD_ALIGN_PARAGRAPH.CENTER, 1.0, 0, 6)
except KeyError:
    pass

definitions = {
    "Chinese Title": ("黑体", 22, True, WD_ALIGN_PARAGRAPH.CENTER, 1.0, 22, 22),
    "Chinese Authors": ("宋体", 10.5, False, WD_ALIGN_PARAGRAPH.CENTER, 1.0, 0, 0),
    "Chinese Affiliations": ("宋体", 10.5, False, WD_ALIGN_PARAGRAPH.CENTER, 1.0, 0, 8),
    "Abstract Body": ("宋体", 10.5, False, WD_ALIGN_PARAGRAPH.JUSTIFY, 1.5, 0, 0),
    "Keywords": ("宋体", 10.5, False, WD_ALIGN_PARAGRAPH.JUSTIFY, 1.5, 0, 0),
    "Classification": ("宋体", 10.5, False, WD_ALIGN_PARAGRAPH.LEFT, 1.0, 0, 8),
    "English Title": ("Times New Roman", 22, False, WD_ALIGN_PARAGRAPH.CENTER, 1.0, 22, 22),
    "English Authors": ("Times New Roman", 10.5, False, WD_ALIGN_PARAGRAPH.CENTER, 1.0, 0, 0),
    "English Abstract": ("Times New Roman", 10.5, False, WD_ALIGN_PARAGRAPH.JUSTIFY, 1.5, 0, 0),
    "English Keywords": ("Times New Roman", 10.5, False, WD_ALIGN_PARAGRAPH.JUSTIFY, 1.5, 0, 10),
    "Figure Placeholder": ("宋体", 10.5, False, WD_ALIGN_PARAGRAPH.CENTER, 1.0, 8, 4),
    "Image Caption": ("宋体", 10.5, False, WD_ALIGN_PARAGRAPH.CENTER, 1.0, 0, 6),
    "Table Caption": ("宋体", 10.5, False, WD_ALIGN_PARAGRAPH.CENTER, 1.0, 6, 0),
    "Reference Heading": ("黑体", 12, True, WD_ALIGN_PARAGRAPH.LEFT, 1.0, 8, 4),
    "References": ("宋体", 10.5, False, WD_ALIGN_PARAGRAPH.JUSTIFY, 1.5, 0, 0),
}

for name, (font, size, bold, align, line, before, after) in definitions.items():
    style = paragraph_style(styles, name)
    east_asia = font if font in ("宋体", "黑体") else "宋体"
    set_font(style, east_asia, size, bold, font if font == "Times New Roman" else "Times New Roman")
    configure_paragraph(style, align, line, before, after)

equation = paragraph_style(styles, "Equation")
set_font(equation, "宋体", 12)
configure_paragraph(equation, WD_ALIGN_PARAGRAPH.LEFT, 1.0, 3, 3)
tabs = equation.paragraph_format.tab_stops
tabs.add_tab_stop(Cm(7.96), WD_TAB_ALIGNMENT.CENTER)
tabs.add_tab_stop(Cm(15.92), WD_TAB_ALIGNMENT.RIGHT)

abstract_label = character_style(styles, "Abstract Label")
set_font(abstract_label, "黑体", 12, True)
english_label = character_style(styles, "English Label")
set_font(english_label, "Times New Roman", 12, True)

for table_style_name in ("Table Normal", "Table"):
    try:
        table_style = styles[table_style_name]
    except KeyError:
        if table_style_name == "Table":
            table_style = styles.add_style(table_style_name, WD_STYLE_TYPE.TABLE)
        else:
            continue
    set_font(table_style, "宋体", 10.5)

for section in doc.sections:
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(2.54)
    section.right_margin = Cm(2.54)

doc.save(OUTPUT)
print(OUTPUT)
