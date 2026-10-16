"""report/extract_requirements.py - 要領PDFから要件を抽出する

usage:
    python extract_requirements.py <yourkou_pdf> [--output <out.md>]

PDFのテキストを抽出し、文単位で「するな（禁止）/しろ（必須）/どうしろ（様式）」に分類する。
分類は完璧ではなく、人間（Claude）の最終判断の足場として使う。
"""
import sys
import io
import re
import os

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import fitz  # PyMuPDF


# 分類ルール
NEGATIVE_KEYWORDS = [
    '不適当', '不適切', 'してはいけない', '避けて', '禁止',
    '書かない', '記述することは', '入れない', '使わない', '必要はありません',
    '不要', '禁ずる', '避ける',
]

STYLE_KEYWORDS = [
    '番号をふり', '番号を振って', '番号を割り振って', '番号を振る',
    '出てくる順番', 'タイトルを', '右に記入', 'その右に',
    '見出し', '配置', '位置', 'スタイル', '書式',
    '上に置く', '下に置く', 'キャプション',
]

POSITIVE_KEYWORDS = [
    '下さい', 'ください', 'します', 'する必要',
    '記入', '記述して', '書いて', '挿入', '含めて',
    '表すこと', 'まとめて', '確認', '導出',
]


def extract_pdf_text(pdf_path):
    """PDFから全テキストを取得"""
    doc = fitz.open(pdf_path)
    text = ''
    for page in doc:
        text += page.get_text() + '\n'
    return text


def split_sentences(text):
    """日本語文を句点で分割"""
    # 改行を句点扱いしない（要領PDFは1文が複数行に渡ることが多い）
    text = re.sub(r'\s+', ' ', text)
    # 句点で分割
    sents = re.split(r'(?<=[。．])', text)
    return [s.strip() for s in sents if s.strip()]


def classify_sentence(sent):
    """文を「するな/しろ/どうしろ/その他」に分類"""
    if any(kw in sent for kw in NEGATIVE_KEYWORDS):
        return 'するな'
    if any(kw in sent for kw in STYLE_KEYWORDS):
        return 'どうしろ'
    if any(kw in sent for kw in POSITIVE_KEYWORDS):
        return 'しろ'
    return None


def extract_requirements(text):
    """要件を分類して返す"""
    sentences = split_sentences(text)
    out = {
        'するな（禁止事項）': [],
        'しろ（必須事項）': [],
        'どうしろ（様式指定）': [],
    }
    for sent in sentences:
        if len(sent) < 10 or len(sent) > 250:
            continue
        cls = classify_sentence(sent)
        if cls == 'するな':
            out['するな（禁止事項）'].append(sent)
        elif cls == 'どうしろ':
            out['どうしろ（様式指定）'].append(sent)
        elif cls == 'しろ':
            out['しろ（必須事項）'].append(sent)
    return out


def to_markdown(reqs, pdf_path):
    """Markdown形式で出力"""
    lines = [
        f'# 要領PDFから抽出した要件',
        f'',
        f'**ソース**: `{os.path.basename(pdf_path)}`',
        f'',
        f'_自動抽出のため、最終判断はClaudeが要領PDFを通読して行うこと。_',
        f'',
    ]
    for category, items in reqs.items():
        lines.append(f'## {category} ({len(items)}件)')
        lines.append('')
        if not items:
            lines.append('- （該当なし）')
        else:
            for i, item in enumerate(items, 1):
                # 重複に近いものを軽く除外
                lines.append(f'{i}. {item}')
        lines.append('')
    return '\n'.join(lines)


def main():
    if len(sys.argv) < 2:
        print('usage: python extract_requirements.py <yourkou_pdf> [--output <out.md>]')
        sys.exit(2)
    pdf_path = sys.argv[1]
    output_path = None
    if '--output' in sys.argv:
        idx = sys.argv.index('--output')
        if idx + 1 < len(sys.argv):
            output_path = sys.argv[idx + 1]
    if output_path is None:
        # デフォルトはPDFと同じフォルダに「要件抽出_<basename>.md」
        base = os.path.splitext(os.path.basename(pdf_path))[0]
        output_path = os.path.join(os.path.dirname(pdf_path), f'要件抽出_{base}.md')

    text = extract_pdf_text(pdf_path)
    reqs = extract_requirements(text)
    md = to_markdown(reqs, pdf_path)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md)
    print(f'Saved: {output_path}')
    print(f'  するな: {len(reqs["するな（禁止事項）"])}件')
    print(f'  しろ:   {len(reqs["しろ（必須事項）"])}件')
    print(f'  どうしろ: {len(reqs["どうしろ（様式指定）"])}件')


if __name__ == '__main__':
    main()
