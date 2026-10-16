#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wrap_ja.py -- 日本語テキストを文節境界で自然に改行する（Google BudouX 使用）。

ppt-master のSVG手書きで、長い日本語（見出し／大ラベル／So What帯／箇条書き／
チャートの軸ラベル・注釈）を「勘」で改行せず、文節境界で割るための常設ツール（$T）。
鉄則「大見出しは 1行=1つの<text>、改行は別<text>を縦に並べる」に沿い、
--svg では tspan/dy を使わず <text> を縦積みで出す（PowerPoint折返し重なりを回避）。

処理:
  1. BudouX(既定 日本語パーサ) で文節分割
  2. 後処理グルー:
       - 数字・小数・単位が文節境界で割れたもの（例 "9"+".9%" → "9.9%"）を結合
  3. パッキング:
       --lines N : N行に均等割り（最大行幅を最小化。見出し向け）
       --width W : 各行を視覚幅 W 以下に貪欲パック（本文/ラベル向け）
       （無指定: 文節分割だけ表示する parse モード）
     どちらも 行頭/行末の約物禁則（、。）」を行頭に置かない等）を守る。
  4. 出力: 既定=改行区切り / --json / --svg（<text>縦積み・貼り付け用）
     -o FILE を付けると UTF-8 でファイル出力（Read で拾えば文字化けしない）。

視覚幅: 全角=1.0, 半角=0.5（east_asian_width 基準）。--width の W は全角文字数の目安。

例:
  python wrap_ja.py "福岡市の水道は全国トップの品質"                # parse（文節を | 区切りで表示）
  python wrap_ja.py "福岡市の水道は全国トップの品質" --lines 2       # 2行に均等割り
  python wrap_ja.py "2026年のダム貯水率9.9%でも断水しなかった" --width 12
  python wrap_ja.py "半導体産業における国際競争力の強化" --lines 2 \
      --svg --x 640 --y 140 --size 54 --anchor middle --fill "#1a1a1a" --weight bold -o out.svgfrag
