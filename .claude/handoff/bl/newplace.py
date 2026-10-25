"""Placement of the parts staged off-board after the ESP32 removal / additions / TPS54360B / LM70880 changes (2026-10-25).
Usage: ~/.cache/mark-mods/kicad-mcp-big-venv/bin/python newplace.py <board.kicad_pcb>   (KiCad CLOSED)
Order (pipeline): newplace.py -> buckplace.py (U511) -> critical.py -> pours.py -> fill.py. Idempotent: absolute poses.

- U1 / U901 (TPS54360B DDA): TI's layout (SNVSB93 sec. 10.1, fig. 52: diode + L at SW, CIN at VIN, RT/UVLO left, comp + FB divider under COMP/FB) = the U512 arrangement of buckplace.py's 2026-10-24 version
  (critical.py routed it 18/18, pours.py had its SW / GND / +BATT pours): offsets kept on purpose so that pattern can be
  ported to U1 / U901 as a translation. U1 sits in the left logic column above the U2 / LED cluster (the old U1 spot
  itself is taken by U2, C9/C10, R2/R3/C1, LEDs); U901 below it, turned 180 deg, with its +5V_AUX chain to J511 on
  the left edge.
- The other poses were found by a copper-aware search on the routed board (scratchpad engine.py / greedy.py: pads clear
  of foreign tracks / vias / pads / PWR_ pours by 0.32 mm, courtyards exact): see placement_report.md.
- Copper: tracks / vias ending on a pad that moves are deleted (never critical_routes / PWR_VIAS), GND pour stitches or
  stubs (cleanup_routes or no group) under a new pad are deleted, then whatever that left dangling is trimmed (never
  protected copper, never what dangled before). Any other foreign copper near a new pad is reported as COPPER CONFLICT.
- USB-C J201 + U201/R201/R202/F2/D202 go to the top edge (owner approved 2026-10-25)."""
import subprocess as _sp; assert all(_sp.run(['pgrep', '-x', x], capture_output=True).returncode for x in ('kicad', 'eeschema', 'pcbnew')), 'KiCad is running: close it (without saving) first'
import sys, collections  # noqa: E402,E401
import pcbnew  # noqa: E402


