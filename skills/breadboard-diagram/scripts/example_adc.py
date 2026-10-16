# 例2: AD コンバータ MCP3208 + 可変抵抗器 + SPI（配線 11 本）。作者の学生実験（ラズパイ）テーマ9 の図の原型。
# 配線が多いので、直角配線の「通り道（レーン）」の並びを optimize_wires で全探索し、交差を最小にする。
# 使い方: py example_adc.py [出力フォルダ]     出力: example_adc.pdf（A4・1枚）と pages/example_adc_p1.png
import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from breadboard_lib import *

NROWS = 35
CHIP_TOP = 19
# 補足資料 p.5 の写真を 180° 回した向き（T型基板が上）。左の列は上から 9→16 番、右の列は上から 8→1 番
LEFT_ORDER, RIGHT_ORDER = list(range(9, 17)), list(range(8, 0, -1))
PIN_NAME = {1: 'CH0', 2: 'CH1', 3: 'CH2', 4: 'CH3', 5: 'CH4', 6: 'CH5', 7: 'CH6', 8: 'CH7',
            9: 'DGND', 10: 'CS', 11: 'DIN', 12: 'DOUT', 13: 'CLK', 14: 'AGND', 15: 'VREF', 16: 'VDD'}
HOLES = dip_holes(CHIP_TOP, LEFT_ORDER, RIGHT_ORDER)
POT_COL, POT_ROWS = 'c', (30, 31, 32)                # 上から GND 端・中央・3.3 V 端
POT = {'GND': (POT_COL, 30), 'W': (POT_COL, 31), '3V3': (POT_COL, 32)}
RED, BLK, BLU, YEL = '#d62828', '#222222', '#2a6fdb', '#e6b800'
XL = {k: hx(k, 0)[0] for k in ('a', 'LO', 'LI')}
RED_LANES = [XL['LO'] - 12, XL['LO'] - 22, XL['LO'] - 32]
BLK_LANES = [XL['LI'] - 6, XL['LI'], XL['LI'] + 6]
SPI_LANES = [XL['a'] - 22, XL['a'] - 16, XL['a'] - 10]
RED_W = [('VDD', ('a', HOLES[16][1]), '3.3 V の穴 → VDD（16番ピン）の行'),
         ('VREF', ('a', HOLES[15][1]), '3.3 V の穴 → VREF（15番ピン）の行'),
         ('VR3', ('a', POT['3V3'][1]), '3.3 V の穴 → 可変抵抗器の下の足の行')]
BLK_W = [('DGND', ('a', HOLES[9][1]), 'GND の穴 → DGND（9番ピン）の行'),
         ('AGND', ('a', HOLES[14][1]), 'GND の穴 → AGND（14番ピン）の行'),
         ('VRG', ('a', POT['GND'][1]), 'GND の穴 → 可変抵抗器の上の足の行')]
SPI_W = [('MOSI', ('a', 8), ('a', HOLES[11][1]), 'T型基板 左列 MOSI → DIN（11番ピン）の行'),
         ('MISO', ('a', 9), ('a', HOLES[12][1]), 'T型基板 左列 MISO → DOUT（12番ピン）の行'),
         ('SCLK', ('a', 10), ('a', HOLES[13][1]), 'T型基板 左列 SCLK → CLK（13番ピン）の行')]
ORDER = ['DGND', 'AGND', 'VRG', 'MOSI', 'MISO', 'SCLK', 'CE0', 'WIP', 'VDD', 'VREF', 'VR3']   # 組み立ての順（電源は最後）


