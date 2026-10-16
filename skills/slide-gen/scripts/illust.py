# -*- coding: utf-8 -*-
"""illust.py — いらすとやで絵を探して保存し、選ぶための一覧画像と出典の記録を作る。/slide-gen の道具箱。

なぜ存在するか：2026-10-13 本人「絵を挿入するだけがいい」「Claude がフリー素材を探す」。動きを付ける
スライドの絵（手・ばね・人など）を、図形の組み立てや手描きでなく、1枚の透明 PNG で入れるため。
写真（CC0/CC）は ppt-master の image_search.py、イラストはこちら。

利用条件（https://www.irasutoya.com/p/faq.html を 2026-10-13 に確認）：
  商用でない使い方（授業・研究室・学会の発表）は点数の制限なく無料。クレジットは要らない（書くなら「いらすとや」）。
  商用は1つの制作物につき20点まで無料。絵そのものを素材として配る・売るのは禁止。雰囲気を壊さない加工は可。

使い方：
  py -3 illust.py "ばね" -o <proj>/images [--max 8]
  → <dir>/irasutoya_01_xxx.png …、<dir>/_候補.png（番号付きの一覧。Read して選ぶ）、<dir>/image_sources.json（出典）
  使わなかった候補は消してよい（image_sources.json の該当行も消す）。
"""
from __future__ import annotations

import argparse
import html as htmllib
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import date

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
TERMS = ("いらすとや：商用でない使い方は点数の制限なく無料・クレジット不要。商用は1制作物20点まで無料。"
         "素材としての再配布は禁止（https://www.irasutoya.com/p/faq.html 2026-10-13 確認）")
HIT = re.compile(r"<a href='(https://www\.irasutoya\.com/[^']+\.html)'><script[^>]*>\s*"
                 r'document\.write\(bp_thumbnail_resize\("([^"]+)","([^"]*)"\)')


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def search(query, limit):
    html = fetch("https://www.irasutoya.com/search?q=" + urllib.parse.quote(query)).decode("utf-8", "replace")
    hits, seen = [], set()
    for page, thumb, title in HIT.findall(html):
        if page in seen:
            continue
        seen.add(page)
        if "thumbnail" in os.path.basename(thumb):
            continue  # 「いろいろな〜」のまとめページの見出し画像（jpg・背景が透明でない）
        # 旧型 …/s72-c/name.png と、新型 …/AVvXsE…=s72-c（ファイル名なし）の両方を 800px に
        big = re.sub(r"=s\d+(-c)?$", "=s800", re.sub(r"/s\d+(-c)?/", "/s800/", thumb))
        hits.append({"page": page, "image_url": big, "title": htmllib.unescape(title)})
        if len(hits) >= limit:
            break
    return hits


def contact(dir_, items):
    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.truetype(r"C:\Windows\Fonts\meiryo.ttc", 18)
    except Exception:
        font = ImageFont.load_default()
    cell, pad = 260, 10
    cols = 4
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (cell + pad) + pad, rows * (cell + 40 + pad) + pad), (235, 240, 246))
    d = ImageDraw.Draw(sheet)
    for k, it in enumerate(items):
        im = Image.open(os.path.join(dir_, it["file"])).convert("RGBA")
        im.thumbnail((cell, cell))
        x = pad + (k % cols) * (cell + pad)
        y = pad + (k // cols) * (cell + 40 + pad)
        sheet.paste(im, (x + (cell - im.width) // 2, y + (cell - im.height) // 2), im)
        d.text((x, y + cell + 4), f"{k + 1}. {it['title'][:12]}", font=font, fill=(20, 20, 20))
    out = os.path.join(dir_, "_候補.png")
    sheet.save(out)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="いらすとやで絵を探して保存する")
    ap.add_argument("query", help="日本語の検索語（例：ばね、指さし、男の人 説明）")
    ap.add_argument("-o", "--out", required=True, help="保存先のフォルダ（例 <proj>/images）")
    ap.add_argument("--max", type=int, default=8)
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    os.makedirs(args.out, exist_ok=True)
    hits = search(args.query, args.max)
    if not hits:
        print(f"「{args.query}」は見つからなかった。言い方を変える（例：ばね→スプリング、手→指さし）")
        return 1
    src_path = os.path.join(args.out, "image_sources.json")
    sources = json.load(open(src_path, encoding="utf-8")) if os.path.exists(src_path) else []
    saved = []
    for k, h in enumerate(hits, 1):
        name = os.path.basename(urllib.parse.urlparse(h["image_url"]).path)
        if not re.search(r"\.(png|jpe?g|gif)$", name, re.I) or len(name) > 60:
            # 新型の URL は名前が無く長い ID だけ（2026-10-14「一軒家」で MAX_PATH を超えて止まった）
            name = re.sub(r"\.html$", "", os.path.basename(h["page"]))[:40] + ".png"
        fn = f"irasutoya_{k:02d}_{name}"
        try:
            data = fetch(h["image_url"])
        except Exception as e:
            print(f"  取れなかった: {h['title']} ({e})")
            continue
        with open(os.path.join(args.out, fn), "wb") as f:
            f.write(data)
        rec = {"file": fn, "title": h["title"], "page": h["page"], "image_url": h["image_url"],
               "site": "いらすとや", "terms": TERMS, "saved": date.today().isoformat(), "query": args.query}
        sources = [s for s in sources if s.get("file") != fn] + [rec]
        saved.append(rec)
        print(f"  {len(saved)}. {h['title']}  {fn}")
    with open(src_path, "w", encoding="utf-8") as f:
        json.dump(sources, f, ensure_ascii=False, indent=1)
    if saved:
        print("CANDIDATES:", contact(args.out, saved))
    print("SOURCES:", src_path)
    return 0 if saved else 1


if __name__ == "__main__":
    raise SystemExit(main())
