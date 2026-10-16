"""report/auto_grade_loop.py - 採点結果から減点理由を抽出し、減点パターン集に自動追記

usage:
    # モード1: subagent採点結果のMDを処理する
    python auto_grade_loop.py extract <採点結果.md> --theme "<テーマ名・版>" [--patterns <path>] [--save]

    # モード2: grade.py のプロンプトtxtを subagent 起動用の指示として整形して表示
    python auto_grade_loop.py instruct <採点プロンプト.txt> [--save-as <md path>]

    # モード3: 既存のレポート減点パターン.md の最大P-NNNを表示
    python auto_grade_loop.py next-id [--patterns <path>]

機能:
- 採点結果MDから「総合スコア」「章別小計」「減点理由」「改善提案」を構造化抽出
- 減点理由を `~/.claude/skill-memory/レポート減点パターン.md` に P-NNN として追記
  （--save なしの場合は dry-run で標準出力に表示）
- 既存パターンとのざっくり重複チェック（症状テキストのトークン一致率）
- 90点未満なら再生成推奨フラグを出力し exit 3（extract のみ。90点以上・総合点が読めない時は exit 0）

採点フロー全体:
  1. grade.py で `<docx名>_採点プロンプト.txt` を生成
  2. `auto_grade_loop.py instruct <採点プロンプト.txt>` で subagent 用の起動指示を作る
  3. Claude が Agent ツール (subagent_type=general-purpose) を起動 → 採点結果を受け取る
  4. 受け取った採点結果MDを `<docx名>_採点結果_vN.md` として保存
  5. `auto_grade_loop.py extract <採点結果.md> --theme "..." --save` で減点パターン集に追記
  6. 総合スコアが90点未満なら本文を修正して再採点
"""
import sys
import io
import os
import re
import argparse
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


DEFAULT_PATTERNS_PATH = os.path.expanduser(
    '~/.claude/skill-memory/レポート減点パターン.md'
)


# ============================================================
# 採点結果MDのパース
# ============================================================

def parse_grading_result(md_text):
    """採点結果MDから構造化情報を抽出"""
    result = {
        'total_score': None,
        'max_score': 100,
        'chapters': [],   # [{'name': str, 'score': int, 'max': int, 'deductions': [str]}]
        'improvements': [],
        'raw': md_text,
    }

    # 総合評価: **XX/100点** or XX/100
    m = re.search(r'総合評価[：:]\s*\**\s*(\d+)\s*/\s*(\d+)', md_text)
    if m:
        result['total_score'] = int(m.group(1))
        result['max_score'] = int(m.group(2))

    # 章別採点: ### N章 ...（YY点満点）→ ZZ/YY
    chapter_pattern = re.compile(
        r'###\s*(\d+章[^\n]*?)（(\d+)点満点）\s*[→\-]+\s*(\d+)\s*/\s*\d+',
    )
    for m in chapter_pattern.finditer(md_text):
        result['chapters'].append({
            'name': m.group(1).strip(),
            'max': int(m.group(2)),
            'score': int(m.group(3)),
            'deductions': [],
            'start': m.start(),
        })

    # 各章の「**減点理由（−N点）**：...」を、次章開始までの範囲から抽出
    chapter_starts = [c['start'] for c in result['chapters']] + [len(md_text)]
    for i, ch in enumerate(result['chapters']):
        seg = md_text[chapter_starts[i]:chapter_starts[i + 1]]
        # 「**減点理由（-N点）**：text」あるいは複数行
        ded_pattern = re.compile(
            r'\*\*減点理由[（(]?[-−]?(\d+)?点?[)）]?\*\*[：:]\s*(.+?)(?=\n\n|\n###|\n##|\Z)',
            re.DOTALL,
        )
        for dm in ded_pattern.finditer(seg):
            points = dm.group(1)
            text = dm.group(2).strip()
            # 箇条書きの「- ...」を個別の減点として分割
            items = re.split(r'\n\s*[-・]\s+', '\n- ' + text)
            for it in items:
                it = it.strip()
                if it and len(it) > 4:
                    ch['deductions'].append({
                        'points': int(points) if points else None,
                        'text': it,
                    })
        # 章の構造体から start を削除（後段の出力で邪魔）
        ch.pop('start', None)

    # 改善提案セクション
    imp_match = re.search(r'##\s*改善提案\s*\n(.+?)(?=\n##|\Z)', md_text, re.DOTALL)
    if imp_match:
        body = imp_match.group(1)
        for line in body.splitlines():
            line = line.strip()
            m = re.match(r'^(?:\d+\.|[-・])\s*(.+)', line)
            if m:
                result['improvements'].append(m.group(1).strip())

    return result


