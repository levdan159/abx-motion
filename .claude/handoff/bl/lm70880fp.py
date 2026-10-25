"""Footprint for the TI LM70880RRXR (RRX0029B VQFN-29, 6x6 mm, three die-attach pads): writes
abx-footprints.pretty/TI_RRX0029B_VQFN-29_6x6mm_P0.5mm_ThermalVias.kicad_mod. Re-runnable (overwrites).
Geometry: TI SNVSCD3 (Sept 2024) section 10, drawing 4228757/D, "Example board layout" + "Example stencil design".
TI draws the land pattern in top view with +y up; KiCad has +y down, so every TI y is negated here.
  - 21 signal pads 0.6 x 0.25 centred at +-2.9 (pins 3-19, 23-26; pin 12 sits 0.037 right of centre, so pads 12/13 are
    only 0.213 apart: both carry a 0.2 mm local clearance, otherwise the Power_HV +24V class (0.25) flags them).
  - VIN die pad (top left in top view) merged with pins 1, 2, 27, 28, 29; SW die pad (top right) merged with pins 20-22:
    custom polygon pads (copper = TI's solder-mask opening outline), numbered 1 / 20, plus finger pads 2, 27-29 / 21, 22
    so every symbol pin has a pad. PGND die pad 30 (3.125 x 1.584, centred x +0.037).
  - Thermal vias 0.6/0.3 (as KiCad's TI PowerPAD ThermalVias footprints): 6 in VIN (to In2 +BATT), 6 in PGND pad 30
    (to In1 GND), at TI's via sites pulled inside the pads by <= 0.05 mm; none in SW (TI shows none: no SW copper on
    inner layers). Paste: TI's stencil apertures as separate paste-only pads.
python lm70880fp.py"""
import os
P = os.path.expanduser('~/Documents/abx-motion')
NAME = 'TI_RRX0029B_VQFN-29_6x6mm_P0.5mm_ThermalVias'
f = lambda v: ('%.4f' % v).rstrip('0').rstrip('.')
o = []
def pad(num, x, y, w, h, extra=''):          # TI (x, y-up) -> KiCad
    o.append(f'  (pad "{num}" smd roundrect (at {f(x)} {f(-y)}) (size {f(w)} {f(h)}) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.2){extra})')
def poly_pad(num, anchor, pts):
    ax, ay = anchor
    xy = ' '.join(f'(xy {f(x - ax)} {f(-(y - ay))})' for x, y in pts)
    o.append(f'  (pad "{num}" smd custom (at {f(ax)} {f(-ay)}) (size 0.25 0.25) (layers "F.Cu" "F.Mask")\n'
             f'    (options (clearance outline) (anchor rect))\n    (primitives (gr_poly (pts {xy}) (width 0) (fill yes))))')
def paste(x0, y0, x1, y1):
    o.append(f'  (pad "" smd roundrect (at {f((x0 + x1) / 2)} {f(-(y0 + y1) / 2)}) (size {f(abs(x1 - x0))} {f(abs(y1 - y0))}) (layers "F.Paste") (roundrect_rratio 0.1))')
def via(num, x, y):
    o.append(f'  (pad "{num}" thru_hole circle (at {f(x)} {f(-y)}) (size 0.6 0.6) (drill 0.3) (property pad_prop_heatsink) (layers "*.Cu"))')

H, V = (0.6, 0.25), (0.25, 0.6)             # pad size for side rows (left/right) and top/bottom rows
# ---- signal pads
pad('3', -2.9, 1.25, *H)
for n, y in (('4', 0.25), ('5', -0.25), ('6', -1.25), ('7', -1.75), ('8', -2.25)): pad(n, -2.9, y, *H)
for n, x in (('9', -2.0), ('10', -1.5), ('11', -1.0)): pad(n, x, -2.9, *V)
pad('12', 0.037, -2.9, *V, ' (clearance 0.2)')
pad('13', 0.5, -2.9, *V, ' (clearance 0.2)')
for n, x in (('14', 1.0), ('15', 1.5), ('16', 2.0)): pad(n, x, -2.9, *V)
for n, y in (('17', -1.75), ('18', -1.25), ('19', -0.75)): pad(n, 2.9, y, *H)
for n, x in (('23', 2.0), ('24', 1.5), ('25', 1.0), ('26', 0.5)): pad(n, x, 2.9, *V)
# ---- VIN die pad + fingers (pins 1, 2 left; 29, 28, 27 top)
VIN = [(-2.55, 2.8), (-2.125, 2.8), (-2.125, 3.2), (-1.875, 3.2), (-1.875, 2.8), (-1.625, 2.8), (-1.625, 3.2), (-1.375, 3.2),
       (-1.375, 2.8), (-1.125, 2.8), (-1.125, 3.2), (-0.875, 3.2), (-0.875, 2.8), (-0.625, 2.8), (-0.625, 0.484), (-2.1, 0.484),
       (-2.1, 0.734), (-2.35, 0.734), (-2.35, 1.625), (-3.2, 1.625), (-3.2, 1.875), (-2.8, 1.875), (-2.8, 2.125), (-3.2, 2.125),
       (-3.2, 2.375), (-2.8, 2.375), (-2.8, 2.55)]
