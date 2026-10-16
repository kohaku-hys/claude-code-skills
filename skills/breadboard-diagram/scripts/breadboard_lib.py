# breadboard_lib.py — ブレッドボード組み立て図の部品ライブラリ（T型基板つきブレッドボード）
#  ・T型基板（Raspberry Pi Breakout Board）つきブレッドボードを SVG で描く（LED・抵抗・DIP チップ・可変抵抗器・ジャンパー線）
#  ・配線の接続を union-find で検査してから図にする（check_partition）。回路と食い違う図は作れない
#  ・配線の交差を数え、直角配線の「通り道（レーン）」の並びを全探索して最小にする（optimize_wires）
#  ・HTML → A4 PDF（Chrome ヘッドレス）と、確認用の PNG を出す（to_pdf / page_pngs）
# 座標: 図の「行」は T型基板の SDA/TXD の行を 1 とする（実物のブレッドボードに印刷された数字とは合わなくてよい）
import html
import math

P = 18.0                      # 穴のピッチ [px]
X0, Y0 = 78.0, 76.0           # 左端の列(LO)の x と、行0 の y
COLX = {'LO': 0.0, 'LI': 1.0, 'a': 2.8, 'b': 3.8, 'c': 4.8, 'd': 5.8, 'e': 6.8,
        'f': 9.8, 'g': 10.8, 'h': 11.8, 'i': 12.8, 'j': 13.8, 'RI': 15.6, 'RO': 16.6}
LEFT_STRIP, RIGHT_STRIP = 'abcde', 'fghij'
RAIL_ROWS = 4                 # 赤丸の穴（テープが貼られていない所）= 行1〜4

# T型基板のピン名（補足資料 テーマ8 p.5・テーマ9 p.5 の写真の表示どおり。上から下）
TB_LEFT = ['SDA', 'SCL', 'GCLK', 'GND', 'IO17', 'IO27', 'IO22', 'MOSI', 'MISO', 'SCLK', 'IDSD', 'IO5', 'IO6', 'IO13', 'IO19', 'IO26']
TB_RIGHT = ['TXD', 'RXD', 'GND', 'IO18', 'IO23', 'IO24', 'IO25', 'CE0', 'CE1', 'IDSC', 'GND', 'IO12', 'GND', 'IO16', 'IO20', 'IO21']
TB_ROWS = 16


def hx(col, row):
    return (X0 + COLX[col] * P, Y0 + row * P)


# ---------------------------------------------------------------- 接続の検査
class Nets:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def node(h):
    """穴 → 電気的なノード。同じ行の片側5穴は1つのノード、レールの列は全体で1つ"""
    if isinstance(h, str):
        return h                                  # 'GND' '3V3' '5V' など名前そのもの
    col, row = h
    if col in LEFT_STRIP:
        return ('S', 'L', row)
    if col in RIGHT_STRIP:
        return ('S', 'R', row)
    assert 1 <= row <= RAIL_ROWS, f'レールは行1〜{RAIL_ROWS}の穴だけ使う: {h}'
    return ('RAIL', col)


def build_nets(wires):
    n = Nets()
    # T型基板: GND ピンはどれも Pi の GND、角の4ピンはレールにつながる
    for r, name in enumerate(TB_LEFT, start=1):
        if name == 'GND':
            n.union(node(('a', r)), 'GND')
    for r, name in enumerate(TB_RIGHT, start=1):
        if name == 'GND':
            n.union(node(('h', r)), 'GND')
    n.union(('RAIL', 'LO'), '3V3')
    n.union(('RAIL', 'LI'), 'GND')
    n.union(('RAIL', 'RI'), '5V')
    n.union(('RAIL', 'RO'), 'GND')
    for w in wires:
        n.union(node(w['a']), node(w['b']))
    return n


def check_partition(wires, terminals, expected_groups):
    """terminals: {名前: 穴 or 'GND' など}。接続のグループ分けが expected_groups と完全に一致することを確かめる"""
    n = build_nets(wires)
    groups = {}
    for name, h in terminals.items():
        groups.setdefault(n.find(node(h)), set()).add(name)
    got = {frozenset(g) for g in groups.values()}
    exp = {frozenset(g) for g in expected_groups}
    missing = exp - got
    extra = got - exp
    assert not missing and not extra, f'配線が資料の回路と合わない\n 足りない接続: {sorted(map(sorted, missing))}\n 余計な接続: {sorted(map(sorted, extra))}'
    return True


