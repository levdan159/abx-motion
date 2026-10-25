"""Hand-written floorplan intent for the 2026-10-25 placement (requirements, not an emit of the board).
usage: mkintent.py <board.kicad_pcb> <out.json> [copy]"""
import json
import sys
import pcbnew

b = pcbnew.LoadBoard(sys.argv[1]); copy = len(sys.argv) > 3
refs = sorted(f.GetReference() for f in b.GetFootprints())
G = {   # name: (refs, zone, why)
    'u1_buck': ('U1 D3 C6 C4 C3 C2 R12 R13 R10 R4 R5 C12 R11 C11 L1 C7 C8', [64.5, 83.0, 100.5, 102.0],
                '5 V buck TPS54360B (SNVSB93 fig. 52) in the left logic column next to the old U1 spot'),
    'aux5': ('U901 D902 C905 C903 C902 C901 R907 R908 R903 R901 R902 C911 R904 C904 L901 C906 C907 C908 U902 C909 R905 '
             'C910 D901 R906 J511', [45.0, 124.0, 101.0, 146.0], '+5V_AUX buck + eFuse + TVS + J511 (left edge)'),
    'precharge': ('R830 R831', [160.0, 82.0, 180.0, 99.0], 'precharge string by R803/R804/Q803'),
    'sequencer': ('U802 C811 Q804 D801 R819 R820 C807 R821 R822 C808 R823 R824 R825 R826 R827 C809 R828 R829 C810',
                  [200.0, 55.5, 214.0, 85.8], 'LM339 breaker sequencer right of U801, above the VBAT_IN pour'),
    'vbus_sense': ('R711 R712', [98.0, 88.0, 123.0, 112.0], 'USB VBUS divider into PA9'),
    'imu': ('U711 C726 C727 R713 R714', [118.0, 92.0, 158.0, 123.0], 'IMU on I2C1 in the STM32 strip, off the power stages'),
    'io_header': ('J704 U708 U709 U710 F701 C728 R715 R716 R717 R718 R719 R720', [90.0, 48.0, 122.0, 67.0],
                  'I/O header on the top edge with ESD + series resistors'),
}
if copy:
    G['usb'] = ('J201 U201 R201 R202 F2 D202', [70.0, 48.0, 94.0, 66.0], 'USB-C on the top edge (owner decision pending)')
blocks = [{'name': n, 'refs': r.split(), 'zone': z, 'side': 'F', 'why': w} for n, (r, z, w) in G.items()]
mine = {r for n, (rr, z, w) in G.items() for r in rr.split()}
imu = set(G['imu'][0].split())
# keep-outs: the power stages and the switcher blocks, for the IMU group only (everything else allowed)
allow = [r for r in refs if r not in imu]
K = [('esc1_power', [100.0, 47.9, 190.0, 78.0], 'ESC1 FETs, shunts, phase pours'),
     ('esc2_power', [100.0, 136.0, 170.0, 166.1], 'ESC2 FETs, shunts, phase pours'),
     ('buck24', [160.0, 105.0, 206.0, 140.0], 'LM70880 24 V buck, L520'),
     ('bucks5', [44.9, 83.0, 101.0, 146.0], 'TPS54360B 5 V bucks U1 / U901'),
     ('breaker', [165.0, 47.9, 214.1, 105.0], 'bus breaker FETs, shunt, precharge')]
