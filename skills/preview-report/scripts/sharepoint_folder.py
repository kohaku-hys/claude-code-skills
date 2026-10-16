"""
SharePoint / OneDrive 共有フォルダの動画ファイル一括列挙

共有フォルダの「共有リンク」（個別の stream.aspx ではなく AllItems.aspx / ?id= を
含むフォルダURL）を Chrome CDP で開き、スクロール仮想化に対応した単一の
Runtime.evaluate で全動画ファイル名を列挙する。さらに汎用2段グルーピング規則で
回（kai）ごとに整理した manifest を UTF-8 JSON に書き出す。

設計方針（案B＝薄い委譲 + 案Aの回ごと/平坦構造の統合）:
  - CDP ライフサイクル（is_cdp_alive / start_chrome / list_tabs）は chrome_cdp を再利用し
    本モジュールでは再実装しない。
  - WS 接続・Runtime.evaluate は cdp_seek.seek_and_capture / cdp_call と同一の I/O 規約。
  - ブラウザ側収集は build_collector_js() が生成する『単一』async IIFE で 1 往復に圧縮。
  - 列挙結果は classify_status で STATUS に正規化（EMPTY と AUTH_REQUIRED を必ず区別）。
  - グルーピング規則は load_rule の辞書に 1 エントリ追加するだけで別科目へ拡張可能。

出力規約:
  - コンソールは日本語を一切 print しない（文字化けする）。
  - 日本語ファイル名は ensure_ascii=False の UTF-8 JSON にだけ書き、Claude は Read で読む。
  - stdout は ASCII の件数と JSON 絶対パスのみ。

使い方:
    python sharepoint_folder.py list-folder "<folder_url>" \
        [--out <json>] [--exts mp4,mov,...] [--rule default_hanten|generic] \
        [--use-fallback] [--recursive] [--auth-wait 120] [--timeout 90]
"""
from __future__ import annotations
import os, sys, re, json, time, argparse
from pathlib import Path

# stdout/stderr を UTF-8 へ再構成（保険）。cp932 リダイレクト環境で out パス等に
# cp932 外文字が混ざっても UnicodeEncodeError でクラッシュしないよう backslashreplace。
# 設計契約『stdout は ASCII のみ』を壊さない範囲の防御策。
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    sys.stderr.reconfigure(encoding='utf-8', errors='backslashreplace')
except Exception:
    pass

# このスクリプトのディレクトリを import パスへ（chrome_cdp / cdp_seek をローカル import）
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import chrome_cdp
import websocket

# 既定の動画拡張子フィルタ（大小無視・末尾アンカー）
DEFAULT_EXTS = ("mp4", "mov", "wmv", "avi", "mkv", "m4v")


# === 内部ヘルパ（非純粋: CDP / WS） ===

def _connect_page_ws(timeout: int = 20, retries: int = 3):
    """type=='page' タブの webSocketDebuggerUrl へ WS 接続する（非純粋）。

    cdp_seek.seek_and_capture と同一の接続パターン
    （websocket.create_connection(ws_url, timeout=...)）を踏襲。
    指数バックオフで最大 retries 回リトライし、page タブが空 / 接続不可なら例外を投げる
    （呼び出し側 enumerate_videos が CDP_DOWN に正規化する）。

    Returns: (ws, tab)
    """
    last_err = None
    for attempt in range(retries):
        try:
            tabs = [t for t in chrome_cdp.list_tabs() if t.get('type') == 'page']
            if not tabs:
                raise RuntimeError("no 'page' tab available")
            tab = tabs[0]
            ws_url = tab.get('webSocketDebuggerUrl')
            if not ws_url:
                raise RuntimeError("tab has no webSocketDebuggerUrl")
            ws = websocket.create_connection(ws_url, timeout=timeout)
            return ws, tab
        except Exception as e:
            last_err = e
            # 指数バックオフ（1, 2, 4, ... 秒）。最終試行後は待たない
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"could not connect to a page tab after {retries} tries: {last_err}")