# ---------------------------------------------------------------- 描画
def esc(s):
    return html.escape(str(s))


def board_svg_parts(nrows, highlight=(), rail_circle=True, rownum=True):
    """ブレッドボード＋T型基板の下地。highlight = {('L'|'R', 行), ...} は使うピンのラベルを黄色にする"""
    out = []
    xl, _ = hx('LO', 0)
    xr, _ = hx('RO', 0)
    bx0, bx1 = xl - 0.95 * P, xr + 0.95 * P
    by0, by1 = Y0 - 3.5 * P, Y0 + (nrows + 0.9) * P
    out.append(f'<rect x="{bx0:.1f}" y="{by0:.1f}" width="{bx1 - bx0:.1f}" height="{by1 - by0:.1f}" rx="7" fill="#f4f1ea" stroke="#b9b3a5" stroke-width="1.2"/>')
    # 中央の溝
    xe, _ = hx('e', 0)
    xf, _ = hx('f', 0)
    out.append(f'<rect x="{xe + 0.55 * P:.1f}" y="{Y0 + 0.3 * P:.1f}" width="{xf - xe - 1.1 * P:.1f}" height="{(nrows + 0.5) * P:.1f}" fill="#e2ddd0"/>')
    # レールの色の線（左: 外側が赤・内側が青 / 右: 内側が赤・外側が青）
    for xcol, color in (('LO', '#d9534f'), ('RI', '#d9534f')):
        x, _ = hx(xcol, 0)
        off = -0.6 * P if xcol == 'LO' else -0.6 * P
        out.append(f'<line x1="{x + off:.1f}" y1="{Y0 + 0.4 * P:.1f}" x2="{x + off:.1f}" y2="{Y0 + nrows * P:.1f}" stroke="{color}" stroke-width="1.4" opacity=".75"/>')
    for xcol in ('LI', 'RO'):
        x, _ = hx(xcol, 0)
        out.append(f'<line x1="{x + 0.6 * P:.1f}" y1="{Y0 + 0.4 * P:.1f}" x2="{x + 0.6 * P:.1f}" y2="{Y0 + nrows * P:.1f}" stroke="#3b78c4" stroke-width="1.4" opacity=".75"/>')
    # 穴
    def hole(x, y, c='#4a4a4a'):
        return f'<rect x="{x - 2.1:.1f}" y="{y - 2.1:.1f}" width="4.2" height="4.2" rx="1" fill="{c}"/>'
    for r in range(1, nrows + 1):
        for col in 'abcdefghij':
            if r <= TB_ROWS and col in 'defg':
                continue                      # T型基板の下に隠れる
            x, y = hx(col, r)
            out.append(hole(x, y))
        for col in ('LO', 'LI', 'RI', 'RO'):
            x, y = hx(col, r)
            out.append(hole(x, y, '#4a4a4a' if r <= RAIL_ROWS else '#bdb8aa'))
    # テープ（レールの下の方は使わない）
    for col_a, col_b in (('LO', 'LI'), ('RI', 'RO')):
        xa, _ = hx(col_a, 0)
        xb, _ = hx(col_b, 0)
        y0 = Y0 + (RAIL_ROWS + 0.5) * P
        out.append(f'<rect x="{xa - 0.45 * P:.1f}" y="{y0:.1f}" width="{xb - xa + 0.9 * P:.1f}" height="{(nrows - RAIL_ROWS - 0.2) * P:.1f}" fill="url(#tape)" opacity=".85"/>')
    # 行番号（5行おき）
    for r in (range(5, nrows + 1, 5) if rownum else ()):
        _, y = hx('a', r)
        out.append(f'<text x="{bx0 - 3:.1f}" y="{y + 3:.1f}" text-anchor="end" font-size="8" fill="#8a8a8a">{r}</text>')
    # T型基板（上の帯と足）
    out.append(f'<rect x="{bx0 + 1:.1f}" y="{Y0 - 3.5 * P:.1f}" width="{bx1 - bx0 - 2:.1f}" height="{1.0 * P:.1f}" rx="4" fill="url(#cable)"/>')
    out.append(f'<rect x="{bx0 + 1:.1f}" y="{Y0 - 2.5 * P:.1f}" width="{bx1 - bx0 - 2:.1f}" height="{2.95 * P:.1f}" fill="#c93a3a" stroke="#8c1f1f" stroke-width="1"/>')
    out.append(f'<text x="{(bx0 + bx1) / 2:.1f}" y="{Y0 - 1.15 * P:.1f}" text-anchor="middle" font-size="8.5" fill="#fff" letter-spacing=".6">Raspberry Pi Breakout Board</text>')
    for col, label in (('LO', '3V3'), ('LI', 'GND'), ('RI', '5V'), ('RO', 'GND')):
        x, y = hx(col, 0)
        out.append(f'<text x="{x:.1f}" y="{y - 0.75 * P:.1f}" text-anchor="middle" font-size="7.8" fill="#fff" font-weight="700">{label}</text>')
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.7" fill="#d8d8d8" stroke="#777" stroke-width=".8"/>')
    xd, _ = hx('d', 0)
    xg, _ = hx('g', 0)
    out.append(f'<rect x="{xd - 0.75 * P:.1f}" y="{Y0 + 0.4 * P:.1f}" width="{xg - xd + 1.5 * P:.1f}" height="{(TB_ROWS + 0.35) * P:.1f}" rx="3" fill="#c93a3a" stroke="#8c1f1f" stroke-width="1"/>')
    for i, name in enumerate(TB_LEFT, start=1):
        x, y = hx('d', i)
        hi = ('L', i) in highlight
        if hi:
            out.append(f'<rect x="{x + 0.5 * P:.1f}" y="{y - 6.2:.1f}" width="{len(name) * 5.1 + 5:.1f}" height="12" rx="2" fill="#ffe14d"/>')
        out.append(f'<text x="{x + 0.6 * P:.1f}" y="{y + 2.8:.1f}" font-size="7.6" fill="{"#222" if hi else "#fff"}" font-weight="{"700" if hi else "400"}">{name}</text>')
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="#d8d8d8" stroke="#777" stroke-width=".8"/>')
    for i, name in enumerate(TB_RIGHT, start=1):
        x, y = hx('g', i)
        hi = ('R', i) in highlight
        if hi:
            out.append(f'<rect x="{x - 0.5 * P - len(name) * 5.1 - 5:.1f}" y="{y - 6.2:.1f}" width="{len(name) * 5.1 + 5:.1f}" height="12" rx="2" fill="#ffe14d"/>')
        out.append(f'<text x="{x - 0.6 * P:.1f}" y="{y + 2.8:.1f}" text-anchor="end" font-size="7.6" fill="{"#222" if hi else "#fff"}" font-weight="{"700" if hi else "400"}">{name}</text>')
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="#d8d8d8" stroke="#777" stroke-width=".8"/>')
    # 赤丸（使ってよいレールの穴）
    for ca, cb in ((('LO', 'LI'), ('RI', 'RO')) if rail_circle else ()):
        xa, _ = hx(ca, 0)
        xb, _ = hx(cb, 0)
        out.append(f'<ellipse cx="{(xa + xb) / 2:.1f}" cy="{Y0 + (RAIL_ROWS + 1) / 2 * P:.1f}" rx="{(xb - xa) / 2 + 0.75 * P:.1f}" ry="{(RAIL_ROWS + 0.2) / 2 * P + 4:.1f}" fill="none" stroke="#d11" stroke-width="1.6"/>')
    return out


