# Project: 中文核心投稿稿 — 视觉语义驱动多参数阻抗辅助遥操作方法

Academic paper (《制造业自动化》journal format) about vision-semantics-driven multi-parameter impedance-assisted teleoperation.

## Docx manipulation workflow

**CRITICAL: Never use python-docx.** It strips OMML math formulas (`<m:oMath>`). Always use lxml + zipfile directly.

```python
import zipfile
from lxml import etree

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
M = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
XML_NS = 'http://www.w3.org/XML/1998/namespace'

# Read
with zipfile.ZipFile(DOCX, 'r') as z:
    doc = etree.fromstring(z.read('word/document.xml'))

# Modify XML...

# Write (will fail if file locked by Word — save to alt path as fallback)
new_xml = etree.tostring(doc, xml_declaration=True, encoding='UTF-8', standalone=True)
data['word/document.xml'] = new_xml
with zipfile.ZipFile(DOCX, 'w', zipfile.ZIP_DEFLATED) as zout:
    for name, d in data.items():
        zout.writestr(name, d)
```

## Key file paths

- **Target output**: `F:\前途文件\my_test\output\中文核心投稿稿_视觉语义驱动多参数阻抗辅助遥操作方法_格式整理后.docx`
- **Git source (formulas numbered)**: commit `7a16e64` — `公式编号版.docx` (has 19 OMML formula paragraphs)
- **Backup markdown with 23 refs**: `F:\前途文件\my_test\data\中文核心投稿稿_视觉语义驱动多参数阻抗辅助遥操作方法_格式整理前备份.md`

## Processing scripts

| Script | Purpose |
|--------|---------|
| `format_with_lxml.py` | Apply journal formatting (fonts, sizes, spacing, headings) preserving OMML |
| `apply_23refs.py` | Replace refs with 23-entry scheme, insert citations in body at correct positions |
| `fix_section43.py` | Fix section 4.3 formula numbering (v1, superseded by v2) |
| `fix_section43_v2.py` | Fix section 4.3: correct OMML subscripts, right-align formula numbers, rebuild param explanations |
| `check_section43.py` | Diagnostic: show section 4.3 paragraph content |
| `check_formulas.py` | Diagnostic: show OMML formula elements in a range |

## Namespaces and XML patterns

- `W` = `http://schemas.openxmlformats.org/wordprocessingml/2006/main` — Word elements (`w:p`, `w:r`, `w:t`, `w:pPr`, etc.)
- `M` = `http://schemas.openxmlformats.org/officeDocument/2006/math` — OMML math (`m:oMath`, `m:r`, `m:t`, `m:sSub`, etc.)
- `XML_NS` = `http://www.w3.org/XML/1998/namespace` — used for `xml:space="preserve"`

### Key XML structures

**Paragraph**: `<w:p>` containing `<w:pPr>` (formatting) + `<w:r>` (runs) + `<m:oMath>` (formulas)

**Formula with right-aligned number**:
```xml
<w:pPr>
  <w:tabs>
    <w:tab w:val="center" w:pos="4253"/>
    <w:tab w:val="right" w:pos="8506"/>
  </w:tabs>
</w:pPr>
<w:r><w:tab/></w:r>          <!-- tab to center -->
<m:oMath>...</m:oMath>       <!-- formula centered -->
<w:r><w:tab/><w:t>(N)</w:t></w:r>  <!-- tab to right, then number -->
```

**OMML subscript (f_ext)**:
```xml
<m:sSub>
  <m:e><m:r><m:t>f</m:t></m:r></m:e>
  <m:sub><m:r><m:t>ext</m:t></m:r></m:sub>
</m:sSub>
```

**Run formatting**: `w:rPr/w:rFonts` (fonts), `w:rPr/w:sz` (size in half-points, e.g. 24=12pt), `w:rPr/w:b` (bold), `w:rPr/w:vertAlign@val='superscript'`

**Paragraph formatting**: `w:pPr/w:spacing` (line spacing), `w:pPr/w:jc` (alignment), `w:pPr/w:ind` (indent)

## Paper structure (158 paragraphs, 19 formulas, 23 refs)

- Authors: first 3 (马凤杰, 张华, 周依霖) = ¹ 上海工程技术大学; last 2 (曹其新, 曹创) = ² 上海交通大学
- Citation scheme: individual [1]-[23] scattered in body text, not grouped ranges
- Section 4.3 (主端力反馈): P66-P74, formulas (6) and (7)

## Common pitfalls

- `get_text(para)` only extracts `w:t` text, NOT `m:t` math text — use separate extraction for OMML content
- `rebuild_para_text()` preserves math elements but consolidates all `w:t` into first run — breaks inline math interleaving
- XPath with Clark notation like `'.//{%s}tab' % W` works, but `'.//{%s}tabs/{%s}tab' % W` needs `% (W, W)`
- Word locks the file — save to alt path if PermissionError, then copy over when closed
- PowerShell `>` corrupts binary docx — use bash or python file operations instead
- Git operations on docx files: use `git show` with bash redirection, not PowerShell

## Reproducibility

```powershell
pip install lxml
python F:\前途文件\my_test\format_with_lxml.py
python F:\前途文件\my_test\apply_23refs.py
python F:\前途文件\my_test\fix_section43_v2.py
```

All scripts are idempotent. Input: `公式编号版.docx` (git commit `7a16e64`).
