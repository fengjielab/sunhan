"""
Directly fix formulas and inline parameters in the target docx,
preserving all other formatting (images, tables, styles, text).

Approach:
1. Extract OMML templates from pandoc output
2. Replace display formula paragraphs with center + right-aligned OMML + numbering
3. Replace broken inline parameter text with OMML math elements
"""
import sys
import shutil
import zipfile
import os
import re
import copy
from lxml import etree

sys.stdout.reconfigure(encoding='utf-8')

PANDOC_DOCX = r'F:\前途文件\my_test\output\formatted_omml_output.docx'
SRC = r'F:\前途文件\my_test\output\中文核心投稿稿_视觉语义驱动多参数阻抗辅助遥操作方法_格式整理后.docx'
DST = r'F:\前途文件\my_test\output\中文核心投稿稿_视觉语义驱动多参数阻抗辅助遥操作方法_公式编号版.docx'

NSMAP = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
}

W = NSMAP['w']
M = NSMAP['m']


# =========================================================================
# Phase 0: Build OMML template library
# =========================================================================

def build_omath_templates():
    """Extract OMML templates for inline math from pandoc output."""
    with zipfile.ZipFile(PANDOC_DOCX) as zf:
        xml = zf.read('word/document.xml')
    root = etree.fromstring(xml)

    templates = {}
    for para in root.iter(f'{{{W}}}p'):
        omaths = para.findall(f'.//{{{M}}}oMath')
        if not omaths:
            continue
        plain = ''.join(t.text or '' for t in para.iter(f'{{{W}}}t')).strip()
        if len(plain) > 5:
            for om in omaths:
                mt_chars = []
                for mt in om.findall(f'.//{{{M}}}t'):
                    if mt.text:
                        mt_chars.append(mt.text)
                key = ''.join(mt_chars)
                if key and key not in templates:
                    templates[key] = copy.deepcopy(om)

    return templates


# =========================================================================
# Phase 1: Display formula fixing
# =========================================================================

def clear_paragraph_runs(para_elem):
    """Remove all run elements from a paragraph, keeping pPr."""
    for r in list(para_elem.findall(f'{{{W}}}r')):
        para_elem.remove(r)
    # Also remove any w:tab or other content
    for child in list(para_elem):
        if child.tag not in (f'{{{W}}}pPr',):
            if child.tag == f'{{{W}}}r':
                continue  # already removed
            # Keep only pPr


def fix_display_formula(para_elem, om_elem, number, text_width):
    """Replace paragraph content with centered formula + right-aligned number."""

    # Remove all child elements except pPr
    pPr = para_elem.find(f'{{{W}}}pPr')
    children_to_keep = [pPr] if pPr is not None else []
    for child in list(para_elem):
        if child not in children_to_keep:
            para_elem.remove(child)

    # Add tab stops to pPr
    if pPr is None:
        pPr = etree.Element(f'{{{W}}}pPr')
        para_elem.insert(0, pPr)

    # Center justification
    jc = pPr.find(f'{{{W}}}jc')
    if jc is None:
        jc = etree.Element(f'{{{W}}}jc')
        jc.set(f'{{{W}}}val', 'center')
        pPr.append(jc)

    # Tab stops
    tabs = pPr.find(f'{{{W}}}tabs')
    if tabs is not None:
        pPr.remove(tabs)
    tabs = etree.SubElement(pPr, f'{{{W}}}tabs')

    ct = etree.SubElement(tabs, f'{{{W}}}tab')
    ct.set(f'{{{W}}}val', 'center')
    ct.set(f'{{{W}}}pos', str(int(text_width / 2)))

    rt = etree.SubElement(tabs, f'{{{W}}}tab')
    rt.set(f'{{{W}}}val', 'right')
    rt.set(f'{{{W}}}pos', str(int(text_width)))

    # Center tab run
    tab_run = etree.SubElement(para_elem, f'{{{W}}}r')
    tab_rPr = etree.SubElement(tab_run, f'{{{W}}}rPr')
    etree.SubElement(tab_rPr, f'{{{W}}}rFonts').set(f'{{{W}}}ascii', 'Times New Roman')
    etree.SubElement(tab_run, f'{{{W}}}tab')

    # OMath run
    om_run = etree.SubElement(para_elem, f'{{{W}}}r')
    om_run.append(copy.deepcopy(om_elem))

    # Right tab + number
    num_tab_run = etree.SubElement(para_elem, f'{{{W}}}r')
    num_tab_rPr = etree.SubElement(num_tab_run, f'{{{W}}}rPr')
    etree.SubElement(num_tab_rPr, f'{{{W}}}rFonts').set(f'{{{W}}}ascii', 'Times New Roman')
    etree.SubElement(num_tab_run, f'{{{W}}}tab')

    num_run = etree.SubElement(para_elem, f'{{{W}}}r')
    num_rPr = etree.SubElement(num_run, f'{{{W}}}rPr')
    etree.SubElement(num_rPr, f'{{{W}}}rFonts').set(f'{{{W}}}ascii', 'Times New Roman')
    num_text = etree.SubElement(num_run, f'{{{W}}}t')
    num_text.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    num_text.text = f'({number})'


