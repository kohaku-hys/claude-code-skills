# -*- coding: utf-8 -*-
"""char_count.py — ES の本文が指定字数に収まっているかを数える（es スキル STEP 3 の字数ゲート）。

使い方:
    py ~/.claude/skills/es/scripts/char_count.py <本文ファイル> <指定字数>

数え方（SKILL.md に書いてある約束と同じ）:
  - 改行（\\r と \\n）だけを除き、残りは全角・半角・空白・記号とも1字と数える
  - 本文の1行目が「【○○字／指定△△字】」の見出しなら、それは本文に含めない
合格の範囲: 指定字数の −5% 以上、かつ指定字数以下（例: 指定400字なら 380〜400字）。
  指定字数はふつうフォームの上限なので、超えると入力できないか切られる。だから + 側の余裕は無い。

終了コード: 0=範囲内 / 1=上限超過 または −5% 未満 / 2=引数の誤り・ファイルが無い
出力の1行目は、そのまま ES の冒頭に貼れる「【○○字／指定△△字】」。
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HEADER = re.compile(r"^【\s*\d+\s*字\s*[／/]\s*指定\s*\d+\s*字\s*】\s*$")


def count_chars(text):
    """改行を除いた字数。全角・半角とも1字。"""
    return len(text.replace("\r", "").replace("\n", ""))


def strip_header(text):
    """1行目が字数の見出しなら外す。外したかどうかも返す。"""
    lines = text.split("\n")
    if lines and HEADER.match(lines[0].strip()):
        return "\n".join(lines[1:]), True
    return text, False


def lower_limit(limit):
    """−5% の下限（小数は切り上げ。400→380、250→238）。浮動小数を使わずに整数で計算する。"""
    return (limit * 95 + 99) // 100


def main(argv):
    if len(argv) != 2:
        print("usage: py char_count.py <本文ファイル> <指定字数>")
        return 2
    path, limit_s = argv
    if not os.path.exists(path):
        print(f"ファイルが無い: {path}")
        return 2
    if not limit_s.isdigit() or int(limit_s) <= 0:
        print(f"指定字数は正の整数で渡す: {limit_s!r}")
        return 2
    limit = int(limit_s)

    with open(path, encoding="utf-8-sig") as f:  # メモ帳の BOM を1字と数えない
        text = f.read()
    # 末尾の改行・空白はフォームに貼る時に落ちるので数えない
    text = text.rstrip()
    body, had_header = strip_header(text)
    body = body.strip("\r\n")
    n = count_chars(body)
    low = lower_limit(limit)

    print(f"【{n}字／指定{limit}字】")
    if had_header:
        print("  （1行目の字数見出しは本文に数えていない）")
    if n > limit:
        print(f"NG: 上限を {n - limit} 字超えている（合格は {low}〜{limit} 字）")
        return 1
    if n < low:
        print(f"NG: −5% の下限 {low} 字に {low - n} 字足りない（合格は {low}〜{limit} 字）")
        return 1
    print(f"OK: {low}〜{limit} 字の範囲内")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
