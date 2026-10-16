"""report/lint.py - レポートWord文書の体裁・整合性チェッカー（cp932安全）

usage:
    py lint.py <path_to.docx> [--fig-start N] [--table-start N] [--range-file <学習範囲.md>]

機械的に検出する項目（[NG] が1件でもあれば exit 1。[警告] は exit 0）:
- 図番号・表番号の連番性（飛び番・重複）／表1・図1から始まっているか      [NG]
- 表キャプションが表の上にあるか（学術慣習）                              [NG]
- 図キャプションが図の下にあるか                                          [警告]
- 各図表が本文中から参照されているか（SKILL.md 注意事項・P-009）          [NG]
- 数式番号の表記揺れ（「（式1）」と「…(1)」の混在・P-006）              [NG]
- 番号付きの数式が本文から参照されているか（P-010）                      [NG]
  （参照しているのに式が無い番号は [警告]＝プレレポートや教科書の式のことがある）
- 文体の「です/ます」混入（P-012）                                        [NG]
- 主観・口語表現                                                          [警告]
- 履修範囲外の記号（skill-memory/学習範囲.md の「使用NG」節。本文・表・Word数式も見る・P-011） [NG]
- 書きかけの印（【…を記入】（要記入）XX 等）の残存（P-030）              [NG]
- Unicode の上付き・下付き文字（³ ⁻¹ ₁ ₀）の代用（執筆ルール.md・P-034）   [NG]
- 下付きにし損ねた「V_FB」「10^{-3}」表記の残存（P-034）                  [NG]
- Word数式に添字があるのに、本文に下付き書式の run が1つも無い（P-034）  [NG]
- 実験方法の章の「使用機器」見出しと、直後の表の4列（機器・部品／仕様・型番／用途／説明） [NG]
- Word数式の m:t の中に別の数式要素が入っている（Word では正しく見える構造不正・P-051） [NG]
- 文書のプロパティが python-docx の既定のまま（作成者 python-docx・作成日 2013年・P-052） [警告]
- 文の中に代入計算が埋まっている（「27.901 ÷ (1 − 27.901 ÷ 3000) ≒ 28.163 Ω」が行の途中で折れる・P-059） [NG]
  計算例は文を「〜に代入して求めた。」で閉じ、次の行に番号なしの Word 数式で出す（omml_lib.insert_equation_after）
- Headingスタイルの使用                                                   [警告]
"""
import sys
import io
import os
import re
from docx import Document
from docx.oxml.ns import qn

# Windowsのcp932コンソールでも動かすためにstdoutをUTF-8化
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# 出力用マーカー（cp932では絵文字が使えないので記号で代替）
ERR = '[NG]'
WARN = '[警告]'
OK = '[OK]'
INFO = '[情報]'

# Word 数式（OMML）の名前空間
M_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/math'


def mq(tag):
    return '{%s}%s' % (M_NS, tag)


# 履修範囲の記号リスト（正本は skill-memory/学習範囲.md。読めない時だけ下の内蔵一覧を使う）
RANGE_FILE_DEFAULT = os.path.join(os.path.expanduser('~'), '.claude', 'skill-memory', '学習範囲.md')
FALLBACK_NG_SYMBOLS = {
    'Σ': '総和', 'Π': '総積', '∮': '周回積分', '∂': '偏微分', '∇': 'ナブラ・勾配',
    '∈': '要素記号', '∋': '要素記号', '⊂': '包含', '⊃': '包含', '∪': '和集合',
    '∩': '積集合', '∀': '全称量化子', '∃': '存在量化子',
}
# 見た目が同じ別の文字。Word 数式の総和は Σ(U+03A3) ではなく ∑(U+2211) で入る
SYMBOL_ALIASES = {
    'Σ': ['∑'],
    'Π': ['∏'],
    '∂': ['𝜕', '𝝏'],
    '∇': ['𝛁', '𝜵'],
}

# 図・表キャプションの形:「図1 …」「図1(a) …」「図 1　…」「表1. …」
FIG_CAP_PAT = re.compile(r'^図\s?(\d+)(?:\([a-zａ-ｚ]\)|（[a-zａ-ｚ]）)?[.．]?[\s　]')
TABLE_CAP_PAT = re.compile(r'^表\s?(\d+)[.．]?[\s　]')
# 番号の直後がこれらの助詞なら本文の文（「図1 に示す」）
PARTICLES = 'のにをはがでとへもや'

