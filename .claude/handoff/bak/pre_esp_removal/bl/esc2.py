"""Single-MCU dual ESC: ESC_Channel.kicad_sch = power stage (x2), ESC_MCU.kicad_sch = one STM32F405VGT6 (Stormcore 60D pin map)."""
import sys, os, re, uuid
sys.path.insert(0, os.path.dirname(__file__))
from schgen import Sheet, uid
import sx
P = os.path.expanduser('~/Documents/abx-motion')
ROOT = 'f9149098-3f23-438d-bdc2-2e278b5ca35b'
S1, S2 = '68e0475f-9c75-41f9-88c7-a3831640edb7', 'df9be12f-039b-4c8b-99bb-7b46ec8aece4'
SM = uid('block', 'ESC_MCU')
R06, R08, R12 = 'Resistor_SMD:R_0603_1608Metric', 'Resistor_SMD:R_0805_2012Metric', 'Resistor_SMD:R_2512_6332Metric'
C06, C08, C12 = 'Capacitor_SMD:C_0603_1608Metric', 'Capacitor_SMD:C_0805_2012Metric', 'Capacitor_SMD:C_1210_3225Metric'
G = ('GND', '+5V', 'VBUS', '+3V3_ESC')

# ======================= power stage (instanced twice) =======================
sh = Sheet(paper='A2', globals_=G); add = sh.add
def r(ref, val, x, y, n1, n2, fp=R06): add(ref, 'Device:R', val, fp, x, y, {'1': n1, '2': n2})
def c(ref, val, x, y, n1, n2, fp=C06): add(ref, 'Device:C', val, fp, x, y, {'1': n1, '2': n2})
PIN_IN = ['INHA', 'INLA', 'INHB', 'INLB', 'INHC', 'INLC', 'ENABLE', 'nSCS', 'SCLK', 'SDI']
PIN_OUT = ['SDO', 'nFAULT', 'SOA', 'SOB', 'SOC', 'SENS_A', 'SENS_B', 'SENS_C', 'TEMP_MOS', 'TEMP_MOT', 'HALL1', 'HALL2', 'HALL3']
for n in PIN_IN: sh.hier_shapes[n] = 'input'
for n in PIN_OUT: sh.hier_shapes[n] = 'output'
sh.text('ESC POWER STAGE - one motor (36 V 10S, 30 A peak). DRV8323S + 6x CSD19532Q5B + 3x 1 mOhm shunts', 20, 20, 3.5, True)
sh.text('Instanced twice: ESC_Motor_1 (refs 3xx) and ESC_Motor_2 (refs 4xx). Both are driven by the single STM32F405VGT6 on sheet ESC_MCU (VESC dual-motor, Stormcore 60D pin map).', 20, 28, 1.8)
sh.text('GATE DRIVER: DRV8323S (SPI, 6x PWM, 3 CSAs, gain set by firmware = 10 V/V)', 190, 95, 2.5, True)
sh.text('POWER STAGE: 3 half-bridges, CSD19532Q5B 100 V, 1 mOhm shunts (route SPx/GND as Kelvin pair to the DRV8323S)', 335, 95, 2.5, True)
sh.text('SENSING: phase voltages (39k/2.2k), FET NTC (low side, 10k pull-up, B3435), motor NTC', 290, 280, 2.5, True)
sh.text('MOTOR INTERFACE: halls (commutation) + motor NTC. Odometry encoders go to the ESP32 (J202/J203).', 400, 322, 2.5, True)
sh.text('NOTES: (1) DRV8323S VM abs max 65 V, recommended 60 V: D301 SMCJ43A TVS on VBUS (one per stage): ~54 V at a few A, 69 V at full current, so it only trims regen spikes; the real limit is VESC max input voltage 46-48 V (regen stops before the breaker can strand the energy). (2) R310-R315 slew trim 2.2 R. (3) SDO is open drain: both DRVs share MISO.', 20, 405, 1.5)
drv = {'ENABLE': 'hier:ENABLE', 'INHA': 'hier:INHA', 'INLA': 'hier:INLA', 'INHB': 'hier:INHB', 'INLB': 'hier:INLB', 'INHC': 'hier:INHC', 'INLC': 'hier:INLC',
       'nSCS': 'hier:nSCS', 'SCLK': 'hier:SCLK', 'SDI': 'hier:SDI', 'SDO': 'hier:SDO', 'CAL': 'CAL', 'nFAULT': 'hier:nFAULT',
       'GHA': 'GHA', 'SHA': 'PH_A', 'GLA': 'GLA', 'SPA': 'SPA', 'SNA': 'GND', 'GHB': 'GHB', 'SHB': 'PH_B', 'GLB': 'GLB', 'SPB': 'SPB', 'SNB': 'GND',
       'GHC': 'GHC', 'SHC': 'PH_C', 'GLC': 'GLC', 'SPC': 'SPC', 'SNC': 'GND', 'SOA': 'hier:SOA', 'SOB': 'hier:SOB', 'SOC': 'hier:SOC',
       'CPL': 'CPL', 'CPH': 'CPH', 'VCP': 'VCP', 'VM': 'VBUS', 'VDRAIN': 'VBUS', 'AGND': 'GND', 'PGND': 'GND', 'DVDD': 'DVDD', 'VREF': '+3V3_ESC', 'PAD': 'GND'}