# =========================================================================
# Phase 2: Inline parameter fixing
# =========================================================================

def build_replacement_map(omath_templates):
    """Build: target_text -> OMath mapping."""
    rmap = {}

    # Direct key mappings (OMath key -> target text pattern)
    mappings = [
        # Complex patterns first
        ('c∈{soft,medium,hard}', '(c{,,})'),
        # Values with numbers
        ('Kt=50',  '(K_t=50)'),
        ('Kt=150', '(K_t=150)'),
        ('Kt=200', '(K_t=200)'),
        ('Kr=5',   '(K_r=5)'),
        ('Kr=10',  '(K_r=10)'),
        ('Kr=13',  '(K_r=13)'),
        ('Kf=0.2', '(K_f=0.2)'),
        ('Kf=0.5', '(K_f=0.5)'),
        ('Kf=0.7', '(K_f=0.7)'),
        ('d=0.3',  '(d=0.3)'),
        ('d=0.4',  '(d=0.4)'),
        ('d=0.5',  '(d=0.5)'),
        # Parameter names
        ('Kt',   '(K_t)'),
        ('Kr',   '(K_r)'),
        ('Kf',   '(K_f)'),
        ('vg',   '(v_g)'),
        ('Fg',   '(F_g)'),
        ('Fh',   '(F_h)'),
        ('Fext', '(F_{ext})'),
        ('K(c)', '(K(c))'),
        ('D(c)', '(D(c))'),
        ('xd',   '(x_d)'),
        ('xd(t)','(x_d(t))'),
        ('xΩ(t)','(x_{}(t))'),
        ('ΔxΩ(t)', None),  # Skip - in formulas
        # Simple identifiers
        ('c', '(c)'),
        ('d', '(d)'),
        ('F', '(F)'),
        ('S', '(S)'),
        ('x', '(x)'),
        ('t', '(t)'),
        # Zeta: handled by fix_zeta_in_para separately (not in rmap)
    ]

    for omath_key, target_pat in mappings:
        if target_pat and omath_key in omath_templates:
            rmap[target_pat] = omath_templates[omath_key]

    return rmap


def _get_para_run_texts(para_elem):
    """Return list of (run, [t_elem_list], concatenated_text) for each direct-child run."""
    result = []
    for run in para_elem.findall(f'{{{W}}}r'):
        t_elems = run.findall(f'{{{W}}}t')
        texts = [t.text or '' for t in t_elems]
        result.append((run, t_elems, ''.join(texts)))
    return result


def _remove_run(para_elem, run):
    """Remove a run from its parent."""
    parent = run.getparent()
    if parent is not None:
        parent.remove(run)