# 使用機器の表の列（2026-09-28 本人決定・references/執筆ルール.md「3.0 使用機器表ルール」）
EQUIP_COLUMNS = ['機器・部品', '仕様・型番', '用途', '説明']

# 数式の関係記号（番号付きの行が「式」かどうかの判定に使う）
RELATION_CHARS = '=＝≒≈≃≅∝<>≤≥≦≧≪≫'

# Unicode の上付き・下付き文字（Word の上付き・下付き書式で書くべきもの）
UNI_SUPSUB_PAT = re.compile('[²³¹⁰-₟ᵢ-ᵪⱼ]')
# 下付き・上付きにし損ねた書き方（rich_text の書式指定がそのまま文字で残っている）
PLAIN_SCRIPT_PAT = re.compile(r'(?<![A-Za-z0-9_])[A-Za-zα-ωΑ-Ω]_(?:\{[^}]*\}|[A-Za-z0-9]+)|\^\{[^}]*\}')

# 文の中に埋まった代入計算（P-059）:「数値[単位] 演算子 数値 … =/≒ 数値」。√(4.7 × 3000) ≒ 119 も拾う。
# 範囲「1〜4 mA」・日付「2026-10-06」（ハイフン）・記号だけの式「R_t + r_V」は拾わない
_CALC_NUM = r'\d+(?:\.\d+)?'
_CALC_UNIT = r'(?:\s*(?:[kMmμ]?(?:Ω|V|A|W|Hz|F|H|s)|%)(?![A-Za-z]))?'
INLINE_CALC_PAT = re.compile(
    r'(?:√\s*[\(（]\s*)?[\(（]?\s*' + _CALC_NUM + _CALC_UNIT +
    r'\s*[÷×/+−]\s*[\(（]?\s*(?:√\s*[\(（]?\s*)?' + _CALC_NUM +
    r'[^。、=＝≒≈]{0,40}?[=＝≒≈]\s*[−-]?\s*' + _CALC_NUM + _CALC_UNIT)

# 書きかけの印（P-030）。【テーマ5】のような題名の括弧は拾わない
PLACEHOLDER_PATS = [
    (re.compile(r'【[^】]*(?:記入|記述|ここに|挿入|追記|要確認|要修正|TODO|未定|未記入|あとで|後で|入れる|書く|貼る|貼付|予定)[^】]*】'),
     '【…記入…】の指示書き'),
    (re.compile(r'【[^】]{15,}】'), '【…】の長い指示書き'),
    (re.compile(r'要記入'), '（要記入）'),
    (re.compile(r'[\[［]\s*ここに[^\]］]*[\]］]'), '［ここに…］'),
    (re.compile(r'TODO|TBD|FIXME'), 'TODO'),
    (re.compile(r'[○〇●◯]{2,}'), '○○'),
    (re.compile(r'X\.XX|XX\.X|(?<![A-Za-z])XX+(?![A-Za-z])'), 'XX'),
]


def para_text(el):
    return ''.join(t.text or '' for t in el.iter(qn('w:t')))


def is_code_paragraph(el):
    """ソースコード用フォント（Consolas / Courier New）の段落か"""
    for rf in el.iter(qn('w:rFonts')):
        name = rf.get(qn('w:ascii')) or ''
        if 'Consolas' in name or 'Courier' in name:
            return True
    return False


def get_items_in_order(doc):
    """文書本体を「段落」「表」の順に取得。段落は alignment/bold と Word 数式の有無も保持"""
    body = doc.element.body
    items = []
    last_para = ''

    # body直下の子要素のみ走査（表セル内の段落は自然に除外される）
    for child in list(body):
        if child.tag == qn('w:p'):
            text = para_text(child)
            has_image = (child.find('.//' + qn('w:drawing')) is not None or
                         child.find('.//' + qn('w:pict')) is not None)
            # alignment取得
            alignment = None
            pPr = child.find(qn('w:pPr'))
            if pPr is not None:
                jc = pPr.find(qn('w:jc'))
                if jc is not None:
                    alignment = jc.get(qn('w:val'))
            # 太字 (run単位なので、最初のrunがboldならキャプション可能性)
            is_bold = False
            for r in child.findall(qn('w:r')):
                rPr = r.find(qn('w:rPr'))
                if rPr is not None and rPr.find(qn('w:b')) is not None:
                    is_bold = True
                    break
            has_math = child.find('.//' + mq('oMath')) is not None
            items.append({
                'kind': 'para',
                'text': text,
                'has_image': has_image,
                'alignment': alignment,
                'is_bold': is_bold,
                'has_math': has_math,
                'is_code': is_code_paragraph(child),
            })
            if text.strip():
                last_para = text.strip()
        elif child.tag == qn('w:tbl'):
            rows = child.findall(qn('w:tr'))
            header = []
            if rows:
                header = [para_text(tc) for tc in rows[0].findall(qn('w:tc'))]
            cells = [para_text(tc) for tc in child.iter(qn('w:tc'))]
            joined = '\n'.join(cells)
            is_code = (last_para.startswith('リスト') or '#include' in joined or joined.count(';') >= 3)
            items.append({
                'kind': 'table',
                'text': '[TABLE]',
                'header': header,
                'cells': cells,
                'is_code': is_code,
            })
            last_para = ''
    return items


