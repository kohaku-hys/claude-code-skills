# -*- coding: utf-8 -*-
"""motion.py — pptx に「動き」（アニメーション・画面切り替え）を後から足す。/slide-gen の道具箱。

なぜ存在するか：ppt-master の pptx_animations は「出てくる」効果（フェード等）と普通の画面切り替え
だけで、軌跡で動かす・拡大/収縮・回転・自動で戻す・繰り返し・変形 が無い。2026-10-13 本人
「手が動くスライドを作れるようになりたい」「自分の pptx に動きを付ける」「/slide-gen に足す」。
ppt-master で作ったデッキ（作者の改造版の ppt-master なら SVG の id が図形の名前になる。上流では名前が付かないので
list で名前を見て #ID・text: で指す）にも、手で作った pptx にも使える。
毎回、PowerPoint で同じ動きを自分で付ける手順をノート欄と「_動きの作り方.md」に残す（本人を育てる）。

使い方（python は 3.9 以上・python-pptx と lxml が要る。verify は pywin32・Pillow・ffmpeg も）：
  py -3 motion.py list   <deck.pptx>                         スライドごとの図形の名前・種類・位置・文字
  py -3 motion.py apply  <deck.pptx> <spec.json> -o <out.pptx> [--replace]
  py -3 motion.py verify <deck.pptx> [--fps 4]               動画に書き出し、コマ送りの一覧 PNG を作る

spec.json の形（長さは cm、時間は秒）：
  {"slides": [
     {"slide": 1,
      "transition": "morph",          省略可。morph / fade / push / wipe / none
      "transition_sec": 1.5,
      "clicks": [                     1つの [ ] が1回のクリック。先頭が「クリック時」、残りは「直前の動作と同時」
        [ {"target": "hand",   "effect": "move",  "dx_cm": 3, "sec": 1, "back": true, "repeat": 3},
          {"target": "spring", "effect": "scale", "x": 74, "y": 100, "sec": 1, "back": true, "repeat": 3} ],
        [ {"target": "card1", "effect": "fade"}, {"target": "badge1", "effect": "fade"} ]
      ]}
  ]}
  - 最初の [ ] に {"auto": true} を入れた dict を置くと、クリックせずにスライドが出たら始まる
    （例 [{"auto": true}, {"target": "wave", "effect": "move", "dx_cm": -30, "sec": 4, "repeat": "loop"}]）
  - target：図形の名前（"!!" の有無は問わない）／"#12"（図形の ID）／"text:結論"（その文字を含む図形）
  - effect：
      出る   appear / fade / wipe（dir: left・right・up・down＝その向きから）/ fly（dir 同じ）
      消える fade_out / disappear
      強調   scale（x・y は %。両方同じ／片方 100 のどちらか）/ spin（deg。負は反時計回り）
      動く   move（dx_cm・dy_cm）/ path（points_cm: [[dx,dy], ...] 出発点からの折れ線）
             2つ目以降の軌跡は from_cm: [x, y]（前の軌跡の終点＝元の位置からのずれ）を書く。PowerPoint は
             軌跡を元の位置から始めるので、書かないと図形が元の位置へ跳んで戻る（2026-10-15 実証）
  - 共通：sec（継続時間）・delay（遅延）・back（自動的に元に戻す）・repeat（回数か "loop"）・smooth（true で滑らかに開始/終了）
  - --replace を付けないと、既にある動きの後ろに足す
  - 動きの予算（2026-10-15 本人「動きができすぎてる」「1つのスライドに1つ伝えたいことを」）：1枚のクリックは2回まで・
    1回のクリックで動く物は2つまで・自動で繰り返す動きは1つまでが既定。クリック4回以上／1クリックで4つ以上／繰り返し2つ以上は
    止まる（3回・3つ・繰り返し1つは注意だけ）。数字は pptx_check.py の BUDGET。どうしても要る枚だけ、その枚に
    "busy": "理由" を書くと通り、理由がノートと「_動きの作り方.md」に残る（pptx_check もその枚は注意に下げる）

既知の限界：「直前の動作の後」は使わず delay で代える／グループの中の図形は動かせない（PowerPoint と同じ）。
"""
from __future__ import annotations

import argparse
import copy
import glob
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pptx_check import BUSY_MARK, budget_issues, motion_budget  # noqa: E402  動きの予算は pptx_check と同じ数字

EMU_PER_CM = 360000
NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
}
P = NS["p"]
NOTE_HEAD = "【動きの作り方】"
NOTE_TAIL = "【動きの作り方ここまで】"
GENERIC = re.compile(r"^(Group|TextBox|Image|Picture|Rectangle|Line|Freeform|Oval|Shape|Connector|"
                     r"図|テキスト ボックス|正方形/長方形|グループ化|楕円|直線コネクタ|フリーフォーム)\s*\d*$")

