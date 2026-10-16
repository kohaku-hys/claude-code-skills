"""motion.py の試験（2026-10-13）。pptx を python-pptx で作り、apply の結果の XML・ノート・手順書き・エラーを見る。
verify（PowerPoint で動画にする）は PowerPoint が要るので、ここでは流さない。
Run:  py -3 test_motion.py   (exit 0 = pass)
"""
import json, os, re, subprocess, sys, tempfile
from pptx import Presentation
from pptx.util import Cm
from pptx.enum.shapes import MSO_SHAPE

S = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "motion.py")
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
d = tempfile.mkdtemp()
ok = 0; ng = 0


def check(cond, label):
    global ok, ng
    if cond:
        ok += 1
    else:
        ng += 1
        print("NG:", label)


def deck(path):
    prs = Presentation()
    prs.slide_width, prs.slide_height = Cm(33.867), Cm(19.05)
    for k in range(2):
        s = prs.slides.add_slide(prs.slide_layouts[6])
        for name, x in (("hand", 2), ("box", 8), ("card1", 14)):
            sh = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Cm(x + k), Cm(5), Cm(4), Cm(3))
            sh.name = name
        t = s.shapes.add_textbox(Cm(2), Cm(12), Cm(20), Cm(2))
        t.text_frame.text = "結論はこれ"
    prs.save(path)