DEFS = '''<defs>
<pattern id="tape" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="#e6e0d0"/><line x1="0" y1="0" x2="0" y2="6" stroke="#b8b09c" stroke-width="2.2"/></pattern>
<linearGradient id="cable" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="#7a4b2a"/><stop offset=".12" stop-color="#d33"/><stop offset=".25" stop-color="#e8912c"/><stop offset=".38" stop-color="#e8d82c"/><stop offset=".5" stop-color="#3a3"/><stop offset=".62" stop-color="#36c"/><stop offset=".75" stop-color="#93c"/><stop offset=".88" stop-color="#888"/><stop offset="1" stop-color="#eee"/></linearGradient>
</defs>'''


def wire_path(w):
    """配線の SVG パスと、ラベルを置く中点を返す"""
    x1, y1 = hx(*w['a'])
    x2, y2 = hx(*w['b'])
    pts = w.get('via')
    if pts:                                    # 折れ線（角を丸める）
        P_ = [(x1, y1)] + [tuple(p) for p in pts] + [(x2, y2)]
        r = 7.0
        d = f'M{P_[0][0]:.1f},{P_[0][1]:.1f}'
        for k in range(1, len(P_) - 1):
            ax, ay = P_[k - 1]
            bx, by = P_[k]
            cx, cy = P_[k + 1]
            l1 = math.hypot(bx - ax, by - ay)
            l2 = math.hypot(cx - bx, cy - by)
            rr = min(r, l1 / 2, l2 / 2)
            sx, sy = bx - (bx - ax) / l1 * rr, by - (by - ay) / l1 * rr
            ex, ey = bx + (cx - bx) / l2 * rr, by + (cy - by) / l2 * rr
            d += f' L{sx:.1f},{sy:.1f} Q{bx:.1f},{by:.1f} {ex:.1f},{ey:.1f}'
        d += f' L{P_[-1][0]:.1f},{P_[-1][1]:.1f}'
        seglens = [math.hypot(P_[k + 1][0] - P_[k][0], P_[k + 1][1] - P_[k][1]) for k in range(len(P_) - 1)]
        half = sum(seglens) / 2
        acc = 0
        mx, my = P_[0]
        for k, L in enumerate(seglens):
            if acc + L >= half:
                t = (half - acc) / L
                mx = P_[k][0] + (P_[k + 1][0] - P_[k][0]) * t
                my = P_[k][1] + (P_[k + 1][1] - P_[k][1]) * t
                break
            acc += L
        return d, (mx, my)
    b = w.get('bulge', 0.0)
    c1 = (x1 + b, y1)
    c2 = (x2 + b, y2)
    d = f'M{x1:.1f},{y1:.1f} C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {x2:.1f},{y2:.1f}'
    mx = 0.125 * x1 + 0.375 * c1[0] + 0.375 * c2[0] + 0.125 * x2
    my = 0.125 * y1 + 0.375 * c1[1] + 0.375 * c2[1] + 0.125 * y2
    return d, (mx, my)


