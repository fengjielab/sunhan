"""
Format 公式编号版.docx for journal using lxml (preserves OMML formulas).
Also applies backup markdown's individual citation style.
"""
import zipfile, sys, os, re, copy
from lxml import etree

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
M = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
XML_NS = 'http://www.w3.org/XML/1998/namespace'

sys.stdout.reconfigure(encoding='utf-8')

SRC = r'F:\前途文件\my_test\output\中文核心投稿稿_视觉语义驱动多参数阻抗辅助遥操作方法_公式编号版.docx'
DST = r'F:\前途文件\my_test\output\中文核心投稿稿_视觉语义驱动多参数阻抗辅助遥操作方法_格式整理后.docx'

# Read source
with zipfile.ZipFile(SRC, 'r') as z:
    data = {name: z.read(name) for name in z.namelist()}

doc = etree.fromstring(data['word/document.xml'])
body = doc.find('{%s}body' % W)
paras = list(body.findall('{%s}p' % W))

# ============================================================
# Helper functions
# ============================================================

def get_text(para):
    return ''.join(t.text or '' for t in para.iter('{%s}t' % W))

def get_or_add(el, tag):
    """Get or create a child element."""
    existing = el.find(tag)
    if existing is not None:
        return existing
    child = etree.SubElement(el, tag)
    # Insert at beginning for rPr
    if tag.endswith('}rPr'):
        el.insert(0, child)
    return child

def remove_existing(el, tag):
    """Remove child element if exists."""
    existing = el.find(tag)
    if existing is not None:
        el.remove(existing)

def set_run_font(rPr, western='Times New Roman', east_asian='宋体'):
    """Set font on a run properties element."""
    # Remove existing rFonts
    rFonts = rPr.find('{%s}rFonts' % W)
    if rFonts is not None:
        rPr.remove(rFonts)
    rFonts = etree.SubElement(rPr, '{%s}rFonts' % W)
    rFonts.set('{%s}ascii' % W, western)
    rFonts.set('{%s}hAnsi' % W, western)
    rFonts.set('{%s}eastAsia' % W, east_asian)
    # Clear theme font references
    for attr in ['{%s}asciiTheme' % W, '{%s}eastAsiaTheme' % W, '{%s}hAnsiTheme' % W, '{%s}cstheme' % W]:
        if attr in rFonts.attrib:
            del rFonts.attrib[attr]

def set_run_size(rPr, pt):
    """Set font size in half-points."""
    sz = rPr.find('{%s}sz' % W)
    if sz is None:
        sz = etree.SubElement(rPr, '{%s}sz' % W)
    sz.set('{%s}val' % W, str(int(pt * 2)))
    # Also set szCs for complex script
    szCs = rPr.find('{%s}szCs' % W)
    if szCs is None:
        szCs = etree.SubElement(rPr, '{%s}szCs' % W)
    szCs.set('{%s}val' % W, str(int(pt * 2)))

def set_run_bold(rPr, bold):
    """Set or remove bold."""
    b = rPr.find('{%s}b' % W)
    if bold:
        if b is None:
            etree.SubElement(rPr, '{%s}b' % W)
    else:
        if b is not None:
            rPr.remove(b)

def format_word_runs(para, western='Times New Roman', east_asian='宋体', size=None, bold=None):
    """Format all w:r elements in a paragraph (skips math runs)."""
    for r in para.findall('{%s}r' % W):
        rPr = get_or_add(r, '{%s}rPr' % W)
        set_run_font(rPr, western=western, east_asian=east_asian)
        if size is not None:
            set_run_size(rPr, size)
        if bold is not None:
            set_run_bold(rPr, bold)

def set_para_spacing(para, line=None, before=None, after=None):
    """Set paragraph spacing."""
    pPr = get_or_add(para, '{%s}pPr' % W)
    spacing = pPr.find('{%s}spacing' % W)
    if spacing is None:
        spacing = etree.SubElement(pPr, '{%s}spacing' % W)
    if line is not None:
        spacing.set('{%s}line' % W, str(line))
        spacing.set('{%s}lineRule' % W, 'auto')
    if before is not None:
        spacing.set('{%s}before' % W, str(before))
    if after is not None:
        spacing.set('{%s}after' % W, str(after))

