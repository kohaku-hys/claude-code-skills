# localhost:5050 スライド生成ツール 改修ログ

対象: ppt-master の `svg_editor`（ライブプレビュー）/ `confirm_ui`（八つの確認）サーバと、
slide-gen の起動ランチャー（live.ps1 / confirm.ps1 / stop.ps1）。

> ppt-master 側の修正（server_common・svg_editor・confirm_ui）は、作者が ppt-master のローカルのブランチに入れた物で、上流の ppt-master には入っていない（2026-10 時点）。slide-gen にも同梱していない（同梱したのは作者が新しく書いた deck_doctor.py と build.py だけ）。上流の版では、ここに書いた不具合が残っている場合がある。

---

## 2026-06-30 複数デッキ対応（A方式：別ポートで同時に開く）＋ポート解放

### 背景（本人の報告）
「スライドを複数作ると、5050が開いているのに保管（保存/確定）できない」「作り終わったらポートはなくしたい」。

### 根本原因（実地検証で確定）
1. **find_free_port が Windows で機能していなかった（キーストーン）**
   `server_common.find_free_port` はプローブ socket に `SO_REUSEADDR` を立てて bind 成功で「空き」と判定していた。
   Windows の `SO_REUSEADDR` は「使用中ポートへの bind を許可（共有/横取り）」の意味なので、
   稼働中の5050に対してもプローブが必ず成功 → **常に5050を返し、ポートが前進しない**。
   結果、2つ目のサーバも5050に相乗りし、ブラウザで5050を開くとどちらのデッキに当たるか不定 → 「保管できない/ズレる」。
   さらに **片方への `/api/shutdown` がもう片方に誤配送**され、別デッキのサーバを巻き込んで落とす事故も起きうる
   （実際、検証中に別のデッキのライブプレビューを巻き込み停止＝on-diskファイルは無事）。
2. **confirm_ui の非デーモン経路が find_free_port を呼んでいなかった**
   `app.run(port=args.port)` で5050を直バインド → 5050占有時は `Address already in use` で即クラッシュ（最小化ウィンドウで気づけない）。
3. **ランチャーが実ポートを見ず常に "http://localhost:5050" を表示/クリップボード**。
4. **.ps1 が UTF-8(BOMなし)** で、Windows PowerShell 5.1 が cp932 として誤読 → 日本語でパースエラー（潜在）。

### 修正
- `server_common.py` `find_free_port`: **connect 方式に変更**。実際に listen しているかを `connect_ex` で確認し、
  使用中なら次ポートへ。TIME_WAIT のポートは「空き」扱いになるので、閉じた直後でも5050を再利用できる。クロスプラットフォーム。
- `confirm_ui/server.py` 非デーモン経路: `find_free_port` を追加し、実ポートで bind / lock 記録 / URL 表示。
- `live.ps1` / `confirm.ps1`: 起動後に lock（`live_preview/lock.json` / `.confirm_ui.lock`）から**実ポートを読み取り**、
  表示・クリップボード・案内をそれに合わせる。`--no-browser` を渡し外部ブラウザの自動起動を抑止（VSCodeで開く既定に合わせる）。
  末尾に stop.ps1 の案内を追加。BOM付き UTF-8 で保存。
- `stop.ps1`（新規）: 指定プロジェクトの live preview と confirm の両サーバを停止しポート解放（冪等・死んだロック掃除）。

### 検証
- 回帰テスト `_audit_test/test_multideck.py`: **10/10 合格**
  （2デッキが5050/5051に分離・両方200・lock pid一致・片方shutdownが他方に影響なし・孤児なし）。
- ランチャーE2E: 1つ目=5050、2つ目=5051（「使用中のため5051で起動」表示）、クリップボード=実URL、stop.ps1で解放を確認。

### 使い方（複数デッキ）
1. 各デッキで `confirm.ps1`/`live.ps1` を起動 → 表示/クリップボードの**実URL**で開く（5050, 5051, …）。
2. `Ctrl+Alt+B` は5050固定。2つ目以降は `Ctrl+Shift+P → Simple Browser: Show → クリップボード貼り付け`。
3. 作り終わったデッキは `stop.ps1 -Project <proj>` で閉じる → ポートが空き、次は5050に戻る。

### バックアップ
編集前のツール一式は作者の環境に退避した（公開版には含まれない）。

---

## 監査（多エージェント網羅レビュー・敵対的検証つき）で見つかった追加課題と対応

63件（確定52・可能性11）。全件の一覧（`AUDIT_5050_findings.md`）は作者の環境にあり、公開版には含まれない。以下は適用済みの修正。

### バックエンド（Python・全て構文OK＆回帰テスト合格）