def _cdp_eval(ws, expr: str, msg_id: int, await_promise: bool = True):
    """Runtime.evaluate の薄いラッパ（非純粋）。

    cdp_seek.cdp_call / cdp_eval と同一 I/O 規約。
    {id, method:'Runtime.evaluate', params:{expression, returnByValue:true,
     awaitPromise:await_promise}} を送り result.result.value を返す。
    レスポンスに exceptionDetails があれば RuntimeError を投げ、
    『静かな空配列』を EMPTY でなく障害として顕在化させる。
    build_collector_js は async IIFE なので await_promise 既定 True。
    """
    ws.send(json.dumps({
        "id": msg_id,
        "method": "Runtime.evaluate",
        "params": {
            "expression": expr,
            "returnByValue": True,
            "awaitPromise": await_promise,
        },
    }))
    while True:
        resp = json.loads(ws.recv())
        if resp.get('id') == msg_id:
            result = resp.get('result', {})
            if 'exceptionDetails' in result:
                raise RuntimeError(f"Runtime.evaluate raised: {result['exceptionDetails']}")
            return result.get('result', {}).get('value')


def _navigate_and_wait(ws, folder_url: str, timeout_s: float = 30,
                       exts: tuple = DEFAULT_EXTS) -> str:
    """Page.navigate で folder_url へ遷移し、ロード完了まで待つ（非純粋）。

    Page.enable→Page.navigate→document.readyState==='complete' かつ行要素
    （動画拡張子テキスト）出現まで固定待ち + 条件ポーリング（ナビゲート直後レース対策）。
    現在のタブURLを文字列で返す（認証切れ / 復帰判定に使用）。
    タイムアウト時も現在URLをそのまま返し、呼び出し側が classify_status で
    TIMEOUT / AUTH を判定する。

    exts は行要素出現プローブの拡張子集合。コレクタと同じ集合を渡すことで、
    カスタム --exts でも早期確定（hit）が働く（既定は DEFAULT_EXTS）。
    """
    # cdp_seek.cdp_call と同じく id 一致まで recv する素朴な送受信
    def _call(method, params, mid):
        ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        while True:
            r = json.loads(ws.recv())
            if r.get('id') == mid:
                return r

    _call("Page.enable", {}, 7001)
    _call("Page.navigate", {"url": folder_url}, 7002)

    # ナビゲート直後はまだ前ページが残るレースがあるため少し待つ
    time.sleep(2)

    deadline = time.time() + timeout_s
    # 拡張子のORパターン（行要素出現確認用）。ネット側で評価される。
    # コレクタと同じ exts を使い、カスタム拡張子でも hit を取りこぼさない
    ext_re = "|".join(re.escape(e) for e in (exts or DEFAULT_EXTS))
    probe = (
        "(function(){"
        "var rs=document.readyState;"
        "var hit=false;"
        "var els=document.querySelectorAll('*');"
        "for(var i=0;i<els.length;i++){var e=els[i];"
        "if(e.children.length===0){var t=(e.textContent||'').trim();"
        "if(t&&/\\.(" + ext_re + ")$/i.test(t)){hit=true;break;}}}"
        "return JSON.stringify({rs:rs,hit:hit,url:location.href});"
        "})()"
    )
    last_url = folder_url
    mid = 7100
    while time.time() < deadline:
        try:
            raw = _cdp_eval(ws, probe, mid, await_promise=False)
            mid += 1
            if raw:
                info = json.loads(raw)
                last_url = info.get('url', last_url)
                # 認証切れに飛んでいたら待ち続けても無駄なので即返す
                low = last_url.lower()
                if ('login.microsoftonline.com' in low or 'login.live.com' in low
                        or 'adfs' in low):
                    return last_url
                if info.get('rs') == 'complete' and info.get('hit'):
                    return last_url
        except Exception:
            # ナビゲート直後の評価失敗は無視してポーリング継続
            pass
        time.sleep(1.5)
    return last_url


# ログインドメイン判定（復帰検知で再利用）。これらを URL から抜けたら
# 『サインイン完了候補』とみなし、元 folder_url へ再ナビゲートして最終判定する。
_LOGIN_MARKERS = ('login.microsoftonline.com', 'login.live.com', 'adfs', '/oauth2/')


def _is_login_url(url: str) -> bool:
    """url がログイン系ドメイン/パスを含むか（純粋）。"""
    low = (url or "").lower()
    return any(k in low for k in _LOGIN_MARKERS)


def _list_page_tab_urls() -> list:
    """全 'page' タブの URL を列挙する（非純粋）。

    ログインが別タブ/ポップアップで進むケースを追従するため、ws 固定の
    location.href 一本ではなく list_tabs() の全 page タブ URL を走査する。
    list_tabs が落ちていれば空リスト（呼び出し側で CDP_DOWN 判定に回す）。
    """
    try:
        return [t.get('url', '') for t in chrome_cdp.list_tabs()
                if t.get('type') == 'page']
    except Exception:
        return []


