"""Fix section 4.3 formula numbering and missing content."""
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

def get_text(para):
    return ''.join(t.text or '' for t in para.iter('{%s}t' % W))

def rebuild_para_text(para, new_text):
    """Replace all w:t text, preserving math elements."""
    text_elems = list(para.iter('{%s}t' % W))
    if text_elems:
        text_elems[0].text = new_text
        text_elems[0].set('{%s}space' % XML_NS, 'preserve')
    for t in text_elems[1:]:
        t.text = ''

# ============================================================
# Fix P67: Add "其模值为：" and fix text flow
# ============================================================
# Current: "设从端估计外力为 ，主端力反馈为 。系统采用反馈增益和死区函数处理外力："
# Should be: "设从端估计外力向量为 F_ext，其模值为："
# Then insert formula (6)
# Then: "系统采用反馈增益和死区函数将外力模值转换为主端反馈强度："
text67 = get_text(paras[67])
text67_new = '设从端估计外力向量为 ，其模值为：'
rebuild_para_text(paras[67], text67_new)
print(f'P67: fixed text')

# ============================================================
# Insert formula (6): f_ext = ||F_ext||
# ============================================================
# Build a minimal OMML formula paragraph for f_ext = ||F_ext||
# We'll clone and modify the formula from para 68 (piecewise), simplify it

# New paragraph with formula (6)
formula6_para = etree.SubElement(body, '{%s}p' % W)
body.remove(formula6_para)

# Add pPr for centering
pPr = etree.SubElement(formula6_para, '{%s}pPr' % W)
jc = etree.SubElement(pPr, '{%s}jc' % W)
jc.set('{%s}val' % W, 'center')

# Build simple OMML: f_ext = ||F_ext||
# Structure: oMath > runs with m:t elements
oMath = etree.SubElement(formula6_para, '{%s}oMath' % M)

def make_math_run(parent, text, style='normal'):
    """Create a math run element in OMML."""
    mr = etree.SubElement(parent, '{%s}r' % M)
    if style == 'italic':
        mrPr = etree.SubElement(mr, '{%s}rPr' % M)
        nor = etree.SubElement(mrPr, '{%s}nor' % M)
    mt = etree.SubElement(mr, '{%s}t' % M)
    mt.text = text
    mt.set('{%s}space' % XML_NS, 'preserve')
    return mr

# Build: f_ext = ||F_ext||
# f with italic, _ext as subscript, then = , then norm brackets, F_ext italic
# Actually let's use a simpler approach - put the formula in text with math notation
# f_{ext} = ‖F_{ext}‖

# f
make_math_run(oMath, 'f', 'italic')
# _ext (subscript)
sSub = etree.SubElement(oMath, '{%s}sSub' % M)
e = etree.SubElement(sSub, '{%s}e' % M)
make_math_run(e, 'ext', 'normal')
# =
make_math_run(oMath, '=', 'normal')
# || (norm brackets) - use Unicode double vertical line
make_math_run(oMath, '‖', 'normal')  # ‖
# F
make_math_run(oMath, 'F', 'italic')
# _ext (subscript)
sSub2 = etree.SubElement(oMath, '{%s}sSub' % M)
e2 = etree.SubElement(sSub2, '{%s}e' % M)
make_math_run(e2, 'ext', 'normal')
# ||
make_math_run(oMath, '‖', 'normal')

# Add formula number (6) as text after math
r = etree.SubElement(formula6_para, '{%s}r' % W)
rPr = etree.SubElement(r, '{%s}rPr' % W)
t = etree.SubElement(r, '{%s}t' % W)
t.set('{%s}space' % XML_NS, 'preserve')
t.text = '  (6)'

# Insert after P67
paras[67].addnext(formula6_para)
print('P67+1: inserted formula (6)')

# ============================================================
# Insert new text paragraph: "系统采用反馈增益..."
# ============================================================
text_bridge = etree.SubElement(body, '{%s}p' % W)
body.remove(text_bridge)

r = etree.SubElement(text_bridge, '{%s}r' % W)
rPr = etree.SubElement(r, '{%s}rPr' % W)
t = etree.SubElement(r, '{%s}t' % W)
t.set('{%s}space' % XML_NS, 'preserve')
t.text = '系统采用反馈增益和死区函数将外力模值转换为主端反馈强度：'

