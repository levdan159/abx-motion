"""Brakes sheet v2 = AUX POWER + ONE BRAKE OUTPUT (replaces 24 V brake buck + 2x TPS27S100A + AND gates).
+24V 6 A continuous / 8 A short-term (TI LM70880RRXR synchronous buck, 2026-10-25; was a TPS54560B 4-5 A + catch diode)
-> J510 screw terminal (powers the v1.2 board) ; brake supply = +24V via D523 (2026-10-24: the +12V
TPS54360B buck U512, J511 12V_OUT and the J512 BRK_VSEL jumper were removed with the ESP32 sheets) ;
DRV8874 H-bridge -> J501 4-pole (both brakes in parallel): spring-applied coil brakes OR disc-brake actuators.
Values: 24 V buck .claude/handoff/buck24_6a_design.md + lm70880_report.md (LM708x0 SNVSCD3), DRV8874 SLVSF66 eq. 3.
Also: abx DRV8874PWPR symbol, Power F1 -> 10 A, net classes.  KiCad must be CLOSED.  python aux.py"""
import subprocess as _sp; assert all(_sp.run(['pgrep', '-x', x], capture_output=True).returncode for x in ('kicad', 'eeschema', 'pcbnew')), 'KiCad is running: close it (without saving) first'
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from schgen import Sheet, existing_uuids
P = os.path.expanduser('~/Documents/abx-motion')
ROOT, SBRK = 'f9149098-3f23-438d-bdc2-2e278b5ca35b', '92144cc8-de39-4073-b886-0ba4c248dd07'
R06, R08 = 'Resistor_SMD:R_0603_1608Metric', 'Resistor_SMD:R_0805_2012Metric'
C06, C12 = 'Capacitor_SMD:C_0603_1608Metric', 'Capacitor_SMD:C_1210_3225Metric'
R12, C08 = 'Resistor_SMD:R_1206_3216Metric', 'Capacitor_SMD:C_0805_2012Metric'
FP708 = 'abx-footprints:TI_RRX0029B_VQFN-29_6x6mm_P0.5mm_ThermalVias'   # bl/lm70880fp.py

# ---- abx symbol: DRV8874PWPR (pin-compatible with DRV8876; SLVSF66 pin table) ----
src = open(os.path.join(os.path.dirname(__file__), 'symgen.py')).read()
ns = {}; exec(src[:src.index('\nS = []')], ns)
blk = ns['sym']('DRV8874PWPR', 'TI DRV8874 37V 6A H-bridge, PH/EN or PWM, IPROPI current sense (450 uA/A), ITRIP regulation, HTSSOP-16 PowerPAD',
                'Package_SO:HTSSOP-16-1EP_4.4x5mm_P0.65mm_EP3.4x5mm_Mask3x3mm_ThermalVias', 'https://www.ti.com/lit/ds/symlink/drv8874.pdf', 'H-bridge motor driver brushed',
                [('11', 'VM', 'power_in'), ('12', 'VCP', 'passive'), ('13', 'CPH', 'passive'), ('14', 'CPL', 'passive'), None,
                 ('1', 'EN/IN1', 'input'), ('2', 'PH/IN2', 'input'), ('3', 'nSLEEP', 'input'), ('16', 'PMODE', 'input'), ('7', 'IMODE', 'input'), ('5', 'VREF', 'input')],
                [('8', 'OUT1', 'output'), ('10', 'OUT2', 'output'), None, ('4', 'nFAULT', 'open_collector'), ('6', 'IPROPI', 'output'), None,
                 ('15', 'GND', 'power_in'), ('9', 'PGND', 'power_in'), ('17', 'PAD', 'passive')])
lib = open(f'{P}/abx-symbols.kicad_sym').read()
if '(symbol "DRV8874PWPR"' not in lib:
    i = lib.rstrip().rfind(')'); open(f'{P}/abx-symbols.kicad_sym', 'w').write(lib[:i] + blk + lib[i:])