# === 純粋関数（ネット不要・smoke 対象） ===

def build_collector_js(exts: tuple = DEFAULT_EXTS, max_rounds: int = 200,
                       stable_rounds: int = 3, scroll_px: int = 2000,
                       settle_ms: int = 350, max_chars: int = 200) -> str:
    """スクロール仮想化対応の『単一』ブラウザ側収集式（async IIFE 文字列）を生成（純粋）。

    1 回の Runtime.evaluate で完結する: 実際にスクロール可能なコンテナを
    全候補（[data-automationid=ScrollRegion] / [role=grid]）から選び
    （scrollHeight>clientHeight を満たす最大のもの。無ければ scrollingElement→body）、
    末尾までスクロールしつつ各ラウンドで
      (1) 全要素リーフテキスト走査（children.length===0 && 拡張子正規表現 && trim().length<max_chars）
      (2) 補助 [data-automationid=FieldRenderer-name]
    の和集合を Set に蓄積。

    終了条件は『件数が stable_rounds 回連続で不変 かつ 末尾到達（atBottom）』。
    末尾未到達なら件数不変でも待機を延ばして再 harvest（遅延ロード早期 break 防止）。
    スクロールが実際に進まなければ別コンテナへフォールバックし、それでも進まず
    末尾でもなければ停滞とみなす。break 直後にもう一段スクロール+待機して末尾増分を回収。
    打ち切り（max_rounds 到達かつ末尾未到達）は truncated=true で呼び出し側へ伝える。
    {files,rounds,stable,selectorHit,truncated,atBottom,scrolled,url} を JSON.stringify して返す。

    式生成自体はネット不要。exts の OR 展開・querySelectorAll を含むことを単体検証できる。
    """
    # 拡張子の OR パターン（JS 正規表現リテラルへ埋め込む）
    ext_alt = "|".join(re.escape(e) for e in exts)
    # JS テンプレート。Python の format を避け、置換トークンで安全に埋め込む
    js = """(async () => {
  const EXT_RE = /\\.(__EXT_ALT__)$/i;
  const MAX_ROUNDS = __MAX_ROUNDS__;
  const STABLE_TARGET = __STABLE_ROUNDS__;
  const SCROLL_PX = __SCROLL_PX__;
  const SETTLE = __SETTLE_MS__;
  const MAX_CHARS = __MAX_CHARS__;
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));

  // スクロールコンテナ選定: 実際にスクロール可能（scrollHeight>clientHeight）な
  // 候補の中から最大の scrollHeight を持つものを選ぶ。なければ scrollingElement→body。
  function pickContainer() {
    const cands = Array.from(
      document.querySelectorAll('[data-automationid=ScrollRegion],[role=grid]'));
    let best = null;
    let bestH = -1;
    for (const c of cands) {
      if (c && c.scrollHeight > c.clientHeight + 4 && c.scrollHeight > bestH) {
        best = c;
        bestH = c.scrollHeight;
      }
    }
    if (best) return best;
    return document.scrollingElement || document.body;
  }

  const collected = new Set();
  const hits = new Set();

  function harvest() {
    // (1) 実証済み: 全要素のリーフテキスト走査
    const all = document.querySelectorAll('*');
    for (let i = 0; i < all.length; i++) {
      const e = all[i];
      if (e.children.length === 0) {
        const t = (e.textContent || '').trim();
        if (t && EXT_RE.test(t) && t.length < MAX_CHARS) {
          collected.add(t);
          hits.add('leaf-scan');
        }
      }
    }
    // (2) 補助: FieldRenderer-name セレクタ
    const named = document.querySelectorAll('[data-automationid=FieldRenderer-name]');
    for (let i = 0; i < named.length; i++) {
      const t = (named[i].textContent || '').trim();
      if (t && EXT_RE.test(t) && t.length < MAX_CHARS) {
        collected.add(t);
        hits.add('field-renderer');
      }
    }
  }

  // 実スクロール: コンテナ優先、進まなければ別コンテナ/window へフォールバック。
  // スクロール前後で scrollTop が変化したか（=実際に進んだか）を返す。
  function isAtBottom(c) {
    if (!c) return false;
    return (c.scrollTop + c.clientHeight >= c.scrollHeight - 2);
  }
  function doScroll(c) {
    let before = -1;
    try {
      if (c && typeof c.scrollTop === 'number') {
        before = c.scrollTop;
        // ステップは『ビューポート高 - 1行分の重なり』を上限にして
        // 仮想化の描画ウィンドウが必ず重なるようにする（中間行の飛ばし防止）。
        // clientHeight 不明なら SCROLL_PX へフォールバック。
        let step = SCROLL_PX;
        if (typeof c.clientHeight === 'number' && c.clientHeight > 0) {
          step = Math.max(1, Math.min(SCROLL_PX, c.clientHeight - 50));
        }
        c.scrollTop = c.scrollTop + step;
        if (c.scrollTop !== before) return true;
      }
    } catch (e) { /* fall through to window */ }
    // コンテナで進まなかった: window スクロールへフォールバック
    const wy = window.scrollY;
    const wstep = (typeof window.innerHeight === 'number' && window.innerHeight > 0)
      ? Math.max(1, Math.min(SCROLL_PX, window.innerHeight - 50)) : SCROLL_PX;
    try { window.scrollBy(0, wstep); } catch (e) {}
    return window.scrollY !== wy;
  }

  let container = pickContainer();
  let stable = 0;
  let prevSize = -1;
  let rounds = 0;
  let atBottom = false;
  let scrolled = false;       // 一度でも実スクロールできたか
  let settle = SETTLE;        // アダプティブ・バックオフ用
  for (rounds = 1; rounds <= MAX_ROUNDS; rounds++) {
    harvest();
    atBottom = isAtBottom(container);
    if (collected.size === prevSize) {
      stable += 1;
      // 件数不変でも『末尾到達』が確認できるまでは確定しない。
      // 末尾未到達なら待機を延ばして遅延ロードを待つ（アダプティブ・バックオフ）。
      if (stable >= STABLE_TARGET && atBottom) break;
      if (!atBottom) settle = Math.min(settle * 2, SETTLE * 6);
    } else {
      stable = 0;
      prevSize = collected.size;
      settle = SETTLE;
    }
    const moved = doScroll(container);
    if (moved) scrolled = true;
    if (!moved && !atBottom) {
      // 現コンテナで進まず末尾でもない: 別コンテナを選び直して再試行
      const alt = pickContainer();
      if (alt && alt !== container) {
        container = alt;
      } else {
        // どのコンテナでも進めない & 末尾でもない = 非スクロール環境とみなし停止
        break;
      }
    }
    await sleep(settle);
  }
  // break 直後の末尾増分を確実に回収: もう一段スクロール + 待機 + harvest
  doScroll(container);
  await sleep(SETTLE);
  harvest();
  atBottom = isAtBottom(container);

  const truncated = (rounds >= MAX_ROUNDS && !atBottom);

  return JSON.stringify({
    files: Array.from(collected),
    rounds: rounds,
    stable: stable,
    selectorHit: hits.size ? Array.from(hits).join('+') : 'none',
    truncated: truncated,
    atBottom: atBottom,
    scrolled: scrolled,
    url: location.href,
  });
})()"""
    js = (js
          .replace("__EXT_ALT__", ext_alt)
          .replace("__MAX_ROUNDS__", str(int(max_rounds)))
          .replace("__STABLE_ROUNDS__", str(int(stable_rounds)))
          .replace("__SCROLL_PX__", str(int(scroll_px)))
          .replace("__SETTLE_MS__", str(int(settle_ms)))
          .replace("__MAX_CHARS__", str(int(max_chars))))
    return js