def set_para_alignment(para, align):
    """Set paragraph alignment. align: center, left, right, both."""
    pPr = get_or_add(para, '{%s}pPr' % W)
    jc = pPr.find('{%s}jc' % W)
    if jc is None:
        jc = etree.SubElement(pPr, '{%s}jc' % W)
    jc.set('{%s}val' % W, align)

def set_para_indent(para, first_line=None, left=None):
    """Set paragraph indentation."""
    pPr = get_or_add(para, '{%s}pPr' % W)
    ind = pPr.find('{%s}ind' % W)
    if ind is None:
        ind = etree.SubElement(pPr, '{%s}ind' % W)
    if first_line is not None:
        ind.set('{%s}firstLine' % W, str(first_line))
    if left is not None:
        ind.set('{%s}left' % W, str(left))

def get_para_text(para):
    """Get full text of paragraph."""
    return ''.join(t.text or '' for t in para.iter('{%s}t' % W))

def rebuild_para_text(para, new_text):
    """Set paragraph text, preserving math elements."""
    text_elems = list(para.iter('{%s}t' % W))
    if text_elems:
        text_elems[0].text = new_text
        text_elems[0].set('{%s}space' % XML_NS, 'preserve')
    for t in text_elems[1:]:
        t.text = ''

def insert_text_in_para(para, search_key, insert_text, after=True):
    """Insert text into paragraph near search_key."""
    for r in para.iter('{%s}r' % W):
        for t in r.iter('{%s}t' % W):
            if t.text and search_key in t.text:
                pos = t.text.find(search_key)
                if after:
                    pos += len(search_key)
                t.text = t.text[:pos] + insert_text + t.text[pos:]
                t.set('{%s}space' % XML_NS, 'preserve')
                return True
    return False

# Size constants (in points)
TITLE_SIZE = 22      # 二号
L1_SIZE = 14         # 四号
L2_SIZE = 12         # 小四号
BODY_SIZE = 12       # 小四号
SMALL_SIZE = 10.5    # 五号
REF_SIZE = 10.5      # 五号

# ============================================================
# Phase 1: Apply journal formatting
# ============================================================
print("Phase 1: Applying journal formatting...")

# P0: Chinese title
format_word_runs(paras[0], east_asian='黑体', size=TITLE_SIZE, bold=True)
set_para_alignment(paras[0], 'center')
set_para_spacing(paras[0], line=360, before=440, after=440)

# P1: Authors
format_word_runs(paras[1], east_asian='宋体', size=SMALL_SIZE)
set_para_alignment(paras[1], 'center')

# P2: Affiliations
format_word_runs(paras[2], east_asian='宋体', size=SMALL_SIZE)
set_para_alignment(paras[2], 'center')

# P3: Abstract heading "摘要"
format_word_runs(paras[3], east_asian='黑体', size=L2_SIZE, bold=True)
set_para_alignment(paras[3], 'center')

# P4: Abstract content
format_word_runs(paras[4], east_asian='宋体', size=SMALL_SIZE)
set_para_spacing(paras[4], line=360)
set_para_alignment(paras[4], 'both')

# P5: Keywords
# Split keywords into heading + content
kw_text = get_text(paras[5])
if '：' in kw_text or ':' in kw_text:
    for sep in ['：', ':']:
        if sep in kw_text:
            heading_part = kw_text[:kw_text.find(sep)+1]
            content_part = kw_text[kw_text.find(sep)+1:]
            break
    # Rebuild: first run = heading (黑体 bold), second run = content (宋体)
    runs = list(paras[5].findall('{%s}r' % W))
    for r in runs:
        for t in r.findall('{%s}t' % W):
            t.text = ''
    if runs:
        runs[0].findall('{%s}t' % W)[0].text = heading_part
        rPr0 = get_or_add(runs[0], '{%s}rPr' % W)
        set_run_font(rPr0, east_asian='黑体')
        set_run_size(rPr0, L2_SIZE)
        set_run_bold(rPr0, True)
    if len(runs) >= 2:
        runs[1].findall('{%s}t' % W)[0].text = content_part
        rPr1 = get_or_add(runs[1], '{%s}rPr' % W)
        set_run_font(rPr1, east_asian='宋体')
        set_run_size(rPr1, SMALL_SIZE)
