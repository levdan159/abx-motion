"""High-current copper (2026-10-24): outer-layer net pours + via arrays for both ESC power stages, the bus breaker and
the aux bucks. Usage: python pours.py <board.kicad_pcb>   (KiCad CLOSED; keep the .kicad_pro next to the board).
Re-runnable: deletes every zone named PWR_* and every via in the group PWR_VIAS (plus free 0.6/0.3 vias left inside
old PWR_ outlines on the same net), then rebuilds, refills all zones and saves.
 ESC1 (refs 3xx) geometry is written once in ESC1 coordinates; ESC2 (4xx) = the same copper rotated 180 deg about
 (140,107) (x' = 280 - x, y' = 214 - y), like the placement. Per phase: F.Cu phase zone (J301 pole + high source + low
 drain) mirrored on B.Cu above the FET row with a via block; VBUS zone over the high drain + its two bus caps with
 vias to In2 VBUS; SPx zone (low source -> shunt); shunt/bus-cap GND zone with vias to In1. Bulk caps, breaker
 (VBAT_IN / BUS_SNS / BUS_SRC / VBUS), V_FUSED / +BATT, buck SW node, buck GND/EP, ISNS / +24V pours below
 (the 12 V buck U512 and its +12V / SW_12 / +BATT / GND pours were removed 2026-10-24; section 5 is the LM70880 U511
 since 2026-10-25).
 Vias are locked and grouped (PWR_VIAS: in the GUI double-click the group to edit inside it); zones are locked.
 Run planes.py (In2) BEFORE this script: planes.py deletes every In2 zone, including PWR_In2_VBUS_Q405.
 Vias stay clear of every gate-drive pad (2 mm) and breaker gate / sense pads (1.5 mm) and buck EN/RT/FB/COMP/BOOT pads (1 mm); zones are refilled
 around tracks, so the router's gate/sense tracks win. Report: .claude/handoff/pours_report.md"""
import subprocess as _sp; assert all(_sp.run(['pgrep', '-x', x], capture_output=True).returncode for x in ('kicad', 'eeschema', 'pcbnew')), 'KiCad is running: close it (without saving) first'
import sys, math, re, fnmatch
import pcbnew

P = sys.argv[1]
assert P.endswith('.kicad_pcb'), 'board path must end in .kicad_pcb'
MM = 1e6
VIA_D, VIA_DRILL, GROUP = 0.6, 0.3, 'PWR_VIAS'
PRIO = 10                                   # above the GND pours (0/1) and the In2 planes (1/2)
b = pcbnew.LoadBoard(P)
L = {'F': pcbnew.F_Cu, 'B': pcbnew.B_Cu, 'In1': pcbnew.In1_Cu, 'In2': pcbnew.In2_Cu}
LN = {v: k for k, v in L.items()}

def iu(v): return int(round(v * MM))
def poly_pts(z, i=0):
    o = z.Outline().COutline(i); return [(o.CPoint(k).x / MM, o.CPoint(k).y / MM) for k in range(o.PointCount())]

# ------------------------------------------------------------------ 1. remove what an earlier run made
_gone = []      # removed items stay referenced: letting SWIG free a removed ZONE corrupts the module (Tracks() breaks)
def drop(item): b.RemoveNative(item); _gone.append(item)
old = [(z.GetNetname(), poly_pts(z)) for z in b.Zones() if z.GetZoneName().startswith('PWR_')]
for z in [z for z in b.Zones() if z.GetZoneName().startswith('PWR_')]: drop(z)
ends = set()
for t in b.GetTracks():
    if t.Type() == pcbnew.PCB_TRACE_T:
        for p in (t.GetStart(), t.GetEnd()): ends.add((p.x, p.y))
removed = 0
for g in [g for g in b.Groups() if g.GetName() == GROUP]:
    for it in list(g.GetItems()): g.RemoveItem(it); drop(it); removed += 1
    drop(g)

def pip(pt, poly):
    x, y = pt; inside = False; n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: inside = not inside
    return inside
def dseg(p, a, c):
    (px, py), (ax, ay), (cx, cy) = p, a, c; dx, dy = cx - ax, cy - ay; l2 = dx * dx + dy * dy
    t = 0 if l2 == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / l2))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)
def dedge(pt, poly): return min(dseg(pt, poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))

