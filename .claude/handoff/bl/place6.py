"""ESC area: ESC1 power (top, DRV at bottom edge), shared STM32 strip (middle), ESC2 power mirrored (DRV at top edge)."""
import pcbnew, math, re
P = '/home/mark/Documents/abx-motion/abx-motion-brushless.kicad_pcb'
b = pcbnew.LoadBoard(P); MM = 1000000
def box(f):
    bb = f.GetBoundingBox(False, False); return [bb.GetX() / MM, bb.GetY() / MM, bb.GetRight() / MM, bb.GetBottom() / MM]
def hit(a, c, m=0.3): return not (a[2] + m <= c[0] or c[2] + m <= a[0] or a[3] + m <= c[1] or c[3] + m <= a[1])
def move(f, x, y, rot=0): f.SetOrientationDegrees(rot); f.SetPosition(pcbnew.VECTOR2I(int(x * MM), int(y * MM)))
fp = {f.GetReference(): f for f in b.GetFootprints()}
npads = {}
for f in b.GetFootprints():
    for p in f.Pads(): npads[p.GetNetname()] = npads.get(p.GetNetname(), 0) + 1

def block(pred, REG, KEY, rail_skip, fallback, anch=None, margin=0.3):
    anch = anch or {}
    mem = [f for f in b.GetFootprints() if pred(f)]; ms = {f.GetReference() for f in mem}
    others = [box(f) for f in b.GetFootprints() if f.GetReference() not in ms and f.GetLayer() == pcbnew.F_Cu]
    occ = []; keys = {}
    for r, (x, y, rot) in KEY.items(): move(fp[r], x, y, rot); occ.append(box(fp[r])); keys[r] = fp[r]
    def anchor(f):
        ref = f.GetReference()
        if ref in anch:
            k, num = anch[ref]; return keys[k], [p for p in keys[k].Pads() if p.GetNumber() == num][0]
        nets = [p.GetNetname() for p in f.Pads()]; cand = []
        for kr, k in keys.items():
            for p in k.Pads():
                n = p.GetNetname()
                if n in nets and n not in rail_skip and npads.get(n, 99) <= 9:
                    cand.append((npads[n], 0 if kr[0] == 'U' else (1 if kr[0] == 'Q' else 2), kr, p))
        if cand: cand.sort(key=lambda c: (c[0], c[1])); return keys[cand[0][2]], cand[0][3]
        return keys[fallback], None
    bad = []
    for f in sorted([f for f in mem if f.GetReference() not in KEY], key=lambda f: (f.GetReference() not in anch, f.GetReference()[0] not in 'RC', f.GetReference())):
        a, pad = anchor(f); ac = a.GetPosition(); ax, ay = ac.x / MM, ac.y / MM
        if pad is not None:
            px, py = pad.GetX() / MM, pad.GetY() / MM; dx, dy = px - ax, py - ay; d = math.hypot(dx, dy) or 1; tx, ty = px + dx / d * 2.0, py + dy / d * 2.0
        else: tx, ty = ax, ay
        move(f, 0, 0, 0); w = box(f); fw, fh = w[2] - w[0], w[3] - w[1]; done = False
        for r10 in range(0, 300):
            r = r10 * 0.4
            for k in range(0, 16 if r > 0 else 1):
                ang = 2 * math.pi * k / 16; x, y = tx + r * math.cos(ang), ty + r * math.sin(ang); bx = [x - fw / 2, y - fh / 2, x + fw / 2, y + fh / 2]
                if bx[0] < REG[0] or bx[2] > REG[2] or bx[1] < REG[1] or bx[3] > REG[3]: continue
                if any(hit(bx, o, margin) for o in occ) or any(hit(bx, o, margin) for o in others): continue
                move(f, x, y, 0); occ.append(box(f)); done = True; break
            if done: break
        if not done: bad.append(f.GetReference())
    print('block', len(mem), 'unplaced', bad)
    return bad

# ---------------- power stages: local coords in a 62 x 46 block
W, H = 62, 46
CHK = {'C328': (7, 9, 0), 'C329': (7, 22, 0), 'Q301': (42, 9, 0), 'Q302': (42, 17.5, 0), 'Q303': (33, 9, 0), 'Q304': (33, 17.5, 0), 'Q305': (24, 9, 0), 'Q306': (24, 17.5, 0),
       'R307': (42, 25.5, 0), 'R308': (33, 25.5, 0), 'R309': (24, 25.5, 0), 'J301': (55.5, 8, 90), 'J302': (55.5, 15, 90), 'J303': (55.5, 22, 90),
       'NT301': (49, 27, 0), 'U302': (33, 37.5, 0), 'J304': (9.5, 41.5, 0)}
for i in range(7): CHK['C%d' % (321 + i)] = (21.6 + 5.2 * i, 3, 0)
def sh(r, off): return re.sub(r'(\d{3})$', lambda m: str(int(m.group(1)) + off), r)
for pre, off, oy, mirror in (('/68e0475f', 0, 48, False), ('/df9be12f', 100, 118, True)):
    KEY = {}
    for r, (x, y, rot) in CHK.items():
        if mirror: y, rot = H - y, (rot + 180) % 360
        if mirror and r == 'J304': x += 9  # pin 1 is at the end of the body: keep the same footprint box when rotated
        KEY[sh(r, off)] = (115 + x, oy + y, rot)
    block(lambda f, pre=pre: f.GetPath().AsString().startswith(pre), (115.5, oy + 0.3, 176.5, oy + H - 0.3), KEY, {'GND', 'VBUS', '+3V3_ESC', '+5V'}, sh('U302', off))

# ---------------- shared STM32 strip y 94..118
MCU = lambda f: f.GetSheetname() == '/ESC_MCU/'
KEY = {'U701': (146, 106, 0), 'U706': (126, 101, 0), 'U704': (126, 111.5, 0), 'U705': (166, 112, 0),
       'J701': (173.6, 103, 0), 'J703': (162, 98.5, 0), 'J702': (173.6, 96.4, 0)}
# decoupling caps: one per VDD/VBAT pin, VDDA pair at pins 21/22, LDO caps at the LDO, mux/CAN caps at their chips
ANCH = {'C701': ('U701', '11'), 'C702': ('U701', '19'), 'C703': ('U701', '28'), 'C704': ('U701', '50'), 'C705': ('U701', '75'), 'C706': ('U701', '100'),
        'C707': ('U701', '6'), 'C708': ('U701', '75'), 'C709': ('U701', '22'), 'C710': ('U701', '21'), 'FB701': ('U701', '22'),
        'C720': ('U705', '1'), 'C721': ('U705', '5'), 'C723': ('U706', '16'), 'C718': ('U704', '3'), 'C719': ('U704', '5')}
block(MCU, (115.5, 94.3, 176.5, 117.7), KEY, {'GND', 'VBUS', '+3V3_ESC', '+5V'}, 'U701', ANCH)
for z in list(b.Zones()): b.Remove(z)
b.Save(P)