def wires_svg(wires):
    under, over, badges = [], [], []
    for w in wires:
        d, (mx, my) = wire_path(w)
        col = w['color']
        under.append(f'<path d="{d}" fill="none" stroke="#fff" stroke-width="6.2" stroke-linecap="round" stroke-linejoin="round" opacity=".92"/>')
        over.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="3.3" stroke-linecap="round" stroke-linejoin="round"/>')
        for h in (w['a'], w['b']):
            x, y = hx(*h)
            over.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.6" fill="{col}" stroke="#222" stroke-width=".9"/>')
        pts = w.get('badge_pts') or [(mx + w.get('bdx', 0), my + w.get('bdy', 0))]
        for (bx, by) in pts:
            badges.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="7.2" fill="#fff" stroke="#222" stroke-width="1.1"/>'
                          f'<text x="{bx:.1f}" y="{by + 3.3:.1f}" text-anchor="middle" font-size="9" font-weight="700" fill="#111">{w["no"]}</text>')
    return under + over + badges


def led_svg(color, row, label):
    """LED を溝またぎ(カソード=e列・アノード=f列)に描く。足の長い方がアノード"""
    xe, y = hx('e', row)
    xf, _ = hx('f', row)
    cx = (xe + xf) / 2
    fill = {'青': '#2f6fe0', '緑': '#27a648', '赤': '#e03636'}[color]
    dark = {'青': '#1a3f8f', '緑': '#146a2b', '赤': '#8f1e1e'}[color]
    s = []
    s.append(f'<line x1="{xe:.1f}" y1="{y:.1f}" x2="{cx - 9:.1f}" y2="{y:.1f}" stroke="#777" stroke-width="2.4"/>')
    s.append(f'<line x1="{cx + 9:.1f}" y1="{y:.1f}" x2="{xf:.1f}" y2="{y:.1f}" stroke="#555" stroke-width="2.4"/>')
    s.append(f'<circle cx="{xe:.1f}" cy="{y:.1f}" r="3" fill="#bbb" stroke="#555" stroke-width=".7"/><circle cx="{xf:.1f}" cy="{y:.1f}" r="3" fill="#bbb" stroke="#555" stroke-width=".7"/>')
    s.append(f'<circle cx="{cx:.1f}" cy="{y:.1f}" r="10" fill="{fill}" stroke="{dark}" stroke-width="1.4"/>')
    s.append(f'<ellipse cx="{cx - 3:.1f}" cy="{y - 3.5:.1f}" rx="3.2" ry="2.2" fill="#fff" opacity=".55"/>')
    s.append(f'<line x1="{cx - 10:.1f}" y1="{y - 6:.1f}" x2="{cx - 10:.1f}" y2="{y + 6:.1f}" stroke="{dark}" stroke-width="2"/>')   # 平らな側=カソード
    s.append(f'<text x="{xe - 7:.1f}" y="{y - 7:.1f}" text-anchor="end" font-size="8.6" font-weight="700" fill="#222" paint-order="stroke" stroke="#f4f1ea" stroke-width="3">K</text>')
    s.append(f'<text x="{xf + 7:.1f}" y="{y - 7:.1f}" font-size="8.6" font-weight="700" fill="#222" paint-order="stroke" stroke="#f4f1ea" stroke-width="3">A</text>')
    s.append(f'<text x="{hx("h", row)[0] + 2:.1f}" y="{y + 15:.1f}" font-size="8.8" font-weight="700" fill="{dark}" paint-order="stroke" stroke="#f4f1ea" stroke-width="3">{esc(label)}</text>')
    return s


