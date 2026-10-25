"""Bus_Breaker.kicad_sch generator (TPS48111-Q1 U801) + hardware-autonomous enable/precharge sequencer (2026-10-24).
Replaces the Bus_Breaker section of fuses.py (fuses.py is not idempotent; its breaker block is now stale).
The TPS48111 has NO built-in precharge->main sequencing: INP (main FETs) and INP_G (precharge driver G) are independent
CMOS inputs and TMR is only the overcurrent fault timer (SLUSEE5E sect. 8.3.2.2, 8.3.3). The sequence is made by U802
(LM339 quad open-collector comparator on +5V) from the always-on logic rails (+5V/+3V3 come from +BATT, before the breaker).
Also adds the abx:LM339DR symbol (single unit) to abx-symbols.  KiCad must be CLOSED.  python breaker.py [out_path]"""
import subprocess as _sp; assert _sp.run(['pgrep', '-x', 'kicad'], capture_output=True).returncode, 'KiCad is running: close it (without saving) first'
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from schgen import Sheet, uid, existing_uuids
P = os.path.expanduser('~/Documents/abx-motion')
ROOT = 'f9149098-3f23-438d-bdc2-2e278b5ca35b'
SB = uid('block', 'Bus_Breaker')
OUT = sys.argv[1] if len(sys.argv) > 1 else f'{P}/Bus_Breaker.kicad_sch'
R06, R08, R12 = 'Resistor_SMD:R_0603_1608Metric', 'Resistor_SMD:R_0805_2012Metric', 'Resistor_SMD:R_2512_6332Metric'
C06, C08 = 'Capacitor_SMD:C_0603_1608Metric', 'Capacitor_SMD:C_0805_2012Metric'

# ---- abx symbol: LM339DR as ONE unit (schgen places unit 1 only) ----
src = open(os.path.join(os.path.dirname(__file__), 'symgen.py')).read()
ns = {}; exec(src[:src.index('\nS = []')], ns)
blk = ns['sym']('LM339DR', 'Quad open-collector comparator, 2-36 V, SOIC-14 (single-unit symbol, LM339 pinout)',
                'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm', 'https://www.ti.com/lit/ds/symlink/lm339.pdf', 'comparator quad open collector',
                [('3', 'VCC', 'power_in'), None, ('5', 'IN1+', 'input'), ('4', 'IN1-', 'input'), ('7', 'IN2+', 'input'), ('6', 'IN2-', 'input'),
                 ('9', 'IN3+', 'input'), ('8', 'IN3-', 'input'), ('11', 'IN4+', 'input'), ('10', 'IN4-', 'input'), None, ('12', 'GND', 'power_in')],
                [('2', 'OUT1', 'open_collector'), None, ('1', 'OUT2', 'open_collector'), None, ('14', 'OUT3', 'open_collector'), None, ('13', 'OUT4', 'open_collector')])
lib = open(f'{P}/abx-symbols.kicad_sym').read()
if '(symbol "LM339DR"' not in lib:
    i = lib.rstrip().rfind(')'); open(f'{P}/abx-symbols.kicad_sym', 'w').write(lib[:i] + blk + lib[i:])

def rr(sh): return lambda ref, val, x, y, n1, n2, fp=R06: sh.add(ref, 'Device:R', val, fp, x, y, {'1': n1, '2': n2})
def cc(sh): return lambda ref, val, x, y, n1, n2, fp=C06: sh.add(ref, 'Device:C', val, fp, x, y, {'1': n1, '2': n2})
b = Sheet(paper='A3', globals_=('GND', 'VBUS', 'VBAT_IN', '+3V3', '+5V', 'BUS_FLT_N', 'BUS_IMON')); r, c = rr(b), cc(b)
if os.path.exists(OUT): b.uuids = existing_uuids(OUT)
b.text('MAIN BUS BREAKER - TPS48111-Q1 smart high-side driver between the battery (VBAT_IN, J1) and the motor bus (VBUS)', 20, 20, 3, True)
b.text('Back-to-back Q801/Q802 (common source): bidirectional when on (regen reaches the battery), blocks both ways when off. Logic supply (F1) taps VBAT_IN before the breaker, so the STM32 and brakes stay powered when the bus trips.', 20, 28, 1.6)
b.text('Protection (TPS4811 SLUSEE5E eq. 6/7/9/11/13): RSNS 0.5 mOhm, RSET 100 R. IOC = 80 A (R815 30.1k, blank tOC = 5 ms with C804 330 nF, auto-retry ~7.5 s). ISC = 150 A (R816 4.32k, trips in 1.2 us). IMON gain 61.2 (R813 6.8k): 30.6 mV/A -> 1.84 V at 60 A.', 20, 33, 1.6)
b.text('UVLO (EN/UVLO 1.18 V rising / 1.11 V falling): R806 300k / R807 12k = /26: ON at 30.7 V (3.07 V/cell), OFF at 28.9 V (2.89 V/cell). Faults FLT_I/FLT_T open drain -> BUS_FLT_N -> STM32 PD8; BUS_IMON -> 74HC4051 U706 ch5 (ESC_MCU).', 20, 38, 1.6)
b.text('NOTE: VS/CS+/ISCP are rated -1 V: a reversed battery still damages U801, but Q801/Q802 keep reverse voltage off the ESC side. Keep the external 80 A fuse.', 20, 43, 1.6)
u = {'VS': 'VBAT_IN', 'CS+': 'BUS_CSP', 'CS-': 'BUS_SNS', 'ISCP': 'BUS_ISCP', 'EN/UVLO': 'BUS_UVLO', 'INP': 'BUS_INP', 'INP_G': 'BUS_INPG',
     'IWRN': 'BUS_IWRN', 'TMR': 'BUS_TMR', 'DIODE': 'GND', 'GND': 'GND', 'BST': 'BUS_BST', 'PU': 'BUS_PU', 'PD': 'BUS_GATE', 'SRC': 'BUS_SRC',
     'G': 'PRE_GD', 'FLT_I': 'BUS_FLT_I', 'FLT_T': 'BUS_FLT_T', 'IMON': 'BUS_IMON_R'}