def run(spec, src, out, *extra):
    sp = os.path.join(d, "spec.json")
    json.dump(spec, open(sp, "w", encoding="utf-8"), ensure_ascii=False)
    r = subprocess.run([sys.executable, S, "apply", src, sp, "-o", out, *extra],
                       capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    return r.returncode, r.stdout + r.stderr


def timing(path, no):
    sld = list(Presentation(path).slides)[no - 1]._element
    return sld.find(P + "timing"), sld


src = os.path.join(d, "src.pptx"); deck(src)
PUSH = {"slides": [{"slide": 1, "clicks": [[
    {"target": "hand", "effect": "move", "dx_cm": 3, "sec": 1, "back": True, "repeat": 3},
    {"target": "box", "effect": "scale", "x": 74, "y": 100, "sec": 1, "back": True, "repeat": 3}],
    [{"target": "text:結論", "effect": "fade"}, {"target": "#4", "effect": "wipe", "dir": "up"}]]}]}

# 1) 基本：押す動き＋順番に出す
o1 = os.path.join(d, "o1.pptx")
rc, out = run(PUSH, src, o1)
check(rc == 0, f"1 exit0 ({out})")
tm, sld = timing(o1, 1)
effs = [c for c in tm.iter(P + "cTn") if c.get("presetClass")]
check(len(effs) == 4, f"1 効果4個 ({len(effs)})")
check([c.get("nodeType") for c in effs] == ["clickEffect", "withEffect", "clickEffect", "withEffect"], "1 クリック時/同時の並び")
check(effs[0].get("autoRev") == "1" and effs[0].get("repeatCount") == "3000", "1 自動で戻す・3回")
mo = tm.find(".//" + P + "animMotion")
check(mo is not None and re.match(r"M 0 0 L 0\.0885\d \S+ E", mo.get("path")), f"1 軌跡の長さ（3cm/33.867cm） {mo.get('path') if mo is not None else None}")
sc = tm.find(".//" + P + "by")
check(sc is not None and sc.get("x") == "74000" and sc.get("y") == "100000", "1 拡大/収縮 74%×100%")
ids = [c.get("id") for c in tm.iter(P + "cTn")]
check(len(ids) == len(set(ids)), "1 cTn の id が重ならない")
note = list(Presentation(o1).slides)[0].notes_slide.notes_text_frame.text
check("【動きの作り方】" in note and "自動的に元に戻す" in note and "横方向" in note, "1 ノートに手順")
md = open(os.path.splitext(o1)[0] + "_動きの作り方.md", encoding="utf-8").read()
check("クリック1回目（2個が同時に動く）" in md and "クリック2回目" in md, "1 手順書きのクリック番号")
check("2つ目の動き" not in md, "1 2つ目の動きが無ければ注意は出さない")
o5 = os.path.join(d, "o5.pptx")
rc, out = run({"slides": [{"slide": 1, "clicks": [[
    {"target": "box", "effect": "scale", "x": 74, "y": 100}, {"target": "box", "effect": "move", "dx_cm": 1.5},
    {"target": "hand", "effect": "fade"}], [{"target": "hand", "effect": "fade_out"}]]}]}, src, o5)
md5 = open(os.path.splitext(o5)[0] + "_動きの作り方.md", encoding="utf-8").read()
check(rc == 0 and md5.count("2つ目の動きなので") == 2 and "「box」の行が2本" in md5, "1 同じ図形の2つ目の動きに注意が出る（box と hand）")

# 2) 後ろに足す（--replace なし）と、作り直し（--replace）。ノートの手順は1組だけ
o2 = os.path.join(d, "o2.pptx")
rc, out = run({"slides": [{"slide": 1, "clicks": [[{"target": "card1", "effect": "spin", "deg": -90}]]}]}, o1, o2)
tm, _ = timing(o2, 1)
groups = tm.find(".//" + P + "cTn[@nodeType='mainSeq']").find(P + "childTnLst")
check(rc == 0 and len(groups) == 3, f"2 後ろに足すとクリック3回 ({len(groups)})")
ids = [c.get("id") for c in tm.iter(P + "cTn")]
check(len(ids) == len(set(ids)), "2 足しても id が重ならない")
note = list(Presentation(o2).slides)[0].notes_slide.notes_text_frame.text
check(note.count("【動きの作り方】") == 1 and "反時計回り" in note, "2 ノートの手順は1組（入れ替わる）")
o3 = os.path.join(d, "o3.pptx")
rc, out = run({"slides": [{"slide": 1, "clicks": [[{"target": "card1", "effect": "fade"}]]}]}, o2, o3, "--replace")
tm, _ = timing(o3, 1)
check(rc == 0 and len([c for c in tm.iter(P + "cTn") if c.get("presetClass")]) == 1, "2 --replace で作り直す")

# 2b) 同じ図形に2つ目の動き（出る→消える）：grpId を分け、bldP も2つ（PowerPoint は同じ grpId の2つ目を捨てる）
o6 = os.path.join(d, "o6.pptx")
rc, out = run({"slides": [{"slide": 1, "clicks": [[{"target": "box", "effect": "appear"},
    {"target": "box", "effect": "disappear", "delay": 0.2}, {"target": "box", "effect": "fade", "delay": 0.4}]]}]}, src, o6)
tm, _ = timing(o6, 1)
grps = [c.get("grpId") for c in tm.iter(P + "cTn") if c.get("presetClass")]
check(rc == 0 and grps == ["0", "1", "2"], f"2b 同じ図形の動きは grpId 0・1・2 ({grps})")
blds = sorted((b.get("spid"), b.get("grpId")) for b in tm.find(P + "bldLst"))
check(len(blds) == 3 and len({b[0] for b in blds}) == 1, f"2b bldP が grpId ごとに3つ ({blds})")
o7 = os.path.join(d, "o7.pptx")
rc, out = run({"slides": [{"slide": 1, "clicks": [[{"target": "box", "effect": "fade_out"}]]}]}, o6, o7)
tm, _ = timing(o7, 1)
grps = [c.get("grpId") for c in tm.iter(P + "cTn") if c.get("presetClass")]
check(rc == 0 and grps[-1] == "3", f"2b 後ろに足すと既にある grpId の続き（{grps}）")

# 3) 変形：同じ名前に !! が付き、自動で始まる組は「クリック1回目」から数える
o4 = os.path.join(d, "o4.pptx")
rc, out = run({"slides": [{"slide": 2, "transition": "morph", "clicks": [
    [{"auto": True}, {"target": "hand", "effect": "path", "points_cm": [[1, -1], [2, 0]], "repeat": "loop"}],
    [{"target": "box", "effect": "fade_out"}]]}]}, src, o4)
prs = Presentation(o4)
n1 = sorted(s.name for s in prs.slides[0].shapes); n2 = sorted(s.name for s in prs.slides[1].shapes)
check(rc == 0 and "!!hand" in n1 and "!!hand" in n2 and "!!box" in n2, f"3 !! の名前 {n2}")
check(not any(n.startswith("!!TextBox") for n in n2), "3 決まりの名前（TextBox 4 等）には !! を付けない")
tm, sld = timing(o4, 2)
check(b"p159:morph" in __import__("lxml.etree", fromlist=["x"]).tostring(sld), "3 変形の画面切り替え")
check('evt="onBegin"' in __import__("lxml.etree", fromlist=["x"]).tostring(tm).decode(), "3 自動で始まる")
md = open(os.path.splitext(o4)[0] + "_動きの作り方.md", encoding="utf-8").read()
check("スライドが出たら自動で" in md and "クリック1回目" in md and "クリック2回目" not in md, "3 自動の組を数えない")
check("右1・上1cm" in md, "3 折れ線の点の言い方")

# 4) 止まるべき物
bad = [
    ({"slides": [{"slide": 1, "clicks": [[{"target": "nothing", "effect": "fade"}]]}]}, "が無い"),
    ({"slides": [{"slide": 1, "clicks": [[{"target": "hand", "effect": "scale", "x": 80, "y": 120}]]}]}, "片方 100"),
    ({"slides": [{"slide": 1, "clicks": [[{"target": "hand", "effect": "jump"}]]}]}, "使えない"),
    ({"slides": [{"slide": 1, "clicks": [[{"target": "hand", "effect": "fade"}], [{"auto": True}, {"target": "box", "effect": "fade"}]]}]}, "最初"),
    ({"slides": [{"slide": 9, "clicks": []}]}, "番号"),
    ({"slides": [{"slide": 1, "clicks": [{"target": "hand", "effect": "fade"}]}]}, "[ ]"),
]
for k, (spec, msg) in enumerate(bad):
    rc, out = run(spec, src, os.path.join(d, f"bad{k}.pptx"))
    check(rc == 1 and msg in out, f"4-{k} 止まる（{msg}） rc={rc} {out.strip()[:80]}")
rc, out = run(PUSH, src, src)
check(rc == 2, "4 元のファイルは上書きしない")

# 5) 動きの予算（2026-10-15 本人「動きができすぎてる」）：クリック4回・1クリック4つ・繰り返し2つで止まる。busy で通り、理由が残る
F = lambda t: {"target": t, "effect": "fade"}
over = [
    ({"slides": [{"slide": 1, "clicks": [[F("hand")], [F("box")], [F("card1")], [F("text:結論")]]}]}, "クリックが 4 回"),
    ({"slides": [{"slide": 1, "clicks": [[F("hand"), F("box"), F("card1"), F("text:結論")]]}]}, "4 個が動く"),
    ({"slides": [{"slide": 1, "clicks": [[{"auto": True},
        {"target": "hand", "effect": "move", "dx_cm": 1, "repeat": "loop"},
        {"target": "box", "effect": "move", "dx_cm": 1, "repeat": "loop"}]]}]}, "繰り返す動きが 2 つ"),
]
for k, (spec, msg) in enumerate(over):
    rc, out = run(spec, src, os.path.join(d, f"over{k}.pptx"))
    check(rc == 1 and "動きが多すぎる" in out and msg in out, f"5-{k} 予算で止まる（{msg}） rc={rc} {out.strip()[:90]}")
    check(not os.path.exists(os.path.join(d, f"over{k}.pptx")), f"5-{k} 止まった時は書き出さない")
rc, out = run({"slides": [{"slide": 1, "clicks": [[F("hand")], [F("box")], [F("card1")]]}]}, src, os.path.join(d, "warn3.pptx"))
check(rc == 0 and "注意 A1" in out, f"5 クリック3回は注意だけ ({out.strip()[-80:]})")
busy = {"slides": [{"slide": 1, "busy": "4人が順に出るのがこの枚の伝えたいこと", "clicks": [[F("hand"), F("box"), F("card1"), F("text:結論")]]}]}
ob = os.path.join(d, "busy.pptx")
rc, out = run(busy, src, ob)
mdb = open(os.path.splitext(ob)[0] + "_動きの作り方.md", encoding="utf-8").read()
check(rc == 0 and "動きの予算を超えた理由：4人が順に出る" in mdb, f"5 busy で通り、理由が手順書きに残る rc={rc}")
nb = list(Presentation(ob).slides)[0].notes_slide.notes_text_frame.text
check("動きの予算を超えた理由" in nb, "5 理由がノートにも残る")
PC = os.path.join(os.path.dirname(S), "pptx_check.py")
r = subprocess.run([sys.executable, PC, ob, "--slides", "1"], capture_output=True, text=True, encoding="utf-8",
                   env=dict(os.environ, PYTHONIOENCODING="utf-8"))
check(r.returncode == 0 and "WARNING A2" in r.stdout, f"5 pptx_check は busy の枚を注意に下げる ({r.stdout.strip()[-80:]})")

print(f"ok={ok} ng={ng}")
sys.exit(1 if ng else 0)