def classify_status(url: str, files: list) -> str:
    """列挙結果を STATUS に正規化（純粋・smoke 対象）。

    - url が login.microsoftonline.com / login.live.com / adfs を含めば 'AUTH_REQUIRED'。
    - *.sharepoint.com 系で files が空なら 'EMPTY'、files があれば 'OK'。
    - それ以外（sharepoint 系でない URL）も保守的に 'EMPTY'。

    0件成功（EMPTY）と認証切れ（AUTH_REQUIRED）を必ず区別する。
    CDP_DOWN / TIMEOUT は接続・ナビゲート層の例外/タイムアウトから enumerate_videos 側で付与。
    """
    low = (url or "").lower()
    if ('login.microsoftonline.com' in low or 'login.live.com' in low
            or 'adfs' in low):
        return 'AUTH_REQUIRED'
    if 'sharepoint.com' in low:
        return 'OK' if files else 'EMPTY'
    # sharepoint 系でない URL は保守的に EMPTY（捏造穴埋めを誘発しない）
    return 'EMPTY'


def load_rule(name: str = 'default_hanten', use_fallback: bool = False) -> dict:
    """ルール名からグルーピング設定辞書を返す（純粋・smoke 対象）。

    新パターンはここに 1 エントリ追加するだけで別科目へ拡張可能（科目名プレフィックス非依存）。
    use_fallback を dict に同梱し parse_one / group_videos が参照する（既定 OFF）。
    """
    rules = {
        'default_hanten': {
            'rule_id': 'default_hanten',
            'primary': re.compile(
                r'(?:.*?_)?(?:反転授業用)?動画_(?P<kai>\d{2})_(?P<sub>\d+)_(?P<topic>.+?)'
                r'\.(?P<ext>mp4|mov|wmv|avi|mkv|m4v)$',
                re.IGNORECASE),
            'fallback': re.compile(
                r'(?:.*?_)?(?:反転授業用)?動画_(?P<kai>\d{1,3})_(?P<sub>\d+)_',
                re.IGNORECASE),
        },
        'generic': {
            'rule_id': 'generic',
            'primary': re.compile(
                r'(?P<kai>\d{1,3})_(?P<sub>\d+)_(?P<topic>.+?)'
                r'\.(?P<ext>mp4|mov|wmv|avi|mkv|m4v)$',
                re.IGNORECASE),
            'fallback': re.compile(
                r'(?P<kai>\d{1,3})_(?P<sub>\d+)',
                re.IGNORECASE),
        },
    }
    rule = rules.get(name)
    if rule is None:
        raise ValueError(f"unknown rule: {name!r} (known: {list(rules)})")
    # 浅いコピーへ use_fallback を同梱（呼び出し側で別名指定時の汚染を避ける）
    out = dict(rule)
    out['use_fallback'] = bool(use_fallback)
    return out


