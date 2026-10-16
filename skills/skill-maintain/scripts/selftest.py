# -*- coding: utf-8 -*-
"""selftest.py — スキル資産エコシステムの一発自己診断（モデル非依存の健全性ゲート）

どのモデル（Fable/Opus/後継）でも「py selftest.py → exit 0 なら健全」と機械判定できる。
判断力に頼らず、確立済みのルールを全部コードで検査する。

検査項目:
  1. 全 SKILL.md の構造（frontmatter name/description・3点セット・500行上限）
  2. SKILL.md 内の references/ scripts/ assets/ 参照の実在
  3. 移動済み旧パスの残存（skills/skill-memory/CLAUDE.md/hooks/scripts）
  4. 「（接続済）」断言の禁止（PC間でMCP状態が違うため）
  4.5 SKILL.md コードブロック内の「展開されないパス表記」
      （bash/powershell の %USERPROFILE%・クォート内 ~/・Python文字列の ~）
  5. OneDrive 競合コピー（-<既知ホスト名>/-LAPTOP-*/-DESKTOP-*/競合コピー）ゼロ
     （ワークスペースを渡した時だけ。無ければ SKIP を表示）
  6. 全 .py の py_compile ＋ 3.10+ 専用構文（match / except* / type文）の AST 検出
     ※実行系が 3.10+ の PC では py_compile 単体は 3.9 互換の保証にならないため
  7. プロジェクトメモリの [[リンク]] が実在 name: に解決すること
     （場所を渡していない・ディレクトリが無い時は SKIP を明示表示＝黙ってスキップしない）
  8. agents 体制（会社型マルチエージェント）の整合
     （frontmatter形式・coder以外にEdit/Write無し・共通規約の埋め込み・
       README組織図と実ファイルの双方向一致〈README がある時〉・panel審査員表の実在）
使い方: py ~/.claude/skills/skill-maintain/scripts/selftest.py [--quick] [--skills <スキルのフォルダ>]
  --quick は 6 の compile を省略。終了コード 0=PASS / 1=FAIL。

場所は引数か環境変数で渡す（どれも無ければ ~/.claude/ の既定を使う）:
  --skills / CLAUDE_SKILLS_DIR  スキルのフォルダ（既定 ~/.claude/skills）。
                                agents・hooks・scripts・skill-memory はこのフォルダの隣を見る
  CLAUDE_SKILL_MEMORY           skill-memory のフォルダ（既定 スキルのフォルダの隣の skill-memory）
  CLAUDE_WORKSPACE              ワークスペース。CLAUDE.md の旧パス検査（3）と競合コピー検査（5）に使う。無ければ飛ばす
  CLAUDE_PROJECT_SKILLS         プロジェクト側のスキルのフォルダ（任意。1&2 だけ見る）
  CLAUDE_PROJECT_MEMORY         プロジェクトメモリのフォルダ（任意。無ければ 7 を飛ばす）
  CLAUDE_KNOWN_HOSTS            競合コピーの判定に足すホスト名（「,」区切り。任意。今のPCの名前は自動で入る）
例: py selftest.py --skills C:/dev/claude-code-skills/skills
"""
import argparse
import ast
import io
import os
import platform
import py_compile
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ap = argparse.ArgumentParser(description="スキル資産の一発自己診断")
ap.add_argument("--quick", action="store_true", help="6 の compile を省略する")
ap.add_argument("--skills", default=None, help="スキルのフォルダ（既定 環境変数 CLAUDE_SKILLS_DIR か ~/.claude/skills）")
args = ap.parse_args()