for t in list(b.GetTracks()):        # fallback: free power vias inside old PWR_ outlines (group lost)
    if t.Type() != pcbnew.PCB_VIA_T or t.GetDrill() != iu(VIA_DRILL): continue
    p = t.GetPosition()
    if (p.x, p.y) in ends: continue
    if any(n == t.GetNetname() and pip((p.x / MM, p.y / MM), pts) for n, pts in old): drop(t); removed += 1
print(f'removed {len(old)} old PWR_ zones, {removed} old vias')

# ------------------------------------------------------------------ 2. geometry helpers
fp = {f.GetReference(): f for f in b.GetFootprints()}
def padbb(ref, num):
    bbs = [q.GetBoundingBox() for q in fp[ref].Pads() if q.GetNumber() == num and q.GetAttribute() == pcbnew.PAD_ATTRIB_SMD]
    bb = max(bbs, key=lambda r: r.GetWidth() * r.GetHeight())
    return bb.GetX() / MM, bb.GetY() / MM, bb.GetRight() / MM, bb.GetBottom() / MM
def R(x0, y0, x1, y1): return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
def grow(r, e): return R(r[0] - e, r[1] - e, r[2] + e, r[3] + e)
ID = lambda x, y: (x, y)
MIR = lambda x, y: (280 - x, 214 - y)       # ESC1 -> ESC2 (180 deg about (140,107))

ZONES = []   # dict(name, net, layer, pts, prio, vias)
def zone(name, net, layer, pts, vias=None, prio=PRIO):
    assert b.FindNet(net) is not None and b.FindNet(net).GetNetCode() > 0, f'net {net} not on board'
    vs = [] if vias is None else [dict(vias, region=vias['region'] or pts)]
    ZONES.append(dict(name='PWR_' + name, net=net, layer=layer, pts=pts, prio=prio, vias=vs))
def V(anchor, nmax, targets, pitch=1.0, region=None):
    return dict(anchor=anchor, max=nmax, targets=targets, pitch=pitch, region=region)

# ------------------------------------------------------------------ 3. ESC power stages
PH = (('A', 158.0, 146.3, 168.0), ('B', 140.0, 135.3, 145.4), ('C', 122.0, 112.0, 134.5))   # phase, xc, upper zone x0/x1 (ESC1)
for esc, T in ((1, ID), (2, MIR)):
    s = f'/ESC_Motor_{esc}/'
    def TP(pts): return [T(x, y) for x, y in pts]
    for ph, xc, ux0, ux1 in PH:
        up = R(ux0, 48.5, ux1, 64.35)                                   # above the FET row, J301/J401 pole
        if ph == 'A':                                                   # corner notch: keeps ESC2's copy off TP_5V1/TP_GND1
            up = [(ux0, 48.5), (162.0, 48.5), (162.0, 54.5), (ux1, 54.5), (ux1, 64.35), (ux0, 64.35)]
        node = R(xc - 2.7, 64.3, xc + 6.0, 69.6)                       # high source pins + low drain pad
        ps = pcbnew.SHAPE_POLY_SET(); ps.NewOutline()
        for x, y in up: ps.Append(iu(x), iu(y))
        pn = pcbnew.SHAPE_POLY_SET(); pn.NewOutline()
        for x, y in node: pn.Append(iu(x), iu(y))
        ps.BooleanAdd(pn); ps.Simplify()
        o = ps.COutline(0); phase_pts = [(o.CPoint(k).x / MM, o.CPoint(k).y / MM) for k in range(o.PointCount())]
        zone(f'M{esc}_PH_{ph}_F', s + f'PH_{ph}', 'F', TP(phase_pts),
             V(T(xc + 1.5, 63.6), 40, [('B', s + f'PH_{ph}')], 1.0, TP(R(ux0, 48.5, ux1, 63.6))))
        zone(f'M{esc}_PH_{ph}_B', s + f'PH_{ph}', 'B', TP(up))
        zone(f'M{esc}_VBUS_{ph}', 'VBUS', 'F',
             TP([(xc - 8.2, 64.65), (xc - 3.0, 64.65), (xc - 3.0, 69.9), (xc - 0.9, 69.9), (xc - 0.9, 72.0), (xc - 8.2, 72.0)]),
             V(T(xc - 5.5, 69.7), 8, [('In2', 'VBUS')]))
        zone(f'M{esc}_SP{ph}', s + f'SP{ph}', 'F', TP(R(xc + 6.4, 65.7, xc + 8.4, 74.1)))
        zone(f'M{esc}_GND_SH{ph}', 'GND', 'F',
             TP([(xc - 8.2, 72.35), (xc + 0.45, 72.35), (xc + 0.45, 70.1), (xc + 2.4, 70.1), (xc + 2.4, 74.75), (xc - 8.2, 74.75)]),
             V(T(xc + 1.4, 74.3), 10, [('In1', 'GND')], 1.3))
    zone(f'M{esc}_VBUS_C{esc}27', 'VBUS', 'F', TP(R(132.6, 75.05, 137.6, 76.75)), V(T(135.6, 75.9), 3, [('In2', 'VBUS')]))
