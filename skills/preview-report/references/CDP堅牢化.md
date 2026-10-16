# preview-report CDP設計・堅牢化・ライブラリレシピ（Executor 段階で参照）

## Chrome 起動フラグ（全て必須）
```
--remote-debugging-port=9222
--remote-allow-origins=*                    # 110+ で WebSocket 403 回避
--autoplay-policy=no-user-gesture-required  # 背景タブの play() 拒否回避
--user-data-dir=<非default>                  # default では CDP 拒否される
# 完全バックグラウンド（画面を奪わない）— chrome_cdp.py に設定済み
--disable-renderer-backgrounding
--disable-backgrounding-occluded-windows
--disable-background-timer-throttling
--disable-features=CalculateNativeWinOcclusion
```

## 🎥 実板書キャプチャの堅牢化（2026-06 決定版 — 取りこぼし/取り違え防止）

- **タイトルが明確でも動画を見る。** ユーザーは実板書解析を強く望む。Quickモードで済ませない（指摘済み）。
- **完全バックグラウンド:** スロットリング無効フラグ前提で `cdp_seek.split_and_capture(bring_to_front=False)`。`bringToFront` は使わない。captureScreenshot はレンダラから取るので VS Code 表示中でも内容は汚れない。
- **取り違え防止（必須）:** タブ開閉のレースで別動画を保存する事故が起きる。`split_and_capture(expect_title="_NN_M_")` で `document.title` を照合してから撮る。撮る前にフォルダを空にする。解析Agentにも「各フレームのプレイヤータイトル番号を照合し混入除外」と必ず指示。
- **WSタイムアウト連鎖対策:** 連続開閉で `WebSocketTimeoutException` 多発 → **BATCH(3)本ごとに Chrome を再起動**＋**動画ごとに最大3-4回リトライ**。
- **メタ未ロード対策:** `cdp_seek.wait_video_ready(ws)` で duration 確定を待ってから撮る（None クラッシュ回避）。
- **再利用モジュール:** `scripts/capture_folder.py`（enumerate→restart/retry/title-verify/folder-clear/裏キャプチャ）。CLI: `python scripts/capture_folder.py "<folderURL>" [--only 05_1,09_1]`。stream再生URLは folder id パス＋ファイル名から構築。
- **⚠️ 判読不可は留保で逃げない（必須ルール）:** 10分割の固定点で隠れた箇所は、**時刻をずらして追加キャプチャして読み切る**。`cdp_seek.capture_at_times(tab, [秒…], out_dir, expect_title="_NN_M_")` で任意秒を撮れる。最終解・公式・例題の答えが隠れていたらその時刻周辺を数秒刻みで密にサンプリングし、実物を読んでからレポートを完成させる。録画自体に無い場合のみ留保。
- **🧠 適応追撮（自動・固定分割の谷間対策 / crv の頭脳移植）:** 固定10分割は、区間の中で板書がまるごと入れ替わる短命な状態（例: 100-130s だけ映る式）を丸ごと取りこぼす。`cdp_seek.split_and_capture_adaptive(tab, base_splits=10, out_dir, max_frames=40, expect_title="_NN_M_")` は、まず粗グリッドを撮り、**隣接フレームのピクセル差分（16x16 RGB, dedup.pct_diff）が大きい谷間から順に中点を自動追撮**する。板書が動いた所へキャプチャを集中させ、静止区間には無駄打ちしない。`capture_folder.py --adaptive [--max-frames 40]` で一括モードからも使える。CDP は1枚2秒級なので `max_frames` が予算の上限（既定40）。タイトルが opaque で板書更新が速い回や、固定分割で式が読めなかった回に使う。
- **♻️ 重複間引き dedup（任意・後処理）:** 撮り終えたフレーム群から静止区間の重複を落として解析Agentの注意を分散させない。`dedup.dedup_dir(out_dir)` または `python scripts/dedup.py <out_dir>`。重複は削除せず `out_dir/_dup/` へ退避（非破壊・元に戻せる）。ファイル名の秒数（`at00123s.png`）で時刻順を保つためリネームはしない。`capture_folder.py --dedup` でキャプチャ直後に自動実行。PIL 不在環境では黙って全フレーム素通し（安全側）。
- **⚠️ 日本語パスはシェルで化ける:** `python -c` や Bash/PowerShell に日本語パスを引数で渡すと文字化けする。**Write tool で .py に日本語パスを書いて実行**し、結果も UTF-8 ファイルに書いて Read で読む。出力先は `os.walk` で発見して使う（授業フォルダ名はリネームされ得る）。

## seek の手順（poster 問題対策）
```python
# NG: currentTime だけ → poster のまま
video.currentTime = 600
# OK: play → seek → seeked 待ち → pause → captureScreenshot
video.play(); video.currentTime = 600
# await seeked event
video.pause()
```