add('U302', 'abx:DRV8323SRTAR', 'DRV8323SRTAR', 'abx-footprints:Texas_RTA0040B_WQFN-40-1EP_6x6mm_P0.5mm_EP4.15x4.15mm', 250, 150, drv)
c('C316', '47nF/100V', 200, 110, 'CPH', 'CPL'); c('C317', '1uF/25V', 212, 110, 'VCP', 'VBUS'); c('C318', '1uF', 224, 110, 'DVDD', 'GND')
c('C319', '100nF', 236, 110, '+3V3_ESC', 'GND'); c('C320', '100nF/100V', 248, 110, 'VBUS', 'GND'); c('C321', '10uF/100V', 260, 110, 'VBUS', 'GND', C12)
r('R301', '10k', 276, 110, '+3V3_ESC', 'hier:nFAULT'); r('R302', '10k', 286, 110, '+3V3_ESC', 'hier:SDO'); r('R303', '10k', 296, 110, '+3V3_ESC', 'hier:nSCS'); r('R304', '10k', 306, 110, 'GND', 'CAL')
sh.text('VM: 100nF + 10uF within 3 mm of pin 4; CPH-CPL 47nF rated VM; VCP-VM 1uF/25V', 195, 100, 1.4)
for ph, x0, q_h, q_l, rg_h, rg_l, rs, jn in (('A', 370, 'Q301', 'Q302', 'R310', 'R311', 'R307', 'J301'), ('B', 450, 'Q303', 'Q304', 'R312', 'R313', 'R308', 'J302'), ('C', 530, 'Q305', 'Q306', 'R314', 'R315', 'R309', 'J303')):
    FET, TD = 'Transistor_FET:CSD19532Q5B', 'Package_TO_SOT_SMD:TDSON-8-1'
    add(q_h, FET, 'CSD19532Q5B', TD, x0, 170, {'1': f'PH_{ph}', '2': f'PH_{ph}', '3': f'PH_{ph}', '4': f'GH{ph}_G', '5': 'VBUS'})
    add(q_l, FET, 'CSD19532Q5B', TD, x0, 215, {'1': f'SP{ph}', '2': f'SP{ph}', '3': f'SP{ph}', '4': f'GL{ph}_G', '5': f'PH_{ph}'})
    r(rg_h, '2.2', x0 - 25, 165, f'GH{ph}', f'GH{ph}_G'); r(rg_l, '2.2', x0 - 25, 210, f'GL{ph}', f'GL{ph}_G')
    r(rs, '1m 3W', x0 + 25, 245, f'SP{ph}', 'GND', R12)
