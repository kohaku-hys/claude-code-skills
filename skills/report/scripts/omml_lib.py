"""report/omml_lib.py - Word 数式（OMML）の部品と、数式だけの行（独立行）を作る関数。

2026-10-07 新設（テーマ5 本レポート v12。本人「計算式などはきちんと改行して見やすく」）。

代入計算（計算例）は本文の文の中に「27.901 ÷ (1 − 27.901 ÷ 3000) ≒ 28.163 Ω」と埋め込まない。
行の途中で式が折れて読めなくなる。文は「〜を式(2)に代入して求めた。」で閉じ、次の行に
番号なしの Word 数式（分数・√ を使う）で出す。lint の Check 18 が文中の代入計算を NG で止める。

部品（どれも OMML の文字列を返す。引数に「<」で始まらない文字列を渡すと r() で包む）:
    r('R')                斜体の文字（変数）。数字・演算子は Word が立体で組む
    up('Ω')               立体の文字（単位・%・「100」など）
    unit('Ω')             数値と単位の間に細い空白を入れた立体の単位
    sub('R', 't')         R_t        sup('10', '−3')   10^−3      subsup('R', 't', '2')  R_t²
    frac(a, b)            分数       rad(e)            √（次数なし）
    paren(e)              ( … )      text('①')        数式の中の普通の文字（日本語・丸数字。ＭＳ 明朝）
    cat(a, b, …)          つなぐ

行:
    equation_paragraph(omml, number=None, center=4819, right=9638)   w:p 要素を返す
    add_equation(doc, omml, number=None)              文書の末尾に足す（中央・右端に (N)）
    insert_equation_after(paragraph, omml, number=None)  既存の段落の直後に差し込む（docx の手直し用）
    number=None なら番号なし＝計算例の行。独立行の数式（m:oMathPara）にするので分数が本文と同じ大きさになる。
    番号を付けた式は本文で「式(N)」と参照する（lint Check 6b）

例（テーマ5 表2①の計算例）:
    Rt = sub('R', 't')
    omml = cat(Rt, r('='), frac('27.901', cat(r('1−'), frac('27.901', '3000'))),
               r('≒'), r('28.163'), unit('Ω'))
    insert_equation_after(p, omml)
"""
from xml.sax.saxutils import escape

from docx.oxml import parse_xml
from docx.text.paragraph import Paragraph

M_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
_DECL = f'xmlns:m="{M_NS}" xmlns:w="{W_NS}"'

THIN = ' '   # 数値と単位の間の細い空白


def _x(s):
    return s if s.lstrip().startswith('<') else r(s)


def r(s):
    return f'<m:r><m:t xml:space="preserve">{escape(s)}</m:t></m:r>'


def up(s):
    return f'<m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t xml:space="preserve">{escape(s)}</m:t></m:r>'


def unit(u):
    return up(THIN + u)


def text(s, font='ＭＳ 明朝'):
    return ('<m:r><m:rPr><m:nor/></m:rPr>'
            f'<w:rPr><w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:eastAsia="{font}"/></w:rPr>'
            f'<m:t xml:space="preserve">{escape(s)}</m:t></m:r>')


def cat(*parts):
    return ''.join(_x(p) for p in parts)


def sub(base, s):
    return f'<m:sSub><m:e>{_x(base)}</m:e><m:sub>{_x(s)}</m:sub></m:sSub>'


def sup(base, s):
    return f'<m:sSup><m:e>{_x(base)}</m:e><m:sup>{_x(s)}</m:sup></m:sSup>'


def subsup(base, s, p):
    """R_t² のように添字と指数を両方付ける（sSub を sSup の底に入れるより字の並びがきれい）"""
    return f'<m:sSubSup><m:e>{_x(base)}</m:e><m:sub>{_x(s)}</m:sub><m:sup>{_x(p)}</m:sup></m:sSubSup>'


def frac(num, den):
    return f'<m:f><m:num>{_x(num)}</m:num><m:den>{_x(den)}</m:den></m:f>'


def rad(e):
    return f'<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/><m:e>{_x(e)}</m:e></m:rad>'


def paren(e):
    return (f'<m:d><m:dPr><m:begChr m:val="("/><m:endChr m:val=")"/></m:dPr>'
            f'<m:e>{_x(e)}</m:e></m:d>')


def _center_right(doc):
    """本文の幅から中央と右端のタブ位置（twip）を出す。1 twip = 635 EMU"""
    s = doc.sections[-1]
    width = int((s.page_width - s.left_margin - s.right_margin) / 635)
    return width // 2, width


def equation_paragraph(omml, number=None, center=4819, right=9638, font='ＭＳ 明朝', size=21):
    """数式だけの段落（w:p 要素）を作る。字下げは 0（Normal スタイルの字下げで中央がずれないように）。
    number=None: 独立行の数式（m:oMathPara・中央揃え）。分数が本文と同じ大きさで組まれる。
        タブの後ろに m:oMath を置くと Word は行内の数式として扱い、分数を小さい字で詰めてしまう（v12 で確認）
    number あり: 中央タブに数式、右端タブに (N)。行内の数式なので分数は小さくなる"""
    ppr = ('<w:spacing w:before="60" w:after="60"/>'
           '<w:ind w:left="0" w:leftChars="0" w:firstLine="0" w:firstLineChars="0"/>')
    if number is None:
        xml = (f'<w:p {_DECL}><w:pPr>{ppr}<w:jc w:val="center"/></w:pPr>'
               '<m:oMathPara><m:oMathParaPr><m:jc m:val="center"/></m:oMathParaPr>'
               f'<m:oMath>{omml}</m:oMath></m:oMathPara></w:p>')
        return parse_xml(xml)
    num = (f'<w:r><w:rPr><w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:eastAsia="{font}"/>'
           f'<w:sz w:val="{size}"/></w:rPr><w:tab/><w:t>({number})</w:t></w:r>')
    xml = (f'<w:p {_DECL}><w:pPr>'
           f'<w:tabs><w:tab w:val="center" w:pos="{center}"/><w:tab w:val="right" w:pos="{right}"/></w:tabs>'
           f'{ppr}</w:pPr>'
           f'<w:r><w:tab/></w:r><m:oMath>{omml}</m:oMath>{num}</w:p>')
    return parse_xml(xml)


def add_equation(doc, omml, number=None):
    center, right = _center_right(doc)
    el = equation_paragraph(omml, number, center, right)
    doc.element.body.append(el)
    sect = doc.element.body.find('{%s}sectPr' % W_NS)
    if sect is not None:          # sectPr は本文の最後に置く決まり
        sect.addprevious(el)
    return Paragraph(el, doc._body)


def insert_equation_after(paragraph, omml, number=None):
    center, right = _center_right(paragraph.part.document)
    el = equation_paragraph(omml, number, center, right)
    paragraph._p.addnext(el)
    return Paragraph(el, paragraph._parent)
