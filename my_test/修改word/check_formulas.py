"""Check OMML formulas in section 4.3."""
import sys, zipfile
from lxml import etree
sys.stdout.reconfigure(encoding='utf-8')

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
M = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
DOCX = r'F:\前途文件\my_test\output\中文核心投稿稿_视觉语义驱动多参数阻抗辅助遥操作方法_格式整理后.docx'

with zipfile.ZipFile(DOCX, 'r') as z:
    doc = etree.parse(z.open('word/document.xml'))
body = doc.find('{%s}body' % W)
paras = list(body.findall('{%s}p' % W))

def get_text(p):
    return ''.join(t.text or '' for t in p.iter('{%s}t' % W))

# Show formulas in paras 66-72
for i in range(66, 73):
    para = paras[i]
    math_elems = para.findall('.//{%s}oMath' % M) + para.findall('.//{%s}oMathPara' % M)
    text = get_text(para)
    print(f'=== P{i} === ({len(math_elems)} math elems)')
    print(f'Text: [{text}]')
    if math_elems:
        for mi, me in enumerate(math_elems):
            math_text = ''.join(t.text or '' for t in me.iter('{%s}t' % M))
            print(f'  Math {mi}: [{math_text[:300]}]')
    print()
