"""
Fix formulas in Word document for Chinese journal submission.

Key: Process formulas in REVERSE order (bottom to top) to avoid
COM paragraph index shifting after each modification.
Also: never store paragraph references between modifications.
"""
import sys
import shutil
import traceback
import win32com.client

sys.stdout.reconfigure(encoding='utf-8')

SRC = r'F:\前途文件\my_test\output\中文核心投稿稿_视觉语义驱动多参数阻抗辅助遥操作方法_格式整理后.docx'
DST = r'F:\前途文件\my_test\output\中文核心投稿稿_视觉语义驱动多参数阻抗辅助遥操作方法_公式编号版.docx'

# UnicodeMath for Word equation editor
FORMULA_LATEX = {
    1: r'\Theta(c)={K_t,K_r,\zeta,K_f,d,v_g,F_g}',
    2: r'\Delta x_\Omega(t)=x_\Omega(t)-x_\Omega(t-1)',
    3: r'x_d(t)=x_d(t-1)+S\Delta x_\Omega(t)',
    4: r'F=K(c)(x_d-x)+D(c)(\dot{x}_d-\dot{x})',
    5: r'K(c)="diag"(K_t,K_t,K_t,K_r,K_r,K_r)',
    6: r"F_h=\cases(0&|K_fF_ext|\le d@\operatorname{sgn}(K_fF_ext)(|K_fF_ext|-d)&|K_fF_ext|>d)",
    7: r'3\times4\times6=72',
}

# Formula identification markers
FORMULA_MARKERS = {
    1: ['K_t,K_r', 'F_g'],
    2: ['x_{}(t)=x_{}(t)-x_{}(t-1)'],
    3: ['x_d(t)=x_d(t-1)+S'],
    4: ['F=K(c)(x_d-x)'],
    5: ['diag(K_t'],
    6: ['F_h='],
}


def scan_formulas(doc):
    """Find all formula paragraphs. Returns {formula_num: para_index}."""
    result = {}
    for i in range(1, doc.Paragraphs.Count + 1):
        text = doc.Paragraphs(i).Range.Text.strip()
        if not text or len(text) > 200:
            continue
        if not (text.startswith('[') or 'F_h=' in text):
            continue
        for fnum, markers in FORMULA_MARKERS.items():
            if fnum in result:
                continue
            if all(m in text for m in markers):
                result[fnum] = i
                break
    return result


def find_formula7_context(doc):
    """Find paragraph with '共计' (unique to methods section)."""
    for i in range(1, doc.Paragraphs.Count + 1):
        text = doc.Paragraphs(i).Range.Text
        if '共计' in text and '72' in text:
            return i
    return None


def insert_formula(word, doc, para_idx, latex, number):
    """
    Insert formula equation + right-aligned number at specified paragraph.
    Always accesses paragraph by fresh index.
    """
    text_width = (doc.PageSetup.PageWidth
                  - doc.PageSetup.LeftMargin
                  - doc.PageSetup.RightMargin)

    # Always get fresh paragraph reference
    para = doc.Paragraphs(para_idx)

    # Set up paragraph format
    pf = para.Range.ParagraphFormat
    pf.TabStops.ClearAll()
    pf.TabStops.Add(Position=text_width / 2, Alignment=1)
    pf.TabStops.Add(Position=text_width, Alignment=2)

    # Build formula line
    line = f'\t{latex}\t({number})\r'
    para.Range.Text = line

    # Re-get paragraph after text change
    para = doc.Paragraphs(para_idx)

    # Convert LaTeX to equation
    full_text = para.Range.Text
    last_tab = full_text.rfind('\t')
    if last_tab > 1:
        eq_range = doc.Range(para.Range.Start + 1, para.Range.Start + last_tab)
        eq_range.Select()
        try:
            word.Selection.OMaths.Add(word.Selection.Range)
            if word.Selection.OMaths.Count > 0:
                word.Selection.OMaths(1).BuildUp()
        except Exception as ex:
            print(f"      BuildUp: {ex}")

    return True


def main():
    print("=" * 60)
    print("Formula fixing for Chinese journal submission")
    print("=" * 60)

    word = win32com.client.Dispatch('Word.Application')
    word.Visible = False
    word.DisplayAlerts = 0
    doc = None

    try:
        shutil.copy2(SRC, DST)
        print(f"Working on: {DST}")
        doc = word.Documents.Open(DST)
        print(f"Total paragraphs: {doc.Paragraphs.Count}")

        # --- Scan for formulas ---
        found = scan_formulas(doc)
        print(f"\nFound formulas:")
        for fnum, pidx in sorted(found.items()):
            txt = doc.Paragraphs(pidx).Range.Text.strip()[:80]
            print(f"  ({fnum}) para {pidx}: [{txt}]")

        # --- Fix formulas in REVERSE order (bottom to top) ---
        # This prevents index shifting from affecting earlier formulas
        sorted_nums = sorted(found.keys(), reverse=True)
        print(f"\nProcessing in reverse order: {sorted_nums}")

        for eq_num in sorted_nums:
            pidx = found[eq_num]
            print(f"\nFixing ({eq_num}) at para {pidx}...")

            # Delete orphan ']' paragraph for formula 6
            if eq_num == 6:
                # Check if next paragraph is just ']'
                next_text = doc.Paragraphs(pidx + 1).Range.Text.strip()
                if next_text == ']':
                    print(f"  Deleting orphan ']' at para {pidx + 1}")
                    doc.Paragraphs(pidx + 1).Range.Delete()

            # Re-verify paragraph position hasn't shifted
            # (should be fine since we're going reverse)
            insert_formula(word, doc, pidx, FORMULA_LATEX[eq_num], eq_num)
            print(f"  Done -> ({eq_num})")

        # --- Formula 7: Insert before '共计' paragraph ---
        print(f"\nInserting formula (7)...")
        ctx_idx = find_formula7_context(doc)
        if ctx_idx:
            print(f"  Context at para {ctx_idx}")
            # Insert empty paragraph before context
            ctx_para = doc.Paragraphs(ctx_idx)
            ins_rng = ctx_para.Range.Duplicate
            ins_rng.Collapse(1)  # wdCollapseStart
            ins_rng.InsertBefore('\r\n')

            # Find the newly created empty paragraph (should be at ctx_idx)
            for check_idx in [ctx_idx, ctx_idx - 1]:
                if check_idx < 1:
                    continue
                p = doc.Paragraphs(check_idx)
                if '72' not in p.Range.Text and '共计' not in p.Range.Text:
                    # Check neighbor
                    next_p = doc.Paragraphs(check_idx + 1)
                    if '共计' in next_p.Range.Text and '72' in next_p.Range.Text:
                        insert_formula(word, doc, check_idx, FORMULA_LATEX[7], 7)
                        print(f"  Inserted at para {check_idx}")
                        break
            print(f"  Done -> (7)")
        else:
            print("  WARNING: '共计' paragraph not found!")

        # --- Save ---
        print("\nSaving...")
        doc.Save()
        print(f"Saved: {DST}")
        print("=" * 60)
        print("Done! Open the file to verify.")
        print("=" * 60)

    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()
    finally:
        if doc is not None:
            try:
                doc.Close(SaveChanges=False)
            except Exception:
                pass
        word.Quit()


if __name__ == '__main__':
    main()