b.add('U801', 'abx:TPS48111QDGXRQ1', 'TPS48111QDGXRQ1', 'abx-footprints:TI_DGX0019A_VSSOP-19_3x5.1mm_P0.5mm', 150, 130, u)
r('R801', '0.5m 3W', 60, 80, 'VBAT_IN', 'BUS_SNS', R12)
r('R817', '100', 80, 100, 'VBAT_IN', 'BUS_CSP'); r('R816', '4.32k', 95, 100, 'VBAT_IN', 'BUS_ISCP'); c('C805', '1nF', 110, 100, 'BUS_ISCP', 'BUS_SNS')
c('C806', '100nF/100V', 125, 100, 'VBAT_IN', 'GND')
TOLL = 'Package_TO_SOT_SMD:Infineon_PG-HSOF-8-1_ThermalVias'
b.add('Q801', 'Device:Q_NMOS_GSD', 'IPT015N10N5', TOLL, 230, 80, {'1': 'BUS_GATE', '3': 'BUS_SNS', '2': 'BUS_SRC'})
b.add('Q802', 'Device:Q_NMOS_GSD', 'IPT015N10N5', TOLL, 270, 80, {'1': 'BUS_GATE', '3': 'VBUS', '2': 'BUS_SRC'})
b.add('#FLG801', 'power:PWR_FLAG', 'PWR_FLAG', '', 300, 80, {'1': 'VBUS'})
r('R802', '10', 210, 110, 'BUS_PU', 'BUS_GATE'); c('C801', '470nF/25V', 225, 110, 'BUS_BST', 'BUS_SRC')
b.add('Q803', 'Transistor_FET:CSD19532Q5B', 'CSD19532Q5B', 'Package_TO_SOT_SMD:TDSON-8-1', 250, 150, {'1': 'BUS_SRC', '2': 'BUS_SRC', '3': 'BUS_SRC', '4': 'PRE_G', '5': 'PRE_D'})
r('R805', '330', 225, 150, 'PRE_GD', 'PRE_G'); r('R803', '10 2512 anti-surge', 270, 130, 'BUS_SNS', 'PRE_M', R12); r('R804', '10 2512 anti-surge', 285, 130, 'PRE_M', 'PRE_D', R12)
r('R806', '300k', 80, 140, 'VBAT_IN', 'BUS_UVLO'); r('R807', '12k', 80, 160, 'BUS_UVLO', 'GND'); c('C802', '100nF', 95, 162, 'BUS_UVLO', 'GND')   # was 470k / 20.5k (28 V); same pads, so the routed copper stays
r('R808', '1k', 105, 175, 'BUS_EN', 'BUS_INP'); r('R809', '1k', 120, 175, 'PRECHG_EN', 'BUS_INPG')
r('R815', '30.1k', 135, 190, 'BUS_IWRN', 'GND'); c('C804', '330nF', 150, 190, 'BUS_TMR', 'GND')
r('R810', '1k', 200, 175, 'BUS_FLT_I', 'BUS_FLT_N'); r('R811', '1k', 215, 175, 'BUS_FLT_T', 'BUS_FLT_N'); r('R812', '10k', 230, 175, '+3V3', 'BUS_FLT_N')
r('R813', '6.8k', 200, 200, 'BUS_IMON_R', 'GND'); r('R814', '1k', 215, 200, 'BUS_IMON_R', 'BUS_IMON'); c('C803', '10nF', 230, 200, 'BUS_IMON', 'GND')

