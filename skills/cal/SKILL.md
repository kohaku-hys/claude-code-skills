---
name: cal
description: カレンダー即答 — 「この日空いてる?」「今週なにある?」「○○と被る?」「提出まで平日何日?」にカレンダーを引いて答える。終日枠の排他end・祝日/祭日の判別・同日衝突をスクリプトで計算するので手計算の読み違いが出ない。予定の追加・変更は明示依頼時だけ。**呼び出しキーワード**：「この日空いてる」「予定ある?」「今週なにある」「被ってる?」「ダブってない?」「いつなら空いてる」「平日何日」「窓口いつ開く」「連休いつ」「予定入れて」「カレンダーに追加」「cal」等。
argument-hint: "[例: 10/11 空いてる? / 今週なにある? / 提出まで平日何日? / 10/20 14時に面談を入れて]"
---

# cal — カレンダー即答

> **▶ 実行開始時の共通3点セット**（詳細 → `~/.claude/skills/shared-doc-rules/SKILL.md` §8〜§10）
> 1. 📢 **公言**：応答冒頭で「cal スキルを使っています」と必ず出力する（§10）
> 2. 🎯 **イシューからはじめよ**：聞かれた1点に答える。頼まれていない予定を並べない（§8）
> 3. 🚫 **AIっぽさ撲滅**：事実と日付だけ。「素敵な予定ですね」の類を書かない（§9）
> 4. `~/.claude/skill-memory/cal.md` があれば読む
> 5. **`references/カレンダーAPIの落とし穴.md` を読む**（引数名・排他end・祭日混在・拾い漏れの型。ここを飛ばすと同じ誤読を繰り返す）

勉強の割り付けは `/study-plan`。
**このスキルは「いま聞かれた1点」に答える単発用。**

## STEP 1: 読む

**引くのは自分のメインの暦（primary・`<YOUR_EMAIL>`）と祝日暦の2本だけ**。
家族や友人と共有している暦・別アカウントの暦・他のシステムが自動で書き込む暦は引かない（本人の予定ではない物が混ざる）。

```
ToolSearch("select:mcp__claude_ai_Google_Calendar__list_events")
list_events(calendarId="<YOUR_EMAIL>",
            startTime="YYYY-MM-DDT00:00:00+09:00", endTime="…",
            orderBy="startTime", pageSize=250, timeZone="Asia/Tokyo")
```

- 引数名は `startTime`/`endTime`。`timeMin`/`timeMax` は `Unknown name` で落ちる
- 連休・窓口・平日数が絡む質問なら祝日暦も同じ範囲で1回引く
- **MCP が未接続の PC ではエラーで止めず**「⚠カレンダー未接続なので暦は見ていない」と明示して、暦を見ずに分かる範囲だけ答える

## STEP 2: 日付は手で数えない

応答 JSON をスクラッチパッドに保存して `scripts/cal_dates.py` に通す（標準ライブラリだけで動く）。**終日枠の排他 end・UTC 表記・00:00 終了・祭日の混在を手で処理しない**（全部やらかした実績がある）。

```powershell
py "$env:USERPROFILE\.claude\skills\cal\scripts\cal_dates.py" span      events.json
py "$env:USERPROFILE\.claude\skills\cal\scripts\cal_dates.py" conflicts events.json --on 2026-10-11
py "$env:USERPROFILE\.claude\skills\cal\scripts\cal_dates.py" next-open 2026-10-10 --holidays holidays.json
py "$env:USERPROFILE\.claude\skills\cal\scripts\cal_dates.py" workdays  2026-10-01 2026-10-31 --holidays holidays.json
```

質問の型 → 使うサブコマンド:

| 聞かれ方 | やること |
|---|---|
| 「この日空いてる?」「予定ある?」 | `span` で当日を出す。**終日枠が1件でもあれば「空いている」と断言しない**（時刻が書かれていない） |
| 「今週なにある?」 | `span`。transparent の枠は「予定なし扱いの枠」と添える |
| 「○○と被る?」「ダブってない?」 | `conflicts --on`。終日絡みは「要確認」までしか言わない |
| 「提出まで平日何日?」 | `workdays`。土日祝を除いた実働日 |
| 「窓口いつ開く?」「連休明けは?」 | `next-open`。**窓口提出・対面・自署/押印の締切はここが実効デッドライン** |

## STEP 3: 答える

- **日付は必ず曜日付き**（`2026-10-13(火)`）。「来週の火曜」だけで書かない
- 終日枠は「終日 10/10〜10/12（3日枠）」の形。**end の生値をそのまま書かない**
- 出典は暦の名前ではなく**イベント名**で示す（「メインの暦に『懇親会』10/11 19:00 がある」）
- 暦に無い＝予定が無い、ではない。授業のコマなど暦に入れていない予定もあるので、暦に無いことだけで「空いている」と言わない

## STEP 4: 書き込み（明示依頼があった時だけ）

「入れて」「登録して」と**言われた時だけ**。読みのついでに書かない。

1. 追加先は自分のメインの暦（`<YOUR_EMAIL>`）固定
2. **既存と衝突しないか `conflicts` で先に確認**し、重なるなら登録前に知らせる
3. 内容（日時・タイトル・場所）を1行で復唱してから `create_event`
4. 終日枠を作る時は **end を翌日**にする（排他）
5. 登録したら作成された日時をそのまま読み返して報告する（推測で「入れました」と書かない）

## STEP 5: 記録

新しい落とし穴が出たら **`references/カレンダーAPIの落とし穴.md` に足す**（各 skill-memory に散らさない）。
`scripts/cal_dates.py` を直したら `py scripts/cal_dates.py selftest` を通してから終わる。
