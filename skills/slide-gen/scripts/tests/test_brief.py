"""brief.py の試験（2026-09-28 v2＝証拠の台帳）。前半11件は v1 からの試験を v2 の答えで流し直した物、中の8件が v2 の検査、
後半が v3（genre・overview・結論の強い証拠の ERROR 化・prep の A）。
v1 の「本人一任なら空でも書ける」は仕様変更で逆になった（本人一任でも証拠欄は免除しない）→ 11件目は「本人一任でも
証拠が揃っていれば書ける」、⑧が「本人一任でも proof が空なら exit 1」。
v3 から見本（base）に genre: proposal を足した（genre が無いと exit 2＝general と書く、になったため）。
Run:  py test_brief.py   (exit 0 = pass)
"""
import copy, json, os, shutil, subprocess, sys, tempfile
# 試すのは、この tests の1つ上の scripts にある brief.py（~/.claude/skills/slide-gen に入れた時も同じ物）
S = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brief.py")
# deck_doctor.py も同じ scripts に同梱してある（brief.py と同じ物を使う）
DD = os.path.join(os.path.dirname(S), "deck_doctor.py")
MEMO = ["# 研修メモ", "## 3日目（8月18日）", "> 進路を考えて行動しただけ、と言っていた",
        "- 場面: 8月18日の夕方、食堂で留学生と話した", "> 半導体のやる気全員の", "- 数: 講義は4コマ・見学は2か所",
        "> 長期のプログラムにも挑戦したい", "## 4日目", "- 場面（推測）: 機械工学科の教授に質問したとみられる", "- おわり"]
INV = "# 候補\n- E1 V memo.md:3\n- E2 V memo.md:5\n- E3 N memo.md:6\n- S1 S memo.md:9（推測）\n"


def make_dir():
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "sources"))
    open(os.path.join(d, "sources", "memo.md"), "w", encoding="utf-8").write("\n".join(MEMO) + "\n")
    open(os.path.join(d, "sources", "inventory.md"), "w", encoding="utf-8").write(INV)
    open(os.path.join(d, "spec_lock.md"), "w", encoding="utf-8").write("# Spec Lock\n- delivery: presentation\n- prep: P 1\n")
    return d


