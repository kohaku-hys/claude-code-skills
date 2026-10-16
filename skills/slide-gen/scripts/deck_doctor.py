#!/usr/bin/env python3
"""
PPT Master - Deck Doctor（提出前一括診断ゲート）

（slide-gen 同梱版。作者が ppt-master のローカルのブランチに足した deck_doctor.py を、上流の ppt-master だけで
 動くように slide-gen の scripts に置いた物。ppt-master のファイルは import せず、標準ライブラリだけで動く）

svg_quality_checker が見る「SVG 単体の健全性」より一段上の、
デッキ全体の整合性と日本語組版の落とし穴を機械検出する第2ゲート。
運用で「毎回手作業・目視で確認していた」以下を自動化する:

  [ERROR]
    E1 ライブ注釈の残留 (data-edit-annotation / data-edit-target / id="_edit_N")
    E2 フッター番号 vs ファイル名接頭辞・総ページ数の不整合（並べ替え事故）
    E3 notes/total.md の見出し数・番号 vs svg_output の枚数・順序の不整合
       （svg_to_pptx はファイル名順にノートを割り当てるためズレると悲惨）
  [WARNING]
    W1 行頭・行末の約物禁則違反と数字割れ（行頭「。」「%」「.9%」等）
    W2 テキストの右端/下端はみ出し（east_asian_width による視覚幅の概算）
    W3 テキスト同士の重なり（行 bbox の交差概算 → 目視「文字かぶり」確認の前捌き）
    W4 大きい見出しの dy 複数行 tspan（PPT 変換で折り返し重なりの実害履歴）
  [WARNING / 話す型検査（delivery=presentation のとき自動有効）]
    T1 オンスライド文字数過多（読むだけスライド化。文字はノートへ逃がす）
       T1x: 100字の目安では人の言葉（「」40字まで）を数えない。150字の停止は全部数える
    T2 小さい文字の本文（20px 未満が多い＝後ろの席から読めない）
    T3 本文行数過多
    T4 テキストだけの枚（視覚アンカー＝図/チャート/写真/大数字 が無い）
    T5 画像が小さすぎる（話す型の図は主役級に大きく）
    T6 大見出し・大数字の不在（最大 font-size が小さい）
  [INFO]
    I1 使用色の棚卸し（HEX 集計 → 3色統一の確認材料）

  [中身の検査（2026-09-28 本人指摘「中身がないというか」）。形の検査より先に走らせ、先に出す]
    C1 証拠の台帳 <project>/brief.json（v2・brief.py が書く）があり、必須8欄が埋まっているか
    C2 結論 P・各理由 R・各具体例 E の枚に証拠が割り当たっているか（P の強い証拠は2件以上）
    C3 証拠の引用が、出典の行（前後2行）に本当にあるか。逐語と書いた物が注記・推測の行から来ていないか
    C4 素材を全部読んだ記録（sources_read）が、素材の実物（行数・'> ' の逐語行の数）と合うか
    C5 選んだ証拠と本人の場面（me.scene）が、実際のスライドかノートに出ているか
    C6 結論の核の語（p_core）が R・E の枚に出てくるか
    R0 独立の照合エージェント（slide-evidence-checker）が PASS を出し、その後に中身が変わっていないか
    R1 初見の読み手（slide-reader）が、ノートも brief も見ずにスライドの文字だけで「誰が・何を・どうした」を
       言い直せたか（PASS）。その後に中身が変わっていないか（2026-10-01 本人「結局何を言いたいのか伝わらない」）
  [話の順番 flow（2026-10-01 本人「② PREP は既定のまま、別の順も選べる」）]
    spec_lock の `flow: chronological|problem|custom <日付> 本人 <理由>` があれば PREP の順番の検査を緩める
    （prep＝最初と最後が P／chronological・problem＝最後が P／custom＝P が1枚以上。check_prep の上のコメント）
  [意味の検査（WARNING。Kiminori Yokoi「AI臭い文章とは何なのか」2026-09-28 の3つの特徴を型で拾う）]
    M1 否定の前振り（短い否定文→短い肯定文）   M2 語を入れ替えた反復（AてからB。BてからA）
    M3 短い語の後の読点で溜める（「前提を、…」）   M4 指す物が書いていない（片方・前者・見出しの頭の指示語）
    M5 比喩の動詞・方向の比喩（〜側に倒す・基準が壊れる・静かに壊れる・時間を溶かす・原因を潰す・深掘り）。
       抽象的な物が主語・目的語の時だけ拾い、人・物・薬・物質・建物の文字どおりの文は拾わない（_metaphor）。
       本人が自分の文で使う語（落とし込む・架け橋・刺さる）だけで当たる文は INFO の「M5参考」（2026-10-01 本人の判断）
    M6 名詞化で止めた見出し（〜化・〜性・〜の向上）   M7 前置きの決まり文句（重要なのは・結論から言うと）
    M8 絵文字   M9 日本語の行の終わりのコロン（「以下の3つ：」で溜めて中身を次の行に回す）
    M10 ダッシュで文を区切る（「速さ—それがすべてだった」）   M11 読点の打ちすぎ（「まず、電源を、入れて、…」）
    （2026-10-01 に足した語と型の一覧は yomiyasu（MIT・Copyright (c) 2026 nanaism）の考え方と語の一覧が元。正規表現はこちらで直した。
     同日の2回目に、3つの検査器で共通の試験集（作者の環境の文章用スキルにある ai_smell_cases.json。このリポジトリには含まれない）に合わせて直した）
  [形の検査（AI っぽい型）]
    F1 最初と最後の P の見出しが同じ文（ERROR）   F2 対句のまとめ文（〜ではなく〜・AよりB・〜て初めて・単なる〜ではない）
    F3 片側だけの縦線（カード＋左の色線・画面の端の帯）   F4 全部の枚が同じ入り方（小ラベル→見出し）
    F5 PREP の札（結論・理由…）の小ラベル   F6 文字も写真も無い飾り（decor）
    F7 R・E の枚に証拠の要素（数字・写真・人の言葉・登録した図表）が0（ERROR）。tspan で行を割った「」も1つの引用と数える
    F8 R・E の枚がスライド＋ノートで200字未満
    Q1 複数行の引用「…」を中央揃えにしている   Q2 左揃えの複数行の引用で、2行目以降を1字下げていない
  [目次（A0〜A3。本人の既定＝全デッキに目次。2026-09-28「最初に目次を入れたい」）]
    A0 表紙・目次・謝辞を除いて4枚以上なのに目次(A)の枚が無い（ERROR。--legacy は WARNING。spec_lock の agenda: none で INFO）
    （目次は表紙の直後。本人が別の枚に決めた時は spec_lock の agenda: at <枚> <日付> 本人 <理由> で INFO。check_prep が見る）
    A1 目次の項目が3〜5個の外   A2 項目が中身の無い見出し語（はじめに・まとめ等。ERROR）
    A3 目次の項目の語が、後の P/R/E の枚に半分も出てこない
  [資料の種類 genre（spec_lock の `- genre: xxx`。未記載は general）ごとの検査。重さは GENRE_SEV の表]
    G1 概要の事実（brief.overview）が表紙・目次・最初の P に出ているか   G2 R/E にデータ（数＋単位）が1つも無い
    G3a 人の言葉の行に出どころ（※の行）が無い   G3b 数字のある R/E の枚に出典（※・出典の行）が無い
    G4 お願い（brief.cta）が最後の P に出ているか・時期・窓口   G5 目的（me.why）がどこにも出ていない
    G7 表紙に報告日が無い   G8 説明の無い英略語   G9 研究の発表に参考文献の枚が無い

Usage:
    python3 scripts/deck_doctor.py <project_dir>     # svg_output/ + notes/total.md を診断
    python3 scripts/deck_doctor.py <svg_dir>         # SVG ディレクトリ直接でも可
    python3 scripts/deck_doctor.py <proj> --json     # 機械可読出力（自動修正ループ用）
    python3 scripts/deck_doctor.py <proj> --strict   # WARNING も exit 1 扱い
    python3 scripts/deck_doctor.py <proj> --talk     # 話す型検査を強制ON（--no-talk で強制OFF）
    python3 scripts/deck_doctor.py <proj> --draft    # 途中の確認用ビルド（R0・R1 の記録を WARNING に下げる）
    python3 scripts/deck_doctor.py <proj> --legacy   # 9/28 以前のデッキの作り直し（C1〜C6・R0・R1・A0・G1・G4a を WARNING に下げる）

Exit code: ERROR あり → 1（--strict 時は WARNING でも 1）／なし → 0
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).parent))
# 端末の文字コードを UTF-8 にする（cp932 の端末で日本語の出力が落ちないように）。作者の版の ppt-master の
# console_encoding.configure_utf8_stdio と同じ処理を、ppt-master を import せずに標準ライブラリでやる
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

SVG_NS = 'http://www.w3.org/2000/svg'

# --- 日本語禁則（wrap_ja.py と同じ思想。ただし箇条書きマーカー用途の「・」は除外） ---
KINSOKU_HEAD = set(
    "、。，．）」』】〉》〕｝!?！？%％‰…"
    "ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮーヵヶ々〜"
)
KINSOKU_TAIL = set("([{｛（「『【《〈〔“‘")
# 行頭が「数字の続き」= 数字割れ（例: 前行末 9 / 行頭 .9%）
NUM_CONT_HEAD = re.compile(r'^[.,．，]?\d')

# 見出し番号の抽出（total_md_split.extract_leading_number 互換）
def extract_leading_number(text):
    if not text:
        return None
    m = re.match(r'^(\d{1,3})', text.strip())
    if m:
        return int(m.group(1))
    low = text.lower().strip()
    m = re.match(r'^(?:slide|page|p)\s*[-_:]?\s*(\d{1,3})', low)
    if m:
        return int(m.group(1))
    m = re.match(r'^第\s*(\d{1,3})\s*[页张枚]', low)
    if m:
        return int(m.group(1))
    return None


def visual_width(s):
    """全角=1.0 / 半角=0.5 の視覚幅（font-size 1.0 基準）。"""
    w = 0.0
    for ch in s:
        w += 1.0 if unicodedata.east_asian_width(ch) in ('W', 'F', 'A') else 0.5
    return w


class Issue:
    def __init__(self, severity, file, message, fix=None):
        self.severity = severity  # ERROR / WARNING / INFO
        self.file = file
        self.message = message
        self.fix = fix

    def to_dict(self):
        d = {'severity': self.severity, 'file': self.file, 'message': self.message}
        if self.fix:
            d['fix'] = self.fix
        return d


class TextLine:
    """<text> から組み立てた描画1行（重なり・はみ出し・禁則の判定単位）。"""
    def __init__(self, x, y, text, font_size, anchor, source_id):
        self.x = x
        self.y = y
        self.text = text
        self.font_size = font_size
        self.anchor = anchor
        self.source_id = source_id  # 同一 <text> 由来の行は重なり判定から除外する

    def bbox(self):
        w = visual_width(self.text) * self.font_size
        if self.anchor == 'middle':
            x0 = self.x - w / 2.0
        elif self.anchor == 'end':
            x0 = self.x - w
        else:
            x0 = self.x
        # ベースライン y から上に約 0.8em・下に約 0.25em
        return (x0, self.y - self.font_size * 0.8, w, self.font_size * 1.05)


def _parse_len(val, default=None):
    if val is None:
        return default
    m = re.match(r'^\s*([+-]?\d*\.?\d+)', str(val))
    return float(m.group(1)) if m else default


def _parse_len_px(val, axis_len, default=0.0):
    """長さを px で返す。"100%" 等のパーセント指定は軸長に対する割合として解決する
    （full-bleed 画像を極小と誤認して T5 が誤報するのを防ぐ）。"""
    if val is None:
        return default
    m = re.match(r'^\s*([+-]?\d*\.?\d+)\s*(%?)', str(val))
    if not m:
        return default
    num = float(m.group(1))
    return num / 100.0 * axis_len if m.group(2) == '%' else num


def _parse_viewbox(root, default_w=1280.0, default_h=720.0):
    """viewBox から (w, h) を返す。壊れた viewBox でもクラッシュしない。"""
    vb = root.get('viewBox')
    if vb:
        parts = vb.replace(',', ' ').split()
        if len(parts) == 4:
            try:
                return float(parts[2]), float(parts[3])
            except ValueError:
                pass
    return default_w, default_h


def extract_lines(svg_path):
    """SVG から描画行のリストを返す。パース不能・transform 付きは黙ってスキップ。"""
    try:
        root = ET.fromstring(svg_path.read_text(encoding='utf-8', errors='replace'))
    except (ET.ParseError, OSError, ValueError):
        return [], None

    vb = root.get('viewBox')
    canvas = None
    if vb:
        parts = vb.replace(',', ' ').split()
        if len(parts) == 4:
            try:
                canvas = (float(parts[2]), float(parts[3]))
            except ValueError:
                canvas = None

    lines = []
    tid = 0
    for text_el in root.iter('{%s}text' % SVG_NS):
        tid += 1
        if text_el.get('transform'):
            continue  # 回転・移動は概算不能
        fs = _parse_len(text_el.get('font-size'), 16.0)
        anchor = text_el.get('text-anchor', 'start')
        tx = _parse_len(text_el.get('x'))
        ty = _parse_len(text_el.get('y'))
        dy_lines = 0
        from_tspan = False
        if tx is None or ty is None:
            # 2026-09-28: x・y を <text> ではなく各 <tspan> に書く組み方（1行＝1 tspan。研修報告 v2 の 03・04）も読む。
            # 前は黙って飛ばしていたので、その <text> の字が T1・F7 などに1字も数えられていなかった
            first = None
            for tsp in text_el:
                if tsp.tag == '{%s}tspan' % SVG_NS:
                    first = tsp
                    break
            if first is None or (text_el.text or '').strip():
                continue
            if tx is None:
                tx = _parse_len(first.get('x'))
            if ty is None:
                ty = _parse_len(first.get('y'))
            if tx is None or ty is None:
                continue
            # W4（dy の複数行の大見出し）の印はこの組み方には付けない＝W4 の出方は前と同じ（読み取る字だけを増やす修正）
            from_tspan = True

        cur_text = text_el.text or ''
        cur_x, cur_y = tx, ty
        cur_fs = fs
        for tsp in text_el:
            if tsp.tag != '{%s}tspan' % SVG_NS:
                continue
            t = (tsp.text or '')
            sx, sy = _parse_len(tsp.get('x')), _parse_len(tsp.get('y'))
            dy = _parse_len(tsp.get('dy'), 0.0)
            tfs = _parse_len(tsp.get('font-size'), cur_fs)
            if sx is not None or sy is not None or dy:
                # 新しい行の開始
                if cur_text.strip():
                    lines.append(TextLine(cur_x, cur_y, cur_text.strip(), cur_fs, anchor, tid))
                cur_x = sx if sx is not None else cur_x
                cur_y = sy if sy is not None else cur_y + (dy or 0.0)
                cur_text = t
                cur_fs = tfs
                dy_lines += 1
            else:
                cur_text += t  # インライン強調（同一行に連結）
            cur_text += (tsp.tail or '')
        if cur_text.strip():
            lines.append(TextLine(cur_x, cur_y, cur_text.strip(), cur_fs, anchor, tid))
        # dy 行数を最後の行群に記録する代わりに text 要素単位の情報として返したいので
        # 呼び出し側判定用に属性として持たせる
        if dy_lines >= 1 and fs >= 28 and not from_tspan:
            lines.append(TextLine(tx, ty, '\x00DYHEAD\x00%d\x00%.0f' % (dy_lines + 1, fs), 0.0, anchor, -tid))
    return lines, canvas


def text_groups(lines):
    """同じ <text> の行を [[TextLine, …], …] にまとめる（出てきた順。Q1・Q2 の引用の組み方の判定用）。"""
    order = []
    groups = {}
    for ln in lines:
        if ln.source_id not in groups:
            order.append(ln.source_id)
            groups[ln.source_id] = []
        groups[ln.source_id].append(ln)
    return [groups[k] for k in order]


def joined_blocks(lines):
    """同じ <text> の行をつないだ文のリスト（出てきた順）。
    tspan で行を割った引用「英語を勉強する／だけで／満足していた」を1つの「」として見るため（2026-09-28 研修報告 v2 の 04）。"""
    return [''.join(ln.text for ln in group) for group in text_groups(lines)]


# ---------------------------------------------------------------- checks ---

def check_annotations_left(svg_files, issues):
    pat = re.compile(r'data-edit-annotation|data-edit-target|id="_edit_\d+"')
    for f in svg_files:
        content = f.read_text(encoding='utf-8', errors='replace')
        hits = pat.findall(content)
        if hits:
            issues.append(Issue(
                'ERROR', f.name,
                'ライブ注釈が残留 (%d 箇所: %s)' % (len(hits), ', '.join(sorted(set(hits))[:3])),
                'check_annotations.py で反映済みか確認 → data-edit-*/id="_edit_N" を除去して再ビルド'))


FOOTER_PATS = [
    re.compile(r'font-weight="bold">\s*(\d{1,2})\s*</tspan>\s*/\s*(\d{1,3})'),
    re.compile(r'>\s*(\d{1,2})\s*/\s*(\d{1,3})\s*<'),
]


def check_footers(svg_files, issues):
    total = len(svg_files)
    found_any = False
    for f in svg_files:
        m = re.match(r'^(\d{1,3})', f.name)
        if not m:
            continue
        nn = int(m.group(1))
        content = f.read_text(encoding='utf-8', errors='replace')
        candidates = []
        for pat in FOOTER_PATS:
            candidates += [(int(a), int(b)) for a, b in pat.findall(content)]
        if not candidates:
            continue
        found_any = True
        if not any(a == nn and b == total for a, b in candidates):
            best = candidates[0]
            issues.append(Issue(
                'ERROR', f.name,
                'フッター番号 %d / %d がファイル接頭辞 %02d・総数 %d と不一致' % (best[0], best[1], nn, total),
                'fix_footers.py <svg_dir> で一括修正（並べ替え後は必須）'))
    if not found_any and total > 1:
        issues.append(Issue('INFO', '(全体)', 'フッター「N / 総数」パターン未検出（フッター無しデッキなら問題なし）'))


def _normalize_title(title):
    """total_md_split.normalize_title 互換（SVG stem とのゆるいマッチ用）。"""
    if not title:
        return ''
    text = re.sub(r'[^0-9A-Za-z一-鿿]+', '_', title.strip())
    return re.sub(r'_+', '_', text).strip('_').lower()


def check_notes(project_dir, svg_files, issues):
    """total_md_split と同じマッチング（先頭番号／タイトル正規化）を再現し、
    ノートが割り当たらない SVG＝そのスライドだけノート無しで出荷される事故を検出。"""
    total_md = None
    for cand in (project_dir / 'notes' / 'total.md', project_dir / 'total.md'):
        if cand.is_file():
            total_md = cand
            break
    if total_md is None:
        issues.append(Issue('INFO', '(notes)', 'notes/total.md なし（ノート無しデッキなら問題なし）'))
        return
    headings = []
    for line in total_md.read_text(encoding='utf-8', errors='replace').splitlines():
        m = re.match(r'^#{1,3}\s+(.+)$', line.strip())
        if m:
            headings.append(m.group(1).strip())

    stems = [f.stem for f in svg_files]
    exact = set(stems)
    norm_map = {}
    num_map = {}
    for s in stems:
        norm_map.setdefault(_normalize_title(s), []).append(s)
        n = extract_leading_number(s)
        if n is not None:
            num_map.setdefault(n, []).append(s)

    assigned = {}
    for h in headings:
        matched = None
        if h in exact:
            matched = h
        else:
            norm = _normalize_title(h)
            if norm in norm_map and len(norm_map[norm]) == 1:
                matched = norm_map[norm][0]
            else:
                n = extract_leading_number(h)
                if n is not None and n in num_map and len(num_map[n]) == 1:
                    matched = num_map[n][0]
                elif norm:
                    cands = [s for s in stems if norm in _normalize_title(s)]
                    if len(cands) == 1:
                        matched = cands[0]
        if matched:
            assigned.setdefault(matched, h)
        elif extract_leading_number(h) is not None:
            issues.append(Issue(
                'WARNING', total_md.name,
                '見出し「%s」がどの SVG にもマッチしない（枚数超過・消し忘れ・番号ズレ）' % h[:40],
                '並べ替え/削除のあとは total.md の「## Slide N:」番号も追従させる'))

    missing = [s for s in stems if s not in assigned]
    if missing:
        issues.append(Issue(
            'ERROR', total_md.name,
            'ノートが割り当たらない SVG が %d 枚: %s（ノート無しのまま PPTX に入る）' % (
                len(missing), ', '.join(missing[:5])),
            'notes/total.md に「## Slide N: タイトル」を枚数分そろえる → total_md_split.py 再実行'))


def check_kinsoku(svg_files, issues):
    for f in svg_files:
        lines, _ = extract_lines(f)
        for ln in lines:
            t = ln.text
            if not t or t.startswith('\x00') or len(t) < 2:
                continue
            head = t[0]
            if head in KINSOKU_HEAD:
                kind = '数字割れ/単位はぐれ' if head in '%％‰.,．，' else '行頭禁則'
                issues.append(Issue(
                    'WARNING', f.name,
                    '%s: 行頭が「%s」(y=%.0f 「%s…」)' % (kind, head, ln.y, t[:14]),
                    'wrap_ja.py --lines N で割り直す（数字+単位は同じ行に）'))
            elif NUM_CONT_HEAD.match(t) and head in '.,．，':
                issues.append(Issue(
                    'WARNING', f.name,
                    '数字割れ: 行頭が「%s」(y=%.0f)' % (t[:6], ln.y),
                    '数値と小数点・単位を同じ行に'))
            if t[-1] in KINSOKU_TAIL:
                issues.append(Issue(
                    'WARNING', f.name,
                    '行末禁則: 行末が開き括弧「%s」(y=%.0f 「…%s」)' % (t[-1], ln.y, t[-14:]),
                    '開き括弧を次行頭へ送る'))


def check_overflow(svg_files, issues, margin=8.0, tolerance=6.0):
    for f in svg_files:
        lines, canvas = extract_lines(f)
        cw, ch = canvas if canvas else (1280.0, 720.0)
        for ln in lines:
            if not ln.text or ln.text.startswith('\x00'):
                continue
            x0, y0, w, h = ln.bbox()
            over_r = (x0 + w) - (cw - margin)
            over_l = margin - x0
            over_b = ln.y - (ch - 4)
            if over_r > tolerance:
                issues.append(Issue(
                    'WARNING', f.name,
                    '右端はみ出し推定 %.0fpx (y=%.0f size=%.0f 「%s…」)' % (over_r, ln.y, ln.font_size, ln.text[:14]),
                    '文字を減らす / font-size を下げる / wrap_ja.py で改行'))
            elif over_l > tolerance and ln.anchor == 'start':
                issues.append(Issue(
                    'WARNING', f.name,
                    '左端はみ出し推定 %.0fpx (y=%.0f 「%s…」)' % (over_l, ln.y, ln.text[:14])))
            if over_b > tolerance:
                issues.append(Issue(
                    'WARNING', f.name,
                    '下端はみ出し推定 %.0fpx (y=%.0f 「%s…」)' % (over_b, ln.y, ln.text[:14])))


def check_overlap(svg_files, issues):
    for f in svg_files:
        lines, _ = extract_lines(f)
        real = [ln for ln in lines if ln.text and not ln.text.startswith('\x00')]
        boxes = [(ln, ln.bbox()) for ln in real]
        reported = 0
        for i in range(len(boxes)):
            if reported >= 4:  # 1枚あたりの報告上限（雪崩防止）
                break
            a, (ax, ay, aw, ah) = boxes[i]
            for j in range(i + 1, len(boxes)):
                b, (bx, by, bw, bh) = boxes[j]
                if a.source_id == b.source_id:
                    continue  # 同一 <text> 内の行同士は除外
                ix = max(0.0, min(ax + aw, bx + bw) - max(ax, bx))
                iy = max(0.0, min(ay + ah, by + bh) - max(ay, by))
                inter = ix * iy
                if inter <= 0:
                    continue
                min_area = min(aw * ah, bw * bh)
                if min_area > 0 and inter / min_area > 0.30:
                    issues.append(Issue(
                        'WARNING', f.name,
                        '文字かぶり疑い: 「%s…」(y=%.0f) × 「%s…」(y=%.0f) 重なり%.0f%%' % (
                            a.text[:10], a.y, b.text[:10], b.y, inter / min_area * 100),
                        'コンタクトシートで目視確認 → 座標をずらす'))
                    reported += 1
                    if reported >= 4:
                        break


def check_dy_headline(svg_files, issues):
    for f in svg_files:
        lines, _ = extract_lines(f)
        for ln in lines:
            if ln.text.startswith('\x00DYHEAD\x00'):
                _, _, nlines, fs = ln.text.split('\x00')
                issues.append(Issue(
                    'WARNING', f.name,
                    '大見出し(size=%s)が dy 複数行 tspan (%s行) — PPT 変換で折り返し重なりの実害履歴あり' % (fs, nlines),
                    '1行 = 1<text> の縦積みに書き換える（wrap_ja.py --svg が鉄則どおり出力する）'))


# ------------------------------------------------- talk-mode (話す型) checks ---

# 話す型の数値基準（skill-memory 実績: 本文32px・1枚20〜30秒・オンスライドは薄く）
# 2026-09-28 本人指摘「文字が小さい・AIくさい・シンプルじゃない」で厳しくし、主要な物を ERROR（build が止まる）にした。
# 数字は slide-gen/references/デザイン品質.md の「最小フォント22px・本文30px+」「読む場所12個まで」に合わせた。
TALK_MAX_CHARS = 100        # 本文総文字数の目安（超過で WARNING）
TALK_HARD_CHARS = 150       # これを超えたら ERROR（読むだけスライド）
TALK_FLOOR_FS = 22.0        # これ未満の本文が1字でもあれば ERROR（最小フォント22px）
TALK_SMALL_FS = 28.0        # これ未満の本文が TALK_SMALL_CHARS を超えたら WARNING（本文は 28〜32px）
TALK_SMALL_CHARS = 30       # 小さめの文字がこの文字数を超えたら警告
TALK_MAX_LINES = 8          # 本文行数の上限目安
TALK_MAX_BLOCKS = 12        # 「読む場所」（<text> 要素）の上限。超えたら ERROR
# 謝辞スライドだけは敬語のまま可（デザイン品質.md「スライドの言葉＝書き言葉」）
THANKS_RE = re.compile(r'ありがとう|謝辞|感謝|Thank', re.IGNORECASE)
DESU_MASU_RE = re.compile(r'(です|ます|ました|ません|でした|でしょう)[。．！!]?$')
# 量産コピー（デザイン品質.md 対策B）。AI が埋め草に使う抽象語。スライドでは具体シーン・数字に置き換える
# HARD＝中身の無い決まり文句（ERROR）。SOFT＝分野によっては普通の語（「次世代エネルギー展」等）なので WARNING
# 2026-10-01: 記事の締めの決まり文句（いかがでしたか・参考になれば幸い・ぜひ〜してみてください）と、言い終えた後に
# 付ける決め台詞（〜というわけだ・〜に他ならない）を足した。どちらも中身を足さずに印象だけを足す＝資料「AI臭い文章とは
# 何なのか」（Kiminori Yokoi・豊洲会 2026-09-28・https://speakerdeck.com/nasuvitz/ai-kusai-bunshou-toha-nanina-no-ka）の特徴(3)。
# 語の一覧は yomiyasu（MIT・Copyright (c) 2026 nanaism）が元で、正規表現はこちらで直した。
# 締めの「ぜひ〜してみてください」は、読み手に試すよう勧める形（〜てみて）で拾う。「ぜひご参加ください」「ぜひ応募して
# ください」のような催しの案内・お願いは、何をするかが書いてあるので拾わない。「〜てみてはいかが」も同じ勧める形で、
# 「試してみては」だけでなく「使ってみては」「読んでみては」も拾う（2026-10-01 試験集の回。前は し＋てみて だけだった）。
# 決め台詞（〜に他ならない・〜というわけだ）は、教科書の書き言葉（「この式はオームの法則にほかならない」）でも使うので、
# build を止める HARD ではなく SOFT（WARNING）に置く（2回目の反証 2026-10-01。親の判断）。
# 「今の時代」は、時代の区分を言う「この地層は今の時代のものではない」（文字どおり）を拾わない。
# 3回目の反証（2026-10-01）で2つ直した:
#   ・「シナジー」は、ゲームの仕組みの名前（グループの企画仕様書「カードのシナジー2倍」）でも使う語なので、分野によっては普通の語＝SOFT へ移した。
#   ・「ぜひ〜てみてください」で HARD に残すのは、何を試すかが書いていない勧め（ぜひ試してみて・ぜひ使ってみて）だけ。
#     ぜひ と てみて の間に「〜を・〜に・〜へ」（目的語・行き先）がある案内（「ぜひ一度足を運んでみてください」「ぜひ一度、八女の茶畑に
#     足を運んでみてください」）は、何をするかが書いてあるので拾わない。前は ぜひ からの字数（8字まで）で分けていて、同じ案内が
#     書き方の長さだけで ERROR になったりならなかったりした（人が書いた地元紹介の作文）
# 4回目（2026-10-01 試験集の追加分）で2つ直した:
#   ・「ぜひ〜てみてください」は何を勧めるかで分ける。記事の締めは、書いた方法・道具を読み手に試させる（試す・使う・活用する）形。
#     催し・場所への誘い（参加・応募・来場・見学・訪れる・足を運ぶ・手に取る・見る）は案内の普通の言い方なので、「てみて」が
#     付いても拾わない（大学の掲示「そんな気持ちがあれば、ぜひ参加してみてください」、人が書いた地元紹介「ぜひ、一度見てみて
#     ください」。前は ERROR で build を止めていた）。動詞の分け方は文章の検査器（作者の環境の jp_ai_check.py）の _INVITE_VERB と同じ
#   ・「〜となれば幸い」「〜に役立てば幸い」も、読み手に向けて役立てば幸いと締める同じ型（「本レポートが今後の学習の一助となれば
#     幸いである」）。助詞の に・と と、なれば・立てば の違いでは分けない（実験レポートの検査器 check_ai_likeness.py の CLOSING_RE と
#     同じ語）。「ご確認いただければ幸いです」は読み手への本当の頼みなので入れない
AI_COPY_INVITE = (r'(?:参加し|応募し|申し込ん|申込み|来場し|見学し|訪れ|訪ね|足を運ん|手に取っ|立ち寄っ|遊びに来|聞きに来|見に来'
                  r'|覗い|のぞい|見)てみて')
AI_COPY_HARD_RE = re.compile(r'今の時代(?!のもの|の物)|無限の可能性|可能性を秘め|新たな価値を|Key Takeaways|^Overview$|'
                             r'いかがで(しょうか|した(でしょう)?か)|さあ、|未来を切り拓く|一緒に未来|'
                             r'(?:参考|一助|助け|役)(?:に|と)(?:なれば|なると|立てば)幸い|役立てば幸い|お役に立てれば(幸い|嬉し)|'
                             r'ぜひ(?![^。]{0,12}?' + AI_COPY_INVITE + r')(?:(?![をにへ])[^。]){0,12}?'
                             r'((て|で)みて|参考に|活用|お試し)[^。]{0,6}?(ください|下さい)|'
                             r'(て|で)みてはいかが')
AI_COPY_SOFT_RE = re.compile(r'を(加速|最適化|実現)|DX推進|次世代の|革新的な|包括的な|多角的な|浮き彫り|シナジー|'
                             r'というわけ(です|だ|である)|に(他|ほか)なら(ない|ず|ぬ)|に(他|ほか)なりません')
# 決まり文句を「使う」のではなく「話題にする」文は拾わない（2回目の反証 2026-10-01）:
#   語の名前として言う「シナジー効果という言葉を習った」・言い換えを論じる「「いかがでしたか」を「…」にしても」・
#   人に聞かれた問いを書く「研修の様子はいかがでしたか、と先生に聞かれた」。
# 「「無限の可能性」を秘めた半導体」のように「」で囲んで使う物は、後ろが「という・を「」でないので拾う
AI_COPY_MENTION_RE = re.compile(r'[^。、「」]{0,6}?(」?(という|のような|って|と(言う|いう))'
                                r'(言葉|語|用語|言い方|表現|フレーズ|ラベル|決まり文句)|」を「|'
                                r'」?[、,]?と[^。]{0,10}?(聞か|聞い|言わ|言っ|尋ね|問わ|質問))')
TALK_MIN_HEADLINE = 36.0    # 大見出し・大数字の最低サイズ
TALK_MIN_IMAGE_RATIO = 0.12 # 画像面積 / キャンバス面積 の下限（図は主役級に）
TALK_ANCHOR_MIN_LINES = 5   # 視覚要素ゼロでもこの行数未満なら許容（薄い枚）
TALK_BIGNUM_FS = 60.0       # これ以上のテキストは「大数字」＝視覚アンカー扱い

SOURCE_PREFIXES = ('出典', '出所', 'Source', 'SOURCE', '©', '(C)', '(c)', '※',
                   'Photo', 'photo', 'イメージ', '注:', '注：')
# T1 の直し方（2026-09-28。「文字を減らす」と「中身」の両立。証拠まで削って空の枚にしない）
T1_FIX = ('削るのは説明の文。証拠（数字・写真・人の言葉・場面）はスライドに残し、なぜ・背景はノートへ。'
          '削った後に証拠が0なら F7 で止まる')
SHORT_QUOTE_RE = re.compile(r'「[^」]{1,38}」')   # 人の言葉（括弧込み40字まで）＝T1 の100字の目安では数えない


def detect_delivery(project_dir):
    """spec_lock.md / design_spec.md から delivery を拾う（無ければ None）。
    キーは大文字小文字非依存（Delivery / DELIVERY / delivery_purpose も可）。
    正本はプロジェクト直下だが、svg_dir を直接渡された場合に備え親dirもフォールバック探索する。"""
    seen = set()
    for base in (project_dir, project_dir.parent):
        if base in seen:
            continue
        seen.add(base)
        for cand in (base / 'spec_lock.md', base / 'design_spec.md'):
            if cand.is_file():
                try:
                    txt = cand.read_text(encoding='utf-8', errors='replace')
                except OSError:
                    continue
                m = re.search(r'delivery(?:[_ ]purpose)?[^\S\n]*[:：][^\S\n]*([A-Za-z_-]+)',
                              txt, re.IGNORECASE)
                if m:
                    return m.group(1).lower()
    return None


def _is_footer_or_source(ln, canvas_h):
    """フッター・出典・脚注・注記は話す型の文字数カウントから除外する。
    ※ 小さいという理由だけでは除外しない（"位置(フッター帯)" か "出典プレフィックス" を要件にする）。
      サイズ単独除外にすると、最悪の"極小文字で読ませる"枚が全検査をすり抜ける逆転が起きるため。"""
    if ln.y > canvas_h - 45:            # フッター帯（ページ番号・出典を置く定位置）
        return True
    t = ln.text
    if re.match(r'^\d{1,3}\s*/\s*\d{1,3}$', t):   # 「N / 総数」
        return True
    if t.startswith(SOURCE_PREFIXES):             # 出典・©・※・イメージ 等
        return True
    return False


def extract_visuals(svg_path):
    """テキスト以外の「視覚アンカーになり得る要素」を概算集計する。
    returns (visual_score, image_areas, canvas_area, nonimage_anchor)
      - visual_score   : 画像込みの総合スコア（T4 のアンカー有無判定に使う）
      - nonimage_anchor: 画像以外にチャート/図形/カード群があるか（T5 が装飾画像で誤報しないための材料）"""
    try:
        root = ET.fromstring(svg_path.read_text(encoding='utf-8', errors='replace'))
    except (ET.ParseError, OSError, ValueError):
        return 0, [], 1280.0 * 720.0, False
    cw, ch = _parse_viewbox(root)
    canvas_area = cw * ch

    nonimage_score = 0
    image_areas = []
    nonbg_rects = 0
    for el in root.iter():
        tag = el.tag.rsplit('}', 1)[-1]
        if tag == 'image':
            w = _parse_len_px(el.get('width'), cw) or 0.0
            h = _parse_len_px(el.get('height'), ch) or 0.0
            if w * h > 0:
                image_areas.append(w * h)
        elif tag in ('circle', 'ellipse', 'polygon', 'polyline', 'line'):
            nonimage_score += 1
        elif tag == 'use':
            nonimage_score += 1
        elif tag == 'path':
            if len(el.get('d') or '') > 30:
                nonimage_score += 1
        elif tag == 'rect':
            w = _parse_len_px(el.get('width'), cw) or 0.0
            h = _parse_len_px(el.get('height'), ch) or 0.0
            area = w * h
            # 全面背景と極小罫線は除外。カード/帯/バーは視覚構造として数える
            if 0.001 * canvas_area < area < 0.9 * canvas_area:
                nonbg_rects += 1
    if nonbg_rects >= 3:
        nonimage_score += 1                 # カード群・バー群は構造あり
    score = nonimage_score + len(image_areas) * 2   # 画像は強い視覚アンカー
    return score, image_areas, canvas_area, nonimage_score > 0


def check_talk_mode(svg_files, issues):
    """話す型（人が発表する）デッキ専用: 図を大きめ・文字を少なめ・読むだけ化の検出。"""
    for f in svg_files:
        lines, canvas = extract_lines(f)
        cw, ch = canvas if canvas else (1280.0, 720.0)
        body = [ln for ln in lines
                if ln.text and not ln.text.startswith('\x00')
                and not _is_footer_or_source(ln, ch)]
        total_chars = sum(len(ln.text) for ln in body)
        small_chars = sum(len(ln.text) for ln in body if ln.font_size < TALK_SMALL_FS)
        tiny = [ln for ln in body if ln.font_size < TALK_FLOOR_FS]
        max_fs = max((ln.font_size for ln in body), default=0.0)
        blocks = len({ln.source_id for ln in body})

        # T1: 文字数過多（読むだけスライド化）。HARD 超は ERROR＝build が止まる
        # T1x（2026-09-28）: 100字の目安では、人の言葉（「」40字まで）を数えない＝「文字を減らす」で証拠まで削らせない。
        # 150字の停止は全部の字を数える
        # 同じ <text> の行はつないでから数える（tspan で割った「」も人の言葉として数える）
        quoted_chars = sum(len(q) for t in joined_blocks(body) for q in SHORT_QUOTE_RE.findall(t))
        warn_chars = total_chars - quoted_chars
        if total_chars > TALK_HARD_CHARS:
            issues.append(Issue(
                'ERROR', f.name,
                '話す型: オンスライド %d 字（上限 %d 字・目安 %d 字以内）＝読むだけスライド' % (
                    total_chars, TALK_HARD_CHARS, TALK_MAX_CHARS),
                T1_FIX))
        elif warn_chars > TALK_MAX_CHARS:
            note = ''
            if quoted_chars:
                note = '・人の言葉「」%d 字を除いて %d 字' % (quoted_chars, warn_chars)
            issues.append(Issue(
                'WARNING', f.name,
                '話す型: オンスライド %d 字とやや多い（目安 %d 字以内%s）' % (total_chars, TALK_MAX_CHARS, note),
                T1_FIX))

        # T2a: 最小フォント割れ（1字でも ERROR）
        if tiny:
            issues.append(Issue(
                'ERROR', f.name,
                '話す型: %dpx 未満の本文がある（最小 %.0fpx・「%s」ほか %d 行）' % (
                    int(TALK_FLOOR_FS), min(ln.font_size for ln in tiny), tiny[0].text[:14], len(tiny)),
                '本文は 28〜32px 以上、どんなに小さくても %dpx。入らない分は削るかノートへ（出典・※注記・フッターは対象外）'
                % int(TALK_FLOOR_FS)))

        # T7: 「読む場所」が多すぎる（ぎちぎち）
        if blocks > TALK_MAX_BLOCKS:
            issues.append(Issue(
                'ERROR', f.name,
                '話す型: 読む場所（テキスト要素）が %d 個（上限 %d 個）＝ぎちぎち' % (blocks, TALK_MAX_BLOCKS),
                '1枚1メッセージに絞る。カード×箇条書き×チップの重ねをやめ、削った内容はノートへ移す'))

        # T8: です・ます調（スライドは書き言葉。謝辞スライドだけ例外）
        if not any(THANKS_RE.search(ln.text) for ln in body):
            polite = [ln.text for ln in body if DESU_MASU_RE.search(ln.text.strip())]
            if polite:
                issues.append(Issue(
                    'ERROR', f.name,
                    '話す型: です・ます調の文 %d 行（「%s」）＝スライドに原稿を貼っている' % (len(polite), polite[0][:18]),
                    '体言止めか終止形（〜する／〜ない）で止める。話し言葉はノートへ'))

        # T2: 小さい文字の本文
        if small_chars > TALK_SMALL_CHARS:
            issues.append(Issue(
                'WARNING', f.name,
                '話す型: %dpx 未満の本文が %d 字（後ろの席から読めない）' % (
                    int(TALK_SMALL_FS), small_chars),
                '本文は 28〜32px 以上に。載せきれない分は削るかノートへ（出典・※注記は小さくて可）'))

        # T3: 行数過多
        if len(body) > TALK_MAX_LINES:
            issues.append(Issue(
                'WARNING', f.name,
                '話す型: 本文 %d 行と多い（目安 %d 行以内）' % (len(body), TALK_MAX_LINES),
                '1枚1メッセージに分割するか、列挙はまとめて図解に置き換える'))

        # T4/T5: 視覚アンカー（大数字テキストもアンカー: フロー図/チャート/大数字/写真）
        score, image_areas, canvas_area, nonimage_anchor = extract_visuals(f)
        has_bignum = max_fs >= TALK_BIGNUM_FS
        if score < 1 and not has_bignum and len(body) >= TALK_ANCHOR_MIN_LINES:
            issues.append(Issue(
                'WARNING', f.name,
                '話す型: テキストだけの枚（図・チャート・写真・アイコンが無い）',
                '1枚1視覚アンカー: 図解/チャート/写真/大数字のどれか1つを主役に置く'))
        # T5 は「画像がその枚の唯一の視覚アンカー候補」のときだけ。チャート/図形/大数字が別にある枚の
        # 小さいロゴ・QR で誤って「主役サイズに拡大」を出さない（確定指摘④）。
        elif (image_areas and not nonimage_anchor and not has_bignum
                and max(image_areas) < TALK_MIN_IMAGE_RATIO * canvas_area):
            issues.append(Issue(
                'WARNING', f.name,
                '話す型: 最大の画像がキャンバスの %.0f%%（唯一の図なら大きく＝%.0f%% 以上が目安）' % (
                    max(image_areas) / canvas_area * 100, TALK_MIN_IMAGE_RATIO * 100),
                '主役の図なら大きく拡大しテキストを削る／装飾（ロゴ・QR）なら気にしなくてよい'))

        # T6: 大見出し・大数字の不在
        if body and max_fs < TALK_MIN_HEADLINE:
            issues.append(Issue(
                'WARNING', f.name,
                '話す型: 最大文字サイズ %.0fpx（大見出し・大数字の視覚アンカーが無い）' % max_fs,
                '言い切りタイトルか主役の数字を %.0fpx 以上で1つ置く' % TALK_MIN_HEADLINE))


PREP_LINE_RE = re.compile(r'^[\s\-*>]*prep[^\S\n]*[:：](.+)$', re.IGNORECASE | re.MULTILINE)
PREP_TOKEN_RE = re.compile(r'([CAPRET])\s*[:=]?\s*(\d+(?:\s*[-〜~]\s*\d+)?(?:\s*,\s*\d+(?:\s*[-〜~]\s*\d+)?)*)')
# F5（2026-09-28）: コロン無しの小ラベル「結論」だけの行も札として拾う（行全体が完全に一致する時だけ。
# 「結論が出るまでの3日間」のような見出しは拾わない。01/02/03 の番号は数えない＝単調さは F4 が拾う）
PREP_LABEL_RE = re.compile(r'^(Point|Reason|Example|PREP|結論[:：]|理由[:：]|具体例[:：]|再結論)'
                           r'|^(結論|理由|具体例|まとめ|再結論|わかったこと)$', re.IGNORECASE)


def parse_prep(project_dir):
    """spec_lock.md / design_spec.md の `prep: C 1 / A 2 / P 3 / R 4-5 / E 6-8 / P 9 / T 10` を
    {スライド番号: 役割} にする。無ければ None。
    C=表紙 A=目次（表紙の直後だけ・1枚） T=謝辞・質疑・参考文献（末尾だけ）。"""
    for base in (project_dir, project_dir.parent):
        for cand in (base / 'spec_lock.md', base / 'design_spec.md'):
            if not cand.is_file():
                continue
            m = PREP_LINE_RE.search(cand.read_text(encoding='utf-8', errors='replace'))
            if not m:
                continue
            roles = {}
            for role, spans in PREP_TOKEN_RE.findall(m.group(1)):
                for span in spans.split(','):
                    nums = [int(x) for x in re.split(r'[-〜~]', span.strip())]
                    for n in range(nums[0], nums[-1] + 1):
                        roles.setdefault(n, []).append(role.upper())
            return roles
    return None


BRIEF_RE = re.compile(r'^[\s\-*>]*brief_confirmed[^\S\n]*[:：][^\S\n]*(\S.*)$', re.IGNORECASE | re.MULTILINE)


def check_brief(project_dir, issues):
    """中身を本人が選択式で決めたか（slide-gen STEP 1-0。2026-09-28 本人提案）。
    抽象的なスライドの元は「中身が決まらないまま作り始めること」なので、確認の記録が無ければ止める。"""
    for base in (project_dir, project_dir.parent):
        for cand in (base / 'spec_lock.md', base / 'design_spec.md'):
            if cand.is_file() and BRIEF_RE.search(cand.read_text(encoding='utf-8', errors='replace')):
                return
    issues.append(Issue(
        'ERROR', '(全体)', '中身の確認（選択式）の記録が spec_lock に無い（brief_confirmed:）',
        'slide-gen STEP 1-0: 聴衆・結論P・理由R・具体例E・してほしいこと を本人に選択式で決めてもらい、'
        'spec_lock に `brief_confirmed: <日付> 選択式` と brief を書く（本人一任ならその旨を書く）'))


def prep_core(seq):
    """PREP の本体（P→R/E→P）の並び: 先頭の表紙 C と、その直後の目次 A（1枚だけ）と、末尾の T を外した物。
    check_prep・check_agenda・C2 の3か所で同じ外し方にする。"""
    core = seq[:]
    while core and core[0] == 'C':
        core.pop(0)
    if core and core[0] == 'A':
        core.pop(0)
    while core and core[-1] == 'T':
        core.pop()
    return core


# 話の順番（flow）。2026-10-01 本人の回答「② PREP は既定のまま残し、別の順を選んだ時は止めない」。
# 元は Kiminori Yokoi「AI臭い文章とは何なのか」（豊洲会 2026-09-28）の「AI臭いスライドは説明の全体の流れを
# AIに固定される。手直しされないと誰が作っても同じような流れになる」。spec_lock に
# `flow: <名前> <日付> 本人 <理由>`（brief.py が書く）が無ければ prep。役割の印（C/A/P/R/E/T）はどの順でも付ける
# （証拠の検査 C2・F7 と意味の検査はこの印で動く）。緩めるのは順番の検査だけ:
#   prep          … 表紙・目次の次と最後（謝辞の前）が P（今までどおり ERROR）
#   chronological … 時系列。最後（謝辞の前）が P であること（結論は最後）だけを求める
#   problem       … 困りごと→原因→対策。対策が結論なので、最後（謝辞の前）が P であることだけを求める
#   custom        … 本人が決めた順。P が1枚以上あることだけを求め、R/E が無いのは WARNING
FLOWS = ('prep', 'chronological', 'problem', 'custom')
FLOW_LINE_RE = re.compile(r'^[\s\-*>]*flow[^\S\n]*[:：][^\S\n]*(\S+)(.*)$', re.IGNORECASE | re.MULTILINE)


def read_flow(project_dir):
    """spec_lock の `flow: chronological 2026-10-01 本人 理由` を (名前, 残り) にする。無ければ ('prep', '')。"""
    for base in (project_dir, project_dir.parent):
        cand = base / 'spec_lock.md'
        if cand.is_file():
            found = FLOW_LINE_RE.findall(cand.read_text(encoding='utf-8', errors='replace'))
            if found:
                name, rest = found[-1]
                return name.strip().lower(), rest.strip()
    return 'prep', ''


def check_prep(project_dir, svg_files, issues):
    """PREP（結論→理由→具体例→結論）で組んだか（2026-09-28 本人指示「PREPを用いるように」）。
    spec_lock の flow が prep 以外なら、順番の検査をその順に合わせて緩める（FLOWS の上のコメント・2026-10-01）。"""
    check_prep_labels(svg_files, issues)
    flow, flow_note = read_flow(project_dir)
    if flow not in FLOWS:
        issues.append(Issue(
            'ERROR', '(全体)', '話の順番 flow「%s」が不明' % flow,
            'spec_lock の flow: 行を %s のどれかにする（brief.py の answers.json の flow で書く）' % ' / '.join(FLOWS)))
        return
    if flow != 'prep':
        issues.append(Issue(
            'INFO', '(全体)', '話の順番 flow=%s（%s）＝PREP の順番の検査を緩めた' % (flow, flow_note or '理由の記載なし'),
            '緩めたのは順番だけ。役割の印（P・R・E）と証拠・意味の検査はそのまま'))
    roles = parse_prep(project_dir)
    if roles is None:
        issues.append(Issue(
            'ERROR', '(全体)', 'PREP の割り当てが spec_lock に無い',
            'spec_lock.md に 1 行: `prep: C 1 / A 2 / P 3 / R 4-5 / E 6-8 / P 9 / T 10`（C=表紙 A=目次 T=謝辞）。'
            '最初に結論(P)・理由(R)・具体例やデータ(E)・最後にもう一度結論(P)'))
        return
    n = len(svg_files)
    dup = sorted(k for k, v in roles.items() if len(v) > 1)
    missing = [i for i in range(1, n + 1) if i not in roles]
    extra = sorted(k for k in roles if k > n or k < 1)
    if dup or missing or extra:
        issues.append(Issue(
            'ERROR', '(全体)',
            'PREP の割り当てが枚数(%d)と合わない（重複 %s / 抜け %s / 範囲外 %s）' % (n, dup, missing, extra),
            '全部の枚にちょうど1つずつ役割を付ける'))
        return
    seq = [roles[i][0] for i in range(1, n + 1)]
    core = prep_core(seq)
    bad_pos = [i + 1 for i, r in enumerate(seq) if r in ('C', 'T')
               and not (all(x == 'C' for x in seq[:i + 1]) or all(x == 'T' for x in seq[i:]))]
    probs = []
    if bad_pos:
        probs.append('C/T が両端以外にある（%s 枚目）' % bad_pos)
    # 目次 A は「先頭の表紙 C の直後に1枚だけ」（2026-09-28）
    n_cover = 0
    while n_cover < len(seq) and seq[n_cover] == 'C':
        n_cover += 1
    a_pos = [i + 1 for i, r in enumerate(seq) if r == 'A']
    if len(a_pos) >= 2:
        probs.append('目次(A)が %d 枚ある（%s 枚目。1枚だけにする）' % (len(a_pos), a_pos))
    elif a_pos and (n_cover == 0 or a_pos[0] != n_cover + 1):
        at = agenda_at(project_dir)
        if n_cover and at and at[0] == a_pos[0] and at[1]:
            issues.append(Issue(
                'INFO', '(全体)', '目次(A)は %d 枚目（spec_lock: agenda: at %d %s）' % (a_pos[0], at[0], at[1]),
                '表紙と目次の間の枚も、役割の印（R・E）どおりに証拠の検査を受ける'))
        else:
            probs.append('目次(A)が表紙(C)の直後にない（%d 枚目。本人が決めた位置なら spec_lock に '
                         'agenda: at %d <日付> 本人 <理由>）' % (a_pos[0], a_pos[0]))
    if flow == 'prep' and (not core or core[0] != 'P'):
        probs.append('表紙・目次の次が結論(P)でない')
    if flow in ('prep', 'chronological', 'problem') and (not core or core[-1] != 'P'):
        probs.append('最後（謝辞の前）が結論(P)でない')
    if flow == 'custom' and 'P' not in core:
        probs.append('結論(P)の枚が1枚も無い')
    # 3枚以下の小さなデッキ（1枚の告知・表紙＋まとめ等）は R/E の枚を持てないので、結論の位置だけを見る
    soft = []
    if len(core) > 3:
        for role, name in (('R', '理由(R)'), ('E', '具体例・データ(E)')):
            if role not in core:
                (soft if flow == 'custom' else probs).append('%sの枚が無い' % name)
    label = 'PREP の順番' if flow == 'prep' else '話の順番（flow=%s）' % flow
    if probs:
        issues.append(Issue(
            'ERROR', '(全体)', '%sが崩れている: ' % label + ' / '.join(probs) + '（並び: %s）' % ' '.join(seq),
            '結論を最初と最後に置き、間を理由と具体例で支える。最後の P は最初の P の言い直し（同じ主張・具体を足して）'
            if flow == 'prep' else '結論(P)を最後（謝辞の前）に置き、理由(R)と具体例・データ(E)の枚に役割の印を付ける'))
    if soft:
        issues.append(Issue(
            'WARNING', '(全体)', '%s: ' % label + ' / '.join(soft) + '（並び: %s）' % ' '.join(seq),
            '本人が決めた順でも、主張を支える枚には R か E の印を付ける（証拠の検査 C2・F7 がこの印で動く）'))


def check_prep_labels(svg_files, issues):
    """PREP の札（「理由：」「Point」、F5 のコロン無しの「結論」）がスライドに見えていないか。
    prep 行の有無に関係なく見る（2026-09-28。prep の無い旧デッキの「結論」の小ラベルも拾う）。"""
    for f in svg_files:
        lines, _ = extract_lines(f)
        lab = [ln.text for ln in lines if ln.text and PREP_LABEL_RE.search(ln.text.strip())]
        if lab:
            issues.append(Issue(
                'WARNING', f.name, 'PREP の札がスライドに出ている: 「%s」' % lab[0][:16],
                'PREP は見えない骨組み。「理由：」「Point」「結論」等の札は書かず、見出しを言い切りの主張にする'))


def check_ai_copy(svg_files, issues, brief=None):
    """量産コピー（AIくさい決まり文句）。話す型／読ませる型を問わず全デッキで見る（2026-09-28）。行ごとに見る。
    2026-10-01: brief.json に逐語の証拠（kind=verbatim）として登録した人の言葉の「」だけは見ない。逐語の証拠（C3）は
    書き換えられないので、先生の言葉「結局は慣れに他ならない」を ERROR で止めない。
    「」を全部外すと「「無限の可能性」を秘めた半導体」が括弧で囲むだけで通るので、外すのは登録した物だけ（反証 2026-10-01）。
    tspan で行を割った「」は、同じ <text> の行を改行でつないで消してから、行に戻して見る（^Overview$ も行ごとのまま）"""
    quotes = verbatim_quotes(brief)
    for f in svg_files:
        lines, _ = extract_lines(f)
        lines = [ln for ln in lines if ln.text and not ln.text.startswith('\x00')]
        texts = []
        for group in text_groups(lines):
            texts.extend(drop_verbatim('\n'.join(ln.text for ln in group), quotes).split('\n'))
        hard = [t for t in texts if copy_hits(AI_COPY_HARD_RE, t)]
        soft = [t for t in texts if copy_hits(AI_COPY_SOFT_RE, t)]
        if hard:
            issues.append(Issue(
                'ERROR', f.name,
                'AIくさい決まり文句: 「%s」（中身の無い抽象コピー）' % hard[0][:24],
                '具体シーン・固有名詞・before/after の数字に置き換える（デザイン品質.md 対策B）'))
        if soft:
            issues.append(Issue(
                'WARNING', f.name,
                'AIくさい語の疑い: 「%s」' % soft[0][:24],
                '固有名詞（展示会名など）なら無視してよい。説明文なら「何が・どれだけ」変わるかの具体に置き換える。'
                '決め台詞（〜に他ならない・〜というわけだ）は消して、言いたい中身をそのまま書く'))


def copy_hits(rx, t):
    """決まり文句の正規表現 rx が行 t で「使われて」いる所（話題にしているだけの所は除く）の一覧。
    「浮き彫り」は、物（木の板・模様）の文では彫刻の文字どおりの意味なので除く（比喩の原理は M5 と同じ M_LITERAL_RE）"""
    out = []
    for m in rx.finditer(t or ''):
        if AI_COPY_MENTION_RE.match(t[m.end():m.end() + 16]):
            continue
        if m.group(0) == '浮き彫り' and M_LITERAL_RE.search(t):
            continue
        out.append(m.group(0))
    return out


# ------------------------------------------ 中身の検査（C1〜C6・R0）の共通部品 ---
# 2026-09-28 本人指摘「中身がないというか」。形（見た目）だけ直しても、結論を証拠が証明していなければ
# 「中身がない」は消えない（Wikipedia『Signs of AI writing』も「兆候だけを直すのは誤り」と書く）。
# そこで brief.py が書く証拠の台帳 <project>/brief.json（v2）を読み、形の検査（F1〜F8）より先に中身を見る。
# 下の関数（正規化・対句・bigram・逐語行の数え方・出典の照合）は brief.py と claims.py も import して使う
# ＝2か所で判定がずれないようにする。

BRIEF_KEYS = ('p', 'p_core', 'p_last', 'r', 'proof', 'me', 'sources_read', 'prep')   # 台帳の必須8欄
STRONG_KINDS = ('verbatim', 'photo', 'number', 'scene')   # 結論 P を支える「強い証拠」（逐語・写真・数字・場面）
NO_QUOTE_KINDS = ('photo', 'diagram', 'table')            # quote が空でもよい種類
LEGACY_BEFORE = '2026-09-28'   # brief_confirmed がこの日より前＝台帳ができる前のデッキ（中身の検査は WARNING に下げる）
SPECULATION_RE = re.compile(r'推測|とみられる|起草|未確認')
# 対句のまとめ文（humanizer-ja 規則11「否定並列構文」・Wikipedia の Negative parallelism）
# 2026-10-01「単なる〜ではない」「〜だけの話ではない」を足した＝言われていない誤解を否定してから主文に入る型
# （Kiminori Yokoi「AI臭い文章とは何なのか」豊洲会 2026-09-28 の特徴(1)。語は yomiyasu（MIT・Copyright (c) 2026 nanaism）が元）。
# 「単なる誤差と判断した」のように否定の無い文は拾わない。「単なる接触不良ではないか」（故障を調べる時の仮説の問い）・
# 「〜ではありませんか」は問いで、誤解を否定する言い切りではないので拾わない（2回目の反証 2026-10-01）。
# 「これは単なるバグではありません」（です・ます調の否定）は拾う。
# 「AよりB」の より は、下の _yori_contrast で別に見る（3回目の反証 2026-10-01）
# 4回目（2026-10-01 試験集の追加分）: 否定の後に読点を打ち、同じ文で言いたいことを言い切る「５Sは単なる職場をきれいにする活動だけ
# ではない、あらゆるビジネスの基本である」（大学の進路指導の配布物）は、主文を直接書いているので拾わない（資料の特徴(1)は
# 「主文を直接書かない」こと）。言い切って文を終える「単なる道具ではない。」・「速度だけではない」は拾う。
# 実験レポートの検査器 check_ai_likeness.py の SIMPLY_NOT_RE（否定の後の読点は外す）と同じ
CONTRAST_RE = re.compile(r'ではなく|じゃなく|だけ(では|じゃ)な(?!いか|い[、,])|て初めて|てはじめて|こそが|こそ、'
                         r'|(単なる[^。、]{1,20}|だけの(話|問題))((では|じゃ)な(?!いか|い[、,])|ではありません(?!か))')
# より には、比べる より（「装置より、人の熱意」）のほかに、出典の より（「表1より、」「図5より、」「式(3)より」「以上より、」）と、
# 手段・原因の「により」がある。出典・手段の より は、どこから言えるかを示す普通の書き言葉（本人の実験レポートは「表N より、」
# 「図N より、」を何十回も使う）なので、対句に数えない。出典は、図・表・式・グラフ・写真（番号付きでもよい）と、前を受ける
# 以上・上記・前述・これ・それ の後の より
YORI_SOURCE_RE = re.compile(r'(?:図|表|式|グラフ|写真)[\s0-9０-９()（）.．\-‐~〜～,，、]*$|(?:以上|上記|前述|これ|それ)$')
# 出典を示す「〜より抜粋」「〜より引用」「〜より作成」（図表の注・資料の出どころ。先生の確認問題「…白書「…」より抜粋」）
YORI_CITE_RE = re.compile(r'(?:抜粋|引用|転載|作成|作図|改変|一部改変|参照|出典)')
# より の後ろが、後に置いた式・図・表を指す語（「定義より次式」「式(3)より次の関係」）。YORI_SOURCE_RE が前を受ける 以上・上記 と
# 図・表・式を見るのと同じ物の、後ろを指す側（7回目 2026-10-01。制御基礎 第2回講義資料 ラプラス変換.pdf）。
# 「旧世代より次世代」の 次世代 は式・図ではないので当たらない
YORI_NEXT_RE = re.compile(r'(?:次|下|以下|下記)の?(?:式|図|表|グラフ|写真)')
# 述語の無い名詞の句（「量」「速さ」「確実さ」「人の熱意」）。「多い4コマ」「早く終わった」のように用言が入る句は含まない
NOUN_PHRASE_RE = re.compile(r'[一-鿿々ァ-ヶーA-Za-z0-9]+さ?(?:の[一-鿿々ァ-ヶーA-Za-z0-9]+さ?)*')
QUOTE_SPAN_RE = re.compile(r'「[^」]*」|『[^』]*』')
QUOTE6_RE = re.compile(r'「[^」]{4,}」|『[^』]{4,}』')     # 括弧込み6字以上の人の言葉（F7）
SRC_RE = re.compile(r'^(.+)[:：](\d+)\s*$')                # 'ファイル名:行'
TEXT_SUFFIXES = ('.md', '.markdown', '.txt', '.csv', '.tsv', '.json', '.log', '')
_NORM_DROP_RE = re.compile(r'[\s「」『』、。，．・,.]')
_JACCARD_DROP_RE = re.compile(r'[\s、。，．・,.!?！？]')
_BOLD_LABEL_RE = re.compile(r'^\s*(?:[-*+]\s*)?\*\*[^*]+\*\*')
_NUM_TOKEN_RE = re.compile(r'\d+(?:[.,]\d+)*[^\s\d、。，．,.・「」『』]?')


def normalize_text(s):
    """照合用の正規化。行頭の '> ' を外し、NFKC にして、空白・かぎ括弧・句読点を消す。"""
    parts = []
    for line in str(s or '').splitlines():
        line = line.strip()
        if line.startswith('>'):
            line = line[1:]
        parts.append(line)
    t = unicodedata.normalize('NFKC', ''.join(parts))
    return _NORM_DROP_RE.sub('', t)


def strip_quotes(s):
    """「…」『…』の中身を消す（人の実際の発言は、対句の検査から外す）。"""
    return QUOTE_SPAN_RE.sub('', s or '')


def verbatim_quotes(brief):
    """brief.json の逐語の証拠（kind=verbatim）の quote を、照合用に正規化した物の集合。"""
    out = set()
    for pr in _proofs(brief or {}):
        q = normalize_text(pr.get('quote'))
        if pr.get('kind') == 'verbatim' and q:
            out.add(q)
    return out


def drop_verbatim(s, quotes):
    """「…」『…』のうち、中身が逐語の証拠（verbatim_quotes の集合）のどれかの一部である物だけを消す。
    登録していない「」は残す（決まり文句を「」で囲むだけで検査を抜けられないように。2026-10-01）。"""
    def repl(m):
        inner = normalize_text(m.group(0))
        if inner and any(inner in q for q in quotes):
            return ''
        return m.group(0)
    return QUOTE_SPAN_RE.sub(repl, s or '')


def has_contrast(s):
    """対句のまとめ文（〜ではなく〜・AよりB・〜て初めて）が入っているか。「」の中は見ない。"""
    t = strip_quotes(s)
    return bool(CONTRAST_RE.search(t)) or _yori_contrast(t)


def _yori_contrast(t):
    """F2 の「AよりB」: 比べる より で、読点で溜めるか、述語を書かずに名詞で言い切る形か（3回目の反証 2026-10-01）。
    ・「装置より、人の熱意だった」「便数よりも、時間帯」（より の後の読点）は拾う
    ・「量より質」「速さより確実さ」（前も後ろも名詞の句だけ＝述語の無い決め台詞の対句）は拾う
    ・「実測値は理論値よりも5%低い」「中央の値よりも大きい時は右を探す」「講義は3倍より多い4コマ」のように、比べた結果を
      数・形容詞・動詞で書いた比較は、何が何よりどれだけかが1通りに決まる文字どおりの比較なので拾わない
      （前は より の後に「も」があるだけで拾い、旧PCの人のスライドの「探索対象の値よりも大きい場合」など20件以上に当てていた）
    ・出典の より（「表1より、」「以上より、」）と手段の「により」は拾わない（YORI_SOURCE_RE）
    7回目（2026-10-01 今日の前の版 d6f2b634 との比べで、教員・本人の資料の PDF に当たった物）: 名詞の言い切りの見方を、空白で切った
    語ではなく、より を含む文（句点まで）の全体で見るようにした。「述語の無い決め台詞の対句」は、その文に述語が無いこと:
    ・B の後ろに、同じ文の中で述語（ひらがなの語）が続けば拾わない。前は B を空白・読点で切って最初の語だけを見たので、
      「上記の結果よりTFPB を入れない…と言える。」（創成実験の例のレポート）・「題意よりs = σ −1 とすると，」（制御基礎 第11回
      レポート）・「バンドギャップの（ 中央より上 ）に位置する。」（授業の小テストの解答）・「主記憶より低速、頻繁に
      スワッピングが発生すると」（コンピュータシステムⅡ-9）・「ブックセンターより電話連絡、もしくは…着信を残す場合がございます」
      （教科書販売の案内）の B を、述語の無い対句と見誤っていた
    ・A の前に、同じ文の中で述語や主題（ひらがなの語）があれば拾わない（「なお，プロパーという用語は，分子の絶対値より分母の絶」
      制御基礎 第3回授業資料。A より B は文の途中の比較で、述語は後ろの行にある）。「大切なのは、量より質」は前置き（M7）が拾う
    ・同じ行の前の文を句点で終えているのに、より の文が句点で終わらずに行が終わる時は、句点で文を終える書き方の文が行の終わりで
      折り返している（_rows_to_sents の句点の書き方の見方と同じ。制御基礎 第5回授業資料「…となっている．図1 下段より入力」⏎「r から…」）
    ・B が後ろの式・図を指す語（次式・次の式・下図・以下の表＝YORI_NEXT_RE）の時は、「A から次の式が言える」の述語を
      式の前で省いた導出の より（制御基礎 第2回講義資料 ラプラス変換「ラプラス変換の定義より次式」）。前を受ける 以上より と同じ出典の より"""
    for m in re.finditer(r'より(も)?', t):
        before = t[:m.start()]
        after = t[m.end():]
        if not before or before.endswith('に') or YORI_SOURCE_RE.search(before) or YORI_CITE_RE.match(after):
            continue
        if re.match(r'\s*[、,，]', after):
            return True
        a = re.split(r'[、,，。．\s]', before)[-1]
        b = re.split(r'[、,，。．\s]', after)[0]
        if not (a and b and NOUN_PHRASE_RE.fullmatch(a) and NOUN_PHRASE_RE.fullmatch(b)) or YORI_NEXT_RE.match(b):
            continue
        head = re.split(r'[。．!?！？]', before)[-1][:-len(a)]       # 同じ文の、A より前
        tail = re.split(r'[。．!?！？]', after[len(b):])[0]          # 同じ文の、B より後ろ
        if _has_predicate(head) or _has_predicate(tail):
            continue   # 文に述語・主題がある＝述語の無い対句ではない（7回目）
        if re.search(r'[。．]', before) and not re.match(r'\s*[。．!?！？]', after[len(b):]):
            continue   # 句点で文を終える書き方の文が、行の終わりで折り返している（7回目）
        return True
    return False


def _has_predicate(part):
    """F2 の「AよりB」の文の残り part に、述語・主題のひらがなの語か、式の関係の記号（= < ≤ 等）があるか。
    式は「I2 = I − I1」のように記号が述語の文（回路の授業の過去問題集「キルヒホッフの電流則よりI2 = I −I1 [A]」・回路の授業の資料
    第3回「3-12 ページより0 ≤𝑎< 1」の より は出典）。名詞の句をつなぐ の と、続けて並べた「〜より〜」
    （「長文より短文，短文より単語．」）の より は語に数えない（7回目 2026-10-01）"""
    return bool(re.search(r'[ぁ-ゖ=≠≒≈≡<>≤≥≦≧∝]', re.sub(r'より(も)?|の', '', part)))


def bigram_jaccard(a, b):
    """句読点と空白を除いた文字 bigram の Jaccard（一字一句同じなら 1.0）。"""
    a = _JACCARD_DROP_RE.sub('', unicodedata.normalize('NFKC', a or ''))
    b = _JACCARD_DROP_RE.sub('', unicodedata.normalize('NFKC', b or ''))
    A = set(a[i:i + 2] for i in range(len(a) - 1))
    B = set(b[i:i + 2] for i in range(len(b) - 1))
    if not (A | B):
        return 1.0 if (a and a == b) else 0.0
    return len(A & B) / float(len(A | B))


def count_verbatim_lines(lines):
    """'> ' で始まる行（本人の逐語）の数。"""
    return sum(1 for line in lines if line.startswith('> '))


def parse_read_ranges(read):
    """'1-300,301-574' → [(1, 300), (301, 574)]。読めない書き方なら None。"""
    spans = []
    for part in re.split(r'[,、，]', str(read or '')):
        part = part.strip()
        if not part:
            continue
        m = re.match(r'^(\d+)\s*(?:[-〜~]\s*(\d+))?$', part)
        if not m:
            return None
        a = int(m.group(1))
        b = int(m.group(2) or m.group(1))
        spans.append((min(a, b), max(a, b)))
    return spans


def unread_ranges(spans, total):
    """1〜total 行のうち、spans で覆われていない範囲を [(始め, 終わり), …] で返す。"""
    covered = [False] * (total + 1)
    for a, b in spans:
        for n in range(max(1, a), min(total, b) + 1):
            covered[n] = True
    out = []
    start = None
    for n in range(1, total + 1):
        if not covered[n] and start is None:
            start = n
        if covered[n] and start is not None:
            out.append((start, n - 1))
            start = None
    if start is not None:
        out.append((start, total))
    return out


def _as_list(v):
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return list(v)
    if isinstance(v, str):
        return [x for x in re.split(r'\s*[/／,、，]\s*', v) if x.strip()]
    return [v]


def _int_list(v):
    out = []
    for x in _as_list(v):
        try:
            out.append(int(x))
        except (TypeError, ValueError):
            pass
    return out


def _is_empty(v):
    if v is None:
        return True
    if isinstance(v, str):
        return not v.strip()
    if isinstance(v, (list, tuple, dict)):
        return len(v) == 0
    return False


def brief_missing_keys(brief):
    """台帳の必須8欄のうち、無いか空の欄の名前。"""
    return [k for k in BRIEF_KEYS if _is_empty(brief.get(k))]


def _proofs(brief):
    return [x for x in (brief.get('proof') or []) if isinstance(x, dict)]


def strong_p_count(brief):
    """for=P の強い証拠（逐語・写真・数字・場面）の数。annotation（Claude 側の注記）と web は数えない。"""
    return sum(1 for pr in _proofs(brief)
               if str(pr.get('for', '')).upper() == 'P' and pr.get('kind') in STRONG_KINDS)


def expand_path(p, base):
    """素材・inventory のパス。%USERPROFILE% と ~ を展開し、相対ならプロジェクト基準にする。"""
    q = Path(os.path.expanduser(os.path.expandvars(str(p or ''))))
    if not q.is_absolute():
        q = Path(base) / q
    return q


def read_source_lines(path):
    """素材ファイルを行のリストで返す。文字のファイルでない・開けない（OneDrive のクラウド専用ファイル等）なら None。"""
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return None
    try:
        return path.read_text(encoding='utf-8-sig', errors='replace').splitlines()
    except OSError:
        return None


def _source_item(brief, name):
    """sources_read の中から、basename が name と同じ項目を探す。"""
    want = Path(str(name).replace('\\', '/')).name
    for it in brief.get('sources_read') or []:
        if isinstance(it, dict) and Path(str(it.get('path', '')).replace('\\', '/')).name == want:
            return it
    return None


def speculation_note(lines, k):
    """k 行目（1始まり）と、その上5行以内で最も近い見出し（#）・太字ラベルに、推測・起草の印があればその行を返す。"""
    if SPECULATION_RE.search(lines[k - 1]):
        return lines[k - 1]
    for j in range(k - 1, max(0, k - 6), -1):
        line = lines[j - 1]
        if line.lstrip().startswith('#') or _BOLD_LABEL_RE.match(line):
            if SPECULATION_RE.search(line):
                return line
            return None   # 最も近い見出しだけを見る
    return None


