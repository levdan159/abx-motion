"""Rotation pass: for each small part (R/C/L/D/FB/LED/NT, <= 3 pads) try 0/90/180/270 about its courtyard centre and
keep the rotation with the shortest ratsnest (pad -> nearest same-net pad on another footprint; plane nets ignored)
that adds no courtyard overlap. KiCad must be CLOSED (edits the saved file).  python rotopt.py [refs-regex]"""
import subprocess as _sp; assert _sp.run(['pgrep', '-x', 'kicad'], capture_output=True).returncode, 'KiCad is running: close it (without saving) first'
import pcbnew, math, re, sys
P = '/home/mark/Documents/abx-motion/abx-motion-brushless.kicad_pcb'
PLANE = {'GND', 'VBUS', '+BATT', '+5V', '+3V3', '+3V3_ESC', '/Brakes/+24V_BRAKE'}   # these go to planes/pours, not ratsnest
b = pcbnew.LoadBoard(P); MM = 1e6
pat = re.compile(sys.argv[1] if len(sys.argv) > 1 else r'^(R|C|L|D|FB|LED|NT)\d')
def box(f):
    cy = f.GetCourtyard(pcbnew.F_CrtYd); bb = cy.BBox() if cy.OutlineCount() else f.GetBoundingBox(False, False)
    return (bb.GetX() / MM, bb.GetY() / MM, bb.GetRight() / MM, bb.GetBottom() / MM)
def hit(a, c, m=0.2): return not (a[2] + m <= c[0] or c[2] + m <= a[0] or a[3] + m <= c[1] or c[3] + m <= a[1])
fps = list(b.GetFootprints())
bynet = {}
for f in fps:
    for p in f.Pads():
        n = p.GetNetname()
        if n and n not in PLANE and not n.startswith('unconnected'): bynet.setdefault(n, []).append((f, p))
def cost(f):
    s = 0.0
    for p in f.Pads():
        others = [q for g, q in bynet.get(p.GetNetname(), []) if g is not f]
        if others:
            pp = p.GetPosition(); s += min(math.hypot(pp.x - q.GetPosition().x, pp.y - q.GetPosition().y) for q in others) / MM
    return s
boxes = {f.GetReference(): box(f) for f in fps if not f.IsFlipped()}
cand = [f for f in fps if pat.match(f.GetReference()) and len(f.Pads()) <= 3 and not f.IsFlipped() and not f.IsLocked()]
gain = 0.0; changed = []
for it in range(2):
    for f in cand:
        r = f.GetReference(); c0 = cost(f); rot0 = f.GetOrientationDegrees(); bx = box(f); cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
        best = (c0, rot0, f.GetPosition())
        for rot in (0, 90, 180, 270):
            f.SetOrientationDegrees(rot); nb = box(f); f.Move(pcbnew.VECTOR2I(int((cx - (nb[0] + nb[2]) / 2) * MM), int((cy - (nb[1] + nb[3]) / 2) * MM)))
            nb = box(f)
            if any(hit(nb, o) for k, o in boxes.items() if k != r): continue
            c = cost(f)
            if c < best[0] - 0.3: best = (c, rot, f.GetPosition())
        f.SetOrientationDegrees(best[1]); f.SetPosition(best[2]); boxes[r] = box(f)
        if best[1] != rot0: gain += c0 - best[0]; changed.append(r)
print(f'rotated {len(set(changed))} parts, ratsnest -{gain:.0f} mm')
b.Save(P)