# bulk electrolytics (not mirrored: both pairs sit in the x 104-126 column)
zone('M1_VBUS_BULK', 'VBUS', 'F', [(111.0, 64.65), (114.0, 64.65), (114.0, 72.05), (113.5, 72.05), (113.5, 75.4), (122.7, 75.4),
                                   (122.7, 80.6), (107.8, 80.6), (107.8, 75.4), (111.0, 75.4)], V((115.1, 78.0), 24, [('In2', 'VBUS')]))
zone('M2_VBUS_BULK', 'VBUS', 'F', [(107.0, 130.4), (122.4, 130.4), (122.4, 135.6), (111.0, 135.6), (111.0, 141.8), (107.0, 141.8)],
     V((114.4, 133.0), 24, [('In2', 'VBUS')]))
# In2 VBUS finger under Q405 / C425 / C426: the main In2 VBUS plane stops at x 162 (+BATT beyond), Q405's drain is at x 161-166
zone('In2_VBUS_Q405', 'VBUS', 'In2', R(161.5, 141.6, 166.4, 149.6), prio=3)

# ------------------------------------------------------------------ 4. bus breaker: J1 -> R801 -> Q801 -> Q802 -> VBUS
zone('BRK_VBUS_F', 'VBUS', 'F', R(168.5, 48.5, 188.8, 67.3), V((175.5, 61.0), 40, [('In2', 'VBUS'), ('B', 'VBUS')]))
zone('BRK_VBUS_B', 'VBUS', 'B', R(168.5, 48.5, 188.8, 67.3))
zone('BRK_BUS_SRC', '/Bus_Breaker/BUS_SRC', 'F', [(180.0, 68.8), (188.6, 68.8), (188.6, 72.5), (187.0, 72.5), (187.0, 76.1),
                                                  (178.4, 76.1), (178.4, 72.6), (180.0, 72.6)])
zone('BRK_BUS_SNS_F', '/Bus_Breaker/BUS_SNS', 'F', [(178.3, 77.9), (188.8, 77.9), (188.8, 91.2), (185.5, 91.2), (185.5, 86.7), (178.3, 86.7)],
     V((187.0, 86.9), 8, [('B', '/Bus_Breaker/BUS_SNS')], 1.0, R(185.5, 86.3, 188.8, 91.2)))
zone('BRK_BUS_SNS_B', '/Bus_Breaker/BUS_SNS', 'B', [(178.3, 77.9), (188.8, 77.9), (188.8, 91.5), (185.4, 91.5), (185.4, 86.0), (178.3, 86.0)])
zone('BRK_VBAT_IN_F', 'VBAT_IN', 'F', [(178.3, 87.2), (185.05, 87.2), (185.05, 91.55), (186.2, 91.55), (186.2, 98.6), (178.3, 98.6)],
     V((181.5, 92.8), 36, [('B', 'VBAT_IN')]))
zone('BRK_VBAT_IN_J1', 'VBAT_IN', 'F', R(197.9, 85.8, 213.5, 106.2), V((206.0, 98.84), 30, [('B', 'VBAT_IN'), ('In2', 'VBAT_IN')]))
zone('BRK_VBAT_IN_B', 'VBAT_IN', 'B', [(178.3, 86.4), (185.0, 86.4), (185.0, 91.9), (189.2, 91.9), (189.2, 86.4), (213.5, 86.4),
                                       (213.5, 104.6), (178.3, 104.6)])

# ------------------------------------------------------------------ 5. logic branch + aux bucks
zone('V_FUSED', '/Power_Supply/V_FUSED', 'F', [(170.4, 100.4), (178.4, 100.4), (178.4, 99.0), (185.2, 99.0), (185.2, 112.2),
                                               (175.0, 112.2), (175.0, 105.6), (170.4, 105.6)])