PLACE = {
    # ---- 5 V buck U1 TPS54360B (TI DDA layout, = the U512 pattern buckplace.py used: diode above, CBOOT between pin 8 and L, CIN at pin 2, EN/RT/FB/COMP row under pins 4-6)
    'U1': (79.75, 92.0, 0),
    'D3': (79.65, 86.77, 180),
    'C6': (84.6, 89.79, 270),
    'C4': (75.15, 90.65, 90),
    'C3': (72.15, 89.85, 90),
    'C2': (68.55, 88.25, 270),
    'R12': (74.8, 94.05, 90),
    'R13': (72.25, 93.55, 180),
    'R10': (77.75, 96.38, 270),
    'R4': (79.35, 96.38, 90),
    'R5': (80.95, 96.38, 270),
    'C12': (82.55, 96.38, 270),
    'R11': (84.15, 96.38, 270),
    'C11': (84.35, 99.45, 270),
    'L1': (89.95, 89.0, 0),
    'C7': (96.85, 87.4, 0),
    'C8': (96.85, 90.0, 0),
    # ---- +5V_AUX buck U901 TPS54360B: the same layout turned 180 deg (input on the +BATT side, output towards the left edge)
    'U901': (88.0, 135.0, 180),
    'D902': (88.1, 140.23, 0),
    'C905': (83.15, 137.21, 90),
    'C903': (92.6, 136.35, 270),
    'C902': (95.6, 137.15, 270),
    'C901': (99.2, 138.75, 90),
    'R907': (92.95, 132.95, 270),
    'R908': (95.5, 133.45, 0),
    'R903': (90.0, 130.62, 90),
    'R901': (88.4, 130.62, 270),
    'R902': (86.8, 130.62, 90),
    'C911': (85.2, 130.62, 90),
    'R904': (83.6, 130.62, 90),
    'C904': (83.4, 127.55, 90),
    'L901': (77.8, 138.0, 180),
    'C906': (70.9, 139.6, 180),
    'C907': (70.9, 137.0, 180),
    # ---- +5V_AUX output: C908 at the buck output, eFuse U902 (C909 in, C910 out, R905 ILIM, R906 FAULT pull-up), TVS D901, J511 on the left edge (wire entry out)
    'C908': (71.0, 135.0, 180),
    'U902': (67.25, 137.0, 0),
    'C909': (67.0, 139.0, 180),
    'R905': (64.25, 137.0, 180),
    'C910': (67.25, 134.75, 0),
    'D901': (57.75, 138.0, 270),
    'R906': (64.0, 138.5, 0),
    'J511': (50.1, 135.5, 270),
    # ---- precharge string R803 - R830 - R831 - R804 (SR2512 anti-surge): the two new resistors below R803, pads on PRE_M / PRE_M2 / PRE_M3
    'R830': (169.5, 94.25, 270),
    'R831': (173.5, 94.25, 90),
    # ---- breaker sequencer U802 LM339 right of U801, above the VBAT_IN pour (y < 85.8)
    'U802': (206.0, 72.25, 0),
    'C811': (203.5, 66.0, 90),
    'Q804': (204.0, 78.75, 270),
    'D801': (206.0, 65.75, 90),
    'R819': (206.5, 78.5, 90),
    'R820': (211.25, 72.25, 0),
    'C807': (208.0, 78.5, 270),
    'R821': (211.25, 73.75, 180),
    'R822': (211.25, 75.25, 0),
    'C808': (210.25, 77.75, 0),
    'R823': (204.0, 81.5, 180),
    'R824': (209.25, 66.75, 180),
    'R825': (207.25, 80.75, 180),
    'R826': (203.5, 63.0, 270),
    'R827': (210.25, 79.25, 180),
    'C809': (206.5, 83.25, 270),
    'R828': (203.5, 83.75, 90),
    'R829': (210.25, 80.75, 0),
    'C810': (208.25, 83.0, 270),
    # ---- USB VBUS divider into PA9 (the pin side of U701 is full: nearest pair spot, right of LOGO1)
    'R712': (108.75, 107.25, 90),
    'R711': (107.25, 108.0, 90),
    # ---- IMU U711 LSM6DS3TR-C right of U701 (I2C1 PB8/PB9 + INT1 PE4), decaps at its supply pins, I2C pull-ups
    'U711': (152.0, 116.25, 90),
    'C726': (154.25, 116.5, 90),
    'C727': (153.0, 113.75, 0),
    'R713': (152.0, 119.25, 180),
    'R714': (152.25, 111.5, 270),
    # ---- I/O header J704 on the top edge, ESD arrays right behind it, 100 R series resistors behind them (MCU side), F701/C728 at pin 1
    'J704': (97.0, 50.9, 0),
    'U708': (100.0, 56.25, 270),
    'U709': (104.0, 56.25, 270),
    'U710': (108.0, 56.25, 270),
    'F701': (93.25, 53.0, 90),
    'C728': (96.75, 55.0, 0),
    'R715': (101.0, 59.8, 90),
    'R716': (97.5, 59.3, 90),
    'R717': (105.0, 59.8, 90),
    'R718': (103.0, 59.8, 90),
    'R719': (109.0, 59.8, 90),
    'R720': (107.0, 59.8, 90),
}
# owner approved 2026-10-25: USB-C J201 + its parts to the top edge (opening up), ~70 mm -> ~60 mm from PA11/12
USB_TOP = {
    'J201': (84.0, 52.5, 180),
    'U201': (84.0, 60.0, 270),
    'R201': (86.5, 59.25, 270),
    'R202': (81.5, 59.25, 270),
    'F2': (89.75, 59.0, 0),
    'D202': (91.0, 62.5, 90),
}
EXPECT = {
    ('U1', '1'): '/Power_Supply/U1_BOOT',
    ('U1', '2'): '+BATT',
    ('U1', '3'): '/Power_Supply/U1_EN',
    ('U1', '4'): '/Power_Supply/U1_RT',
    ('U1', '5'): '/Power_Supply/U1_FB',
    ('U1', '6'): '/Power_Supply/U1_COMP',
    ('U1', '7'): 'GND',
    ('U1', '8'): '/Power_Supply/U1_SW',
    ('D3', '1'): '/Power_Supply/U1_SW',
    ('D3', '2'): 'GND',
    ('C6', '1'): '/Power_Supply/U1_BOOT',
    ('C6', '2'): '/Power_Supply/U1_SW',
    ('L1', '1'): '/Power_Supply/U1_SW',
    ('L1', '2'): '+5V',
    ('R12', '1'): '+BATT',
    ('R12', '2'): '/Power_Supply/U1_EN',
    ('R13', '1'): '/Power_Supply/U1_EN',
    ('R10', '1'): '/Power_Supply/U1_RT',
    ('R4', '1'): '+5V',
    ('R4', '2'): '/Power_Supply/U1_FB',
    ('R5', '1'): '/Power_Supply/U1_FB',
    ('R11', '1'): '/Power_Supply/U1_COMP',
    ('R11', '2'): '/Power_Supply/U1_CZ',
    ('C11', '1'): '/Power_Supply/U1_CZ',
    ('C12', '1'): '/Power_Supply/U1_COMP',
    ('U901', '1'): '/Power_Supply/U901_BOOT',
    ('U901', '2'): '+BATT',
    ('U901', '3'): '/Power_Supply/U901_EN',
    ('U901', '4'): '/Power_Supply/U901_RT',
    ('U901', '5'): '/Power_Supply/U901_FB',
    ('U901', '6'): '/Power_Supply/U901_COMP',
    ('U901', '7'): 'GND',
    ('U901', '8'): '/Power_Supply/U901_SW',
    ('D902', '1'): '/Power_Supply/U901_SW',
    ('D902', '2'): 'GND',
    ('C905', '1'): '/Power_Supply/U901_BOOT',
    ('C905', '2'): '/Power_Supply/U901_SW',
    ('L901', '1'): '/Power_Supply/U901_SW',
    ('L901', '2'): '/Power_Supply/5V_AUX_BUCK',
    ('R907', '1'): '+BATT',
    ('R907', '2'): '/Power_Supply/U901_EN',
    ('R908', '1'): '/Power_Supply/U901_EN',
    ('R903', '1'): '/Power_Supply/U901_RT',
    ('R901', '1'): '/Power_Supply/5V_AUX_BUCK',
    ('R901', '2'): '/Power_Supply/U901_FB',
    ('R902', '1'): '/Power_Supply/U901_FB',
    ('R904', '1'): '/Power_Supply/U901_COMP',
    ('R904', '2'): '/Power_Supply/U901_CZ',
    ('C904', '1'): '/Power_Supply/U901_CZ',
    ('C911', '1'): '/Power_Supply/U901_COMP',
}