"""
import sys
import argparse
import json
import unicodedata

try:
    import budoux
except ImportError:
    sys.stderr.write("budoux 未導入: `pip install budoux` を実行してください\n")
    sys.exit(2)

# --- 禁則（日本語の行頭・行末で避ける約物） ---------------------------------
# 行頭禁則: この文字で行を始めない → 前行末尾へ寄せる
KINSOKU_HEAD = set(
    "、。，．・：；？！?!)]}｝）」』】》〉›»”’%‰°℃…ー〜～々ゝゞ"
    "ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮ"  # 小書き仮名・長音は行頭に置かない
)
# 行末禁則: この文字で行を終えない → 次行頭へ送る
KINSOKU_TAIL = set("([{｛（「『【《〈‹«“‘")

_FW_DIGITS = set("０１２３４５６７８９")
_NUM_TAIL = _FW_DIGITS | set("0123456789")
_NUM_HEAD = _NUM_TAIL | set(".,．，")        # 数字の続き（小数点・桁区切り）
_UNIT_HEAD = set("%％‰°℃")                    # 数字直後に付く単位記号


def _reconfigure_utf8():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def char_width(ch):
    return 1.0 if unicodedata.east_asian_width(ch) in ("F", "W", "A") else 0.5


def text_width(s):
    return sum(char_width(c) for c in s)


# --- 分割 + グルー ----------------------------------------------------------
_PARSER = None


def _parser():
    global _PARSER
    if _PARSER is None:
        _PARSER = budoux.load_default_japanese_parser()
    return _PARSER


def segment(text):
    """BudouX で文節分割し、数字・単位の割れを結合して返す。"""
    if not text:
        return []
    segs = _parser().parse(text)
    return _glue_numbers(segs)


def _glue_numbers(segs):
    merged = []
    for s in segs:
        if not s:
            continue
        if merged:
            a = merged[-1][-1]
            b = s[0]
            num_join = (a in _NUM_TAIL) and (b in _NUM_HEAD)
            unit_join = (a in _NUM_TAIL) and (b in _UNIT_HEAD)
            if num_join or unit_join:
                merged[-1] += s
                continue
        merged.append(s)
    return merged


# --- パッキング -------------------------------------------------------------
def pack_width(segs, width):
    """各行を視覚幅 width 以下に貪欲パック。"""
    lines, cur = [], ""
    for s in segs:
        if cur and text_width(cur + s) > width + 1e-9:
            lines.append(cur)
            cur = s
        else:
            cur += s
    if cur:
        lines.append(cur)
    return _apply_kinsoku(lines)


def pack_lines(segs, n):
    """N 行に均等割り（各行の最大幅を最小化 = linear partition）。"""
    if not segs:
        return []
    n = max(1, min(n, len(segs)))
    # 0.5 刻みの視覚幅を 2 倍して整数化し、幅上限を二分探索
    w2 = [int(round(text_width(s) * 2)) for s in segs]
    lo, hi = max(w2), sum(w2)

    def feasible(cap):
        cnt, cur = 1, 0
        for w in w2:
            if cur + w > cap:
                cnt += 1
                cur = w
            else:
                cur += w
        return cnt <= n

    while lo < hi:
        mid = (lo + hi) // 2
        if feasible(mid):
            hi = mid
        else:
            lo = mid + 1
    cap = lo

    lines, cur, curw = [], "", 0
    for s, w in zip(segs, w2):
        if cur and curw + w > cap:
            lines.append(cur)
            cur, curw = s, w
        else:
            cur += s
            curw += w
    if cur:
        lines.append(cur)
    return _apply_kinsoku(lines)


def _apply_kinsoku(lines):
    """行頭・行末の約物禁則を満たすよう文字を隣の行へ寄せる。"""
    lines = [l for l in lines if l != ""]
    for _ in range(50):
        changed = False
        # 行頭禁則: 行の先頭が禁則文字なら前行末尾へ
        for i in range(1, len(lines)):
            while len(lines[i]) > 1 and lines[i][0] in KINSOKU_HEAD:
                lines[i - 1] += lines[i][0]
                lines[i] = lines[i][1:]
                changed = True
        # 行末禁則: 行の末尾が開き括弧等なら次行頭へ
        for i in range(len(lines) - 1):
            while len(lines[i]) > 1 and lines[i][-1] in KINSOKU_TAIL:
                lines[i + 1] = lines[i][-1] + lines[i + 1]
                lines[i] = lines[i][:-1]
                changed = True
        if not changed:
            break
    return [l for l in lines if l != ""]


# --- 出力 -------------------------------------------------------------------
def xml_escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def to_svg(lines, x, y, size, line_height, fill, family, anchor, weight):
    lh = line_height if line_height else round(size * 1.5)
    wattr = ' font-weight="%s"' % weight if weight else ""
    out = []
    for i, ln in enumerate(lines):
        yy = _fmt(y + i * lh)
        out.append(
            '<text x="%s" y="%s" font-family="%s" font-size="%s" '
            'fill="%s" text-anchor="%s"%s>%s</text>'
            % (_fmt(x), yy, family, _fmt(size), fill, anchor, wattr, xml_escape(ln))
        )
    return "\n".join(out)


def _fmt(v):
    return str(int(v)) if float(v).is_integer() else str(v)


def main():
    _reconfigure_utf8()
    ap = argparse.ArgumentParser(
        description="日本語を文節境界で自然改行（BudouX）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("text", nargs="?", help="対象テキスト（省略時は標準入力から読む）")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--lines", type=int, metavar="N", help="N行に均等割り（見出し向け）")
    mode.add_argument("--width", type=float, metavar="W",
                      help="各行の視覚幅上限（全角文字数目安・本文/ラベル向け）")
    ap.add_argument("--json", action="store_true", help="JSONで {segments, lines} を出力")
    ap.add_argument("--svg", action="store_true", help="貼り付け用 <text> 縦積みを出力")
    ap.add_argument("-o", "--out", metavar="FILE", help="結果を UTF-8 でファイル出力")
    # SVG 用
    ap.add_argument("--x", type=float, default=0)
    ap.add_argument("--y", type=float, default=0)
    ap.add_argument("--size", type=float, default=48)
    ap.add_argument("--line-height", dest="line_height", type=float, default=0,
                    help="行送りpx（既定 = size*1.5）")
    ap.add_argument("--fill", default="#1a1a1a")
    ap.add_argument("--family", default="'Yu Gothic'")
    ap.add_argument("--anchor", default="start", choices=["start", "middle", "end"])
    ap.add_argument("--weight", default="", help="例: bold")
    args = ap.parse_args()

    text = args.text if args.text is not None else sys.stdin.read()
    text = (text or "").strip()
    segs = segment(text)

    if args.width is not None:
        lines = pack_width(segs, args.width)
        for ln in lines:
            if text_width(ln) > args.width + 1e-9:
                sys.stderr.write("⚠ 幅超過（分割不能な長い文節）: %s\n" % ln)
    elif args.lines is not None:
        lines = pack_lines(segs, args.lines)
    else:
        lines = None  # parse モード

    if args.json:
        payload = {"segments": segs}
        if lines is not None:
            payload["lines"] = lines
            payload["widths"] = [text_width(l) for l in lines]
        result = json.dumps(payload, ensure_ascii=False, indent=2)
    elif lines is None:
        result = " | ".join(segs)
    elif args.svg:
        result = to_svg(lines, args.x, args.y, args.size, args.line_height,
                        args.fill, args.family, args.anchor, args.weight)
    else:
        result = "\n".join(lines)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(result + "\n")
        sys.stderr.write("wrote %s (%d行)\n" % (args.out, len(lines) if lines else len(segs)))
    else:
        print(result)


if __name__ == "__main__":
    main()