HOME = os.path.expanduser("~")  # ユーザー名を埋め込まない（どのPCでも正しく動く）
SKILLS = args.skills or os.environ.get("CLAUDE_SKILLS_DIR") or os.path.join(HOME, ".claude", "skills")
SKILLS = os.path.abspath(os.path.expanduser(SKILLS))
BASE = os.path.dirname(SKILLS)  # ~/.claude/skills なら ~/.claude。agents・hooks・scripts はここを見る
MEMORY = os.environ.get("CLAUDE_SKILL_MEMORY") or os.path.join(BASE, "skill-memory")
# プロジェクト側のスキル（例: ワークスペースの .claude/skills）。渡された時だけ見る。
# 共通の規約（3点セット等）は課さず、frontmatter・参照実在・行数だけ見る。
PROJECT_SKILLS = os.environ.get("CLAUDE_PROJECT_SKILLS", "")
PROJ_MEM = os.environ.get("CLAUDE_PROJECT_MEMORY", "")
WORKSPACE = os.environ.get("CLAUDE_WORKSPACE", "")
CLAUDE_MD = os.path.join(WORKSPACE, "CLAUDE.md") if WORKSPACE else ""
HOST = platform.node()
QUICK = args.quick

if not os.path.isdir(SKILLS):
    print(f"スキルのフォルダが無い: {SKILLS}（--skills か CLAUDE_SKILLS_DIR で渡す）")
    sys.exit(1)
print(f"[対象] {SKILLS}")

problems = []
skips = []  # SKIP した検査（PASS の時も一緒に出す）


def check(cond, msg):
    if not cond:
        problems.append(msg)


# --- 1&2. SKILL.md 構造と参照実在 ---
for _root, _is_hub in ((SKILLS, True), (PROJECT_SKILLS, False)):
  if not _root or not os.path.isdir(_root):
    continue
  for name in sorted(os.listdir(_root)):
    d = os.path.join(_root, name)
    p = os.path.join(d, "SKILL.md")
    if not os.path.isdir(d) or not os.path.exists(p):
        continue
    s = open(p, encoding="utf-8").read()
    lines = len(s.splitlines())
    check(s.startswith("---"), f"{name}: frontmatter無し")
    if s.startswith("---") and s.count("---") >= 2:
        fm = s.split("---")[1]
        check("name:" in fm, f"{name}: name無し")
        check("description:" in fm, f"{name}: description無し")
    if _is_hub and name != "shared-doc-rules":
        check("共通3点セット" in s or "共通4点セット" in s, f"{name}: 3点セット無し")
    check(lines <= 500, f"{name}: {lines}行（公式上限500超）")
    for m in re.finditer(r"(references|scripts|assets)/([\w\-./]+\.(md|py|ps1|gs|html|json))", s):
        # 直前が / なら他スキルへのフルパスの一部＝そのスキル相対では検査しない
        if m.start() > 0 and s[m.start() - 1] == "/":
            continue
        check(os.path.exists(os.path.join(d, m.group(0))), f"{name}: 参照切れ {m.group(0)}")

# --- 3. 旧パス残存 ---
moved = [
    (r"skills/report/(lint|check_ai_likeness|run_pipeline|grade|auto_grade_loop|extract_requirements|review_outline|circuit_lib|fill_cover|pdf_vocab_check)\.py", "report直下→scripts/"),
    (r"slide-gen/tools/", "tools→scripts"),
    (r"skills/preview-report/(preview|chrome_cdp|cdp_seek|sharepoint_folder|omml_lib|report_gen|capture_folder|smoke_test)\.py", "preview-report直下→scripts/"),
    (r"forms/assets/(gforms_cdp|render_preview)\.py", "forms assets→scripts"),
    # 自分の環境でフォルダを移したら、ここに (旧パスの正規表現, ラベル) を足す
]
# ワークスペースを渡された時だけ、その CLAUDE.md も見る
targets = [CLAUDE_MD] if CLAUDE_MD else []
for root in (SKILLS, MEMORY):
    for dirpath, dirs, files in os.walk(root):
        # synced/ と .trash/ は Claude アプリが管理する claude.ai 側スキルの配布先と屑籠。
        # 自分たちの資産ではなく直せもしないので検査しない（2026-09-28）
        dirs[:] = [x for x in dirs if x not in ("__pycache__", "synced", ".trash")]
        # .py/.ps1 も見る（slide-gen の試験がパスを区切りごとに組み立てていて .md だけでは漏れた）
        targets += [os.path.join(dirpath, f) for f in files if f.endswith((".md", ".py", ".ps1"))]
