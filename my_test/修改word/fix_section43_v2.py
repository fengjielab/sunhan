"""Fix section 4.3: subscripts, right-alignment, parameter explanations."""
import sys, zipfile, copy
from lxml import etree
sys.stdout.reconfigure(encoding='utf-8')

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
M = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
XML_NS = 'http://www.w3.org/XML/1998/namespace'
DOCX = r'F:\前途文件\my_test\output\中文核心投稿稿_视觉语义驱动多参数阻抗辅助遥操作方法_格式整理后.docx'

with zipfile.ZipFile(DOCX, 'r') as z:
    data = {name: z.read(name) for name in z.namelist()}

doc = etree.fromstring(data['word/document.xml'])
body = doc.find('{%s}body' % W)
paras = list(body.findall('{%s}p' % W))

def get_text(p):
    return ''.join(t.text or '' for t in p.iter('{%s}t' % W))

# ============================================================
# Helper: standard formula paragraph pPr with tabs
# ============================================================
def setup_formula_pPr(para):
    """Set pPr for formula paragraph: center tab for formula, right tab for number."""
    pPr = para.find('{%s}pPr' % W)
    if pPr is None:
        pPr = etree.Element('{%s}pPr' % W)
        para.insert(0, pPr)
    else:
        # Clear existing pPr children but keep the element
        for child in list(pPr):
            pPr.remove(child)

    # Tab stops
    tabs = etree.SubElement(pPr, '{%s}tabs' % W)
    tab_c = etree.SubElement(tabs, '{%s}tab' % W)
    tab_c.set('{%s}val' % W, 'center')
    tab_c.set('{%s}pos' % W, '4253')
    tab_r = etree.SubElement(tabs, '{%s}tab' % W)
    tab_r.set('{%s}val' % W, 'right')
    tab_r.set('{%s}pos' % W, '8506')

    # Spacing
    spacing = etree.SubElement(pPr, '{%s}spacing' % W)
    spacing.set('{%s}line' % W, '360')
    spacing.set('{%s}lineRule' % W, 'auto')

    # Justify
    jc = etree.SubElement(pPr, '{%s}jc' % W)
    jc.set('{%s}val' % W, 'both')

# ============================================================
# Helper: create a math run (inside oMath)
# ============================================================
def make_math_run(parent, text, bold=False, italic=False):
    """Create <m:r> inside oMath parent."""
    mr = etree.SubElement(parent, '{%s}r' % M)
    if bold or italic:
        mrPr = etree.SubElement(mr, '{%s}rPr' % M)
        if bold:
            sty = etree.SubElement(mrPr, '{%s}sty' % M)
            sty.set('{%s}val' % M, 'b')
        if italic:
            sty = etree.SubElement(mrPr, '{%s}sty' % M)
            sty.set('{%s}val' % M, 'i')
    mt = etree.SubElement(mr, '{%s}t' % M)
    mt.text = text
    mt.set('{%s}space' % XML_NS, 'preserve')
    return mr

def make_math_subscript(parent, base_text, sub_text, base_bold=False):
    """Create <m:sSub> with base and subscript."""
    sSub = etree.SubElement(parent, '{%s}sSub' % M)
    # Base
    e = etree.SubElement(sSub, '{%s}e' % M)
    make_math_run(e, base_text, bold=base_bold)
    # Subscript
    sub = etree.SubElement(sSub, '{%s}sub' % M)
    make_math_run(sub, sub_text)
    return sSub

# ============================================================
# Helper: create inline oMath element
# ============================================================
def make_inline_math(text, bold=False):
    """Create a simple inline <m:oMath> with a single math run."""
    oMath = etree.Element('{%s}oMath' % M)
    make_math_run(oMath, text, bold=bold)
    return oMath

def make_inline_subscript(base_text, sub_text, base_bold=False):
    """Create inline <m:oMath> with subscript."""
    oMath = etree.Element('{%s}oMath' % M)
    make_math_subscript(oMath, base_text, sub_text, base_bold=base_bold)
    return oMath

