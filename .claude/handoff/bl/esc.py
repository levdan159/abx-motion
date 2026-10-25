import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from schgen import Sheet
ROOT = 'f9149098-3f23-438d-bdc2-2e278b5ca35b'
S1 = '68e0475f-9c75-41f9-88c7-a3831640edb7'      # ESC_Motor_1 sheet block uuid in the root
S2 = '9d5b7c3e-2a41-4f6e-8b0c-5e7d1a2c4f90'      # ESC_Motor_2
sh = Sheet(paper='A2')
sh.hier_shapes['+3V3_DRV_EN'] = 'input'
add = sh.add
R06, R08, R12 = 'Resistor_SMD:R_0603_1608Metric', 'Resistor_SMD:R_0805_2012Metric', 'Resistor_SMD:R_2512_6332Metric'
C06, C08, C12 = 'Capacitor_SMD:C_0603_1608Metric', 'Capacitor_SMD:C_0805_2012Metric', 'Capacitor_SMD:C_1210_3225Metric'
def r(ref, val, x, y, n1, n2, fp=R06): add(ref, 'Device:R', val, fp, x, y, {'1': n1, '2': n2})
def c(ref, val, x, y, n1, n2, fp=C06): add(ref, 'Device:C', val, fp, x, y, {'1': n1, '2': n2})

# ---------------- titles
sh.text('ESC CHANNEL - one brushless motor (36 V 10S pack, 30 A peak). STM32F405 + DRV8323S, VESC-firmware compatible pinout (hw_hd60 style)', 20, 20, 3.5, True)
sh.text('Instanced twice in the root: ESC_Motor_1 (refs 3xx) and ESC_Motor_2 (refs 4xx). VBUS = battery bus after the main connector (no fuse/TVS here: see notes).', 20, 28, 1.8)
sh.text('MCU: STM32F405RGT6', 20, 105, 2.5, True)
sh.text('GATE DRIVER: DRV8323S (SPI mode, 3 CSAs)', 190, 95, 2.5, True)
sh.text('POWER STAGE: 3 half-bridges, CSD19532Q5B 100 V, 1 mOhm shunts (route SPx/GND as Kelvin pair to the DRV8323S)', 335, 95, 2.5, True)
sh.text('SENSING: phase voltages, VBUS, PCB NTC, motor NTC', 290, 280, 2.5, True)
sh.text('3V3 SUPPLY + HARDWARE E-STOP GATE (ENABLE = MCU AND +3V3_DRV_EN)', 140, 322, 2.5, True)
sh.text('CAN TO ESP32 (internal bus)', 335, 322, 2.5, True)
sh.text('MOTOR INTERFACE', 430, 322, 2.5, True)
sh.text('NOTES: (1) DRV8323S VM abs max 65 V, recommended 60 V. Do not add a TVS clamping above ~65 V on VBUS. (2) R310-R315 are slew-rate trim (2.2 R). (3) SPx/SNx = Kelvin sense pair from each shunt. (4) Firmware: copy hwconf/trampa/hd/hw_hd60.h, set CURRENT_SHUNT_RES 0.001, V limits 8..48.', 20, 405, 1.5)

# ---------------- STM32
st = {'PA8': 'INHA', 'PA9': 'INHB', 'PA10': 'INHC', 'PB13': 'INLA', 'PB14': 'INLB', 'PB15': 'INLC',
      'PC9': 'DRV_nSCS', 'PC12': 'DRV_SDI', 'PB4': 'DRV_SCLK', 'PB3': 'DRV_SDO', 'PB5': 'ENABLE_MCU', 'PB7': 'nFAULT',
      'PC0': 'SOA', 'PC1': 'SOB', 'PC2': 'SOC', 'PC3': 'VIN_SENS', 'PA0': 'SENS_A', 'PA1': 'SENS_B', 'PA2': 'SENS_C',
      'PA3': 'TEMP_PCB', 'PC4': 'TEMP_MOT', 'PC6': 'HALL1', 'PC7': 'HALL2', 'PC8': 'HALL3', 'PB8': 'CAN_RX', 'PB9': 'CAN_TX',
      'PB10': 'UART_TX', 'PB11': 'UART_RX', 'PA4': 'ENC_CS', 'PA5': 'ENC_SCK', 'PA6': 'ENC_MISO', 'PA7': 'ENC_MOSI',
      'PB0': 'LED_G', 'PB1': 'LED_R', 'PA13': 'SWDIO', 'PA14': 'SWCLK', 'NRST': 'NRST', 'BOOT0': 'BOOT0',
      'PH0': 'OSC_IN', 'PH1': 'OSC_OUT', 'VCAP_1': 'VCAP1', 'VCAP_2': 'VCAP2',
      '1': '+3V3_ESC', '13': 'VDDA_ESC', '19': '+3V3_ESC', '32': '+3V3_ESC', '48': '+3V3_ESC', '64': '+3V3_ESC',
      '12': 'GND', '18': 'GND', '63': 'GND'}