for ref, x0, kind in (('C322', 345, 'c'), ('C323', 360, 'c'), ('C328', 395, 'p'), ('C324', 425, 'c'), ('C325', 440, 'c'), ('C329', 470, 'p'), ('C326', 505, 'c'), ('C327', 520, 'c')):
    if kind == 'c': c(ref, '10uF/100V', x0, 128, 'VBUS', 'GND', C12)
    else: add(ref, 'Device:C_Polarized', '220uF/63V', 'Capacitor_SMD:CP_Elec_10x10.5', x0, 128, {'1': 'VBUS', '2': 'GND'})
add('J301', 'Connector:Screw_Terminal_01x03', 'PHASES DG135T-10.16-03P', 'abx-footprints:ABX_Degson_DG135T-10.16-03P', 570, 192, {'1': 'PH_A', '2': 'PH_B', '3': 'PH_C'})  # 57 A screw terminal on the board edge
add('D301', 'Device:D_TVS', 'SMCJ43A', 'Diode_SMD:D_SMC', 540, 128, {'1': 'VBUS', '2': 'GND'})  # pin 1 = pad 1 = cathode
x = 300
for ph, rt, rb, cc in (('A', 'R316', 'R319', 'C330'), ('B', 'R317', 'R320', 'C331'), ('C', 'R318', 'R321', 'C332')):
    r(rt, '39k', x, 292, f'PH_{ph}', f'hier:SENS_{ph}', R08); r(rb, '2.2k', x, 308, f'hier:SENS_{ph}', 'GND'); c(cc, '2.2nF', x + 12, 308, f'hier:SENS_{ph}', 'GND'); x += 30
r('R324', '10k', 430, 292, '+3V3_ESC', 'hier:TEMP_MOS')
add('NT301', 'Device:Thermistor_NTC', 'NTC 10k B3435', R06, 430, 308, {'1': 'hier:TEMP_MOS', '2': 'GND'})
r('R325', '10k', 455, 292, '+3V3_ESC', 'hier:TEMP_MOT'); c('C334', '10nF', 467, 308, 'hier:TEMP_MOT', 'GND')
sh.text('FET NTC on the low side (VESC NTC_RES formula, beta 3434). Place NT301 next to the FETs.', 290, 318, 1.4)
add('J304', 'Connector_Generic:Conn_01x06', 'HALL_TEMP', 'Connector_JST:JST_PH_B6B-PH-K_1x06_P2.00mm_Vertical', 440, 355,
    {'1': '+5V', '2': 'HALL1_IN', '3': 'HALL2_IN', '4': 'HALL3_IN', '5': 'hier:TEMP_MOT', '6': 'GND'})
for i, (rs_, rp, cc) in enumerate((('R326', 'R329', 'C340'), ('R327', 'R330', 'C341'), ('R328', 'R331', 'C342')), 1):
    xx = 470 + 22 * i
    r(rs_, '1k', xx, 350, f'HALL{i}_IN', f'hier:HALL{i}'); r(rp, '4.7k', xx + 8, 365, '+3V3_ESC', f'hier:HALL{i}'); c(cc, '1nF', xx + 16, 350, f'hier:HALL{i}', 'GND')
sh.check()
open(f'{P}/ESC_Channel.kicad_sch', 'w').write(sh.render([(f'/{ROOT}/{S1}', 0), (f'/{ROOT}/{S2}', 100)]))
print('power parts', len(sh.parts))

# ======================= ESC MCU (single) =======================
m = Sheet(paper='A2', globals_=G); add = m.add
def r(ref, val, x, y, n1, n2, fp=R06): add(ref, 'Device:R', val, fp, x, y, {'1': n1, '2': n2})
def c(ref, val, x, y, n1, n2, fp=C06): add(ref, 'Device:C', val, fp, x, y, {'1': n1, '2': n2})
MOT = ['INHA', 'INLA', 'INHB', 'INLB', 'INHC', 'INLC', 'ENABLE', 'nSCS', 'nFAULT', 'SOA', 'SOB', 'SOC', 'SENS_A', 'SENS_B', 'SENS_C', 'TEMP_MOS', 'TEMP_MOT', 'HALL1', 'HALL2', 'HALL3']
for k in (1, 2):
    for n in MOT: m.hier_shapes[f'M{k}_{n}'] = 'output' if n in PIN_IN else 'input'