for d in (os.path.join(BASE, "hooks"), os.path.join(BASE, "scripts")):
    if not os.path.isdir(d):  # 公開リポジトリなど hooks/scripts が無い所では飛ばす
        continue
    targets += [os.path.join(d, f) for f in os.listdir(d) if os.path.isfile(os.path.join(d, f))]
for t in targets:
    if os.path.basename(t) == "selftest.py":   # 自分の moved 表そのものに当たるので除く
        continue
    try:
        s = open(t, encoding="utf-8", errors="replace").read()
    except OSError:
        continue
    for pat, label in moved:
        if re.search(pat, s):
            check(False, f"旧パス[{label}]: {t}")

# --- 4. 「（接続済）」断言禁止 ---
for name in sorted(os.listdir(SKILLS)):
    p = os.path.join(SKILLS, name, "SKILL.md")
    if os.path.exists(p):
        s = open(p, encoding="utf-8").read()
        check("（接続済）" not in s, f"{name}: 「（接続済）」断言が残存（PC差で嘘になる。「利用可能なら」に）")

# --- 4.5 コードブロック内の「展開されないパス表記」---
# 散文の ~ 表記は正だが、実行スニペットに書くと壊れる（bashクォート内 ~・PowerShell/py の
# %USERPROFILE%・Python文字列の ~ は展開されない）。2026-07-04 に5スキルで実例を修正済み。
FENCE_RE = re.compile(r"```(\w*)[^\n]*\n(.*?)```", re.S)
for name in sorted(os.listdir(SKILLS)):
    p = os.path.join(SKILLS, name, "SKILL.md")
    if not os.path.exists(p):
        continue
    s = open(p, encoding="utf-8").read()
    for fm_ in FENCE_RE.finditer(s):
        lang, code = fm_.group(1).lower(), fm_.group(2)
        if lang in ("powershell", "ps1", "bash", "sh") and "%USERPROFILE%" in code:
            check(False, f"{name}: {lang}ブロック内の %USERPROFILE%（cmd構文。$env:USERPROFILE / $USERPROFILE に）")
        if re.search(r'''(?:cd|=)\s*["']~[/\\]''', code):
            check(False, f'{name}: クォートされた "~/"（シェルは展開しない。~/"…" 連結か $HOME/$env:USERPROFILE に）')
        if lang in ("python", "py"):
            for tm_ in re.finditer(r'''r?["']~[/\\]''', code):
                # expanduser() に包まれている正しい用法は許可（直前40字で判定）
                if "expanduser" in code[max(0, tm_.start() - 40):tm_.start()]:
                    continue
                check(False, f"{name}: Python文字列リテラルの ~（os.path.expanduser が必要）")

# --- 5. 競合コピー ---
# 「競合」の裸の部分一致は使わない（コンペの「競合分析.md」等の正当ファイルを誤検知するため）。
# OneDrive は競合したファイルを「元の名前-<ホスト名>.md」にする。使っているPCの名前を CLAUDE_KNOWN_HOSTS に足す
KNOWN_HOSTS = tuple(h.strip().upper() for h in os.environ.get("CLAUDE_KNOWN_HOSTS", "").split(",") if h.strip())
_hosts = set(KNOWN_HOSTS) | {HOST.upper()}
def _is_conflict_name(n):
    up = n.upper()
    if any(re.search(rf"-{re.escape(h)}(?=[.\-_（(\s]|$)", up) for h in _hosts):
        return True
    if re.search(r"-(LAPTOP|DESKTOP)-[0-9A-Z]+", n):
        return True
    return "競合コピー" in n or re.search(r"-競合", n) is not None
if not WORKSPACE or not os.path.isdir(WORKSPACE):
    print("[conflict] SKIP: CLAUDE_WORKSPACE が無い（競合コピーの検査5は未実施）")
    skips.append("5 競合コピー")
