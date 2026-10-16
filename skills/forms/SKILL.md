---
name: forms
description: アンケート・問い合わせ・申込フォームを Google Forms 用 Apps Script (.gs) で自動生成する。冒頭で「留学生/日本人」の区分を選ばせて表示を分岐し、学籍番号・学科・名前・メールアドレス・質問を必須項目として備える。**呼び出しキーワード**：「フォーム作って」「アンケート作って」「Googleフォーム」「申込フォーム」「問い合わせフォーム」「回答フォーム」「フォーム生成」「formsスキル」等。
argument-hint: "[フォームの用途・聞きたい質問・対象者（例: 学生相談の受付フォーム）]"
---

# forms — Google Forms 自動生成スキル

> **▶ 実行開始時の共通3点セット**（詳細 → `~/.claude/skills/shared-doc-rules/SKILL.md` §8〜§10）
> 1. 📢 **公言**：応答冒頭で「forms スキルを使っています」と必ず出力する（§10）
> 2. 🎯 **イシューからはじめよ**：何のためのアウトプットか（答えるべき問い・満たすべき要件）を最初に確認する（§8）
> 3. 🚫 **AIっぽさ撲滅**：人に読ませる文面は定型句を避ける（§9・該当する場合）
> 4. `~/.claude/skill-memory/forms.md` を読み込む

質問・アンケート・申込フォームを **Google Apps Script (`.gs`)** として生成する。生成した `.gs` を
`script.google.com` に貼って `buildForm` を実行すると、条件分岐つきの本物の Google Form ができる。

**実行開始前に必ず:**
1. `~/.claude/skills/shared-doc-rules/SKILL.md` を読み込む（命名規則・OneDrive ロック対策・出力先）
2. `~/.claude/skill-memory/forms.md` があれば読み込む（過去の調整点）
3. このフォルダの `assets/form_template.gs` を雛形として読み込む

**前提**: 実物の自動生成（STEP 3）とプレビュー画像（STEP 1.5）は Google Chrome と、preview-report スキルの `chrome_cdp.py`（`~/.claude/skills/preview-report/scripts/`）を使う。Python は `requests` と `websocket-client` が要る。無ければ `.gs` を手で貼るフォールバックで進める。

---

## このスキルが必ず守る仕様

どんな依頼でも、生成するフォームは次の骨格を**必ず**含む。

1. **冒頭に区分セレクト1つ（必須）**
   - 「区分 / Category」: 日本人学生 / 留学生 ← **この回答でセクション分岐する**
   - ※「言語 / Language」質問は付けない。表示言語は区分で決まるので不要（運用で廃止した）。
2. **区分でセクションを分けて表示**
   - 日本人学生 → 日本語ラベルのセクション
   - 留学生 → **日英併記**ラベルのセクション
   - （日本人セクションも日英併記にしたい時は CONFIG の `japaneseSectionBilingual: true` だけ）
3. **両セクション共通の必須項目（5つ）**
   - 学籍番号 / 学科 / 名前 / メールアドレス / 質問
   - メールは形式チェック、学籍番号は任意で正規表現チェック

依頼内容（用途・追加で聞きたいこと）に応じて、この5項目に**質問を足す**・選択肢を変える。
ただし上の骨格（区分の分岐・5必須項目）は削らない。

---

## STEP 0: 依頼の把握

`$ARGUMENTS` から用途を読む。不足なら最小限だけ確認する:

- **フォームの用途/タイトル**（例: 相談受付、イベント申込、授業アンケート）
- **5項目に加えて聞きたい質問**（あれば。なければ「質問」欄1つで足りる）
- **学籍番号の形式チェックの要否**（例: `S00X0000` 形式なら `^[A-Za-z]\d{2}[A-Za-z]\d{4}$`。形式は大学ごとに違うので本人に聞く）
- **回答をスプレッドシートに集めるか**（既定はフォーム内集計、必要なら `setDestination` を有効化）

迷う点が無ければ確認せず既定で進める（区分分岐・5必須は確定仕様なので聞き直さない）。

---

## STEP 1: テンプレートを依頼内容に合わせて編集

`assets/form_template.gs` をベースに、次を書き換えて成果物 `.gs` を作る:

- `CONFIG.title` / `CONFIG.description` を用途に合わせる
- 追加質問があれば `addStandardFields` の後ろ、または各セクション内に項目を足す
  - 短文 `addTextItem` / 長文 `addParagraphTextItem` / 単一選択 `addMultipleChoiceItem`
  - 複数選択 `addCheckboxItem` / プルダウン `addListItem` / 日付 `addDateItem` 等
- `CONFIG.studentIdPattern` を要望に応じて設定（不要なら空のまま）
- 学科リストは雛形の例（一般的な学科名を並べただけ）なので、`<大学名>` の実際の学科・用途に合わせて必ず差し替える

### 分岐ロジック（壊さない・最重要）

```
ページ1: 区分(分岐)
  ├ 日本人学生 → jpSection(ページ2)  → 完了後そのまま「送信」
  └ 留学生     → intlSection(ページ3) → 末尾なので「送信」
```

- 分岐は `categoryItem.createChoice('…', セクションのPageBreakItem)` で配線する
- 日本人が留学生セクションに流れ落ちないよう `intlSection.setGoToPage(FormApp.PageNavigationType.SUBMIT)` を入れる
  （`setGoToPage` は「その区切りの“手前ページ”完了後の遷移先」を定める＝手前は日本人セクション）
- セクション(`addPageBreakItem`)・項目は**生成順がそのまま表示順**。冒頭1問（区分）→jp区切り→jp項目→intl区切り→intl項目 の順で append する

---

## STEP 1.5: プレビュー画像を必ず生成して見せる（毎回・最重要）

**`.gs` を渡して「自分で貼って実行して」で止めない。** 自動でできるところまでやって実物を毎回見せる。
最低でもフォームの**実物プレビュー画像**を必ず生成して確かめる。

**作業は成果物フォルダの中で完結させる（Temp に置きっぱなしにしない）**。日本語パスの argv 文字化けは
「Write で日本語パスを埋めた .py を作り subprocess/open で処理」で回避する（shell argv だけが化ける）。

1. `assets/preview_template.html` を複製し、`<!--FIELDS-->` を `.gs` と同じ構成のカードで置換する
   （ページ1の区分→各セクションの全項目。必須は赤 `*`、分岐はバッジで明示）。
   **成果物フォルダ**に `フォーム_{用途}_{YYYYMMDD}_preview.html` として Write する（Write は日本語パスOK）。
2. PNG 化は `scripts/render_preview.py` の `render()` を使う。Write で日本語パスを埋めた driver を作って実行:
   ```python
   import os, sys; sys.path.insert(0, os.path.expanduser(r"~/.claude/skills/forms/scripts"))
   from render_preview import render
   render(r"<成果物フォルダ>\フォーム_{用途}_{YYYYMMDD}_preview.html",
          r"<成果物フォルダ>\フォーム_{用途}_{YYYYMMDD}_v1.png", height=3600)  # 切れたら height を増やす
   ```
   （`~` は Python では展開されない。必ず `os.path.expanduser` を通す）
3. Read ツールで PNG を自分で見て、切れ・崩れ・項目漏れを確認（崩れていれば直して撮り直す）。
4. PNG のパスを提示して見せる（**画面では自動で開かない**。開くのは本人が「開いて」と言った時だけ）。
5. 続けて **STEP 3 で実物の Google フォームも全自動生成**して見せる（プレビュー画像だけで終わらせない）。

## STEP 2: 保存

- 出力先フォルダ: `<YOUR_WORKSPACE>/40_ツール/フォーム/`（作者の構成例。自分の構成に合わせる）
  （特定のイベント・団体の用途なら、そのプロジェクト／イベントのフォルダ配下に置く）
- ファイル名は `shared-doc-rules` §1 の命名規則に従う: `フォーム_{用途}_{YYYYMMDD}_v{N}.gs`
  （`form.gs` のような無印・無版の固定名にしない。「最終版」禁止・同名があれば `_v2`,`_v3`…）
- OneDrive ロック時はバージョンを上げて別名保存し、ユーザーに報告

---

## STEP 3: 実物の Google フォームを全自動生成して見せる（既定・最重要）