m.hier_shapes.update({'DRV_SCLK': 'output', 'DRV_SDI': 'output', 'DRV_SDO': 'input', 'NRST': 'input', '+3V3_DRV_EN': 'input'})
m.text('ESC MCU - one STM32F405VGT6 runs both motors (VESC firmware, HW_HAS_DUAL_MOTORS)', 20, 20, 3.5, True)
m.text('Pin map = hwconf/stormcore/60D (HW_VER_IS_60D: CURRENT_AMP_GAIN 10, CURRENT_SHUNT_RES 0.001, VIN 39k/2.2k). Own hwconf: copy hw_stormcore_60d_core.*, drop the smart switch (HW_EARLY_INIT, SWITCH_*), NRF, IMU and RGB LED.', 20, 28, 1.8)
m.text('Motor 1 = TIM1 (PE8-PE13), CURR1-3 PB1/PB0/PC4, SENS1-3 PA2/PA0/PA1, halls PD13/PD12/PD14 (+ABI encoder option on TIM4), nSCS PC13, EN PE14, nFAULT PE3', 20, 34, 1.8)
m.text('Motor 2 = TIM8 (PC6-8, PA7, PB14, PB15), CURR4-6 PC5/PA6/PA5, SENS4-6 PC3/PC2/PC1, halls PB4/PB6/PB7, nSCS PD2, EN PD4, nFAULT PD3. Shared DRV SPI (bit-bang): SCK PC10, MISO PC11, MOSI PC12', 20, 40, 1.8)
st = {'PE9': 'hier:M1_INHA', 'PE8': 'hier:M1_INLA', 'PE11': 'hier:M1_INHB', 'PE10': 'hier:M1_INLB', 'PE13': 'hier:M1_INHC', 'PE12': 'hier:M1_INLC',
      'PC6': 'hier:M2_INHA', 'PA7': 'hier:M2_INLA', 'PC7': 'hier:M2_INHB', 'PB14': 'hier:M2_INLB', 'PC8': 'hier:M2_INHC', 'PB15': 'hier:M2_INLC',
      'PE14': 'M1_EN_MCU', 'PD4': 'M2_EN_MCU', 'PE3': 'hier:M1_nFAULT', 'PD3': 'hier:M2_nFAULT',
      'PC10': 'hier:DRV_SCLK', 'PC11': 'hier:DRV_SDO', 'PC12': 'hier:DRV_SDI', 'PC13': 'hier:M1_nSCS', 'PD2': 'hier:M2_nSCS',
      'PB1': 'hier:M1_SOA', 'PB0': 'hier:M1_SOB', 'PC4': 'hier:M1_SOC', 'PC5': 'hier:M2_SOA', 'PA6': 'hier:M2_SOB', 'PA5': 'hier:M2_SOC',
      'PA2': 'hier:M1_SENS_A', 'PA0': 'hier:M1_SENS_B', 'PA1': 'hier:M1_SENS_C', 'PC3': 'hier:M2_SENS_A', 'PC2': 'hier:M2_SENS_B', 'PC1': 'hier:M2_SENS_C',
      'PC0': 'VIN_SENS', 'PA3': 'VIN_SENS', 'PA4': 'ADC_MUX', 'PB12': 'MUX_EN_N', 'PD7': 'MUX_S0', 'PB3': 'MUX_S1', 'PE7': 'MUX_S2',
      'PD13': 'hier:M1_HALL1', 'PD12': 'hier:M1_HALL2', 'PD14': 'hier:M1_HALL3', 'PB4': 'hier:M2_HALL1', 'PB6': 'hier:M2_HALL2', 'PB7': 'hier:M2_HALL3',
      'PE15': 'ESTOP_OK', 'PD0': 'CAN_RX', 'PD1': 'CAN_TX', 'PB10': 'UART_TX', 'PB11': 'UART_RX', 'PC9': 'LED_G', 'PA8': 'LED_R',
      'PA13': 'SWDIO', 'PA14': 'SWCLK', 'NRST': 'hier:NRST', 'BOOT0': 'BOOT0', 'PH0': 'OSC_IN', 'PH1': 'OSC_OUT',
      'VCAP_1': 'VCAP1', 'VCAP_2': 'VCAP2', 'VBAT': '+3V3_ESC', 'VDDA': 'VDDA_ESC', 'VREF+': 'VDDA_ESC', 'VSSA': 'GND'}