add('U301', 'MCU_ST_STM32F4:STM32F405RGTx', 'STM32F405RGT6', 'Package_QFP:LQFP-64_10x10mm_P0.5mm', 120, 215, st)
# decoupling row
x = 30
for ref, val, net in [('C301', '100nF', 'NRST'), ('C302', '100nF', '+3V3_ESC'), ('C303', '100nF', '+3V3_ESC'), ('C304', '100nF', '+3V3_ESC'),
                      ('C305', '100nF', '+3V3_ESC'), ('C306', '100nF', '+3V3_ESC'), ('C307', '100nF', 'VDDA_ESC'), ('C308', '1uF', 'VDDA_ESC'),
                      ('C309', '2.2uF', 'VCAP1'), ('C310', '2.2uF', 'VCAP2')]:
    c(ref, val, x, 125, net, 'GND'); x += 12
add('FB301', 'Device:FerriteBead', '600R@100MHz', 'Inductor_SMD:L_0603_1608Metric', 160, 125, {'1': '+3V3_ESC', '2': 'VDDA_ESC'})
add('#FLG301', 'power:PWR_FLAG', 'PWR_FLAG', '', 175, 125, {'1': 'VDDA_ESC'})
sh.text('Decoupling: one 100 nF per VDD pin (19/32/48/64) + VBAT; VDDA via ferrite; place at pins', 30, 112, 1.5)
add('Y301', 'Device:Crystal_GND24', '8MHz CL12pF', 'Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm', 60, 170, {'1': 'OSC_IN', '3': 'OSC_OUT', '2': 'GND', '4': 'GND'})
c('C311', '18pF', 40, 180, 'OSC_IN', 'GND'); c('C312', '18pF', 80, 180, 'OSC_OUT', 'GND')
r('R332', '10k', 30, 205, 'BOOT0', 'GND')
add('J308', 'Connector_Generic:Conn_01x02', 'BOOT', 'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical', 45, 205, {'1': 'BOOT0', '2': '+3V3_ESC'})
add('J307', 'Connector_Generic:Conn_01x05', 'SWD', 'Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical', 45, 240, {'1': '+3V3_ESC', '2': 'SWDIO', '3': 'SWCLK', '4': 'NRST', '5': 'GND'})
r('R333', '1k', 30, 285, 'LED_G', 'LED_G_A'); add('LED301', 'Device:LED', 'LED_GRN', 'LED_SMD:LED_0603_1608Metric', 48, 295, {'1': 'GND', '2': 'LED_G_A'})
r('R334', '1k', 70, 285, 'LED_R', 'LED_R_A'); add('LED302', 'Device:LED', 'LED_RED', 'LED_SMD:LED_0603_1608Metric', 88, 295, {'1': 'GND', '2': 'LED_R_A'})

# ---------------- DRV8323S
drv = {'ENABLE': 'ENABLE', 'INHA': 'INHA', 'INLA': 'INLA', 'INHB': 'INHB', 'INLB': 'INLB', 'INHC': 'INHC', 'INLC': 'INLC',
       'nSCS': 'DRV_nSCS', 'SCLK': 'DRV_SCLK', 'SDI': 'DRV_SDI', 'SDO': 'DRV_SDO', 'CAL': 'CAL', 'nFAULT': 'nFAULT',
       'GHA': 'GHA', 'SHA': 'PH_A', 'GLA': 'GLA', 'SPA': 'SPA', 'SNA': 'GND', 'GHB': 'GHB', 'SHB': 'PH_B', 'GLB': 'GLB', 'SPB': 'SPB', 'SNB': 'GND',
       'GHC': 'GHC', 'SHC': 'PH_C', 'GLC': 'GLC', 'SPC': 'SPC', 'SNC': 'GND', 'SOA': 'SOA', 'SOB': 'SOB', 'SOC': 'SOC',
       'CPL': 'CPL', 'CPH': 'CPH', 'VCP': 'VCP', 'VM': 'VBUS', 'VDRAIN': 'VBUS', 'AGND': 'GND', 'PGND': 'GND', 'DVDD': 'DVDD', 'VREF': '+3V3_ESC', 'PAD': 'GND'}