zone('BATT_Q1', '+BATT', 'F', R(164.2, 99.7, 170.0, 104.0), V((166.5, 102.0), 9, [('In2', '+BATT')]))
zone('BATT_D2', '+BATT', 'F', R(171.5, 106.0, 174.65, 112.7), V((173.3, 112.2), 6, [('In2', '+BATT')]))   # merges with BATT_U511 below
# +24V buck U511 = TI LM70880 (2026-10-25), placement of buckplace.py: VIN die pad top-left with the input caps C524 /
# C520 above it bridging to the PGND pins 23-26, C522 left (GND via In1), bulk C523 / C521 further left (+BATT top, GND
# bottom); SW die pad top-right -> L520 pad 1; L520 pad 2 = ISNS_24 -> shunt R538 -> +24V (R538 / C531 / C529).
zone('BATT_U511', '+BATT', 'F', [(172.0, 112.4), (175.45, 112.4), (175.45, 120.9), (172.4, 120.9), (172.4, 119.35), (162.5, 119.35),
                                 (162.5, 116.6), (172.0, 116.6)], V((173.9, 112.9), 8, [('In2', '+BATT')]))
zone('BATT_R520', '+BATT', 'F', R(170.2, 127.25, 171.8, 129.9), V((171.0, 129.3), 2, [('In2', '+BATT')]))   # R520 (UVLO top) +BATT pad
zone('GND_U511', 'GND', 'F', R(175.85, 112.6, 181.3, 118.72), V((179.6, 114.6), 10, [('In1', 'GND')], 1.2))  # C524/C520 GND + PGND 23-26
zone('GND_C522', 'GND', 'F', R(167.8, 112.95, 171.65, 116.35), V((168.9, 114.6), 6, [('In1', 'GND')], 1.2))
zone('GND_C523_C521', 'GND', 'F', R(162.5, 119.6, 168.9, 122.6), V((165.7, 120.6), 6, [('In1', 'GND')], 1.2))
zone('SW_24', '/Brakes/SW_24', 'F', [(175.7, 119.0), (181.6, 119.0), (181.6, 118.0), (185.3, 118.0), (185.3, 124.0), (181.6, 124.0),
                                     (181.6, 121.25), (175.7, 121.25)])
for ref in ('U1', 'U511'):                   # exposed pads: solid copper so the thermal vias / pads are never starved
    if fp[ref].GetPosition().x > 214 * MM: continue   # staged off-board (U1 TPS54360B since 2026-10-24; U511 LM70880 until buckplace.py)
    if ref == 'U1':
        ep = padbb(ref, '9'); zone('GND_EP_U1_B', 'GND', 'B', grow(ep, 0.5)); zone('GND_EP_U1_F', 'GND', 'F', grow(ep, 0.0))
    else:                                     # LM70880: PGND pad 30 (F + B), VIN die pad on B.Cu as +BATT (its 6 thermal vias)
        ep = padbb(ref, '30'); vin = padbb(ref, '1')
        zone('GND_EP_U511_F', 'GND', 'F', grow(ep, 0.2))
        zone('GND_EP_U511_B', 'GND', 'B', grow(ep, 0.4))
        zone('BATT_EP_U511_B', '+BATT', 'B', grow(vin, 0.25))
zone('ISNS_24', '/Brakes/ISNS_24', 'F', [(192.8, 117.9), (196.6, 117.9), (196.6, 123.9), (200.0, 123.9), (200.0, 125.8), (192.8, 125.8)])
zone('24V_R538_C531_C529', '+24V', 'F', [(196.9, 126.9), (200.6, 126.9), (200.6, 128.9), (199.6, 128.9), (199.6, 132.4), (197.2, 132.4),
                                         (197.2, 136.2), (194.2, 136.2), (194.2, 130.3), (196.9, 130.3)],
     V((198.0, 131.0), 6, [('In2', '+24V')]))
for ref in ('C530', 'C532', 'C533'):         # output caps above L520: +24V through In2 only
    zone(f'24V_{ref}', '+24V', 'F', grow(padbb(ref, '1'), 0.9), V(((padbb(ref, '1')[0] + padbb(ref, '1')[2]) / 2, padbb(ref, '1')[3] + 0.5), 3, [('In2', '+24V')]))

# ------------------------------------------------------------------ 6. merge overlapping same-net pours, create zones
def sps(pts):
    s = pcbnew.SHAPE_POLY_SET(); s.NewOutline()
    for x, y in pts: s.Append(iu(x), iu(y))
    return s