# ============================================================
# 既存パターン集の解析
# ============================================================

def read_existing_patterns(patterns_path):
    """既存パターン集を読み、(max_id, [既存症状テキスト群], 全文) を返す"""
    if not os.path.exists(patterns_path):
        return 0, [], ''
    with open(patterns_path, 'r', encoding='utf-8') as f:
        text = f.read()
    ids = re.findall(r'P-(\d+)', text)
    max_id = max(int(i) for i in ids) if ids else 0
    # 各 ### P-NNN ブロックの「症状」行を抽出
    symptoms = []
    for m in re.finditer(
        r'###\s*P-\d+[^\n]*\n(.*?)(?=\n###\s*P-\d+|\Z)', text, re.DOTALL
    ):
        block = m.group(1)
        sm = re.search(r'\*\*症状\*\*[：:](.+?)(?=\n-\s*\*\*|\Z)', block, re.DOTALL)
        if sm:
            symptoms.append(sm.group(1).strip())
    return max_id, symptoms, text


def is_duplicate(new_text, existing_symptoms, threshold=0.5):
    """既存症状テキストとのざっくり一致率で重複判定"""
    new_tokens = set(re.findall(r'[一-龥ぁ-んァ-ヶa-zA-Z0-9]+', new_text))
    if not new_tokens:
        return False, None
    for ex in existing_symptoms:
        ex_tokens = set(re.findall(r'[一-龥ぁ-んァ-ヶa-zA-Z0-9]+', ex))
        if not ex_tokens:
            continue
        overlap = len(new_tokens & ex_tokens) / max(len(new_tokens), 1)
        if overlap >= threshold:
            return True, ex
    return False, None


# ============================================================
# 新規パターンのレンダリング
# ============================================================

def render_pattern_block(pid, name, theme, symptom, cause, action, detection):
    return (
        f'\n### P-{pid:03d} {name}（{theme}で発生）\n'
        f'- **症状**: {symptom}\n'
        f'- **原因**: {cause}\n'
        f'- **対策**: {action}\n'
        f'- **検出**: {detection}\n'
    )


def infer_pattern_name(deduction_text):
    """減点理由テキストからパターン名（短い見出し）を推測"""
    text = deduction_text.replace('\n', ' ').strip()
    text = re.sub(r'^[-・\d.]+\s*', '', text)
    # 最初の句点 or 30文字までを名前として使う
    cut = re.split(r'[。、,]', text, maxsplit=1)[0]
    if len(cut) > 40:
        cut = cut[:40] + '…'
    return cut


def infer_detection(deduction_text):
    """検出手段を推測（lint/AI/手動/subagent）"""
    t = deduction_text
    if any(k in t for k in ['番号', '飛び番', 'キャプション', '参照', '記号', 'Heading', '見出し']):
        return '`lint.py`'
    if any(k in t for k in ['AI', '考えられる', '実現されている', '把握', '理解']):
        return '`check_ai_likeness.py`'
    if any(k in t for k in ['教科書', '範囲外', 'PDF']):
        return '`pdf_vocab_check.py`'
    return 'subagent採点'


# ============================================================
# extract コマンド
# ============================================================