ENTR = {"appear": 1, "fly": 2, "fade": 10, "wipe": 22}
EXIT = {"disappear": 1, "fade_out": 10}
EMPH = {"scale": 6, "spin": 8}
PATH = {"move", "path"}
ALL_EFFECTS = set(ENTR) | set(EXIT) | set(EMPH) | PATH
DIR_WIPE = {"left": (8, "wipe(left)"), "right": (2, "wipe(right)"), "up": (1, "wipe(up)"), "down": (4, "wipe(down)")}
DIR_FLY = {"left": (8, "0-#ppt_w/2", "#ppt_y"), "right": (2, "1+#ppt_w/2", "#ppt_y"),
           "up": (1, "#ppt_x", "0-#ppt_h/2"), "down": (4, "#ppt_x", "1+#ppt_h/2")}
DIR_JA = {"left": "左", "right": "右", "up": "上", "down": "下"}
UI_NAME = {"appear": "［表示］", "fade": "［フェード］", "wipe": "［ワイプ］", "fly": "［スライドイン］",
           "fade_out": "［終了］の［フェード］", "disappear": "［終了］の［クリア］",
           "scale": "［強調］の［拡大/収縮］", "spin": "［強調］の［スピン］"}
DEFAULT_SEC = {"appear": 0.0, "fly": 0.5, "fade": 0.5, "wipe": 0.5, "fade_out": 0.5, "disappear": 0.0,
               "scale": 1.0, "spin": 1.0, "move": 1.0, "path": 1.0}


class SpecError(Exception):
    pass


# --------------------------------------------------------------------------- 図形を探す

def top_shapes(slide):
    """アニメーションを付けられる図形（スライド直下だけ。グループの中は対象外）。"""
    return list(slide.shapes)


def shape_kind(shape):
    return shape._element.tag.split("}")[-1]


def shape_text(shape):
    try:
        if shape.has_text_frame:
            return shape.text_frame.text.replace("\n", " ").strip()
    except Exception:
        pass
    return ""


def find_shape(slide, target, slide_no):
    shapes = top_shapes(slide)
    if target.startswith("#"):
        hits = [s for s in shapes if str(s.shape_id) == target[1:]]
    elif target.startswith("text:"):
        key = target[5:]
        hits = [s for s in shapes if key in shape_text(s)]
    else:
        bare = target.lstrip("!")
        hits = [s for s in shapes if s.name == target] or [s for s in shapes if s.name.lstrip("!") == bare]
    if not hits:
        names = ", ".join(f"{s.name}(#{s.shape_id})" for s in shapes)
        raise SpecError(f"{slide_no}枚目に「{target}」が無い。あるのは: {names}")
    if len(hits) > 1:
        raise SpecError(f"{slide_no}枚目の「{target}」が {len(hits)} 個ある。#ID か text: で1つに絞る: "
                        + ", ".join(f"{s.name}(#{s.shape_id})" for s in hits))
    return hits[0]


# --------------------------------------------------------------------------- 効果の XML

class Ids:
    def __init__(self, start):
        self.n = start

    def __call__(self):
        self.n += 1
        return self.n


def _ms(sec):
    return max(1, int(round(float(sec) * 1000)))


def _tgt(spid):
    return f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl>'


def _set_visibility(ids, spid, val, delay_ms=0):
    return (f'<p:set><p:cBhvr><p:cTn id="{ids()}" dur="1" fill="hold"><p:stCondLst><p:cond delay="{delay_ms}"/>'
            f'</p:stCondLst></p:cTn>{_tgt(spid)}<p:attrNameLst><p:attrName>style.visibility</p:attrName>'
            f'</p:attrNameLst></p:cBhvr><p:to><p:strVal val="{val}"/></p:to></p:set>')


