# -*- coding: utf-8 -*-
"""brief.py — STEP 1-0c「中身の確認（選択式）」の答え＝証拠の台帳（v2）を brief.json と spec_lock.md に書く。

2026-09-28 v2（本人指摘「中身がないというか」）。v1 は p / r / e を文字列で書くだけだったので、
結論を証明する証拠が無くても、注記や推測の行を「本人の言葉」にしても通っていた。v2 では
証拠ごとに出典の行（ファイル名:行）と引用を書き、その引用が本当にその行にあるかを確かめてから書く。

本人が AskUserQuestion などの選択式で選んだ答えを JSON にして渡すと、
  - <project>/brief.json に、その JSON をそのまま書く（deck_doctor の C1〜C6・G1〜G5 はここを読む）
  - spec_lock.md に「## genre / - genre: xxx」と、brief_confirmed / brief_version: 2 / brief（人が読む要約）/ prep の1組を書く
    （既にあれば置き換える。何度流しても1組だけ）

使い方:
    py brief.py <project_dir> <answers.json>
answers.json（v2。旧書式の p / r / e の文字列だけ、は受け付けない）:
{
  "brief_version": 2, "how": "選択式",            // 本人一任でも証拠欄は免除しない（選ぶのを任されただけ）
  "genre": "experience",                          // 資料の種類（下の一覧）。無ければ general と書いて exit 2
  "audience": "学生支援室への研修報告・10分",
  "overview": [{"k": "期間", "v": "8月16日〜22日", "src": "研修メモ_現地投函.md:3", "quote": "8月16日から22日まで"}],
                                                  // 概要の事実（いつ・どこで・何を）。experience / progress は必須
  "p": "…", "p_core": ["やる気", "熱意"], "p_last": "…（p と別の文。E の具体を1つ含む）",
  "r": [{"id": "R1", "claim": "教える側が本気だった", "slides": [3]}],
  "proof": [{"id": "E1", "for": "R1", "kind": "verbatim", "src": "研修メモ_現地投函.md:243",
             "quote": "進路を考えて行動しただけ", "slides": [4]}],
  "me": {"why": "…", "scene": {"src": "研修メモ_現地投函.md:398", "quote": "…"}, "next": "…"},
  "sources_read": [{"path": "…\\研修メモ_現地投函.md", "lines": 574, "read": "1-574", "verbatim": 52,
                    "inventory": "sources/inventory.md"}],
  "cta": "…", "ng": ["…"], "prep": "C 1 / A 2 / P 3 / R 4 / E 5 / P 6",
  "flow": "prep", "flow_why": ""                  // 話の順番（下の一覧）。無ければ prep。prep 以外は spec_lock に flow: 行を書く
}
flow（2026-10-01 本人の回答「② PREP は既定のまま、別の順も選べる」。資料「AI臭い文章とは何なのか」の
      「AI臭いスライドは説明の全体の流れをAIに固定される」から）:
      prep（既定。結論→理由→具体例→結論）/ chronological（時系列。結論は最後）/
      problem（困りごと→原因→対策。対策が結論）/ custom（本人が決めた順）。
      prep 以外では p_last を省いてよい（結論が最後の1回だけの順があるため。省けば p と同じ文を入れる）。
genre: experience（体験・研修・留学・出張の報告）/ progress（進捗・中間）/ proposal（提案・企画・申請・コンペ）/
       research（研究・実験・授業発表・調べ学習の発表）/ explainer（解説・勉強会・LT）/ notice（告知）/ general。
prep の役割: C=表紙 A=目次（表紙の直後に1枚） P=結論 R=理由 E=具体例・データ T=謝辞・質疑・参考文献。
kind: verbatim（本人や相手の逐語）/ scene（日時・場所・人が揃った場面）/ number / photo / diagram / table /
      annotation（Claude 側の注記）/ web。photo の quote は空でよい（deck_doctor が画像の href で照合する）。
相対パス（sources_read.path・inventory）はプロジェクトを基準にする。

終了コード:
  0 = 書いた
  1 = 書かない。必須8欄（p, p_core, p_last, r, proof, me, sources_read, prep）のどれかが空／引用が出典の行
      （前後2行）に無い／出典が sources_read に無い／読んだ範囲が全行を覆わない・'> ' の逐語行の数が合わない／
      inventory が無い・証拠の ID が載っていない／p と p_last がほぼ同じ文（flow=prep の時だけ）／flow が一覧に無い値／
      結論の強い証拠（逐語・写真・数字・場面）が2件未満（deck_doctor の C2 と同じ重さ）／genre が一覧に無い値／
      genre が experience・progress なのに overview が空／overview の quote が出典の行（前後2行）に無い
  2 = 書いたが警告。p か p_last に具体（数字・カタカナ3字以上・「・英字2字以上）が無い／対句（〜ではなく〜 等）／
      推測・起草の行を使っている／素材を開けず照合できない／genre が無い（general と書く）
検査の関数（正規化・対句・bigram・逐語行の数え方・出典の照合）は deck_doctor.py から import する
（2か所で判定がずれないように）。deck_doctor.py は同じ scripts フォルダの同梱版を使う。
"""
import datetime
import json
import os
import re
import sys
from pathlib import Path

