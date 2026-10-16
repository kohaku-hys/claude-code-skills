# -*- coding: utf-8 -*-
"""カレンダーの日付計算。認証も通信もしない純関数だけ（入力は MCP list_events の JSON）。

なぜ要るか: 予定の確認で毎回手計算していた3つが、実際に読み違いを起こしている。
  1. 終日枠の end は排他（2026-09-11 に旅程の最終日を1日読み違えた）
  2. 窓口提出は「期日」ではなく「次に窓口が開く平日」が実効デッドライン（2026-09-21）
  3. 同じ日に別の予定が乗っているかの突き合わせ（2026-09-14 の二重予約見落とし）
手で数えると間違うので、ここに閉じ込めて selftest で守る。読む対象は自分のメインの暦と祝日暦だけ。

使い方:
  py cal_dates.py span      events.json                   # 各予定の「表示上の初日〜最終日」に正規化
  py cal_dates.py conflicts events.json [--on YYYY-MM-DD] # 重なり・同日衝突を出す
  py cal_dates.py next-open YYYY-MM-DD --holidays H       # その日以降で最初に窓口が開く平日
  py cal_dates.py workdays  FROM TO      --holidays H     # 平日（土日祝を除く）の日数
  py cal_dates.py selftest
置き場: ~/.claude/skills/cal/scripts/cal_dates.py（標準ライブラリだけで動く）
events.json は MCP list_events の応答をそのまま保存した物（"-" で標準入力）。
H は祝日暦の list_events JSON か、`2026-10-12,2026-11-03` のようなカンマ区切り。
"""
from __future__ import annotations
import json
import sys
import argparse
from datetime import date, datetime, timedelta

# ---------- 入力の正規化 ----------


def _plain_date(v):
    """終日枠の date を拾う。MCP は `2026-10-10` と `2026-10-10T00:00:00Z` の両方を返す。
    後者を UTC として parse して JST に直すと +9h ずれて日付が翌日になるので、先頭10文字だけ見る。"""
    return date.fromisoformat(v[:10])


def _jst(v):
    """dateTime を JST の naive datetime にする。
    イベントの `timeZone` フィールドは当てにしない（旅程の名残で Asia/Ho_Chi_Minh のまま
    dateTime が +09:00 という実物があった）。オフセットは文字列側が正。"""
    d = datetime.fromisoformat(v.replace("Z", "+00:00"))
    if d.tzinfo is None:
        return d
    return (d - d.utcoffset()) + timedelta(hours=9)


def normalize(ev):
    """1件を {summary, all_day, first, last, start, end, transparent} に正す。
    first/last は **表示上の初日と最終日（両端含む）**。"""
    s = ev.get("start") or {}
    e = ev.get("end") or {}
    transparent = ev.get("transparency") == "transparent"
    summary = ev.get("summary", "(無題)")
    if "date" in s:
        first = _plain_date(s["date"])
        last = _plain_date(e["date"]) - timedelta(days=1) if "date" in e else first
        if last < first:  # 1日枠で end==start の壊れた枠を拾う
            last = first
        return {"summary": summary, "all_day": True, "first": first, "last": last,
                "start": None, "end": None, "transparent": transparent}
    if "dateTime" not in s:
        raise ValueError("start に date も dateTime も無い: %r" % (summary,))
    st = _jst(s["dateTime"])
    en = _jst(e["dateTime"]) if "dateTime" in e else st
    last = en.date()
    if en.time() == datetime.min.time() and last > st.date():
        last -= timedelta(days=1)  # 00:00 終了は前日までの表示
    return {"summary": summary, "all_day": False, "first": st.date(), "last": last,
            "start": st, "end": en, "transparent": transparent}


def load_events(path):
    raw = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
    d = json.loads(raw)
    if isinstance(d, dict):
        d = d.get("events", [])
    return [e for e in d if e.get("status") != "cancelled"]


def _days(n):
    d = n["first"]
    while d <= n["last"]:
        yield d
        d += timedelta(days=1)


