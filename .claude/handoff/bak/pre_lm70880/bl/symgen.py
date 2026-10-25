"""Add TPS48111-Q1, TPS27S100A, MIC2009YM6 to abx-symbols and the TI DGX0019A footprint to abx-footprints."""
import os
P = os.path.expanduser('~/Documents/abx-motion')
E = '(effects (font (size 1.27 1.27)))'
EH = '(effects (font (size 1.27 1.27)) hide)'

def sym(name, desc, fp, ds, kw, left, right, w=10.16):
    """left/right: lists of (number, name, type) top to bottom; None = gap"""
    n = max(len(left), len(right)); h = (n + 1) * 2.54 / 2
    h = round(h / 1.27) * 1.27
    pins = []
    for side, lst in ((-1, left), (1, right)):
        y = h - 2.54
        for p in lst:
            if p is not None:
                num, nm, typ = p
                x = side * (w + 2.54); ang = 0 if side < 0 else 180
                pins.append(f'      (pin {typ} line (at {x:g} {y:g} {ang}) (length 2.54)\n        (name "{nm}" {E})\n        (number "{num}" {E})\n      )')
            y = round(y - 2.54, 2)
    return f'''  (symbol "{name}" (in_bom yes) (on_board yes)
    (property "Reference" "U" (at 0 {h + 1.27:g} 0) {E})
    (property "Value" "{name}" (at 0 {-h - 1.27:g} 0) {E})
    (property "Footprint" "{fp}" (at 0 0 0) {EH})
    (property "Datasheet" "{ds}" (at 0 0 0) {EH})
    (property "Description" "{desc}" (at 0 0 0) {EH})
    (property "ki_keywords" "{kw}" (at 0 0 0) {EH})
    (symbol "{name}_0_1"
      (rectangle (start {-w:g} {h:g}) (end {w:g} {-h:g}) (stroke (width 0.254) (type default)) (fill (type background)))
    )
    (symbol "{name}_1_1"
{chr(10).join(pins)}
    )
  )
'''

S = []
S.append(sym('TPS48111QDGXRQ1', 'TI TPS48111-Q1 100V smart high-side driver: back-to-back FETs, precharge driver (G), ISCP/IWRN protection, IMON, VSSOP-19 (DGX)',
             'abx-footprints:TI_DGX0019A_VSSOP-19_3x5.1mm_P0.5mm', 'https://www.ti.com/lit/gpn/tps4811-q1', 'eFuse circuit breaker high-side driver',
             [('20', 'VS', 'power_in'), ('18', 'CS+', 'input'), ('17', 'CS-', 'input'), ('19', 'ISCP', 'input'), None, ('1', 'EN/UVLO', 'input'),
              ('3', 'INP', 'input'), ('2', 'INP_G', 'input'), None, ('8', 'IWRN', 'passive'), ('9', 'TMR', 'passive'), ('10', 'DIODE', 'passive'), ('6', 'GND', 'power_in')],
             [('12', 'BST', 'passive'), ('15', 'PU', 'output'), ('14', 'PD', 'output'), ('13', 'SRC', 'passive'), ('11', 'G', 'output'), None,
              ('5', 'FLT_I', 'open_collector'), ('4', 'FLT_T', 'open_collector'), ('7', 'IMON', 'output')], w=12.7))
S.append(sym('TPS27S100APWPR', 'TI TPS27S100A 40V 4A protected high-side switch, adjustable current limit, open-drain FLT, HTSSOP-14 PowerPAD',
             'Package_SO:HTSSOP-14-1EP_4.4x5mm_P0.65mm_EP3.4x5mm_Mask3x3.1mm_ThermalVias', 'https://www.ti.com/lit/ds/symlink/tps27s100.pdf', 'high side switch protected',
             [('8', 'IN', 'power_in'), ('9', 'IN', 'passive'), ('10', 'IN', 'passive'), None, ('3', 'EN', 'input'), ('12', 'DIAG_EN', 'input'), ('13', 'ILIM', 'passive'),
              ('2', 'GND', 'power_in'), ('15', 'PAD', 'passive')],
             [('5', 'OUT', 'power_out'), ('6', 'OUT', 'passive'), ('7', 'OUT', 'passive'), None, ('14', 'FLT', 'open_collector'), None,
              ('1', 'NC', 'no_connect'), ('4', 'NC', 'no_connect'), ('11', 'NC', 'no_connect')]))
S.append(sym('MIC2009YM6', 'Microchip MIC2009 2.5-5.5V adjustable current-limit power switch (0.2-2A, RSET=CLF/I, CLF~235), open-drain FAULT/, SOT-23-6',
             'Package_TO_SOT_SMD:SOT-23-6', 'https://ww1.microchip.com/downloads/aemDocuments/documents/APID/ProductDocuments/DataSheets/MIC20XX-Fixed-and-Adjustable-Current-Limiting-Power-Distribution-Switches-DS20006486B.pdf',
             'eFuse power switch current limit', [('1', 'VIN', 'power_in'), ('3', 'EN', 'input'), ('5', 'ILIMIT', 'passive'), ('2', 'GND', 'power_in')],
             [('6', 'VOUT', 'power_out'), ('4', 'FAULT', 'open_collector')], w=7.62))
lib = open(f'{P}/abx-symbols.kicad_sym').read()
for blk in S:
    name = blk.split('"')[1]
    if f'(symbol "{name}"' in lib: continue
    i = lib.rstrip().rfind(')'); lib = lib[:i] + blk + lib[i:]
open(f'{P}/abx-symbols.kicad_sym', 'w').write(lib)

# ---- TI DGX0019A land pattern: 20 positions, pin 16 absent, pads 1.45 x 0.3, pitch 0.5, rows at +-2.2
pads = []
for n in range(1, 21):
    if n == 16: continue
    if n <= 10: x, y = -2.2, -2.25 + (n - 1) * 0.5
    else: x, y = 2.2, 2.25 - (n - 11) * 0.5
    pads.append(f'  (pad "{n}" smd roundrect (at {x:g} {y:g}) (size 1.45 0.3) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.166))')
fp = f'''(footprint "TI_DGX0019A_VSSOP-19_3x5.1mm_P0.5mm"
  (version 20240108)
  (generator "abx-symgen")
  (layer "F.Cu")
  (descr "TI DGX0019A VSSOP-19 (20-pin body, pin 16 removed), 3x5.1 mm, 0.5 mm pitch, per TPS4811-Q1 datasheet land pattern example (pads 1.45x0.3, rows 4.4 mm apart)")
  (tags "VSSOP DGX TPS4811")
  (attr smd)
  (property "Reference" "REF**" (at 0 -3.6 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))
  (property "Value" "TI_DGX0019A" (at 0 3.6 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
  (fp_line (start -1.5 -2.6) (end 1.5 -2.6) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))
  (fp_line (start -1.5 2.6) (end 1.5 2.6) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))
  (fp_circle (center -3.2 -2.6) (end -3.05 -2.6) (stroke (width 0.3) (type solid)) (fill solid) (layer "F.SilkS"))
  (fp_rect (start -1.5 -2.55) (end 1.5 2.55) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))
  (fp_rect (start -3.2 -2.85) (end 3.2 2.85) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
{chr(10).join(pads)}
)
'''
open(f'{P}/abx-footprints.pretty/TI_DGX0019A_VSSOP-19_3x5.1mm_P0.5mm.kicad_mod', 'w').write(fp)
print('symbols + footprint written')
