---
name: slide-gen
description: AIスライド生成 — ppt-master でネイティブ編集可能な .pptx（DrawingML図形＋テキスト＋スピーカーノート・1280×720）を生成する。confirm_ui（八つの確認）で戦略・体裁を確定してからSVGを1枚ずつ手書きし、チャート・アイコン・数式・CC0画像・ナレーション・PDF/動画書き出しまで対応。作ったデッキや本人の pptx に、軌跡・拡大/収縮・変形などの**動き（アニメーション）を後から付け、PowerPoint で同じ動きを自分で付ける手順も残す**（motion.py）。**呼び出しキーワード**：「スライド作って」「スライド生成」「プレゼン資料」「発表資料」「登壇資料」「パワポ作って」「パワーポイント」「PPT作成」「PPTX作って」「デッキ作って」「プレゼンテーション」「LT資料」「スライドにまとめて」「slide」「動きを付けて」「アニメーション付けて」「動くスライド」「手が動くスライド」「変形で動かして」「順番に出して」等。
argument-hint: "[スライドのテーマ・用途 or 素材ファイルパス]"
---

# AIスライド生成スキル（ppt-master 一軸）

> **▶ 実行開始時の共通4点セット**（詳細 → `~/.claude/skills/shared-doc-rules/SKILL.md` §8〜§10）
> 1. 📢 **公言**：応答冒頭で「slide-gen スキルを使っています」と必ず出力する（§10）
> 2. 🎯 **イシューからはじめよ**：STEP 1 でイシュー・キーメッセージ・ストーリーラインを固めてから作図に進む（§8）
> 3. 🚫 **AIっぽさ撲滅**：`references/デザイン品質.md` のレイヤーを全スライドに適用する（§9）
> 4. 📒 `~/.claude/skill-memory/slide-gen.md` を読み込み、過去の改善（特に「実地フィードバック総まとめ」）を反映する（無ければ飛ばす）

> **既に手元にある .pptx を部分的に直すだけ**なら、python-pptx で図形IDを指定して直す（作者の環境では別スキル `/slides` の担当。このリポジトリには含まれない）。こちらは新規生成が担当。

ユーザーが提供した素材・テキスト・トピックをもとに、**ネイティブ編集可能な .pptx** を生成する。

**フォルダ構成**: 補助スクリプト = `scripts/`（`$T`。build/deck_doctor（同梱）/preview/render_png/to_pdf/chart/wrap_ja/recommend/confirm/live/stop/motion/illust 等）／詳細ルール = `references/`（confirm_ui.md, 機能カタログ.md, デザイン品質.md, 動き.md, CHANGELOG_5050.md）

---

## 🟥 大原則（2026-06-30 確定）★最優先

- **スライド生成は必ず ppt-master を軸に動かす**（編集可能PPTX・1280×720）。指定がなくてもこれが既定。新規作成も修正もすべて ppt-master（外部 OSS。https://github.com/hugohe3/ppt-master を別に入れる → 下の「🟦 ppt-master 本体・依存」）。
- 🟥🟥 **序盤は必ず localhost の confirm_ui（八つの確認）で確定してから作る＝絶対に飛ばさない（BLOCKING）**。手順：`recommend.py` → `confirm.ps1`（http://localhost:5050）→ ユーザーが確定 → `result.json` を spec_lock に反映 → **そこで初めて SVG を書く**。spec_lock 確定前に SVG を1行でも書いたら違反。詳細 → `references/confirm_ui.md`
- **並列生成OK（spec_lock 確定後）**：独立レイアウトのページは**並列**で作ってよい（各ページは spec_lock のみ参照→最後に一貫性レビュー一巡）。※データからの一括スクリプト生成は不可（鉄則#9）。
- **ppt-master の機能を9割使う**：素のテキスト貼り付けで終わらせず、Strategist → Executor → アイコン/チャート/数式/CC0画像/ナレーション/動画/アニメ/テンプレ継承まで活用 → `references/機能カタログ.md`
- **写真は必要に応じて Web から取る**（2026-10-02 本人指示「webの画像を用いたりするようにしてください必要に応じて」）：本人の素材に写真が無くても、題材が場所・物・人・出来事（観光地・製品・施設・イベント等）なら、`$SK/image_search.py "英語query" -o <proj>/images` で CC0/CC の写真を探し、コンタクトシートで目視して選ぶ。「素材に写真が無いから画像なし」で終わらせない。画像なしにしてよいのは、題材が手順・規則・数式のように写真が証拠にも説明にもならない時だけで、その時は design_spec に理由を1行書く。使った写真は出典とライセンスを `image_sources.json` に残し、CC BY 系はスライドにクレジット、実物でない写真は「イメージ」と書く。Web の写真を証拠にする時は inventory の Ph に出典 URL とライセンス付きで載せる（proof の kind は photo、src は画像のファイル名）。
- **旧 HTML→画像PPTX（スクショ貼り）経路は廃止**。**python-pptx の直接編集は使わない**（ppt-master が内部で使うので土台として残すが、こちらから直接は呼ばない）。**例外は動きを付ける工程だけ**：`$T/motion.py` が書き出し後の pptx に動き（`p:timing`）と画面切り替えを足す。ppt-master の pptx_animations に軌跡・強調・変形が無いため（2026-10-13 本人の選択「/slide-gen に足す」）。文字・図形・配置は今までどおり SVG で直す。
- **PDF化**：PowerPoint COM で各スライド PNG 書き出し → Pillow で結合。Word COM の PDF 書き出しは、裏に残った WINWORD.EXE があると固まることがあるので使わない。
- ppt-master は git で clone して使う（置き場の例: `C:\dev\ppt-master`）。手元で直した分はローカルのブランチにコミットしてよい。push は本人確認の後だけ。
- 生成物の置き場所は毎回確認する。

## 🟥🟥 STEP 0 環境ゲート（Preflight）★init 前に必ず通す（2026-07-06 実地で大量手戻り→恒久化）

ppt-master に触る前に、この4点を**先に**確定する。1つでも飛ばすと今回のように何十分も溶かす。

1. **Python は 3.10+ の実体で呼ぶ（`py`＝3.9 では即クラッシュ）**。ppt-master は `list[str] | None` 等を import 時に評価するため 3.9 で `TypeError` 即死。**必ず preflight でインタプリタを解決する**：
   ```
   PYPPT=$(py -3 "$T/ppt_env.py" | sed -n 's/^PYPPT=//p')   # 使うべき 3.10+ python の絶対パス
   ```
   以後 ppt-master の全スクリプト（project_manager / svg_quality_checker …）と、同梱の `$T/build.py`・`$T/deck_doctor.py` は **`"$PYPPT" <script>`** で呼ぶ。`$PYPPT` が空なら 3.12 未導入＝ppt_env.py の stderr の手順で入れる（Windows の例: `%LOCALAPPDATA%\Programs\Python\Python312\python.exe`）。**`winget install ... --scope user --silent` でも py ランチャーで UAC が出て固まる**ので、winget が落とした installer を `/quiet InstallAllUsers=0 Include_launcher=0 PrependPath=1` で直接実行する（Windows の場合）。
2. **チャート/画像は `svg_output/images/` に置く**。quality_checker は `<image href>` を**SVGファイルの場所を基準に解決**する（`svg_output/xx.svg` の `href="images/c1.png"` → `svg_output/images/c1.png`）。project直下の `images/` だけだと `Image file not found` の **ERROR でビルドが止まる**。両方に置くのが確実。
3. **spec_lock.md の色は「セクション名が厳密に `## colors`」＋「値は純 `#HEX` のみ」**。checker は `lock['colors']` を引き（`## colors（...）`のように括弧付きだと section 名不一致で**空**＝全色 drift）、値は **`HEX_VALUE_RE.fullmatch`**＝末尾に説明文が1文字でも付くと不採用（`- navy: #16305C 見出し` はダメ）。空白区切り（`- navy  #16305C`）もコロン無しで拾われない。**使う色は全部**ここに宣言する（未宣言は drift）。正しい形：
   ```
   ## colors
   - navy: #16305C
   - blue: #2F6BFF
   - ink: #1A2233
   ```
   （name は半角英数と `_` のみ。説明を書きたいなら別途コメント行に。この形で `[OK] spec_lock drift: none / Fully passed 100%` を 12/12 で実証済み。font-family / font-size も同様に厳密節。）