def _multi_run_replace(para_elem, pattern, om_elem):
    """
    Find pattern in concatenated text of all runs and replace with OMML.
    Handles patterns that span multiple runs.
    Returns True if a replacement was made.
    """
    run_info = _get_para_run_texts(para_elem)
    full_text = ''.join(ri[2] for ri in run_info)

    pos = full_text.find(pattern)
    if pos < 0:
        return False

    pat_end = pos + len(pattern)

    # Find runs intersecting the pattern
    char_pos = 0
    first_run = first_t_elems = None
    first_start = 0
    last_run = last_t_elems = None
    last_end = 0

    for run, t_elems, text in run_info:
        run_start = char_pos
        run_end = char_pos + len(text)
        char_pos = run_end

        if run_end <= pos:
            continue
        if run_start >= pat_end:
            continue

        if first_run is None:
            first_run = run
            first_t_elems = t_elems
            first_start = max(0, pos - run_start)
        last_run = run
        last_t_elems = t_elems
        last_end = min(len(text), pat_end - run_start)

        if run_end >= pat_end:
            break

    if first_run is None:
        return False

    parent = first_run.getparent()
    insert_idx = list(parent).index(first_run)

    first_text = ''.join(t.text or '' for t in first_t_elems)
    last_text = ''.join(t.text or '' for t in last_t_elems)
    before = first_text[:first_start]
    after = last_text[last_end:]

    same_run = (first_run == last_run)

    # Modify first run: keep before text
    if first_t_elems:
        if not same_run:
            first_t_elems[0].text = before
            for t in first_t_elems[1:]:
                t.text = ''
        else:
            # Same run: will handle after below
            first_t_elems[0].text = before

    # Remove middle runs between first and last (only when spanning multiple runs)
    if not same_run:
        found_first = False
        for run, _, _ in run_info:
            if run == first_run:
                found_first = True
                continue
            if run == last_run:
                break
            if found_first:
                _remove_run(para_elem, run)

    # Handle insertion based on whether pattern is within one run or spans multiple
    if same_run:
        # Pattern entirely within one run: before + OMML + after
        first_t_elems[0].text = before
        om_run = etree.Element(f'{{{W}}}r')
        om_run.append(copy.deepcopy(om_elem))
        parent.insert(insert_idx + 1, om_run)
        if after:
            after_run = etree.Element(f'{{{W}}}r')
            orig_rPr = first_run.find(f'{{{W}}}rPr')
            if orig_rPr is not None:
                after_run.append(copy.deepcopy(orig_rPr))
            after_t = etree.SubElement(after_run, f'{{{W}}}t')
            after_t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
            after_t.text = after
            parent.insert(insert_idx + 2, after_run)
    else:
        # Pattern spans multiple runs: keep before in first run, OMML before runs, keep after in last run
        if last_t_elems:
            last_t_elems[-1].text = after
            for t in last_t_elems[:-1]:
                t.text = ''
        om_run = etree.Element(f'{{{W}}}r')
        om_run.append(copy.deepcopy(om_elem))
        parent.insert(insert_idx, om_run)

    return True


def fix_inline_math_in_para(para_elem, rmap):
    """
    Replace broken math patterns with OMML using multi-run matching.
    """
    total_fixed = 0
    patterns = sorted(rmap.keys(), key=len, reverse=True)

    made_progress = True
    while made_progress:
        made_progress = False
        run_info = _get_para_run_texts(para_elem)
        full_text = ''.join(ri[2] for ri in run_info)

        # Find earliest match
        best_pos = len(full_text) + 1
        best_pattern = None
        for pattern in patterns:
            pos = full_text.find(pattern)
            if 0 <= pos < best_pos:
                best_pos = pos
                best_pattern = pattern

        if best_pattern is None:
            break

        if _multi_run_replace(para_elem, best_pattern, rmap[best_pattern]):
            total_fixed += 1
            made_progress = True

    return total_fixed


# =========================================================================
# Handle zeta: () -> ζ with context
# =========================================================================

def fix_mathrm_in_all_omaths(root):
    """
    Add <m:nor/> to 'diag' and 'sgn' character runs across all OMML elements.
    Pandoc drops the \\mathrm{} styling, so we restore it.
    """
    total_fixed = 0
    for omath in root.findall(f'.//{{{M}}}oMath'):
        # Get all direct child elements that could contain m:r sequences
        for container in omath.iter():
            children = list(container)
            i = 0
            while i < len(children):
                child = children[i]
                if child.tag != f'{{{M}}}r':
                    i += 1
                    continue
                texts = [mt.text or '' for mt in child.findall(f'{{{M}}}t')]
                joined = ''.join(texts)

                if joined not in ('d', 's'):
                    i += 1
                    continue

                target = 'diag' if joined == 'd' else 'sgn'
                runs_to_fix = [child]
                matched = True
                for expected_char in target[1:]:
                    ni = i + len(runs_to_fix)
                    if ni >= len(children):
                        matched = False
                        break
                    nc = children[ni]
                    if nc.tag != f'{{{M}}}r':
                        matched = False
                        break
                    nc_texts = [mt.text or '' for mt in nc.findall(f'{{{M}}}t')]
                    if ''.join(nc_texts) != expected_char:
                        matched = False
                        break
                    runs_to_fix.append(nc)

                if matched and len(runs_to_fix) == len(target):
                    for run in runs_to_fix:
                        if run.find(f'{{{M}}}nor') is None:
                            nor_elem = etree.Element(f'{{{M}}}nor')
                            run.insert(0, nor_elem)
                            total_fixed += 1
                    i += len(runs_to_fix)
                else:
                    i += 1
    return total_fixed