def make_wires(red_rows, red_lane, blk_rows, blk_lane, spi_lane):
    ws = []
    for k, (nm, end, desc) in enumerate(RED_W):
        a = ('LO', red_rows[k])
        ws.append(dict(key=nm, color=RED, a=a, b=end, via=ortho_via(a, end, red_lane[k]), desc=desc))
    for k, (nm, end, desc) in enumerate(BLK_W):
        a = ('LI', blk_rows[k])
        ws.append(dict(key=nm, color=BLK, a=a, b=end, via=ortho_via(a, end, blk_lane[k]), desc=desc))
    for k, (nm, a, end, desc) in enumerate(SPI_W):
        ws.append(dict(key=nm, color=BLU, a=a, b=end, via=ortho_via(a, end, spi_lane[k]), desc=desc))
    xj, y8 = hx('j', 8)
    xd = hx('d', 0)[0]
    y_gap = hx('d', 17.7)[1]
    ws.append(dict(key='CE0', color=BLU, a=('j', 8), b=('d', HOLES[10][1]), via=[(xj + 24, y8), (xj + 24, y_gap), (xd, y_gap)],
                   desc='T型基板 右列 CE0 → CS（10番ピン）の行'))
    xb, xg = hx('b', 0)[0], hx('g', 0)[0]
    y33 = hx('b', 33.4)[1]
    ws.append(dict(key='WIP', color=YEL, a=('b', 31), b=('g', HOLES[1][1]), via=[(xb, y33), (xg, y33)],
                   desc='可変抵抗器の中央の足 → CH0（1番ピン）の行'))
    return ws


def make_model():
    perms = itertools.permutations
    n_cross, wires = optimize_wires(make_wires, [perms([1, 2, 3]), perms(RED_LANES), perms([1, 2, 3]), perms(BLK_LANES), perms(SPI_LANES)])
    number_wires(wires, ORDER)
    terminals = {'GND': 'GND', '3V3': '3V3', 'MOSI': ('d', 8), 'MISO': ('d', 9), 'SCLK': ('d', 10), 'CE0': ('g', 8),
                 'VR.GND': POT['GND'], 'VR.W': POT['W'], 'VR.3V3': POT['3V3']}
    terminals.update({f'U{n}': HOLES[n] for n in range(1, 17)})
    expected = [{'GND', 'U9', 'U14', 'VR.GND'}, {'3V3', 'U15', 'U16', 'VR.3V3'},
                {'MOSI', 'U11'}, {'MISO', 'U12'}, {'SCLK', 'U13'}, {'CE0', 'U10'}, {'U1', 'VR.W'}] + [{f'U{n}'} for n in range(2, 9)]
    return wires, terminals, expected, n_cross


def build(out_dir, name='example_adc'):
    wires, terminals, expected, n_cross = make_model()
    check_partition(wires, terminals, expected)               # 回路と食い違えばここで止まる
    used = [h for h in terminals.values() if isinstance(h, tuple)]
    assert len(used) == len(set(used)), '部品の足が同じ穴に重なっている'
    highlight = {('L', 4), ('L', 8), ('L', 9), ('L', 10), ('R', 8)}
    body = board_svg_parts(NROWS, highlight, rail_circle=True, rownum=False)
    body += dip_svg(CHIP_TOP, LEFT_ORDER, RIGHT_ORDER, PIN_NAME, 'MCP3208', notch='bottom')
    body += pot_svg(POT_COL, POT_ROWS, ('GND', '中央', '3.3V'), '可変抵抗器 10 kΩ')
    body += wires_svg(wires)
    svg = svg_wrap(NROWS, body)
    rows = wire_table_rows(wires, {RED: '赤', BLK: '黒', BLU: '青', YEL: '黄'})
    html_text = (f'<!doctype html><html lang="ja"><head><meta charset="utf-8"><title>{name}</title><style>{SHEET_CSS}</style></head><body>'
                 f'<h1>例: MCP3208 と可変抵抗器の組み立て図</h1><div class="sub">配線 {len(wires)} 本（交差 {n_cross} か所）。配線の接続は自動検査済み</div>'
                 f'<div class="wrap"><div class="fig">{svg}<div class="cap">T型基板を上にした見取り図（資料の写真は上下逆）。</div></div>'
                 f'<div><div class="warn"><b>3.3 V の赤い線は最後に。</b></div>'
                 f'<div class="box"><h2>配線表</h2><table><tr><th>No.</th><th style="width:11mm">色</th><th>から → まで</th></tr>{rows}</table></div></div></div></body></html>')
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
