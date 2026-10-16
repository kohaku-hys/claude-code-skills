"""
グラフ描画ライブラリ — 実験レポートのグラフを共通スタイルで描く関数群。
全て白黒（線・マーカー・文字は黒）、背景白、日本語フォント対応。

使用例:
    from graph_lib import *
    fig, ax = new_graph()
    style_axes(ax, '電圧 [V]', '電流 [mA]')
    plot_series(ax, x1, y1, series=0, label='試料1')
    plot_series(ax, x2, y2, series=1, label='試料2')
    add_legend(ax)
    save_graph(fig, 'output.png')

ルールのまとめ:
- グラフタイトルは付けない。軸ラベルは「物理量 [単位]」形式。
- 目盛りは内向きで、上と右の枠にも付ける（理系のグラフの標準）。
- グリッドは横線のみ薄灰色。縦グリッドは引かない
  （記入用の空枠 blank_frame の対数軸だけ例外で縦も引く）。
- 対数軸の目盛りは 10^3 のような指数表記ではなく 1000 のような普通の数字。
- 系列は ●実線 → △破線 → ■一点鎖線 → ◇点線 の順に区別する。
"""
import os
import re
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, NullFormatter
import numpy as np

BASE = os.environ.get("USERPROFILE") or str(Path.home())

# デフォルト設定
_COLOR = 'black'
_FONTSIZE = 11
_DPI = 300
_LW = 1.2               # 線の太さ
_MS = 10                # マーカーの大きさ
_GRID_COLOR = '#CCCCCC' # グリッドの薄灰色
_GRID_LW = 0.6          # グリッドの線の太さ

# 系列ごとのマーカー: ●塗り黒丸 → △白抜き三角 → ■塗り四角 → ◇白抜き菱形
_MARKERS = ['o', '^', 's', 'D']
_FILLED = [True, False, True, False]
# 系列ごとの線種: 実線 → 破線 → 一点鎖線 → 点線
_LINESTYLES = ['-', '--', '-.', ':']


def new_graph(figsize=(6.4, 4.4)):
    """新しいグラフ用キャンバスを作成（フォント等の rcParams もここで設定）"""
    # 英数字は Century、日本語は MS Gothic で描く。
    # フォント名のリストを font.family に直接渡すと、無い文字（漢字など）は
    # 次の候補のフォントに自動で落ちる（font.serif 経由だと落ちないので注意）。
    plt.rcParams['font.family'] = ['Century', 'MS Gothic']
    plt.rcParams['font.serif'] = ['Century', 'MS Gothic']
    plt.rcParams['font.size'] = _FONTSIZE
    plt.rcParams['mathtext.fontset'] = 'cm'
    fig, ax = plt.subplots(1, 1, figsize=figsize)
    return fig, ax


def _plain_number(v, pos=None):
    """対数軸の目盛り用。1000.0 → '1000'、0.001 → '0.001' のように
    指数を使わず普通の数字で表示する"""
    return np.format_float_positional(v, trim='-')


def style_axes(ax, xlabel, ylabel, xscale='linear', yscale='linear'):
    """軸のスタイルを設定する。タイトルは付けない。
    xlabel/ylabel は「物理量 [単位]」の形式の文字列をそのまま渡す。"""
    ax.set_xscale(xscale)
    ax.set_yscale(yscale)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    # 目盛りは内向き、上と右の枠にも付ける
    ax.tick_params(which='both', direction='in', top=True, right=True)
    # 横グリッドだけ薄灰色で引く（縦は引かない）
    ax.grid(axis='y', which='major', color=_GRID_COLOR, linewidth=_GRID_LW)
    ax.set_axisbelow(True)
    # 対数軸の目盛りを 10^3 ではなく 1000 のような表記にする
    fmt = FuncFormatter(_plain_number)
    if xscale == 'log':
        ax.xaxis.set_major_formatter(fmt)
        ax.xaxis.set_minor_formatter(NullFormatter())
    if yscale == 'log':
        ax.yaxis.set_major_formatter(fmt)
        ax.yaxis.set_minor_formatter(NullFormatter())


