# -*- coding: utf-8 -*-
"""pptx → 各スライドPNG + コンタクトシート（PowerPoint COM / pywin32）。

なぜ存在するか：slide-gen の preview.ps1 は PowerShell 経由で、auto-mode 分類器が
`-ExecutionPolicy Bypass` を Security Weaken として拒否する環境がある（実際に拒否された）。
そこで PowerShell を一切使わず pywin32 だけで pptx をレンダリングし、目視レビュー用の
コンタクトシート `_all.png` を作る。3.9/3.12 どちらでも動く（pywin32 と Pillow があれば可）。

使い方：
  <python> render_deck.py <deck.pptx> [out_dir] [--cols N]
  out_dir 省略時は pptx と同じフォルダに `_preview/` を作る。
  最終行に `_all.png` の絶対パスを出す（それを Read してセルフレビュー）。
"""
import os
import sys
import glob


def main(argv):
    if len(argv) < 2:
        print("usage: render_deck.py <deck.pptx> [out_dir] [--cols N]")
        return 2
    pptx = os.path.abspath(argv[1])
    if not os.path.exists(pptx):
        print("not found:", pptx)
        return 2
    cols = 3
    rest = [a for a in argv[2:]]
    if "--cols" in rest:
        i = rest.index("--cols")
        cols = int(rest[i + 1])
        del rest[i:i + 2]
    out = os.path.abspath(rest[0]) if rest else os.path.join(os.path.dirname(pptx), "_preview")
    os.makedirs(out, exist_ok=True)
    for f in glob.glob(os.path.join(out, "*.png")):
        os.remove(f)

    import subprocess
    import win32com.client
    # 本人が PowerPoint で作業中なら、終わっても PowerPoint は閉じない（Quit すると本人のファイルまで閉じる。2026-10-13）
    try:
        tl = subprocess.run(["tasklist", "/FI", "IMAGENAME eq POWERPNT.EXE"], capture_output=True, text=True).stdout
        running = "POWERPNT.EXE" in tl.upper()
    except Exception:
        running = True
    pp = win32com.client.Dispatch("PowerPoint.Application")
    pres = pp.Presentations.Open(pptx, WithWindow=False)
    try:
        n = pres.Slides.Count
        for i in range(1, n + 1):
            pres.Slides.Item(i).Export(os.path.join(out, "s%02d.png" % i), "PNG", 1280, 720)
        print("exported", n, "slides")
    finally:
        pres.Close()
        if not running:
            pp.Quit()

    from PIL import Image
    imgs = sorted(glob.glob(os.path.join(out, "s*.png")))
    tw = 620
    thumbs = []
    for p in imgs:
        im = Image.open(p).convert("RGB")
        r = tw / im.width
        thumbs.append(im.resize((tw, int(im.height * r))))
    if not thumbs:
        print("no slides rendered")
        return 1
    th = thumbs[0].height
    rows = (len(thumbs) + cols - 1) // cols
    pad = 12
    W = cols * tw + (cols + 1) * pad
    H = rows * th + (rows + 1) * pad
    sheet = Image.new("RGB", (W, H), (230, 233, 238))
    for idx, t in enumerate(thumbs):
        r, c = divmod(idx, cols)
        sheet.paste(t, (pad + c * (tw + pad), pad + r * (th + pad)))
    allp = os.path.join(out, "_all.png")
    sheet.save(allp)
    print("CONTACT_SHEET:", allp, sheet.size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