def load_holidays(spec, observances=False):
    """閉庁日の集合。祝日暦の list_events JSON でも、カンマ区切りの日付でも受ける。

    `ja.japanese#holiday` には **祝日と祭日が混在している**（2026-09-28 に実データで確認）。
    description が「祝日」の物だけが休み。「祭日」は七五三 11/15・クリスマス 12/25 のような
    年中行事で、**役所も大学も開いている**。全件を休みにすると 12/25(金) を閉庁日と誤判定する。
    行事も数えたい時だけ observances=True。"""
    if not spec:
        return set()
    try:
        evs = load_events(spec)
    except (OSError, ValueError, json.JSONDecodeError):
        return {date.fromisoformat(x.strip()) for x in spec.split(",") if x.strip()}
    out = set()
    for ev in evs:
        desc = (ev.get("description") or "").strip()
        # description が空の暦（祝日暦以外を渡された時）は区別できないので全部数える
        if desc and not observances and not desc.startswith("祝日"):
            continue
        for d in _days(normalize(ev)):
            out.add(d)
    return out

# ---------- 平日計算 ----------


def is_open(d, holidays):
    """窓口が開く日か。土日と祝日は閉まっている（振替休日は祝日暦に入っているので別扱い不要）。"""
    return d.weekday() < 5 and d not in holidays


def next_open(d, holidays):
    while not is_open(d, holidays):
        d += timedelta(days=1)
    return d


def workdays(a, b, holidays):
    """a から b まで（両端含む）の開いている日数。a > b なら 0。"""
    if a > b:
        return 0
    n = 0
    d = a
    while d <= b:
        if is_open(d, holidays):
            n += 1
        d += timedelta(days=1)
    return n

# ---------- 衝突検出 ----------


def conflicts(norms, on=None):
    """同日に重なる組を返す。時刻が両方にあれば実際の重なりだけ、片方でも終日なら同日で報告。
    終日枠は時刻が書かれていないことが多く、本当に衝突するかは本人しか判定できない
    （2026-09-14 の学び）ので、ここでは「要確認」として出すに留める。"""
    out = []
    for i in range(len(norms)):
        for j in range(i + 1, len(norms)):
            a, b = norms[i], norms[j]
            lo = max(a["first"], b["first"])
            hi = min(a["last"], b["last"])
            if lo > hi:
                continue
            if on and not (lo <= on <= hi):
                continue
            if a["all_day"] or b["all_day"]:
                why = "同日（終日枠あり＝時刻不明・要確認）"
            elif a["start"] < b["end"] and b["start"] < a["end"]:
                why = "時刻が重なる"
            else:
                why = "同日（時間帯は重ならない）"
            out.append((a, b, lo, hi, why))
    return out

# ---------- 出力 ----------