merged = True
while merged:
    merged = False
    for i, A in enumerate(ZONES):
        for B_ in ZONES[i + 1:]:
            if (A['net'], A['layer'], A['prio']) != (B_['net'], B_['layer'], B_['prio']): continue
            s = sps(A['pts']); s.BooleanIntersection(sps(B_['pts']))
            if not s.OutlineCount(): continue
            u = sps(A['pts']); u.BooleanAdd(sps(B_['pts'])); u.Simplify()
            o = u.COutline(0); A['pts'] = [(o.CPoint(k).x / MM, o.CPoint(k).y / MM) for k in range(o.PointCount())]
            A['vias'] += B_['vias']; A['name'] += '+' + B_['name'][4:]; ZONES.remove(B_); merged = True; break
        if merged: break

ref = [z for z in b.Zones() if z.GetNetname() == 'GND'][0]
made = []
for Z in ZONES:
    z = pcbnew.ZONE(b); z.SetLayer(L[Z['layer']]); z.SetNet(b.FindNet(Z['net'])); z.SetAssignedPriority(Z['prio'])
    z.SetLocalClearance(ref.GetLocalClearance()); z.SetMinThickness(ref.GetMinThickness())
    z.SetThermalReliefGap(ref.GetThermalReliefGap()); z.SetThermalReliefSpokeWidth(ref.GetThermalReliefSpokeWidth())
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL); z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    z.SetZoneName(Z['name']); z.SetLocked(True)
    o = z.Outline(); o.NewOutline()
    for x, y in Z['pts']: o.Append(iu(x), iu(y))
    b.Add(z); made.append((Z, z))

# overlap check: my zones of different nets on one layer must not overlap (they share a priority)
for i, (A, za) in enumerate(made):
    for B_, zb in made[i + 1:]:
        if A['layer'] != B_['layer'] or A['net'] == B_['net']: continue
        s = pcbnew.SHAPE_POLY_SET(za.Outline()); s.BooleanIntersection(zb.Outline())
        if s.OutlineCount() and s.Area() > 0: print('WARNING overlap', A['name'], B_['name'], s.Area() / MM / MM)

# ------------------------------------------------------------------ 7. via arrays
pads = []                                     # (net, x0, y0, x1, y1, smd_F, th)
for f in b.GetFootprints():
    for p in f.Pads():
        if not p.IsOnCopperLayer() and p.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH: continue
        bb = p.GetBoundingBox()
        th = p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
        pads.append((p.GetNetname(), bb.GetX() / MM, bb.GetY() / MM, bb.GetRight() / MM, bb.GetBottom() / MM, th))