args = [a for a in sys.argv[1:] if not a.startswith('--')]
BOARD = args[0]
assert BOARD.endswith('.kicad_pcb'), 'board path must end in .kicad_pcb'
MM = 1e6
PLACE = dict(PLACE)
PLACE.update(USB_TOP)
b = pcbnew.LoadBoard(BOARD)
fp = {f.GetReference(): f for f in b.GetFootprints()}
PROTECT = ('critical_routes', 'PWR_VIAS')
grp = {}
for g in b.Groups():
    for it in g.GetItems(): grp[it.m_Uuid.AsString()] = g
def protected(it): g = grp.get(it.m_Uuid.AsString()); return g is not None and g.GetName() in PROTECT
_gone = []; stats = collections.Counter()      # removed items stay referenced (SWIG frees -> crashes, see pours.py)
def drop(it, why):
    g = grp.get(it.m_Uuid.AsString())
    if g is not None: g.RemoveItem(it)
    b.RemoveNative(it); _gone.append(it); stats[why] += 1
b.BuildConnectivity()
OLD_DANGLING = {t.m_Uuid.AsString() for t in b.GetTracks() if b.GetConnectivity().TestTrackEndpointDangling(t, False)}

def iv(x, y): return pcbnew.VECTOR2I(int(round(x * MM)), int(round(y * MM)))
moved = [r for r, (x, y, rot) in PLACE.items()
         if fp[r].GetPosition() != iv(x, y) or round(fp[r].GetOrientationDegrees() - rot) % 360 != 0]
# 1. copper ending on a pad that moves (buckplace.py rule; protected groups are never touched)
old_pads = [(q, q.GetNetname()) for r in moved for q in fp[r].Pads()]
kept_prot = 0
for t in list(b.GetTracks()):
    ends = (t.GetPosition(),) if t.Type() == pcbnew.PCB_VIA_T else (t.GetStart(), t.GetEnd())
    if any(n == t.GetNetname() and (t.Type() == pcbnew.PCB_VIA_T or q.IsOnLayer(t.GetLayer())) and q.HitTest(e)
           for q, n in old_pads for e in ends):
        if protected(t): kept_prot += 1; continue
        drop(t, 'copper on a moved pad')
