"""Place the F8 parts: bus breaker (right strip above J1), brake drivers (old Q501/Q502 spots),
eFuses (old PTC spots), TPs (logic strip row), J102 (bottom edge), logo out of J102's way.
Runs on the saved file; then KiCad(...).get_board().revert() in the live editor."""
import pcbnew, math
P = '/home/mark/Documents/abx-motion/abx-motion-brushless.kicad_pcb'
b = pcbnew.LoadBoard(P); MM = 1000000
fp = {f.GetReference(): f for f in b.GetFootprints()}
def box(f):
    bb = f.GetCourtyard(pcbnew.F_CrtYd).BBox() if f.GetCourtyard(pcbnew.F_CrtYd).OutlineCount() else f.GetBoundingBox(False, False)
    return [bb.GetX() / MM, bb.GetY() / MM, bb.GetRight() / MM, bb.GetBottom() / MM]
def hit(a, c, m=0.3): return not (a[2] + m <= c[0] or c[2] + m <= a[0] or a[3] + m <= c[1] or c[3] + m <= a[1])
def move(f, x, y, rot=0): f.SetOrientationDegrees(rot); f.SetPosition(pcbnew.VECTOR2I(int(x * MM), int(y * MM)))

MOVE = set()  # everything this script places; the rest is fixed
def key(r, x, y, rot=0): move(fp[r], x, y, rot); MOVE.add(r)

# ---- fixed keys
key('J1', 191.0, 104.0, 270)                       # VBAT_IN pads now on top, facing the breaker
key('R801', 183.5, 89.2, 180)                      # horizontal: VBAT_IN pad right (U801 side), BUS_SNS left (precharge side)
key('Q801', 183.5, 79.6, 270)                      # drain (BUS_SNS) down, sources up
key('Q802', 183.5, 65.3, 90)                       # sources down (common BUS_SRC), drain = VBUS up toward ESC1 bus caps
key('R803', 172.5, 88.5, 180); key('R804', 172.5, 84.0, 0); key('Q803', 172.5, 78.5, 0)  # precharge left of the power column
key('U801', 195.5, 66.0, 180)                      # pins 11-20 (gate, SNS, VIN) face the FETs
key('U504', 186.0, 122.4, 180); key('U505', 186.0, 135.4, 180)  # OUT side faces J501/J502
key('J102', 58.1, 160.1, 0)                        # wire entry toward the bottom edge
key('LOGO1', 76.0, 90.0, fp['LOGO1'].GetOrientationDegrees())
for i, r in enumerate(('TP_BATT1', 'TP_5V1', 'TP_3V3_1', 'TP_GND1', 'TP_GND2')): key(r, 97.0 + 4.0 * i, 122.5, 0)

# ---- small parts: spiral from a target point inside a region
GROUPS = [  # (refs, region x0 y0 x1 y1, target)
    ('C801 C806 C805 R816 R817 R802 R805 C802 R806 R807 C804 R815 R808 R809 R810 R811 R812 R813 R814 C803'.split(),
     (177.0, 48.6, 201.7, 91.0), (195.5, 66.0)),
    ('C510 R508 U502 R503 R510'.split(), (158.0, 117.6, 201.7, 131.9), (182.0, 122.4)),
    ('C511 R509 U503 R505'.split(), (158.0, 131.0, 201.7, 145.0), (182.0, 135.4)),
    ('U205 C215 C216 R233 R235'.split(), (52.5, 118.6, 63.6, 131.0), (58.0, 122.0)),
    ('U206 C217 C218 R234'.split(), (52.5, 106.5, 66.0, 131.0), (63.0, 112.0)),
    ('U602 C610 C611 R624 R623'.split(), (85.8, 110.3, 99.0, 118.6), (91.0, 115.0)),
]
for refs, *_ in GROUPS: MOVE.update(refs)
occ = [box(f) for f in b.GetFootprints() if f.GetReference() not in MOVE and f.GetLayer() == pcbnew.F_Cu]
occ += [box(fp[r]) for r in MOVE if not any(r in g[0] for g in GROUPS)]
bad = []
for refs, REG, (tx, ty) in GROUPS:
    for r in refs:
        f = fp[r]; move(f, 0, 0, 0); w = box(f); fw, fh = w[2] - w[0], w[3] - w[1]; ox, oy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
        done = False
        for r10 in range(300):
            rad = r10 * 0.4
            for k in range(16 if rad else 1):
                a = 2 * math.pi * k / 16; x, y = tx + rad * math.cos(a), ty + rad * math.sin(a)
                bx = [x - fw / 2, y - fh / 2, x + fw / 2, y + fh / 2]
                if bx[0] < REG[0] or bx[2] > REG[2] or bx[1] < REG[1] or bx[3] > REG[3] or any(hit(bx, o) for o in occ): continue
                move(f, x - ox, y - oy, 0); occ.append(box(f)); done = True; break
            if done: break
        if not done: bad.append(r)
print('unplaced', bad)
for r in sorted(MOVE):
    p = fp[r].GetPosition(); print(r, round(p.x / MM, 1), round(p.y / MM, 1), fp[r].GetOrientationDegrees())
if not bad: b.Save(P); print('saved')