add('U302', 'abx:DRV8323SRTAR', 'DRV8323SRTAR', 'Package_DFN_QFN:Texas_RHA0040B_VQFN-40-1EP_6x6mm_P0.5mm_EP4.15x4.15mm', 250, 150, drv)
c('C316', '47nF/100V', 200, 110, 'CPH', 'CPL'); c('C317', '1uF/25V', 212, 110, 'VCP', 'VBUS'); c('C318', '1uF', 224, 110, 'DVDD', 'GND')
c('C319', '100nF', 236, 110, '+3V3_ESC', 'GND'); c('C320', '100nF/100V', 248, 110, 'VBUS', 'GND'); c('C321', '10uF/100V', 260, 110, 'VBUS', 'GND', C12)
r('R301', '10k', 276, 110, '+3V3_ESC', 'nFAULT'); r('R302', '10k', 286, 110, '+3V3_ESC', 'DRV_SDO'); r('R303', '10k', 296, 110, '+3V3_ESC', 'DRV_nSCS'); r('R304', '10k', 306, 110, 'GND', 'CAL')
sh.text('VM: 100nF + 10uF within 3 mm of pin 4; CPH-CPL 47nF rated VM; VCP-VM 1uF/25V', 195, 100, 1.4)

# ---------------- power stage
for ph, x0, q_h, q_l, rg_h, rg_l, rs, jn in (('A', 370, 'Q301', 'Q302', 'R310', 'R311', 'R307', 'J301'), ('B', 450, 'Q303', 'Q304', 'R312', 'R313', 'R308', 'J302'), ('C', 530, 'Q305', 'Q306', 'R314', 'R315', 'R309', 'J303')):
    FET, TD = 'Transistor_FET:CSD19532Q5B', 'Package_TO_SOT_SMD:TDSON-8-1'
    add(q_h, FET, 'CSD19532Q5B', TD, x0, 170, {'1': f'PH_{ph}', '2': f'PH_{ph}', '3': f'PH_{ph}', '4': f'GH{ph}_G', '5': 'VBUS'})
    add(q_l, FET, 'CSD19532Q5B', TD, x0, 215, {'1': f'SP{ph}', '2': f'SP{ph}', '3': f'SP{ph}', '4': f'GL{ph}_G', '5': f'PH_{ph}'})
    r(rg_h, '2.2', x0 - 25, 165, f'GH{ph}', f'GH{ph}_G'); r(rg_l, '2.2', x0 - 25, 210, f'GL{ph}', f'GL{ph}_G')
    r(rs, '1m 3W', x0 + 25, 245, f'SP{ph}', 'GND', R12)
    add(jn, 'Connector:Conn_01x01_Pin', f'PHASE_{ph}', 'Connector_Wire:SolderWirePad_1x01_SMD_5x10mm', x0 + 40, 192, {'1': f'PH_{ph}'})
for ref, x0, kind in (('C322', 345, 'c'), ('C323', 360, 'c'), ('C328', 395, 'p'), ('C324', 425, 'c'), ('C325', 440, 'c'), ('C329', 470, 'p'), ('C326', 505, 'c'), ('C327', 520, 'c')):
    if kind == 'c': c(ref, '10uF/100V', x0, 128, 'VBUS', 'GND', C12)
    else: add(ref, 'Device:C_Polarized', '220uF/63V', 'Capacitor_SMD:CP_Elec_10x10.5', x0, 128, {'1': 'VBUS', '2': 'GND'})

# ---------------- sensing
x = 300
for ph, rt, rb, cc in (('A', 'R316', 'R319', 'C330'), ('B', 'R317', 'R320', 'C331'), ('C', 'R318', 'R321', 'C332')):
    r(rt, '39k', x, 292, f'PH_{ph}', f'SENS_{ph}', R08); r(rb, '2.2k', x, 308, f'SENS_{ph}', 'GND'); c(cc, '2.2nF', x + 12, 308, f'SENS_{ph}', 'GND'); x += 30
