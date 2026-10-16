# claude-code-skills

大学生が Claude Code で学業や課外活動の文書を作るために書いた、日本語のスキル24個と、スキルから呼ぶ審査役のエージェント13体です。
実験レポート（Word）、スライド（編集できる PowerPoint）、議事録、ES、メール、予習レポートなどを、確認の質問から仕上げの検査まで同じ手順で回せます。
作者は電子情報工学科の学部2年で、自分の課題や発表の準備に使いながら直してきました。

- 前提: **Windows 11 ＋ 日本語**。Python は `py` ランチャーで呼びます（3.9 以上）
- ライセンス: MIT

## 入れ方

使いたいスキルのフォルダを `~/.claude/skills/` に、エージェントを `~/.claude/agents/` にコピーします。
文書系のスキルは共通ルール `shared-doc-rules` を読むので、これは必ず一緒に入れてください。

PowerShell:

```powershell
git clone https://github.com/kohaku-hys/claude-code-skills.git "$env:USERPROFILE\claude-code-skills"
New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills", "$env:USERPROFILE\.claude\agents" | Out-Null
Copy-Item -Recurse -Force "$env:USERPROFILE\claude-code-skills\skills\*" "$env:USERPROFILE\.claude\skills\"
Copy-Item -Force "$env:USERPROFILE\claude-code-skills\agents\*" "$env:USERPROFILE\.claude\agents\"
```

Git Bash / macOS / Linux:

```bash
git clone https://github.com/kohaku-hys/claude-code-skills.git ~/claude-code-skills
mkdir -p ~/.claude/skills ~/.claude/agents
cp -r ~/claude-code-skills/skills/* ~/.claude/skills/
cp ~/claude-code-skills/agents/* ~/.claude/agents/
```

一部だけ入れる時は、例えば `skills/report` と `skills/shared-doc-rules` だけをコピーします。
コピーした後に Claude Code を開き直すと、`/report` のように呼べるようになり、発話の言葉からも自動で選ばれます。

## 入れた後に書き換える所

作者の環境の固有名は、次の置き換え文字にしてあります。自分の値に書き換えるか、スキルを使う時にその値を Claude に伝えてください。

| 置き換え文字 | 中身 |
| --- | --- |
| `<YOUR_WORKSPACE>` | 成果物を置く作業フォルダ（作者は OneDrive 上の1フォルダ） |
| `<YOUR_ONEDRIVE>` | OneDrive のルート |
| `<YOUR_NAME>` / `<STUDENT_ID>` | 表紙などに入れる氏名と学籍番号 |
| `<YOUR_EMAIL>` | カレンダーを読む時の自分の暦（Google アカウント） |
| `<YOUR_GITHUB>` / `<YOUR_ZENN_ID>` | Zenn 連携の GitHub リポジトリと Zenn のユーザー名 |
| `<大学名>` | フォームの選択肢など |

フォルダ構成（`10_学内/10_授業/…` のような番号付きフォルダ）は作者の構成の例です。保存先は `shared-doc-rules/SKILL.md` の §2 でまとめて決めているので、そこを自分の構成に直せば、その変更が全スキルに効きます。

## スキル一覧

`/スキル名` で呼べます。前提の列が空の物は、Claude Code だけで動きます。

### 文書を作る

| スキル | できること | 前提 |
| --- | --- | --- |
| `report` | 実験レポート・技術報告書を Word で作り、表データの照合・文体の検査・採点役の審査まで回す | python-docx, pymupdf, pikepdf, matplotlib, openpyxl, pywin32。Word・Excel（PDF化とグラフ書き出しだけ） |
| `proposal` | 留学申請書・提案書・イベント企画書を、構成案の合意から Word で作る | python-docx |
| `abroad-report` | 留学・海外研修の報告書を、体験と写真から日英対応の Word で作る | python-docx |
| `budget` | 費目分類と集計式の入った予算表を Excel で作る | openpyxl |
| `agenda` | 時間配分と担当の入った会議のアジェンダを作る | |
| `meeting-notes` | メモから、決定事項とアクション付きの議事録を作る | |
| `email` | 宛先に合わせた敬語とトーンで、そのまま送れる日本語のメールを作る・直す | |
| `forms` | 区分で質問が分かれる Google フォームの Apps Script を作り、実物の作成まで行う | Chrome, requests, websocket-client。`preview-report` の chrome_cdp.py を使う |

### スライド

