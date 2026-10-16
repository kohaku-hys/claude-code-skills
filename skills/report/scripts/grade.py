"""report/grade.py - 別エージェントで採点するためのプロンプト準備

usage:
    python grade.py <docx> <yourkou_pdf> [--save-result]

レポート本文 + 要領PDF を抽出し、採点用プロンプトを構築する。
このプロンプトを別の Claude エージェント（subagent）に渡すことで、
生成過程を知らない第三者として採点する（自己採点バイアスを排除）。

出力:
  <docx>と同じフォルダに `<docx名>_採点プロンプト.txt` を生成。
  Claudeはこれを Agent ツールで subagent に渡し、採点結果を受け取る。
"""
import sys
import io
import os
from docx import Document
from docx.oxml.ns import qn

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import fitz


GRADING_PROMPT_TEMPLATE = """あなたは大学の実験レポート採点者です。生成プロセスを知らない第三者として、要領PDFと本文のみから100点満点で**厳しめに**採点してください。

# 採点ルール（厳守）

1. 要領PDFに「するな（不適当・禁止・してはいけない）」と書かれた項目に違反していたらゼロ寛容で大きく減点（−5点以上）
2. 要領PDFに「しろ（必須・記入・記述）」「どうしろ（番号・タイトル・配置）」の指示を欠けば減点（−2〜5点）
3. 学術慣習も採点対象：
   - 表番号・図番号の連番性（飛び番禁止）→ −3点
   - 表キャプションは表の上、図キャプションは図の下 → 違反−2点
   - 文体は「である」調統一 → 「です/ます」混入で −5点以上
   - 履修範囲外の数学記号（Σ等）の混入 → −2点
   - 図表が本文中で参照されているか → 違反−1点ずつ
4. 各章の小計と減点理由を必ず明記する
5. 出力は以下のフォーマット：

```
# 採点結果

## 総合評価：**XX/100点**

---

## 章別採点

### 1章 目的（YY点満点）→ ZZ/YY
| 要件 | 判定 |
|---|---|
| ... | ◎/○/△/× |

**減点理由（−N点）**：（具体的に）

### 2章 ...（同様）

---

## 改善提案
1. （優先度高）...
2. ...

```

---

# 要領PDFの内容

{requirements}

---

# 採点対象レポート本文

{report_body}

---

採点を開始してください。
"""


def extract_pdf_text(pdf_path):
    doc = fitz.open(pdf_path)
    return '\n'.join(p.get_text() for p in doc)


def extract_docx_text(docx_path):
    doc = Document(docx_path)
    parts = []
    for el in list(doc.element.body):
        if el.tag == qn('w:p'):
            text = ''.join(t.text or '' for t in el.iter(qn('w:t')))
            if text.strip():
                parts.append(text)
        elif el.tag == qn('w:tbl'):
            # テーブルは「[表: row1 | row2 | ...]」形式で要約
            rows = []
            for tr in el.findall(qn('w:tr')):
                cells = []
                for tc in tr.findall(qn('w:tc')):
                    cell_text = ''.join(t.text or '' for t in tc.iter(qn('w:t')))
                    cells.append(cell_text.strip())
                rows.append(' | '.join(cells))
            parts.append('[表]\n  ' + '\n  '.join(rows))
    return '\n'.join(parts)


def main():
    if len(sys.argv) < 3:
        print('usage: python grade.py <docx> <yourkou_pdf>')
        sys.exit(2)
    docx_path = sys.argv[1]
    pdf_path = sys.argv[2]

    requirements = extract_pdf_text(pdf_path)
    report_body = extract_docx_text(docx_path)

    prompt = GRADING_PROMPT_TEMPLATE.format(
        requirements=requirements,
        report_body=report_body,
    )

    out_path = docx_path.rsplit('.', 1)[0] + '_採点プロンプト.txt'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(prompt)
    print(f'採点プロンプト生成: {out_path}')
    print(f'  要領PDF: {os.path.basename(pdf_path)} ({len(requirements)} chars)')
    print(f'  本文: {os.path.basename(docx_path)} ({len(report_body)} chars)')
    print()
    print('次のステップ: Claudeが Agent ツールで subagent_type=general-purpose を起動し、')
    print('              このプロンプトを渡して採点を実施する。')


if __name__ == '__main__':
    main()