def _fmt(n):
    if n["all_day"]:
        days = (n["last"] - n["first"]).days + 1
        tail = "" if days == 1 else "〜%s（%d日枠）" % (n["last"], days)
        mark = "  [transparent＝予定なし扱い]" if n["transparent"] else ""
        return "終日 %s%s %s%s" % (n["first"], tail, n["summary"], mark)
    if n["first"] == n["last"]:
        when = "%s %s〜%s" % (n["first"], n["start"].strftime("%H:%M"), n["end"].strftime("%H:%M"))
    else:
        when = "%s %s 〜 %s %s" % (n["first"], n["start"].strftime("%H:%M"),
                                  n["last"], n["end"].strftime("%H:%M"))
    return "%s %s" % (when, n["summary"])


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("span")
    q.add_argument("events")
    q = sub.add_parser("conflicts")
    q.add_argument("events")
    q.add_argument("--on")
    q = sub.add_parser("next-open")
    q.add_argument("day")
    q.add_argument("--holidays")
    q.add_argument("--observances", action="store_true",
                   help="祭日（七五三・クリスマス等）も休みとして数える。既定は祝日だけ")
    q = sub.add_parser("workdays")
    q.add_argument("frm")
    q.add_argument("to")
    q.add_argument("--holidays")
    q.add_argument("--observances", action="store_true")
    sub.add_parser("selftest")
    a = p.parse_args(argv)

    if a.cmd == "selftest":
        return selftest()
    if a.cmd == "span":
        norms = sorted((normalize(e) for e in load_events(a.events)),
                       key=lambda x: (x["first"], x["last"]))
        for n in norms:
            print(_fmt(n))
        return 0
    if a.cmd == "conflicts":
        on = date.fromisoformat(a.on) if a.on else None
        cs = conflicts([normalize(e) for e in load_events(a.events)], on)
        if not cs:
            print("衝突なし")
            return 0
        for x, y, lo, hi, why in cs:
            rng = str(lo) if lo == hi else "%s〜%s" % (lo, hi)
            print("⚠ %s: %s  ×  %s   [%s]" % (rng, x["summary"], y["summary"], why))
        return 1
    h = load_holidays(a.holidays, a.observances)
    if a.cmd == "next-open":
        d0 = date.fromisoformat(a.day)
        d1 = next_open(d0, h)
        gap = "" if d1 == d0 else "  ※%d日ずれる" % (d1 - d0).days
        print("%s → 次に開くのは %s (%s)%s" % (d0, d1, "月火水木金土日"[d1.weekday()], gap))
        return 0
    a0 = date.fromisoformat(a.frm)
    b0 = date.fromisoformat(a.to)
    print("%s〜%s の平日: %d日（土日祝を除く / 祝日 %d件を考慮）"
          % (a0, b0, workdays(a0, b0, h), len(h)))
    return 0

# ---------- selftest ----------