- **#13/#14 save-all のデータ損失（svg_editor）**: 1ファイルでも編集適用に失敗すると全体を中断、かつ最後に状態を一括クリアしていたため、他デッキの未保存編集まで消える恐れ。→ **原子書き込み（temp→os.replace）＋成功したファイルのみ状態クリア＋スナップショット方式**に変更。失敗ファイルは状態を保持し再保存可能、`errors` も返す。
- **#15 並行安全性（svg_editor）**: 注釈/編集/2sポーリング/save が threaded サーバで競合し dict 破壊・編集消失の恐れ。→ `STATE_LOCK` を導入し、ANNOTATIONS/PENDING_EDITS の read-modify-write を短時間ロックで保護（I/O中はロックしない）。
- **#05 shutdown 誤配送 / #11 PID再利用（両サーバ）**: lock のポートに無条件で `/api/shutdown` を投げ、別プロジェクトのサーバを巻き込んで落とす事故（実際に発生）。PID再利用で無関係プロセスを kill する恐れ。→ `/api/config` に project を持たせ、**身元一致を確認してからのみ停止**。不一致なら触れずに stale lock だけ掃除。確信できない PID は hard-kill しない。`force_release_lock` で他pid所有の stale lock も掃除。
- **#06 result.json 非原子書き込み（confirm_ui）**: 中断/同期ロックで破損の恐れ。→ 原子書き込み（temp→os.replace）。
- **#16 CSRF/Origin 未検査（両サーバ）**: 別サイトのページからローカルツールを操作されうる。→ 状態変更系 POST/DELETE で Origin がクロスサイトなら 403（非ブラウザの no-Origin は許可）。
- **#26 検証の過剰拒否（svg_editor）**: `data:` 部分一致で正当値も拒否。→ スキーム先頭一致に精緻化。
- **#44 パストラバーサル判定（svg_editor）**: `startswith` でセパレータ無し判定 → 兄弟ディレクトリ誤通過。→ `relative_to` に。
- **#45 mtime キャッシュ（svg_editor）**: OneDrive 同 mtime 別内容で stale キャッシュ。→ キャッシュキーに size 追加。
- **#12 lock 原子書き込み / #39 span枯渇ログ（server_common）**: OneDrive 競合で半端な lock を防ぐ原子書き込み、空きポート枯渇時の警告。
- **#43 xlink 名前空間（annotations）**: save 時に ElementTree が `xlink:href`→`ns1:href` に書き換え画像参照破壊。→ xlink を登録。

### 回帰テスト（`_audit_test/`、全合格）
- `test_multideck.py` 10/10、`test_confirm_coexist.py` 6/6、`test_backend_extra.py` 9/9（save-all原子性・状態クリア・shutdown身元クロスキル防止）。

### フロントエンド（svg_editor / confirm_ui の static）
- **#03 critical 修正済み**: `svg_editor/static/app.js` の `markSelection()` が未定義で、テキスト行の移動（tspan→text昇格）が毎回 ReferenceError で失敗していた。選択モデル（`svg-selected` クラス再同期＋パネル更新）に合わせて関数を定義。
- **日本語ロケール追加（#30, 両UI）**: MESSAGES に `ja` を全キー追加し既定を日本語に（navigator.language / localStorage を考慮）。言語トグルは ja→en→zh の3状態に。英語UIで迷う問題を解消。
- **confirm_ui の状態・フロー修正**: #07 tier2 派生ポーリングが永久スタックする経路に復帰UI、#08 役割別HEX上書きが再描画で消える問題を STATE 永続化、#09 確定時に未保存編集の警告、#21 HEX入力の検証。
- **アクセシビリティ（#17/#31/#32, svg_editor）**: スライド一覧・重なり選択メニュー・各操作に role/aria/キーボード操作（Enter/Space/矢印/Esc）を付与。
- **堅牢化（svg_editor app.js）**: 複数要素注釈の部分失敗を `Promise.allSettled` で個別反映（#29）、編集POSTのnullスライドガード（#47）、未送信編集中のページ離脱警告（#49）、エラー/警告バナーの重複抑止＋`role=alert`（#51/#55）、クイックアクション接頭辞の二重付与防止（#54）、spec-banner の表示位置（#50）。
- **体裁（#22/#36/#60, confirm_ui）**: 無効ボタンのコントラスト改善、ハードコード英語テキストの是正、保存ボタンのラベル。
- 検証: 両 app.js を `node --check` 合格、実サーバ配信スモーク 13/13 合格（静的配信・API・ja反映・/api/config project）。
- **視覚確認のお願い**: フロントのUX/i18n/a11y変更はブラウザ実機での見た目確認を推奨（自動検証は構文・配信レベルまで）。

### フロントの recommend-only（リスク回避でスキップ・後日適用候補）
- #28 loadSlides の2s毎フルDOM再構築 → data-name で差分更新に（フォーカス/リスナー保全）。
- #53 色/長さ入力が change のみ → blur/デバウンスでも staging。
- #52 サーバが5051へ移動した時のタブ側検知 → /api/config の project を画面に表示（バックエンドは対応済み、フロント表示のみ未）。
- #57 三分割の固定幅でキャンバスが潰れる狭幅対応、#48 行列変形警告の出し方。

### 残課題（recommend-only・未適用）
- Ctrl+Alt+B キーバインドは 5050 固定（複数デッキの2つ目以降はクリップボードURLで開く運用で回避）。
- daemon 二重起動レース（#20/#46）、ログの無制限肥大（#62）等は影響軽微のため記録のみ。
