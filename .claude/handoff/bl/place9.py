"""Whole-board placement pass v2 (2026-10-23): Degson DG135T screw terminals, STM32 toward the board centre. KiCad must be CLOSED (edits the saved file).
ESC1 top / ESC2 bottom (180 deg copy about (140,107)): REDCUBE phase lugs on the board edge, each phase a
side-by-side high|low FET pair (drain left, PH node between, source right into the shunt), bus caps under the
high-side drains, DRV below (gates up). STM32 strip in the middle, bulk electrolytics in the x96-112 column,
battery J1 (2x REDCUBE M5) on the right edge under the breaker, input protection beside it.
Owner's left-side placement (ESP32 / IO / logic power) is kept; only stragglers move."""
import pcbnew, math, re
P = '/home/mark/Documents/abx-motion/abx-motion-brushless.kicad_pcb'
b = pcbnew.LoadBoard(P); MM = 1000000
fp = {f.GetReference(): f for f in b.GetFootprints()}
def box(f):
    cy = f.GetCourtyard(pcbnew.F_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else f.GetBoundingBox(False, False)
    return [bb.GetX() / MM, bb.GetY() / MM, bb.GetRight() / MM, bb.GetBottom() / MM]
def hit(a, c, m=0.3): return not (a[2] + m <= c[0] or c[2] + m <= a[0] or a[3] + m <= c[1] or c[3] + m <= a[1])
def move(f, x, y, rot=0): f.SetOrientationDegrees(rot); f.SetPosition(pcbnew.VECTOR2I(int(round(x * MM)), int(round(y * MM))))
def m2(r): return re.sub(r'(\d{3})$', lambda m: str(int(m.group(1)) + 100), r)      # ESC1 ref -> ESC2 ref
def refl(x, y, rot): return 280 - x, 214 - y, (rot + 180) % 360                         # 180 deg about (140, 107)
npads = {}
for f in b.GetFootprints():
    for p in f.Pads(): npads[p.GetNetname()] = npads.get(p.GetNetname(), 0) + 1

ESC1 = {r for r, f in fp.items() if f.GetSheetname() == '/ESC_Motor_1/'} - {'D301'}
ESC2 = {r for r, f in fp.items() if f.GetSheetname() == '/ESC_Motor_2/'}
MCU = {r for r, f in fp.items() if f.GetSheetname() == '/ESC_MCU/'}
PROT = {'Q1', 'F1', 'D2', 'R1'}
MISC = {'C611', 'R623', 'R624', 'LOGO1'} | {r for r in fp if r.startswith('TP_')}
MOVING = ESC1 | ESC2 | MCU | PROT | MISC | {'J1'}
fixed = [box(f) for r, f in fp.items() if r not in MOVING and f.GetLayer() == pcbnew.F_Cu]
virtual = []   # footprints F8 will swap: reserve the NEW courtyards
occ = []

# ---------------- ESC1 keys (board coords)
K = {}
FET_ROT, SH_ROT, CAP_ROT, DRV_ROT = 180, 270, 270, 180       # drain left / SP pad up / VBUS pad up / gates up
SH_ROT = 180                                                # shunt horizontal under the low FET, SP pad right (source pins)
# J301 DG135T 3-pole: rot 180 = wire entry up (board edge); pin 1 (PH_A) right, pin 3 (PH_C) left; front holes 3 mm from the
# edge, main body 0.8 mm inside it, the wire-entry bump overhangs the edge
K['J301'] = (150.16, 50.93, 180)
for ph, xc, qh, ql, rs, caps in (('A', 158, 'Q301', 'Q302', 'R307', ('C321', 'C322')),
                                  ('B', 140, 'Q303', 'Q304', 'R308', ('C323', 'C324')),
                                  ('C', 122, 'Q305', 'Q306', 'R309', ('C325', 'C326'))):
    K[qh] = (xc - 4.4, 66.9, FET_ROT); K[ql] = (xc + 4.4, 66.9, FET_ROT)
    K[rs] = (xc + 4.4, 72.1, SH_ROT)
    K[caps[0]] = (xc - 6.2, 72.4, CAP_ROT); K[caps[1]] = (xc - 2.6, 72.4, CAP_ROT)
K['C327'] = (140 - 4.4, 77.2, CAP_ROT)
K['U302'] = (140.0, 86.5, DRV_ROT)
K['J304'] = (121.0, 90.6, 0)
KEYS1 = dict(K)
for r, (x, y, rot) in KEYS1.items(): move(fp[r], x, y, rot)
for r, (x, y, rot) in KEYS1.items(): move(fp[m2(r)], *refl(x, y, rot))
# bulk electrolytics (VBUS pad toward the FETs), ESC2 TVS
for r, x, y in (('C328', 104.5, 78.0), ('C329', 104.5, 89.5), ('C428', 104.5, 136.0), ('C429', 104.5, 124.5)): move(fp[r], x, y, 180)
move(fp['D401'], 104.5, 147.5, 0)
# battery J1 DG135T 2-pole: rot 90 = wire entry to the right edge; pad 1 (BAT+) on top (y 97.0), pad 2 (GND) y 107.2
move(fp['J1'], 199.07, 107.2, 90)
keyset = set(KEYS1) | {m2(r) for r in KEYS1} | {'C328', 'C329', 'C428', 'C429', 'D401', 'J1'}
occ = fixed + [box(fp[r]) for r in keyset]

def spiral(f, tx, ty, REG, rots=(0, 90)):
    for r10 in range(400):
        rad = r10 * 0.35
        for k in range(24 if rad else 1):
            a = 2 * math.pi * k / 24; x, y = tx + rad * math.cos(a), ty + rad * math.sin(a)
            for rot in rots:
                move(f, 0, 0, rot); w = box(f); fw, fh = w[2] - w[0], w[3] - w[1]; ox, oy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
                bx = [x - fw / 2, y - fh / 2, x + fw / 2, y + fh / 2]
                if bx[0] < REG[0] or bx[2] > REG[2] or bx[1] < REG[1] or bx[3] > REG[3] or any(hit(bx, o) for o in occ): continue
                move(f, x - ox, y - oy, rot); occ.append(box(f)); return True
    return False

def anchor_target(f, keys, skip, fallback, anch):
    ref = f.GetReference()
    if ref in anch:
        k, num = anch[ref]; pad = [p for p in fp[k].Pads() if p.GetNumber() == num][0]; a = fp[k]
    else:
        nets = {p.GetNetname() for p in f.Pads()}; cand = []
        for kr in keys:
            for p in fp[kr].Pads():
                n = p.GetNetname()
                if n in nets and n not in skip and npads.get(n, 99) <= 9:
                    cand.append((npads[n], 0 if kr[0] == 'U' else (1 if kr[0] == 'Q' else 2), kr, p))
        if not cand:
            c = fp[fallback].GetPosition(); return c.x / MM, c.y / MM
        cand.sort(key=lambda c: (c[0], c[1])); a, pad = fp[cand[0][2]], cand[0][3]
    ac, pc = a.GetPosition(), pad.GetPosition()
    dx, dy = (pc.x - ac.x) / MM, (pc.y - ac.y) / MM; d = math.hypot(dx, dy) or 1
    return pc.x / MM + dx / d * 2.0, pc.y / MM + dy / d * 2.0

RAILS = {'GND', 'VBUS', '+3V3_ESC', '+5V', '+3V3'}
bad = []
# ---------------- ESC1 small parts, then the same placement rotated 180 deg for ESC2
REG1 = (112.6, 69.0, 167.2, 94.2)
small1 = sorted(ESC1 - set(KEYS1) - {'C328', 'C329'}, key=lambda r: (r[0] not in 'UQ', r[0] not in 'RC', r))
for r in small1:
    tx, ty = anchor_target(fp[r], [k for k in KEYS1 if k[0] in 'UQR' and not k.startswith('J')], RAILS, 'U302', {})
    if not spiral(fp[r], tx, ty, REG1): bad.append(r)
for r in small1:
    f1, f2 = fp[r], fp[m2(r)]; p = f1.GetPosition()
    x, y, rot = refl(p.x / MM, p.y / MM, f1.GetOrientationDegrees()); move(f2, x, y, rot); bx = box(f2)
    if any(hit(bx, o) for o in occ):
        if not spiral(f2, x, y, (112.6, 119.8, 167.2, 145.0)): bad.append(m2(r))
    else: occ.append(bx)

# ---------------- STM32 strip: pick the U701 rotation with the shortest ratsnest to the two DRVs
drv1, drv2 = fp['U302'].GetPosition(), fp['U402'].GetPosition()
m1n = {p.GetNetname() for r in ESC1 for p in fp[r].Pads()}; m2n = {p.GetNetname() for r in ESC2 for p in fp[r].Pads()}
best = None
for rot in (0, 90, 180, 270):
    move(fp['U701'], 130.0, 107.0, rot); s = 0
    for p in fp['U701'].Pads():
        n = p.GetNetname(); t = drv1 if n in m1n - RAILS else (drv2 if n in m2n - RAILS else None)
        if t is not None: s += math.hypot(p.GetPosition().x - t.x, p.GetPosition().y - t.y) / MM
    if best is None or s < best[0]: best = (s, rot)
move(fp['U701'], 130.0, 107.0, best[1]); occ.append(box(fp['U701'])); print('U701 rot', best[1], 'ratsnest', round(best[0]))
ANCH = {'C701': ('U701', '11'), 'C702': ('U701', '19'), 'C703': ('U701', '28'), 'C704': ('U701', '50'), 'C705': ('U701', '75'), 'C706': ('U701', '100'),
        'C707': ('U701', '6'), 'C708': ('U701', '75'), 'C709': ('U701', '22'), 'C710': ('U701', '21'), 'FB701': ('U701', '22'),
        'C711': ('U701', '49'), 'C712': ('U701', '73'), 'C713': ('U701', '12'), 'C714': ('U701', '13'), 'Y701': ('U701', '12'), 'C715': ('U701', '14')}
REGM = (96.3, 95.6, 167.2, 118.4)
order = ['Y701', 'U706', 'U704', 'U705', 'J701', 'J702', 'J703', 'U702', 'U703'] + sorted(MCU - {'U701', 'Y701', 'U706', 'U704', 'U705', 'J701', 'J702', 'J703', 'U702', 'U703'}, key=lambda r: (r not in ANCH, r))
mkeys = ['U701']
for r in order:
    tx, ty = anchor_target(fp[r], mkeys, RAILS, 'U701', ANCH)
    if not spiral(fp[r], tx, ty, REGM): bad.append(r)
    if r[0] in 'UJY': mkeys.append(r)
# ---------------- input protection beside J1 pad 1, eFuse stragglers at U602, TPs, logo
for r in ('F1', 'Q1', 'D2', 'R1'):
    if not spiral(fp[r], 180.0, 100.0, (167.6, 91.6, 186.0, 118.6), rots=(0, 90, 180, 270)): bad.append(r)
u = fp['U602'].GetPosition()
for r in ('C611', 'R624', 'R623'):
    if not spiral(fp[r], u.x / MM, u.y / MM, (60.0, 80.0, 99.0, 104.0)): bad.append(r)
for r in sorted(x for x in MISC if x.startswith('TP_')):
    if not spiral(fp[r], 106.0, 162.0, (96.3, 151.3, 113.4, 165.6)): bad.append(r)
if not spiral(fp['LOGO1'], 104.0, 107.0, (96.3, 95.6, 112.6, 118.4)) and not spiral(fp['LOGO1'], 175.0, 162.0, (45.5, 48.5, 201.5, 165.5)): bad.append('LOGO1')
# H5/H6 reference text sat outside the board: put it above the hole
for r in ('H5', 'H6'):
    f = fp[r]; p = f.GetPosition(); f.Reference().SetPosition(pcbnew.VECTOR2I(p.x, p.y - int(2.6 * MM)))
print('unplaced', bad)
if not bad: b.Save(P); print('saved')
