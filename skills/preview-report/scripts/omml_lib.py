"""
OMML (Office Math Markup Language) ヘルパーライブラリ
Word の数式機能で行列・分数・下付き上付き等を描画する。

使い方:
    from omml_lib import add_math, m_det, m_r, m_ri, m_sub, m_sup, m_frac, m_sum, m_int
    add_math(doc, m_det([[m_r('1'), m_r('2')], [m_r('3'), m_r('4')]]))

原則:
    - 変数（a, x, A 等）は m_ri (italic)
    - 定数（1, 2, ...）・演算子・記号は m_r (plain)
    - 負号は U+2212 (−) を使う（ASCII ハイフンは数式に見えない）
"""
from docx.shared import Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn
from docx.shared import Pt

MATH_NS = 'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"'

def _esc(s: str) -> str:
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


# === 基本要素 ===

def m_r(text: str) -> str:
    """プレーンな文字列（定数・演算子・記号）"""
    return f'<m:r><m:t xml:space="preserve">{_esc(text)}</m:t></m:r>'

def m_ri(text: str) -> str:
    """イタリック（変数名用）"""
    return (f'<m:r><m:rPr><m:sty m:val="i"/></m:rPr>'
            f'<m:t xml:space="preserve">{_esc(text)}</m:t></m:r>')

def m_b(text: str) -> str:
    """ボールド（ベクトル・行列名など）"""
    return (f'<m:r><m:rPr><m:sty m:val="b"/></m:rPr>'
            f'<m:t xml:space="preserve">{_esc(text)}</m:t></m:r>')


# === 添字 ===

def m_sub(base: str, sub: str) -> str:
    """下付き: base_sub"""
    return f'<m:sSub><m:e>{base}</m:e><m:sub>{sub}</m:sub></m:sSub>'

def m_sup(base: str, sup: str) -> str:
    """上付き: base^sup"""
    return f'<m:sSup><m:e>{base}</m:e><m:sup>{sup}</m:sup></m:sSup>'

def m_subsup(base: str, sub: str, sup: str) -> str:
    """上下付き同時"""
    return (f'<m:sSubSup><m:e>{base}</m:e>'
            f'<m:sub>{sub}</m:sub><m:sup>{sup}</m:sup></m:sSubSup>')


# === 分数・根号 ===

def m_frac(num: str, den: str) -> str:
    """分数 num/den（上下 2 段）"""
    return f'<m:f><m:num>{num}</m:num><m:den>{den}</m:den></m:f>'

def m_sqrt(inner: str) -> str:
    """平方根"""
    return f'<m:rad><m:deg/><m:e>{inner}</m:e></m:rad>'

def m_root(inner: str, degree: str) -> str:
    """n 乗根"""
    return f'<m:rad><m:deg>{degree}</m:deg><m:e>{inner}</m:e></m:rad>'


# === 行列 ===

def m_matrix(rows, open_b: str = '[', close_b: str = ']') -> str:
    """括弧付き行列 [...] / (...) / |...| など

    rows: 2次元リスト、各要素は内部 XML 文字列
          例: [[m_r('1'), m_r('2')], [m_r('3'), m_r('4')]]
    """
    rows_xml = ''
    for row in rows:
        cells = ''.join(f'<m:e>{c}</m:e>' for c in row)
        rows_xml += f'<m:mr>{cells}</m:mr>'
    return (f'<m:d><m:dPr><m:begChr m:val="{open_b}"/>'
            f'<m:endChr m:val="{close_b}"/></m:dPr>'
            f'<m:e><m:m>{rows_xml}</m:m></m:e></m:d>')

def m_det(rows) -> str:
    """行列式 |...|"""
    return m_matrix(rows, '|', '|')

def m_mat_paren(rows) -> str:
    """丸括弧行列 (...)"""
    return m_matrix(rows, '(', ')')


# === 大演算子（総和・積分等） ===

def m_nary(chr_: str, lower: str, upper: str, body: str) -> str:
    """n 項演算子の汎用。chr_ に演算子記号 (∑ ∫ ∏ 等)"""
    return (f'<m:nary><m:naryPr><m:chr m:val="{chr_}"/></m:naryPr>'
            f'<m:sub>{lower}</m:sub><m:sup>{upper}</m:sup>'
            f'<m:e>{body}</m:e></m:nary>')

def m_sum(lower: str, upper: str, body: str) -> str:
    """総和 Σ"""
    return m_nary('∑', lower, upper, body)

def m_prod(lower: str, upper: str, body: str) -> str:
    """総積 Π"""
    return m_nary('∏', lower, upper, body)

