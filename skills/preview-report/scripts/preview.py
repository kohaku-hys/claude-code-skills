"""
予習レポート生成のワンショット・エントリーポイント

使い方:
    # キャプチャのみ（全動画を10分割して保存、Claude が後で Read & Agent 解析）
    python preview.py capture <url1> [<url2> ...] [--out <dir>] [--splits N]

    # 既に解析済みの JSON からレポート生成（レポート内容を Python 側で組み立てる場合）
    python preview.py generate --title "<タイトル>" --out <docx_path>
      (注: 実運用では Claude Code が Agent 解析後に report_gen を直接 import する想定)

    # Chrome CDP 状態確認
    python preview.py status

    # 全動画タブで split 10 を実行
    python preview.py capture-tabs --out <dir>

フロー（推奨）:
    1. python preview.py capture <URL...>     # Chrome 起動 + 認証 + 10分割
    2. Claude が Agent 並列でフレーム解析       # ~60秒
    3. Claude が report_gen.generate_docx()   # OMML付き Word 出力
"""
import sys, os, argparse, json, time
from pathlib import Path

# stdout/stderr を UTF-8 へ再構成（保険）。cp932 リダイレクト環境で out パス等に
# cp932 外文字が混ざっても UnicodeEncodeError でクラッシュしないよう backslashreplace。
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    sys.stderr.reconfigure(encoding='utf-8', errors='backslashreplace')
except Exception:
    pass

# このスクリプトのディレクトリを import パスに追加
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import chrome_cdp
import cdp_seek
import sharepoint_folder


def cmd_status(args):
    if chrome_cdp.is_cdp_alive():
        tabs = [t for t in chrome_cdp.list_tabs() if t.get('type') == 'page']
        print(f"[OK] CDP alive. {len(tabs)} tabs:")
        for t in tabs:
            print(f"  - {t.get('title','')[:70]}")
    else:
        print("[--] CDP down. Run: python preview.py capture <URL>")


def cmd_capture(args):
    """Chrome 起動 → URL を開く → 各動画を split 10 でキャプチャ"""
    out_dir = Path(args.out or HERE.parent.parent / "preview_capture")
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/3] Chrome CDP lifecycle...")
    chrome_cdp.start_chrome(args.urls)

    print(f"[2/3] Waiting for {len(args.urls)} video tab(s)...")
    tabs = chrome_cdp.wait_video_tabs(len(args.urls), timeout_s=45)
    # タイトルで安定ソート
    tabs.sort(key=lambda t: t.get('title', ''))
    print(f"  Found {len(tabs)} tab(s):")
    for t in tabs:
        print(f"    - {t.get('title','')[:70]}")

    print(f"[3/3] Capturing {args.splits} frames per video -> {out_dir}")
    meta = []
    for t in tabs:
        title = t.get('title', '')
        # "05_1" のようなパート番号を拾う
        import re
        m = re.search(r'(\d+)_(\d+)', title)
        sub = f"{m.group(1)}_{m.group(2)}" if m else f"tab_{len(meta)+1}"
        sub_dir = out_dir / sub
        sub_dir.mkdir(exist_ok=True)
        saved = cdp_seek.split_and_capture(t, args.splits, str(sub_dir))
        meta.append({
            "title": title,
            "subfolder": sub,
            "frames": [os.path.basename(p) for p in saved],
            "n_frames": len(saved),
        })

    manifest_path = out_dir / "manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump({"captured_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                   "videos": meta}, f, ensure_ascii=False, indent=2)
    print(f"\n[done] manifest: {manifest_path}")
    print(f"\nNext step: Claude will read frames and run Agent analysis.")


def cmd_capture_tabs(args):
    """既に Chrome で開かれている全 stream.aspx タブで split"""
    if not chrome_cdp.is_cdp_alive():
        print("[!] CDP not alive. Run 'capture <URL>' first")
        return
    tabs = [t for t in chrome_cdp.list_tabs()
            if t.get('type') == 'page' and 'stream.aspx' in t.get('url', '')]
    if not tabs:
        print("[!] No video tabs open")
        return
    out_dir = Path(args.out or HERE.parent.parent / "preview_capture")
    out_dir.mkdir(parents=True, exist_ok=True)

    tabs.sort(key=lambda t: t.get('title', ''))
    for t in tabs:
        import re
        m = re.search(r'(\d+)_(\d+)', t.get('title', ''))
        sub = f"{m.group(1)}_{m.group(2)}" if m else "tab"
        sub_dir = out_dir / sub
        sub_dir.mkdir(exist_ok=True)
        cdp_seek.split_and_capture(t, args.splits, str(sub_dir))


