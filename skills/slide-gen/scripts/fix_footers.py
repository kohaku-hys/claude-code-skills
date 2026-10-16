"""フッター採番＋注釈除去: スライド並べ替え後に使う。
各 NN_*.svg のフッター番号を「NN / 総数」に揃え、svg_editor のライブ注釈
(id=_edit_*, data-edit-target, data-edit-annotation) を全除去する。
リネーム自体は別途（tmp名経由で衝突回避）。 usage: python fix_footers.py <svg_dir>"""
import sys, os, re, glob

d = sys.argv[1] if len(sys.argv) > 1 else "."
files = sorted(glob.glob(os.path.join(d, "*.svg")))
total = len(files)
for f in files:
    nn = os.path.basename(f)[:2]
    s0 = open(f, encoding="utf-8").read()
    s = s0
    s = re.sub(r'\s+id="_edit_\d+"', "", s)
    s = re.sub(r'\s+data-edit-target="true"', "", s)
    s = re.sub(r'\s+data-edit-annotation="[^"]*"', "", s)
    # footer: <tspan ... font-weight="bold">NN</tspan> / TOTAL  → NN / total
    s = re.sub(r'(font-weight="bold">)\d{1,2}(</tspan>\s*/\s*)\d+',
               lambda m: m.group(1) + nn + m.group(2) + str(total), s)
    if s != s0:
        open(f, "w", encoding="utf-8").write(s)
        print("fixed", os.path.basename(f), "->", nn, "/", total)
    else:
        print("nochange", os.path.basename(f))