def m_int(lower: str, upper: str, body: str) -> str:
    """積分 ∫"""
    return m_nary('∫', lower, upper, body)

def m_lim(base: str, target: str) -> str:
    """極限 lim_{x→a}"""
    return (f'<m:func><m:fName>{m_ri("lim")}'
            f'<m:sSub><m:e></m:e><m:sub>{target}</m:sub></m:sSub></m:fName>'
            f'<m:e>{base}</m:e></m:func>')


# === 線形代数で頻出のパターン ===

def m_transpose(var: str) -> str:
    """転置 A^T（右上に t/T を立てる、日本の教科書では左上 ᵗA の流儀もある）"""
    return m_sup(var, m_ri('T'))

def m_inverse(var: str) -> str:
    """逆行列 A^{-1}"""
    return m_sup(var, m_r('−1'))

def m_norm(inner: str) -> str:
    """ノルム ‖...‖"""
    return (f'<m:d><m:dPr><m:begChr m:val="‖"/>'
            f'<m:endChr m:val="‖"/></m:dPr><m:e>{inner}</m:e></m:d>')

def m_abs(inner: str) -> str:
    """絶対値 |...|"""
    return (f'<m:d><m:dPr><m:begChr m:val="|"/>'
            f'<m:endChr m:val="|"/></m:dPr><m:e>{inner}</m:e></m:d>')

def m_generic_matrix(n_rows: int = 3, n_cols: int = 3, letter: str = 'a') -> list:
    """
    一般的な n×m 行列 [[a_11, ..., a_1n], [...], [a_n1, ..., a_nn]] を生成。
    省略記号 (…, ⋮, ⋱) を入れた省略形ではなく、明示的な添字を返す。
    """
    rows = []
    for i in range(1, n_rows + 1):
        row = []
        for j in range(1, n_cols + 1):
            row.append(m_sub(m_ri(letter), m_r(f'{i}{j}')))
        rows.append(row)
    return rows


# === Word 側の段落挿入 ===

def add_math(doc, inner_xml: str, center: bool = True, indent_cm: float = 0.5):
    """
    段落に数式を挿入する。中央揃え or 左インデント。
    inner_xml: m_* で構築した OMML 文字列
    """
    p = doc.add_paragraph()
    if center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    else:
        p.paragraph_format.left_indent = Cm(indent_cm)
    wrapper = f'<m:oMathPara {MATH_NS}><m:oMath>{inner_xml}</m:oMath></m:oMathPara>'
    p._p.append(parse_xml(wrapper))
    return p

def add_inline_math(paragraph, inner_xml: str):
    """
    既存の段落の中にインライン数式を挿入する（文中に式を混ぜる用）。
    """
    wrapper = f'<m:oMath {MATH_NS}>{inner_xml}</m:oMath>'
    paragraph._p.append(parse_xml(wrapper))


# === 日本語フォント設定 ===

def setup_japanese(doc, mincho: str = 'Yu Mincho', gothic: str = 'Yu Gothic',
                   size: float = 10.5, margin_cm: float = 2.0):
    """日本語文書の標準セットアップ。Normal スタイルと余白を設定"""
    style = doc.styles['Normal']
    style.font.name = mincho
    style.font.size = Pt(size)
    rpr = style.element.get_or_add_rPr()
    rF = OxmlElement('w:rFonts')
    rF.set(qn('w:eastAsia'), mincho)
    rpr.append(rF)
    for s in doc.sections:
        s.top_margin = s.bottom_margin = Cm(margin_cm)
        s.left_margin = s.right_margin = Cm(margin_cm + 0.2)

def heading(doc, text: str, size: float = 12, gothic: str = 'Yu Gothic'):
    """太字の見出し"""
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(size)
    r.font.name = gothic
    rpr = r._element.get_or_add_rPr()
    rF = OxmlElement('w:rFonts')
    rF.set(qn('w:eastAsia'), gothic)
    rpr.append(rF)
    return p


# === ファイルパスのロック対策保存 ===

def safe_save_path(base_path: str) -> str:
    """OneDrive ロック時にバージョン番号を +1 して別名保存。

    本体は shared-doc-rules/scripts/safe_save_path.py（2026-09-28 から、以前の写しをやめてそちらを呼ぶ）。
    「最終版」「完成版」「final」入りや _v{N} の無いファイル名は、そこで ValueError になる。
    """
    import os, sys
    shared = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                           '..', '..', 'shared-doc-rules', 'scripts'))
    if shared not in sys.path:
        sys.path.insert(0, shared)
    import safe_save_path as _shared
    return _shared.safe_save_path(base_path)