# deck_doctor.py はこのファイルと同じ scripts フォルダに同梱してある（上流の ppt-master には無いため）
DD_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DD_DIR))
try:
    import deck_doctor as dd
except ImportError:
    dd = None

CONCRETE = re.compile(r'[0-9０-９]|[ァ-ヶー]{3,}|「|『|[A-Za-z]{2,}')
KINDS = ('verbatim', 'scene', 'number', 'photo', 'diagram', 'table', 'annotation', 'web')
# brief_confirmed 行・続く brief_version 行・brief: 行・その下の字下げ行をまとめて1組として消す。
# 2026-09-28 までの版は brief_confirmed の1行で止まり、古い brief: の塊が残って2組になっていた
BLOCK_RE = re.compile(r'^brief_confirmed:.*(?:\n|\Z)(?:^brief_version[^\S\n]*[:：].*(?:\n|\Z))?'
                      r'(?:^brief[^\S\n]*[:：].*(?:\n|\Z))?(?:^[ \t]+\S.*(?:\n|\Z))*',
                      re.MULTILINE)
ORPHAN_RE = re.compile(r'^brief[^\S\n]*[:：][^\S\n]*(?:\n|\Z)(?:^[ \t]+\S.*(?:\n|\Z))*', re.MULTILINE)
VERSION_RE = re.compile(r'^brief_version[^\S\n]*[:：].*(?:\n|\Z)', re.MULTILINE)
PREP_RE = re.compile(r'^[\s\-*>]*prep[^\S\n]*[:：].*$\n?', re.IGNORECASE | re.MULTILINE)
# 「## genre」の見出しと「- genre: xxx」の行（何度流しても1組だけにするため、書く前に消す）
GENRE_HEAD_RE = re.compile(r'^##[^\S\n]*genre[^\S\n]*(?:\n|\Z)', re.IGNORECASE | re.MULTILINE)
GENRE_LINE_RE = re.compile(r'^[ \t\-*>]*genre[^\S\n]*[:：].*(?:\n|\Z)', re.IGNORECASE | re.MULTILINE)
# 話の順番（flow）。一覧の正本は deck_doctor.FLOWS（無い版の deck_doctor でも動くように同じ値を持つ）
FLOWS_FALLBACK = ('prep', 'chronological', 'problem', 'custom')
FLOW_LINE_RE = re.compile(r'^[ \t\-*>]*flow[^\S\n]*[:：].*(?:\n|\Z)', re.IGNORECASE | re.MULTILINE)


def flows():
    return tuple(getattr(dd, 'FLOWS', FLOWS_FALLBACK))


def flow_of(a):
    return str((a or {}).get('flow') or 'prep').strip().lower()


def one_line(v):
    """要約に入れる値を1行にする（改行で spec_lock の塊が切れないように）。"""
    if isinstance(v, list):
        v = ' / '.join(str(x) for x in v)
    return re.sub(r'\s*\n\s*', ' ', str(v or '')).strip()