r('R322', '39k', 395, 292, 'VBUS', 'VIN_SENS', R08); r('R323', '2.2k', 395, 308, 'VIN_SENS', 'GND'); c('C333', '100nF', 407, 308, 'VIN_SENS', 'GND')
add('NT301', 'Device:Thermistor_NTC', 'NTC 10k B3380', R06, 430, 292, {'1': '+3V3_ESC', '2': 'TEMP_PCB'}); r('R324', '10k', 430, 308, 'TEMP_PCB', 'GND')
r('R325', '10k', 455, 292, '+3V3_ESC', 'TEMP_MOT'); c('C334', '10nF', 467, 308, 'TEMP_MOT', 'GND')
sh.text('Divider ratio 18.7:1 (39k/2.2k) as hw_hd60: 42 V -> 2.2 V at the ADC. Place NT301 next to the FETs.', 290, 318, 1.4)

# ---------------- 3V3 + E-stop gate
add('U305', 'Regulator_Linear:AP2112K-3.3', 'AP2112K-3.3', 'Package_TO_SOT_SMD:SOT-23-5', 190, 340, {'VIN': '+5V', 'EN': '+5V', 'GND': 'GND', 'VOUT': '+3V3_ESC'}, nc=['4'])
c('C313', '1uF', 160, 345, '+5V', 'GND'); c('C314', '10uF', 222, 345, '+3V3_ESC', 'GND', C08)
add('U303', '74xGxx:74LVC1G08', '74LVC1G08', 'Package_TO_SOT_SMD:SOT-23-5', 275, 350, {'1': 'ENABLE_MCU', '2': 'hier:+3V3_DRV_EN', '4': 'ENABLE', '5': '+3V3_ESC', '3': 'GND'})
c('C315', '100nF', 305, 340, '+3V3_ESC', 'GND'); r('R305', '10k', 240, 372, 'ENABLE_MCU', 'GND'); r('R306', '100k', 252, 372, 'hier:+3V3_DRV_EN', 'GND')
sh.text('E-stop: +3V3_DRV_EN is 3.3 V only while the E-stop loop is closed. ENABLE low => all gates off (coast). Fail-safe brakes are a separate output (main board).', 140, 395, 1.4)

# ---------------- CAN
add('U304', 'Interface_CAN_LIN:CA-IF1042LVS', 'TCAN1042V', 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm', 360, 355,
    {'TXD': 'CAN_TX', 'RXD': 'CAN_RX', 'VIO': '+3V3_ESC', 'VCC': '+5V', 'GND': 'GND', 'STB': 'GND', 'CANH': 'hier:CAN_H', 'CANL': 'hier:CAN_L'})
c('C338', '100nF', 385, 340, '+5V', 'GND'); c('C339', '100nF', 335, 340, '+3V3_ESC', 'GND')

# ---------------- motor interface
add('J304', 'Connector_Generic:Conn_01x06', 'HALL_TEMP', 'Connector_JST:JST_PH_B6B-PH-K_1x06_P2.00mm_Vertical', 440, 355, {'1': '+5V', '2': 'HALL1_IN', '3': 'HALL2_IN', '4': 'HALL3_IN', '5': 'TEMP_MOT', '6': 'GND'})
for i, (rs_, rp, cc) in enumerate((('R326', 'R329', 'C335'), ('R327', 'R330', 'C336'), ('R328', 'R331', 'C337')), 1):
    xx = 470 + 22 * i
    r(rs_, '1k', xx, 350, f'HALL{i}_IN', f'HALL{i}'); r(rp, '4.7k', xx + 8, 365, '+3V3_ESC', f'HALL{i}'); c(cc, '1nF', xx + 16, 350, f'HALL{i}', 'GND')
add('J305', 'Connector_Generic:Conn_01x06', 'ENC_SPI', 'Connector_JST:JST_PH_B6B-PH-K_1x06_P2.00mm_Vertical', 440, 395, {'1': '+3V3_ESC', '2': 'GND', '3': 'ENC_SCK', '4': 'ENC_MISO', '5': 'ENC_MOSI', '6': 'ENC_CS'})
add('J306', 'Connector_Generic:Conn_01x04', 'UART', 'Connector_JST:JST_PH_B4B-PH-K_1x04_P2.00mm_Vertical', 520, 395, {'1': '+5V', '2': 'UART_TX', '3': 'UART_RX', '4': 'GND'})

sh.check(autonc=['U301'])
paths = [(f'/{ROOT}/{S1}', 0), (f'/{ROOT}/{S2}', 100)]
out = sh.render(paths)
open(f'{os.path.expanduser("~")}/Documents/abx-motion/ESC_Channel.kicad_sch', 'w').write(out)
print('parts', len(sh.parts), 'labels', len(sh.labels), 'hier', len(sh.hier), 'nc', len(sh.ncs), 'bytes', len(out))
