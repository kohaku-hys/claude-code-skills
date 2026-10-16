---
name: preview-report
description: 予習レポート生成 — 授業動画(SharePoint/OneDrive/YouTube)のURL・トピック名から Word(.docx) の予習レポートを自動生成。行列・分数・下付き上付きなどWord数式(OMML)で本物の数式として描画する。数学・物理・工学系の予習に対応。**このスキルを呼び出すキーワード**：「予習レポートを作成」「予習レポート作って」「予習を作って」「授業の予習」「反転授業」「動画から予習」「予習資料」等。動画URLが含まれていたら他の解釈より優先してこのスキルを起動する。
argument-hint: "[動画URL or トピック名 or ファイルパス]"
---

# 予習レポート生成スキル

> **▶ 実行開始時の共通3点セット**（詳細 → `~/.claude/skills/shared-doc-rules/SKILL.md` §8〜§10）
> 1. 📢 **公言**：応答冒頭で「preview-report スキルを使っています」と必ず出力する（§10）
> 2. 🎯 **イシューからはじめよ**：手を動かす前に「このアウトプットで答えるべき問い」を1文で立て、合意してから進む（§8）
> 3. 🚫 **AIっぽさ撲滅**：生成文に量産コピー・定型句を使わない。仕上げに AIくささの観点で見直す（AIくささを消すスキルを別に入れていれば使う）（§9）
> 4. `~/.claude/skill-memory/preview-report.md` があれば読み込み、過去の改善を反映する（無ければ飛ばす）

授業動画のURL or トピック名から **Word (.docx)** の予習レポートを自動生成する。数式・行列は Word の数式機能 (OMML) で描画（プレーンテキスト/LaTeX不使用）。

**フォルダ構成**: 実行コード = `scripts/`（preview.py, chrome_cdp.py, cdp_seek.py, sharepoint_folder.py, capture_folder.py, omml_lib.py, report_gen.py, smoke_test.py）／詳細 = `references/`（フォルダ一括モード.md, CDP堅牢化.md）

**実行開始前に必ず:**
1. `shared-doc-rules/SKILL.md` を読み、命名規則・出力先・ロック対策を適用
2. `~/.claude/skill-memory/学習範囲.md` があれば読む（履修範囲の記号ホワイトリスト。範囲外の記号は展開形に書き換え＝予習レポートでも同じ減点リスク。無ければ飛ばす。「### 使用NG」節に太字で記号を書いておくと build 時に検査される）
3. **動作確認**: `py ~/.claude/skills/preview-report/scripts/smoke_test.py`（約3秒、全項目検証）。FAIL が出たらそのモジュールを修正してから作業開始
4. **連携(MCP):** 動画・資料が Google Drive にあれば、Google Drive のコネクタを入れている場合はそこから取得可。SharePoint は Chrome CDP パイプラインで行う（個人用サイトのホストは環境変数 `SHAREPOINT_HOST` に入れておく。例 `https://contoso-my.sharepoint.com`）

---

## 🗺️ 処理フロー

```
USER: 動画URL [1〜N個] / 共有フォルダURL / 「予習レポート作って」
  → [0] scripts/smoke_test.py（3秒検証）
  → URL種別判定
     ├ フォルダ共有URL（AllItems.aspx/?id=）→ 📁フォルダ一括モード（references/フォルダ一括モード.md）
     │    sharepoint_folder.py list-folder → STATUS分岐 → manifest.json を Read → 回ごとに展開
     └ 個別動画URL / タイトルのみ
  → タイトル判定: 章番号_トピック名形式? ─ YES → Quick モード（~15秒）
                                        └ NO → CDP モード（~3分）
  → [4] ReportConfig 組み立て（omml_lib で数式構築）
  → [5] report_gen.build_report() → .docx（1授業=1ファイル）
  → [6] パスを提示（自動で開かない） → [7] Chrome 終了 → skill-memory 追記
```

## 2 モードの判定

- **🥇 Quick モード（~15秒）**: タイトルに `章番号_トピック名` パターン（例 `05_1_行列式の性質.mp4`）→ 標準カリキュラム知識だけで生成。Chrome 不使用。
- **🏆 CDP モード（~3分）**: タイトルが opaque（`lecture5.mp4` 等）、または実板書の精度が要る場合。**ユーザーは実板書解析を強く望むので、タイトルが明確でも原則動画を見る**（references/CDP堅牢化.md）。

## CDP モード 標準フロー

```bash
# ステップ1: キャプチャ（Chrome起動→認証→10分割スクショ）
py ~/.claude/skills/preview-report/scripts/preview.py capture "<URL1>" "<URL2>" --out ~/AppData/Local/Temp/preview_capture
# → manifest.json + 各動画ディレクトリに10枚のPNG
```

