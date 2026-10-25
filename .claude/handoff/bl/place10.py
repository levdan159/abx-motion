"""Place the aux-power / brake block (Brakes sheet v2) + the E-stop delay parts. KiCad must be CLOSED.
Right edge under J1: J501 brakes (4p), J511 12 V (2p); bottom edge: J510 XT60 (+24V out). Bucks + DRV8874 in the
gap x161-191 / y113-147 (+BATT enters from Q1/F1 above). Big parts first, then passives spiral-placed next to the IC pin
they serve. Everything else stays where the owner put it."""
import subprocess as _sp; assert _sp.run(['pgrep', '-x', 'kicad'], capture_output=True).returncode, 'KiCad is running: close it (without saving) first'
import pcbnew, math
P = '/home/mark/Documents/abx-motion/abx-motion-brushless.kicad_pcb'
b = pcbnew.LoadBoard(P); MM = 1e6
fp = {f.GetReference(): f for f in b.GetFootprints()}
def box(f):
    cy = f.GetCourtyard(pcbnew.F_CrtYd); bb = cy.BBox() if cy.OutlineCount() else f.GetBoundingBox(False, False)
    return [bb.GetX() / MM, bb.GetY() / MM, bb.GetRight() / MM, bb.GetBottom() / MM]
def hit(a, c, m=0.25): return not (a[2] + m <= c[0] or c[2] + m <= a[0] or a[3] + m <= c[1] or c[3] + m <= a[1])
def move(f, x, y, rot=0): f.SetOrientationDegrees(rot); f.SetPosition(pcbnew.VECTOR2I(int(round(x * MM)), int(round(y * MM))))
BRK = {r for r, f in fp.items() if f.GetSheetname() == '/Brakes/'}
DLY = {'U707', 'R709', 'R710', 'C724', 'C725'}
MOVING = BRK | DLY
occ = [box(f) for r, f in fp.items() if r not in MOVING and not f.IsFlipped()]
REG = [(160.8, 113.3, 203.1, 147.3), (185.3, 88.0, 203.1, 113.3), (153.8, 124.0, 161.2, 139.0), (166.2, 147.3, 185.0, 165.8), (202.0, 147.3, 206.3, 165.8)]   # free gap, old J1 slot, J404 pocket, bottom strips
def inside(bx, regs): return any(bx[0] >= r[0] and bx[1] >= r[1] and bx[2] <= r[2] and bx[3] <= r[3] for r in regs)
def spiral(f, tx, ty, regs, rots=(0, 90, 180, 270)):
    for r10 in range(500):
        rad = r10 * 0.3
        for k in range(28 if rad else 1):
            a = 2 * math.pi * k / 28; x, y = tx + rad * math.cos(a), ty + rad * math.sin(a)
            for rot in rots:
                move(f, 0, 0, rot); w = box(f); fw, fh = w[2] - w[0], w[3] - w[1]; ox, oy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
                bx = [x - fw / 2, y - fh / 2, x + fw / 2, y + fh / 2]
                if not inside(bx, regs) or any(hit(bx, o) for o in occ): continue
                move(f, x - ox, y - oy, rot); occ.append(box(f)); return True
    return False
def pad(ref, num):
    p = [q for q in fp[ref].Pads() if q.GetNumber() == num][0].GetPosition(); return p.x / MM, p.y / MM