def is_caption_paragraph(item, text):
    """キャプション段落の判定: 「図N」「表N」＋空白で始まる短い段落。

    2026-09-28 に緩めた。以前は「である」「を測定」等を含む段落を外していたため、
    「図5 位相差を測定するときの入出力波形」のような正しいキャプションまで外れ、
    誤った欠番 NG が出た（skill-memory/report.md 2026-06-25 の記録）。
    本文の文と見分けるのは次の3つだけにした:
      - 100字以下で「。」を含まない
      - 番号の後の最初の文字が助詞（の・に・を…）でない（「図1 に示す」は本文）

    中央揃え・太字は学術慣習だが SKILL.md STEP 3 の図表挿入ルールでは必須化して
    いないため判定の前提条件にはしない（必須にすると add_para 経由の非太字・非中央
    キャプションを全て取りこぼし、Check 1〜5 が無言でパスしてしまう）。
    """
    m = FIG_CAP_PAT.match(text)
    if not m:
        m = TABLE_CAP_PAT.match(text)
    if not m:
        return False
    if len(text) > 100:
        return False
    if '。' in text:
        return False
    rest = text[m.end():].lstrip(' 　')
    if rest and rest[0] in PARTICLES:
        return False
    return True


def ref_numbers(text, word):
    """本文中の「図1」「図2〜4」「図1、図3」「表 2」などから参照されている番号を集める。
    word は '図' か '表'。「〜」「-」は範囲として間の番号も全部数える"""
    nums = set()
    pat = re.compile(word + r'\s?(\d+)')
    cont = re.compile(r'\s*([、,・〜～~\-−–]|および|及び|と|や)\s*(?:' + word + r')?\s?(\d+)')
    for m in pat.finditer(text):
        prev = int(m.group(1))
        nums.add(prev)
        pos = m.end()
        while True:
            c = cont.match(text, pos)
            if not c:
                break
            n = int(c.group(2))
            if c.group(1) in ('〜', '～', '~', '-', '−', '–') and prev < n <= prev + 50:
                for k in range(prev, n + 1):
                    nums.add(k)
            else:
                nums.add(n)
            prev = n
            pos = c.end()
    return nums


# 式番号の定義: 段落の末尾にある「（式1）」「(式1)」「式(1)」「(1)」
EQ_DEF_TAIL = re.compile(
    r'(?:[\(（]\s*式\s*(\d+)\s*[\)）]|式\s*[\(（]\s*(\d+)\s*[\)）]|[\(（]\s*(\d+)\s*[\)）])\s*$')
# 式の参照:「式1」「式(1)」「式 (1)」「（式1）」「(1)式」。続く「〜(3)」「、(4)」も拾う
EQ_REF = re.compile(r'式\s*[\(（]?\s*(\d+)\s*[\)）]?|[\(（]\s*(\d+)\s*[\)）]\s*式')
EQ_REF_CONT = re.compile(r'\s*([、,・〜～~\-−–]|および|及び|と)\s*(?:式)?\s*[\(（]?\s*(\d+)\s*[\)）]?')