def build_block(a):
    """spec_lock に書く1組（人が読む要約。機械の判定は brief.json を使う）。"""
    today = datetime.date.today().isoformat()
    proofs = [x for x in a.get('proof') or [] if isinstance(x, dict)]
    lines = ['brief_confirmed: %s %s' % (today, one_line(a.get('how', '選択式'))),
             'brief_version: 2',
             'brief:',
             '  ledger: brief.json（証拠の台帳。deck_doctor の C1〜C6 はこちらを読む）',
             '  audience: %s' % one_line(a.get('audience')),
             '  p: %s' % one_line(a.get('p')),
             '  p_core: %s' % one_line(a.get('p_core')),
             '  p_last: %s' % one_line(a.get('p_last'))]
    for r in a.get('r') or []:
        ev = ['%s(%s)' % (pr.get('id'), pr.get('src')) for pr in proofs if str(pr.get('for')) == str(r.get('id'))]
        lines.append('  %s: %s ← %s' % (r.get('id'), one_line(r.get('claim')), ', '.join(ev) or '証拠なし'))
    ev = ['%s(%s)' % (pr.get('id'), pr.get('src')) for pr in proofs if str(pr.get('for', '')).upper() == 'P']
    lines.append('  結論の証拠: %s' % (', '.join(ev) or 'なし'))
    me = a.get('me') if isinstance(a.get('me'), dict) else {}
    scene = me.get('scene') if isinstance(me.get('scene'), dict) else {}
    lines.append('  本人の場面: %s（%s）' % (one_line(scene.get('quote')), one_line(scene.get('src'))))
    lines.append('  cta: %s' % one_line(a.get('cta')))
    lines.append('  ng: %s' % one_line(a.get('ng')))
    lines.append('prep: %s' % one_line(a.get('prep')))
    flow = flow_of(a)
    if flow != 'prep':
        # deck_doctor の check_prep が読む。PREP の順番の検査を、この順に合わせて緩める
        lines.append('flow: %s %s 本人 %s' % (flow, today, one_line(a.get('flow_why')) or '選択式で本人が選んだ'))
    return '\n'.join(lines) + '\n'