def trace_proofs(brief, base):
    """C3: 証拠の引用が、書いてある出典の行（前後2行＝計5行）に本当にあるか。
    『本人の言葉（verbatim）』が、Claude の注記や推測の行から来ていないか。
    returns [(severity, message, fix)]。brief.py も同じ関数で判定する。"""
    return trace_items(_proofs(brief), brief, base, 'C3')


def trace_overview(brief, base):
    """G1: 概要の事実（overview の {k, v, src, quote}）の引用が、出典の行（前後2行）にあるか。C3 と同じ照合。
    brief.py も同じ関数で判定する。"""
    items = [x for x in (brief.get('overview') or []) if isinstance(x, dict)]
    return trace_items(items, brief, base, 'G1')


def trace_items(items, brief, base, tag):
    """C3・G1 の本体: 各項目の quote が src（'ファイル名:行'）の行の前後2行にあるか。returns [(severity, message, fix)]"""
    out = []
    fix_nf = '素材の該当行を開き、quote を行からそのまま写す（言い換え・要約をしない）。無ければその証拠を使わない'
    for pr in items:
        pid = str(pr.get('id') or pr.get('k') or '?')
        kind = str(pr.get('kind', ''))
        src = str(pr.get('src') or '').strip()
        quote = str(pr.get('quote') or '')
        if kind in ('photo', 'web'):
            continue   # 写真は C5 が画像の href で、web は手元の素材では照合できない
        m = SRC_RE.match(src)
        if not m:
            if kind in ('diagram', 'table') and src:
                continue   # 図表の出典（資料名だけ）は行で照合しない
            out.append(('WARNING', '%s %s: src「%s」が「ファイル名:行」の形でない＝照合できなかった' % (tag, pid, src[:30]),
                        'src を「研修メモ.md:243」の形で書く'))
            continue
        item = _source_item(brief, m.group(1))
        if item is None:
            if tag != 'C3':
                # 証拠（proof）の出典の抜けは C4 が ERROR にする。概要（overview）は C4 が見ないのでここで止める
                out.append(('ERROR', '%s %s: 出典 %s が sources_read（読んだ素材）に無い' % (tag, pid, m.group(1)),
                            'その素材を全文読んで sources_read に足す'))
            continue
        if not quote.strip():
            if kind not in NO_QUOTE_KINDS:
                out.append(('ERROR', '%s %s: quote が空（出典の行から写す）' % (tag, pid), fix_nf))
            continue
        path = expand_path(item.get('path'), base)
        lines = read_source_lines(path)
        if lines is None:
            out.append(('WARNING', '%s %s: 出典 %s を開けず、照合できなかった' % (tag, pid, path.name),
                        'OneDrive のクラウド専用ファイルなら実体化してから流し直す'))
            continue
        n = int(m.group(2))
        q = normalize_text(quote)
        if n < 1 or n > len(lines):
            out.append(('ERROR', '%s %s: %s の %d 行目は無い（素材は %d 行）' % (tag, pid, path.name, n, len(lines)),
                        fix_nf))
            continue
        lo, hi = max(1, n - 2), min(len(lines), n + 2)
        window = normalize_text('\n'.join(lines[lo - 1:hi])) if lo <= hi else ''
        if not q or q not in window:
            out.append(('ERROR', '%s %s: 「%s」が出典 %s の行（%d行目の前後2行）に無い＝作文の疑い' % (
                tag, pid, quote[:20], src, n), fix_nf))
            continue
        # 見つかった行（src の行を優先し、近い順に探す。行をまたぐ引用なら src の行）
        found = n
        for k in sorted(range(lo, hi + 1), key=lambda k: abs(k - n)):
            if q in normalize_text(lines[k - 1]):
                found = k
                break
        line = lines[found - 1]
        if kind == 'verbatim':
            if str(item.get('verbatim') or '0').strip() in ('0', ''):
                # 引用記号の決まりが無い素材: その行の「」の中にあればよい
                spans = QUOTE_SPAN_RE.findall(line)
                if not any(q in normalize_text(s) for s in spans):
                    out.append(('ERROR', 'C3 %s: 逐語（verbatim）なのに、%s:%d の「」の中に無い' % (pid, path.name, found),
                                '本人の言葉として使うのは「」の中か \'> \' の行だけ。そうでなければ kind を annotation にする'))
            elif not line.startswith('>'):
                out.append(('ERROR', 'C3 %s: 逐語（verbatim）なのに、%s:%d は \'> \' の逐語行ではない（注記・推測の行）' % (
                    pid, path.name, found),
                    '本人の言葉として使うのは \'> \' の行だけ。注記なら kind を annotation にし、スライドで本人の言葉として見せない'))
        note = speculation_note(lines, found)
        if note:
            out.append(('WARNING', '%s %s: 推測・起草の行／節を事実として使っている（%s:%d「%s」）' % (
                tag, pid, path.name, found, note.strip()[:30]),
                '本人に選択式で確かめる。確認が取れるまでは「〜とみられる」と書くか、使わない'))
    return out