def selftest():
    state = {"ok": True}

    def eq(got, want, label):
        if got != want:
            state["ok"] = False
            print("NG  %s: got %r want %r" % (label, got, want))
        else:
            print("ok  %s" % label)

    # 実データ由来（2026-09-28 取得）: 終日枠の end は排他 → 最終日は 10/12
    n = normalize({"summary": "学会ボランティア", "transparency": "transparent",
                   "start": {"date": "2026-10-10T00:00:00Z"},
                   "end": {"date": "2026-10-13T00:00:00Z"}})
    eq((n["first"], n["last"]), (date(2026, 10, 10), date(2026, 10, 12)),
       "終日枠の排他 end（T00:00:00Z 形式）")
    eq(n["transparent"], True, "transparency:transparent を拾う")

    # 素の `2026-10-10` 形式でも同じ結果になること
    eq(normalize({"start": {"date": "2026-10-10"}, "end": {"date": "2026-10-13"}})["last"],
       date(2026, 10, 12), "終日枠の排他 end（素の date 形式）")

    # timeZone が dateTime のオフセットと食い違う実物（10/1・timeZone=Asia/Ho_Chi_Minh）
    n = normalize({"summary": "打ち合わせ",
                   "start": {"dateTime": "2026-10-01T18:00:00+09:00", "timeZone": "Asia/Ho_Chi_Minh"},
                   "end": {"dateTime": "2026-10-01T19:00:00+09:00", "timeZone": "Asia/Ho_Chi_Minh"}})
    eq((n["first"], n["start"].hour), (date(2026, 10, 1), 18),
       "timeZone より dateTime のオフセットを信じる")

    # UTC 表記は JST に直す
    eq(normalize({"start": {"dateTime": "2026-10-03T00:10:00Z"},
                  "end": {"dateTime": "2026-10-03T04:00:00Z"}})["start"].hour, 9, "UTC→JST 変換")

    # 00:00 終了は前日までの表示
    eq(normalize({"start": {"dateTime": "2026-10-01T22:00:00+09:00"},
                  "end": {"dateTime": "2026-10-02T00:00:00+09:00"}})["last"],
       date(2026, 10, 1), "00:00 終了は前日扱い")

    # 窓口: 2026-10-10(土)〜10-12(月・スポーツの日) の3連休 → 次に開くのは 10/13(火)
    h = {date(2026, 10, 12)}
    eq(next_open(date(2026, 10, 10), h), date(2026, 10, 13), "3連休明けの初日")
    eq(next_open(date(2026, 10, 13), h), date(2026, 10, 13), "開いている日はその日のまま")

    # 2026-09-19(土)〜09-23(水) の5連休（9/21 敬老・9/22 国民の休日・9/23 秋分）→ 9/24(木)
    h5 = {date(2026, 9, 21), date(2026, 9, 22), date(2026, 9, 23)}
    eq(next_open(date(2026, 9, 19), h5), date(2026, 9, 24), "5連休明けの初日")
    eq(workdays(date(2026, 9, 19), date(2026, 9, 25), h5), 2, "5連休を含む週の平日数")
    eq(workdays(date(2026, 10, 2), date(2026, 10, 1), h), 0, "逆順は0日")

    # 衝突: 学会ボランティア(10/10〜10/12 終日) と 懇親会(10/11 19:00)
    ev = [{"summary": "学会ボランティア", "start": {"date": "2026-10-10T00:00:00Z"},
           "end": {"date": "2026-10-13T00:00:00Z"}},
          {"summary": "懇親会", "start": {"dateTime": "2026-10-11T19:00:00+09:00"},
           "end": {"dateTime": "2026-10-11T20:00:00+09:00"}},
          {"summary": "無関係", "start": {"dateTime": "2026-11-01T10:00:00+09:00"},
           "end": {"dateTime": "2026-11-01T11:00:00+09:00"}}]
    cs = conflicts([normalize(e) for e in ev])
    eq(len(cs), 1, "衝突は1組だけ")
    eq(cs[0][4], "同日（終日枠あり＝時刻不明・要確認）", "終日絡みは要確認として出す")
    eq(len(conflicts([normalize(e) for e in ev], date(2026, 11, 1))), 0, "--on で日を絞れる")

    # 時刻が重なる/重ならないの区別
    ev2 = [{"summary": "A", "start": {"dateTime": "2026-10-05T10:00:00+09:00"},
            "end": {"dateTime": "2026-10-05T12:00:00+09:00"}},
           {"summary": "B", "start": {"dateTime": "2026-10-05T11:00:00+09:00"},
            "end": {"dateTime": "2026-10-05T13:00:00+09:00"}},
           {"summary": "C", "start": {"dateTime": "2026-10-05T13:00:00+09:00"},
            "end": {"dateTime": "2026-10-05T14:00:00+09:00"}}]
    kinds = sorted(c[4] for c in conflicts([normalize(e) for e in ev2]))
    eq(kinds, ["同日（時間帯は重ならない）", "同日（時間帯は重ならない）", "時刻が重なる"],
       "重なりと同日の区別")

    eq(len(load_holidays("2026-10-12,2026-11-03")), 2, "カンマ区切りの祝日指定")

    # 祝日暦には祭日（七五三・クリスマス）が混ざる。既定では休みに数えない
    import tempfile
    import os as _os
    hol = {"events": [
        {"summary": "スポーツの日", "description": "祝日", "status": "confirmed",
         "start": {"date": "2026-10-12T00:00:00Z"}, "end": {"date": "2026-10-13T00:00:00Z"}},
        {"summary": "クリスマス", "description": "祭日\n祭日を非表示にするには…", "status": "confirmed",
         "start": {"date": "2026-12-25T00:00:00Z"}, "end": {"date": "2026-12-26T00:00:00Z"}}]}
    fd, tmp = tempfile.mkstemp(suffix=".json")
    with _os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(hol, fh, ensure_ascii=False)
    try:
        eq(load_holidays(tmp), {date(2026, 10, 12)}, "祭日（クリスマス）は休みに数えない")
        eq(len(load_holidays(tmp, observances=True)), 2, "--observances なら祭日も数える")
        # 2026-12-25 は金曜。祭日を休みにすると窓口の判定を3日間違える
        eq(next_open(date(2026, 12, 25), load_holidays(tmp)), date(2026, 12, 25),
           "12/25(金) は開庁日のまま")
    finally:
        _os.unlink(tmp)

    print("\n%s" % ("全部通った" if state["ok"] else "失敗あり"))
    return 0 if state["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
