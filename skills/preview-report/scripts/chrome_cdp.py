"""
Chrome CDP ライフサイクル管理

- 9222 port が生きてれば再利用（Chrome を殺さない）
- 死んでれば --user-data-dir=<temp> で新規起動
- 認証 cookie は CDP プロファイルに保持される（初回ログイン後）
"""
import os, sys, time, subprocess, shutil
import requests
from pathlib import Path

CDP_PORT = 9222
CDP_URL = f"http://localhost:{CDP_PORT}"

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

CDP_PROFILE = Path.home() / "AppData" / "Local" / "Temp" / "chrome_cdp_profile"
DEFAULT_PROFILE = Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data"


def find_chrome():
    for p in CHROME_PATHS:
        if os.path.isfile(p):
            return p
    raise FileNotFoundError("Chrome not found")


def is_cdp_alive() -> bool:
    try:
        r = requests.get(f"{CDP_URL}/json/version", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def list_tabs():
    try:
        return requests.get(f"{CDP_URL}/json", timeout=3).json()
    except Exception:
        return []


def bootstrap_profile():
    """初回: 既存プロファイルの最低限ファイルをコピー（認証誘導を軽減）"""
    if CDP_PROFILE.exists():
        return
    dest = CDP_PROFILE / "Default"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "Network").mkdir(exist_ok=True)
    src = DEFAULT_PROFILE / "Default"
    # App-Bound 暗号化で cookie 復号は通常失敗するが、設定等は持ち込む
    for f in ("Preferences", "Secure Preferences", "Login Data", "Web Data"):
        p = src / f
        if p.exists():
            try:
                shutil.copy(p, dest / f)
            except Exception:
                pass
    # Local State (暗号化キー) もコピー
    ls = DEFAULT_PROFILE / "Local State"
    if ls.exists():
        try:
            shutil.copy(ls, CDP_PROFILE / "Local State")
        except Exception:
            pass


def start_chrome(urls: list, kill_existing: bool = True):
    """CDP Chrome を起動。既に動いていれば urls を追加タブで開く"""
    if is_cdp_alive():
        # 既存 Chrome 再利用：各 URL を新タブで開く
        for u in urls:
            import urllib.parse as up
            try:
                requests.put(f"{CDP_URL}/json/new?{up.quote(u, safe=':/?=&%')}", timeout=5)
            except Exception:
                pass
        time.sleep(3)
        return

    # 新規起動が必要
    if kill_existing:
        subprocess.run(["taskkill", "/IM", "chrome.exe", "/F"],
                       capture_output=True, text=True)
        time.sleep(3)

    bootstrap_profile()

    cmd = [
        find_chrome(),
        f"--remote-debugging-port={CDP_PORT}",
        "--remote-allow-origins=*",
        "--autoplay-policy=no-user-gesture-required",
        f"--user-data-dir={CDP_PROFILE}",
        "--no-first-run",
        "--no-default-browser-check",
        # --- 完全バックグラウンドキャプチャ用（背景/被遮蔽タブでも描画を止めない）---
        # これらが無いと背景タブの compositor が止まり、bringToFront でウィンドウを
        # 前面化しないと captureScreenshot が poster/古いフレームしか返さない。
        # 揃えることで bringToFront 無し（= 画面を一切奪わない）で実フレームを取れる。
        "--disable-renderer-backgrounding",
        "--disable-backgrounding-occluded-windows",
        "--disable-background-timer-throttling",
        "--disable-features=CalculateNativeWinOcclusion",
    ] + urls

    # バックグラウンド起動
    subprocess.Popen(cmd, creationflags=0x00000008 if sys.platform == 'win32' else 0)

    # CDP が立ち上がるまで待つ
    for _ in range(30):
        if is_cdp_alive():
            time.sleep(3)
            return
        time.sleep(1)
    raise RuntimeError("CDP failed to start")


def wait_video_tabs(n_expected: int, timeout_s: int = 30):
    """stream.aspx タブが n_expected 個現れるまで待つ（ログインリダイレクトで時間がかかる場合）"""
    import time as _t
    deadline = _t.time() + timeout_s
    while _t.time() < deadline:
        tabs = [t for t in list_tabs()
                if t.get('type') == 'page' and 'stream.aspx' in t.get('url', '')]
        if len(tabs) >= n_expected:
            return tabs
        _t.sleep(2)
    # timeout 時でもあるだけ返す
    return [t for t in list_tabs()
            if t.get('type') == 'page' and 'stream.aspx' in t.get('url', '')]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: chrome_cdp.py [status|start <url>...|tabs]")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "status":
        print("CDP alive" if is_cdp_alive() else "CDP down")
    elif cmd == "start":
        start_chrome(sys.argv[2:])
        print(f"Started. Tabs: {len(list_tabs())}")
    elif cmd == "tabs":
        for t in list_tabs():
            if t.get('type') == 'page':
                print(f"  {t.get('title','')[:60]}")
