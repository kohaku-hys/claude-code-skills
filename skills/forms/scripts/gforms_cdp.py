"""
Google Apps Script (script.google.com) を Chrome CDP で操作して
.gs を貼り付け→実行→生成された Google Form の URL を回収するドライバ。

前提: /preview-report の chrome_cdp.py（CDP ライフサイクル）を再利用する。
標準出力は ASCII のみ（日本語は出さない＝文字化け回避）。フォームURLはASCIIなので安全。

サブコマンド:
  open  <shot.png>           Chrome起動→新規プロジェクト作成URLを開く→状態print＋スクショ
  status                     現在の script.google.com タブの url/title/ログイン/エディタ有無
  shot  <out.png> [full]     現在タブをスクショ（full でページ全体）
  inject <code.utf8.gs>      Monaco エディタに全文セット（失敗時はタイプ入力）→ Ctrl+S 保存
  run                        実行ボタンをクリック（複数セレクタ試行）
  harvest <form_shot.png>    画面テキストから forms URL を抽出→公開フォームを開いてスクショ
"""
import sys, os, json, time, base64, re
import requests, websocket

CDP = "http://localhost:9222"
# chrome_cdp.py は preview-report スキルの scripts/ にある
sys.path.insert(0, os.path.expanduser(r"~/.claude/skills/preview-report/scripts"))
import chrome_cdp  # noqa

CREATE_URL = "https://script.google.com/home/projects/create"
CONFIG_PATH = os.path.expanduser(r"~/.claude/skills/forms/forms_config.json")


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def ensure_chrome(urls):
    """既存CDP(9222)を再利用。無ければユーザーのChromeを殺さずに起動。"""
    if chrome_cdp.is_cdp_alive():
        if urls:
            chrome_cdp.start_chrome(urls)          # 新タブで開く
    else:
        chrome_cdp.start_chrome(urls or [CREATE_URL], kill_existing=False)


def _pages():
    try:
        return [t for t in requests.get(f"{CDP}/json", timeout=5).json()
                if t.get("type") == "page"]
    except Exception:
        return []


def gas_tab():
    pages = _pages()
    for t in pages:
        if "script.google.com" in t.get("url", ""):
            return t
    for t in pages:
        if "accounts.google" in t.get("url", ""):
            return t
    return pages[0] if pages else None


def connect(tab):
    return websocket.create_connection(tab["webSocketDebuggerUrl"], timeout=40)


_ID = [1000]
def call(ws, method, params=None):
    _ID[0] += 1
    i = _ID[0]
    ws.send(json.dumps({"id": i, "method": method, "params": params or {}}))
    while True:
        m = json.loads(ws.recv())
        if m.get("id") == i:
            return m


def ev(ws, expr, awaitp=True):
    r = call(ws, "Runtime.evaluate",
             {"expression": expr, "returnByValue": True, "awaitPromise": awaitp})
    res = r.get("result", {}).get("result", {})
    return res.get("value")


def shot_tab(tab, out, full=False):
    ws = connect(tab)
    try:
        call(ws, "Page.enable")
        r = call(ws, "Page.captureScreenshot",
                 {"format": "png", "captureBeyondViewport": bool(full)})
        d = r.get("result", {}).get("data")
        if d:
            with open(out, "wb") as f:
                f.write(base64.b64decode(d))
            return True
        return False
    finally:
        ws.close()


def cmd_open(shot_path):
    if chrome_cdp.is_cdp_alive():
        chrome_cdp.start_chrome([CREATE_URL])         # 既存CDP再利用：新タブで開く
    else:
        chrome_cdp.start_chrome([CREATE_URL], kill_existing=False)
    # プロジェクト作成→エディタ読み込みを待つ
    for _ in range(20):
        time.sleep(2)
        t = gas_tab()
        if t and "/projects/" in t.get("url", "") and "/edit" in t.get("url", ""):
            break
    cmd_status()
    t = gas_tab()
    if t and shot_path:
        shot_tab(t, shot_path)
        print("SHOT=" + shot_path)


def cmd_status():
    t = gas_tab()
    if not t:
        print("STATUS=NO_TAB")
        return
    url = t.get("url", "")
    ws = connect(t)
    try:
        has_editor = ev(ws, "!!document.querySelector('.monaco-editor')", awaitp=False)
        has_monaco = ev(ws, "(typeof monaco!=='undefined' && !!monaco.editor)", awaitp=False)
        signed = "accounts.google" not in url
        title = ev(ws, "document.title", awaitp=False) or ""
    finally:
        ws.close()
    state = "EDITOR" if has_editor else ("LOGIN" if "accounts.google" in url else "LOADING")
    print("STATUS=" + state)
    print("URL=" + url[:120])
    print("TITLE=" + re.sub(r"[^\x20-\x7e]", "?", title)[:80])
    print("SIGNED_IN=" + str(bool(signed)))
    print("MONACO=" + str(bool(has_monaco)))