def effect_xml(item, spid, node, ids, sw, sh, grp=0):
    """1つの効果の <p:par>。node は clickEffect / withEffect。grp は同じ図形の何番目の動きか（grpId）。
    PowerPoint は同じ図形の動きに同じ grpId があると2つ目以降を捨てる（2026-10-13 くじの数字の「消える」が消えた）。"""
    eff = item["effect"]
    sec = item.get("sec", DEFAULT_SEC[eff])
    dur = _ms(sec) if sec else 1
    delay = _ms(item["delay"]) if item.get("delay") else 0
    attrs = ""
    if item.get("back"):
        attrs += ' autoRev="1"'
    rep = item.get("repeat")
    if rep == "loop":
        attrs += ' repeatCount="indefinite"'
    elif rep and int(rep) > 1:
        attrs += f' repeatCount="{int(rep) * 1000}"'
    if item.get("smooth"):
        attrs += ' accel="50000" decel="50000"'
    elif eff in PATH:
        attrs += ' accel="0" decel="0"'

    if eff in ENTR:
        cls, pid, sub = "entr", ENTR[eff], 0
        body = _set_visibility(ids, spid, "visible")
        if eff == "fade":
            body += (f'<p:animEffect transition="in" filter="fade"><p:cBhvr><p:cTn id="{ids()}" dur="{dur}"/>'
                     f'{_tgt(spid)}</p:cBhvr></p:animEffect>')
        elif eff == "wipe":
            d = item.get("dir", "left")
            sub, flt = DIR_WIPE[d]
            body += (f'<p:animEffect transition="in" filter="{flt}"><p:cBhvr><p:cTn id="{ids()}" dur="{dur}"/>'
                     f'{_tgt(spid)}</p:cBhvr></p:animEffect>')
        elif eff == "fly":
            d = item.get("dir", "left")
            sub, x0, y0 = DIR_FLY[d]
            for attr, v0, v1 in (("ppt_x", x0, "#ppt_x"), ("ppt_y", y0, "#ppt_y")):
                body += (f'<p:anim calcmode="lin" valueType="num"><p:cBhvr additive="base"><p:cTn id="{ids()}" '
                         f'dur="{dur}" fill="hold"/>{_tgt(spid)}<p:attrNameLst><p:attrName>{attr}</p:attrName>'
                         f'</p:attrNameLst></p:cBhvr><p:tavLst><p:tav tm="0"><p:val><p:strVal val="{v0}"/></p:val>'
                         f'</p:tav><p:tav tm="100000"><p:val><p:strVal val="{v1}"/></p:val></p:tav></p:tavLst></p:anim>')
    elif eff in EXIT:
        cls, pid, sub = "exit", EXIT[eff], 0
        body = ""
        if eff == "fade_out":
            body += (f'<p:animEffect transition="out" filter="fade"><p:cBhvr><p:cTn id="{ids()}" dur="{dur}"/>'
                     f'{_tgt(spid)}</p:cBhvr></p:animEffect>')
            body += _set_visibility(ids, spid, "hidden", max(0, dur - 1))
        else:
            body += _set_visibility(ids, spid, "hidden")
    elif eff == "scale":
        cls, pid, sub = "emph", EMPH[eff], 0
        x, y = float(item.get("x", 100)), float(item.get("y", 100))
        body = (f'<p:animScale><p:cBhvr><p:cTn id="{ids()}" dur="{dur}" fill="hold"/>{_tgt(spid)}</p:cBhvr>'
                f'<p:by x="{int(x * 1000)}" y="{int(y * 1000)}"/></p:animScale>')
    elif eff == "spin":
        cls, pid, sub = "emph", EMPH[eff], 0
        deg = float(item.get("deg", 360))
        body = (f'<p:animRot by="{int(deg * 60000)}"><p:cBhvr><p:cTn id="{ids()}" dur="{dur}" fill="hold"/>'
                f'{_tgt(spid)}<p:attrNameLst><p:attrName>r</p:attrName></p:attrNameLst></p:cBhvr></p:animRot>')
    else:  # move / path
        cls, pid, sub = "path", 0, 0
        # from_cm: 2つ目の軌跡は、PowerPoint では図形の元の位置から始まる（前の軌跡の終点から続かない）。
        # 前の軌跡の終点を from_cm に書くと、そこを始点にした軌跡にする（2026-10-15 本人「4枚目の動き座標がおかしい」）
        sx, sy = (float(v) for v in item.get("from_cm", (0, 0)))
        if eff == "move":
            pts = [(sx + float(item.get("dx_cm", 0)), sy + float(item.get("dy_cm", 0)))]
        else:
            pts = [(sx + float(a), sy + float(b)) for a, b in item["points_cm"]]
        fx = [p[0] * EMU_PER_CM / sw for p in pts]
        fy = [p[1] * EMU_PER_CM / sh for p in pts]
        f0x, f0y = sx * EMU_PER_CM / sw, sy * EMU_PER_CM / sh
        start = "M 0 0 " if (sx, sy) == (0, 0) else f"M {f0x:.5f} {f0y:.5f} "
        path = start + " ".join(f"L {a:.5f} {b:.5f}" for a, b in zip(fx, fy)) + " E"
        types = "A" * (len(pts) + 1)
        body = (f'<p:animMotion origin="layout" path="{path}" pathEditMode="relative" rAng="0" ptsTypes="{types}">'
                f'<p:cBhvr><p:cTn id="{ids()}" dur="{dur}" fill="hold"/>{_tgt(spid)}<p:attrNameLst>'
                f'<p:attrName>ppt_x</p:attrName><p:attrName>ppt_y</p:attrName></p:attrNameLst></p:cBhvr>'
                f'<p:rCtr x="{int(fx[-1] * 50000)}" y="{int(fy[-1] * 50000)}"/></p:animMotion>')
    leaf = ids()
    return (f'<p:par><p:cTn id="{leaf}" presetID="{pid}" presetClass="{cls}" presetSubtype="{sub}"{attrs} '
            f'fill="hold" grpId="{grp}" nodeType="{node}"><p:stCondLst><p:cond delay="{delay}"/></p:stCondLst>'
            f'<p:childTnLst>{body}</p:childTnLst></p:cTn></p:par>')