# ---- abx symbol: LM70880RRXR (SNVSCD3 table 4-1; die pads: VIN = pins 1-3/27-29, SW = 20-22, PGND = 30)
blk = ns['sym']('LM70880RRXR', 'TI LM70880 80V 8A synchronous buck, peak current mode with shunt sense, 0.8V ref, 200k-2.2MHz, hiccup OCP, VQFN-29 RRX (three die pads)',
                FP708, 'https://www.ti.com/lit/ds/symlink/lm70880.pdf', 'buck converter synchronous 80V 8A',
                [('27', 'VIN1', 'power_in'), ('28', 'VIN2', 'passive'), ('29', 'VIN3', 'passive'), ('1', 'VIN4', 'passive'), ('2', 'VIN5', 'passive'),
                 ('3', 'VIN6', 'passive'), None, ('9', 'EN_UVLO', 'input'), ('8', 'PFM_SYNCIN', 'input'), ('13', 'CONFIG', 'input'), ('14', 'RT', 'passive'),
                 None, ('16', 'FB', 'input'), ('15', 'EXTCOMP', 'passive'), None, ('6', 'BIAS', 'power_in'), ('10', 'NC', 'no_connect')],
                [('4', 'CBOOT', 'passive'), ('5', 'SW4', 'passive'), ('20', 'SW1', 'power_out'), ('21', 'SW2', 'passive'), ('22', 'SW3', 'passive'), None,
                 ('11', 'ISNS+', 'input'), ('12', 'VOUT', 'input'), ('7', 'PG_SYNCOUT', 'open_collector'), None, ('19', 'VCC', 'power_out'),
                 ('18', 'VDDA', 'power_out'), None, ('17', 'AGND', 'power_in'), ('30', 'PGND', 'power_in'), ('23', 'PGND1', 'passive'),
                 ('24', 'PGND2', 'passive'), ('25', 'PGND3', 'passive'), ('26', 'PGND4', 'passive')], w=12.7)
import sx   # noqa: E402  (bl/ is on sys.path)
lib = open(f'{P}/abx-symbols.kicad_sym').read()
old = [(s, e) for s, e, h in sx.spans(lib, 1) if h == 'symbol' and lib[s:e].startswith('(symbol "LM70880RRXR"')]
if old:                                   # always rewrite it: the generator is the source (pin names without '/')
    s, e = old[0]; s = lib.rfind('\n', 0, s) + 1; e = lib.index('\n', e) + 1; lib = lib[:s] + lib[e:]
i = lib.rstrip().rfind(')'); open(f'{P}/abx-symbols.kicad_sym', 'w').write(lib[:i] + blk + lib[i:])

k = Sheet(paper='A3', globals_=('GND', '+BATT', '+3V3', 'BRK_FLT_N', '+24V', 'DRV_EN_DLY'))
k.uuids = existing_uuids(f'{P}/Brakes.kicad_sch')
k.hier_shapes.update({'BRAKE1_EN': 'input', 'BRAKE2_EN': 'input', '+3V3_DRV_EN': 'input', 'ESTOP_SENSE': 'output'})
r = lambda ref, val, x, y, n1, n2, fp=R06: k.add(ref, 'Device:R', val, fp, x, y, {'1': n1, '2': n2})
c = lambda ref, val, x, y, n1, n2, fp=C06: k.add(ref, 'Device:C', val, fp, x, y, {'1': n1, '2': n2})

def lcsc(**kw): k.fields.update({ref: {'LCSC': v} for ref, v in kw.items()})

# ---- A: +24V 6 A continuous / 8 A short-term, TI LM70880 synchronous buck, 500 kHz (design: lm70880_report.md)
k.text('AUX POWER + BRAKE OUTPUT (Brakes sheet v2)', 25.4, 20, 3, True)
k.text('+24V: LM70880 synchronous buck, 500 kHz (RT 43.2k), 24.0 V (0.8 V x (1 + 348k/12k)), 6 A continuous / 8 A short-term. Peak current limit 56 mV / 5 mOhm R538 = 10.0-12.4 A (cycle by cycle); hiccup when FB < 0.4 V for 512 limited cycles (off 16384 cycles = 33 ms, 2.8 ms soft start).', 25.4, 27)
k.text('UVLO 27.7 V on / 24.9 V off (267k/10k). FPWM (PFM = GND), spread spectrum on (CONFIG 41.2k), BIAS = GND (immune to v1.2 back-feed; VCC from VIN). Ext. comp 4.42k + 15nF // 100pF (fc ~25 kHz). PG not used. Powers the v1.2 board (J510) and the brake output (via D523).', 25.4, 32)
k.add('U511', 'abx:LM70880RRXR', 'LM70880RRXR', FP708, 130, 100,
      {'27': '+BATT', '28': '+BATT', '29': '+BATT', '1': '+BATT', '2': '+BATT', '3': '+BATT', '9': 'EN_24', '8': 'GND', '13': 'CFG_24', '14': 'RT_24',
       '16': 'FB_24', '15': 'COMP_24', '6': 'GND', '4': 'BOOT_24', '5': 'SW_24', '20': 'SW_24', '21': 'SW_24', '22': 'SW_24', '11': 'ISNS_24',
       '12': '+24V', '19': 'VCC_24', '18': 'VDDA_24', '17': 'GND', '30': 'GND', '23': 'GND', '24': 'GND', '25': 'GND', '26': 'GND'}, nc=('10', '7'))