set_para_spacing(paras[5], line=360)

# P6: 中图分类号
format_word_runs(paras[6], east_asian='宋体', size=SMALL_SIZE)

# P7: Empty line - nothing to format

# P8: English title
format_word_runs(paras[8], western='Times New Roman', east_asian='Times New Roman', size=TITLE_SIZE, bold=True)
set_para_alignment(paras[8], 'center')

# P9: English authors
format_word_runs(paras[9], western='Times New Roman', east_asian='Times New Roman', size=SMALL_SIZE)
set_para_alignment(paras[9], 'center')

# P10: English abstract
format_word_runs(paras[10], western='Times New Roman', east_asian='Times New Roman', size=SMALL_SIZE)
set_para_spacing(paras[10], line=360)

# P11: English keywords
format_word_runs(paras[11], western='Times New Roman', east_asian='Times New Roman', size=SMALL_SIZE)
set_para_spacing(paras[11], line=360)

print("  Front matter done")

# Format body sections
import re as regex

def is_heading(text, level=1):
    if level == 1:
        return bool(regex.match(r'^\d+\s+\S+', text))
    elif level == 2:
        return bool(regex.match(r'^\d+\.\d+\s+\S+', text))
    return False

def is_figure_caption(text):
    return bool(regex.match(r'^图\s*\d+', text))

def is_table_caption(text):
    return bool(regex.match(r'^表\s*\d+', text) and len(text) < 80)

for i, para in enumerate(paras):
    text = get_text(para).strip()

    # Skip front matter (already formatted)
    if i <= 11:
        continue

    # References
    if text == '参考文献':
        format_word_runs(para, east_asian='黑体', size=L2_SIZE, bold=True)
        set_para_spacing(para, before=240)
        continue

    # Reference items
    if regex.match(r'^\[\d+\]', text):
        format_word_runs(para, east_asian='宋体', size=REF_SIZE)
        set_para_spacing(para, line=360)
        set_para_alignment(para, 'both')
        set_para_indent(para, first_line=0)
        continue

    # L1 headings
    if is_heading(text, level=1) and not is_heading(text, level=2):
        format_word_runs(para, east_asian='黑体', size=L1_SIZE, bold=True)
        set_para_spacing(para, before=120, after=60)
        continue

    # L2 headings
    if is_heading(text, level=2):
        format_word_runs(para, east_asian='黑体', size=L2_SIZE, bold=True)
        set_para_spacing(para, before=60, after=40)
        continue

    # Figure captions
    if is_figure_caption(text):
        format_word_runs(para, east_asian='宋体', size=SMALL_SIZE)
        set_para_alignment(para, 'center')
        set_para_spacing(para, before=120, after=120)
        continue

    # Table captions
    if is_table_caption(text):
        format_word_runs(para, east_asian='宋体', size=SMALL_SIZE, bold=True)
        set_para_alignment(para, 'center')
        set_para_spacing(para, before=120, after=60)
        continue

    # Body text (everything else with content)
    if text:
        format_word_runs(para, east_asian='宋体', size=BODY_SIZE)
        set_para_spacing(para, line=360)
        set_para_alignment(para, 'both')
        set_para_indent(para, first_line=480)  # 2-char indent at 12pt

print("  Body text done")

# ============================================================
# Phase 2: Apply individual citations from backup markdown
# ============================================================
print("\nPhase 2: Applying citations from backup...")

# Step 1: Remove existing grouped citations
grouped_citations = {
    14: [r'\[1-10\]'],
    15: [r'\[15-22\]'],
    44: [r'\[1-8\]'],   # para 45 in 0-indexed
    60: [r'\[1-3\]'],   # para 61
    92: [r'\[24-25\]'], # para 93
}

