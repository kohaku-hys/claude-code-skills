#!/usr/bin/env python3
"""Regression tests for deck_doctor.py (2026-07-05 導入・fable改良):
- 壊れデッキ: 注釈残留/フッター不整合/ノート割当なし = ERROR、
  禁則・数字割れ・はみ出し・文字かぶり・dy大見出し = WARNING を全部検出する
- クリーンデッキ: ERROR 0 / WARNING 0、exit 0
- exit code: 壊れ=1 / クリーン=0 / クリーン+--strict でも 0
- 2026-09-28 v2: 中身の検査（C1〜C6・R0）・形の検査（F1〜F8）・T1x（人の言葉は100字の目安で数えない）。
  クリーンデッキには証拠の台帳（brief.json・素材・inventory・照合の記録）を足した（無いと C1/R0 で止まるのが正しい）
- 2026-09-28 v3: 目次 A（A0〜A3）・資料の種類 genre（G1〜G9。ジャンルごとの ON/OFF の表）・引用の組み方（Q1・Q2）・
  tspan に割れた引用の F7。見本は表紙に報告日・人の言葉と数字の枚に ※ の行・ノートにお願い（cta）を足し、
  spec_lock に agenda: none（試験用の5枚。目次の試験は別に組む）を書いた
- 2026-10-01: 意味の検査 M1〜M6・R1、続けて yomiyasu（MIT・Copyright (c) 2026 nanaism）の語の一覧から言い回しを直して
  移した型（M5 の追加・M7 前置き・M8 絵文字・M9 行の終わりのコロン・F2 の「単なる〜ではない」・締めの決まり文句）。
  型ごとに当たる例と、同じ語を物の話で使った当たらない例を1組以上置く。
  同日の反証で3件を直した: M9 は予告の語がある行か、述語でコロンの直前が終わる行だけ（名詞の見出し語「入力：」は
  人のスライドで普通）・
  決まり文句の検査で外す「」は brief.json の逐語の証拠だけ（「」で囲むだけでは抜けない）・M7 は箇条書きの行の頭も見る
- 2026-10-01 2回目: 3つの検査器で共通の試験集（CORPUS＝作者の環境の文章用スキルにある tests/ai_smell_cases.json。このリポジトリには含まれず、無ければ SKIP）のスライドに当てはまる全件を
  種別ごとに確かめる（期待を争った2件は CORPUS_DISPUTED に出した期待で）。親の判断で直した物: 決め台詞（〜に他ならない・
  〜というわけだ）は ERROR から WARNING へ（前の「→ ERROR」の試験3つをこの決めに合わせて書き換えた）・M1・M3 も箇条書きの
  2行目より後の行の頭を見る・比喩（M5）は「抽象的な物が主語・目的語の時だけ拾う」原理で書き直した。M10 ダッシュ・M11 読点の
  打ちすぎを足した。続きで、崩れる の「計画が崩れる（辞書に載る意味）」「数と単位で書いた条件」を文章の検査器とそろえ、
  締めの「〜てみてはいかが」を し＋てみて 以外にも広げた
- 2026-10-01 3回目の反証: 語の一覧でなく原理でそろえた直しを、本人・先生・旧PCの人の文と資料の型の組で確かめる
  （M5 は動詞の相手の最後の語が抽象の時だけ・抽象の一覧は文章の検査器と同じ語の集合、M3 は名詞＋を・が・比べる より と
  は＋言い切らない文だけ、F2 の より は比べる より だけ、M1・M2・M4・M7・M9・M10・M11・決まり文句の誤検知と取りこぼし）
- 2026-10-01 4回目: 試験集に足した290件（全部で789件。スライドに当てはまるのは721件）に合わせて直した。直し方は文章の検査器
  文章の検査器の同じ規則に揃えた（決まり文句の誘い・幸い、M1 の評価の否定・存在の否定、M2 の1文の中の対句、M3 の時・条件の節、
  M4 の「〜を片方」、M5 の名札・静かに＋動詞・効く・溶かす・たどり着く・土台になる・落とし穴、M7 の型、M9 の接続の語・コマンド、
  M10 の名詞をつなぐダッシュ、F2 の否定の後の読点）。人の文の母集団で見つけた文を「4回目」の試験に置いた。
  共通の抽象の語の一覧に無い語（ばらつき・測定・知見・挙動）が要る4件は、一覧を2つの検査器で一緒に直すまで落ちる
- 2026-10-01 5回目（裁定の後）: 裁定は「争う件なし・抽象の語の一覧は変えない」だった。4件のうち「チームの知見を資産として
  積み上げる。」は、文章の検査器が同じ文を当てている規則（〜を〜として積み上げる）を移して直した。残りの3件（ばらつき・測定・
  挙動）は、文章の検査器も当てておらず、直すには共通の一覧に語を足すしかないので、既知の限界（KNOWN_LIMITS）に理由つきで置いた。
  既知の限界の件は、試験集の期待と違う結果のままであることを確かめる（一覧を直して当たるようになったら、一覧から外せと落ちる）
- 2026-10-01 6回目: 今日の前の版（git d6f2b634）と比べて人の文で増えた誤検知を直した回帰。本人の判断「① 参考の扱いにする」で
  落とし込む・架け橋・刺さる だけで当たる文は INFO の M5参考（前の「落とし込む → M5 が出る」の試験はこの決めに合わせて移した）。
  旧PCにあった班発表の pptx の M1・M2、実験のプレレポートの「片方が鰐口クリップの線」の M4、式が抜けた写しの M3・M11、
  経済学入門の「次の経済を考える：」の M9 と比較生産費説の M1、個人レポートの「ただ、これだと」の M1

Run:  py test_deck_doctor.py   (exit 0 = pass)
"""
import contextlib
import copy
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

BASE = Path.home()
# deck_doctor.py は slide-gen の scripts に同梱してある（この tests の1つ上。上流の ppt-master には無い）
SK = Path(__file__).resolve().parent.parent
DOCTOR = SK / "deck_doctor.py"
CLAIMS = Path(__file__).resolve().parent.parent / "claims.py"
sys.path.insert(0, str(SK))
import deck_doctor as dd  # noqa: E402  content_hash を試験でも同じ計算で出す

results = []
def check(name, ok, detail=""):
    results.append(ok)
    print("[%s] %s%s" % ("PASS" if ok else "FAIL", name, (" :: " + detail) if detail else ""))

SVG_HEAD = '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">'
FOOTER = ('<g id="footer"><text x="1200" y="700" text-anchor="end" font-family="Yu Gothic" '
          'font-size="14" fill="#3A4452"><tspan font-weight="bold">%d</tspan> / %d</text></g>')

CLEAN = [
    SVG_HEAD + '<g id="t"><text x="640" y="320" text-anchor="middle" font-family="Yu Gothic" '
    'font-size="48" fill="#1F4E79">表紙タイトル</text>'
    '<text x="640" y="400" text-anchor="middle" font-family="Yu Gothic" font-size="24">2026年9月28日</text></g>'
    + FOOTER % (1, 2) + '</svg>',
    SVG_HEAD + '<g id="m"><text x="80" y="240" font-family="Yu Gothic" font-size="24" '
    'fill="#3A4452">本文は 9.9% を同じ行に。</text></g>' + FOOTER % (2, 2) + '</svg>',
]

BROKEN = [
    # 1枚目: 注釈残留 + dy大見出し + 禁則 + はみ出し + 重なり
    SVG_HEAD
    + '<g id="h"><text x="80" y="100" font-family="Yu Gothic" font-size="40" '
    'data-edit-target="true" data-edit-annotation="x">見出し折返し'
    '<tspan x="80" dy="52">悪い例</tspan></text></g>'
    '<g id="b"><text x="80" y="280" font-family="Yu Gothic" font-size="24">。行頭句点</text>'
    '<text x="80" y="320" font-family="Yu Gothic" font-size="24">%行頭単位</text>'
    '<text x="80" y="380" font-family="Yu Gothic" font-size="28">'
    'とても長い行でキャンバスの右端を大きく超えることを検出させるための全角テキストの例文です</text>'
    '<text x="200" y="460" font-family="Yu Gothic" font-size="30">重なりテキストA いろは</text>'
    '<text x="240" y="470" font-family="Yu Gothic" font-size="30" id="_edit_3">重なりテキストB にほへ</text></g>'
    + FOOTER % (5, 9) + '</svg>',
    # 2枚目: フッターは正しいが total.md にノートが無い
    SVG_HEAD + '<g id="m"><text x="640" y="340" text-anchor="middle" font-family="Yu Gothic" '
    'font-size="40">まとめ</text></g>' + FOOTER % (2, 2) + '</svg>',
]


def make_project(dirpath, svgs, total_md=None, spec_lock=None):
    out = Path(dirpath) / "svg_output"
    out.mkdir(parents=True)
    for i, content in enumerate(svgs, 1):
        (out / ("%02d_page.svg" % i)).write_text(content, encoding="utf-8")
    if total_md is not None:
        notes = Path(dirpath) / "notes"
        notes.mkdir()
        (notes / "total.md").write_text(total_md, encoding="utf-8")
    if spec_lock is not None:
        (Path(dirpath) / "spec_lock.md").write_text(spec_lock, encoding="utf-8")


def run_doctor(proj, *extra):
    return subprocess.run([sys.executable, str(DOCTOR), str(proj)] + list(extra),
                          capture_output=True, text=True, encoding="utf-8")


def add_ledger(dirpath, brief, memo, inventory, evidence="PASS", reader="PASS"):
    """証拠の台帳一式（brief.json・sources/memo.md・inventory）と、照合の記録（evidence_check 行）・
    初見の読み手の記録（reader_check 行。2026-10-01 R1）を足す。
    記録は最後に書く（hash は SVG とノートを全部書いた後の中身で取る）。"""
    p = Path(dirpath)
    (p / "sources").mkdir(exist_ok=True)
    (p / "sources" / "memo.md").write_text("\n".join(memo) + "\n", encoding="utf-8")
    if inventory is not None:
        (p / "sources" / "inventory.md").write_text(inventory, encoding="utf-8")
    if brief is not None:
        (p / "brief.json").write_text(json.dumps(brief, ensure_ascii=False, indent=1), encoding="utf-8")
    if evidence:
        with open(p / "spec_lock.md", "a", encoding="utf-8") as fh:
            fh.write("evidence_check: %s 2026-09-28 hash=%s report=review/evidence_check.md\n"
                     % (evidence, dd.content_hash(p)))
    if reader:
        with open(p / "spec_lock.md", "a", encoding="utf-8") as fh:
            fh.write("reader_check: %s 2026-10-01 hash=%s report=review/reader_check.md\n"
                     % (reader, dd.content_hash(p)))


def TX(x, y, fs, s, extra=""):
    return '<text x="%d" y="%d" font-family="Yu Gothic" font-size="%d"%s>%s</text>' % (x, y, fs, extra, s)


def S(head, body=(), eyebrow=None, extra="", hfs=48):
    """1枚の中身: 小ラベル（28px・y=120）→ 見出し（48px・y=200）→ 本文（32px・y=300 から50px おき）＋任意の図形。"""
    s = ""
    if eyebrow:
        s += TX(96, 120, 28, eyebrow)
    s += TX(96, 200, hfs, head)
    for k, b in enumerate(body):
        s += TX(96, 300 + 50 * k, 32, b)
    return s + extra


# --- 中身の検査の見本（C 1 / P 2 / R 3 / E 4 / P 5）。これが ERROR 0・WARNING 0 で通ることが基準 ---
GOOD_SLIDES = [
    S("東湖で見た半導体の熱意", ["山田 太郎　2026年9月28日"]),                       # G7: 表紙に報告日
    S("留学生の一言で、東湖の熱意を知った", ["「半導体のやる気全員の」", "※3日目の夜の研修メモから"]),   # G3a: ※
    S("教える側も学ぶ側も、熱意で動いた", ["講義4コマ・見学2か所を1日で", "※8月17日の研修メモから"]),   # G3b: ※
    S("8月18日、食堂で聞いた一言", ["「進路を考えて行動しただけ」", "※8月18日、食堂で日本人留学生から"]),
    S("8月18日の一言で、来年の挑戦を決めた", ["講義は4コマ・見学は2か所"]),
]
GOOD_NOTES = [
    "（約30秒）工学部2年の山田太郎です。8月に海外の東湖工科大学で6日間の研修に参加しました。今日はその報告をします。",
    "（約40秒）結論から言います。3日目の夜、メモに「半導体のやる気全員の」と書きました。周りの全員が半導体に本気でした。",
    "（約50秒）" + "TKRIでは午前のうちに講義4コマと見学2か所を回りました。教える側は質問に全部答えてくれて、学ぶ側も最後まで手を挙げ続けていました。" * 3,
    "（約50秒）" + "8月18日の夕方、食堂で日本人の留学生と話しました。進路のことを聞くと、大したことはしていないと笑っていました。その人の熱意が伝わりました。" * 3,
    "（約40秒）最後にもう一度。8月18日の一言で、来年の挑戦を決めました。長期のプログラムにも挑戦したいと思っています。"
    "来年の募集に応募してほしいです。",   # G4a: お願い（cta）を最後の P のノートに
]
GOOD_MEMO = [
    "# 研修メモ",
    "## 3日目（8月18日）",
    "> 進路を考えて行動しただけ、と言っていた",
    "- 場面: 8月18日の夕方、食堂で留学生と話した",
    "> 半導体のやる気全員の",
    "- 数: 講義は4コマ・見学は2か所",
    "> 長期のプログラムにも挑戦したい",
    "## 感想",
    "- 印象: 熱意がすごかった",
    "- おわり",
]
GOOD_INV = "# 候補\n- E1 V memo.md:3\n- E2 V memo.md:5\n- E3 N memo.md:6\n- A1 A memo.md:9\n- D1 図 講義資料.pdf:3\n"
GOOD_BRIEF = {
    "brief_version": 2, "how": "選択式", "audience": "学生支援室への研修報告・10分",
    "p": "留学生の一言で、東湖の熱意を知った", "p_core": ["熱意"],
    "p_last": "8月18日の一言で、来年の挑戦を決めた",
    "r": [{"id": "R1", "claim": "教える側も学ぶ側も本気だった", "slides": [3]}],
    "proof": [
        {"id": "E1", "for": "R1", "kind": "verbatim", "src": "memo.md:3", "quote": "進路を考えて行動しただけ", "slides": [4]},
        {"id": "E2", "for": "P", "kind": "verbatim", "src": "memo.md:5", "quote": "半導体のやる気全員の", "slides": [2]},
        {"id": "E3", "for": "P", "kind": "number", "src": "memo.md:6", "quote": "講義は4コマ・見学は2か所", "slides": [5]},
    ],
    "me": {"why": "同世代の行動に背中を押された", "scene": {"src": "memo.md:7", "quote": "長期のプログラムにも挑戦したい"},
           "next": "英語を増やす"},
    "sources_read": [{"path": "sources/memo.md", "lines": 10, "read": "1-10", "verbatim": 3,
                      "inventory": "sources/inventory.md"}],
    "cta": "来年の募集に応募してほしい", "ng": [],
    "prep": "C 1 / P 2 / R 3 / E 4 / P 5",
}


AGENDA_NONE = "agenda: none 2026-09-28 本人 試験用の5枚の見本（目次の試験は別に組む）\n"


def spec_v2(prep="C 1 / P 2 / R 3 / E 4 / P 5", extra="", agenda=AGENDA_NONE):
    return ("# Spec Lock\n- delivery: presentation\nbrief_confirmed: 2026-09-28 選択式\nbrief_version: 2\n"
            "prep: %s\n%s%s" % (prep, agenda, extra))


OLD_SPEC = ("# Spec Lock\n- delivery: presentation\nbrief_confirmed: 2026-09-28 選択式\n"
            "brief:\n  p: 人の熱意だった\n  r: 教える側の熱量\n  e: 研修メモ 84行\n"
            "prep: C 1 / P 2 / R 3 / E 4 / P 5\n")


def good_parts():
    return {"slides": list(GOOD_SLIDES), "notes": list(GOOD_NOTES), "brief": copy.deepcopy(GOOD_BRIEF),
            "memo": list(GOOD_MEMO), "inventory": GOOD_INV, "spec": spec_v2(), "evidence": "PASS"}


# --- 3つの検査器で共通の試験集（2026-10-01。作者の環境の文章用スキルの scripts/tests にある。読むだけで書き換えない。
# このリポジトリには含まれないので、無ければ下の試験集の段は SKIP と出して飛ばす） ---
# かけ方は試験集の about のとおり: 1行目を見出し（48px）、2行目より後を1つの <text> の tspan の行（32px）にして、
# 見本のデッキ（good_parts）の3枚目に入れて流す。見本だけで出る指摘は差し引く。期待 hit＝その種別の規則が WARNING か ERROR を出す
CORPUS = Path.home() / ".claude" / "skills" / "humanize" / "scripts" / "tests" / "ai_smell_cases.json"
CORPUS_RULES = {   # 種別 → deck_doctor の指摘の頭
    "neg_then_pos": ["M1 "], "swap": ["M2 "], "tame": ["M3 "], "vague_ref": ["M4 "], "nominal": ["M6 "],
    "preface": ["M7 "], "emoji": ["M8 "], "colon_end": ["M9 "], "dash": ["M10 "], "many_commas": ["M11 "],
    "simply_not": ["F2 "], "closing": ["AIくさい決まり文句"], "kimezerifu": ["AIくさい決まり文句", "AIくさい語の疑い"],
    "ai_copy": ["AIくさい決まり文句", "AIくさい語の疑い"],
}
for _f in ("B1", "B2", "B3", "B4", "B5", "B6", "B12", "B13", "metaphor_other"):
    CORPUS_RULES[_f] = ["M5 "]
# 試験集の期待が違うと考えて最後の段に出した物（試験集は書き換えない）。ここでは出した期待（提案）で確かめる
# 2026-10-01 4回目: 前に争った tame-miss-25・26 は、試験集の仕上げの裁定で slides=hit に直り、id が tame-hit-11・12 に変わった
# （試験集の期待と同じになった）ので消した。今は争う件は無い（5回目の裁定の後も空のまま）
CORPUS_DISPUTED = {}
# 既知の限界: 試験集の期待どおりには直さない件（id: 理由）。試験集のスライドに当てはまる件数の3%以下に収める。
# ここの件は「期待と違う今の結果のまま」であることを確かめる（直ったら一覧から外す）。理由は報告の not_fixed にも書く。
# 2026-10-01 5回目: 3件とも、動詞の相手の名詞が共通の抽象の語の一覧（M_ABSTRACT_INFO・M_ABSTRACT_IDEA。文章の検査器の
# ABSTRACT_INFO・ABSTRACT_IDEA と同じ語の集合）に無いので当たらない。直すには一覧に語を足すしかないが、
# この段の裁定は「一覧は変えない」で、片方だけ足すと下の「抽象の語の一覧が文章の検査器と同じ」の試験が落ち、2つの検査器の
# 判定がずれる。文章の検査器も同じ3件を当てていない。語を足しても人の文の当たりが増えないことは4回目に測った
# （人の文の約8.9万単位・過去のデッキ24個・文章の検査器にかけた .md 1160本で、どれも0件）
# 2026-10-01 親（CEO）の判断: 4語（測定・現象・挙動・ばらつき）を文章とスライドの両方の一覧に足した（裁定役に提案が届いて
# いなかったワークフローの不具合を、親が直した）。3件とも期待どおりになったので空にした
KNOWN_LIMITS = {}
# B6-miss-10「台風で旅行の計画が崩れた」・B6-miss-11「1GHzでは集中定数の前提が崩れる」は、前は争ったが、文章の検査器
# （COLLOC_KUZURE・_judge_collapse）と同じ原理（計画が崩れる＝辞書に載る意味・数と単位で書いた条件）で
# deck_doctor を直したので、試験集の期待どおり miss で確かめる


def corpus_slide(text):
    """試験集の text を3枚目の中身（見出し＋本文の tspan の行）にする。"""
    rows = [r.strip() for r in text.split("\n") if r.strip()]
    s = TX(96, 200, 48, xml_escape(rows[0]))
    if rows[1:]:
        s += '<text x="96" y="300" font-family="Yu Gothic" font-size="32">%s' % xml_escape(rows[1])
        s += "".join('<tspan x="96" dy="50">%s</tspan>' % xml_escape(r) for r in rows[2:]) + "</text>"
    return s


