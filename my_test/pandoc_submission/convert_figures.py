from pathlib import Path

import fitz
from PIL import Image


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FIG_DIR = DATA_DIR / "fig"

for svg_path in sorted(FIG_DIR.glob("*.svg")):
    png_path = svg_path.with_suffix(".png")
    svg_data = svg_path.read_bytes()
    # Repair a legacy unescaped comparison sign in one SVG before rendering.
    svg_data = svg_data.replace(b"<75%", b"&lt;75%")
    document = fitz.open(stream=svg_data, filetype="svg")
    page = document[0]
    pixmap = page.get_pixmap(matrix=fitz.Matrix(4, 4), alpha=False)
    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    image.save(png_path, dpi=(300, 300))
    print(f"{svg_path.name} -> {png_path.name}")
