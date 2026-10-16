# -*- coding: utf-8 -*-
"""SharePoint 共有フォルダの動画を堅牢に一括キャプチャする再利用モジュール。

今回（2026-06）の実戦で確立した、取りこぼし・取り違えを防ぐ決定版フロー:
- 完全バックグラウンド: chrome_cdp の描画スロットリング無効化フラグ前提で
  cdp_seek.split_and_capture(bring_to_front=False)。画面を一切奪わない。
- 取り違え防止: 各動画で document.title が期待する "_NN_M_" を含むか検証してから撮る
  （expect_title）。タブ開閉のレースで前の動画タブを掴む事故を防ぐ。
- リソース蓄積対策: BATCH 本ごとに Chrome を再起動（連続で開閉すると WS が timeout する）。
- 冪等: 既に frames>=min_frames あるフォルダはスキップ。フォルダは撮る前に必ず空にする。
- リトライ: 動画ごと最大 RETRY 回。失敗時は Chrome 再起動して再試行。

CLI:
    python capture_folder.py <folder_url> [--out <dir>] [--splits 10] [--only 05_1,09_1]
sharepoint_folder.enumerate_videos でファイル名を列挙 → 回ごとにキャプチャ。
"""
import os, sys, json, time, re, glob
import urllib.parse as up
from pathlib import Path
import requests, websocket

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import chrome_cdp
import cdp_seek

CDP = "http://localhost:9222"
DEFAULT_OUT = Path.home() / "AppData" / "Local" / "Temp" / "preview_capture" / "frames"
# SharePoint の個人用サイト（OneDrive for Business）のホスト。組織ごとに違うので、
# 環境変数 SHAREPOINT_HOST に自分の組織のもの（例: https://contoso-my.sharepoint.com）を入れておく
SHAREPOINT_HOST = os.environ.get("SHAREPOINT_HOST", "https://<YOUR_TENANT>-my.sharepoint.com")


def _list_tabs():
    try:
        return requests.get(f"{CDP}/json", timeout=5).json()
    except Exception:
        return []


def _bring_front(tab):
    try:
        ws = websocket.create_connection(tab["webSocketDebuggerUrl"], timeout=8)
        ws.send(json.dumps({"id": 1, "method": "Page.bringToFront"})); ws.recv(); ws.close()
    except Exception:
        pass


def _close_stream_tabs():
    for t in _list_tabs():
        if t.get("type") == "page" and "stream.aspx" in t.get("url", ""):
            try:
                requests.get(f"{CDP}/json/close/{t.get('id')}", timeout=5)
            except Exception:
                pass


def _neutral_tab():
    """動画タブを前面化しないための無害なタブ（フォルダ表示等）。無ければ None。"""
    return next((t for t in _list_tabs()
                 if t.get("type") == "page" and "stream.aspx" not in t.get("url", "")), None)


def stream_url(folder_id_path, filename):
    """SharePoint の stream.aspx 再生URLを folder_id_path(/personal/.../微分方程式) + filename から構築。"""
    host = SHAREPOINT_HOST
    # folder_id_path は personal サイト配下の絶対パス。host は環境変数 SHAREPOINT_HOST で差し替える。
    base = host + "/personal/" + folder_id_path.split("/personal/")[-1].split("/", 1)[0]
    base += "/_layouts/15/stream.aspx"
    return base + "?" + up.urlencode({"id": folder_id_path.rstrip("/") + "/" + filename}) + "&referrer=StreamWebApp"


def restart_chrome(landing_url):
    chrome_cdp.start_chrome([landing_url], kill_existing=True)
    time.sleep(4)
    tabs = _list_tabs()
    url0 = tabs[0].get("url", "") if tabs else ""
    return bool(tabs) and "login.microsoftonline.com" not in url0


def _wait_ready_verified(expect_token, timeout_s=45):
    """新規 stream タブが ready かつ document.title に expect_token を含むまで待つ。
    一致タブを返す。タイトル不一致なら (None, title) を返し呼び出し側がリトライ/再起動。"""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        st = [t for t in _list_tabs() if t.get("type") == "page" and "stream.aspx" in t.get("url", "")]
        if st:
            t = st[-1]
            try:
                ws = websocket.create_connection(t["webSocketDebuggerUrl"], timeout=10)
                try:
                    dur = cdp_seek.wait_video_ready(ws, timeout_s=8)
                    title = cdp_seek.cdp_eval(ws, "document.title", 999) if dur else ""
                finally:
                    ws.close()
                if dur:
                    if expect_token in (title or ""):
                        return t, title
                    return None, title
            except Exception:
                pass
        time.sleep(1.5)
    return None, ""


