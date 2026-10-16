"""report/pdf_vocab_check.py - 教科書PDF外の情報が混入していないかチェック

usage:
    python pdf_vocab_check.py <docx> <textbook_pdf>

教科書PDFから型番・数値・固有名詞を抽出し、本文と差集合をとって
「教科書PDFに無い情報」をリストアップする。

運用で起きた事故の例: テーマ4で「直流安定化電源 0–30 V 可変」など教科書PDFに記載のない
情報を勝手に書き、教授から指摘された。これを構造的に防ぐ。
"""
import sys
import io
import re
import os
from docx import Document
from docx.oxml.ns import qn

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import fitz


# 検出パターン
MODEL_NUMBER_PAT = re.compile(r'\b[A-Z][A-Z0-9]{1,}[-]?[0-9]+[A-Z0-9]*\b')

# 単位付き数値（電気系を中心に）
NUMERIC_VALUE_PAT = re.compile(
    r'(\d+(?:\.\d+)?)[\s ]*'
    r'(V|kV|mV|[μµ]V|A|mA|[μµ]A|nA|Ω|kΩ|MΩ|F|[μµ]F|nF|pF|H|mH|[μµ]H|'
    r'Hz|kHz|MHz|GHz|W|kW|mW|s|ms|μs|ns|°C|K)\b'
)


def extract_pdf_text(path):
    doc = fitz.open(path)
    return '\n'.join(p.get_text() for p in doc)


def extract_docx_text(path):
    doc = Document(path)
    parts = []
    for el in doc.element.body.iter():
        if el.tag == qn('w:p'):
            text = ''.join(t.text or '' for t in el.iter(qn('w:t')))
            if text.strip():
                parts.append(text)
    return '\n'.join(parts)


def normalize_value(num, unit):
    """同じ値の表記揺れを揃える: '10 V' と '10V' を同一視"""
    return f'{num}{unit}'


def check(docx_path, pdf_path):
    pdf_text = extract_pdf_text(pdf_path)
    doc_text = extract_docx_text(docx_path)

    # 型番
    pdf_models = set(MODEL_NUMBER_PAT.findall(pdf_text))
    doc_models = set(MODEL_NUMBER_PAT.findall(doc_text))
    extra_models = doc_models - pdf_models

    # 数値
    pdf_values = set(normalize_value(n, u) for n, u in NUMERIC_VALUE_PAT.findall(pdf_text))
    doc_values = set(normalize_value(n, u) for n, u in NUMERIC_VALUE_PAT.findall(doc_text))
    extra_values = doc_values - pdf_values

    issues = []
    if extra_models:
        issues.append({
            'category': '教科書PDFに無い型番',
            'items': sorted(extra_models),
        })
    if extra_values:
        # 単位だけは除外（誤検出が多い）
        filtered = sorted(v for v in extra_values if not v.endswith('s'))
        if filtered:
            issues.append({
                'category': '教科書PDFに無い数値',
                'items': filtered,
            })

    return issues


def main():
    if len(sys.argv) < 3:
        print('usage: python pdf_vocab_check.py <docx> <textbook_pdf>')
        sys.exit(2)
    docx_path = sys.argv[1]
    pdf_path = sys.argv[2]
    print(f'Checking: {os.path.basename(docx_path)} vs {os.path.basename(pdf_path)}\n')
    issues = check(docx_path, pdf_path)
    if not issues:
        print('[OK] 教科書PDFと整合 - 不審な型番・数値の混入なし')
        return 0
    for issue in issues:
        print(f'[警告] {issue["category"]}:')
        for item in issue['items']:
            print(f'   - {item}')
        print()
    print('※ 一部は誤検出の可能性あり。本文中で実際に教科書外の情報か確認すること。')
    return 1


if __name__ == '__main__':
    sys.exit(main())
