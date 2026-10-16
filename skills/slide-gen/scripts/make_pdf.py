"""PDF化: PNG ディレクトリ（スライド番号順）を1つのPDFに結合。
render_png.ps1 で書き出した PNG を渡す。Word COM のPDFは環境によってハングする（裏に残った WINWORD.EXE）のでこの方式。
usage: python make_pdf.py <png_dir> <out.pdf>"""
import sys, os, re
from PIL import Image

d = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(d, "deck.pdf")

def num(f):
    m = re.search(r"(\d+)", f)
    return int(m.group(1)) if m else 0

files = sorted([f for f in os.listdir(d)
                if f.lower().endswith(".png") and not f.startswith("_")], key=num)
ims = [Image.open(os.path.join(d, f)).convert("RGB") for f in files]
if not ims:
    print("no png in " + d); sys.exit(1)
ims[0].save(out, "PDF", save_all=True, append_images=ims[1:], resolution=150.0)
print(out + "  (%d pages)" % len(ims))
