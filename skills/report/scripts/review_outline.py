"""report/review_outline.py - STEP 0.6 構成案レビュー用プロンプト生成

usage:
    python review_outline.py <要件抽出_*.md> <章立て案.md or .txt> [--textbook <教科書PDF>] [--out <out.txt>]

要件抽出MDと章立て案を結合し、subagent（general-purpose）に渡すレビュー用プロンプトを生成する。
作成前ゲートとして要件レイヤーの欠落を検出する。

出力:
  デフォルトで章立て案と同じフォルダに `<章立て案ベース名>_構成レビュープロンプト.txt` を生成。
  Claude は Agent ツールで subagent_type=general-purpose を起動し、このプロンプトを渡す。
"""
import sys
import io
import os
import argparse

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


REVIEW_PROMPT_TEMPLATE = """あなたは大学レポート構成案のレビュアーです。
要件抽出MD・教科書PDF（あれば）と章立て案を突き合わせ、要件抽出の各項目
（するな／しろ／どうしろ）が章立て案でカバーされているかを判定してください。

# 判定基準
- ◎ 明確にカバー（章立て案に具体的記述あり）
- ○ 暗黙的にカバー（章立てから自然に出てくる）
- × 章立て案に記述なし（欠落）

# 出力フォーマット

```
# 構成案レビュー結果

## サマリー
- するな違反リスク: N件
- しろ欠落: N件
- どうしろ欠落: N件
- **作成前ゲート判定: PASS / FAIL**

## するな（禁止事項）
| 要件 | 章立てでの扱い | 判定 | 補足 |
|---|---|---|---|

## しろ（必須事項）
| 要件 | 章立てでの扱い | 判定 | 補足 |
|---|---|---|---|

## どうしろ（様式指定）
| 要件 | 章立てでの扱い | 判定 | 補足 |
|---|---|---|---|

## 修正提案（× が出た項目に対し具体的に）
1. ...
2. ...
```

# 重要ルール
- 「しろ」項目で × が1つでもあれば作成前ゲート FAIL とする
- 「するな」項目への違反リスクが章立てから推測できれば指摘する
- 教科書PDFがある場合、章立てが教科書範囲を逸脱していないかも見る
- 推測ではなく、章立て案に明示されているかを基準に判定する

---

# 要件抽出MD

{requirements_md}

---

# 章立て案

{outline}

{textbook_section}---

レビューを開始してください。
"""


def read_text(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def extract_pdf_text(pdf_path):
    import fitz
    doc = fitz.open(pdf_path)
    return '\n'.join(p.get_text() for p in doc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('requirements_md', help='要件抽出_*.md のパス')
    ap.add_argument('outline', help='章立て案ファイル（.md または .txt）')
    ap.add_argument('--textbook', help='教科書PDF（任意）', default=None)
    ap.add_argument('--out', help='出力先（任意）', default=None)
    args = ap.parse_args()

    if not os.path.exists(args.requirements_md):
        print(f'[NG] 要件抽出MDが見つかりません: {args.requirements_md}')
        sys.exit(2)
    if not os.path.exists(args.outline):
        print(f'[NG] 章立て案ファイルが見つかりません: {args.outline}')
        sys.exit(2)

    requirements_md = read_text(args.requirements_md)
    outline = read_text(args.outline)

    textbook_section = ''
    if args.textbook:
        if not os.path.exists(args.textbook):
            print(f'[WARN] 教科書PDFが見つかりません（スキップ）: {args.textbook}')
        else:
            tb = extract_pdf_text(args.textbook)
            textbook_section = '---\n\n# 教科書PDFの内容（参考）\n\n' + tb + '\n\n'

    prompt = REVIEW_PROMPT_TEMPLATE.format(
        requirements_md=requirements_md,
        outline=outline,
        textbook_section=textbook_section,
    )

    if args.out:
        out_path = args.out
    else:
        base = os.path.splitext(args.outline)[0]
        out_path = base + '_構成レビュープロンプト.txt'

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(prompt)

    print(f'構成レビュープロンプト生成: {out_path}')
    print(f'  要件抽出MD: {os.path.basename(args.requirements_md)} ({len(requirements_md)} chars)')
    print(f'  章立て案: {os.path.basename(args.outline)} ({len(outline)} chars)')
    if textbook_section:
        print(f'  教科書PDF: {os.path.basename(args.textbook)} 含む')
    print()
    print('次のステップ: Claudeが Agent ツールで subagent_type=general-purpose を起動し、')
    print('              このプロンプトを渡してレビュー実施。FAIL なら章立てを修正してSTEP 2へ。')


if __name__ == '__main__':
    main()
