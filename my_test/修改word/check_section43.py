"""Check section 4.3 content."""
import sys, zipfile
from lxml import etree
sys.stdout.reconfigure(encoding='utf-8')

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
DOCX = r'F:\前途文件\my_test\output\中文核心投稿稿_视觉语义驱动多参数阻抗辅助遥操作方法_格式整理后.docx'

with zipfile.ZipFile(DOCX, 'r') as z:
    doc = etree.parse(z.open('word/document.xml'))
body = doc.find('{%s}body' % W)
paras = list(body.findall('{%s}p' % W))

def get_text(p):
    return ''.join(t.text or '' for t in p.iter('{%s}t' % W))

# Find section 4.3 heading
for i in range(60, 80):
    if i < len(paras):
        text = get_text(paras[i])
        if '4.3' in text or ('主端力' in text):
            print(f'--- P{i} (4.3 heading) ---')
            print(text[:200])
            print()
            # Show next 10 paragraphs
            for j in range(i, min(i+12, len(paras))):
                print(f'--- P{j} ---')
                print(get_text(paras[j])[:300])
                print()
            break
