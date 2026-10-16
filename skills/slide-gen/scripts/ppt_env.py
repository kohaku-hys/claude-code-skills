# -*- coding: utf-8 -*-
"""ppt-master 実行前の環境ゲート（Preflight）。

なぜ存在するか：ppt-master のスクリプトは 3.10+ 構文（`list[str] | None` 等）を
import 時に評価するため、Python 3.9 で呼ぶと `TypeError: unsupported operand ... | ...`
で即クラッシュする。既定の `py` が 3.9 の PC もあるので、**盲目的に `py` で ppt-master を
呼ぶと必ず失敗する**（今回それで大量の手戻り）。このスクリプトは 3.10+ の実体を探し、
ppt-master の必須依存が入っているかを確認し、使うべき python.exe の絶対パスを1行で返す。

使い方（このスクリプト自体は 3.9 でも 3.12 でも動く＝標準ライブラリのみ）：
  py -3 ppt_env.py            # → 使うべき 3.10+ python の絶対パスを最終行 PYPPT= で出す
  py -3 ppt_env.py --strict   # 依存が欠けていたら exit 1
戻り最終行： `PYPPT=<path>`（見つからなければ `PYPPT=` 空 + 導入手順を stderr に）。
"""
import os
import re
import sys
import glob
import subprocess

REQUIRED = ["pptx", "svglib", "reportlab", "PIL", "numpy", "lxml", "bs4"]


def candidates():
    seen = []
    # 1) 既知の user-scope インストール先（Windows の python.org 版を利用者ごとに入れた場所）
    base = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python")
    for d in sorted(glob.glob(os.path.join(base, "Python3*")), reverse=True):
        exe = os.path.join(d, "python.exe")
        if os.path.exists(exe):
            seen.append(exe)
    # 2) py ランチャーの 3.12/3.11/3.10
    for v in ("3.13", "3.12", "3.11", "3.10"):
        try:
            out = subprocess.run(["py", "-" + v, "-c", "import sys;print(sys.executable)"],
                                 capture_output=True, text=True, timeout=15)
            if out.returncode == 0:
                p = out.stdout.strip().splitlines()[-1].strip()
                if p and os.path.exists(p):
                    seen.append(p)
        except Exception:
            pass
    # 重複除去（順序維持）
    uniq = []
    for p in seen:
        if p.lower() not in [u.lower() for u in uniq]:
            uniq.append(p)
    return uniq


def ver_ok(exe):
    try:
        out = subprocess.run([exe, "-c", "import sys;print('%d.%d' % sys.version_info[:2])"],
                             capture_output=True, text=True, timeout=15)
        m = re.match(r"(\d+)\.(\d+)", out.stdout.strip().splitlines()[-1].strip())
        if not m:
            return None
        return (int(m.group(1)), int(m.group(2)))
    except Exception:
        return None


def missing_deps(exe):
    code = "import importlib,sys\nbad=[m for m in %r if importlib.util.find_spec(m) is None]\nprint(','.join(bad))" % REQUIRED
    try:
        out = subprocess.run([exe, "-c", code], capture_output=True, text=True, timeout=30)
        return [m for m in out.stdout.strip().split(",") if m]
    except Exception:
        return REQUIRED


def main(argv):
    strict = "--strict" in argv
    for exe in candidates():
        v = ver_ok(exe)
        if not v or v < (3, 10):
            continue
        miss = missing_deps(exe)
        if miss:
            sys.stderr.write(
                "[preflight] 3.%d found (%s) だが依存が不足: %s\n"
                "  導入: \"%s\" -m pip install %s\n"
                % (v[1], exe, ",".join(miss), exe, " ".join(
                    {"pptx": "python-pptx", "PIL": "Pillow", "bs4": "beautifulsoup4"}.get(m, m)
                    for m in miss)))
            if strict:
                print("PYPPT=")
                return 1
            continue
        print("PYPPT=" + exe)
        return 0
    sys.stderr.write(
        "[preflight] Python 3.10+ が見つからない。ppt-master は 3.9 では動かない。\n"
        "  導入（管理者不要・UAC回避）: winget が落とした installer を\n"
        "  \"%TEMP%\\WinGet\\Python.Python.3.12.*\\python-3.12.*-amd64.exe\" /quiet InstallAllUsers=0 Include_launcher=0 PrependPath=1\n"
        "  で直接実行し、その python.exe に python-pptx svglib reportlab Pillow numpy lxml beautifulsoup4 budoux を pip 導入。\n")
    print("PYPPT=")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