for n in ('11', '19', '28', '50', '75', '100'): st[n] = '+3V3_ESC'
for n in ('10', '27', '74', '99'): st[n] = 'GND'
add('U701', 'MCU_ST_STM32F4:STM32F405VGTx', 'STM32F405VGT6', 'Package_QFP:LQFP-100_14x14mm_P0.5mm', 170, 210, st)
x = 30
for ref, val, net in [('C701', '100nF', '+3V3_ESC'), ('C702', '100nF', '+3V3_ESC'), ('C703', '100nF', '+3V3_ESC'), ('C704', '100nF', '+3V3_ESC'), ('C705', '100nF', '+3V3_ESC'),
                      ('C706', '100nF', '+3V3_ESC'), ('C707', '100nF', '+3V3_ESC'), ('C709', '100nF', 'VDDA_ESC'), ('C710', '1uF', 'VDDA_ESC'),
                      ('C711', '2.2uF', 'VCAP1'), ('C712', '2.2uF', 'VCAP2')]:
    c(ref, val, x, 70, net, 'GND'); x += 12
c('C708', '4.7uF', x, 70, '+3V3_ESC', 'GND', C08)
add('FB701', 'Device:FerriteBead', '600R@100MHz', 'Inductor_SMD:L_0603_1608Metric', 190, 70, {'1': '+3V3_ESC', '2': 'VDDA_ESC'})
add('#FLG701', 'power:PWR_FLAG', 'PWR_FLAG', '', 205, 70, {'1': 'VDDA_ESC'})
m.text('Decoupling: 100 nF at each of the 6 VDD pins + VBAT, 4.7 uF bulk; VDDA/VREF+ via ferrite; VCAP 2.2 uF each', 30, 58, 1.5)
add('Y701', 'Device:Crystal_GND24', '8MHz CL12pF', 'Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm', 60, 130, {'1': 'OSC_IN', '3': 'OSC_OUT', '2': 'GND', '4': 'GND'})
c('C713', '18pF', 40, 140, 'OSC_IN', 'GND'); c('C714', '18pF', 80, 140, 'OSC_OUT', 'GND')
c('C715', '100nF', 40, 170, 'hier:NRST', 'GND')
r('R701', '10k', 30, 195, 'BOOT0', 'GND')
add('J702', 'Connector_Generic:Conn_01x02', 'BOOT', 'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical', 45, 195, {'1': 'BOOT0', '2': '+3V3_ESC'})
add('J701', 'Connector_Generic:Conn_01x05', 'SWD', 'Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical', 45, 230, {'1': '+3V3_ESC', '2': 'SWDIO', '3': 'SWCLK', '4': 'hier:NRST', '5': 'GND'})
r('R702', '1k', 30, 275, 'LED_G', 'LED_G_A'); add('LED701', 'Device:LED', 'LED_GRN', 'LED_SMD:LED_0603_1608Metric', 48, 285, {'1': 'GND', '2': 'LED_G_A'})
r('R703', '1k', 70, 275, 'LED_R', 'LED_R_A'); add('LED702', 'Device:LED', 'LED_RED', 'LED_SMD:LED_0603_1608Metric', 88, 285, {'1': 'GND', '2': 'LED_R_A'})
# E-stop gates
m.text('HARDWARE E-STOP GATE (category 1 stop): Mx_ENABLE = MCU enable AND DRV_EN_DLY. E-stop -> PE15 (ESTOP_OK, immediate): firmware brakes; ~1.7 s later DRV_EN_DLY drops => all gates off (coast).', 280, 58, 2, True)
m.globals.add('DRV_EN_DLY')
for k, (u, rr, cc, y) in enumerate((('U702', 'R704', 'C716', 80), ('U703', 'R705', 'C717', 110)), 1):
    add(u, '74xGxx:74LVC1G08', '74LVC1G08', 'Package_TO_SOT_SMD:SOT-23-5', 310, y, {'1': f'M{k}_EN_MCU', '2': 'DRV_EN_DLY', '4': f'hier:M{k}_ENABLE', '5': '+3V3_ESC', '3': 'GND'})
    r(rr, '10k', 285, y + 12, f'M{k}_EN_MCU', 'GND'); c(cc, '100nF', 340, y, '+3V3_ESC', 'GND')
