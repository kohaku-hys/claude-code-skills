# -*- coding: utf-8 -*-
"""linkdle_check.py — LinkedIn 投稿の下書きが linkdle の約束（SKILL.md STEP 2・注意事項）を守っているかを見る。

使い方:
    py ~/.claude/skills/linkdle/scripts/linkdle_check.py <下書きファイル>

見るもの:
  1. 長さ   … ハッシュタグを除いた本文の字数（改行を除き、全角・半角とも1字）。
               300〜600字が目安。601〜900字は「濃い体験談のときだけ可」の注意（不合格にはしない）。
               300字未満・900字超は不合格
  2. タグ   … ハッシュタグ（#語）が3〜5個
  3. フック … LinkedIn は冒頭の約140字しか見えない。最初の文が140字以内で終わっていて、
               冒頭140字に具体（数字・カギ括弧・英字語・カタカナ語のどれか）がある
  4. 予告   … 「〜について書きます」型（本文が自分自身を話題にする書き出し）が無い
  5. 学籍番号 … s00x0000・00x0000 のような「数字2桁＋英字1字＋数字4桁」が無い（個人情報）
終了コード: 0=合格（注意は出ることがある） / 1=不合格が1つ以上 / 2=引数の誤り・ファイルが無い
AIくささは別の検査で見る（このスクリプトは LinkedIn 固有の約束だけ）。
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MIN_CHARS, SOFT_MAX, HARD_MAX = 300, 600, 900
MIN_TAGS, MAX_TAGS = 3, 5
HOOK_CHARS = 140

# 「C#」のような英数字の直後の # はタグではない。「# 見出し」のように空白が続くものも違う
HASHTAG = re.compile(r"(?<![0-9A-Za-z&])[#＃][^\s#＃]+")
# 具体の目印（数字・カギ括弧・英字語・カタカナ語）
CONCRETE = re.compile(r"[0-9０-９]|「|[A-Za-z]{2,}|[ァ-ヴ][ァ-ヴー]+")
# 「文書自身が話題」になる書き出し（〜について書きます 等）
ANNOUNCE = re.compile(r"について(書きます|書いていきます|書きたいと思います"
                      r"|(まとめ|述べ|紹介し)(ます|ていきます|たいと思います))")
STUDENT_ID = re.compile(r"(?<![0-9])[sS]?[0-9]{2}[A-Za-z][0-9]{4}(?![0-9])")
SENT_END = re.compile(r"[。！？!?]|\n")


def body_chars(text):
    """ハッシュタグを除いた本文の字数（改行と行頭・行末の空白は数えない）。"""
    n = 0
    for line in text.splitlines():
        n += len(HASHTAG.sub("", line).strip())
    return n


def check(text):
    """(不合格のリスト, 注意のリスト, 字数, タグ数) を返す。"""
    ng, warn = [], []
    text = text.strip()

    # 1. 長さ
    n = body_chars(text)
    if n < MIN_CHARS:
        ng.append(f"本文が {n} 字。{MIN_CHARS} 字に {MIN_CHARS - n} 字足りない")
    elif n > HARD_MAX:
        ng.append(f"本文が {n} 字。濃い体験談でも上限は {HARD_MAX} 字（{n - HARD_MAX} 字超え）")
    elif n > SOFT_MAX:
        warn.append(f"本文が {n} 字。目安の {SOFT_MAX} 字を超えている（濃い体験談のときだけ {HARD_MAX} 字まで可）")

    # 2. ハッシュタグ
    tags = HASHTAG.findall(text)
    if len(tags) < MIN_TAGS or len(tags) > MAX_TAGS:
        ng.append(f"ハッシュタグが {len(tags)} 個（{MIN_TAGS}〜{MAX_TAGS} 個にする）: {' '.join(tags)}")

    # 3. フック（冒頭140字）
    head = text[:HOOK_CHARS]
    m = SENT_END.search(text)
    first_end = m.start() + 1 if m else len(text)
    if first_end > HOOK_CHARS:
        ng.append(f"最初の文が {first_end} 字目まで続いている。{HOOK_CHARS} 字で折りたたまれるので、その前で言い切る")
    if not CONCRETE.search(head):
        ng.append(f"冒頭 {HOOK_CHARS} 字に具体（数字・「」・固有名詞）が無い。場面か数字で止める")

    # 4. 予告の書き出し
    for m in ANNOUNCE.finditer(text):
        ng.append(f"「{m.group(0)}」型の予告がある。何があったかから書き始める")

    # 5. 学籍番号
    for m in STUDENT_ID.finditer(text):
        masked = m.group(0)[:3] + "*" * (len(m.group(0)) - 3)
        ng.append(f"学籍番号らしき文字列（{masked}）がある。載せない")

    return ng, warn, n, len(tags)


def main(argv):
    files = [a for a in argv if not a.startswith("--")]
    if len(files) != 1:
        print("usage: py linkdle_check.py <下書きファイル>")
        return 2
    if not os.path.exists(files[0]):
        print(f"ファイルが無い: {files[0]}")
        return 2
    with open(files[0], encoding="utf-8-sig") as f:
        text = f.read()
    ng, warn, n, n_tags = check(text)
    print(f"-- 本文 {n} 字 / ハッシュタグ {n_tags} 個 --")
    for w in warn:
        print(f"  [注意] {w}")
    if ng:
        print(f"== linkdle チェック: 不合格 {len(ng)} 件 ==")
        for x in ng:
            print(f"  [NG] {x}")
        return 1
    print("== linkdle チェック: 合格 ==")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