def cmd_shot(out, full=False):
    t = gas_tab()
    if not t:
        print("STATUS=NO_TAB"); return
    ok = shot_tab(t, out, full=full)
    print("SHOT=" + (out if ok else "FAIL"))


def cmd_inject(code_file):
    with open(code_file, "r", encoding="utf-8") as f:
        code = f.read()
    t = gas_tab()
    if not t:
        print("STATUS=NO_TAB"); return
    ws = connect(t)
    try:
        # まず Monaco の model に直接 setValue（最も確実）
        js = ("(function(){try{var ms=monaco.editor.getModels();"
              "if(ms&&ms.length){ms[0].setValue(" + json.dumps(code) + ");"
              "return 'OK:'+ms.length;}return 'NO_MODELS';}catch(e){return 'ERR:'+e;}})()")
        res = ev(ws, js, awaitp=False)
        print("INJECT=" + str(res))
        if not (isinstance(res, str) and res.startswith("OK")):
            # フォールバック: テキストエリアにフォーカスして全選択削除→挿入
            ev(ws, "(function(){var e=document.querySelector('.monaco-editor textarea');"
                   "if(e){e.focus();return 1;}return 0;})()", awaitp=False)
            for mod, k, code_k, vk in [(2, "a", "KeyA", 65), (0, "Delete", "Delete", 46)]:
                call(ws, "Input.dispatchKeyEvent", {"type": "keyDown", "modifiers": mod,
                     "key": k, "code": code_k, "windowsVirtualKeyCode": vk})
                call(ws, "Input.dispatchKeyEvent", {"type": "keyUp", "modifiers": mod,
                     "key": k, "code": code_k, "windowsVirtualKeyCode": vk})
            call(ws, "Input.insertText", {"text": code})
            print("INJECT=TYPED")
        time.sleep(0.6)
        # 保存 Ctrl+S
        for typ in ("keyDown", "keyUp"):
            call(ws, "Input.dispatchKeyEvent", {"type": typ, "modifiers": 2,
                 "key": "s", "code": "KeyS", "windowsVirtualKeyCode": 83})
        time.sleep(2.0)
        print("SAVED=1")
    finally:
        ws.close()


def cmd_run():
    t = gas_tab()
    if not t:
        print("STATUS=NO_TAB"); return
    ws = connect(t)
    try:
        js = """
(function(){
  var sels = ['[aria-label="Run"]','[aria-label="実行"]','[data-tooltip="Run"]',
              'button[guidedhelpid="run_button"]','.cdItcd-LgbsSe'];
  for (var i=0;i<sels.length;i++){var b=document.querySelector(sels[i]); if(b){b.click(); return 'CLICKED:'+sels[i];}}
  // 新IDEは Run ボタンが material-icon 'play_arrow' を含む（最も確実）
  var all=[].slice.call(document.querySelectorAll('*'));
  for (var k=0;k<all.length;k++){var e=all[k];
    if(e.childElementCount===0 && (e.textContent||'').trim()==='play_arrow'){
      var c=e.closest('button,[role=button],div[role=button]')||e.parentElement;
      if(c){c.click(); return 'CLICKED_PLAY';}}}
  // テキスト一致で探す
  var btns=[].slice.call(document.querySelectorAll('button,div[role=button]'));
  for (var j=0;j<btns.length;j++){var s=(btns[j].innerText||btns[j].getAttribute('aria-label')||'');
    if(/^(run|実行)$/i.test(s.trim())){btns[j].click(); return 'CLICKED_TEXT';}}
  return 'NO_RUN_BUTTON';
})()"""
        print("RUN=" + str(ev(ws, js, awaitp=False)))
    finally:
        ws.close()


def cmd_harvest(form_shot):
    t = gas_tab()
    if not t:
        print("STATUS=NO_TAB"); return
    ws = connect(t)
    try:
        txt = ev(ws, "document.body.innerText", awaitp=False) or ""
    finally:
        ws.close()
    urls = re.findall(r"https://docs\.google\.com/forms/[^\s\"'<>]+", txt)
    pub = next((u for u in urls if "viewform" in u or "/e/" in u), None)
    edit = next((u for u in urls if "/edit" in u), None)
    print("PUBLISHED=" + (pub or "NONE"))
    print("EDIT=" + (edit or "NONE"))
    if pub:
        chrome_cdp.start_chrome([pub])   # 公開フォームを新タブで開く
        time.sleep(5)
        # 公開フォームのタブを探す
        for p in _pages():
            if "docs.google.com/forms" in p.get("url", "") and "viewform" in p.get("url", ""):
                shot_tab(p, form_shot, full=True)
                print("SHOT=" + form_shot)
                break