for pi, patterns in grouped_citations.items():
    if pi < len(paras):
        for pattern in patterns:
            for r in paras[pi].iter('{%s}r' % W):
                for t in r.iter('{%s}t' % W):
                    if t.text:
                        t.text = t.text.replace(pattern, '')
                        t.set('{%s}space' % XML_NS, 'preserve')
        print(f"  Para {pi}: removed grouped citation")

# Step 2: Insert individual citations
# Map: (para_idx, search_key, insert_after_key, citation_text)
INSERTIONS = [
    # Para 13: Teleoperation basics
    # "...判断任务状态[1]。"
    (13, '判断任务状态', '[1]', True),

    # Para 14: Impedance control
    # "...提供了重要基础[4]。混合阻抗控制...影响[5]。...变阻抗控制...在线调整[6-7]。"
    (14, '提供了重要基础', '[4]', True),
    (14, '混合阻抗控制进一步说明了接触环境特性对力位控制策略选择的影响', '[5]', False),

    # Para 15: Visual perception
    (15, '目标检测模型识别物体类别', '[8]', True),
    (15, '一种可行方式', '[9]', True),

    # Para 23: Platform description
    # Search in the Franka platform paragraph
    (23, '适合用于人机交互和遥操作接触任务研究', '[10]', True),
    (23, '碰撞检测和柔顺控制能力', '[11]', True),

    # Para 45: Parameter design basis
    (44, '共同确定', '[4,6,12]', True),
    (44, '参数设计遵循以下原则', '[13-14]', True),

    # Para 61: Impedance formula
    (60, '可表示为', '[4-5]', True),

    # Para 70: Visual force fusion
    (69, '增强接触提示', '[15-16]', True),

    # Para 72: Grasping
    (71, '提高任务效率', '[17-18]', True),
    (71, '抓取效率', '[17-18]', True),  # fallback

    # Para 93: Evaluation
    (92, '人机交互体验', '[3]', True),
]

# Need to detect actual paragraph indices since mappings may change
# Let's search by text content
for para_idx, search_key, citation, after in INSERTIONS:
    if para_idx < len(paras):
        ok = insert_text_in_para(paras[para_idx], search_key, citation, after=after)
        print(f"  Para {para_idx} [{citation}] {'OK' if ok else 'NOT FOUND'} <- '{search_key[:40]}'")

# Add extra text for [2] and [3] in para 13 (after [1])
extra_p13 = "在存在通信延迟或接触不确定性的场景中，稳定性和力觉透明性是双边遥操作系统需要重点考虑的问题[2]。针对环境、操作者和任务状态自适应调整控制策略，也被认为是提升遥操作系统性能的重要途径[3]。"
ok = insert_text_in_para(paras[13], '[1]', extra_p13, after=True)
print(f"  Para 13 extra [2][3]: {'OK' if ok else 'NOT FOUND'}")

# Add extra text for [5] and [6-7] in para 14
extra_p14 = "混合阻抗控制进一步说明了接触环境特性对力/位控制策略选择的影响[5]。近年来，面向未知环境和动态接触任务的自适应变阻抗控制得到关注，其核心思想是根据接触状态在线调整阻抗参数[6-7]。"
ok = insert_text_in_para(paras[14], '[4]', extra_p14, after=True)
if not ok:
    # Try inserting at start of text
    for r in paras[14].iter('{%s}r' % W):
        for t in r.iter('{%s}t' % W):
            if t.text and len(t.text) > 50:
                t.text = t.text + extra_p14
                t.set('{%s}space' % XML_NS, 'preserve')
                ok = True
                break
        if ok:
            break
print(f"  Para 14 extra [5][6-7]: {'OK' if ok else 'NOT FOUND'}")

# Add extra text for [9] in para 15
extra_p15 = "在机器人抓取领域，基于视觉的未知物体抓取方法已被用于解决未知物体抓取点选择问题[9]。"
print(f"  Para 15 extra [9]: {'OK' if insert_text_in_para(paras[15], '[8]', extra_p15, after=True) else 'NOT FOUND'}")

