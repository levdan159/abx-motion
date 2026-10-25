"""Aux-buck placement (U511 24 V, TI LM70880 VQFN-29 since 2026-10-25) so critical.py can route the small-signal nets.
(The 12 V buck U512 TPS54360B and its parts were removed 2026-10-24 with the ESP32 sheets; its entries are gone.)
Usage: ~/.cache/mark-mods/kicad-mcp-big-venv/bin/python buckplace.py <board.kicad_pcb>   (KiCad CLOSED; moves parts only)
Then run critical.py <board> and pours.py <board>. Idempotent: every part goes to an absolute (x, y, rot).

LM70880 at (176.0, 121.3) rot 0 (top view = TI land pattern): VIN die pad + VIN pins top-left, PGND pins 23-26 top-right,
SW die pad + SW1-3 right (towards L520 pad 1), signal row 9-16 along the bottom, CBOOT/SW4 (4/5) and BIAS/PG/PFM (6-8)
left, AGND/VDDA/VCC (17-19) right. After TI SNVSCD3 fig. 7-29:
  - input caps above the IC bridging the VIN fingers (27-29) and PGND pins (23-26): C524 100 nF right at the pins, C520
    1210 above it; C522 1210 left of C520 (its GND pad via In1); C523 / C521 bulk further left (+BATT top, GND bottom).
  - CBOOT loop on the left: R539 (1R) above C528 (47 nF), pin 4 -> R539 -> C528 -> pin 5 (SW4), ~2.5 x 2 mm.
  - VCC cap C550 (0805) and VDDA cap C551 in the 2 mm column between the IC and L520, below the SW copper.
  - EN divider R520/R521 under pin 9 (left); the ISNS+/VOUT Kelvin pair (pins 11/12) drops to B.Cu right under the pins
    and runs to the shunt R538, which takes C529's old place next to L520 pad 2 (C529 moves below C531).
  - CFG / RT / COMP leave pins 13-15 as a 0.5 mm bundle and fan down-left to R540 / R522 / R525 (+ C527, C526 below);
    FB (pin 16) goes down-right to R524 / R523 under the VDDA cap, clear of the SW node.
"""
import subprocess as _sp; assert all(_sp.run(['pgrep', '-x', x], capture_output=True).returncode for x in ('kicad', 'eeschema', 'pcbnew')), 'KiCad is running: close it (without saving) first'
import sys  # noqa: E402  (the KiCad guard above must be the first statement)
import pcbnew  # noqa: E402

BOARD = sys.argv[1]
assert BOARD.endswith('.kicad_pcb'), 'board path must end in .kicad_pcb'
MM = 1e6
b = pcbnew.LoadBoard(BOARD)
fp = {f.GetReference(): f for f in b.GetFootprints()}

PLACE = {
    # ---- 24 V buck (U511 LM70880); rot 270 puts pad 1 on top for the 2-pad parts, rot 90 puts it at the bottom
    'U511': (176.0, 121.3, 0),
    'C524': (175.75, 117.05, 0),        # 100 nF: +BATT pad over VIN finger 27, GND pad over PGND pin 26
    'C520': (176.25, 114.66, 0),       # 4.7 uF 1210 above C524 (+BATT left, GND right)
    'C522': (171.5, 114.66, 180),      # 4.7 uF: +BATT pad right (beside C520's), GND pad left (In1 vias)
    'C523': (167.4, 119.0, 270),       # bulk 4.7 uF: +BATT top, GND bottom
    'C521': (164.0, 119.0, 270),
    'R539': (170.6, 120.2, 180),       # RBOOT: pad 1 (BOOT) right towards pin 4, pad 2 (BOOTR) left
    'C528': (170.6, 122.3, 0),         # CBOOT: pad 1 (BOOTR) left under R539 pad 2, pad 2 (SW) right towards pin 5
    'C550': (180.48, 122.9, 270),      # VCC 4.7 uF 0805: pad 1 level with pin 19
    'C551': (180.48, 126.1, 270),      # VDDA 100 nF: pad 1 at the end of the VDDA lane down the right column
    'R520': (171.0, 127.0, 90),        # UVLO top 267k 0805: pad 2 (EN) up, pad 1 (+BATT) down (In2 via)
    'R521': (172.9, 127.0, 270),       # UVLO bottom 10k: pad 1 (EN) up
    'R540': (175.0, 130.0, 270),       # CONFIG 41.2k: pad 1 (CFG) up
    'R522': (176.8, 130.0, 270),       # RT 43.2k: pad 1 (RT) up
    'R525': (178.6, 130.0, 270),       # Rcomp: pad 1 (COMP) up, pad 2 (CZ) down onto C526
    'C527': (180.4, 130.0, 270),      # Chf: pad 1 (COMP) up
    'C526': (178.6, 133.2, 270),       # Ccomp: pad 1 (CZ) up
    'R524': (182.2, 129.3, 270),       # FB bottom 12k: pad 1 (FB) up
    'R523': (184.0, 129.3, 90),        # FB top 348k: pad 2 (FB) up, pad 1 (+24V sense) down
    'R538': (198.9, 126.4, 270),       # 5 mOhm shunt (C529's old place): pad 1 (ISNS, L520 side) up, pad 2 (+24V) down
    'C529': (196.6, 134.6, 0),         # output cap moved below C531: +24V pad left
}
# copper ending on a pad that moves would be left behind as a stub (or now overlap another net): delete those tracks /
# vias first (pour vias of PWR_VIAS are left to pours.py, critical_routes to critical.py); counts are printed
_keep = []
old_pads = [(q, q.GetNetname()) for ref in PLACE for q in fp[ref].Pads()
            if fp[ref].GetPosition() != pcbnew.VECTOR2I(int(round(PLACE[ref][0] * MM)), int(round(PLACE[ref][1] * MM)))
            or round(fp[ref].GetOrientationDegrees() - PLACE[ref][2]) % 360 != 0]