r('R706', '100k', 285, 140, 'hier:+3V3_DRV_EN', 'GND')
# delayed cut: off delay = (R709 + R706) x C724 x ln(3.3 / VT-) ~ 1.7 s, on delay ~1 s (C724 10 uF X5R derated ~7.5 uF at 3.3 V)
r('R709', '150k', 300, 310, 'hier:+3V3_DRV_EN', 'DRV_DLY_RC'); c('C724', '10uF', 315, 320, 'DRV_DLY_RC', 'GND', C08)
add('U707', '74xGxx:74LVC1G17', '74LVC1G17', 'Package_TO_SOT_SMD:SOT-23-5', 335, 310, {'2': 'DRV_DLY_RC', '4': 'DRV_EN_DLY', '5': '+3V3_ESC', '3': 'GND'}, nc=['1'])
c('C725', '100nF', 350, 300, '+3V3_ESC', 'GND')
r('R710', '1k', 300, 330, 'hier:+3V3_DRV_EN', 'ESTOP_OK')
# temp / aux mux (ADC_IND_ADC_MUX): S2 S1 S0 = PE7 PB3 PD7, /E = PB12
m.text('ADC MUX (Stormcore ADC_SW): 000 MOS1, 001 MOS2, 010 MOT1, 011 MOT2, 100 EXT2, 101 EXT1, 110 EXT3, 111 V_BATT', 280, 165, 2, True)
add('U706', '74xx:74HC4051', '74HC4051', 'Package_SO:TSSOP-16_4.4x5mm_P0.65mm', 320, 200,
    {'VCC': '+3V3_ESC', 'VEE': 'GND', 'GND': 'GND', '~{E}': 'MUX_EN_N', 'S0': 'MUX_S0', 'S1': 'MUX_S1', 'S2': 'MUX_S2', 'A': 'ADC_MUX',
     'A0': 'hier:M1_TEMP_MOS', 'A1': 'hier:M2_TEMP_MOS', 'A2': 'hier:M1_TEMP_MOT', 'A3': 'hier:M2_TEMP_MOT', 'A4': 'GND', 'A5': 'GND', 'A6': 'GND', 'A7': 'VIN_SENS'})
