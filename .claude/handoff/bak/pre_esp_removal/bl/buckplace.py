"""Aux-buck placement (U511 24 V / U512 12 V, TPS54560B / TPS54360B) so critical.py can route FB/COMP/CZ/RT/EN/BOOT.
Usage: ~/.cache/mark-mods/kicad-mcp-big-venv/bin/python buckplace.py <board.kicad_pcb>   (KiCad CLOSED; moves parts only)
Then run critical.py <board> and pours.py <board>. Idempotent: every part goes to an absolute (x, y, rot).

Per buck, after the TI layout example (SLVSBN8 / SLVSCJ6 "Layout example"), keeping the IC rotation (pins 1-4 left, 5-8 right):
  - catch diode horizontal right ABOVE the IC (the only free spot between pin 8 and the inductor): cathode (SW) above
    pin 8 / beside the inductor's SW pad, anodes (GND) on the left beside the input-cap GND pads -> small hot loop
    VIN cap -> pin 2 -> SW pin 8 -> cathode -> anode -> cap GND; the SW node is pin 8 + diode cathode + inductor pad.
  - BOOT cap vertical in the gap between pin 8 and the inductor (pad 1 BOOT up, pad 2 SW at pin 8); the BOOT trace
    runs from pin 1 over the top of the IC, between the pins and the diode pads.
  - 100 nF VIN cap (C524 / C537) right at pin 2, 1210 VIN cap beside it; bulk 1210s further left (+BATT via In2).
  - EN divider at pin 3 (top resistor 0805 left of the pin, bottom resistor beside it), RT at pin 4.
  - FB divider + COMP network in one row under pins 4/5/6, away from the SW node: FB from pin 5 straight down,
    COMP from pin 6 out right, then down a lane that keeps 1 mm from the SW pads; CZ cap below Rcomp.
  - ICs moved straight down (U511 +2.0 mm, U512 +2.0 mm) to make room for the diodes; inductors and the output caps
    stay put. The FB top resistors' Vout pads (R523 +24V, R529 +12V) still need their Kelvin sense line to the
    output caps (not routed by critical.py).
"""
import subprocess as _sp; assert _sp.run(['pgrep', '-x', 'kicad'], capture_output=True).returncode, 'KiCad is running: close it (without saving) first'
import sys  # noqa: E402  (the KiCad guard above must be the first statement)
import pcbnew  # noqa: E402

BOARD = sys.argv[1]
assert BOARD.endswith('.kicad_pcb'), 'board path must end in .kicad_pcb'
MM = 1e6
b = pcbnew.LoadBoard(BOARD)
fp = {f.GetReference(): f for f in b.GetFootprints()}

ROW24, ROW12 = 124.875, 139.875        # FB/COMP/RT row centres (0603 vertical: courtyard +-1.525 mm)
PLACE = {
    # ---- 24 V buck (U511)
    'U511': (176.0, 120.5, 0),
    'D520': (175.9, 115.27, 180),      # cathode (pad 1) right, anodes left
    'C528': (180.63, 118.29, 270),     # BOOT cap: pad 1 BOOT up, pad 2 SW level with pin 8
    'C524': (171.4, 119.15, 90),       # 100 nF: +BATT at pin 2, GND up
    'C520': (168.32, 118.6, 90),
    'C522': (165.0, 117.86, 90),
    'R520': (171.05, 122.7, 90),       # EN top (0805): EN pad up at pin 3, +BATT down
    'R521': (168.5, 122.4, 180),       # EN bottom: EN pad right
    'R522': (174.0, ROW24, 270),       # RT under pin 4
    'R523': (175.6, ROW24, 90),        # FB top: FB pad up, +24V sense pad down
    'R524': (177.2, ROW24, 270),       # FB bottom: FB pad up (pin 5)
    'C527': (178.8, ROW24, 270),       # Chf: COMP pad up (GND pad beside R524's GND pad: two thermal spokes)
    'R525': (180.4, ROW24, 270),       # Rcomp: COMP pad up, CZ pad down onto C526
    'C526': (180.6, 127.95, 270),      # Ccomp (CZ) right below Rcomp
    'C523': (169.6, 126.2, 180),       # bulk VIN: +BATT pad right, beside R520's +BATT pad
    'C521': (164.8, 126.75, 90),       # bulk VIN pair with C535 (+BATT pads face each other, vias between)
    # ---- 12 V buck (U512)
    'U512': (176.0, 135.5, 0),
    'D521': (175.9, 130.27, 180),
    'C540': (180.85, 133.29, 270),
    'C537': (171.4, 134.15, 90),
    'C534': (168.4, 133.35, 90),
    'C535': (164.8, 131.75, 270),
    'C536': (164.6, 136.5, 90),
    'R526': (171.05, 137.55, 90),       # EN top (0805): EN pad up beside pin 3
    'R527': (168.5, 137.05, 180),       # EN bottom: EN pad right
    'R528': (174.0, ROW12, 270),
    'R529': (175.6, ROW12, 90),        # FB top: +12V sense pad down
    'R530': (177.2, ROW12, 270),
    'C539': (178.8, ROW12, 270),
    'R531': (180.4, ROW12, 270),
    'C538': (180.6, 142.95, 270),
}
for ref, (x, y, rot) in PLACE.items():
    f = fp[ref]; assert not f.IsFlipped(), ref
    f.SetOrientationDegrees(rot); f.SetPosition(pcbnew.VECTOR2I(int(round(x * MM)), int(round(y * MM))))