# Add formatting: 宋体, 12pt, first-line indent
pPr_bridge = etree.SubElement(text_bridge, '{%s}pPr' % W)
ind = etree.SubElement(pPr_bridge, '{%s}ind' % W)
ind.set('{%s}firstLine' % W, '480')
jc_bridge = etree.SubElement(pPr_bridge, '{%s}jc' % W)
jc_bridge.set('{%s}val' % W, 'both')
spacing = etree.SubElement(pPr_bridge, '{%s}spacing' % W)
spacing.set('{%s}line' % W, '360')
spacing.set('{%s}lineRule' % W, 'auto')

rFonts = etree.SubElement(rPr, '{%s}rFonts' % W)
rFonts.set('{%s}eastAsia' % W, '宋体')
rFonts.set('{%s}ascii' % W, 'Times New Roman')
rFonts.set('{%s}hAnsi' % W, 'Times New Roman')
sz = etree.SubElement(rPr, '{%s}sz' % W)
sz.set('{%s}val' % W, '24')
szCs = etree.SubElement(rPr, '{%s}szCs' % W)
szCs.set('{%s}val' % W, '24')

# Insert after formula (6) paragraph
formula6_para.addnext(text_bridge)
print('Inserted bridge text paragraph')

# ============================================================
# Fix P68 (now shifted): change (6) to (7)
# ============================================================
# Need to refresh para list
paras = list(body.findall('{%s}p' % W))

# Find the piecewise function paragraph (now at different index)
for i, p in enumerate(paras):
    text = get_text(p)
    if '(6)' in text and any(m in text for m in ['Fh', 'Kf', 'Fext']):
        text = text.replace('(6)', '(7)')
        rebuild_para_text(p, text)
        print(f'P{i}: formula renumbered (6) -> (7)')
        break

# ============================================================
# Fix/remove the stray "]" paragraph
# ============================================================
paras = list(body.findall('{%s}p' % W))
for i, p in enumerate(paras):
    text = get_text(p).strip()
    if text == ']' or text == ']]' or text == '] ]':
        body.remove(p)
        print(f'P{i}: removed stray bracket paragraph')
        break

# ============================================================
# Fix P70 (now shifted): add proper variable explanations
# ============================================================
paras = list(body.findall('{%s}p' % W))
for i, p in enumerate(paras):
    text = get_text(p)
    if '其中，' in text and '为力反馈增益' in text and '为死区' in text:
        new_text = '式中， 为从端估计外力向量； 为外力模值； 为 Omega.7 主端输出反馈强度； 为力反馈增益； 为死区。soft 类物体采用较小 ，以避免操作者在主端感受到过强冲击；hard 类物体采用较大 ，以增强接触提示。视觉阻抗控制和视觉-力觉融合控制研究表明，将视觉感知与接触控制结合有助于改善机器人与环境交互过程[18-19]。'
        rebuild_para_text(p, new_text)
        print(f'P{i}: fixed explanation text')
        break

# ============================================================
# Save
# ============================================================
print("\nSaving...")
new_xml = etree.tostring(doc, xml_declaration=True, encoding='UTF-8', standalone=True)
data['word/document.xml'] = new_xml

with zipfile.ZipFile(DOCX, 'w', zipfile.ZIP_DEFLATED) as zout:
    for name, d in data.items():
        zout.writestr(name, d)

# Verify
with zipfile.ZipFile(DOCX, 'r') as z:
    doc2 = etree.parse(z.open('word/document.xml'))
body2 = doc2.find('{%s}body' % W)
paras2 = list(body2.findall('{%s}p' % W))

print("\n=== SECTION 4.3 VERIFICATION ===")
for i in range(66, min(76, len(paras2))):
    text = get_text(paras2[i])
    math_count = len(paras2[i].findall('.//{%s}oMath' % M))
    if math_count > 0 or text.strip():
        print(f'P{i} ({math_count} math): [{text[:200]}]')

print(f'\nTotal paragraphs: {len(paras2)}')
print('Done!')
