"""+5V_AUX external output (2026-10-24): second LMR36520 5 V buck (copy of Power U1: same parts and values) from +BATT,
MIC2009YM6 eFuse (2.0 A typ limit, FAULT -> STM32 PD11), SMAJ5.0A TVS, J511 2-pole screw terminal.
Injected into the hand-drawn Power.kicad_sch (paper A3 -> A2, block below the existing drawing). Re-runnable: the previous
injection (every item whose uuid this script generates) is removed first.  KiCad must be CLOSED.  python aux5v.py [out_path]"""
import subprocess as _sp; assert _sp.run(['pgrep', '-x', 'kicad'], capture_output=True).returncode, 'KiCad is running: close it (without saving) first'
import sys, os, re
sys.path.insert(0, os.path.dirname(__file__))
from schgen import Sheet, inject
import sx
P = os.path.expanduser('~/Documents/abx-motion')
ROOT, SPWR = 'f9149098-3f23-438d-bdc2-2e278b5ca35b', '383ff9ef-8565-4c62-b17f-0912fd19804f'
SRC = f'{P}/Power.kicad_sch'; OUT = sys.argv[1] if len(sys.argv) > 1 else SRC
R06, C06, C12 = 'Resistor_SMD:R_0603_1608Metric', 'Capacitor_SMD:C_0603_1608Metric', 'Capacitor_SMD:C_1206_3216Metric'

k = Sheet(paper='A2', globals_=('GND', '+BATT', '+3V3', '+5V_AUX', 'AUX5_FLT_N'))
r = lambda ref, val, x, y, n1, n2, fp=R06: k.add(ref, 'Device:R', val, fp, x, y, {'1': n1, '2': n2})
c = lambda ref, val, x, y, n1, n2, fp=C06: k.add(ref, 'Device:C', val, fp, x, y, {'1': n1, '2': n2})
X, Y = 40, 320
k.text('+5V_AUX EXTERNAL OUTPUT (2 A): own buck U901 = copy of U1 (LMR36520, 1.0 V x (1 + 100k/24.9k) = 5.02 V, same L/C), fed from +BATT (before the bus breaker)', X - 15, Y - 25, 2.5, True)
k.text('U901 runs at its 2 A rating (no margin): the MIC2009 limit (R905 124 R: 2.0 A typ, 1.69-2.31 A) keeps it there; the LMR36520 cycle-by-cycle limit + hiccup protect it above that. More current = a different buck (see additions_report.md).', X - 15, Y - 19, 1.6)
k.text('U902 MIC2009YM6 (active-high EN, tied on): constant-current limit, thermal shutdown, FAULT/ -> AUX5_FLT_N (R906 10k to +3V3) -> STM32 PD11. D901 SMAJ5.0A clamps outside transients at J511.', X - 15, Y - 14, 1.6)
k.add('U901', 'Regulator_Switching:LMR33630ADDA', 'LMR36520FADDA', 'Package_SO:Texas_HSOP-8-1EP_3.9x4.9mm_P1.27mm_ThermalVias', X + 60, Y + 20,
      {'1': 'GND', '9': 'GND', '2': '+BATT', '3': '+BATT', '5': 'U901_FB', '6': 'U901_VCC', '7': 'U901_BOOT', '8': 'U901_SW'}, nc=['4'])
c('C901', '4.7uF/100V', X, Y + 50, '+BATT', 'GND', C12); c('C902', '4.7uF/100V', X + 12, Y + 50, '+BATT', 'GND', C12); c('C903', '100nF/100V', X + 24, Y + 50, '+BATT', 'GND')
c('C904', '1uF', X + 36, Y + 50, 'U901_VCC', 'GND'); c('C905', '100nF', X + 95, Y + 5, 'U901_BOOT', 'U901_SW')
k.add('L901', 'Device:L', '15uH', 'Inductor_SMD:L_Bourns_SRP7028A_7.3x6.6mm', X + 110, Y + 20, {'1': 'U901_SW', '2': '5V_AUX_BUCK'})
r('R901', '100k', X + 125, Y + 40, '5V_AUX_BUCK', 'U901_FB'); r('R902', '24.9k', X + 137, Y + 40, 'U901_FB', 'GND')
c('C906', '22uF', X + 125, Y + 5, '5V_AUX_BUCK', 'GND', C12); c('C907', '22uF', X + 137, Y + 5, '5V_AUX_BUCK', 'GND', C12); c('C908', '1uF', X + 149, Y + 5, '5V_AUX_BUCK', 'GND')
k.add('#FLG901', 'power:PWR_FLAG', 'PWR_FLAG', '', X + 160, Y + 40, {'1': '5V_AUX_BUCK'})
k.add('U902', 'abx:MIC2009YM6', 'MIC2009YM6', 'Package_TO_SOT_SMD:SOT-23-6', X + 190, Y + 20,
      {'VIN': '5V_AUX_BUCK', 'EN': '5V_AUX_BUCK', 'ILIMIT': 'U902_ILIM', 'GND': 'GND', 'VOUT': '+5V_AUX', 'FAULT': 'AUX5_FLT_N'})
c('C909', '1uF', X + 165, Y + 5, '5V_AUX_BUCK', 'GND')
r('R905', '124', X + 175, Y + 45, 'U902_ILIM', 'GND'); r('R906', '10k', X + 205, Y + 45, '+3V3', 'AUX5_FLT_N')
c('C910', '10uF', X + 220, Y + 5, '+5V_AUX', 'GND', 'Capacitor_SMD:C_0805_2012Metric')
k.add('D901', 'Device:D_TVS', 'SMAJ5.0A', 'Diode_SMD:D_SMA', X + 232, Y + 30, {'1': '+5V_AUX', '2': 'GND'})   # pin 1 = pad 1 = cathode
k.add('J511', 'Connector:Conn_01x02_Pin', '5V_AUX', 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal', X + 250, Y + 20, {'1': '+5V_AUX', '2': 'GND'})
k.check()
rend = k.render([(f'/{ROOT}/{SPWR}', 0)])

t = open(SRC).read()
mine = set(re.findall(r'\(uuid "([^"]+)"\)', rend))
for s, e, h in sorted(sx.spans(t, 1), reverse=True):     # drop a previous injection
    if h in ('symbol', 'label', 'global_label', 'no_connect', 'text') and (m := re.search(r'\(uuid "([^"]+)"\)', t[s:e])) and m.group(1) in mine:
        j = s
        while t[j - 1] in ' \t': j -= 1
        t = t[:j - 1] + t[e:] if t[j - 1] == '\n' else t[:j] + t[e:]
t = t.replace('(paper "A3")', '(paper "A2")', 1)
t = inject(t, rend)
open(OUT, 'w').write(t)
print('+5V_AUX block:', len(k.parts), 'parts ->', OUT)
