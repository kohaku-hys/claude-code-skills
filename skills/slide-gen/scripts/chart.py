"""chart.py — 説得力のあるネイティブSVGチャート断片を「データから計算して」出力する。
ppt-master の手書きSVGに貼る <g> 断片を作る道具（ページ一括生成ではない。出力を手で配置・微調整して使う）。

データジャーナリズムの作法を既定で内蔵：
  ・主役は accent(橙)、その他は primary(青)、基準/平均は ink(黒) で意味を色分け
  ・直接ラベル（凡例を使わない）／0始まりの正直なスケール／降順整列（任意）
  ・benchmark（全国平均など比較線/バー）を足せる＝「全ての数字に比較を」
  ・title と source 行のプレースホルダ

対応 type: hbar（横棒ランキング・比較）／vbar（縦棒）／line（折れ線・推移）／table（データ表）

usage:
  python chart.py <data.json>            # JSONで全部指定（推奨・日本語OK）
  python chart.py <data.json> --out x.svg
JSON 例（hbar）:
{
  "type":"hbar","title":"大都市の漏水率と全国平均（低いほど良い・%）","source":"出典：…",
  "x":300,"y":280,"w":660,"barh":30,"gap":14,"highlight":"福岡市","sort":false,
  "items":[{"label":"福岡市","value":2.6,"note":"← 全国1位"},{"label":"名古屋市","value":2.7}],
  "benchmark":{"label":"全国平均","value":5.0,"display":"約5%"}
}
"""
import sys, json

C = {"primary": "#125E90", "accent": "#E08A2E", "ink": "#14202B",
     "tint": "#EAF4FB", "bg": "#FFFFFF", "muted": "#14202B"}
F = {"jp": "'Yu Gothic','Yu Gothic UI',Meiryo,sans-serif",
     "mono": "Consolas,'Courier New',monospace"}


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def txt(x, y, s, size, fill, *, b=False, anchor="start", mono=False):
    fam = F["mono"] if mono else F["jp"]
    w = ' font-weight="bold"' if b else ""
    a = ' text-anchor="%s"' % anchor if anchor != "start" else ""
    return ('  <text x="%s" y="%s" font-family="%s" font-size="%d" fill="%s"%s%s>%s</text>'
            % (x, y, fam, size, fill, w, a, esc(s)))


def rect(x, y, w, h, fill):
    return '  <rect x="%s" y="%s" width="%s" height="%s" fill="%s" />' % (x, y, w, h, fill)


def hbar(d):
    x = d.get("x", 300); y = d.get("y", 280); w = d.get("w", 660)
    bh = d.get("barh", 30); gap = d.get("gap", 14)
    hi = d.get("highlight"); unit = d.get("unit", "")
    items = list(d["items"])
    if d.get("sort"):
        items.sort(key=lambda it: it["value"])
    bm = d.get("benchmark")
    allv = [it["value"] for it in items] + ([bm["value"]] if bm else [])
    mx = max(allv) * 1.05
    scale = w / mx
    out = ['<g id="chart">']
    if d.get("title"):
        out.append(txt(x, y - 28, d["title"], 22, C["ink"]))
    out.append('  <line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="2" />'
               % (x, y - 12, x, y + len(items + ([1] if bm else [])) * (bh + gap) - gap + 6, C["tint"]))
    cy = y
    rows = items + ([{"label": bm["label"], "value": bm["value"],
                      "display": bm.get("display"), "_bm": True}] if bm else [])
    for it in rows:
        isbm = it.get("_bm"); ishi = (it.get("label") == hi)
        col = C["ink"] if isbm else (C["accent"] if ishi else C["primary"])
        bw = max(2, it["value"] * scale)
        out.append(txt(x - 16, cy + bh - 8, it["label"], 22 if not ishi else 24,
                       col, b=(ishi or isbm), anchor="end"))
        out.append(rect(x, cy, round(bw, 1), bh, col))
        lab = it.get("display") or ("%s%s" % (_fmt(it["value"]), unit))
        out.append(txt(x + bw + 12, cy + bh - 8, lab, 24 if ishi else 22, col,
                       b=(ishi or isbm), mono=True))
        if it.get("note"):
            out.append(txt(x + bw + 110, cy + bh - 8, it["note"], 22, C["accent"], b=True))
        cy += bh + gap
    if d.get("source"):
        out.append(txt(x, cy + 22, d["source"], 16, C["ink"]))
    out.append("</g>")
    return "\n".join(out)