def plot_series(ax, x, y, series=0, line=True, label=None):
    """測定データの系列を描画する。series は 0 から順に
    ●実線 → △破線 → ■一点鎖線 → ◇点線 と変わる。
    line=False にすると点のみ（測定点だけ打つとき用）。"""
    i = series % len(_MARKERS)
    face = _COLOR if _FILLED[i] else 'white'
    ls = _LINESTYLES[i] if line else 'none'
    ax.plot(x, y, linestyle=ls, color=_COLOR, linewidth=_LW,
            marker=_MARKERS[i], markersize=_MS,
            markerfacecolor=face, markeredgecolor=_COLOR, label=label)


def plot_theory(ax, x, y, label=None):
    """理論曲線を黒実線（マーカー無し）で描画する"""
    ax.plot(x, y, '-', color=_COLOR, linewidth=_LW, label=label)


def add_legend(ax):
    """枠なしの凡例を付ける。1系列だけで凡例が要らないグラフでは呼ばない。"""
    ax.legend(frameon=False)


def blank_frame(xlabel, ylabel, xlim, ylim, xscale='log', yscale='linear',
                figsize=(6.4, 4.4)):
    """データ無しの記入用グラフ枠を作る（プレレポート用）。
    対数軸のときは手書きで記入しやすいように縦グリッドも補助目盛りまで引く。"""
    fig, ax = new_graph(figsize=figsize)
    style_axes(ax, xlabel, ylabel, xscale=xscale, yscale=yscale)
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    if xscale == 'log':
        ax.grid(axis='x', which='both', color=_GRID_COLOR, linewidth=_GRID_LW)
    if yscale == 'log':
        ax.grid(axis='y', which='both', color=_GRID_COLOR, linewidth=_GRID_LW)
    return fig, ax


# ---- 物理量記号の mathtext 変換 ----------------------------------------
# MS Gothic には結合上ドット（U+0307）のグリフが無く V̇ が文字化けするので、
# ドット付き記号は mathtext の \dot{} で描く（過去テーマ5で確立した方式）。

_DOT = '̇'  # 結合上ドット（V̇ の点の部分）

# 記号1文字（英字かギリシャ文字）+ ドット(任意) + _{...} や ^{...} の並び(任意)
_ML_TOKEN = re.compile(
    r'([A-Za-zΑ-ω])(' + _DOT + r'?)((?:[_^]\{[^{}]*\})*)')


def _ml_group(m):
    """_{out} → _{\\mathrm{out}}（下付きは立体にする）。^{2} はそのまま。"""
    kind = m.group(1)
    body = m.group(2)
    if kind == '_':
        return '_{\\mathrm{' + body + '}}'
    return '^{' + body + '}'


def _ml_repl(m):
    base = m.group(1)
    dot = m.group(2)
    groups = m.group(3)
    if not dot and not groups:
        return m.group(0)  # 添字もドットも無いただの文字はそのまま
    s = base
    if dot:
        s = '\\dot{' + base + '}'
    s += re.sub(r'([_^])\{([^{}]*)\}', _ml_group, groups)
    return '$' + s + '$'


_JP_CHARS = re.compile(r'[　-ヿ一-鿿＀-￯]')


def ml(text):
    """物理量記号の簡易記法を matplotlib の mathtext に変換する。
    例: ml('V_{out}') → '$V_{\\mathrm{out}}$'
        ml('x^{2}')   → '$x^{2}$'
        ml('V̇_{in}')  → '$\\dot{V}_{\\mathrm{in}}$'
    '[V]' のような単位はそのまま残るので ml('V̇_{in} [V]') と書ける。

    注意: matplotlib は $...$ を含む文字列全体を mathtext（cm フォント）で
    描くため、日本語を同じ文字列に混ぜると豆腐（□）になる（2026-07-03 実測確認済み）。
    ×: ml('入力電圧 V̇_{in} [V]')  →  ○: ml('V̇_{in} [V]') か '入力電圧 [V]'
    この組合せを渡すと ValueError で止まる（豆腐がレポートに載るのを防ぐ）。"""
    out = _ML_TOKEN.sub(_ml_repl, text)
    if '$' in out and _JP_CHARS.search(out):
        raise ValueError(
            'ml(): 日本語と数式記号($...$)は同じラベル文字列に混ぜられない'
            '（日本語が全部豆腐□になる）。'
            '「V_{out} [V]」だけにするか「出力電圧 [V]」と日本語だけにする。')
    return out


def save_graph(fig, path, dpi=_DPI):
    """グラフを保存する"""
    fig.savefig(path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close(fig)
