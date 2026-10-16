# Google カレンダー（MCP）の落とし穴

結論から: **引数は `startTime`/`endTime`。終日枠の `end` は排他。祝日暦には祭日が混ざる。日付計算は手でやらず `cal_dates.py` に通す。**

カレンダーを引くスキル（cal・study-plan 等）の skill-memory に散っていた知見の集約先。
新しい落とし穴はここに足す（各 skill-memory に散らさない）。as of 2026-09-28。

## 0. 読んでよいカレンダー

**自分のメインの暦（primary・`<YOUR_EMAIL>`）と日本の祝日暦 `ja.japanese#holiday@group.v.calendar.google.com` の2本だけ。**
それ以外の暦（家族・友人と共有している暦、別アカウントの暦、他のシステムが自動で書き込む暦）は読まない。本人の予定ではない物が混ざるため。

`list_calendars` で一覧を出し、読む2本を最初に1度決めておく:

| summary | id | 扱い |
|---|---|---|
| （自分のメールアドレス） | `<YOUR_EMAIL>` | **読む**（primary） |
| 日本の祝日 | `ja.japanese#holiday@group.v.calendar.google.com` | **読む**（連休判定のみ・予定欄には出さない） |
| それ以外 | `…@group.calendar.google.com` など | 読まない |

## 1. 引数名（ここで1往復無駄にした実績が2回ある）

`timeMin` / `timeMax` / `max_results` は **`Unknown name` エラー**。正しくは:

```
calendarId, startTime, endTime, orderBy, pageSize, timeZone, fullText, eventType
```

- `startTime`/`endTime` は ISO8601。`+09:00` を付ける（`2026-09-28T00:00:00+09:00`）
  - 2026-10-16 追記: ツールの説明が「オフセットも `Z` も付けない」に変わった。`2026-10-16T00:00:00` のように素の時刻で渡すと JST として通る（timeZone も渡さなくてよい）
- `timeZone` は `Asia/Tokyo`
- `orderBy` は `default` / `startTime` / `startTimeDesc` / `lastModified`
- `pageSize` は既定100・最大250

## 2. 終日枠の `end` は排他

`end.date` は**翌日**が入る。表示上の最終日は **end − 1日**。

さらに **MCP は `date` を `2026-10-10T00:00:00Z` の形で返すことがある**（素の `2026-10-10` の時もある）。
これを UTC の datetime として parse して JST に直すと **+9時間ずれて日付が翌日になる**。`date` は先頭10文字だけ見る。

実物（2026-09-28 取得）: 「学会ボランティア」`start.date=2026-10-10T00:00:00Z` / `end.date=2026-10-13T00:00:00Z` → **10/10〜10/12 の3日枠**。

`dateTime` 形式でも **00:00 終了は前日まで**の表示。

## 3. `timeZone` フィールドは信用しない

イベントの `timeZone` は旅程の名残が残る。実物: ある予定（10/1）は `timeZone: Asia/Ho_Chi_Minh` なのに `dateTime` は `+09:00`。
**`dateTime` 文字列のオフセットが正。**

## 4. 祝日暦には祭日が混ざる（2026-09-28 に発見）

`ja.japanese#holiday` は祝日と**祭日（年中行事）を両方返す**。祭日は役所も大学も開いている。

- `description` が `祝日` → 閉庁（スポーツの日 10/12・文化の日 11/3・勤労感謝の日 11/23）
- `description` が `祭日` → **開庁**（七五三 11/15・クリスマス 12/25）

全件を休みに数えると **12/25(金) を閉庁日と誤判定して窓口の判定が3日ずれる**。
`cal_dates.py` は既定で祝日だけを数える（祭日も数えたい時は `--observances`）。

## 5. `orderBy=lastModified` は昇順（新しい物が最後のページ）

前回巡回以降の新規・更新を探す時に使うが、**昇順なので新しい登録は最後のページに出る**。
1ページ目だけ見て「今日の登録は無い」と書かない。`pageSize=250` で最後まで繰る。

