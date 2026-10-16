"""report/run_pipeline.py - レポート品質チェック一括実行

usage:
    python run_pipeline.py <docx> [options]

options:
    --requirements <要領PDF>      STEP 0.5 要件抽出を実行（＋要領の「切り出し禁止」と図の画像名の照合＝警告のみ）
    --textbook <教科書PDF>        STEP 4b PDF語彙チェックを実行
    --source <実測データ>         STEP 4b 表データ照合（compare_tables.py）。xlsx/docx。複数指定可
    --skip-table <N>              compare_tables.py に渡す（理論値の表など入力に無いのが正しい表）。複数可
    --skip-col <N:k>              compare_tables.py に渡す（表N の k 列目＝誤差率などの計算列）。複数可
    --fig-start <N>               lint.py に渡す図番号開始
    --table-start <N>             lint.py に渡す表番号開始
    --no-strict                   NGでも exit 0（旧挙動。既定は strict=NGで exit 1）

実行内容:
    STEP 0.5: extract_requirements.py  （--requirements 指定時）
    STEP 4b:  lint.py
    STEP 4b:  check_ai_likeness.py
    STEP 4b:  pdf_vocab_check.py       （--textbook 指定時）
    STEP 4b:  compare_tables.py        （--source 指定時。未指定なら「未実行」と集約レポートに残す）
    STEP 4b:  要領の切り出し禁止チェック（--requirements 指定時・警告のみで合否には数えない）

出力:
    <docx>と同じフォルダに `<docx名>_pipeline_report.md` として全結果を集約。
    各スクリプトの標準出力をセクションごとにまとめる。
"""
import sys
import io
import os
import re
import argparse
import subprocess
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))

# 要領PDFの「図の切り出し禁止」らしい文（切り出し系の語と、禁止系の語が同じ文にある）
CUT_WORDS = re.compile(r'切り(?:取|抜|出)|切取|切抜|スクリーンショット|スクショ|コピー(?:して|＆|&)?(?:貼|ペースト)|そのまま貼')
BAN_WORDS = re.compile(r'禁止|しない(?:こと|で)|不可|不適|E\s*判定|認めない|減点')
# 切り出し画像らしい名前（python-docx は画像のファイル名を pic:cNvPr の name に残す）
CUT_NAME = re.compile(r'pdf|crop|clip|cutout|切り|切出|切抜|textbook|教科書|screenshot|スクショ|page\d|_p\d+|^p\d+_',
                      re.IGNORECASE)
PIC_NS = 'http://schemas.openxmlformats.org/drawingml/2006/picture'
WP_NS = 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'


def check_cutout(docx_path, pdf_path):
    """要領に切り出し禁止の文言があるとき、docx の画像名に切り出しらしいものが無いかを見る（警告のみ）。
    2026-09-28 本人決定: 教科書PDFの図を切り出すかは授業ごとに要領に従う（禁止の授業は自作）。
    画像の中身までは判定できないので、名前で分からない物は目視確認を促すだけにする。
    戻り値: 表示する文字列"""
    lines = []
    try:
        import fitz
        pdf = fitz.open(pdf_path)
        text = ''
        for page in pdf:
            text += page.get_text() + '\n'
    except Exception as e:
        return '[警告] 要領PDFが読めないので切り出し禁止の確認を省略: %s' % e
    text = re.sub(r'\s+', ' ', text)
    bans = []
    for sent in re.split(r'(?<=[。．])', text):
        if CUT_WORDS.search(sent) and BAN_WORDS.search(sent):
            bans.append(sent.strip()[:120])
    if not bans:
        return '[情報] 要領PDFに図の切り出し禁止らしい文は見つからない（切り出す場合は出典を図の下に明記）'
    lines.append('[警告] 要領に図の切り出し禁止らしい文がある（この授業は回路図などを自作する）:')
    for s in bans[:3]:
        lines.append('    「%s」' % s)
    from docx import Document
    doc = Document(docx_path)
    names = []
    body = doc.element.body
    for el in body.iter('{%s}cNvPr' % PIC_NS):
        names.append(el.get('name') or '')
    for el in body.iter('{%s}docPr' % WP_NS):
        names.append(el.get('descr') or '')
    suspicious = sorted(set(n for n in names if n and CUT_NAME.search(n)))
    if suspicious:
        lines.append('[警告] 切り出しらしい名前の画像がある: %s → 自作図に差し替える' % ', '.join(suspicious))
    else:
        lines.append('[情報] 画像の名前からは切り出しと分からない（画像 %d 枚）。図が自作か目視で確認する'
                     % len(set(n for n in names if n)))
    return '\n'.join(lines)