def _ext_from_name(name: str) -> str:
    """ファイル名末尾から拡張子（小文字・ドット無し）を取り出す。無ければ ''。"""
    m = re.search(r'\.([A-Za-z0-9]+)$', name or '')
    return m.group(1).lower() if m else ''


def parse_one(name: str, rule: dict = None) -> dict | None:
    """単一ファイル名を rule に従ってパース（純粋・smoke 主対象）。

    primary→(rule['use_fallback']==True のとき)fallback の順でパースし
    {kai:int, sub:int, topic:str, ext:str, via:str} を返す。
    rule 未指定時は load_rule('default_hanten') を内部既定とする。
    primary 一致は via='primary'、fallback 救済は via='fallback'
    （topic 欠落時は ''、ext は拡張子から補完）。
    どちらにも当たらなければ None（fallback OFF 時に強制グループ化しない）。
    """
    if rule is None:
        rule = load_rule('default_hanten')

    m = rule['primary'].search(name)
    if m:
        gd = m.groupdict()
        return {
            'kai': int(gd['kai']),
            'sub': int(gd['sub']),
            'topic': gd.get('topic') or '',
            'ext': (gd.get('ext') or _ext_from_name(name)).lower(),
            'via': 'primary',
        }

    if rule.get('use_fallback'):
        mf = rule['fallback'].search(name)
        if mf:
            gd = mf.groupdict()
            return {
                'kai': int(gd['kai']),
                'sub': int(gd['sub']),
                'topic': gd.get('topic') or '',
                'ext': (gd.get('ext') or _ext_from_name(name)).lower(),
                'via': 'fallback',
            }

    return None