4. **プレビューは PowerShell を使わない**。`preview.ps1` / `render_png.ps1` は `powershell -ExecutionPolicy Bypass` を使い、**auto-mode 分類器が Security Weaken として拒否**する（実際に拒否された）。代わりに **`$T/render_deck.py`（pywin32のみ）** を使う：
   ```
   py -3 "$T/render_deck.py" "<deck.pptx>"      # → 最終行 CONTACT_SHEET=... を Read してセルフレビュー
   ```
   （PDFも PowerShell 版がハングするなら pywin32 の Export で代替。）

> ⚠️ 上の1〜4は「confirm_ui を飛ばさない」と同格の**機械的ゲート**。着手前に `ppt_env.py` を1回叩き、`$PYPPT` を握ってから init する。

## 🟦 ppt-master 本体・依存

- **本体**：https://github.com/hugohe3/ppt-master を clone した中の `skills/ppt-master/`。このファイルでは置き場の例を `C:/dev/ppt-master/skills/ppt-master/` とする（自分の置き場に読み替える。同梱の build.py とサーバの試験は、環境変数 `PPT_MASTER_SCRIPTS` で ppt-master の scripts の場所を変えられる）。`$SK = <それ>/scripts`、`$REF = <それ>/references`。**呼ぶときは `"$PYPPT" "$SK/xxx.py"`（STEP 0 で解決した 3.10+ 実体）**。
- **依存（ppt-master 側で入れる）**：python-pptx, svglib, reportlab, Pillow, numpy, edge-tts, PyMuPDF, mammoth, openpyxl, beautifulsoup4, requests, curl_cffi, google-genai, flask, python-docx。
- **同梱した検査の段**：`deck_doctor.py`（第2ゲート）と `build.py`（一発ビルド）は、作者が ppt-master のローカルのブランチに書き足した物を slide-gen の `scripts/`（`$T`）に同梱した。上流の ppt-master だけで、build（quality→deck_doctor→split→finalize→pptx）と brief.py・claims.py まで動く。build.py は deck_doctor を同梱版から、ほかの4段を `PPT_MASTER_SCRIPTS` の ppt-master から呼ぶ。
- **上流の ppt-master の新しい決まり（2026-10 時点）**：spec_lock の書式が新しくなっている（`<!-- ppt-master-schema: spec-lock/v1 -->`・`## canvas` の viewBox・`## typography` の title/body など。上流の `templates/spec_lock_reference.md` に従う）。STEP 0 の3（`## colors` の書き方）は作者の版で確かめた書き方として読む。svg_to_pptx は最終の品質レポートを求めるので、同梱の build.py は上流の checker なら `--canonical-authoring --stage final --json` を付けて呼ぶ（作者の版ではオプション無しで呼ぶ）。2026-10-16 に、上流の ppt-master（origin/main）と作者の版の両方で、build の5段が通り pptx ができることを試した。
- **⚠ 作者の改造版の ppt-master でだけ動く物**（上流のファイルへの手直しは同梱していない。2026-10-05 時点の上流で確認）：
  - **SVG の id を PowerPoint の図形の名前にする処理**（svg_to_pptx）：上流では図形の名前が付かない（Group 12 のような、作るたびに変わる名前になる）。motion.py で動きを付ける時は、書き出した後に `motion.py list` で名前を見て `#ID` か `text:文字` で指すか、PowerPoint の［ホーム］→［選択］→［オブジェクトの選択と表示］で手で名前を付ける。
  - **仮名とハングルを CJK として和文の書体を当てる処理**（svg_to_pptx）：上流ではかなの書体が欧文の書体になることがある。書き出した後に PowerPoint で書体を確かめる。
  - **confirm_ui・svg_editor の修正**（2つのデッキを同時に開いた時に別ポートに分ける・別のデッキのサーバを誤って止めない・保存の原子性・日本語の画面。`references/CHANGELOG_5050.md`）：上流ではデッキを1つずつ開き、終わったら `stop.ps1` で閉じる。サーバの試験3本（test_multideck・test_confirm_coexist・test_backend_extra）は、上流の版では SKIP になる。
- **プロジェクトはASCIIパスで作る**（生成物pptxは最後に用途別のフォルダへ）。
- 参考実装（作者の環境専用・無ければ飛ばす）：`~/_pptmaster_demos/`（showcaseデッキ＋`GALLERY.md`）。

## 🟩 正規ワークフロー

```
Source取込 → init → Strategist（design_spec＋spec_lock＋confirm_ui 八つの確認）
  → 画像取得 → Executor（svg_editor ライブプレビュー／spec_lock毎ページ再読／1枚ずつ手書き）
  → quality_check → finalize → svg_to_pptx → export → （任意）ナレーション/動画/PDF
```

### 実行規律（ppt-master 本体 SKILL.md の10ルール要約・厳守）
1. **直列実行**：各ステップの出力が次の入力。前提を満たせば連続実行可。
2. **confirm_ui の八つの確認は BLOCKING**：必ずユーザーの明示確認を待つ。確認後の design_spec出力〜SVG生成〜ノート〜後処理は自動で進めてよい。
3. **GATE**：各ステップの前提を満たしてから着手。投機的先取り禁止。
4. **SVGは手書き**（一括スクリプト生成禁止＝鉄則#9）。spec_lock 確定後は独立ページの並列作成可。
5. **spec_lock を毎ページ再読**：色/フォント/アイコン/画像は spec_lock.md の値のみ。`page_rhythm`・`page_layouts`・`page_charts` も都度参照。
6. **ルート逸脱の質問を足さない**：確認ゲート以外で止めない。