for r, (x, y, rot) in PLACE.items():
    f = fp[r]; assert not f.IsFlipped(), r
    f.SetOrientationDegrees(rot); f.SetPosition(iv(x, y))
# 2. foreign-net copper under / too close to a new pad: only GND pour stitches and stubs (cleanup_routes or no group)
#    may go; anything else is a placement error (reported, not deleted)
CL = int(0.25 * MM)
blockers = []
crts = [fp[r].GetCourtyard(pcbnew.F_CrtYd) for r in PLACE]
for t in list(b.GetTracks()):      # GND stitch vias inside a placed part's courtyard (hole-to-hole with EP thermal vias)
    g = grp.get(t.m_Uuid.AsString())
    if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == 'GND' and (g is None or g.GetName() == 'cleanup_routes') \
            and any(c.OutlineCount() and c.Contains(t.GetPosition()) for c in crts):
        drop(t, 'GND stitch via inside a new courtyard')
for t in list(b.GetTracks()):
    for r in PLACE:
        if t.GetNetname() == '' : continue
        hit = None
        for q in fp[r].Pads():
            if q.GetNetname() == t.GetNetname(): continue
            th = q.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
            if t.Type() != pcbnew.PCB_VIA_T and not (th or q.IsOnLayer(t.GetLayer())): continue
            sh = q.GetEffectiveShape(pcbnew.F_Cu if not th else pcbnew.F_Cu)
            if t.GetEffectiveShape().Collide(sh, CL): hit = q; break
        if hit is None: continue
        g = grp.get(t.m_Uuid.AsString())
        if t.GetNetname() == 'GND' and (g is None or g.GetName() == 'cleanup_routes'):
            drop(t, 'GND stitch/stub under a new pad'); break
        blockers.append(f'{r}.{hit.GetNumber()} [{hit.GetNetname()}] vs {t.GetNetname()} ({g.GetName() if g else "-"})'); break
# 3. trim what that left dangling (never protected copper, never what dangled before)
while True:
    b.BuildConnectivity(); c = b.GetConnectivity(); n0 = sum(stats.values())
    for t in list(b.GetTracks()):
        if t.m_Uuid.AsString() in OLD_DANGLING or protected(t) or not c.TestTrackEndpointDangling(t, False): continue
        drop(t, 'dangling ' + ('via' if t.Type() == pcbnew.PCB_VIA_T else 'track'))
    if sum(stats.values()) == n0: break
# 4. checks: courtyards of the placed parts against every front part; region; pad nets of the switcher templates
bad = len(blockers)
for s in blockers: print('COPPER CONFLICT', s)
front = [f for f in b.GetFootprints() if not f.IsFlipped()]
for r in PLACE:
    a = fp[r].GetCourtyard(pcbnew.F_CrtYd)
    if not a.OutlineCount(): continue
    bb = a.BBox()
    if not (44.9 * MM <= bb.GetX() and bb.GetRight() <= 214.1 * MM and 47.9 * MM <= bb.GetY() and bb.GetBottom() <= 166.1 * MM):
        print('OUTSIDE board', r); bad += 1
    for g in front:
        if g.GetReference() == r or (g.GetReference() in PLACE and g.GetReference() < r): continue
        c2 = g.GetCourtyard(pcbnew.F_CrtYd)
        if not c2.OutlineCount(): continue
        s = pcbnew.SHAPE_POLY_SET(a); s.Inflate(int(0.002 * MM), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, int(0.001 * MM))   # touching = DRC overlap
        s.BooleanIntersection(c2)
        if s.OutlineCount() and s.Area() > 0: print('COURTYARD overlap', r, g.GetReference(), round(s.Area() / MM / MM, 4)); bad += 1
def pnet(r, n): return [q for q in fp[r].Pads() if q.GetNumber() == n][0].GetNetname()
for (r, n), net in EXPECT.items():
    if pnet(r, n) != net: print('NET mismatch', r, n, pnet(r, n), '!=', net); bad += 1
b.Save(BOARD)
print(f'newplace: {len(PLACE)} parts at their poses ({len(moved)} moved), {bad} problem(s); copper removed: {dict(stats)}; '
      f'protected copper on moved pads kept: {kept_prot}; saved {BOARD}')