def resistor_svg(row_top, row_bot, col='c'):
    x, y1 = hx(col, row_top)
    _, y2 = hx(col, row_bot)
    b0, b1 = y1 + 0.75 * P, y2 - 0.75 * P
    s = [f'<line x1="{x:.1f}" y1="{y1:.1f}" x2="{x:.1f}" y2="{y2:.1f}" stroke="#777" stroke-width="2"/>',
         f'<rect x="{x - 5:.1f}" y="{b0:.1f}" width="10" height="{b1 - b0:.1f}" rx="3" fill="#e6c98d" stroke="#9a7b3c" stroke-width="1"/>']
    # 色の帯: 橙 橙 茶 金
    n = 4
    seg = (b1 - b0 - 6) / (n + 1)
    for k, c in enumerate(['#ee8a1c', '#ee8a1c', '#7a4a1e', '#d4af37']):
        yy = b0 + 3 + seg * (k + (0.3 if k < 3 else 0.9))
        s.append(f'<rect x="{x - 5:.1f}" y="{yy:.1f}" width="10" height="2.6" fill="{c}"/>')
    s.append(f'<circle cx="{x:.1f}" cy="{y1:.1f}" r="2.8" fill="#bbb" stroke="#555" stroke-width=".7"/><circle cx="{x:.1f}" cy="{y2:.1f}" r="2.8" fill="#bbb" stroke="#555" stroke-width=".7"/>')
    xt = hx('d', row_top)[0] + 1
    ymid = (y1 + y2) / 2
    s.append(f'<text x="{xt:.1f}" y="{ymid - 1:.1f}" font-size="8.2" fill="#6b4e12" font-weight="700" paint-order="stroke" stroke="#f4f1ea" stroke-width="3">330Ω</text>')
    s.append(f'<text x="{xt:.1f}" y="{ymid + 8.5:.1f}" font-size="7.2" fill="#6b4e12" paint-order="stroke" stroke="#f4f1ea" stroke-width="3">橙橙茶金</text>')
    return s


def svg_wrap(nrows, body, width=None):
    xr, _ = hx('RO', 0)
    w = width or (xr + 1.4 * P + 14)
    h = Y0 + (nrows + 1.6) * P
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" width="{w:.0f}" height="{h:.0f}" '
            f'font-family="\'Yu Gothic\',\'Meiryo\',sans-serif">{DEFS}{"".join(body)}</svg>')


def circled(n):
    return '①②③④⑤⑥⑦⑧⑨⑩⑪⑫'[n - 1]


def polyline_points(w):
    x1, y1 = hx(*w['a'])
    x2, y2 = hx(*w['b'])
    return [(x1, y1)] + [tuple(p) for p in w.get('via', [])] + [(x2, y2)]


def _ccw(a, b, c):
    return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0])


def seg_cross(p1, p2, p3, p4):
    """線分 p1p2 と p3p4 が、端点以外で交わるか（重なりや端点の接触は数えない）"""
    d1, d2 = _ccw(p3, p4, p1), _ccw(p3, p4, p2)
    d3, d4 = _ccw(p1, p2, p3), _ccw(p1, p2, p4)
    return d1 * d2 < -1e-9 and d3 * d4 < -1e-9


