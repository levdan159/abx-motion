"""Power sheet 5 V bucks (2026-10-24, rev. TPS54360B): board +5V (U1) and the +5V_AUX 2 A external output (U901) are the
SAME TI TPS54360B design (one BOM; values in .claude/handoff/tps54360_report.md, SNVSB93 sect. 8.2.2):
  494 kHz (RT 196k), 5.00 V (0.8 V x (1 + 53.6k/10.2k)), L 10 uH Sunlord MWSA0603S-100MT, catch diode PDS5100-13 (100 V 5 A),
  Cout 2x 47 uF/10 V 1206, Cin 2x 4.7 uF/100 V 1206 + 100 nF/100 V, BOOT 100 nF, comp 9.1k + 10 nF // 68 pF,
  EN/UVLO 560k/33k: start 20.9 V / stop 19.0 V typ (logic is up long before the 30.7 V bus-breaker UVLO).
+5V_AUX: U901 -> U902 TPS25200 eFuse (RILIM 39k: 2.33 / 2.49 / 2.65 A min/typ/max, 5.4 V OUT clamp, FAULT -> PD11)
-> D901 SMAJ5.0A -> J511.  (Was: LMR36520 x2 + MIC2009, not sourceable / limit too low.)
The board-buck support parts that were hand drawn (C2-C4 Cin, C6 BOOT, R4/R5 FB, C7/C8 Cout, C9) stay hand drawn and are
re-valued here; the hand-drawn LMR36520 U1, its VCC cap C5 and L1 are removed (first run) and U1 + L1 + its new parts are
injected at the right of the sheet (labels U1_SW/U1_BOOT/U1_FB join the hand-drawn ones).
Injected into the hand-drawn Power.kicad_sch (paper A2). Re-runnable: the previous injection (every item whose uuid this
script generates) is removed first.  KiCad must be CLOSED.  python aux5v.py [out_path]"""
import subprocess as _sp; assert _sp.run(['pgrep', '-x', 'kicad'], capture_output=True).returncode, 'KiCad is running: close it (without saving) first'
import sys, os, re, json
sys.path.insert(0, os.path.dirname(__file__))
from schgen import Sheet, inject
import sx
P = os.path.expanduser('~/Documents/abx-motion')
ROOT, SPWR = 'f9149098-3f23-438d-bdc2-2e278b5ca35b', '383ff9ef-8565-4c62-b17f-0912fd19804f'
SRC = f'{P}/Power.kicad_sch'; OUT = sys.argv[1] if len(sys.argv) > 1 else SRC
R06, R08, C06, C12 = 'Resistor_SMD:R_0603_1608Metric', 'Resistor_SMD:R_0805_2012Metric', 'Capacitor_SMD:C_0603_1608Metric', 'Capacitor_SMD:C_1206_3216Metric'
UFP, LFP, DFP = 'Package_SO:TI_SO-PowerPAD-8_ThermalVias', 'Inductor_SMD:L_Sunlord_MWSA0603S', 'Diode_SMD:D_PowerDI-5'   # PowerDI-5 pad 1 (tab) = K
V = dict(u='TPS54360BDDAR', l='10uH MWSA0603S-100MT', d='PDS5100-13', rt='196k', rc='9.1k', cz='10nF', chf='68pF C0G', uv1='560k', uv2='33k',
         fb1='53.6k', fb2='10.2k', cout='47uF/10V', cin='4.7uF/100V', cbyp='100nF/100V', boot='100nF')

# ---- abx symbol: TPS25200DRV (TI eFuse, WSON-6 DRV; pin table SLVSCJ0F) ----
src = open(os.path.join(os.path.dirname(__file__), 'symgen.py')).read()
ns = {}; exec(src[:src.index('\nS = []')], ns)
blk = ns['sym']('TPS25200DRV', 'TI TPS25200 5V eFuse 2.5-6.5V (20V abs), 60mOhm, adjustable current limit 85mA-2.9A (RILIM 33k-1100k), 5.4V OUT clamp, 7.6V OVLO, open-drain FAULT, WSON-6 DRV',
                'Package_SON:WSON-6-1EP_2x2mm_P0.65mm_EP1x1.6mm_ThermalVias', 'https://www.ti.com/lit/ds/symlink/tps25200.pdf', 'eFuse power switch current limit overvoltage',
                [('6', 'IN', 'power_in'), ('4', 'EN', 'input'), ('2', 'ILIM', 'passive'), ('5', 'GND', 'power_in'), ('7', 'PAD', 'passive')],
                [('1', 'OUT', 'power_out'), None, ('3', 'FAULT', 'open_collector')], w=7.62)
