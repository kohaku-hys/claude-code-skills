"""report/pdf_layout_check.py - PDF の折り返しで読みにくい所を列挙する（Word 書き出し後の目視の補助・P-053）

usage:
    py pdf_layout_check.py <pdf> [<pdf> ...]

検出する物（すべて [警告]。exit 0。見つかったら本文や列幅を直して再書き出しする）:
- 行頭に長音「ー」・小さい仮名（っゃゅょ など）が来る折り返し（例「サーバ／ーには」「デジタルマルチメ／ータ」）
    → 原因は禁則処理が標準レベルなこと。生成側で Word の settings.xml に w:strictFirstAndLastChars を立てると直る
- 「I－V」「V－I」の途中改行（行末が I／V で次の行が「－V」「－I」）
- URL がハイフンや記号の直後で切れる折り返し → URL は独立した行にする

表の1字折り返し（「表／示」）は文字の並びだけでは判定できないので、この検査の対象外。
表1〜数ページを dpi 150 で切り出して目視する（列幅は 全角1字＝フォントpt×0.0353 cm、必要幅＝字数×それ＋余白 0.38 cm で見積もる）。
"""
import os
import re
import sys

LINE_HEAD_NG = 'ーぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ'


def bad_breaks(prev_line, next_line):
    """連続する2行（同じ段落内）の折り返しに問題があれば、その説明の一覧を返す"""
    a, c = prev_line.rstrip(), next_line.lstrip()
    out = []
    if not a or not c:
        return out
    if c[0] in LINE_HEAD_NG:
        out.append('行頭に長音・小さい仮名「%s」' % c[0])
    if re.search(r'[IV]$', a) and re.match(r'^[－\-]\s*[IV]', c):
        out.append('「I－V」の途中改行')
    if re.search(r'https?://\S*[-/._]$', a):
        out.append('URL が記号の直後で切れている')
    return out


def check_pdf(path):
    import fitz
    d = fitz.open(path)
    found = []
    for pi, page in enumerate(d, 1):
        for b in page.get_text('blocks'):
            lines = [ln for ln in b[4].split('\n') if ln != '']
            for a, c in zip(lines, lines[1:]):
                for why in bad_breaks(a, c):
                    found.append((pi, why, a.rstrip()[-10:], c.lstrip()[:10]))
    return len(d), found


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')   # cp932 コンソール対策（import 時には触らない）
    except Exception:
        pass
    if len(sys.argv) < 2:
        print('usage: py pdf_layout_check.py <pdf> [<pdf> ...]')
        sys.exit(2)
    for path in sys.argv[1:]:
        n, found = check_pdf(path)
        print('== %s（%d頁）' % (os.path.basename(path), n))
        if not found:
            print('  [OK] 読みにくい折り返しなし')
        for pi, why, a, c in found:
            print('  [警告] p%d %s: 「…%s」／「%s…」' % (pi, why, a, c))


if __name__ == '__main__':
    main()