# ======================= autonomous sequencer (no MCU) =======================
b.text('AUTONOMOUS ENABLE + PRECHARGE (no MCU). U802 LM339 on +5V, open-collector outputs pulled up to +3V3. Inputs stay inside the 0..3.5 V common-mode range up to VBUS = 60 V.', 20, 214, 2, True)
b.text('A (OUT1) BUS_GOOD_N: low when VBUS > 92 % of VBAT_IN (R819/R820 vs R821/R822). Q804 inverts it: BUS_EN (INP, main FETs) is high only while the bus is good. Sticky: R823 from BUS_EN lifts VBUS_DIV, so A releases only below ~40-53 % (VBUS 12 V at 30 V, 22 V at 42 V).', 20, 220, 1.5)
b.text('PRECHG_EN (INP_G, precharge FET Q803) = high while the bus is NOT good, pulled low via D801 when it is good, or by B (OUT2) after the timeout.', 20, 224.5, 1.5)
b.text('Timeout PRE_TMR: R827 220k / C809 2.2 uF from +3V3 to SEQ_REF 1.03 V (R828 22k / R829 10k): 0.18 s = R C ln(3.3 / 2.27). Reset (held low) while the bus is good (D801) or while VBAT_IN < 26.8 V (C, OUT3: BUS_UVLO < SEQ_REF, below the TPS falling threshold).', 20, 229, 1.5)
b.text('Sequence: +3V3 up, VBAT >= 30.7 V -> INP_G high (precharge through R803/R804 20 R, tau ~20 ms with ~1 mF) -> VBUS reaches 92 % (~60 ms incl. BST charge) -> INP high (main on), INP_G low.', 20, 233.5, 1.5)
b.text('Faults: OC/SC trip -> VBUS collapses below the sticky threshold -> INP low (resets the TPS fault counter), precharge retried once for 0.18 s; a short keeps VBUS low -> timeout -> precharge stays off (latched) until the pack is reconnected. VBAT sag < UVLO: TPS off; recovers by itself if VBAT returns >= 30.7 V.', 20, 238, 1.5)
b.text('CHECK: R803/R804 must take one 0.18 s pulse into a shorted bus (42 V / 20 R = 2.1 A, 88 W total, ~16 J). Unused comparator D: IN4+ = GND, IN4- = SEQ_REF, OUT4 open.', 20, 242.5, 1.5)
SQ = 252
b.add('U802', 'abx:LM339DR', 'LM339DR', 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm', 175, SQ + 14,
      {'3': '+5V', '12': 'GND', '5': 'VBAT_REF', '4': 'VBUS_DIV', '2': 'BUS_GOOD_N', '7': 'SEQ_REF', '6': 'PRE_TMR', '1': 'PRECHG_EN',
       '9': 'BUS_UVLO', '8': 'SEQ_REF', '14': 'PRE_TMR', '11': 'GND', '10': 'SEQ_REF'}, nc=['13'])
c('C811', '100nF', 205, SQ + 5, '+5V', 'GND')
r('R819', '220k', 30, SQ, 'VBUS', 'VBUS_DIV'); r('R820', '10k', 30, SQ + 16, 'VBUS_DIV', 'GND'); c('C807', '100nF', 42, SQ + 16, 'VBUS_DIV', 'GND')
r('R821', '300k', 57, SQ, 'VBAT_IN', 'VBAT_REF'); r('R822', '10k', 57, SQ + 16, 'VBAT_REF', 'GND'); c('C808', '100nF', 69, SQ + 16, 'VBAT_REF', 'GND')
r('R823', '39k', 84, SQ, 'BUS_EN', 'VBUS_DIV')
r('R828', '22k', 99, SQ, '+3V3', 'SEQ_REF'); r('R829', '10k', 99, SQ + 16, 'SEQ_REF', 'GND'); c('C810', '100nF', 111, SQ + 16, 'SEQ_REF', 'GND')
r('R827', '220k', 126, SQ, '+3V3', 'PRE_TMR'); c('C809', '2.2uF', 126, SQ + 16, 'PRE_TMR', 'GND', C08)
r('R824', '10k', 225, SQ, '+3V3', 'BUS_GOOD_N'); r('R825', '10k', 240, SQ, '+3V3', 'BUS_EN'); r('R826', '10k', 255, SQ, '+3V3', 'PRECHG_EN')
b.add('Q804', 'Transistor_FET:2N7002', '2N7002', 'Package_TO_SOT_SMD:SOT-23', 240, SQ + 20, {'1': 'BUS_GOOD_N', '2': 'GND', '3': 'BUS_EN'})
b.add('D801', 'Diode:BAT54C', 'BAT54C', 'Package_TO_SOT_SMD:SOT-23', 270, SQ + 20, {'1': 'PRECHG_EN', '2': 'PRE_TMR', '3': 'BUS_GOOD_N'})
b.check()
open(OUT, 'w').write(b.render([(f'/{ROOT}/{SB}', 0)]))
print('Bus_Breaker:', len(b.parts), 'parts ->', OUT)
