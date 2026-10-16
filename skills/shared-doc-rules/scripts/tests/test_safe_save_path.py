# -*- coding: utf-8 -*-
"""safe_save_path.py の回帰テスト。

    py ~/.claude/skills/shared-doc-rules/scripts/tests/test_safe_save_path.py

固定していること:
  1. 命名規則どおりの名前（_v{N}、_v{N}_HHMMSS）はそのまま通る
  2. 「最終版」「完成版」「final」（大文字小文字問わず）入りは ValueError
  3. 「finals」「finally」のような別の英単語は止めない
  4. _v{N} で終わらない名前は ValueError
  5. SAFE_SAVE_EXEMPT_DIRS に登録した共有フォルダの配下は検査しない（【完成】や作成者名で終わる名前を止めない）
  6. ロック時は版を +1 した別名を返す（時刻付きの名前は時刻を外して +1）
  7. preview-report の omml_lib.safe_save_path も同じ検査を通る（写しではなく本体を呼んでいる）
"""
import os
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import safe_save_path as ssp  # noqa: E402

# 例外に登録する共有フォルダ（テスト用のダミー名）
SHARED_MARK = "サークル共有フォルダ"
SHARED = os.path.join("workspace", "10_学内", SHARED_MARK)


def raises(path):
    try:
        ssp.safe_save_path(path)
    except ValueError:
        return True
    return False


def main():
    # 使う人の環境で例外フォルダが登録されていても結果が変わらないよう、試験中は外す
    user_env = os.environ.pop(ssp.EXEMPT_ENV, None)
    try:
        return run_checks()
    finally:
        if user_env is not None:
            os.environ[ssp.EXEMPT_ENV] = user_env


def run_checks():
    fails = []
    tmp = tempfile.mkdtemp(prefix="t_ssp_")

    # 1. 通る名前
    for name in ("企画書_ハッカソン2026_v1.docx", "議事録_定例_20260417_v1_153000.md", "予算表_留学費用_v12.xlsx"):
        p = os.path.join(tmp, name)
        try:
            if ssp.safe_save_path(p) != p:
                fails.append(f"存在しないファイルなのに別のパスを返した: {name}")
        except ValueError as e:
            fails.append(f"規則どおりの名前を止めた: {name}: {e}")

    # 2. 禁止語
    for name in ("企画書_最終版_v1.docx", "レポート_完成版_v2.docx", "report_final_v1.docx",
                 "Report_FINAL_v3.pptx", "スライドFinal_v1.pptx"):
        if not raises(os.path.join(tmp, name)):
            fails.append(f"禁止語入りの名前を通した: {name}")

    # 3. 別の英単語は止めない
    for name in ("finals対策_v1.md", "finally_memo_v1.md"):
        if raises(os.path.join(tmp, name)):
            fails.append(f"final 以外の英単語で止めた: {name}")

    # 4. 版なし
    for name in ("企画書_ハッカソン2026.docx", "企画書_v.docx", "企画書_v1_メモ.docx"):
        if not raises(os.path.join(tmp, name)):
            fails.append(f"_v{{N}} で終わらない名前を通した: {name}")

    # 5. 例外に登録した共有フォルダの配下は検査しない（登録しなければ検査する）
    os.environ[ssp.EXEMPT_ENV] = "別の共有;" + SHARED_MARK
    try:
        for name in ("20260301_01_アジェンダ_山田.docx", "【完成】20260310_03_企画書_v1_田中.docx"):
            p = os.path.join(tmp, SHARED, name)
            if raises(p):
                fails.append(f"例外フォルダ配下の名前を止めた: {name}")
    finally:
        del os.environ[ssp.EXEMPT_ENV]
    if not raises(os.path.join(tmp, SHARED, "20260301_01_アジェンダ_山田.docx")):
        fails.append("例外を登録していないのに共有フォルダの名前を通した")

    # 6. ロック時は版を +1（書き込みテストの open を PermissionError にして確かめる）
    locked = os.path.join(tmp, "企画書_テスト_v1.docx")
    stamped = os.path.join(tmp, "議事録_テスト_v3_120000.md")
    for p in (locked, stamped):
        with open(p, "w", encoding="utf-8") as f:
            f.write("x")

    def fake_open(*args, **kwargs):
        raise PermissionError("locked (test)")

    ssp.open = fake_open  # モジュールの名前空間に置くと組み込みの open より先に引かれる
    try:
        got = ssp.safe_save_path(locked)
        if os.path.basename(got) != "企画書_テスト_v2.docx":
            fails.append(f"ロック時に v2 を返さない: {got}")
        got = ssp.safe_save_path(stamped)
        if os.path.basename(got) != "議事録_テスト_v4.md":
            fails.append(f"時刻付きの名前で v4 を返さない: {got}")
    finally:
        del ssp.open

    # 7. preview-report の omml_lib も本体を通っている。
    #    このプロセスでは本体を import 済みなので、別プロセスで omml_lib 自身に本体を探させて確かめる
    skipped = 0
    omml_dir = os.path.join(os.path.dirname(os.path.dirname(HERE)), "preview-report", "scripts")
    bad = os.path.join(tmp, "線形代数_予習レポート_最終版_v1.docx")
    good = os.path.join(tmp, "線形代数_予習レポート_05_v1.docx")
    code = (f"import sys\nsys.path.insert(0, {omml_dir!r})\nimport omml_lib\n"
            f"try:\n    omml_lib.safe_save_path({bad!r})\n    print('PASSED_THROUGH')\n"
            f"except ValueError:\n    print('STOPPED')\n"
            f"print('GOOD_OK' if omml_lib.safe_save_path({good!r}) == {good!r} else 'GOOD_CHANGED')\n")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60)
    if "No module named 'docx'" in r.stderr:
        print("  (python-docx が無いので 7 は SKIP。python-docx の入った Python で実行すると確かめられる)")
        skipped = 1
    elif "STOPPED" not in r.stdout or "GOOD_OK" not in r.stdout:
        fails.append(f"omml_lib.safe_save_path が本体の検査を通っていない: {r.stdout.strip()} {r.stderr.strip()[-300:]}")

    for name in os.listdir(tmp):
        os.remove(os.path.join(tmp, name))
    os.rmdir(tmp)

    if fails:
        print("== test_safe_save_path: FAIL ==")
        for x in fails:
            print("  NG:", x)
        return 1
    if skipped:
        print(f"== test_safe_save_path: PASS（{7 - skipped}項目・{skipped}項目 SKIP）==")
    else:
        print("== test_safe_save_path: PASS（7項目）==")
    return 0


def test_safe_save_path():
    """pytest から呼ぶ入口（py -m pytest scripts/tests -q）。"""
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
