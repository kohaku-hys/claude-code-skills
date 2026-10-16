"""
preview-report スキル スモークテスト

使い方:
    python ~/.claude/skills/preview-report/scripts/smoke_test.py

スキル改変後・定期チェック用。全項目（sharepoint_folder の実30件グルーピング・
manifest 往復を含む）を数秒で検証。
"""
import sys, os, importlib

# コンソール出力の日本語文字化け（cp932 環境）対策。テスト判定には影響しないが
# 実行時の表示を正しくするため stdout/stderr を UTF-8 へ再構成する。
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    sys.stderr.reconfigure(encoding='utf-8', errors='backslashreplace')
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

failed = []
def check(name, fn):
    try:
        fn()
        print(f'  OK  : {name}')
    except Exception as e:
        print(f'  FAIL: {name}: {e}')
        failed.append(name)

print('=== モジュール import ===')
check('omml_lib',   lambda: importlib.import_module('omml_lib'))
check('chrome_cdp', lambda: importlib.import_module('chrome_cdp'))
check('cdp_seek',   lambda: importlib.import_module('cdp_seek'))
check('report_gen', lambda: importlib.import_module('report_gen'))

print('\n=== omml_lib 主要関数 ===')
from omml_lib import (m_det, m_r, m_ri, m_frac, m_sum, m_int,
                       m_transpose, m_inverse, m_generic_matrix,
                       m_abs, m_norm)
check('m_det',            lambda: m_det([[m_r('1'), m_r('2')]]))
check('m_frac',           lambda: m_frac(m_r('1'), m_r('2')))
check('m_sum',            lambda: m_sum(m_r('i=1'), m_ri('n'), m_ri('i')))
check('m_int',            lambda: m_int(m_r('0'), m_r('∞'), m_ri('x')))
check('m_transpose',      lambda: m_transpose(m_ri('A')))
check('m_inverse',        lambda: m_inverse(m_ri('A')))
check('m_generic_matrix', lambda: m_generic_matrix(3, 3))
check('m_abs',            lambda: m_abs(m_ri('x')))
check('m_norm',           lambda: m_norm(m_ri('v')))

print('\n=== chrome_cdp ===')
from chrome_cdp import is_cdp_alive, list_tabs, find_chrome
check('find_chrome',  lambda: os.path.isfile(find_chrome()))
check('is_cdp_alive', lambda: isinstance(is_cdp_alive(), bool))
check('list_tabs',    lambda: isinstance(list_tabs(), list))

print('\n=== cdp_seek ===')
from cdp_seek import get_video_tabs
check('get_video_tabs', lambda: isinstance(get_video_tabs(), list))

print('\n=== sharepoint_folder ===')
check('import sharepoint_folder',
      lambda: importlib.import_module('sharepoint_folder'))
import sharepoint_folder as _sf
_SF_SAMPLE = [
    '微分方程式_反転授業用動画_01_1_導入.mp4',
    '微分方程式_反転授業用動画_05_1_変数分離形.mp4',
    '微分方程式_反転授業用動画_05_2_同次形.mp4',
    '微分方程式_反転授業用動画_07_1_x.mp4',
    '微分方程式_反転授業用動画_09_1_2階線形.mp4',
    '科目ガイダンス.mp4',
]
def _t_collector():
    js = _sf.build_collector_js()
    assert isinstance(js, str) and 'querySelectorAll' in js
    for e in ('mp4', 'mov', 'wmv', 'avi', 'mkv', 'm4v'):
        assert e in js, f'missing ext {e}'
check('build_collector_js (str + querySelectorAll + exts)', _t_collector)
def _t_parse_primary():
    r = _sf.parse_one('微分方程式_反転授業用動画_05_2_変数分離形.mp4')
    assert r == {'kai': 5, 'sub': 2, 'topic': '変数分離形', 'ext': 'mp4', 'via': 'primary'}, r
check('parse_one primary', _t_parse_primary)
def _t_parse_case():
    r = _sf.parse_one('微分方程式_反転授業用動画_12_1_x.MP4')
    assert r and r['ext'] == 'mp4' and r['kai'] == 12, r
    assert _sf.parse_one('動画_03_1_a.mp4_x.txt') is None  # 末尾アンカー: 誤爆しない
check('parse_one case-insensitive + end-anchor', _t_parse_case)
def _t_parse_none():
    assert _sf.parse_one('random_video.mp4') is None  # fallback OFF: 強制グループ化しない
check('parse_one non-match -> None', _t_parse_none)
def _t_parse_fallback():
    rule = _sf.load_rule('default_hanten', use_fallback=True)
    r = _sf.parse_one('微分方程式_反転授業用動画_03_2_部分.dat', rule)  # primary外し fallback救済
    assert r and r['kai'] == 3 and r['via'] == 'fallback', r
