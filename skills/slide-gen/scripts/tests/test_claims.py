"""claims.py の試験（2026-09-28。照合エージェントへの受け渡しと、判定の記録）6件。
① 役割とノートの割り当てが prep どおり ② hash は2回流しても同じで、SVG の文字を1字変えると変わる
③ --record は1行だけ（何度流しても） ④ --minor で理由が残る
⑤ sources_read に素材ごとの行数と '> ' の逐語行の数（開けない素材は brief の記録） ⑥ 目次の役割 A と役割の読み方
Run:  py test_claims.py   (exit 0 = pass)
"""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
# 試すのは、この tests の1つ上の scripts にある claims.py（~/.claude/skills/slide-gen に入れた時も同じ物）
C = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "claims.py")
# deck_doctor.py も同じ scripts に同梱してある（claims.py と同じ物を使う）
SK = os.path.dirname(C)
sys.path.insert(0, SK)
import deck_doctor as dd  # noqa: E402

HEAD = '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">'
def T(x, y, fs, s):
    return '<text x="%d" y="%d" font-family="Yu Gothic" font-size="%d">%s</text>' % (x, y, fs, s)
SLIDES = [T(96, 320, 56, "東湖で見た熱意"),
          T(96, 120, 28, "6日間でいちばん驚いたこと") + T(96, 200, 48, "留学生の一言で熱意を知った") + T(96, 300, 32, "「半導体のやる気全員の」"),
          T(96, 200, 48, "教える側も本気だった") + T(96, 300, 32, "講義4コマ・見学2か所"),
          T(96, 200, 48, "8月18日の食堂") + T(96, 300, 32, "「進路を考えて行動しただけ」"),
          T(96, 200, 48, "8月18日の一言で来年を決めた")]
NOTES = ["表紙のノート", "結論のノート", "理由のノート", "食堂の場面のノート", "最後のノート"]

ok = 0; ng = 0
def check(name, cond, detail=""):
    global ok, ng
    print(("OK  " if cond else "FAIL") + " " + name + ((" :: " + detail) if (detail and not cond) else ""))
    ok += cond; ng += (not cond)