# ---- checks: courtyards of the moved parts against every front part, region, pad nets the routing relies on
def crt(f):
    s = f.GetCourtyard(pcbnew.F_CrtYd)
    return s if s.OutlineCount() else None
bad = 0
front = [f for f in b.GetFootprints() if not f.IsFlipped()]
for ref in PLACE:
    f = fp[ref]; a = crt(f); bb = a.BBox()
    if not (160.0 <= bb.GetX() / MM and bb.GetRight() / MM <= 206.0 and 88.0 <= bb.GetY() / MM and bb.GetBottom() / MM <= 166.0):
        print('OUTSIDE region', ref); bad += 1
    for g in front:
        if g.GetReference() == ref or (g.GetReference() in PLACE and g.GetReference() < ref): continue
        c = crt(g)
        if c is None: continue
        s = pcbnew.SHAPE_POLY_SET(a); s.BooleanIntersection(c)
        if s.OutlineCount() and s.Area() > 0:
            print('COURTYARD overlap', ref, g.GetReference(), round(s.Area() / MM / MM, 4)); bad += 1
def pnet(ref, num): return [q for q in fp[ref].Pads() if q.GetNumber() == num][0].GetNetname()
for v, u, d, cb, (ena, enb, rt, fbh, fbl, rz, cc, cz) in (
        ('24', 'U511', 'D520', 'C528', ('R520', 'R521', 'R522', 'R523', 'R524', 'R525', 'C527', 'C526')),
        ('12', 'U512', 'D521', 'C540', ('R526', 'R527', 'R528', 'R529', 'R530', 'R531', 'C539', 'C538'))):
    B = '/Brakes/'
    exp = {(u, '1'): f'BOOT_{v}', (u, '3'): f'EN_{v}', (u, '4'): f'RT_{v}', (u, '5'): f'FB_{v}', (u, '6'): f'COMP_{v}', (u, '8'): f'SW_{v}',
           (d, '1'): f'SW_{v}', (cb, '1'): f'BOOT_{v}', (cb, '2'): f'SW_{v}', (ena, '2'): f'EN_{v}', (enb, '1'): f'EN_{v}', (rt, '1'): f'RT_{v}',
           (fbh, '2'): f'FB_{v}', (fbl, '1'): f'FB_{v}', (rz, '1'): f'COMP_{v}', (rz, '2'): f'CZ_{v}', (cc, '1'): f'COMP_{v}', (cz, '1'): f'CZ_{v}'}
    for (ref, num), n in exp.items():
        if pnet(ref, num) != B + n: print('NET mismatch', ref, num, pnet(ref, num), '!=', B + n); bad += 1
b.Save(BOARD)
print(f'buckplace: placed {len(PLACE)} parts, {bad} problem(s); saved {BOARD}')