def check_answers(a, proj):
    """returns (書かない理由のリスト, 警告のリスト)"""
    errors = []
    warns = []
    if not isinstance(a, dict):
        return ['answers.json の中身が {…} の形でない'], warns
    ver = a.get('brief_version', 2)
    if str(ver) != '2':
        errors.append('brief_version が 2 でない（%s）' % ver)
    # 資料の種類（deck_doctor の G1〜G9 の重さが変わる）
    genre = str(a.get('genre') or '').strip().lower()
    if not genre:
        warns.append('genre が無い＝general と書く（%s から選ぶと、資料の種類に合った検査が走る）'
                     % ' / '.join(dd.GENRES))
    elif genre not in dd.GENRES + ('general',):
        errors.append('genre「%s」が不明（%s / general のどれか）' % (a.get('genre'), ' / '.join(dd.GENRES)))
    flow = flow_of(a)
    if flow not in flows():
        errors.append('flow「%s」が不明（%s のどれか）' % (a.get('flow'), ' / '.join(flows())))
    elif flow != 'prep' and not str(a.get('p_last') or '').strip() and str(a.get('p') or '').strip():
        a['p_last'] = a.get('p')    # 結論が最後の1回だけの順。p と同じ文を入れて必須欄を満たす
    miss = dd.brief_missing_keys(a)
    if miss:
        errors.append('必須欄が空: %s（旧書式の p / r / e の文字列だけでは受け付けない。本人一任でも証拠欄は埋める）'
                      % ', '.join(miss))
        return errors, warns
    # 形の確認（後の検査が読めるように）
    for r in a.get('r') or []:
        if not isinstance(r, dict) or not r.get('id'):
            errors.append('r の各項目は {id, claim, slides} の形にする（旧書式の文字列は不可）: %s' % str(r)[:30])
    for pr in a.get('proof') or []:
        if not isinstance(pr, dict) or not pr.get('id'):
            errors.append('proof の各項目は {id, for, kind, src, quote, slides} の形にする: %s' % str(pr)[:30])
        elif pr.get('kind') not in KINDS:
            errors.append('%s の kind「%s」が不明（%s のどれか）' % (pr.get('id'), pr.get('kind'), ' / '.join(KINDS)))
    overview = a.get('overview') or []
    if not isinstance(overview, list) or not all(isinstance(x, dict) for x in overview):
        errors.append('overview は [{k, v, src, quote}, …] の形にする')
        overview = []
    if genre in ('experience', 'progress') and not overview:
        errors.append('genre=%s なのに overview（概要の事実: いつ・どこで・何を）が空＝'
                      '[{"k": "期間", "v": "8月16日〜22日", "src": "研修メモ.md:3", "quote": "…"}] の形で書く' % genre)
    for x in overview:
        if not str(x.get('v') or '').strip():
            errors.append('overview の %s の v（スライドで見せる値）が空' % (x.get('k') or '?'))
    if errors:
        return errors, warns
    # C3（引用が出典の行にあるか）と C4（読んだ記録が素材の実物と合うか）は deck_doctor と同じ関数で見る。
    # overview の quote も C3 と同じ照合（deck_doctor の G1 と同じ関数）
    for sev, msg, _fix in dd.trace_proofs(a, proj) + dd.trace_overview(a, proj) + dd.audit_sources_read(a, proj):
        if sev == 'ERROR':
            errors.append(msg)
        else:
            warns.append(msg)
    p = str(a.get('p') or '')
    p_last = str(a.get('p_last') or '')
    j = dd.bigram_jaccard(p, p_last)
    if j >= 0.8 and flow == 'prep':
        errors.append('p と p_last がほぼ同じ文（J=%.2f）＝最後の結論は、E の具体を1つ足して言い直す' % j)
    for name, s in (('p', p), ('p_last', p_last)):
        if name == 'p_last' and flow != 'prep' and s == p:
            continue
        if not CONCRETE.search(s):
            warns.append('%s に具体（数字・固有名詞・「」の言葉）が無い:「%s」— 数字・固有名詞・場面を入れた案を本人に出し直す'
                         % (name, s))
        if dd.has_contrast(s):
            warns.append('%s が対句のまとめ文（〜ではなく〜・AよりB・〜て初めて）:「%s」— 言い切りの1文にする' % (name, s))
    # 2026-09-28: deck_doctor の C2 と同じ重さ（書いた後の build で必ず止まる物を、ここで通さない）
    n = dd.strong_p_count(a)
    if n < 2:
        errors.append('結論（for=P）の強い証拠（逐語・写真・数字・場面）が %d 件＝2件以上にする（注記と web は数えない）' % n)
    return errors, warns


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 1
    if dd is None:
        print('deck_doctor.py を import できない: %s（slide-gen の scripts に同梱の deck_doctor.py があるか確かめる）' % DD_DIR)
        return 1
    proj = Path(argv[1])
    ans = json.loads(Path(argv[2]).read_text(encoding='utf-8-sig'))
    errors, warns = check_answers(ans, proj)
    if errors:
        print('書かなかった（直して流し直す）:')
        for e in errors:
            print('  ✗ ' + e)
        return 1
    if 'brief_version' not in ans:
        ans['brief_version'] = 2
    genre = str(ans.get('genre') or '').strip().lower() or 'general'   # 無ければ general と書く（exit 2）
    ans['genre'] = genre
    (proj / 'brief.json').write_text(json.dumps(ans, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    sl = proj / 'spec_lock.md'
    text = sl.read_text(encoding='utf-8') if sl.is_file() else '# Spec Lock\n'
    if not text.endswith('\n'):
        text += '\n'
    text = PREP_RE.sub('', VERSION_RE.sub('', ORPHAN_RE.sub('', BLOCK_RE.sub('', text))))
    text = FLOW_LINE_RE.sub('', GENRE_LINE_RE.sub('', GENRE_HEAD_RE.sub('', text))).rstrip('\n')
    sl.write_text(text + '\n\n## genre\n- genre: %s\n\n' % genre + build_block(ans), encoding='utf-8')
    print('brief.json と spec_lock.md（genre: %s・brief_version: 2・prep・flow: %s）を書いた: %s'
          % (genre, flow_of(ans), proj))
    if warns:
        for w in warns:
            print('⚠ ' + w)
        if any(dd.SPECULATION_RE.search(w) for w in warns):
            print('  → 推測・起草の行は、本人に選択式で確かめる（例「Q&A は 8/18 の機械工学科の教授だった？'
                  ' はい／いいえ／覚えていない」）。確認が取れるまでは、スライドに「〜とみられる」と書くか、使わない')
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