## 複数タブ処理
- スロットリング無効フラグ前提では `bring_to_front=False` で裏のまま捕捉できる。`Page.bringToFront` は前面化が避けられない場合の fallback のみ。
- タブ毎に新しい WebSocket 接続を作る（使い回さない）。

## 認証
- 初回のみ MS ログイン（10秒）。`chrome_cdp_profile` に cookie 保存。2回目以降は自動。

## ライブラリ呼び出しレシピ

### omml_lib（数式）
```python
from omml_lib import m_det, m_r, m_ri, m_sub, m_sup, m_frac, m_sum, m_int, \
                     m_matrix, m_transpose, m_inverse, m_generic_matrix, \
                     add_math, setup_japanese, heading, safe_save_path

add_math(doc, m_det([[m_ri('a'), m_ri('b')], [m_ri('c'), m_ri('d')]]))   # 行列式
add_math(doc, m_det(m_generic_matrix(3, 3, 'a')))                        # 一般 3x3
add_math(doc, m_frac(m_r('1'), m_ri('ad') + m_r(' − ') + m_ri('bc')))    # 分数
add_math(doc, m_transpose(m_ri('A')))                                    # 転置
add_math(doc, m_sum(m_ri('i') + m_r('=1'), m_ri('n'), m_sub(m_ri('a'), m_ri('i'))))  # Σ
```

### 検証済み 微分方程式(DE)レシピ（昇格済み・そのまま使える）
```python
# dy/dx        = m_frac(m_r('d')+m_ri('y'), m_r('d')+m_ri('x'))
# d²y/dx²      = m_frac(m_sup(m_r('d'),m_r('2'))+m_ri('y'), m_r('d')+m_sup(m_ri('x'),m_r('2')))
# y′ y″        = m_ri('y')+m_r('′')  /  m_r('″')
# e^{∫P dx}    = m_sup(m_r('e'), m_int('','', m_ri('P')+m_r('(')+m_ri('x')+m_r(') d')+m_ri('x')))  # 不定積分は上下端を空文字
# 特性方程式    = m_sup(m_ri('λ'),m_r('2'))+m_r(' + ')+m_ri('a')+m_ri('λ')+...
# 複素根解      = m_sup(m_r('e'),m_ri('α')+m_ri('x'))+m_r('(')+m_sub(m_ri('C'),m_r('1'))+m_r(' cos ')+...
# べき級数      = m_sum(m_ri('n')+m_r('=0'), m_r('∞'), m_sub(m_ri('a'),m_ri('n'))+m_sup(m_ri('x'),m_ri('n')))
```

### chrome_cdp（ブラウザ）
```python
import chrome_cdp
chrome_cdp.is_cdp_alive()              # → True/False
chrome_cdp.start_chrome([url1, url2])  # 起動or再利用。認証済みなら即使える
chrome_cdp.wait_video_tabs(3)          # stream.aspx タブが N 個揃うまで待機
```

### cdp_seek（動画操作）
```python
from cdp_seek import (get_video_tabs, seek_and_capture, split_and_capture,
                      capture_at_times, split_and_capture_adaptive)
tabs = get_video_tabs()
seek_and_capture(tabs[0], 600, "out.png")           # 10分位置を1枚
split_and_capture(tabs[0], 10, "out_dir/")          # 10分割×1動画（既定・軽い）
capture_at_times(tabs[0], [615, 618, 621], "d/")    # 判読不可を手で追撮
# 板書が変わった谷間を自動追撮（固定分割の取りこぼし対策）:
split_and_capture_adaptive(tabs[0], 10, "d/", max_frames=40, expect_title="_05_1_")
```

### dedup（フレーム間引き・crv ピクセル差分）
```python
import dedup
res = dedup.dedup_dir("out_dir/")            # 重複を out_dir/_dup/ へ退避（非破壊）
# res = {"kept":[...], "dropped":[...], "records":[...], "pil":True}
d = dedup.pct_diff(dedup.frame_sig("a.png"), dedup.frame_sig("b.png"))  # 変化率%
# スケジューラ単体（CDP不要・テスト可）: cdp_seek.plan_adaptive_captures(...)
```

## デバッグ・トラブルシュート

| 症状 | 原因 | 対処 |
|------|------|------|
| Handshake 403 Forbidden | `--remote-allow-origins=*` なし | Chrome 再起動 |
| CDP 拒否（non-default data directory 要求） | default プロファイル使用 | `--user-data-dir=<temp>` |
| poster のまま撮れる | currentTime 直接設定 | play→seek→pause の順に |
| 背景タブで捕捉失敗 | bringToFront 未実行 | `Page.bringToFront` 呼び出し |
| 2番目以降のタブで play() 拒否 | autoplay-policy 設定不足 | `--autoplay-policy=no-user-gesture-required` |
| 初回ログイン毎回 | プロファイル消された | `chrome_cdp_profile` を保持 |