def _inject_ws(ws, code):
    js = ("(function(){try{var ms=monaco.editor.getModels();"
          "if(ms&&ms.length){ms[0].setValue(" + json.dumps(code) + ");"
          "return 'OK';}return 'NO_MODELS';}catch(e){return 'ERR';}})()")
    return ev(ws, js, awaitp=False)


def _run_ws(ws):
    js = ("(function(){var a=[].slice.call(document.querySelectorAll('*'));"
          "for(var i=0;i<a.length;i++){var e=a[i];"
          "if(e.childElementCount===0&&(e.textContent||'').trim()==='play_arrow'){"
          "var c=e.closest('button,[role=button],div[role=button]')||e.parentElement;"
          "if(c){c.click();return 'CLICKED_PLAY';}}}return 'NO_RUN';})()")
    return ev(ws, js, awaitp=False)


def cmd_build(code_file, out_png):
    """ワンショット: 承認済みプロジェクトを再利用して .gs を流し込み→実行→実物URL回収。
    OAuth再承認なし（同一プロジェクト・同一スコープ）。未ログイン時のみ NEED_SIGNIN。"""
    cfg = load_config()
    pid = cfg.get("builder_project_id")
    with open(code_file, "r", encoding="utf-8") as f:
        code = f.read()
    if not pid:
        print("STATUS=NO_PROJECT_ID"); return
    edit_url = "https://script.google.com/home/projects/%s/edit" % pid
    ensure_chrome([edit_url])

    tab = None
    for _ in range(20):
        time.sleep(2)
        t = gas_tab()
        if not t:
            continue
        url = t.get("url", "")
        if "accounts.google" in url or "developers.google.com" in url:
            print("STATUS=NEED_SIGNIN"); return
        if pid in url and "/edit" in url:
            ws = connect(t)
            try:
                ok = ev(ws, "(typeof monaco!=='undefined'&&!!monaco.editor&&monaco.editor.getModels().length>0)", awaitp=False)
            finally:
                ws.close()
            if ok:
                tab = t; break
    if not tab:
        print("STATUS=NO_EDITOR"); return

    ws = connect(tab)
    try:
        print("INJECT=" + str(_inject_ws(ws, code)))
        for typ in ("keyDown", "keyUp"):   # Ctrl+S
            call(ws, "Input.dispatchKeyEvent", {"type": typ, "modifiers": 2,
                 "key": "s", "code": "KeyS", "windowsVirtualKeyCode": 83})
        time.sleep(2.5)
        print("RUN=" + str(_run_ws(ws)))
    finally:
        ws.close()

    # 実行ログにフォームURLが出るまで待つ（承認済みなのでダイアログは出ない想定）
    pub = edit = None
    for _ in range(25):
        time.sleep(2)
        ws = connect(tab)
        try:
            txt = ev(ws, "document.body.innerText", awaitp=False) or ""
        finally:
            ws.close()
        urls = re.findall(r"https://docs\.google\.com/forms/[^\s\"'<>]+", txt)
        pub = next((u for u in urls if "viewform" in u or "/e/" in u), None)
        edit = next((u for u in urls if "/edit" in u), None)
        if "承認が必要" in txt or "Authorization required" in txt:
            print("STATUS=NEED_OAUTH"); return
        if pub:
            break
    if not pub:
        print("STATUS=NO_URL"); return
    print("PUBLISHED=" + pub)
    print("EDIT=" + (edit or "NONE"))
    chrome_cdp.start_chrome([pub]); time.sleep(5)
    for p in _pages():
        if "docs.google.com/forms" in p.get("url", "") and "viewform" in p.get("url", ""):
            shot_tab(p, out_png, full=True)
            print("SHOT=" + out_png); break


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "open":
        cmd_open(sys.argv[2] if len(sys.argv) > 2 else "")
    elif cmd == "status":
        cmd_status()
    elif cmd == "shot":
        cmd_shot(sys.argv[2], full=(len(sys.argv) > 3 and sys.argv[3] == "full"))
    elif cmd == "inject":
        cmd_inject(sys.argv[2])
    elif cmd == "run":
        cmd_run()
    elif cmd == "harvest":
        cmd_harvest(sys.argv[2] if len(sys.argv) > 2 else "form.png")
    elif cmd == "build":
        cmd_build(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "form.png")
    else:
        print("unknown cmd")