def audit_sources_read(brief, base):
    """C4: 素材を全部読んだ記録（sources_read）が、素材の実物と合うか。
    『キーワード grep だけで全文を読まなかった』への機械の代理指標。自己申告は偽れるので、最終判定は R0。
    returns [(severity, message, fix)]。brief.py も同じ関数で判定する。"""
    out = []
    fix_read = '素材を Read で最後まで読み直し、sources_read の lines・read・verbatim を実物に合わせる'
    names = set()
    inventories = []
    for it in brief.get('sources_read') or []:
        if not isinstance(it, dict):
            continue
        path = expand_path(it.get('path'), base)
        names.add(path.name)
        if it.get('inventory') and it.get('inventory') not in inventories:
            inventories.append(it.get('inventory'))
        try:
            total = int(it.get('lines'))
        except (TypeError, ValueError):
            out.append(('ERROR', 'C4 %s: lines（読んだ時の行数）が無い' % path.name, fix_read))
            continue
        spans = parse_read_ranges(it.get('read'))
        if spans is None or not spans:
            out.append(('ERROR', 'C4 %s: read「%s」が読めない（例: 1-574）' % (path.name, it.get('read')), fix_read))
        else:
            miss = unread_ranges(spans, total)
            if miss:
                txt = '・'.join('%d〜%d' % (a, b) if a != b else '%d' % a for a, b in miss[:5])
                out.append(('ERROR', 'C4 %s: %s 行が未読（read=%s・全 %d 行）' % (path.name, txt, it.get('read'), total),
                            fix_read))
        lines = read_source_lines(path)
        if lines is None:
            out.append(('WARNING', 'C4 %s: 素材を開けず、行数と逐語行の数を照合できなかった' % path.name,
                        'OneDrive のクラウド専用ファイルなら実体化してから流し直す'))
            continue
        if len(lines) > total:
            # 2026-09-28 反証: lines を少なく申告すると読み残しが WARNING だけで通っていた＝ERROR にする
            out.append(('ERROR', 'C4 %s: 記録 %d 行より実物が長い（今 %d 行）＝%d〜%d 行を読んでいない' % (
                path.name, total, len(lines), total + 1, len(lines)), '残りの行を Read で読み、lines と read を今の行数に直す'))
        elif len(lines) < total:
            out.append(('ERROR', 'C4 %s: 記録 %d 行より実物が短い（今 %d 行）＝別のファイルか、読んだ後に消された' % (
                path.name, total, len(lines)), 'パスと行数を実物に合わせ、使う行を読み直す'))
        if path.suffix.lower() in ('.md', '.markdown'):
            real = count_verbatim_lines(lines[:total])
            try:
                said = int(it.get('verbatim') or 0)
            except (TypeError, ValueError):
                said = -1
            if real != said:
                out.append(('ERROR', 'C4 %s: 逐語行の数が合わない（記録 %s 本・実物 %d 本）＝全文を読んでいない疑い' % (
                    path.name, it.get('verbatim'), real), fix_read))
    # (d) 証拠の出典が、読んだ素材の一覧にあるか
    for pr in _proofs(brief):
        if pr.get('kind') in ('photo', 'web'):
            continue
        m = SRC_RE.match(str(pr.get('src') or '').strip())
        if m and Path(m.group(1).replace('\\', '/')).name not in names:
            out.append(('ERROR', 'C4 %s: 出典 %s が sources_read（読んだ素材）に無い' % (pr.get('id', '?'), m.group(1)),
                        'その素材を全文読んで sources_read に足す'))
    # (e) 候補の一覧（inventory）があり、証拠の ID が載っているか
    if not inventories:
        out.append(('ERROR', 'C4 inventory（素材から拾った候補の一覧）が sources_read に書かれていない',
                    '読みながら sources/inventory.md に候補の ID（V/S/N/Ph/A）を振って並べる'))
    else:
        texts = []
        for inv in inventories:
            ip = expand_path(inv, base)
            try:
                texts.append(ip.read_text(encoding='utf-8-sig', errors='replace'))
            except OSError:
                out.append(('ERROR', 'C4 inventory %s が無い' % inv,
                            '読みながら sources/inventory.md に候補の ID を振って並べる'))
        if texts:
            alltext = '\n'.join(texts)
            gone = [str(pr.get('id')) for pr in _proofs(brief) if pr.get('id') and not re.search(
                r'(?<![A-Za-z0-9])%s(?![0-9])' % re.escape(str(pr.get('id'))), alltext)]
            if gone:
                out.append(('ERROR', 'C4 inventory に無い証拠 ID: %s' % ', '.join(gone[:8]),
                            '証拠は inventory の候補から選ぶ（候補に無い物を後から足さない）'))
    return out


def coverage_problems(brief, roles):
    """C2: 結論 P・各理由 R・各具体例 E の枚に、証拠が割り当たっているか。returns [(severity, message, fix)]"""
    out = []
    fix = 'brief.json の r[].slides と proof[].for / slides を埋める。証拠の無い理由は削るか、inventory から証拠を探す'
    rs = [x for x in (brief.get('r') or []) if isinstance(x, dict)]
    proofs = _proofs(brief)
    if roles:
        seq = [roles[k][0] for k in sorted(roles)]
        core = prep_core(seq)
        # 3枚以下の小さなデッキは R/E を求めない（check_prep と同じ）＝(d) の結論の証拠だけを見る
        if len(core) > 3:
            r_slides = sorted(k for k, v in roles.items() if v[0] == 'R')
            e_slides = sorted(k for k, v in roles.items() if v[0] == 'E')
            in_r = set()
            for x in rs:
                in_r |= set(_int_list(x.get('slides')))
            miss = [k for k in r_slides if k not in in_r]
            if miss:
                out.append(('ERROR', 'C2 %s枚目(R)がどの理由（r[].slides）にも入っていない' % '・'.join(map(str, miss)), fix))
            for x in rs:
                rid = str(x.get('id', '?'))
                if not any(str(pr.get('for', '')) == rid for pr in proofs):
                    out.append(('ERROR', 'C2 %s に証拠が無い（proof の for=%s が0件）' % (rid, rid), fix))
            in_e = set()
            for pr in proofs:
                in_e |= set(_int_list(pr.get('slides')))
            miss = [k for k in e_slides if k not in in_e]
            if miss:
                out.append(('ERROR', 'C2 %s枚目(E)がどの証拠にも割り当たっていない' % '・'.join(map(str, miss)), fix))
    n = strong_p_count(brief)
    if n < 2:
        out.append(('ERROR', 'C2 結論の証拠が2件未満（逐語・写真・数字・場面が %d 件。注記と web は数えない）' % n,
                    '結論 P を証明する本人の逐語・写真・数字・場面を2つ以上、inventory から選ぶ'))
    return out


def _quote_in(quote, text):
    """正規化した quote そのもの、または quote の中の連続8字が text（正規化済み）にあるか。"""
    q = normalize_text(quote)
    if not q or not text:
        return False
    if len(q) < 8:
        return q in text
    for i in range(len(q) - 7):
        if q[i:i + 8] in text:
            return True
    return False


def _number_tokens(quote):
    """数字と単位（例: 52本・574行）を取り出す。"""
    t = unicodedata.normalize('NFKC', quote or '')
    return [normalize_text(m.group(0)) for m in _NUM_TOKEN_RE.finditer(t)]


# ------------------------------------------------- スライドの読み取り（中身・形の検査で共用） ---
HEAD_MIN_FS = 40.0     # 見出し＝この大きさ以上
HEAD_MAX_Y = 330.0     # 見出し＝この y より上
NUM_ONLY_RE = re.compile(r'^[\d０-９\s/%％.,．，:：~〜\-+]+$')
SECONDS_RE = re.compile(r'[（(]\s*約?\s*\d+\s*秒\s*[）)]')


def body_lines(svg_path):
    """フッター・出典を除いた本文行と (幅, 高さ) を返す（T1 と同じ数え方）。"""
    lines, canvas = extract_lines(svg_path)
    cw, ch = canvas if canvas else (1280.0, 720.0)
    body = [ln for ln in lines
            if ln.text and not ln.text.startswith('\x00') and not _is_footer_or_source(ln, ch)]
    return body, (cw, ch)


def _headline_lines(body):
    """見出しの行: font-size 40以上・y 330以下で、数字だけではない行を (y, x) の順に。"""
    cand = [ln for ln in body
            if ln.font_size >= HEAD_MIN_FS and ln.y <= HEAD_MAX_Y and not NUM_ONLY_RE.match(ln.text)]
    cand.sort(key=lambda ln: (ln.y, ln.x))
    return cand


def _headline(body):
    """見出しの文（見出しの行をつないだ物）。"""
    return ''.join(ln.text for ln in _headline_lines(body))


def _eyebrow(body, head_lines=None):
    """小ラベル: 見出しの最初の行より上（y < 見出しの y − 0.8×font-size）・y 230以下・
    font-size が見出しの0.65倍以下・20字以下の行。無ければ None。"""
    if head_lines is None:
        head_lines = _headline_lines(body)
    if not head_lines:
        return None
    h = head_lines[0]
    top = h.y - 0.8 * h.font_size
    cand = [ln for ln in body
            if ln.y < top and ln.y <= 230 and ln.font_size <= h.font_size * 0.65 and len(ln.text) <= 20]
    cand.sort(key=lambda ln: (ln.y, ln.x))
    return cand[0] if cand else None


def notes_by_slide(project_dir):
    """notes/total.md を {枚番号: ノート本文} にする（見出しの先頭番号で割り当てる）。total.md が無ければ None。"""
    total_md = None
    for cand in (project_dir / 'notes' / 'total.md', project_dir / 'total.md'):
        if cand.is_file():
            total_md = cand
            break
    if total_md is None:
        return None
    out = {}
    cur = None
    for line in total_md.read_text(encoding='utf-8', errors='replace').splitlines():
        m = re.match(r'^#{1,3}\s+(.+)$', line.strip())
        if m:
            n = extract_leading_number(m.group(1).strip())
            if n is not None:
                cur = n
                out.setdefault(cur, [])
                continue
        if cur is not None:
            out[cur].append(line)
    return dict((k, '\n'.join(v)) for k, v in out.items())


def _elements_with_groups(root):
    """[(要素, 祖先の <g> の id の並び)]（bg・decor の中かどうかの判定用）。"""
    out = []

    def walk(el, ids):
        for ch in el:
            tag = ch.tag.rsplit('}', 1)[-1]
            if tag == 'g':
                walk(ch, ids + [(ch.get('id') or '').lower()])
            else:
                out.append((ch, ids))
                walk(ch, ids)
    if root is not None:
        walk(root, [])
    return out


def _in_bg(ids):
    return any(i == 'bg' or i.startswith('bg') or i == 'background' for i in ids)


def _tag(el):
    return el.tag.rsplit('}', 1)[-1]


def slide_infos(project_dir, svg_files):
    """中身・形の検査で使う、枚ごとの読み取り結果。returns (infos, total.md があるか)"""
    roles = parse_prep(project_dir) or {}
    notes = notes_by_slide(project_dir)
    infos = []
    for i, f in enumerate(svg_files, 1):
        lines, cv = extract_lines(f)
        canvas = cv if cv else (1280.0, 720.0)
        all_lines = [ln for ln in lines if ln.text and not ln.text.startswith('\x00')]
        body = [ln for ln in all_lines if not _is_footer_or_source(ln, canvas[1])]   # body_lines と同じ数え方
        head_lines = _headline_lines(body)
        try:
            root = ET.fromstring(f.read_text(encoding='utf-8', errors='replace'))
        except (ET.ParseError, OSError, ValueError):
            root = None
        hrefs = []
        for el, _ in _elements_with_groups(root):
            if _tag(el) == 'image':
                h = el.get('href') or el.get('{http://www.w3.org/1999/xlink}href') or ''
                hrefs.append(Path(h.replace('\\', '/')).name)
        note = (notes or {}).get(i, '')
        infos.append({
            'n': i, 'file': f, 'role': (roles.get(i) or ['?'])[0], 'body': body, 'lines': all_lines,
            'canvas': canvas, 'root': root,
            'head_lines': head_lines, 'head': ''.join(ln.text for ln in head_lines),
            'eyebrow': _eyebrow(body, head_lines), 'notes': note, 'hrefs': hrefs,
            'text': normalize_text(''.join(ln.text for ln in body)), 'notes_norm': normalize_text(note),
        })
    return infos, notes is not None


def content_hash(project_dir, svg_files=None):
    """中身の指紋: 全 SVG の文字の行（ファイル名順）＋notes/total.md を、空白を除いてつなぎ、sha1 の先頭10桁。
    claims.py も同じ関数で記録する（照合の後に中身が変わったかを R0 が見る）。"""
    project_dir = Path(project_dir)
    if svg_files is None:
        _, svg_dir = resolve_svg_dir(project_dir)
        svg_files = sorted(svg_dir.glob('*.svg'))
    parts = []
    for f in sorted(svg_files, key=lambda p: p.name):
        lines, _ = extract_lines(f)
        parts.extend(ln.text for ln in lines if ln.text and not ln.text.startswith('\x00'))
    for cand in (project_dir / 'notes' / 'total.md', project_dir / 'total.md'):
        if cand.is_file():
            parts.append(cand.read_text(encoding='utf-8', errors='replace'))
            break
    joined = re.sub(r'\s', '', ''.join(parts))
    return hashlib.sha1(joined.encode('utf-8')).hexdigest()[:10]


def load_brief(project_dir):
    """<project>/brief.json を読む。returns (中身 or None, パス or None, 問題の文 or '')"""
    for base in (project_dir, project_dir.parent):
        cand = base / 'brief.json'
        if cand.is_file():
            try:
                data = json.loads(cand.read_text(encoding='utf-8-sig'))
            except (OSError, ValueError):
                return None, cand, 'brief.json が壊れている（JSON として読めない）'
            if not isinstance(data, dict):
                return None, cand, 'brief.json の中身が {…} の形でない'
            return data, cand, ''
    return None, None, '証拠の台帳 brief.json(v2) が無い'


def brief_confirmed_date(project_dir):
    """spec_lock の brief_confirmed の日付（YYYY-MM-DD）。無ければ None。"""
    for base in (project_dir, project_dir.parent):
        for cand in (base / 'spec_lock.md', base / 'design_spec.md'):
            if cand.is_file():
                m = BRIEF_RE.search(cand.read_text(encoding='utf-8', errors='replace'))
                if m:
                    d = re.match(r'(\d{4}-\d{2}-\d{2})', m.group(1))
                    return d.group(1) if d else None
    return None


def _down(sev, legacy):
    """--legacy（旧書式のデッキ）では ERROR を WARNING に下げる。"""
    return 'WARNING' if (legacy and sev == 'ERROR') else sev


# ---------------------------------------------------------- 中身の検査（C1〜C6） ---

def check_content(project_dir, infos, roles, issues, legacy):
    """C1〜C6。C1（台帳）が落ちたら C2〜C6 は走らせない。returns 読めた brief（F7 用。無ければ None）"""
    brief, bpath, problem = load_brief(project_dir)
    if brief is not None:
        try:
            ver = int(brief.get('brief_version') or 0)
        except (TypeError, ValueError):
            ver = 0
        if ver < 2:
            problem = 'brief.json の brief_version が 2 でない（旧書式の台帳）'
        else:
            miss = brief_missing_keys(brief)
            if miss:
                problem = '証拠の台帳 brief.json の必須欄が空: %s' % ', '.join(miss)
    if problem:
        issues.append(Issue(
            _down('ERROR', legacy), 'brief.json', 'C1 ' + problem,
            'slide-gen STEP 1-0: 素材を全文読んで sources/inventory.md を作り、'
            '`py brief.py <proj> <answers.json>`（v2）で brief.json を書く。9/28 以前のデッキの作り直しだけなら --legacy'))
        issues.append(Issue('INFO', 'brief.json', 'C2〜C6 中身の検査は未実行（brief.json が無い・欠けている）'))
        return brief
    base = bpath.parent
    for sev, msg, fix in coverage_problems(brief, roles):
        issues.append(Issue(_down(sev, legacy), 'brief.json', msg, fix))
    for sev, msg, fix in trace_proofs(brief, base):
        issues.append(Issue(_down(sev, legacy), 'brief.json', msg, fix))
    for sev, msg, fix in audit_sources_read(brief, base):
        issues.append(Issue(_down(sev, legacy), 'brief.json', msg, fix))
    check_brief_to_deck(brief, infos, issues, legacy)
    check_core_link(brief, infos, issues, legacy)
    return brief


def check_brief_to_deck(brief, infos, issues, legacy):
    """C5: brief で選んだ証拠と本人の場面が、実際のスライドかノートに出ているか（台帳だけ立派、を止める）。"""
    by_n = dict((info['n'], info) for info in infos)
    fix = 'その証拠を、割り当てた枚の本文（またはノートの「## Slide N:」節）に置く。置かないなら brief から外す'
    for pr in _proofs(brief):
        pid = str(pr.get('id', '?'))
        kind = str(pr.get('kind', ''))
        slides = [k for k in _int_list(pr.get('slides')) if k in by_n]
        if not slides:
            issues.append(Issue(_down('ERROR', legacy), 'brief.json',
                                'C5 %s の slides が空か範囲外（どの枚で見せるか決まっていない）' % pid, fix))
            continue
        where = '・'.join(str(k) for k in slides)
        if kind == 'photo':
            name = Path(str(pr.get('src') or '').replace('\\', '/')).name
            if not name or not any(name in by_n[k]['hrefs'] for k in slides):
                issues.append(Issue(_down('ERROR', legacy), 'brief.json',
                                    'C5 選んだ写真 %s（%s）が %s 枚目の画像に無い' % (pid, name or 'src 無し', where), fix))
            continue
        quote = str(pr.get('quote') or '')
        if not quote.strip():
            continue   # 空の quote は C3 が見る
        tokens = _number_tokens(quote) if kind == 'number' else []
        ok = False
        for k in slides:
            info = by_n[k]
            for txt in (info['text'], info['notes_norm']):
                if tokens:
                    if all(t in txt for t in tokens):
                        ok = True
                elif _quote_in(quote, txt):
                    ok = True
        if not ok:
            issues.append(Issue(_down('ERROR', legacy), 'brief.json',
                                'C5 選んだ証拠 %s「%s」が %s 枚目の本文にもノートにも出ていない' % (pid, quote[:20], where), fix))
    # 本人の場面（me.scene）はデッキのどこか（本文かノート）にあればよい
    me = brief.get('me') if isinstance(brief.get('me'), dict) else {}
    scene = me.get('scene') if isinstance(me.get('scene'), dict) else {}
    sq = str(scene.get('quote') or '')
    found = False
    for info in infos:
        if _quote_in(sq, info['text']) or _quote_in(sq, info['notes_norm']):
            found = True
    if not found:
        sev = 'ERROR' if not _is_empty(brief.get('cta')) else 'WARNING'
        issues.append(Issue(
            _down(sev, legacy), 'brief.json',
            'C5 本人の場面 me.scene「%s」がデッキ（本文・ノート）のどこにも無い' % (sq[:20] or '空'),
            '本人にしか話せない場面（いつ・どこで・誰と・何を思ったか）を、R/E か最後の P の本文かノートに入れる'))


def check_core_link(brief, infos, issues, legacy):
    """C6: 結論の核の語（p_core）が R・E の枚に出てくるか（Backward Logic Check の機械でできる部分）。"""
    core = [normalize_text(w) for w in _as_list(brief.get('p_core'))]
    core = [w for w in core if w]
    re_infos = [info for info in infos if info['role'] in ('R', 'E')]
    if not core or not re_infos:
        return
    miss = [info['n'] for info in re_infos
            if not any(w in info['text'] or w in info['notes_norm'] for w in core)]
    n = len(re_infos)
    k = n - len(miss)
    fix = 'その枚が結論のどこを支えるかを見出しに出す。支えないなら削るかノートへ'
    msg = 'C6 結論の核（%s）が R/E の %d 枚中 %d 枚にしか出ない（出ない枚: %s）' % (
        '・'.join(str(x) for x in _as_list(brief.get('p_core'))[:6]), n, k, '・'.join(str(x) for x in miss))
    if k == 0:
        issues.append(Issue(_down('ERROR', legacy), '(全体)', msg, fix))
    elif k < n / 2.0:
        issues.append(Issue('WARNING', '(全体)', msg, fix))


# ------------------------------------------------------ 照合の記録（R0） ---
EVIDENCE_RE = re.compile(r'^[\s\-*>]*evidence_check[^\S\n]*[:：][^\S\n]*(.*)$', re.IGNORECASE | re.MULTILINE)
EVIDENCE_LINE_RE = re.compile(r'^[ \t\-*>]*evidence_check[^\S\n]*[:：].*(?:\n|\Z)', re.IGNORECASE | re.MULTILINE)


def read_evidence_check(project_dir):
    """spec_lock の `evidence_check: PASS 2026-09-29 hash=<10桁> report=review/evidence_check.md [minor=理由]` を読む。
    returns {'verdict', 'date', 'hash', 'report', 'minor'} か None"""
    for base in (project_dir, project_dir.parent):
        cand = base / 'spec_lock.md'
        if not cand.is_file():
            continue
        found = EVIDENCE_RE.findall(cand.read_text(encoding='utf-8', errors='replace'))
        if not found:
            continue
        body = found[-1].strip()
        words = body.split()
        rec = {'verdict': words[0].upper() if words else '', 'date': '', 'hash': '', 'report': '', 'minor': ''}
        m = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', body)
        if m:
            rec['date'] = m.group(1)
        m = re.search(r'hash=([0-9a-fA-F]+)', body)
        if m:
            rec['hash'] = m.group(1).lower()
        m = re.search(r'report=(\S+)', body)
        if m:
            rec['report'] = m.group(1)
        m = re.search(r'minor=(.*)$', body)
        if m:
            rec['minor'] = m.group(1).strip()
        return rec
    return None


READER_RE = re.compile(r'^[\s\-*>]*reader_check[^\S\n]*[:：][^\S\n]*(.*)$', re.IGNORECASE | re.MULTILINE)
READER_LINE_RE = re.compile(r'^[ \t\-*>]*reader_check[^\S\n]*[:：].*(?:\n|\Z)', re.IGNORECASE | re.MULTILINE)


def read_reader_check(project_dir):
    """spec_lock の `reader_check: PASS 2026-10-01 hash=<10桁> report=review/reader_check.md [minor=理由]` を読む。
    形は evidence_check と同じ。returns {'verdict', 'date', 'hash', 'report', 'minor'} か None"""
    for base in (project_dir, project_dir.parent):
        cand = base / 'spec_lock.md'
        if not cand.is_file():
            continue
        found = READER_RE.findall(cand.read_text(encoding='utf-8', errors='replace'))
        if not found:
            continue
        body = found[-1].strip()
        words = body.split()
        rec = {'verdict': words[0].upper() if words else '', 'date': '', 'hash': '', 'report': '', 'minor': ''}
        for key, pat in (('date', r'\b(\d{4}-\d{2}-\d{2})\b'), ('hash', r'hash=([0-9a-fA-F]+)'),
                         ('report', r'report=(\S+)'), ('minor', r'minor=(.*)$')):
            m = re.search(pat, body)
            if m:
                rec[key] = m.group(1).strip().lower() if key == 'hash' else m.group(1).strip()
        return rec
    return None


def check_reader_record(project_dir, svg_files, issues, draft, legacy):
    """R1: 初見の読み手（slide-reader）が、ノートも brief も見ずにスライドの文字だけで
    「誰が・何を・どうした」を言い直せたか（PASS）。その後に中身が変わっていないか。
    根拠: 本人「今のスライド生成は結局何を言いたいのか伝わらない」（2026-10-01）と、
    Kiminori Yokoi「AI臭い文章とは何なのか」（豊洲会 2026-09-28・Speaker Deck）の
    「話者の説明なしに意味理解を復元できないと、資料を再配布しにくい」。R0 は証拠の噛み合い、R1 は意味が通るか。"""
    sev = 'WARNING' if (draft or legacy) else 'ERROR'
    fix = ('提示前に `py claims.py <proj> --reader` → slide-reader に review/slide_text.md だけを渡す（ノート・brief・画像は渡さない）→ '
           '報告を review/reader_check.md に保存 → `py claims.py <proj> --record-reader PASS|FAIL --report review/reader_check.md`'
           '（途中の確認用ビルドなら --draft）')
    rec = read_reader_check(project_dir)
    if rec is None:
        issues.append(Issue(sev, '(全体)', 'R1 初見の読み手（slide-reader）の記録が spec_lock に無い（reader_check:）', fix))
        return
    if rec['verdict'] != 'PASS':
        issues.append(Issue(sev, '(全体)', 'R1 初見の読み手の判定が %s（意味を補わないと読めない枚がある）' % (rec['verdict'] or '空'),
                            '報告 %s の「聞き返し」に、こちらの答え（こういう意味）をそのまま書いた文で置き換えて、もう一度読ませる' % (
                                rec['report'] or 'review/reader_check.md')))
        return
    now = content_hash(project_dir, svg_files)
    if rec['hash'] != now:
        issues.append(Issue(sev, '(全体)', 'R1 初見の読み手の後に中身が変わった（記録 hash=%s ／ 今 %s）' % (rec['hash'] or '無し', now),
                            '変えた枚をもう一度読ませる。誤字の修正だけなら `py claims.py <proj> --minor "理由"` で付け直す'))
        return
    if rec['minor']:
        issues.append(Issue('INFO', '(全体)', 'R1 初見の読み手の後に軽い修正で hash を付け直した（minor=%s）' % rec['minor']))