def cmd_list_folder(args):
    """SharePoint/OneDrive 共有フォルダの動画一括列挙（sharepoint_folder への薄い委譲）。

    列挙・グルーピング・JSON 書き出しのロジックは全て sharepoint_folder に集約する
    （二重化禁止）。本関数は引数を整形して enumerate_videos を呼ぶだけ。
    stdout は ASCII のみ（日本語ファイル名は一切 print せず JSON へ書く）。
    """
    exts = tuple(e.strip().lower() for e in args.exts.split(',') if e.strip())
    out = os.path.abspath(
        args.out or str(HERE.parent.parent / "preview_capture" / "folder_manifest.json"))
    rule = sharepoint_folder.load_rule(args.rule, use_fallback=args.use_fallback)
    res = sharepoint_folder.enumerate_videos(
        args.folder_url, out_json=out, exts=exts, rule=rule,
        recursive=args.recursive, auth_wait_s=args.auth_wait, timeout_s=args.timeout)
    st = res.get('status')
    # stdout 契約は sharepoint_folder.py main と完全一致させる
    # （STATUS=... count=... json=<絶対パス>。stdout は ASCII のみ）。
    if st == 'OK':
        g = res['groups']
        trunc = bool(res.get('log', {}).get('truncated'))
        tag = "OK_TRUNCATED" if trunc else "OK"
        print(f"STATUS={tag} count={res['count']} lectures={len(g['lectures'])} "
              f"unmatched={len(g['unmatched'])} truncated={str(trunc).lower()} json={out}")
        # 各回の概要は回番号と本数のみ（日本語 topic は出さない＝文字化け回避）。
        # 詳細（トピック等）は manifest JSON を Read ツールで読む。
        for lec in g['lectures']:
            print(f"  - kai={lec['kai']:02d} videos={len(lec['videos'])}")
    elif st == 'EMPTY':
        print(f"STATUS=EMPTY count=0 json={out}")
    elif st == 'AUTH_REQUIRED':
        print(f"STATUS=AUTH_REQUIRED please sign in on the opened Chrome window "
              f"then re-run json={out}")
    elif st == 'CDP_DOWN':
        print("STATUS=CDP_DOWN start chrome failed (port 9222)")
    elif st == 'TIMEOUT':
        print(f"STATUS=TIMEOUT folder did not stabilize json={out}")
    else:
        print(f"STATUS={st} json={out}")
    return res


def main():
    p = argparse.ArgumentParser(prog="preview.py")
    sp = p.add_subparsers(dest='cmd', required=True)

    p_status = sp.add_parser('status', help='Show CDP status')

    p_cap = sp.add_parser('capture', help='Start Chrome + capture split frames')
    p_cap.add_argument('urls', nargs='+')
    p_cap.add_argument('--out', help='Output directory')
    p_cap.add_argument('--splits', type=int, default=10)

    p_tabs = sp.add_parser('capture-tabs', help='Capture from already open tabs')
    p_tabs.add_argument('--out')
    p_tabs.add_argument('--splits', type=int, default=10)

    p_lf = sp.add_parser(
        'list-folder',
        help='Enumerate video files in a SharePoint/OneDrive shared folder via CDP')
    p_lf.add_argument('folder_url')
    p_lf.add_argument('--out')
    p_lf.add_argument('--exts', default='mp4,mov,wmv,avi,mkv,m4v')
    p_lf.add_argument('--rule', default='default_hanten')
    p_lf.add_argument('--use-fallback', action='store_true')
    p_lf.add_argument('--recursive', action='store_true')
    p_lf.add_argument('--auth-wait', type=int, default=120)
    p_lf.add_argument('--timeout', type=int, default=90)

    args = p.parse_args()
    {
        'status': cmd_status,
        'capture': cmd_capture,
        'capture-tabs': cmd_capture_tabs,
        'list-folder': cmd_list_folder,
    }[args.cmd](args)


if __name__ == "__main__":
    main()