# --------------------------------------------------------------------------- 確かめる

def check_item(item, where):
    eff = item.get("effect")
    if eff not in ALL_EFFECTS:
        raise SpecError(f"{where}: effect「{eff}」は使えない。使えるのは {sorted(ALL_EFFECTS)}")
    if "target" not in item:
        raise SpecError(f"{where}: target が無い")
    if eff in ("wipe", "fly") and item.get("dir", "left") not in DIR_JA:
        raise SpecError(f"{where}: dir は left/right/up/down")
    if eff == "scale":
        x, y = float(item.get("x", 100)), float(item.get("y", 100))
        if not (x == y or x == 100 or y == 100):
            raise SpecError(f"{where}: 拡大/収縮は「縦横同じ %」か「片方 100」だけ（PowerPoint で同じ設定を作れないため）")
    if eff == "path" and not item.get("points_cm"):
        raise SpecError(f"{where}: path には points_cm が要る")
    rep = item.get("repeat")
    if rep not in (None, "loop") and not (isinstance(rep, int) and rep >= 1):
        raise SpecError(f"{where}: repeat は 1 以上の整数か \"loop\"")


# --------------------------------------------------------------------------- 手順の文

def _num(v):
    v = round(float(v), 1)
    return str(int(v)) if v == int(v) else str(v)


def _offset_ja(dx, dy):
    """出発点から見た位置を「右1.2・上0.6cm」の形で言う。"""
    dx, dy = float(dx), float(dy)
    parts = []
    if dx:
        parts.append(f"{'右' if dx > 0 else '左'}{_num(abs(dx))}")
    if dy:
        parts.append(f"{'下' if dy > 0 else '上'}{_num(abs(dy))}")
    return ("・".join(parts) + "cm") if parts else "出発点"


def howto_item(item, name, first, auto, again=False):
    eff = item["effect"]
    sec = item.get("sec", DEFAULT_SEC[eff])
    parts = []
    if eff in ("move", "path"):
        if eff == "move":
            dx, dy = float(item.get("dx_cm", 0)), float(item.get("dy_cm", 0))
            if dy == 0:
                where = f"終点の赤い印を Shift を押しながら{'右' if dx > 0 else '左'}へ約{_num(abs(dx))}cm ドラッグ"
            elif dx == 0:
                where = f"終点の赤い印を Shift を押しながら{'下' if dy > 0 else '上'}へ約{_num(abs(dy))}cm ドラッグ"
            else:
                where = (f"終点の赤い印を{'右' if dx > 0 else '左'}へ約{_num(abs(dx))}cm・"
                         f"{'下' if dy > 0 else '上'}へ約{_num(abs(dy))}cm の位置へドラッグ")
            parts.append(f"「{name}」を選び、［アニメーションの追加］→「アニメーションの軌跡」の［直線］→ {where}")
        else:
            steps = "→".join(f"（{_offset_ja(a, b)}）" for a, b in item["points_cm"])
            parts.append(f"「{name}」を選び、［アニメーションの追加］→「アニメーションの軌跡」の［ユーザー設定パス］で、"
                         f"図形の真ん中をクリックしてから、そこから見て {steps} の点を順にクリックし、最後の点でダブルクリック")
        if item.get("from_cm"):
            fx0, fy0 = item["from_cm"]
            parts.append(f"引いた軌跡全体をドラッグして、始点（緑の三角）を前の軌跡の終点（赤の三角）＝図形の元の位置から"
                         f"（{_offset_ja(fx0, fy0)}）に重ねる（重ねないと、この動きの始めに図形が元の位置へ跳んで戻る）")
    else:
        opt = ""
        if eff in ("wipe", "fly"):
            opt = f" →［効果のオプション］で「{DIR_JA[item.get('dir', 'left')]}から」"
        elif eff == "scale":
            x, y = float(item.get("x", 100)), float(item.get("y", 100))
            if x == y:
                opt = f" → 一覧の行を右クリック→「効果のオプション」の「サイズ」をユーザー設定 {_num(x)}%（両方向）"
            elif y == 100:
                opt = f" → 一覧の行を右クリック→「効果のオプション」の「サイズ」をユーザー設定 {_num(x)}%（横方向）"
            else:
                opt = f" → 一覧の行を右クリック→「効果のオプション」の「サイズ」をユーザー設定 {_num(y)}%（縦方向）"
        elif eff == "spin":
            deg = float(item.get("deg", 360))
            opt = f" → 一覧の行を右クリック→「効果のオプション」の「量」を {_num(abs(deg))}°（{'時計回り' if deg >= 0 else '反時計回り'}）"
        add = "［アニメーションの追加］から" if (again or eff in EXIT or eff in EMPH) else "［アニメーション］の一覧から"
        parts.append(f"「{name}」を選び、{add}{UI_NAME[eff]}{opt}")
    timing = []
    if auto:
        timing.append("開始「直前の動作と同時」（クリックしなくてもスライドが出たら始まる）")
    else:
        timing.append("開始「クリック時」" if first else "開始「直前の動作と同時」")
    if sec:
        timing.append(f"継続時間 {_num(sec)}秒")
    if item.get("delay"):
        timing.append(f"遅延 {_num(item['delay'])}秒")
    rep = item.get("repeat")
    if rep == "loop":
        timing.append("繰り返し「スライドの最後まで」")
    elif rep and int(rep) > 1:
        timing.append(f"繰り返し {int(rep)}回")
    parts.append("、".join(timing))
    if item.get("back"):
        parts.append("一覧の行を右クリック→「効果のオプション」の「効果」タブで「自動的に元に戻す」にチェック")
    if item.get("smooth"):
        half = _num(float(sec) / 2)
        parts.append(f"同じ「効果」タブで「滑らかに開始」「滑らかに終了」を {half}秒")
    return "。".join(parts) + "。"