def check_evidence_record(project_dir, svg_files, issues, draft, legacy):
    """R0: 独立の照合エージェント（slide-evidence-checker）が PASS を出したか。その後に中身が変わっていないか。"""
    sev = 'WARNING' if (draft or legacy) else 'ERROR'
    fix = ('提示前に `py claims.py <proj>` → slide-evidence-checker に review/claims.json と素材のパスだけを渡す → '
           '報告を review/evidence_check.md に保存 → `py claims.py <proj> --record PASS|FAIL --report review/evidence_check.md`'
           '（途中の確認用ビルドなら --draft）')
    rec = read_evidence_check(project_dir)
    if rec is None:
        issues.append(Issue(sev, '(全体)', 'R0 独立の照合（slide-evidence-checker）の記録が spec_lock に無い（evidence_check:）', fix))
        return
    if rec['verdict'] != 'PASS':
        issues.append(Issue(sev, '(全体)', 'R0 照合の判定が %s（重大な指摘が残っている）' % (rec['verdict'] or '空'),
                            '報告 %s の「重大」を直して、もう一度照合する。2回続けて FAIL なら本人に聞く' % (
                                rec['report'] or 'review/evidence_check.md')))
        return
    now = content_hash(project_dir, svg_files)
    if rec['hash'] != now:
        issues.append(Issue(sev, '(全体)', 'R0 照合の後に中身が変わった（記録 hash=%s ／ 今 %s）' % (rec['hash'] or '無し', now),
                            '変えた枚をもう一度照合する。誤字の修正だけなら `py claims.py <proj> --minor "理由"` で付け直す'))
        return
    if rec['minor']:
        issues.append(Issue('INFO', '(全体)', 'R0 照合の後に軽い修正で hash を付け直した（minor=%s）' % rec['minor']))


# ---------------------------------------------------------- 形の検査（F1〜F8） ---
EVIDENCE_GROUP_RE = re.compile(r'chart|graph|diagram|flow|table|timeline|map', re.IGNORECASE)
ENUM_PREFIX_RE = re.compile(r'^0?\d[\s　]')      # 行頭の番号（01　…）は数字の証拠に数えない
SHAPE_TAGS = ('line', 'path', 'circle', 'rect', 'polygon', 'polyline', 'ellipse')
DECOR_OK_RE = re.compile(r'^[\s\-*>]*decor_ok[^\S\n]*[:：][^\S\n]*(\d+(?:\s*[,、]\s*\d+)*)(.*)$',
                         re.IGNORECASE | re.MULTILINE)


def check_p_repeat(infos, roles, issues):
    """F1: 最初の P と最後の P の見出しが同じ文になっていないか（最後の P は言い直し）。"""
    if roles is None:
        return
    ps = [info for info in infos if info['role'] == 'P']
    if len(ps) < 2 or not ps[0]['head'] or not ps[-1]['head']:
        return
    j = bigram_jaccard(ps[0]['head'], ps[-1]['head'])
    if j >= 0.8:
        issues.append(Issue(
            'ERROR', '(全体)',
            'F1 最初と最後の結論の見出しが同じ文（%02d枚目と%02d枚目・J=%.2f「%s」）' % (
                ps[0]['n'], ps[-1]['n'], j, ps[0]['head'][:24]),
            '最後の P は、最初の P に E で見せた具体（人・数字・場面）を1つ足して言い直す。brief.p_last をそのまま使う'))


def check_contrast(infos, issues):
    """F2: 対句のまとめ文が、見出しか小ラベルに入っていないか。本文はデッキ全体で2回以上なら警告。ノートは見ない。"""
    fix = ('言い切りの1文にする（例:「人の熱意に驚いた」。「単なる〜ではない」は、何に使って何が変わったかを書く）。'
           '判定の問い＝本人が教授や聴衆の前で声に出して言うか')
    body_hits = []
    for info in infos:
        where = []
        if info['head'] and _contrast_line(info['head']):
            where.append('見出し「%s」' % info['head'][:24])
        eb = info['eyebrow']
        if eb is not None and _contrast_line(eb.text):
            where.append('小ラベル「%s」' % eb.text[:20])
        if where:
            issues.append(Issue('WARNING', info['file'].name,
                                'F2 対句のまとめ文（〜ではなく〜・AよりB・〜て初めて）: ' + ' / '.join(where), fix))
        skip = set(id(ln) for ln in info['head_lines'])
        if eb is not None:
            skip.add(id(eb))
        for ln in info['body']:
            nxt = _next_line(info, ln)
            if id(ln) not in skip and _contrast_line(ln.text, nxt.text if nxt is not None else None):
                body_hits.append('%02d「%s」' % (info['n'], ln.text[:16]))
    if len(body_hits) >= 2:
        issues.append(Issue('WARNING', '(全体)',
                            'F2 本文に対句のまとめ文が %d 回（%s）' % (len(body_hits), ' / '.join(body_hits[:4])), fix))


# 行の頭に来ない語＝前の行の続き（7回目 2026-10-01）。を・に・へ は名詞の後ろにしか付かない助詞で、文の頭には来ない
# （助動詞で始まる行を前の行の続きとみなす M_ROW_CONT_RE と同じ考え）
M_ROW_CONT_PARTICLE_RE = re.compile(r'[をにへ]')


def contrast_row(t, nxt=None):
    """F2: 1行 t に対句のまとめ文があるか（has_contrast）。行が句点で終わらず、すぐ下の行 nxt が前の行の続き（助動詞・
    を・に・へ で始まる）の時は、文の途中で行を折り返しているので、2行をつないだ文で見る（7回目 2026-10-01。先生の
    Moodle の小テストの画面 moodle 10.pdf「✓ a. キャッシュメモリよりパイプライン」⏎「を適用したほうが高速であるX」は、
    つなぐと「パイプラインを適用したほうが高速である」の比べる より＝述語のある文。M1〜M11 の文の分け方 _rows_to_sents と同じ見方）"""
    if not has_contrast(t):
        return False
    rest = (nxt or '').strip()
    if rest and not M_SENT_END_RE.search(t.rstrip()) and (M_ROW_CONT_RE.match(rest) or M_ROW_CONT_PARTICLE_RE.match(rest)):
        return has_contrast(t.rstrip() + rest)
    return True


def _contrast_line(t, nxt=None):
    """F2 で数える行か。「これこそがチームの力にほかならない」の こそ と決め台詞（〜に他ならない・〜というわけだ）は、
    1つの強調の前と後ろなので、決め台詞の検査（AIくさい語の疑い）の1件だけにして、F2 には二重に数えない
    （M7 と M3・M11 と M3 を同じ読点で二重に数えないのと同じ扱い。3回目の反証 2026-10-01）。
    nxt＝すぐ下の行。文の途中で行を折り返した行は、次の行とつないで見る（contrast_row）"""
    if not contrast_row(t, nxt):
        return False
    if copy_hits(AI_COPY_SOFT_RE, t) and re.search(r'に(他|ほか)なら|というわけ', t):
        return has_contrast(re.sub(r'こそ(が|、)?', '', t))
    return True


def _one_side_bars(info):
    """F3 の材料: (カード＋左の色線がある, 画面の端の帯がある, 単独の縦線がある)"""
    cw, ch = info['canvas']
    rects = []
    for el, ids in _elements_with_groups(info['root']):
        if _tag(el) != 'rect':
            continue
        w = _parse_len_px(el.get('width'), cw) or 0.0
        h = _parse_len_px(el.get('height'), ch) or 0.0
        x = _parse_len(el.get('x'), 0.0)
        y = _parse_len(el.get('y'), 0.0)
        rects.append((x, y, w, h, _in_bg(ids)))
    card_bar = False
    lone = False
    band = False
    for (x, y, w, h, bg) in rects:
        # 画面の端に沿った全高の細い帯（bg の中でも数える）
        if (x <= 2 or x + w >= cw - 2) and 0 < w <= 40 and h >= 0.9 * ch:
            band = True
        if bg:
            continue
        # 縦線: 幅12以下・高さ40以上・高さが幅の3倍以上・全高ではない
        if not (0 < w <= 12 and h >= 40 and h >= 3 * w and h < 0.9 * ch):
            continue
        paired = False
        for (cx, cy, cwid, chei, cbg) in rects:
            if cbg or (cx, cy, cwid, chei) == (x, y, w, h):
                continue
            if (cwid >= 200 and cwid * chei < 0.9 * cw * ch and abs(cx - x) <= 2
                    and y >= cy - 2 and y + h <= cy + chei + 2):
                paired = True
                break
        if paired:
            card_bar = True
        else:
            lone = True
    return card_bar, band, lone


def check_one_side_bar(infos, issues):
    """F3: 片側だけの縦線（カード＋左端の色線・画面の端の全高の帯）。禁止の型なのでデッキに1回でも出れば警告。"""
    cards, bands, lones = [], [], []
    for info in infos:
        if info['root'] is None:
            continue
        card_bar, band, lone = _one_side_bars(info)
        if card_bar:
            cards.append('%02d' % info['n'])
        if band:
            bands.append('%02d' % info['n'])
        if lone:
            lones.append('%02d' % info['n'])
    if not cards and not bands:
        return
    parts = []
    if cards:
        parts.append('カード＋左の色線 %s 枚目' % '・'.join(cards))
    if bands:
        parts.append('画面の端の帯 %s 枚目' % '・'.join(bands))
    msg = 'F3 片側だけの縦線: ' + '／'.join(parts)
    if lones:
        msg += '（ほかに単独の縦線: %s 枚目）' % '・'.join(lones)
    issues.append(Issue('WARNING', '(全体)', msg,
                        '薄い背景だけにするか、何も置かない（AI の埋め草として名指しされている型）'))


def check_same_entry(infos, roles, issues):
    """F4: 全部の枚が同じ入り方（左上の小ラベル→太字の見出し、が同じ座標と大きさ）になっていないか。"""
    from collections import Counter
    if roles:
        content = [info for info in infos if info['role'] in ('P', 'R', 'E')]
    else:
        content = infos[1:]
    if len(content) < 4:
        return
    sigs = Counter()
    for info in content:
        eb = info['eyebrow']
        if eb is None or not info['head_lines']:
            continue
        sigs[(int(round(eb.x / 10.0)), eb.font_size, int(round(info['head_lines'][0].x / 10.0)))] += 1
    if not sigs:
        return
    sig, cnt = sigs.most_common(1)[0]
    ratio = cnt / float(len(content))
    if ratio >= 0.85:
        issues.append(Issue(
            'WARNING', '(全体)',
            'F4 全部の枚が同じ入り方（小ラベル→見出し）: %d/%d 枚＝%.0f%%（小ラベル x≈%d・%.0fpx、見出し x≈%d）' % (
                cnt, len(content), ratio * 100, sig[0] * 10, sig[1], sig[2] * 10),
            'レイアウトは証拠の種類で選ぶ（写真／人の言葉／数字／場面で器を変える）。小ラベルは要る枚にだけ置く'))


def decor_ok_slides(project_dir):
    """spec_lock の `decor_ok: <枚番号> <題材との関係>` を {枚番号: 理由} にする。"""
    out = {}
    for base in (project_dir, project_dir.parent):
        cand = base / 'spec_lock.md'
        if cand.is_file():
            for nums, why in DECOR_OK_RE.findall(cand.read_text(encoding='utf-8', errors='replace')):
                for n in re.split(r'\s*[,、]\s*', nums.strip()):
                    if n.isdigit():
                        out[int(n)] = why.strip()
            break
    return out


def check_decor(project_dir, infos, issues):
    """F6: 文字も写真も無い飾りのグループ（題材とつながらない記号）が無いか。"""
    ok = decor_ok_slides(project_dir)
    for info in infos:
        root = info['root']
        if root is None:
            continue
        for g in root.iter('{%s}g' % SVG_NS):
            if 'decor' not in (g.get('id') or '').lower():
                continue
            has_text = any(True for _ in g.iter('{%s}text' % SVG_NS))
            has_img = any(True for _ in g.iter('{%s}image' % SVG_NS))
            shapes = sum(1 for el in g.iter() if _tag(el) in SHAPE_TAGS)
            if has_text or has_img or shapes < 5:
                continue
            if info['n'] in ok:
                issues.append(Issue('INFO', info['file'].name,
                                    'F6 飾り（図形 %d 個）は decor_ok で許可済み: %s' % (shapes, ok[info['n']] or '理由なし')))
            else:
                issues.append(Issue(
                    'WARNING', info['file'].name,
                    'F6 文字も写真も無い飾り（<g id="%s">・図形 %d 個）＝題材とつながらない記号' % (g.get('id'), shapes),
                    '消す。題材そのもの（町家の立面など）を描く時だけ、spec_lock に `decor_ok: %d <題材との関係を1文>` を書く'
                    % info['n']))
            break


def _registered_diagram(info, brief):
    """F7(d): 図・表のグループがあり、brief.proof に diagram / table として出典付きで登録してあるか。
    returns (図表のグループがあるか, 登録されているか)"""
    has_group = False
    root = info['root']
    if root is not None:
        for g in root.iter('{%s}g' % SVG_NS):
            if not EVIDENCE_GROUP_RE.search(g.get('id') or ''):
                continue
            shapes = sum(1 for el in g.iter() if _tag(el) in SHAPE_TAGS)
            texts = sum(1 for _ in g.iter('{%s}text' % SVG_NS))
            if shapes >= 3 and texts >= 3:
                has_group = True
    registered = False
    if has_group and brief:
        for pr in _proofs(brief):
            if (pr.get('kind') in ('diagram', 'table') and info['n'] in _int_list(pr.get('slides'))
                    and str(pr.get('src') or '').strip()):
                registered = True
    return has_group, registered


def slide_evidence(info, brief):
    """F7: 枚の中の証拠の要素（写真・数字・人の言葉・登録した図表）の一覧。"""
    found = []
    cw, ch = info['canvas']
    for el, ids in _elements_with_groups(info['root']):
        if _tag(el) != 'image' or _in_bg(ids) or any('decor' in i for i in ids):
            continue
        w = _parse_len_px(el.get('width'), cw) or 0.0
        h = _parse_len_px(el.get('height'), ch) or 0.0
        if w * h >= 0.04 * cw * ch:
            found.append('写真')
            break
    for ln in info['body']:
        if ln.font_size >= TALK_FLOOR_FS and re.search(r'[0-9０-９]', ENUM_PREFIX_RE.sub('', ln.text)):
            found.append('数字')
            break
    # 同じ <text> の行はつないでから探す（2026-09-28 反証: 研修報告 v2 の 04 の「英語を勉強する／だけで／満足していた」は
    # 3つの tspan に割れていて、1行ずつでは「」が閉じないので人の言葉に数えられていなかった）
    for t in joined_blocks(info['body']):
        if QUOTE6_RE.search(t):
            found.append('人の言葉')
            break
    if _registered_diagram(info, brief)[1]:
        found.append('図表')
    return found


def check_re_evidence(infos, brief, issues):
    """F7: R・E の枚に証拠の要素が最低1つあるか（文字を削っても、証拠のない空の枚は通さない）。"""
    for info in infos:
        if info['role'] not in ('R', 'E'):
            continue
        if slide_evidence(info, brief):
            continue
        msg = 'F7 証拠の要素（数字・写真・人の言葉・登録した図表）が1つも無い %s の枚（「%s」）' % (
            info['role'], info['head'][:20])
        has_group, _ = _registered_diagram(info, brief)
        if has_group:
            msg += '。図のグループはあるが brief.proof に diagram / table として出典付きの登録が無いので数えない'
        issues.append(Issue('ERROR', info['file'].name, msg,
                            '削った説明の代わりに、その枚の主張を証明する数字・写真・人の言葉・場面を1つ置く（brief.proof から）'))


def check_re_thin(infos, has_notes, issues):
    """F8: R・E の枚が、スライドとノートを合わせても薄すぎないか（ノートへ移した中身が、ノートにも無い）。"""
    if not has_notes:
        return
    for info in infos:
        if info['role'] not in ('R', 'E'):
            continue
        s = sum(len(ln.text) for ln in info['body'])
        nt = len(re.sub(r'\s', '', SECONDS_RE.sub('', info['notes'])))
        if s + nt < 200:
            issues.append(Issue(
                'WARNING', info['file'].name,
                'F8 スライドとノートを合わせて %d 字（スライド %d 字＋ノート %d 字・目安 200 字以上）＝中身が消えている' % (
                    s + nt, s, nt),
                'ノートへ移した理由・背景を、ノートに書き戻す。スライドには証拠を1つ置く'))


def check_quote_layout(infos, issues):
    """Q1・Q2: 複数行に割った引用「…」の組み方（2026-09-28 本人指摘「言語よりもの位置が少しおかしい」）。
    1つの <text> が2行以上で、最初の行が「で始まり、その行で」が閉じていない時だけ見る
    （1行目で閉じて2行目が「誰の言葉か」の行なら、複数行の引用ではない）。"""
    for info in infos:
        q1 = None
        q2 = None
        for group in text_groups(info['lines']):
            if len(group) < 2:
                continue
            first = group[0]
            t0 = first.text.strip()
            if not t0.startswith(('「', '『')):
                continue
            close = '」' if t0.startswith('「') else '』'
            if close in t0:
                continue
            if first.anchor == 'middle':
                if q1 is None:
                    q1 = t0
            elif first.anchor != 'end':
                # 2行目以降を1字（font-size の半分以上）下げていない行があるか
                if any(ln.x - first.x < first.font_size * 0.5 for ln in group[1:]) and q2 is None:
                    q2 = t0
        if q1:
            issues.append(Issue(
                'WARNING', info['file'].name, 'Q1 複数行の引用を中央揃えにしている（%s…）' % q1[:14],
                '1行に収めるか、左揃えで2行目以降を1字下げる（中央揃えだと行ごとに頭の位置がずれて「が浮く）'))
        if q2:
            issues.append(Issue(
                'WARNING', info['file'].name, 'Q2 引用の2行目以降が1字下がっていない（%s…）' % q2[:14],
                '2行目以降の x を1字ぶん（font-size）右へ下げ、「の後ろの字と頭をそろえる'))


# ----------------------------------------------------- 意味の検査（M1〜M11） ---
# 2026-10-01 本人「今のスライド生成は結局何を言いたいのか伝わらない」。元の資料は Kiminori Yokoi
# 「AI臭い文章とは何なのか」（豊洲会 2026-09-28。https://speakerdeck.com/nasuvitz/ai-kusai-bunshou-toha-nanina-no-ka）。
# AI臭い文章の3つの特徴＝(1) 不要な対比・否定・留保から入り、主文を直接書かない (2) 抽象語や比喩的な動詞で、
# 何をするのかが曖昧 (3) 短文・対句・不自然な読点・名詞化で、内容以上に印象的に見せる。
# 判定の問い＝「書き手の説明なしに、この文だけで誰が・何を・どうしたが1通りに決まるか」。1通りに決まる文は拾わない。
# 語の一覧ではなく型で拾う（F2 は対句の型、ここは省略・比喩・溜めの型）。意味が通るかの最終判定は R1
# （slide-reader が文字だけで言い直せたか）で、ここは読み手が補わされる箇所の手がかり＝WARNING。
# 各 fix の書き直し例は資料の修正例を書き言葉にした物。語の一覧の一部は yomiyasu（MIT・Copyright (c) 2026 nanaism）が元で、
# 正規表現はこちらで直した。2回目（同日）に、3つの検査器で共通の試験集
# ~/.claude/skills/humanize/scripts/tests/ai_smell_cases.json の全件に合わせて直した（試験は test_deck_doctor.py の CORPUS）。
M_SPLIT_RE = re.compile(r'[。．！？!?]+|　+')
# 色の無い丸・四角の絵文字の字（⚪⚫◽◾⬛⬜）。字の形の ○●◽◾■□ と同じ形で、PDF の箇条書きの丸（Wingdings の丸）を字に戻すと
# この字になる（教員の授業資料の PDF の「⚫種別」「⚫履修に必要な知識・能力」。7回目 2026-10-01 に、今日の前の版
# d6f2b634 との比べで M8 に当たった482字は、どれも行の頭だった）。行の頭では ● と同じ箇条書きの印（M_MARK_RE）で、M8 に数えない
# （_emoji）。色の付いた丸（🔴 未解決）は状態を色で飾る印なので印にしない。実験レポートの検査器 check_ai_likeness.py の
# MONO_SHAPE_EMOJI（行の頭の ⚫ は箇条書きの印）と同じ字
M_MONO_SHAPE = '⚪⚫◽◾⬛⬜'
# 行の頭の箇条書きの印（・■ など）と番号（1. ／ (1) ／ ①）。文の頭の型（M3・M7）は印を外してから見る
M_MARK_RE = re.compile(r'^(?:[\s・\-‐→■□●○◆◇▶▷•＊*' + M_MONO_SHAPE + r']+'
                       r'|(?:[0-9０-９]{1,2}[.．)）](?![0-9０-９])|[(（][0-9０-９]{1,2}[)）]|[①-⑳])\s*)')
# この字で終わる行の次の行は、同じ文の続き（助詞・読点・て形で行を折り返した物）。それ以外の行の次の行は新しい文の頭
# （句点の無い箇条書きを tspan で1行ずつ並べた物。2回目の反証で M1・M3・M7 を同じ扱いにそろえた）
M_WRAP_END_RE = re.compile(r'[をがはにでとのへもやて、,「（(]$')
# 接続の語で終わる行も、前の行の続き（「ファイルから」⏎「読むようにする。」。3回目の反証）。行の終わりは NFKC にしてから見る
M_WRAP_WORD_RE = re.compile(r'(から|まで|ので|ため|けど|けれど|のに)$')
# 助動詞・接続の語で始まる行も前の行の続き（文は助動詞から始まらない。旧PCにあった授業の pptx の「…トラブルを招か」「ないように、…」）
M_ROW_CONT_RE = re.compile(r'^(ない|なかっ|ように|ような|ため|ので|から|けど|けれど|のに|ながら|ます|ません|です|でし|だっ|られ|させ|れる|れた)')
M_SENT_END_RE = re.compile(r'[。．！？!?]$')   # 句点で終わる行（箇条書きの項目ではなく文）

# M1（特徴(1)）: 短い否定文で前振りし、短い肯定文で決める型（「依存構造は分割できない。動かしながら引き返す」）
M_NEG_END_RE = re.compile(r'(ない|ず|ません|ぬ)$')
# 否定の形でも否定ではない言い方（推量の かもしれない・義務の ないといけない・強調の に他ならない・はず）は数えない。
# 〜なかった（「LEDは点灯しなかった。配線を見直した」）は起きた事を順に書いた報告で、言い切りの前振りではないので
# M_NEG_END_RE に入れない（2回目の反証）
M_NEG_NOT_RE = re.compile(r'(かもしれ|しれ|に違い|にちがい|ないといけ|なければなら|ねばなら|ざるを得|ざるをえ|はず|'
                          r'に(他|ほか)なら)(ない|ず|ぬ)?$'
                          # 評価・点検の報告（問題はない・異常はない・悪くない・申し分ない）は、意味は「よい・問題が無い」の肯定
                          # （4回目 2026-10-01 試験集の追加分「配線に問題はない。電源を入れる。」「仕事は、悪くない。給料も、まあまあ。」。
                          # 文章の検査器の NEG_NEUTRAL と同じ語）
                          r'|(?:(?:問題|異常|支障|遜色)(?:は|が|も)?(?:あり)?|悪く(?:は)?|申し分(?:あり)?)(?:ない|ません)$')
# 2文目が否定かどうかは、言い切りの後ろの「〜んです」「〜のだ」も含めて見る（「頭のなかには、答えはないんです」「電源の容量が
# 足りないのだ」は否定→否定の組で、否定→肯定ではない。4回目 2026-10-01。文章の検査器の NEG_END と同じ）。
# 1文目には広げない（人の文の当たりを増やさないため。資料の例の1文目はどれも「〜ない」で言い切る）
M_NEG_END2_RE = re.compile(r'(ない|ず|ません|ぬ)(?:ん?です|のだ|んだ|のです)?$')
# 1文目が「〜が・は ない」（何かが無いという存在の否定）で、2文目に時か場所の語と を の目的語がある組は、予定や出来事を順に書いた
# 報告（「明日は授業がない。午前中に実験レポートを仕上げる。」）。過去の「その日は授業がなかった。図書館で課題をした。」と同じ
# （4回目 2026-10-01。文章の検査器の EXIST_NEG・WHEN_WHERE と同じ）
M_EXIST_NEG_RE = re.compile(r'[一-鿿々ァ-ヶーA-Za-z0-9](?:が|は|も)(?:ない|ありません)$')
M_WHEN_WHERE_RE = re.compile(r'今日|明日|あした|明後日|今週|来週|今夜|今晩|朝|昼|夕方|夜|午前|午後|放課後|[0-9]+(?:時|日|分)'
                             r'|[一-鿿々ァ-ヶー]で')
M_CONT_HEAD_RE = re.compile(r'^(ため|ので|から|が|けど|けれど|のに|と|まま|うち|よう|ほど|くらい|場合|時|とき|こと|もの|人|方|なら|ば)')
M_TOKEN_RE = re.compile(r'[一-鿿々〆]+|[ァ-ヶー]{2,}|[A-Za-z]{2,}')
# M1 の除外: 主題と目的語のそろった否定文と、同じ動詞の肯定文の組（「コンデンサは直流を通さない。交流は通す」）は性質の対比。
# 2文目の主語は1文目の主題に1通りに決まり、省いた物が無い。「速さは要らない。しかし正確さは要る」（何の速さかが無い）は拾う
M_TOPIC_OBJ_RE = re.compile(r'^[^、,]+?は[^、,]+?(を|には|では|に|へ|から)')
# 文が自分の主語（名詞＋が・は）を持つか（M1 の箇条書きの組の判定）
M_OWN_SUBJ_RE = re.compile(r'(?<=[一-鿿ァ-ヶーA-Za-z0-9」])[がは]')
# 前の文との関係（但し書き・言い換え・理由）を言葉で示す接続の語。逆接の しかし・でも は、対比で決める資料の型のままなので入れない
# （試験集 neg_then_pos-hit-04「速さは要らない。しかし正確さは要る」・hit-11「…知らない。でも、…」は拾う）
M_NEG_LINK_RE = re.compile(r'(ただし|但し|つまり|だから|なので|そのため|したがって|従って|よって)')
# 2文目が逆接の語＋読点の後に指示語で前の文を受ける形（「今回は補正を入れていない。ただ、これだと画面の外へ出てしまう。」）は、
# 前の文の事実の結果を書いていて、省いた物は前の文にある（6回目 2026-10-01。本人の個人レポートの文で、
# 試験集 neg_then_pos-miss-27 は文章・レポートとも miss。文章の検査器の CONTRA_THEN_DEMO と同じ語）。
# 「でも、お互いの歩みが街を救う。」（指示語で受けない）は拾う
M_CONTRA_DEMO_RE = re.compile(r'^(ただ|でも|しかし|だが|けれど|けれども|ところが)[、,]\s*'
                              r'(この|その|あの|これ|それ|あれ|ここ|そこ|そう|こう)')
# 2文目が言いさしで終わる（「その他・・・」「など…」）＝言い切っていないので、決めの肯定文ではない（6回目 2026-10-01。旧PCにあった
# 授業の班発表の3枚目の調査理由の箇条書き「電車やバスの中でやることがない。　…その他・・・」）。
# 文は NFKC 済みなので … は ... になる
M_TRAIL_OFF_RE = re.compile(r'(?:・{2,}|\.{2,}|‥|…)$')
# 式・記号が抜けた写し（6回目 2026-10-01）。Word の数式（OMML）や図の中の記号は、文字を取り出すと消えて、語の入る所が空く
# （本人の実験 テーマ4 プレレポート「電流を、電圧およびで表す。」、先生 経済学入門 生産物市場の均衡 2.docx「の状態を、
# 生産物市場の均衡と定義する。」・3.3 利潤最大化と短期費用関数 2.docx「生産活動は、のとき行われ、供給関数は、」）。
# 空いた所の印＝並べる語（および・または 等）のすぐ後ろに助詞が来る所と、文の頭か読点の直後に格助詞（を・が・は・に・で・へ）や
# 連体の の が来る所（助詞は前に語が無いと使えない）。こういう文は、読点の数や短い語の後の読点（M3・M11）と、文の組（M1・M2）を
# 字面から決められないので見ない。スライドの字は Claude が書くので式も文字のまま残り、この形にはならない
M_GAP_RE = re.compile(r'(?:および|及び|ならびに|並びに|または|又は|もしくは)\s*[をがはにでへのと]'
                      r'|(?:^|[、,]\s*)[をがはにでへ](?=[一-鿿々ァ-ヶーA-Za-z0-9])'
                      r'|(?:^|[、,]\s*)の(?=[一-鿿々ァ-ヶーA-Za-z0-9]|とき|ため|よう|もと|うち)')

# M2（特徴(3)）の除外（2回目の反証）: 条件の と（「抵抗を大きくすると電流は小さくなる」）でつないだ組は、量の関係を
# 両向きに書いた説明。数の入った組（「実測値は理論値より5%低かった」「コピーした値に1を加算する」）は手順・測定の記述で、
# 資料の型（数も固有名も無い言い換え）ではない
M_COND_TO_RE = re.compile(r'(?<=[るいた])と(?![言い思考呼聞])')
# M2 の1文の中の対句（4回目 2026-10-01 試験集の追加分）: 連用中止（「変え、」「導き、」「作り、」）と て形（「理解して、」）の読点で
# 1文を節に分け、隣り合う節を2文の組と同じ _chiasmus で見る（「道具が人を変え、人が道具を選ぶ」「理論が測定を導き、測定が理論を
# 確かめる」）。2文に割った「道具が人を変える。人が道具を選ぶ。」と同じ型。文章の検査器の RENYO_COMMA・
# swapped_clauses と同じ切り方
M_RENYO_COMMA_RE = re.compile(r'(?<=[一-鿿々][えきしちにびみりいけせてねへめれげべぎじ])[、,]|(?<=[てで])[、,]')
M_DIGIT_RE = re.compile(r'[0-9０-９]')
# 語の後ろの平仮名がこの助詞で始まる時は、役割をこの助詞だけにする（「電圧をかけた」と「電圧を」は同じ を の役割）。
# で・が などは送り仮名の頭にもなる（「遮熱できる」「上がる」）ので、送り仮名にならない を・は だけ
M_CASE_RE = re.compile(r'[をは]')

# M3（特徴(3)）: 短い語の後の読点で溜める（「前提を、経路が代わりに添える」「規則は、機械で止めて」）
M_TAME_RE = re.compile(r'^([^、,]{1,4}?)(を|は|が|も|に|へ|で|と|より)[、,]')
# 溜めとして拾うのは、述語の項（〜を・〜が・〜は）と比べる より（「装置より、」）の後の読点だけ。読点の前の語は名詞（漢字・カタカナ・
# 英数字で終わる語、「学び」「考え」「流れ」のような送り仮名の付いた名詞（漢字＋み・び・き・え・り 等。形容詞の 〜い と、
# 副詞の「先ず」「確か」は入れない）と、「使うこと」「休むことを」のような こと・もの・の で名詞にした節、「上位2つ」の数＋つ）。
# 次の物は普通の日本語なので拾わない（語の一覧ではなく形で外す。3回目の反証 2026-10-01。前は語の一覧 M_TAME_OK_RE で外していて、
# 一覧に無い「でも、」「ところが、」「確かに、」「仮に、」「一つ目は、」「1点目は、」「以上より、」「では、」「運営面では、」を
# 本人の発表・志望書・レポートと yomiyasu の人の文で誤検知した）:
#   ・接続の語・文全体にかかる副詞（でも・ところが・確かに・要するに・仮に・具体的には・基本的に）＝助詞が に・も・で か、語が名詞でない
#   ・場面の枠（運営面では・警告では・最近では・二分探索とは）＝は の前が で・に・と・へ
#   ・時・順番の枠（今日は・今回は・次は・最初は・以前は・実験後は・一つ目は・1点目は・第2に）＝M_TAME_FRAME_RE
#   ・出典の より（表1より・図5より・以上より）と手段の「により」＝YORI_SOURCE_RE と、語が名詞でない（〜に）
#   ・主題の は の後の読点で、述語まで言い切る文（先生のスライド「変数は，使用する前に宣言する必要がある」「C言語は、…から処理が
#     始まる」、旧PCにあった授業の pptx の「棒グラフは、カテゴリごとの数値を比較する」）＝主題の後の読点は普通の書き言葉。は で溜めるのは、
#     言い切らずに助詞・て形で止めた文（資料の型の「規則は、機械で止めて」「離島は、まず1軒から」）だけ（人の文の母集団で、M3 の
#     当たりの7割がこの形の誤検知だった。を・が・より は、述語まで言い切る「前提を、経路が代わりに添える」も拾う）
M_TAME_NOUN_END_RE = re.compile(r'(?:[一-鿿々〆ァ-ヶーA-Za-z0-9０-９）)」]|(?<=[一-鿿])[みびきえりちれけめげぎじ]|こと|もの|'
                                r'(?<=[ぁ-ゖ])の|[0-9０-９一二三四五六七八九十]つ)$')
M_TAME_FRAME_RE = re.compile(
    r'^(?:今|昨|来|毎|翌|先|次|当|初|前|本)[日回年週月朝晩夜]?$'
    r'|^(?:最初|初め|最後|最終日?|以前|以後|以降|最近|現在|将来|当時|今後|従来|当初|後日|前日|普段|日頃)$'
    r'|[一-鿿](?:後|前)$'
    r'|^(?:[0-9０-９一二三四五六七八九十]+(?:つ|点|番|回|個)?目|第[0-9０-９一二三四五六七八九十]+[^、,]{0,2}|もう(?:一|1|１)つ)$')
# 前の文を受ける語（これを・その横を）・後ろを指す語（次の2つを・以下の手順を）と疑問詞（何を）の後の読点は普通の日本語
# （指示語の見出しは M4 が別に見る）
M_TAME_REF_RE = re.compile(r'^(これ|それ|あれ|ここ|そこ|この|その|あの|次の|以下の|上記の|下記の|何|なに|どれ|どちら|誰|だれ|どこ|いつ)')
# 読点の後ろに、数・英字の名前・図表の番号・節（〜ように・〜まで・〜ながら）・名前を定める言い方（〜と呼ぶ）が続き、
# 述語で言い切る文は、長い修飾語との境を示す普通の読点で、省いた物が無い（「電圧を、0Vから10Vまで1V刻みで変化させた」
# 「周波数を、出力電圧が最大になるように調整した」、先生の授業のスライド「ループは，(要素数-1)回繰り返される」）。
# 資料の型「前提を、経路が代わりに添える」と、言い切らずに助詞・て形で止めた「離島は、まず1軒から」は拾う
# 4回目（2026-10-01 試験集の追加分）: 時・条件の節（〜てから・〜たら・〜場合）も同じ。「試料を、温度が下がってから取り出した」
# 「電源を、教員が確認してから入れた」の が は節の中の主語で、主文の主語は書き手のまま（文章の検査器の TAME_RE と同じ）
M_TAME_DETAIL_RE = re.compile(r'[0-9０-９A-Za-z]|ように|まで|範囲|ながら|たが|だが|ので|ため|うちに|とき|と呼|という'
                              r'|てから|でから|たら|だら|場合')