def vbar(d):
    x = d.get("x", 300); y = d.get("y", 480); h = d.get("h", 200)
    bw = d.get("barw", 70); gap = d.get("gap", 40); unit = d.get("unit", "")
    hi = d.get("highlight"); items = list(d["items"])
    mx = max(it["value"] for it in items) * 1.1; scale = h / mx
    out = ['<g id="chart">']
    if d.get("title"):
        out.append(txt(x, y - h - 28, d["title"], 22, C["ink"]))
    out.append('  <line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="2" />'
               % (x - 10, y, x + len(items) * (bw + gap), y, C["tint"]))
    cx = x
    for it in items:
        ishi = (it.get("label") == hi); col = C["accent"] if ishi else C["primary"]
        bhh = max(2, it["value"] * scale)
        out.append(rect(cx, y - bhh, bw, round(bhh, 1), col))
        out.append(txt(cx + bw / 2, y - bhh - 12, "%s%s" % (_fmt(it["value"]), unit), 22, col, b=True, anchor="middle", mono=True))
        out.append(txt(cx + bw / 2, y + 28, it["label"], 20, C["ink"], b=ishi, anchor="middle"))
        cx += bw + gap
    if d.get("source"):
        out.append(txt(x - 10, y + 64, d["source"], 16, C["ink"]))
    out.append("</g>")
    return "\n".join(out)


def line(d):
    x = d.get("x", 300); y = d.get("y", 480); w = d.get("w", 760); h = d.get("h", 200)
    pts = d["items"]; unit = d.get("unit", "")
    vals = [p["value"] for p in pts]; mx = max(vals) * 1.1; mn = min(min(vals) * 0.9, 0)
    sx = w / (len(pts) - 1) if len(pts) > 1 else w
    def py(v): return y - (v - mn) / (mx - mn) * h
    out = ['<g id="chart">']
    if d.get("title"):
        out.append(txt(x, y - h - 28, d["title"], 22, C["ink"]))
    out.append('  <line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="2" />' % (x, y, x + w, y, C["tint"]))
    pth = " ".join(("M" if i == 0 else "L") + " %s %s" % (round(x + i * sx, 1), round(py(p["value"]), 1)) for i, p in enumerate(pts))
    out.append('  <path d="%s" fill="none" stroke="%s" stroke-width="3" />' % (pth, C["primary"]))
    for i, p in enumerate(pts):
        cx = x + i * sx; cyy = py(p["value"])
        hot = p.get("highlight")
        out.append('  <circle cx="%s" cy="%s" r="%s" fill="%s" />' % (round(cx, 1), round(cyy, 1), 7 if hot else 5, C["accent"] if hot else C["primary"]))
        out.append(txt(cx, cyy - 16, "%s%s" % (_fmt(p["value"]), unit), 20, C["accent"] if hot else C["ink"], b=bool(hot), anchor="middle", mono=True))
        out.append(txt(cx, y + 28, p["label"], 18, C["ink"], anchor="middle"))
    if d.get("source"):
        out.append(txt(x, y + 64, d["source"], 16, C["ink"]))
    out.append("</g>")
    return "\n".join(out)


def table(d):
    x = d.get("x", 120); y = d.get("y", 280); cw = d.get("colw", [260, 180, 180])
    rh = d.get("rowh", 48); cols = d["cols"]; rows = d["rows"]; hi = d.get("highlight_row")
    tw = sum(cw)
    out = ['<g id="chart">']
    if d.get("title"):
        out.append(txt(x, y - 24, d["title"], 22, C["ink"]))
    out.append(rect(x, y, tw, rh, C["primary"]))
    cx = x
    for j, c in enumerate(cols):
        anc = "end" if j > 0 else "start"
        tx = cx + (cw[j] - 14 if j > 0 else 14)
        out.append(txt(tx, y + rh - 16, c, 22, C["bg"], b=True, anchor=anc))
        cx += cw[j]
    cy = y + rh
    for r, row in enumerate(rows):
        ishi = (hi is not None and r == hi)
        if ishi:
            out.append(rect(x, cy, tw, rh, C["tint"]))
        elif r % 2 == 1:
            out.append(rect(x, cy, tw, rh, "#F5F8FB"))
        cx = x
        for j, cell in enumerate(row):
            anc = "end" if j > 0 else "start"
            tx = cx + (cw[j] - 14 if j > 0 else 14)
            col = C["accent"] if ishi else C["ink"]
            out.append(txt(tx, cy + rh - 16, cell, 22, col, b=ishi, anchor=anc, mono=(j > 0)))
            cx += cw[j]
        cy += rh
    out.append('  <line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="1" />' % (x, cy, x + tw, cy, C["tint"]))
    if d.get("source"):
        out.append(txt(x, cy + 24, d["source"], 16, C["ink"]))
    out.append("</g>")
    return "\n".join(out)


def _fmt(v):
    return str(int(v)) if float(v) == int(v) else str(v)


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    # color/font override
    C.update(data.get("colors", {}))
    F.update(data.get("fonts", {}))
    fn = {"hbar": hbar, "vbar": vbar, "line": line, "table": table}[data["type"]]
    svg = fn(data)
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
        open(out, "w", encoding="utf-8").write(svg)
        print("wrote " + out)
    print(svg)


if __name__ == "__main__":
    main()