# ============================================================
# Helper: create a Word run with text
# ============================================================
def make_text_run(text, font_east='宋体', font_west='Times New Roman', size_pt=12):
    """Create <w:r> with <w:t>."""
    r = etree.Element('{%s}r' % W)
    rPr = etree.SubElement(r, '{%s}rPr' % W)
    rFonts = etree.SubElement(rPr, '{%s}rFonts' % W)
    rFonts.set('{%s}eastAsia' % W, font_east)
    rFonts.set('{%s}ascii' % W, font_west)
    rFonts.set('{%s}hAnsi' % W, font_west)
    sz = etree.SubElement(rPr, '{%s}sz' % W)
    sz.set('{%s}val' % W, str(int(size_pt * 2)))
    szCs = etree.SubElement(rPr, '{%s}szCs' % W)
    szCs.set('{%s}val' % W, str(int(size_pt * 2)))
    t = etree.SubElement(r, '{%s}t' % W)
    t.set('{%s}space' % XML_NS, 'preserve')
    t.text = text
    return r

# ============================================================
# 1. FIX FORMULA (6) at P68: correct OMML structure + tabs
# ============================================================
p68 = paras[68]
# Remove existing oMath
for om in list(p68.findall('.//{%s}oMath' % M)):
    p68.remove(om)
# Remove existing runs (keep pPr)
for r_elem in list(p68.findall('{%s}r' % W)):
    p68.remove(r_elem)

# Setup pPr
setup_formula_pPr(p68)

# Add leading tab run
r_tab1 = etree.Element('{%s}r' % W)
etree.SubElement(r_tab1, '{%s}tab' % W)
p68.append(r_tab1)

# Build formula (6): f_ext = ||F_ext||
oMath = etree.Element('{%s}oMath' % M)
make_math_subscript(oMath, 'f', 'ext')  # f_ext
make_math_run(oMath, '=')
make_math_run(oMath, '‖')  # ‖
make_math_subscript(oMath, 'F', 'ext', base_bold=True)  # F_ext (bold)
make_math_run(oMath, '‖')  # ‖
p68.append(oMath)

# Add number run with tab: (6)
r_num = etree.Element('{%s}r' % W)
etree.SubElement(r_num, '{%s}tab' % W)
t = etree.SubElement(r_num, '{%s}t' % W)
t.set('{%s}space' % XML_NS, 'preserve')
t.text = '(6)'
p68.append(r_num)

print('P68: rebuilt formula (6) with correct sSub and tabs')

# ============================================================
# 2. FIX FORMULA (7) at P70: add tabs
# ============================================================
p70 = paras[70]
setup_formula_pPr(p70)

# Insert leading tab run before the math
r_tab1_f7 = etree.Element('{%s}r' % W)
etree.SubElement(r_tab1_f7, '{%s}tab' % W)
# Insert before the first oMath
first_om = p70.find('{%s}oMath' % M)
if first_om is not None:
    first_om.addprevious(r_tab1_f7)

# The number "(7)" run - find it and add tab
for r_elem in p70.findall('{%s}r' % W):
    t_elem = r_elem.find('{%s}t' % W)
    if t_elem is not None and t_elem.text and '(7)' in (t_elem.text or ''):
        # Add tab before the text in this run
        tab = etree.Element('{%s}tab' % W)
        r_elem.insert(0, tab)
        print('P70: added tab before (7)')
        break

print('P70: setup tabs for formula (7)')

# ============================================================
# 3. REBUILD P71: proper inline math matching backup md
# ============================================================
# Desired structure (from backup md):
# 式中，F_ext 为从端估计外力向量；f_ext 为外力模值；f_h 为 Omega.7
# 主端输出反馈强度；K_f(c) 为力反馈增益；d(c) 为死区。soft 类物体采用
# 较小 K_f(c)，以避免操作者在主端感受到过强冲击；hard 类物体采用较大
# K_f(c)，以增强接触提示。视觉阻抗控制和视觉-力觉融合控制研究表明，
# 将视觉感知与接触控制结合有助于改善机器人与环境交互过程[18-19]。

p71 = paras[71]
# Remove all existing runs and math elements
for child in list(p71):
    tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
    if tag in ('r', 'oMath', 'oMathPara', 'proofErr'):
        p71.remove(child)

# Setup pPr (body text with indent)
pPr71 = p71.find('{%s}pPr' % W)
if pPr71 is None:
    pPr71 = etree.Element('{%s}pPr' % W)
    p71.insert(0, pPr71)
