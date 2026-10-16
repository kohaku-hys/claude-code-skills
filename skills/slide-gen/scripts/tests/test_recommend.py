"""recommend.py の回帰テスト（2026-09-28）。

"tier": 2 を付けると confirm_ui が用紙・用途・体裁の欄を描かず、本人に見えないまま一覧の先頭で確定していた。
tier を付けないこと、tier-1 の推奨（canvas/mode/visual_style/delivery_purpose）が recommend に入ることを確かめる。
"""
import json, os, shutil, subprocess, sys, tempfile

S = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "recommend.py")
ok = ng = 0


def check(name, cond):
    global ok, ng
    print(("OK   " if cond else "FAIL ") + name)
    ok += bool(cond); ng += (not cond)


for prof, want in (("presentation", "presentation"), ("report", "balanced"), ("sns", "presentation")):
    d = tempfile.mkdtemp()
    try:
        subprocess.run([sys.executable, S, d, "--profile", prof, "--pages", "7"], capture_output=True,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"), check=True)
        rec = json.load(open(os.path.join(d, "confirm_ui", "recommendations.json"), encoding="utf-8"))
        check(f"{prof}: tier を付けない（全項目を1ページに出す）", "tier" not in rec)
        r = rec.get("recommend", {})
        check(f"{prof}: tier-1 の4項目が recommend に入る",
              all(k in r for k in ("canvas", "mode", "visual_style", "delivery_purpose")))
        check(f"{prof}: 用途の推奨が {want}", r.get("delivery_purpose") == want)
        check(f"{prof}: tier-2 の推奨も残る", r.get("icons") and r.get("generation_mode"))
        check(f"{prof}: ページ数が渡る", rec.get("page_count", {}).get("value") == "7")
    finally:
        shutil.rmtree(d, ignore_errors=True)
print("%d/%d passed" % (ok, ok + ng))
sys.exit(1 if ng else 0)