# 言い切らずに止めた文の終わり。「〜すること」「〜するもの」は名詞で言い切った文（先生の指示「準備すること」）なので入れない
M_FRAG_END_RE = re.compile(r'(から|まで|へ|に|で|(?<!こ)と|て|を|が|は|も|(?<!も)の|や)$')

# M4（特徴(2)）: 指す物が書いていない（片方・前者・見出しの頭の指示語）
# 指示語は語の頭だけ: 「そうめん」「こうもり」は語の一部、「これから」「ここ数年」は時の語なので拾わない（2回目の反証）
M_DEICTIC_HEAD_RE = re.compile(r'^(この|その|あの|(これ|それ|あれ|ここ|そこ|あそこ|こちら|そちら|あちら)(?!から)'
                               r'(ら|が|を|は|に|で|も|と|の|へ|まで|だ|こそ)|(こう|そう|ああ)(して|した|する|いう|いった|なる|なった|やって|だ))')
M_VAGUE_REF_RE = re.compile(r'もう片方|片方|前者|後者|(こちら|そちら|あちら|どちら)側')
# 何の片方かが同じ所に書いてあれば、指す物は1通りに決まる（2回目の反証）: 「リード線の片方」「片方の端子」「もう片方の手」と、
# 前に組を出してある「2本のリード線のうち、片方を」「DB更新とメッセージ発行を別々に行うと、片方だけ」「銅線とアルミ線を比べた。前者の方が」。
# 組は型で見る（3回目の反証 2026-10-01。前は助数詞の一覧に 行・件 が無く「締切台帳に2行を新設した。前者は」を、
# 名前の後ろの括弧・空白を挟む「フィンガープリント（データの指紋）と指紋認証（…）は別物」を組と見なかった）:
#   2つを数える語（2＋助数詞・両〜・ペア・一対・〜のうち）か、名詞（括弧・空白を挟んでもよい）と名詞を と でつないだ所
M_PAIR_RE = re.compile(r'(?<![0-9０-９])[2２二両]\s*(?:つ|[一-鿿ァ-ヶー]{1,3})|ペア|一対|うち|'
                       r'[一-鿿ァ-ヶーA-Za-z0-9）)」]\s*と\s*[一-鿿ァ-ヶーA-Za-z0-9（(「]')
# 「片方が〜の〜」で後ろの名詞を飾る節（6回目 2026-10-01）: 「MCP4725のVOUTに片方が鰐口クリップの線を接続した。」（本人の実験の
# テーマ2 プレレポート・完成レポートの手順5・6）の「片方が鰐口クリップの」は 線 を飾る節で、片方＝その線の片側に決まる
# （「片方の端子」の 片方の と同じく、何の片方かが同じ文にある）。は は飾る節の中に入らないので が だけ。
# 飾る節の語も飾られる名詞も物の名前の時だけ（「片方が全体の品質を決める」は 品質 が抽象の語なので、片方 は 決める の主語＝拾う）
M_SIDE_REL_RE = re.compile(r'が([一-鿿々ァ-ヶーA-Za-z0-9]+)の([一-鿿々ァ-ヶーA-Za-z0-9]+?)(?:を|に|が|へ|と|で|から|まで|$)')

# M5（特徴(2)）: 比喩の動詞・方向の比喩。原理（2回目の反証・親の判断）＝抽象的な物（データ・設計・前提・時間・判断・品質・
# 議論・関係など）が主語か目的語の時だけ拾い、人・物・薬・物質・建物が主語や目的語の文字どおりの文は拾わない。
# 比喩の動詞は、相手（主語・目的語・行き先）が抽象の語（M_ABSTRACT_NOUN）の時だけ拾う（_metaphor・_arg_abstract）。
# 下の M_LITERAL_RE（人・生き物・物・薬・物質・建物・場所の名前）は、動詞の相手ではなく、向き・質感の語の文字どおりの見分け
# （「レバーを右側に倒す」「海溝の深淵」「木の板に浮き彫り」）にだけ使う。3回目の反証（2026-10-01）で、動詞の相手がこの一覧に
# 無ければ拾う作りをやめた（一覧に無いコンデンサ・ホテル・タオル・ノートを相手にした文を拾っていた）
M_LITERAL_RE = re.compile(
    # 人・生き物（代名詞・家族・役割の語、〜人・〜者・〜員・〜家・〜士・〜師、魚へんの字、植物）
    r'私|僕|俺|自分|彼|母|父|祖[父母]|兄|姉|弟|妹|息子|娘|子ども|子供|先輩|後輩|先生|教授|友人|友達|学生|生徒|'
    r'職人|警察|医師|医者|患者|ダイバー|[一-鿿](?:人|者|員|家|士|師)(?![一-鿿])|金\u9b5a|犬|猫|鳥|虫|[\u9b5a-\u9c7f]|'
    r'トマト|植物|苗|'
    # 物（道具・部品・機器・材料・食べ物）
    r'ゴミ|ごみ|缶|瓶|箱|紙|布|木(?!曜)|板|石|金属|ガラス|綿|生地|革|漫画|試作品|部品|端子|ケーブル|配線|チップ|IC|基板|'
    r'スイッチ|レバー|ジョイスティック|ブレーキ|冷房|暖房|エアコン|カメラ|画像|画面|写真|映像|モニタ|釘|針|刃|ナイフ|矢|'
    r'船|艦|'
    # 薬・物質
    r'薬|湿布|わさび|塩酸|硫酸|食塩|砂糖|試料|ハンダ|はんだ|氷|バター|'
    # 建物・場所・体
    r'建物|町家|民家|塀|崖|山頂|頂上|川|海(?!外)|湖|池|庭|水深|穴|井戸|病院|倉庫|鉱山|皮膚')
# 抽象的な物の語（比喩の動詞の相手がこれなら比喩）。文章の検査器（作者の環境の jp_ai_check.py）の ABSTRACT_INFO・ABSTRACT_IDEA と同じ語の写し
# （3回目の反証 2026-10-01。前のこの一覧は人の気持ち（熱意・思い・気持ち）を含み、データ・時間・答え を含まなかったので、
# 「感謝の気持ちを手紙に添えた」はスライドだけが当て、「答えが芽生える」は文章だけが当てた）。
# 抽象的な物＝情報・処理、考え・計画・議論、時間、性質（〜性・〜化・〜感）。人の気持ち（不安・友情）は入れない。
# 一覧は片方だけ直すと2つの検査器の判定がずれるので、直す時は両方を直す（test_deck_doctor.py が2つの語の集合を比べる）
M_ABSTRACT_INFO = (
    # 情報・処理（コンピュータの中の物と、その動き）
    r"データ|情報|値|記録|ログ|設定|処理|例外|エラー|バグ|不具合|テスト|キャッシュ|ジョブ|タスク|プロセス|同期|更新|通知"
    r"|掃除|仕組み|機能|システム|コード|ロジック|経路|ルート|フロー|運用|手順|方法|方針|ルール|規則|状態|品質|性能"
    # ソフトウェア・情報の物（「スキルが静かに壊れる」）
    r"|スキル|スクリプト|プログラム|ソフト|アプリ|ボット|サーバー|サービス|ファイル|フォルダ|リポジトリ|パイプライン"
    r"|ワークフロー|モデル|データベース|メッセージ|リクエスト|イベント"
)
M_ABSTRACT_IDEA = (
    # 作業・出来事（「裏取りを深掘りする」）
    r"確認|調査|検証|分析|検討|作業|実装|説明|裏取り|整理|準備|対応|改善|開発|研究|レビュー"
    # 測る作業と、測って見える現象・振る舞い・ばらつき（2026-10-01 試験集 B3-hit-09「測定値のばらつきを1つずつ潰した」・
    # B12-hit-07「位相差の挙動を深掘りした」・B13-hit-13「測定の手触りがつかめた」。文章とスライドの担当が
    # 人の文（本人の文・授業ノートの .md 1160本・過去のデッキ・人の文 約8.9万単位）で当たりの増減0を確かめた語）
    r"|測定|現象|挙動|ばらつき"
    # 考え・計画・議論（分野・領域・内容・工夫 のような、考えの範囲や中身を指す語も含める）
    r"|前提|根拠|理由|原因|問題|課題|論点|懸念|リスク|可能性|候補|仮説|選択肢|設計|判断|戦略|計画|構想|理論|論理|理屈"
    r"|議論|意見|案|提案|アイデア|考え|発想|視点|観点|理解|学び|知識|経験|成果|結論|答え|本質|テーマ|目標|狙い"
    r"|意図|価値|信頼|関係|文化|空気|雰囲気|努力|才能|習慣|分野|領域|範囲|内容|要素|要因|工夫|手法|手段|表現"
    # 時間
    r"|時間|一日|半日|週末|休日|休み|土日|連休|一晩|徹夜|午前|午後|人生|青春"
)
# 性質を表す語尾（男性・女性の 性 は人なので外す）と、形容詞を名詞にした「〜さ」（良さ・正確さ）・程度の「差」
# （「設計の筋の良さが、ここで効いてきます」「この差が、最終的に効いてくる」）。文章の検査器では ABSTRACT_IDEA の最後に入っている。
# 構造 は物にも考えにも使う語なので、この一覧ではなく M_STRUCT_RE で修飾する語から決める（文章の検査器の STRUCT_NOUN と同じ）
M_ABSTRACT_SUFFIX = r"(?<![男女異])性|化|感|観|(?<=[一-龥ぁ-ゖ])さ|差"
M_ABSTRACT_NOUN = M_ABSTRACT_INFO + '|' + M_ABSTRACT_IDEA + '|' + M_ABSTRACT_SUFFIX
# 物にも考えにも使う建物の部分の語（構造・土台・基盤）。抽象かどうかは修飾する語で決める（「議論の土台」「問題の構造」は比喩、
# 「町家の土台」「建物の構造」「結晶構造」は文字どおり。3回目の反証で「イオン注入で結晶構造が壊れる」を拾っていた）
M_STRUCT_RE = re.compile(r'(?:土台|基盤|構造|柱|骨組み|骨格|足場|屋台骨)$')
# 辞書に載る決まった組み合わせ（抽象の名詞でも意味が1通りに決まる。文章の検査器の COLLOC_TSUBUSU と同じ）＝時間・暇を潰す。
# 崩れる の組み合わせ（計画・体調が崩れる）は、崩れる の枝で土台の語だけを拾うので要らない（_metaphor）
# 時間の語（文章の検査器の TIME_NOUN と同じ）。潰す の時間の語は全部（「時間を潰す」と同じく「土日を潰した」「休日を潰した」も辞書
# どおり＝その時間を使ってしまう。4回目 2026-10-01 試験集の追加分。文章の検査器の COLLOC_TSUBUSU と同じ）
M_TIME_NOUN = (r'(?:時間|一日|半日|丸一日|週末|休日|休み|土日|連休|一晩|徹夜|夜|午前|午後|人生|青春'
               r'|[0-9０-９一二三四五六七八九十数何半丸]+(?:時間|日|週間?|晩|か月|ヶ月|カ月|年))')
M_COLLOC_TSUBUSU = r'時間|暇|' + M_TIME_NOUN
# 時・順序の語。「半年後に効いてくる」「本番直前に効いた」「午後にたどり着いた」の「〜に」は、いつのことかで、何に効くか・
# どこへ着くかの相手ではない（4回目 2026-10-01。文章の検査器の TIME_ORDER と同じ）
M_TIME_ORDER = (r'(?:' + M_TIME_NOUN + r'|後|前|直前|直後|最後|最初|先|のち|あと|当日|本番|今後|将来|最終|終盤|序盤|途中|以降'
                r'|今日|明日|昨日|今週|来週|先週|今月|来月|朝|昼|夕方|晩|深夜)')
# 名詞の後ろに空白をはさんで付けた部品・量の名札（「コンデンサ C1」「時定数 τ」「試料 A」「プローブ CH2」）。本人の実験レポートの
# 「測定値 Rx は」の書き方。名札は物を指す記号なので、抽象か物かは前の名詞で決める（4回目 2026-10-01。文章の検査器の LABEL_TAIL と同じ）
M_LABEL_TAIL = r'(?<=[一-鿿々ァ-ヶー])[ 　]+(?:[A-Za-z]{1,4}[0-9０-９]{0,3}|[0-9０-９]{1,3}|[α-ωΑ-Ω])[ 　]*$'
# 人を指す語（代名詞・家族・立場と、〜さん・〜者・〜員 のような人の語尾）。静かに・黙って で主語が人かを見る（文章の検査器の PERSON_END と同じ）
M_PERSON_END = (r'(?:私|僕|俺|自分|彼|彼女|彼ら|母|父|兄|姉|弟|妹|祖父|祖母|夫|妻|息子|娘|子ども|子供|先生|教授|先輩|後輩|友人|友達'
                r'|上司|部下|同僚|店員|客|誰か|みんな|皆|人|[一-鿿ァ-ヶー](?:さん|くん|君|ちゃん|氏|様|者|員|長))$')
# 連体の節の後ろに来ても、動詞の相手（主語・目的語）にならない名詞（「深掘りした結果」「壊れた後」。文章の検査器の OUTER_NOUN と同じ）
M_OUTER_NOUN = r'^(?:結果|後|あと|ため|時|とき|際|場合|こと|事|もの|物|ところ|所|上|うえ|まま|通り|とおり|様子|ほう|方|分|旨)$'
# 静かに・黙って の後の動詞の分け方（4回目 2026-10-01。文章の検査器の QUIET_PROCESS・QUIET_HUMAN と同じ）:
#   処理の動作（壊れる・失敗する・スキップする 等）は、名詞が無くても拾う（「16回も黙って失敗し続けた」は何が失敗したかが無い）。
#   人の動作（捨てる・無視する・死ぬ）は、相手を前の文に書くことが多いので名詞が無ければ拾わない（「母は私の漫画を見つけた。
#   そして黙って捨てた。」）。ほかの動詞（消える・止まる・劣化する）は、相手が情報・処理の物（M_ABSTRACT_INFO）の時だけ拾う
#   （「ログが静かに消える」「ジョブが黙って止まる」「品質が静かに劣化していく」。考え・時間は文字どおり静かでありうる）
M_QUIET_RE = re.compile(r'(静かに|黙って|ひっそりと?)(壊れ|壊す|壊し|失敗|沈黙|無視|捨て|スキップ|破棄|握りつぶ|死ぬ|死ん'
                        r'|(?!溶|潰|効|崩|添|語|寄り添|見守|芽生|実を|花開|深掘|深堀|掘り下)[一-鿿々ァ-ヶー]+)')
M_QUIET_PROCESS = r'壊れ|壊す|壊し|失敗|沈黙|スキップ|破棄|握りつぶ'
M_QUIET_HUMAN = r'無視|捨て|死ぬ|死ん'
# 物を動かす・変える動詞（相手が抽象の語の時に比喩）。「溶け込む」（なじむ）は別の語なので外す（文章の検査器の B2_RE と同じ）
M_PHYS_VERB_RE = re.compile(r'(?<![一-鿿])(?:壊れ|壊す|倒[しすさ]|刺さ|響[くいか]|溶け(?!込)|溶か|転が|握[るり]|踏み込|紐解|磨[くいか]|'
                            r'育[つてち]|掘り下げ|落とし込|引き返|積み上げ|織り込|紡[ぐいが]|灯|咲[くいか]|芽生|宿[るり]|'
                            r'編み|束ね|彩)')
# 人の動作を抽象の主語に当てる擬人化（資料の例「経路が代わりに添える」・yomiyasu の「データが語る」）。相手が主語（〜が・〜は）の
# 時だけ（「感謝の気持ちを手紙に添えた」「資料を添えて出した」の 〜を は、人が添える文字どおりの文）。文章の検査器の PERSONIFY_RE と同じ
M_PERSONIFY_RE = re.compile(r'添え(る|た|て|ま)|(?<!物)語(る|っ[たて])|寄り添(う|っ|い)|見守(る|っ|り)')
# 時間の語（「丸一日溶かした」「週末を溶かした」の時間を物のように溶かす比喩）
M_TIME_RE = re.compile(r'(丸|まる)?(一日|半日|週末|休日|連休|時間|[0-9０-９一二三四五六七八九十数半]+(時間|日|週間?|か月|ヶ月))')
# 「効く」が「機能が働く」の意味になる、コンピュータの仕組みの語（「キャッシュが効く」）と、効く を比喩の評価にする副詞
M_MECH_RE = re.compile(r'キャッシュ|インデックス|設定|フィルタ|フィルター|オプション|ショートカット|最適化|圧縮')
# 4回目（2026-10-01）: あとあと・後々・のちのち・最終的に も、時間がたって効いてくる比喩の副詞（文章の検査器と同じ）
M_EFFECT_ADV_RE = re.compile(r'地味に|じわじわ|じわり|後から|あとから|あとあと|後々|のちのち|最終的に|ボディブロー|ジャブ')
# 効く の文字どおりの相手（薬・器具・調味料）。「後から効いた」と副詞が付いても文字どおり（文章の検査器の EFFECT_THING と同じ）
M_EFFECT_THING = (r'薬|剤|湿布|麻酔|注射|ワクチン|冷房|暖房|エアコン|クーラー|ヒーター|ブレーキ|わさび|ワサビ|辛子|からし|スパイス'
                  r'|香辛料|肥料|消毒')
# 様子を表す「〜に」（副詞）。何に効くかの相手ではない（「確実に効く」「一気に効く」「実際に効いた」。文章の検査器の ADVERB_NI と同じ。
# 4回目 2026-10-01 に 実際・一般・同時・直接・逆・自然・単純・さら・つい・ため を足して揃えた）
M_ADVERB_NI = (r'(?:的|特|本当|非常|一気|確実|着実|意外|大い|実|実際|妙|確か|すぐ|地味|静か|密か|徐々|次第|急|更|既|常|特別'
               r'|十分|充分|大幅|一般|同時|直接|逆|自然|単純|さら|つい|ため)')
# 助詞の前に来ても名詞の終わりではない字（動詞・形容詞の活用語尾など。文章の検査器の _NOT_NOUN_END と同じ）
M_NOT_NOUN_END = 'るうくすつむぶぐぬいただなてでばかよねわにへはがをもの'
# 動詞の相手を探す節の切れ目（逆接・理由の「〜けれど、」「〜ので、」、条件の「〜ば」「〜たら」、並べた項目の「・」の前は別の節。
# 文章の検査器の _clause と同じ）
M_CLAUSE_CUT_RE = re.compile(
    r'(?:けれど(?:も)?|けど|のに|(?<=[るいたうくすつむぶぐだな])ので|(?<=[るいたうくすつむぶぐだ])(?:から|が)|ため)[、,]'
    r'|(?<=[えけせてねへめれげべ])ば|(?:たら|だら)(?=[、,\s]|[一-鿿々ァ-ヶA-Za-z0-9])|[・①-⑳]')
# 目的語（〜を）と動詞の間に、目的・同時の「〜ように」「〜ために」「〜ながら」で別の動詞がある時は、その〜を は間の動詞の目的語
# （本人の報告書「その答えをはっきり書けるように積み上げていきます」の 答えを は 書ける の目的語で、積み上げる の相手ではない）。
# 主題・主語（〜は・〜が）は節をまたいで後ろの動詞にもかかるので、この扱いにしない（「祖父は眠るように静かに死んだ」の 祖父 は 死んだ の主語）
M_OBJ_OTHER_VERB_RE = re.compile(r'(?<=[うくすつぬむゆるぐぶ])(?:ように|ために)|ながら')
# 数と単位で書いた条件（「1GHzでは」「10 V以上では」「85℃を超えると」）。文は NFKC 済みなので ℃ は °C・Ω は Ω になる
M_UNIT_COND_RE = re.compile(r'[0-9]+(?:\.[0-9]+)?\s*[A-Za-zΩμ°%]+\s*(では|で|だと|以上|以下|を超え|未満|より)')
# 空間の向き（「レバーを右側に倒す」は文字どおり。「残さない側に倒す」「安全側に倒す」は判断を向きに例える比喩）
# 向きの語は語の頭から（「除外側」の 外 は向きではない）
M_SPATIAL_RE = re.compile(r'(?<![一-鿿])(右|左|上|下|前|後ろ?|奥|外|内|手前|向こう|こちら|そちら|あちら|こっち|そっち|あっち|'
                          r'東|西|南|北|ON|OFF|オン|オフ|反対)(の)?$')
# 比喩の名詞が、その名詞の本来の場面（事件・病院・船・鉱山・川・遊び）の文にある時は文字どおり（2回目の反証:
# 「警察は防犯カメラの映像から犯人を絞り込んだ」「病院で処方箋をもらった」「船の羅針盤が北を指していた」）
# 4回目（2026-10-01 試験集の追加分）: 犯人 の本来の場面に、作り話・遊びの中（推理小説・ドラマ・人狼ゲーム・犯人役）を足した
# （「推理小説を最後まで読んで犯人を当てた」「人狼ゲームで犯人役になった」）
M_FRAME = (
    ('犯人|黒幕', r'警察|刑事|探偵|事件|容疑|逮捕|捜査|防犯|犯行|被害|裁判|推理|小説|ミステリ|ドラマ|映画|漫画|アニメ|ゲーム|人狼|犯人役'),
    ('処方箋', r'病院|医師|医者|薬局|薬|診察|患者'),
    ('羅針盤', r'船|航海|方位|磁石|[東西南北]を指'),
    ('起爆剤', r'鉱山|爆破|発破|火薬|爆薬|倉庫|保管'),
    ('架け橋', r'川|谷|建設|工事'),
    ('切り札', r'トランプ|カード|ゲーム|手札'),
)
# 語そのものが比喩で、文字どおりの読みが無い語（質感・体温を装う語・腹落ちなど）
# 熱量・体温 は物理量・体の温度でもあるので、後ろの名詞の質感として言う形（「熱量のある議論」「体温の伝わる資料」）だけを拾う
# （yomiyasu の「質感を装う語」。3回目の反証 2026-10-01。「体温を測った」「熱量の高い燃料」「手の体温が伝わる」は文字どおり）
M_FIGURE_RE = re.compile(r'腹落ち|伴走|血肉に|血の通った|地に足の(つい|着い)た|意思決定OS|虚飾|'
                         r'肌感覚?(?![一-鿿])|温度感(?![一-鿿])|(熱量|体温)の(ある|こもった|伝わる)|メンタルモデル')
# 語のすぐ前の名詞が物・場所なら文字どおりになる語（「海溝の深淵」「この川の鮒は泥臭い」「島と本土は地続き」「画像の解像度を上げる」）。
# 境地 は、辞書に載る「新境地を開く」を外す（文章の検査器の QUALIA_RE と同じ。3回目の反証で「新境地を開いた」だけの文を拾っていた）。
# 手触り は、抽象の物の手触り（「現場の手触りのある提案」）だけを拾う（_touch。「布の手触り」「タオルの手触り」は文字どおり）
# 4回目（2026-10-01 試験集の追加分）: yomiyasu の「認知を装う語」の メンタルモデル を M_FIGURE_RE に足し、境地 は辞書に載る
# 決まった言い方（新境地・無我の境地・悟りの境地・無心の境地）を外した（文章の検査器の QUALIA_RE と同じ）
M_FIGURE_LITERAL = ('深淵', '(?<!新)(?<!無我の)(?<!悟りの)(?<!無心の)境地', '泥臭', '地続き', '解像度', '刺さる')
# 本人が自分の文で使う比喩の語（2026-10-01 本人の判断「① 参考の扱いにする」）。比喩の型に当たっても WARNING に
# せず、INFO の「M5参考」で表示だけする（文章の検査器は info、実験レポートの検査器は参考層）。本人の標準ルール「本人が書いた文の
# 当たりを増やさない」による。本人の文の実物: 1年の報告「アイデアを実際の動きに落とし込んで」・授業のレポート
# 「他国との交流の架け橋になり」・研修会の感想文「説明も刺さった」（試験集 metaphor_other-hit-08・
# hit-12・miss-43〜45）。語の判定（相手が抽象か）は M5 と同じで、出す重さだけを変える（_metaphor の skip_owner）
M_OWNER_WORD_RE = re.compile(r'落とし込|架け橋|刺さ')
M_REF_NAMES = {'M5': '本人も使う比喩の語（落とし込む・架け橋・刺さる。参考）'}

# M6（特徴(3)）: 見出しを抽象の動作の名詞で止める。3回目の反証（2026-10-01）で、yomiyasu の例の「観光の再定義」「地域との共創」
# 「島の魅力の再発見」「持続可能性の追求」の語尾を足した（旧PCの人のスライド・本人の文書の母集団では、この4つで終わる行は0件）
M_NOMINAL_END_RE = re.compile(r'(化|性|の(実現|強化|向上|推進|最適化|構築|確立|創出|醸成|促進|深化|再定義|共創|再発見|追求))$')
# M7（特徴(1)）: 主文の前に「重要なのは」「結論から言うと」を置き、言う前に言うことを予告する前置きの決まり文句。
# 文の頭だけを見る（「抵抗が重要な理由は2つある」は拾わない）。語は yomiyasu（MIT・Copyright (c) 2026 nanaism）の
# 「前置フィラー」が元で、「最も・一番・特に・本当に・何より」と「大事・大切・肝心」「〜なことは」の言い換え、
# 前に付く接続語（だが、・そして、）を足した。M3（溜めの読点）と同じ文なら M7 だけを出す。
# HEAD は文の頭（印を外した物）だけ、SAY は文のどこにあっても拾う。
# HEAD の後ろに中身（「重要なのは、応答時間だ」）が来る時が前置き。「大事なのは分かっているが」「重要なのはどれか、グループで
# 話し合った」（〜のは が「分かる」の主語・問いの形＝後ろが が・か・ので で終わるか、分か・知っ で始まる）は前置きではない（2回目の反証）
# 4回目（2026-10-01 試験集の追加分）で、語でなく型で足した（文章の検査器の PREFACE_RE と同じ型）:
#   ・「〜な点は」（「重要な点は、配線の抵抗である」＝「重要なのは、」と同じ分裂文）
#   ・書き手の言い方・読み手の注意を向けさせる動詞＋たいのは・すべきは（伝えたいのは・強調したいのは・注目したいのは・特筆すべきは）。
#     注意・確認の動詞（注意すべき点は・気をつけたいのは）は、何に気をつけるかを教える本当の指示（先生のスライド「線形探索の際に
#     注意すべき点は、…終了条件を正しく設定することです」先生の授業資料 5枚目）なので入れない
#   ・〜がちなのは（見落としがちなのは）
#   ・要点を指す語＋は、（ポイントは、・肝は、・カギになるのは、）。読点が付く形だけ（「鍵は机の上にある」「ポイントは3つある」は拾わない）
# 「重要な点は2つある」のように、ある・いる で言い切る文は、数を言い切っていて予告ではない（M_PREFACE_NOT_RE）
M_PREFACE_HEAD_RE = re.compile(
    r'^(?:(?:だが|でも|しかし|そして|また|ただ|一方で?|さて|つまり|なお|さらに)[、,]\s*)?'
    r'(?:まず|ここで|特に|本当に|何より|なにより|最も|一番|いちばん)?'
    r'(?:(?:重要|大事|大切|肝心|避けたい|厄介|面白い|おもしろい|興味深い)な?(?:の|こと|点)は'
    r'|(?:注目|着目|特筆|強調|言及|指摘)すべき(?:点|なの|こと)?は'
    r'|(?:伝え|強調し|注目し|着目し|言い|述べ|指摘し|お伝えし|共有し)たい(?:の|こと)は'
    r'|[ぁ-ゖ一-鿿]{1,6}がちな(?:の|こと)は'
    r'|(?:ポイント|カギ|鍵|肝|キモ)(?:[とに]なる(?:の|こと))?は(?=[、,]))')
M_PREFACE_NOT_RE = re.compile(r'(か|が|けど|けれど|ので|のに|ても)$|^(分か|わか|知っ|知ら|言うまでも)|(?<!で)(ある|あります|いる|います)$')
# 前置きの語の一覧に無くても、「〜のは、」の後ろが名詞だけで止まる分裂文（「見落としがちなのは、電源の容量」「鍵となるのは、現場の声」
# 「見えてきたのは、島の課題」）は、言う前に言うことを予告して溜める同じ型なので拾う（3回目の反証 2026-10-01。yomiyasu の
# 「前置フィラー」の型）。後ろに述語がある「驚いたのは、装置より、人の熱意だった」「分からなかったのは、…というより、」や、読点の無い
# 「復号できるのはBさんだけ」（人の解説の普通の書き方）は拾わない。人の文の母集団（本人・先生・旧PCのスライドと文書）では0件
M_CLEFT_RE = re.compile(r'^(?:(?:だが|でも|しかし|そして|また|ただ|一方で?|さて|つまり|なお|さらに)[、,]\s*)?'
                        r'[^、,。「」]{1,14}?[なたるい]のは[、,]\s*(.+)$')
# 「結論から言うと」「結論から言えば」「一言で言えば」。「結論から言えるのは2点」（結論から導ける事）・「結論から言うのが
# 基本」（言い方を話題にする文）・「端的に言えない」は拾わない（2回目の反証）。
# 「正直に言うと」「実を言うと」「本音を言えば」と、文の頭の「正直なところ」も同じ前置き（yomiyasu の「前置フィラー」に
# 「正直に言うと」が載っていて、この語だけ抜けていた。3回目の反証 2026-10-01）。「正直、」（言う が後ろに無い）は拾わない
# 4回目（2026-10-01 試験集の追加分）: 言い方の前置き「結論を先に言うと」「簡単に言うと」「平たく言えば」も同じ（文章の検査器の
# PREFACE_RE の語。ひらがなの「ひとことで言うと」は、本人のグループの Docker 発表のスライドで当たったので
# 入れない＝人の文の当たりを増やさない）。後ろが「・・・」「…」で止まる物は、次の行に中身を回す札（先生の経済学の資料「∴　簡単に言えば・・・」
# 経済学入門の資料）で、文の前置きではないので拾わない（文章の検査器が「：」「**」の札を外すのと同じ）
M_PREFACE_SAY_RE = re.compile(r'(結論から|結論を先に|端的に|一言で|簡単に|平たく|正直に|実を|本音を)'
                              r'((言う|いう)と|(言え|いえ)ば)(?![・….])|'
                              r'結論から申し上げ(ると|れば|ます)|^正直なところ')
# M8（特徴(3)）: 絵文字で内容以上に目立たせる。拾うのは、そのままで絵文字の形で出る字（Unicode の Emoji_Presentation）と、
# FE0F を付けて絵文字にした字。★・✓・①・FE0F の無い ⚠ のような字の形の記号は拾わない（2回目の反証で ⚡❓⛔⏰⌛🇯🇵🆗❗☕ を足した）
M_EMOJI_RE = re.compile(
    '[\u231a\u231b\u23e9-\u23ec\u23f0\u23f3\u25fd\u25fe\u2614\u2615\u2648-\u2653\u267f\u2693\u26a1\u26aa\u26ab'
    '\u26bd\u26be\u26c4\u26c5\u26ce\u26d4\u26ea\u26f2\u26f3\u26f5\u26fa\u26fd\u2705\u270a\u270b\u2728\u274c\u274e'
    '\u2753-\u2755\u2757\u2795-\u2797\u27b0\u27bf\u2b1b\u2b1c\u2b50\u2b55'
    '\U0001F004\U0001F0CF\U0001F18E\U0001F191-\U0001F19A\U0001F1E6-\U0001F1FF\U0001F201\U0001F21A\U0001F22F'
    '\U0001F232-\U0001F236\U0001F238-\U0001F23A\U0001F250\U0001F251\U0001F300-\U0001FAFF]'
    '|[\u2190-\u2bff\u3030\u303d\u3297\u3299]\ufe0f')
# 絵文字を物の名前として書いた文（「GitHub の ⭐ は 17,956 だった」＝後ろに助詞）と、括弧の中の逐語の写し
# （「回答（👍／🙅‍♂️）」）は飾りではないので拾わない
M_EMOJI_NAME_RE = re.compile(r'\s*[はがをのにでとも](?=[\s　0-9０-９]|$)')
M_PAREN_RE = re.compile(r'\([^()]*\)|（[^（）]*）')
# M9（特徴(1)）: 日本語の行をコロンで終え（「以下の3つ：」）、主文を次の行に回す英語直訳の書き方（yomiyasu の「文末コロン」）。
# 英語の行（コロンで続きを示すのが普通）・「日時：10月1日」のように同じ行に値がある物・PREP の札（F5 が拾う）は見ない
M_COLON_END_RE = re.compile(r'[:：]\s*$')
M_JA_RE = re.compile(r'[ぁ-ゖァ-ヺ一-鿿々]')
# M9 で拾うのは、予告の語（次の・以下・下記・数＋つ）がある行と、述語（〜った・〜ない・〜する）か助詞（〜は・〜には・
# 〜と）でコロンの直前が終わる行＝文を言いかけて中身を次の行に回す行だけ（「具体的には：」「まとめると：」「その理由は：」は
# 2回目の反証で足した）。「入力：」「絶対パス：」「長所：」のような名詞の見出し語は、人が書いた授業の
# スライドで普通の組み方（旧PCにあった授業の pptx で、次の段落に中身が続く物が52種類・36ファイル。反証 2026-10-01）なので拾わない。
# 述語を行の終わりだけにしたのは、「画面に文字列を表示するプログラム：」（授業の配布資料 12枚目）の
# ように、述語の後ろに名詞が付いた行も見出し語だから（述語を行のどこでも拾うと、授業の pptx で1行誤検知した）。
# 助詞の と は、動詞の後の条件の と（「まとめると：」「言い換えると：」「手順を文章で書くと：」）だけ。「確認すること：」「分かったこと：」「やること：」の
# こと の と は名詞の見出し語の一部なので拾わない（3回目の反証 2026-10-01。先生の課題文「授業終了時に確認しておくこと：」）
# 4回目（2026-10-01 試験集の追加分）: 数＋つ は、「ポイントは3つ：」「〜の3つ：」のように は・の の後（数が述語・予告になる形）だけ。
# 名詞に数を付けた見出し「測定の注意点2つ：」は名詞の見出し語なので拾わない（実験レポートの検査器 check_ai_likeness.py の
# COLON_END_RE と同じ）
M_COLON_LEAD_RE = re.compile(r'次の|以下|下記|(?:は|の)[0-9０-９一二三四五六七八九十]+(つ|点|個|項目)|'
                             r'(った|ない|する|した|れる|ます|です|(?<!と)は|には|では|(?<=[うくすつぬむゆるぐぶた])と)\s*[:：]\s*$')