def main():
    tmp = Path(tempfile.mkdtemp(prefix="deck_doctor_test_"))
    try:
        # --- 壊れデッキ ---
        broken = tmp / "broken"
        make_project(broken, BROKEN,
                     "# Speaker Notes\n\n## Slide 1: 表紙\n\n1枚目のノート。\n")  # 2枚目のノート無し
        r = run_doctor(broken, "--json")
        check("broken: exit 1", r.returncode == 1, "exit=%d" % r.returncode)
        d = json.loads(r.stdout)
        msgs = " | ".join(i["severity"] + ":" + i["message"] for i in d["issues"])
        check("broken: 注釈残留 ERROR", any(
            i["severity"] == "ERROR" and "注釈" in i["message"] for i in d["issues"]))
        check("broken: フッター不整合 ERROR", any(
            i["severity"] == "ERROR" and "フッター" in i["message"] for i in d["issues"]))
        check("broken: ノート割当なし ERROR", any(
            i["severity"] == "ERROR" and "ノートが割り当たらない" in i["message"] for i in d["issues"]))
        check("broken: 行頭禁則 WARNING", any("行頭禁則" in i["message"] for i in d["issues"]))
        check("broken: 数字割れ WARNING", any("数字割れ" in i["message"] for i in d["issues"]))
        check("broken: はみ出し WARNING", any("はみ出し" in i["message"] for i in d["issues"]))
        check("broken: 文字かぶり WARNING", any("文字かぶり" in i["message"] for i in d["issues"]))
        check("broken: dy大見出し WARNING", any("dy 複数行" in i["message"] for i in d["issues"]),
              msgs[:200])

        # --- クリーンデッキ ---
        clean = tmp / "clean"
        # 2026-09-28 から delivery 未記載でも話す型検査が走るので、読ませる型の見本は document と明記する
        make_project(clean, CLEAN,
                     "# Speaker Notes\n\n## Slide 1: 表紙\n\nノート1。\n\n## Slide 2: まとめ\n\nノート2。\n",
                     "# Spec Lock\n- delivery: document\n- prep: C 1 / P 2\nbrief_confirmed: 2026-09-28 選択式\n")
        # 2026-09-28 v2: クリーン＝証拠の台帳と照合の記録もそろっている状態（2枚なので結論の証拠2件だけを見る）
        add_ledger(clean, {
            "brief_version": 2, "how": "選択式", "p": "表紙タイトルで9.9%を示す", "p_core": ["9.9%"],
            "p_last": "本文は9.9%を同じ行に置く", "r": [{"id": "R1", "claim": "数字は同じ行", "slides": []}],
            "proof": [{"id": "E1", "for": "P", "kind": "number", "src": "memo.md:1", "quote": "9.9%", "slides": [2]},
                      {"id": "E2", "for": "P", "kind": "verbatim", "src": "memo.md:2", "quote": "本文は", "slides": [2]}],
            "me": {"scene": {"src": "memo.md:3", "quote": "表紙タイトル"}},
            "sources_read": [{"path": "sources/memo.md", "lines": 3, "read": "1-3", "verbatim": 2,
                              "inventory": "sources/inventory.md"}],
            "cta": "", "prep": "C 1 / P 2"},
            ["- 数: 9.9%", "> 本文は同じ行に", "> 表紙タイトル"], "- E1\n- E2\n")
        r = run_doctor(clean, "--json")
        d = json.loads(r.stdout)
        check("clean: exit 0", r.returncode == 0, "exit=%d" % r.returncode)
        check("clean: ERROR 0", d["errors"] == 0,
              " | ".join(i["message"] for i in d["issues"] if i["severity"] == "ERROR"))
        check("clean: WARNING 0", d["warnings"] == 0,
              " | ".join(i["message"] for i in d["issues"] if i["severity"] == "WARNING"))
        r = run_doctor(clean, "--strict")
        check("clean --strict: exit 0", r.returncode == 0, "exit=%d" % r.returncode)

        # --- 話す型検査（delivery=presentation で自動ON） ---
        yomudake = (
            SVG_HEAD + '<g id="b">'
            + '<text x="80" y="80" font-family="Yu Gothic" font-size="24">読むだけスライドの長い説明タイトル行</text>'
            + "".join(
                '<text x="80" y="%d" font-family="Yu Gothic" font-size="16">'
                '説明文をそのまま貼り付けた本文で四十字ぶんほどの長さの行がここに延々と続いている例</text>' % y
                for y in range(140, 380, 30))
            + '</g>' + FOOTER % (1, 2) + '</svg>')
        hanasu = (
            SVG_HEAD
            + '<g id="h"><text x="80" y="110" font-family="Yu Gothic" font-size="44" font-weight="bold">'
              '言い切りの大見出し。</text></g>'
            '<g id="n"><text x="320" y="420" text-anchor="middle" font-family="Yu Gothic" '
            'font-size="120" font-weight="bold">2.6%</text>'
            '<text x="320" y="480" text-anchor="middle" font-family="Yu Gothic" font-size="24">ラベル</text></g>'
            '<g id="c"><rect x="640" y="300" width="420" height="60" fill="#1F4E79"/>'
            '<rect x="640" y="400" width="120" height="60" fill="#B5462E"/>'
            '<text x="640" y="280" font-family="Yu Gothic" font-size="22">比較 約25%</text>'
            '<text x="640" y="500" font-family="Yu Gothic" font-size="22">主役 2.6%</text></g>'
            '<g id="s"><text x="80" y="690" font-family="Yu Gothic" font-size="12">出典：テスト</text></g>'
            + FOOTER % (2, 2) + '</svg>')
        talk = tmp / "talk"
        make_project(talk, [yomudake, hanasu],
                     "# Notes\n\n## Slide 1: a\n\nn1\n\n## Slide 2: b\n\nn2\n",
                     "# Spec Lock\n- delivery: presentation\n")
        r = run_doctor(talk, "--json")
        d = json.loads(r.stdout)
        w1 = [i["message"] for i in d["issues"] if i["file"] == "01_page.svg" and i["severity"] == "WARNING"]
        w2 = [i["message"] for i in d["issues"] if i["file"] == "02_page.svg" and i["severity"] == "WARNING"]
        check("talk: 自動ON (INFO)", any("話す型検査 ON" in i["message"] for i in d["issues"]))
        check("talk: 読むだけ枚に文字数過多", any("読むだけ" in m or "字" in m for m in w1), " | ".join(w1)[:120])
        check("talk: 読むだけ枚に小さい文字", any("未満の本文" in m for m in w1))
        check("talk: 読むだけ枚に視覚アンカー無し", any("テキストだけ" in m for m in w1))
        check("talk: 良い枚は警告ゼロ（大数字=アンカー）", not w2, " | ".join(w2)[:120])
        r = run_doctor(talk, "--no-talk", "--json")
        d = json.loads(r.stdout)
        check("talk --no-talk: 話す型警告ゼロ",
              not any("話す型" in i["message"] and i["severity"] == "WARNING" for i in d["issues"]))

        # --- T3 行数過多 / T5 小画像 / T6 見出し不在 / --talk 強制ON（spec_lock 無し） ---
        many_lines = (
            SVG_HEAD + '<g id="b">'
            + "".join(
                '<text x="80" y="%d" font-family="Yu Gothic" font-size="24">項目%02d</text>' % (80 + i * 44, i)
                for i in range(13))
            + '</g>' + FOOTER % (1, 2) + '</svg>')
        small_img = (
            SVG_HEAD
            + '<g id="h"><text x="80" y="110" font-family="Yu Gothic" font-size="30">小さすぎる写真の枚</text></g>'
            '<g id="p"><image x="80" y="200" width="200" height="130" href="images/x.jpg"/></g>'
            + FOOTER % (2, 2) + '</svg>')
        talk2 = tmp / "talk2"
        make_project(talk2, [many_lines, small_img])  # spec_lock 無し → 既定の話す型で ON
        r = run_doctor(talk2, "--json")
        d = json.loads(r.stdout)
        talk_warns = [i for i in d["issues"] if "話す型" in i["message"] and i["severity"] == "WARNING"]
        check("talk2 spec_lock無し: 既定で話す型検査が走る（2026-09-28〜）", bool(talk_warns))
        check("talk2 spec_lock無し: 既定ON を INFO で可視化",
              any("既定の話す型" in i["message"] and i["severity"] == "INFO" for i in d["issues"]))
        r = run_doctor(talk2, "--talk", "--json")
        d = json.loads(r.stdout)
        w1 = [i["message"] for i in d["issues"] if i["file"] == "01_page.svg"]
        w2 = [i["message"] for i in d["issues"] if i["file"] == "02_page.svg"]
        check("talk2 --talk: 強制ON (INFO)", any("--talk 指定" in i["message"] for i in d["issues"]))
        check("talk2: T3 行数過多", any("行と多い" in m for m in w1), " | ".join(w1)[:100])
        check("talk2: T6 見出し不在（最大24px）", any("最大文字サイズ" in m for m in w1))
        check("talk2: T5 画像が小さい（唯一のアンカー）", any("唯一の図" in m for m in w2), " | ".join(w2)[:100])

        # === レビュー確定指摘の回帰ケース（fable/opus レビュー 2026-07-05） ===
        # 確定②: 極小(≤12px)文字だけの読むだけスライドが検査をすり抜けない
        micro = (
            SVG_HEAD + '<g id="b">'
            + "".join(
                '<text x="80" y="%d" font-family="Yu Gothic" font-size="12">'
                '極小の説明文をびっしり並べた読むだけスライドの行がここに延々と続く四十字級の本文</text>' % (80 + i * 22)
                for i in range(10))
            + '</g>' + FOOTER % (1, 1) + '</svg>')
        micro_p = tmp / "micro"
        make_project(micro_p, [micro], spec_lock="# Spec Lock\n- delivery: presentation\n")
        d = json.loads(run_doctor(micro_p, "--json").stdout)
        mw = [i["message"] for i in d["issues"] if i["severity"] == "WARNING"]
        check("確定②: 12px本文の読むだけ枚を検出（逆転解消）",
              any("字" in m for m in mw) and any("未満の本文" in m for m in mw), " | ".join(mw)[:120])

        # 確定①: svg_output/ を直接渡しても delivery を親から検出し話す型検査が走る
        d = json.loads(run_doctor(micro_p / "svg_output", "--json").stdout)
        check("確定①: svg_dir 直接指定でも話す型検査 ON",
              any("話す型検査 ON" in i["message"] for i in d["issues"]))

        # 確定③: 大文字 "Delivery:" でも自動ON（大文字小文字非依存）
        cap_p = tmp / "cap"
        make_project(cap_p, [micro], spec_lock="# Spec Lock\n- Delivery: Presentation\n")
        d = json.loads(run_doctor(cap_p, "--json").stdout)
        check("確定③: 大文字 Delivery でも自動ON",
              any("話す型検査 ON" in i["message"] for i in d["issues"]))

        # 確定④: チャート(path)がある枚の小さいロゴでは T5 を出さない
        chart_logo = (
            SVG_HEAD
            + '<g id="h"><text x="80" y="110" font-family="Yu Gothic" font-size="40">主役の折れ線チャート</text></g>'
            '<g id="c"><path d="M100 400 L300 350 L500 380 L700 300 L900 320 L1100 280" '
            'stroke="#1F4E79" fill="none" stroke-width="3"/>'
            '<rect x="100" y="450" width="1000" height="4" fill="#3A4452"/></g>'
            '<g id="logo"><image x="1150" y="40" width="80" height="80" href="images/logo.png"/></g>'
            + FOOTER % (1, 1) + '</svg>')
        cl_p = tmp / "chart_logo"
        make_project(cl_p, [chart_logo], spec_lock="# Spec Lock\n- delivery: presentation\n")
        d = json.loads(run_doctor(cl_p, "--json").stdout)
        check("確定④: チャート枚の小ロゴで T5 誤報しない",
              not any("画像がキャンバス" in i["message"] for i in d["issues"]),
              " | ".join(i["message"] for i in d["issues"] if i["severity"] == "WARNING")[:120])

        # 安全ガード: full-bleed 画像(width=100%)を極小と誤認しない
        fullbleed = (
            SVG_HEAD
            + '<g id="bgimg"><image x="0" y="0" width="100%" height="100%" href="images/bg.jpg"/></g>'
            '<g id="h"><text x="80" y="110" font-family="Yu Gothic" font-size="44">全面写真の上に見出し</text></g>'
            + FOOTER % (1, 1) + '</svg>')
        fb_p = tmp / "fullbleed"
        make_project(fb_p, [fullbleed], spec_lock="# Spec Lock\n- delivery: presentation\n")
        d = json.loads(run_doctor(fb_p, "--json").stdout)
        check("安全ガード: 100%画像を小さいと誤報しない",
              not any("画像がキャンバス" in i["message"] for i in d["issues"]))

        # --- 2026-09-28「文字が小さい・AIくさい・シンプルじゃない」で足した ERROR 群 ---
        def one(body_svg, spec="# Spec Lock\n- delivery: presentation\n"):
            p = tmp / ("s%d" % len(results))
            make_project(p, [SVG_HEAD + body_svg + FOOTER % (1, 1) + '</svg>'], spec_lock=spec)
            return json.loads(run_doctor(p, "--json").stdout)

        def errs(d):
            return [i["message"] for i in d["issues"] if i["severity"] == "ERROR"]

        H = '<text x="80" y="110" font-family="Yu Gothic" font-size="48">言い切りの見出し</text>'
        d = one(H + '<text x="80" y="300" font-family="Yu Gothic" font-size="18">小さすぎる本文</text>')
        check("新: 22px未満の本文は1行でも ERROR", any("px 未満の本文がある" in m for m in errs(d)))
        d = one(H + '<text x="80" y="690" font-family="Yu Gothic" font-size="12">出典：総務省 2025</text>')
        check("新: 出典の小さい字は ERROR にしない", not any("px 未満" in m for m in errs(d)), " | ".join(errs(d)))
        d = one(H + "".join('<text x="80" y="%d" font-family="Yu Gothic" font-size="28">項目%d</text>' % (160 + i * 36, i)
                            for i in range(13)))
        check("新: 読む場所13個は ERROR", any("読む場所" in m for m in errs(d)))
        d = one(H + '<text x="80" y="300" font-family="Yu Gothic" font-size="32">町家はこうして傷んでいきます</text>')
        check("新: です・ます調は ERROR", any("です・ます調" in m for m in errs(d)))
        d = one('<text x="80" y="300" font-family="Yu Gothic" font-size="60">ご清聴ありがとうございました</text>')
        check("新: 謝辞スライドの敬語は許す", not any("です・ます調" in m for m in errs(d)), " | ".join(errs(d)))
        d = one(H + "".join('<text x="80" y="%d" font-family="Yu Gothic" font-size="28">%s</text>' % (200 + i * 40, "あ" * 40)
                            for i in range(4)))
        check("新: 150字超は ERROR", any("読むだけスライド" in m for m in errs(d)))
        d = one(H + '<text x="80" y="300" font-family="Yu Gothic" font-size="32">無限の可能性を秘めた技術</text>',
                spec="# Spec Lock\n- delivery: document\n")
        check("新: 決まり文句は読ませる型でも ERROR", any("決まり文句" in m for m in errs(d)))
        d = one(H + '<text x="80" y="300" font-family="Yu Gothic" font-size="32">現場の作業を最適化</text>')
        check("新: 文脈次第の語は WARNING どまり",
              not any("決まり文句" in m for m in errs(d))
              and any("AIくさい語の疑い" in i["message"] for i in d["issues"] if i["severity"] == "WARNING"))
        d = one(H + '<text x="80" y="300" font-family="Yu Gothic" font-size="32">第1回 九州 次世代エネルギー展</text>')
        check("新: 固有名詞（次世代エネルギー展）は引っかけない",
              not any("AIくさい" in i["message"] for i in d["issues"]))
        # 2026-10-01: 締めの決まり文句・決め台詞（yomiyasu の語の一覧から、言い回しを直して移した物）
        DOC = "# Spec Lock\n- delivery: document\n"
        d = one(H + '<text x="80" y="300" font-family="Yu Gothic" font-size="32">いかがでしたでしょうか</text>', spec=DOC)
        check("新: 締めの決まり文句「いかがでしたでしょうか」→ ERROR", any("決まり文句" in m for m in errs(d)), " | ".join(errs(d)))
        d = one(H + '<text x="80" y="300" font-family="Yu Gothic" font-size="32">ぜひ試してみてください</text>', spec=DOC)
        check("新: 締めの決まり文句「ぜひ試してみてください」→ ERROR", any("決まり文句" in m for m in errs(d)), " | ".join(errs(d)))
        def warns(d):
            return [i["message"] for i in d["issues"] if i["severity"] == "WARNING"]
        # 2回目の反証 2026-10-01（親の判断）: 決め台詞「〜に他ならない」「〜というわけだ」は教科書の書き言葉でも使うので、
        # build を止める ERROR から WARNING（AIくさい語の疑い）に下げた。前の試験「→ ERROR」はこの決めに合わせて書き換えた
        d = one(H + '<text x="80" y="300" font-family="Yu Gothic" font-size="32">これは設計の失敗に他ならない</text>', spec=DOC)
        check("新: 決め台詞「〜に他ならない」（である調）→ WARNING（ERROR にしない。2回目の反証）",
              any("AIくさい語の疑い" in m for m in warns(d)) and not any("決まり文句" in m for m in errs(d)),
              " | ".join(errs(d) + warns(d)))
        d = one(H + '<text x="80" y="300" font-family="Yu Gothic" font-size="32">来年の募集にぜひ応募してください</text>', spec=DOC)
        check("新: お願い「ぜひ応募してください」は決まり文句にしない", not any("決まり文句" in m for m in errs(d)), " | ".join(errs(d)))
        # 「」で囲むだけでは抜けられない（反証 2026-10-01。外すのは brief.json に逐語の証拠として登録した「」だけ。
        # 登録した「」を見ない試験は、台帳のある v2 のデッキで下の M の節に置いた）
        d = one(H + '<text x="80" y="300" font-family="Yu Gothic" font-size="32">「無限の可能性」を秘めた半導体</text>', spec=DOC)
        check("新: 決まり文句を「」で囲んだだけ「「無限の可能性」を秘めた半導体」→ ERROR のまま",
              any("決まり文句" in m for m in errs(d)), " | ".join(errs(d)))
        d = one(H + '<text x="80" y="300" font-family="Yu Gothic" font-size="32">「結局は慣れに他ならない」</text>', spec=DOC)
        check("新: 台帳に登録していない「」の中の決め台詞 → WARNING のまま（brief.json が無い＝逐語の証拠と確かめられない。"
              "2回目の反証で ERROR から WARNING に下げた）",
              any("AIくさい語の疑い" in m for m in warns(d)), " | ".join(errs(d) + warns(d)))
        d = one(H + '<text x="80" y="300" font-family="Yu Gothic" font-size="32">Overview'
                    '<tspan x="80" dy="50">研修の3日間をまとめる</tspan></text>', spec=DOC)
        check("新: 「Overview」の下に tspan の行が続いても ERROR（決まり文句は行ごとに見る）",
              any("決まり文句" in m for m in errs(d)), " | ".join(errs(d)))
        d = one(H + '<text x="80" y="300" font-family="Yu Gothic" font-size="16">配布資料の本文は小さくてよい</text>',
                spec="# Spec Lock\n- delivery: document\n")
        check("新: delivery=document は話す型検査 OFF", not any("px 未満" in m for m in errs(d)))

        # --- PREP（2026-09-28 本人指示「PREPを用いるように」）---
        def deck(n, spec):
            p = tmp / ("prep%d" % len(results))
            svgs = [SVG_HEAD + '<text x="80" y="110" font-family="Yu Gothic" font-size="48">主張%d</text>' % i
                    + FOOTER % (i, n) + '</svg>' for i in range(1, n + 1)]
            notes = "# Notes\n\n" + "".join("## Slide %d: s\n\nn\n\n" % i for i in range(1, n + 1))
            make_project(p, svgs, notes, spec)
            return json.loads(run_doctor(p, "--json").stdout)

        def prep_errs(d):
            return [i["message"] for i in d["issues"] if i["severity"] == "ERROR" and "PREP" in i["message"]]

        d = deck(4, "# Spec Lock\n- delivery: presentation\n")
        check("PREP: 割り当てが無ければ ERROR", any("割り当てが spec_lock に無い" in m for m in prep_errs(d)))
        d = deck(7, "# Spec Lock\n- delivery: presentation\n- prep: C 1 / P 2 / R 3-4 / E 5-6 / P 7\n")
        check("PREP: 正しい並びは通る", not prep_errs(d), " | ".join(prep_errs(d)))
        d = deck(5, "# Spec Lock\n- delivery: presentation\n- prep: C 1 / R 2 / E 3-4 / P 5\n")
        check("PREP: 結論から始まらないと ERROR", any("表紙・目次の次が結論" in m for m in prep_errs(d)))
        d = deck(4, "# Spec Lock\n- delivery: presentation\n- prep: P 1 / R 2-3 / P 4\n")
        check("PREP: 具体例(E)が無いと ERROR", any("具体例" in m for m in prep_errs(d)))
        d = deck(5, "# Spec Lock\n- delivery: presentation\n- prep: P 1 / R 2 / E 3 / P 4\n")
        check("PREP: 枚数と合わないと ERROR", any("枚数(5)と合わない" in m for m in prep_errs(d)))
        d = deck(6, "# Spec Lock\n- delivery: presentation\n- prep: P 1 / R 2 / E 3 / R 4 / E 5 / P 6\n")
        check("PREP: R と E の交互は通る", not prep_errs(d), " | ".join(prep_errs(d)))

        # --- 中身の確認（選択式）の記録（2026-09-28 本人提案）---
        def brief_errs(d):
            return [i["message"] for i in d["issues"] if i["severity"] == "ERROR" and "中身の確認" in i["message"]]
        d = deck(4, "# Spec Lock\n- delivery: presentation\n- prep: P 1 / R 2 / E 3 / P 4\n")
        check("brief: 記録が無ければ ERROR", bool(brief_errs(d)))
        d = deck(4, "# Spec Lock\n- delivery: presentation\n- prep: P 1 / R 2 / E 3 / P 4\n"
                    "brief_confirmed: 2026-09-28 選択式\n")
        check("brief: 記録があれば通る", not brief_errs(d), " | ".join(brief_errs(d)))
        d = deck(4, "# Spec Lock\n- delivery: document\n")
        check("brief: 配布用（document）でも求める（2026-09-28〜 全デッキ）", bool(brief_errs(d)))
        d = deck(2, "# Spec Lock\n- delivery: document\n- prep: C 1 / P 2\nbrief_confirmed: 2026-09-28 選択式\n")
        check("PREP: 3枚以下は R/E が無くても通る", not prep_errs(d), " | ".join(prep_errs(d)))
        d = deck(2, "# Spec Lock\n- delivery: document\n- prep: C 1 / R 2\nbrief_confirmed: 2026-09-28 選択式\n")
        check("PREP: 小さなデッキでも最後は結論(P)", any("結論(P)でない" in m for m in prep_errs(d)))

        # ================= 2026-09-28 v2: 中身の検査（C1〜C6・R0）と形の検査（F1〜F8） =================
        def build(name, parts):
            p = tmp / name
            n = len(parts["slides"])
            svgs = [SVG_HEAD + s + FOOTER % (i, n) + '</svg>' for i, s in enumerate(parts["slides"], 1)]
            notes_md = None
            if parts["notes"] is not None:
                notes = list(parts["notes"])
                while len(notes) < n:
                    notes.append("（約20秒）補足のノート。")
                notes_md = "# Speaker Notes\n\n" + "".join(
                    "## Slide %d: s%d\n\n%s\n\n" % (i, i, t) for i, t in enumerate(notes, 1))
            make_project(p, svgs, notes_md, parts["spec"])
            add_ledger(p, parts["brief"], parts["memo"], parts["inventory"], parts["evidence"],
                       parts.get("reader", "PASS"))
            return p

        def dj(p, *flags):
            r = run_doctor(p, "--json", *flags)
            d = json.loads(r.stdout)
            d["exit"] = r.returncode
            return d

        def got(d, prefix, sev=None):
            return [i["message"] for i in d["issues"]
                    if i["message"].startswith(prefix) and (sev is None or i["severity"] == sev)]

        def show(d, sev):
            return " | ".join(i["message"][:60] for i in d["issues"] if i["severity"] == sev)[:300]

        # --- 見本（v2 の台帳・照合の記録・形も整った5枚）は ERROR 0・WARNING 0 ---
        good = build("good", good_parts())
        d = dj(good)
        check("v2 見本: exit 0・ERROR 0", d["exit"] == 0 and d["errors"] == 0, show(d, "ERROR"))
        check("v2 見本: WARNING 0", d["warnings"] == 0, show(d, "WARNING"))

        # --- C1 証拠の台帳 ---
        pt = good_parts(); pt["brief"] = None; pt["spec"] = OLD_SPEC
        old = build("c1_old", pt)
        d = dj(old)
        check("C1: 旧書式の spec_lock だけ（brief.json 無し）→ ERROR",
              any("brief.json(v2) が無い" in m for m in got(d, "C1", "ERROR")), show(d, "ERROR"))
        check("C1: 落ちたら C2〜C6 は INFO で未実行",
              bool(got(d, "C2〜C6", "INFO")) and not any(got(d, c) for c in ("C2 ", "C3 ", "C4 ", "C5 ", "C6 ")))
        d = dj(old, "--legacy")
        check("C1 --legacy: 同じ指摘が WARNING・他に ERROR が無ければ exit 0",
              bool(got(d, "C1", "WARNING")) and not got(d, "C1", "ERROR") and d["exit"] == 0, show(d, "ERROR"))
        pt = good_parts(); pt["brief"] = None; pt["spec"] = OLD_SPEC.replace("2026-09-28", "2026-09-01")
        d = dj(build("c1_olddate", pt))
        # 2026-09-28 反証: 日付を手で古く書くだけで下がる抜け道だったので、自動の旧書式扱いは廃止（--legacy だけ）
        check("C1 移行: brief_confirmed を 9/28 より前の日付にしても自動では下がらない（ERROR のまま）",
              bool(got(d, "C1", "ERROR")) and not got(d, "C1", "WARNING"), show(d, "ERROR"))
        pt = good_parts(); pt["brief"]["proof"] = []
        d = dj(build("c1_empty", pt))
        check("C1: proof=[] → ERROR（空の欄名 proof を出す）",
              any("proof" in m for m in got(d, "C1", "ERROR")), show(d, "ERROR"))
        check("C1: 見本では出ない", not got(dj(good), "C1"))

        # --- C2 証拠の割り当て ---
        pt = good_parts(); pt["brief"]["proof"] = pt["brief"]["proof"][1:]   # E1（R1 と 4枚目の証拠）を外す
        d = dj(build("c2_miss", pt))
        c2 = got(d, "C2", "ERROR")
        check("C2: R1 に証拠が無い → ERROR", any("R1 に証拠が無い" in m for m in c2), " | ".join(c2))
        check("C2: 4枚目(E)が割り当たっていない → ERROR",
              any("4枚目(E)がどの証拠にも割り当たっていない" in m for m in c2), " | ".join(c2))
        pt = good_parts()
        pt["brief"]["proof"] = [pt["brief"]["proof"][0],
                                {"id": "A1", "for": "P", "kind": "annotation", "src": "memo.md:9",
                                 "quote": "熱意がすごかった", "slides": [2]}]
        d = dj(build("c2_weak", pt))
        check("C2: 結論の証拠が注記1件だけ → ERROR（2件未満）",
              any("結論の証拠が2件未満" in m for m in got(d, "C2", "ERROR")), show(d, "ERROR"))
        check("C2: 見本（R1←E1・P に逐語と数字）では出ない", not got(dj(good), "C2"))
        pt = good_parts()
        pt["slides"] = [GOOD_SLIDES[0], GOOD_SLIDES[1], GOOD_SLIDES[4]]
        pt["notes"] = [GOOD_NOTES[0], GOOD_NOTES[1], GOOD_NOTES[4]]
        pt["spec"] = spec_v2("C 1 / P 2 / P 3")
        pt["brief"]["prep"] = "C 1 / P 2 / P 3"
        pt["brief"]["r"] = [{"id": "R1", "claim": "本気だった", "slides": []}]
        pt["brief"]["proof"] = [dict(GOOD_BRIEF["proof"][1]), dict(GOOD_BRIEF["proof"][2], slides=[3])]
        d = dj(build("c2_small", pt))
        check("C2: 3枚以下（C 1 / P 2 / P 3）は (a)〜(c) を見ない", not got(d, "C2"), " | ".join(got(d, "C2")))
        pt["brief"]["proof"] = pt["brief"]["proof"][:1]
        d = dj(build("c2_small_weak", pt))
        check("C2: 3枚以下でも結論の証拠2件は見る", any("2件未満" in m for m in got(d, "C2", "ERROR")))

        # --- C3 出典の行 ---
        pt = good_parts()
        pt["memo"] = ["# メモ", "## 1日目", "- 移動した", "- 昼食", "- 場面: 夕方に話した", "- 夜", "- 就寝",
                      "## 2日目", "> 進路を考えて行動しただけ", "- おわり"]
        pt["brief"]["proof"][0]["src"] = "memo.md:5"
        d = dj(build("c3_nf", pt))
        check("C3: 引用が src 行の前後2行に無い → ERROR（作文の疑い）",
              any(m.startswith("C3 E1") and "無い" in m for m in got(d, "C3", "ERROR")), show(d, "ERROR"))
        pt = good_parts()
        pt["memo"][2] = "- 場面（推測）: 進路を考えて行動しただけと話したとみられる"
        d = dj(build("c3_fake", pt))
        check("C3: verbatim なのに推測の行 → ERROR（逐語の行ではない）",
              any(m.startswith("C3 E1") and "逐語行ではない" in m for m in got(d, "C3", "ERROR")), show(d, "ERROR"))
        check("C3: 同じ行の推測 → WARNING も出る",
              any(m.startswith("C3 E1") and "推測" in m for m in got(d, "C3", "WARNING")))
        check("C3: 見本（'> ' の行の引用）では出ない", not got(dj(good), "C3"))
        pt = good_parts()
        pt["memo"][7] = "## 感想（本人の一言＋Claude起草案）"
        pt["memo"][9] = "- 先生の熱量がすごかった"
        pt["brief"]["proof"].append({"id": "A1", "for": "R1", "kind": "annotation", "src": "memo.md:10",
                                     "quote": "先生の熱量がすごかった", "slides": [3]})
        d = dj(build("c3_draft", pt))
        check("C3: 2行上の見出しが『起草案』→ WARNING（起草の節）",
              any(m.startswith("C3 A1") and "起草" in m for m in got(d, "C3", "WARNING"))
              and not any(m.startswith("C3 A1") for m in got(d, "C3", "ERROR")), " | ".join(got(d, "C3")))
        pt = good_parts()
        pt["memo"] = [x.replace("> ", "- 本人: 「", 1) + "」" if x.startswith("> ") else x for x in GOOD_MEMO]
        pt["brief"]["sources_read"][0]["verbatim"] = 0
        d = dj(build("c3_noquote_rule", pt))
        check("C3: 逐語の記号の無い素材（verbatim=0）は「」の中にあればよい", not got(d, "C3"), " | ".join(got(d, "C3")))

        # --- C4 読んだ記録 ---
        pt = good_parts(); pt["brief"]["sources_read"][0]["read"] = "1-5"
        d = dj(build("c4_part", pt))
        check("C4: read=1-5（10行中）→ ERROR『6〜10 行が未読』",
              any("6〜10 行が未読" in m for m in got(d, "C4", "ERROR")), show(d, "ERROR"))
        pt = good_parts(); pt["brief"]["sources_read"][0]["verbatim"] = 2
        d = dj(build("c4_vcount", pt))
        check("C4: '> ' が3本なのに verbatim=2 → ERROR", any("逐語行の数が合わない" in m for m in got(d, "C4", "ERROR")))
        pt = good_parts(); pt["brief"]["proof"][0]["src"] = "other.md:4"
        d = dj(build("c4_other", pt))
        check("C4: 出典 other.md が sources_read に無い → ERROR",
              any("other.md" in m and "sources_read" in m for m in got(d, "C4", "ERROR")), show(d, "ERROR"))
        check("C4: 見本（read=1-10・verbatim=3・inventory に ID）では出ない", not got(dj(good), "C4"))
        pt = good_parts(); pt["memo"] = GOOD_MEMO + ["- 追記1", "- 追記2"]
        d = dj(build("c4_append", pt))
        # 2026-09-28 反証: lines を少なく申告すると読み残しが WARNING だけで通っていた → ERROR
        check("C4: 記録は10行・今は12行 → ERROR（11〜12 行を読んでいない）",
              any("11〜12" in m for m in got(d, "C4", "ERROR")), " | ".join(got(d, "C4")))
        pt = good_parts(); pt["memo"] = GOOD_MEMO[:8]
        d = dj(build("c4_shrink", pt))
        check("C4: 記録は10行・今は8行 → ERROR（別のファイルか消された）",
              any("短い" in m for m in got(d, "C4", "ERROR")), " | ".join(got(d, "C4")))
        # C3: 出典の行番号がファイルの末尾を越えても落ちない（2026-09-28 反証の IndexError）
        pt = good_parts(); pt["brief"]["proof"][0]["src"] = "memo.md:11"
        d = dj(build("c3_past_end", pt))
        check("C3: 行番号がファイルの末尾より後 → 落ちずに ERROR（行は無い）",
              d["exit"] == 1 and any("行目は無い" in m for m in got(d, "C3", "ERROR")), show(d, "ERROR"))
        pt = good_parts(); pt["inventory"] = "- E1\n- E2\n"
        d = dj(build("c4_inv", pt))
        check("C4: inventory に無い証拠 ID → ERROR", any("E3" in m for m in got(d, "C4 inventory", "ERROR")))

        # --- C5 台帳 → デッキ ---
        s4_noquote = S("8月18日、食堂で聞いた一言", ["夕方の食堂で話した"])
        pt = good_parts(); pt["slides"][3] = s4_noquote
        d = dj(build("c5_gone", pt))
        check("C5: E1 の引用が 4枚目の SVG にもノートにも無い → ERROR",
              any(m.startswith("C5 選んだ証拠 E1") for m in got(d, "C5", "ERROR")), show(d, "ERROR"))
        pt = good_parts(); pt["slides"][3] = s4_noquote
        pt["notes"][3] = GOOD_NOTES[3] + "その人は、進路を考えて行動しただけ、と言いました。"
        d = dj(build("c5_notes", pt))
        check("C5: ノートの Slide 4 にあれば出ない", not any("E1" in m for m in got(d, "C5")), " | ".join(got(d, "C5")))
        pt = good_parts(); pt["brief"]["me"]["scene"]["quote"] = "長期の東湖工科大学のプログラム"
        d = dj(build("c5_scene", pt))
        check("C5: 本人の場面がデッキに無い（cta あり）→ ERROR",
              any("本人の場面" in m for m in got(d, "C5", "ERROR")), show(d, "ERROR"))
        pt["brief"]["cta"] = ""
        d = dj(build("c5_scene_nocta", pt))
        check("C5: 同じで cta が空 → WARNING",
              any("本人の場面" in m for m in got(d, "C5", "WARNING")) and not got(d, "C5", "ERROR"))
        pt = good_parts(); pt["slides"][4] = S("8月18日の一言で、来年の挑戦を決めた", ["4コマの講義と2か所の見学"])
        d = dj(build("c5_number", pt))
        check("C5: number は数字と単位で照合（語順が違っても通る）", not got(d, "C5"), " | ".join(got(d, "C5")))
        pt = good_parts()
        pt["brief"]["proof"].append({"id": "P1", "for": "R1", "kind": "photo", "src": "photos/sensor.jpg",
                                     "quote": "", "slides": [3]})
        d = dj(build("c5_photo", pt))
        check("C5: 写真の証拠が割り当てた枚の画像に無い → ERROR",
              any("P1" in m and "写真" in m for m in got(d, "C5", "ERROR")), show(d, "ERROR"))

        # --- C6 結論の核 ---
        pt = good_parts(); pt["brief"]["p_core"] = ["本気度"]
        d = dj(build("c6_zero", pt))
        check("C6: p_core が R/E のどの枚（本文・ノート）にも無い → ERROR", bool(got(d, "C6", "ERROR")), show(d, "ERROR"))
        re7 = "C 1 / P 2 / R 3 / E 4 / R 5 / E 6 / P 7"
        pt = good_parts()
        pt["slides"] = [GOOD_SLIDES[0], GOOD_SLIDES[1], GOOD_SLIDES[2],
                        S("食堂で聞いた一言", ["「進路を考えて行動しただけ」"]),
                        S("東湖は技術を学ぶところから", ["1976年に技術を移転"]),
                        S("修了証と言葉の壁", ["英語で2時間の議論"]), GOOD_SLIDES[4]]
        pt["notes"] = [GOOD_NOTES[0], GOOD_NOTES[1], GOOD_NOTES[2], "（約20秒）食堂での話。", "（約20秒）歴史の話。",
                       "（約20秒）言葉の話。", GOOD_NOTES[4]]
        pt["spec"] = spec_v2(re7)
        d = dj(build("c6_half", pt))
        c6 = got(d, "C6", "WARNING")
        check("C6: R/E 4枚のうち1枚だけ → WARNING（出ない3枚を並べる）",
              any("4・5・6" in m for m in c6) and not got(d, "C6", "ERROR"), " | ".join(got(d, "C6")))
        pt["notes"][4] = "（約20秒）歴史の話。人の熱意から産業ができた。"
        d = dj(build("c6_two", pt))
        check("C6: 2枚に出る（1枚はノートだけ）→ 出ない", not got(d, "C6"), " | ".join(got(d, "C6")))

        # --- R0 照合の記録 ---
        pt = good_parts(); pt["evidence"] = None
        noev = build("r0_none", pt)
        d = dj(noev)
        check("R0: evidence_check 行が無い → ERROR", bool(got(d, "R0", "ERROR")))
        d = dj(noev, "--draft")
        check("R0 --draft: 同じデッキで WARNING・exit 0", bool(got(d, "R0", "WARNING")) and not got(d, "R0", "ERROR")
              and d["exit"] == 0, show(d, "ERROR"))
        pt = good_parts(); pt["evidence"] = "FAIL"
        d = dj(build("r0_fail", pt))
        check("R0: 判定が FAIL → ERROR", any("FAIL" in m for m in got(d, "R0", "ERROR")))
        check("R0: PASS で hash が一致 → 出ない", not got(dj(good), "R0"))
        chg = build("r0_changed", good_parts())
        f2 = chg / "svg_output" / "02_page.svg"
        f2.write_text(f2.read_text(encoding="utf-8").replace("東湖の熱意を知った", "東湖の熱意を知る"), encoding="utf-8")
        d = dj(chg)
        check("R0: PASS の後に見出しを変える → ERROR（照合の後に中身が変わった）",
              any("照合の後に中身が変わった" in m for m in got(d, "R0", "ERROR")), show(d, "ERROR"))
        r = subprocess.run([sys.executable, str(CLAIMS), str(chg), "--minor", "誤字の修正"],
                           capture_output=True, text=True, encoding="utf-8")
        d = dj(chg)
        check("R0: claims.py --minor で付け直すと INFO（minor=理由）",
              r.returncode == 0 and not got(d, "R0", "ERROR")
              and any("minor=誤字の修正" in m for m in got(d, "R0", "INFO")), r.stdout[-200:])
        check("R1: claims.py --minor は reader_check も同じ理由で付け直す",
              not got(d, "R1", "ERROR") and any("minor=誤字の修正" in m for m in got(d, "R1", "INFO")),
              " | ".join(got(d, "R1")))

        # --- R1 初見の読み手の記録（2026-10-01） ---
        pt = good_parts(); pt["reader"] = None
        nord = build("r1_none", pt)
        d = dj(nord)
        check("R1: reader_check 行が無い → ERROR", bool(got(d, "R1", "ERROR")), " | ".join(got(d, "R1")))
        d = dj(nord, "--draft")
        check("R1 --draft: 同じデッキで WARNING・exit 0", bool(got(d, "R1", "WARNING")) and not got(d, "R1", "ERROR")
              and d["exit"] == 0, show(d, "ERROR"))
        d = dj(nord, "--legacy")
        check("R1 --legacy: WARNING に下がる", bool(got(d, "R1", "WARNING")) and not got(d, "R1", "ERROR"))
        pt = good_parts(); pt["reader"] = "FAIL"
        d = dj(build("r1_fail", pt))
        check("R1: 判定が FAIL → ERROR", any("FAIL" in m for m in got(d, "R1", "ERROR")))
        check("R1: PASS で hash が一致 → 出ない", not got(dj(good), "R1"))
        chg1 = build("r1_changed", good_parts())
        f2 = chg1 / "svg_output" / "02_page.svg"
        f2.write_text(f2.read_text(encoding="utf-8").replace("東湖の熱意を知った", "東湖の熱意を知る"), encoding="utf-8")
        d = dj(chg1)
        check("R1: PASS の後に見出しを変える → ERROR（読み手の後に中身が変わった）",
              any("中身が変わった" in m for m in got(d, "R1", "ERROR")), show(d, "ERROR"))
        # claims.py --reader: スライドの文字だけ（ノートは入れない・ページ番号を外す・見出しに印）
        r = subprocess.run([sys.executable, str(CLAIMS), str(chg1), "--reader"],
                           capture_output=True, text=True, encoding="utf-8")
        st = (chg1 / "review" / "slide_text.md")
        txt = st.read_text(encoding="utf-8") if st.is_file() else ""
        check("claims.py --reader: slide_text.md に見出しの印・本文・※の行があり、ノートとページ番号が無い",
              r.returncode == 0 and "【見出し】留学生の一言で、東湖の熱意を知る" in txt, r.stdout[-200:] + " ".join(txt.split())[:300])
        check("claims.py --reader: ノートの文（結論から言います）は入らない", "結論から言います" not in txt and "## 02枚目" in txt
              and "【※】※3日目の夜の研修メモから" in txt and not re.search(r"^\d+ / \d+$", txt, re.M),
              " ".join(txt.split())[:200])
        rep = chg1 / "review" / "reader_check.md"
        rep.write_text("判定: PASS\n", encoding="utf-8")
        r = subprocess.run([sys.executable, str(CLAIMS), str(chg1), "--record-reader", "PASS",
                            "--report", "review/reader_check.md"], capture_output=True, text=True, encoding="utf-8")
        d = dj(chg1)
        check("R1: claims.py --record-reader PASS で付け直すと R1 が消える",
              r.returncode == 0 and not got(d, "R1"), r.stdout[-200:])
        sl = (chg1 / "spec_lock.md").read_text(encoding="utf-8")
        check("R1: --record-reader は reader_check 行を1行だけにする（evidence_check 行は残す）",
              sl.count("reader_check:") == 1 and sl.count("evidence_check:") == 1, sl[-300:])

        # --- M1〜M6 意味の検査（2026-10-01。例は Kiminori Yokoi「AI臭い文章とは何なのか」の具体例を書き言葉にした物） ---
        def m_deck(name, head, body=("「半導体のやる気全員の」",), eyebrow=None):
            pt = good_parts(); pt["slides"][2] = S(head, list(body), eyebrow=eyebrow)
            return dj(build(name, pt))
        d = m_deck("m1", "依存構造は分割できない。動かしながら引き返す")
        check("M1: 「分割できない。動かしながら引き返す」→ WARNING", bool(got(d, "M1", "WARNING")), " | ".join(got(d, "M")))
        d = m_deck("m1_fix", "依存関係を分離できないため、稼働中に変更し、問題が出たら元の状態に戻す")
        check("M1: 修正例（1文にして対象と条件を書く）→ 出ない", not got(d, "M"), " | ".join(got(d, "M")))
        pt = good_parts(); pt["slides"][2] = S("依存関係を分離できない", [], extra=TX(96, 260, 48, "ため稼働中に変更する"))
        d = dj(build("m1_wrap", pt))
        check("M1: 見出しの2行目が「ため」で始まる（折り返し）→ 出ない", not got(d, "M1"), " | ".join(got(d, "M")))
        d = m_deck("m2", "読んで身に付けてから、効く。効いてから、身に付く")
        check("M2: 「身に付けてから、効く。効いてから、身に付く」→ WARNING", bool(got(d, "M2", "WARNING")), " | ".join(got(d, "M")))
        d = m_deck("m2_fix", "実際の業務で使い、効果を確かめながら使い方を覚える")
        check("M2: 修正例 → 出ない", not got(d, "M"), " | ".join(got(d, "M")))
        d = m_deck("m3", "前提を、経路が代わりに添える")
        check("M3: 「前提を、経路が代わりに添える」→ WARNING", bool(got(d, "M3", "WARNING")), " | ".join(got(d, "M")))
        check("M5: 同じ文の「経路が代わりに添える」→ WARNING", bool(got(d, "M5", "WARNING")), " | ".join(got(d, "M")))
        d = m_deck("m3_fix", "運用者は問い合わせ先に応じた前提条件を参照する")
        check("M3: 修正例 → 出ない", not got(d, "M"), " | ".join(got(d, "M")))
        d = m_deck("m3_time", "8月18日、食堂で聞いた一言")
        check("M3: 日付の後の読点（8月18日、）→ 出ない", not got(d, "M3"))
        d = m_deck("m3_adv", "図らずも、対照実験になった", ["最後に、明日の最終発表の方向を話す"])
        check("M3: 接続・副詞の後の読点（図らずも、・最後に、）→ 出ない（過去のデッキの誤検知）", not got(d, "M3"),
              " | ".join(got(d, "M")))
        d = m_deck("m3_obj", "表の数値を、実測の入力と一致させる")
        check("M3: 目的語の直後の読点（表の数値を、）→ WARNING（資料「多くの場合は不要」・本人「てんおおい」）",
              bool(got(d, "M3", "WARNING")))
        d = m_deck("m5_culprit", "モーターが回らない原因を探す", ["0V から犯人を絞る"])
        check("M5: 原因を「犯人」に例える → WARNING", bool(got(d, "M5", "WARNING")), " | ".join(got(d, "M")))
        d = m_deck("m4", "片方だけを見て基準を作ると、もう片方が壊れる")
        check("M4: 「片方」「もう片方」→ WARNING", bool(got(d, "M4", "WARNING")), " | ".join(got(d, "M")))
        d = m_deck("m4_fix", "開発速度だけを基準にすると、保守性の要件を満たせなくなる")
        check("M4: 修正例 → 出ない", not got(d, "M"), " | ".join(got(d, "M")))
        d = m_deck("m4_deictic", "それが答えだった")
        check("M4: 見出しが指示語で始まる → WARNING", any("指示語" in m for m in got(d, "M4", "WARNING")))
        d = m_deck("m5", "判断に迷うものは、残さない側に倒す")
        check("M5: 「残さない側に倒す」→ WARNING", bool(got(d, "M5", "WARNING")), " | ".join(got(d, "M")))
        d = m_deck("m5_fix", "採否を判断できない項目は、原則として除外する")
        check("M5: 修正例 → 出ない", not got(d, "M"), " | ".join(got(d, "M")))
        d = m_deck("m6", "現場の情報共有の効率化")
        check("M6: 見出しが「〜の効率化」で止まる → WARNING", bool(got(d, "M6", "WARNING")), " | ".join(got(d, "M")))
        d = m_deck("m_quote", "8月18日の一言", ["「片方だけ見てたら、もう片方が壊れる」", "※8月18日、食堂で日本人留学生から"])
        check("M: 「」の中の実際の発言は見ない", not got(d, "M"), " | ".join(got(d, "M")))

        # --- 2026-10-01 M5 の追加・M7〜M9（語は yomiyasu（MIT・Copyright (c) 2026 nanaism）の一覧が元。正規表現は直した） ---
        # 当たる例は yomiyasu の例を書き言葉にした物、当たらない例は同じ語を物の話で使った文
        for key, hit, miss in [
                ("quiet", "キャッシュが切れるとデータが静かに壊れる", "試料を実験台に静かに置いた"),
                ("melt", "デバッグに丸一日溶かした", "ハンダを溶かして配線をつないだ"),
                ("crush", "原因を1つずつ潰す", "空き缶を潰して捨てた"),
                ("kiku", "命名規則が地味に効いてくる", "鎮痛薬を飲むと30分で効いた"),
                ("kuzure", "ここを読み違えると前提が崩れる", "地震で塀が崩れた"),
                ("dig", "センサーの仕組みを深掘りする", "穴を深く掘った"),
                ("hada", "現場の肌感では遅い", "体温を測った")]:
            d = m_deck("m5_" + key, hit)
            check("M5: 「%s」→ WARNING" % hit, bool(got(d, "M5", "WARNING")), " | ".join(got(d, "M")))
            d = m_deck("m5_" + key + "_ok", miss)
            check("M5: 物の話の「%s」→ 出ない" % miss, not got(d, "M"), " | ".join(got(d, "M")))
        d = m_deck("m7", "結論から言うと、原因は設定だった")
        check("M7: 「結論から言うと、」→ WARNING", bool(got(d, "M7", "WARNING")), " | ".join(got(d, "M")))
        d = m_deck("m7_tame", "重要なのは、応答時間だ")
        check("M7: 「重要なのは、」→ M7 だけ（同じ読点を M3 に二重に数えない）",
              bool(got(d, "M7", "WARNING")) and not got(d, "M3"), " | ".join(got(d, "M")))
        d = m_deck("m7_ok", "抵抗が重要な理由は2つある")
        check("M7: 文の途中の「重要な」→ 出ない", not got(d, "M"), " | ".join(got(d, "M")))
        d = m_deck("m8", "新しい機能を出した", ["\u2705 動作を確かめた"])
        check("M8: 絵文字（チェックの絵文字）→ WARNING", bool(got(d, "M8", "WARNING")), " | ".join(got(d, "M")))
        d = m_deck("m8_ok", "必須の項目に印を付けた", ["★印は必須の項目", "① 最初の手順"])
        check("M8: ★・① の記号 → 出ない", not got(d, "M"), " | ".join(got(d, "M")))
        d = m_deck("m9", "使った機器は3つ", ["次の3つを使った：", "テスター・電源・オシロ"])
        check("M9: 行の終わりのコロン「次の3つを使った：」→ WARNING", bool(got(d, "M9", "WARNING")), " | ".join(got(d, "M")))
        d = m_deck("m9_inline", "報告会の日時を決めた", ["日時：10月1日"])
        check("M9: 同じ行に値がある「日時：10月1日」→ 出ない", not got(d, "M"), " | ".join(got(d, "M")))
        pt = good_parts(); pt["slides"][2] = S("報告会の日時を決めた", [], extra=TX(96, 300, 32, "日時：") + TX(300, 300, 32, "10月1日"))
        d = dj(build("m9_pair", pt))
        check("M9: 「日時：」と「10月1日」を2つの <text> で横に並べた表 → 出ない", not got(d, "M9"), " | ".join(got(d, "M")))
        d = m_deck("m9_en", "Results", ["The smell was very strong:", "the sensors went near their maximum."])
        check("M9: 英語の行のコロン → 出ない（英語では普通の書き方）", not got(d, "M9"), " | ".join(got(d, "M")))
        d = m_deck("m9_said", "島民は夜の便を求めた", ["若者：「もう1時間遅く」", "・主な質問：「不便なところは？」"])
        check("M9: コロンの後ろに同じ行で人の言葉が続く「若者：「…」」→ 出ない（過去のデッキの誤検知）",
              not got(d, "M9"), " | ".join(got(d, "M")))
        d = m_deck("m9_prep", "教える側も学ぶ側も、熱意で動いた", ["理由：", "講義4コマ・見学2か所を1日で"])
        check("M9: PREP の札「理由：」は F5 だけ（M9 に二重に数えない）",
              not got(d, "M9") and any("PREP の札" in i["message"] for i in d["issues"]), " | ".join(got(d, "M")))
        # 反証 2026-10-01: 名詞の見出し語＋コロンで、次の行に中身を書くのは人が書いた授業のスライドで普通の組み方。
        # 例は旧PCにあった授業の pptx から
        for key, lines, src in [
                ("input", ["入力：", "4 50 30 10 21 32 12 3"], "授業の班発表 A 9枚目"),
                ("path", ["絶対パス：", "ルートから始まる道順"], "授業の配布資料 B 24枚目"),
                ("chem", ["・ アニオン排除材：", "Tetrakis[3,5-bis(trifluoromethyl)phenyl]borate"],
                 "実験の最終発表 C 9枚目")]:
            d = m_deck("m9_noun_" + key, "授業のスライドの組み方", lines)
            check("M9: 名詞の見出し語「%s」＋次の行（%s）→ 出ない" % (lines[0], src), not got(d, "M9"), " | ".join(got(d, "M")))
        pt = good_parts(); pt["slides"][2] = S("研修の反省を2つの列に分けた", [], extra=(
            TX(96, 300, 32, "良かった点：") + TX(700, 300, 32, "悪かった点：")
            + TX(96, 350, 28, "講義が4コマ") + TX(700, 350, 28, "移動に2時間")))
        d = dj(build("m9_cols", pt))
        check("M9: 段組みの列の頭「良かった点：」「悪かった点：」（同じ高さに並ぶ）→ 出ない", not got(d, "M9"), " | ".join(got(d, "M")))
        d = m_deck("m9_pred", "島民の要望を2つに絞った", ["島民に聞いて分かった：", "夜の便がほしい"])
        check("M9: 述語でコロンの直前が終わる「島民に聞いて分かった：」→ WARNING",
              bool(got(d, "M9", "WARNING")), " | ".join(got(d, "M")))
        d = m_deck("m9_pred_noun", "授業のスライドの組み方", ["画面に文字列を表示するプログラム：", "printf(\"Hello\");"])
        check("M9: 述語の後ろに名詞が付いた見出し語「画面に文字列を表示するプログラム：」（授業の配布資料 B "
              "12枚目）→ 出ない", not got(d, "M9"), " | ".join(got(d, "M")))
        d = m_deck("m9_rel_noun", "島民の要望を2つに絞った", ["今回選ばなかった論点：", "医療・行政は市の領域"])
        check("M9: 同じ形の「今回選ばなかった論点：」（過去のデッキ 06）→ 出ない",
              not got(d, "M9"), " | ".join(got(d, "M")))
        # 反証 2026-10-01: 句点の無い箇条書きを tspan で1行ずつ並べると、2行目より後の行の頭の「重要なのは」を見逃していた
        def m_lines(name, lines):
            pt = good_parts()
            body = '<text x="96" y="300" font-family="Yu Gothic" font-size="32">%s' % lines[0]
            body += "".join('<tspan x="96" dy="50">%s</tspan>' % t for t in lines[1:]) + '</text>'
            pt["slides"][2] = S("温度を測りながら電圧を測った", [], extra=body)
            return dj(build(name, pt))
        d = m_lines("m7_line2", ["・電圧を3回測った", "・重要なのは温度管理"])
        check("M7: tspan の2行目「・重要なのは温度管理」→ WARNING", bool(got(d, "M7", "WARNING")), " | ".join(got(d, "M")))
        d = m_lines("m7_line1", ["・重要なのは温度管理", "・電圧を3回測った"])
        m7 = got(d, "M7", "WARNING")
        check("M7: 1行目の「重要なのは」は1回だけ挙げる（文の頭と行の頭で二重に数えない）",
              len(m7) == 1 and m7[0].split(": ", 1)[1].count("重要なのは") == 1, " | ".join(m7))
        d = m_lines("m7_after_period", ["電圧を3回測った。", "重要なのは温度管理だ。"])
        m7 = got(d, "M7", "WARNING")
        # 規則の名前「前置きの決まり文句（重要なのは・…）」にも同じ語があるので、数えるのは「: 」の後ろの当たりの一覧だけ
        check("M7: 前の行が句点で終わる行の「重要なのは」も1回だけ",
              len(m7) == 1 and m7[0].split(": ", 1)[1].count("重要なのは") == 1,
              " | ".join(m7))
        d = m_lines("m7_wrap_ok", ["抵抗の値が", "重要な理由は2つある"])
        check("M7: 折り返した文の2行目「重要な理由は…」→ 出ない", not got(d, "M7"), " | ".join(got(d, "M")))
        # 反証 2026-10-01: 決まり文句の検査で外す「」は、brief.json に逐語の証拠として登録した物だけ
        def copy_deck(name, quote_on_slide, registered, split=False):
            pt = good_parts()
            if registered:
                pt["memo"][4] = "> 結局は慣れに他ならない"
                pt["brief"]["proof"][1]["quote"] = "結局は慣れに他ならない"
            if split:
                q = ('<text font-family="Yu Gothic" font-size="32"><tspan x="96" y="300">「結局は慣れに</tspan>'
                     '<tspan x="96" y="350">他ならない」</tspan></text>')
                pt["slides"][1] = S("留学生の一言で、東湖の熱意を知った", [], extra=q + TX(96, 420, 24, "※3日目の夜の研修メモから"))
            else:
                pt["slides"][1] = S("留学生の一言で、東湖の熱意を知った", [quote_on_slide, "※3日目の夜の研修メモから"])
            return dj(build(name, pt))
        # 2回目の反証（親の判断）で「〜に他ならない」は ERROR から WARNING（AIくさい語の疑い）に下げたので、
        # 登録した逐語は WARNING も出ないこと、登録していない「」は WARNING のまま出ることを見る
        d = copy_deck("copy_reg", "「結局は慣れに他ならない」", True)
        check("決まり文句: brief.json に逐語の証拠として登録した「結局は慣れに他ならない」→ ERROR も WARNING も出さない",
              not got(d, "AIくさい") and not got(d, "C3"),
              " | ".join(got(d, "AIくさい") + got(d, "C3")))
        d = copy_deck("copy_reg_split", "", True, split=True)
        check("決まり文句: 登録した逐語を tspan で行を割った「」→ ERROR も WARNING も出さない",
              not got(d, "AIくさい"), " | ".join(got(d, "AIくさい")))
        d = copy_deck("copy_unreg", "「結局は慣れに他ならない」", False)
        check("決まり文句: 台帳に無い「」の中の「〜に他ならない」→ WARNING（2回目の反証で ERROR から下げた）",
              bool(got(d, "AIくさい語の疑い", "WARNING")) and not got(d, "AIくさい", "ERROR"),
              " | ".join(got(d, "AIくさい")))
        check("M: 見本のデッキでは M1〜M11 が1件も出ない", not got(dj(good), "M"), " | ".join(got(dj(good), "M")))

        # --- 2回目の反証 2026-10-01: 親の判断で必ず直す物と、比喩の原理の組 ---
        # (b) 句点の無い箇条書きを tspan で1行ずつ並べた時、2行目より後の行の頭も文の頭として M1・M3 を見る（M7 と同じ扱い）
        d = m_lines("m1_line2", ["・AIは答えを教えない", "・問いを返す"])
        check("M1: tspan の箇条書き「・AIは答えを教えない」「・問いを返す」→ WARNING（2回目 (b)）",
              bool(got(d, "M1", "WARNING")), " | ".join(got(d, "M")))
        d = m_lines("m3_line2", ["・電圧を3回測った", "・前提を、経路が代わりに添える"])
        check("M3: tspan の2行目「・前提を、経路が代わりに添える」→ WARNING（2回目 (b)）",
              bool(got(d, "M3", "WARNING")), " | ".join(got(d, "M")))
        d = m_lines("m3_line3", ["・電圧を3回測った", "・抵抗を2本用意した", "・前提を、経路が代わりに添える"])
        check("M3: tspan の3行目「・前提を、経路が代わりに添える」→ WARNING（2行目より後も文の頭。2回目 (b)）",
              bool(got(d, "M3", "WARNING")), " | ".join(got(d, "M")))
        d = m_lines("m1_list", ["短所:","負の辺がある場合は使えない", "無向グラフの場合は正しく動作しない", "計算量が大きい"])
        check("M1: 句点の無い箇条書きが3行以上（短所の並び。授業の班発表 D 6枚目）→ 項目どうしを組にしない",
              not got(d, "M1"), " | ".join(got(d, "M")))
        d = m_lines("m1_label", ["動的計画法を使用しない", "短所:"])
        check("M1: 2文目が見出し語「短所:」→ 出ない（肯定の言い切りの文ではない）", not got(d, "M1"), " | ".join(got(d, "M")))
        d = m_lines("m3_wrap", ["・誤解やトラブルを招か", "ないように、常に気をつけて使う"])
        check("M3: 語の途中で折り返した行「ないように、…」（授業の班発表 E 18枚目）→ 前の行の続きとして見て出ない",
              not got(d, "M3"), " | ".join(got(d, "M")))
        d = m_deck("m3_quote_word", "改善と伸ばす点を1つずつに絞った", ["改善は「フェリーの時間帯」、伸ばすのは「景観」に絞った"])
        check("M3: 「」の中身を消すと読点が短い語の後に見える「改善は「…」、」（過去のデッキ 06）→ 出ない",
              not got(d, "M3"), " | ".join(got(d, "M")))
        d = m_deck("m3_conj", "人工無脳には学習機能が無い", ["なので、学習機能がない", "入力すると、カレンダーに追加される"])
        check("M3: 接続の語「なので、」・条件の節「入力すると、」（授業の班発表 A・F）→ 出ない", not got(d, "M3"), " | ".join(got(d, "M")))
        # (a) 決め台詞は ERROR ではなく WARNING。締めの決まり文句（いかがでしたか・参考になれば幸い・ぜひ〜てみてください）は ERROR のまま
        for key, text in [("hoka", "この式はオームの法則にほかならない"), ("wake", "100Ωを2本並べて50Ωというわけだ")]:
            d = m_deck("copy_soft_" + key, text)
            check("決め台詞「%s」→ WARNING（build を止めない。2回目 (a)）" % text,
                  bool(got(d, "AIくさい語の疑い", "WARNING")) and not got(d, "AIくさい", "ERROR"), " | ".join(got(d, "AIくさい")))
        d = m_deck("copy_hard_try", "ぜひ一度試してみてください")
        check("締めの決まり文句「ぜひ一度試してみてください」→ ERROR のまま", bool(got(d, "AIくさい決まり文句", "ERROR")),
              " | ".join(got(d, "AIくさい")))
        d = m_deck("copy_hard_ikaga", "この方法を使ってみてはいかが")
        check("締めの決まり文句「〜てみてはいかが」（使ってみては。し＋てみて 以外も）→ ERROR",
              bool(got(d, "AIくさい決まり文句", "ERROR")), " | ".join(got(d, "AIくさい")))
        d = m_deck("copy_mention", "経済学の授業の言葉", ["シナジー効果という言葉を経済学の授業で習った"])
        check("決まり文句を話題にする文「シナジー効果という言葉を…習った」→ 出ない", not got(d, "AIくさい"), " | ".join(got(d, "AIくさい")))
        # (c) M9 の同じ高さの幅＝2つの行の大きい方の字の0.3倍（小さい札の右に大きい字の値。ベースラインが12px ずれる）
        pt = good_parts(); pt["slides"][2] = S("島民の要望を2つに絞った", [], extra=(
            TX(96, 420, 24, "島民に聞いて分かった：") + TX(420, 432, 64, "夜の便")))
        d = dj(build("m9_bigval", pt))
        check("M9: 小さい札「島民に聞いて分かった：」の右に大きい字の値（12px ずれ）→ 表の一部として出ない", not got(d, "M9"),
              " | ".join(got(d, "M")))
        d = m_deck("m9_toha", "二分探索の考え方", ["二分探索とは：", "整列した配列を半分ずつに絞って探す方法"])
        check("M9: 定義の見出し「二分探索とは：」＋次の行（授業の配布資料 G 2枚目）→ 出ない", not got(d, "M9"),
              " | ".join(got(d, "M")))
        # (c) 比喩の原理（M5）: 抽象的な物が主語・目的語なら拾い、人・物・薬・物質・建物の文字どおりの文は拾わない。
        # 同じ動詞で1組ずつ（左＝抽象で拾う・右＝文字どおりで拾わない）
        for key, hit, miss in [
                ("tezawari", "現場の手触りのある提案にする", "布の手触りを比べた"),
                ("dodai", "議論の土台が崩れた", "町家の土台が腐って崩れていた"),
                ("melt", "環境構築で週末を溶かした", "試料を塩酸で24時間溶かした"),
                ("crush", "不具合の候補を順番に潰した", "断線の原因はケーブルを潰したこと"),
                ("kiku", "書いた人を素直に褒める空気のほうが効いた", "鎮痛薬は後から効いてきた"),
                ("taosu", "グレーな項目は捨てる方向に倒す", "トグルスイッチをON側に倒す"),
                ("quiet", "テストが静かに失敗していた", "祖父は眠るように静かに死んだ"),
                ("dive", "データに深く分け入る", "ダイバーは水深30mまで深く潜った"),
                ("hannin", "0V から犯人を絞る", "警察は防犯カメラの映像から犯人を絞り込んだ"),
                ("kasane", "同じ1軒の町家に案を重ねる", "班で検討を重ねた"),
                # 崩れる: 計画・予定が崩れる は辞書に載る意味、数と単位で書いた条件は1通りに決まる（試験集の回で足した）
                ("kuzure_plan", "戦略の根拠が崩れた", "台風で旅行の計画が崩れた"),
                ("kuzure_unit", "この条件では集中定数の前提が崩れる", "1GHzでは集中定数の前提が崩れる"),
                # 効く: 仕組みが働く（キャッシュが効く）と、働かない報告（効かない）は「機能が働く」の意味（文章の検査器と同じ扱い）
                ("kiku_mech", "キャッシュが地味に効く", "HTTPキャッシュも効きにくい"),
                ("kiku_neg", "日々の記録がじわじわ効いてくる", "このショートカットはWordでは効かない")]:
            d = m_deck("m5p_" + key, hit)
            check("M5 原理: 抽象「%s」→ WARNING" % hit, bool(got(d, "M5", "WARNING")), " | ".join(got(d, "M")))
            d = m_deck("m5p_" + key + "_ok", miss)
            check("M5 原理: 文字どおり「%s」→ 出ない" % miss, not got(d, "M5"), " | ".join(got(d, "M")))
        # M10 ダッシュ・M11 読点の打ちすぎ（2回目で足した規則）
        d = m_deck("m10", "速さ—それがすべてだった")
        check("M10: 文の途中のダッシュ「速さ—それがすべてだった」→ WARNING", bool(got(d, "M10", "WARNING")), " | ".join(got(d, "M")))
        d = m_deck("m10_ok", "英語の授業の資料", ["English Conversation — Quick Reference", "10–100 Hz の範囲で測った"])
        check("M10: 英語の見出しの区切り・数の範囲 → 出ない", not got(d, "M10"), " | ".join(got(d, "M")))
        d = m_deck("m11", "測り方を決めた", ["まず、電源を、入れて、少し、待ってから、測る"])
        check("M11: 読点の打ちすぎ「まず、電源を、入れて、少し、…」→ WARNING", bool(got(d, "M11", "WARNING")), " | ".join(got(d, "M")))
        d = m_deck("m11_ok", "使った部品を数えた", ["抵抗、コンデンサ、コイル、ダイオード、トランジスタを使った"])
        check("M11: 名詞を並べる読点 → 出ない", not got(d, "M11"), " | ".join(got(d, "M")))

        # ================= 2026-10-01 3回目の反証: 語の一覧でなく原理でそろえた直し =================
        # 文の型は meaning_hits を直接呼んで確かめる（デッキを組むと1件0.2秒かかるので）。text の ⏎ は <text> の中の改行。
        # head=True は見出し（1行ずつ文の頭）、False は本文（1つの <text>）。例の出どころは、本人・先生・旧PCの人の文と、
        # 反証の担当が作った文字どおりの文（出典を併記）
        def mcodes(text, head=False):
            rows = [r for r in text.split("⏎") if r.strip()]
            return sorted(dd.meaning_hits([("見出し" if head else "本文",) + dd._rows_to_sents(rows, merge=not head)]))

        def m_case(code, text, want, src):
            got_h, got_b = mcodes(text, True), mcodes(text)
            ok = (code in got_h) == want and (code in got_b) == want
            check("%s 3回目: 「%s」→ %s（%s）" % (code, text.replace("⏎", "／")[:34], "出る" if want else "出ない", src), ok,
                  "見出し %s / 本文 %s" % (got_h, got_b))

        # M5: 動詞の相手（主語・目的語・行き先）が抽象の語の時だけ拾う。相手の名詞の句の最後の語で見る
        for text, src in [
                ("なお，電流計なので，電圧計と同じように接続すると，大電流が流れてメータが壊れるので注意すること．", "先生の電子工作編テキスト"),
                ("過電流が流れてICが壊れた", "反証の文字どおりの文"),
                ("課題のプリントを束ねて提出した", "反証の文字どおりの文"),
                ("イオン注入で結晶構造が壊れるので、アニールで回復させる", "反証の文字どおりの文"),
                ("昨夜入れた「削除前に OneDrive の属性を落とす」前処理が効いて、ゴミ箱の中身が実際に消えた", "本人の日記"),
                ("8/6の最大の失敗は再発せず=前夜からの予熱対策が効いた", "本人の日記"),
                ("デカップリングコンデンサが効いて、ノイズが10 mVから2 mVに減った", "反証の文字どおりの文"),
                ("抗生物質が効いて熱が下がった", "反証の文字どおりの文"),
                ("夜中の2時にようやくホテルにたどり着いた", "反証の文字どおりの文"),
                ("フェリーで島にたどり着いた", "反証の文字どおりの文"),
                ("3にたどり着ければ「A」、たどり着けなければ「B」を返す", "授業の班発表 A 10枚目"),
                ("タオルの手触りを比べた", "反証の文字どおりの文"),
                ("古いノートを黙って捨てた", "反証の文字どおりの文"),
                ("感謝の気持ちを手紙に添えた", "人の気持ちは抽象の一覧に入れない"),
                ("皆の思いを束ねて1つの案にした", "人の気持ちは抽象の一覧に入れない"),
                ("彼女の気持ちが溶けた", "人の気持ちは抽象の一覧に入れない"),
                ("新境地を開いた", "辞書に載る語"),
                ("4年次の最終報告書で、その答えをはっきり書けるように積み上げていきます", "本人の報告書"),
                ("遅い便を出しても、景観は壊れない", "過去のデッキ 10"),
                ("SVOCの関係が崩れやすい", "先生のレポート作成用付録"),
                ("熱量の高い燃料を選んだ", "物理量の熱量")]:
            m_case("M5", text, False, src)
        for text, src in [
                ("答えが芽生える", "文章の検査器と同じ抽象の一覧"),
                ("データが静かに語る", "yomiyasu の擬人化"),
                ("ログが黙って捨てられる", "試験集 B1 と同じ型"),
                ("前提そのものが崩れた", "本人の運用メモ"),
                ("議論に踏み込む", "踏み込む の行き先"),
                ("熱量のある議論", "yomiyasu の質感を装う語"),
                ("体温の伝わる資料", "yomiyasu の質感を装う語")]:
            m_case("M5", text, True, src)
        # 「提案3案を具体的なアクションレベルまで落とし込む」（過去のデッキ 07）は、2026-10-01 本人の判断
        # 「① 参考の扱いにする」で INFO の M5参考 になった（試験集 metaphor_other-hit-12 も slides=miss に直った）。下の「6回目」で確かめる
        # M3: 名詞＋（を・が・比べる より）＋読点と、は＋読点で言い切らずに止めた文だけ
        for text, src in [
                ("でも、どの測定を使うかで答えが変わった", "本人 PBL 最終発表 7枚目"),
                ("仮に、この先もずっと、うまくいくとします", "yomiyasu human_oga_05.md:42"),
                ("一つ目は、国際適応力を体系的に伸ばすことである", "本人の志望書"),
                ("1点目は、レポートの期限を守ることである", "先生の文"),
                ("以上より、初期値問題の解は次の通りである", "本人 予習レポート"),
                ("では、どちらを使うかの境目はどこか", "本人 テーマ5 本レポート v2"),
                ("運営面では、参加申込フォームに締切日と定員を設定する", "本人の報告書"),
                ("ところが、電流は流れなかった", "接続の語"),
                ("具体的には、抵抗を替えた", "文全体にかかる副詞"),
                ("表1より、全ての測定点で抵抗値は一定", "本人 テーマ2 レポート v2"),
                ("熱拡散により、不純物が横にも広がる", "手段の により"),
                ("変数は，使用する前に宣言する必要がある", "先生 PL4_1_dist (2).pptx 20枚目"),
                ("次の2つを,自分の言葉で説明しなさい", "先生の課題文"),
                ("・授業冒頭で，事前学習内容の確認を行う．", "先生のスライド"),
                ("学期ごと、科目ごとのテスト点数（番号×科目×学期）", "先生のスライド"),
                ("ソース中に直接書いた⏎初期値を、⏎ファイルから⏎読むようにする。", "先生 PL4_2_dist (2).pptx 8枚目")]:
            got_b = mcodes(text)
            check("M3 3回目: 本文「%s」→ 出ない（%s）" % (text.replace("⏎", "／")[:34], src), "M3" not in got_b, str(got_b))
        check("M3 3回目: 本文の全角の読点で折り返した文「…直接関係しないが，／…書くべき」→ 1文として見て出ない（先生 PL3-1_dist 8枚目）",
              "M3" not in mcodes("コメントは，プログラムの実行には直接関係しないが，⏎プログラムの可読性（見やすさ）のために書くべき"))
        for text in ("学びを、現場に落とし込む", "便数よりも、朝と夜の時間帯の問題", "離島は、まず1軒から", "使うことが、そのまま保存になる"):
            check("M3 3回目: 「%s」→ 出る（資料の型・過去のデッキ）" % text, "M3" in mcodes(text), str(mcodes(text)))
        # M1: 2文目が指示の言い切り・関係を言葉で示す接続語の組は外す。3行以上の箇条書きでも、2行目が自分の主語を持たなければ組にする
        for text, src in [
                ("なお，図は 3 つに限らない．考察に必要なものを適宜掲載すること．", "先生 テーマ3 見本レポート"),
                ("AIを使うこと自体は禁止しない．ただし，AIに企画を丸投げしないこと．", "先生 第8回演習課題"),
                ("水だけではセンサはほぼ動かない。つまり信号の正体は醤油そのもの。", "本人 PBL 最終発表 9枚目"),
                ("金属屑はゴミ箱に捨ててはいけない。指定の容器に廃棄すること。", "先生 電子工作編テキスト")]:
            m_case("M1", text, False, src)
        check("M1 3回目: 本文の3行の箇条書き「・依存構造は分割できない／・動かしながら引き返す／・半年で移行を終える」→ 出る（資料の例）",
              "M1" in mcodes("・依存構造は分割できない⏎・動かしながら引き返す⏎・半年で移行を終える"))
        check("M1 3回目: 本文の3行の長所・短所「検索漏れが発生しない／検索効率が向上する／計算量が大きい」→ 出ない（2行目に主語）",
              "M1" not in mcodes("検索漏れが発生しない⏎検索効率が向上する⏎計算量が大きい"))
        # M2: 入れ替わりに数えるのは述語の項と動詞の形だけ。2文目が矢印で始まる組は外す
        for text, src in [
                ("メモリ上のデータを，ファイルに書き出す⏎ファイル中のデータを，メモリ上に読み込む", "先生 第26回事前学習資料 3枚目"),
                ("他の変数の値を代入することも可能⏎⇒ 代入したい変数を「＝」の右に書く", "先生 PL4_2_dist (2).pptx 8枚目"),
                ("このグラフからたくさんのノイズが見られるのである。ノイズを削除したグラフが右図である。", "人の実験レポート DSP_T03")]:
            got_b = mcodes(text)
            check("M2 3回目: 本文「%s」→ 出ない（%s）" % (text.replace("⏎", "／")[:34], src), "M2" not in got_b, str(got_b))
        # M4: もう片方の＋名詞、括弧・空白を挟む「AとB」、2＋どの助数詞でも組とみなす
        for text, src in [
                ("プローブを手に持ち、もう片方の手の指に対してプローブ先端を接触させる。", "先生 テーマ5"),
                ("フィンガープリント（データの指紋）と指紋認証（バイオメトリクス）は別物。名前が似ているだけで、前者はデータの改ざん検知、後者は利用者認証。",
                 "授業ノート 期末試験対策.md:1201"),
                ("締切台帳に2行を新設した。前者は _hot.md と昨日のノートが根拠", "本人の日記")]:
            m_case("M4", text, False, src)
        m_case("M4", "2026年の調査では前者が多い", True, "年の数字は組ではない")
        # M7: 前置きの語（正直に言うと・実を言うと・本音を言えば・正直なところ）と、「〜のは、」＋名詞だけの分裂文
        for text in ("正直に言うと、まだ答えは出ていない", "実を言うと、測定は2回失敗した", "本音を言えば、もっと早く始めたかった",
                     "正直なところ、効果は小さかった", "見落としがちなのは、電源の容量", "鍵となるのは、現場の声", "見えてきたのは、島の課題"):
            m_case("M7", text, True, "yomiyasu の前置フィラー")
        for text in ("復号できるのはBさんだけ", "いちばん驚いたのは、装置より、人の熱意だった", "実験の結論から言えるのは2点"):
            m_case("M7", text, False, "人の解説・述語のある分裂文")
        # M10: 対応の表・議事録の見出し―中身は記号として外す
        for text, src in [("りんご—青果A、みかん—青果B、ぶどう—青果C、もも—青果A", "授業ノート 演習問題集.md:3418"),
                          ("イベントの提案―予算箱の設置は可決", "学生団体の議事録 2026-05"), ("新入生歓迎―花道", "学生団体の議事録 2026-03")]:
            m_case("M10", text, False, src)
        m_case("M10", "原因は一つ―配線の取り違えだ", True, "試験集 dash-hit-07")
        # M11: 並べる読点は数からも外す。平均の字数は並びを除いた区切りで見る
        for text, src in [
                ("まず，ＬＥＤを点灯した状態で，電圧VFE，VFB，VBE，VFA，VAK，VCE値を測定し，実験ノートに記録する。", "先生 電子工作編テキスト"),
                ("・方法は，停止，跳ね返り，または元の位置に戻す，のいずれでもよい．", "先生 第5回演習課題"),
                ("なお，計算項目の追加，入力方法，結果表示方法は，各自で工夫をし，オリジナリティを高めること", "先生 PL06_dist_modified 26枚目"),
                ("なお、半加算器は、入力信号A、Bに対して、SとCの2種類の異なる出力が得られる回路である", "先生 情報実験の手引書")]:
            m_case("M11", text, False, src)
        # F2: 出典・手段の より と、数・形容詞で結果を書いた比較は対句ではない。述語の無い「量より質」は拾う
        for text in ("表1より、全ての測定点で抵抗値は一定", "図5より、ICはIBにほぼ比例する", "熱拡散により、不純物が横にも広がる",
                     "実測値は理論値よりも5%低い", "中央の値よりも大きい時は右を探す", "以上より、結論は次のとおり",
                     "総務省令和3年版情報通信白書「コロナ禍におけるデジタル活用で生じた課題」より抜粋", "単なる接触不良ではないか"):
            check("F2 3回目: 「%s」→ 対句ではない" % text[:30], not dd.has_contrast(text))
        for text in ("量より質", "速さより確実さ", "便数よりも、時間帯", "装置より、人の熱意だった"):
            check("F2 3回目: 「%s」→ 対句" % text, dd.has_contrast(text))
        pt = good_parts(); pt["slides"][2] = S("トランジスタの特性を測った", ["図4より、VBEが0.5 V以下ではIBはほぼ0", "図5より、ICはIBにほぼ比例する"])
        d = dj(build("f2_zu", pt))
        check("F2 3回目: 本文に「図4より、」「図5より、」の2行（本人 テーマ10 本レポート v4）→ (全体) の F2 も出ない", not got(d, "F2"),
              " | ".join(got(d, "F2")))
        pt = good_parts(); pt["slides"][1] = S("これこそがチームの力にほかならない", ["「半導体のやる気全員の」"])
        d = dj(build("f2_kimezerifu", pt))
        check("F2 3回目: 見出し「これこそがチームの力にほかならない」→ 決め台詞の WARNING だけ（こそ を F2 に二重に数えない）",
              bool(got(d, "AIくさい語の疑い", "WARNING")) and not got(d, "F2"), " | ".join(got(d, "F2") + got(d, "AIくさい")))
        # M9: 名詞の見出し語「〜こと：」は拾わない。動詞の後の条件の と（〜すると・〜書くと）は拾う
        d = m_deck("m9_koto", "授業の最後の確認", ["授業終了時に確認しておくこと：", "ポインタの宣言と使い方"])
        check("M9 3回目: 「授業終了時に確認しておくこと：」（先生 第5回演習課題）→ 出ない", not got(d, "M9"), " | ".join(got(d, "M")))
        d = m_deck("m9_wakatta", "測定の結果", ["分かったこと：", "電流は電圧に比例した"])
        check("M9 3回目: 「分かったこと：」→ 出ない", not got(d, "M9"), " | ".join(got(d, "M")))
        d = m_deck("m9_kakuto", "測定の手順", ["手順を文章で書くと：", "回路を組んで電圧を測る"])
        check("M9 3回目: 「手順を文章で書くと：」（授業ノート 期末試験対策.md）→ WARNING", bool(got(d, "M9", "WARNING")), " | ".join(got(d, "M")))
        # M6: 名詞化の語尾（yomiyasu の例）
        check("M6 3回目: 「観光の再定義」「地域との共創」「島の魅力の再発見」「持続可能性の追求」→ 名詞化で止めた見出し",
              all(dd.M_NOMINAL_END_RE.search(t) for t in ("観光の再定義", "地域との共創", "島の魅力の再発見", "持続可能性の追求")))
        # 決まり文句: シナジーは SOFT（ゲームの仕組みの名前でも使う）。ぜひ〜てみて は目的語・行き先が書いてあれば拾わない
        hard = lambda t: bool(dd.copy_hits(dd.AI_COPY_HARD_RE, t))  # noqa: E731
        soft = lambda t: bool(dd.copy_hits(dd.AI_COPY_SOFT_RE, t))  # noqa: E731
        t = "ホーミング弾・ヒットストップ・カードのシナジー2倍・コンボ係数の割り算なども追加できる。"
        check("決まり文句 3回目: グループの企画仕様書の「カードのシナジー2倍」→ ERROR にせず WARNING（SOFT）", not hard(t) and soft(t))
        for t in ("とても素晴らしい街なのでぜひ一度足を運んでみてください。", "ぜひ一度、八女の茶畑に足を運んでみてください"):
            check("決まり文句 3回目: 行き先・目的語のある案内「%s」→ ERROR にしない" % t[:24], not hard(t))
        for t in ("ぜひ一度試してみてください", "ぜひ使ってみてください", "ぜひ皆さんも活用してみてください"):
            check("決まり文句 3回目: 何を試すかが無い「%s」→ ERROR のまま" % t, hard(t))
        # 抽象の語の一覧は、文章の検査器（作者の環境の jp_ai_check.py）の ABSTRACT_INFO・ABSTRACT_IDEA と同じ語の集合
        # （片方だけ直すとずれる）。文章の検査器は import せず、ソースの文字列の定数だけを読む（並行で直している途中でも動くように）。
        # 文章の検査器はこのリポジトリに含まれないので、無ければ SKIP と出して飛ばす
        import ast
        jp_path = Path.home() / ".claude" / "skills" / "humanize" / "scripts" / "jp_ai_check.py"
        if jp_path.is_file():
            jp_src = jp_path.read_text(encoding="utf-8")
            jp_words = set()
            for node in ast.parse(jp_src).body:
                if isinstance(node, ast.Assign) and any(getattr(t, "id", "") in ("ABSTRACT_INFO", "ABSTRACT_IDEA") for t in node.targets):
                    jp_words |= set(ast.literal_eval(node.value).split("|"))
            dd_words = set((dd.M_ABSTRACT_INFO + "|" + dd.M_ABSTRACT_IDEA + "|" + dd.M_ABSTRACT_SUFFIX).split("|"))
            check("M5 3回目: 抽象の語の一覧が文章の検査器と同じ（%d 語）" % len(dd_words), bool(jp_words) and jp_words == dd_words,
                  "文章だけ %s / スライドだけ %s" % (sorted(jp_words - dd_words), sorted(dd_words - jp_words)))
        else:
            print("[SKIP] M5 3回目: 抽象の語の一覧を文章の検査器と照らす試験（%s が無い）" % jp_path)

        # ================= 2026-10-01 4回目: 試験集の追加分（290件）を直した時に、人の文の母集団で見つけた文 =================
        # 試験集の件そのものは下の「試験集 <種別>」で確かめる。ここは、直し方を決めた人の文（本人・先輩・先生）が当たらないことと、
        # 機械が書いた文（python-docx で作った予習レポート）の型は当たることを固める
        def m_case4(code, text, want, src, rnd="4回目"):
            got_h, got_b = mcodes(text, True), mcodes(text)
            ok = (code in got_h) == want and (code in got_b) == want
            check("%s %s: 「%s」→ %s（%s）" % (code, rnd, text.replace("⏎", "／")[:34], "出る" if want else "出ない", src), ok,
                  "見出し %s / 本文 %s" % (got_h, got_b))

        # 土台に なる は、抽象の主語が書いてある時だけ。効く は、どこで効くか（〜で）が書いてあれば拾わない
        for text, src in [
                ("その土台になったのは、2026年6月の学外研修です。", "本人の報告書"),
                ("まず自分で考え、0から1を生み出す思考力を失わないことが、どの国・どの職場でも通用する技術者の土台になると思っている。",
                 "本人の英文レポート"),
                ("コミュニケーションには土台となる知識、文化、言語などがある。", "先輩 心理学のワークシート"),
                ("授業・研究・PBLで実際に効くシーン。", "本人のグループの Docker 発表"),
                ("静かに壊れたコンデンサを交換した。", "動詞が後ろの名詞（物）を飾る形")]:
            m_case4("M5", text, False, src)
        for text, src in [
                ("この同値関係は、線形代数 I の中核を成す柱であり、今後の単元すべての土台になります。",
                 "python-docx で作った線形代数Ⅰの予習レポート 12（機械の文）"),
                ("黙って壊れていた自動の仕組みを4か所直した。", "動詞が後ろの名詞（抽象）を飾る形")]:
            m_case4("M5", text, True, src)
        # 前置き（M7）: 注意の動詞（注意すべき点は）は本当の指示。ひらがなの「ひとことで」と、後ろが「・・・」の札は拾わない
        for text, src in [
                ("線形探索の際に注意すべき点は、探索範囲の境界条件やループの終了条件を正しく設定することです",
                 "先生の授業資料 H 5枚目"),
                ("ひとことで言うと「アプリの持ち運び用の箱」。", "本人のグループの Docker 発表"),
                ("簡単に言えば・・・", "先生 経済学入門 ＬＭ曲線 2.docx"),
                ("重要な点は2つある。", "数を言い切る文")]:
            m_case4("M7", text, False, src)
        for text, src in [("特筆すべきは、立ち上がり時間である。", "試験集 preface-hit-44 と同じ型"),
                          ("伝えたいのは、仕組みの話です。", "試験集 preface-hit-32 と同じ型")]:
            m_case4("M7", text, True, src)
        # 行の終わりのコロン（M9）: 名詞に数を付けた見出しは、人の授業のスライド・資料で普通。接続の語＋コロンは次の行が文の時だけ
        for name, line, nxt, src in [
                ("m9_rei4", "例（４つの例は、すべて同じ初期化処理）：", "文字列配列を初期化する",
                 "先生 PE11-1rev.pptx 5枚目の行。次の行は試験で置いた日本語の行"),
                ("m9_shijo", "2つの市場の選び方：", "生産物市場と貨幣市場",
                 "先生 経済学入門 マクロ経済について 2.docx の行。次の行は試験で置いた語句"),
                ("m9_tatoeba", "例えば：", "PからQへの移動", "教員の物理の講義資料（試験集 colon_end-miss-32）")]:
            d = m_deck(name, "測定の手順", [line, nxt])
            check("M9 4回目: 「%s」⏎「%s」→ 出ない（%s）" % (line[:20], nxt[:16], src), not got(d, "M9"), " | ".join(got(d, "M")))
        d = m_deck("m9_tsumari", "測定の結果", ["つまり：", "遮断周波数が5%低かった。"])
        check("M9 4回目: 「つまり：」⏎ 文 → WARNING", bool(got(d, "M9", "WARNING")), " | ".join(got(d, "M")))
        # 決まり文句: 催し・場所への誘いは ERROR にしない。読み手に向けて役立てば幸いと締める形は ERROR
        for t in ("そんな気持ちがあれば、ぜひ参加してみてください。", "ぜひ、一度見てみてください。"):
            check("決まり文句 4回目: 催し・場所への誘い「%s」→ ERROR にしない" % t[:20], not hard(t))
        for t in ("本レポートが今後の学習の一助となれば幸いである。", "本報告が今後の実験に役立てば幸いである。"):
            check("決まり文句 4回目: 「%s」→ ERROR" % t[:24], hard(t))
        check("決まり文句 4回目: 読み手への頼み「ご確認いただければ幸いです」→ ERROR にしない", not hard("ご確認いただければ幸いです"))
        # 5回目（2026-10-01 裁定の後）: 案・経験・知見を「〜として」で物に見立てて積む形（文章の検査器の「比喩でごまかす」から移した）。
        # 〜として の無い本人の文（行動量を積み上げる・工程で回路を積み上げる）と、くり返す意味の「経験を重ねる」は拾わない
        for text, src in [
                ("行動量は積み上げてきたものの、学びを立ち止まって言語化し他者へ届ける練習が不足していました。",
                 "本人の授業課題"),
                ("前工程は成膜、リソグラフィ、エッチング、イオン注入を繰り返して回路を積み上げていく。",
                 "本人の研修報告書 v4"),
                ("現場で経験を重ねる。", "くり返す意味の決まった言い方")]:
            m_case4("M5", text, False, src, "5回目")
        for text, src in [("チームの知見を資産として積み上げる。", "試験集 metaphor_other-hit-16"),
                          ("現場の経験を財産として積み上げていく。", "同じ型（〜を〜として積み上げる）")]:
            m_case4("M5", text, True, src, "5回目")

        # ================= 2026-10-01 6回目: 今日の前の版（git d6f2b634）と比べて人の文で増えた誤検知の回帰 =================
        # (a) 本人の判断「① 参考の扱いにする」（2026-10-01）: 落とし込む・架け橋・刺さる は本人が自分の文で使う語なので、
        #     比喩の型でも WARNING にせず INFO の M5参考 で表示だけ。ほかの比喩もある文は WARNING のまま
        def refs(text):
            rows = [r for r in text.split("⏎") if r.strip()]
            return sorted(dd.meaning_refs([("本文",) + dd._rows_to_sents(rows)]))
        for text, src in [
                ("特に、自分たちで考えたアイデアを実際の動きに落とし込んで、何度も上手くいかなかった。", "本人 1年の報告 25F2054.docx"),
                ("外国人材を受け入れることで、他国との交流の架け橋になり、グローバル化が進められる。", "本人 コミュニケーション基礎 移民問題.docx"),
                ("うつ状態の学生についての説明も刺さった。", "本人の研修会の感想文"),
                ("提案3案を具体的なアクションレベルまで落とし込む", "過去のデッキ 07・試験集 metaphor_other-hit-12")]:
            m_case4("M5", text, False, src, "6回目")
            check("M5参考 6回目: 「%s」→ 参考（INFO）に出る（%s）" % (text[:24], src), refs(text) == ["M5"], str(refs(text)))
        text = "課題を紐解き、学びを現場に落とし込む。"
        check("M5参考 6回目: ほかの比喩（紐解く）もある文「%s」→ WARNING の M5 だけ（参考に二重に出さない）" % text,
              "M5" in mcodes(text) and not refs(text), "%s / 参考 %s" % (mcodes(text), refs(text)))
        d = m_deck("m5_ref", "交流の架け橋になる", ["他国との交流の架け橋になり、グローバル化が進む"])
        check("M5参考 6回目: デッキでは INFO「M5参考」で、WARNING の M5 は出ない",
              any(i["severity"] == "INFO" and i["message"].startswith("M5参考") for i in d["issues"])
              and not got(d, "M5", "WARNING"), " | ".join(i["message"][:40] for i in d["issues"] if "M5" in i["message"]))
        # (b) 授業の班発表 I 3枚目の調査理由の箇条書き（M1・M2 の誤検知）
        goban = ("テレビを見る習慣がなく、普段からニュースを見ない。⏎気になるニュースが見つからない。⏎"
                 "電車やバスの中でやることがない。　　　　　　　　　　　　その他・・・")
        m_case4("M1", goban, False, "班発表 I 3枚目。2文目が言いさしの「その他・・・」", "6回目")
        m_case4("M2", goban, False, "班発表 I 3枚目。見 が ニュース の前と後ろの両方にあり、順番が入れ替わっていない", "6回目")
        m_case4("M2", "道具が人を変える。⏎人が道具を選ぶ。", True, "資料の型（語は1回ずつ）", "6回目")
        # (c) 本人の実験 テーマ2 プレレポート・完成レポートの手順5・6（M4 の誤検知）。片方が〜の は後ろの物を飾る節
        for text in ("5.\tMCP4725のVOUTに片方が鰐口クリップの線を接続した。", "6.\tラズベリーパイのGNDに片方が鰐口クリップの線を接続した。"):
            m_case4("M4", text, False, "本人の実験 テーマ2 プレレポート", "6回目")
        m_case4("M4", "片方が全体の品質を決める。", True, "飾る節の名詞が抽象（品質）＝片方は 決める の主語", "6回目")
        # (d) 式・記号が抜けた写し（Word の数式が消えて語の入る所が空いた文）。M3・M11・M1 を見ない
        for code, text, src in [
                ("M3", "　  2.\t電流を、電圧およびで表す。これを(2)式とする。", "本人の実験 プレレポート テーマ4"),
                ("M3", "の状態を、生産物市場の均衡と定義する。", "先生 経済学入門 生産物市場の均衡 2.docx"),
                ("M11", "したがって、生産活動は、のとき行われ、供給関数は、", "先生 経済学入門 3.3 利潤最大化と短期費用関数 2.docx")]:
            m_case4(code, text, False, src, "6回目")
        for t in ("電圧および電流を測った", "はじめに、電源を入れる", "なお、のちに再測定した", "「遅い」と言われた"):
            check("M_GAP_RE 6回目: 語の抜けていない文「%s」→ 抜けとみなさない" % t, not dd.M_GAP_RE.search(t))
        # (e) M1: 同じ事柄の否定と肯定（2つの場合を並べた図の欄）と、逆接の語の後に指示語で前の文を受ける形
        m_case4("M1", "　　　　　2国間に貿易成立しない　　　　　　　　　　2国間に貿易成立", False,
                "先生 経済学入門 比較生産費説 2.docx", "6回目")
        m_case4("M1", "今回は補正を入れていない。ただ、これだと画面の外へ出てしまう。", False,
                "本人 個人レポート team03_25f2054.docx・試験集 neg_then_pos-miss-27", "6回目")
        # (f) M9: コロンの行より下に文字の行が無い（中身は式の画像。先生 経済学入門 乗数分析：（閉鎖経済＃2）解答なし 2.docx）
        d = m_deck("m9_last", "乗数分析の練習", ["次の経済を考える："])
        check("M9 6回目: 「次の経済を考える：」の下に文字の行が無い → 出ない", not got(d, "M9"), " | ".join(got(d, "M")))
        d = m_deck("m9_last_ja", "乗数分析の練習", ["次の経済を考える：", "消費は所得の8割とする。"])
        check("M9 6回目: 同じ行の下に日本語の文がある → WARNING のまま", bool(got(d, "M9", "WARNING")), " | ".join(got(d, "M")))

        # --- 話の順番 flow（2026-10-01 本人の回答「② PREP は既定のまま、別の順も選べる」） ---
        def order_msgs(d, sev=None):
            return [i["message"] for i in d["issues"] if "順番" in i["message"] and (sev is None or i["severity"] == sev)]
        def flow_deck(name, prep, flow=None):
            pt = good_parts()
            pt["spec"] = spec_v2(prep=prep, extra=("flow: %s 2026-10-01 本人 試験\n" % flow) if flow else "")
            return dj(build(name, pt))
        d = flow_deck("flow_none", "C 1 / R 2 / E 3 / E 4 / P 5")
        check("flow: 書かない＝prep → 表紙の次が P でないと ERROR（今までどおり）",
              any("PREP の順番が崩れている" in m and "表紙・目次の次" in m for m in order_msgs(d, "ERROR")), " | ".join(order_msgs(d)))
        d = flow_deck("flow_chrono", "C 1 / R 2 / E 3 / E 4 / P 5", "chronological")
        check("flow=chronological: 表紙の次が P でなくても止めない・INFO に flow を出す",
              not order_msgs(d, "ERROR") and any("flow=chronological" in m for m in order_msgs(d, "INFO")),
              " | ".join(order_msgs(d)))
        d = flow_deck("flow_chrono_last", "C 1 / P 2 / R 3 / E 4 / E 5", "chronological")
        check("flow=chronological: 最後（謝辞の前）が P でない → ERROR",
              any("最後（謝辞の前）が結論(P)でない" in m for m in order_msgs(d, "ERROR")), " | ".join(order_msgs(d)))
        d = flow_deck("flow_problem", "C 1 / E 2 / R 3 / E 4 / P 5", "problem")
        check("flow=problem: 困りごと→原因→対策（対策が最後の P）→ 止めない", not order_msgs(d, "ERROR"), " | ".join(order_msgs(d)))
        d = flow_deck("flow_custom", "C 1 / E 2 / P 3 / E 4 / E 5", "custom")
        check("flow=custom: P が途中に1枚 → 順番では止めない・R が無いのは WARNING",
              not order_msgs(d, "ERROR") and any("理由(R)の枚が無い" in m for m in order_msgs(d, "WARNING")),
              " | ".join(order_msgs(d)))
        d = flow_deck("flow_custom_nop", "C 1 / R 2 / E 3 / E 4 / E 5", "custom")
        check("flow=custom: P が1枚も無い → ERROR", any("結論(P)の枚が1枚も無い" in m for m in order_msgs(d, "ERROR")),
              " | ".join(order_msgs(d)))
        d = flow_deck("flow_bogus", "C 1 / P 2 / R 3 / E 4 / P 5", "zigzag")
        check("flow が一覧に無い名前 → ERROR", any("flow「zigzag」が不明" in m for m in order_msgs(d, "ERROR")),
              " | ".join(order_msgs(d)))
        d = flow_deck("flow_prep_explicit", "C 1 / P 2 / R 3 / E 4 / P 5", "prep")
        check("flow=prep と明記 → 見本と同じく順番の指摘なし", not order_msgs(d), " | ".join(order_msgs(d)))

        # --- F1 最初と最後の P ---
        same = "規則は、機械で止めて初めて守られる"
        pt = good_parts(); pt["slides"][1] = S(same, ["「半導体のやる気全員の」"], hfs=56)
        pt["slides"][4] = S(same, ["講義は4コマ・見学は2か所"], hfs=56)
        d = dj(build("f1_same", pt))
        check("F1: 最初と最後の P の見出しが同じ文 → ERROR（J=1.00）",
              any("J=1.00" in m for m in got(d, "F1", "ERROR")), show(d, "ERROR"))
        pt = good_parts(); pt["slides"][1] = S("1日だけなら、10月1日。15時のTKRIを外さない", ["「半導体のやる気全員の」"])
        pt["slides"][4] = S("1日だけなら10月1日。15時のTKRIを外さない！", ["講義は4コマ・見学は2か所"])
        d = dj(build("f1_near", pt))
        check("F1: 句読点と！だけ違う → ERROR（J≥0.8）", bool(got(d, "F1", "ERROR")))
        check("F1: 見本（言い直してある）では出ない", not got(dj(good), "F1"))
        pt = good_parts(); pt["slides"][1] = S(same); pt["slides"][4] = S(same)
        pt["spec"] = "# Spec Lock\n- delivery: presentation\nbrief_confirmed: 2026-09-28 選択式\n"
        d = dj(build("f1_noprep", pt))
        check("F1: prep 行が無いデッキでは走らない（check_prep が ERROR）", not got(d, "F1")
              and any("PREP の割り当てが spec_lock に無い" in i["message"] for i in d["issues"]))

        # --- F2 対句のまとめ文 ---
        pt = good_parts(); pt["slides"][1] = S("いちばん驚いたのは、装置より、人の熱意だった", ["「半導体のやる気全員の」"])
        d = dj(build("f2_head", pt))
        check("F2: 見出し『装置より、人の熱意だった』→ WARNING",
              any("見出し" in m for m in got(d, "F2", "WARNING")), " | ".join(got(d, "F2")))
        pt = good_parts(); pt["slides"][2] = S("教える側も学ぶ側も、熱意で動いた", ["講義4コマ・見学2か所を1日で"],
                                               eyebrow="02　スライドだけではない")
        d = dj(build("f2_eyebrow", pt))
        check("F2: 小ラベル『02　スライドだけではない』→ WARNING",
              any("小ラベル" in m for m in got(d, "F2", "WARNING")), " | ".join(got(d, "F2")))
        pt = good_parts(); pt["slides"][1] = S("「言語よりも、半導体に興味を持つこと」", ["「半導体のやる気全員の」"])
        d = dj(build("f2_quote", pt))
        check("F2: 「」の中の実際の発言は対象外", not got(d, "F2"), " | ".join(got(d, "F2")))
        pt = good_parts(); pt["slides"][2] = S("教える側も学ぶ側も、熱意で動いた", ["講義4コマ・見学2か所を1日で", "警告ではなく、止める"])
        d = dj(build("f2_body1", pt))
        check("F2: 本文に1回だけ → 出ない", not got(d, "F2"), " | ".join(got(d, "F2")))
        pt["slides"][3] = S("8月18日、食堂で聞いた一言", ["「進路を考えて行動しただけ」", "便数よりも、時間帯"])
        d = dj(build("f2_body2", pt))
        check("F2: 本文にもう1回（デッキで2回）→ WARNING を1件",
              len([m for m in got(d, "F2", "WARNING") if "本文" in m]) == 1, " | ".join(got(d, "F2")))
        pt = good_parts(); pt["slides"][1] = S("講義は3倍より多い4コマ", ["「半導体のやる気全員の」"])
        d = dj(build("f2_yori", pt))
        check("F2: 『3倍より多い』（より の後に読点なし）→ 出ない", not got(d, "F2"), " | ".join(got(d, "F2")))
        # 2026-10-01: 言われていない誤解を否定してから入る「単なる〜ではない」（yomiyasu の語の一覧が元）
        pt = good_parts(); pt["slides"][1] = S("AIは単なる道具ではない", ["「半導体のやる気全員の」"])
        d = dj(build("f2_tannaru", pt))
        check("F2: 見出し『AIは単なる道具ではない』→ WARNING",
              any("見出し" in m for m in got(d, "F2", "WARNING")), " | ".join(got(d, "F2")))
        pt = good_parts(); pt["slides"][1] = S("速度だけの話ではない", ["「半導体のやる気全員の」"])
        d = dj(build("f2_dakeno", pt))
        check("F2: 見出し『速度だけの話ではない』→ WARNING",
              any("見出し" in m for m in got(d, "F2", "WARNING")), " | ".join(got(d, "F2")))
        pt = good_parts(); pt["slides"][1] = S("測定値の差は単なる誤差と判断した", ["「半導体のやる気全員の」"])
        d = dj(build("f2_tannaru_ok", pt))
        check("F2: 『単なる誤差と判断した』（否定が無い）→ 出ない", not got(d, "F2"), " | ".join(got(d, "F2")))

        # --- F3 片側だけの縦線 ---
        card = '<rect x="96" y="370" width="1088" height="200" fill="#EAF4FB"/>'
        bar = '<rect x="96" y="370" width="10" height="200" fill="#E08A2E"/>'
        pt = good_parts(); pt["slides"][3] = GOOD_SLIDES[3] + card + bar
        d = dj(build("f3_card", pt))
        check("F3: 薄い箱＋左端の10px の色線 → WARNING", any("カード＋左の色線 04" in m for m in got(d, "F3", "WARNING")),
              " | ".join(got(d, "F3")))
        pt = good_parts(); pt["slides"][0] = '<rect x="0" y="0" width="24" height="720" fill="#125E90"/>' + GOOD_SLIDES[0]
        d = dj(build("f3_band", pt))
        check("F3: x=0・幅24・高さ720 の帯 → WARNING（端の帯）", any("端の帯 01" in m for m in got(d, "F3", "WARNING")))
        pt = good_parts(); pt["slides"][3] = GOOD_SLIDES[3] + card + '<rect x="96" y="600" width="1088" height="4" fill="#125E90"/>'
        d = dj(build("f3_none", pt))
        check("F3: 薄い箱だけ・横の罫線 → 出ない", not got(d, "F3"), " | ".join(got(d, "F3")))
        pt = good_parts(); pt["slides"][3] = GOOD_SLIDES[3] + '<rect x="640" y="250" width="2" height="400" fill="#125E90"/>'
        d = dj(build("f3_divider", pt))
        check("F3: カードにも端にも接しない区切り線 → 出ない", not got(d, "F3"), " | ".join(got(d, "F3")))

        # --- F4 全部同じ入り方 ---
        six = "C 1 / P 2 / R 3 / E 4 / E 5 / P 6"
        pt = good_parts()
        pt["slides"] = [GOOD_SLIDES[0]] + [S(h, b, eyebrow="0%d　ラベル" % k) for k, (h, b) in enumerate([
            ("留学生の一言で、東湖の熱意を知った", ["「半導体のやる気全員の」"]),
            ("教える側も学ぶ側も、熱意で動いた", ["講義4コマ・見学2か所を1日で"]),
            ("8月18日、食堂で聞いた一言", ["「進路を考えて行動しただけ」"]),
            ("1976年、学ぶところから始まった", ["技術移転は1976年"]),
            ("8月18日の一言で、来年の挑戦を決めた", ["講義は4コマ・見学は2か所"])], 1)]
        pt["spec"] = spec_v2(six)
        d = dj(build("f4_same", pt))
        check("F4: P/R/E の5枚すべて同じ小ラベル＋見出し → WARNING（100%）",
              any("100%" in m for m in got(d, "F4", "WARNING")), " | ".join(got(d, "F4")))
        pt = good_parts()
        pt["slides"] = [GOOD_SLIDES[0]] + [S(h, b, eyebrow=(("0%d　ラベル" % k) if k <= 4 else None)) for k, (h, b) in enumerate([
            ("留学生の一言で、東湖の熱意を知った", ["「半導体のやる気全員の」"]),
            ("教える側も学ぶ側も、熱意で動いた", ["講義4コマ・見学2か所を1日で"]),
            ("8月18日、食堂で聞いた一言", ["「進路を考えて行動しただけ」"]),
            ("1976年、学ぶところから始まった", ["技術移転は1976年"]),
            ("英語で2時間、議論した", ["修了証は2枚"]),
            ("8月18日の一言で、来年の挑戦を決めた", ["講義は4コマ・見学は2か所"])], 1)]
        pt["spec"] = spec_v2("C 1 / P 2 / R 3 / E 4 / R 5 / E 6 / P 7")
        d = dj(build("f4_67", pt))
        check("F4: 6枚のうち小ラベルは4枚（67%）→ 出ない", not got(d, "F4"), " | ".join(got(d, "F4")))
        pt = good_parts()
        pt["slides"] = [GOOD_SLIDES[0]] + [S(h, b, eyebrow="0%d　ラベル" % k) for k, (h, b) in enumerate([
            ("留学生の一言で、東湖の熱意を知った", ["「半導体のやる気全員の」"]),
            ("8月18日、食堂で聞いた一言", ["「進路を考えて行動しただけ」"]),
            ("8月18日の一言で、来年の挑戦を決めた", ["講義は4コマ・見学は2か所"])], 1)]
        pt["spec"] = spec_v2("C 1 / P 2 / E 3 / P 4")
        d = dj(build("f4_small", pt))
        check("F4: P/R/E が3枚（全部同じ）→ 出ない（4枚未満）", not got(d, "F4"))

        # --- F5 PREP の札の小ラベル ---
        def f5(name, slide2):
            pt = good_parts(); pt["slides"][1] = slide2
            return [i["message"] for i in dj(build(name, pt))["issues"]
                    if i["file"] == "02_page.svg" and "PREP の札" in i["message"]]
        check("F5: 小ラベル『結論』（コロン無し）→ WARNING",
              bool(f5("f5_tag", S("留学生の一言で、東湖の熱意を知った", ["「半導体のやる気全員の」"], eyebrow="結論"))))
        check("F5: 小ラベル『6日間でいちばん驚いたこと』→ 出ない",
              not f5("f5_ok", S("留学生の一言で、東湖の熱意を知った", ["「半導体のやる気全員の」"], eyebrow="6日間でいちばん驚いたこと")))
        check("F5: 見出し『結論が出るまでの3日間』→ 出ない（完全一致ではない）",
              not f5("f5_head", S("結論が出るまでの3日間", ["「半導体のやる気全員の」"])))
        check("F5: 小ラベル『01　教える側の熱量』→ 出ない（番号は F4 の対象）",
              not f5("f5_num", S("留学生の一言で、東湖の熱意を知った", ["「半導体のやる気全員の」"], eyebrow="01　教える側の熱量")))

        # --- F6 情報の無い飾り ---
        deco = ('<g id="decor"><circle cx="1000" cy="200" r="90" fill="#EAF4FB"/>'
                + "".join('<line x1="%d" y1="120" x2="%d" y2="280" stroke="#125E90"/>' % (940 + 20 * k, 940 + 20 * k)
                          for k in range(6)) + '</g>')
        pt = good_parts(); pt["slides"][0] = GOOD_SLIDES[0] + deco
        d = dj(build("f6_decor", pt))
        check("F6: <g id=decor> に円1つと細線6本・文字なし → WARNING", bool(got(d, "F6", "WARNING")))
        pt = good_parts(); pt["slides"][0] = GOOD_SLIDES[0] + deco.replace(
            '</g>', '<image x="900" y="100" width="200" height="200" href="images/me.jpg"/></g>')
        d = dj(build("f6_img", pt))
        check("F6: decor に本人の写真がある → 出ない", not got(d, "F6"))
        pt = good_parts(); pt["slides"][0] = GOOD_SLIDES[0] + (
            '<g id="decor"><line x1="900" y1="100" x2="900" y2="200" stroke="#125E90"/>'
            '<line x1="920" y1="100" x2="920" y2="200" stroke="#125E90"/></g>')
        d = dj(build("f6_two", pt))
        check("F6: decor に線2本だけ → 出ない", not got(d, "F6"))
        pt = good_parts(); pt["slides"][0] = GOOD_SLIDES[0] + deco
        pt["spec"] = spec_v2(extra="decor_ok: 1 町家の立面＝発表の題材\n")
        d = dj(build("f6_ok", pt))
        check("F6: spec_lock に decor_ok: 1 → INFO だけ", bool(got(d, "F6", "INFO")) and not got(d, "F6", "WARNING"))

        # --- F7 R/E の証拠の下限 ---
        def f7(name, slides_patch, brief_patch=None):
            pt = good_parts()
            for k, v in slides_patch.items():
                pt["slides"][k] = v
            if brief_patch:
                brief_patch(pt["brief"])
            d = dj(build(name, pt))
            return [i["message"] for i in d["issues"] if i["message"].startswith("F7") and i["severity"] == "ERROR"]
        check("F7: R の枚が見出し＋本文3行だけ（数字・「」・画像なし）→ ERROR",
              bool(f7("f7_r", {2: S("教える側も学ぶ側も、熱意で動いた", ["講義の後に見学", "質問に全部答える", "最後まで手を挙げる"])})))
        check("F7: E の枚の数字が行頭の『01　』とフッターだけ → ERROR",
              bool(f7("f7_enum", {3: S("食堂で聞いた一言", ["進路の話をした"], eyebrow="01　食堂の夕方")})))
        check("F7: 本文に『13枚中13枚が22px未満』→ 出ない",
              not f7("f7_num", {3: S("食堂で聞いた一言", ["13枚中13枚が22px未満"])}))
        check("F7: 400×300 の写真（キャンバスの13%）→ 出ない",
              not f7("f7_photo", {3: S("食堂で聞いた一言", ["夕方の食堂"],
                                     extra='<g id="photo"><image x="700" y="300" width="400" height="300" href="images/a.jpg"/></g>')}))
        check("F7: 本文に「進路を考えて行動しただけ」→ 出ない（見本の4枚目）", not f7("f7_quote", {}))
        flow = ('<g id="flow">' + "".join('<rect x="%d" y="400" width="180" height="80" fill="#EAF4FB"/>' % (96 + 200 * k)
                                          for k in range(5))
                + "".join('<text x="%d" y="450" font-family="Yu Gothic" font-size="28">工程%s</text>' % (110 + 200 * k, "一二三四"[k])
                          for k in range(4)) + '</g>')
        s4_flow = S("食堂で聞いた一言", ["講義の流れ"], extra=flow)
        check("F7: flow（図形5・text 4）＋ brief.proof の diagram（出典付き）→ 出ない",
              not f7("f7_flow_ok", {3: s4_flow}, lambda b: b["proof"].append(
                  {"id": "D1", "for": "R1", "kind": "diagram", "src": "講義資料.pdf:3", "quote": "", "slides": [4]})))
        check("F7: 同じ flow でも brief.proof に登録が無い → ERROR", bool(f7("f7_flow_ng", {3: s4_flow})))

        # --- F8 R/E が薄すぎる ---
        s3_80 = S("熱意" + "あ" * 18, ["4コマ" + "い" * 27, "う" * 30])   # 見出し20字＋本文30字×2＝80字
        def f8(name, note3, with_notes=True):
            pt = good_parts(); pt["slides"][2] = s3_80
            pt["notes"][2] = note3
            if not with_notes:
                pt["notes"] = None
            d = dj(build(name, pt))
            return [i["message"] for i in d["issues"] if i["message"].startswith("F8")]
        r80 = f8("f8_thin", "（約20秒）" + "う" * 95)
        check("F8: R の枚 スライド80字＋ノート95字＝175字 → WARNING", any("175 字" in m for m in r80), " | ".join(r80))
        check("F8: スライド80字＋ノート150字＝230字 → 出ない", not f8("f8_ok", "（約20秒）" + "う" * 150))
        check("F8: notes/total.md が無い → 走らない", not f8("f8_nonotes", "", with_notes=False))

        # --- T1x 人の言葉は100字の目安で数えない ---
        def t1(body_lines):
            return [(i["severity"], i["message"], i.get("fix", "")) for i in one(
                H + "".join('<text x="80" y="%d" font-family="Yu Gothic" font-size="28">%s</text>' % (200 + 40 * k, t)
                            for k, t in enumerate(body_lines)))["issues"] if "オンスライド" in i["message"]]
        # H（言い切りの見出し）8字 + 本文102字 = 110字。うち「」20字
        r_q = t1(["「" + "あ" * 18 + "」" + "い" * 20, "う" * 31, "え" * 31])
        check("T1x: 110字のうち「」20字 → 90字と数えて WARNING は出ない", not r_q, str(r_q)[:120])
        r_nq = t1(["い" * 40, "う" * 31, "え" * 31])
        check("T1x: 110字で引用なし → WARNING（新しい直し方の文）",
              any(s == "WARNING" and "証拠（数字・写真・人の言葉・場面）はスライドに残し" in f for s, m, f in r_nq), str(r_nq)[:160])
        r_big = t1(["「" + "あ" * 28 + "」" + "い" * 10, "う" * 38, "え" * 38, "お" * 36])
        check("T1x: 160字のうち「」30字 → ERROR（150字の停止は引用も数える）",
              any(s == "ERROR" for s, m, f in r_big), str(r_big)[:160])

        # ================= 2026-09-28 v3: 目次 A（A0〜A3） =================
        def agenda(items, title="目次"):
            s = TX(96, 150, 48, title)
            for k, t in enumerate(items):
                s += TX(96, 250 + 64 * k, 32, t)
            return s

        AG_OK = ["01　留学生の一言と熱意", "02　教える側の熱意", "03　来年の挑戦"]
        PREP9 = "C 1 / A 2 / P 3 / E 4 / R 5 / E 6-7 / P 8 / T 9"
        THANKS = S("ありがとうございました", ["学生支援室の皆さま"])

        def a_deck(name, prep, items=None, agenda_line="", slides=None, flags=()):
            pt = good_parts()
            if slides is None:
                slides = [GOOD_SLIDES[0], agenda(items or AG_OK), GOOD_SLIDES[1], GOOD_SLIDES[3], GOOD_SLIDES[2],
                          S("食堂で聞いた二言目", ["「死ぬ気で中国語を勉強していた」"]),
                          S("英語で2時間、議論した", ["修了証は2枚"]), GOOD_SLIDES[4], THANKS]
            pt["slides"] = slides
            pt["spec"] = spec_v2(prep, agenda=agenda_line)
            return dj(build(name, pt), *flags)

        def a_msgs(d, sev=None):
            return [i["message"] for i in d["issues"]
                    if re.match(r"A[0-3] ", i["message"]) and (sev is None or i["severity"] == sev)]

        d = a_deck("a_ok", PREP9)
        check("A: C 1 / A 2 / P 3 / E 4 / R 5 / E 6-7 / P 8 / T 9 が通る（PREP の ERROR も A0〜A3 も出ない）",
              not prep_errs(d) and not a_msgs(d), " | ".join(prep_errs(d) + a_msgs(d)))
        d = a_deck("a_after_p", "C 1 / P 2 / A 3 / E 4 / R 5 / E 6-7 / P 8 / T 9")
        check("A: C 1 / P 2 / A 3 … → ERROR（目次が表紙の直後にない）",
              any("目次(A)が表紙(C)の直後にない" in m for m in prep_errs(d)), " | ".join(prep_errs(d)))
        AT3 = "agenda: at 3 2026-10-16 本人 前提のニュースを表紙の次に置く\n"
        d = a_deck("a_at_ok", "C 1 / P 2 / A 3 / E 4 / R 5 / E 6-7 / P 8 / T 9", agenda_line=AT3)
        check("A: C 1 / P 2 / A 3 … に agenda: at 3（理由つき）→ 順番の ERROR は出ず INFO",
              not prep_errs(d) and any(i["severity"] == "INFO" and "agenda: at 3" in i["message"] for i in d["issues"]),
              " | ".join(prep_errs(d)))
        d = a_deck("a_at_wrong", "C 1 / P 2 / A 3 / E 4 / R 5 / E 6-7 / P 8 / T 9",
                   agenda_line="agenda: at 4 2026-10-16 本人 前提のニュースを表紙の次に置く\n")
        check("A: agenda: at 4 なのに目次は3枚目 → ERROR のまま",
              any("目次(A)が表紙(C)の直後にない" in m for m in prep_errs(d)), " | ".join(prep_errs(d)))
        d = a_deck("a_at_noreason", "C 1 / P 2 / A 3 / E 4 / R 5 / E 6-7 / P 8 / T 9", agenda_line="agenda: at 3\n")
        check("A: agenda: at 3 に理由が無い → ERROR のまま",
              any("目次(A)が表紙(C)の直後にない" in m for m in prep_errs(d)), " | ".join(prep_errs(d)))
        d = a_deck("a_two", "C 1 / A 2-3 / P 4 / R 5 / E 6-7 / P 8 / T 9")
        check("A: 目次(A)が2枚 → ERROR", any("目次(A)が 2 枚" in m for m in prep_errs(d)), " | ".join(prep_errs(d)))
        EIGHT = [GOOD_SLIDES[0], GOOD_SLIDES[1], GOOD_SLIDES[3], GOOD_SLIDES[2], GOOD_SLIDES[3], GOOD_SLIDES[3],
                 GOOD_SLIDES[4], THANKS]
        PREP8 = "C 1 / P 2 / E 3 / R 4 / E 5-6 / P 7 / T 8"     # 研修報告 v2 の prep（表紙・謝辞を除いて6枚）
        d = a_deck("a0_none", PREP8, slides=EIGHT)
        check("A0: 表紙・謝辞を除いて6枚で A 無し → ERROR", any(m.startswith("A0") for m in a_msgs(d, "ERROR")),
              " | ".join(a_msgs(d)))
        d = a_deck("a0_off", PREP8, slides=EIGHT, agenda_line="agenda: none 2026-09-28 本人 3分の立ち話なので\n")
        check("A0: agenda: none 付き → INFO だけ",
              bool(a_msgs(d, "INFO")) and not a_msgs(d, "ERROR") and not a_msgs(d, "WARNING"), " | ".join(a_msgs(d)))
        d = a_deck("a0_small", "C 1 / P 2 / E 3 / P 4",
                   slides=[GOOD_SLIDES[0], GOOD_SLIDES[1], GOOD_SLIDES[3], GOOD_SLIDES[4]])
        check("A0: 表紙を除いて3枚で A 無し → 何も出ない", not a_msgs(d), " | ".join(a_msgs(d)))
        d = a_deck("a0_legacy", PREP8, slides=EIGHT, flags=("--legacy",))
        check("A0 --legacy: 同じデッキで WARNING（ERROR は出ない）",
              any(m.startswith("A0") for m in a_msgs(d, "WARNING")) and not a_msgs(d, "ERROR"), " | ".join(a_msgs(d)))
        d = a_deck("a2_vague", PREP9, items=["01　留学生の一言と熱意", "02　教える側の熱意", "03　まとめ"])
        check("A2: 項目「まとめ」→ ERROR", any("まとめ" in m for m in a_msgs(d, "ERROR")), " | ".join(a_msgs(d)))
        d = a_deck("a1_six", PREP9, items=["01　留学生の一言", "02　教える側の熱意", "03　食堂の一言",
                                           "04　英語で議論", "05　来年の挑戦", "06　応募の窓口"])
        check("A1: 項目が6個 → WARNING", any("6 個" in m for m in a_msgs(d, "WARNING")), " | ".join(a_msgs(d)))
        numbered = TX(96, 150, 48, "目次") + "".join(
            TX(96, 260 + 80 * k, 40, "0%d" % (k + 1)) + TX(200, 260 + 80 * k, 32, t)
            for k, t in enumerate(["留学生の一言と熱意", "教える側の熱意", "来年の挑戦"]))
        d = a_deck("a1_numbers", PREP9, slides=[GOOD_SLIDES[0], numbered] + [
            GOOD_SLIDES[1], GOOD_SLIDES[3], GOOD_SLIDES[2], GOOD_SLIDES[3], GOOD_SLIDES[3], GOOD_SLIDES[4], THANKS])
        check("A1: 番号（01）と項目が別の <text> でも3個と数える → 出ない", not a_msgs(d), " | ".join(a_msgs(d)))
        d = a_deck("a3_unrelated", PREP9, items=["01　東京の天気", "02　京都の紅葉", "03　大阪の食べ物"])
        check("A3: 後の枚と関係の無い項目だけ → WARNING", any(m.startswith("A3") for m in a_msgs(d, "WARNING")),
              " | ".join(a_msgs(d)))

        # 回帰: 既存13本の prep の読み方が変わらない（A を足す前の読み方と比べる）
        OLD_TOKEN_RE = re.compile(r'([CPRET])\s*[:=]?\s*(\d+(?:\s*[-〜~]\s*\d+)?(?:\s*,\s*\d+(?:\s*[-〜~]\s*\d+)?)*)')

        def old_parse(body):
            roles = {}
            for role, spans in OLD_TOKEN_RE.findall(body):
                for span in spans.split(','):
                    nums = [int(x) for x in re.split(r'[-〜~]', span.strip())]
                    for n in range(nums[0], nums[-1] + 1):
                        roles.setdefault(n, []).append(role.upper())
            return roles

        def old_parse_dir(proj):
            for cand in (proj / "spec_lock.md", proj / "design_spec.md"):
                if cand.is_file():
                    m = dd.PREP_LINE_RE.search(cand.read_text(encoding="utf-8", errors="replace"))
                    if m:
                        return old_parse(m.group(1))
            return None

        KNOWN = ["C 1 / P 2 / R 3 / E 4 / P 5", "C 1 / P 2 / R 3 / E 4 / R 5 / E 6 / R 7 / E 8 / P 9",
                 "C 1 / P 2 / R 3 / E 4-5 / R 6 / E 7 / R 8 / E 9 / P 10 / T 11",
                 "C 1 / P 2 / E 3 / R 4 / E 5-6 / P 7 / T 8"]
        diff = []
        for k, line in enumerate(KNOWN):
            p = tmp / ("prep_reg%d" % k)
            p.mkdir()
            (p / "spec_lock.md").write_text("# Spec Lock\nprep: %s\n" % line, encoding="utf-8")
            if dd.parse_prep(p) != old_parse(line):
                diff.append(line)
        # 作者の環境では ~/_slidegen_work にある過去のデッキ13本の名前をここに並べていた。公開版は環境変数
        # SLIDEGEN_PAST_DECKS（カンマ区切りのフォルダ名）で渡した物だけを見る（無ければ見本4本だけ）
        PAST = [x.strip() for x in os.environ.get("SLIDEGEN_PAST_DECKS", "").split(",") if x.strip()]
        real = 0
        for name in PAST:
            proj = BASE / "_slidegen_work" / name
            if not proj.is_dir():
                continue
            real += 1
            if dd.parse_prep(proj) != old_parse_dir(proj):
                diff.append(name)
        check("回帰: 既存の prep（見本4本＋実物 %d/%d 本）の parse_prep の結果が A を足す前と同じ" % (real, len(PAST)),
              not diff, " | ".join(diff))

        # ================= 2026-09-28 v3: 資料の種類 genre（G1〜G9） =================
        GENRE_LIST = ["experience", "progress", "proposal", "research", "explainer", "notice", "general"]
        EXPECT = {   # 仕様の表（E=ERROR W=WARNING -=出ない。'*' はその他のジャンル）
            "G1": {"experience": "E", "progress": "E"},
            "G2": {"proposal": "E", "research": "E", "progress": "W", "general": "W"},
            "G3b": {"proposal": "E", "research": "E", "*": "W"},
            "G3a": {"*": "W"},
            "G4a": {"*": "E"},
            "G4b": {"*": "W"},
            "G4c": {"notice": "W"},
            "G5": {"experience": "W", "proposal": "W", "research": "W"},
            "G7": {"notice": "-", "*": "W"},
            "G8": {"*": "W"},
            "G9": {"research": "W"},
        }
        OV_OK = [{"k": "日付", "v": "8月18日", "src": "memo.md:4", "quote": "8月18日の夕方"}]

        def expect(g, genre):
            t = EXPECT[g]
            return t.get(genre, t.get("*", "-"))

        def gsev(d, g):
            return set(i["severity"] for i in d["issues"]
                       if i["message"].startswith(g + " ") and i["severity"] in ("ERROR", "WARNING"))

        def fits(found, e):
            if e == "E":
                return found == {"ERROR"}
            if e == "W":
                return found == {"WARNING"}
            return not found

        def genre_parts(genre, bad=0):
            """bad=0: どのジャンルでも G が出ない見本 / bad=1: G3b 以外を全部踏む / bad=2: G3b だけを踏む"""
            pt = good_parts()
            slides = list(GOOD_SLIDES) + [S("参考文献", ["研修メモ（2026年8月18日）"])]
            notes = list(GOOD_NOTES) + ["（約10秒）参考文献の一覧。"]
            notes[0] += "3日目は8月18日でした。"                  # G1: 概要の事実（overview.v）
            notes[3] += "同世代の行動に背中を押されました。"         # G5: 目的（me.why）
            notes[4] += "応募は学生支援室へ。"                     # G4c: 窓口
            pt["brief"]["overview"] = copy.deepcopy(OV_OK)
            prep = "C 1 / P 2 / R 3 / E 4 / P 5 / T 6"
            if bad == 1:
                pt["brief"]["overview"][0]["v"] = "西浜"                                     # G1
                slides[0] = S("東湖で見た半導体の熱意", ["山田 太郎　2026年9月"])                   # G7
                slides[2] = S("TKRIでも、熱意で動いた", ["講義の後に見学を回った", "※8月17日の研修メモから"])   # G2・G8
                slides[3] = S("8月18日、食堂で聞いた一言", ["「進路を考えて行動しただけ」"])        # G3a
                slides[4] = S("あの一言で、挑戦を決めた", ["講義は4コマ・見学は2か所"])            # G4a・G4b・G4c
                notes[3] = GOOD_NOTES[3]                                                       # G5
                notes[4] = "（約40秒）最後にもう一度。あの一言で、挑戦を決めました。"
                slides, notes = slides[:5], notes[:5]                                          # G9
                prep = "C 1 / P 2 / R 3 / E 4 / P 5"
            elif bad == 2:
                slides[2] = S("教える側も学ぶ側も、熱意で動いた", ["講義4コマ・見学2か所を1日で"])   # G3b
            pt["slides"] = slides
            pt["notes"] = notes
            pt["brief"]["prep"] = prep
            gl = "" if genre == "general" else "## genre\n- genre: %s\n" % genre
            pt["spec"] = spec_v2(prep, extra=gl)
            return pt

        for genre in GENRE_LIST:
            dg = dj(build("g_ok_%s" % genre, genre_parts(genre)))
            bad = [g for g in EXPECT if gsev(dg, g)]
            check("genre=%s: 見本では G が1つも出ない" % genre, not bad,
                  " | ".join(i["message"][:50] for i in dg["issues"]
                             if i["message"].startswith("G") and i["severity"] != "INFO")[:300])
            d1 = dj(build("g_bad1_%s" % genre, genre_parts(genre, 1)))
            d2 = dj(build("g_bad2_%s" % genre, genre_parts(genre, 2)))
            for g in EXPECT:
                e = expect(g, genre)
                found = gsev(d2 if g == "G3b" else d1, g)
                check("%s genre=%s: %s" % (g, genre, {"E": "ERROR", "W": "WARNING", "-": "出ない"}[e]), fits(found, e),
                      "found=%s" % sorted(found))
            if genre == "general":
                check("genre 未記載 → INFO「genre 未記載」", any("genre 未記載" in i["message"] and i["severity"] == "INFO"
                                                             for i in d1["issues"]))

        pt = genre_parts("experience"); pt["brief"]["overview"] = []
        d = dj(build("g1_empty", pt))
        check("G1: experience で overview が空 → ERROR", any("overview" in m for m in got(d, "G1", "ERROR")),
              " | ".join(got(d, "G1")))
        pt = genre_parts("explainer"); pt["brief"]["overview"] = []
        check("G1: explainer で overview が空 → 出ない", not got(dj(build("g1_empty_ex", pt)), "G1"))
        pt = genre_parts("experience"); pt["brief"]["overview"][0]["quote"] = "8月20日の朝"
        d = dj(build("g1_trace", pt))
        check("G1: overview の quote が出典の行に無い → ERROR（C3 と同じ照合）",
              any("作文の疑い" in m for m in got(d, "G1", "ERROR")), " | ".join(got(d, "G1")))
        pt = genre_parts("general"); pt["brief"]["genre"] = "research"
        d = dj(build("g_brief_genre", pt))
        check("genre: spec_lock に無ければ brief.json の genre を使う", any(
            i["message"] == "genre: research" for i in d["issues"]))
        pt = genre_parts("general"); pt["spec"] = spec_v2("C 1 / P 2 / R 3 / E 4 / P 5 / T 6", extra="- genre: report\n")
        d = dj(build("g_unknown", pt))
        check("genre: 一覧に無い値 → WARNING（general として検査）",
              any("genre「report」は不明" in i["message"] and i["severity"] == "WARNING" for i in d["issues"]))

        # 誤検知の回帰（過去のデッキの実物の文から）
        def L(t):
            return dd.TextLine(96, 300, t, 32, "start", 1)
        cnt = [dd.data_count([L(t)]) for t in ("第3回 九州半導体産業展", "9月30日（水）・10月1日（木）",
                                                "10:00〜17:00　入場は事前登録制", "01　書いても守られない",
                                                "講義は3回", "13枚中13枚", "34.8→10.2KB", "4つのブース")]
        check("回帰 expo: 「第3回」・日付・時刻・行頭の番号は数＋単位に数えない（講義は3回・13枚・KB・4つは数える）",
              cnt == [0, 0, 0, 0, 1, 2, 1, 1], str(cnt))
        pt = genre_parts("proposal")
        pt["slides"][2] = S("第3回の展示会で、熱意で動いた", ["10月1日 15:00〜16:00", "※公式の時間割から"])
        d = dj(build("g_expo", pt))
        check("回帰 expo: R/E の数字が「第3回」と日時だけ → G2 ERROR（データ0）・G3b は出ない",
              bool(got(d, "G2", "ERROR")) and not got(d, "G3b"), " | ".join(got(d, "G2") + got(d, "G3b")))
        pt = genre_parts("explainer")
        pt["slides"][0] = S("書いた規則は、なぜ守られないのか", ["勉強会｜5分", "2026年9月28日　山田 太郎"])
        d = dj(build("g_rules", pt))
        check("回帰 rules: 表紙の「勉強会｜5分」＋「2026年9月28日　山田 太郎」→ G7 も G3b も出ない",
              not got(d, "G7", "WARNING") and not got(d, "G3b"), " | ".join(got(d, "G7") + got(d, "G3b")))
        pt = genre_parts("research")
        pt["slides"][0] = S("東湖で見た半導体の熱意", ["9 August 2026 · Nagoya, Japan"])
        d = dj(build("g_en_date", pt))
        check("回帰 英語の日付: 英語の日付「9 August 2026」を報告日と数える → G7 は出ない", not got(d, "G7", "WARNING"),
              " | ".join(got(d, "G7")))
        dates = [any(rx.search(t) for rx in dd.COVER_DATE_RES) for t in (
            "August 9, 2026", "2026年8月16日〜22日", "2026年9月2日（火）｜市民交流館", "9月30日（水）")]
        check("G7: 『August 9, 2026』・『2026年9月2日（火）』は日付、期間の端・年の無い日付は数えない",
              dates == [True, False, True, False], str(dates))
        pt = genre_parts("explainer")
        pt["slides"][2] = S("QRコードで答えた人の熱意", ["講義4コマ・見学2か所を1日で", "JR駅から徒歩で", "※8月17日の研修メモから"])
        d = dj(build("g_qr_jr", pt))
        check("回帰 QR・JR: QR・JR は説明なしでよい（既定の許可リスト）→ G8 は出ない", not got(d, "G8"), " | ".join(got(d, "G8")))

        def g8(name, line, extra_spec=""):
            pt = genre_parts("explainer")
            pt["slides"][2] = S("教える側も学ぶ側も、熱意で動いた", ["講義4コマ・見学2か所を1日で", line, "※8月17日の研修メモから"])
            if extra_spec:
                pt["spec"] = pt["spec"] + extra_spec
            return got(dj(build(name, pt)), "G8")
        check("G8: 「TKRI（東湖工業研究所）」→ 出ない", not g8("g8_after", "TKRI（東湖工業研究所）"))
        check("G8: 「東湖工業研究所（TKRI）」→ 出ない", not g8("g8_before", "東湖工業研究所（TKRI）"))
        check("G8: 説明の無い「TKRIで学ぶ」→ WARNING", bool(g8("g8_bare", "TKRIで学ぶ")))
        check("G8: spec_lock の terms_ok: TKRI → 出ない", not g8("g8_ok", "TKRIで学ぶ", "terms_ok: TKRI, ABC\n"))
        check("G8: 数字の後の単位「10.2KB」は略語に数えない", not g8("g8_unit", "指示書は34.8→10.2KB"))
        pt = genre_parts("research")
        pt["slides"][5] = S("参考文献", ["[1] 水系キャパシタの電圧窓", "ACS Sustainable Chem. Eng. (2021)"])
        d = dj(build("g8_refs", pt))
        check("G8: 参考文献の枚の誌名（ACS）は見ない（過去の研究発表の 09 の回帰）", not got(d, "G8"), " | ".join(got(d, "G8")))

        # ================= 2026-09-28 v3: 引用の組み方（Q1・Q2）と tspan に割れた引用（F7） =================
        def qmsgs(svg):
            return [i["message"][:2] for i in one(svg)["issues"] if i["message"].startswith(("Q1", "Q2"))]

        def quote3(x1, x2, fs=40, y=360):
            return ('<text font-family="Yu Gothic" font-size="%d"><tspan x="%d" y="%d">「英語を勉強する</tspan>'
                    '<tspan x="%d" y="%d">だけで</tspan><tspan x="%d" y="%d">満足していた」</tspan></text>'
                    % (fs, x1, y, x2, y + 60, x2, y + 120))
        V2_06_AFTER = ('<text x="640" y="380" font-family="Yu Gothic" font-size="56" text-anchor="middle">'
                       '「言語よりも、半導体に興味を持つこと」</text>')
        V2_06_BEFORE = ('<text font-family="Yu Gothic" font-size="68" text-anchor="middle">'
                        '<tspan x="640" y="330">「言語よりも、</tspan><tspan x="640" y="420">半導体に興味を持つこと」</tspan></text>')
        check("Q: 研修報告 v2 の直した後の 06（1行・中央）→ 出ない", not qmsgs(H + V2_06_AFTER))
        q = qmsgs(H + V2_06_BEFORE)   # one() は結果の数で作業フォルダの名前を決めるので、1回の check で1回だけ呼ぶ
        check("Q1: 直す前の 06（2行の引用を中央揃え）→ WARNING", q == ["Q1"], str(q))
        check("Q: 直した後の 04（x=136→176・40px＝1字下げ）→ 出ない", not qmsgs(H + quote3(136, 176)))
        check("Q2: 直す前の 04（3行とも x=136）→ WARNING", qmsgs(H + quote3(136, 136)) == ["Q2"])
        check("Q: 直した後の 03（x=96→130・34px）→ 出ない", not qmsgs(H + quote3(96, 130, fs=34)))
        check("Q2: 直す前の 03（x=96 のまま）→ WARNING", qmsgs(H + quote3(96, 96, fs=34)) == ["Q2"])
        check("Q2: 1行目で」が閉じ、2行目が出どころ → 出ない", not qmsgs(
            H + '<text x="96" y="300" font-family="Yu Gothic" font-size="40">「英語を勉強するだけで満足していた」'
                '<tspan x="96" y="360">研修メモ 8月18日</tspan></text>'))
        check("Q2: <text> に x・y、続きを dy の tspan（1字下げなし）→ WARNING", qmsgs(
            H + '<text x="96" y="300" font-family="Yu Gothic" font-size="40">「英語を'
                '<tspan x="96" dy="60">勉強する」</tspan></text>') == ["Q2"])

        split = ('<text font-family="Yu Gothic" font-size="40"><tspan x="136" y="420">「英語を勉強する</tspan>'
                 '<tspan x="176" y="480">だけで</tspan><tspan x="176" y="540">満足していた」</tspan></text>')
        check("F7: tspan に割れた引用（x・y が tspan だけ・研修報告 v2 の 04）→ 人の言葉と数えて出ない",
              not f7("f7_split", {3: S("食堂で聞いた一言", ["夕方の食堂"]) + split}))
        split2 = ('<text x="136" y="420" font-family="Yu Gothic" font-size="40">「英語を勉強する'
                  '<tspan x="176" dy="60">だけで</tspan><tspan x="176" dy="60">満足していた」</tspan></text>')
        check("F7: <text> に x・y、続きが tspan の割れた引用 → 出ない",
              not f7("f7_split2", {3: S("食堂で聞いた一言", ["夕方の食堂"]) + split2}))
        check("F7: 同じ行でも「」が無ければ ERROR のまま",
              bool(f7("f7_split_noq", {3: S("食堂で聞いた一言", ["夕方の食堂"]) + split.replace("「", "").replace("」", "")})))
        sp = tmp / "tspan_only.svg"
        sp.write_text(SVG_HEAD + split + '</svg>', encoding="utf-8")
        lines, _ = dd.extract_lines(sp)
        check("extract_lines: x・y が tspan だけの <text> も3行読む（前は黙って飛ばしていた）・W4 の印は付けない",
              [ln.text for ln in lines] == ["「英語を勉強する", "だけで", "満足していた」"], str([ln.text for ln in lines]))

        # ================= 2026-10-01 2回目: 試験集（CORPUS）のスライドに当てはまる全件 =================
        # 速さのため deck_doctor は同じプロセスで流す（main は --json の結果を標準出力に書くので受け取る）
        def corpus_issues(name, slide3):
            pt = good_parts()
            if slide3 is not None:
                pt["slides"][2] = slide3
            p = tmp / name
            n = len(pt["slides"])
            svgs = [SVG_HEAD + s + FOOTER % (i, n) + '</svg>' for i, s in enumerate(pt["slides"], 1)]
            notes_md = "# Speaker Notes\n\n" + "".join(
                "## Slide %d: s%d\n\n%s\n\n" % (i, i, t) for i, t in enumerate(pt["notes"], 1))
            make_project(p, svgs, notes_md, pt["spec"])
            add_ledger(p, pt["brief"], pt["memo"], pt["inventory"], pt["evidence"], "PASS")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                dd.main([str(p), "--json"])
            return [(i["severity"], i["file"], i["message"]) for i in json.loads(buf.getvalue())["issues"]]

        if not CORPUS.is_file():
            print("[SKIP] 試験集（%s が無い。作者の環境の文章用スキルにある試験集で、このリポジトリには含まれない）" % CORPUS)
        else:
            cases = json.loads(CORPUS.read_text(encoding="utf-8"))["cases"]
            base = set(corpus_issues("corpus_base", None))
            disputed, n_slide, n_note = [], 0, 0
            limit_seen, limit_fixed = [], []
            fam_n, fam_bad = {}, {}
            for k, c in enumerate(cases):
                want = c["expect"]["slides"]
                if want == "n/a":
                    continue
                n_slide += 1
                fam_n[c["family"]] = fam_n.get(c["family"], 0) + 1
                bad = fam_bad.setdefault(c["family"], [])
                mine = [x for x in corpus_issues("corpus_%03d" % k, corpus_slide(c["text"]))
                        if x not in base and x[1] in ("03_page.svg", "(全体)")]
                hits = [x for x in mine if x[0] in ("WARNING", "ERROR")
                        and any(x[2].startswith(r) for r in CORPUS_RULES[c["family"]])]
                got_ = "hit" if hits else "miss"
                if c["id"] in CORPUS_DISPUTED:
                    want = CORPUS_DISPUTED[c["id"]][0]
                    disputed.append("%s（期待 %s → 提案 %s）" % (c["id"], c["expect"]["slides"], want))
                if c["id"] in KNOWN_LIMITS:
                    # 既知の限界は、期待と違う今の結果のままであることを確かめる（当たるようになったら一覧から外す）
                    limit_seen.append(c["id"])
                    if got_ == want:
                        limit_fixed.append("%s は期待どおり %s になった。KNOWN_LIMITS から外す" % (c["id"], want))
                elif got_ != want:
                    bad.append("%s 期待 %s・結果 %s「%s」" % (c["id"], want, got_, c["text"].replace("\n", "⏎")[:30]))
                note = c.get("note", "")
                # note に書いた重さ・二重計上の決め（決め台詞は ERROR にしない・M1 と二重に数えない）
                if "ERROR ではなく WARNING" in note:
                    n_note += 1
                    if any(x[0] == "ERROR" for x in hits):
                        bad.append("%s note「ERROR ではなく WARNING」なのに ERROR" % c["id"])
                if "M1" in note and "二重に数えない" in note:
                    n_note += 1
                    if any(x[2].startswith("M1 ") for x in mine):
                        bad.append("%s note「M1 と二重に数えない」なのに M1 が出た" % c["id"])
            print("   試験集 %s: スライドに当てはまる %d 件・note の決め %d 件・期待を争った %d 件（%s）・既知の限界 %d 件（%s）"
                  % (CORPUS.name, n_slide, n_note, len(disputed), " / ".join(disputed), len(limit_seen), " / ".join(limit_seen)))
            check("試験集: 読み込めた（スライドに当てはまる件が400件以上・種別が20以上）", n_slide >= 400 and len(fam_n) >= 20,
                  "%d 件・%d 種別" % (n_slide, len(fam_n)))
            all_ids = set(c["id"] for c in cases)
            check("試験集 既知の限界: id が試験集にある・理由がある・スライドに当てはまる件の3%%以下（%d/%d 件）"
                  % (len(KNOWN_LIMITS), n_slide),
                  all(cid in all_ids and why for cid, why in KNOWN_LIMITS.items()) and len(KNOWN_LIMITS) <= n_slide * 0.03
                  and sorted(limit_seen) == sorted(KNOWN_LIMITS),
                  "試験集に無い id・スライドで n/a の id: %s" % sorted(set(KNOWN_LIMITS) - set(limit_seen)))
            check("試験集 既知の限界: どれも期待と違う今の結果のまま（直ったら一覧から外す）", not limit_fixed, " | ".join(limit_fixed))
            for fam in sorted(fam_n):
                check("試験集 %s: %d 件が期待どおり（争った件は出した期待で・note の決めも）" % (fam, fam_n[fam]),
                      not fam_bad[fam], " | ".join(fam_bad[fam][:8]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("----")
    print("%d/%d passed" % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