# ---- edge connectors (rot 90: wire entry to the right edge x 202.1; rot 180 XT60 mouth on the bottom edge y 166.1)
move(fp['J501'], 208.96, 134.4, 90)      # y 116.1-137.5 (board widened to x 214)
move(fp['J511'], 208.96, 146.8, 90)      # y 138.6-149.9
move(fp['J510'], 190.0, 160.96, 0)      # MKDS 2p, rot 0 = wire entry down: x 186.9-198.2, y 155.2-166.1
for r in ('J501', 'J511', 'J510'): occ.append(box(fp[r]))
bad = []
# ---- big parts: +24V row on top (input from Q1/F1), +12V row below, brake driver at the bottom near J501/J511
for r, tx, ty, rots in (('C525', 192.0, 96.0, (0, 90)), ('U511', 176.0, 118.5, (0, 90, 180, 270)), ('L520', 189.0, 121.0, (0,)), ('D520', 179.5, 124.5, (0, 90, 180, 270)),
                        ('U512', 176.0, 133.5, (0, 90, 180, 270)), ('L521', 189.0, 135.5, (0,)), ('D521', 179.5, 139.0, (0, 90, 180, 270)),
                        ('U513', 199.0, 143.0, (0, 90, 180, 270)), ('C546', 199.5, 129.0, (90, 0)), ('D523', 194.0, 144.5, (0, 90)), ('D522', 199.5, 120.0, (0, 90)),
                        ('J512', 167.0, 143.0, (0, 90))):
    if not spiral(fp[r], tx, ty, REG, rots): bad.append(r)
# ---- passives next to the pin they serve (first matching net on a key IC / inductor / connector)
KEYS = ['U511', 'U512', 'U513', 'L520', 'L521', 'J510', 'J511', 'J501', 'J512', 'D523']
ANCH = {'C524': ('U511', '2'), 'C537': ('U512', '2'), 'C528': ('U511', '1'), 'C540': ('U512', '1'), 'C544': ('U513', '11'), 'C547': ('U513', '12'),
        'C548': ('U513', '13'), 'R532': ('U513', '6'), 'R533': ('U513', '5'), 'R534': ('U513', '5'), 'R536': ('U513', '7'), 'R537': ('U513', '16'),
        'JP501': ('U513', '3'), 'R510': ('U513', '4'), 'C545': ('U513', '11'),
        'C520': ('U511', '2'), 'C521': ('U511', '2'), 'C522': ('U511', '2'), 'C523': ('U511', '2'), 'C534': ('U512', '2'), 'C535': ('U512', '2'), 'C536': ('U512', '2'),
        'C529': ('L520', '2'), 'C530': ('L520', '2'), 'C531': ('L520', '2'), 'C532': ('L520', '2'), 'C533': ('L520', '2'),
        'C541': ('L521', '2'), 'C542': ('L521', '2'), 'C543': ('L521', '2'),
        'R520': ('U511', '3'), 'R521': ('U511', '3'), 'R522': ('U511', '4'), 'R523': ('U511', '5'), 'R524': ('U511', '5'), 'R525': ('U511', '6'), 'C526': ('U511', '6'), 'C527': ('U511', '6'),
        'R526': ('U512', '3'), 'R527': ('U512', '3'), 'R528': ('U512', '4'), 'R529': ('U512', '5'), 'R530': ('U512', '5'), 'R531': ('U512', '6'), 'C538': ('U512', '6'), 'C539': ('U512', '6'),
        'R507': ('J512', '2')}
order = sorted(BRK - {'J501', 'J510', 'J511'} - {r for r, *_ in []} - set(KEYS) - {'C525', 'C546', 'D520', 'D521', 'D522'},
               key=lambda r: (r[0] != 'C' or not r.startswith('C52') and not r.startswith('C53') and not r.startswith('C54'), r))
for r in order:
    if r not in ANCH: print('no anchor', r)
    tx, ty = pad(*ANCH[r]) if r in ANCH else (175.0, 140.0)
    if not spiral(fp[r], tx, ty, REG): bad.append(r)
# ---- E-stop delay next to the DRV_EN AND gates / STM32 PE15 (ESC_MCU strip)
REGM = [(96.3, 95.6, 167.2, 118.4)]
for r, a in (('U707', ('U702', '2')), ('R709', ('U707', '2')), ('C724', ('U707', '2')), ('C725', ('U707', '5')), ('R710', ('U701', '46'))):
    if not spiral(fp[r], *pad(*a), REGM): bad.append(r)
print('unplaced', bad)
if not bad: b.Save(P); print('saved')