# --------------------------------------------------------------------------- 画面切り替え

def set_transition(slide, kind, sec):
    from lxml import etree
    sld = slide._element
    for el in list(sld):
        tag = el.tag.split("}")[-1]
        if tag == "transition" or (tag == "AlternateContent" and el.find(".//p:transition", NS) is not None):
            sld.remove(el)
    if kind in (None, "none"):
        return
    ms = _ms(sec)
    if kind == "morph":
        xml = (f'<mc:AlternateContent xmlns:mc="{NS["mc"]}">'
               '<mc:Choice xmlns:p159="http://schemas.microsoft.com/office/powerpoint/2015/09/main" Requires="p159">'
               f'<p:transition xmlns:p="{P}" xmlns:p14="http://schemas.microsoft.com/office/powerpoint/2010/main" '
               f'spd="slow" p14:dur="{ms}"><p159:morph option="byObject"/></p:transition></mc:Choice>'
               f'<mc:Fallback><p:transition xmlns:p="{P}" spd="slow"><p:fade/></p:transition></mc:Fallback>'
               '</mc:AlternateContent>')
    else:
        inner = {"fade": "<p:fade/>", "push": '<p:push dir="u"/>', "wipe": '<p:wipe dir="r"/>'}.get(kind)
        if inner is None:
            raise SpecError(f"transition「{kind}」は使えない（morph / fade / push / wipe / none）")
        xml = f'<p:transition xmlns:p="{P}" spd="med">{inner}</p:transition>'
    el = etree.fromstring(xml)
    anchor = sld.find("p:clrMapOvr", NS)
    if anchor is None:
        anchor = sld.find("p:cSld", NS)
    anchor.addnext(el)


def morph_names(prev, cur):
    """変形の前後で同じ名前の図形に "!!" を付け、PowerPoint に同じ物だと確実に分からせる。"""
    if prev is None:
        return []
    pn = {}
    for s in top_shapes(prev):
        pn.setdefault(s.name.lstrip("!"), []).append(s)
    done = []
    for s in top_shapes(cur):
        bare = s.name.lstrip("!")
        if not bare or GENERIC.match(bare) or len(pn.get(bare, [])) != 1:
            continue
        for x in (pn[bare][0], s):
            x.name = "!!" + bare
        done.append(bare)
    return done


# --------------------------------------------------------------------------- 適用