# Add extra text for [4][6][12][13-14] in para 45
extra_p44 = "阻抗控制理论为刚度、阻尼和接触柔顺性之间的关系提供了基础依据[4]；变阻抗控制研究则说明，阻抗参数需要结合任务状态和交互对象进行调整[6]。同时，参数在线调节还需关注稳定性约束问题[12]；在人机协作场景中，操作者意图和运动状态也可作为阻抗调节的重要依据[13-14]。"
print(f"  Para 44 extra [4][6][12][13-14]: {'OK' if insert_text_in_para(paras[44], '共同确定', extra_p44, after=True) else 'NOT FOUND'}")

# Add [19] and [20] in discussion section
extra_disc = "已有研究表明，变阻抗调节可改善人机物理交互过程中的舒适性和任务表现[19]，示教学习方法也可用于获得随任务变化的阻抗参数[20]。"
found_19_20 = False
for pi in range(125, min(135, len(paras))):
    text = get_text(paras[pi])
    if '学习型阻抗控制' in text or '力觉自适应' in text:
        ok = insert_text_in_para(paras[pi], '学习型阻抗控制', extra_disc, after=True)
        if not ok:
            ok = insert_text_in_para(paras[pi], '力觉自适应', extra_disc, after=True)
        found_19_20 = ok
        print(f"  Para {pi} [19][20]: {'OK' if ok else 'NOT FOUND'}")
        break

# ============================================================
# Phase 3: Replace reference list with 20 entries from backup
# ============================================================
print("\nPhase 3: Replacing reference list...")

ref_list_20 = [
    '[1] Lawrence D A. Stability and transparency in bilateral teleoperation[J]. IEEE Transactions on Robotics and Automation, 1993, 9(5): 624-637.',
    '[2] Niemeyer G, Slotine J J E. Stable adaptive teleoperation[J]. IEEE Journal of Oceanic Engineering, 1991, 16(1): 152-162.',
    '[3] Passenberg C, Peer A, Buss M. A survey of environment-, operator-, and task-adapted controllers for teleoperation systems[J]. Mechatronics, 2010, 20(7): 787-801.',
    '[4] Hogan N. Impedance control: An approach to manipulation: Part I-theory[J]. Journal of Dynamic Systems, Measurement, and Control, 1985, 107(1): 1-7.',
    '[5] Anderson R J, Spong M W. Hybrid impedance control of robotic manipulators[J]. IEEE Journal on Robotics and Automation, 1988, 4(5): 549-556.',
    '[6] Duan J J, Gan Y H, Chen M, 等. Adaptive variable impedance control for dynamic contact force tracking in uncertain environment[J]. Robotics and Autonomous Systems, 2018, 102: 54-65.',
    '[7] Abu-Dakka F J, Rozo L, Caldwell D G. Force-based variable impedance learning for robotic manipulation[J]. Robotics and Autonomous Systems, 2018, 109: 156-167.',
    '[8] Redmon J, Divvala S, Girshick R, 等. You only look once: Unified, real-time object detection[C]//Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition. Las Vegas: Institute of Electrical and Electronics Engineers, 2016: 779-788.',
    '[9] Saxena A, Driemeyer J, Ng A Y. Robotic grasping of novel objects using vision[J]. The International Journal of Robotics Research, 2008, 27(2): 157-173.',
    '[10] Haddadin S, Parusel S, Johannsmeier L, 等. The Franka Emika robot: A reference platform for robotics research and education[J]. IEEE Robotics & Automation Magazine, 2022, 29(2): 46-64.',
    '[11] Haddadin S, De Luca A, Albu-Schaffer A. Robot collisions: A survey on detection, isolation, and identification[J]. IEEE Transactions on Robotics, 2017, 33(6): 1292-1312.',
    '[12] Kronander K, Billard A. Stability considerations for variable impedance control[J]. IEEE Transactions on Robotics, 2016, 32(5): 1298-1305.',
    '[13] Peternel L, Tsagarakis N, Ajoudani A. Towards multi-modal intention interfaces for human-robot co-manipulation[C]//Proceedings of the IEEE/RSJ International Conference on Intelligent Robots and Systems. Daejeon: Institute of Electrical and Electronics Engineers, 2016: 2663-2669.',
    '[14] Dong B, Sun R, An T J, 等. Adaptive fuzzy impedance control of human-robot interaction modular robot manipulators based on human motion intention estimation[C]//Proceedings of the 14th International Conference on Information Science and Technology. Chengdu: Institute of Electrical and Electronics Engineers, 2024.',
    '[15] Lippiello V, Siciliano B, Villani L. A position-based visual impedance control for robot manipulators[C]//Proceedings of the IEEE International Conference on Robotics and Automation. Roma: Institute of Electrical and Electronics Engineers, 2007: 2068-2073.',
    '[16] Oliva A A, Giordano P R, Chaumette F. A general visual-impedance framework for effectively combining vision and force sensing in feature space[J]. IEEE Robotics and Automation Letters, 2021, 6(3): 4441-4448.',
    '[17] Lenz I, Lee H, Saxena A. Deep learning for detecting robotic grasps[J]. The International Journal of Robotics Research, 2015, 34(4-5): 705-724.',
    '[18] Jang E, Vijayanarasimhan S, Ibarz J, 等. End-to-end learning of semantic grasping[C]//Proceedings of the Conference on Robot Learning. Mountain View: PMLR, 2017.',
    '[19] Ficuciello F, Villani L, Siciliano B. Variable impedance control of redundant manipulators for intuitive human-robot physical interaction[J]. IEEE Transactions on Robotics, 2015, 31(4): 850-863.',
    '[20] Buchli J, Stulp F, Theodorou E, 等. Learning variable impedance control[J]. The International Journal of Robotics Research, 2011, 30(7): 820-833.',
]

