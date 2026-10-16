# OMML 数式チートシート（report スキル用）

`python-docx` の `docx.oxml.parse_xml` で直接挿入するOMML(Office Math Markup Language)の要素例。
COM経由のLaTeX変換は不要 — 通常の数式はすべて parse_xml で表現可能。

## まず `scripts/omml_lib.py` を使う（2026-10-07〜）

部品（r・up・unit・sub・sup・subsup・frac・rad・paren・text・cat）と、数式だけの行を作る
`add_equation(doc, omml, number=None)`／`insert_equation_after(paragraph, omml, number=None)` が入っている。
下の「ヘルパ関数」は中身の説明として残してある。

### 計算例（代入計算）は1式1行・番号なし（P-059）

文の中に「27.901 ÷ (1 − 27.901 ÷ 3000) ≒ 28.163 Ω」と埋め込むと行の途中で折れて読めない（lint Check 18 が NG）。
文を閉じてから、次の行に番号なしの数式を置く（実際のレポートで使った形）:

```python
import sys, os; sys.path.insert(0, os.path.expanduser(r'~/.claude/skills/report/scripts'))
from omml_lib import r, up, unit, cat, sub, sup, frac, rad, insert_equation_after

Rt, ea = sub('R', 't'), sub('ε', 'a')
p = add_para('計算例として、表2の①は平均値 R_{x} = 27.901 Ω を式(2)と式(3)に代入して次のように求めた。')
e1 = insert_equation_after(p, cat(Rt, r('='), frac('27.901', cat(r('1−'), frac('27.901', '3000'))),
                                  r('≒'), r('28.163'), unit('Ω')))
e2 = insert_equation_after(e1, cat(ea, r('='), frac('27.901−28.163', '28.163'), r('×'), r('100'),
                                   r('≒'), r('−0.930'), up('%')))
# 10 のべき: frac('13.4', cat(r('12×'), sup('10', '−3')))／根号: rad(cat(sub('r','A'), sub('r','V')))
# 数式の中の丸数字・日本語は text('①　')（m:nor でＭＳ 明朝）
```

### 独立行と行内の違い（Word の組み方）

- **数式だけの段落（m:oMathPara）＝独立行**: 分数が本文と同じ大きさで組まれる。番号なしの行（number=None）はこれ
- **タブや (N) の run と同じ段落に m:oMath を置く＝行内**: 分数が小さい字で詰まる（入れ子の分数は特に読みにくい）。番号付きの式（number あり）は今これ
- Word の「式 #(10)」の式番号は、この PC の Word では右寄せにならず式の直後に (10) が付いた（2026-10-07 試験）。使わない
- 番号付きで大きい分数にしたい時は、枠線なし3列の表に入れる方法があるが未実装（lint の式番号の検出が段落前提なので、入れるなら lint も直す）

## ヘルパ関数

```python
from docx.oxml import parse_xml
from docx.shared import Pt, Cm
from docx.enum.text import WD_TAB_ALIGNMENT

OMML_NS = 'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"'

def add_equation(doc, omml_inner, number=None):
    """OMML形式の数式を中央配置・番号付きで挿入。"""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    tab_stops = p.paragraph_format.tab_stops
    tab_stops.add_tab_stop(Cm(8.0), WD_TAB_ALIGNMENT.CENTER)
    tab_stops.add_tab_stop(Cm(16.0), WD_TAB_ALIGNMENT.RIGHT)
    p.add_run('\t')
    xml = f'<m:oMath {OMML_NS}>{omml_inner}</m:oMath>'
    p._p.append(parse_xml(xml))
    if number is not None:
        r = p.add_run(f'\t({number})')
        r.font.name = 'Century'
        r.font.size = Pt(11)
    return p
```

## 要素チートシート

| 数式 | OMML |
|------|------|
| x² | `<m:sSup><m:e><m:r><m:t>x</m:t></m:r></m:e><m:sup><m:r><m:t>2</m:t></m:r></m:sup></m:sSup>` |
| I_s | `<m:sSub><m:e><m:r><m:t>I</m:t></m:r></m:e><m:sub><m:r><m:t>s</m:t></m:r></m:sub></m:sSub>` |
| 分数 a/b | `<m:f><m:num><m:r><m:t>a</m:t></m:r></m:num><m:den><m:r><m:t>b</m:t></m:r></m:den></m:f>` |
| √5（次数非表示） | `<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/><m:e><m:r><m:t>5</m:t></m:r></m:e></m:rad>` |
| 定積分 ∫₀ˣ | `<m:nary><m:naryPr><m:limLoc m:val="subSup"/></m:naryPr><m:sub>...</m:sub><m:sup>...</m:sup><m:e>...</m:e></m:nary>` |
| 括弧 (…) | `<m:d><m:dPr><m:begChr m:val="("/><m:endChr m:val=")"/></m:dPr><m:e>...</m:e></m:d>` |
| 関数 tan²φ | sSup の e に `<m:r><m:t>tan</m:t></m:r>` を入れ、続けて `<m:r><m:t>φ</m:t></m:r>` |

## 使用例：ダイオード式 I = Is(exp(qV/kT) - 1)

```python
I_s = '<m:sSub><m:e><m:r><m:t>I</m:t></m:r></m:e><m:sub><m:r><m:t>s</m:t></m:r></m:sub></m:sSub>'
qV_kT = '<m:f><m:num><m:r><m:t>qV</m:t></m:r></m:num><m:den><m:r><m:t>kT</m:t></m:r></m:den></m:f>'
eq = (
    '<m:r><m:t>I=</m:t></m:r>' + I_s +
    '<m:d><m:dPr><m:begChr m:val="("/><m:endChr m:val=")"/></m:dPr>'
    '<m:e><m:r><m:t>exp</m:t></m:r>'
    '<m:d><m:dPr><m:begChr m:val="("/><m:endChr m:val=")"/></m:dPr>'
    '<m:e>' + qV_kT + '</m:e></m:d>'
    '<m:r><m:t>−1</m:t></m:r>'
    '</m:e></m:d>'
)
add_equation(doc, eq, number=1)
```

## 番号運用

- 1つのレポート内で通し番号（課題ごとにリセットしない）
- 本文中の参照「式(2)の両辺に…」も連動

## 禁止

- 「※注意: この数式は手動で変換してください」等の注意書き
- Unicode上付き文字（³⁴⁵）での代用 — 本文フォントと不整合になる
