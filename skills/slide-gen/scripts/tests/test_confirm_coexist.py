#!/usr/bin/env python3
"""Regression test for the EXACT reported bug: making a new deck's confirm page
while a live-preview server already holds port 5050.

Before the fix, confirm_ui bound args.port (5050) directly -> crash with
"Address already in use". After: it find_free_port()s onto 5051 and serves.

Run:  python test_confirm_coexist.py   (exit 0 = pass)
"""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

BASE = os.environ.get("USERPROFILE") or str(Path.home())
# ppt-master の scripts の場所。既定は作者の置き場（例）で、環境変数 PPT_MASTER_SCRIPTS で変えられる
SK = Path(os.environ.get("PPT_MASTER_SCRIPTS", r"C:\dev\ppt-master\skills\ppt-master\scripts"))
SVG = SK / "svg_editor" / "server.py"
CONFIRM = SK / "confirm_ui" / "server.py"
WORK = Path(BASE) / "_slidegen_work" / "_audit_test"
# この試験は、作者が ppt-master のサーバ（server_common・svg_editor・confirm_ui）に入れた修正
# （../../references/CHANGELOG_5050.md）を確かめる物。修正は上流の ppt-master に入っていないので、
# ppt-master が無い時と、上流の版（修正の印 force_release_lock が server_common.py に無い）の時は、何もせず SKIP で終わる
_COMMON = SK / "server_common.py"
if __name__ == "__main__" and (not _COMMON.is_file()
                               or "force_release_lock" not in _COMMON.read_text(encoding="utf-8", errors="replace")):
    print("[SKIP-ALL] %s: 作者の修正が入った ppt-master のサーバが無い（%s）" % (Path(__file__).name, SK))
    sys.exit(0)

results = []
def check(name, ok, detail=""):
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" :: {detail}" if detail else ""))

def http_ok(port, path, timeout=2):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False

def shutdown(port):
    try:
        urllib.request.urlopen(urllib.request.Request(
            f"http://127.0.0.1:{port}/api/shutdown", data=b'{"reason":"test"}',
            headers={"Content-Type": "application/json"}, method="POST"), timeout=3)
    except Exception:
        pass

def read_lock(path, key="port"):
    for _ in range(60):
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8")).get(key)
            except (OSError, json.JSONDecodeError):
                pass
        time.sleep(0.25)
    return None

def main():
    live = WORK / "liveDeck"
    conf = WORK / "confirmDeck"
    for d in (live, conf):
        shutil.rmtree(d, ignore_errors=True)
    (conf / "confirm_ui").mkdir(parents=True, exist_ok=True)
    (conf / "confirm_ui" / "recommendations.json").write_text('{"recommend":{},"tier":1}', encoding="utf-8")

    p_live = p_conf = None
    try:
        # 1) Occupy 5050 with a live-preview server.
        live.mkdir(parents=True, exist_ok=True)
        log1 = open(live / "_s.log", "a", encoding="utf-8")
        p_live = subprocess.Popen(
            [sys.executable, str(SVG), str(live), "--port", "5050", "--no-browser", "--live", "--timeout", "120"],
            stdout=log1, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        live_port = read_lock(live / "live_preview" / "lock.json")
        check("live-preview took 5050", live_port == 5050, f"port={live_port}")

        # 2) Launch confirm_ui on the SAME --port 5050 (the crash scenario).
        log2 = open(conf / "_s.log", "a", encoding="utf-8")
        p_conf = subprocess.Popen(
            [sys.executable, str(CONFIRM), str(conf), "--port", "5050", "--no-browser", "--timeout", "120"],
            stdout=log2, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        conf_port = read_lock(conf / ".confirm_ui.lock")
        check("confirm_ui did NOT crash, bound a port", conf_port is not None, f"port={conf_port}")
        check("confirm_ui advanced off the busy 5050", conf_port not in (None, 5050), f"port={conf_port}")
        check("confirm_ui process still alive", p_conf.poll() is None)
        check("confirm_ui serves /api/catalogs 200", http_ok(conf_port, "/api/catalogs") if conf_port else False)
        check("live-preview still serves on 5050", http_ok(5050, "/api/config"))

        shutdown(conf_port)
        shutdown(live_port)
        time.sleep(1.0)
    finally:
        for p in (p_live, p_conf):
            try:
                if p is not None and p.poll() is None:
                    p.kill()
            except Exception:
                pass
        time.sleep(0.5)
        for d in (live, conf):
            shutil.rmtree(d, ignore_errors=True)

    ok = sum(results)
    print(f"\n=== {ok}/{len(results)} checks passed ===")
    return 0 if ok == len(results) else 1

if __name__ == "__main__":
    raise SystemExit(main())