def group_videos(files: list, rule: dict = None) -> dict:
    """汎用2段グルーピングの中核（純粋・smoke 対象）。

    第1段=拡張子フィルタ、第2段=parse_one で回（kai）へ割当て。
    マッチ名は kai 昇順・同一回内 sub 昇順で整列、非マッチ名は捨てず unmatched へ退避。
    欠番（例: 第08回）は by_kai_sorted から自然に欠落させるのみで、キー '8' を
    空配列やダミーで埋めない（捏造禁止）。

    Returns: {rule_id, lectures, matched, flat, by_kai_sorted, unmatched}
    """
    if rule is None:
        rule = load_rule('default_hanten')

    # 拡張子フィルタ用の許可セット（rule は正規表現側で拡張子を持つが、
    # 第1段の明示フィルタとして DEFAULT_EXTS を使う。大小無視・末尾アンカー）
    allowed = set(e.lower() for e in DEFAULT_EXTS)

    matched_by_kai = {}     # int kai -> list of record dict
    unmatched = []

    for name in (files or []):
        ext = _ext_from_name(name)
        if ext not in allowed:
            unmatched.append(name)
            continue
        parsed = parse_one(name, rule)
        if parsed is None:
            unmatched.append(name)
            continue
        rec = {
            'name': name,
            'kai': parsed['kai'],
            'sub': parsed['sub'],
            'topic': parsed['topic'],
            'ext': parsed['ext'],
            'via': parsed['via'],
        }
        matched_by_kai.setdefault(parsed['kai'], []).append(rec)

    # 各回内を sub 昇順に整列
    for kai in matched_by_kai:
        matched_by_kai[kai].sort(key=lambda r: (r['sub'], r['name']))

    by_kai_sorted = sorted(matched_by_kai.keys())

    # matched: 回キー（int を文字列化）基準
    matched = {str(kai): matched_by_kai[kai] for kai in by_kai_sorted}

    # lectures: report_gen が 1 回=1 docx 単位として直接消費する整形済みビュー
    lectures = []
    flat = []
    for kai in by_kai_sorted:
        recs = matched_by_kai[kai]
        videos = []
        topics = []
        for r in recs:
            vid_id = f"{r['kai']:02d}_{r['sub']}"
            videos.append({
                'id': vid_id,
                'filename': r['name'],
                'topic': r['topic'],
                'via': r['via'],
            })
            topics.append(r['topic'])
            flat.append({
                'id': vid_id,
                'filename': r['name'],
                'kai': r['kai'],
                'sub': r['sub'],
                'topic': r['topic'],
                'ext': r['ext'],
                'via': r['via'],
            })
        lectures.append({
            'kai': kai,
            'kai_label': f"第{kai:02d}回",
            'videos': videos,
            'topics': topics,
        })

    return {
        'rule_id': rule.get('rule_id', 'unknown'),
        'lectures': lectures,
        'matched': matched,
        'flat': flat,
        'by_kai_sorted': by_kai_sorted,
        'unmatched': unmatched,
    }


# === 公開エントリ（非純粋） ===