stub = 0
for tr in list(b.GetTracks()):
    g = tr.GetParentGroup()
    if g and g.GetName() in ('PWR_VIAS', 'critical_routes'): continue
    ends = (tr.GetPosition(),) if tr.Type() == pcbnew.PCB_VIA_T else (tr.GetStart(), tr.GetEnd())
    if any(n == tr.GetNetname() and q.IsOnLayer(tr.GetLayer() if tr.Type() != pcbnew.PCB_VIA_T else pcbnew.F_Cu) and q.HitTest(e)
           for q, n in old_pads for e in ends):
        if g: g.RemoveItem(tr)
        b.RemoveNative(tr); _keep.append(tr); stub += 1
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
    if not (160.0 <= bb.GetX() / MM and bb.GetRight() / MM <= 206.0 and 88.0 <= bb.GetY() / MM and bb.GetBottom() / MM <= 166.0):   # buck block area
        print('OUTSIDE region', ref); bad += 1
    for g in front:
        if g.GetReference() == ref or (g.GetReference() in PLACE and g.GetReference() < ref): continue
        c = crt(g)
        if c is None: continue
        s = pcbnew.SHAPE_POLY_SET(a); s.BooleanIntersection(c)
        if s.OutlineCount() and s.Area() > 0:
            print('COURTYARD overlap', ref, g.GetReference(), round(s.Area() / MM / MM, 4)); bad += 1
def pnet(ref, num): return [q for q in fp[ref].Pads() if q.GetNumber() == num][0].GetNetname()
B = '/Brakes/'
exp = {('U511', '4'): B + 'BOOT_24', ('U511', '5'): B + 'SW_24', ('U511', '9'): B + 'EN_24', ('U511', '11'): B + 'ISNS_24', ('U511', '12'): '+24V',
       ('U511', '13'): B + 'CFG_24', ('U511', '14'): B + 'RT_24', ('U511', '15'): B + 'COMP_24', ('U511', '16'): B + 'FB_24', ('U511', '18'): B + 'VDDA_24',
       ('U511', '19'): B + 'VCC_24', ('U511', '20'): B + 'SW_24', ('U511', '1'): '+BATT', ('U511', '30'): 'GND',
       ('R539', '1'): B + 'BOOT_24', ('R539', '2'): B + 'BOOTR_24', ('C528', '1'): B + 'BOOTR_24', ('C528', '2'): B + 'SW_24',
       ('C524', '1'): '+BATT', ('C520', '1'): '+BATT', ('C522', '1'): '+BATT', ('C523', '1'): '+BATT', ('C521', '1'): '+BATT',
       ('C550', '1'): B + 'VCC_24', ('C551', '1'): B + 'VDDA_24', ('R520', '2'): B + 'EN_24', ('R521', '1'): B + 'EN_24',
       ('R540', '1'): B + 'CFG_24', ('R522', '1'): B + 'RT_24', ('R525', '1'): B + 'COMP_24', ('R525', '2'): B + 'CZ_24', ('C527', '1'): B + 'COMP_24',
       ('C526', '1'): B + 'CZ_24', ('R524', '1'): B + 'FB_24', ('R523', '2'): B + 'FB_24', ('R523', '1'): '+24V',
       ('L520', '1'): B + 'SW_24', ('L520', '2'): B + 'ISNS_24', ('R538', '1'): B + 'ISNS_24', ('R538', '2'): '+24V', ('C529', '1'): '+24V'}
for (ref, num), n in exp.items():
    if pnet(ref, num) != n: print('NET mismatch', ref, num, pnet(ref, num), '!=', n); bad += 1
b.Save(BOARD)
print(f'buckplace: placed {len(PLACE)} parts, {bad} problem(s), {stub} track(s)/via(s) on moved pads deleted; saved {BOARD}')