レスポンス直下の `updated`（`events` 配列の外にある**暦そのもの**の更新時刻）が一覧中のどの `updated` より新しければ、
**引いた期間の外で何かが変わっている**。

## 6. 拾い漏れやすいイベントの型

| 型 | 見分け方 | 扱い |
|---|---|---|
| 試験の一斉登録 | 同じ色（`colorId`）で summary が「〜テスト」の枠がまとめて入っている | 試験日として控える |
| 本人が手で入れた提出物 | colorId も description も無い。summary に「レポート/課題/提出」 | 提出締切として控える |
| 研修・留学の移動枠 | 終日＋`transparency: transparent`（＝予定なし扱い） | **description を必ず読む**。「成果発表/final presentation/提出」があれば締切として控える |
| 繰り返しの移動した回 | `recurringEventId` と `originalStartTime` がある | `start` が実際の開催時刻 |
| 説明文が空の枠 | get_event でも `description`/`location` が空 | 推測で埋めない。⚠要確認で載せる |

## 7. 日付計算は手でやらない

```powershell
py "$env:USERPROFILE\.claude\skills\cal\scripts\cal_dates.py" span      events.json
py "$env:USERPROFILE\.claude\skills\cal\scripts\cal_dates.py" conflicts events.json [--on 2026-10-11]
py "$env:USERPROFILE\.claude\skills\cal\scripts\cal_dates.py" next-open 2026-10-10 --holidays holidays.json
py "$env:USERPROFILE\.claude\skills\cal\scripts\cal_dates.py" workdays  2026-10-01 2026-10-31 --holidays holidays.json
py "$env:USERPROFILE\.claude\skills\cal\scripts\cal_dates.py" selftest
```

`events.json` / `holidays.json` は **MCP の応答をそのまま保存した物**（`{"events":[…]}` でも素の配列でもよい）。
`--holidays` はカンマ区切りの日付（`2026-10-12,2026-11-03`）も受ける。

- `span` — 各予定を「表示上の初日〜最終日」に正規化（排他 end・UTC・00:00終了を全部吸収）
- `conflicts` — 同日衝突を出す。**終日枠が絡む組は「要確認」までしか言わない**（時刻が書かれていないので本当に衝突するかは本人しか判定できない＝2026-09-14 の学び）
- `next-open` — 窓口が次に開く平日。**窓口提出・対面・自署/押印が要る締切はここが実効デッドライン**（2026-09-21 の学び）
- `workdays` — 土日祝を除いた日数。「準備に充てられる平日が何日あるか」に使う

変更したら必ず `selftest` を通す（19件。実データ由来のケースが入っている）。

## 8. 書き込み

**読むのは随時。書くのは明示依頼があった時だけ。** 自動で回す処理からの書き込みも、外部送信と同じ扱いで下書き止まりにする。

## 8b. 終日枠を作る時は時刻を `Z`（UTC 0時）で渡す（2026-09-29 に踏んだ）

`create_event` / `update_event` に `allDay=true` で `startTime=2026-09-30T00:00:00+09:00` を渡すと、
**UTC に直されて `start.date=2026-09-29` になる**（前日にずれる）。応答の `start.date` は先頭10文字が日付。

- 正しい渡し方: `allDay=true`, `startTime=2026-09-30T00:00:00Z`, `endTime=2026-10-01T00:00:00Z`（end は翌日で排他）
- **作った直後に応答の `start.date` を読み、狙った日か確かめる**。ずれていたら `update_event` で直す（今回は1回の update で直った）
- 直したら `list_events`（`fullText` で絞る）で読み返し、対象日に1件だけあること・前日に残っていないことを見る

## 9. 認証はPCごとに違う

- claude.ai の Google Calendar コネクタは PC（アカウント）ごとに認証が要る。読めるかは1回引いて確かめる
- 自前の OAuth クライアントを使う時、同意画面が「テスト」のままだと **refresh token が7日で失効**する。無人で回す物はサービスアカウントにする

取れない PC では**エラーで止めず**「⚠カレンダー未接続」と1行入れて続行する。
