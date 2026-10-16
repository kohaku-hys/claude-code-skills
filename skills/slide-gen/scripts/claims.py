# -*- coding: utf-8 -*-
"""claims.py — 提示前の「証拠の照合」への受け渡しと、その判定の記録（slide-gen。brief.py の仲間。2026-09-28）。

独立の照合エージェント slide-evidence-checker には、下書き（画像・design_spec・会話）を見せず、
スライドから抜き出した主張と、素材のパスだけを渡す（claim-verifier の考え方）。
このスクリプトは、その受け渡し用の review/claims.json を作り、照合の判定（PASS / FAIL）を
spec_lock.md に1行で記録する。deck_doctor の R0 は、この行の hash と今の中身の hash を比べる
（hash の計算は deck_doctor.content_hash と同じ物を使う）。
claims.json には、素材ごとの行数と '> ' の逐語行の数（sources_read。2026-09-28）と、役割の読み方（roles。
A=目次は主張ではない）も入れる。

2026-10-01 に「初見の読み手」（slide-reader・deck_doctor の R1）への受け渡しを足した。
本人「今のスライド生成は結局何を言いたいのか伝わらない」と、Kiminori Yokoi「AI臭い文章とは何なのか」
（豊洲会 2026-09-28）の「話者の説明なしに意味理解を復元できないと、資料を再配布しにくい」から。
slide-reader には、スライドに見えている文字だけ（review/slide_text.md）を渡す。ノート・brief・画像は渡さない。

使い方:
    py claims.py <proj>                                                  # review/claims.json を書き、hash を表示
    py claims.py <proj> --record PASS --report review/evidence_check.md   # 判定を spec_lock に1行で書く（FAIL も同じ）
    py claims.py <proj> --reader                                          # review/slide_text.md（スライドの文字だけ）を書く
    py claims.py <proj> --record-reader PASS --report review/reader_check.md  # 初見の読み手の判定を1行で書く
    py claims.py <proj> --minor "誤字の修正"                              # 判定は PASS のまま、hash だけ付け直す（両方の行）
spec_lock に書く行:
    evidence_check: PASS 2026-09-29 hash=<10桁> report=review/evidence_check.md [minor=理由]
    reader_check: PASS 2026-10-01 hash=<10桁> report=review/reader_check.md [minor=理由]
終了コード: 0=書いた / 1=書かない（SVG が無い・report が無い・PASS の記録が無いのに --minor 等）
"""
import argparse
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


# claims.json の role の読み方（照合エージェント向け。A の目次の枚は主張ではなく、後の枚の見出しの一覧）
ROLE_NAMES = {'C': '表紙', 'A': '目次（主張ではない。項目が後の枚と合っているかだけ見る）', 'P': '結論', 'R': '理由',
              'E': '具体例・データ', 'T': '謝辞・質疑・参考文献', '?': 'prep に無い枚'}


def source_facts(brief, proj):
    """sources_read の各素材の path・行数（lines）・'> ' の逐語行の数（verbatim）。
    照合エージェントが「'> ' の決まりがある素材か」を知るため（verbatim が 0 なら、逐語は「」の中で探す）。
    素材を開ければ実物を数え（from=file）、開けない素材は brief の記録をそのまま渡す（from=brief）。"""
    out = []
    for it in brief.get('sources_read') or []:
        if not isinstance(it, dict):
            continue
        path = dd.expand_path(it.get('path'), proj)
        lines = dd.read_source_lines(path)
        if lines is not None:
            if path.suffix.lower() in ('.md', '.markdown'):
                verbatim = dd.count_verbatim_lines(lines)
            else:
                verbatim = it.get('verbatim', 0)
            out.append({'path': str(path), 'lines': len(lines), 'verbatim': verbatim, 'from': 'file'})
        else:
            out.append({'path': str(path), 'lines': it.get('lines'), 'verbatim': it.get('verbatim'), 'from': 'brief'})
    return out