def build_timing(slide, groups, replace, sw, sh, slide_no):
    from lxml import etree
    sld = slide._element
    timing = sld.find("p:timing", NS)
    if timing is not None and replace:
        sld.remove(timing)
        timing = None
    seq_list = None
    bld = None
    start_id = 2
    next_grp = {}
    if timing is not None:
        main = timing.find(".//p:cTn[@nodeType='mainSeq']", NS)
        if main is None:
            raise SpecError(f"{slide_no}枚目には動画などの別の動きがある。--replace で作り直すか、手で足す")
        seq_list = main.find("p:childTnLst", NS)
        ids_in = [int(e.get("id")) for e in timing.iter("{%s}cTn" % P) if e.get("id")]
        start_id = max(ids_in or [2])
        bld = timing.find("p:bldLst", NS)
        for ctn in timing.iter("{%s}cTn" % P):   # 既にある動きの grpId の続きから振る
            g, tgt = ctn.get("grpId"), ctn.find(".//p:spTgt", NS)
            if g is not None and tgt is not None:
                k = tgt.get("spid")
                next_grp[k] = max(next_grp.get(k, 0), int(g) + 1)
        if groups and groups[0][0].get("auto") and len(seq_list):
            raise SpecError(f"{slide_no}枚目：自動で始まる動き（auto）は、既に動きがあるスライドの後ろには足せない（--replace）")
    ids = Ids(start_id)
    parts = []
    bld_ids = []
    for gi, group in enumerate(groups):
        auto = bool(group and group[0].get("auto"))
        items = [it for it in group if "effect" in it]
        if auto and gi != 0:
            raise SpecError(f"{slide_no}枚目：auto は最初のクリックの組にだけ置ける")
        outer, inner = ids(), ids()
        body = []
        for k, it in enumerate(items):
            shp = it["_shape"]
            node = "withEffect" if (auto or k > 0) else "clickEffect"
            grp = next_grp.get(str(shp.shape_id), 0)
            next_grp[str(shp.shape_id)] = grp + 1
            body.append(effect_xml(it, shp.shape_id, node, ids, sw, sh, grp))
            if shape_kind(shp) == "sp":
                bld_ids.append((shp.shape_id, grp))
        cond = ('<p:cond delay="indefinite"/><p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond>'
                if auto else '<p:cond delay="indefinite"/>')
        parts.append(f'<p:par xmlns:p="{P}"><p:cTn id="{outer}" fill="hold"><p:stCondLst>{cond}</p:stCondLst>'
                     f'<p:childTnLst><p:par><p:cTn id="{inner}" fill="hold"><p:stCondLst><p:cond delay="0"/>'
                     f'</p:stCondLst><p:childTnLst>{"".join(body)}</p:childTnLst></p:cTn></p:par>'
                     f'</p:childTnLst></p:cTn></p:par>')
    if timing is None:
        xml = (f'<p:timing xmlns:p="{P}"><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" '
               'nodeType="tmRoot"><p:childTnLst><p:seq concurrent="1" nextAc="seek"><p:cTn id="2" '
               'dur="indefinite" nodeType="mainSeq"><p:childTnLst/></p:cTn><p:prevCondLst><p:cond evt="onPrev" '
               'delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst><p:nextCondLst><p:cond '
               'evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq>'
               '</p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>')
        timing = etree.fromstring(xml)
        ext = sld.find("p:extLst", NS)
        if ext is not None:
            ext.addprevious(timing)
        else:
            sld.append(timing)
        seq_list = timing.find(".//p:cTn[@nodeType='mainSeq']/p:childTnLst", NS)
    for x in parts:
        seq_list.append(etree.fromstring(x))
    if bld_ids:
        if bld is None:
            bld = etree.SubElement(timing, f"{{{P}}}bldLst")
        have = {(b.get("spid"), b.get("grpId")) for b in bld}
        for s, g in dict.fromkeys(bld_ids):
            if (str(s), str(g)) not in have:
                e = etree.SubElement(bld, f"{{{P}}}bldP")
                e.set("spid", str(s)); e.set("grpId", str(g)); e.set("animBg", "1")


def write_note(slide, lines):
    tf = slide.notes_slide.notes_text_frame
    old = tf.text
    if NOTE_HEAD in old:
        a = old.index(NOTE_HEAD)
        b = old.find(NOTE_TAIL)
        old = (old[:a] + (old[b + len(NOTE_TAIL):] if b >= 0 else "")).rstrip()
    block = "\n".join([NOTE_HEAD] + lines + [NOTE_TAIL])
    tf.text = (old + "\n\n" + block) if old.strip() else block