def run(proj, *extra):
    return subprocess.run([sys.executable, C, str(proj)] + list(extra), capture_output=True, text=True,
                          encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8"))

tmp = Path(tempfile.mkdtemp())
try:
    p = tmp / "deck"
    (p / "svg_output").mkdir(parents=True)
    for i, s in enumerate(SLIDES, 1):
        (p / "svg_output" / ("%02d_page.svg" % i)).write_text(HEAD + s + "</svg>", encoding="utf-8")
    (p / "notes").mkdir()
    (p / "notes" / "total.md").write_text("# Notes\n\n" + "".join(
        "## Slide %d: s\n\n%s\n\n" % (i, n) for i, n in enumerate(NOTES, 1)), encoding="utf-8")
    (p / "spec_lock.md").write_text("# Spec Lock\nprep: C 1 / P 2 / R 3 / E 4 / P 5\n", encoding="utf-8")
    (p / "brief.json").write_text(json.dumps({"brief_version": 2, "p": "留学生の一言で熱意を知った", "p_core": ["熱意"],
                                              "p_last": "8月18日の一言で来年を決めた", "proof": [], "me": {},
                                              "sources_read": [{"path": "sources/memo.md"}]}, ensure_ascii=False),
                                  encoding="utf-8")

    # ① 役割とノート
    r = run(p)
    cj = json.loads((p / "review" / "claims.json").read_text(encoding="utf-8"))
    sl = cj["slides"]
    check("①役割とノートの割り当てが prep どおり（小ラベル・見出し・本文も分かれる）",
          r.returncode == 0 and [s["role"] for s in sl] == ["C", "P", "R", "E", "P"]
          and sl[3]["notes"] == "食堂の場面のノート" and sl[1]["eyebrow"] == "6日間でいちばん驚いたこと"
          and sl[1]["headline"] == "留学生の一言で熱意を知った" and sl[1]["body"] == "「半導体のやる気全員の」"
          and cj["p_last"] == "8月18日の一言で来年を決めた" and cj["sources"][0].endswith("memo.md"), r.stdout + str(sl[:2]))

    # ② hash
    h1 = cj["hash"]
    run(p)
    h2 = json.loads((p / "review" / "claims.json").read_text(encoding="utf-8"))["hash"]
    f = p / "svg_output" / "03_page.svg"
    f.write_text(f.read_text(encoding="utf-8").replace("本気だった", "本気だつた"), encoding="utf-8")
    run(p)
    h3 = json.loads((p / "review" / "claims.json").read_text(encoding="utf-8"))["hash"]
    check("②hash は2回流しても同じ・SVG の文字を1字変えると変わる（deck_doctor.content_hash と同じ値）",
          h1 == h2 and h1 != h3 and len(h1) == 10 and h3 == dd.content_hash(p), "%s %s %s" % (h1, h2, h3))

    # ③ --record は1行だけ
    (p / "review" / "evidence_check.md").write_text("判定: PASS\n", encoding="utf-8")
    for _ in range(3):
        r = run(p, "--record", "PASS", "--report", "review/evidence_check.md")
    t = (p / "spec_lock.md").read_text(encoding="utf-8")
    rec = dd.read_evidence_check(p)
    check("③--record は何度流しても1行だけ（PASS・今の hash）",
          r.returncode == 0 and t.count("evidence_check:") == 1 and rec["verdict"] == "PASS"
          and rec["hash"] == dd.content_hash(p) and "prep: C 1" in t, t)

    # ④ --minor
    f.write_text(f.read_text(encoding="utf-8").replace("本気だつた", "本気だった"), encoding="utf-8")
    r = run(p, "--minor", "誤字の修正")
    rec = dd.read_evidence_check(p)
    t = (p / "spec_lock.md").read_text(encoding="utf-8")
    check("④--minor で判定は PASS のまま・hash を付け直し・理由が残る",
          r.returncode == 0 and rec["verdict"] == "PASS" and rec["minor"] == "誤字の修正"
          and rec["hash"] == dd.content_hash(p) and t.count("evidence_check:") == 1, r.stdout + t)
    # ⑤ sources_read（素材の行数と '> ' の逐語行の数。照合エージェントが「'> ' の決まりがある素材か」を知るため）
    (p / "sources").mkdir()
    (p / "sources" / "memo.md").write_text("# メモ\n> 半導体のやる気全員の\n- 講義4コマ\n> 進路を考えて行動しただけ\n",
                                          encoding="utf-8")
    b = json.loads((p / "brief.json").read_text(encoding="utf-8"))
    b["sources_read"] = [{"path": "sources/memo.md", "lines": 4, "verbatim": 2},
                         {"path": "sources/無い.md", "lines": 9, "verbatim": 0}]
    (p / "brief.json").write_text(json.dumps(b, ensure_ascii=False), encoding="utf-8")
    r = run(p)
    sr = json.loads((p / "review" / "claims.json").read_text(encoding="utf-8"))["sources_read"]
    check("⑤sources_read: 開ける素材は実物の行数と逐語行の数（4行・2本）、開けない素材は brief の記録（9行・0本）",
          r.returncode == 0 and [(x["lines"], x["verbatim"], x["from"]) for x in sr] == [(4, 2, "file"), (9, 0, "brief")]
          and sr[0]["path"].endswith("memo.md"), str(sr))

    # ⑥ 目次の役割 A（2枚目に目次を差し込んだ6枚のデッキを別に作る）
    q = tmp / "deck_a"
    (q / "svg_output").mkdir(parents=True)
    AG = T(96, 150, 48, "目次") + T(96, 260, 32, "01　留学生の一言") + T(96, 330, 32, "02　教える側の熱意")
    for i, sv in enumerate([SLIDES[0], AG] + SLIDES[1:], 1):
        (q / "svg_output" / ("%02d_page.svg" % i)).write_text(HEAD + sv + "</svg>", encoding="utf-8")
    (q / "spec_lock.md").write_text("# Spec Lock\nprep: C 1 / A 2 / P 3 / R 4 / E 5 / P 6\n", encoding="utf-8")
    (q / "brief.json").write_text((p / "brief.json").read_text(encoding="utf-8"), encoding="utf-8")
    r = run(q)
    cj = json.loads((q / "review" / "claims.json").read_text(encoding="utf-8"))
    check("⑥目次の役割 A が claims.json に出て、役割の読み方（roles）に A の説明がある",
          r.returncode == 0 and [x["role"] for x in cj["slides"]] == ["C", "A", "P", "R", "E", "P"]
          and "目次" in cj["roles"]["A"] and cj["slides"][1]["headline"] == "目次", r.stdout + str(cj["slides"][:2]))
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("%d/%d passed" % (ok, ok + ng)); sys.exit(1 if ng else 0)