def build_claims(proj):
    """claims.json の中身（brief の結論・証拠と、枚ごとの小ラベル・見出し・本文・ノート）。"""
    _, svg_dir = dd.resolve_svg_dir(proj)
    svg_files = sorted(svg_dir.glob('*.svg'))
    roles = dd.parse_prep(proj) or {}
    notes = dd.notes_by_slide(proj) or {}
    brief, _, problem = dd.load_brief(proj)
    brief = brief or {}
    slides = []
    for i, f in enumerate(svg_files, 1):
        body, _ = dd.body_lines(f)
        head_lines = dd._headline_lines(body)
        eb = dd._eyebrow(body, head_lines)
        skip = set(id(ln) for ln in head_lines)
        if eb is not None:
            skip.add(id(eb))
        slides.append({
            'n': i,
            'file': f.name,
            'role': (roles.get(i) or ['?'])[0],
            'eyebrow': eb.text if eb is not None else '',
            'headline': ''.join(ln.text for ln in head_lines),
            'body': '\n'.join(ln.text for ln in body if id(ln) not in skip),
            'notes': notes.get(i, '').strip(),
        })
    sources = [str(dd.expand_path(it.get('path'), proj)) for it in brief.get('sources_read') or []
               if isinstance(it, dict)]
    data = {
        'project': proj.name,
        'hash': dd.content_hash(proj, svg_files),
        'p': brief.get('p', ''),
        'p_core': brief.get('p_core', []),
        'p_last': brief.get('p_last', ''),
        'me': brief.get('me', {}),
        'proof': brief.get('proof', []),
        'sources': sources,
        'sources_read': source_facts(brief, proj),
        'roles': ROLE_NAMES,
        'slides': slides,
    }
    return data, svg_files, problem



PAGE_NO_RE = re.compile(r'^\d{1,3}\s*/\s*\d{1,3}$')


def build_slide_text(proj):
    """slide-reader に渡す review/slide_text.md の中身（スライドに見えている文字だけ）。
    <text> ごとに1行、上から下・左から右の順。見出し・小ラベル・※の行に印を付ける。ページ番号は外す。
    画像は数だけ書く（中身は書かない＝読み手が文字で意味を取れるかを見るため）。ノート・brief・役割は入れない。"""
    _, svg_dir = dd.resolve_svg_dir(proj)
    svg_files = sorted(svg_dir.glob('*.svg'))
    out = ['# スライドの文字（ノート・brief・画像の中身は含まない）',
           'デッキ: %s・%d枚' % (proj.name, len(svg_files)),
           '印: 【見出し】【小ラベル】【※】（出典・注記の行）。印の無い行は本文。[画像 N点] はその枚に写真か図の画像があることだけを示す。',
           '']
    for i, f in enumerate(svg_files, 1):
        lines, _ = dd.extract_lines(f)
        lines = [ln for ln in lines if ln.text and not ln.text.startswith('\x00') and not PAGE_NO_RE.match(ln.text.strip())]
        body, _ = dd.body_lines(f)
        heads = set(ln.text for ln in dd._headline_lines(body))
        eb = dd._eyebrow(body)
        blocks = []
        for group in dd.text_groups(lines):
            t = ''.join(ln.text for ln in group).strip()
            if not t:
                continue
            y = min(ln.y for ln in group)
            x = min(ln.x for ln in group)
            if eb is not None and any(ln is eb or ln.text == eb.text for ln in group):
                tag = '【小ラベル】'
            elif any(ln.text in heads for ln in group):
                tag = '【見出し】'
            elif t.startswith(dd.SOURCE_PREFIXES):
                tag = '【※】'
            else:
                tag = ''
            blocks.append((y, x, tag + t))
        blocks.sort(key=lambda b: (b[0], b[1]))
        n_img = len(re.findall(r'<image\b', f.read_text(encoding='utf-8', errors='replace')))
        out.append('## %02d枚目%s' % (i, ('　[画像 %d点]' % n_img) if n_img else ''))
        out += [b[2] for b in blocks] or ['（文字なし）']
        out.append('')
    return '\n'.join(out) + '\n', svg_files


def write_record(proj, line, line_re=None):
    """spec_lock の evidence_check 行（line_re を渡せば reader_check 行）を1行だけにして書く（何度流しても1行）。"""
    sl = proj / 'spec_lock.md'
    text = sl.read_text(encoding='utf-8') if sl.is_file() else '# Spec Lock\n'
    text = (line_re or dd.EVIDENCE_LINE_RE).sub('', text).rstrip('\n')
    sl.write_text(text + '\n\n' + line + '\n', encoding='utf-8')