def apply(pptx, spec, out, replace=False):
    from pptx import Presentation
    prs = Presentation(pptx)
    sw, sh = prs.slide_width, prs.slide_height
    slides = list(prs.slides)
    report, md = [], ["# 動きの作り方", "", f"元のファイル: {os.path.basename(pptx)}", ""]
    for si, s in enumerate(spec.get("slides", [])):
        no = s.get("slide")
        if not isinstance(no, int) or not 1 <= no <= len(slides):
            raise SpecError(f"slides[{si}]: slide は 1〜{len(slides)} の番号")
        slide = slides[no - 1]
        groups = s.get("clicks", [])
        lines = []
        for gi, g in enumerate(groups):
            if not isinstance(g, list):
                raise SpecError(f"{no}枚目 clicks[{gi}] は [ ] で囲む（1つの [ ] が1回のクリック）")
            for k, it in enumerate(g):
                if it.get("auto") and "effect" not in it:
                    continue
                check_item(it, f"{no}枚目 クリック{gi + 1} の {k + 1}個目")
                it["_shape"] = find_shape(slide, str(it["target"]), no)
        renamed = []
        if s.get("transition"):
            if s["transition"] == "morph":
                renamed = morph_names(slides[no - 2] if no >= 2 else None, slide)
            set_transition(slide, s["transition"], s.get("transition_sec", 1.0 if s["transition"] != "morph" else 1.5))
        if groups:
            build_timing(slide, groups, replace, sw, sh, no)
        # 動きの予算（既にある動きも含めて数える）
        over = budget_issues(motion_budget(slide._element), busy=bool(s.get("busy")))
        errs = [m for lv, _, m in over if lv == "ERROR"]
        if errs:
            raise SpecError(f"{no}枚目：動きが多すぎる（{'／'.join(errs)}）。1枚に伝えたいことは1つ＝動きは"
                            "「2クリックまで・1クリックで2つまで・繰り返しは1つまで」が既定。減らすか、"
                            "どうしても要る枚だけ spec のその枚に \"busy\": \"理由\" を書く")
        notes_over = [f"{no}枚目 注意 {c}: {m}" for lv, c, m in over if lv == "WARNING"]
        # 手順の文
        if s.get("transition") == "morph":
            lines.append(f"・画面切り替え：このスライドを選び、［画面切り替え］→［変形］、［期間］{_num(s.get('transition_sec', 1.5))}。"
                         "前のスライドと同じ名前の物が、位置・大きさ・色の違いの分だけ滑って動く"
                         + (f"（同じ物だと確実に分かるよう {', '.join('!!' + r for r in renamed)} の名前を付けた。"
                            "名前は［ホーム］→［配置］→［オブジェクトの選択と表示］で見られる）" if renamed else ""))
        elif s.get("transition") and s["transition"] != "none":
            ja = {"fade": "フェード", "push": "プッシュ", "wipe": "ワイプ"}[s["transition"]]
            lines.append(f"・画面切り替え：［画面切り替え］→［{ja}］")
        n_click = 0
        seen = set()  # 2つ目の動きが付く図形（効果の一覧から選ぶと1つ目と入れ替わる＝2026-10-13 本人がつまずいた）
        for g in groups:
            auto = bool(g and g[0].get("auto"))
            items = [it for it in g if "effect" in it]
            if not auto:
                n_click += 1
            head = "スライドが出たら自動で" if auto else f"クリック{n_click}回目"
            lines.append(f"・{head}（{len(items)}個が同時に動く）" if len(items) > 1 else f"・{head}")
            for k, it in enumerate(items):
                sid = it["_shape"].shape_id
                again = sid in seen
                seen.add(sid)
                lines.append(f"  {k + 1}. " + howto_item(it, it["_shape"].name, k == 0, auto, again))
                if again:
                    lines.append(f"     ※「{it['_shape'].name}」には2つ目の動きなので、必ず［アニメーションの追加］から付ける。"
                                 "上の効果の一覧から選ぶと、1つ目の動きと入れ替わってしまう。"
                                 "アニメーション ウィンドウに「" + it['_shape'].name + "」の行が2本並べば正しい")
        if any(len([i for i in g if "effect" in i]) > 1 for g in groups):
            lines.append("・確かめ方：［アニメーション ウィンドウ］で、番号はクリックの回数。番号の無い行は上の行と同時に動く。"
                         "「すべて再生」でその場で試せる")
        if s.get("busy"):
            lines.append(f"・{BUSY_MARK}：{s['busy']}")
        write_note(slide, lines)
        md += [f"## {no}枚目", ""] + [ln for ln in lines] + [""]
        report.append(f"{no}枚目: クリック {len([g for g in groups if not (g and g[0].get('auto'))])} 回"
                      + (" ＋自動" if any(g and g[0].get("auto") for g in groups) else "")
                      + (f" / 画面切り替え {s['transition']}" if s.get("transition") else "")
                      + (f" / !! を付けた: {', '.join(renamed)}" if renamed else ""))
        report.extend(notes_over)
    prs.save(out)
    md_path = os.path.splitext(out)[0] + "_動きの作り方.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md).rstrip() + "\n")
    return report, md_path


# --------------------------------------------------------------------------- 一覧

def cmd_list(pptx):
    from pptx import Presentation
    prs = Presentation(pptx)
    for i, slide in enumerate(prs.slides, 1):
        sld = slide._element
        n_anim = sum(1 for e in sld.iter("{%s}cTn" % P) if e.get("presetClass"))
        tr = "あり" if (sld.find("p:transition", NS) is not None or sld.find("mc:AlternateContent", NS) is not None) else "なし"
        print(f"=== {i}枚目  動き {n_anim}個  画面切り替え {tr}")
        for s in top_shapes(slide):
            try:
                pos = f"左{s.left / EMU_PER_CM:5.1f} 上{s.top / EMU_PER_CM:5.1f} 幅{s.width / EMU_PER_CM:5.1f} 高{s.height / EMU_PER_CM:5.1f}cm"
            except Exception:
                pos = "位置なし"
            txt = shape_text(s)[:24]
            print(f"  #{s.shape_id:<4} {s.name[:28]:28} {shape_kind(s):12} {pos}  {txt}")


