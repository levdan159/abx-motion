"""Brakes sheet v2 = AUX POWER + ONE BRAKE OUTPUT (replaces 24 V brake buck + 2x TPS27S100A + AND gates).
+24V 5 A (TPS54560B) -> J510 screw terminal (powers the v1.2 board) ; brake supply = +24V via D523 (2026-10-24: the +12V
TPS54360B buck U512, J511 12V_OUT and the J512 BRK_VSEL jumper were removed with the ESP32 sheets) ;
DRV8874 H-bridge -> J501 4-pole (both brakes in parallel): spring-applied coil brakes OR disc-brake actuators.
Values: scratchpad aux_design.md (TPS5x560B/360B sect. 8.2.2), DRV8874 SLVSF66 eq. 3.
Also: abx DRV8874PWPR symbol, Power F1 -> 10 A, net classes.  KiCad must be CLOSED.  python aux.py"""
import subprocess as _sp; assert _sp.run(['pgrep', '-x', 'kicad'], capture_output=True).returncode, 'KiCad is running: close it (without saving) first'
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from schgen import Sheet, existing_uuids
P = os.path.expanduser('~/Documents/abx-motion')
ROOT, SBRK = 'f9149098-3f23-438d-bdc2-2e278b5ca35b', '92144cc8-de39-4073-b886-0ba4c248dd07'
R06, R08 = 'Resistor_SMD:R_0603_1608Metric', 'Resistor_SMD:R_0805_2012Metric'
C06, C12 = 'Capacitor_SMD:C_0603_1608Metric', 'Capacitor_SMD:C_1210_3225Metric'
PDI5 = 'Diode_SMD:D_PowerDI-5'   # pad 1 (tab) = K

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

k = Sheet(paper='A3', globals_=('GND', '+BATT', '+3V3', 'BRK_FLT_N', '+24V', 'DRV_EN_DLY'))
k.uuids = existing_uuids(f'{P}/Brakes.kicad_sch')
k.hier_shapes.update({'BRAKE1_EN': 'input', 'BRAKE2_EN': 'input', '+3V3_DRV_EN': 'input', 'ESTOP_SENSE': 'output'})
r = lambda ref, val, x, y, n1, n2, fp=R06: k.add(ref, 'Device:R', val, fp, x, y, {'1': n1, '2': n2})
c = lambda ref, val, x, y, n1, n2, fp=C06: k.add(ref, 'Device:C', val, fp, x, y, {'1': n1, '2': n2})

def buck(u, sym, val, fp, x, y, s, cin, cbyp, ruv, rt, rfb, rcomp, cz, chf, cboot, l, d, couts, out, vals):
    k.add(u, sym, val, fp, x, y, {'1': f'BOOT_{s}', '2': '+BATT', '3': f'EN_{s}', '4': f'RT_{s}', '5': f'FB_{s}', '6': f'COMP_{s}', '7': 'GND', '8': f'SW_{s}', '9': 'GND'})
    for i, ref in enumerate(cin): c(ref, '2.2uF/100V', x - 60 + 12 * i, y + 30, '+BATT', 'GND', C12)
    c(cbyp, '100nF/100V', x - 60 + 12 * len(cin), y + 30, '+BATT', 'GND')
    r(ruv[0], vals['uv1'], x - 40, y - 10, '+BATT', f'EN_{s}', R08); r(ruv[1], vals['uv2'], x - 28, y - 10, f'EN_{s}', 'GND')
    r(rt, vals['rt'], x - 16, y + 15, f'RT_{s}', 'GND')
    r(rcomp, vals['rc'], x - 4, y + 15, f'COMP_{s}', f'CZ_{s}'); c(cz, vals['cz'], x + 8, y + 15, f'CZ_{s}', 'GND'); c(chf, vals['chf'], x + 20, y + 15, f'COMP_{s}', 'GND')
    c(cboot, '100nF', x + 25, y - 15, f'BOOT_{s}', f'SW_{s}')
    k.add(l, 'Device:L', vals['l'], vals['lfp'], x + 40, y - 15, {'1': f'SW_{s}', '2': out})
    k.add(d, 'Device:D_Schottky', 'PDS5100H-13', PDI5, x + 40, y + 5, {'1': f'SW_{s}', '2': 'GND'})
    r(rfb[0], vals['fb1'], x + 55, y + 15, out, f'FB_{s}'); r(rfb[1], vals['fb2'], x + 67, y + 15, f'FB_{s}', 'GND')
    for i, ref in enumerate(couts): c(ref, '10uF/50V', x + 55 + 12 * i, y - 15, out, 'GND', C12)

# ---- A: +24V 5 A (4 A continuous), 400 kHz ----
k.text('AUX POWER + BRAKE OUTPUT (Brakes sheet v2)', 25.4, 20, 3, True)
k.text('+24V: TPS54560B 400 kHz, 24.0 V (0.8 V x (1 + 348k/12k)), 4 A continuous / 5 A peak (IC 2.2-2.85 W at 5 A). UVLO 27 V on / 25 V off (590k/26.7k). Powers the v1.2 board (J510) and the brake output (via D523).', 25.4, 27)
buck('U511', 'Regulator_Switching:TPS54560BDDA', 'TPS54560BDDAR', 'Package_SO:TI_SO-PowerPAD-8_ThermalVias', 110, 70, '24',
     ('C520', 'C521', 'C522', 'C523'), 'C524', ('R520', 'R521'), 'R522', ('R523', 'R524'), 'R525', 'C526', 'C527', 'C528', 'L520', 'D520',
     ('C529', 'C530', 'C531', 'C532', 'C533'), '+24V',
     dict(uv1='590k', uv2='26.7k', rt='243k', rc='14.3k', cz='6.8nF', chf='56pF C0G', fb1='348k', fb2='12k', l='22uH Isat>=9.5A MWSA1265S-220MT', lfp='Inductor_SMD:L_Sunlord_MWSA1265S'))
k.add('C525', 'Device:C_Polarized', '47uF/80V low ESR', 'Capacitor_SMD:CP_Elec_10x10.5', 30, 70, {'1': '+BATT', '2': 'GND'})
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
k.text('R507: ESTOP_SENSE reads +3V3_DRV_EN on an STM32 input (PD10). BRK_FLT_N (DRV8874 nFAULT, OC / thermal / UVLO): pull-up only (was PCA9555 IO1_3, removed); TODO: MCU input.', 250, 270)
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
for pat in ('+24V', '/Brakes/SW_*', '/Brakes/VM_BRK', '/Brakes/BRK_OUT*'):
    if not any(x['pattern'] == pat for x in pats): pats.append({'netclass': 'Power_HV', 'pattern': pat})
pats[:] = [x for x in pats if x['pattern'] not in ('+12V', '/Brakes/BRK_VSEL')]   # 12 V buck + BRK_VSEL jumper removed 2026-10-24
json.dump(pr, open(f'{P}/abx-motion-brushless.kicad_pro', 'w'), indent=2)
print('done')