def capture_one(folder_id_path, item, out_root, splits=10, retry=4, restart_landing=None,
                host=SHAREPOINT_HOST, log=print,
                adaptive=False, max_frames=40, dedup=False):
    """item={id,filename}. out_root/<id>/ を空にして splits 枚キャプチャ。成否を返す。

    adaptive=True: split_and_capture_adaptive で板書が変わった谷間を自動追撮（max_frames 上限）。
    dedup=True:    撮り終えた後に静止区間の重複フレームを _dup/ へ退避（非破壊）。
    既定(adaptive=False, dedup=False)は従来どおり splits 枚の固定分割。"""
    vid = item["id"]
    d = Path(out_root) / vid
    d.mkdir(parents=True, exist_ok=True)
    for p in glob.glob(str(d / "*.png")):
        try:
            os.remove(p)
        except Exception:
            pass
    vurl = stream_url(folder_id_path, item["filename"])
    token = f"_{vid}_"
    for attempt in range(1, retry + 1):
        _close_stream_tabs(); time.sleep(1.5)
        try:
            requests.put(f"{CDP}/json/new?{up.quote(vurl, safe=':/?=&%')}", timeout=10)
        except Exception as e:
            log(f"    [{vid}] a{attempt} open err {e!r}"); continue
        nt = _neutral_tab()
        if nt:
            _bring_front(nt)
        vtab, title = _wait_ready_verified(token, 45)
        if not vtab:
            log(f"    [{vid}] a{attempt} not ready / title mismatch")
            if attempt < retry and restart_landing:
                restart_chrome(restart_landing)
            continue
        try:
            if adaptive:
                saved = cdp_seek.split_and_capture_adaptive(
                    vtab, splits, str(d), max_frames=max_frames,
                    bring_to_front=False, expect_title=token)
            else:
                saved = cdp_seek.split_and_capture(vtab, splits, str(d), bring_to_front=False, expect_title=token)
        except Exception as e:
            log(f"    [{vid}] a{attempt} capture err {e!r}")
            if attempt < retry and restart_landing:
                restart_chrome(restart_landing)
            continue
        if len(saved) >= max(1, splits - 2):
            if dedup:
                try:
                    import dedup as _dedup
                    r = _dedup.dedup_dir(str(d))
                    if r["pil"]:
                        log(f"    [{vid}] dedup: kept {len(r['kept'])} / dup {len(r['dropped'])} -> _dup/")
                except Exception as e:
                    log(f"    [{vid}] dedup skipped ({e!r})")
            log(f"    [{vid}] OK {len(saved)} frames (title verified)")
            _close_stream_tabs(); return True
        log(f"    [{vid}] a{attempt} only {len(saved)} frames")
        if attempt < retry and restart_landing:
            restart_chrome(restart_landing)
    return False


def capture_folder(folder_url, out_root=None, splits=10, batch=3, only=None, log=print,
                   adaptive=False, max_frames=40, dedup=False):
    """folder_url を列挙し、回ごとに堅牢キャプチャ。out_root/<id>/*.png と manifest を作る。
    adaptive/max_frames/dedup は capture_one へそのまま渡す（既定は従来の固定分割）。"""
    import sharepoint_folder
    out_root = Path(out_root or DEFAULT_OUT)
    out_root.mkdir(parents=True, exist_ok=True)
    res = sharepoint_folder.enumerate_videos(folder_url)
    if res.get("status") not in ("OK", "OK_TRUNCATED"):
        log(f"enumerate failed: {res.get('status')}"); return res
    # folder_id_path は enumerate の final_url / folder_url の id= から復元
    qs = up.parse_qs(up.urlparse(folder_url).query)
    folder_id_path = up.unquote(qs.get("id", [""])[0])
    files = res.get("files", [])
    items = []
    for fn in files:
        m = re.search(r"_(\d{2})_(\d+)_", fn)
        if m:
            items.append({"id": f"{m.group(1)}_{m.group(2)}", "filename": fn})
    if only:
        only = set(only)
        items = [it for it in items if it["id"] in only]
    items.sort(key=lambda x: x["id"])
    log(f"capture {len(items)} videos, batch={batch}")
    done = {}
    for bi in range(0, len(items), batch):
        b = items[bi:bi + batch]
        restart_chrome(folder_url)
        for it in b:
            done[it["id"]] = capture_one(folder_id_path, it, out_root, splits=splits,
                                         restart_landing=folder_url, log=log,
                                         adaptive=adaptive, max_frames=max_frames, dedup=dedup)
    ok = [k for k, v in done.items() if v]
    bad = [k for k, v in done.items() if not v]
    log(f"DONE ok={len(ok)} fail={bad}")
    return {"ok": ok, "fail": bad, "out_root": str(out_root)}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(prog="capture_folder.py")
    ap.add_argument("folder_url")
    ap.add_argument("--out")
    ap.add_argument("--splits", type=int, default=10, help="固定分割の枚数／adaptive時は粗グリッド枚数")
    ap.add_argument("--batch", type=int, default=3)
    ap.add_argument("--only", help="comma separated ids e.g. 05_1,09_1")
    ap.add_argument("--adaptive", action="store_true",
                    help="板書が変わった谷間を自動追撮（固定分割の取りこぼし対策）")
    ap.add_argument("--max-frames", type=int, default=40,
                    help="adaptive時の総キャプチャ上限（既定40）")
    ap.add_argument("--dedup", action="store_true",
                    help="撮影後に静止区間の重複フレームを _dup/ へ退避（非破壊）")
    a = ap.parse_args()
    only = a.only.split(",") if a.only else None
    r = capture_folder(a.folder_url, out_root=a.out, splits=a.splits, batch=a.batch, only=only,
                       adaptive=a.adaptive, max_frames=a.max_frames, dedup=a.dedup)
    print(f"OK={len(r.get('ok', []))} FAIL={r.get('fail')}")