else:
    for child in list(pPr71):
        pPr71.remove(child)

spacing = etree.SubElement(pPr71, '{%s}spacing' % W)
spacing.set('{%s}line' % W, '360')
spacing.set('{%s}lineRule' % W, 'auto')
ind = etree.SubElement(pPr71, '{%s}ind' % W)
ind.set('{%s}firstLine' % W, '480')
jc = etree.SubElement(pPr71, '{%s}jc' % W)
jc.set('{%s}val' % W, 'both')

# Build content elements
content = [
    ('text', '式中，'),
    ('msub', ('F', 'ext', True)),    # F_ext bold
    ('text', '为从端估计外力向量；'),
    ('msub', ('f', 'ext', False)),   # f_ext
    ('text', '为外力模值；'),
    ('msub', ('f', 'h', False)),     # f_h
    ('text', '为 Omega.7 主端输出反馈强度；'),
    ('msub', ('K', 'f', False)),     # K_f
    ('text', '('),
    ('math', ('c', False)),          # c
    ('text', ')为力反馈增益；'),
    ('math', ('d', False)),          # d
    ('text', '('),
    ('math', ('c', False)),          # c
    ('text', ')为死区。soft 类物体采用较小'),
    ('msub', ('K', 'f', False)),     # K_f
    ('text', '('),
    ('math', ('c', False)),          # c
    ('text', ')，以避免操作者在主端感受到过强冲击；hard 类物体采用较大'),
    ('msub', ('K', 'f', False)),     # K_f
    ('text', '('),
    ('math', ('c', False)),          # c
    ('text', ')，以增强接触提示。视觉阻抗控制和视觉-力觉融合控制研究表明，将视觉感知与接触控制结合有助于改善机器人与环境交互过程[18-19]。'),
]

for item in content:
    kind = item[0]
    if kind == 'text':
        p71.append(make_text_run(item[1]))
    elif kind == 'math':
        text, bold = item[1]
        p71.append(make_inline_math(text, bold=bold))
    elif kind == 'msub':
        base, sub, bold = item[1]
        p71.append(make_inline_subscript(base, sub, base_bold=bold))

print('P71: rebuilt with proper inline math variables')

# ============================================================
# Save
# ============================================================
print('\nSaving...')
new_xml = etree.tostring(doc, xml_declaration=True, encoding='UTF-8', standalone=True)
data['word/document.xml'] = new_xml

try:
    with zipfile.ZipFile(DOCX, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, d in data.items():
            zout.writestr(name, d)
    print('Saved to original path')
except PermissionError:
    alt_path = DOCX.replace('.docx', '_section43_fixed.docx')
    with zipfile.ZipFile(alt_path, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, d in data.items():
            zout.writestr(name, d)
    print('Saved to alt path: ' + alt_path)

# ============================================================
# Verify (from in-memory doc, not file)
# ============================================================
paras2 = list(body.findall('{%s}p' % W))

print('\n=== VERIFICATION ===')
for i in range(66, 76):
    p = paras2[i]
    text_elems = list(p.iter('{%s}t' % W))
    math_elems = p.findall('.//{%s}oMath' % M)
    w_text = ''.join(t.text or '' for t in text_elems)
    # Check for tab stops
    tabs_def = p.findall('.//{%s}tabs/{%s}tab' % (W, W))
    # Check for tab characters (those without val attr)
    tab_chars = [t for t in p.findall('.//{%s}tab' % W) if t.get('{%s}val' % W) is None]

    w_val = '{%s}val' % W
    w_pos = '{%s}pos' % W
    tabs_info = [(t.get(w_val), t.get(w_pos)) for t in tabs_def]
    print('\nP%d: [tabs: %s] [tab_chars: %d] [math: %d]' % (i, tabs_info, len(tab_chars), len(math_elems)))
    print('  w:t: [%s]' % w_text[:200])
    for j, om in enumerate(math_elems):
        mt = ''.join(t.text or '' for t in om.iter('{%s}t' % M))
        print('  oMath[%d]: [%s]' % (j, mt[:200]))

print(f'\nTotal paragraphs: {len(paras2)}')
print('Done!')
