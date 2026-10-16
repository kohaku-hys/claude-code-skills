# -*- coding: utf-8 -*-
"""report スキル共通: 提出用表紙PDFの「確定欄」だけを記入して PNG 化する。

確定欄 = テーマ番号/テーマ名/学籍番号/氏名 のように本人が確実に決まっている欄。
班・共同実験者・実験日・提出日・作成時間など **本人/班依存・後日記入の欄は空欄のまま**
（捏造禁止 P-035 の延長。勝手に埋めない）。

要点（テーマ9でハマった点を恒久化）:
 1. 表紙PDFが暗号化されていても **ユーザPWは空のことが多い** → `authenticate("")` で開ける。
 2. PyMuPDF の `insert_text` で漢字を出すには **内蔵フォント `fontname="japan"`** を使う。
    `fontfile=msgothic.ttc` を渡すと漢字が「…」に化ける（TTCのグリフ解決に失敗）。
 3. 記入位置(x,y=baseline)は `find_cover_fields()` でラベル語の座標から当たりを付ける。
    ラベルの y0+8 付近を baseline に、ラベル右端の少し右を x にすると概ね合う。

使い方:
    from fill_cover import fill_cover, find_cover_fields
    # まず座標を調べる（ラベル語→x0,y0,x1,y1 を表示）
    find_cover_fields("レポート表紙.pdf")
    # 確定欄だけ記入して PNG 出力
    fill_cover("レポート表紙.pdf", [
        (108, 103, "9"), (212, 103, "LC共振回路"),
        (212, 138, "s00x0000"), (478, 138, "山田 太郎"),
    ], "figures/cover.png")

CLI:
    python fill_cover.py <cover.pdf>                      # 座標調査（words一覧）
    python fill_cover.py <cover.pdf> <out.png> <entries.json>
        entries.json = [[x, y, "text"], ...]
"""
import sys, json, os
import fitz  # PyMuPDF


def _open(cover_pdf):
    doc = fitz.open(cover_pdf)
    if doc.is_encrypted:
        if not doc.authenticate(""):
            raise RuntimeError(
                f"{cover_pdf}: 空パスワードで開けません。所有者PWではなくユーザPWが設定されています。")
    return doc


def find_cover_fields(cover_pdf, dump_path=None):
    """表紙のテキスト語を (y, x0, x1, text) で並べて返す/出力する。記入座標の当たり付け用。"""
    doc = _open(cover_pdf)
    pg = doc[0]
    rows = sorted((round(w[1], 1), round(w[0], 1), round(w[2], 1), w[4])
                  for w in pg.get_text("words"))
    lines = [f"y={y:6.1f}  x={x0:6.1f}-{x1:6.1f}  {t}" for y, x0, x1, t in rows]
    out = "\n".join(lines)
    if dump_path:
        with open(dump_path, "w", encoding="utf-8") as f:
            f.write(f"PAGE {pg.rect}\n" + out)
    return out


def fill_cover(cover_pdf, entries, out_png, dpi=300, fontsize=11):
    """entries=[(x, y_baseline, text), ...] を内蔵日本語フォントで記入し PNG 化。

    確定欄だけ渡すこと。空欄にすべき欄は entries に含めない。
    """
    doc = _open(cover_pdf)
    pg = doc[0]
    for x, y, txt in entries:
        pg.insert_text((x, y), str(txt), fontname="japan", fontsize=fontsize, color=(0, 0, 0))
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    pg.get_pixmap(dpi=dpi).save(out_png)
    return out_png


if __name__ == "__main__":
    if len(sys.argv) == 2:
        print(find_cover_fields(sys.argv[1]))
    elif len(sys.argv) == 4:
        cover, out_png, entries_json = sys.argv[1], sys.argv[2], sys.argv[3]
        entries = json.load(open(entries_json, encoding="utf-8"))
        print("saved:", fill_cover(cover, [tuple(e) for e in entries], out_png))
    else:
        print(__doc__)
        sys.exit(2)