def eq_definition(item):
    """番号付きの数式の段落なら (番号, 番号部分を除いた文字) を返す。そうでなければ None。
    Word 数式（OMML）を含む段落は末尾の番号だけで式とみなす。
    数式オブジェクトの無い段落は「関係記号（= ≒ 等）を含み、句点が無い」行だけを式とみなす"""
    text = item['text'].strip()
    m = EQ_DEF_TAIL.search(text)
    if not m:
        return None
    num = m.group(1) or m.group(2) or m.group(3)
    rest = text[:m.start()]
    if item.get('has_math'):
        return int(num), rest
    # 「…近似的に式1で表せる。（改行）N = c / n （式1）」のように文と式が同じ段落のこともあるので、
    # 最後の「。」より後ろ（＝式の行）に関係記号があるかで判定する
    tail = rest.split('。')[-1]
    has_relation = False
    for ch in RELATION_CHARS:
        if ch in tail:
            has_relation = True
            break
    if not has_relation:
        return None
    return int(num), rest


def eq_ref_numbers(text):
    nums = set()
    for m in EQ_REF.finditer(text):
        prev = int(m.group(1) or m.group(2))
        nums.add(prev)
        pos = m.end()
        while True:
            c = EQ_REF_CONT.match(text, pos)
            if not c:
                break
            n = int(c.group(2))
            if c.group(1) in ('〜', '～', '~', '-', '−', '–') and prev < n <= prev + 50:
                for k in range(prev, n + 1):
                    nums.add(k)
            else:
                nums.add(n)
            prev = n
            pos = c.end()
    return nums


def load_ng_symbols(path):
    """学習範囲.md の「使用NG」節から、使ってはいけない記号を読み込む。
    太字 **…** の中の、括弧（説明）より前にある1文字の記号だけを拾う
    （「ベクトル記号」「行列・行列式」のような言葉は機械で探せないので拾わない）。
    戻り値: ({記号: 説明}, 出どころの説明)"""
    try:
        with open(path, encoding='utf-8') as f:
            lines = f.read().splitlines()
    except OSError:
        return dict(FALLBACK_NG_SYMBOLS), '内蔵の一覧（%s が読めない）' % path
    symbols = {}
    in_ng = False
    for line in lines:
        if line.startswith('#'):
            in_ng = ('使用NG' in line)
            continue
        if not in_ng:
            continue
        for bold in re.findall(r'\*\*(.+?)\*\*', line):
            head = re.split(r'[（(]', bold)[0]
            desc_m = re.search(r'[（(](.+?)[）)]', bold)
            desc = desc_m.group(1) if desc_m else head
            for tok in re.split(r'[,、・\s]+', head):
                if len(tok) != 1:
                    continue
                if tok.isascii():
                    continue
                if '぀' <= tok <= '鿿':
                    continue
                symbols[tok] = desc
    if not symbols:
        return dict(FALLBACK_NG_SYMBOLS), '内蔵の一覧（%s の「使用NG」節から記号を読めない）' % path
    return symbols, os.path.basename(path)


def text_blocks(doc):
    """本文段落と表のセルの文字を (場所, 文字) で返す。プログラムのリスト（表・Consolas段落）は除く"""
    blocks = []
    last_para = ''
    pn = 0
    for child in list(doc.element.body):
        if child.tag == qn('w:p'):
            pn += 1
            text = para_text(child)
            if text.strip() and not is_code_paragraph(child):
                blocks.append(('本文%d段落目' % pn, text))
            if text.strip():
                last_para = text.strip()
        elif child.tag == qn('w:tbl'):
            cells = [para_text(tc) for tc in child.iter(qn('w:tc'))]
            joined = '\n'.join(cells)
            if last_para.startswith('リスト') or '#include' in joined or joined.count(';') >= 3:
                last_para = ''
                continue
            m = re.match(r'^表\s?\d+', last_para)
            if m:
                label = m.group(0).replace(' ', '')
            else:
                label = '表'
            for t in cells:
                if t.strip():
                    blocks.append(('%sのセル' % label, t))
            last_para = ''
    return blocks


def snippet(text, m, width=10):
    s = max(0, m.start() - width)
    return text[s:m.end() + width].replace('\n', ' ')


