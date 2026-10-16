---
name: zenn
description: Zenn 記事投稿の自動化 — 記事作成・プレビュー・公開・更新を一気通貫。**このスキルを呼び出すキーワード**：「Zennに投稿」「Zenn記事作って」「Zennに公開」「Zenn更新」「技術記事書いて公開」「ブログ記事 Zenn」等。
argument-hint: "[記事タイトル or 下書きMDファイル or トピック]"
---

# Zenn 記事投稿スキル

> **▶ 実行開始時の共通3点セット**（詳細 → `~/.claude/skills/shared-doc-rules/SKILL.md` §8〜§10）
> 1. 📢 **公言**：応答冒頭で「zenn スキルを使っています」と必ず出力する（§10）
> 2. 🎯 **イシューからはじめよ**：手を動かす前に「このアウトプットで答えるべき問い」を1文で立て、合意してから進む（§8）
> 3. 🚫 **AIっぽさ撲滅**：生成文に量産コピー・定型句を使わない。仕上げに §9 の観点で見直す（§9）
> 4. `~/.claude/skill-memory/zenn.md` を読み込み、過去の改善を反映する

Zenn に技術記事を投稿する一連の作業（下書き作成→プレビュー→GitHub経由で公開）を自動化する。

**実行開始前に必ず:**
1. `~/.claude/skills/shared-doc-rules/SKILL.md` を読み込み（命名規則・OneDrive ロック対策、§7外部連携）
2. `~/.claude/skill-memory/zenn.md` が存在すれば読み込み（過去の気づき）

**連携(MCP):** `zenn-content` リポジトリの状態・既存記事・PRは手元の `git`/`gh` CLI で確認する（GitHub MCP があっても、ここでは `git`/`gh` CLI で十分）。記事内の事実・最新情報は **WebSearch / WebFetch**（使えるなら Tavily も）で裏取り。push・公開は確認を取ってから。

---

## 🎯 トリガーフレーズ

ユーザーが以下を発話したら **必ずこのスキルを Skill ツールで呼び出す**：

- 「Zennに投稿してください」「Zenn記事作って」「Zennに公開」
- 「技術記事を書いて Zenn にアップ」
- 「ブログ記事まとめて Zenn へ」
- 「今回の実装を Zenn 記事化」「この内容を Zenn にまとめて」
- 既存の Markdown を渡して「Zenn で公開」

---

## 📁 Zenn プロジェクト（既存）

置き場は作者の例（`C:/dev/zenn-content/`）。自分の clone 先に読み替える。

```
C:/dev/zenn-content/
├── articles/
│   └── <slug>.md      ← 記事本体
├── books/
├── .gitignore         ← .letta/ 等の除外設定済み
├── package.json
└── README.md
```

**GitHub リポジトリ**: `https://github.com/<YOUR_GITHUB>/zenn-content`
**Zenn連携**: 設定済み（push で自動公開）

**下書きのバックアップ（環境依存・任意）**: リポジトリをクラウド同期の外に置いている場合、PC が壊れると push していない下書きが消える。
記事を作ったり直したりしたら、最後に同期フォルダにも写しておく（例: `cp articles/<slug>.md "<YOUR_ONEDRIVE>/drafts/zenn-content/articles/"`）。

---

## 🗺️ 処理フロー

```
USER: 「Zennに投稿して」 + [記事内容 or Markdownファイル or 依頼]
        │
        ▼
[1] 記事の骨格を決定
    - タイトル・emoji・topics・type(tech/idea) を決める
    - slug は英数字ハイフン（例: claude-code-cdp-automation）
        │
        ▼
[2] 本文を書く（または既存MDをリライト）
    - 読みやすさ優先（学生でも読める温度感）
    - 失敗談・再現手順を具体的に
    - コードブロックは言語指定必須
        │
        ▼
[3] frontmatter 付けて articles/<slug>.md に保存
    ---
    title: "…"
    emoji: "🔧"
    type: "tech"
    topics: ["claudecode", "python", ...]
    published: false   ← 最初は false で下書き
    ---
        │
        ▼
[4] プレビュー (任意)
    cd zenn-content && npx zenn preview --port 8000
    → http://localhost:8000/articles/<slug> でブラウザ確認
        │
        ▼
[5] セキュリティ監査 (必須！)
    - 個人情報 (氏名・学籍番号・メアド・PCユーザー名パス) が無いか
    - 組織特定できる文字列 (ドメイン名・社内URL) は汎用化
    - .letta/ 等の AI 会話履歴が含まれていないか
        │
        ▼
[6] 公開
    - published: false → true に変更
    - git add & commit & push
    - Zenn 連携なので自動で zenn.dev/<YOUR_ZENN_ID> に反映
```

---

## セキュリティ監査（最重要）

**公開前に必ずチェック**。1回でも流出すると取り返しがつかない。

```bash
# ⚠ クォート内の ~ は展開されない。~/"…" の連結形（~はクォートの外）で書く
cd "C:/dev/zenn-content"
# 記事内の危険文字列スキャン。<…> は自分の学籍番号・氏名・メールの @ より前・組織のドメイン・
# PC のユーザー名・GitHub 名に置き換えて並べる
grep -inE "(<STUDENT_ID>|<YOUR_NAME>|<YOUR_EMAIL_LOCAL>|<ORG_DOMAIN>|C:\\\\Users\\\\<USERNAME>|<YOUR_GITHUB>)" articles/*.md \
    || echo "OK: no personal info"

# 履歴にも残ってないか
git log --all --oneline --name-only | grep -E "(letta|\.env|credentials)" \
    || echo "OK: history clean"
```

**必ず汎用化するもの**:

| 危険 | 置換先 |
|------|--------|
| 組織の SharePoint の URL（テナント名入り） | テナント名を `<org>` に置き換える |
| `C:\Users\<ユーザー名>\...` | `<ホームディレクトリ>/...` |
| 学籍番号（`<STUDENT_ID>`） | (削除) |
| 氏名（`<YOUR_NAME>`） | (削除) |
| 個人メアド | (削除) |

**絶対に push してはいけないもの**:

- `.letta/` — AI会話履歴（プロンプト全文が入る）
- `.env` — APIキー
- `credentials.json` — 認証情報
- OAuth トークン

`.gitignore` に常に追加：
```
node_modules
.DS_Store
.letta/
.env
*.key
credentials*.json
```

---

## 🚀 公開コマンド

```bash
ZENN_DIR="C:/dev/zenn-content"   # 自分の clone 先（例）
cd "$ZENN_DIR"
# ⚠ GitHub の認証が無い PC では、push の初回にブラウザ認証を求められる。本人がその場にいる時だけ実行する

# 1. published を true に
# (Edit ツールで `published: false` → `true`)

# 2. コミットして push（★push＝外部公開。実行前に必ず本人の明示承認を得る）
git add articles/
git commit -m "publish: <記事slug>"
git push

# → Zenn 側で自動公開、URL: https://zenn.dev/<YOUR_ZENN_ID>/articles/<slug>
```

> **公開の主体**: 外部公開は本人実行が原則。/zenn の `git push` だけは、
> 「セキュリティ監査クリア＋本文最終版の提示＋本人がその場で『公開して/pushして』と明示承認」
> の3条件が揃った時のみ代行してよい。承認なしの push は絶対にしない。

初回セットアップ手順（リポジトリを作る時・作り直す時）→ `references/執筆ガイド.md`

---

## 記事の書き方（STEP [2] で必読）

本文を書く前に **`references/執筆ガイド.md` を読む**（読みやすさの原則・構造テンプレ・frontmatter テンプレ・トラブルシューティング・初回セットアップ手順）。