# 行の全体が接続の語＋コロン（「例えば：」「要するに：」「つまり：」「その結果：」）も、続きを次の行に回す予告（4回目 2026-10-01）。
# 次の行が文（句点か述語で終わる）の時だけ拾う。次の行が図の名前・語句（教員の物理の講義資料「例えば：⏎PからQへの移動」）なら
# 「例：」と同じ見出し。語と決め方は文章の検査器の CONNECTIVE_COLON・実験レポートの検査器の CONNECTIVE_COLON_RE と同じ
M_COLON_CONNECTIVE_RE = re.compile(r'^(?:例えば|たとえば|要するに|つまり|すなわち|その結果|結果として|したがって|よって|そのため|ゆえに)'
                                   r'\s*[:：]\s*$')
# 次の行が式・コード（日本語が無く、= などの記号がある「V = RI」）なら、文で書き切れない物を示す普通のコロン（2回目の反証）
M_FORMULA_RE = re.compile(r'[=＝<>≦≧≤≥+*/^(){};]')
# 次の行がシェルのコマンド（$ の後か、小文字の英語のコマンド名＋空白・オプション・パス）で日本語が無い時も、コマンドの前置き
# （ラズパイの「次のコマンドを実行する：⏎sudo raspi-config」「次のコマンドで起動する：⏎python3 led.py」。4回目 2026-10-01。
# 実験レポートの検査器の NEXT_COMMAND_RE と同じ）
M_NEXT_COMMAND_RE = re.compile(r'^(?:\$\s*)?[a-z][A-Za-z0-9_.+\-]*(?:\s+\S|$)')
# M10（特徴(3)）: ダッシュ（— ―）で文を途中で区切り、間を取って印象を足す英語直訳の書き方（「速さ—それがすべてだった」）。
# 前後に空白がある物（見出しの区切り「English — Quick Reference」・副題「― 本レポート ―」）、矢印の線（←——→）、
# 英語の中の物は拾わない。― の1本がカタカナ・英数字の直後にある物（「フィルタ―」「Vcc―」）は長音・マイナスの打ち間違い
M_DASH_RE = re.compile(r'[\u2014\u2015]+')
M_ARROW = '←→↔⇔⇒⇐'
# ダッシュを記号として使う物も拾わない（3回目の反証 2026-10-01）: 読点で区切った並びの2つ以上の項目にダッシュがある対応の表
# （授業ノートの演習問題「りんご—青果A、みかん—青果B」）と、名詞の見出しと中身を区切る議事録の書き方
# （「イベントの提案―予算箱の設置は可決」「新入生歓迎―花道」＝左に助詞の は・が 等が無く、右が指示語で始まらず、述語で終わらない）。
# 述語の終わり（だ・である・た・る・い・ない・ます・です）。ダッシュの右がこれで終わらなければ名詞の句（体言止め）
M_PRED_END_RE = re.compile(r'(?:だ|である|です|ます|た|る|い|ない|ず|う)$')
# M11（特徴(3)）: 読点の打ちすぎ（本人「てんおおい」・作者の文章の修正ログ）。読点が4つ以上あり、3つ以上が
# 助詞・送り仮名の後（溜めの読点）で、溜めの読点の間が平均6字以下の文。名詞・数を並べる読点（「抵抗、コンデンサ、コイル」
# 「1 V、2 V、3 V」）と、長い節をつなぐ読点は拾わない。並べる読点は数からも外す（3回目の反証 2026-10-01。先生の実験テキストの
# 「まず，LEDを点灯した状態で，電圧VFE，VFB，VBE，…値を測定し，」と課題文の「方法は，停止，跳ね返り，または元の位置に戻す，の
# いずれでもよい．」を、名前の並びが平均の字数を下げて拾っていた）:
#   ・短い名詞の区切り（平仮名で終わらない区切り）が3つ以上続く所
#   ・「〜、または〜、のいずれか」の項目（または・および・の いずれ 等で始まる区切りと、その前の項目）
M_ENUM_HEAD_RE = re.compile(r'^\s*(?:または|又は|および|及び|あるいは|もしくは|ならびに|の(?:いずれ|どれ|うち)|など|といった)')
M_FIX = {
    'M1': '否定の短文で前振りし、短い肯定文で決める型。省いた対象・条件・状態を書いて1文にする'
          '（例:「依存構造は分割できない。動かしながら引き返す」→「依存関係を分離できないため、稼働中に変更し、問題が出たら元の状態に戻す」）',
    'M2': '同じ語を入れ替えて2回言う型。何をして、どんな効果があるかを1文で書く'
          '（例:「読んで身に付けてから、効く。効いてから、身に付く」→「実際の業務で使い、効果を確かめながら使い方を覚える」）',
    'M3': '短い語の後の読点で溜めて強調している。読点を取り、誰が何をするかを書く'
          '（例:「前提を、経路が代わりに添える」→「運用者は問い合わせ先に応じた前提条件を参照する」）',
    'M4': '見出しと1行は単独で読まれる（目次・配布の PDF・後から読む人）。指す物の名前を書く'
          '（例:「片方だけを見て基準を作ると、もう片方が壊れる」→「開発速度だけを基準にすると、保守性の要件を満たせなくなる」）',
    'M5': '抽象的な物を、物を動かす動詞や方向で述べている。何をどうするかを普通の動詞で書く'
          '（例:「判断に迷うものは、残さない側に倒す」→「採否を判断できない項目は、原則として除外する」。'
          '「データが静かに壊れる」→ どの値がエラーを出さずに変わるかを書く。「丸一日溶かした」→「設定に8時間かかった」の形で、何に何時間かを書く）',
    'M6': '見出しが「〜化」「〜性」「〜の向上」のような名詞で止まり、誰が何をどうしたかが無い。主語と動詞で結論を書く',
    'M7': '主文の前に「重要なのは」「結論から言うと」と予告している。前置きを消して、重要な中身そのものを主語と動詞で書く'
          '（例:「重要なのは、応答時間だ」→「応答時間を2秒以内にする」の形）',
    'M8': '絵文字は中身を足さずに目立たせるだけ。消して、強調したい物は言葉（数字・固有名詞）か図で示す',
    'M9': 'コロンで行を終えて、中身を次の行に回している（英語直訳の書き方）。「〜は次の3つ」と言い切るか、前置きの行を消して中身から書く',
    'M10': 'ダッシュで文を区切って間を取っている（英語直訳の書き方）。ダッシュを消し、「〜は〜だ」の1文か2文に分けて書く'
           '（例:「速さ—それがすべてだった」→「応答時間を半分にしたことが評価を決めた」の形）',
    'M11': '読点が多く、文が細切れになっている。要らない読点を取り、主語と述語の間を短くする'
           '（例:「まず、電源を、入れて、少し、待ってから、測る」→「電源を入れて1分待ってから測る」）',
}


def _rows_to_sents(rows, merge=True):
    """1つの <text> の行（見出しは見出しの行の全部）を (文のリスト, 組にしない境目の集合) にする。
    人の言葉「」の中身は見ない（中身だけを消して「」は残す。「改善は「フェリーの時間帯」、」の読点を短い語の後の読点と
    見誤らないため。2回目の反証で、過去のデッキの「改善は、伸ばすのはに絞った」の誤検知を見つけた）。
    句点で文に割るほか、句点の無い箇条書きの行（前の行が助詞・読点・て形で終わらない行、印で始まる行）も文の頭として割る。
    merge=False（見出し）は、前と同じく1行ずつ文の頭として割る（大きな字の見出しは句の切れ目で行を変える。
    「いちばん驚いたのは、」「装置より、人の熱意だった」の2行目の溜めを見る）。文ごとに NFKC にする。
    組にしない境目＝句点の無い箇条書きの行が3つ以上並ぶ時の、行と行の境目（長所・短所・手順の並びの項目どうしは、
    前振りと決め（M1）・言い換え（M2）の組ではない。授業の班発表の「検索漏れが発生しない／検索効率が向上する」）。
    集合の k は「sents[k] と sents[k+1] の間」。
    3回目の反証（2026-10-01）で、文の途中で行を折り返した人のスライドを文の頭として割っていたのを直した:
    ・行の終わりは NFKC にしてから見る（先生のスライドの全角の「，」で終わる行「…直接関係しないが，」）
    ・「〜から」「〜まで」「〜ので」「〜ため」「〜けど」で終わる行も前の文の続き
    ・句点で文を終える書き方の <text>（どれかの行が句点で終わる）では、句点で終わらない行は文の途中の折り返し
      （「ソース中に直接書いた」「初期値を、」「ファイルから」「読むようにする。」は1文）。印で始まる行は、どの書き方でも文の頭"""
    text = QUOTE_SPAN_RE.sub('「」', '\n'.join(rows))
    lines = [row.strip() for row in text.split('\n') if row.strip()]
    kuten = any(M_SENT_END_RE.search(r) for r in lines)
    chunks = []
    cur = ''
    for r in lines:
        end = unicodedata.normalize('NFKC', cur)
        joined = (M_WRAP_END_RE.search(end) or M_WRAP_WORD_RE.search(end) or M_ROW_CONT_RE.match(r)
                  or (kuten and not M_SENT_END_RE.search(cur)))
        if cur and (not merge or M_MARK_RE.match(r) or not joined):
            chunks.append(cur)
            cur = r
        else:
            cur += r
    if cur:
        chunks.append(cur)
    nlist = len([c for c in chunks if not M_SENT_END_RE.search(c)])
    sents = []
    cut = set()
    for c in chunks:
        for s in M_SPLIT_RE.split(c):
            s = unicodedata.normalize('NFKC', s).strip()
            if s and s != '「」':
                sents.append(s)
        if merge and nlist >= 3 and sents and not M_SENT_END_RE.search(c):
            cut.add(len(sents) - 1)
    return sents, cut


def _meaning_units(info):
    """意味の検査の単位: (場所の名前, 文のリスト, 組にしない境目)。見出し（見出しの行の全部）・小ラベル・本文（<text> ごと）。"""
    units = []
    heads = [ln.text for ln in info['head_lines']]
    skip = set(id(ln) for ln in info['head_lines'])
    if heads:
        units.append(('見出し', heads))
    eb = info['eyebrow']
    if eb is not None:
        skip.add(id(eb))
        units.append(('小ラベル', [eb.text]))
    for group in text_groups([ln for ln in info['body'] if id(ln) not in skip]):
        units.append(('本文', [ln.text for ln in group]))
    out = []
    for where, rows in units:
        sents, cut = _rows_to_sents(rows, merge=(where != '見出し'))
        if sents:
            out.append((where, sents, cut))
    return out


def _drop_mark(s):
    """文の頭の箇条書きの印・番号を外す（「・重要なのは」「1. 重要なのは」「1.電流を、」）。"""
    return M_MARK_RE.sub('', s, count=1).strip()


def _neg_pair(s, s2):
    """M1: 短い否定文 s の次に短い肯定文 s2 が来る組か（推量・義務・過去の報告・性質の対比・F2 の対句は除く）。"""
    a = s.rstrip('、,')
    if not (3 <= len(s) <= 18 and 3 <= len(s2) <= 18):
        return False
    if not M_NEG_END_RE.search(a) or M_NEG_NOT_RE.search(a):
        return False
    if M_NEG_END2_RE.search(s2.rstrip('、,')) or M_CONT_HEAD_RE.match(s2):
        return False
    if M_EXIST_NEG_RE.search(a) and M_WHEN_WHERE_RE.search(s2) and re.search(r'[一-鿿々ァ-ヶーA-Za-z0-9）)」]を', s2):
        return False   # 存在の否定の後の予定・出来事の報告（「明日は授業がない。午前中に実験レポートを仕上げる。」）
    if not _statement(s2):
        return False   # 2文目が見出し語・名詞だけ・矢印で始まる（「欠点:」「大容量」「☞信頼性」）＝肯定文の決めではない
    b2 = _drop_mark(s2)
    if re.search(r'こと$', b2.rstrip('、,')) or M_NEG_LINK_RE.match(b2) or M_CONTRA_DEMO_RE.match(b2):
        # 2文目が指示の言い切り（「考察に必要なものを適宜掲載すること」）か、前の文との関係を言葉で示す（「ただし、」「つまり」）
        # ＝主語も対象も1通りに決まる、先生の課題文・本人の発表の普通の書き方（3回目の反証 2026-10-01）。
        # 逆接の語の後に指示語で前の文を受ける「ただ、これだと…」も同じ（6回目。M_CONTRA_DEMO_RE の上）
        return False
    t1 = M_TOKEN_RE.findall(a)
    if t1 and t1 == M_TOKEN_RE.findall(s2):
        # 2文目が、1文目の否定を外しただけの同じ事柄（先生 経済学入門 比較生産費説 2.docx の図の2つの欄「2国間に貿易成立しない」
        # 「2国間に貿易成立」）。同じ事を否定してから肯定する2文は互いに打ち消し合うので、前振りと決めではなく、2つの場合を並べた物
        # （表・場合分け）。資料の型は、否定した物と別の物を肯定する（「答えを教えない。問いを返す」）。6回目 2026-10-01
        return False
    if has_contrast(s):
        return False   # 「速度だけではない。精度も要る」「単なる道具ではない。考え方の型だ」は F2 が拾う（二重に数えない）
    if M_TOPIC_OBJ_RE.match(a):
        t1 = M_TOKEN_RE.findall(a)
        t2 = M_TOKEN_RE.findall(s2)
        if t1 and t2 and t1[-1] == t2[-1]:
            return False   # 性質の対比（「コンデンサは直流を通さない。交流は通す」）
    return True


def _statement(s):
    """M1 の2文目が肯定の言い切りの文か。見出し語（コロン入り）・名詞だけの行（「PCとスマホの連携」「大容量」）・
    矢印や ☞ で始まる行（前の行との関係を記号で書いてある）・言いさしの行（「その他・・・」）は文ではない（授業の班発表の長所・短所・
    調査理由の箇条書き）。"""
    if re.search(r'[:：]', s) or re.match(r'[⇒→☞∴∵➡]', s):
        return False
    if M_TRAIL_OFF_RE.search(s.rstrip()):
        return False   # 言いさし（「その他・・・」）は言い切った文ではない（6回目 2026-10-01。M_TRAIL_OFF_RE の上）
    return not re.fullmatch(r'[^ぁ-ゖ]*([のとや][^ぁ-ゖ]+)*', s)


def _roles(s):
    """M2 用: 語 → (出てきた順番, 語の後ろの役割)。役割は、後ろの平仮名が助詞で始まればその助詞、そうでなければ送り仮名の全部。"""
    out = {}
    for m in M_TOKEN_RE.finditer(s):
        w = m.group(0)
        if w in out:
            continue
        tail = re.match(r'[ぁ-ゖ]*', s[m.end():]).group(0)
        if tail and M_CASE_RE.match(tail[0]):
            tail = tail[0]
        out[w] = (len(out), tail)
    return out


def _chiasmus(s1, s2):
    """M2: 2つの短い文で、同じ2つの語の順番が入れ替わり、その2つの語の役割（が↔を・〜てから↔〜く）も入れ替わっているか
    （「AてからB。BてからA」「道具が人を変える。人が道具を選ぶ」）。
    「スイッチを閉じた。閉じたスイッチを開いた」（役割が同じ を のまま）・条件の と の組・数の入った組は拾わない"""
    if M_COND_TO_RE.search(s1) or M_COND_TO_RE.search(s2):
        return False
    if M_DIGIT_RE.search(s1 + s2):
        return False
    if re.match(r'[⇒→☞∴∵➡]', _drop_mark(s2)):
        return False   # 2文目が矢印で始まる＝前の文との関係を記号で書いた手順（「⇒ 代入したい変数を「＝」の右に書く」）
    r1 = _roles(s1)
    r2 = _roles(s2)
    p1 = _token_places(s1)
    p2 = _token_places(s2)
    shared = [w for w in r1 if w in r2]
    for a in shared:
        for b in shared:
            if a == b or not (r1[a][0] < r1[b][0] and r2[a][0] > r2[b][0]):
                continue
            if not (max(p1[a]) < min(p1[b]) and max(p2[b]) < min(p2[a])):
                # 語が同じ文に2回以上出て、もう一方の語の前にも後ろにもある時は、順番が入れ替わったと言えない（6回目 2026-10-01。
                # 授業の班発表の3枚目「テレビを見る習慣がなく、普段からニュースを見ない。」「気になるニュースが
                # 見つからない。」は、見 が ニュース の前（見る）と後ろ（見ない）の両方にあり、ニュース→見 の順は2文で同じ）
                continue
            if not all(_swap_role(r[w][1]) for r in (r1, r2) for w in (a, b)):
                continue
            if r1[a][1] != r2[a][1] and r1[b][1] != r2[b][1]:
                return True
    return False


def _token_places(s):
    """M2 用: 語 → 文の中で出てきた順番の全部（_roles は最初の1回だけを見る）。"""
    out = {}
    for k, m in enumerate(M_TOKEN_RE.finditer(s)):
        out.setdefault(m.group(0), []).append(k)
    return out


def _swap_role(role):
    """M2 で入れ替わりに数える役割か。数えるのは述語の項（〜が・〜を・〜は・〜も）と、動詞・形容詞の形（〜てから・〜く・
    〜して・〜できない）。名詞の後ろの の・に・から・で・と（「メモリ上の」「ファイルに」「グラフから」）と、後ろに漢字が続く
    名詞（「ファイル中」）は、述語の項ではないので数えない（3回目の反証 2026-10-01。先生のスライドの「メモリ上のデータを，ファイルに
    書き出す」「ファイル中のデータを，メモリ上に読み込む」は、書き出す・読み込むという別の操作で、言い換えた反復ではない）。
    役割は後ろの平仮名の全部なので、の・から・まで・より・へ・や は頭だけで見る（「グラフからたくさんの」）。に・で・と は
    動詞の頭にもなる（「できる」）ので、助詞だけの時に限る"""
    if not role:
        return False
    if re.fullmatch(r'(?:の|に|へ|で|と|や|から|まで|より)(?:は|も|の)?', role):
        return False
    return not re.match(r'(?:の|から|まで|より|へ|や)', role)


def _tame(s):
    """M3: 短い語の後の読点で溜める文か（s は印を外した文）。拾うのは、名詞＋（を・が・は・比べる より）＋読点だけ
    （外す形は M_TAME_NOUN_END_RE の上に書いた）。"""
    m = M_TAME_RE.match(s)
    if not m or len(s) > 26 or M_TAME_REF_RE.match(s):
        return False
    w = m.group(1)
    p = m.group(2)
    if '「' in w:
        return False   # 「」の中に人の言葉・名前がある（「アプリ「人工無脳」は、」）＝短い語ではない
    if p == 'も' and w.endswith('より'):
        w, p = w[:-2], 'より'   # 「便数よりも、」は比べる より（過去のデッキ 06）
    if p not in ('を', 'が', 'は', 'より'):
        return False   # 〜に・〜で・〜と・〜も の後（「確かに、」「教授に、」「入力すると、」「でも、」「3本とも、」）
    if not M_TAME_NOUN_END_RE.search(w):
        return False   # 語が名詞でない（「ところが、」「先ずは、」「では、」「運営面では、」「具体的には、」）
    if M_TAME_FRAME_RE.search(w):
        return False   # 時・順番の枠（「今回は、」「次は、」「最初は、」「一つ目は、」「1点目は、」）
    if p == 'より' and YORI_SOURCE_RE.search(w):
        return False   # 出典の より（「表1より、」「以上より、」）
    rest = s[m.end():]
    if p == 'は' and not M_FRAG_END_RE.search(rest):
        return False   # 主題の後の読点で、述語まで言い切る文（「変数は、使用する前に宣言する必要がある」）
    # 同じ助詞が読点の後ろにもう一度来る（「規則は、機械は止める」）＝2つの句を分ける普通の読点
    if re.search('(?<=[^ぁ-ゖ])' + p, rest):
        return False
    if M_TAME_DETAIL_RE.search(rest) and not M_FRAG_END_RE.search(rest):
        return False
    return True


def _vague_ref(sents, k):
    """M4: 文 sents[k] の片方・前者・こちら側の指す物が、同じ単位の中に書いてないか。"""
    s = sents[k]
    m = M_VAGUE_REF_RE.search(s)
    if not m:
        return False
    if m.group(0) in ('片方', 'もう片方') and (s[:m.start()].endswith('の') or re.match(r'の[一-鿿ァ-ヶーA-Za-z]', s[m.end():])):
        return False   # 「リード線の片方」「片方の端子」「もう片方の手」（何の片方かが後ろに書いてある）
    if m.group(0) == '片方' and re.search(r'[一-鿿々ァ-ヶーA-Za-z0-9）)」]\s*[をがは]$', s[:m.start()]):
        # 「ワニ口クリップを片方だけ外し、もう片方は…」「入力端子を片方接地し」: 名詞＋を・が・は の直後の 片方 は、その名詞の
        # 片方（数の語を名詞から離して後ろに置く言い方。「学生が3人来た」の 3人 と同じ）。何の片方かが書いてあるので、
        # 同じ文の もう片方 も1通りに決まる（4回目 2026-10-01 試験集の追加分）
        return False
    mr = M_SIDE_REL_RE.match(s[m.end():])
    if (m.group(0) in ('片方', 'もう片方') and mr and not _foreign(mr.group(2))
            and not _abstract(mr.group(1)) and not _abstract(mr.group(2))):
        return False   # 「片方が鰐口クリップの線」（片方が〜の は後ろの物の名前を飾る節。M_SIDE_REL_RE の上）
    return not M_PAIR_RE.search(''.join(sents[:k]) + s[:m.start()])


def _np(s, i, parts):
    """s[:i] の中で一番近い「名詞の句＋助詞（parts の字のどれか）」の名詞の句。無ければ ''。
    名詞の句は、前の読点・空白・別の助詞の後ろから（「断線の原因はケーブルを」→「ケーブル」）。の でつないだ修飾は含む"""
    head = s[:i]
    j = max(head.rfind(c) for c in parts)
    if j < 0:
        return ''
    np = head[:j]
    np = re.split(r'[、,。\s]', np)[-1]
    return re.split(r'から|まで|より|[はがをにでもとへ]', np)[-1]


def _clause(head):
    """文の頭からの文字列を、動詞が入っている節だけに切る（M_CLAUSE_CUT_RE の前は別の節）。"""
    return M_CLAUSE_CUT_RE.split(head)[-1]


def _args(head, parts):
    """head（節の頭から動詞の前まで）の中の「名詞＋助詞（parts の語）」を、動詞に近い順に (助詞の前までの文字列, 助詞) で返す。
    文章の検査器の _args_before と同じ見方:
    ・助詞の前の字が動詞・形容詞の活用語尾（M_NOT_NOUN_END）や読点なら、その字は助詞ではない（「もう」の も・「ながら」の が）
    ・「空気のほうが」は「〜空気」で返す。「〜かを」「〜のを」「〜ことを」「〜のが」「〜ことが」は節（出来事）を相手にした物
    ・「16回も」「3人も」の数を強める も は相手ではない
    4回目（2026-10-01 試験集の追加分）で2つ足した（文章の検査器と同じ）:
    ・名詞と助詞の間の空白（「コンデンサ C1 は」「時定数 τ が」「fact-check を」）は、空白の前が名札（M_LABEL_TAIL）か英数字・記号
      なら相手として返す。本人の実験レポートの「測定値 Rx は」の書き方で、空白があるだけで相手が無いことにしない
    ・parts に の がある時は、動詞のすぐ前の「名詞＋の」（「冷房の効いた部屋」「希釈の効き方」）も相手として返す（助詞は の）"""
    found = []
    for p in parts:
        if p == 'の':
            continue
        for mm in re.finditer(re.escape(p), head):
            found.append((mm.start(), p))
    tail = head.rstrip()
    if ('の' in parts and tail.endswith('の') and len(tail) > 1
            and re.search(r'[一-鿿々ァ-ヶーA-Za-z0-9）)]$', tail[:-1])):
        found.append((len(head), 'の'))
    found.sort(reverse=True)
    out = []
    for k, p in found:
        if p == 'の':
            out.append((tail[:-1], p))
            continue
        before = head[:k]
        if not before:
            continue
        mh = re.search(r'の(?:ほう|方)$', before)
        if mh:
            out.append((before[:mh.start()], p))
            continue
        if (p == 'を' and re.search(r'(?:か|の|こと)$', before)
                or p in ('が', 'は') and re.search(r'(?:[ぁ-ゖ]の|こと)$', before)):
            out.append((before, p))
            continue
        c = before[-1]
        if c in ' 　' and (_foreign(before) or re.search(M_LABEL_TAIL, before)):
            out.append((before.rstrip(), p))
            continue
        if c in M_NOT_NOUN_END or c in '。、，,　 「（(':
            continue
        if p in ('は', 'も') and c == 'と':
            continue
        if p == 'も' and re.search(r'[0-9０-９一二三四五六七八九十百千数何]+[回個本件人枚台倍%％]$', before):
            continue
        if p == 'を' and M_OBJ_OTHER_VERB_RE.search(head[k + 1:]):
            continue
        out.append((before, p))
    return out


def _noun_end(noun):
    """名詞の終わりを見るために、後ろの括弧の補足（「IC（集積回路）」の（…））と、名札（M_LABEL_TAIL。「コンデンサ C1」の C1）を取る
    （4回目 2026-10-01。文章の検査器の _noun_end と同じ）。"""
    noun = re.sub(r'[（(][^（）()]*[）)]$', '', (noun or '').rstrip()).rstrip()
    return re.sub(M_LABEL_TAIL, '', noun)


def _foreign(noun):
    """名詞の終わりが英字・数字・記号（「IC」「LED」「水深10m」「3」）か。抽象か物かを字面で決められない。
    4回目（2026-10-01）: 式・単位・量の記号（「y = x²」「10 Ω」「sinθ」「β」）も同じにし、名札（「コンデンサ C1」）は取ってから見る
    （文章の検査器の _foreign と同じ）"""
    return bool(re.search(r'[A-Za-z0-9_`\'"\]\[)(}{<>←→↑↓+\-\\/.*#$%=²³¹⁰-⁹ΩμΩ°℃％α-ωΑ-Ω]$', _noun_end(noun)))


def _abstract(noun, words=None):
    """名詞の句 noun の最後の語が抽象的な物か（文章の検査器の _abstract と同じ見方）。
    名詞の句の全体ではなく最後の語で見る（3回目の反証 2026-10-01。前は句の全体を探して「課題のプリント」の 課題、
    「大電流が流れてメータ」の 流れ に当てていた）。
    ・「〜残らなかったの」「〜したこと」のような節（出来事・行い）は抽象
    ・物にも考えにも使う語（土台・構造）は、修飾する語（「議論の土台」の 議論、「結晶構造」の 結晶）で決める
    ・名札（「コンデンサ C1」の C1）は取って、前の名詞で決める（4回目 2026-10-01）
    ・ひらがなの「もの」は、節を名詞にする の（「〜したの」）ではなく、物（漢字）と同じ名詞なので、節の扱いにしない
      （7回目 2026-10-01。前は「も＋の」が「ひらがな＋の」に当たり、先生の実験のテーマ7,8 内容詳細レジュメ
      「(4) エッチング」の「溶解性のある各種溶液によって不要なものを溶かす．」の 不要なもの を抽象と見て M5 に当てていた。
      漢字の「不要な物を溶かす」は当たらず、書き方で判定が変わる穴だった。こと（事）は出来事なので抽象のまま）"""
    words = words or M_ABSTRACT_NOUN
    noun = _noun_end(noun)
    if re.search(r'(?:[ぁ-ゖ]の|こと|ところ)$', noun) and not noun.endswith('もの'):
        return True
    ms = M_STRUCT_RE.search(noun)
    if ms:
        pre = noun[:ms.start()]
        if pre.endswith('の'):
            pre = pre[:-1]
        if not re.search(r'[一-鿿々ァ-ヶーA-Za-z0-9]$', pre):
            return False
        return _abstract(pre, words)
    return bool(re.search(r'(?:%s)(?:点)?$' % words, noun) or re.search(r'(?:%s)$' % M_TIME_RE.pattern, noun))


def _arg_abstract(s, i, parts, no_arg, words=None, colloc=None, subject_only=False, foreign=None, rest=None):
    """s[i] の動詞の相手（同じ節の中で一番近い「名詞＋助詞（parts）」）が抽象的な物か（True なら比喩として拾う）。
    no_arg＝相手が1つも無い時に拾うか（何が〜したのかが文から決まらない物は拾う。文章の検査器の _judge_arg と同じ）。
    colloc＝辞書に載る組み合わせ（「時間を潰す」）。subject_only＝一番近い相手が主語（が・は）の時だけ拾う（擬人化）。
    foreign＝相手が英数字・記号で終わる時の答え（既定は no_arg と同じ）。
    rest＝動詞の後ろの文字列。相手が無くても拾う動詞（no_arg）で、動詞が後ろの名詞を飾る形（「静かに壊れたコンデンサを交換した」
    「黙って壊れていた自動の仕組みを」）は、その名詞が相手なので、それで決める（4回目 2026-10-01 試験集の追加分。文章の検査器の
    _judge_arg と同じ。「壊れた後」の 後 のように動詞の相手にならない名詞 M_OUTER_NOUN は相手にしない）"""
    args = _args(_clause(s[:i]), parts)
    if not args:
        if no_arg and rest is not None:
            mh = re.match(r'[ぁ-ゖ]{0,4}?(?:た|る|だ)([一-鿿々ァ-ヶーA-Za-z0-9][^、。をがはにでへもと\s]*)', rest)
            if mh and not re.match(M_OUTER_NOUN, mh.group(1)) and not _foreign(mh.group(1)):
                return _abstract(mh.group(1), words)
        return no_arg
    noun, p = args[0]
    if subject_only and p not in ('が', 'は'):
        return False
    if colloc and re.search(r'(?:%s)$' % colloc, _noun_end(noun)):
        return False
    if _foreign(noun):
        return no_arg if foreign is None else foreign
    return _abstract(noun, words)


def _not_target(before):
    """「〜に」の前の before が、何に効くかの相手ではない語（様子の副詞・時と順序の語）で終わるか（文章の検査器の _not_target と同じ）。"""
    b = before.rstrip()
    return bool(re.search(M_ADVERB_NI + r'$', b) or re.search(M_TIME_ORDER + r'$', b))


def _target_written(head):
    """効く の前に、何に効くか（「〜に」「〜への」）が書いてあるか。様子を表す「確実に」等と、時・順序の「半年後に」「直前に」は
    相手ではない（4回目 2026-10-01 に時・順序の語を足した。文章の検査器の _target_written と同じ）。"""
    h = head.rstrip()
    if 'への' in h:
        return True
    h = re.sub(r'(?:同じく|同様に|特に|よく|すぐに?|一番|いちばん|最も|もっと|大きく|強く|かなり|ちゃんと)$', '', h).rstrip()
    mm = re.search(r'[^\s、。]\s?に[もは]?$', h)
    return bool(mm) and not _not_target(re.sub(r'\s?に[もは]?$', '', h))


def _target_topic(head):
    """節の中に、何に効くかを主題にした「名詞＋には・にも」があるか（「肩こりにはストレッチの習慣が効く」「過学習には正則化が効く」）。
    様子の副詞・時と順序の語（「実際には」「最後には」）と、疑問詞＋にも（「どこにも」）は相手ではない（4回目 2026-10-01。
    文章の検査器の _target_topic と同じ）。"""
    for mm in re.finditer(r'[^\s、。，,「『（(]\s?に[はも]', head):
        before = re.sub(r'\s?に[はも]$', '', head[:mm.end()])
        if _not_target(before) or re.search(r'(?:どこ|何|なに|誰|だれ|いつ|どれ)$', before):
            continue
        return True
    return False


def _target_domain(head):
    """効く場面・領域を「名詞＋で（は・も）」で書いた形があるか（「授業・研究・PBLで実際に効くシーン」「高域では C2 が効く」）。
    どこで効くかが書いてあれば、何に効くかを書いた形（「肩こりに効く」）と同じく文から決まる（4回目 2026-10-01。人の文の母集団で、
    本人のグループの Docker 発表のスライドの「授業・研究・PBLで実際に効くシーン」に当たったので足した）。
    時・順序の「後で」・様子の語と、指示語の「ここで」（「設計の筋の良さが、ここで効いてきます」）は場面の名前ではない。
    で の後ろが平仮名（「対応できる」「設計でした」）は助詞の で ではない"""
    for mm in re.finditer(r'(?<=[一-鿿々ァ-ヶーA-Za-z0-9）)」])\s?で(?:は|も)?(?![ぁ-ゖ])', head):
        before = head[:mm.start()]
        if _not_target(before) or re.search(r'(?:ここ|そこ|あそこ|どこ)$', before):
            continue
        return True
    return False


def _effect(s, m):
    """M5 の 効く（s の m の位置）を比喩として拾うか。4回目（2026-10-01 試験集の追加分）で、文章の検査器の _judge_effect と
    同じ順に並べ直した（同じ文に同じ判定を出すため）:
    ・相手が薬・器具・調味料（M_EFFECT_THING）なら文字どおり（「鎮痛薬は後から効いた」）
    ・効いた結果を同じ文に書いた物（「前処理が効いて、ファイルが消えた」「前処理が効いてエラーが0件になった」）は、何に効いたかが
      決まるので拾わない。読点が無い時は、て の直後から結果の節（名詞で始まり、同じ節に が・を がある）が続く物だけ
    ・「効いていない」「効いてない」は「効かない」と同じ、働いていないという報告なので見ない
    ・副詞（地味に・後から・あとあと・最終的に）が付いたら拾う（「配線抵抗の影響が後から効いてくる」「一行のコメントが、あとあと
      効いてくる」。前は相手が抽象の一覧に無いと副詞があっても拾わなかった）
    ・相手が英数字・記号（「C2」「時定数 τ」「sinθ」）なら拾わない
    ・何に効くか（「肩こりに効く」「肩こりには〜が効く」「過学習には正則化が効く」）か、どこで効くか（「PBLで実際に効く」_target_domain）
      が書いてあれば拾わない。時・順序の「半年後に」「本番直前に」と、様子の「実際に」は何に効くかではない
    ・「〜効いたのは Y」「効いてくるのは Y」は Y（焦点）で決める（Y が抽象か「〜こと」なら拾う。「低域で効いてくるのは結合
      コンデンサである」は拾わない）
    ・それ以外は、相手が抽象の時（コンピュータの仕組みが効く＝キャッシュが効く は除く）と、相手が無い時に拾う"""
    head = _clause(s[:m.start()])
    rest = s[m.end():]
    args = _args(head, ('が', 'は', 'も', 'を', 'の'))
    if args and re.search(r'(?:%s)$' % M_EFFECT_THING, _noun_end(args[0][0])):
        return False
    if re.match(r'(?:て|た(?:結果|ので|ため|から))(?:[、,]|(?=[一-鿿々ァ-ヶーA-Za-z0-9「（(][^。、]*?'
                r'[一-鿿々ァ-ヶーA-Za-z0-9）)」](?:が|を)))', rest):
        return False
    if re.match(r'て(?:い)?な[いく]|ておらず|て(?:い)?ません', rest):
        return False
    if M_EFFECT_ADV_RE.search(head[-15:]):
        return True
    if args and _foreign(args[0][0]):
        return False
    # 節を主語にした「〜残らなかったのが効いている」の「どこにも」は、主語の節の中の語なので、何に効くかの相手として見ない
    clause_subject = bool(args) and bool(re.search(r'(?:[ぁ-ゖ]の|こと)$', _noun_end(args[0][0])))
    if _target_written(head) or (not clause_subject and _target_topic(head)) or _target_domain(head):
        return False
    mc = (re.match(r'(?:た|ている|ていた|てる|てい|てくる|てきた|てきている|ます|く)?のは[、,]?', rest)
          if m.group(0).endswith(('い', 'く', 'き')) else None)
    if mc:
        focus = rest[mc.end():].rstrip()
        focus = re.sub(r'(?:だ|である|です)?と(?:思|考え)[^。]*$', '', focus)
        focus = re.sub(r'(?:だ|です|である|でした|だった)$', '', focus).rstrip()
        return bool(re.search(r'(?:こと|ところ|の)$', focus)) or _abstract(focus)
    if args:
        return _abstract(args[0][0]) and not re.search(r'(?:%s)$' % M_MECH_RE.pattern, _noun_end(args[0][0]))
    return True