def main(argv=None):
    ap = argparse.ArgumentParser(description='証拠の照合への受け渡し（claims.json）と判定の記録')
    ap.add_argument('proj', help='プロジェクトdir')
    ap.add_argument('--record', choices=['PASS', 'FAIL'], help='照合の判定を spec_lock に書く')
    ap.add_argument('--report', help='照合の報告（例: review/evidence_check.md）。--record の時は必須')
    ap.add_argument('--minor', help='判定は PASS のまま hash だけ付け直す（誤字の修正など。理由を書く）')
    ap.add_argument('--reader', action='store_true',
                    help='初見の読み手（slide-reader）に渡す review/slide_text.md（スライドの文字だけ）を書く')
    ap.add_argument('--record-reader', choices=['PASS', 'FAIL'],
                    help='初見の読み手の判定を spec_lock に書く（--report review/reader_check.md と一緒に）')
    args = ap.parse_args(argv)

    if dd is None:
        print('deck_doctor.py を import できない: %s（slide-gen の scripts に同梱の deck_doctor.py があるか確かめる）' % DD_DIR)
        return 1
    proj = Path(args.proj)
    _, svg_dir = dd.resolve_svg_dir(proj)
    svg_files = sorted(svg_dir.glob('*.svg')) if svg_dir.is_dir() else []
    if not svg_files:
        print('SVG がありません: %s' % svg_dir)
        return 1
    today = datetime.date.today().isoformat()

    # 初見の読み手への受け渡し
    if args.reader:
        text, _ = build_slide_text(proj)
        out = proj / 'review' / 'slide_text.md'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding='utf-8')
        print('slide_text.md を書いた: %s' % out)
        print('content_hash: %s' % dd.content_hash(proj, svg_files))
        print('次: slide-reader に review/slide_text.md の絶対パスだけを渡す（ノート・brief・画像・会話は渡さない）')
        return 0
    # 初見の読み手の判定の記録
    if args.record_reader:
        if not args.report:
            print('--record-reader には --report（読み手の報告のパス）が要る')
            return 1
        if not dd.expand_path(args.report, proj).is_file():
            print('読み手の報告が無い: %s（slide-reader の報告を先に保存する）' % args.report)
            return 1
        line = 'reader_check: %s %s hash=%s report=%s' % (
            args.record_reader, today, dd.content_hash(proj, svg_files), args.report)
        write_record(proj, line, dd.READER_LINE_RE)
        print('spec_lock に書いた: %s' % line)
        return 0
    # 判定の記録
    if args.record:
        if args.record == 'FAIL' and args.minor:
            print('--minor は PASS の時だけ使える（FAIL は直して照合をやり直す）')
            return 1
        if not args.report:
            print('--record には --report（照合の報告のパス）が要る')
            return 1
        if not dd.expand_path(args.report, proj).is_file():
            print('照合の報告が無い: %s（slide-evidence-checker の報告を先に保存する）' % args.report)
            return 1
        line = 'evidence_check: %s %s hash=%s report=%s' % (
            args.record, today, dd.content_hash(proj, svg_files), args.report)
        if args.minor:
            line += ' minor=%s' % ' '.join(args.minor.split())
        write_record(proj, line)
        print('spec_lock に書いた: %s' % line)
        return 0
    if args.minor:
        rec = dd.read_evidence_check(proj)
        if rec is None or rec['verdict'] != 'PASS':
            print('PASS の記録が無いので --minor は使えない（slide-evidence-checker の照合をやり直す）')
            return 1
        reason = ' '.join(args.minor.split())
        now = dd.content_hash(proj, svg_files)
        line = 'evidence_check: PASS %s hash=%s report=%s minor=%s' % (
            rec['date'] or today, now, rec['report'] or 'review/evidence_check.md', reason)
        write_record(proj, line)
        print('spec_lock に書いた（hash だけ付け直し）: %s' % line)
        # 初見の読み手の記録も、PASS なら同じ理由で付け直す（FAIL・記録なしは触らない＝R1 がそのまま止める）
        rrec = dd.read_reader_check(proj)
        if rrec is not None and rrec['verdict'] == 'PASS':
            rline = 'reader_check: PASS %s hash=%s report=%s minor=%s' % (
                rrec['date'] or today, now, rrec['report'] or 'review/reader_check.md', reason)
            write_record(proj, rline, dd.READER_LINE_RE)
            print('spec_lock に書いた（hash だけ付け直し）: %s' % rline)
        return 0

    # 受け渡し用の claims.json
    data, _, problem = build_claims(proj)
    out = proj / 'review' / 'claims.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('claims.json を書いた: %s（%d 枚）' % (out, len(data['slides'])))
    if problem:
        print('⚠ %s（p / proof が空のまま渡すことになる。先に brief.py で台帳を作る）' % problem)
    print('content_hash: %s' % data['hash'])
    print('次: slide-evidence-checker に review/claims.json と、sources の各パスだけを渡す'
          '（画像・design_spec・会話は渡さない）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