check('parse_one fallback opt-in', _t_parse_fallback)
def _t_group_gap():
    g = _sf.group_videos(_SF_SAMPLE)
    assert 8 not in g['by_kai_sorted'] and '8' not in g['matched']  # 欠番非補完
check('group_videos 欠番非補完 (kai 8 absent)', _t_group_gap)
def _t_group_unmatched():
    g = _sf.group_videos(_SF_SAMPLE)
    assert '科目ガイダンス.mp4' in g['unmatched']
    assert all(f['filename'] != '科目ガイダンス.mp4' for f in g['flat'])
check('group_videos unmatched 分離', _t_group_unmatched)
def _t_group_shape():
    g = _sf.group_videos(_SF_SAMPLE)
    for k in ('rule_id', 'lectures', 'matched', 'flat', 'by_kai_sorted', 'unmatched'):
        assert k in g, k
    l0 = g['lectures'][0]
    assert all(k in l0 for k in ('kai', 'kai_label', 'videos', 'topics'))
    assert all(k in l0['videos'][0] for k in ('id', 'filename', 'topic'))
check('group_videos 形状', _t_group_shape)
def _t_group_flat():
    g = _sf.group_videos(_SF_SAMPLE)
    matched_n = sum(len(v) for v in g['matched'].values())
    assert matched_n == len(g['flat'])
    assert matched_n + len(g['unmatched']) == len(_SF_SAMPLE)
check('group_videos flat 平坦化', _t_group_flat)
def _t_classify_auth():
    assert _sf.classify_status('https://login.microsoftonline.com/x', []) == 'AUTH_REQUIRED'
check('classify_status AUTH', _t_classify_auth)
def _t_classify_empty_ok():
    assert _sf.classify_status('https://x-my.sharepoint.com/x', []) == 'EMPTY'
    assert _sf.classify_status('https://x-my.sharepoint.com/x', ['a.mp4']) == 'OK'
check('classify_status EMPTY/OK', _t_classify_empty_ok)
def _t_load_rule():
    a, b = _sf.load_rule('default_hanten'), _sf.load_rule('generic')
    assert a is not b
    for r in (a, b):
        assert all(k in r for k in ('rule_id', 'primary', 'fallback', 'use_fallback'))
check('load_rule default_hanten/generic distinct', _t_load_rule)
def _t_enum_sig():
    import inspect as _ins
    assert callable(_sf.enumerate_videos)
    pr = _ins.signature(_sf.enumerate_videos).parameters
    for nm, dv in (('out_json', None), ('recursive', False),
                   ('auth_wait_s', 120), ('timeout_s', 90)):
        assert nm in pr and pr[nm].default == dv, (nm, pr.get(nm))
    assert 'exts' in pr and 'rule' in pr
check('enumerate_videos signature defaults', _t_enum_sig)

# --- 追加項目（ネット不要）: 実30件グルーピング + manifest 往復 ---
def _build_30():
    """実在ファイル名を模した動画30件（回1-7,9-14=13回、第08回は欠番）。"""
    pre = '微分方程式_反転授業用動画'
    counts = {1: 2, 2: 2, 3: 3, 4: 2, 5: 3, 6: 2, 7: 2,
              9: 3, 10: 2, 11: 2, 12: 3, 13: 2, 14: 2}  # 計30件・回8なし
    topics = ['導入', '基礎', '応用']
    out = []
    for kai in sorted(counts):
        for sub in range(1, counts[kai] + 1):
            out.append(f'{pre}_{kai:02d}_{sub}_{topics[sub - 1]}.mp4')
    return out
_SF_30 = _build_30()
def _t_group_30():
    assert len(_SF_30) == 30, len(_SF_30)
    g = _sf.group_videos(_SF_30)
    assert len(g['lectures']) == 13, len(g['lectures'])
    assert g['by_kai_sorted'] == [1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14], g['by_kai_sorted']
    assert 8 not in g['by_kai_sorted'] and '8' not in g['matched']  # 第08回 欠番非補完
    assert len(g['flat']) == 30 and sum(len(v) for v in g['matched'].values()) == 30
