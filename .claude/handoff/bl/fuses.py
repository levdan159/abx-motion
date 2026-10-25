"""Active protection: Bus_Breaker sheet (TPS48111-Q1), protected high-side brake drivers (TPS27S100A), MIC2009 eFuses for F3/F4/F5."""
import sys, os, re, json
sys.path.insert(0, os.path.dirname(__file__))
from schgen import Sheet, uid, existing_uuids, inject
import sx
from schq import items, libpins, pinpos
P = os.path.expanduser('~/Documents/abx-motion')
ROOT = 'f9149098-3f23-438d-bdc2-2e278b5ca35b'
SB, SBRK, SMCU, SIIO = uid('block', 'Bus_Breaker'), '92144cc8-de39-4073-b886-0ba4c248dd07', 'c81c9d86-49aa-496e-8f70-b852842466ca', '5b34e428-8262-458c-b688-d5bdfede8a4e'
R06, R08, R12 = 'Resistor_SMD:R_0603_1608Metric', 'Resistor_SMD:R_0805_2012Metric', 'Resistor_SMD:R_2512_6332Metric'
C06, C08, C12 = 'Capacitor_SMD:C_0603_1608Metric', 'Capacitor_SMD:C_0805_2012Metric', 'Capacitor_SMD:C_1210_3225Metric'
def rr(sh): return lambda ref, val, x, y, n1, n2, fp=R06: sh.add(ref, 'Device:R', val, fp, x, y, {'1': n1, '2': n2})
def cc(sh): return lambda ref, val, x, y, n1, n2, fp=C06: sh.add(ref, 'Device:C', val, fp, x, y, {'1': n1, '2': n2})

# ======================= Bus breaker (new sheet) =======================
b = Sheet(paper='A3', globals_=('GND', 'VBUS', 'VBAT_IN', '+3V3', 'BUS_EN', 'PRECHG_EN', 'BUS_FLT_N', 'BUS_IMON')); r, c = rr(b), cc(b)
b.text('MAIN BUS BREAKER - TPS48111-Q1 smart high-side driver between the battery (VBAT_IN, J1) and the motor bus (VBUS)', 20, 20, 3, True)
b.text('Back-to-back Q801/Q802 (common source): bidirectional when on (regen reaches the battery), blocks both ways when off. Logic supply (F1) taps VBAT_IN before the breaker, so the ESP32 and brakes stay powered when the bus trips.', 20, 28, 1.6)
b.text('Start-up (firmware): BUS_EN=0, PRECHG_EN=1 -> Q803 + R803/R804 (20 R) charge ~1 mF of ESC bulk capacitance through the Q802 body diode (tau ~20 ms); after ~150 ms BUS_EN=1, then PRECHG_EN=0.', 20, 33, 1.6)
b.text('Protection (TPS4811 SLUSEE5E eq. 6/7/9/11/13): RSNS 0.5 mOhm, RSET 100 R. IOC = 80 A (R815 30.1k, blank tOC = 5 ms with C804 330 nF, auto-retry ~7.5 s). ISC = 150 A (R816 4.32k, trips in 1.2 us). IMON gain 61.2 (R813 6.8k): 30.6 mV/A -> 1.84 V at 60 A.', 20, 38, 1.6)
b.text('UVLO: 28 V rising (R806 470k / R807 20.5k, 1.18 V threshold). Faults FLT_I/FLT_T open drain -> BUS_FLT_N (ESP32). INP/INP_G have internal pull-downs: bus is OFF while the ESP32 is in reset.', 20, 43, 1.6)
b.text('NOTE: VS/CS+/ISCP are rated -1 V: a reversed battery still damages U801, but Q801/Q802 keep reverse voltage off the ESC side. Keep the external 80 A fuse.', 20, 48, 1.6)
b.text('TODO: hardware-autonomous enable/precharge (next step). BUS_EN and PRECHG_EN have no driver since the ESP32 was removed (2026-10-24): INP/INP_G internal pull-downs keep the bus OFF.', 20, 56, 2, True)   # added 2026-10-24 (ESP32 removed)
b.text('BUS_FLT_N -> STM32 PD8 (ESC_MCU), BUS_IMON -> 74HC4051 U706 ch5 (ESC_MCU). The ESP32 mentions above are history.', 20, 61, 1.6)
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
r('R806', '470k', 80, 140, 'VBAT_IN', 'BUS_UVLO'); r('R807', '20.5k', 80, 160, 'BUS_UVLO', 'GND'); c('C802', '100nF', 95, 160, 'BUS_UVLO', 'GND')
r('R808', '1k', 105, 175, 'BUS_EN', 'BUS_INP'); r('R809', '1k', 120, 175, 'PRECHG_EN', 'BUS_INPG')
r('R815', '30.1k', 135, 190, 'BUS_IWRN', 'GND'); c('C804', '330nF', 150, 190, 'BUS_TMR', 'GND')
r('R810', '1k', 200, 175, 'BUS_FLT_I', 'BUS_FLT_N'); r('R811', '1k', 215, 175, 'BUS_FLT_T', 'BUS_FLT_N'); r('R812', '10k', 230, 175, '+3V3', 'BUS_FLT_N')
r('R813', '6.8k', 200, 200, 'BUS_IMON_R', 'GND'); r('R814', '1k', 215, 200, 'BUS_IMON_R', 'BUS_IMON'); c('C803', '10nF', 230, 200, 'BUS_IMON', 'GND')
b.check()
open(f'{P}/Bus_Breaker.kicad_sch', 'w').write(b.render([(f'/{ROOT}/{SB}', 0)]))