# Find and remove old reference list
ref_header_idx = None
for i, para in enumerate(paras):
    text = get_text(para).strip()
    if text == '参考文献' or text == '參考文献':
        ref_header_idx = i
        break

if ref_header_idx:
    # Remove all paragraphs after references heading
    to_remove = []
    for i in range(ref_header_idx + 1, len(paras)):
        to_remove.append(paras[i])
    for p in to_remove:
        body.remove(p)

    # Rebuild paragraph list
    paras = list(body.findall('{%s}p' % W))

    # Clone template from a reference paragraph (use any paragraph as template)
    # Create reference paragraphs with proper formatting
    ref_template_para = etree.SubElement(body, '{%s}p' % W)
    body.remove(ref_template_para)

    # Build template: p > pPr + r > rPr + t
    pPr = etree.SubElement(ref_template_para, '{%s}pPr' % W)
    set_para_spacing(ref_template_para, line=360)
    set_para_indent(ref_template_para, first_line=0)
    jc = etree.SubElement(pPr, '{%s}jc' % W)
    jc.set('{%s}val' % W, 'both')

    r = etree.SubElement(ref_template_para, '{%s}r' % W)
    rPr = etree.SubElement(r, '{%s}rPr' % W)
    set_run_font(rPr, east_asian='宋体')
    set_run_size(rPr, REF_SIZE)
    t = etree.SubElement(r, '{%s}t' % W)
    t.set('{%s}space' % XML_NS, 'preserve')

    # Insert reference entries after header
    insert_after = paras[ref_header_idx]
    for ref_text in ref_list_20:
        new_para = copy.deepcopy(ref_template_para)
        new_para.find('.//{%s}t' % W).text = ref_text
        insert_after.addnext(new_para)
        insert_after = new_para

    print(f"  Replaced reference list: {len(ref_list_20)} entries")

# ============================================================
# Phase 4: Add funding and author bio
# ============================================================
print("\nPhase 4: Adding funding and author bio...")

# Re-get paragraphs after modifications
paras = list(body.findall('{%s}p' % W))

# Build a simple text paragraph template
def make_text_para(text, east_asian='宋体', size=SMALL_SIZE, alignment=None):
    p = etree.SubElement(body, '{%s}p' % W)
    body.remove(p)

    pPr = etree.SubElement(p, '{%s}pPr' % W)
    if alignment:
        jc = etree.SubElement(pPr, '{%s}jc' % W)
        jc.set('{%s}val' % W, alignment)

    r = etree.SubElement(p, '{%s}r' % W)
    rPr = etree.SubElement(r, '{%s}rPr' % W)
    set_run_font(rPr, east_asian=east_asian)
    set_run_size(rPr, size)
    t = etree.SubElement(r, '{%s}t' % W)
    t.set('{%s}space' % XML_NS, 'preserve')
    t.text = text
    return p