def count_crossings(wires):
    n = 0
    pls = [polyline_points(w) for w in wires]
    for i in range(len(pls)):
        for j in range(i + 1, len(pls)):
            for a in range(len(pls[i]) - 1):
                for b in range(len(pls[j]) - 1):
                    if seg_cross(pls[i][a], pls[i][a + 1], pls[j][b], pls[j][b + 1]):
                        n += 1
    return n


def dot_on_wire(wires, tol=5.5):
    """他の配線の線が、別の配線の端の点(穴)の上を通っていないか"""
    bad = []
    for i, w in enumerate(wires):
        pl = polyline_points(w)
        for j, v in enumerate(wires):
            if i == j:
                continue
            for h in (v['a'], v['b']):
                px, py = hx(*h)
                for k in range(len(pl) - 1):
                    (x1, y1), (x2, y2) = pl[k], pl[k + 1]
                    dx, dy = x2 - x1, y2 - y1
                    L2 = dx * dx + dy * dy
                    t = 0 if L2 == 0 else max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L2))
                    if math.hypot(px - (x1 + t * dx), py - (y1 + t * dy)) < tol:
                        bad.append((w.get('no', w.get('key')), v.get('no', v.get('key')), h))
    return bad


def badge_on_segment(p_from, p_to, dist):
    """p_from から p_to の向きに dist だけ進んだ点（線分が短ければ中点）"""
    L = math.hypot(p_to[0] - p_from[0], p_to[1] - p_from[1])
    t = 0.5 if L < dist * 1.6 else dist / L
    return (p_from[0] + (p_to[0] - p_from[0]) * t, p_from[1] + (p_to[1] - p_from[1]) * t)


# ======================================================================== ここから下は汎用部品（スキル化で追加）
import itertools
import os
import subprocess
import tempfile
import time


def dip_holes(top_row, left_order, right_order):
    """DIP チップの各ピンが入る穴。left_order / right_order は上から下へ並ぶピン番号。
    チップは溝またぎで、左の列のピンは e 列、右の列のピンは f 列に入る。戻り値: {ピン番号: (列, 行)}"""
    d = {}
    for k, n in enumerate(left_order):
        d[n] = ('e', top_row + k)
    for k, n in enumerate(right_order):
        d[n] = ('f', top_row + k)
    return d


def dip_svg(top_row, left_order, right_order, names, label, notch='bottom'):
    """DIP チップを描く。names は {ピン番号: 名前}。notch は切り欠きの側（'top' か 'bottom'）。
    1番ピンの印（白い点）は、切り欠きと反対側の左上（notch=top）か右下（notch=bottom）の角に付く"""
    holes = dip_holes(top_row, left_order, right_order)
    n_rows = max(len(left_order), len(right_order))
    xe, y_top = hx('e', top_row)
    xf, y_bot = hx('f', top_row + n_rows - 1)
    x0, x1 = xe - 0.55 * P, xf + 0.55 * P
    y0, y1 = y_top - 0.55 * P, y_bot + 0.55 * P
    s = []
    for n, (col, row) in holes.items():
        x, y = hx(col, row)
        if col == 'e':
            s.append(f'<rect x="{x0 - 3:.1f}" y="{y - 2:.1f}" width="{x - x0 + 3 + 0.2 * P:.1f}" height="4" fill="#bbb"/>')
        else:
            s.append(f'<rect x="{x - 0.2 * P:.1f}" y="{y - 2:.1f}" width="{x1 - x + 3 + 0.2 * P:.1f}" height="4" fill="#bbb"/>')
    s.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{x1 - x0:.1f}" height="{y1 - y0:.1f}" rx="3" fill="#2b2b2b" stroke="#000" stroke-width="1"/>')
    cx = (x0 + x1) / 2
    if notch == 'bottom':
        s.append(f'<path d="M{cx - 7:.1f},{y1:.1f} A7,7 0 0 1 {cx + 7:.1f},{y1:.1f}" fill="#f4f1ea" stroke="#000" stroke-width="1"/>')
        s.append(f'<circle cx="{x1 - 6:.1f}" cy="{y1 - 6:.1f}" r="2.4" fill="#ddd"/>')
        ty = y1 + 12
    else:
        s.append(f'<path d="M{cx - 7:.1f},{y0:.1f} A7,7 0 0 0 {cx + 7:.1f},{y0:.1f}" fill="#f4f1ea" stroke="#000" stroke-width="1"/>')
        s.append(f'<circle cx="{x0 + 6:.1f}" cy="{y0 + 6:.1f}" r="2.4" fill="#ddd"/>')
        ty = y0 - 4
    s.append(f'<text x="{cx:.1f}" y="{ty:.1f}" text-anchor="middle" font-size="8.8" fill="#222" font-weight="700" paint-order="stroke" stroke="#f4f1ea" stroke-width="3">{esc(label)}</text>')
    for n, (col, row) in holes.items():
        x, y = hx(col, row)
        if col == 'e':
            s.append(f'<text x="{x0 + 3:.1f}" y="{y + 2.8:.1f}" font-size="7.4" fill="#fff"><tspan font-weight="700">{n}</tspan> {esc(names.get(n, ""))}</text>')
        else:
            s.append(f'<text x="{x1 - 3:.1f}" y="{y + 2.8:.1f}" text-anchor="end" font-size="7.4" fill="#fff">{esc(names.get(n, ""))} <tspan font-weight="700">{n}</tspan></text>')
    return s