d = make_dir()
ok = 0; ng = 0
def run(ans, where=None):
    w = where or d
    p = os.path.join(w, "a.json"); json.dump(ans, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    return subprocess.run([sys.executable, S, w, p], capture_output=True, text=True, encoding="utf-8",
                          env=dict(os.environ, PYTHONIOENCODING="utf-8"))
def check(name, cond, detail=""):
    global ok, ng
    print(("OK  " if cond else "FAIL") + " " + name + ((" :: " + detail) if (detail and not cond) else ""))
    ok += cond; ng += (not cond)
base = {"brief_version": 2, "how": "選択式", "genre": "proposal", "audience": "展示会の下見・5分",
        "p": "10月1日15時のTKRIだけは外さない", "p_core": ["TKRI", "10月1日"],
        "p_last": "8月18日の一言で、TKRIの講演を聞くと決めた",
        "r": [{"id": "R1", "claim": "海外進学の窓口になる", "slides": [3]}],
        "proof": [{"id": "E1", "for": "R1", "kind": "verbatim", "src": "memo.md:3", "quote": "進路を考えて行動しただけ", "slides": [4]},
                  {"id": "E2", "for": "P", "kind": "verbatim", "src": "memo.md:5", "quote": "半導体のやる気全員の", "slides": [2]},
                  {"id": "E3", "for": "P", "kind": "number", "src": "memo.md:6", "quote": "講義は4コマ・見学は2か所", "slides": [5]}],
        "me": {"why": "同世代の行動に背中を押された", "scene": {"src": "memo.md:7", "quote": "長期のプログラムにも挑戦したい"},
               "next": "英語を増やす"},
        "sources_read": [{"path": "sources/memo.md", "lines": 10, "read": "1-10", "verbatim": 3,
                          "inventory": "sources/inventory.md"}],
        "cta": "申込む", "ng": [], "prep": "C 1 / P 2 / R 3 / E 4 / P 5"}
def v(**kw):
    a = copy.deepcopy(base); a.update(kw); return a

# --- v1 からの11件（答えは v2 の書式） ---
r = run(base); check("具体的な結論は exit 0", r.returncode == 0, r.stdout)
t = open(os.path.join(d, "spec_lock.md"), encoding="utf-8").read()
check("brief_confirmed が入る", "brief_confirmed:" in t)
check("古い prep 行は消えて1本だけ", t.count("prep:") == 1 and "prep: C 1 / P 2" in t)
r = run(base); t = open(os.path.join(d, "spec_lock.md"), encoding="utf-8").read()
check("2回流しても1組だけ", t.count("brief_confirmed:") == 1 and t.count("prep:") == 1)
check("delivery 行は残る", "delivery: presentation" in t)
check("2回流しても brief: の塊は1つ", t.count("\nbrief:") == 1 and t.count("audience:") == 1)
# v1 を写して作り直した時の形（見出しの後に古い塊・その後に節）でも古い塊が残らない
open(os.path.join(d, "spec_lock.md"), "w", encoding="utf-8").write(
    "# Spec Lock\n## page_layouts\n- 01: 表紙\n\nbrief_confirmed: 2026-09-01 選択式\nbrief:\n  audience: 古い聴衆\n  p: 古い結論\n"
    "prep: C 1 / P 2 / R 3 / E 4 / P 5\n\n## colors\n- blue: #125E90\n")
r = run(base); t = open(os.path.join(d, "spec_lock.md"), encoding="utf-8").read()
check("写した spec_lock の古い brief が消える", "古い結論" not in t and t.count("audience:") == 1)
check("後ろの節は残る", "## colors" in t and "- blue: #125E90" in t)
r = run(v(p="業務の効率化で新しい価値を実現する")); check("抽象的な結論は exit 2", r.returncode == 2, r.stdout)
r = run({"prep": "P 1"}); check("必須項目が無ければ exit 1", r.returncode == 1)
r = run(v(how="本人一任")); check("本人一任でも証拠が揃っていれば書ける（v1 の『空でも書ける』は廃止）", r.returncode == 0, r.stdout)

# --- v2 の8件 ---
r = run({"how": "選択式", "audience": "研修報告", "p": "装置より人の熱意", "r": ["教える側の熱量"],
         "e": ["研修メモ 84行"], "cta": "応募してほしい", "prep": "C 1 / P 2 / R 3 / E 4 / P 5"})
check("①旧書式（p/r/e の文字列）→ exit 1・欠けているキーを列挙",
      r.returncode == 1 and all(k in r.stdout for k in ("p_core", "p_last", "proof", "me", "sources_read")), r.stdout)
d2 = make_dir()
r = run(base, d2); r2 = run(base, d2)
t = open(os.path.join(d2, "spec_lock.md"), encoding="utf-8").read()
bj = json.load(open(os.path.join(d2, "brief.json"), encoding="utf-8"))
check("②v2 の見本 → exit 0・brief.json と spec_lock の brief_version: 2・2回流しても1組（genre も1組）",
      r.returncode == 0 and r2.returncode == 0 and bj == base and t.count("brief_version: 2") == 1
      and t.count("brief_confirmed:") == 1 and t.count("## genre") == 1 and t.count("- genre: proposal") == 1,
      r.stdout + t)
d3 = make_dir()
before = open(os.path.join(d3, "spec_lock.md"), encoding="utf-8").read()
bad = v(); bad["proof"][0]["src"] = "memo.md:8"      # 6〜10行目に「進路を考えて行動しただけ」は無い
r = run(bad, d3)
check("③quote が src 行（前後2行）に無い → exit 1・ファイルを書かない",
      r.returncode == 1 and not os.path.exists(os.path.join(d3, "brief.json"))
      and open(os.path.join(d3, "spec_lock.md"), encoding="utf-8").read() == before, r.stdout)
r = run(v(p="装置ではなく、人の熱意だった"))
check("④p＝『装置ではなく、人の熱意だった』→ exit 2（対句＋具体なし）",
      r.returncode == 2 and "対句" in r.stdout and "具体" in r.stdout, r.stdout)
r = run(v(p_last=base["p"])); check("⑤p_last が p と同じ → exit 1", r.returncode == 1, r.stdout)
sc = v(); sc["proof"].append({"id": "S1", "for": "R1", "kind": "scene", "src": "memo.md:9",
                              "quote": "機械工学科の教授に質問した", "slides": [3]})
r = run(sc); check("⑥src が『場面（推測）』の行 → exit 2（本人に確かめる）", r.returncode == 2 and "推測" in r.stdout, r.stdout)
vc = v(); vc["sources_read"][0]["verbatim"] = 2
r = run(vc); check("⑦verbatim の数が合わない → exit 1", r.returncode == 1 and "逐語行の数" in r.stdout, r.stdout)
r = run(v(how="本人一任", proof=[])); check("⑧how='本人一任' でも proof が空なら exit 1", r.returncode == 1 and "proof" in r.stdout, r.stdout)

# --- v3（2026-09-28）: genre・overview・結論の強い証拠・prep の A ---
sys.path.insert(0, os.path.dirname(DD))
import deck_doctor as dd  # noqa: E402
nog = v(); del nog["genre"]
d4 = make_dir()
r = run(nog, d4)
t = open(os.path.join(d4, "spec_lock.md"), encoding="utf-8").read()
bj = json.load(open(os.path.join(d4, "brief.json"), encoding="utf-8"))
check("⑨genre が無い → exit 2・general と書く（brief.json と spec_lock・deck_doctor が general と読む）",
      r.returncode == 2 and "genre" in r.stdout and bj.get("genre") == "general" and "- genre: general" in t
      and dd.detect_genre(__import__("pathlib").Path(d4)) == "general", r.stdout + t)
r = run(v(genre="report"))
check("⑩genre が一覧に無い値（report）→ exit 1", r.returncode == 1 and "report" in r.stdout, r.stdout)
r = run(v(genre="experience"))
check("⑪experience で overview が無い → exit 1", r.returncode == 1 and "overview" in r.stdout, r.stdout)
OV = [{"k": "日付", "v": "8月18日", "src": "memo.md:4", "quote": "8月18日の夕方"}]
r = run(v(genre="experience", overview=OV))
check("⑫experience で overview の quote が出典の行にある → exit 0", r.returncode == 0, r.stdout)
bad_ov = [{"k": "日付", "v": "8月20日", "src": "memo.md:4", "quote": "8月20日の朝"}]
r = run(v(genre="experience", overview=bad_ov))
check("⑬overview の quote が出典の行（前後2行）に無い → exit 1（C3 と同じ照合）",
      r.returncode == 1 and "作文の疑い" in r.stdout, r.stdout)
r = run(v(genre="proposal", overview=[{"k": "場所", "v": "西浜", "src": "other.md:1", "quote": "西浜"}]))
check("⑭overview の出典が sources_read に無い → exit 1", r.returncode == 1 and "sources_read" in r.stdout, r.stdout)
one_p = v(); one_p["proof"] = [base["proof"][0], base["proof"][1]]   # for=P は E2 の1件だけ
r = run(one_p)
check("⑮結論（for=P）の強い証拠が1件 → exit 1（deck_doctor の C2 と同じ重さ）",
      r.returncode == 1 and "強い証拠" in r.stdout, r.stdout)
d5 = make_dir()
r = run(v(prep="C 1 / A 2 / P 3 / R 4 / E 5 / P 6"), d5)
t = open(os.path.join(d5, "spec_lock.md"), encoding="utf-8").read()
roles = dd.parse_prep(__import__("pathlib").Path(d5))
check("⑯prep の A（目次）を受け付ける → exit 0・spec_lock の prep を deck_doctor が A と読む",
      r.returncode == 0 and "prep: C 1 / A 2 / P 3" in t and roles.get(2) == ["A"], r.stdout + str(roles))

# --- v4（2026-10-01）: 話の順番 flow。本人の回答「② PREP は既定のまま、別の順も選べる」 ---
d6 = make_dir()
r = run(base, d6); t = open(os.path.join(d6, "spec_lock.md"), encoding="utf-8").read()
check("⑰flow を書かない＝prep → spec_lock に flow: 行を書かない", r.returncode == 0 and "\nflow:" not in t, r.stdout)
r = run(v(flow="chronological", flow_why="8月の研修を日付の順に話したい"), d6)
t = open(os.path.join(d6, "spec_lock.md"), encoding="utf-8").read()
check("⑱flow=chronological → spec_lock に flow: 行が1本（本人の理由つき）",
      r.returncode == 0 and t.count("\nflow:") == 1 and "flow: chronological" in t and "本人 8月の研修を日付の順に" in t,
      r.stdout + t[-300:])
r = run(v(flow="problem"), d6); t = open(os.path.join(d6, "spec_lock.md"), encoding="utf-8").read()
check("⑲流し直すと flow: 行は置き換わって1本", t.count("\nflow:") == 1 and "flow: problem" in t, t[-200:])
r = run(base, d6); t = open(os.path.join(d6, "spec_lock.md"), encoding="utf-8").read()
check("⑳prep に戻すと flow: 行が消える", "\nflow:" not in t, t[-200:])
r = run(v(flow="random"))
check("㉑flow が一覧に無い値 → exit 1", r.returncode == 1 and "flow" in r.stdout, r.stdout)
same = v(flow="chronological", p_last=base["p"])
r = run(same)
check("㉒flow が prep 以外なら、p と p_last が同じ文でも止めない（結論が最後の1回だけの順）", r.returncode == 0, r.stdout)
r = run(v(p_last=base["p"]))
check("㉓flow=prep では p と p_last が同じ文 → exit 1（従来どおり）", r.returncode == 1 and "p_last" in r.stdout, r.stdout)
no_last = v(flow="problem"); no_last.pop("p_last")
d7 = make_dir()
r = run(no_last, d7)
bj = json.load(open(os.path.join(d7, "brief.json"), encoding="utf-8")) if os.path.isfile(os.path.join(d7, "brief.json")) else {}
check("㉔flow が prep 以外で p_last を省く → p と同じ文を入れて書く（deck_doctor の C1 の必須欄を満たす）",
      r.returncode == 0 and bj.get("p_last") == base["p"], r.stdout)

for x in (d, d2, d3, d4, d5, d6, d7):
    shutil.rmtree(x, ignore_errors=True)
print("%d/%d passed" % (ok, ok + ng)); sys.exit(1 if ng else 0)