# Find last paragraph and insert after it
last_para = paras[-1] if paras else None

funding_para = make_text_para(
    '基金项目：[基金类型 基金编号（基金名称）] [待补充]',
    east_asian='宋体', size=SMALL_SIZE
)
bio_para = make_text_para(
    '作者简介：[姓名]（[出生年]-），[性别]，[民族]，[籍贯]人，[职称]，[学位]，研究方向为[研究方向]。',
    east_asian='宋体', size=SMALL_SIZE
)

if last_para is not None:
    last_para.addnext(bio_para)
    last_para.addnext(funding_para)

print("  Funding and author bio added")

# ============================================================
# Phase 5: Apply superscript to citations
# ============================================================
print("\nPhase 5: Applying superscript to citations...")

paras = list(body.findall('{%s}p' % W))
citation_pattern = regex.compile(r'\[\d+(?:[-–]\d+)?(?:[,，]\s*\d+(?:[-–]\d+)?)*\]')

for para in paras:
    text = get_text(para).strip()
    if not text:
        continue
    # Skip headings, reference items, front matter
    if is_heading(text) or regex.match(r'^\[\d+\]', text):
        continue
    if text in ('参考文献', '摘要', '关键词'):
        continue

    for r in para.findall('{%s}r' % W):
        t = r.find('{%s}t' % W)
        if t is None or not t.text:
            continue

        if not citation_pattern.search(t.text):
            continue

        # Simple case: entire text is a citation
        if citation_pattern.fullmatch(t.text.strip()):
            rPr = get_or_add(r, '{%s}rPr' % W)
            vertAlign = etree.SubElement(rPr, '{%s}vertAlign' % W)
            vertAlign.set('{%s}val' % W, 'superscript')
            t.text = t.text.replace('–', '-').replace('－', '-')
            continue

        # Complex case: split text around citations
        parts = citation_pattern.split(t.text)
        citations = citation_pattern.findall(t.text)
        if not citations:
            continue

        # Rebuild: interleave text parts and citations
        parent = r.getparent()
        r_index = list(parent).index(r)

        # Build new runs
        new_elements = []
        for idx in range(len(parts)):
            if parts[idx]:
                new_r = etree.SubElement(parent, '{%s}r' % W)
                parent.remove(new_r)
                # Copy rPr from original
                orig_rPr = r.find('{%s}rPr' % W)
                if orig_rPr is not None:
                    new_rPr = copy.deepcopy(orig_rPr)
                    new_r.append(new_rPr)
                new_t = etree.SubElement(new_r, '{%s}t' % W)
                new_t.set('{%s}space' % XML_NS, 'preserve')
                new_t.text = parts[idx]
                new_elements.append(new_r)

            if idx < len(citations):
                cit_r = etree.SubElement(parent, '{%s}r' % W)
                parent.remove(cit_r)
                orig_rPr = r.find('{%s}rPr' % W)
                if orig_rPr is not None:
                    cit_rPr = copy.deepcopy(orig_rPr)
                    cit_r.append(cit_rPr)
                else:
                    cit_rPr = etree.SubElement(cit_r, '{%s}rPr' % W)
                # Add superscript
                va = etree.SubElement(cit_rPr, '{%s}vertAlign' % W)
                va.set('{%s}val' % W, 'superscript')
                cit_t = etree.SubElement(cit_r, '{%s}t' % W)
                cit_t.set('{%s}space' % XML_NS, 'preserve')
                cit_t.text = citations[idx].replace('–', '-').replace('－', '-')
                new_elements.append(cit_r)

        # Insert new elements
        for elem in reversed(new_elements):
            parent.insert(r_index, elem)

        # Remove old run
        parent.remove(r)

print("  Citation superscript applied")

# ============================================================
# Phase 6: Format tables
# ============================================================
print("\nPhase 6: Formatting tables...")

