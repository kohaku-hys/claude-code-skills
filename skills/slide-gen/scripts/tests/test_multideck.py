#!/usr/bin/env python3
"""Regression test for the localhost:5050 multi-deck port handling.

Verifies that two preview servers requested on the SAME --port land on DISTINCT
ports (find_free_port advances correctly on Windows), and that a graceful
shutdown of one does NOT take down the other (no shared-port cross-talk).

Run:  python test_multideck.py
Exit code 0 = all checks passed.
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
SERVER = SK / "svg_editor" / "server.py"
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
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" :: {detail}" if detail else ""))

def read_port(proj):
    lock = proj / "live_preview" / "lock.json"
    for _ in range(60):
        if lock.exists():
            try:
                d = json.loads(lock.read_text(encoding="utf-8"))
                if d.get("port"):
                    return int(d["port"]), int(d.get("pid", 0))
            except (OSError, json.JSONDecodeError):
                pass
        time.sleep(0.25)
    return None, None

def http_ok(port, path="/api/config", timeout=2):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False

def shutdown(port):
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/shutdown",
            data=b'{"reason":"test"}',
            headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=3)
    except Exception:
        pass

def start(proj):
    proj.mkdir(parents=True, exist_ok=True)
    log = open(proj / "_server.log", "a", encoding="utf-8")
    return subprocess.Popen(
        [sys.executable, str(SERVER), str(proj), "--port", "5050",
         "--no-browser", "--live", "--timeout", "120"],
        stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)

def main():
    a = WORK / "deckA"
    b = WORK / "deckB"
    for d in (a, b):
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
    p1 = p2 = None
    try:
        p1 = start(a)
        time.sleep(1.0)
        p2 = start(b)

        portA, pidA = read_port(a)
        portB, pidB = read_port(b)
        check("server A bound a port", portA is not None, f"port={portA} pid={pidA}")
        check("server B bound a port", portB is not None, f"port={portB} pid={pidB}")

        if portA and portB:
            check("two decks got DISTINCT ports", portA != portB, f"A={portA} B={portB}")
            check("ports are 5050 and 5051", {portA, portB} == {5050, 5051}, f"A={portA} B={portB}")
            check("server A responds 200", http_ok(portA))
            check("server B responds 200", http_ok(portB))
            check("lock pid A matches child", pidA == p1.pid, f"lock={pidA} child={p1.pid}")
            check("lock pid B matches child", pidB == p2.pid, f"lock={pidB} child={p2.pid}")

            # Cross-talk test: graceful shutdown of A must not kill B.
            shutdown(portA)
            time.sleep(1.5)
            check("shutting down A actually stopped A", not http_ok(portA))
            check("shutting down A did NOT affect B (no cross-talk)", http_ok(portB))

            shutdown(portB)
            time.sleep(1.0)
    finally:
        # Always reap children, even if an assertion raised, so no orphan
        # servers linger on the test ports.
        for p in (p1, p2):
            try:
                if p is not None and p.poll() is None:
                    p.kill()
            except Exception:
                pass
        time.sleep(0.5)
        for d in (a, b):
            shutil.rmtree(d, ignore_errors=True)

    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n=== {passed}/{total} checks passed ===")
    return 0 if passed == total else 1

if __name__ == "__main__":
    raise SystemExit(main())
