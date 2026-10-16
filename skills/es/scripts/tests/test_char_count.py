# -*- coding: utf-8 -*-
"""char_count.py の回帰テスト。

    py ~/.claude/skills/es/scripts/tests/test_char_count.py
    py -m pytest ~/.claude/skills/es/scripts/tests -q

固定していること:
  1. 改行は数えない。全角・半角・空白は1字
  2. 指定字数ちょうど・−5% ちょうどは合格（exit 0）
  3. 上限を1字でも超えたら exit 1（+5% の余裕は無い）
  4. −5% を1字でも下回ったら exit 1
  5. −5% の下限は切り上げ（250字指定なら238字から）
  6. 1行目の【○○字／指定△△字】は本文に数えない
  7. 引数の誤りは exit 2
"""
import os
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "char_count.py")


def run(text, *args):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8", newline="") as f:
        f.write(text)
        path = f.name
    try:
        r = subprocess.run([sys.executable, SCRIPT, path, *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
        return r.returncode, r.stdout
    finally:
        os.unlink(path)


def main():
    fails = []

    # 1. 改行を除く・全角半角とも1字（「あa 1」は4字＋改行）
    code, out = run("あa 1\r\nいb\n", "6")
    if "【6字／指定6字】" not in out:
        fails.append("改行を除いて全角・半角・空白を1字で数えていない: " + out)

    # 2. ちょうど・下限ちょうど
    code, out = run("あ" * 400, "400")
    if code != 0:
        fails.append(f"指定字数ちょうどが不合格 (exit={code})")
    code, out = run("あ" * 380, "400")
    if code != 0:
        fails.append(f"−5% ちょうど（380/400）が不合格 (exit={code})")

    # 3. 上限超過
    code, out = run("あ" * 401, "400")
    if code != 1 or "超えている" not in out:
        fails.append(f"上限を1字超えても合格にした (exit={code})")

    # 4. 下限割れ
    code, out = run("あ" * 379, "400")
    if code != 1 or "足りない" not in out:
        fails.append(f"−5% を1字下回っても合格にした (exit={code})")

    # 5. 切り上げ（250 × 0.95 = 237.5 → 238）
    code, out = run("あ" * 237, "250")
    if code != 1:
        fails.append("250字指定で237字を合格にした（下限は238字）")
    code, out = run("あ" * 238, "250")
    if code != 0:
        fails.append("250字指定で238字を不合格にした")

    # 6. 字数見出しは数えない
    code, out = run("【400字／指定400字】\n" + "あ" * 400, "400")
    if code != 0 or "【400字／指定400字】" not in out:
        fails.append("1行目の字数見出しを本文に数えている: " + out)

    # 7. 引数の誤り
    code, out = run("あ", "abc")
    if code != 2:
        fails.append(f"字数が数字でないのに exit 2 にならない (exit={code})")
    r = subprocess.run([sys.executable, SCRIPT], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 2:
        fails.append(f"引数なしで exit 2 にならない (exit={r.returncode})")

    if fails:
        print("== test_char_count: FAIL ==")
        for x in fails:
            print("  NG:", x)
        return 1
    print("== test_char_count: PASS（7項目）==")
    return 0


def test_char_count():
    """pytest から回す時の入口（py -m pytest es/scripts/tests -q）。中身は main() と同じ7項目。"""
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
