"""
回路図描画ライブラリ — matplotlib直描で回路部品を描画する共通関数群。
全て白黒、日本語フォント対応。

使用例:
    from circuit_lib import *
    fig, ax = new_circuit(figsize=(8, 5))
    p = draw_source_dc(ax, 1, 0, 'up', 'V = 10 V')
    draw_wire(ax, [(p[1][0], p[1][1]), (5, 6)])
    p2 = draw_resistor(ax, 5, 6, 'down', 'R = 10 Ω')
    save_circuit(fig, 'output.png')
"""
import os
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

BASE = os.environ.get("USERPROFILE") or str(Path.home())

# デフォルト設定
_LW = 2
_COLOR = 'black'
_FONTSIZE = 11
_FONT = 'MS Gothic'
_DPI = 300

def new_circuit(figsize=(8, 5)):
    """新しい回路図キャンバスを作成"""
    fig, ax = plt.subplots(1, 1, figsize=figsize)
    ax.set_aspect('equal')
    ax.axis('off')
    return fig, ax

def save_circuit(fig, path, dpi=_DPI):
    """回路図を保存する。保存の前に、図の中の全ての軸で文字かぶりを機械検査し、
    1件でもあれば AssertionError で止める（重なった図がファイルに出ない）。

    2026-09-28 から save_circuit の中で必ず検査する（呼び忘れで重なった図が載るのを防ぐ）。
    呼び出し側で先に assert_no_overlaps(fig, ax) を呼んでいても、同じ検査をもう一度する
    だけで結果は変わらない（二重に呼んでも害はない）。"""
    for ax in fig.axes:
        assert_no_overlaps(fig, ax)
    fig.savefig(path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close(fig)

def _offset(x, y, direction, dist):
    """方向に沿ってdist分移動した座標を返す"""
    d = {'up': (0, dist), 'down': (0, -dist), 'right': (dist, 0), 'left': (-dist, 0)}
    dx, dy = d[direction]
    return x + dx, y + dy

def _perp_offset(direction, dist):
    """方向に垂直なオフセットを返す"""
    d = {'up': (dist, 0), 'down': (-dist, 0), 'right': (0, dist), 'left': (0, -dist)}
    return d[direction]

def draw_wire(ax, points, lw=_LW):
    """配線を描画。pointsは(x,y)タプルのリスト"""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    ax.plot(xs, ys, '-', color=_COLOR, linewidth=lw)
    return points[0], points[-1]

def draw_dot(ax, x, y, size=6):
    """接続点を描画"""
    ax.plot(x, y, 'o', color=_COLOR, markersize=size)
    return (x, y)

def draw_gnd(ax, x, y, size=0.3):
    """GND記号を描画"""
    ax.plot([x, x], [y, y - size * 0.5], '-', color=_COLOR, linewidth=_LW)
    for i, w in enumerate([size, size * 0.6, size * 0.2]):
        yy = y - size * 0.5 - i * size * 0.25
        ax.plot([x - w / 2, x + w / 2], [yy, yy], '-', color=_COLOR, linewidth=_LW)
    return (x, y)

def draw_label(ax, x, y, text, fontsize=_FONTSIZE, ha='center', va='center', **kwargs):
    """ラベルを描画"""
    ax.text(x, y, text, fontsize=fontsize, ha=ha, va=va,
            fontfamily=_FONT, color=_COLOR, **kwargs)

def draw_resistor(ax, x, y, direction='right', label='', length=2.0, label_side='left', label_offset=0.4):
    """ジグザグ抵抗を描画。returns (start, end)"""
    n_zigzag = 6
    lead = length * 0.2
    body = length * 0.6

    start = (x, y)
    end = _offset(x, y, direction, length)

    if direction in ('right', 'left'):
        sign = 1 if direction == 'right' else -1
        # リード線
        ax.plot([x, x + sign * lead], [y, y], '-', color=_COLOR, linewidth=_LW)
        # ジグザグ
        zx = [x + sign * lead]
        zy = [y]
        amp = 0.15
        for i in range(n_zigzag):
            zx.append(x + sign * (lead + body * (i + 0.5) / n_zigzag))
            zy.append(y + amp * (1 if i % 2 == 0 else -1))
        zx.append(x + sign * (lead + body))
        zy.append(y)
        ax.plot(zx, zy, '-', color=_COLOR, linewidth=_LW)
        # リード線
        ax.plot([x + sign * (lead + body), end[0]], [y, y], '-', color=_COLOR, linewidth=_LW)
        # ラベル
        if label:
            lx = x + sign * length / 2
            ly = y + (label_offset if label_side == 'top' else -label_offset)
            draw_label(ax, lx, ly, label)
    else:
        sign = 1 if direction == 'up' else -1
        ax.plot([x, x], [y, y + sign * lead], '-', color=_COLOR, linewidth=_LW)
        zx = [x]
        zy = [y + sign * lead]
        amp = 0.15
        for i in range(n_zigzag):
            zx.append(x + amp * (1 if i % 2 == 0 else -1))
            zy.append(y + sign * (lead + body * (i + 0.5) / n_zigzag))
        zx.append(x)
        zy.append(y + sign * (lead + body))
        ax.plot(zx, zy, '-', color=_COLOR, linewidth=_LW)
        ax.plot([x, x], [y + sign * (lead + body), end[1]], '-', color=_COLOR, linewidth=_LW)
        if label:
            lx = x + (-label_offset if label_side == 'left' else label_offset)
            ly = y + sign * length / 2
            ha = 'right' if label_side == 'left' else 'left'
            draw_label(ax, lx, ly, label, ha=ha)

    return start, end

def draw_capacitor(ax, x, y, direction='right', label='', length=1.5, label_side='left', label_offset=0.4):
    """コンデンサを描画"""
    gap = 0.12
    plate_size = 0.3
    start = (x, y)
    end = _offset(x, y, direction, length)
    mid = length / 2

    if direction in ('right', 'left'):
        sign = 1 if direction == 'right' else -1
        mx = x + sign * mid
        ax.plot([x, mx - sign * gap], [y, y], '-', color=_COLOR, linewidth=_LW)
        ax.plot([mx - sign * gap, mx - sign * gap], [y - plate_size, y + plate_size], '-', color=_COLOR, linewidth=_LW + 0.5)
        ax.plot([mx + sign * gap, mx + sign * gap], [y - plate_size, y + plate_size], '-', color=_COLOR, linewidth=_LW + 0.5)
        ax.plot([mx + sign * gap, end[0]], [y, y], '-', color=_COLOR, linewidth=_LW)
        if label:
            ly = y + (label_offset if label_side == 'top' else -label_offset)
            draw_label(ax, mx, ly, label)
    else:
        sign = 1 if direction == 'up' else -1
        my = y + sign * mid
        ax.plot([x, x], [y, my - sign * gap], '-', color=_COLOR, linewidth=_LW)
        ax.plot([x - plate_size, x + plate_size], [my - sign * gap, my - sign * gap], '-', color=_COLOR, linewidth=_LW + 0.5)
        ax.plot([x - plate_size, x + plate_size], [my + sign * gap, my + sign * gap], '-', color=_COLOR, linewidth=_LW + 0.5)
        ax.plot([x, x], [my + sign * gap, end[1]], '-', color=_COLOR, linewidth=_LW)
        if label:
            lx = x + (-label_offset if label_side == 'left' else label_offset)
            ha = 'right' if label_side == 'left' else 'left'
            draw_label(ax, lx, my, label, ha=ha)

    return start, end

def draw_diode(ax, x, y, direction='down', label='', length=1.5, label_side='left', label_offset=0.5):
    """ダイオードを描画"""
    start = (x, y)
    end = _offset(x, y, direction, length)
    mid = length / 2
    tri = 0.2

    if direction in ('right', 'left'):
        sign = 1 if direction == 'right' else -1
        mx = x + sign * mid
        ax.plot([x, mx - sign * tri], [y, y], '-', color=_COLOR, linewidth=_LW)
        triangle = plt.Polygon(
            [(mx - sign * tri, y - tri), (mx - sign * tri, y + tri), (mx + sign * tri, y)],
            closed=True, fill=True, facecolor=_COLOR, edgecolor=_COLOR)
        ax.add_patch(triangle)
        ax.plot([mx + sign * tri, mx + sign * tri], [y - tri, y + tri], '-', color=_COLOR, linewidth=_LW + 0.5)
        ax.plot([mx + sign * tri, end[0]], [y, y], '-', color=_COLOR, linewidth=_LW)
        if label:
            ly = y + (label_offset if label_side == 'top' else -label_offset)
            draw_label(ax, mx, ly, label)
    else:
        sign = 1 if direction == 'up' else -1
        my = y + sign * mid
        ax.plot([x, x], [y, my - sign * tri], '-', color=_COLOR, linewidth=_LW)
        triangle = plt.Polygon(
            [(x - tri, my - sign * tri), (x + tri, my - sign * tri), (x, my + sign * tri)],
            closed=True, fill=True, facecolor=_COLOR, edgecolor=_COLOR)
        ax.add_patch(triangle)
        ax.plot([x - tri, x + tri], [my + sign * tri, my + sign * tri], '-', color=_COLOR, linewidth=_LW + 0.5)
        ax.plot([x, x], [my + sign * tri, end[1]], '-', color=_COLOR, linewidth=_LW)
        if label:
            lx = x + (-label_offset if label_side == 'left' else label_offset)
            ha = 'right' if label_side == 'left' else 'left'
            draw_label(ax, lx, my, label, ha=ha)

    return start, end

def draw_source_dc(ax, x, y, direction='up', label='', length=2.0, label_side='left', label_offset=0.5):
    """直流電源を描画（丸に+/-）"""
    start = (x, y)
    end = _offset(x, y, direction, length)
    mid_x, mid_y = _offset(x, y, direction, length / 2)
    r = 0.4

    # リード線
    if direction in ('up', 'down'):
        sign = 1 if direction == 'up' else -1
        ax.plot([x, x], [y, mid_y - sign * r], '-', color=_COLOR, linewidth=_LW)
        ax.plot([x, x], [mid_y + sign * r, end[1]], '-', color=_COLOR, linewidth=_LW)
    else:
        sign = 1 if direction == 'right' else -1
        ax.plot([x, mid_x - sign * r], [y, y], '-', color=_COLOR, linewidth=_LW)
        ax.plot([mid_x + sign * r, end[0]], [y, y], '-', color=_COLOR, linewidth=_LW)

    circle = plt.Circle((mid_x, mid_y), r, fill=False, color=_COLOR, linewidth=_LW)
    ax.add_patch(circle)
    # +/- 記号
    if direction in ('up', 'down'):
        sign = 1 if direction == 'up' else -1
        draw_label(ax, mid_x, mid_y + sign * 0.15, '+', fontsize=10)
        draw_label(ax, mid_x, mid_y - sign * 0.15, '−', fontsize=10)
    else:
        sign = 1 if direction == 'right' else -1
        draw_label(ax, mid_x + sign * 0.15, mid_y, '+', fontsize=10)
        draw_label(ax, mid_x - sign * 0.15, mid_y, '−', fontsize=10)

    if label:
        px, py = _perp_offset(direction, label_offset)
        if label_side == 'right':
            px, py = -px, -py
        draw_label(ax, mid_x - px, mid_y - py, label,
                   ha='right' if label_side == 'left' else 'left')

    return start, end

def draw_source_ac(ax, x, y, direction='up', label='', length=2.0, label_side='left', label_offset=0.5):
    """交流電源を描画（丸に~）"""
    start = (x, y)
    end = _offset(x, y, direction, length)
    mid_x, mid_y = _offset(x, y, direction, length / 2)
    r = 0.4

    if direction in ('up', 'down'):
        sign = 1 if direction == 'up' else -1
        ax.plot([x, x], [y, mid_y - sign * r], '-', color=_COLOR, linewidth=_LW)
        ax.plot([x, x], [mid_y + sign * r, end[1]], '-', color=_COLOR, linewidth=_LW)
    else:
        sign = 1 if direction == 'right' else -1
        ax.plot([x, mid_x - sign * r], [y, y], '-', color=_COLOR, linewidth=_LW)
        ax.plot([mid_x + sign * r, end[0]], [y, y], '-', color=_COLOR, linewidth=_LW)

    circle = plt.Circle((mid_x, mid_y), r, fill=False, color=_COLOR, linewidth=_LW)
    ax.add_patch(circle)
    # ~ 記号
    t = np.linspace(-0.2, 0.2, 30)
    ax.plot(mid_x + t, mid_y + 0.1 * np.sin(t * 15), '-', color=_COLOR, linewidth=1.5)

    if label:
        px, py = _perp_offset(direction, label_offset)
        if label_side == 'right':
            px, py = -px, -py
        draw_label(ax, mid_x - px, mid_y - py, label,
                   ha='right' if label_side == 'left' else 'left')

    return start, end

def draw_source_current(ax, x, y, direction='up', label='', length=2.0, label_side='left', label_offset=0.5):
    """電流源を描画（丸に↑）"""
    start = (x, y)
    end = _offset(x, y, direction, length)
    mid_x, mid_y = _offset(x, y, direction, length / 2)
    r = 0.4

    if direction in ('up', 'down'):
        sign = 1 if direction == 'up' else -1
        ax.plot([x, x], [y, mid_y - sign * r], '-', color=_COLOR, linewidth=_LW)
        ax.plot([x, x], [mid_y + sign * r, end[1]], '-', color=_COLOR, linewidth=_LW)
    else:
        sign = 1 if direction == 'right' else -1
        ax.plot([x, mid_x - sign * r], [y, y], '-', color=_COLOR, linewidth=_LW)
        ax.plot([mid_x + sign * r, end[0]], [y, y], '-', color=_COLOR, linewidth=_LW)

    circle = plt.Circle((mid_x, mid_y), r, fill=False, color=_COLOR, linewidth=_LW)
    ax.add_patch(circle)
    # 矢印
    arrow_len = 0.25
    if direction in ('up', 'down'):
        sign = 1 if direction == 'up' else -1
        ax.annotate('', xy=(mid_x, mid_y + sign * arrow_len),
                     xytext=(mid_x, mid_y - sign * arrow_len),
                     arrowprops=dict(arrowstyle='->', color=_COLOR, lw=_LW))
    else:
        sign = 1 if direction == 'right' else -1
        ax.annotate('', xy=(mid_x + sign * arrow_len, mid_y),
                     xytext=(mid_x - sign * arrow_len, mid_y),
                     arrowprops=dict(arrowstyle='->', color=_COLOR, lw=_LW))

    if label:
        px, py = _perp_offset(direction, label_offset)
        if label_side == 'right':
            px, py = -px, -py
        draw_label(ax, mid_x - px, mid_y - py, label,
                   ha='right' if label_side == 'left' else 'left')

    return start, end

def draw_meter(ax, x, y, label='V', size=0.35):
    """メーター（丸囲み文字）"""
    circle = plt.Circle((x, y), size, fill=False, color=_COLOR, linewidth=_LW)
    ax.add_patch(circle)
    draw_label(ax, x, y, label, fontsize=12, fontweight='bold')
    return (x, y)

def draw_led(ax, x, y, direction='down', label='', length=1.5, label_side='left', label_offset=0.5):
    """LEDを描画（ダイオード + 矢印2本）"""
    start, end = draw_diode(ax, x, y, direction, label, length, label_side, label_offset)
    mid_x, mid_y = _offset(x, y, direction, length / 2)
    # 光の矢印
    arrow_size = 0.15
    if direction in ('up', 'down'):
        for dx in [0.3, 0.5]:
            ax.annotate('', xy=(mid_x + dx + arrow_size, mid_y + arrow_size),
                         xytext=(mid_x + dx, mid_y),
                         arrowprops=dict(arrowstyle='->', color=_COLOR, lw=1))
    else:
        for dy in [0.3, 0.5]:
            ax.annotate('', xy=(mid_x + arrow_size, mid_y + dy + arrow_size),
                         xytext=(mid_x, mid_y + dy),
                         arrowprops=dict(arrowstyle='->', color=_COLOR, lw=1))
    return start, end

def draw_transistor_npn(ax, x, y, label='', size=0.8):
    """npnトランジスタを描画。ベース左、コレクタ右上、エミッタ右下を返す"""
    r = size / 2
    # 丸
    circle = plt.Circle((x, y), r, fill=False, color=_COLOR, linewidth=_LW)
    ax.add_patch(circle)
    # ベース線（左→中央縦棒）
    ax.plot([x - r, x - r * 0.3], [y, y], '-', color=_COLOR, linewidth=_LW)
    # 縦棒
    ax.plot([x - r * 0.3, x - r * 0.3], [y - r * 0.5, y + r * 0.5], '-', color=_COLOR, linewidth=_LW + 0.5)
    # コレクタ線
    ax.plot([x - r * 0.3, x + r * 0.5], [y + r * 0.3, y + r * 0.7], '-', color=_COLOR, linewidth=_LW)
    # エミッタ線（矢印付き）
    ax.annotate('', xy=(x + r * 0.5, y - r * 0.7),
                 xytext=(x - r * 0.3, y - r * 0.3),
                 arrowprops=dict(arrowstyle='->', color=_COLOR, lw=_LW))

    # 端子位置
    base = (x - r, y)
    collector = (x + r * 0.5, y + r * 0.7)
    emitter = (x + r * 0.5, y - r * 0.7)

    if label:
        draw_label(ax, x + r + 0.3, y, label, ha='left')

    return base, collector, emitter

def draw_inductor(ax, x, y, direction='right', label='', length=2.0, label_side='top', label_offset=0.5):
    """コイル（インダクタ）を描画。半円のこぶ4個。returns (start, end)"""
    n_hump = 4
    lead = length * 0.2
    body = length * 0.6
    r = body / (2 * n_hump)  # こぶ1個の半径
    t = np.linspace(np.pi, 0, 40)

    start = (x, y)
    end = _offset(x, y, direction, length)

    if direction in ('right', 'left'):
        sign = 1 if direction == 'right' else -1
        # リード線
        ax.plot([x, x + sign * lead], [y, y], '-', color=_COLOR, linewidth=_LW)
        # こぶ4個（上にふくらむ半円）
        for i in range(n_hump):
            cx = x + sign * (lead + (2 * i + 1) * r)
            ax.plot(cx + r * np.cos(t), y + r * np.sin(t), '-', color=_COLOR, linewidth=_LW)
        # リード線
        ax.plot([x + sign * (lead + body), end[0]], [y, y], '-', color=_COLOR, linewidth=_LW)
        if label:
            lx = x + sign * length / 2
            ly = y + (label_offset if label_side == 'top' else -label_offset)
            draw_label(ax, lx, ly, label)
    else:
        sign = 1 if direction == 'up' else -1
        ax.plot([x, x], [y, y + sign * lead], '-', color=_COLOR, linewidth=_LW)
        # こぶ4個（右にふくらむ半円）
        for i in range(n_hump):
            cy = y + sign * (lead + (2 * i + 1) * r)
            ax.plot(x + r * np.sin(t), cy + r * np.cos(t), '-', color=_COLOR, linewidth=_LW)
        ax.plot([x, x], [y + sign * (lead + body), end[1]], '-', color=_COLOR, linewidth=_LW)
        if label:
            lx = x + (-label_offset if label_side == 'left' else label_offset)
            ly = y + sign * length / 2
            ha = 'right' if label_side == 'left' else 'left'
            draw_label(ax, lx, ly, label, ha=ha)

    return start, end

def draw_zener(ax, x, y, direction='down', label='', length=1.5, label_side='left', label_offset=0.5):
    """ツェナーダイオードを描画（カソード線の両端に折り返しを付けたZ形バー）。returns (start, end)"""
    start = (x, y)
    end = _offset(x, y, direction, length)
    mid = length / 2
    tri = 0.2
    fold = 0.12  # バー両端の折り返しの長さ

    if direction in ('right', 'left'):
        sign = 1 if direction == 'right' else -1
        mx = x + sign * mid
        bx = mx + sign * tri  # バーの位置
        ax.plot([x, mx - sign * tri], [y, y], '-', color=_COLOR, linewidth=_LW)
        triangle = plt.Polygon(
            [(mx - sign * tri, y - tri), (mx - sign * tri, y + tri), (mx + sign * tri, y)],
            closed=True, fill=True, facecolor=_COLOR, edgecolor=_COLOR)
        ax.add_patch(triangle)
        # Z形バー（縦バー + 両端の折り返し）
        ax.plot([bx, bx], [y - tri, y + tri], '-', color=_COLOR, linewidth=_LW + 0.5)
        ax.plot([bx, bx + sign * fold], [y + tri, y + tri], '-', color=_COLOR, linewidth=_LW + 0.5)
        ax.plot([bx, bx - sign * fold], [y - tri, y - tri], '-', color=_COLOR, linewidth=_LW + 0.5)
        ax.plot([bx, end[0]], [y, y], '-', color=_COLOR, linewidth=_LW)
        if label:
            ly = y + (label_offset if label_side == 'top' else -label_offset)
            draw_label(ax, mx, ly, label)
    else:
        sign = 1 if direction == 'up' else -1
        my = y + sign * mid
        by = my + sign * tri  # バーの位置
        ax.plot([x, x], [y, my - sign * tri], '-', color=_COLOR, linewidth=_LW)
        triangle = plt.Polygon(
            [(x - tri, my - sign * tri), (x + tri, my - sign * tri), (x, my + sign * tri)],
            closed=True, fill=True, facecolor=_COLOR, edgecolor=_COLOR)
        ax.add_patch(triangle)
        # Z形バー（横バー + 両端の折り返し）
        ax.plot([x - tri, x + tri], [by, by], '-', color=_COLOR, linewidth=_LW + 0.5)
        ax.plot([x + tri, x + tri], [by, by + sign * fold], '-', color=_COLOR, linewidth=_LW + 0.5)
        ax.plot([x - tri, x - tri], [by, by - sign * fold], '-', color=_COLOR, linewidth=_LW + 0.5)
        ax.plot([x, x], [my + sign * tri, end[1]], '-', color=_COLOR, linewidth=_LW)
        if label:
            lx = x + (-label_offset if label_side == 'left' else label_offset)
            ha = 'right' if label_side == 'left' else 'left'
            draw_label(ax, lx, my, label, ha=ha)

    return start, end

def draw_switch(ax, x, y, direction='right', label='', length=1.5, open_angle=25, label_side='top', label_offset=0.5):
    """SPSTスイッチ（開状態）を描画。両端に端子点、可動線が斜めに開く。returns (start, end)"""
    lead = length * 0.2
    gap = length - 2 * lead  # 端子間の距離
    rad = np.radians(open_angle)

    start = (x, y)
    end = _offset(x, y, direction, length)

    if direction in ('right', 'left'):
        sign = 1 if direction == 'right' else -1
        t1 = (x + sign * lead, y)
        t2 = (x + sign * (length - lead), y)
        # リード線
        ax.plot([x, t1[0]], [y, y], '-', color=_COLOR, linewidth=_LW)
        ax.plot([t2[0], end[0]], [y, y], '-', color=_COLOR, linewidth=_LW)
        # 可動線（開いた状態）
        bx = t1[0] + sign * gap * np.cos(rad)
        by = y + gap * np.sin(rad)
        ax.plot([t1[0], bx], [y, by], '-', color=_COLOR, linewidth=_LW)
        # 端子点（白抜き）
        for tx, ty in (t1, t2):
            ax.plot(tx, ty, 'o', color=_COLOR, markerfacecolor='white', markersize=6)
        if label:
            lx = x + sign * length / 2
            ly = y + (label_offset if label_side == 'top' else -label_offset)
            draw_label(ax, lx, ly, label)
    else:
        sign = 1 if direction == 'up' else -1
        t1 = (x, y + sign * lead)
        t2 = (x, y + sign * (length - lead))
        ax.plot([x, x], [y, t1[1]], '-', color=_COLOR, linewidth=_LW)
        ax.plot([x, x], [t2[1], end[1]], '-', color=_COLOR, linewidth=_LW)
        bx = x + gap * np.sin(rad)
        by = t1[1] + sign * gap * np.cos(rad)
        ax.plot([x, bx], [t1[1], by], '-', color=_COLOR, linewidth=_LW)
        for tx, ty in (t1, t2):
            ax.plot(tx, ty, 'o', color=_COLOR, markerfacecolor='white', markersize=6)
        if label:
            lx = x + (-label_offset if label_side == 'left' else label_offset)
            ly = y + sign * length / 2
            ha = 'right' if label_side == 'left' else 'left'
            draw_label(ax, lx, ly, label, ha=ha)

    return start, end

def draw_battery(ax, x, y, direction='up', label='', length=2.0, label_side='left', label_offset=0.5):
    """電池記号を描画（長線=+極、短線=−極）。end側が+極。returns (start, end)"""
    start = (x, y)
    end = _offset(x, y, direction, length)
    mid_x, mid_y = _offset(x, y, direction, length / 2)
    sep = 0.12        # 2本の線の中心からのずれ
    long_half = 0.4   # 長線（+極）の半分の長さ
    short_half = 0.18  # 短線（−極）の半分の長さ

    if direction in ('up', 'down'):
        sign = 1 if direction == 'up' else -1
        plus_y = mid_y + sign * sep
        minus_y = mid_y - sign * sep
        ax.plot([x, x], [y, minus_y], '-', color=_COLOR, linewidth=_LW)
        ax.plot([x - short_half, x + short_half], [minus_y, minus_y], '-', color=_COLOR, linewidth=_LW + 1.5)
        ax.plot([x - long_half, x + long_half], [plus_y, plus_y], '-', color=_COLOR, linewidth=_LW)
        ax.plot([x, x], [plus_y, end[1]], '-', color=_COLOR, linewidth=_LW)
    else:
        sign = 1 if direction == 'right' else -1
        plus_x = mid_x + sign * sep
        minus_x = mid_x - sign * sep
        ax.plot([x, minus_x], [y, y], '-', color=_COLOR, linewidth=_LW)
        ax.plot([minus_x, minus_x], [y - short_half, y + short_half], '-', color=_COLOR, linewidth=_LW + 1.5)
        ax.plot([plus_x, plus_x], [y - long_half, y + long_half], '-', color=_COLOR, linewidth=_LW)
        ax.plot([plus_x, end[0]], [y, y], '-', color=_COLOR, linewidth=_LW)

    if label:
        px, py = _perp_offset(direction, label_offset)
        if label_side == 'right':
            px, py = -px, -py
        draw_label(ax, mid_x - px, mid_y - py, label,
                   ha='right' if label_side == 'left' else 'left')

    return start, end

def draw_variable_resistor(ax, x, y, direction='right', label='', length=2.0, label_side='left', label_offset=0.6):
    """可変抵抗を描画（抵抗本体に斜め45°の矢印を貫通させる）。returns (start, end)"""
    start, end = draw_resistor(ax, x, y, direction, label, length, label_side, label_offset)
    mid_x, mid_y = _offset(x, y, direction, length / 2)
    a = 0.35  # 矢印の中心からの長さ
    ax.annotate('', xy=(mid_x + a, mid_y + a),
                 xytext=(mid_x - a, mid_y - a),
                 arrowprops=dict(arrowstyle='->', color=_COLOR, lw=_LW))
    return start, end

def draw_terminal(ax, x, y, label='', label_side='left', size=0.08, label_offset=0.3):
    """白抜き小円の端子（測定端子・入出力端子用）を描画"""
    circle = plt.Circle((x, y), size, fill=True, facecolor='white',
                        edgecolor=_COLOR, linewidth=_LW, zorder=3)
    ax.add_patch(circle)
    if label:
        if label_side == 'left':
            draw_label(ax, x - label_offset, y, label, ha='right')
        elif label_side == 'right':
            draw_label(ax, x + label_offset, y, label, ha='left')
        elif label_side == 'top':
            draw_label(ax, x, y + label_offset, label, va='bottom')
        else:
            draw_label(ax, x, y - label_offset, label, va='top')
    return (x, y)

def draw_current_arrow(ax, x, y, direction='right', label='I', size=0.6, label_side='', label_offset=0.35):
    """電流の向きを示す矢印＋ラベルを描画。(x, y)が矢印の中心。

    注意: 素子本体（特に縦向き抵抗の中央）に重ねて置くと可変抵抗記号に
    誤読されるので、必ず素子から離した配線部の脇に置くこと。
    """
    tail = _offset(x, y, direction, -size / 2)
    head = _offset(x, y, direction, size / 2)
    ax.annotate('', xy=head, xytext=tail,
                 arrowprops=dict(arrowstyle='->', color=_COLOR, lw=1.5))
    if label:
        if direction in ('right', 'left'):
            if label_side == '':
                label_side = 'top'
            ly = y + (label_offset if label_side == 'top' else -label_offset)
            draw_label(ax, x, ly, label)
        else:
            if label_side == '':
                label_side = 'right'
            lx = x + (label_offset if label_side == 'right' else -label_offset)
            ha = 'left' if label_side == 'right' else 'right'
            draw_label(ax, lx, y, label, ha=ha)
    return (x, y)


# ============================================================
# 文字かぶり（ラベルの重なり）の機械検出
# ------------------------------------------------------------
# 目視だと見落とすので、描画済みの図から各ラベルの表示bboxを取り、
# (1) ラベル同士の重なり (2) ラベルbboxを配線・素子線が横切る を検出する。
# 生成のたびに assert_no_overlaps(fig, ax) を呼べば、重なりが1件でも
# あれば例外で止まる（＝重なった図がレポートに載るのを構造的に防ぐ）。
# ============================================================

def _seg_rect_intersect(p0, p1, x0, y0, x1, y1):
    """線分 p0-p1 が軸並行矩形 [x0,x1]×[y0,y1] の内部を通るか。
    端点が矩形内なら True。各辺との交差も見る（Liang-Barsky）。"""
    def inside(px, py):
        return x0 <= px <= x1 and y0 <= py <= y1
    if inside(*p0) or inside(*p1):
        return True
    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, p0[0] - x0), (dx, x1 - p0[0]),
                 (-dy, p0[1] - y0), (dy, y1 - p0[1])):
        if p == 0:
            if q < 0:
                return False
        else:
            r = q / p
            if p < 0:
                if r > t1:
                    return False
                if r > t0:
                    t0 = r
            else:
                if r < t0:
                    return False
                if r < t1:
                    t1 = r
    return t0 <= t1