| スキル | できること | 前提 |
| --- | --- | --- |
| `slide-gen` | 編集できる PowerPoint（図形・文字・ノート付き）を作り、検査を通してから渡す。作ったデッキに後から動きを付けることもできる | [ppt-master](https://github.com/hugohe3/ppt-master)（Python 3.10 以上）を別に入れ、場所を環境変数 `PPT_MASTER_SCRIPTS` で渡す（既定 `C:\dev\ppt-master\skills\ppt-master\scripts`）。python-pptx, lxml, Pillow, budoux, pywin32。プレビュー・PDF・動画の書き出しは PowerPoint |

### 授業と勉強

| スキル | できること | 前提 |
| --- | --- | --- |
| `preview-report` | 授業動画の URL やトピック名から、数式入りの Word の予習レポートを作る | python-docx, requests, websocket-client, numpy, Pillow, Chrome。SharePoint の動画は環境変数 `SHAREPOINT_HOST` |
| `quiz` | 授業資料から、解答と解説の付いたテスト問題を作る | |
| `study-plan` | 授業資料と試験日から、週単位・日単位の学習計画を作る | Google Calendar のコネクタ（任意） |
| `transcribe` | 授業の録音を文字に起こし、授業ノートにまとめる | `GROQ_API_KEY`, groq, python-dotenv, pydub, ffmpeg。手元で回すなら faster-whisper |
| `breadboard-diagram` | ブレッドボードの組み立て図を、配線の接続を検査してから A4 の PDF にする | pymupdf, Chrome か Edge |
| `cal` | 「この日空いてる?」「提出まで平日何日?」にカレンダーを引いて答える。日付の計算はスクリプトで行う | Google Calendar のコネクタ |

### 就活と発信

| スキル | できること | 前提 |
| --- | --- | --- |
| `es` | 自分の素材メモから、字数に収めた ES・自己PR・志望動機と面接の想定問答を作る | |
| `self-intro` | 素材メモから、話題を並べずに一本の線で語る自己紹介文を作る | |
| `linkdle` | 活動から LinkedIn の投稿の下書きを作り、投稿ネタを時系列のネタ帳で管理する | |
| `competition` | コンペのアイデアを「自分の体験、課題の数字、事業の形」の順に整理し、出典で裏を取る | |
| `zenn` | Zenn の記事の下書き、個人情報の検査、公開までを通しで行う | git, Node.js (zenn-cli) |

### 審査と管理

| スキル | できること | 前提 |
| --- | --- | --- |
| `panel` | 成果物を複数のエージェントに同時に審査させ、直す順番の付いた講評にまとめる | `agents/`。レポートとスライドの機械検査は `report`・`slide-gen` の道具を使う |
| `skill-new` | 要望の文から、自動で選ばれやすい説明の付いた SKILL.md を作る | |
| `skill-maintain` | スキル群の古いパス・切れた参照・構造の崩れを点検して直す | 点検は `py skills/skill-maintain/scripts/selftest.py --skills <スキルのフォルダ>` |
| `shared-doc-rules` | 文書系スキルが読む共通ルール（命名・保存先・ロック対策・文体）。直接は呼ばない | |

## エージェント一覧（`agents/`）

スキルの中から `subagent_type` で呼ぶ審査役・作業役です。書き手の Claude と判定を切り離すために使います。

| エージェント | 役目 |
| --- | --- |
| `grader` | 実験レポート・課題を、要領と慣習だけを見て100点満点で厳しめに採点する |
| `math-checker` | 数式・数値・単位・有効数字を、入力値から計算し直して確かめる |
| `copy-editor` | 誤字・敬語・文体の揺れ・AIくささを校正し、採るか決められる修正案で返す |
| `ai-detector` | 文章が人の書いた物か AI の書いた物かだけを判定する（書いた事情は渡さない） |
| `fact-checker` | 数値・固有名詞・実績を Web の一次情報で裏取りする |
| `adversarial-verifier` | 主張や数値を、崩す側に立って確かめる |
| `web-researcher` | まだ手元に無い情報を集め、出典付きのメモにする |
| `doc-scout` | ワークスペースから要領・過去のレポート・資料を探し、中身の1行要約を付けて返す |
| `board-analyst` | 授業動画の板書の画像から、定理・数式・例題を取り出す |
| `slide-critic` | スライドの画像を8つの観点で辛口に批評する |
| `slide-evidence-checker` | スライドの主張が素材で裏付けられているかを、下書きを見ずに照らし合わせる |
| `slide-reader` | スライドの文字だけを読み、話し手の説明なしで意味が通るかを判定する |
| `coder` | 実装・バグ修正・スクリプト作成・テストの実行を受け持つ |

## 共通の仕組み

- **公言とイシュー思考**: どのスキルも、始める時に「◯◯スキルを使っています」と言い、作る前に「この成果物で答える問い」を1文で決めます（`shared-doc-rules` §8・§10）
- **AIくささの抑制**: 人に読ませる文章は、定型句や意味が1通りに決まらない文を避ける規則を通します（§9）
- **自己改善メモ**: 各スキルは `~/.claude/skill-memory/{スキル名}.md` があれば最初に読み、終わったら学んだことを追記します。無くても動きます
- **版の管理**: ファイル名は `_v1` `_v2` と数字を上げるだけにし、「最終版」「final」は付けません（`shared-doc-rules/scripts/safe_save_path.py` が機械で止めます）

## このリポジトリに入れていない物

作者の環境専用の物（Telegram の bot と連動する日報・締切管理・大学ポータルの巡回など）と、他の人が作ったスキルは入れていません。
作者が一緒に使っている他の人のスキルは、元の場所から入れてください。

| 物 | 元の場所 |
| --- | --- |
| 公式のスキル集（docx・pptx・pdf など） | <https://github.com/anthropics/skills> |
| Obsidian のノート記法のスキル | <https://github.com/kepano/obsidian-skills> |
| 日本語の技術文書の文章規範（japanese-tech-writing） | <https://gist.github.com/k16shikano/fd287c3133457c4fd8f5601d34aa817d> |
| 説明文に緩急を付ける規範（cognitive-rhythm-writing） | <https://gist.github.com/k16shikano/eb2929f13ed19c97188393d297be8432> |
| 編集できる PPTX を作る OSS（`slide-gen` の前提） | <https://github.com/hugohe3/ppt-master> |

## Python のパッケージ

使うスキルの分だけ入れれば足ります。全部入れる時は次の1行です。

```powershell
py -m pip install python-docx python-pptx lxml budoux openpyxl pymupdf pikepdf matplotlib numpy Pillow requests websocket-client pywin32 groq python-dotenv pydub pytest
```

テストは `py -m pytest skills/<スキル>/scripts/tests -q` で回せます。