def _quiet(s, m):
    """M5 の 静かに・黙って＋動詞（M_QUIET_RE の m）を比喩として拾うか（4回目 2026-10-01。文章の検査器の _judge_quiet と同じ）。
    人が主語（「母は私の答案を黙って捨てた」「彼は黙って部屋を出た」）なら、人が静かに・黙って動いた文字どおりの文。
    動詞の分け方は M_QUIET_RE の上"""
    verb = m.group(2)
    head = _clause(s[:m.start()])
    if any(p in ('が', 'は') and re.search(M_PERSON_END, _noun_end(n)) for n, p in _args(head, ('が', 'は'))):
        return False
    if re.match(M_QUIET_PROCESS, verb):
        return _arg_abstract(s, m.start(), ('が', 'は', 'を', 'も'), True, rest=s[m.end():])
    if re.match(M_QUIET_HUMAN, verb):
        return _arg_abstract(s, m.start(), ('が', 'は', 'を', 'も'), False)
    args = _args(head, ('が', 'は', 'を', 'も'))
    if not args or _foreign(args[0][0]):
        return False
    return bool(re.search(r'(?:%s)$' % M_ABSTRACT_INFO, _noun_end(args[0][0])))


def _touch(s, i):
    """手触り（s[i:]）: 抽象の物の手触り（「現場の手触りのある提案」「議論の手触り」）だけ拾う。布・タオルの手触りは文字どおり
    （文章の検査器の _judge_touch と同じ）。"""
    head = s[:i]
    if head.endswith('の') and _abstract(head[:-1]):
        return True
    mm = re.match(r'(?:の|が)?(?:ある|あった|ない)', s[i + 3:])
    return bool(mm and re.match(r'(?:%s)' % M_ABSTRACT_NOUN, s[i + 3 + mm.end():]))


def _metaphor(s, skip_owner=False):
    """M5: 比喩の動詞・方向の比喩・比喩の名詞が、抽象的な物について使われているか（True なら拾う）。
    skip_owner=True は、本人が自分の文で使う語（M_OWNER_WORD_RE＝落とし込む・架け橋・刺さる）の当たりを数えない
    （その語だけで当たる文は INFO の M5参考。meaning_refs）。
    原理（本人の標準ルール・3回目の反証 2026-10-01 で全部の動詞をこの形にそろえた）: 動詞の相手（主語・目的語・行き先）が
    抽象的な物（M_ABSTRACT_NOUN）の時だけ拾い、人・物・薬・物質・建物・場所が相手の文字どおりの文は拾わない。
    前は 効く・たどり着く・黙って〜 などが「文字どおりの相手の一覧（M_LITERAL_RE）に無ければ拾う」逆向きの作りで、一覧に無い
    コンデンサ・ホテル・タオル・ノート・前処理を相手にした本人の文を拾っていた。相手の見つけ方・抽象の見方は文章の検査器
    文章の検査器の LITERAL_JUDGE と同じ（_args・_abstract・_arg_abstract）"""
    # 判断を向きに例える（資料の例「残さない側に倒す」）。空間の向き・物（レバー・スイッチ）を倒すのは文字どおり
    # 側の前が英字・数字（「ON 側」「GND 側」。空白をはさんでもよい）なら、スイッチ・端子の表示を文字どおりに倒す操作
    # （4回目 2026-10-01 試験集の追加分「トグルスイッチ SW1 は ON 側に倒した」「プローブ CH2 は GND 側に倒した」。文章の検査器の _judge_side と同じ）
    for m in re.finditer(r'(側|方向|方|ほう)に(倒[しすさ]|寄せ|傾け|振る|振った)', s):
        before = s[:m.start()].rstrip()
        if M_SPATIAL_RE.search(before) or re.search(r'[A-Za-z0-9]$', before) or M_LITERAL_RE.search(_np(s, m.start(), 'を')):
            continue
        return True
    # 失敗・放置を人の動作に例える（静かに壊れる＝エラーを出さずに値が変わる）。相手がデータ・テスト・例外・ログ（抽象）の時と、
    # 相手の無い「16回も黙って失敗し続けた」を拾う。人が主語の文（「母は私の答案を黙って捨てた」）と、物が相手の文
    # （「古いノートを黙って捨てた」「静かに壊れたコンデンサを交換した」）は文字どおり（_quiet。4回目 2026-10-01 に動詞を一覧で
    # 限らない形にした＝「ログが静かに消える」「ジョブが黙って止まる」）
    for m in M_QUIET_RE.finditer(s):
        if _quiet(s, m):
            return True
    # 時間を物のように溶かす（「丸一日溶かした」「週末を溶かした」「一日が溶けていた」）。溶かす・溶ける の一番近い相手（〜を・〜が・
    # 〜は・〜も）が時間の時と、相手が無く直前が時間の語の時だけ拾う。ほかの物（物質）が相手の文の時間は、溶かす時間の長さ
    # （「試料を塩酸で24時間溶かした」「試料 A は塩酸で24時間溶かした」。4回目 2026-10-01 に、前は を の目的語しか見ず、主題の 試料 A は
    # を相手と見なかったのを直した。文章の検査器の _judge_melt と同じ）
    for m in re.finditer(r'溶(か|け)(?!込)', s):
        head = _clause(s[:m.start()])
        args = _args(head, ('が', 'は', 'を', 'も'))
        if args:
            if re.search(M_TIME_NOUN + r'$', _noun_end(args[0][0])):
                return True
            continue
        if re.search(M_TIME_NOUN + r'$', head.rstrip()):
            return True
    # 原因・問題を物のように潰す（「原因を1つずつ潰す」「不具合の候補を順番に潰した」）。相手が物（空き缶・ケーブル・IC）なら
    # 文字どおり。「時間を潰す」「暇を潰す」は辞書に載る組み合わせ。相手の無い「1つずつ潰していく」は、潰す相手を前の文に書く
    # ことが多いので拾わない（文章の検査器と同じ）
    for m in re.finditer(r'潰(す|し|さ|せ|そ)', s):
        if _arg_abstract(s, m.start(), ('を', 'が', 'は', 'も'), False, colloc=M_COLLOC_TSUBUSU):
            return True
    # 効く（_effect）
    for m in re.finditer(r'(?<![一-鿿])効(く|い|き(?!目)|け)', s):
        if _effect(s, m):
            return True
    # 考えの土台を建物のように崩す。主語（〜が・〜は・〜も）が、ほかの考えが載っている土台の語（前提・根拠・設計・戦略）か、
    # 抽象の物の土台・基盤（「議論の土台」）の時だけ。関係・構造・バランス・計画・体調が崩れる は、辞書に載る「整っていた状態が
    # 乱れる」の意味で1通りに決まるので拾わない（「台風で旅行の計画が崩れた」、先生の手引書「SVOCの関係が崩れやすい」。
    # 計画 は文章の検査器の COLLOC_KUZURE と同じ扱い）。成り立たなくなる条件を数と単位で書いた文（「1GHzでは集中定数の前提が崩れる」）も、
    # いつ何が成り立たなくなるかが文だけで決まるので拾わない（文章の検査器の _judge_collapse と同じ。「Bだと台帳と朝ブリーフの前提が
    # 崩れる」の B は文の外を指す名札で、数と単位ではないので拾う）
    for m in re.finditer(r'崩れ', s):
        if M_UNIT_COND_RE.search(_clause(s[:m.start()])):
            continue
        args = _args(_clause(s[:m.start()]), ('が', 'は', 'も'))
        if not args:
            continue
        noun = re.sub(r'(?:そのもの|自体)$', '', args[0][0])   # 「前提そのものが崩れた」の そのもの は強めの語
        if M_STRUCT_RE.search(noun) and _abstract(noun):
            return True
        if re.search(r'(?:前提|根拠|設計|戦略)$', noun):
            return True
    # 調べることを穴や水に潜ることに例える。「深掘りインタビュー」（調べ方の名前）は文字どおり。
    # 「深掘りした溝」のように後ろの名詞を飾る形は、その名詞（溝＝物）で決める（4回目 2026-10-01 試験集の追加分。文章の検査器と同じ）
    for m in re.finditer(r'深[掘堀]り(?![ァ-ヶ一-鿿A-Za-z])', s):
        mh = re.match(r'(?:した|する|された|される)([一-鿿々ァ-ヶーA-Za-z0-9][^、。をがはにでへもと\s]*)', s[m.end():])
        if mh and not re.match(M_OUTER_NOUN, mh.group(1)) and not _abstract(mh.group(1)):
            continue
        return True
    # 深く分け入る・潜る: 行き先・主語が抽象（「データに深く分け入る」）の時だけ。「海に深く潜った」「水深30mまで深く潜った」は文字どおり
    for m in re.finditer(r'深く(分け入|潜)', s):
        if _arg_abstract(s, m.start(), ('に', 'へ', 'まで', 'が', 'は', 'を'), False):
            return True
    # 抽象の語が相手の、物を動かす動詞（「課題を紐解く」「学びを落とし込む」「答えが芽生える」「議論に踏み込む」）。
    # 壊れる・壊す は、情報・処理の物（データ・ファイル・設定）がコンピュータの中で文字どおり壊れる（破損する）ので、
    # 考え・計画の側（M_ABSTRACT_IDEA）だけを見る（「前提が壊れる」は拾い、「設定ファイルが壊れた」は拾わない）。
    # 性質の語尾（〜観・〜性）も見ない（「景観は壊れない」「外観が壊れた」は、物の見た目が壊れる文字どおりの文。過去のデッキ
    # 過去のデッキ「遅い便を出しても、景観は壊れない」）。
    # 物・部品・物質が相手（「大電流が流れてメータが壊れる」「過電流でICが壊れた」「課題のプリントを束ねて提出した」
    # 「イオン注入で結晶構造が壊れる」）は文字どおり
    for m in M_PHYS_VERB_RE.finditer(s):
        verb = m.group(0)
        if skip_owner and M_OWNER_WORD_RE.match(verb):
            continue
        parts = ('が', 'を', 'は', 'も') + (('に', 'まで') if verb == '踏み込' else ())
        words = M_ABSTRACT_IDEA if verb in ('壊れ', '壊す') else None
        if _arg_abstract(s, m.start(), parts, False, words=words):
            return True
    # 人の動作を抽象の主語に当てる擬人化（資料の例「経路が代わりに添える」・yomiyasu の「データが語る」）
    for m in M_PERSONIFY_RE.finditer(s):
        if _arg_abstract(s, m.start(), ('が', 'は', 'を', 'も'), False, subject_only=True):
            return True
    # 抽象（案・考え）を、場所に物のように積む（本人「これいらないしおかしい」の「同じ1軒の町家に案を重ねています」）。
    # 「議論を重ねた」「経験を重ねる」（くり返す意味の決まった言い方。〜に が無い）は拾わない
    if re.search(r'に[^。、]{0,6}?(案|考え|アイデア|想い|思い|願い|期待)を重ね', s):
        return True
    # 案・経験・知見を「〜として」で物に見立てて積む（「チームの知見を資産として積み上げる」）。5回目（2026-10-01 試験集の
    # metaphor_other-hit-16）。文章の検査器の「比喩でごまかす」の規則（案|提案|…|知見|ノウハウ＋〜として＋
    # 重ね・積み上げ・織り込・練り上げ・紡）と同じ語のうち、〜として を間にはさむ形だけを移した。〜として の無い「経験を重ねる」
    # 「行動量は積み上げてきた」（本人の第1回課題）は、くり返す意味の決まった言い方なので、上と同じく拾わない
    if re.search(r'(?:案|提案|意見|視点|経験|思い|成果|知見|ノウハウ)を[^。、]{1,8}?として(?:重ね|積み上げ|織り込|練り上げ|紡)', s):
        return True
    # 鍵を握る・実を結ぶ・花開く: 主語が抽象（「設計が鍵を握る」「努力が実を結んだ」）か、主語が無い時に拾う。
    # 人・物・植物（「母は家の鍵を握った」「庭のトマトが実を結んだ」）は文字どおり
    for m in re.finditer(r'鍵を握|花開|実を結', s):
        if _arg_abstract(s, m.start(), ('が', 'は', 'も'), True):
            return True
    # 土台に なる・土台と なる（4回目 2026-10-01 試験集の追加分「この仕組みが、判断の土台になります」。文章の検査器の GROW_RE と同じ語）:
    # 主語が書いてあり、それが抽象の時だけ拾う。主語の無い「その土台になったのは、6月の学外研修です」（本人の報告書）・
    # 「〜技術者の土台になると思っている」（本人の英文レポート）・後ろの名詞を飾る「土台となる知識」（先輩の心理学のワークシート）は、
    # 人の文で普通に使う言い方なので拾わない（人の文の母集団で、主語の無い形を拾うと本人・先輩の文が4件増えた）
    for m in re.finditer(r'土台[とに]な(?=る|り|っ)', s):
        if _arg_abstract(s, m.start(), ('が', 'は', 'も'), False):
            return True
    # たどり着く: 行き先（〜に・〜まで・〜へ）が抽象（「案にたどり着けた」「結論にたどり着く」）の時だけ拾う。
    # 場所（「山頂に」「ホテルに」「島に」）・番号の点（グラフの頂点「3にたどり着ければ」授業の班発表）・式（「特異解 y = x² に」）は文字どおり。
    # 4回目（2026-10-01 試験集の追加分。文章の検査器の _judge_reach と同じ）: 時・順序の「〜に」（「会場には午後にたどり着いた」の 午後に）は
    # 行き先ではないので飛ばす。行き先が無ければ、人が場所に着く文字どおりの文が多い（「山道を3時間歩いて、やっとたどり着いた」）ので
    # 拾わない。ただし後ろの名詞を飾る形（「僕がたどり着いた方針は」）は、その名詞が行き先なので、それで決める
    for m in re.finditer(r'たどり着(け|い|く)', s):
        args = [a for a in _args(_clause(s[:m.start()]), ('に', 'まで', 'へ'))
                if not re.search(M_TIME_ORDER + r'$', _noun_end(a[0]))]
        if not args:
            mh = re.match(r'(?:た|だ)?([一-鿿々ァ-ヶー]+)', s[m.end():])
            if mh and _abstract(mh.group(1)):
                return True
            continue
        if not _foreign(args[0][0]) and _abstract(args[0][0]):
            return True
    # 原因・手段を人や道具に例える名詞（過去のデッキの「0V から犯人を絞る」）。その名詞の本来の場面の文は文字どおり
    for words, frame in M_FRAME:
        if skip_owner and M_OWNER_WORD_RE.search(words):
            continue
        if re.search(words, s) and not re.search(frame, s):
            return True
    # 名詞の比喩の 落とし穴（yomiyasu の references/slop-catalog.md 3節）は、中身が同じ文に無い時だけ拾う（4回目 2026-10-01 試験集の
    # 追加分の裁定）。「送信側にも落とし穴がある」は何の落とし穴かが文に無い。「位相の遅れという落とし穴があった」（という で中身を
    # 書いた物）と、本物の穴（落とし穴を掘る・落とし穴に落ちる）は拾わない。文章・レポートの検査器では参考層の型
    for m in re.finditer(r'落とし穴', s):
        if re.search(r'(?:という|との|って|といった)$', s[:m.start()]) or re.search(r'掘|落ち[たるて]|はま[っる]', s):
            continue
        if re.match(r'(?:が|も)?(?:ある|あり|あっ|潜[むん])', s[m.end():]):
            return True
    if M_FIGURE_RE.search(s):
        return True
    i = s.find('手触り')
    if i >= 0 and _touch(s, i):
        return True
    # 質感・体温を装う語。すぐ前（同じ句）か文の前の方に物・場所・人がある文は文字どおり（「海溝の深淵」
    # 「この川の鮒は泥臭い」「釘が刺さる」）
    for w in M_FIGURE_LITERAL:
        mw = re.search(w, s)
        if skip_owner and mw and M_OWNER_WORD_RE.match(mw.group(0)):
            continue
        if mw and not M_LITERAL_RE.search(s[:mw.start()]):
            if mw.group(0) == '解像度' and not re.match(r'解像度(を|が)(上|高)', s[mw.start():]):
                continue
            return True
    return False


def _many_commas(s):
    """M11: 並べる読点を除いて読点が4つ以上・3つ以上が平仮名（助詞・送り仮名）の後・その溜めの読点の間が平均6字以下の文か。
    parts[k] の後ろに k 番目の読点がある。並べる読点の見分け方は M_ENUM_HEAD_RE の上"""
    parts = re.split(r'[、,]', s)
    if len(parts) < 5:
        return False
    segs = [p.strip() for p in parts[:-1]]
    enum = set()
    # 短い名詞の区切りが3つ以上続く所（「VFE，VFB，VBE，VFA」「BOM、所要量展開、発注点」）
    # 並びの最後の項目は助詞を持つことがある（「計算項目の追加，入力方法，結果表示方法は，」＝3つの項目で、並べる読点は2つ）
    run = []
    for k, p in enumerate(segs + [None]):
        if p is not None and len(p) <= 8 and not re.search(r'[ぁ-ゖ]$', p):
            run.append(k)
            continue
        if len(run) >= 3 or (len(run) >= 2 and p is not None and len(p) <= 10
                             and re.search(r'[一-鿿ァ-ヶーA-Za-z0-9][はがをにでともへや]$', p)):
            enum.update(run)
        run = []
    # 「停止，跳ね返り，または元の位置に戻す，のいずれでもよい」: または・の いずれ 等で始まる区切りの前の項目は、
    # 助詞で終わる区切り（「方法は，」）まで戻って並びとみなす
    for k in range(1, len(parts)):
        if not M_ENUM_HEAD_RE.match(parts[k]):
            continue
        j = k - 1
        while j >= 0 and not re.search(r'[はがをにでともへ]$', segs[j]):
            enum.add(j)
            j -= 1
    # 平均の字数は、並べる読点の項目を除いた区切り（最後の区切りを含む）で見る。溜めの読点の区切りだけで見ると、最後に長い節が
    # 続く普通の文（先生の手引書「なお、半加算器は、入力信号A、Bに対して、…異なる出力が得られる回路である」）まで細切れに見える
    rest = [segs[k] for k in range(len(segs)) if k not in enum]
    kana = [p for p in rest if re.search(r'[ぁ-ゖ]$', p)]
    pieces = rest + [parts[-1].strip()]
    return len(rest) >= 4 and len(kana) >= 3 and sum(len(p) for p in pieces) <= 6 * len(pieces)


def _dash(s):
    """M10: 日本語の文の途中のダッシュ（前後に空白が無い）か。見出しの区切り・矢印の線・打ち間違い・英語の中・
    対応の表（「りんご—青果A、みかん—青果B」）・議事録の見出しと中身の区切り（「イベントの提案―予算箱の設置は可決」）は除く。"""
    if sum(1 for item in re.split(r'[、,]', s) if M_DASH_RE.search(item)) >= 2:
        return False
    for m in M_DASH_RE.finditer(s):
        a = s[m.start() - 1] if m.start() > 0 else ''
        b = s[m.end()] if m.end() < len(s) else ''
        if not a or not b or a.isspace() or b.isspace() or a in M_ARROW or b in M_ARROW:
            continue
        if m.group(0) == '―' and re.match(r'[ァ-ヶーA-Za-z0-9]', a):
            continue
        if not M_JA_RE.search(a + b):
            continue
        left = re.split(r'[、,。\s]', s[:m.start()])[-1]
        right = re.split(r'[、,。]', s[m.end():])[0].strip()
        if (not re.search(r'[はがをにでとへもや]', left) and not M_TAME_REF_RE.match(right)
                and not M_PRED_END_RE.search(right)):
            continue   # 名詞の見出し―名詞の中身（議事録・一覧の区切りの記号）
        # 2つの名詞をつなぐ記号（「素子の電圧—電流特性を測った」＝en ダッシュの「電流–電圧特性」と同じ。4回目 2026-10-01 試験集の
        # 追加分の裁定）: ダッシュの前の節に助詞（の 以外）が無く、ダッシュの後ろが名詞＋助詞で文の項（目的語・主語）を続け、
        # 「〜だ・〜である」で言い換えを明かす形でも、指示語で受ける形でもない時は、ダッシュは名詞の句の中の記号で、間を置く使い方ではない
        left_clause = re.split(r'[、,。]', s[:m.start()])[-1]
        if (not re.search(r'[はがをにでとへもや]', left_clause) and not M_TAME_REF_RE.match(right)
                and re.match(r'[一-鿿々ァ-ヶーA-Za-z0-9]+[をにでがはと]', right)
                and not re.search(r'(?:だ|である|です|だった|でした)$', right)):
            continue
        return True
    return False


def _emoji(s):
    """M8: 飾りの絵文字があるか。括弧の中の逐語の写しと、物の名前として書いた絵文字（後ろに助詞）は除く。
    文の頭の色の無い丸・四角（「⚫種別」）は箇条書きの印（M_MONO_SHAPE の上。7回目 2026-10-01）なので除く"""
    s = M_PAREN_RE.sub('', s)
    for m in M_EMOJI_RE.finditer(s):
        if m.group(0) in M_MONO_SHAPE and not s[:m.start()].strip():
            continue
        if not M_EMOJI_NAME_RE.match(s[m.end():].lstrip('\ufe0f\u200d')):
            return True
    return False


def _preface(s):
    """M7: 前置きの決まり文句で始まる文か（s は印を外した文）。"""
    if M_PREFACE_SAY_RE.search(s):
        return True
    m = M_PREFACE_HEAD_RE.match(s)
    if not m:
        mc = M_CLEFT_RE.match(s)
        return bool(mc and NOUN_PHRASE_RE.fullmatch(mc.group(1).replace('「', '').replace('」', '').rstrip('。. ')))
    body = re.split(r'[、,]', s[m.end():].lstrip('、, '))[0]
    return not M_PREFACE_NOT_RE.search(body)


def _next_line(info, ln):
    """ln のすぐ下の行（フォントの大きさの3.5倍以内）。無ければ None。"""
    below = [o for o in info['body']
             if o is not ln and o.y > ln.y and o.y - ln.y <= 3.5 * max(ln.font_size, o.font_size)]
    return min(below, key=lambda o: (o.y, o.x)) if below else None


def _colon_end_lines(info):
    """M9: 日本語の行で、コロンで終わり、予告の語があるか述語・助詞でコロンの直前が終わる行（M_COLON_LEAD_RE）。
    返すのは場所の名前「行」のリスト。
    名詞の見出し語だけの行（「入力：」「絶対パス：」）と、PREP の札（F5）は外す。
    同じ高さに別の字がある行も外す（「日時：」「10月1日」を2つの <text> で横に並べた表、「良かった点：」「悪かった点：」の
    段組みの列の頭。左右どちらに並んでいても表の一部）。同じ高さの幅は、2つの行の大きい方の字の0.3倍
    （小さい札の右に大きい数字を置いた「到達時間：」「3.2秒」。2回目の反証）。
    次の行が式・コード（「V = RI」）の行と、下に文字の行が1つも無い行（中身が図・式の画像。6回目）も外す。
    「」は消さずに見る（「若者：「もう1時間遅く」」は、コロンの後ろに同じ行で人の言葉が続く＝行の終わりではない。
    過去のデッキで「」を先に消して2件誤検知した。2026-10-01）。「が閉じずに次の行へ続く行（人の言葉の途中）は見ない"""
    out = []
    heads = set(id(ln) for ln in info['head_lines'])
    eb = info['eyebrow']
    for ln in info['body']:
        t = ln.text.strip()
        if not (M_COLON_END_RE.search(t) and M_JA_RE.search(t)) or PREP_LABEL_RE.search(t):
            continue
        lead = bool(M_COLON_LEAD_RE.search(t))
        connective = bool(M_COLON_CONNECTIVE_RE.match(_drop_mark(t)))
        if not (lead or connective):
            continue
        if t.count('「') > t.count('」') or t.count('『') > t.count('』'):
            continue
        if any(other is not ln and abs(other.y - ln.y) <= 0.3 * max(ln.font_size, other.font_size)
               for other in info['body']):
            continue
        if not any(other is not ln and other.y > ln.y for other in info['body']):
            # コロンの行より下に文字の行が1つも無い＝中身は文字ではなく、図・表・式の画像か、式が抜けた配布物の空の段落
            # （先生 経済学入門 乗数分析：（閉鎖経済＃2）解答なし 2.docx「次の経済を考える：」の次は Word の数式で、文字を取り出すと空）。
            # 次の行が式・コードの時（下の M_FORMULA_RE）と同じく、文で書き切れない物を示す普通のコロン（6回目 2026-10-01）
            continue
        nxt = _next_line(info, ln)
        if nxt is not None and not M_JA_RE.search(nxt.text) and (M_FORMULA_RE.search(nxt.text)
                                                                  or M_NEXT_COMMAND_RE.match(nxt.text.strip())):
            continue
        if connective and not lead:
            # 接続の語＋コロンは、次の行が文の時だけ（図の名前・語句の行なら「例：」と同じ見出し）
            nt = unicodedata.normalize('NFKC', nxt.text).strip() if nxt is not None else ''
            if not (M_SENT_END_RE.search(nt) or M_PRED_END_RE.search(_drop_mark(nt))):
                continue
        where = '見出し' if id(ln) in heads else ('小ラベル' if (eb is not None and ln is eb) else '本文')
        out.append('%s「%s」' % (where, t[-20:]))
    return out


def meaning_hits(units):
    """文の型の検査（M1〜M5・M7・M8・M10・M11）。units は _meaning_units と同じ形の [(場所の名前, 文のリスト, 組にしない境目)]。
    返すのは {規則: [場所「文」, …]}（旧PCの人のスライドの回帰でも、この関数をそのまま使う）。
    WARNING の当たりだけを返す。本人も使う比喩の語だけで当たる文（INFO の M5参考）は meaning_refs が返す。"""
    hits = {}

    def add(code, where, s):
        hits.setdefault(code, []).append('%s「%s」' % (where, s[:20]))

    for where, sents, cut in units:
        # 式・記号が抜けた写しの文（M_GAP_RE の上）は、読点と文の組の型（M1・M2・M3・M11）を見ない（6回目 2026-10-01）
        gaps = [bool(M_GAP_RE.search(_drop_mark(x))) for x in sents]
        for k, s in enumerate(sents):
            body = _drop_mark(s)
            # M7 と M3 は「重要なのは、」の同じ読点を、M11 と M3 は同じ読点の多さを指すので、M7・M11 に当たった文は M3 に数えない
            if _preface(body):
                add('M7', where, s)
            if not gaps[k] and _many_commas(s):
                add('M11', where, s)
            elif not gaps[k] and not _preface(body) and _tame(body):
                add('M3', where, s)
            if _emoji(s):
                add('M8', where, s)
            if _vague_ref(sents, k):
                add('M4', where, s)
            if _metaphor(s, skip_owner=True):
                add('M5', where, s)
            if _dash(s):
                add('M10', where, s)
            if not gaps[k] and len(s) <= 48:
                # 1文の中で、連用中止・て形の読点の前後の節が語を入れ替えた対句（M_RENYO_COMMA_RE の上）
                parts = [p.strip() for p in M_RENYO_COMMA_RE.split(s) if p.strip()]
                for j in range(len(parts) - 1):
                    if len(parts[j]) <= 24 and len(parts[j + 1]) <= 24 and _chiasmus(parts[j], parts[j + 1]):
                        hits.setdefault('M2', []).append('%s「%s、%s」' % (where, parts[j][:14], parts[j + 1][:14]))
                        break
            if k + 1 >= len(sents) or gaps[k] or gaps[k + 1]:
                continue
            s2 = sents[k + 1]
            # 句点の無い箇条書きが3行以上並ぶ所（cut）でも、2行目が自分の主語（名詞＋が・は）を持たない「・AIは答えを教えない」
            # 「・問いを返す」は、前の行の主語を補わないと読めない前振りと決めの組なので M1 だけは組にする（3回目の反証 2026-10-01。
            # 資料の例を3行の箇条書きにすると取りこぼしていた）。授業の班発表の長所・短所の並び「検索漏れが発生しない」「検索効率が向上する」は、
            # 2行目に主語があるので組にしない。M2 は前のまま（同じように緩めると授業の pptx で2件増えた）
            if (k not in cut or not M_OWN_SUBJ_RE.search(_drop_mark(s2))) and _neg_pair(s, s2):
                hits.setdefault('M1', []).append('%s「%s。%s」' % (where, s[:14], s2[:14]))
            if k not in cut and len(s) <= 24 and len(s2) <= 24 and _chiasmus(s, s2):
                hits.setdefault('M2', []).append('%s「%s。%s」' % (where, s[:14], s2[:14]))
    return hits


def meaning_refs(units):
    """参考（INFO）の型。本人が自分の文で使う比喩の語（M_OWNER_WORD_RE＝落とし込む・架け橋・刺さる）だけで M5 に当たる文
    （2026-10-01 本人の判断「① 参考の扱いにする」）。返す形は meaning_hits と同じ {規則: [場所「文」, …]}。
    ほかの比喩でも当たる文は meaning_hits の M5（WARNING）に出るので、ここには出さない（二重に数えない）。"""
    refs = {}
    for where, sents, cut in units:
        for s in sents:
            if not _metaphor(s, skip_owner=True) and _metaphor(s):
                refs.setdefault('M5', []).append('%s「%s」' % (where, s[:20]))
    return refs


M_NAMES = {'M1': '否定の前振り（短い否定文→短い肯定文）', 'M2': '語を入れ替えた反復',
           'M3': '短い語の後の読点で溜める', 'M4': '指す物が書いていない（片方・前者・指示語）',
           'M5': '比喩の動詞・方向の比喩', 'M6': '名詞化で止めた見出し',
           'M7': '前置きの決まり文句（重要なのは・結論から言うと）', 'M8': '絵文字',
           'M9': '行の終わりのコロン（中身を次の行に回す）', 'M10': 'ダッシュで文を区切る',
           'M11': '読点の打ちすぎ'}


def check_meaning(infos, issues):
    """意味の検査（M1〜M11）。スライドの文字だけを見る（ノートは見ない＝話者なしで読まれる前提）。
    謝辞・参考文献（T）の枚は見ない。M4 の見出しの指示語と M6 は、表紙（C）と目次（A）でも見ない。"""
    for info in infos:
        role = info['role']
        if role == 'T':
            continue
        units = _meaning_units(info)
        hits = meaning_hits(units)
        head = strip_quotes(unicodedata.normalize('NFKC', info['head'] or '')).strip().rstrip('。.')
        if head and role not in ('C', 'A'):
            if M_DEICTIC_HEAD_RE.match(head):
                hits.setdefault('M4', []).append('見出しが指示語で始まる「%s」' % head[:20])
            if M_NOMINAL_END_RE.search(head):
                hits.setdefault('M6', []).append('見出し「%s」' % head[:24])
        colon = _colon_end_lines(info)
        if colon:
            hits['M9'] = colon
        for code in ('M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8', 'M9', 'M10', 'M11'):
            if code in hits:
                issues.append(Issue('WARNING', info['file'].name,
                                    '%s %s: %s' % (code, M_NAMES[code], ' / '.join(hits[code][:3])), M_FIX[code]))
        # 参考（INFO）: 本人も使う比喩の語だけで当たる文（2026-10-01 本人の判断）。止めずに表示だけ
        for code, lst in sorted(meaning_refs(units).items()):
            issues.append(Issue('INFO', info['file'].name,
                                '%s参考 %s: %s' % (code, M_REF_NAMES[code], ' / '.join(lst[:3])), M_FIX[code]))


def check_form(project_dir, infos, roles, has_notes, brief, issues):
    """形の検査（F1〜F8・Q1・Q2。F5 は check_prep の札ループの中）。"""
    check_p_repeat(infos, roles, issues)
    check_contrast(infos, issues)
    check_one_side_bar(infos, issues)
    check_same_entry(infos, roles, issues)
    check_decor(project_dir, infos, issues)
    if roles is not None:
        check_re_evidence(infos, brief, issues)
        check_re_thin(infos, has_notes, issues)
    check_quote_layout(infos, issues)


# ------------------------------------------------------------ 目次（A0〜A3） ---
# 本人の既定: 目次を全デッキに入れる（2026-09-28「最初に目次を入れたい」・作者の skill-memory/slide-gen.md
# 「アジェンダ（目次）を必ず入れる」）。外部の手引きは目次を条件付き（長い発表なら等）にしているので、
# 根拠は「本人の既定」。入れない時は spec_lock に `agenda: none <日付> 本人 <理由>` を書く（INFO になる）。
AGENDA_MIN_CORE = 4          # 表紙・目次・謝辞を除いてこの枚数以上なら目次を求める
AGENDA_NONE_RE = re.compile(r'^[\s\-*>]*agenda[^\S\n]*[:：][^\S\n]*none\b[^\S\n]*(.*)$', re.IGNORECASE | re.MULTILINE)
# A2: 中身の無い見出し語（項目の行の全体がこれと同じ時だけ。「背景：町家が空いている」は拾わない）
AGENDA_VAGUE_RE = re.compile(r'^(はじめに|概要|背景|目的|結論|理由|具体例|まとめ|考察|今後の展望|今後の課題|おわりに|'
                             r'質疑応答?|Q&A|Introduction|Overview|Background|Summary|Conclusions?|Outline|Agenda)$',
                             re.IGNORECASE)