c('C723', '100nF', 350, 185, '+3V3_ESC', 'GND')
# VBUS sense
r('R707', '39k', 300, 250, 'VBUS', 'VIN_SENS', R08); r('R708', '2.2k', 300, 266, 'VIN_SENS', 'GND'); c('C722', '100nF', 312, 266, 'VIN_SENS', 'GND')
m.text('VIN_SENS 39k/2.2k: 42 V -> 2.2 V. Feeds PC0 (VIN), PA3 (VM) and mux ch7 (V_BATT).', 280, 280, 1.4)
# 3V3 LDO, CAN, UART
m.text('3V3_ESC SUPPLY', 400, 58, 2.5, True)
add('U705', 'Regulator_Linear:AP2112K-3.3', 'AP2112K-3.3', 'Package_TO_SOT_SMD:SOT-23-5', 430, 80, {'VIN': '+5V', 'EN': '+5V', 'GND': 'GND', 'VOUT': '+3V3_ESC'}, nc=['4'])
c('C720', '1uF', 400, 85, '+5V', 'GND'); c('C721', '10uF', 462, 85, '+3V3_ESC', 'GND', C08)
m.text('CAN TO ESP32 (one node, both motors: CAN IDs per motor in VESC Tool)', 400, 120, 2.5, True)
add('U704', 'Interface_CAN_LIN:CA-IF1042LVS', 'TCAN1042V', 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm', 430, 150,
    {'TXD': 'CAN_TX', 'RXD': 'CAN_RX', 'VIO': '+3V3_ESC', 'VCC': '+5V', 'GND': 'GND', 'STB': 'GND', 'CANH': 'hier:CAN_H', 'CANL': 'hier:CAN_L'})
c('C718', '100nF', 460, 135, '+5V', 'GND'); c('C719', '100nF', 400, 135, '+3V3_ESC', 'GND')
add('J703', 'Connector_Generic:Conn_01x04', 'UART', 'Connector_JST:JST_PH_B4B-PH-K_1x04_P2.00mm_Vertical', 430, 200, {'1': '+5V', '2': 'UART_TX', '3': 'UART_RX', '4': 'GND'})
m.check(autonc=['U701'])
open(f'{P}/ESC_MCU.kicad_sch', 'w').write(m.render([(f'/{ROOT}/{SM}', 0)]))
print('mcu parts', len(m.parts))

# ======================= ESP32 sheet: one ESC reset =======================
t = open(f'{P}/MCU.kicad_sch').read()
t = t.replace('(hierarchical_label "ESC1_NRST"', '(hierarchical_label "ESC_NRST"')
for s, e, h in sx.spans(t, 1):
    if h == 'hierarchical_label' and t[s:e].startswith('(hierarchical_label "ESC2_NRST"'):
        x, y = re.search(r'\(at ([-\d.]+) ([-\d.]+)', t[s:e]).groups()
        t = t[:s] + f'(no_connect (at {x} {y}) (uuid "{uid("nc", "esp", x, y)}"))' + t[e:]; break
open(f'{P}/MCU.kicad_sch', 'w').write(t)

# ======================= root =======================
t = open(f'{P}/abx-motion-brushless.kicad_sch').read().replace('(paper "A4")', '(paper "A3")', 1)
def cut(t, s, e):
    j = s
    while t[j - 1] in ' \t': j -= 1
    if t[j - 1] == '\n': j -= 1
    return t[:j] + t[e:]
pages = {}
for s, e, h in sorted(sx.spans(t, 1), reverse=True):
    if h == 'sheet' and sx.prop(t[s:e], 'Sheetfile') == 'ESC_Channel.kicad_sch':
        pages[sx.prop(t[s:e], 'Sheetname')] = re.search(r'\(page "(\d+)"\)', t[s:e]).group(1); t = cut(t, s, e)
# MCU block: ESC1_NRST -> ESC_NRST, drop ESC2_NRST
for s, e, h in sx.spans(t, 1):
    if h == 'sheet' and sx.prop(t[s:e], 'Sheetname') == 'MCU_and_Encoders':
        b = t[s:e].replace('(pin "ESC1_NRST"', '(pin "ESC_NRST"')
        for ps, pe, ph in sorted(sx.spans(b, 1), reverse=True):
            if ph == 'pin' and b[ps:pe].startswith('(pin "ESC2_NRST"'): b = cut(b, ps, pe)
        t = t[:s] + b + t[e:]; break