check('group_videos 実30件 -> 13 lectures (回1-7,9-14)', _t_group_30)
def _t_manifest_roundtrip():
    import tempfile, json as _json
    g = _sf.group_videos(_SF_30)
    manifest = {  # manifestShape に準拠した最小マニフェスト（ネット不要）
        'status': 'OK', 'folder_url': 'https://x-my.sharepoint.com/f',
        'final_url': 'https://x-my.sharepoint.com/f', 'count': len(_SF_30),
        'files': _SF_30, 'groups': g, 'log': {}, 'captured_at': 'smoke',
    }
    # OneDrive 外の Temp へ UTF-8(ensure_ascii=False) で書き出し→再読込で count 一致
    p = os.path.join(tempfile.gettempdir(), 'sf_smoke_manifest.json')
    with open(p, 'w', encoding='utf-8') as f:
        _json.dump(manifest, f, ensure_ascii=False, indent=2)
    try:
        with open(p, encoding='utf-8') as f:
            back = _json.load(f)
        assert back['count'] == 30, back['count']
        assert len(back['groups']['lectures']) == 13
        assert back['files'][0] == _SF_30[0]  # 日本語ファイル名が文字化けせず往復
    finally:
        try:
            os.remove(p)
        except OSError:
            pass
check('build manifest UTF-8 Temp round-trip (count=30)', _t_manifest_roundtrip)

print('\n=== dedup / 適応追撮（crvピクセル差分の頭脳・ネット不要）===')
check('import dedup', lambda: importlib.import_module('dedup'))
import dedup as _dd
def _t_dedup_import_shape():
    for nm in ('frame_sig', 'frame_sig_from_bytes', 'pct_diff', 'dedup_dir'):
        assert hasattr(_dd, nm), nm
check('dedup 関数一式', _t_dedup_import_shape)

def _mk_frames(dirpath, spec):
    """spec=[(filename,(r,g,b))] で単色PNGを書き出す。PIL 前提。"""
    from PIL import Image
    for name, col in spec:
        Image.new('RGB', (240, 135), col).save(os.path.join(dirpath, name))

def _t_pct_diff():
    import tempfile
    d = tempfile.mkdtemp(prefix='sm_dd_')
    _mk_frames(d, [('a.png', (10, 10, 10)), ('b.png', (10, 12, 11)), ('c.png', (230, 20, 20))])
    a = _dd.frame_sig(os.path.join(d, 'a.png'))
    b = _dd.frame_sig(os.path.join(d, 'b.png'))
    c = _dd.frame_sig(os.path.join(d, 'c.png'))
    assert _dd.pct_diff(a, b) == 0.0, _dd.pct_diff(a, b)     # ほぼ同色 -> 0%
    assert _dd.pct_diff(a, c) == 100.0, _dd.pct_diff(a, c)   # 別板書 -> 100%
    import shutil; shutil.rmtree(d, ignore_errors=True)
check('pct_diff 同色0%/別色100%', _t_pct_diff)

def _t_dedup_dir_window():
    """A, A', B, B', A(往復で戻る) -> 残るのは A と B の2枚（A-B-A の往復も窓で吸収）。"""
    import tempfile, shutil
    d = tempfile.mkdtemp(prefix='sm_dd2_')
    _mk_frames(d, [('at00010s.png', (10, 10, 10)), ('at00020s.png', (12, 11, 10)),
                   ('at00030s.png', (230, 30, 30)), ('at00040s.png', (232, 28, 31)),
                   ('at00050s.png', (10, 10, 10))])
    res = _dd.dedup_dir(d, dry_run=True)
    kept = [os.path.basename(x) for x in res['kept']]
    assert res['pil'] and kept == ['at00010s.png', 'at00030s.png'], kept
    shutil.rmtree(d, ignore_errors=True)
check('dedup_dir A-B-A 往復吸収（2枚残す）', _t_dedup_dir_window)

def _t_adaptive_planner():
    """短命の板書B(100-130s)を固定10分割は取りこぼすが、適応追撮は捕捉する。"""
    import cdp_seek as _cs
    import numpy as _np
    def _state(t):
        return 0 if t < 100 else (1 if t < 130 else (2 if t < 600 else 3))
    col = [(10, 10, 10), (230, 20, 20), (20, 200, 20), (20, 20, 230)]
    def _sig(t):
        a = _np.zeros((16, 16, 3), dtype=_np.int16); a[:] = col[_state(t)]; return a
    times = _cs.plan_adaptive_captures(10, 1000.0, _sig, _dd.pct_diff,
                                       max_frames=30, diff_threshold=12.0, min_gap_s=25.0)
    states = {_state(t) for t in times}
    fixed10 = {_state(1000.0 * (i + 0.5) / 10) for i in range(10)}
    assert states == {0, 1, 2, 3}, f'適応で取りこぼし: {states}'
    assert 1 not in fixed10, '前提崩れ: 固定10分割がBを拾ってしまう'
    assert len(times) <= 30, len(times)
check('plan_adaptive_captures 短命板書を捕捉（固定分割は取りこぼす）', _t_adaptive_planner)

print('\n=== report_gen 実生成 ===')
from report_gen import (build_report, ReportConfig, Section, MathBlock, Problem,
                        check_config, load_ng_symbols)
import tempfile as _tf
import json as _js