def enumerate_videos(folder_url: str, out_json: str | None = None,
                     exts: tuple = DEFAULT_EXTS, rule: dict | None = None,
                     recursive: bool = False, auth_wait_s: int = 120,
                     timeout_s: int = 90) -> dict:
    """共有フォルダを列挙してグルーピング済み manifest を返し JSON へ書き出す（非純粋）。

    フロー:
      chrome_cdp.is_cdp_alive()→未起動なら chrome_cdp.start_chrome([folder_url])
      →_connect_page_ws→_navigate_and_wait→build_collector_js() を 1 回 _cdp_eval で実行
      →files 取得→classify_status(final_url, files)。
      AUTH_REQUIRED なら ASCII でサインイン促し→全 page タブ URL を走査し
      『ログインドメインを脱出』するまでポーリング（KMSI/office.com 着地でも復帰判定）
      →元 folder_url へ再ナビゲートして再列挙（復帰時 log.auth_recovered=True）、
      再び AUTH なら残予算で1回だけ再待機し、なお失効なら log.auth_recovered_but_reexpired=True。
      待機中に CDP/WS が落ちたら CDP_DOWN、超過で TIMEOUT。接続不可は CDP_DOWN。
      確定後 group_videos(files, rule or load_rule()) を適用し manifest を組み立てる。
    """
    if rule is None:
        rule = load_rule()
    if out_json is None:
        out_json = str(HERE.parent.parent / "preview_capture" / "folder_manifest.json")
    out_json = os.path.abspath(out_json)

    log = {
        'selector_hit': None,
        'scroll_rounds': 0,
        'stable_rounds': 0,
        'truncated': False,
        'auth_recovered': False,
        'auth_recovered_but_reexpired': False,
        'navigations': 0,
        'ws_retries': 0,
        'recursive': bool(recursive),
        'write_error': None,
    }

    def _write(manifest):
        try:
            os.makedirs(os.path.dirname(out_json), exist_ok=True)
            with open(out_json, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
        except Exception as e:
            # 書き込み失敗を可観測化（stdout には出さず log に残す＝文字化けしない）。
            # 下流が『status=OK だが JSON が無い/古い』を検知できるようにする。
            log['write_error'] = repr(e)
        return manifest

    def _build_manifest(status, final_url, files):
        groups = group_videos(files, rule)
        return {
            'status': status,
            '_status_enum': 'OK | AUTH_REQUIRED | EMPTY | CDP_DOWN | TIMEOUT',
            'folder_url': folder_url,
            'final_url': final_url,
            'count': len(files),
            'files': files,
            'groups': groups,
            'log': log,
            'captured_at': time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    # --- CDP ライフサイクル ---
    try:
        if not chrome_cdp.is_cdp_alive():
            chrome_cdp.start_chrome([folder_url])
        if not chrome_cdp.is_cdp_alive():
            raise RuntimeError("CDP still down after start_chrome")
    except Exception:
        return _write(_build_manifest('CDP_DOWN', folder_url, []))

    # --- WS 接続 ---
    ws = None
    try:
        try:
            ws, _tab = _connect_page_ws(timeout=20, retries=3)
        except Exception:
            return _write(_build_manifest('CDP_DOWN', folder_url, []))

        collector = build_collector_js(exts=tuple(exts))

        def _enumerate_once(nav_url):
            """1 回分: ナビゲート→収集式実行→(final_url, files) を返す。"""
            log['navigations'] += 1
            final_url = _navigate_and_wait(ws, nav_url, timeout_s=min(timeout_s, 60),
                                           exts=tuple(exts))
            raw = _cdp_eval(ws, collector, msg_id=8000 + log['navigations'],
                            await_promise=True)
            files = []
            if raw:
                try:
                    info = json.loads(raw)
                    files = info.get('files', []) or []
                    log['selector_hit'] = info.get('selectorHit', log['selector_hit'])
                    log['scroll_rounds'] = info.get('rounds', log['scroll_rounds'])
                    log['stable_rounds'] = info.get('stable', log['stable_rounds'])
                    log['truncated'] = bool(info.get('truncated', log['truncated']))
                    final_url = info.get('url', final_url)
                except Exception:
                    files = []
            return final_url, files

        deadline = time.time() + timeout_s

        try:
            final_url, files = _enumerate_once(folder_url)
        except Exception:
            return _write(_build_manifest('TIMEOUT', folder_url, []))

        status = classify_status(final_url, files)

        # --- 認証切れ → サインイン待ち → 復帰再列挙 ---
        # 復帰判定は『SharePoint 到達』に固定せず『ログインドメインを抜けた』へ緩める。
        # MS ログイン後は KMSI / office.com / portal.office.com 等に着地し
        # sharepoint.com へ自発遷移しないことが多いため。脱出を検知したら元 folder_url
        # へ再ナビゲートして classify_status で最終判定する。
        def _auth_wait_and_recover():
            """サインイン待ち→脱出検知→再ナビゲート→再列挙。

            (recovered: bool, status, final_url, files, fatal_manifest or None) を返す。
            fatal_manifest が非 None なら即 return すべき終局状態（CDP_DOWN 等）。
            """
            print("Please sign in on the opened Chrome window")
            # auth 待ちを全体予算へクランプ（待機後の再列挙ぶん最大60sを残す）。
            budget = max(0, deadline - time.time() - 60)
            auth_deadline = time.time() + min(auth_wait_s, budget) if budget > 0 \
                else time.time() + auth_wait_s
            poll = 0
            while time.time() < auth_deadline:
                time.sleep(3)
                poll += 1
                # 待機中に Chrome/WS が落ちたら TIMEOUT ではなく CDP_DOWN で区別する
                if not chrome_cdp.is_cdp_alive():
                    return (False, 'CDP_DOWN', folder_url, [],
                            _build_manifest('CDP_DOWN', folder_url, []))
                # 全 page タブの URL を走査（ログインが別タブ/ポップアップで進むケース追従）。
                # どれか1つでもログインドメインを抜けていれば『サインイン完了候補』。
                tab_urls = _list_page_tab_urls()
                # バインド済み ws の location.href も補助的に確認（毎回 msg_id を変えて
                # stale 応答の取り違えを防ぐ）
                try:
                    cur_url = _cdp_eval(ws, "location.href", 8900 + poll,
                                        await_promise=False) or ''
                except Exception:
                    cur_url = ''
                if cur_url:
                    tab_urls = tab_urls + [cur_url]
                # sharepoint.com に既に到達しているタブがあれば即復帰候補
                reached_sp = any('sharepoint.com' in (u or '').lower()
                                 and not _is_login_url(u) for u in tab_urls)
                escaped_login = any(u and not _is_login_url(u) for u in tab_urls)
                if reached_sp or escaped_login:
                    return (True, None, final_url, files, None)
            return (False, 'TIMEOUT', folder_url, [],
                    _build_manifest('TIMEOUT', folder_url, []))

        if status == 'AUTH_REQUIRED':
            recovered, _st, _fu, _fl, fatal = _auth_wait_and_recover()
            if not recovered:
                return _write(fatal)
            # 復帰: 元 folder_url へ再ナビゲートして再列挙
            log['auth_recovered'] = True
            try:
                final_url, files = _enumerate_once(folder_url)
            except Exception:
                return _write(_build_manifest('TIMEOUT', folder_url, []))
            status = classify_status(final_url, files)

            # 再列挙が再び AUTH_REQUIRED: 残り予算があれば1回だけ再待機。
            # それでも再失効するなら、Cookie 未保存（App-Bound 暗号化で復号失敗の
            # 可能性）として log にフラグを残し、AUTH_REQUIRED のまま返す。
            if status == 'AUTH_REQUIRED':
                if (deadline - time.time()) > 65:
                    recovered2, _st2, _fu2, _fl2, fatal2 = _auth_wait_and_recover()
                    if not recovered2:
                        return _write(fatal2)
                    try:
                        final_url, files = _enumerate_once(folder_url)
                    except Exception:
                        return _write(_build_manifest('TIMEOUT', folder_url, []))
                    status = classify_status(final_url, files)
                if status == 'AUTH_REQUIRED':
                    log['auth_recovered_but_reexpired'] = True

        # 全体タイムアウト超過チェック（EMPTY のときだけ TIMEOUT に格上げはしない:
        # EMPTY は 0 件成功であり障害ではない。明示の例外/到達不能のみ TIMEOUT）
        if time.time() > deadline and not files and status not in ('OK', 'AUTH_REQUIRED'):
            # ナビゲート/列挙が安定せず時間切れ
            return _write(_build_manifest('TIMEOUT', folder_url, files))

        return _write(_build_manifest(status, final_url, files))

    finally:
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass


# === CLI ===

def cmd_list_folder(args) -> dict:
    """list-folder サブコマンド本体（preview.py からも同じ enumerate_videos を使う）。"""
    exts = tuple(e.strip().lower() for e in args.exts.split(',') if e.strip())
    out = args.out or str(HERE.parent.parent / "preview_capture" / "folder_manifest.json")
    out = os.path.abspath(out)
    rule = load_rule(args.rule, use_fallback=args.use_fallback)
    res = enumerate_videos(
        args.folder_url, out_json=out, exts=exts, rule=rule,
        recursive=args.recursive, auth_wait_s=args.auth_wait, timeout_s=args.timeout)
    return res


def main(argv: list | None = None) -> int:
    """単体 CLI 兼テスト用エントリ（非純粋）。status→終了コードを返す。

    OK=0, AUTH_REQUIRED=2, CDP_DOWN=3, TIMEOUT=4, EMPTY=5。stdout は ASCII のみ。
    """
    p = argparse.ArgumentParser(prog="sharepoint_folder.py")
    sp = p.add_subparsers(dest='cmd', required=True)

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

    args = p.parse_args(argv)

    if args.cmd != 'list-folder':
        p.error(f"unknown command: {args.cmd}")
        return 1

    res = cmd_list_folder(args)
    status = res.get('status')
    out = os.path.abspath(
        args.out or str(HERE.parent.parent / "preview_capture" / "folder_manifest.json"))

    if status == 'OK':
        g = res['groups']
        trunc = bool(res.get('log', {}).get('truncated'))
        # 打ち切り（仮想化リスト末尾未到達で MAX_ROUNDS 到達）は明示する。
        # 部分列挙を完全な成功と誤認させない（取りこぼし防止）。
        tag = "OK_TRUNCATED" if trunc else "OK"
        print(f"STATUS={tag} count={res['count']} lectures={len(g['lectures'])} "
              f"unmatched={len(g['unmatched'])} truncated={str(trunc).lower()} json={out}")
        return 0
    if status == 'EMPTY':
        print(f"STATUS=EMPTY count=0 json={out}")
        return 5
    if status == 'AUTH_REQUIRED':
        print(f"STATUS=AUTH_REQUIRED please sign in on the opened Chrome window "
              f"then re-run json={out}")
        return 2
    if status == 'CDP_DOWN':
        print("STATUS=CDP_DOWN start chrome failed (port 9222)")
        return 3
    if status == 'TIMEOUT':
        print(f"STATUS=TIMEOUT folder did not stabilize within {args.timeout}s json={out}")
        return 4
    # 未知 status は保守的に非0
    print(f"STATUS={status} json={out}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