for i, ref in enumerate(('C520', 'C521', 'C522', 'C523')): c(ref, '4.7uF/100V X7R', 40 + 12 * i, 160, '+BATT', 'GND', C12)
c('C524', '100nF/100V', 88, 160, '+BATT', 'GND')
r('R520', '267k', 40, 60, '+BATT', 'EN_24', R08); r('R521', '10k', 52, 60, 'EN_24', 'GND')
r('R539', '1R', 190, 60, 'BOOT_24', 'BOOTR_24'); c('C528', '47nF/50V', 202, 60, 'BOOTR_24', 'SW_24')
k.add('L520', 'Device:L', '10uH 15.5A TMPC1265HP-100MG-D', 'Inductor_SMD:L_Sunlord_MWSA1265S', 205, 85, {'1': 'SW_24', '2': 'ISNS_24'})
k.add('R538', 'Device:R', '5mR 1% 1W (shunt)', R12, 225, 85, {'1': 'ISNS_24', '2': '+24V'})
for i, ref in enumerate(('C529', 'C530', 'C531', 'C532', 'C533')): c(ref, '10uF/50V X7R', 165 + 12 * i, 160, '+24V', 'GND', C12)
r('R523', '348k', 40, 185, '+24V', 'FB_24'); r('R524', '12k', 52, 185, 'FB_24', 'GND')
r('R525', '4.42k', 64, 185, 'COMP_24', 'CZ_24'); c('C526', '15nF', 76, 185, 'CZ_24', 'GND'); c('C527', '100pF C0G', 88, 185, 'COMP_24', 'GND')
r('R522', '43.2k', 100, 185, 'RT_24', 'GND'); r('R540', '41.2k', 112, 185, 'CFG_24', 'GND')
c('C550', '4.7uF/25V X7R', 124, 185, 'VCC_24', 'GND', C08); c('C551', '100nF', 136, 185, 'VDDA_24', 'GND')
k.text('Kelvin: ISNS+ (pin 11) and VOUT (pin 12) from the inner pad edges of R538; R538 sits next to L520 pad 2. R539 1R in series with CBOOT (required, VCC = 8 V with an adjustable output).', 25.4, 200)
lcsc(U511='C41525220', C520='C381466', C521='C381466', C522='C381466', C523='C381466', C524='C88219', R520='C17585', R521='C25804',
     R539='C22936', C528='C1622', L520='C305223', R538='C316225', C529='C386166', C530='C386166', C531='C386166', C532='C386166',
     C533='C386166', R523='C23006', R524='C22790', R525='C482858', C526='C1596', C527='C14858', R522='C23053', R540='C185330',
     C550='C98195', C551='C14663', C525='C249920', J510='C480516')