def block(name, file, bu, x, y, w, h, pins, page):
    ps = ''.join(f'\t\t(pin "{n}" {ty}\n\t\t\t(at {px:g} {py:g} {a})\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(justify {"left" if a == 180 else "right"})\n\t\t\t)\n\t\t\t(uuid "{uid("spin", name, n)}")\n\t\t)\n' for n, ty, px, py, a in pins)
    return f'''\t(sheet
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
\t\t(uuid "{bu}")
\t\t(property "Sheetname" "{name}"
\t\t\t(at {x:g} {y - 1.27:g} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(justify left bottom)
\t\t\t)
\t\t)
\t\t(property "Sheetfile" "{file}"
\t\t\t(at {x:g} {y + h + 0.6:g} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(justify left top)
\t\t\t)
\t\t)
{ps}\t\t(instances
\t\t\t(project "abx-motion-brushless"
\t\t\t\t(path "/{ROOT}"
\t\t\t\t\t(page "{page}")
\t\t\t\t)
\t\t\t)
\t\t)
\t)
'''
PW = PIN_IN + PIN_OUT
blks = ''
for name, bu, y0 in (('ESC_Motor_1', S1, 127.0), ('ESC_Motor_2', S2, 200.66)):
    pins = [(n, 'input' if n in PIN_IN else 'output', 60.96, y0 + 5.08 + 2.54 * i, 0) for i, n in enumerate(PW)]
    blks += block(name, 'ESC_Channel.kicad_sch', bu, 20.32, y0, 40.64, 2.54 * len(PW) + 7.62, pins, pages[name])
mp = []
yy = 132.08
for k in (1, 2):
    for n in MOT: mp.append((f'M{k}_{n}', m.hier_shapes[f'M{k}_{n}'], 124.46, yy, 180)); yy += 2.54
    yy += 2.54
for i, n in enumerate(['DRV_SCLK', 'DRV_SDI', 'DRV_SDO', 'CAN_H', 'CAN_L', 'NRST', '+3V3_DRV_EN']):
    mp.append((n, m.hier_shapes.get(n, 'bidirectional'), 175.26, 132.08 + 2.54 * i, 0))
blks += block('ESC_MCU', 'ESC_MCU.kicad_sch', SM, 124.46, 127.0, 50.8, yy - 127.0 + 2.54, mp, '12')
i = t.index('\t(sheet_instances'); t = t[:i] + blks + t[i:]
# regenerate stubs for every sheet pin
for s, e in sorted([(s, e) for s, e, h in sx.spans(t, 1) if h in ('wire', 'label')], reverse=True): t = cut(t, s, e)
add = []
for s, e, h in sx.spans(t, 1):
    if h != 'sheet': continue
    sname = sx.prop(t[s:e], 'Sheetname')
    for name, x, y, a in re.findall(r'\(pin "([^"]+)" \w+\s*\(at ([\d.]+) ([\d.]+) (\d+)\)', t[s:e]):
        lab = name
        if sname.startswith('ESC_Motor_'): lab = 'DRV_' + name if name in ('SCLK', 'SDI', 'SDO') else f'M{sname[-1]}_{name}'
        if sname == 'ESC_MCU' and name == 'NRST': lab = 'ESC_NRST'
        x = float(x); y = float(y); a = int(a); x2 = x + 7.62 if a == 0 else x - 7.62; j = 'left' if a == 0 else 'right'
        add.append(f'\t(wire (pts (xy {x:g} {y:g}) (xy {x2:g} {y:g})) (stroke (width 0) (type default)) (uuid "{uid("w", sname, name)}"))\n\t(label "{lab}" (at {x2:g} {y:g} {a}) (fields_autoplaced yes) (effects (font (size 1.27 1.27)) (justify {j} bottom)) (uuid "{uid("l", sname, name)}"))\n')
i = t.index('(sheet\n'); i = t.rfind('\n', 0, i) + 1
open(f'{P}/abx-motion-brushless.kicad_sch', 'w').write(t[:i] + ''.join(add) + t[i:])
# project: +3V3_ESC is now a global net
pr = open(f'{P}/abx-motion-brushless.kicad_pro').read().replace('"/ESC_Motor_*/+3V3_ESC"', '"+3V3_ESC"')
open(f'{P}/abx-motion-brushless.kicad_pro', 'w').write(pr)
print('root ok, ESC_MCU block', SM, 'pages', pages)