def fix_zeta_in_para(para_elem, templates):
    """Fix () -> zeta with context-based variant selection."""
    zeta_plain = templates.get('ζ')
    zeta_08 = templates.get('ζ=0.8')
    zeta_10 = templates.get('ζ=1.0')
    zeta_12 = templates.get('ζ=1.2')

    if zeta_plain is None:
        return 0

    fixed = 0
    made_progress = True
    while made_progress:
        made_progress = False

        run_info = _get_para_run_texts(para_elem)
        full_text = ''.join(ri[2] for ri in run_info)

        pos = full_text.find('()')
        if pos < 0:
            break

        # Context-based variant
        before_ctx = full_text[:pos]
        if 'soft' in before_ctx[-20:] and '采用' in before_ctx[-20:]:
            chosen = zeta_08 if zeta_08 is not None else zeta_plain
        elif '临界阻尼' in before_ctx[-30:]:
            chosen = zeta_10 if zeta_10 is not None else zeta_plain
        elif 'hard' in before_ctx[-20:] and '采用' in before_ctx[-20:]:
            chosen = zeta_12 if zeta_12 is not None else zeta_plain
        else:
            chosen = zeta_plain

        if chosen is None:
            break

        if _multi_run_replace(para_elem, '()', chosen):
            fixed += 1
            made_progress = True

    return fixed


# =========================================================================
# Main
# =========================================================================

def find_formula_para_index(all_paras, marker):
    """Find paragraph index containing marker text."""
    for i, para in enumerate(all_paras):
        full = ''.join(t.text or '' for t in para.iter(f'{{{W}}}t'))
        if marker in full:
            return i
    return None