lib = open(f'{P}/abx-symbols.kicad_sym').read()
if '(symbol "TPS25200DRV"' not in lib:
    i = lib.rstrip().rfind(')'); open(f'{P}/abx-symbols.kicad_sym', 'w').write(lib[:i] + blk + lib[i:])

k = Sheet(paper='A2', globals_=('GND', '+BATT', '+3V3', '+5V', '+5V_AUX', 'AUX5_FLT_N'))
r = lambda ref, val, x, y, n1, n2, fp=R06: k.add(ref, 'Device:R', val, fp, x, y, {'1': n1, '2': n2})
c = lambda ref, val, x, y, n1, n2, fp=C06: k.add(ref, 'Device:C', val, fp, x, y, {'1': n1, '2': n2})

def ctl(s, u, l, d, rt, rc, cz, chf, ruv, x, y, out):
    """TPS54360B + its RT / EN divider / compensation / inductor / catch diode. Nets <s>_SW/_BOOT/_FB/_EN/_RT/_COMP/_CZ."""
    k.add(u, 'Regulator_Switching:TPS54360DDA', V['u'], UFP, x, y,
          {'1': f'{s}_BOOT', '2': '+BATT', '3': f'{s}_EN', '4': f'{s}_RT', '5': f'{s}_FB', '6': f'{s}_COMP', '7': 'GND', '8': f'{s}_SW', '9': 'GND'})
    r(ruv[0], V['uv1'], x - 40, y - 5, '+BATT', f'{s}_EN', R08); r(ruv[1], V['uv2'], x - 28, y - 5, f'{s}_EN', 'GND')
    r(rt, V['rt'], x - 16, y + 25, f'{s}_RT', 'GND')
    r(rc, V['rc'], x + 25, y + 25, f'{s}_COMP', f'{s}_CZ'); c(cz, V['cz'], x + 37, y + 25, f'{s}_CZ', 'GND'); c(chf, V['chf'], x + 49, y + 25, f'{s}_COMP', 'GND')
    k.add(l, 'Device:L', V['l'], LFP, x + 40, y - 15, {'1': f'{s}_SW', '2': out})
    k.add(d, 'Device:D_Schottky', V['d'], DFP, x + 40, y + 5, {'1': f'{s}_SW', '2': 'GND'})

# ---------------- board +5V: U1 (support caps / FB divider are the hand-drawn C2-C4, C6, R4/R5, C7-C9) ----------------
XU, YU = 390, 85
k.text('BOARD +5V BUCK U1 = TPS54360B (replaces LMR36520, 2026-10-24)', XU - 15, YU - 50, 2.5, True)
for n, s_ in enumerate(('Same design as U901 below: 494 kHz (R10 196k), 5.00 V = 0.8 V x (1 + R4 53.6k / R5 10.2k).',
                        'L1 10 uH, D3 PDS5100-13, comp R11 9.1k + C11 10 nF // C12 68 pF; Cin C2/C3 + C4, BOOT C6, Cout C7/C8 47 uF/10 V.',
                        'EN/UVLO R12 560k / R13 33k: start 20.9 V / stop 19.0 V typ (tolerance 18.8-23.0 V / 16.2-21.8 V):',
                        '+5V/+3V3 are up before the 30.7 V bus-breaker UVLO and stay up below its 26.8 V UV gate.',
                        'Loads: AP2112 U2/U705, J304/J404/J703, CAN U704, LM339 U802, LEDs: < 1.5 A worst case (IC 3.5 A).')):
    k.text(s_, XU - 15, YU - 44 + 4.5 * n, 1.6)
ctl('U1', 'U1', 'L1', 'D3', 'R10', 'R11', 'C11', 'C12', ('R12', 'R13'), XU + 60, YU + 20, '+5V')
k.text('U1 TPS54360B: see the block at the right (x 375-500).', 240, 66, 2.0, True)