### 手順とスクリプト
| 段階 | コマンド / 参照 | 要点 |
|---|---|---|
| Source取込 | `scripts/source_to_md/{pdf,doc,excel,ppt,web}_to_md.py <file>` | docx/講義PDF/Web/Excel/既存PPTXを素材化 |
| init | `$SK/project_manager.py init <name> --format ppt169 --dir <ASCIIdir>` | svg_output/ notes/ images/ exports/ を生成 |
| Strategist | `$REF/strategist.md`／`$SK/update_spec.py` | **design_spec.md＋spec_lock.md** を作る |
| 八つの確認 | `$SK/confirm_ui/server.py <project>`（BLOCKING） | → `references/confirm_ui.md`（日本語ガイド・推奨表） |
| 画像取得 | `$SK/image_search.py "英語query" -o <proj>/images` | CC0/CCライセンス自動記録。候補はコンタクトシートで目視選定 |
| Executor | `$SK/svg_editor/server.py <project> --live`／`$REF/executor-base.md` | **書く前に `references/デザイン品質.md` を必ず読む**。1枚ずつ手書き |
| quality_check | `$SK/svg_quality_checker.py <project>` | **error 0 必須**（warnは可）。spec_lock drift も検出 |
| deck_doctor | `$T/deck_doctor.py <project>`（同梱） | **第2ゲート（error 0 必須）**：注釈残留・フッター番号・ノート割当・禁則/数字割れ・はみ出し/文字かぶり推定・dy大見出し。**話す型検査**（delivery を書かなければ ON・`delivery: document`/`balanced` で OFF、`--talk`/`--no-talk`）＝文字数過多・小さい文字・行数・読む場所の数・視覚アンカー不在・画像が小さい・大見出し不在。`--json`/`--strict`。**中身の検査 C1〜C6・R0・R1、意味の検査 M1〜、形の検査 F1〜F8・Q1・Q2、目次 A0〜A3、資料の種類 G1〜G9 は表の下** |
| **build（一発）** | `$T/build.py <project>`（同梱） | ★quality→doctor→split→finalize→pptx を**ゲート付きで直列一括**。軽微修正後は `--rebuild`（finalize省略）。`-- -t push` 等は svg_to_pptx へ素通し |
| split notes | `$SK/total_md_split.py <project>` | notes/total.md「## Slide N:」をページ単位へ |
| finalize | `$SK/finalize_svg.py <project>` | アイコン/画像埋込・tspan平坦化 |
| export | `$SK/svg_to_pptx.py <project>` | → exports/*.pptx（ネイティブ編集可能） |
| ライブ注釈反映 | `$SK/check_annotations.py <project>` | ユーザーのクリック注釈→反映→再ビルド（複数ラウンド前提） |

deck_doctor の検査は**中身が先、形が後**の順で走り、結果もその順に出る（形だけ直しても中身の問題は消えないため）。
- **中身の検査（2026-09-28〜）**：C1 証拠の台帳 `brief.json`(v2) と必須8欄／C2 P・各 R・各 E の枚に証拠が割り当たっているか（P の強い証拠2件以上）／C3 引用が出典の行（前後2行）に本当にあるか・逐語の偽装・推測や起草の行の使用／C4 素材を全部読んだ記録が実物の行数・逐語行の数と合うか／C5 選んだ証拠と本人の場面（me.scene）がスライドかノートに出ているか／C6 結論の核の語（p_core）が R・E の枚に出るか／**R0 slide-evidence-checker の PASS 記録があり、その後に中身が変わっていないか**（spec_lock の `evidence_check:` 行のハッシュ）／**R1 slide-reader（初見の読み手）の PASS 記録があり、その後に中身が変わっていないか**（`reader_check:` 行。2026-10-01〜）。
- **意味の検査 M1〜（2026-10-01 本人「今のスライド生成は結局何を言いたいのか伝わらない」・WARNING）**：スライドの文字だけで「誰が・何を・どうした」が読めるかの手がかり。M1 否定の前振り（短い否定文→短い肯定文）／M2 語を入れ替えた反復／M3 短い語の後の読点で溜める（「規則は、」「装置より、」）／M4 指す物が書いていない（片方・前者・見出しの頭の指示語）／M5 比喩の動詞・方向の比喩（〜側に倒す・犯人を絞る）／M6 名詞化で止めた見出し（〜化・〜性・〜の向上）／M7 前置きの決まり文句（重要なのは・結論から言うと）／M8 絵文字／M9 行の終わりのコロンで中身を次の行に回す／M10 ダッシュで文を区切る／M11 読点の打ちすぎ。言い回しの一部は nanaism/yomiyasu（MIT）の一覧を直して入れた。比喩は「抽象的な物が主語か目的語の時だけ」拾い、人・物・薬・建物の文字どおりの文は拾わない。**落とし込む・架け橋・刺さる は INFO だけ**（2026-10-01 本人の判断「① 参考の扱い」＝本人が自分の文で使う語）。作者の環境では、文章用の AIくささ検査スクリプト・レポート（report スキルの check_ai_likeness）と同じ判定に揃え、3つで共通の試験集（約790文）を test_deck_doctor.py が全件流している。文章用の検査スクリプトと試験集はこのリポジトリに含まれない（無ければ test_deck_doctor.py はその部分を SKIP と出して飛ばす）。考え方は `references/デザイン品質.md`「🟥 スライドの文字だけで意味が通る」。
- **形の検査**：F1 最初と最後の P の見出しがほぼ同じ文（ERROR）／F2「〜ではなく」「AよりB」「〜て初めて」式の対句（見出し・小ラベルで1回、本文で2回）／F3 片側だけの縦線（カード左端の色線・画面の端の全高の帯）／F4 P/R/E の85%以上が同じ入り方／F5 PREP の札（「結論」等）が小ラベルに出ている／F6 文字も写真も無い飾りの線画（`decor_ok:` 行で題材との関係を書けば INFO）／F7 R・E の枚に証拠の要素（数字・人の言葉・写真・出典付きの図表）が0（ERROR）／F8 R・E の枚がスライド＋ノートで200字未満。
- **引用の組み方 Q1・Q2**（WARNING）：Q1 複数行に割った「」の引用を中央揃えにしている／Q2 左揃えの複数行の引用で、2行目以降を1字下げていない（1行目で」が閉じ、2行目が出どころの行なら対象外）。
- **目次 A0〜A3**（本人の既定＝全デッキに目次）：A0 表紙・目次・謝辞を除いて4枚以上なのに目次(A)の枚が無い（ERROR。`agenda: none` を書けば INFO）。目次は表紙の直後が既定で、外れると順番の ERROR。本人が別の枚に決めた時（2026-10-16 本人「スライドも2枚目に変えて」＝表紙の次に前提のニュース、目次は3枚目）は spec_lock に `agenda: at <枚> <日付> 本人 <理由>` を書けば INFO（枚の番号が実物と合い、理由がある時だけ）／A1 項目が3〜5個の外（WARNING）／A2 項目が中身の無い見出し語「はじめに」「概要」「まとめ」等（ERROR）／A3 項目の語が後の P/R/E の枚に半分も出ない（WARNING）。
- **資料の種類 G1〜G9**（spec_lock の `- genre: xxx`。brief.py が書く。未記載は general）：G1 概要の事実（brief.overview）が表紙・目次・最初の P に出ているか／G2 R/E の枚にデータ（数＋単位）が1つも無い／G3a 人の言葉の行がある枚に出どころの ※ 行が無い／G3b 数字のある R/E の枚に ※・出典 の行が無い／G4a お願い（cta）が最後の P に無い・G4b 時期が無い・G4c 告知なのに窓口が無い／G5 目的（me.why）がどこにも無い／G7 表紙に報告日が無い／G8 説明の無い英略語（聞き手が知っている語は spec_lock に `terms_ok: PBL, LT`）／G9 研究の発表に参考文献の枚が無い（G6 は無い）。重さ（E=ERROR・W=WARNING・-=見ない）：

| genre | G1 | G2 | G3b | G4c | G5 | G7 | G9 |
|---|---|---|---|---|---|---|---|
| experience（研修・留学・出張の報告） | E | - | W | - | W | W | - |
| progress（進捗・中間） | E | W | W | - | - | W | - |
| proposal（提案・企画・申請・コンペ） | - | E | E | - | W | W | - |
| research（研究・実験・授業発表・調べ学習） | - | E | E | - | W | W | W |
| explainer（解説・勉強会・LT） | - | - | W | - | - | W | - |
| notice（告知） | - | - | W | W | - | - | - |
| general（未記載） | - | W | W | - | - | W | - |

  全部の genre で同じ物：G3a・G8 は W（G8 は日本語のデッキだけ）、G4a は E・G4b は W（G4 は brief に cta がある時だけ見る）。
- フラグ：`--draft`＝途中の確認用（R0・R1 を WARNING に下げる。本人に見せる版には付けない）／`--legacy`＝9/28 以前の旧書式 brief のデッキを作り直す時だけ（C1〜C6・R0・R1・A0・G1・G4a を WARNING に下げる）。build.py にも `--draft` を足して deck_doctor にそのまま渡す（**`build.py -h` に `--draft` が無い版なら**、途中確認だけ `"$PYPPT" "$T/deck_doctor.py" <proj> --draft` で ERROR 0 を確かめてから `build.py --skip-doctor`。本人に見せる版は必ず `--draft` なしの build を通す）。

## 🛠 同梱ツール（`~/.claude/skills/slide-gen/scripts/` ＝ `$T`）★毎回これを使う

| ツール | 用途 | 使い方 |
|---|---|---|
| `build.py` ★ | **一発ビルド（同梱）**：svg_quality_checker → deck_doctor → total_md_split → finalize_svg → svg_to_pptx をゲート付きで直列に流す | `"$PYPPT" "$T/build.py" <proj> [--rebuild] [--draft] [--strict]` |
| `deck_doctor.py` ★ | **第2ゲート（同梱）**：中身・意味・形・目次・資料の種類の検査（上の表の下に一覧）。brief.py・claims.py もここから判定の関数を借りる | `"$PYPPT" "$T/deck_doctor.py" <proj> [--json] [--draft]` |
| `ppt_env.py` ★ | **Preflight**：3.10+ 実体を解決し依存を確認（`$PYPPT`） | `py -3 "$T\ppt_env.py"` → 最終行 `PYPPT=<path>`。init 前に必ず |
| `render_deck.py` ★ | **pptx→PNG＋`_all.png`（pywin32のみ・PowerShell不使用）**。本人が PowerPoint を開いていたら閉じない（2026-10-13〜） | `py -3 "$T\render_deck.py" <x.pptx>` → 最終行 `CONTACT_SHEET=` を Read |
| `motion.py` ★ | **動きを足す**：軌跡・拡大/収縮・回転・出る/消える・自動で戻す・繰り返し・変形。ノート欄と `_動きの作り方.md` に PowerPoint での手順を残す。`verify` で動画→コマ送り | `py -3 "$T\motion.py" list|apply|verify …`（→ 下の「🎬 動きを付ける」） |
| `pptx_check.py` ★ | **できあがった pptx の関門**（2026-10-15〜）：情報量（読む場所・字数/語数・小さい字）・1枚1メッセージの手がかり（見出しのつなぎ・文の本数）・動きの予算を1枚ずつ見る。deck_doctor は SVG しか見ないので、**pptx を直接直した時（/slides）と motion.py の後は必ずこれ**。ERROR 0 で渡す | `py -3 "$T\pptx_check.py" <x.pptx> [--slides 6,7] [--draft]` |
| `illust.py` | いらすとやで絵を探して保存＋候補の一覧＋出典の記録 | `py -3 "$T\illust.py" "ばね" -o <proj>/images` → `_候補.png` を Read |
| `render_png.ps1` | pptx→各スライドPNG(COM)。※PowerShell経路＝分類器に拒否されうる→`render_deck.py`推奨 | `& "$T\render_png.ps1" -Pptx <x.pptx>` |
| `preview.ps1` | レンダリング＋`_all.png`。※`-ExecutionPolicy Bypass`が拒否される環境あり→`render_deck.py`推奨 | `& "$T\preview.ps1" -Pptx <x.pptx> [-Open]` |
| `montage.py` | PNG群→`_all.png`（番号順） | `py "$T\montage.py" <pngdir> [cols]` |
| `to_pdf.ps1` / `make_pdf.py` | pptx→PDF（COM PNG→Pillow結合） | `& "$T\to_pdf.ps1" -Pptx <x.pptx> -OutPdf <out.pdf>` |
| `color_audit.py` | 使用HEX色を集計（3色統一の確認） | `py "$T\color_audit.py" <svg_dir>` |
| `fix_footers.py` | 並べ替え後のフッター採番＋注釈除去 | `py "$T\fix_footers.py" <svg_dir>` |
| `wrap_ja.py` | 日本語を**文節境界で自然改行**（BudouX・禁則入り） | `py "$T\wrap_ja.py" "テキスト" --lines 2`／`--svg …` |
| `chart.py` | データ→3色統一・出典・比較付きSVG断片 | `py "$T\chart.py" data.json` → 手で配置（→ `references/機能カタログ.md`） |
| `recommend.py` / `confirm.ps1` / `live.ps1` / `stop.ps1` | confirm_ui の推奨生成・起動・ライブ編集・停止 | → `references/confirm_ui.md` |

⚠️ `render_png.ps1` は出力dirを毎回消して作り直す → `preview` と `to_pdf` を同じ既定dirで連続実行すると `_all.png` が消える。PDFも要るなら `-OutDir` を分けるか PDF を先に。

### ⚡ クイックスタート（雛形→実物まで一気通貫）
```
$SK = "<ppt-master>/scripts"; $T = "$env:USERPROFILE\.claude\skills\slide-gen\scripts"   # "~/" は py.exe が解釈しない
PYPPT=$(py -3 "$T/ppt_env.py" | sed -n 's/^PYPPT=//p')   # ★STEP0：3.10+ の実体を解決（py=3.9では動かない）
"$PYPPT" $SK/project_manager.py init <name> --format ppt169 --dir <ASCIIdir>
# references/デザイン品質.md を読む → svg_output/NN_*.svg を1枚ずつ手書き・notes/total.md を「## Slide N:」で
# チャート/画像は svg_output/images/ に置く。spec_lock の色は「- name: #HEX」のコロン区切りで（STEP0の2・3）
"$PYPPT" "$T/build.py" <proj>           # quality→deck_doctor→split→finalize→pptx をゲート付きで一括（同梱。ppt-master の場所は PPT_MASTER_SCRIPTS）
py -3 "$T/render_deck.py" <最新.pptx>          # → _all.png を Read してセルフレビュー（PowerShell不使用）
# 直し → "$PYPPT" "$T/build.py" <proj> --rebuild （finalize省略の高速再ビルド）→ OKなら用途別フォルダへコピー
```
※ build.py が止まったら表示される「→ 次の一手」に従う。deck_doctor は注釈残留・フッター番号・ノート割当をERROR、禁則・はみ出し・文字かぶり推定をWARNINGで出す（機械検出できる分は目視前に潰す）。

### 🟨 発表資料は「薄く」保つ（話す型の密度ルール・2026-07-07 本人指摘「授業資料のように詰め込むな」）
- **既定は発表資料＝話す型**：オンスライドは「見出し＋視覚アンカー1つ＋短い要点」だけ。**「なぜ・詳細・補足の一言（灰色の“＝…”行）・出典の説明」は全部スピーカーノートへ落とす**。1枚に灰色の補足行を並べ始めたら授業資料化のサイン＝即カット。ただし**証拠（数字・写真・人の言葉・場面）はスライドに残す**（→ 下の「文字を減らすことと中身の両立」）。
- **`deck_doctor --talk`（delivery を書かなければ自動ON。document/balanced で OFF）を作った直後に必ず回す**。潰す優先度：
  - **真の詰め込み＝直す**（数字は deck_doctor の値）：`オンスライド N 字`（**100字超で警告・150字超で停止**）、`22px 未満の本文`（**1字でも停止**）、`28px 未満の本文が30字超`（警告）、`読む場所（<text> の数）`（**13個以上で停止**）、`最大文字が36px 未満＝大見出し/大数字アンカー不在`（警告。→見出しを36px+か大数字を1つ置く）。
  - **例外＝そのままでよい**：比較表・フロー図・対応表など**箱に短いラベルを並べる図**は「本文 N 行と多い」（8行超で警告）が出るが、これは prose の詰め込みではなく**その1枚の視覚アンカー**なので許容（各ラベルが1〜数語なら OK）。**参考文献の行は「※」か「出典」で始めれば字数に数えない**（22px の床の対象からも外れる。`[1]` で始めた行は本文として数える＝2026-09-28 に今の deck_doctor で確かめた）。
- **本当に配る前提（leave-behind）なら delivery=balanced** に切り替える（confirm_ui/spec_lock で明示）＝話す型検査が自動OFF・本文16-17pxで自己完結の読ませる型に。発表と配布を1デッキで兼ねるなら「薄いスライド＋厚いノート」で両立させる（配布時はノート付きPDFで出す）。
- 実測（12枚のデッキ・2026-07 の旧基準での件数）：初版は詰め込みで **--talk WARNING 31件**（S2 272字／S7 302字／S10 326字）。灰色補足行を全カット＋見出し36pxで **13件**（残りは表/フロー図の行数と参考文献のみ）＝発表資料として合格ラインに。

## 🎬 動きを付ける（motion.py・2026-10-13〜）

新しく作ったデッキにも、本人が手で作った pptx にも、書き出した後で動きを足す。**動きだけを頼まれた時（既にある pptx）は、STEP 0 の ppt-master 準備・STEP 1・confirm_ui・brief は通さない**（新しく作るわけではないため）。公言だけはする。詳細・型・落とし穴 → `references/動き.md`。

1. 本人と「どの枚の何を、どう動かすか」を選択式で決める（押す・戻る／順番に出す／変形で配置を変える／流れ続ける背景）。動きは説明に要る所だけ。
   - **動きの予算（2026-10-15 本人「動きができすぎてる」）**：1枚のクリックは**2回まで**・1回のクリックで動く物は**2つまで**・自動で繰り返す動きは**1枚1つまで**（その枚の伝えたいこと自体を見せる時だけ）・強調と軌跡は1枚1〜2つ。motion.py はクリック4回以上／1クリック4つ以上／繰り返し2つ以上で止まり、3回・3つ・繰り返し1つは注意を出す。動きは「その枚の1つのメッセージ」を見せるためだけに使う。全部の要素を順に出す・飾りの点滅・同時に何個も動かす、はしない。どうしても要る枚だけ spec に `"busy": "理由"`（理由がノートと手順書きに残る）。
   - 動きを頼まれた時も、デッキ全体で動く枚は半分くらいまでを目安にする（以前のデッキでは12枚中11枚に動きがあり、4枚で1回のクリックに4〜7個が同時に動いていた＝本人の指摘の元）。
2. 絵が要れば `illust.py` でいらすとやから探し、`_候補.png` を見て選ぶ（背景が透明な PNG）。ppt-master なら SVG の動かす物に `id`（hand・spring 等）を付け、`svg_to_pptx -a none` で書き出す（id が図形の名前になるのは作者の改造版の ppt-master だけ。上流では名前が付かないので、`motion.py list` で名前を見て `#ID`・`text:文字` で指すか、PowerPoint の選択ウィンドウで手で名前を付ける）。
3. `motion.py list` で名前を見る → spec.json → `motion.py apply <deck> spec.json -o <deck>_vN.pptx`（元は上書きしない）。
4. `motion.py verify <deck>_vN.pptx` → `_確認\_コマ送り.png` を Read して、動くべき物が動き、止まるべき端が止まっているかを見る。
5. **本人に渡す時は `_動きの作り方.md`（ノート欄の【動きの作り方】と同じ文）を必ず添える**（本人の回答「毎回、作り方の手順も付ける」）。
6. **`pptx_check.py <deck_vN.pptx>` で ERROR 0 を確かめてから渡す**（動きの予算と情報量を同じ物差しで見る）。
7. 試験：`py -3 "$T/tests/test_motion.py"`（41件）・`py -3 "$T/tests/test_pptx_check.py"`（10件）。

## 📐 STEP 1：イシューからはじめる構成設計（★着手前に必ずユーザー確認）

> 「イシューからはじめよ」(安宅和人) の型を厳守（本人のマスト）。きれいな作図から入らない。**A〜E を提示し合意してから Strategist へ。**

### 🟥 STEP 1-0：中身の確認（選択式・BLOCKING・2026-09-28 本人提案「初めに詳細を細かくセレクト方式で決める＝ありきたりな抽象的スライドを作らないで済む」）

confirm_ui（見た目の八つの確認）より**前**に、中身を決める。**1-0a 全文読み → 1-0b 選択式3回（experience は4回） → 1-0c brief.py v2** の3段。どれも飛ばさない。
> 2026-09-28 本人指摘「中身がないというか」。3本とも、結論を証拠が証明していなかった。海外研修のデッキはキーワードの grep で候補を拾ったので、具体例 E に引いた7行（研修メモ L84・123・129・157・163・172・225）がどれも本人の逐語（`> ` の行）ではなく Claude 側の注記だった。L163 は「本人の一言＋Claude起草案」の節で、08枚目に使った L293 は「場面（推測）」だった。

#### ■ 1-0a 素材の全文読み（BLOCKING・最初の質問より前）
- 本人の素材（研修メモ・議事録・授業ノート・下書き）は **Read で全文**を読む。2000行を超えるなら offset/limit で分け、最後の行まで読む。
- **候補探しに Grep を使わない**。Grep は、読み終えた後に行番号を確かめる時だけ使う。
- 参照メーター（lookup_meter）が「打ち切って」と出しても、この読みは打ち切らない（手順が求める読みなので）。
- 読みながら `<project>/sources/inventory.md` を作る。候補に ID を振り、種類で分ける：

| 種類 | 何を載せるか | 例（海外研修のメモ `研修メモ_現地投函.md`） |
|---|---|---|
| V 逐語 | 本人・相手の言葉そのまま（`> ` の行・発言） | V2 `:320`「半導体のやる気全員の」／V1 `:243`「進路を考えて行動しただけ」 |
| S 場面 | 日時・場所・人がそろう出来事 | S1「Day 3・EM205・Q&A 交流」 |
| N 数字 | 数・日付・時刻・量 | N1「10月1日15時」 |
| Ph 写真 | 写真ファイル名と写っている物 | Ph1 `photos/20260818_QA交流_板書_青色LEDとCMOSインバータ.jpg` |
| A 注記 | Claude 側の補足。推測・起草の行は【推測】【起草】と印を付ける | A1 `:293`【推測】／A2 `:161` の節【起草】 |

  - ID は「種類の頭文字＋番号」（V1・V2・S1・N1・Ph1・A1）。**answers.json の proof.id はこの ID をそのまま使う**（C4 が inventory に同じ ID があるかを見る。E1 のような別の番号を振ると止まる）。
  - 逐語行（V）は全部載せる。V/S/N/Ph の候補は合わせて10個以上（素材にそれより少なければ全部）。
- **読んだ記録**を answers.json の `sources_read` に書く：`{"path": 素材の絶対パス, "lines": 総行数, "read": "1-574"（分けたら "1-300,301-574"）, "verbatim": "> " で始まる行の数, "inventory": "sources/inventory.md"}`。deck_doctor の C4 と brief.py が実物と照合する（範囲に隙間がある・逐語行の数が合わない＝全部読んでいない疑いで停止）。

#### ■ 1-0b 選択式（AskUserQuestion を3回。experience は 1b を足して4回。1回に4問まで。外出中に聞く仕組み〈チャットのボタン等〉を持っていれば同じ物をそちらで・環境依存・任意）

| 回 | 質問 | 選択肢の作り方 |
|---|---|---|
| 1 | **資料の種類（genre）** | 4択＋その他。各選択肢に「選ぶと何が要るか」を書く（deck_doctor の G1〜G9 の重さが変わる）。①研修・留学の報告（experience）＝証明は言葉・写真・場面。数字の枚は必須にしない。期間・人数・主催は表紙か目次に1行（overview）②提案・企画（proposal）＝効果・費用・期限の数字と出典の行 ③研究・実験・授業発表・調べ学習（research）＝データ・方法・参考文献の枚 ④進捗・中間報告（progress）＝いつ・どこまでの事実（overview）と数字。その他＝解説・勉強会・LT（explainer）／告知（notice） |
| 1 | 聴衆と場（誰に・何分・どこで） | 素材・カレンダーから分かる具体（「地域PBLの中間発表・8分・学内の講義室」） |
| 1 | **話の順番（flow）**（2026-10-01 本人の回答「② PREP は既定のまま、別の順も選べる」） | ①PREP（既定・結論→理由→具体例→結論）②時系列（chronological・出来事の順に話し、結論は最後）③困りごと→原因→対策（problem・対策が結論）＋その他（custom）。選択肢には、この発表の素材でその順にすると何枚目に何が来るかを1行ずつ書く。答えは answers.json の `flow`（理由は `flow_why`） |
| 1 | 結論 P（最初に言い切る1文） | **3案。各案を V か S の行から作り、ID と行番号を添える**。「〜ではなく〜」「AよりB」「〜て初めて」は使わない |
| 1b | **experience の時だけ**：聴衆に後輩はいるか | はい／いいえ／分からない。いれば cta を後輩の行動（来年の募集に応募する等）にし、英略語は後輩が分かる言葉で説明する（G8） |
| 1b | **experience の時だけ**：概要の事実（src 付き）はこれで合っているか | 期間・人数・主催を、素材の行（`ファイル名:行`）付きで並べて見せる。はい／直す（その他で直し）。答えが overview になる |
| 2 | 理由 R（multiSelect） | 3〜4案。選択肢に「ID・種類・行番号」を見せる |
| 2 | 具体例・データ E（multiSelect） | 同上。**数字・写真・事例は出典（ファイル名:行／写真ファイル名／URL）付き**。無い数字は作らない |
| 2 | 触れない話題・使わない写真（ng） | 素材から誤解を招きそうな物・SNS禁止の写真・実名 |
| 2 | 聴衆に最後にしてほしいこと（cta）（2026-10-01 に回1から移した＝回1が話の順番で4問になったため） | 「次回の実測に協力してほしい」「空き家の情報を1件教えてほしい」等の行動 |
| 3 | **結論を何で証明するか**（multiSelect・2つ以上） | V/S/N/Ph の候補だけを出す。A（注記）は出さない |
| 3 | 本人の場面（me.scene） | V の行から1つ（本人が何を体験し、何を感じたか） |
| 3 | 最後の結論の言い直し（p_last） | 3案。各案に E の具体（人・数字・場面）を1つ入れる。P と同じ文は出さない。flow が prep 以外で結論が最後の1回だけの順なら聞かない（brief.py が p と同じ文を入れる） |
| 3 | なぜ自分が話すのか（me.why） | 3案。V の行から |

- **選択肢の条件**：どの候補も、素材にある**人・言葉・場面・数値・写真**のどれかで作り、出典（`ファイル名:行` か写真ファイル名）を添える。「効率化」「価値の創出」「今後の展望」「人の熱意」のような、どの発表にも当てはまる**抽象的な候補は失格**。具体的な候補を3つ作れないなら選択肢を出さず、先に素材（資料・写真・数字・メモ）をもらう。
- 元の行が推測・起草なら、選択肢にそう書き添える。本人が確かめるまで、事実や本人の言葉として使わない。確かめ方は選択式の質問（例「Q&A は 8/18 の機械工学科の教授だった？ はい／いいえ／覚えていない」）。確認が取れるまでは、スライドに「〜とみられる」と書くか、使わない。
- 本人が「任せる」と言った時は `how: 本人一任` と書く。**証拠の欄は免除しない**（任されたのは選ぶことだけで、埋めるのは Claude）。
- 選択肢で足りない部分は「その他」の自由入力で受ける。答えを受けたら A〜E（下）はこの brief から埋める＝再度聞かない。

#### ■ 1-0c brief.py v2 で証拠の台帳を書く
- 答えを answers.json にまとめ、**`py "$T/brief.py" <project> <answers.json>`** で書く。手で書かない。出力は2つ：`<project>/brief.json`（証拠の台帳。deck_doctor の C1〜C6・G1〜G5 が読む）と、spec_lock.md の `## genre` / `- genre: xxx` の組と3行組（`brief_confirmed` / `brief`＝`brief_version: 2` と人が読む要約 / `prep`）。何度流しても1組だけ。試験は `scripts/tests/test_brief.py`。
- answers.json の形（海外研修の報告デッキの作り直しの例。値は短くしてある。**proof.id は inventory の ID をそのまま使う**＝V1・V2・Ph1。作者の環境で 2026-09-28 にこの例を試しの inventory と実物の研修メモで brief.py に通し、exit 0 を確かめた）：
  ```
  {"brief_version": 2, "how": "選択式", "genre": "experience", "audience": "学内の研修報告会・10分",
   "overview": [{"k": "期間", "v": "8月16日〜22日", "src": "研修メモ_現地投函.md:7", "quote": "2026-08-16〜08-22"}],
   "p": "（V2 から作る言い切り。対句にしない）", "p_core": ["やる気", "熱意", "本気"],
   "p_last": "（p と別の文。E の具体を1つ含む）",
   "r": [{"id": "R1", "claim": "同じ年ごろの留学生が、進路を考えて動いていた", "slides": [4]}],
   "proof": [{"id": "V1", "for": "R1", "kind": "verbatim", "src": "研修メモ_現地投函.md:243",
              "quote": "進路を考えて行動しただけ", "slides": [4]},
             {"id": "V2", "for": "P", "kind": "verbatim", "src": "研修メモ_現地投函.md:320",
              "quote": "半導体のやる気全員の", "slides": [3, 6]},
             {"id": "Ph1", "for": "P", "kind": "photo", "src": "photos/20260818_QA交流_板書_青色LEDとCMOSインバータ.jpg",
              "quote": "", "slides": [5]}],
   "me": {"why": "…", "scene": {"src": "研修メモ_現地投函.md:398", "quote": "長期の東湖工科大学のプログラム"}, "next": "…"},
   "sources_read": [{"path": "…/研修メモ_現地投函.md", "lines": 574, "read": "1-574", "verbatim": 52, "inventory": "sources/inventory.md"}],
   "cta": "…", "ng": ["研究所の内部の写真（SNS禁止）"], "prep": "C 1 / A 2 / P 3 / R 4 / E 5 / P 6 / T 7"}
  ```
  - 例の割り付け：R1 の枚（4）に R1 の証拠 V1、E の枚（5）に写真 Ph1、最初と最後の P の枚（3・6）に V2。結論 P の強い証拠は V2 と Ph1 の2件。
  - 必須8キー：`p` `p_core`（結論の核の語1〜6個・同義語可）`p_last` `r` `proof` `me` `sources_read` `prep`。加えて `genre`（無ければ general と書いて exit 2）と `overview`（概要の事実 `{k, v, src, quote}`。experience・progress は必須）。
  - `proof.kind` は verbatim（逐語）/ scene / number / photo / diagram / table / annotation（Claude の注記）/ web。**結論 P の強い証拠（verbatim・photo・number・scene）を2件以上**。photo の quote は空でよい。
- **exit 1＝書かない**：必須欄が空／旧書式（p・r・e の文字列だけ）／quote が src 行の前後2行に無い（overview の quote も同じ照合）／src のファイルが sources_read に無い／読んだ範囲に隙間がある・逐語行の数が合わない／inventory に proof の ID が無い／p と p_last がほぼ同じ文／**P の強い証拠が2件未満**（deck_doctor の C2 と同じ重さ）／genre が一覧に無い値／experience・progress なのに overview が空。→ 直して流し直す。
- **exit 2＝書くが警告**：p か p_last に具体（数字・カタカナ3字以上・「」・英字2字以上）が無い／対句（〜ではなく 等）／推測・起草の行を使っている／素材を開けず照合できない／genre が無い（general と書く）。→ 本人に確認するか、案を作り直す。
- brief.json が無い・必須欄が空なら deck_doctor が **ERROR（C1・build 停止）**。PREP と brief の検査は **delivery に関係なく全デッキ**で走る（表紙・目次・謝辞を除いて3枚以下のデッキは R/E の枚を求めない）。9/28 以前の旧書式のデッキを作り直す時だけ `--legacy`（C1〜C6・R0・A0・G1・G4a を WARNING に下げる）。

- **A. イシューを1文で**：「〜について話す」でなく「〜は○○すべきか？」「なぜ〜なのか？」の*問い*。
- **B. 仮説＝キーメッセージを一文**：イシューへの答えを先に言い切る。表紙副題＆まとめの核。
- **C. サブイシューに分解（MECE・3つ程度）**。
- **D. ストーリーラインは PREP（既定・2026-09-28 本人指示「PREPを用いるように」）**：表紙(C) → **目次(A)** → **結論(P)** → 理由(R) → 具体例・データ(E) → **結論をもう一度(P)** → 謝辞(T)。R と E は交互でもよい（R→E→R→E）。最後の P は最初の P の言い直し（同じ主張に、E で見せた具体を1つ足す）。**P/R/E の札（「理由：」「Point」）はスライドに書かない**＝見えない骨組み。WHY型・空雨傘型は本人が指定した時だけ。
  - **PREP 以外の順（2026-10-01〜）**：資料「AI臭い文章とは何なのか」（Kiminori Yokoi・2026-09-28）は「AI臭いスライドは説明の全体の流れをAIに固定される。手直しされないと誰が作っても同じ流れになる」と言う。本人の回答は「② PREP は既定のまま、別の順も選べる」。1-0b の回1で時系列（chronological）・困りごと→原因→対策（problem）・その他（custom）を選んだら、brief.py が spec_lock に `flow: <名前> <日付> 本人 <理由>` を書き、deck_doctor は PREP の順番の検査を緩める（何を緩めるかは deck_doctor の check_prep の docstring）。役割の印（P・R・E）は同じように付ける（証拠と意味の検査はこの印で動く）。結論が最後の1回だけの順では、brief の p_last を省いてよい。
  - **spec_lock.md に必ず1行**：`prep: C 1 / A 2 / P 3 / R 4-5 / E 6-8 / P 9 / T 10`。deck_doctor が読み、無い／表紙・目次の次と最後（謝辞の前）が P でない／R か E が無い／枚数と合わない／A が2枚以上か表紙の直後にない、のどれかで **ERROR（build が止まる）**。`C 1-2`（目次を表紙扱いにする書き方）は使わない＝目次は A と書く。
  - **目次は既定で表紙の直後に1枚**（根拠は本人の既定：2026-09-28「最初に目次を入れたい」・skill-memory「アジェンダ（目次）を必ず入れる」。外部の手引きは目次を条件付きにしている）。例外は3つ：表紙・目次・謝辞を除いて3枚以下（機械は求めない）／告知（notice）／本人が要らないと言った時。後の2つは spec_lock に `agenda: none <日付> 本人 <理由>` を書く（A0 が INFO になる）。
  - **目次の書き方**：項目は3〜5個（A1）。各項目は、対応する枚の見出しを短くした言葉（A3 が後の P/R/E の枚の語と照らす）。「はじめに」「概要」「背景」「まとめ」「今後の展望」のような抽象語の札は使わない（A2 で停止）。1列に縦に並べ、36px 以上、項目の合計100字以内。見出しは「目次」か「この5つの順で話す」。
  - **最後の P は brief の `p_last` を使う**。最初の P と同じ文を貼らない（ほぼ同じ文なら deck_doctor の F1 で ERROR）。
  - **P の文に対句を使わない**（「〜ではなく〜だった」「AよりB」「〜て初めて」。F2 が警告）。
  - **小ラベルにも「結論」「理由」「具体例」「まとめ」と書かない**（コロン無しでも F5 が警告）。
- **E. 絵コンテ化**：1スライド＝1メッセージ。タイトルは結論を言い切るメッセージライン。各メッセージに「So What?」。枚数目安＝5分で10〜12枚。絵コンテの各行に C/A/P/R/E/T を付けて本人に見せる。
  - **1枚1メッセージの確かめ方（2026-10-15 本人「情報量が多い」「1つのスライドに1つ伝えたいことを載せるように」）**：絵コンテの各行に「この枚で伝えたいこと」を**1文**で書く。「〜し、〜」「〜, so 〜」「〜, which 〜」「また」でつながないと書けない枚は、伝えたいことが2つある＝**2枚に分けるか、片方をノートへ**。その枚に置く物は、その1文を支える物（視覚アンカー1つ＋短いラベル）だけ。理論の名前・研究の細部・注意書きなど、1文を支えない物はノートへ。
  - **「もっと詰めて」「専門的に」と言われても、1枚に足し込まない**：中身を深める時は、枚を分けるか、ノート（話す原稿）を厚くする。以前のデッキの2枚は、1枚に図を2〜3つ・読む場所15〜16か所・文6本まで積んで「情報量が多い」と言われた（pptx_check の I1・I2・O2 で停止する量）。
  - **1枚ごとに証拠を割り付ける**（描く前に「主張・証拠・出典」を書く）。design_spec.md に必ず表 `## 証拠の割り付け` を作る。列は、枚／役割（P/R/E）／主張（見出しの文）／証拠 ID（brief.proof）／証拠の種類／レイアウトとその理由。
  - **証拠の欄が空の枚は描かない**（証拠を足すか、枚を削るかノートへ回す）。
  - **レイアウトは証拠の種類で決める**：写真→写真が主役で、見出しを写真の上か横に置く／人の言葉→引用を大きく、話者・日付・場所を添える／数字→大きな数字＋比べる相手／場面→日時と場所＋写真。こうすると枚ごとの形が自然に変わる（全部同じ入り方＝F4 の対策）。

レイアウトの引き出し（表紙/つかみ/ひとことで言うと/3カード(1回まで)/比較表/断言/図解/before-after/まとめ/参考文献）は**毎回同じ並びにしない**。目次は既定で表紙の直後（上の D）。
**左端の色線付きカード・画面の端の全高の帯・題材と関係ない線画は使わない（F3・F6）。小ラベルは全部の枚に置かない（F4）。**

## ✍️ Executor 段階の必読

**文字の大きさ・量の機械ゲート（2026-09-28 本人指摘「文字が小さい・AIくさい・シンプルじゃない」で ERROR 化）**：出典・※注記・フッター以外の文字は **22px 未満が1字でもあれば停止**・28px 未満の本文が30字を超えたら警告。**書く大きさの既定は、本文 32px 以上（2026-09-10 本人指示「24pt 以上」＝32px）・見出し 48px 以上・出典/キャプション/※注記 24px 以上・ページ番号 20px**（22px と 28px は機械の床で、書く大きさではない）／**1枚150字超で停止・100字超で警告**／**読む場所（`<text>` の数）13個以上で停止**／**です・ます調で停止**（謝辞だけ可）／**中身の無い決まり文句で停止**（「無限の可能性」「シナジー」等）。delivery を書かなくても話す型として検査される（配布用は `delivery: document`）。最初からこの数字で書く＝後で削るより速い。

**文字を減らすことと意味の両立（2026-10-01 本人指摘「結局何を言いたいのか伝わらない」）**：減らすのは**文の数**。残した1文の中から**主語・目的語・条件・数字を削らない**。「規則は、機械で止めて」「回らない。0V から犯人を絞る」のように語を削って読点・短文・比喩で締めると、話者がいないと意味が戻らない（配布の PDF・目次・後から読む人）。見出しは、ノートを隠して読んでも「誰が・何を・どうした」が1通りに決まる文にする。→ `references/デザイン品質.md`「🟥 スライドの文字だけで意味が通る」

**文字を減らすことと中身の両立（2026-09-28 本人指摘「中身がないというか」）**：削るのは**説明の文**（なぜ・背景・つなぎ）。**証拠（数字・写真・人の言葉・場面）は削らず、スライドに残す**。100字の目安は人の言葉（「」の引用・括弧込み40字まで）を数えない。150字の停止はすべての字を数える。削った後の R/E の枚に証拠が1つも無ければ deck_doctor の F7 で停止する。ノートへ移すのは理由の説明だけで、ノートは証拠の置き場ではない（スライド＋ノートで200字未満の R/E の枚は F8 が警告）。根拠：Assertion-Evidence（見出しは主張の文、その下は目に見える証拠。https://www.assertion-evidence.com/ ）。

SVG を書く前に **`references/デザイン品質.md` を必ず読む**（SVG手書きの鉄則／AIっぽさ撲滅レイヤー／削った分は証拠で埋める／密度・話し方のモード／目次・引用・データの枚の書き方／言語・トーン・禁止／誤読・うるさい・実感・掴み）。「話す型 vs 読ませる型」は着手前に確認（既定は話す型＝登壇・ノートに原稿）。

## ✅ 提示前セルフレビュー（実物を見せる直前に必ず通す）

### 🟥 初見の読み手（必須・証拠の照合より先・2026-10-01〜）
SVG とノートを書き終えたら、まずこれを通す（読み手の聞き返しで文言が変わるので、証拠の照合より先）。根拠は本人「今のスライド生成は結局何を言いたいのか伝わらない」と、Kiminori Yokoi「AI臭い文章とは何なのか」（豊洲会 2026-09-28）の「話者の説明なしに意味理解を復元できないと、資料を再配布しにくい」。
1. deck_doctor の意味の検査（M1〜）の WARNING を先に潰す（機械で見つかる分を読み手に回さない）。
2. `py "$T/claims.py" <proj> --reader` → `<proj>/review/slide_text.md`（スライドに見えている文字だけ。ノート・brief・画像の中身は入らない）。
3. **subagent_type=slide-reader** を起動する。渡すのは `review/slide_text.md` の絶対パスと聴衆の1行**だけ**。ノート・brief・design_spec・画像・会話の要約は渡さない（意図を知った読み手は、書いていない意味を補ってしまう）。
4. 報告をそのまま `<proj>/review/reader_check.md` に保存する。
5. 聞き返し1件ごとに、資料の会話の型で直す：「これってどういう意味？」→ **こちらの答え（こういう意味）を1文で書く**。答えは brief・ノート・素材から書く（作らない）→ **その答えの文をスライドに置く**（削ってよいのは、無くても意味が変わらない語だけ）。答えが素材から書けない＝その枚の主張に根拠が無い＝削るか本人に聞く。
6. 2 から流し直し、PASS になったら `py "$T/claims.py" <proj> --record-reader PASS --report review/reader_check.md`。**2回続けて FAIL なら選択式で本人に判断を聞く**。
7. 誤字の修正だけなら `--minor '理由'` で evidence_check と reader_check を両方付け直せる。言い回しを変えたら両方やり直す（R0・R1 は同じ hash を見る）。

### 🟥 結論と証拠の噛み合いの照合（必須・これを通るまで本人に見せない・2026-09-28〜）
初見の読み手が PASS した後、目視の自己採点より先にこれを通す。
1. `py "$T/claims.py" <proj>` → `<proj>/review/claims.json` ができる（枚ごとの役割・小ラベル・見出し・本文・ノートと、brief の p / p_core / p_last / proof / me）。最後に content_hash が表示される。
2. **subagent_type=slide-evidence-checker**（~/.claude/agents/）を起動する。渡すのは `review/claims.json` の絶対パスと、`sources_read` にある素材の絶対パス**だけ**。画像・design_spec・spec_lock・会話の要約は渡さない（下書きの見た目と言い回しに引っ張られないようにするため）。
3. 返ってきた報告をそのまま `<proj>/review/evidence_check.md` に保存する（checker は読み取り専用なので、保存は親が行う）。
4. `py "$T/claims.py" <proj> --record PASS|FAIL --report review/evidence_check.md`（報告の最終行の判定をそのまま書く）→ spec_lock に `evidence_check:` 行が1行だけ入り、deck_doctor の R0 がそれを見る。
5. FAIL なら、指摘にある素材の行番号をもとに直し、1 から流し直す。**2回続けて FAIL なら、選択式で本人に判断を聞く**。
6. PASS の後に中身を変えると、R0 が ERROR（ハッシュ不一致）を出す。誤字の修正だけなら `--minor '誤字の修正'` で付け直す（判定は PASS のまま、理由が行に残る）。言い回しや証拠を変えたら 1 からやり直す。

### 目視の自己採点
`preview.ps1` のコンタクトシート `_all.png` を Read して自己採点。1つでもNGなら直してから出す。
「批判を回して」「辛口で」と言われたら **subagent_type=slide-critic**（8観点の辛口批評家・~/.claude/agents/）を起動、提出直前は `/panel` で多面審査。役割の違い：**文字だけで意味が通るかは slide-reader、中身の噛み合いは slide-evidence-checker、見た目と話し方は slide-critic**。
- [ ] **ノートを隠して見出しだけを縦に読み、デッキの主張が1文で言えるか**（言えない＝R1 の読み手に回す前に直す）。比喩の動詞（倒す・壊れる・効く・添える）・指示語（片方・この言葉）・溜めの読点（「規則は、」）で締めた見出しが無いか（M1〜）
- [ ] **最初と最後の P が別の文か**（最後は E の具体を1つ足した言い直し。F1）
- [ ] **R/E の見出しを縦に並べ、全部が P を支えているか**（支えない枚は削るかノートへ）
- [ ] **本人の場面（me.scene）が本文かノートにあるか**（C5）
- [ ] **推測・起草の行を、事実や本人の言葉として使っていないか**（C3）
- [ ] **文字かぶり・はみ出し**なし（`deck_doctor.py` のWARNINGを先に潰した上で、写真/チャート周り・長い見出しを目視）
- [ ] **色は spec_lock 内だけ＝3色のみ**（`color_audit.py` が `3色ルール: PASS` を出す。ベース/メイン/アクセント＋その濃淡だけで4色目の色相なし。主役は accent で目立つか）
- [ ] **写真は現代カラーで"何か・どこか"が一目**。非実物は「イメージ」、CC BY系はクレジット
- [ ] **専門用語に※言い換え**、硬い語を避け具体化。タイトルに主題キーワード
- [ ] **見出し・箇条書きが具体的**（カテゴリ名でなく結論そのもの。「◯◯について」「特徴」「まとめ」で止めていない・数字は見出しに出す）→ `デザイン品質.md`「具体的に書く」
- [ ] **数値は実データ＋出典**。公開に無い数字は作らない
- [ ] **複数行の「」引用を中央揃えにしない**（1行に収めるか、左揃え＋2行目以降1字下げ。Q1・Q2）
- [ ] **目次が表紙の直後にある**（3〜5項目・抽象語の札なし。A0〜A3）／レイアウトが1枚ごとに違う（AI量産感なし。同じ入り方の繰り返し・左端の色線・対句のまとめ文・題材と関係ない線画も無い＝F2〜F6）
- [ ] **読むだけの資料になっていない**（話す型なら薄く＋ノートに原稿・目安秒数）
- [ ] **誤読チェック**：ポジティブ数字が否定に聞こえる／動詞が別義／主語が誤解 になっていないか
- [ ] **大きい数字に実感の換算**がある（裏取り済み。例 5万m³→約25万人分）
- [ ] **うるさくない**：色タグ/インライン色は最小・帯の重複なし・**1枚1視覚アンカー**・リストは並列構造
- [ ] **1枚1メッセージ・動きの予算**：各枚の伝えたいことが1文で言える（つなぎ語なし）／`pptx_check.py` が ERROR 0（読む場所・語数・小さい字・クリック2回まで・1クリック2つまで・繰り返し1つまで）
- [ ] **掴み（なぜ凄いか）が出ている**：落差／世界比較／本番で効いた実証
- [ ] フッター番号・ページ数・ノート割当が正しい（`deck_doctor.py` がERROR検出。並べ替え時の修正は `fix_footers.py`）

## 📒 skill-memory 運用

- 実行完了後、必ず `~/.claude/skill-memory/slide-gen.md` を更新（今回の改善・注意点を追記。無ければ作る）。
- 育てる章の例：**「編集可能デッキ 実地フィードバック総まとめ」**（本人の指摘をラウンドごとに貯める）。あれば**着手時に必ず読む**（誤読潰し・実感換算・うるさい回避・掴みの実例）。
