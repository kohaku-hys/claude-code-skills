"""色監査: svg_output 内の全 SVG で使われている HEX 色を集計し、
「3色のみ」ルール（ベース＋メイン＋アクセント）の合否を機械判定する。

判定の考え方:
  - 白/黒/グレー等の無彩色（彩度が低い色）は、まとめて 1 系統（ベース）として数える。
  - 有彩色は「色相」でクラスタリングし、同じ色相の濃淡（tint/shade・opacity違い）は 1 系統に束ねる。
  - 系統数 = 有彩色クラスタ数 ＋（無彩色があれば +1）。これが 3 以下なら PASS。

usage: python color_audit.py <svg_dir>
"""
import sys, os, re, glob
from collections import Counter

NEUTRAL_CHROMA = 20   # max-min がこれ以下なら無彩色（白/黒/グレー）
HUE_TOL = 25          # 有彩色を同一系統とみなす色相の許容差（度）


def rgb(hexv):
    return tuple(int(hexv[i:i + 2], 16) for i in (1, 3, 5))


def hue_of(r, g, b):
    mx, mn = max(r, g, b), min(r, g, b)
    c = mx - mn
    if c == 0:
        return None  # 無彩色
    if mx == r:
        h = ((g - b) / c) % 6
    elif mx == g:
        h = (b - r) / c + 2
    else:
        h = (r - g) / c + 4
    return h * 60.0


def hue_dist(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else "."
    c = Counter()
    for f in glob.glob(os.path.join(d, "*.svg")):
        s = open(f, encoding="utf-8").read()
        for h in re.findall(r"#[0-9A-Fa-f]{6}", s):
            c[h.upper()] += 1

    if not c:
        print("SVG に HEX 色が見つかりません: %s" % d)
        return

    for hexv, n in c.most_common():
        print("%s : %d" % (hexv, n))
    print("-- distinct colors: %d" % len(c))

    # 分類
    neutrals, chroma_hues = [], []  # chroma_hues: (hue, hexv, count)
    for hexv, n in c.items():
        r, g, b = rgb(hexv)
        if max(r, g, b) - min(r, g, b) <= NEUTRAL_CHROMA:
            neutrals.append(hexv)
        else:
            chroma_hues.append((hue_of(r, g, b), hexv, n))

    # 有彩色を色相でクラスタリング（使用回数の多い色を代表に）
    chroma_hues.sort(key=lambda x: -x[2])
    clusters = []  # 各要素: {"hue": 代表色相, "members": [hexv,...]}
    for hue, hexv, n in chroma_hues:
        for cl in clusters:
            if hue_dist(hue, cl["hue"]) <= HUE_TOL:
                cl["members"].append(hexv)
                break
        else:
            clusters.append({"hue": hue, "members": [hexv]})

    families = len(clusters) + (1 if neutrals else 0)

    print("-- 系統: 無彩色ベース %s / 有彩色 %d系統" %
          ("あり(1)" if neutrals else "なし(0)", len(clusters)))
    if neutrals:
        print("   [無彩色] %s" % " ".join(sorted(neutrals)))
    for i, cl in enumerate(clusters, 1):
        print("   [有彩%d 色相~%d°] %s" % (i, round(cl["hue"]), " ".join(sorted(cl["members"]))))

    if families <= 3:
        print("3色ルール: PASS （合計 %d 系統 ≤ 3）" % families)
    else:
        over = families - 3
        print("3色ルール: WARN （合計 %d 系統 ＞ 3。%d 系統ぶんの色相が多い）" % (families, over))
        print("  → 増えた色相を既存3色（ベース/メイン/アクセント）の濃淡に寄せてから出す。")


if __name__ == "__main__":
    main()