# ---------------- +5V_AUX: U901 (complete) -> U902 TPS25200 -> J511 ----------------
X, Y = 40, 320
k.text('+5V_AUX EXTERNAL OUTPUT (2 A): own buck U901 = same TPS54360B design as U1 (5.00 V, 494 kHz, 10 uH), fed from +BATT (before the bus breaker)', X - 15, Y - 25, 2.5, True)
k.text('U901 is rated 3.5 A (4.5 A min switch limit): 2 A continuous has margin. IC ~0.55 W, D902 ~1.3 W at 42 V in / 2 A out (give D902 copper).', X - 15, Y - 19, 1.6)
k.text('U902 TPS25200 eFuse (EN tied on): RILIM R905 39k -> 2.33 A min / 2.49 A typ / 2.65 A max (SLVSCJ0F eq. 1), 2.6 A continuous rating, 5.4 V OUT clamp. FAULT -> AUX5_FLT_N (R906 10k to +3V3) -> STM32 PD11. D901 SMAJ5.0A clamps outside transients at J511.', X - 15, Y - 14, 1.6)
ctl('U901', 'U901', 'L901', 'D902', 'R903', 'R904', 'C904', 'C911', ('R907', 'R908'), X + 60, Y + 20, '5V_AUX_BUCK')
c('C901', V['cin'], X, Y + 50, '+BATT', 'GND', C12); c('C902', V['cin'], X + 12, Y + 50, '+BATT', 'GND', C12); c('C903', V['cbyp'], X + 24, Y + 50, '+BATT', 'GND')
c('C905', V['boot'], X + 95, Y - 5, 'U901_BOOT', 'U901_SW')
r('R901', V['fb1'], X + 125, Y + 40, '5V_AUX_BUCK', 'U901_FB'); r('R902', V['fb2'], X + 137, Y + 40, 'U901_FB', 'GND')
c('C906', V['cout'], X + 125, Y + 5, '5V_AUX_BUCK', 'GND', C12); c('C907', V['cout'], X + 137, Y + 5, '5V_AUX_BUCK', 'GND', C12); c('C908', '1uF', X + 149, Y + 5, '5V_AUX_BUCK', 'GND')
k.add('#FLG901', 'power:PWR_FLAG', 'PWR_FLAG', '', X + 160, Y + 40, {'1': '5V_AUX_BUCK'})
k.add('U902', 'abx:TPS25200DRV', 'TPS25200DRVR', 'Package_SON:WSON-6-1EP_2x2mm_P0.65mm_EP1x1.6mm_ThermalVias', X + 190, Y + 20,
      {'IN': '5V_AUX_BUCK', 'EN': '5V_AUX_BUCK', 'ILIM': 'U902_ILIM', 'GND': 'GND', 'PAD': 'GND', 'OUT': '+5V_AUX', 'FAULT': 'AUX5_FLT_N'})