def run_step(name, cmd):
    """1ステップ実行し、(成否, stdout, stderr) を返す"""
    print(f'\n========== {name} ==========')
    print(f'cmd: {" ".join(cmd)}')
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding='utf-8', errors='replace'
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(f'[stderr] {result.stderr}', file=sys.stderr)
        ok = (result.returncode == 0)
        print(f'[exit] {result.returncode} {"OK" if ok else "NG"}')
        return ok, result.stdout, result.stderr, result.returncode
    except Exception as e:
        print(f'[NG] 実行失敗: {e}')
        return False, '', str(e), -1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('docx', help='対象Word文書')
    ap.add_argument('--requirements', help='要領PDF（STEP 0.5用）', default=None)
    ap.add_argument('--textbook', help='教科書PDF（STEP 4b PDF語彙チェック用）', default=None)
    ap.add_argument('--source', action='append', default=[],
                    help='実測データの入力ファイル（xlsx/docx）。表データ照合 compare_tables.py を実行。複数可')
    ap.add_argument('--skip-table', action='append', type=int, default=[],
                    help='表データ照合で除外する表番号（理論値の表など）。複数可')
    ap.add_argument('--skip-col', action='append', default=[],
                    help='表データ照合で除外する列（表番号:列番号）。複数可')
    ap.add_argument('--fig-start', type=int, default=None)
    ap.add_argument('--table-start', type=int, default=None)
    # 2026-07-04: strict を既定に変更（NGでも exit 0 だと ops-loop 等の機械判定が効かない）。
    # --strict は後方互換のため受け付ける（no-op）。旧挙動が要る時だけ --no-strict。
    ap.add_argument('--strict', action='store_true', default=True,
                    help='1つでもNGがあれば exit 1（既定でON）')
    ap.add_argument('--no-strict', dest='strict', action='store_false',
                    help='NGでも exit 0 を返す（旧挙動）')
    args = ap.parse_args()

    if not os.path.exists(args.docx):
        print(f'[NG] docxが見つかりません: {args.docx}')
        sys.exit(2)

    py = sys.executable
    results = []  # [(step_name, ok, stdout, stderr, returncode)]

    # STEP 0.5: 要件抽出
    if args.requirements:
        if not os.path.exists(args.requirements):
            print(f'[WARN] 要領PDFが見つかりません（スキップ）: {args.requirements}')
        else:
            cmd = [py, os.path.join(SKILL_DIR, 'extract_requirements.py'), args.requirements]
            ok, out, err, rc = run_step('STEP 0.5: 要件抽出', cmd)
            results.append(('STEP 0.5 要件抽出', ok, out, err, rc))

    # STEP 4b-1: lint.py
    cmd = [py, os.path.join(SKILL_DIR, 'lint.py'), args.docx]
    if args.fig_start is not None:
        cmd += ['--fig-start', str(args.fig_start)]
    if args.table_start is not None:
        cmd += ['--table-start', str(args.table_start)]
    ok, out, err, rc = run_step('STEP 4b-1: lint', cmd)
    results.append(('STEP 4b-1 lint', ok, out, err, rc))

    # STEP 4b-2: AI臭検出
    cmd = [py, os.path.join(SKILL_DIR, 'check_ai_likeness.py'), args.docx]
    ok, out, err, rc = run_step('STEP 4b-2: AI生成っぽさ検出', cmd)
    results.append(('STEP 4b-2 AI生成っぽさ検出', ok, out, err, rc))

    # STEP 4b-3: PDF語彙チェック
    if args.textbook:
        if not os.path.exists(args.textbook):
            print(f'[WARN] 教科書PDFが見つかりません（スキップ）: {args.textbook}')
        else:
            cmd = [py, os.path.join(SKILL_DIR, 'pdf_vocab_check.py'), args.docx, args.textbook]
            ok, out, err, rc = run_step('STEP 4b-3: PDF語彙チェック', cmd)
            results.append(('STEP 4b-3 PDF語彙チェック', ok, out, err, rc))

    # STEP 4b-4: 表データ照合（実測の入力と出力の表をセル単位で比べる・P-035）
    notes = []   # 合否に数えないが集約レポートに必ず残す行
    if args.source:
        missing = [s for s in args.source if not os.path.exists(s)]
        if missing:
            print(f'[NG] 実測データが見つかりません: {missing}')
            results.append(('STEP 4b-4 表データ照合', False, '', f'入力が見つからない: {missing}', 2))
        else:
            cmd = [py, os.path.join(SKILL_DIR, 'compare_tables.py'), args.docx]
            for s in args.source:
                cmd += ['--source', s]
            for n in args.skip_table:
                cmd += ['--skip-table', str(n)]
            for c in args.skip_col:
                cmd += ['--skip-col', c]
            ok, out, err, rc = run_step('STEP 4b-4: 表データ照合', cmd)
            results.append(('STEP 4b-4 表データ照合', ok, out, err, rc))
    else:
        msg = ('[警告] 表データ照合は未実行（--source 未指定）。実測データを使った本レポートなら '
               '--source <記録の xlsx/docx> を付けて流し直す')
        print('\n' + msg)
        notes.append(msg)

    # STEP 4b-5: 要領の切り出し禁止と図の画像名（警告のみ）
    if args.requirements and os.path.exists(args.requirements):
        msg = check_cutout(args.docx, args.requirements)
        print('\n========== STEP 4b-5: 要領の切り出し禁止（警告のみ） ==========')
        print(msg)
        notes.append(msg)

    # 集約レポートを書き出し
    base = os.path.splitext(args.docx)[0]
    report_path = base + '_pipeline_report.md'
    lines = [
        f'# レポート品質チェック集約結果',
        f'',
        f'- 対象: `{os.path.basename(args.docx)}`',
        f'- 実行時刻: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        f'',
        f'## サマリー',
        f'',
        f'| ステップ | 結果 | exit |',
        f'|---|---|---|',
    ]
    for name, ok, _out, _err, rc in results:
        lines.append(f'| {name} | {"OK" if ok else "**NG**"} | {rc} |')

    if notes:
        lines.append('')
        lines.append('## 合否に数えない確認事項')
        lines.append('')
        lines.append('```')
        lines += notes
        lines.append('```')

    lines.append('')
    lines.append('## 各ステップの出力')
    for name, ok, out, err, rc in results:
        lines.append('')
        lines.append(f'### {name} （{"OK" if ok else "NG"}, exit {rc}）')
        lines.append('')
        lines.append('```')
        lines.append(out.rstrip() if out else '(no stdout)')
        lines.append('```')
        if err.strip():
            lines.append('')
            lines.append('stderr:')
            lines.append('```')
            lines.append(err.rstrip())
            lines.append('```')

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print()
    print(f'集約レポート: {report_path}')
    all_ok = all(r[1] for r in results)
    print(f'総合判定: {"OK" if all_ok else "**NG**（修正必要）"}')

    if args.strict and not all_ok:
        sys.exit(1)


if __name__ == '__main__':
    main()
