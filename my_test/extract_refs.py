"""Build GB/T 7714 reference entries from actual PDF metadata."""
import os, sys, re
from PyPDF2 import PdfReader

sys.stdout.reconfigure(encoding='utf-8')

REF_DIR = r'F:\前途文件\my_test\references'

def get_pdf_info(filepath):
    """Extract basic metadata from PDF."""
    try:
        reader = PdfReader(filepath)
        info = reader.metadata
        title = None
        authors = None
        subject = None

        if info:
            title = info.get('/Title', None)
            authors = info.get('/Author', None)
            subject = info.get('/Subject', None)

        # Get first page text
        first_page = ""
        try:
            if reader.pages:
                first_page = reader.pages[0].extract_text()[:3000]
        except:
            pass

        return {
            'title': title,
            'authors': authors,
            'subject': subject,
            'first_page': first_page,
            'pages': len(reader.pages),
        }
    except Exception as e:
        return {'error': str(e)}

def extract_doi(subject_str):
    """Extract DOI from subject string."""
    if not subject_str:
        return None
    m = re.search(r'10\.\d{4,}/[^\s;]+', subject_str)
    return m.group(0) if m else None

def extract_year(subject_str):
    """Extract year from subject string."""
    if not subject_str:
        return None
    # Pattern: JournalName;Year;Vol;Issue;DOI
    parts = subject_str.split(';')
    if len(parts) >= 2:
        try:
            return int(parts[1].strip())
        except:
            pass
    return None

def extract_journal(subject_str):
    """Extract journal name from subject string."""
    if not subject_str:
        return None
    parts = subject_str.split(';')
    if parts:
        j = parts[0].strip()
        # Expand abbreviations
        j = j.replace('IEEE Trans Robot', 'IEEE Transactions on Robotics')
        return j
    return None

# Process all PDFs
results = []
for fname in sorted(os.listdir(REF_DIR)):
    if not fname.endswith('.pdf'):
        continue

    info = get_pdf_info(os.path.join(REF_DIR, fname))
    info['filename'] = fname
    results.append(info)

# Now build properly formatted GB/T 7714 reference entries
# Based on actual PDF metadata
print("=== REFERENCE ENTRIES FROM ACTUAL PDFs ===\n")

for i, r in enumerate(results):
    print(f"PDF {i+1}: {r['filename']}")
    print(f"  Title:   {r.get('title', 'N/A')[:120]}")
    print(f"  Authors: {r.get('authors', 'N/A')[:120]}")
    print(f"  Subject: {r.get('subject', 'N/A')[:120]}")
    print(f"  DOI:     {extract_doi(r.get('subject', ''))}")
    print(f"  Year:    {extract_year(r.get('subject', ''))}")
    print(f"  Pages:   {r.get('pages', 'N/A')}")
    print()

# Identify discrepancies with current 参考文献清单
print("\n" + "="*80)
print("KEY DISCREPANCIES vs 参考文献清单:")
print("="*80)
discrepancies = [
    "1. Hogan 1984 PDF is ACC conference version, not ASME 1985 journal version",
    "2. Hogan 1985 Part II PDF downloaded but NOT in 参考文献清单 (could be used)",
    "3. Oliva PDF is IEEE RA-L 2021, not IROS 2018 as listed in 参考文献清单",
    "4. Franka PDF: IEEE RAM 2022 vol.29(2), NOT Gazen 2020 vol.27(4) as listed",
    "5. Morrison PDF first page shows different paper - metadata may be wrong",
    "6. Dong 2024 paper NOT in 参考文献清单 (extra downloaded paper)",
    "7. MISSING PDFs: [2]Hogan ICRA 1987, [5]Roveda 2016, [11]Hokayem 2006, [16]Ultralytics, [26]Hart 1988, [27]Hart 2006",
]
for d in discrepancies:
    print(f"  {d}")