_bases = [WORKSPACE] if WORKSPACE and os.path.isdir(WORKSPACE) else []
for _base in _bases:
  for dirpath, dirs, files in os.walk(_base):
    rel = os.path.relpath(dirpath, _base)
    # skills/synced と skills/.trash は Claude アプリが PC ごとに書き直す claude.ai 側スキルの控え（manifest.json 等）。
    # 複数のPCが同じ所に書くので、競合コピーが出ても中身は lastUpdated の違いだけ。本人のデータではないので数えない
    if "ゴミ箱" in rel or "node_modules" in rel or rel.replace("\\", "/").endswith(("skills/synced", "skills/.trash")):
        dirs[:] = []
        continue
    for n in files + dirs:
        if _is_conflict_name(n):
            check(False, f"競合コピー: {os.path.normpath(os.path.join(os.path.basename(_base), rel, n))}")

# --- 6. py_compile ＋ 3.10+ 専用構文の AST 検出 ---
# 注意: py_compile は「今の py が受理するか」しか見ない。py が 3.10+ の PC では
# match 文等が素通りするため、AST で 3.10+ 専用ノードを直接検出する
# （3.9で消える主要構文: match / except* / type 文。`X | None` 注釈は構文上3.9でも
#   通り実行時にしか落ちないため、ここでは検出対象外＝レビューで見る）。
PY310_NODES = tuple(n for n in (getattr(ast, "Match", None),
                                getattr(ast, "TryStar", None),
                                getattr(ast, "TypeAlias", None)) if n)
if not QUICK:
    n_ok = 0
    for dirpath, dirs, files in os.walk(SKILLS):
        # synced/ と .trash/ は Claude アプリが管理する claude.ai 側スキルの配布先と屑籠。
        # 自分たちの資産ではなく直せもしないので検査しない（2026-09-28）
        dirs[:] = [x for x in dirs if x not in ("__pycache__", "synced", ".trash")]
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(dirpath, f)
                try:
                    py_compile.compile(path, doraise=True)
                    n_ok += 1
                except py_compile.PyCompileError:
                    check(False, f"compile失敗: {path}")
                    continue
                try:
                    tree = ast.parse(open(path, encoding="utf-8", errors="replace").read())
                    bad = [type(node).__name__ for node in ast.walk(tree)
                           if isinstance(node, PY310_NODES)]
                    check(not bad, f"3.10+専用構文({'/'.join(sorted(set(bad)))}): {path}（py3.9機で落ちる）")
                except SyntaxError:
                    pass  # compile が通っていれば来ない
    print(f"[compile] {n_ok} 本 OK（＋3.10+構文のAST検査）")
    # 検査で生成した __pycache__ は同期を汚さないよう掃除
    import shutil
    for dirpath, dirs, files in os.walk(SKILLS):
        for x in list(dirs):
            if x == "__pycache__":
                shutil.rmtree(os.path.join(dirpath, x), ignore_errors=True)

# --- 7. メモリ [[リンク]] と索引の完全性 ---
# 黙ってスキップしない: ディレクトリが無ければその旨を表示する（PASS の意味を正直に保つ。
# 固定パスのせいで別のPCで検査が無言でスキップされていた事故の教訓）。
if not PROJ_MEM:
    print("[memory] SKIP: CLAUDE_PROJECT_MEMORY が無い（検査7は未実施）")
    skips.append("7 メモリリンク")
elif not os.path.isdir(PROJ_MEM):
    print(f"[memory] SKIP: {PROJ_MEM} が無い（このPCでは当該プロジェクト未使用。検査7は未実施）")
    skips.append("7 メモリリンク")
if PROJ_MEM and os.path.isdir(PROJ_MEM):
    names = set()
    entries = []
    for f in os.listdir(PROJ_MEM):
        if f.endswith(".md") and f != "MEMORY.md":
            s = open(os.path.join(PROJ_MEM, f), encoding="utf-8").read()
            m = re.search(r"^name:\s*(.+?)\s*$", s, re.M)
            if m:
                names.add(m.group(1).strip())
            entries.append((f, s))
    for f, s in entries:
        for l in re.findall(r"\[\[([^\]]+)\]\]", s):
            check(l.strip() in names, f"メモリ壊れリンク: {f} → [[{l}]]")
    # 索引の完全性: name/description を持つメモリは全て MEMORY.md に載っていること
    # （CRLF が原因で索引から11件落ちた事故を恒久ゲート化。索引に無い記憶は想起されない）
    idx_path = os.path.join(PROJ_MEM, "MEMORY.md")
    if os.path.exists(idx_path):
        idx = open(idx_path, encoding="utf-8").read()
        for f, s in entries:
            fm = s.split("---")[1] if s.startswith("---") and s.count("---") >= 2 else ""
            if re.search(r"^name:\s*\S", fm, re.M) and re.search(r"^description:\s*\S", fm, re.M):
                check(f"({f})" in idx, f"索引欠落: {f} が MEMORY.md に無い（MEMORY.md に索引の行を足す）")

