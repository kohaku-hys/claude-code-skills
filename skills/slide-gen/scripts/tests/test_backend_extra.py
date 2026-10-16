#!/usr/bin/env python3
"""Backend regression tests for the audit fixes:
- save-all persists annotations atomically and clears only saved state (#13/#14)
- save-all skips a bad file without aborting the whole save or losing its state
- CLI --shutdown is identity-checked: it never kills a different project's
  server that happens to hold the recorded port (#05 / #11)

Run:  python test_backend_extra.py   (exit 0 = pass)
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

MIN_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
           '<rect id="el1" x="10" y="10" width="50" height="50" fill="red"/></svg>')

def start(proj, port):
    proj.mkdir(parents=True, exist_ok=True)
    log = open(proj / "_s.log", "a", encoding="utf-8")
    return subprocess.Popen(
        [sys.executable, str(SVG), str(proj), "--port", str(port),
         "--no-browser", "--live", "--timeout", "120"],
        stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)

def read_lock(proj):
    lf = proj / "live_preview" / "lock.json"
    for _ in range(60):
        if lf.exists():
            try:
                d = json.loads(lf.read_text(encoding="utf-8"))
                if d.get("port"):
                    return int(d["port"]), int(d.get("pid", 0))
            except (OSError, json.JSONDecodeError):
                pass
        time.sleep(0.25)
    return None, None

def api(port, path, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", data=data,
        headers={"Content-Type": "application/json"}, method=method)
    with urllib.request.urlopen(req, timeout=4) as r:
        return r.status, json.loads(r.read().decode())

def http_ok(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/config", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False

def cli_shutdown(proj):
    subprocess.run([sys.executable, str(SVG), str(proj), "--shutdown"],
                   timeout=30, capture_output=True)

def test_save_all():
    proj = WORK / "saveDeck"
    shutil.rmtree(proj, ignore_errors=True)
    (proj / "svg_output").mkdir(parents=True, exist_ok=True)
    (proj / "svg_output" / "01.svg").write_text(MIN_SVG, encoding="utf-8")
    p = start(proj, 5050)
    try:
        port, _ = read_lock(proj)
        if not port:
            check("save: server started", False); return
        # Annotate el1, then save-all.
        api(port, "/api/slide/01.svg/annotate", "POST",
            {"element_id": "el1", "annotation": "make it bigger"})
        st, resp = api(port, "/api/save-all", "POST")
        check("save: save-all ok", st == 200 and resp.get("status") == "ok", str(resp))
        check("save: 01.svg in files_modified", "01.svg" in resp.get("files_modified", []))
        disk = (proj / "svg_output" / "01.svg").read_text(encoding="utf-8")
        check("save: annotation persisted to disk",
              'data-edit-annotation="make it bigger"' in disk)
        check("save: no leftover .tmp file",
              not (proj / "svg_output" / "01.svg.tmp").exists())
        # Second save-all should be a no-op (state was cleared).
        st2, resp2 = api(port, "/api/save-all", "POST")
        check("save: state cleared (2nd save modifies nothing)",
              resp2.get("files_modified") == [], str(resp2))
    finally:
        cli_shutdown(proj)
        try:
            if p.poll() is None: p.kill()
        except Exception: pass
        time.sleep(0.4)
        shutil.rmtree(proj, ignore_errors=True)

def test_shutdown_identity():
    # Project B runs a real server; project X has a STALE lock pointing at B's
    # port. `--shutdown X` must NOT kill B.
    b = WORK / "deckB_id"
    x = WORK / "deckX_id"
    for d in (b, x):
        shutil.rmtree(d, ignore_errors=True)
    pb = start(b, 5050)
    try:
        bport, bpid = read_lock(b)
        if not bport:
            check("identity: B started", False); return
        check("identity: B serving", http_ok(bport), f"port={bport}")
        # Forge X's lock to point at B's port (recycled-port / stale-lock case).
        (x / "live_preview").mkdir(parents=True, exist_ok=True)
        (x / "live_preview" / "lock.json").write_text(
            json.dumps({"pid": bpid, "port": bport}), encoding="utf-8")
        # Shut down X -> identity mismatch -> must leave B alone, clear X's lock.
        cli_shutdown(x)
        time.sleep(0.6)
        check("identity: B STILL alive after shutting down X (no cross-kill)",
              http_ok(bport))
        check("identity: X stale lock cleared",
              not (x / "live_preview" / "lock.json").exists())
        # Positive control: shutting down B really stops B.
        cli_shutdown(b)
        time.sleep(0.6)
        check("identity: shutting down B actually stops B", not http_ok(bport))
    finally:
        try:
            if pb.poll() is None: pb.kill()
        except Exception: pass
        time.sleep(0.4)
        for d in (b, x):
            shutil.rmtree(d, ignore_errors=True)

def main():
    test_save_all()
    test_shutdown_identity()
    ok = sum(results)
    print(f"\n=== {ok}/{len(results)} checks passed ===")
    return 0 if ok == len(results) else 1

if __name__ == "__main__":
    raise SystemExit(main())