def check_equipment(items, issues, infos):
    """実験方法の章に「使用機器」見出しと4列の表があるか（プレ・本レポート共通）"""
    method_idx = None
    equip_idx = []
    for i, item in enumerate(items):
        if item['kind'] != 'para':
            continue
        text = item['text'].strip()
        if not text or len(text) > 30 or '。' in text:
            continue
        if FIG_CAP_PAT.match(text) or TABLE_CAP_PAT.match(text):
            continue
        if method_idx is None and re.search(r'実験(?:の)?方法', text):
            method_idx = i
        if '使用機器' in text:
            equip_idx.append(i)
    if method_idx is None:
        infos.append('%s 「実験方法」の見出しが無いので、使用機器の見出し・表の検査は省略'
                     '（技術報告書や、実験方法をプレレポートに書いた本レポート）' % INFO)
        return
    if not equip_idx:
        issues.append('%s 実験方法の章に「使用機器」の見出しが無い（見出しの直後に 機器・部品／仕様・型番／'
                      '用途／説明 の4列の表を置く。references/執筆ルール.md 3.0）' % ERR)
        return
    for idx in equip_idx:
        head = items[idx]['text'].strip()
        if idx < method_idx:
            issues.append('%s 「%s」が「実験方法」の見出しより前にある（実験方法の章の中に置く）' % (WARN, head))
        table = None
        for j in range(idx + 1, min(idx + 7, len(items))):
            it = items[j]
            if it['kind'] == 'table':
                table = it
                break
            t = it['text'].strip()
            # 次の節の見出し（「3.1 実験1」等）に着いたら探すのをやめる
            if re.match(r'^\s*\d+(?:[.．]\d+)*[\s　.．]', t) and len(t) <= 40:
                break
        if table is None:
            issues.append('%s 「%s」の見出しの後に表が無い（機器・部品／仕様・型番／用途／説明 の4列の表を置く）'
                          % (ERR, head))
            continue
        got = []
        for h in table['header']:
            h = re.sub(r'\s', '', h)
            h = re.sub(r'[／/･・]', '・', h)
            got.append(h)
        if got != EQUIP_COLUMNS:
            issues.append('%s 使用機器の表の列が %s。4列（%s）にする（2026-09-28 本人決定）'
                          % (ERR, got, '／'.join(EQUIP_COLUMNS)))


