# 例1: LED 3個（GPIO → LED → 330Ω → GND）。作者の学生実験（ラズパイ）テーマ8 の図の原型。
# 使い方: py example_led3.py [出力フォルダ]     出力: example_led3.pdf（A4・1枚）と pages/example_led3_p1.png
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from breadboard_lib import *

NROWS = 34
# (GPIO 番号, T型基板 右列のピン行, LED を置く行, LED の色, 配線の色)。上から 25, 24, 23 の順に置くと右側の配線が交差しない
LEDS = [(25, 7, 19, '赤', '#e03636'), (24, 6, 24, '緑', '#27a648'), (23, 5, 29, '青', '#2f6fe0')]
GND_START = [('c', 4), ('b', 4), ('a', 4)]          # T型基板 左列 4番目の GND ピンの行（空いている穴 a b c）
GND_BULGE = [-26, -40, -56]
GPIO_BULGE = {19: 40, 24: 52, 29: 64}


def make_model():
    """配線(dict)・検査用の端子表・期待する接続のグループ を返す"""
    wires, no = [], 1
    for gp, prow, row, jp, col in LEDS:                       # GPIO → LED のアノード側（右）
        wires.append(dict(no=no, color=col, a=('j', prow), b=('j', row), bulge=GPIO_BULGE[row],
                          desc=f'T型基板 右列 IO{gp} → {jp}LED の A 側（右）の行'))
        no += 1
    for k, (gp, prow, row, jp, col) in enumerate(LEDS):       # 抵抗の下の足 → GND
        wires.append(dict(no=no, color='#222222', a=GND_START[k], b=('a', row + 3), bulge=GND_BULGE[k],
                          desc=f'T型基板 左列 GND → {jp}LED の抵抗の下の足の行'))
        no += 1
    terminals = {'GND': 'GND'}
    expected = [{'GND'} | {f'R{gp}.2' for gp, *_ in LEDS}]
    for gp, prow, row, jp, col in LEDS:
        terminals[f'IO{gp}'] = ('g', prow)                    # T型基板のピンは g 列
        terminals[f'LED{gp}.A'] = ('f', row)
        terminals[f'LED{gp}.K'] = ('e', row)
        terminals[f'R{gp}.1'] = ('c', row)
        terminals[f'R{gp}.2'] = ('c', row + 3)
        expected += [{f'IO{gp}', f'LED{gp}.A'}, {f'LED{gp}.K', f'R{gp}.1'}]
    return wires, terminals, expected


def build(out_dir, name='example_led3'):
    wires, terminals, expected = make_model()
    check_partition(wires, terminals, expected)               # 回路と食い違えばここで止まる
    used = [h for h in terminals.values() if isinstance(h, tuple)]
    assert len(used) == len(set(used)), '部品の足が同じ穴に重なっている'
    highlight = {('R', prow) for _, prow, *_ in LEDS} | {('L', 4)}
    body = board_svg_parts(NROWS, highlight, rail_circle=False)
    for gp, prow, row, jp, col in LEDS:
        body += resistor_svg(row, row + 3)
    for gp, prow, row, jp, col in LEDS:
        body += led_svg(jp, row, f'{jp}  GPIO{gp}')
    body += wires_svg(wires)
    svg = svg_wrap(NROWS, body)
    rows = wire_table_rows(wires, {'#e03636': '赤', '#27a648': '緑', '#2f6fe0': '青', '#222222': '黒'})
    html_text = (f'<!doctype html><html lang="ja"><head><meta charset="utf-8"><title>{name}</title><style>{SHEET_CSS}</style></head><body>'
                 f'<h1>例: LED 3個の組み立て図</h1><div class="sub">配線 {len(wires)} 本。配線の接続は自動検査済み</div>'
                 f'<div class="wrap"><div class="fig">{svg}<div class="cap">T型基板を上にした見取り図。数字は図の行番号（T型基板の SDA/TXD の行が1）。</div></div>'
                 f'<div><div class="box"><h2>配線表</h2><table><tr><th>No.</th><th style="width:11mm">色</th><th>から → まで</th></tr>{rows}</table></div></div></div></body></html>')
    os.makedirs(out_dir, exist_ok=True)
    html_path = os.path.join(out_dir, name + '.html')
    open(html_path, 'w', encoding='utf-8').write(html_text)
    pdf = to_pdf(html_path, os.path.join(out_dir, name + '.pdf'))
    pages, _ = page_pngs(pdf, os.path.join(out_dir, 'pages'), name)
    return pdf, pages


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.getcwd(), 'breadboard_out')
    pdf, pages = build(out)
    print('配線の検査 OK ->', pdf, pages, 'ページ')