c('C909', '1uF', X + 165, Y + 5, '5V_AUX_BUCK', 'GND')
r('R905', '39k', X + 175, Y + 45, 'U902_ILIM', 'GND'); r('R906', '10k', X + 205, Y + 45, '+3V3', 'AUX5_FLT_N')
c('C910', '10uF', X + 220, Y + 5, '+5V_AUX', 'GND', 'Capacitor_SMD:C_0805_2012Metric')
k.add('D901', 'Device:D_TVS', 'SMAJ5.0A', 'Diode_SMD:D_SMA', X + 232, Y + 30, {'1': '+5V_AUX', '2': 'GND'})   # pin 1 = pad 1 = cathode
k.add('J511', 'Connector:Conn_01x02_Pin', '5V_AUX', 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal', X + 250, Y + 20, {'1': '+5V_AUX', '2': 'GND'})
k.check()
rend = k.render([(f'/{ROOT}/{SPWR}', 0)])

# hand-drawn LMR36520 U1 items (uuids of the original drawing; gone after the first run): U1 + pin stubs + its labels and
# power symbols + no-connect; VCC cap C5 + stubs + U1_VCC label + #PWR025; L1 + stubs + U1_SW label + #PWR026
OLD = {'0a5bfd9d-d4a5-524c-a5b2-edfe27913b6a', '211a1fa3-9127-59a9-961e-51162c2a43d1', '49993e9b-0b62-5c72-94cf-7fde3efe719a',
       'd0dde36d-cd6e-5332-9daf-7854e22566d4', '0384d1be-b0d9-536b-bca2-7d4f842404ef', 'f679d7e6-d88e-54bd-9913-4d8c8756f897',
       'f8da9b01-ad62-59d4-9ee8-99f6a7564836', '9a079dbc-ccd3-519f-889a-52ee3943307d', '1e2fb1bb-2c85-5101-90a8-1e8de165b4f8',
       '9b7bbbe0-2561-5481-a960-7a6652b2702e', 'b67c5dcd-5c75-58c7-a6aa-44bfc60643f3', '49d6aa8f-b307-5e19-94d7-64962d1d9592',
       'e498fdfd-b6d1-5545-a1f8-1419cd74f86c', 'f3721f23-a5c0-5185-a8b5-6201f69be169', 'fe1e612b-f4a4-54a1-88f8-0b6bc956e149',
       '29151c7d-23d3-5fc4-b455-1d5e7fd05c52',
       'b7dd48bd-87c4-5063-83de-70ccb0e6af73', '18635a6b-3026-5e09-9651-d1d468ef70a0', 'b41f2879-cecd-5d23-82ea-361a9e19224f',
       'e2712bba-3a69-5c69-8d84-6a54e19c45cf', '8dd1a5aa-a26d-505e-be7c-1f5400245957',
       '5c79c6dd-ffcb-51c2-942e-db5a2d041b53', 'cc8d49c6-0f83-50ae-be37-34f7124cde98', '4acebb0a-5caa-5d32-9997-5820787dc389',
       '64ca323b-2995-5ed8-a76a-6b9f4d6e668f', '0b3ec130-ab93-5e65-84ce-e5be1b180973'}
t = open(SRC).read()
mine = set(re.findall(r'\(uuid "([^"]+)"\)', rend)) | OLD
if '(lib_id "abx:MIC2009YM6")' in t:   # one-time migration: the LMR36520/MIC2009 injection (2026-10-24) = every item not in the pre-injection sheet
    ref_ = open(f'{P}/.claude/handoff/bak/pre_additions/Power.kicad_sch').read()
    keep = {m.group(1) for s, e, h in sx.spans(ref_, 1) if (m := re.search(r'\(uuid "([^"]+)"\)', ref_[s:e]))}
    mine |= {m.group(1) for s, e, h in sx.spans(t, 1) if h != 'lib_symbols' and (m := re.search(r'\(uuid "([^"]+)"\)', t[s:e])) and m.group(1) not in keep}
for s, e, h in sorted(sx.spans(t, 1), reverse=True):     # drop a previous injection + the old hand-drawn U1/C5/L1 items
    if h in ('symbol', 'label', 'global_label', 'no_connect', 'text', 'wire', 'junction') and (m := re.search(r'\(uuid "([^"]+)"\)', t[s:e])) and m.group(1) in mine:
        j = s
        while t[j - 1] in ' \t': j -= 1
        t = t[:j - 1] + t[e:] if t[j - 1] == '\n' else t[:j] + t[e:]
assert '(lib_id "Regulator_Switching:LMR33630ADDA")' not in t, 'an LMR36520 symbol is left on the Power sheet'
ls_ = [x for x in sx.spans(t, 1) if x[2] == 'lib_symbols'][0]          # drop cached lib symbols no instance uses any more
for s, e, h in sorted(sx.spans(t[ls_[0]:ls_[1]], 1), reverse=True):
    s, e = s + ls_[0], e + ls_[0]
    nm = re.match(r'\(symbol "([^"]+)"', t[s:e])
    if nm and f'(lib_id "{nm.group(1)}")' not in t:
        j = s
        while t[j - 1] in ' \t': j -= 1
        t = t[:j - 1] + t[e:] if t[j - 1] == '\n' else t[:j] + t[e:]

def setval(t, ref, val):
    """re-value one hand-drawn symbol (Value property)."""
    for s, e, h in sx.spans(t, 1):
        if h == 'symbol' and sx.prop(t[s:e], 'Reference') == ref:
            b = re.sub(r'(\(property "Value" ")((?:[^"\\]|\\.)*)(")', lambda m: m.group(1) + val + m.group(3), t[s:e], count=1)
            return t[:s] + b + t[e:]
    raise KeyError(ref)
for ref, val in (('R4', V['fb1']), ('R5', V['fb2']), ('C7', V['cout']), ('C8', V['cout']), ('C2', V['cin']), ('C3', V['cin']), ('C4', V['cbyp']), ('C6', V['boot'])):
    t = setval(t, ref, val)
t = t.replace('(paper "A3")', '(paper "A2")', 1)
t = inject(t, rend)
open(OUT, 'w').write(t)
print('5 V bucks (U1 controller + U901 block):', len(k.parts), 'parts ->', OUT)

# ---- net classes: buck switch nodes + 5 V AUX rails on Power_LV ----
if OUT == SRC:
    pr = json.load(open(f'{P}/abx-motion-brushless.kicad_pro')); pats = pr['net_settings']['netclass_patterns']
    for pat in ('+5V_AUX', '/Power_Supply/5V_AUX_BUCK', '/Power_Supply/U901_SW', '/Power_Supply/U1_SW'):
        if not any(x['pattern'] == pat for x in pats): pats.append({'netclass': 'Power_LV', 'pattern': pat})
    json.dump(pr, open(f'{P}/abx-motion-brushless.kicad_pro', 'w'), indent=2)