# --- 8. agents 体制（会社型マルチエージェント）の整合 ---
AGENTS = os.path.join(BASE, "agents")
if os.path.isdir(AGENTS):
    defs = {}  # name -> tools
    for f in sorted(os.listdir(AGENTS)):
        if not f.endswith(".md") or f == "README.md":
            continue
        s = open(os.path.join(AGENTS, f), encoding="utf-8").read()
        stem = f[:-3]
        ok_fm = s.startswith("---") and s.count("---") >= 2
        check(ok_fm, f"agents/{f}: frontmatter無し")
        fm = s.split("---")[1] if ok_fm else ""
        m = re.search(r"^name:\s*(\S+)\s*$", fm, re.M)
        check(bool(m) and m.group(1) == stem, f"agents/{f}: name がファイル名と不一致")
        check(re.search(r"^description:\s*\S", fm, re.M), f"agents/{f}: description無し")
        tm = re.search(r"^tools:\s*(.+)$", fm, re.M)
        check(bool(tm), f"agents/{f}: tools無し")
        tools = [t.strip() for t in tm.group(1).split(",")] if tm else []
        if stem != "coder":
            check("Edit" not in tools and "Write" not in tools,
                  f"agents/{f}: coder以外にEdit/Write（README体制違反）")
        check("共通規約" in s, f"agents/{f}: 共通規約の節が無い")
        check("⚠不足入力" in s, f"agents/{f}: ⚠不足入力の規則が無い")
        check(("確信度" in s) or ("確度" in s), f"agents/{f}: 確信度の規則が無い")
        defs[stem] = tools
    # README.md（体制の正本・組織図）を置いている時だけ、組織図と実ファイルを突き合わせる
    readme_p = os.path.join(AGENTS, "README.md")
    if not os.path.exists(readme_p):
        print("[agents] SKIP: agents/README.md が無い（組織図との照合は未実施）")
        skips.append("8 組織図の照合")
    if os.path.exists(readme_p):
        r = open(readme_p, encoding="utf-8").read()
        chart = set(re.findall(r"[├└]─\s+([a-z][a-z0-9-]+)", r))
        for n in sorted(chart - set(defs)):
            check(False, f"agents/README.md 組織図の {n} が実ファイルに無い（幽霊社員）")
        for n in sorted(set(defs) - chart):
            check(False, f"agents/{n}.md が README 組織図に載っていない（欠員記載）")
    panel_p = os.path.join(SKILLS, "panel", "SKILL.md")
    if os.path.exists(panel_p) and defs:
        ps = open(panel_p, encoding="utf-8").read()
        sec = ps.split("## STEP 0")[1].split("## STEP 1")[0] if "## STEP 0" in ps else ""
        for n in sorted(set(re.findall(r"`([a-z][a-z0-9-]+)`", sec))):
            check(n in defs, f"panel審査員表の `{n}` が agents に実在しない")

# --- 結果 ---
print()
if problems:
    print(f"== FAIL: {len(problems)} 件 ==")
    for p in problems:
        print("  NG:", p)
    sys.exit(1)
if skips:
    print(f"== PASS: 実施した検査は全部通った（SKIP: {'・'.join(skips)}） ==")
    sys.exit(0)
print("== PASS: スキル資産は健全（構造・参照・旧パス・断言・競合・compile・メモリリンク・agents体制 全クリア） ==")
sys.exit(0)