def cmd_extract(args):
    if not os.path.exists(args.grading_md):
        print(f'[NG] 採点結果MDが見つかりません: {args.grading_md}')
        sys.exit(2)

    with open(args.grading_md, 'r', encoding='utf-8') as f:
        md = f.read()

    parsed = parse_grading_result(md)

    print('========== 採点結果サマリー ==========')
    print(f'総合: {parsed["total_score"]}/{parsed["max_score"]}'
          if parsed['total_score'] is not None else '総合: (抽出失敗)')
    for ch in parsed['chapters']:
        print(f'  {ch["name"]}: {ch["score"]}/{ch["max"]} '
              f'(減点理由 {len(ch["deductions"])} 件)')

    all_deductions = []
    for ch in parsed['chapters']:
        for d in ch['deductions']:
            all_deductions.append((ch['name'], d))

    if not all_deductions:
        print('\n[INFO] 減点理由が抽出できませんでした。採点結果MDのフォーマットを確認してください。')
        # 構造に頼らず改善提案だけ救済
        if parsed['improvements']:
            print(f'\n改善提案 {len(parsed["improvements"])} 件:')
            for i, imp in enumerate(parsed['improvements'], 1):
                print(f'  {i}. {imp}')
        return _maybe_print_regen_hint(parsed, args)

    patterns_path = args.patterns or DEFAULT_PATTERNS_PATH
    max_id, existing_symptoms, full_text = read_existing_patterns(patterns_path)
    print(f'\n既存パターン: 最大ID = P-{max_id:03d} ({len(existing_symptoms)} ブロック)')

    new_blocks = []
    next_id = max_id + 1
    for ch_name, d in all_deductions:
        text = d['text']
        dup_result = is_duplicate(text, existing_symptoms)
        if isinstance(dup_result, tuple) and dup_result[0]:
            print(f'\n[SKIP 重複] {ch_name}: {text[:60]}...')
            continue

        name = infer_pattern_name(text)
        symptom = f'【{ch_name}】{text}'
        cause = '（要分析。subagent採点で初出）'
        if d['points']:
            cause += f' / 配点 -{d["points"]}点'
        action = '（次回までに具体策を記入）'
        detection = infer_detection(text)
        block = render_pattern_block(next_id, name, args.theme, symptom, cause, action, detection)
        new_blocks.append((next_id, name, block))
        next_id += 1

    print(f'\n========== 追記候補（{len(new_blocks)} 件）==========')
    for pid, name, block in new_blocks:
        print(block)

    if not new_blocks:
        print('[INFO] 追記すべき新規パターンはありません。')
        return _maybe_print_regen_hint(parsed, args)

    if args.save:
        # 既存ファイルの末尾に追記
        append_text = '\n\n'.join(b[2] for b in new_blocks)
        # skill-memory のフォルダがまだ無い環境（初めて使う時）でも追記できるように作っておく
        os.makedirs(os.path.dirname(os.path.abspath(patterns_path)), exist_ok=True)
        with open(patterns_path, 'a', encoding='utf-8') as f:
            f.write(f'\n\n<!-- auto_grade_loop.py 追記: {datetime.now().strftime("%Y-%m-%d %H:%M")} ({args.theme}) -->\n')
            f.write(append_text)
        print(f'\n[OK] {patterns_path} に {len(new_blocks)} 件追記しました。')
        print('     索引（パターンID一覧表）への追記は手動で行ってください。')
        print('     check_ai_likeness.py の AI_PATTERNS 追加も検討してください。')
    else:
        print('\n[DRY-RUN] --save を付けると上記を レポート減点パターン.md に追記します。')

    return _maybe_print_regen_hint(parsed, args)