poly_pad('1', (-1.6, 1.6), VIN)
pad('1', -2.9, 2.25, *H); pad('2', -2.9, 1.75, *H)
for n, x in (('29', -2.0), ('28', -1.5), ('27', -1.0)): pad(n, x, 2.9, *V)
# ---- SW die pad + fingers (pins 22, 21, 20 right)
SW = [(-0.14, 2.1), (2.8, 2.1), (2.8, 1.875), (3.2, 1.875), (3.2, 1.625), (2.8, 1.625), (2.8, 1.375), (3.2, 1.375), (3.2, 1.125),
      (2.8, 1.125), (2.8, 0.875), (3.2, 0.875), (3.2, 0.625), (2.8, 0.625), (2.8, 0.14), (-0.14, 0.14)]
poly_pad('20', (1.3, 1.1), SW)
for n, y in (('22', 1.75), ('21', 1.25), ('20', 0.75)): pad(n, 2.9, y, *H)
# ---- PGND die pad 30
o.append(f'  (pad "30" smd roundrect (at 0.037 {f(-(-0.5 - 2.084) / 2)}) (size 3.125 1.584) (layers "F.Cu" "F.Mask") (roundrect_rratio 0.03))')
# ---- thermal vias
for x, y in ((-2.05, 2.5), (-0.925, 2.5), (-2.05, 1.642), (-0.925, 1.642), (-1.8, 0.784), (-0.925, 0.784)): via('1', x, y)
for x in (-1.225, 0.037, 1.3):
    for y in (-0.8, -1.784): via('30', x, y)
# ---- paste apertures (TI stencil, 0.125 mm): VIN 3, SW 2, PGND 2
paste(-2.2, 2.73, -1.25, 1.72); paste(-1.15, 2.73, -0.7, 1.72); paste(-2.2, 1.53, -0.7, 0.54); paste(-2.7, 2.62, -2.4, 1.73)
paste(0.0, 1.95, 1.23, 0.22); paste(1.44, 1.95, 2.69, 0.22)
paste(-1.4, -0.6, -0.06, -2.01); paste(0.15, -0.6, 1.49, -2.01)

g = []
def line(x0, y0, x1, y1, layer, w):
    g.append(f'  (fp_line (start {f(x0)} {f(y0)}) (end {f(x1)} {f(y1)}) (stroke (width {w}) (type solid)) (layer "{layer}"))')
for x0, y0, x1, y1 in ((-2.0, -3.0, 3.0, -3.0), (3.0, -3.0, 3.0, 3.0), (3.0, 3.0, -3.0, 3.0), (-3.0, 3.0, -3.0, -2.0), (-3.0, -2.0, -2.0, -3.0)):
    line(x0, y0, x1, y1, 'F.Fab', 0.1)
for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):      # silk corners, clear of the pads (outermost pad edge 2.375)
    line(sx * 3.11, sy * 3.11, sx * 3.11, sy * 2.75, 'F.SilkS', 0.12)
    line(sx * 3.11, sy * 3.11, sx * 2.75, sy * 3.11, 'F.SilkS', 0.12)
g.append('  (fp_circle (center -3.55 -2.25) (end -3.4 -2.25) (stroke (width 0.3) (type solid)) (fill solid) (layer "F.SilkS"))')
g.append('  (fp_rect (start -3.5 -3.5) (end 3.5 3.5) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))')
txt = f'''(footprint "{NAME}"
  (version 20240108)
  (generator "abx-lm70880fp")
  (layer "F.Cu")
  (descr "TI RRX0029B VQFN-29 6x6 mm, 0.5 mm pitch, three die-attach pads (VIN with pins 1/2/27-29, SW with pins 20-22, PGND pad 30), thermal vias 0.6/0.3 in VIN and PGND, per LM708x0 datasheet SNVSCD3 land pattern and stencil (drawing 4228757/D)")
  (tags "VQFN RRX0029B LM70880 LM70860 LM70840")
  (attr smd)
  (property "Reference" "REF**" (at 0 -4.4 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))
  (property "Value" "{NAME}" (at 0 4.4 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
  (fp_text user "${{REFERENCE}}" (at 0 0 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
{chr(10).join(g)}
{chr(10).join(o)}
  (model "${{KICAD10_3DMODEL_DIR}}/Package_DFN_QFN.3dshapes/QFN-40-1EP_6x6mm_P0.5mm.step"
    (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))
)
'''
open(f'{P}/abx-footprints.pretty/{NAME}.kicad_mod', 'w').write(txt)
print('wrote', NAME, len(o), 'pads')
