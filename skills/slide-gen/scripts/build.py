#!/usr/bin/env python3
"""
PPT Master - Build（パイプライン一発実行）

quality_checker → deck_doctor → total_md_split → finalize_svg → svg_to_pptx
を1コマンドで直列実行する。ゲート（checker error / doctor error）で即停止し、
どのステップで何が起きたか・次の一手を表示する。

（slide-gen 同梱版。作者が ppt-master のローカルのブランチに足した build.py を slide-gen の scripts に置いた物。
 deck_doctor はこのファイルの隣の同梱版を呼び、ほかの4つ（svg_quality_checker・total_md_split・finalize_svg・
 svg_to_pptx）は上流の ppt-master の scripts を呼ぶ。ppt-master の scripts の場所は環境変数 PPT_MASTER_SCRIPTS
 （既定は作者の置き場の例 C:/dev/ppt-master/skills/ppt-master/scripts）。ppt-master と同じ Python 3.10+ で動かす）

Usage:
    python3 build.py <project_dir>                         # フルビルド
    python3 build.py <project_dir> --rebuild               # 軽微修正後の再ビルド
                                                           #   (finalize をスキップ = svg_to_pptx が
                                                           #    変換時にアイコン/画像を展開するので十分)
    python3 build.py <project_dir> --strict                # doctor の WARNING でも停止
    python3 build.py <project_dir> -- -t push --auto-advance 6
                                                           # "--" 以降は svg_to_pptx へパススルー

Exit code: 全ステップ成功 → 0 ／ いずれか失敗 → そのステップの exit code
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# 同梱の deck_doctor.py はこのファイルの隣。ほかのステップは上流の ppt-master の scripts を呼ぶ
HERE = Path(__file__).resolve().parent
SCRIPTS = Path(os.environ.get('PPT_MASTER_SCRIPTS', r'C:\dev\ppt-master\skills\ppt-master\scripts'))

# 端末の文字コードを UTF-8 にする（cp932 の端末で日本語の出力が落ちないように）。作者の版の ppt-master の
# console_encoding.configure_utf8_stdio と同じ処理を、ppt-master を import せずに標準ライブラリでやる
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


def checker_args(proj):
    """svg_quality_checker に渡す引数。2026-10 時点の上流の ppt-master は、svg_to_pptx が「最終の品質レポート」
    （validation/svg_quality_report.json）を求め、checker はそれを --canonical-authoring --stage final --json の時だけ書く。
    作者の版の checker にはこのオプションが無いので、checker の CLI にオプションがある時だけ付ける。"""
    try:
        cli = (SCRIPTS / 'svg_quality' / 'cli.py').read_text(encoding='utf-8', errors='replace')
    except OSError:
        cli = ''
    if '--canonical-authoring' in cli and '--stage' in cli:
        return [str(proj), '--canonical-authoring', '--stage', 'final', '--json']
    return [str(proj)]


def run_step(name, script, args, hint):
    """1ステップ実行（script はスクリプトの絶対パス）。失敗したら (False, code)。"""
    print()
    print('== %s ==' % name)
    t0 = time.time()
    sys.stdout.flush()  # 子プロセス出力より先に見出しを出す
    cmd = [sys.executable, str(script)] + args
    proc = subprocess.run(cmd)
    dt = time.time() - t0
    if proc.returncode != 0:
        print()
        print('✗ %s が失敗 (exit %d, %.1fs)' % (name, proc.returncode, dt))
        print('  → %s' % hint)
        return False, proc.returncode
    print('✓ %s OK (%.1fs)' % (name, dt))
    return True, 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    passthrough = []
    if '--' in argv:
        idx = argv.index('--')
        passthrough = argv[idx + 1:]
        argv = argv[:idx]

    ap = argparse.ArgumentParser(description='PPT Master build（パイプライン一発実行）')
    ap.add_argument('project', help='プロジェクトディレクトリ')
    ap.add_argument('--rebuild', action='store_true',
                    help='finalize をスキップ（SVG/ノート軽微修正後の再ビルド）')
    ap.add_argument('--strict', action='store_true', help='deck_doctor の WARNING でも停止')
    ap.add_argument('--skip-doctor', action='store_true', help='deck_doctor を省略（非推奨）')
    ap.add_argument('--draft', action='store_true',
                    help='途中の確認用。deck_doctor の R0（照合の記録）を WARNING に下げる。本人に見せる版には付けない')
    ap.add_argument('--legacy', action='store_true',
                    help='2026-09-28 以前の旧書式 brief のデッキを作り直す時だけ。C1〜C6・R0 を WARNING に下げる')
    args = ap.parse_args(argv)

    proj = Path(args.project)
    if not proj.is_dir():
        print('プロジェクトが見つかりません: %s' % proj)
        return 2
    if not (SCRIPTS / 'svg_to_pptx.py').is_file():
        print('ppt-master の scripts が見つかりません: %s' % SCRIPTS)
        print('  → 環境変数 PPT_MASTER_SCRIPTS に、clone した ppt-master の skills/ppt-master/scripts を指定する')
        return 2

    total0 = time.time()

    # 1. SVG 単体品質（error 0 必須）
    ok, code = run_step(
        'svg_quality_checker', SCRIPTS / 'svg_quality_checker.py', checker_args(proj),
        'error を修正してから再実行（spec_lock drift は lock 値に合わせるか lock へ追記）')
    if not ok:
        return code

    # 2. デッキ整合診断（注釈残留・フッター・notes整合・禁則・はみ出し・重なり）
    if not args.skip_doctor:
        doctor_args = [str(proj)]
        if args.strict:
            doctor_args.append('--strict')
        if args.draft:
            doctor_args.append('--draft')
        if args.legacy:
            doctor_args.append('--legacy')
        ok, code = run_step(
            'deck_doctor', HERE / 'deck_doctor.py', doctor_args,
            '各指摘の「→」の直し方に従って修正（WARNING だけなら --strict なしで先へ進める判断も可）')
        if not ok:
            return code

    # 3. ノート分割（total.md があるときだけ）
    if (proj / 'notes' / 'total.md').is_file() or (proj / 'total.md').is_file():
        ok, code = run_step(
            'total_md_split', SCRIPTS / 'total_md_split.py', [str(proj)],
            'notes/total.md の「## Slide N:」見出しと SVG の対応を確認')
        if not ok:
            return code
    else:
        print()
        print('== total_md_split == スキップ（notes/total.md なし）')

    # 4. 後処理（アイコン/画像埋込・tspan平坦化 → svg_final/）
    if args.rebuild:
        print()
        print('== finalize_svg == スキップ（--rebuild: svg_to_pptx が変換時に展開する）')
    else:
        ok, code = run_step(
            'finalize_svg', SCRIPTS / 'finalize_svg.py', [str(proj)],
            'アイコン名が tabler-outline に実在するか・画像パスが images/ にあるか確認')
        if not ok:
            return code

    # 5. PPTX 変換
    ok, code = run_step(
        'svg_to_pptx', SCRIPTS / 'svg_to_pptx.py', [str(proj)] + passthrough,
        '変換ログの直近エラーを確認（フォント・画像・アニメ設定）')
    if not ok:
        return code

    # 成果物の案内
    exports = sorted((proj / 'exports').glob('*.pptx'),
                     key=lambda p: p.stat().st_mtime, reverse=True)
    print()
    print('=== build 完了 (%.1fs) ===' % (time.time() - total0))
    if exports:
        print('成果物: %s' % exports[0])
        print('次: render_deck.py（か preview.ps1）でコンタクトシート → 目視セルフレビュー（写真妥当性・誤読・掴み）')
    else:
        print('⚠ exports/*.pptx が見つかりません（svg_to_pptx の出力先を確認）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