def pot_svg(col, rows, labels, title='可変抵抗器'):
    """3本足の可変抵抗器を、同じ列の連続した3行（別々のストリップ）に立てて描く。rows=(上, 中央, 下) の行、labels=(上, 中央, 下) の足の名前"""
    x, y_a = hx(col, rows[0])
    _, y_c = hx(col, rows[2])
    s = []
    bx0, bx1 = x + 0.55 * P, hx('e', 0)[0] + 0.7 * P
    s.append(f'<rect x="{bx0:.1f}" y="{y_a - 0.6 * P:.1f}" width="{bx1 - bx0:.1f}" height="{y_c - y_a + 1.2 * P:.1f}" rx="5" fill="#9aa0a6" stroke="#5f6368" stroke-width="1.2"/>')
    ymid = (y_a + y_c) / 2
    s.append(f'<circle cx="{bx1 - 9:.1f}" cy="{ymid:.1f}" r="9" fill="#cfd3d7" stroke="#5f6368" stroke-width="1"/><line x1="{bx1 - 9:.1f}" y1="{ymid - 8:.1f}" x2="{bx1 - 9:.1f}" y2="{ymid:.1f}" stroke="#5f6368" stroke-width="1.6"/>')
    for r, t in zip(rows, labels):
        _, y = hx(col, r)
        s.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{bx0:.1f}" y2="{y:.1f}" stroke="#777" stroke-width="2.2"/>')
        s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.9" fill="#bbb" stroke="#555" stroke-width=".7"/>')
        s.append(f'<text x="{bx0 + 3:.1f}" y="{y + 2.8:.1f}" font-size="7.4" fill="#111" font-weight="700">{esc(t)}</text>')
    s.append(f'<text x="{bx0:.1f}" y="{y_a - 0.85 * P:.1f}" font-size="8.4" font-weight="700" fill="#333" paint-order="stroke" stroke="#f4f1ea" stroke-width="3">{esc(title)}</text>')
    return s


def ortho_via(a, b, lane_x):
    """始点 → 左右へ lane_x まで → 縦に終点の行まで → 終点の穴、と直角に配線するときの通過点"""
    xs, ys = hx(*a)
    _, ye = hx(*b)
    via = []
    if abs(lane_x - xs) > 0.5:
        via.append((lane_x, ys))
    via.append((lane_x, ye))
    return via


def optimize_wires(make_wires, choices):
    """配線の「選べる並び」を全探索して、交差が最小で、別の配線の端の穴の上を線が通らない並びを返す。
    make_wires(*選んだ値) -> 配線(dict)のリスト、choices = 各引数の候補リスト（順列などのイテラブルのリスト）。
    戻り値: (交差の数, 配線のリスト)。条件を満たす並びが無ければ AssertionError"""
    best = None
    for combo in itertools.product(*[list(c) for c in choices]):
        ws = make_wires(*combo)
        c = count_crossings(ws)
        if best is not None and c >= best[0]:
            continue
        if dot_on_wire(ws):
            continue
        best = (c, ws)
    assert best is not None, '穴の上を線が通らない並びが見つからない（レーンや終点の穴を増やす）'
    return best


def number_wires(wires, order):
    """order（配線の key の並び）の順に番号を振り、始点と終点の近くに番号札を付ける"""
    wires.sort(key=lambda w: order.index(w['key']))
    for i, w in enumerate(wires, start=1):
        w['no'] = i
        pl = polyline_points(w)
        w['badge_pts'] = [badge_on_segment(pl[0], pl[1], 15), badge_on_segment(pl[-1], pl[-2], 15)]
    return wires