AGENDA_NUM_RE = re.compile(r'^0?\d{1,2}[.．]?$')                      # 番号だけの行（項目の数を数える用）
AGENDA_ENUM_RE = re.compile(r'^0?\d{1,2}(?:[.．、)）][\s　]*|[\s　]+)')   # 項目の頭の番号「01　」「1. 」
AGENDA_WORD_RE = re.compile(r'[一-鿿々〆]{2,}|[ァ-ヶー]{2,}|[A-Za-z]{3,}')   # A3 の語（漢字・カタカナ2字以上、英字3字以上）


def agenda_none(project_dir):
    """spec_lock の `agenda: none <理由>` の理由（書いてあれば文字列、無ければ None）。"""
    for base in (project_dir, project_dir.parent):
        cand = base / 'spec_lock.md'
        if cand.is_file():
            m = AGENDA_NONE_RE.search(cand.read_text(encoding='utf-8', errors='replace'))
            if m:
                return m.group(1).strip()
    return None


# 本人が目次を表紙の直後でない枚に決めた時は spec_lock に `agenda: at <枚> <日付> 本人 <理由>` を書く
# （2026-10-16 本人「スライドも2枚目に変えて」＝前提のニュースを表紙の次に置き、目次は3枚目）。
# 枚の番号が実物の目次と合い、理由が書いてある時だけ check_prep が INFO にする。
AGENDA_AT_RE = re.compile(r'^[\s\-*>]*agenda[^\S\n]*[:：][^\S\n]*at[^\S\n]+(\d{1,3})\b[^\S\n]*(.*)$',
                          re.IGNORECASE | re.MULTILINE)


def agenda_at(project_dir):
    """spec_lock の `agenda: at <枚> <理由>` を (枚, 理由) にする。無ければ None。"""
    for base in (project_dir, project_dir.parent):
        cand = base / 'spec_lock.md'
        if cand.is_file():
            m = AGENDA_AT_RE.search(cand.read_text(encoding='utf-8', errors='replace'))
            if m:
                return int(m.group(1)), m.group(2).strip()
    return None


def agenda_items(info):
    """目次の枚の項目: 見出し（無ければいちばん上の行）より下の本文を、<text> ごとにつないだ物。
    フッター・※の行は本文に入っていない。番号だけの行（01 など）は項目に入れず、数を数えるのに使う。
    returns (項目の文のリスト, 番号だけの行の数)"""
    body = info['body']
    if not body:
        return [], 0
    heads = info['head_lines']
    if heads:
        # 見出しは最初の行と、その折り返し（1.6行ぶん以内）だけ。大きい字の項目を見出しと取り違えない
        heads = [ln for ln in heads if ln.y <= heads[0].y + heads[0].font_size * 1.6]
    else:
        heads = [min(body, key=lambda ln: (ln.y, ln.x))]
    bottom = max(ln.y for ln in heads)
    skip = set(id(ln) for ln in heads)
    below = sorted([ln for ln in body if id(ln) not in skip and ln.y > bottom], key=lambda ln: (ln.y, ln.x))
    items = []
    nums = 0
    for t in joined_blocks(below):
        t = unicodedata.normalize('NFKC', t).strip()
        if AGENDA_NUM_RE.match(t):
            nums += 1
        elif t:
            items.append(t)
    return items, nums


def check_agenda(project_dir, infos, roles, issues, legacy):
    """A0〜A3: 目次（役割 A）があるか・項目の数・中身のある項目か・中身の枚と語が合っているか。"""
    if roles is None:
        return   # prep が無いことは check_prep が ERROR にする
    seq = [roles[k][0] for k in sorted(roles)]
    core = prep_core(seq)
    a_infos = [info for info in infos if info['role'] == 'A']
    if not a_infos:
        why = agenda_none(project_dir)
        if why is not None:
            issues.append(Issue('INFO', '(全体)', 'A0 目次なし（spec_lock: agenda: none %s）' % (why or '理由なし')))
        elif len(core) >= AGENDA_MIN_CORE:
            issues.append(Issue(
                _down('ERROR', legacy), '(全体)',
                'A0 目次(A)の枚が無い（表紙・謝辞を除いて %d 枚。%d 枚以上は目次を入れるのが本人の既定）' % (
                    len(core), AGENDA_MIN_CORE),
                'prep に A を足し（例 C 1 / A 2 / P 3 …）、表紙の直後に3〜5項目の目次を置く。'
                '入れない時は spec_lock に agenda: none <日付> 本人 <理由>'))
        return
    info = a_infos[0]
    items, nums = agenda_items(info)
    count = nums if nums else len(items)
    name = info['file'].name
    # A1: 項目の数（nulljapan「多くても5つぐらい」・MiniMax「3-5 sections」。Deckary は4〜7なので WARNING 止まり）
    if count < 3 or count > 5:
        issues.append(Issue(
            'WARNING', name, 'A1 目次の項目が %d 個（3〜5個が目安）' % count,
            '細かい節はまとめて3〜5個にする。項目が1〜2個しか無いなら、目次ではなく節の分け方を見直す'))
    # A2: 中身の無い見出し語
    vague = []
    for t in items:
        s = AGENDA_ENUM_RE.sub('', t).strip(' 　:：・')
        if AGENDA_VAGUE_RE.match(s):
            vague.append(s)
    if vague:
        issues.append(Issue(
            'ERROR', name, 'A2 目次の項目が中身の無い見出し語（「%s」）' % '」「'.join(vague[:4]),
            '項目は、その節で言う中身の短い言い切りにする（例「まとめ」→「来年の募集に応募してほしい」）'))
    # A3: 項目の語が、目次より後の P/R/E の枚の文字に出てくるか
    later = ''.join(x['text'] for x in infos if x['n'] > info['n'] and x['role'] in ('P', 'R', 'E'))
    later = later.lower()
    if items:
        hit = 0
        for t in items:
            words = AGENDA_WORD_RE.findall(AGENDA_ENUM_RE.sub('', t))
            if any(w.lower() in later for w in words):
                hit += 1
        if hit < len(items) / 2.0:
            issues.append(Issue(
                'WARNING', name,
                'A3 目次の項目 %d 個のうち、後の P/R/E の枚に語が出るのは %d 個＝目次と中身がずれている' % (len(items), hit),
                '目次の項目の語を、その節の見出しと同じ語にする'))


# ------------------------------------------------- 資料の種類 genre（G1〜G9） ---
# 2026-09-28。報告・提案・研究発表で「要る物」が違うので、spec_lock の `- genre: xxx`（brief.py が書く）で検査の重さを変える。
#   experience=体験・研修・留学・出張の報告 / progress=進捗・中間 / proposal=提案・企画・申請・コンペ /
#   research=研究・実験・授業発表・調べ学習の発表 / explainer=解説・勉強会・LT / notice=告知。未記載は general。
# 重さ: E=ERROR W=WARNING -=検査しない（'*' はその他のジャンル全部）。
GENRES = ('experience', 'progress', 'proposal', 'research', 'explainer', 'notice')
GENRE_SEV = {
    'G1': {'experience': 'E', 'progress': 'E', '*': '-'},                  # 概要の事実（brief.overview）
    # G2 データの証拠。experience を OFF にするのは本人の判断（海外研修の報告）。一般の研修・出張報告の手引きは
    # 成果・経費・目標の数字を勧めている（Manegy・engine・Felo）ので、報告でも数字を足せるなら足す
    'G2': {'proposal': 'E', 'research': 'E', 'progress': 'W', 'general': 'W', '*': '-'},
    'G3b': {'proposal': 'E', 'research': 'E', '*': 'W'},                  # 数字の出典の行
    'G3a': {'*': 'W'},                                                    # 人の言葉の出どころ
    'G4a': {'*': 'E'},                                                    # お願いが最後の P にあるか
    'G4b': {'*': 'W'},                                                    # お願いの時期
    'G4c': {'notice': 'W', '*': '-'},                                     # お願いの窓口
    'G5': {'experience': 'W', 'proposal': 'W', 'research': 'W', '*': '-'},  # 目的（me.why）
    'G7': {'notice': '-', '*': 'W'},                                      # 表紙の報告日
    'G8': {'*': 'W'},                                                     # 英略語の説明
    'G9': {'research': 'W', '*': '-'},                                    # 参考文献の枚
}
GENRE_LINE_RE = re.compile(r'(?<![A-Za-z_])genre[^\S\n]*[:：][^\S\n]*([A-Za-z_-]+)', re.IGNORECASE)
# 「数＋単位」（NFKC の後）。日付・時刻・行頭の番号・「第N回」の序数は NUM_SKIP_RES で先に消してから探す
NUM_UNIT_RE = re.compile(
    r'\d+(?:[.,]\d+)*\s*(?:%|‰|割|倍|件|名|人|社|校|回|円|万|億|兆|個|本|点|票|枚|台|冊|問|つ|か所|カ所|ヶ所|箇所|'
    r'か国|カ国|ヶ国|コマ|時間|分|秒|日間|週間|か月|カ月|ヶ月|年間|歳|位|度|℃|行|字|ドル|元|'
    r'kg|km|mm|cm|m|g|px|KB|MB|GB|TB|kW|W|V|Hz|kHz|MHz|GHz|nm|ppm|dB|pt)(?![A-Za-z])')
_MONTHS = ('January|February|March|April|May|June|July|August|September|October|November|December')
NUM_SKIP_RES = [
    re.compile(r'\d{4}\s*年\s*\d{1,2}\s*月(?:\s*\d{1,2}\s*日)?'),        # 2026年9月28日・2026年9月
    re.compile(r'\d{1,2}\s*月\s*\d{1,2}\s*日'),                          # 9月28日
    re.compile(r'\d{4}\s*年度?'),                                        # 2026年・1976年
    re.compile(r'\d{1,2}\s*月'),                                         # 8月
    re.compile(r'\d{4}[/.\-]\d{1,2}(?:[/.\-]\d{1,2})?'),                 # 2026-09-28
    re.compile(r'\d{1,2}/\d{1,2}(?!\d)'),                                # 9/28
    re.compile(r'\d{1,2}[:：]\d{2}'),                                    # 15:00
    re.compile(r'\d{1,2}\s*時(?!間)(?:\s*\d{1,2}\s*分)?半?'),             # 15時・15時30分（5時間は残す）
    re.compile(r'第\s*\d+\s*(?:回|章|部|期|弾|号|話|節|位|条|項|次|週|日|学年|世代)?'),   # 第3回（序数）
    re.compile(r'\d{1,2}\s+(?:%s)(?:\s+\d{4})?|(?:%s)\s+\d{1,2}(?:,\s*\d{4})?' % (_MONTHS, _MONTHS)),
]
LEAD_ENUM_RE = re.compile(r'^(?:0\d|\d{1,2}[.．、)）])[\s　]*|^\d{1,2}　')   # 行頭の番号「01」「1.」「1　」
SOURCE_LINE_PREFIXES = ('※', '出典', '出所', 'Source', 'SOURCE')
# G3a: 行の全体が「…」の行（文の途中の「」は数えない）
QUOTE_LINE_RE = re.compile(r'^[「『][^「」『』]+[」』][。．]?$')
# G4: お願いの時期と窓口
TIME_WORD_RE = re.compile(r'\d+月|\d+日|まで|来年|今年度|春|夏|秋|冬|今日中|今週|明日')
CONTACT_RE = re.compile(r'室|課|係|窓口|先生|教員|https?://|@|\.jp')
# G7: 表紙の報告日（単独の日付。「8月16日〜22日」のような期間の端は数えない）
_DASHES = '〜~\\-－–—'
COVER_DATE_RES = [
    re.compile(r'(?<![%s])(?<![%s]\s)\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日(?!\s*[%s])' % (_DASHES, _DASHES, _DASHES)),
    re.compile(r'(?<![%s])(?<![%s]\s)\b\d{1,2}\s+(?:%s)\s+\d{4}\b(?!\s*[%s])' % (_DASHES, _DASHES, _MONTHS, _DASHES)),
    re.compile(r'(?<![%s])(?<![%s]\s)\b(?:%s)\s+\d{1,2},\s*\d{4}\b(?!\s*[%s])' % (_DASHES, _DASHES, _MONTHS, _DASHES)),
]
RECIPIENT_RE = re.compile(r'室|課|係|様|向け|御中|宛')
# G8: 英大文字2〜6字の語（数字の直後の単位 10.2KB・ファイル名 CLAUDE.md は除く）
TERM_RE = re.compile(r'(?<![A-Za-z0-9.])[A-Z]{2,6}(?![A-Za-z])(?!\.[a-z])')
TERMS_OK_DEFAULT = ('QR', 'JR', 'CSV', 'PC', 'AI', 'OK', 'USB', 'LED', 'PDF', 'URL', 'SNS', 'IT', 'Q&A')
TERMS_OK_RE = re.compile(r'^[\s\-*>]*terms_ok[^\S\n]*[:：][^\S\n]*(.+)$', re.IGNORECASE | re.MULTILINE)
HIRAGANA_RE = re.compile(r'[ぁ-ゖ]')
# G9: 参考文献の枚
REFS_RE = re.compile(r'参考文献|出典一覧|References|Bibliography', re.IGNORECASE)


def detect_genre(project_dir, brief=None):
    """spec_lock.md / design_spec.md の `genre: xxx` を拾う（detect_delivery と同じ探し方）。
    無ければ brief.json の genre。どちらにも無ければ None。"""
    seen = set()
    for base in (project_dir, project_dir.parent):
        if base in seen:
            continue
        seen.add(base)
        for cand in (base / 'spec_lock.md', base / 'design_spec.md'):
            if cand.is_file():
                try:
                    txt = cand.read_text(encoding='utf-8', errors='replace')
                except OSError:
                    continue
                m = GENRE_LINE_RE.search(txt)
                if m:
                    return m.group(1).lower()
    if isinstance(brief, dict) and not _is_empty(brief.get('genre')):
        return str(brief.get('genre')).strip().lower()
    return None


def genre_sev(check, genre):
    """GENRE_SEV の表から重さを返す（'ERROR' / 'WARNING'。検査しないなら None）。"""
    table = GENRE_SEV[check]
    v = table.get(genre, table.get('*', '-'))
    return {'E': 'ERROR', 'W': 'WARNING'}.get(v)


def data_count(lines):
    """行の中の「数＋単位」の数。日付・時刻・行頭の番号・第N回 を先に消す（それらはデータではない）。"""
    n = 0
    for ln in lines:
        t = unicodedata.normalize('NFKC', ln.text).strip()
        t = LEAD_ENUM_RE.sub('', t)
        for rx in NUM_SKIP_RES:
            t = rx.sub(' ', t)
        n += len(NUM_UNIT_RE.findall(t))
    return n


def has_source_line(info):
    """その枚に「※」「出典」で始まる行があるか（フッターの帯に置いた物も数える）。"""
    return any(ln.text.strip().startswith(SOURCE_LINE_PREFIXES) for ln in info['lines'])


def _loose(s):
    """G1 の照合用: normalize_text に加えて、波ダッシュの違い（〜 と ～）をそろえる。"""
    return normalize_text(s).replace('〜', '~')


def _segments(info):
    """G4・G5 の照合の単位: 本文の行・<text> ごとにつないだ文・ノートの文（。と改行で切る）。"""
    segs = [ln.text for ln in info['body']] + joined_blocks(info['body'])
    segs += [s for s in re.split(r'[。\n]', info['notes'] or '') if s.strip()]
    return segs


def _gist_in(s, infos):
    """s の要旨が、その枚たちの本文かノートにあるか（連続8字の一致か、文の bigram の重なり 0.5 以上）。"""
    for info in infos:
        if _quote_in(s, info['text']) or _quote_in(s, info['notes_norm']):
            return True
        if any(bigram_jaccard(s, seg) >= 0.5 for seg in _segments(info)):
            return True
    return False


def terms_ok(project_dir):
    """G8 で説明が要らない略語: 既定の一覧＋spec_lock の `terms_ok: A, B, C`。"""
    ok = set(TERMS_OK_DEFAULT)
    for base in (project_dir, project_dir.parent):
        cand = base / 'spec_lock.md'
        if cand.is_file():
            for m in TERMS_OK_RE.findall(cand.read_text(encoding='utf-8', errors='replace')):
                ok |= set(x for x in re.split(r'[\s,、，/／]+', m) if x)
            break
    return ok


def check_genre(project_dir, infos, roles, brief, issues, legacy):
    """G1〜G9: 資料の種類（genre）ごとに、要る物があるか。genre 未記載の過去のデッキは general（ERROR は増やさない）。"""
    genre = detect_genre(project_dir, brief)
    if genre is None:
        issues.append(Issue('INFO', '(全体)', 'genre 未記載＝general として検査（spec_lock に `- genre: %s` のどれか）'
                            % ' / '.join(GENRES)))
        genre = 'general'
    elif genre not in GENRES and genre != 'general':
        issues.append(Issue('WARNING', '(全体)', 'genre「%s」は不明＝general として検査した' % genre,
                            'spec_lock の genre を %s のどれかにする（brief.py が書く）' % ' / '.join(GENRES)))
        genre = 'general'
    else:
        issues.append(Issue('INFO', '(全体)', 'genre: %s' % genre))
    bpath = load_brief(project_dir)[1] if brief is not None else None
    check_overview(brief, bpath, infos, genre, issues, legacy)
    check_data(infos, genre, issues)
    check_quote_source(infos, brief, genre, issues)
    check_ask(brief, infos, genre, issues, legacy)
    check_why(brief, infos, genre, issues)
    check_cover_date(infos, genre, issues)
    check_terms(project_dir, infos, genre, issues)
    check_references(infos, roles, genre, issues)


def check_overview(brief, bpath, infos, genre, issues, legacy):
    """G1: 概要の事実（いつ・どこで・何を）が、表紙・目次・最初の P の枚の文字かノートに出ているか（報告・中間だけ）。"""
    sev = genre_sev('G1', genre)
    if sev is None or brief is None:
        return
    sev = _down(sev, legacy)
    items = [x for x in (brief.get('overview') or []) if isinstance(x, dict)]
    if not items:
        issues.append(Issue(
            sev, 'brief.json', 'G1 概要の事実（overview）が空（%s は、いつ・どこで・何を を最初に見せる）' % genre,
            'brief.json に overview: [{"k": "期間", "v": "8月16日〜22日", "src": "研修メモ.md:3", "quote": "…"}] を書く'
            '（py brief.py で書き直す）'))
        return
    where = [info for info in infos if info['role'] in ('C', 'A')]
    ps = [info for info in infos if info['role'] == 'P']
    if ps:
        where.append(ps[0])
    if not where:
        where = infos[:2]
    text = ''.join(_loose(''.join(ln.text for ln in info['lines'])) + _loose(info['notes']) for info in where)
    names = '・'.join('%02d' % info['n'] for info in where)
    for it in items:
        v = str(it.get('v') or '')
        if not _loose(v):
            issues.append(Issue(sev, 'brief.json', 'G1 overview の %s の v が空' % (it.get('k') or '?'),
                                'v にスライドで見せる値（例 8月16日〜22日）を書く'))
        elif _loose(v) not in text:
            issues.append(Issue(
                sev, 'brief.json', 'G1 概要の事実 %s「%s」が表紙・目次・最初の P（%s 枚目）の文字にもノートにも無い' % (
                    it.get('k') or '?', v[:20], names),
                '表紙か最初の P に、いつ・どこで・何を を1行で置く（ノートでもよい）'))
    for s, msg, fix in trace_overview(brief, bpath.parent if bpath else Path('.')):
        issues.append(Issue(_down(s, legacy), 'brief.json', msg, fix))


def check_data(infos, genre, issues):
    """G2: R/E の枚に「数＋単位」が1つも無い（デッキ全体で）。G3b: 数字のある R/E の枚に ※・出典 の行が無い。"""
    re_infos = [info for info in infos if info['role'] in ('R', 'E')]
    if not re_infos:
        return
    counts = dict((info['n'], data_count(info['body'])) for info in re_infos)
    sev = genre_sev('G2', genre)
    if sev and sum(counts.values()) == 0:
        issues.append(Issue(
            sev, '(全体)', 'G2 R/E の枚（%d 枚）に、数＋単位のデータが1つも無い（genre=%s）' % (len(re_infos), genre),
            '素材にある数（件数・人数・回数・割合・時間）を、その主張の枚に1つ置く。素材に無い数は作らない'))
    sev = genre_sev('G3b', genre)
    if sev:
        for info in re_infos:
            if counts[info['n']] and not has_source_line(info):
                issues.append(Issue(
                    sev, info['file'].name, 'G3b 数字（%d 個）がある %s の枚に、出典の行（※・出典）が無い' % (
                        counts[info['n']], info['role']),
                    '同じ枚の下に「※8月17日の研修メモから」「出典：…（2026-09-28 取得）」の1行を置く'))


def check_quote_source(infos, brief, genre, issues):
    """G3a: 人の言葉の行（行の全体が「…」か、brief の逐語と同じ行）がある P/R/E の枚に、※ の行（誰が・いつ）があるか。"""
    sev = genre_sev('G3a', genre)
    if sev is None:
        return
    quotes = set()
    for pr in _proofs(brief or {}):
        if pr.get('kind') == 'verbatim' and normalize_text(pr.get('quote')):
            quotes.add(normalize_text(pr.get('quote')))
    for info in infos:
        if info['role'] not in ('P', 'R', 'E'):
            continue
        hit = None
        for t in joined_blocks(info['body']) + [ln.text for ln in info['body']]:
            t = t.strip()
            if QUOTE_LINE_RE.match(t) or (quotes and normalize_text(t) in quotes):
                hit = t
                break
        if hit and not has_source_line(info):
            issues.append(Issue(
                sev, info['file'].name, 'G3a 人の言葉「%s」の枚に、出どころの行（※）が無い' % hit.strip('「」『』')[:16],
                '同じ枚に「※8月18日、日本人留学生から（研修メモ）」のように、誰が・いつ言ったかを1行で置く'))


def check_ask(brief, infos, genre, issues, legacy):
    """G4: お願い（brief.cta）が最後の P に出ているか（a）・時期があるか（b）・告知なら窓口があるか（c）。"""
    if brief is None:
        return
    cta = str(brief.get('cta') or '').strip()
    ps = [info for info in infos if info['role'] == 'P']
    if not cta or not ps:
        return
    last = ps[-1]
    name = last['file'].name
    sev = genre_sev('G4a', genre)
    if sev and not _gist_in(cta, [last]):
        issues.append(Issue(
            _down(sev, legacy), name, 'G4a お願い（cta「%s」）が最後の P（%02d 枚目）の本文にもノートにも無い' % (
                cta[:20], last['n']),
            '最後の P に、聞き手にしてほしいことを1行で置く（brief.cta の言葉で）'))
    alltext = unicodedata.normalize('NFKC', ''.join(ln.text for ln in last['body']) + (last['notes'] or ''))
    sev = genre_sev('G4b', genre)
    if sev and not TIME_WORD_RE.search(alltext):
        issues.append(Issue(
            sev, name, 'G4b お願いに時期が無い（いつまでに・いつ。最後の P の本文とノート）',
            '「10月31日まで」「来年の夏」など、いつするかを添える'))
    sev = genre_sev('G4c', genre)
    if sev and not CONTACT_RE.search(alltext):
        issues.append(Issue(
            sev, name, 'G4c 告知なのに窓口が無い（〜室・〜係・先生・URL・メール）',
            '申込先・問い合わせ先を1行で置く'))


def check_why(brief, infos, genre, issues):
    """G5: 目的（brief.me.why）の要旨が、スライドかノートのどこかに出ているか。"""
    sev = genre_sev('G5', genre)
    if sev is None or brief is None:
        return
    me = brief.get('me') if isinstance(brief.get('me'), dict) else {}
    why = str(me.get('why') or '').strip()
    if why and not _gist_in(why, infos):
        issues.append(Issue(
            sev, '(全体)', 'G5 目的（me.why「%s」）がスライドにもノートにも出ていない' % why[:20],
            'なぜそれをしたか（参加した・調べた理由）を、最初の P か表紙のノートに1文で入れる'))


def check_cover_date(infos, genre, issues):
    """G7: 表紙（1枚目）に単独の日付（報告日）があるか。宛先（〜室・〜様・〜向け）は INFO だけ。"""
    sev = genre_sev('G7', genre)
    if sev is None or not infos:
        return
    cover = infos[0]
    texts = [unicodedata.normalize('NFKC', ln.text) for ln in cover['lines']]
    if not any(rx.search(t) for t in texts for rx in COVER_DATE_RES):
        issues.append(Issue(
            sev, cover['file'].name, 'G7 表紙に報告日（2026年9月28日・9 August 2026 の形の単独の日付）が無い',
            '表紙に発表する日を1行で置く（研修の期間「8月16日〜22日」とは別に）'))
    if not any(RECIPIENT_RE.search(t) for t in texts):
        issues.append(Issue('INFO', cover['file'].name, 'G7 表紙に宛先（〜室・〜課・〜様・〜向け）が無い（任意）'))


def check_terms(project_dir, infos, genre, issues):
    """G8: 英大文字2〜6字の略語が、初めて出る枚で、直後の（…）か、同じ枚の ※ の行で説明されているか。日本語のデッキだけ。
    「宇宙航空研究開発機構（JAXA）」のように、説明の後の（）の中に置いた略語も説明ありと数える。参考文献の枚は見ない。"""
    sev = genre_sev('G8', genre)
    if sev is None:
        return
    kana = sum(len(HIRAGANA_RE.findall(ln.text)) for info in infos for ln in info['body'])
    if kana < 10:
        return   # 英語のデッキ（本文にひらがなが10字未満）は見ない
    ok = terms_ok(project_dir)
    seen = set()
    for info in infos:
        title = info['head'] or (min(info['body'], key=lambda ln: (ln.y, ln.x)).text if info['body'] else '')
        if REFS_RE.search(title):
            continue   # 参考文献の枚の出版社・誌名（ACS など）は説明しない（過去の研究発表のデッキの 09 で確かめた）
        new = []
        for ln in info['body']:
            for m in TERM_RE.finditer(unicodedata.normalize('NFKC', ln.text)):
                w = m.group(0)
                if w in ok or w in seen:
                    continue
                seen.add(w)
                new.append(w)
        bad = []
        for w in new:
            explained = False
            for ln in info['lines']:
                t = unicodedata.normalize('NFKC', ln.text)
                if re.search(re.escape(w) + r'[\s　]*[（(]', t) or re.search(r'[（(][\s　]*' + re.escape(w), t):
                    explained = True
                elif t.strip().startswith('※') and w in t:
                    explained = True
            if not explained:
                bad.append(w)
        if bad:
            issues.append(Issue(
                sev, info['file'].name, 'G8 初めて出る略語に説明が無い: %s' % ', '.join(bad[:6]),
                '初めて出る枚で「JAXA（宇宙航空研究開発機構）」のように（）で説明するか、※の行で説明する。'
                '聞き手が知っている語なら spec_lock に terms_ok: %s' % ', '.join(bad[:6])))


def check_references(infos, roles, genre, issues):
    """G9: 研究の発表は、末尾に参考文献（出典一覧・References）の枚があるか。図表番号は出典が無いので見ない。"""
    sev = genre_sev('G9', genre)
    if sev is None or not infos:
        return
    if roles:
        tail = [info for info in infos if info['role'] == 'T'] or infos[-1:]
    else:
        tail = infos[-2:]
    if not any(REFS_RE.search(ln.text) for info in tail for ln in info['lines']):
        issues.append(Issue(
            sev, '(全体)', 'G9 研究の発表なのに、末尾に参考文献（出典一覧・References）の枚が無い',
            '最後（謝辞の前か後）に参考文献の枚を1枚置き、prep では T にする'))


def check_colors(svg_files, issues):
    from collections import Counter
    counter = Counter()
    for f in svg_files:
        content = f.read_text(encoding='utf-8', errors='replace')
        for hexv in re.findall(r'#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b', content):
            counter[hexv.upper()] += 1
    if counter:
        top = ', '.join('%s×%d' % (c, n) for c, n in counter.most_common(12))
        issues.append(Issue('INFO', '(全体)', '使用色 %d 種: %s' % (len(counter), top)))
        if len(counter) > 12:
            issues.append(Issue(
                'WARNING', '(全体)',
                '使用色が %d 種と多い — 「色は3系統＋白＋タイント」の統一を確認' % len(counter),
                'color_audit.py で棚卸し → 近似色を spec_lock のトークンへ寄せる'))


# ------------------------------------------------------------------ main ---

def resolve_svg_dir(path):
    """(project_dir, svg_dir) を返す。svg_output/ を直接渡されても親をプロジェクトとして扱う
    ＝spec_lock.md（delivery）や notes/total.md を親から正しく見つけられるようにする（確定指摘①）。"""
    p = Path(path)
    if (p / 'svg_output').is_dir():
        return p, p / 'svg_output'
    if p.name == 'svg_output':
        return p.parent, p
    return p, p


def main(argv=None):
    ap = argparse.ArgumentParser(description='PPT Master deck doctor（提出前一括診断）')
    ap.add_argument('path', help='プロジェクトdir または SVG dir')
    ap.add_argument('--json', action='store_true', help='JSON 出力（自動修正ループ用）')
    ap.add_argument('--strict', action='store_true', help='WARNING も exit 1 にする')
    ap.add_argument('--no-overlap', action='store_true', help='重なり検出を省略')
    ap.add_argument('--talk', action='store_true',
                    help='話す型検査を強制ON（既定は spec_lock の delivery=presentation で自動ON）')
    ap.add_argument('--no-talk', action='store_true', help='話す型検査を強制OFF')
    ap.add_argument('--draft', action='store_true',
                    help='途中の確認用ビルド: R0（照合）・R1（初見の読み手）の記録を WARNING に下げる')
    ap.add_argument('--legacy', action='store_true',
                    help='9/28 以前のデッキの作り直し: 中身の検査 C1〜C6・R0・R1・目次 A0・G1・G4a を WARNING に下げる')
    args = ap.parse_args(argv)

    project_dir, svg_dir = resolve_svg_dir(args.path)
    if not svg_dir.is_dir():
        print('ディレクトリが見つかりません: %s' % svg_dir)
        return 2
    svg_files = sorted(svg_dir.glob('*.svg'))
    if not svg_files:
        print('SVG がありません: %s' % svg_dir)
        return 2

    issues = []
    infos, has_notes = slide_infos(project_dir, svg_files)
    roles = parse_prep(project_dir)

    # 中身の検査（C1〜C6・R0）を先に走らせ、先に出す（形だけ直しても中身の問題は消えない）
    # 旧書式として扱うのは --legacy を明示した時だけ（2026-09-28 反証: brief_confirmed の日付を手で古く書くだけで
    # 中身の検査が WARNING に下がる抜け道になっていた。日付による自動判定は廃止）
    legacy = args.legacy
    if legacy:
        issues.append(Issue('INFO', '(全体)', '旧書式のデッキとして扱う（--legacy 指定）＝中身の検査 C1〜C6・R0・R1・A0・G1・G4a は WARNING に下げた'))
    brief = check_content(project_dir, infos, roles, issues, legacy)
    check_evidence_record(project_dir, svg_files, issues, args.draft, legacy)
    check_reader_record(project_dir, svg_files, issues, args.draft, legacy)
    if args.draft:
        issues.append(Issue('INFO', '(全体)', '--draft: 途中の確認用ビルド（R0 の照合・R1 の初見の読み手の記録は WARNING）'))

    check_annotations_left(svg_files, issues)
    check_footers(svg_files, issues)
    check_notes(project_dir, svg_files, issues)
    check_kinsoku(svg_files, issues)
    check_overflow(svg_files, issues)
    if not args.no_overlap:
        check_overlap(svg_files, issues)
    check_dy_headline(svg_files, issues)

    # 話す型検査: --talk で強制ON / --no-talk で強制OFF / 既定は delivery から自動判定
    delivery = detect_delivery(project_dir)
    # 既定は話す型（デザイン品質.md「既定は話す型＝登壇」）。配布・印刷と明記した時だけ外す（2026-09-28）
    READING = ('document', 'balanced', 'handout', 'print', 'report', 'reading')
    talk_on = args.talk or (not args.no_talk and delivery not in READING)
    if talk_on:
        why = ('--talk 指定' if args.talk else
               'spec_lock: delivery=%s' % delivery if delivery else 'delivery 未記載＝既定の話す型')
        issues.append(Issue('INFO', '(全体)', '話す型検査 ON（%s）' % why))
        check_talk_mode(svg_files, issues)
    elif args.no_talk:
        issues.append(Issue('INFO', '(全体)', '話す型検査 OFF（--no-talk 指定）'))
    else:
        issues.append(Issue('INFO', '(全体)', '話す型検査 OFF（delivery=%s＝配布・印刷用。発表用なら --talk）' % delivery))

    # PREP と「中身の確認（選択式）」は用途に関係なく全デッキで見る（2026-09-28。本人の指示はスライド全般への物。
    # 配布用 balanced が confirm_ui の既定値だった時期に、この2つが黙って外れていた）
    check_prep(project_dir, svg_files, issues)
    # 目次（A0〜A3）。本人の既定＝全デッキに目次（2026-09-28）
    check_agenda(project_dir, infos, roles, issues, legacy)
    check_brief(project_dir, issues)
    check_ai_copy(svg_files, issues, brief)
    # 意味の検査（M1〜M9。2026-10-01「結局何を言いたいのか伝わらない」）。スライドの文字だけで意味が通るかの手がかり
    check_meaning(infos, issues)
    # 形の検査（F1〜F8・Q1・Q2。2026-09-28「AIっぽい」の型の数値化）。用途に関係なく全デッキで見る
    check_form(project_dir, infos, roles, has_notes, brief, issues)
    # 資料の種類（genre）ごとの検査（G1〜G9）
    check_genre(project_dir, infos, roles, brief, issues, legacy)
    check_colors(svg_files, issues)

    errors = [i for i in issues if i.severity == 'ERROR']
    warnings = [i for i in issues if i.severity == 'WARNING']
    infos = [i for i in issues if i.severity == 'INFO']

    if args.json:
        print(json.dumps({
            'project': str(project_dir), 'slides': len(svg_files),
            'errors': len(errors), 'warnings': len(warnings),
            'issues': [i.to_dict() for i in issues],
        }, ensure_ascii=False, indent=2))
    else:
        print('=== deck_doctor: %s (%d 枚) ===' % (project_dir.name, len(svg_files)))
        for sev, group in (('ERROR', errors), ('WARNING', warnings), ('INFO', infos)):
            for i in group:
                print('[%s] %s: %s' % (sev, i.file, i.message))
                if i.fix:
                    print('         → %s' % i.fix)
        print('--- サマリ: ERROR %d / WARNING %d / INFO %d ---' % (len(errors), len(warnings), len(infos)))
        if not errors and not warnings:
            print('OK: 機械検出できる範囲は問題なし（写真の妥当性・誤読・掴みは目視レビューで）')

    if errors:
        return 1
    if args.strict and warnings:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