def lint(path, fig_start=1, table_start=1, range_file=None):
    """fig_start, table_start: 図・表番号の期待開始値（部分レポート用）"""
    doc = Document(path)
    items = get_items_in_order(doc)
    issues = []
    infos = []

    # 「図1 ...」「図1(a) ...」「図1（a） ...」「図 1 ...」「表1. ...」を許容
    fig_cap_pat = FIG_CAP_PAT
    table_cap_pat = TABLE_CAP_PAT

    fig_captions = []  # [(idx, num, text)]
    table_captions = []

    for idx, item in enumerate(items):
        if item['kind'] != 'para' or item.get('has_image'):
            continue
        text = item['text'].strip()
        if not text:
            continue
        if not is_caption_paragraph(item, text):
            continue
        m = fig_cap_pat.match(text)
        if m:
            fig_captions.append((idx, int(m.group(1)), text))
            continue
        m = table_cap_pat.match(text)
        if m:
            table_captions.append((idx, int(m.group(1)), text))

    # ===== Check 1: 図番号の連番性 =====
    fig_nums = sorted(n for _, n, _ in fig_captions)
    if fig_nums:
        if fig_nums[0] != fig_start:
            issues.append(f'[NG] 図番号が図{fig_start}から始まっていない（図{fig_nums[0]}始まり）')
        expected = list(range(fig_nums[0], fig_nums[-1] + 1))
        missing = [n for n in expected if n not in fig_nums]
        if missing:
            issues.append(f'[NG] 図番号の飛び番: 図{missing} が欠番')
        dup = [n for n in fig_nums if fig_nums.count(n) > 1]
        if dup:
            issues.append(f'[NG] 図番号の重複: 図{set(dup)}')

    # ===== Check 2: 表番号の連番性 =====
    table_nums = sorted(n for _, n, _ in table_captions)
    if table_nums:
        if table_nums[0] != table_start:
            issues.append(f'[NG] 表番号が表{table_start}から始まっていない（表{table_nums[0]}始まり）')
        expected = list(range(table_nums[0], table_nums[-1] + 1))
        missing = [n for n in expected if n not in table_nums]
        if missing:
            issues.append(f'[NG] 表番号の飛び番: 表{missing} が欠番')
        dup = [n for n in table_nums if table_nums.count(n) > 1]
        if dup:
            issues.append(f'[NG] 表番号の重複: 表{set(dup)}')

    # ===== Check 3: 表キャプションは表の上にあるか =====
    for cap_idx, num, _ in table_captions:
        is_above = False
        for j in range(cap_idx + 1, min(cap_idx + 4, len(items))):
            if items[j]['kind'] == 'table':
                is_above = True
                break
            if items[j]['kind'] == 'para' and items[j]['text'].strip() and not items[j].get('has_image'):
                # 別の本文段落が先に来た = キャプションの直後に表がない
                break
        is_below = False
        if not is_above:
            for j in range(max(0, cap_idx - 3), cap_idx):
                if items[j]['kind'] == 'table':
                    is_below = True
                    break
        if is_below:
            issues.append(f'[NG] 表{num} のキャプションが表の下にある（学術慣習：表は上）')

    # ===== Check 4: 図キャプションは図の下にあるか =====
    for cap_idx, num, _ in fig_captions:
        is_below = False
        for j in range(max(0, cap_idx - 3), cap_idx):
            if items[j]['kind'] == 'para' and items[j].get('has_image'):
                is_below = True
                break
        if not is_below:
            issues.append(f'[警告] 図{num} のキャプションの直前に図画像が見当たらない（または図の上に配置）')

    # ===== Check 5: 図表が本文中で参照されているか（2026-09-28 から NG） =====
    # キャプション行と画像段落を除いた本文＋表のセル（表の「対応図」列から図を指す書き方も数える）
    caption_indices = {idx for idx, _, _ in fig_captions + table_captions}
    parts = []
    for i, item in enumerate(items):
        if item['kind'] == 'para' and not item.get('has_image') and i not in caption_indices:
            parts.append(item['text'])
        elif item['kind'] == 'table' and not item.get('is_code'):
            parts += item['cells']
    body_text = '\n'.join(parts)
    referenced_figs = ref_numbers(body_text, '図')
    referenced_tables = ref_numbers(body_text, '表')
    for _, num, _ in fig_captions:
        if num not in referenced_figs:
            issues.append(f'[NG] 図{num} は本文中で参照されていない（「図{num}に示す」等で必ず触れる）')
    for _, num, _ in table_captions:
        if num not in referenced_tables:
            issues.append(f'[NG] 表{num} は本文中で参照されていない（「表{num}に示す」等で必ず触れる）')

    # ===== Check 6: 数式番号の表記揺れ =====
    body_full = '\n'.join(item['text'] for item in items if item['kind'] == 'para')
    eq_styles = []
    if re.search(r'（式\d+）', body_full):
        eq_styles.append('（式N）')
    if re.search(r'…\(\d+\)', body_full) or re.search(r'\.\.\.\(\d+\)', body_full):
        eq_styles.append('…(N)')
    if re.search(r'(?<![…\.])\(式\d+\)', body_full):
        eq_styles.append('(式N)')
    if re.search(r'^\s*\(\d+\)\s*$', body_full, re.MULTILINE):
        eq_styles.append('(N)')
    if len(eq_styles) > 1:
        issues.append(f'[NG] 数式番号の表記揺れ: {eq_styles} が混在。1つに統一')

    # ===== Check 6b: 番号付きの数式が本文から参照されているか（P-010） =====
    eq_defs = {}       # 番号 → 出てきた回数
    eq_refs = set()
    for i, item in enumerate(items):
        if item['kind'] == 'table':
            if not item.get('is_code'):
                for t in item['cells']:
                    eq_refs |= eq_ref_numbers(t)
            continue
        d = eq_definition(item)
        if d is not None:
            eq_defs[d[0]] = eq_defs.get(d[0], 0) + 1
            eq_refs |= eq_ref_numbers(d[1])   # 式の行の中で別の式を指している分
        else:
            eq_refs |= eq_ref_numbers(item['text'])
    for n in sorted(eq_defs):
        if n not in eq_refs:
            issues.append(f'[NG] 式({n}) は本文から参照されていない（P-010。「式({n})より」等で使うか、番号を外す）')
        if eq_defs[n] > 1:
            issues.append(f'[警告] 式({n}) の番号が {eq_defs[n]} 回付いている（番号の重複）')
    undefined = sorted(n for n in eq_refs if n not in eq_defs)
    if undefined:
        names = '、'.join(f'式({n})' for n in undefined)
        issues.append(f'[警告] {names} を参照しているが、この文書にその番号の式が無い'
                      '（プレレポート・教科書の式なら「教科書の式(22)」のように出どころを書く）')

    # ===== Check 7: 文体「です/ます」混入 =====
    desu_masu = re.findall(r'(です。|ます。|ました。|ません。|でした。)', body_full)
    if desu_masu:
        issues.append(f'[NG] 「です/ます」調が {len(desu_masu)} 箇所（実験レポートは「である」調で統一）')

    # ===== Check 8: 主観・口語表現 =====
    subjective_words = ['と思う', 'と感じた', 'と思った', '感じる', 'だいたい', 'ぶん',
                        'お弁当', 'ボタン一つで', 'ありがたみ', '点きっぱなし']
    found_subjective = [w for w in subjective_words if w in body_full]
    if found_subjective:
        issues.append(f'[警告] 主観・口語表現の検出: {found_subjective}')

    # ===== Check 9: 履修範囲外記号（学習範囲.md 連動・本文／表／Word数式・P-011） =====
    ng_symbols, source_desc = load_ng_symbols(range_file or RANGE_FILE_DEFAULT)
    infos.append(f'{INFO} 履修範囲外の記号の一覧: {source_desc}（{"".join(sorted(ng_symbols))}）')
    body = doc.element.body
    w_text = '\n'.join(t.text or '' for t in body.iter(qn('w:t')))
    m_text = '\n'.join(t.text or '' for t in body.iter(mq('t')))
    m_chrs = ''.join(c.get(mq('val')) or '' for c in body.iter(mq('chr')))
    for sym in sorted(ng_symbols):
        desc = ng_symbols[sym]
        variants = [sym] + SYMBOL_ALIASES.get(sym, [])
        where = []
        for v in variants:
            if v in w_text:
                where.append(f'本文・表に「{v}」')
            if v in m_text or v in m_chrs:
                where.append(f'Word数式に「{v}」')
        if where:
            issues.append(f'[NG] 履修範囲外の記号「{sym}」({desc}): {"・".join(where)}'
                          '（学習範囲.md に従い展開形に書き換える。例 I_1 + I_2 + … + I_n）')

    # ===== Check 11: 書きかけの印の残存（P-030） =====
    blocks = text_blocks(doc)
    for place, text in blocks:
        for pat, label in PLACEHOLDER_PATS:
            m = pat.search(text)
            if m:
                issues.append(f'[NG] 書きかけの印（{label}）が残っている: {place}「…{snippet(text, m)}…」（P-030）')
                break

    # ===== Check 12: Unicode の上付き・下付き文字（執筆ルール.md・P-034） =====
    hits = []
    for place, text in blocks:
        for m in UNI_SUPSUB_PAT.finditer(text):
            hits.append(f'{place}「…{snippet(text, m, 6)}…」')
    for m in UNI_SUPSUB_PAT.finditer(m_text):
        hits.append(f'Word数式「…{snippet(m_text, m, 6)}…」')
    if hits:
        more = f' ほか{len(hits) - 5}件' if len(hits) > 5 else ''
        issues.append(f'[NG] Unicode の上付き・下付き文字が {len(hits)} 個（³ ⁻¹ ₁ ₀ などは Word の上付き・下付き書式で書く。'
                      f'rich_text.add_rich の V_{{1}}・10^{{-3}}）: {" / ".join(hits[:5])}{more}')

    # ===== Check 13: 下付きにし損ねた書き方の残存（P-034） =====
    hits = []
    for place, text in blocks:
        for m in PLAIN_SCRIPT_PAT.finditer(text):
            hits.append(f'{place}「{m.group(0)}」')
    if hits:
        more = f' ほか{len(hits) - 5}件' if len(hits) > 5 else ''
        issues.append(f'[NG] 下付き・上付きの書式指定が文字のまま残っている {len(hits)} 箇所'
                      f'（add_rich を通していない）: {" / ".join(hits[:5])}{more}')

    # ===== Check 14: Word数式に添字があるのに下付き書式の run が0個（P-034） =====
    n_sub_runs = 0
    for va in body.iter(qn('w:vertAlign')):
        if va.get(qn('w:val')) == 'subscript':
            n_sub_runs += 1
    n_math_sub = len(list(body.iter(mq('sSub')))) + len(list(body.iter(mq('sSubSup'))))
    if n_math_sub > 0 and n_sub_runs == 0:
        issues.append(f'[NG] Word数式に添字が {n_math_sub} 個あるのに、本文・表に下付き書式の文字が1つも無い'
                      '（物理量記号 V_out 等がプレーン表示。本文も rich_text.add_rich で書く）')

    # ===== Check 15: 使用機器の見出しと4列の表 =====
    check_equipment(items, issues, infos)

    # ===== Check 16: Word数式の m:t の中に別の数式要素が入っている（構造不正・P-051） =====
    # Word は開けて PDF も正しく出すので目視では見つからない。sSub 等の断片を r() で包んで sSup の底にした時に起きる
    nested = [t for t in body.iter(mq('t')) if len(t) > 0]
    if nested:
        issues.append(f'[NG] Word数式の m:t の中に数式の要素が入っている（構造不正）: {len(nested)} か所'
                      '（Word では正しく見えるが他の環境で底や添字が欠ける。sSub などの断片は r() で包まず m:e に直接入れる。P-051）')

    # ===== Check 17: 文書のプロパティが python-docx の既定のまま（P-052） =====
    cp = doc.core_properties
    created = cp.created
    if (cp.author or '').strip() in ('', 'python-docx') or (created is not None and created.year < 2020):
        issues.append('[警告] 文書のプロパティが python-docx の既定のまま'
                      f'（作成者「{cp.author}」・作成日 {created.date() if created else "なし"}）。'
                      '提出物の作成者・題名・日時を生成スクリプトで設定する（doc.core_properties の author・title・created。P-052）')

    # ===== Check 18: 文の中に代入計算が埋まっている（P-059・2026-10-07 本人「計算式などはきちんと改行して見やすく」） =====
    # 本文の文（「。」を含む段落）だけを見る。表のセル・キャプション・コード・式だけの行は対象外
    hits = []
    for item in items:
        if item['kind'] != 'para' or item.get('is_code'):
            continue
        text = item['text'].strip().replace(' ', ' ')
        if '。' not in text or is_caption_paragraph(item, text):
            continue
        for m in INLINE_CALC_PAT.finditer(text):
            hits.append(f'「{m.group(0).strip()}」')
    if hits:
        more = f' ほか{len(hits) - 5}件' if len(hits) > 5 else ''
        issues.append(f'[NG] 文の中に代入計算が {len(hits)} か所埋まっている（行の途中で式が折れて読めない）: '
                      f'{" / ".join(hits[:5])}{more}。文を「〜に代入して求めた。」で閉じ、次の行に番号なしの '
                      'Word 数式（分数・√）で出す＝omml_lib.insert_equation_after（P-059）')

    # ===== Check 10: Headingスタイル使用 =====
    for p in doc.paragraphs:
        if p.style.name.startswith('Heading'):
            issues.append(f'[警告] Headingスタイルが使用されている（実験レポートはNormal+太字を推奨）')
            break

    return issues, {
        'fig_count': len(fig_captions),
        'table_count': len(table_captions),
        'fig_nums': fig_nums,
        'table_nums': table_nums,
        'eq_nums': sorted(eq_defs),
        'infos': infos,
    }