def main():
    print("=" * 60)
    print("Direct fix: injecting OMML into target document")
    print("=" * 60)

    # Step 1: Build OMML template library
    print("\n[1] Building OMML templates from pandoc output...")
    templates = build_omath_templates()
    print(f"  {len(templates)} templates extracted")

    # Step 2: Extract display formula OMML
    print("\n[2] Extracting display formulas...")
    with zipfile.ZipFile(PANDOC_DOCX) as zf:
        pandoc_xml = zf.read('word/document.xml')
    pandoc_root = etree.fromstring(pandoc_xml)

    display_omaths = []
    for para in pandoc_root.iter(f'{{{W}}}p'):
        in_table = False
        p = para.getparent()
        while p is not None:
            if p.tag == f'{{{W}}}tbl':
                in_table = True
                break
            p = p.getparent()
        if in_table:
            continue
        omaths = para.findall(f'.//{{{M}}}oMath')
        if not omaths:
            continue
        plain = ''.join(t.text or '' for t in para.iter(f'{{{W}}}t')).strip()
        if len(plain) <= 5:
            display_omaths.append(omaths[0])
            mt_preview = ' '.join(
                mt.text for mt in omaths[0].findall(f'.//{{{M}}}t') if mt.text
            )[:80]
            print(f"  Formula ({len(display_omaths)}): {mt_preview}")

    # Step 3: Load target document
    print("\n[3] Loading target document...")
    shutil.copy2(SRC, DST)

    with zipfile.ZipFile(DST, 'r') as zf:
        all_files = zf.namelist()
        file_data = {name: zf.read(name) for name in all_files}

    xml_path = 'word/document.xml'
    target_root = etree.fromstring(file_data[xml_path])
    all_paras = list(target_root.iter(f'{{{W}}}p'))

    text_width = 11906 - 1700 - 1700  # page - margins

    # ---- Fix display formulas ----
    print("\n[4] Fixing display formulas...")

    formula_markers = [
        ('K_t,K_r', 1),       # check for K_t and K_r together
        ('x_{}(t)-x_{}(t-1)', 2),
        ('x_d(t-1)+Sx_{}', 3),
        ('F=K(c)(x_d-x)', 4),
        ('diag(K_t,K_t', 5),
        ('F_h=', 6),
    ]

    fixed_formulas = set()
    for marker, fnum in formula_markers:
        idx = find_formula_para_index(all_paras, marker)
        if idx is not None:
            para = all_paras[idx]
            full = ''.join(t.text or '' for t in para.iter(f'{{{W}}}t')).strip()
            fix_display_formula(para, display_omaths[fnum - 1], fnum, text_width)
            fixed_formulas.add(fnum)
            print(f"  Fixed ({fnum}) at para {idx}: [{full[:80]}]")
        else:
            print(f"  WARNING: Formula ({fnum}) marker '{marker}' not found")

    # Clean orphan ']' after formula 6
    for i, para in enumerate(all_paras):
        full = ''.join(t.text or '' for t in para.iter(f'{{{W}}}t')).strip()
        if full == ']':
            if i > 0:
                prev_text = ''.join(t.text or '' for t in all_paras[i-1].iter(f'{{{W}}}t'))
                if 'F_h=' in prev_text:
                    for r in list(para.findall(f'{{{W}}}r')):
                        para.remove(r)
                    print(f"  Cleaned orphan ']' after formula (6) at para {i}")

    # Formula (7): insert before '共计...72'
    for i, para in enumerate(all_paras):
        full = ''.join(t.text or '' for t in para.iter(f'{{{W}}}t'))
        if '共计' in full and '72' in full and 7 not in fixed_formulas:
            # Check if previous para already has it
            prev_text = ''.join(t.text or '' for t in all_paras[i-1].iter(f'{{{W}}}t')) if i > 0 else ''
            if '×' not in prev_text:
                new_para = etree.Element(f'{{{W}}}p')
                parent = para.getparent()
                pidx = list(parent).index(para)
                parent.insert(pidx, new_para)
                all_paras.insert(pidx, new_para)
                fix_display_formula(new_para, display_omaths[6], 7, text_width)
                fixed_formulas.add(7)
                print(f"  Inserted formula (7) before para {i}")
            break

    print(f"  Fixed {len(fixed_formulas)}/7 display formulas")

    # ---- Fix inline parameters ----
    print("\n[5] Fixing inline parameters...")
    rmap = build_replacement_map(templates)
    print(f"  Replacement patterns: {len(rmap)}")

    # Identify formula paragraph indices to skip
    formula_indices = set()
    for marker, fnum in formula_markers:
        idx = find_formula_para_index(all_paras, marker)
        if idx is not None:
            formula_indices.add(idx)
    # Also skip the newly inserted formula (7)
    for i, para in enumerate(all_paras):
        full = ''.join(t.text or '' for t in para.iter(f'{{{W}}}t'))
        if full.strip() == '(7)':
            formula_indices.add(i)

    inline_fixed = 0
    zeta_fixed = 0

    for i, para in enumerate(all_paras):
        if i in formula_indices:
            continue

        full = ''.join(t.text or '' for t in para.iter(f'{{{W}}}t')).strip()
        if not full:
            continue
        # Skip reference paragraphs
        if re.match(r'^\[\d+\]', full):
            continue

        # Fix zeta first (context-specific) then other patterns
        zeta_templates = {k: v for k, v in templates.items()
                         if k in ('ζ', 'ζ=0.8', 'ζ=1.0', 'ζ=1.2')}
        z = fix_zeta_in_para(para, zeta_templates)
        zeta_fixed += z

        # Fix regular patterns (no () → won't conflict with zeta)
        n = fix_inline_math_in_para(para, rmap)
        inline_fixed += n

    print(f"  Regular inline fixes: {inline_fixed}")
    print(f"  Zeta fixes: {zeta_fixed}")

    # ---- Fix \\mathrm (diag/sgn roman) ----
    print("\n[6] Fixing \\mathrm{diag} and \\mathrm{sgn} (roman style)...")
    roman_fixed = fix_mathrm_in_all_omaths(target_root)
    print(f"  Added m:nor to {roman_fixed} math runs")

    # ---- Save ----
    print("\n[7] Saving...")
    file_data[xml_path] = etree.tostring(
        target_root, xml_declaration=True, encoding='UTF-8', standalone=True
    )

    with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zf_out:
        for name, data in file_data.items():
            zf_out.writestr(name, data)

    print(f"\nSaved: {DST}")
    print("Done!")


if __name__ == '__main__':
    main()