# ======================= Brakes (regenerated, existing uuids kept) =======================
k = Sheet(paper='A4', globals_=('GND', '+BATT', '+3V3', 'BRK_FLT_N')); r, c = rr(k), cc(k); k.uuids = existing_uuids(f'{P}/Brakes.kicad_sch')
k.hier_shapes.update({'BRAKE1_EN': 'input', 'BRAKE2_EN': 'input', '+3V3_DRV_EN': 'input', 'ESTOP_SENSE': 'output'})
k.add('U501', 'Regulator_Switching:LMR33630ADDA', 'LMR36520FADDA', 'Package_SO:Texas_HSOP-8-1EP_3.9x4.9mm_P1.27mm', 68.58, 60.96,
      {'2': '+BATT', '3': '+BATT', '6': 'BR_VCC', '1': 'GND', '9': 'GND', '7': 'BR_BOOT', '8': 'BR_SW', '5': 'BR_FB'}, nc=['4'])
c('C505', '4.7uF/100V', 25.4, 101.6, '+BATT', 'GND', 'Capacitor_SMD:C_1206_3216Metric'); c('C506', '4.7uF/100V', 40.64, 101.6, '+BATT', 'GND', 'Capacitor_SMD:C_1206_3216Metric')
c('C507', '100nF/100V', 55.88, 101.6, '+BATT', 'GND'); c('C501', '100nF', 76.2, 101.6, 'BR_BOOT', 'BR_SW'); c('C502', '1uF', 91.44, 101.6, 'BR_VCC', 'GND')
k.add('L501', 'Device:L', '47uH 3A', 'Inductor_SMD:L_Bourns_SRP7028A_7.3x6.6mm', 106.68, 101.6, {'1': 'BR_SW', '2': '+24V_BRAKE'})
r('R501', '100k', 121.92, 101.6, '+24V_BRAKE', 'BR_FB'); r('R502', '4.32k', 137.16, 101.6, 'BR_FB', 'GND')
c('C503', '22uF/50V', 152.4, 101.6, '+24V_BRAKE', 'GND', C12); c('C504', '22uF/50V', 167.64, 101.6, '+24V_BRAKE', 'GND', C12)
k.add('#FLG501', 'power:PWR_FLAG', 'PWR_FLAG', '', 185, 101.6, {'1': '+24V_BRAKE'})
for i, (y, u_, cd, rs, us, rl, ci, d, j) in enumerate(((140, 'U502', 'C508', 'R503', 'U504', 'R508', 'C510', 'D501', 'J501'), (180, 'U503', 'C509', 'R505', 'U505', 'R509', 'C511', 'D502', 'J502')), 1):
    k.add(u_, '74xGxx:74LVC1G08', '74LVC1G08', 'Package_TO_SOT_SMD:SOT-23-5', 40, y, {'1': f'hier:BRAKE{i}_EN', '2': 'hier:+3V3_DRV_EN', '3': 'GND', '4': f'BRK{i}_G', '5': '+3V3'})
    c(cd, '100nF', 20, y, '+3V3', 'GND'); r(rs, '10k', 62, y, f'BRK{i}_G', f'BRK{i}_EN')
    k.add(us, 'abx:TPS27S100APWPR', 'TPS27S100APWPR', 'Package_SO:HTSSOP-14-1EP_4.4x5mm_P0.65mm_EP3.4x5mm_Mask3x3.1mm_ThermalVias', 100, y,
          {'8': '+24V_BRAKE', '9': '+24V_BRAKE', '10': '+24V_BRAKE', '3': f'BRK{i}_EN', '12': '+3V3', '13': f'BRK{i}_ILIM', '2': 'GND', '15': 'GND',
           '5': f'BRK{i}_OUT', '6': f'BRK{i}_OUT', '7': f'BRK{i}_OUT', '14': 'BRK_FLT_N'}, nc=['1', '4', '11'])
    r(rl, '1.65k', 75, y + 15, f'BRK{i}_ILIM', 'GND'); c(ci, '220nF/50V', 125, y - 15, '+24V_BRAKE', 'GND')
    k.add(d, 'Device:D_Schottky', 'SS34', 'Diode_SMD:D_SMA', 140, y, {'1': f'BRK{i}_OUT', '2': 'GND'})
    k.add(j, 'Connector:Conn_01x02_Pin', f'BRAKE{i}', 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal', 170, y, {'1': f'BRK{i}_OUT', '2': 'GND'})
r('R510', '10k', 150, 160, '+3V3', 'BRK_FLT_N')
r('R507', '1k', 226.06, 60.96, 'hier:+3V3_DRV_EN', 'hier:ESTOP_SENSE')
k.text('BRAKES: fail-safe (spring-applied, power-off) holding brakes for the 2 drive motors', 25.4, 25.4, 2, True)
k.text('+24V_BRAKE: LMR36520FADDA buck from +BATT. Vout = 1.0 V x (1 + R501/R502) = 24.1 V (12 V coils: R502 = 9.09k).', 25.4, 33.02)
k.text('Coil ENERGISED (brake released) only while BRAKEn_EN = 1 AND +3V3_DRV_EN (E-stop) = 1. High-side switched: a coil wire shorted to chassis cannot release the brake.', 25.4, 38.1)
k.text('TPS27S100A: current limit 1.5 A (R508/R509 = 1.233 V x 2000 / 1.5 A), <1 us hard-short trip, thermal shutdown; FLT (open drain, wired-OR) -> BRK_FLT_N -> PCA9555 IO1_3.', 25.4, 43.18)
k.text('D501/D502 freewheel the coil (switch clamp not relied on). R507: ESTOP_SENSE reads +3V3_DRV_EN on an ESP32 input.', 25.4, 48.26)
k.check()
open(f'{P}/Brakes.kicad_sch', 'w').write(k.render([(f'/{ROOT}/{SBRK}', 0)]))

# ======================= helpers for hand-drawn sheets =======================
def cut(t, s, e):
    j = s
    while t[j - 1] in ' \t': j -= 1
    if t[j - 1] == '\n': j -= 1
    return t[:j] + t[e:]
def drop_fuse(t, ref):
    it = items(t); sym = [i for i in it if i[0] == 'symbol' and i[2] == ref][0]; lp = libpins(t, sym[3])
    kill = [(sym[4], sym[5])]
    for n, p in lp.items():
        pp = pinpos(sym[1], p)
        for w in [i for i in it if i[0] == 'wire' and any(abs(a - pp[0]) < .01 and abs(c_ - pp[1]) < .01 for a, c_ in i[1])]:
            kill.append((w[2], w[3])); far = [q for q in w[1] if abs(q[0] - pp[0]) > .01 or abs(q[1] - pp[1]) > .01][0]
            for i in it:
                if i[0] == 'label' and abs(i[1][0] - far[0]) < .01 and abs(i[1][1] - far[1]) < .01: kill.append((i[3], i[4]))
                if i[0] == 'symbol' and i[3].startswith('power:') and abs(i[1][0] - far[0]) < .01 and abs(i[1][1] - far[1]) < .01: kill.append((i[4], i[5]))
    print('  drop', ref, len(kill), 'items')
    for s, e in sorted(kill, reverse=True): t = cut(t, s, e)
    return t
def pin_label(t, ref, pin, net):
    it = items(t); sym = [i for i in it if i[0] == 'symbol' and i[2] == ref][0]; lp = libpins(t, sym[3]); p = lp[pin]
    x, y = pinpos(sym[1], p); a = (p[3] + sym[1][2] + 180) % 360
    for i in it:
        if i[0] == 'no_connect' and abs(i[1][0] - x) < .01 and abs(i[1][1] - y) < .01: t = cut(t, i[3], i[4]); break
    lab = f'\t(global_label "{net}"\n\t\t(shape bidirectional)\n\t\t(at {x:g} {y:g} {a})\n\t\t(effects (font (size 1.27 1.27)) (justify {"right" if a == 180 else "left"}))\n\t\t(uuid "{uid("gl", ref, pin, net)}")\n\t)\n'
    j = t.rfind('\n', 0, min(s for s, e, h in sx.spans(t, 1) if h in ('sheet_instances', 'embedded_fonts'))) + 1
    print('  ', ref, pin, p[0], '->', net, (x, y, a))
    return t[:j] + lab + t[j:]

# ======================= MCU (ESP32) sheet =======================
t = open(f'{P}/MCU.kicad_sch').read().replace('(paper "A3")', '(paper "A2")', 1)
t = drop_fuse(t, 'F3'); t = drop_fuse(t, 'F4')
for pin, net in (('7', 'BUS_EN'), ('38', 'PRECHG_EN'), ('25', 'BUS_FLT_N'), ('6', 'BUS_IMON'), ('24', 'EFUSE_EN')): t = pin_label(t, 'U3', pin, net)
m = Sheet(paper='A2', globals_=('GND', '+5V', '+3V3', 'EFUSE_EN', 'EFUSE_FLT_N')); r, c = rr(m), cc(m)
m.text('OUTPUT eFUSES (were PTC F3/F4): MIC2009 current-limited switches, RSET = CLF/I (CLF ~235). FAULT/ open drain wired-OR -> EFUSE_FLT_N (PCA9555 IO1_2).', 440, 40, 1.8, True)
m.text('EFUSE_EN (ESP32 IO47, 100k pull-up): outputs on at boot for an active-high part; firmware can switch them / match the ordered EN polarity.', 440, 46, 1.6)
for (u_, vin, vout, rs, val, ci, co, x) in (('U205', '+5V', '+5V_ENC', 'R233', '470', 'C215', 'C216', 460), ('U206', '+3V3', '+3V3_EXT', 'R234', '931', 'C217', 'C218', 530)):
    m.add(u_, 'abx:MIC2009YM6', 'MIC2009YM6', 'Package_TO_SOT_SMD:SOT-23-6', x, 80, {'VIN': vin, 'EN': 'EFUSE_EN', 'ILIMIT': f'{u_}_ILIM', 'GND': 'GND', 'VOUT': vout, 'FAULT': 'EFUSE_FLT_N'})
    r(rs, val, x - 5, 105, f'{u_}_ILIM', 'GND'); c(ci, '1uF', x - 25, 80, vin, 'GND'); c(co, '4.7uF', x + 25, 80, vout, 'GND', C08)
m.text('U205: +5V_ENC 0.5 A (encoders).  U206: +3V3_EXT 0.25 A, below the 600 mA 3V3 LDO so a short cannot brown out the ESP32.', 440, 120, 1.6)
r('R235', '100k', 460, 140, '+3V3', 'EFUSE_EN')
m.check()
t = inject(t, m.render([(f'/{ROOT}/{SMCU}', 0)]))
open(f'{P}/MCU.kicad_sch', 'w').write(t)

# ======================= Industrial IO sheet =======================
t = open(f'{P}/Industrial_IO.kicad_sch').read().replace('(paper "A3")', '(paper "A2")', 1)
t = drop_fuse(t, 'F5')
t = pin_label(t, 'U601', '15', 'EFUSE_FLT_N'); t = pin_label(t, 'U601', '16', 'BRK_FLT_N')
q = Sheet(paper='A2', globals_=('GND', '+5V', '+3V3', 'EFUSE_EN', 'EFUSE_FLT_N')); r, c = rr(q), cc(q)
q.text('+5V_OUT eFUSE (was PTC F5): MIC2009, 0.5 A (RSET 470 R). FAULT/ -> EFUSE_FLT_N (pull-up R623) -> PCA9555 IO1_2.', 440, 40, 1.8, True)
q.add('U602', 'abx:MIC2009YM6', 'MIC2009YM6', 'Package_TO_SOT_SMD:SOT-23-6', 470, 80, {'VIN': '+5V', 'EN': 'EFUSE_EN', 'ILIMIT': 'U602_ILIM', 'GND': 'GND', 'VOUT': '+5V_OUT', 'FAULT': 'EFUSE_FLT_N'})
r('R624', '470', 465, 105, 'U602_ILIM', 'GND'); c('C610', '1uF', 445, 80, '+5V', 'GND'); c('C611', '4.7uF', 495, 80, '+5V_OUT', 'GND', C08)
r('R623', '10k', 520, 80, '+3V3', 'EFUSE_FLT_N')
q.check()
t = inject(t, q.render([(f'/{ROOT}/{SIIO}', 0)]))
open(f'{P}/Industrial_IO.kicad_sch', 'w').write(t)

# ======================= Power sheet: J1 net is now VBAT_IN =======================
t = open(f'{P}/Power.kicad_sch').read()
n = t.count('(global_label "VBUS"'); t = t.replace('(global_label "VBUS"', '(global_label "VBAT_IN"'); print('  Power: VBUS global labels renamed', n)
open(f'{P}/Power.kicad_sch', 'w').write(t)

# ======================= root block + net classes =======================
t = open(f'{P}/abx-motion-brushless.kicad_sch').read()
if 'Bus_Breaker.kicad_sch' not in t:
    x, y, w, h = 213.36, 172.72, 55.88, 15.24
    blk = f'''\t(sheet
\t\t(at {x:g} {y:g})
\t\t(size {w:g} {h:g})
\t\t(fields_autoplaced yes)
\t\t(stroke
\t\t\t(width 0.1524)
\t\t\t(type solid)
\t\t)
\t\t(fill
\t\t\t(color 0 0 0 0.0000)
\t\t)
\t\t(uuid "{SB}")
\t\t(property "Sheetname" "Bus_Breaker"
\t\t\t(at {x:g} {y - 1.27:g} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(justify left bottom)
\t\t\t)
\t\t)
\t\t(property "Sheetfile" "Bus_Breaker.kicad_sch"
\t\t\t(at {x:g} {y + h + 0.6:g} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(justify left top)
\t\t\t)
\t\t)
\t\t(instances
\t\t\t(project "abx-motion-brushless"
\t\t\t\t(path "/{ROOT}"
\t\t\t\t\t(page "13")
\t\t\t\t)
\t\t\t)
\t\t)
\t)
'''
    i = t.index('\t(sheet_instances'); t = t[:i] + blk + t[i:]
    open(f'{P}/abx-motion-brushless.kicad_sch', 'w').write(t)
pr = json.load(open(f'{P}/abx-motion-brushless.kicad_pro'))
pats = pr['net_settings']['netclass_patterns']
for pat in ('VBAT_IN', '/Bus_Breaker/BUS_SNS', '/Bus_Breaker/BUS_SRC', '/Bus_Breaker/PRE_*'):
    if not any(x['pattern'] == pat for x in pats): pats.append({'netclass': 'Power_HV', 'pattern': pat})
json.dump(pr, open(f'{P}/abx-motion-brushless.kicad_pro', 'w'), indent=2)
print('done; Bus_Breaker block', SB)