def _manifest():
    """キャプチャ済みを模した manifest.json（Temp に置く）。"""
    p = os.path.join(_tf.gettempdir(), 'smoke_capture_manifest.json')
    with open(p, 'w', encoding='utf-8') as f:
        _js.dump({'captured_at': 'smoke', 'videos': [{'title': '01_1', 'n_frames': 10}]}, f)
    return p

def _full_cfg(**over):
    """標準構成を全部満たした設定（over で1項目ずつ壊して検査する）。"""
    kw = dict(
        subject='スモーク', subtitle='test',
        goals=['骨格の確認'],
        sections=[Section(heading='§1', paragraphs=['p'],
                          math=[MathBlock(inner_xml=m_det([[m_r('1')]]))])],
        common_pitfalls=['落とし穴'],
        problems=[Problem(question=f'q{i}', answer='a') for i in range(5)],
        summary_paragraphs=['まとめ'],
        capture_manifest=_manifest(),
    )
    kw.update(over)
    return ReportConfig(**kw)

def test_build():
    tmp = _tf.gettempdir()
    p = build_report(_full_cfg(), tmp, 'smoke_test')
    assert os.path.isfile(p) and os.path.getsize(p) > 1000, f'bad: {p}'
check('build_report', test_build)

def _t_full_no_warning():
    errors, warnings = check_config(_full_cfg())
    assert errors == [] and warnings == [], (errors, warnings)
check('check_config 標準構成どおりなら止めず警告も無し', _t_full_no_warning)

def _t_stop_missing():
    """つまずき・練習問題が欠けたら、Word を作る前に止まる。"""
    out_dir = _tf.mkdtemp(prefix='smoke_stop_')
    cfg = _full_cfg(common_pitfalls=[], problems=[Problem(question='q', answer='a')])
    try:
        build_report(cfg, out_dir, 'smoke_stop')
        raise AssertionError('欠けた構成で Word を作った')
    except ValueError as e:
        msg = str(e)
        assert 'つまずき' in msg and '練習問題が 1 問' in msg, msg
    assert os.listdir(out_dir) == [], os.listdir(out_dir)  # 途中まで作ったファイルも残さない
    os.rmdir(out_dir)
check('build_report 構成欠け（つまずき・練習1問）で止まる', _t_stop_missing)

def _t_problem_bounds():
    for n in (4, 7):
        errors, _ = check_config(_full_cfg(problems=[Problem(question='q', answer='a')] * n))
        assert any(f'練習問題が {n} 問' in e for e in errors), (n, errors)
    errors, _ = check_config(_full_cfg(problems=[Problem(question='q', answer='a')] * 6))
    assert errors == [], errors
    errors, _ = check_config(_full_cfg(problems=[Problem(question='q', answer='')] * 5))
    assert any('解答の無い' in e for e in errors), errors
    for key in ('goals', 'sections', 'summary_paragraphs'):
        errors, _ = check_config(_full_cfg(**{key: []}))
        assert errors, key
check('check_config 練習問題 5〜6問・解答必須・学習目標/節/まとめ必須', _t_problem_bounds)

def _t_manifest_warn():
    _, warnings = check_config(_full_cfg(capture_manifest=None))
    assert any('capture_manifest' in w and '動画を必ず見る' in w for w in warnings), warnings
    _, warnings = check_config(_full_cfg(capture_manifest=os.path.join(_tf.gettempdir(), 'no_such_manifest.json')))
    assert any('見つからない' in w for w in warnings), warnings
check('check_config manifest 無し・見つからないで警告（止めない）', _t_manifest_warn)

def _t_scope_symbols():
    syms, path = load_ng_symbols()
    if not syms:
        print('    (学習範囲.md が無いPCなので記号検査は SKIP)')
        return
    assert 'Σ' in syms and '∈' in syms and '∀' in syms, syms
    assert all(len(s) == 1 for s in syms), syms   # 「ベクトル記号」等の語は記号に数えない
    from omml_lib import m_sum, m_ri
    cfg = _full_cfg(sections=[Section(heading='§1', paragraphs=['x ∈ A とする'],
                                      math=[MathBlock(inner_xml=m_sum(m_r('i=1'), m_ri('n'), m_ri('i')))])])
    errors, warnings = check_config(cfg)
    assert errors == [], errors
    assert any('Σ' in w and '∈' in w for w in warnings), warnings   # OMML の ∑ も Σ として拾う
check('check_config 学習範囲外の記号（Σ・∈）を警告（止めない）', _t_scope_symbols)
try:
    os.remove(os.path.join(_tf.gettempdir(), 'smoke_capture_manifest.json'))
except OSError:
    pass

print('\n' + '=' * 40)
if failed:
    print(f'FAILED {len(failed)}: {failed}')
    sys.exit(1)
print('ALL PASSED')