CELL = 2.0
grid = {}
for k, pd in enumerate(pads):
    for gx in range(int(pd[1] // CELL) - 1, int(pd[3] // CELL) + 2):
        for gy in range(int(pd[2] // CELL) - 1, int(pd[4] // CELL) + 2): grid.setdefault((gx, gy), []).append(k)
segs = [(t.GetNetname(), t.GetStart().x / MM, t.GetStart().y / MM, t.GetEnd().x / MM, t.GetEnd().y / MM, t.GetWidth() / MM)
        for t in b.GetTracks() if t.Type() in (pcbnew.PCB_TRACE_T, pcbnew.PCB_ARC_T)]
vias = [(t.GetNetname(), t.GetPosition().x / MM, t.GetPosition().y / MM, t.GetWidth(pcbnew.F_Cu) / MM)
        for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
# keep-outs: gate-drive pads (2.0 mm) and control/sense pads of the breaker and bucks (1.5 mm)
GATE = ['/ESC_Motor_*/G[HL]?', '/ESC_Motor_*/G[HL]?_G']
CTRL = ['/Bus_Breaker/BUS_GATE', '/Bus_Breaker/PRE_G', '/Bus_Breaker/BUS_CSP', '/Power_Supply/Q1_GATE', '/M?_SENS_*',
        '/ESC_Motor_*/SP?']
BUCK = ['/Brakes/FB_*', '/Brakes/COMP_*', '/Brakes/CZ_*', '/Brakes/RT_*', '/Brakes/EN_*', '/Brakes/BOOT*', '/Brakes/CFG_*',
        '/Brakes/VCC_*', '/Brakes/VDDA_*']
keep = []
for n, x0, y0, x1, y1, th in pads:
    r = 2.0 if any(fnmatch.fnmatchcase(n, g) for g in GATE) else 1.5 if any(fnmatch.fnmatchcase(n, g) for g in CTRL) \
        else 1.0 if any(fnmatch.fnmatchcase(n, g) for g in BUCK) else 0
    if r: keep.append((x0 - r, y0 - r, x1 + r, y1 + r))
def rectd(x, y, x0, y0, x1, y1): return math.hypot(max(x0 - x, 0, x - x1), max(y0 - y, 0, y - y1))
in2 = [(z.GetNetname(), z.GetAssignedPriority(), poly_pts(z)) for z in b.Zones() if z.GetLayer() == pcbnew.In2_Cu]
in1 = [poly_pts(z) for z in b.Zones() if z.GetLayer() == pcbnew.In1_Cu and z.GetNetname() == 'GND']
mine = [(Z['net'], Z['layer'], Z['pts']) for Z in ZONES]
r = VIA_D / 2

def target_ok(x, y, layer, net):
    if layer == 'In1': return any(pip((x, y), p) and dedge((x, y), p) >= 0.7 for p in in1)
    if layer == 'In2':
        tz = [(pr, p) for n, pr, p in in2 if n == net and pip((x, y), p) and dedge((x, y), p) >= 0.7]
        if not tz: return False
        pr = max(t[0] for t in tz)
        return not any(n != net and q >= pr and (pip((x, y), p) or dedge((x, y), p) < 0.7) for n, q, p in in2)
    return any(n == net and l == layer and pip((x, y), p) and dedge((x, y), p) >= 0.5 for n, l, p in mine)

def ok(x, y, net, region, placed):
    if not (45.9 <= x <= 213.1 and 48.9 <= y <= 165.1): return False
    if not pip((x, y), region) or dedge((x, y), region) < r + 0.05: return False
    for k in grid.get((int(x // CELL), int(y // CELL)), ()):
        n, x0, y0, x1, y1, th = pads[k]
        d = rectd(x, y, x0, y0, x1, y1) - r
        if d < (0.3 if n != net else 0.15 if th else 0.05): return False
    for kx0, ky0, kx1, ky1 in keep:
        if kx0 <= x <= kx1 and ky0 <= y <= ky1: return False
    for n, x0, y0, x1, y1, w in segs:
        if n != net and dseg((x, y), (x0, y0), (x1, y1)) - w / 2 - r < 0.3: return False
    for n, vx, vy, vd in vias + placed:
        d = math.hypot(x - vx, y - vy)
        if d < (vd / 2 + r + 0.3 if n != net else 0.75): return False
    for n, l, p in mine:                       # never inside / next to my pours of another net (any layer)
        if n != net and (pip((x, y), p) or dedge((x, y), p) < r + 0.3): return False
    return True

group = pcbnew.PCB_GROUP(b); group.SetName(GROUP); b.Add(group)
placed, report = [], []
for Z, S in [(Z, S) for Z in ZONES for S in Z['vias']]:
    region = S['region']
    xs, ys = [p[0] for p in region], [p[1] for p in region]
    ax, ay = S['anchor']
    cand = [(min(xs) + i * 0.2, min(ys) + j * 0.2) for i in range(int((max(xs) - min(xs)) / 0.2) + 1)
            for j in range(int((max(ys) - min(ys)) / 0.2) + 1)]
    cand.sort(key=lambda c: math.hypot(c[0] - ax, c[1] - ay))
    got = []
    for x, y in cand:
        if len(got) >= S['max']: break
        if any(math.hypot(x - gx, y - gy) < S['pitch'] for gx, gy in got): continue
        if not ok(x, y, Z['net'], region, placed): continue
        if not any(target_ok(x, y, l, n) for l, n in S['targets']): continue
        got.append((x, y)); placed.append((Z['net'], x, y, VIA_D))
    net = b.FindNet(Z['net'])
    for x, y in got:
        v = pcbnew.PCB_VIA(b); v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetPosition(pcbnew.VECTOR2I(iu(x), iu(y))); v.SetWidth(iu(VIA_D)); v.SetDrill(iu(VIA_DRILL)); v.SetNet(net)
        v.SetLocked(True); b.Add(v); group.AddItem(v)
    report.append((Z['name'], len(got), S['max']))

# ------------------------------------------------------------------ 8. fill + save
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(P)
print(f'{len(ZONES)} PWR_ zones, {len(placed)} vias')
for Z, z in made:
    rr = [(n, m) for nm, n, m in report if nm == Z['name']]
    nv = f'{sum(n for n, m in rr)}/{sum(m for n, m in rr)} vias' if rr else ''
    print(f"  {Z['name']:30s} {Z['layer']:3s} {Z['net'][:24]:24s} {z.GetFilledArea() / MM / MM:7.1f} mm2 "
          f"{z.GetFilledPolysList(L[Z['layer']]).OutlineCount()} piece(s) {nv}")