def find_chrome():
    for c in (r'C:\Program Files\Google\Chrome\Application\chrome.exe', r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
              r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'):
        if os.path.exists(c):
            return c
    raise FileNotFoundError('Chrome も Edge も見つからない')


def to_pdf(html_path, pdf_path, timeout=90):
    """HTML を Chrome ヘッドレスで A4 PDF にする。毎回新しいプロファイルを使う（前回のロックで固まらないように）"""
    prof = tempfile.mkdtemp(prefix='cu_bb_', dir=os.environ.get('TEMP'))
    args = [find_chrome(), '--headless=new', '--disable-gpu', '--no-sandbox', f'--user-data-dir={prof}', '--no-pdf-header-footer',
            f'--print-to-pdf={pdf_path}', 'file:///' + os.path.abspath(html_path).replace('\\', '/')]
    p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
    for _ in range(20):
        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000:
            return pdf_path
        time.sleep(0.5)
    raise RuntimeError('PDF ができなかった（Chrome が固まった可能性。新しい --user-data-dir で再実行）')


def page_pngs(pdf_path, out_dir, stem, dpi=130):
    """PDF の各ページを PNG にして目視確認用に保存する。同じ名前の古いページ画像は先に消す（ページ数が減った時の取り残し防止）"""
    import fitz
    os.makedirs(out_dir, exist_ok=True)
    for f in os.listdir(out_dir):
        if f.startswith(stem + '_p') and f.endswith('.png'):
            os.remove(os.path.join(out_dir, f))
    d = fitz.open(pdf_path)
    outs = []
    for i, pg in enumerate(d):
        o = os.path.join(out_dir, f'{stem}_p{i + 1}.png')
        pg.get_pixmap(dpi=dpi).save(o)
        outs.append(o)
    return d.page_count, outs


SHEET_CSS = '''@page { size: A4; margin: 6mm 8mm; }
* { box-sizing: border-box; }
body { font-family: "Yu Gothic","Meiryo",sans-serif; color:#1b1b1b; font-size: 9pt; line-height:1.34; margin:0; }
h1 { font-size: 15pt; margin:0 0 1mm; }
.sub { color:#555; font-size:8.5pt; margin-bottom:2.5mm; }
.wrap { display:grid; grid-template-columns: 92mm 1fr; gap: 5mm; align-items:start; }
.fig svg { width:100%; height:auto; display:block; }
.cap { font-size:7.8pt; color:#555; margin-top:1mm; }
h2 { font-size:10pt; margin:0 0 1mm; padding:.6mm 2mm; background:#2b3a8f; color:#fff; border-radius:2px; }
.box { margin-bottom:2.2mm; break-inside:avoid; }
table { border-collapse:collapse; width:100%; font-size:8.3pt; }
td,th { border:1px solid #aab; padding:.7mm 1.4mm; vertical-align:top; }
th { background:#eef; }
td.n { text-align:center; font-weight:700; width:9mm; white-space:nowrap; }
.sw { display:inline-block; width:8px; height:8px; border-radius:50%; border:1px solid #333; margin-right:3px; }
ol, ul { margin:0; padding-left:5mm; }
li { margin-bottom:.7mm; }
.warn { border:1.6px solid #c22; background:#fff2f2; padding:1.6mm 2.4mm; border-radius:3px; font-size:8.6pt; margin-bottom:3mm; }
.warn b { color:#b00; }
code { font-family: Consolas,monospace; background:#f0f0f0; padding:0 1mm; font-size:8.4pt; }
.bottom { display:grid; grid-template-columns: 1fr 1fr; gap:5mm; margin-top:1.5mm; }
.chk li { list-style:none; margin-left:-4mm; }
.chk li::before { content:"□ "; }
.small { font-size:7.8pt; color:#555; }'''


def wire_table_rows(wires, color_names):
    """配線表の <tr> を作る。wires の各要素に no / color / desc が要る。color_names は {色コード: 色名}"""
    rows = ''
    for w in wires:
        rows += (f'<tr><td class="n">{circled(w["no"])}</td><td><span class="sw" style="background:{w["color"]}"></span>'
                 f'{color_names[w["color"]]}</td><td>{w["desc"]}</td></tr>')
    return rows