def find_overlaps(fig, ax, shrink=0.20, min_seg_len=1e-6):
    """描画済みの図で「文字かぶり」を検出し、問題のリストを返す。

    shrink: ラベルbboxを各辺この割合だけ内側に縮めてから判定する
            （素子の脇にラベルを寄せた時に、リード線がbboxの端を
            かすめるだけの正常配置を誤検出しないための余裕）。
    戻り値: [{'kind':'text-text'|'text-line', 'labels':(..), 'label':..}, ...]
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    inv = None  # 使わない
    texts = [t for t in ax.texts if t.get_text().strip()]
    boxes = []
    for t in texts:
        bb = t.get_window_extent(renderer)
        w, h = bb.width, bb.height
        sx, sy = w * shrink, h * shrink
        boxes.append((t.get_text(), bb.x0 + sx, bb.y0 + sy,
                      bb.x1 - sx, bb.y1 - sy))

    problems = []
    # (1) ラベル同士
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            if a[1] < b[3] and b[1] < a[3] and a[2] < b[4] and b[2] < a[4]:
                problems.append({'kind': 'text-text',
                                 'labels': (a[0], b[0])})

    # (2) ラベル bbox を線分が横切る
    for ln in ax.lines:
        xy = ln.get_xydata()
        if len(xy) < 2:
            continue
        disp = ax.transData.transform(xy)
        for txt, x0, y0, x1, y1 in boxes:
            hit = False
            for k in range(len(disp) - 1):
                p0, p1 = disp[k], disp[k + 1]
                if abs(p1[0] - p0[0]) + abs(p1[1] - p0[1]) < min_seg_len:
                    continue
                if _seg_rect_intersect(p0, p1, x0, y0, x1, y1):
                    hit = True
                    break
            if hit:
                problems.append({'kind': 'text-line', 'label': txt})
    return problems


def assert_no_overlaps(fig, ax, shrink=0.20):
    """文字かぶりが1件でもあれば AssertionError で止める。
    生成スクリプトの save_circuit の直前に置く想定。"""
    problems = find_overlaps(fig, ax, shrink=shrink)
    if problems:
        lines = []
        for p in problems:
            if p['kind'] == 'text-text':
                lines.append('  ラベル同士が重なり: %r ↔ %r' % p['labels'])
            else:
                lines.append('  ラベルに線がかぶり: %r' % p['label'])
        raise AssertionError('文字かぶりを検出（%d件）:\n%s'
                             % (len(problems), '\n'.join(lines)))
    return True


if __name__ == '__main__':
    """テスト: 全部品を並べたサンプル画像を生成"""
    fig, ax = new_circuit(figsize=(15, 9))
    ax.set_xlim(-1.5, 15)
    ax.set_ylim(-2.2, 8)

    # 行1: 電源系 + 縦向きコイル
    draw_source_dc(ax, 0, 5.5, 'up', 'DC 10V', length=2)
    draw_source_ac(ax, 3, 5.5, 'up', 'AC 1kHz', length=2)
    draw_source_current(ax, 6, 5.5, 'up', 'I = 1mA', length=2)
    draw_battery(ax, 9, 5.5, 'up', 'E = 1.5V', length=2)
    draw_inductor(ax, 12, 5.5, 'up', 'L = 10mH', length=2, label_side='right')

    # 行2: 受動素子（横向き）
    draw_resistor(ax, 0, 3.5, 'right', 'R = 10 kΩ', label_side='top')
    draw_capacitor(ax, 3, 3.5, 'right', 'C = 100 pF', label_side='top')
    draw_inductor(ax, 5.5, 3.5, 'right', 'L = 10 mH', label_side='top')
    draw_diode(ax, 8.5, 3.5, 'right', 'D (1S953)', label_side='top')
    draw_led(ax, 11, 3.5, 'right', 'LED', label_side='bottom')

    # 行3: 新部品（横向きと縦向き）
    draw_zener(ax, 0, 1.5, 'right', 'Z.D.', label_side='top')
    draw_switch(ax, 2.5, 1.5, 'right', 'S', label_side='top')
    draw_variable_resistor(ax, 5, 1.5, 'right', 'VR', label_side='top')
    draw_zener(ax, 9, 0.75, 'up', 'Z.D.', label_side='right')
    draw_switch(ax, 11, 0.75, 'up', 'S', label_side='right')
    draw_variable_resistor(ax, 13, 0.5, 'up', 'VR', label_side='right')

    # 行4: その他
    draw_meter(ax, 0.5, -1, 'V')
    draw_meter(ax, 2, -1, 'A')
    draw_transistor_npn(ax, 4, -1, '2SC1815')
    draw_gnd(ax, 7, -0.7)
    draw_dot(ax, 8, -1)
    draw_terminal(ax, 9.5, -1, label='P1', label_side='top')
    draw_current_arrow(ax, 11, -1, 'right', 'I')
    draw_wire(ax, [(12.5, -1.5), (14, -1.5), (14, -0.5)])
    draw_label(ax, 13.25, -1.2, 'wire')

    problems = find_overlaps(fig, ax)
    if problems:
        print('文字かぶり検出:', problems)
    else:
        print('文字かぶり: 0件')
    save_circuit(fig, os.path.join(BASE, '.claude', 'skills', 'report', 'circuit_lib_test.png'))
    print('テスト画像生成完了')
