# スキルの回帰テスト: 例が1枚のPDFになること、配線を間違えると自動検査が止まること
import copy
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import breadboard_lib as bb
import example_led3 as led
import example_adc as adc


def must_fail(fn, label):
    try:
        fn()
    except AssertionError as e:
        print(f'  OK  {label} → 検査が止めた')
        return
    raise SystemExit(f'NG  {label} → 間違った配線を検査が通してしまった')


tmp = tempfile.mkdtemp(prefix='bbtest_', dir=os.environ.get('TEMP'))
print('1) 例を実際に出力して、1ページか確かめる')
for mod, name in ((led, 'example_led3'), (adc, 'example_adc')):
    pdf, pages = mod.build(tmp, name)
    assert pages == 1, f'{name} が {pages} ページになった'
    print(f'  OK  {name}: {os.path.getsize(pdf)} bytes, {pages} ページ')

print('2) 配線をわざと間違えて、自動検査が止めるか')
w, t, e = led.make_model()
a, b = w[0]['b'], w[1]['b']
w[0]['b'], w[1]['b'] = b, a                                   # GPIO25 と GPIO24 の行き先を入れ替え
must_fail(lambda: bb.check_partition(w, t, e), 'LED: 2本の行き先を入れ替え')
w, t, e = led.make_model()
del w[5]                                                      # GND の線を1本忘れる
must_fail(lambda: bb.check_partition(w, t, e), 'LED: GND の線を1本忘れる')
w, t, e, _ = adc.make_model()
for x in w:
    if x['key'] == 'MOSI':
        x['b'] = ('a', adc.HOLES[12][1])                      # MOSI を DOUT（12番）へ
must_fail(lambda: bb.check_partition(w, t, e), 'ADC: MOSI を DOUT につなぐ')
w, t, e, _ = adc.make_model()
for x in w:
    if x['key'] == 'VREF':
        x['b'] = ('a', adc.HOLES[14][1])                      # 3.3 V を AGND につなぐ（ショート）
must_fail(lambda: bb.check_partition(w, t, e), 'ADC: 3.3 V と GND をショート')

print('3) 作図の補助が働くか')
w, t, e, n = adc.make_model()
assert not bb.dot_on_wire(w), '最適化後の配線で穴の上を線が通っている'
bad = copy.deepcopy(w)
bad[0]['via'] = [bb.hx(*bad[1]['b'])]                         # 別の配線の端の穴の上を通す
assert bb.dot_on_wire(bad), 'dot_on_wire が穴の上の通過を見逃した'
print(f'  OK  交差 {n} か所、穴の上を通る線は 0、わざと通した場合は検出')
print('全部 OK')
