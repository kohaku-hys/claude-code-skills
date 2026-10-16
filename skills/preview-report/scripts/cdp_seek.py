"""Chrome DevTools Protocol で動画を任意秒にシーク + キャプチャ"""
import json, base64, time, sys, os
from pathlib import Path
import requests
import websocket

CDP = "http://localhost:9222"
BASE = os.environ.get("USERPROFILE") or str(Path.home())

def get_video_tabs():
    try:
        tabs = requests.get(f"{CDP}/json", timeout=3).json()
    except Exception:
        return []
    return [t for t in tabs if t.get('type') == 'page' and 'stream.aspx' in t.get('url', '')]

def cdp_call(ws, method, params=None, msg_id=1):
    ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
    while True:
        resp = json.loads(ws.recv())
        if resp.get('id') == msg_id:
            return resp

def cdp_eval(ws, expr, msg_id):
    r = cdp_call(ws, "Runtime.evaluate", {
        "expression": expr, "returnByValue": True, "awaitPromise": True
    }, msg_id)
    return r.get('result', {}).get('result', {}).get('value')

def seek_and_capture(tab, target_seconds, out_path):
    ws_url = tab['webSocketDebuggerUrl']
    ws = websocket.create_connection(ws_url, timeout=20)
    try:
        # 動画要素確認
        n = cdp_eval(ws, "document.querySelectorAll('video').length", 1)
        print(f"  video elements: {n}")
        if not n:
            print("  [!] no <video> tag")
            return False

        # 現在位置と長さ
        dur = cdp_eval(ws, "document.querySelector('video').duration", 2)
        cur = cdp_eval(ws, "document.querySelector('video').currentTime", 3)
        paused = cdp_eval(ws, "document.querySelector('video').paused", 4)
        print(f"  duration={dur}, current={cur}, paused={paused}")

        # 1. 先に play() で video パイプライン初期化（poster 状態だと seek しても描画されない）
        cdp_eval(ws, "document.querySelector('video').play()", 5)
        time.sleep(1.2)
        # 2. seek → seeked イベント待ち → 短い追加待機
        target = min(target_seconds, dur - 1) if dur else target_seconds
        seeked = cdp_eval(ws, f"""
(async () => {{
  const v = document.querySelector('video');
  v.currentTime = {target};
  await new Promise(res => v.addEventListener('seeked', res, {{once: true}}));
  await new Promise(r => setTimeout(r, 400));
  return v.currentTime;
}})()
""", 6)
        # 3. pause でフリーズ（次の captureScreenshot で確定フレームを取る）
        cdp_eval(ws, "document.querySelector('video').pause()", 7)
        time.sleep(0.4)
        new_cur = cdp_eval(ws, "document.querySelector('video').currentTime", 8)
        print(f"  seeked to {seeked}, now paused at {new_cur}")

        # スクリーンショット (CDP Page.captureScreenshot)
        cdp_call(ws, "Page.enable", msg_id=10)
        r = cdp_call(ws, "Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False}, msg_id=11)
        data = r.get('result', {}).get('data')
        if data:
            with open(out_path, 'wb') as f:
                f.write(base64.b64decode(data))
            print(f"  saved -> {out_path}")
            return True
        return False
    finally:
        ws.close()

def wait_video_ready(ws, timeout_s=20):
    """<video> が現れ duration が確定する（readyState>=1）まで待つ。
    確定した duration(float) を返す。ダメなら None。"""
    deadline = time.time() + timeout_s
    mid = 50
    while time.time() < deadline:
        dur = cdp_eval(ws, """
(function(){
  var v = document.querySelector('video');
  if(!v) return null;
  var d = v.duration;
  return (v.readyState >= 1 && d && isFinite(d) && d > 0) ? d : null;
})()
""", mid)
        mid += 1
        if dur:
            return dur
        time.sleep(0.7)
    return None

def split_and_capture(tab, n, out_dir, bring_to_front=False, expect_title=None):
    """動画を n 分割して各区間の中点でキャプチャ。

    bring_to_front=False（既定）: chrome_cdp の描画スロットリング無効化フラグ前提で、
        ウィンドウを前面化せず（画面を奪わず）裏でキャプチャする。
    bring_to_front=True: 旧挙動。フラグ無しの古い Chrome で背景タブが描画停止する場合用。
    expect_title: 期待するタイトル断片（例 "_05_1_"）。document.title に含まれなければ
        取り違え（別動画タブを掴んだ等）とみなし、撮らずに [] を返す。
        ※ タブ開閉のレースで前の動画タブを掴むと別動画を保存してしまう事故への防御。
    """
    import os
    os.makedirs(out_dir, exist_ok=True)
    ws_url = tab['webSocketDebuggerUrl']
    ws = websocket.create_connection(ws_url, timeout=30)
    try:
        if bring_to_front:
            # フラグ無し環境向けフォールバック（ウィンドウが前面化する）
            cdp_call(ws, "Page.bringToFront", msg_id=99)
            time.sleep(0.8)
        # メタデータ確定待ち（duration=None クラッシュ対策。タブ開直後のレース回避）
        dur = wait_video_ready(ws, timeout_s=25)
        title_js = cdp_eval(ws, "document.title", 2)
        title_s = (title_js or "")[:60]
        if not dur or dur < 1:
            print(f"  [!] invalid/timeout duration (title={title_s})"); return []
        # タイトル検証（取り違え防止）。期待断片が含まれなければ撮らない。
        if expect_title and expect_title not in (title_js or ""):
            print(f"  [!] title mismatch: want '{expect_title}' got '{title_s}' -> skip")
            return []
        print(f"  duration={dur:.1f}s, title={title_s}")

        # 初回だけ play してパイプライン起動
        cdp_eval(ws, "document.querySelector('video').play()", 3)
        time.sleep(1.2)

        cdp_call(ws, "Page.enable", msg_id=100)
        saved = []
        for i in range(n):
            ratio = (i + 0.5) / n   # 5%, 15%, 25%, ..., 95% の中点
            target = min(dur - 0.5, dur * ratio)
            msg_base = 200 + i * 10
            cdp_eval(ws, f"""
(async () => {{
  const v = document.querySelector('video');
  v.currentTime = {target};
  await new Promise(res => v.addEventListener('seeked', res, {{once: true}}));
  await new Promise(r => setTimeout(r, 350));
}})()
""", msg_base)
            cdp_eval(ws, "document.querySelector('video').pause()", msg_base + 1)
            time.sleep(0.25)

            r = cdp_call(ws, "Page.captureScreenshot",
                         {"format": "png", "captureBeyondViewport": False},
                         msg_id=msg_base + 2)
            data = r.get('result', {}).get('data')
            if data:
                fname = f"split{n:02d}_{i+1:02d}_of_{n}_at{int(target):04d}s.png"
                fp = os.path.join(out_dir, fname)
                with open(fp, 'wb') as f:
                    f.write(base64.b64decode(data))
                saved.append(fp)
                print(f"  [{i+1}/{n}] t={target:6.1f}s ({ratio*100:4.1f}%) -> {fname}")

            # 次のseek前にplay再開（paused状態のままだとseekがたまに固まる）
            if i < n - 1:
                cdp_eval(ws, "document.querySelector('video').play()", msg_base + 3)
                time.sleep(0.3)
        return saved
    finally:
        ws.close()

def capture_at_times(tab, seconds_list, out_dir, prefix="t", bring_to_front=False, expect_title=None):
    """指定した秒数リストでフレームをキャプチャする。

    10分割の固定点で人物に隠れた/板書途中だった『判読不可』箇所を、
    時刻を前後にずらして撮り直し、読めるフレームを得るために使う。
    （留保で逃げず、最終解・公式を実際に読み切ってレポートを完成させるための機構）
    """
    import os
    os.makedirs(out_dir, exist_ok=True)
    ws = websocket.create_connection(tab['webSocketDebuggerUrl'], timeout=30)
    try:
        if bring_to_front:
            cdp_call(ws, "Page.bringToFront", msg_id=99); time.sleep(0.8)
        dur = wait_video_ready(ws, timeout_s=25)
        title_js = cdp_eval(ws, "document.title", 2)
        if not dur or dur < 1:
            print("  [!] invalid duration"); return []
        if expect_title and expect_title not in (title_js or ""):
            print(f"  [!] title mismatch (want {expect_title}) -> skip"); return []
        cdp_eval(ws, "document.querySelector('video').play()", 3); time.sleep(1.0)
        cdp_call(ws, "Page.enable", msg_id=100)
        saved = []
        for i, sec in enumerate(seconds_list):
            target = max(0.0, min(dur - 0.3, float(sec)))
            mb = 300 + i * 10
            cdp_eval(ws, f"""
(async () => {{
  const v = document.querySelector('video');
  v.currentTime = {target};
  await new Promise(res => v.addEventListener('seeked', res, {{once: true}}));
  await new Promise(r => setTimeout(r, 350));
}})()
""", mb)
            cdp_eval(ws, "document.querySelector('video').pause()", mb + 1); time.sleep(0.25)
            r = cdp_call(ws, "Page.captureScreenshot",
                         {"format": "png", "captureBeyondViewport": False}, msg_id=mb + 2)
            data = r.get('result', {}).get('data')
            if data:
                fp = os.path.join(out_dir, f"{prefix}_{int(target):04d}s.png")
                with open(fp, 'wb') as f:
                    f.write(base64.b64decode(data))
                saved.append(fp)
                print(f"  cap t={target:6.0f}s -> {os.path.basename(fp)}")
            if i < len(seconds_list) - 1:
                cdp_eval(ws, "document.querySelector('video').play()", mb + 3); time.sleep(0.25)
        return saved
    finally:
        ws.close()


def _seek_capture(ws, target, out_path, mid, settle=0.35):
    """1点だけ seek → pause → captureScreenshot → PNG保存。生PNGバイト列を返す（失敗時 None）。
    split_and_capture / capture_at_times と同じ手順を1関数に切り出したもの（adaptive で再利用）。"""
    cdp_eval(ws, f"""
(async () => {{
  const v = document.querySelector('video');
  v.currentTime = {target};
  await new Promise(res => v.addEventListener('seeked', res, {{once: true}}));
  await new Promise(r => setTimeout(r, {int(settle * 1000)}));
}})()
""", mid)
    cdp_eval(ws, "document.querySelector('video').pause()", mid + 1)
    time.sleep(0.25)
    r = cdp_call(ws, "Page.captureScreenshot",
                 {"format": "png", "captureBeyondViewport": False}, msg_id=mid + 2)
    data = r.get('result', {}).get('data')
    if not data:
        return None
    raw = base64.b64decode(data)
    with open(out_path, 'wb') as f:
        f.write(raw)
    return raw


def plan_adaptive_captures(base_splits, dur, sig_at, diff_fn, max_frames=40,
                           diff_threshold=12.0, min_gap_s=25.0):
    """適応追撮の純粋スケジューラ（CDP 非依存＝オフラインでテスト可能）。

    sig_at(t) -> フレーム署名 or None（撮影失敗）。diff_fn(a, b) -> 変化率%。
    まず base_splits 点の均等グリッドを撮り、隣接署名の差が大きい谷間から順に中点を
    追撮する。`diff<=diff_threshold`（最大の谷間でも十分似ている）、`幅<min_gap_s`、
    または `max_frames` 到達で停止。板書が動いた所だけにキャプチャを集中させる。

    返り値: 実際に撮れた時刻の昇順リスト。sig_at が呼ばれるたびに撮影は起きるので、
    呼び出し側は sig_at 内で t→パスを控えておき、この戻り値でパスを引ける。
    """
    import heapq
    frames = []  # [(t, sig)]
    for i in range(base_splits):
        t = dur * (i + 0.5) / base_splits
        s = sig_at(t)
        if s is not None:
            frames.append((t, s))
    if not frames:
        return []

    heap = []
    seq = 0

    def push_gap(lo, hi):
        # heap タプルは (−diff, 連番, lo, hi)。連番でユニークにし、numpy 署名同士の
        # 比較（タプルの後方要素）に絶対に到達させない。
        nonlocal seq
        heapq.heappush(heap, (-diff_fn(lo[1], hi[1]), seq, lo, hi)); seq += 1

    ordered = sorted(frames, key=lambda x: x[0])
    for lo, hi in zip(ordered, ordered[1:]):
        push_gap(lo, hi)

    while len(frames) < max_frames and heap:
        negd, _, lo, hi = heapq.heappop(heap)
        if -negd <= diff_threshold:
            break  # 最大の谷間でも閾値以下なら、残りは全部それ以下
        if (hi[0] - lo[0]) < min_gap_s:
            continue  # これ以上割ると中点が近すぎる
        mt = (lo[0] + hi[0]) / 2.0
        ms = sig_at(mt)
        if ms is None:
            continue
        mid = (mt, ms)
        frames.append(mid)
        push_gap(lo, mid)
        push_gap(mid, hi)

    return sorted(t for t, _ in frames)


def split_and_capture_adaptive(tab, base_splits, out_dir, max_frames=40,
                               diff_threshold=12.0, min_gap_s=25.0,
                               bring_to_front=False, expect_title=None):
    """粗い N 分割グリッドを撮った後、隣接フレームのピクセル差分が大きい
    （＝板書が大きく変わった）谷間を優先して中点を追撮する適応キャプチャ。

    固定10分割の弱点＝「谷間で板書がまるごと変わって読めない箇所を手で追撮」を
    自動化する。crv (claude-real-video) のピクセル差分を、間引きではなく
    『どこを追撮するか』の判断に転用したもの。板書が動いた所へキャプチャを集中させ、
    静止区間には無駄打ちしない。スケジューリング本体は plan_adaptive_captures。

    引数:
      base_splits: 最初に撮る均等グリッドの枚数（10 目安）
      max_frames:  総キャプチャ上限（グリッド＋追撮の合計）。CDP は1枚2秒級なので予算で頭打ち
      diff_threshold: この%を超える差の谷間だけ追撮する（16x16 RGB のピクセル変化率）
      min_gap_s:   これ未満の幅の谷間はもう割らない（中点が近すぎて無意味）
    返り値: 保存した PNG パスのリスト（時刻昇順）。PIL 不在時は素の base_splits グリッドに退避。
    """
    os.makedirs(out_dir, exist_ok=True)
    try:
        import dedup  # 同ディレクトリ。差分判断の頭脳（PIL 依存）。
    except Exception:
        dedup = None

    ws = websocket.create_connection(tab['webSocketDebuggerUrl'], timeout=30)
    try:
        if bring_to_front:
            cdp_call(ws, "Page.bringToFront", msg_id=99); time.sleep(0.8)
        dur = wait_video_ready(ws, timeout_s=25)
        title_js = cdp_eval(ws, "document.title", 2)
        title_s = (title_js or "")[:60]
        if not dur or dur < 1:
            print(f"  [!] invalid/timeout duration (title={title_s})"); return []
        if expect_title and expect_title not in (title_js or ""):
            print(f"  [!] title mismatch: want '{expect_title}' got '{title_s}' -> skip")
            return []
        print(f"  duration={dur:.1f}s, title={title_s} (adaptive base={base_splits} max={max_frames})")

        cdp_eval(ws, "document.querySelector('video').play()", 3)
        time.sleep(1.2)
        cdp_call(ws, "Page.enable", msg_id=100)

        mid_id = [1000]      # ws メッセージID採番（クロージャで可変にする）
        saved = {}           # t(プランナーが渡す元の値) -> 保存パス

        def cap_raw(t):
            seek_t = max(0.0, min(dur - 0.5, float(t)))
            fp = os.path.join(out_dir, f"at{int(round(seek_t)):05d}s.png")
            raw = _seek_capture(ws, seek_t, fp, mid_id[0]); mid_id[0] += 3
            # 次の seek 前に少し再生（paused のまま seek するとたまに固まる既知事象）
            cdp_eval(ws, "document.querySelector('video').play()", mid_id[0]); mid_id[0] += 1
            time.sleep(0.25)
            if not raw:
                return None, fp
            saved[t] = fp
            return raw, fp

        # dedup/PIL が無ければ差分判断できない → 均等グリッドだけ撮って返す（安全側）
        if dedup is None:
            print("  [i] dedup/PIL 不在: 適応追撮はスキップし均等グリッドで返す")
            for i in range(base_splits):
                cap_raw(dur * (i + 0.5) / base_splits)
            return sorted(saved.values())

        def sig_at(t):
            raw, fp = cap_raw(t)
            if not raw:
                return None
            print(f"  cap t={float(t):6.1f}s -> {os.path.basename(fp)} [{len(saved)}]")
            return dedup.frame_sig_from_bytes(raw)

        times = plan_adaptive_captures(base_splits, dur, sig_at, dedup.pct_diff,
                                       max_frames=max_frames, diff_threshold=diff_threshold,
                                       min_gap_s=min_gap_s)
        out = sorted({saved[t] for t in times if t in saved and os.path.isfile(saved[t])})
        print(f"  adaptive done: {len(out)} frames (base {base_splits}, budget {max_frames})")
        return out
    finally:
        ws.close()


if __name__ == "__main__":
    # サブコマンド: split N out_dir  /  <秒数> <出力パス>
    if len(sys.argv) >= 3 and sys.argv[1] == "split":
        n = int(sys.argv[2])
        out_dir = sys.argv[3] if len(sys.argv) > 3 else rf"{BASE}\AppData\Local\Temp\cdp_split"
        tabs = get_video_tabs()
        if not tabs:
            print("no video tabs"); sys.exit(1)
        for t in tabs:
            print(f"tab: {t.get('title','')[:60]}")
            split_and_capture(t, n, out_dir)
            break
    else:
        target = int(sys.argv[1]) if len(sys.argv) > 1 else 600
        out = sys.argv[2] if len(sys.argv) > 2 else rf"{BASE}\AppData\Local\Temp\cdp_seek_{target}s.png"
        tabs = get_video_tabs()
        if not tabs:
            print("no video tabs"); sys.exit(1)
        print(f"Found {len(tabs)} video tab(s)")
        for t in tabs:
            print(f"  tab: {t.get('title','')[:60]}")
            seek_and_capture(t, target, out)
            break