`.gs` を渡すだけで終わらない。**承認済みプロジェクトを再利用してフォーム本体を自動生成**し、実物を見せる。
`forms_config.json` の `builder_project_id`（FormApp 承認済み）を使うので、通常は **OAuth 再承認もサインインも不要**。
（配布時は空。初回は下の `NO_PROJECT_ID` の手順で自分の Apps Script プロジェクトを1度作り、その id を入れる）

`.gs` も実物PNGも成果物フォルダ（日本語パスでよい）に置いたままでよい。
argv 文字化けを避けるため、**Write で日本語パスを埋めた driver を作って `cmd_build` を直接呼ぶ**
（`open()`/`subprocess` は Unicode パスを正しく扱う。argv だけが化ける）:
```python
import os, sys; sys.path.insert(0, os.path.expanduser(r"~/.claude/skills/forms/scripts"))
import gforms_cdp as G
G.cmd_build(r"<成果物フォルダ>\フォーム_{用途}_{YYYYMMDD}_v1.gs",
            r"<成果物フォルダ>\フォーム_{用途}_{YYYYMMDD}_実物.png")
```
（CDPが使えず ASCII argv で叩く場合のフォールバックは `python scripts/gforms_cdp.py build "<.gs>" "<png>"`）
3. stdout の `STATUS=` / URL で分岐:
   - `PUBLISHED=... EDIT=... SHOT=...` → 成功。実物PNGを Read で確認→フォルダへ Copy-Item→パスを提示（自動で開かない）。
     公開URL/編集URLを `_URL.md` に保存して提示。
   - `NEED_SIGNIN` → CDP Chrome が Google 未ログイン。開いた Chrome でサインインしてもらい（1クリック）、再度 `build`。
   - `NEED_OAUTH` → 新スコープ（例 `SpreadsheetApp`）を使った時だけ出る。一度だけ承認してもらい再実行。
   - `NO_EDITOR` / `NO_PROJECT_ID` → 再利用プロジェクトが無効。`open`→`inject`→`run`→`harvest` で新規作成し、
     できた project id を `forms_config.json` に更新（次回からまた全自動に戻る）。
4. 個別ステップ（手動デバッグ用）: `open <png>` / `status` / `inject <gs>` / `run` / `harvest <png>` / `shot <png> [full]`。

**通し確認チェックリスト（回答用URLで確認）** — 分岐の実機確認はフォームを開いて行う:
- [ ] 「日本人学生」を選ぶ → 日本人セクションだけ表示→「送信」（留学生ページが出ない）
- [ ] 「留学生」を選ぶ → 日英併記セクション→「送信」
- [ ] 必須を空／メール不正でエラーになる

### フォールバック（CDP が使えない時だけ）: 手動手順を渡す
1. https://script.google.com →「新しいプロジェクト」 2. `.gs` を全文貼り付け→保存
3. `buildForm` を「実行」（初回は権限承認） 4. 実行ログの 編集用URL / 回答用URL を開く

> 補足: Google フォームは回答に応じてラベルを動的に多言語化できないため、本スキルは
> 「区分セクション分岐」で日本語表示と日英併記を出し分ける方式を採る。
> 完全な4分岐（日本語×英語 × 日本人×留学生）が要るなら、セクションを増やして同じ配線を繰り返す。

---

## STEP 終: 完了

1. 成果物 `.gs` を所定フォルダに保存（ルート直下に置かない）
2. `~/.claude/skill-memory/forms.md` を更新（ユーザーの修正・効いた工夫を1行追記、最大10件）

---

## 注意事項

- **確定仕様（区分の分岐・5必須項目）は削らない。** 追加・変更はこの骨格の上に乗せる。「言語」質問は付けない。
- 分岐の `setGoToPage` を消すと日本人回答者に留学生欄まで出てしまう。検証時に必ず通し確認。
- 学科リスト・学籍番号形式などの既定値は**雛形の例**。使う組織の物に必ず差し替える（憶測で残さない）。
- 個人情報を含むサンプル回答や実在メールを `.gs` に書き込まない。
- フォームの文言にも AIくささを残さない（shared-doc-rules §9）。実在しない団体名・数値を作らない。
- 実物生成は CDP で承認済みプロジェクトを再利用する全自動方式が既定（STEP 3）。CDP が使えない時だけ手動手順へフォールバック。
- `builder_project_id` が消えた/無効になったら新規作成して `forms_config.json` を更新する（憶測でIDを書かない）。