def main():
    if len(sys.argv) < 2:
        print('usage: python lint.py <path_to.docx> [--fig-start N] [--table-start N] [--range-file <学習範囲.md>]')
        sys.exit(2)
    path = sys.argv[1]
    fig_start = 1
    table_start = 1
    range_file = None
    if '--fig-start' in sys.argv:
        fig_start = int(sys.argv[sys.argv.index('--fig-start') + 1])
    if '--table-start' in sys.argv:
        table_start = int(sys.argv[sys.argv.index('--table-start') + 1])
    if '--range-file' in sys.argv:
        range_file = sys.argv[sys.argv.index('--range-file') + 1]
    print(f'Linting: {path}')
    if fig_start != 1 or table_start != 1:
        print(f'  （部分レポートモード: 図{fig_start}〜 / 表{table_start}〜）')
    print()
    issues, stats = lint(path, fig_start=fig_start, table_start=table_start, range_file=range_file)
    print(f'検出: 図 {stats["fig_count"]}個 / 表 {stats["table_count"]}個 / 番号付きの式 {len(stats["eq_nums"])}個')
    if stats['fig_nums']:
        print(f'  図番号: {stats["fig_nums"]}')
    if stats['table_nums']:
        print(f'  表番号: {stats["table_nums"]}')
    if stats['eq_nums']:
        print(f'  式番号: {stats["eq_nums"]}')
    for s in stats['infos']:
        print(f'  {s}')
    print()
    if not issues:
        print('[OK] 全チェック通過 — 体裁問題なし')
        sys.exit(0)
    error_count = sum(1 for i in issues if i.startswith('[NG]'))
    print(f'[警告] 検出された問題: {len(issues)}件（うち NG {error_count}件）\n')
    for i, issue in enumerate(issues, 1):
        print(f'  {i}. {issue}')
    sys.exit(1 if error_count else 0)


if __name__ == '__main__':
    main()