for tbl in body.iter('{%s}tbl' % W):
    # Get or create tblPr
    tblPr = tbl.find('{%s}tblPr' % W)
    if tblPr is None:
        tblPr = etree.Element('{%s}tblPr' % W)
        tbl.insert(0, tblPr)

    # Remove existing borders
    for existing_borders in tblPr.findall('{%s}tblBorders' % W):
        tblPr.remove(existing_borders)

    # Add borders
    borders = etree.SubElement(tblPr, '{%s}tblBorders' % W)
    for border_name in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
        border = etree.SubElement(borders, '{%s}%s' % (W, border_name))
        border.set('{%s}val' % W, 'single')
        border.set('{%s}sz' % W, '4')
        border.set('{%s}space' % W, '0')
        border.set('{%s}color' % W, '000000')

    # Format cells
    for ri, row in enumerate(tbl.findall('{%s}tr' % W)):
        for cell in row.findall('{%s}tc' % W):
            for p in cell.findall('{%s}p' % W):
                set_para_spacing(p, before=20, after=20, line=240)
                set_para_alignment(p, 'center')
                for r in p.findall('{%s}r' % W):
                    rPr = get_or_add(r, '{%s}rPr' % W)
                    set_run_font(rPr, east_asian='宋体')
                    set_run_size(rPr, SMALL_SIZE)
                    if ri == 0:  # Header row bold
                        set_run_bold(rPr, True)

print(f"  Tables formatted")

# ============================================================
# Save
# ============================================================
print("\nSaving...")

# Get all sections and set page properties
sectPr = body.getparent().find('{%s}sectPr' % W) if body.getparent() is not None else None
if sectPr is not None:
    # Page size A4
    pgSz = sectPr.find('{%s}pgSz' % W)
    if pgSz is None:
        pgSz = etree.SubElement(sectPr, '{%s}pgSz' % W)
    pgSz.set('{%s}w' % W, '11906')   # 21cm in twips
    pgSz.set('{%s}h' % W, '16838')   # 29.7cm

    # Margins
    pgMar = sectPr.find('{%s}pgMar' % W)
    if pgMar is None:
        pgMar = etree.SubElement(sectPr, '{%s}pgMar' % W)
    for attr, val in [('top', '1440'), ('bottom', '1440'), ('left', '1440'), ('right', '1440')]:
        pgMar.set('{%s}%s' % (W, attr), val)  # 2.54cm in twips

# Serialize
new_xml = etree.tostring(doc, xml_declaration=True, encoding='UTF-8', standalone=True)
data['word/document.xml'] = new_xml

with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zout:
    for name, d in data.items():
        zout.writestr(name, d)

# ============================================================
# Final verification
# ============================================================
print("\n=== VERIFICATION ===")
with zipfile.ZipFile(DST, 'r') as z:
    doc2 = etree.parse(z.open('word/document.xml'))

body2 = doc2.find('{%s}body' % W)
paras2 = list(body2.findall('{%s}p' % W))

print(f"Total paragraphs: {len(paras2)}")

# OMML formulas
math_count = 0
for p in paras2:
    if p.findall('.//{%s}oMath' % M) or p.findall('.//{%s}oMathPara' % M):
        math_count += 1
print(f"OMML formula paragraphs: {math_count}")

# Check for double periods
issues = 0
for i, p in enumerate(paras2):
    text = get_text(p)
    if '。。' in text:
        print(f"  Para {i}: DOUBLE PERIOD ISSUE")
        issues += 1
if issues == 0:
    print("  No double period issues")

# List citations
print("\nCitations by paragraph:")
all_cits = []
for i, p in enumerate(paras2):
    text = get_text(p)
    found = regex.findall(r'\[[\d,\-]+\]', text)
    if found:
        # Filter out reference list items
        if not regex.match(r'^\[\d+\]\s', text.strip()):
            print(f"  Para {i}: {found}")
            all_cits.extend(found)

# Reference list
print(f"\nReference entries: {sum(1 for p in paras2 if regex.match(r'^\[\d+\]\s', get_text(p).strip()))}")

print(f"\nFile saved to: {DST}")
print("Done!")