# --------------------------------------------------------------------------- 確かめ（動画→コマ）

def _powerpoint_running():
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq POWERPNT.EXE"], capture_output=True, text=True).stdout
        return "POWERPNT.EXE" in out.upper()
    except Exception:
        return True  # 分からない時は閉じない側に倒す


def _ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    pat = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\*FFmpeg*\**\bin\ffmpeg.exe")
    hits = glob.glob(pat, recursive=True)
    return hits[0] if hits else None


def cmd_verify(pptx, fps=4, sec_per_slide=3):
    import time
    pptx = os.path.abspath(pptx)
    out = os.path.join(os.path.dirname(pptx), os.path.splitext(os.path.basename(pptx))[0] + "_確認")
    os.makedirs(out, exist_ok=True)
    mp4 = os.path.join(out, "動き.mp4")
    import win32com.client
    running = _powerpoint_running()
    pp = win32com.client.Dispatch("PowerPoint.Application")
    pres = pp.Presentations.Open(pptx, ReadOnly=True, WithWindow=False)
    try:
        pres.CreateVideo(mp4, False, sec_per_slide, 720, 15, 70)
        t = 0
        while pres.CreateVideoStatus in (1, 2) and t < 600:
            time.sleep(1); t += 1
        status = pres.CreateVideoStatus
    finally:
        pres.Close()
        if not running:  # 本人が開いている PowerPoint は閉じない
            pp.Quit()
    if status != 3:
        print("動画に書き出せなかった（CreateVideoStatus=%s）" % status)
        return 1
    ff = _ffmpeg()
    if not ff:
        print("VIDEO:", mp4)
        print("ffmpeg が無いのでコマ切り出しは省いた（winget install Gyan.FFmpeg）")
        return 0
    fdir = os.path.join(out, "frames")
    os.makedirs(fdir, exist_ok=True)
    for f in glob.glob(os.path.join(fdir, "*.png")):
        os.remove(f)
    subprocess.run([ff, "-v", "error", "-y", "-i", mp4, "-vf", f"fps={fps},scale=400:-1",
                    os.path.join(fdir, "f_%04d.png")], check=True)
    from PIL import Image, ImageDraw
    fs = sorted(glob.glob(os.path.join(fdir, "f_*.png")))
    if not fs:
        print("コマが取れなかった")
        return 1
    w, h = Image.open(fs[0]).size
    cols = 6
    rows = (len(fs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (w + 4), rows * (h + 4)), "black")
    d = ImageDraw.Draw(sheet)
    for k, f in enumerate(fs):
        x, y = (k % cols) * (w + 4), (k // cols) * (h + 4)
        sheet.paste(Image.open(f).convert("RGB"), (x, y))
        d.text((x + 4, y + h - 14), f"{k / fps:.2f}s", fill="red")
    cp = os.path.join(out, "_コマ送り.png")
    sheet.save(cp)
    shutil.rmtree(fdir, ignore_errors=True)  # 1コマずつの PNG は残さない（一覧と動画だけ残す）
    print("VIDEO:", mp4)
    print("FRAMES:", cp, sheet.size)
    return 0


# --------------------------------------------------------------------------- 入口

def main(argv=None):
    ap = argparse.ArgumentParser(description="pptx に動き（アニメーション・画面切り替え）を足す")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("list"); a.add_argument("pptx")
    b = sub.add_parser("apply"); b.add_argument("pptx"); b.add_argument("spec")
    b.add_argument("-o", "--out", required=True); b.add_argument("--replace", action="store_true")
    c = sub.add_parser("verify"); c.add_argument("pptx"); c.add_argument("--fps", type=int, default=4)
    c.add_argument("--sec", type=float, default=3, help="動きの無いスライドを映す秒数")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if args.cmd == "list":
        cmd_list(args.pptx)
        return 0
    if args.cmd == "verify":
        return cmd_verify(args.pptx, args.fps, args.sec)
    if os.path.abspath(args.pptx) == os.path.abspath(args.out):
        print("元のファイルは上書きしない。-o に版の数字を上げた名前を付ける（例 _v2.pptx）")
        return 2
    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)
    try:
        report, md_path = apply(args.pptx, copy.deepcopy(spec), args.out, args.replace)
    except SpecError as e:
        print("ERROR:", e)
        return 1
    for r in report:
        print(r)
    print("OUT:", os.path.abspath(args.out))
    print("HOWTO:", md_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