keepouts = [{'name': n, 'rect': r, 'sides': ['F'], 'allow': allow, 'why': w} for n, r, w in K]
P = lambda ref, near, pads, mm, why: {'ref': ref, 'near': near, 'pads': pads, 'max_mm': mm, 'basis': 'pad_edge', 'why': why}
prox = [P('C726', 'U711', {'C726': ['1'], 'U711': ['5']}, 2.0, 'VDDIO decap at pin 5'),
        P('C727', 'U711', {'C727': ['1'], 'U711': ['8']}, 2.0, 'VDD decap at pin 8'),
        P('R713', 'U711', {'R713': ['2'], 'U711': ['13']}, 5.0, 'SCL pull-up by the IMU'),
        P('R714', 'U711', {'R714': ['2'], 'U711': ['14']}, 5.0, 'SDA pull-up by the IMU'),
        P('U711', 'U701', {'U711': ['13', '14'], 'U701': ['95', '96']}, 25.0, 'IMU on I2C1 (PB8/PB9): in the STM32 strip'),
        P('C811', 'U802', {'C811': ['1'], 'U802': ['3']}, 4.0, 'LM339 VCC decap at pin 3 (3rd pin of the row: above the package)'),
        P('U802', 'U801', {'U802': ['9'], 'U801': ['1']}, 15.0, 'sequencer by the TPS48111 (UVLO / INP / INPG)'),
        P('R830', 'R803', {'R830': ['1'], 'R803': ['2']}, 3.0, 'precharge string: PRE_M'),
        P('R831', 'R830', {'R831': ['1'], 'R830': ['2']}, 3.0, 'precharge string: PRE_M2'),
        P('R831', 'R804', {'R831': ['2'], 'R804': ['1']}, 12.0, 'precharge string: PRE_M3'),
        P('C909', 'U902', {'C909': ['1'], 'U902': ['4', '6']}, 2.0, 'eFuse input cap at IN'),
        P('C910', 'U902', {'C910': ['1'], 'U902': ['1']}, 3.0, 'eFuse output cap at OUT'),
        P('R905', 'U902', {'R905': ['1'], 'U902': ['2']}, 2.0, 'ILIM resistor at pin 2'),
        P('D901', 'J511', {'D901': ['1'], 'J511': ['1']}, 6.0, 'TVS at the output terminal (J511 body is 5.5 mm deep)'),
        P('U708', 'J704', {'U708': ['1', '3'], 'J704': ['2', '3']}, 6.0, 'ESD array at its header pins'),
        P('U709', 'J704', {'U709': ['1', '3'], 'J704': ['4', '5']}, 6.0, 'ESD array at its header pins'),
        P('U710', 'J704', {'U710': ['1', '3'], 'J704': ['6', '7']}, 6.0, 'ESD array at its header pins'),
        P('C728', 'J704', {'C728': ['1'], 'J704': ['1']}, 6.0, '+3V3_HDR cap at the header'),
        P('R712', 'U701', {'R712': ['1'], 'U701': ['68']}, 16.0, 'VBUS divider into PA9 (the pin side of U701 is full)'),
        P('R711', 'R712', {'R711': ['2'], 'R712': ['1']}, 2.0, 'divider pair together')]
if copy:
    prox += [P('U201', 'J201', {'U201': ['1', '3'], 'J201': ['A7', 'A6']}, 5.0, 'USB ESD at the receptacle')]
qn = '/ESC_MCU/OSC_IN,/ESC_MCU/OSC_OUT,/ESC_MCU/I2C1_SCL,/ESC_MCU/I2C1_SDA,/ESC_MCU/USB_DP,/ESC_MCU/USB_DM'
keep_away = [{'rule': f'/Power_Supply/U1_SW:{qn}:3', 'why': '5 V buck switch node away from clock / I2C / USB'},
             {'rule': f'/Power_Supply/U901_SW:{qn}:3', 'why': '+5V_AUX buck switch node away from clock / I2C / USB'}]
edge = [{'ref': 'J511', 'edge': 'west', 'overhang_mm': {'min': 0.0, 'max': 0.6}, 'why': '+5V_AUX output terminal, wire entry out'},
        {'ref': 'J704', 'edge': 'north', 'overhang_mm': {'min': 0.0, 'max': 0.6}, 'why': 'I/O header'},
        {'ref': 'J201', 'edge': 'north' if copy else 'west', 'overhang_mm': {'min': 0.0, 'max': 0.6}, 'why': 'USB-C'},
        {'ref': 'J205', 'edge': 'west', 'overhang_mm': {'min': 0.0, 'max': 0.6}, 'why': 'CAN terminal'}]
caps = [r for r in refs if r.startswith('C')]
decaps = {'max_distance_mm': 4.0, 'exempt': [c for c in caps if c not in ('C726', 'C727', 'C811', 'C909', 'C910', 'C728')]}
doc = {'schema': 1, 'kind': 'floorplan-intent', 'board': sys.argv[1].rsplit('/', 1)[-1], 'units': 'mm', 'min_reader': 12,
       'envelope': {'rect': [45.0, 48.0, 214.0, 166.0], 'tolerance_mm': 0.5}, 'defaults': {'zone_tolerance_mm': 0.5},
       'assembly': {'sides': 'F', 'why': 'single-sided SMT, as the board'}, 'blocks': blocks, 'keepouts': keepouts,
       'proximity': prox, 'keep_away': keep_away, 'edge_connectors': edge, 'decaps': decaps, 'severity': {},
       'dispositions': {'rules': {'legality': 'graded by check_assembly + KiCad DRC on this already-routed board',
                                  'decap_pin_distance': 'the new decaps are held by proximity rows (C726 C727 C811 C909 C910 C728); the rails of the parts placed before are outside this placement'}},
       'context': {'note': 'written by hand for the 2026-10-25 placement of the staged parts; the power stage, buck '
                           'U511 (buckplace.py) and every part placed before are outside these blocks and not graded here'}}
json.dump(doc, open(sys.argv[2], 'w'), indent=1)
print('intent', sys.argv[2], len(blocks), 'blocks', len(prox), 'proximity')
