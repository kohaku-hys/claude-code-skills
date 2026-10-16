"""コンタクトシート: PNG ディレクトリを1枚の _all.png に並べる（スライド番号順）。
画像APIに大量Readさせず一括レビューするため。  usage: python montage.py <png_dir> [cols]
注: ファイル内で // を使わない（PowerShell経由だとガード誤検知するため int(a/b) で割る）。"""
import sys, os, re, math
from PIL import Image

d = sys.argv[1]
cols = int(sys.argv[2]) if len(sys.argv) > 2 else 3

def num(f):
    m = re.search(r"(\d+)", f)
    return int(m.group(1)) if m else 0

files = sorted([f for f in os.listdir(d)
                if f.lower().endswith(".png") and not f.startswith("_")], key=num)
ims = []
for f in files:
    im = Image.open(os.path.join(d, f)).convert("RGB")
    im.thumbnail((440, 440))
    ims.append(im)
if not ims:
    print("no png in " + d); sys.exit(1)
cw = max(i.width for i in ims); ch = max(i.height for i in ims); pad = 8
rows = int(math.ceil(len(ims) / float(cols)))
W = cols * cw + (cols + 1) * pad
H = rows * ch + (rows + 1) * pad
sheet = Image.new("RGB", (W, H), (235, 235, 235))
for i, im in enumerate(ims):
    r, c = divmod(i, cols)
    x = pad + c * (cw + pad) + int((cw - im.width) / 2)
    y = pad + r * (ch + pad) + int((ch - im.height) / 2)
    sheet.paste(im, (x, y))
out = os.path.join(d, "_all.png")
sheet.save(out)
print(out)