def _maybe_print_regen_hint(parsed, args):
    """合格水準（90点）に届いたかを表示し、終了コードを返す。
    0=90点以上 / 3=90点未満（再生成が要る） / 0=総合点が読めない時（抽出失敗は上で表示済み）。
    2026-09-28 から 90点未満は exit 3（以前は exit 0 で、機械判定では合否が分からなかった）"""
    if parsed['total_score'] is None:
        return 0
    if parsed['total_score'] < 90:
        print()
        print(f'⚠ 総合スコア {parsed["total_score"]}/100 < 90 → 再生成推奨（exit 3）')
        print('  改善提案を本文に反映し、再度 lint/AI/PDF語彙チェック後に grade.py を回してください。')
        if parsed['improvements']:
            print('  優先改善項目:')
            for i, imp in enumerate(parsed['improvements'][:5], 1):
                print(f'    {i}. {imp}')
        return 3
    print(f'\n✅ 総合スコア {parsed["total_score"]}/100 ≧ 90 → 合格水準')
    return 0


# ============================================================
# instruct コマンド
# ============================================================

def cmd_instruct(args):
    if not os.path.exists(args.grading_prompt):
        print(f'[NG] 採点プロンプトtxtが見つかりません: {args.grading_prompt}')
        sys.exit(2)
    with open(args.grading_prompt, 'r', encoding='utf-8') as f:
        prompt_body = f.read()

    instruction = (
        '# Claude → subagent (general-purpose) 起動指示\n'
        '\n'
        '以下のプロンプトを `Agent` ツールで起動する subagent に渡してください。\n'
        '  - subagent_type: `general-purpose`\n'
        '  - description: "レポート採点（厳しめ・第三者視点）"\n'
        '\n'
        '採点結果を受け取ったら、レポート docx と同じフォルダに `<docx名>_採点結果_v<N>.md` として保存し、\n'
        '`python auto_grade_loop.py extract <採点結果.md> --theme "<テーマ名・版>" --save` を実行して\n'
        '減点パターン集に自動追記してください。\n'
        '\n'
        '90点未満なら本文を修正し、再度 STEP 4b → STEP 4c を回します（最大3回）。\n'
        '\n'
        '---\n'
        '# subagentに渡すプロンプト本体\n'
        '\n'
        + prompt_body
    )

    if args.save_as:
        with open(args.save_as, 'w', encoding='utf-8') as f:
            f.write(instruction)
        print(f'[OK] 起動指示を {args.save_as} に保存しました。')
    else:
        print(instruction)


# ============================================================
# next-id コマンド
# ============================================================

def cmd_next_id(args):
    patterns_path = args.patterns or DEFAULT_PATTERNS_PATH
    max_id, _existing, _full = read_existing_patterns(patterns_path)
    print(f'最大ID: P-{max_id:03d}')
    print(f'次回ID: P-{max_id + 1:03d}')


# ============================================================
# main
# ============================================================

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)

    p_ex = sub.add_parser('extract', help='採点結果MDから減点パターンを抽出・追記')
    p_ex.add_argument('grading_md', help='subagent採点結果MDのパス')
    p_ex.add_argument('--theme', required=True, help='テーマ名・版（例: テーマ4 v3）')
    p_ex.add_argument('--patterns', help='パターン集MDのパス（既定: ~/.claude/skill-memory/レポート減点パターン.md）', default=None)
    p_ex.add_argument('--save', action='store_true', help='実際に追記する（既定はdry-run）')

    p_in = sub.add_parser('instruct', help='採点プロンプトtxtを subagent 起動指示として整形')
    p_in.add_argument('grading_prompt', help='grade.py が生成した採点プロンプトtxt')
    p_in.add_argument('--save-as', help='出力先mdパス（省略時は標準出力）', default=None)

    p_id = sub.add_parser('next-id', help='次に振るべき P-NNN を表示')
    p_id.add_argument('--patterns', default=None)

    args = ap.parse_args()

    if args.cmd == 'extract':
        # 90点未満は exit 3（再生成が要る）。減点パターンの追記（--save）は点数に関係なく先に済ませてある
        sys.exit(cmd_extract(args))
    elif args.cmd == 'instruct':
        cmd_instruct(args)
    elif args.cmd == 'next-id':
        cmd_next_id(args)


if __name__ == '__main__':
    main()
