# -*- coding: utf-8 -*-
"""linkdle_check.py の回帰テスト。

    py ~/.claude/skills/linkdle/scripts/tests/test_linkdle_check.py
    py -m pytest ~/.claude/skills/linkdle/scripts/tests -q

固定していること:
  1. 約束を守った投稿は合格（exit 0）
  2. 300字未満・900字超は不合格、601〜900字は注意だけ（合格のまま）
  3. ハッシュタグが2個・6個は不合格。「C#」はタグに数えない
  4. 最初の文が140字を超える／冒頭140字に具体が無い投稿は不合格
  5. 「〜について書きます」型の予告は不合格。「〜について話しました」は通す
  6. 学籍番号（s00x0000・00x0000 の形）は不合格
  7. 引数の誤りは exit 2
"""
import os
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "linkdle_check.py")

HOOK = "駅前の屋台通りと商店街で、2日間に42人へ聞き取りをしました。\n\n"
# 1文36字前後の本文。回数を変えて長さを作る
FILLER = "屋台を知っている人は34人で、働きに来ている方ほど使ってみたいと答えてくれました。\n"
TAGS = "\n#商店街 #屋台 #地域調査"


def post(n_filler, hook=HOOK, tags=TAGS, extra=""):
    return hook + FILLER * n_filler + extra + tags


def run(text):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(text)
        path = f.name
    try:
        r = subprocess.run([sys.executable, SCRIPT, path], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
        return r.returncode, r.stdout
    finally:
        os.unlink(path)


def main():
    fails = []

    # 1. 合格する投稿（約390字）
    code, out = run(post(9))
    if code != 0:
        fails.append(f"約束どおりの投稿が不合格:\n{out}")

    # 2. 長さ
    code, out = run(post(3))
    if code != 1 or "足りない" not in out:
        fails.append(f"300字未満を合格にした (exit={code})")
    code, out = run(post(16))
    if code != 0 or "[注意]" not in out:
        fails.append(f"601〜900字で注意が出ない、または不合格にした (exit={code}):\n{out}")
    code, out = run(post(25))
    if code != 1 or "上限は 900 字" not in out:
        fails.append(f"900字超を合格にした (exit={code})")

    # 3. ハッシュタグ
    code, out = run(post(9, tags="\n#商店街 #屋台"))
    if code != 1 or "ハッシュタグが 2 個" not in out:
        fails.append(f"タグ2個を合格にした (exit={code})")
    code, out = run(post(9, tags="\n#商店街 #屋台 #地域調査 #建築 #地域 #大学生"))
    if code != 1 or "ハッシュタグが 6 個" not in out:
        fails.append(f"タグ6個を合格にした (exit={code})")
    code, out = run(post(9, extra="授業では C# も少し触りました。\n"))
    if "ハッシュタグ 3 個" not in out:
        fails.append("「C#」をハッシュタグに数えた:\n" + out)

    # 4. フック
    long_hook = "この夏は" + "いろいろなことがあって考えることが多かったのですが" * 6 + "商店街に行きました。\n\n"
    code, out = run(post(9, hook=long_hook))
    if code != 1 or "最初の文が" not in out:
        fails.append(f"140字を超える最初の文を合格にした (exit={code})")
    # 具体の無い文だけで冒頭140字を埋める（FILLER の「34人」が140字の外に出るように）
    vague_hook = "この夏は、ずっと考えていたことを確かめに行きました。\n\n" + "とても楽しかったです。\n" * 12
    code, out = run(post(9, hook=vague_hook))
    if code != 1 or "具体" not in out:
        fails.append(f"冒頭140字に具体が無い投稿を合格にした (exit={code}):\n{out}")

    # 5. 予告
    code, out = run(post(9, hook="今日は駅前の屋台について書きます。42人に聞いた話です。\n\n"))
    if code != 1 or "について書きます" not in out:
        fails.append(f"「について書きます」を合格にした (exit={code})")
    code, out = run(post(9, extra="最終日は先生と進路について話しました。\n"))
    if code != 0:
        fails.append(f"「について話しました」を予告と誤検出した:\n{out}")

    # 6. 学籍番号
    for sid in ("s00x0000", "00x0000"):
        code, out = run(post(9, extra=f"学籍番号は {sid} です。\n"))
        if code != 1 or "学籍番号" not in out:
            fails.append(f"学籍番号 {sid} を見逃した (exit={code})")
        if sid in out:
            fails.append(f"学籍番号 {sid} をそのまま出力した（伏せ字にしていない）")

    # 7. 引数の誤り
    r = subprocess.run([sys.executable, SCRIPT], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 2:
        fails.append(f"引数なしで exit 2 にならない (exit={r.returncode})")

    if fails:
        print("== test_linkdle_check: FAIL ==")
        for x in fails:
            print("  NG:", x)
        return 1
    print("== test_linkdle_check: PASS（7項目）==")
    return 0


def test_linkdle_check():
    """pytest から回す時の入口（py -m pytest linkdle/scripts/tests -q）。中身は main() と同じ7項目。"""
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