k.add('C525', 'Device:C_Polarized', '47uF/80V low ESR', 'Capacitor_SMD:CP_Elec_10x10.5', 30, 120, {'1': '+BATT', '2': 'GND'})
k.add('J510', 'Connector:Conn_01x02_Pin', '24V_OUT (to v1.2 board)', 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal', 260, 60, {'1': '+24V', '2': 'GND'})
k.add('#FLG510', 'power:PWR_FLAG', 'PWR_FLAG', '', 260, 80, {'1': '+24V'})

# ---- C: one brake output, DRV8874 ----
k.text('BRAKE OUTPUT: DRV8874 PWM mode (PMODE high). IN1/IN2 = BRAKE1_EN/BRAKE2_EN (STM32 PE5/PE6 = TIM9 CH1/CH2): 00 coast, 10 OUT1+ (coil brake: RELEASED), 01 reverse (actuator), 11 brake.', 25.4, 215)
k.text('J501: both brakes in parallel (1-2 brake A, 3-4 brake B). Coil brake: OUT1 = +, never drive 01 if the coil has a built-in diode. Supply: +24V through D523 (blocks coil energy from the rail); D522 clamps VM_BRK.', 25.4, 220)
k.text('ITRIP = VREF / (RIPROPI x 450 uA/A) = 3.0 V / (2.2k x 450u) = 3.0 A, fixed off-time (IMODE GND). ~1.5-2 A continuous (0.2 Ohm). nSLEEP via JP501: 1-2 (default) = E-stop immediate (coil brakes), 2-3 = DRV_EN_DLY (actuators get ~1.7 s to apply).', 25.4, 225)
k.add('D523', 'Device:D_Schottky', 'SS54', 'Diode_SMD:D_SMC', 60, 255, {'2': '+24V', '1': 'VM_BRK'})
k.add('#FLG512', 'power:PWR_FLAG', 'PWR_FLAG', '', 60, 270, {'1': 'VM_BRK'})
k.add('D522', 'Device:D_TVS', 'SMBJ28A', 'Diode_SMD:D_SMB', 75, 270, {'1': 'VM_BRK', '2': 'GND'})
k.add('C546', 'Device:C_Polarized', '100uF/50V', 'Capacitor_SMD:CP_Elec_8x10.5', 87, 270, {'1': 'VM_BRK', '2': 'GND'})
c('C545', '10uF/50V', 99, 270, 'VM_BRK', 'GND', C12); c('C544', '100nF/50V', 111, 270, 'VM_BRK', 'GND')
k.add('U513', 'abx:DRV8874PWPR', 'DRV8874PWPR', 'Package_SO:HTSSOP-16-1EP_4.4x5mm_P0.65mm_EP3.4x5mm_Mask3x3mm_ThermalVias', 160, 255,
      {'11': 'VM_BRK', '12': 'BRK_VCP', '13': 'BRK_CPH', '14': 'BRK_CPL', '1': 'hier:BRAKE1_EN', '2': 'hier:BRAKE2_EN', '3': 'BRK_nSLEEP',
       '16': 'BRK_PMODE', '7': 'BRK_IMODE', '5': 'BRK_VREF', '8': 'BRK_OUT1', '10': 'BRK_OUT2', '4': 'BRK_FLT_N', '6': 'BRK_IPROPI',
       '15': 'GND', '9': 'GND', '17': 'GND'})
c('C547', '100nF/50V', 125, 240, 'BRK_VCP', 'VM_BRK'); c('C548', '22nF/50V', 137, 240, 'BRK_CPH', 'BRK_CPL')
r('R537', '0R', 125, 285, 'BRK_PMODE', '+3V3'); r('R536', '0R', 137, 285, 'BRK_IMODE', 'GND')
r('R533', '10k', 195, 285, '+3V3', 'BRK_VREF'); r('R534', '100k', 207, 285, 'BRK_VREF', 'GND'); r('R532', '2.2k', 219, 285, 'BRK_IPROPI', 'GND')
k.add('JP501', 'Jumper:SolderJumper_3_Bridged12', 'nSLEEP: E-stop | delayed', 'Jumper:SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm', 125, 205,
      {'1': 'hier:+3V3_DRV_EN', '2': 'BRK_nSLEEP', '3': 'DRV_EN_DLY'})
k.add('J501', 'Connector:Conn_01x04_Pin', 'BRAKES (A: 1-2, B: 3-4)', 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-4-5.08_1x04_P5.08mm_Horizontal', 230, 255,
      {'1': 'BRK_OUT1', '2': 'BRK_OUT2', '3': 'BRK_OUT1', '4': 'BRK_OUT2'})
r('R510', '10k', 205, 240, '+3V3', 'BRK_FLT_N')
r('R507', '1k', 300, 255, 'hier:+3V3_DRV_EN', 'hier:ESTOP_SENSE')
k.text('R507: ESTOP_SENSE reads +3V3_DRV_EN on an STM32 input (PD10). BRK_FLT_N (DRV8874 nFAULT, OC / thermal / UVLO, R510 pull-up) -> STM32 PD9 (input, 2026-10-24).', 250, 270)
k.check()
open(f'{P}/Brakes.kicad_sch', 'w').write(k.render([(f'/{ROOT}/{SBRK}', 0)]))
print('Brakes sheet:', len(k.parts), 'parts')

# ---- Power: F1 5 A -> 10 A (logic branch now also feeds +24V) ----
t = open(f'{P}/Power.kicad_sch').read()
for old, new in (('(property "Value" "5A"', '(property "Value" "10A 58V ATO"'),
                 ('F1 now only protects the logic branch (buck + LDO), 5 A.', 'F1 protects the logic branch (5 V buck + LDO, +24V aux buck), 10 A 58 V blade.'),
                 ('(5 V buck + LDO, +24V/+12V aux bucks)', '(5 V buck + LDO, +24V aux buck)')):
    if old in t: assert t.count(old) == 1, old; t = t.replace(old, new)
open(f'{P}/Power.kicad_sch', 'w').write(t)

# ---- net classes ----
pr = json.load(open(f'{P}/abx-motion-brushless.kicad_pro')); pats = pr['net_settings']['netclass_patterns']
for pat in ('+24V', '/Brakes/SW_*', '/Brakes/ISNS_*', '/Brakes/VM_BRK', '/Brakes/BRK_OUT*'):
    if not any(x['pattern'] == pat for x in pats): pats.append({'netclass': 'Power_HV', 'pattern': pat})
pats[:] = [x for x in pats if x['pattern'] not in ('+12V', '/Brakes/BRK_VSEL')]   # 12 V buck + BRK_VSEL jumper removed 2026-10-24
json.dump(pr, open(f'{P}/abx-motion-brushless.kicad_pro', 'w'), indent=2)
print('done')