- **ステップ2**: N動画 = N Agent（**subagent_type=board-analyst**＝板書解析官・~/.claude/agents/）を1メッセージで並列発行（プロンプト雛形は下記。タイトル照合・判読不可報告は board-analyst が標準装備）。
- **ステップ3**: 結果を集約し `report_gen.build_report(ReportConfig(...))` で Word 生成（`sys.path` に `scripts/` を追加して import。数式は `omml_lib` の `m_det/m_frac/m_sum` 等 → レシピは `references/CDP堅牢化.md`）。
- **ステップ4**: 生成した .docx のパスを提示（**自動で開かない**）。

**堅牢化ルール（必読 → `references/CDP堅牢化.md`）**: 取り違え防止の `expect_title` 照合／BATCH(3)ごとの Chrome 再起動／`wait_video_ready`／**判読不可箇所は `capture_at_times` で時刻をずらして読み切る（留保で逃げない）**／**板書更新が速い回・固定分割で式を取りこぼす回は `split_and_capture_adaptive`（谷間を差分検出して自動追撮）／`capture_folder.py --adaptive`**／日本語パスは Write tool 経由の .py に埋めて処理。

## 📁 フォルダ一括モード（共有フォルダURL）

手順10ステップ・STATUS分岐・オプション表 → **`references/フォルダ一括モード.md` を必ず読む**。絶対ルールだけここに再掲:

- **STATUS で必ず分岐**（`OK` / `OK_TRUNCATED` / `AUTH_REQUIRED` / `EMPTY` / `CDP_DOWN` / `TIMEOUT`）。`AUTH_REQUIRED` は Chrome でのサインイン完了を**待ってから**再実行。
- **捏造禁止**: 欠番の連番補完・ダミー生成・件数やファイル名の推測記入は一切しない。ファイル名は manifest JSON を Read で読む（コンソールに日本語を print しない＝文字化け）。
- **1回 = 1 Word**。`groups.lectures` 単位で処理。

## レポート生成の原則

- **1授業 = 1 Word ファイル**。N動画は章立て `§1, §2, ...`。ファイル名は回数のみ（例: `線形代数Ⅰ_予習レポート_05_行列式の性質と一般の計算_v1.docx`）
- **標準構成**: タイトル（科目・回・トピック）／氏名・学籍番号・提出日／■対応動画一覧／■学習目標／§1 導入／§2〜§4 各動画の内容（定理・数式・例）／§5 つまずきやすい点／§6 予習用練習問題（解答付き5-6問）／■授業前のまとめ
- **build 時の機械検査**（`report_gen.check_config`。`build_report` が Word を作る前に必ず呼ぶ）:
  - **止める（ValueError・Word を作らない）**: `goals`・`sections`・`common_pitfalls`・`summary_paragraphs` のどれかが空／練習問題が5〜6問でない／解答の無い問題がある
  - **警告（stderr に出す・止めない）**: `capture_manifest` が未指定か見つからない（＝動画を見ていない疑い。タイトルが明確でも動画を見る）／`~/.claude/skill-memory/学習範囲.md` の「使用NG」記号（Σ・∈ 等。OMML の ∑ も含む）を使っている。その回で習う記号なら残してよく、そうでなければ展開形に直す
  - CDP モードでは `ReportConfig(capture_manifest=<preview.py capture が出した manifest.json>)` を必ず渡す
- 保存は `omml_lib.safe_save_path`（中身は shared-doc-rules の本体）。「最終版」「完成版」「final」入りのファイル名は ValueError で止まる
- **Agent 並列解析のプロンプト雛形**: 「動画〈タイトル〉の10枚の板書スクショを解析し、①定理番号と名前 ②各定理の数式 ③例題と計算過程 ④章構成 ⑤訂正・注釈 を Markdown で返す。フレームパス: [10個]。各フレームのプレイヤータイトル番号を照合し混入は除外。手書き推測OK、その場合『(推測)』と付記」

## 本人の情報（表紙に入る値）

- 氏名 `<YOUR_NAME>` ／ 学籍番号 `<STUDENT_ID>` ／ 所属 `<学部・学科>`。`ReportConfig(student_name=..., student_id=..., affiliation=...)` に渡すか、環境変数 `PREVIEW_REPORT_STUDENT_NAME` / `PREVIEW_REPORT_STUDENT_ID` / `PREVIEW_REPORT_AFFILIATION` に入れておく（どれも無ければダミーの `山田 太郎` / `s00x0000` が入るので、提出前に必ず直す）
- 学年は `currentDate` と本人の入学年度から計算する（入学年度が分からなければ本人に聞く）
- 出力先: `<YOUR_WORKSPACE>/10_学内/10_授業/{学年}年{前期|後期}/{科目名}/予習/`（作者の構成例。自分の構成に合わせて書き換える。例 `2年前期/物理学Ⅱ/予習/`）
