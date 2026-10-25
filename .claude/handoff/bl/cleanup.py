"""Stage 4: post-autoroute cleanup (after `autoroute.py import`). KiCad must be CLOSED.
Usage: python cleanup.py <board.kicad_pcb> [--rip-pour-crossers]   (.kicad_pro + schematic next to it; kicad-cli on PATH)
 --rip-pour-crossers: also rip autorouted copper that cuts a PWR_* pour into islands and reroute it outside the pours
 (heals all 17 split pours; leaves ~13 more connections for hand routing). Two islands of a PWR_ pour are never
 bridged with a track (needs copper, reported instead).

Touches only UNLOCKED tracks/vias (Freerouting's) plus what it adds; locked pre-routes, zones and footprints stay.
Everything it adds goes into the PCB group `cleanup_routes`, which is deleted and rebuilt on every run (idempotent:
the fixes to unlocked items are projections, and the router is deterministic).
 1. S0: delete the old group; exact clearance check of every unlocked track/via against all copper, holes and the
    edge (KiCad's own shapes): violators are ripped (U513 BRK_*, CAN_H over the LOGO1 copper); neck-downs < 0.15 mm
    are widened to the net-class width, else 0.15, else ripped; then dangling unlocked copper is removed.
 2. Fill, clusters per net (KiCad connectivity). A cluster of a plane net (GND -> In1, +3V3 / VBUS / VBAT_IN / +BATT
    / +24V -> In2) not on its plane gets a stub + via into the plane (0.6/0.3; power 0.8/0.4, +3V3 falls back to
    0.6/0.3) where the plane covers the spot. GND pads with a starved thermal get the same stub + via.
 3. Other clusters are joined by a 2-layer grid A* router (0.05 mm grid, 45-degree moves, string-pulled), short
    connections only (MAX_ROUTE mm); the rest are listed.
 Obstacles: other nets' copper (net-class / pad / footprint clearance), holes (0.25), edge (0.3), rule areas,
 other nets' PWR_* pour outlines (no new copper or vias inside them), courtyards (no vias except the endpoint's
 own footprint), no via in pad. A DRC pass (kicad-cli) then removes any added unit that shows up in an error or
 creates a new starved thermal / isolated island, and the router retries with a larger margin.
Prints a summary; report: .claude/handoff/cleanup_report.md"""
import subprocess as _sp; assert _sp.run(['pgrep', '-x', 'kicad'], capture_output=True).returncode, 'KiCad is running: close it (without saving) first'
import sys  # noqa: E402
import os  # noqa: E402
import math  # noqa: E402
import json  # noqa: E402
import heapq  # noqa: E402
import tempfile  # noqa: E402
import collections  # noqa: E402
import time  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.path import Path  # noqa: E402
import pcbnew  # noqa: E402

P = sys.argv[1]
assert P.endswith('.kicad_pcb'), 'board path must end in .kicad_pcb'
RIP_POUR = '--rip-pour-crossers' in sys.argv[2:]   # also rip autorouted copper that splits a PWR_* pour into islands
MM = 1e6
GROUP = 'cleanup_routes'
G = 0.05                    # router grid (mm); cell centres on multiples of G
MARGIN = 0.01               # raster safety margin (mm), raised on DRC retries
MAX_ROUTE = 200.0           # longest connection (manhattan, mm) the router tries (beyond 45 mm: via budget, wider window)
VIA_SIG, VIA_PWR, VIA_LV = (0.6, 0.3), (0.8, 0.4), (0.6, 0.3)
PLANE_NETS = {'GND': 'In1', '+3V3': 'In2', 'VBUS': 'In2', 'VBAT_IN': 'In2', '+BATT': 'In2', '+24V': 'In2'}
HOLE_CLR, EDGE_CLR, H2H = 0.25, 0.3, 0.15
T0 = time.time()
def log(*a): print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)
def iu(v): return int(round(v * MM))

b = pcbnew.LoadBoard(P)
CU = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
LI = {ly: i for i, ly in enumerate(CU)}            # copper layer -> index 0..3 (0 = F, 3 = B)
RL = (0, 3)                                       # routing layers (F, B)
_gone = []                                        # keep removed SWIG objects alive (freeing them corrupts the board)
def drop(item): b.RemoveNative(item); _gone.append(item)
def uid(item): return item.m_Uuid.AsString()

# ---------------------------------------------------------------- 1. remove the previous run's group
old = 0
for g in [g for g in b.Groups() if g.GetName() == GROUP]:
    for it in list(g.GetItems()): g.RemoveItem(it); drop(it); old += 1
    drop(g)
log(f'removed {old} items of the old {GROUP} group')

def net_clearance(netname):
    t = pcbnew.PCB_TRACK(b); t.SetNet(b.FindNet(netname)); t.SetLayer(pcbnew.F_Cu); b.Add(t)
    c = t.GetOwnClearance(pcbnew.F_Cu) / MM; w = t.GetNetClassName(); drop(t); return c, w
NC = {}
def ncl(net):
    if net not in NC: NC[net] = net_clearance(net)
    return NC[net]
CLASS_W = {'Default': 0.2, 'Power_LV': 0.5, 'Power_HV': 2.0, 'Power_Shunt': 2.0, 'Gate_Drive': 0.4}

# ---------------------------------------------------------------- 2. exact checker (KiCad shapes, spatial hash)
class Exact:
    CELL = 1.0
    def __init__(self):
        self.h = collections.defaultdict(list); self.recs = []
        ps = pcbnew.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(ps, False)
        self.edges = []
        for i in range(ps.OutlineCount()):
            o = ps.COutline(i)
            for k in range(o.SegmentCount()): self.edges.append(o.CSegment(k))
        for f in b.GetFootprints():
            for p in f.Pads():
                for ly in CU:
                    if p.IsOnLayer(ly) and p.FlashLayer(ly):
                        self.add('cu', p, ly, p.GetEffectiveShape(ly), p.GetNetCode(), p.GetOwnClearance(ly))
                if p.HasHole(): self.add('hole', p, None, p.GetEffectiveHoleShape(), p.GetNetCode(), 0)
            for s in f.GraphicalItems():
                if s.GetLayer() in LI: self.add('cu', s, s.GetLayer(), s.GetEffectiveShape(s.GetLayer()), s.GetNetCode(), iu(0.15))
        for t in b.GetTracks(): self.add_track(t)
    def add(self, kind, item, layer, shape, net, clr):
        bb = shape.BBox()
        rec = (kind, item, layer, shape, net, clr, uid(item)); self.recs.append(rec)
        for cx in range(int(bb.GetX() / MM // self.CELL), int(bb.GetRight() / MM // self.CELL) + 1):
            for cy in range(int(bb.GetY() / MM // self.CELL), int(bb.GetBottom() / MM // self.CELL) + 1):
                self.h[(cx, cy)].append(rec)
    def add_track(self, t):
        if t.Type() == pcbnew.PCB_VIA_T:
            for ly in CU: self.add('cu', t, ly, t.GetEffectiveShape(ly), t.GetNetCode(), t.GetOwnClearance(ly))
            self.add('hole', t, None, t.GetEffectiveHoleShape(), t.GetNetCode(), 0)
        else:
            self.add('cu', t, t.GetLayer(), t.GetEffectiveShape(t.GetLayer()), t.GetNetCode(), t.GetOwnClearance(t.GetLayer()))
    def near(self, bb, grow):
        out = {}
        g = grow / MM
        for cx in range(int((bb.GetX() / MM - g) // self.CELL), int((bb.GetRight() / MM + g) // self.CELL) + 1):
            for cy in range(int((bb.GetY() / MM - g) // self.CELL), int((bb.GetBottom() / MM + g) // self.CELL) + 1):
                for r in self.h.get((cx, cy), ()): out[id(r)] = r
        return out.values()
    def violations(self, item, dead=()):
        """[(kind, other uuid)] for a track or via against everything else (other nets)."""
        net, me = item.GetNetCode(), uid(item); out = []
        if item.Type() == pcbnew.PCB_VIA_T:
            mine = [(ly, item.GetEffectiveShape(ly)) for ly in CU]; hole = item.GetEffectiveHoleShape()
        else:
            mine = [(item.GetLayer(), item.GetEffectiveShape(item.GetLayer()))]; hole = None
        bb = item.GetBoundingBox()
        for kind, it, layer, shape, onet, oclr, ou in self.near(bb, iu(0.6)):
            if ou == me or ou in dead: continue
            other_net = onet != net or onet == 0
            if kind == 'cu':
                if not other_net: continue
                for ly, s in mine:
                    if ly != layer: continue
                    c = max(item.GetOwnClearance(ly), oclr)
                    if s.Collide(shape, c - 1): out.append(('clearance', ou)); break
                if hole is not None and other_net and hole.Collide(shape, iu(HOLE_CLR) - 1): out.append(('hole', ou))
            elif kind == 'hole':
                if hole is not None and hole.Collide(shape, iu(H2H) - 1) and other_net: out.append(('h2h', ou))
                if other_net and any(s.Collide(shape, iu(HOLE_CLR) - 1) for ly, s in mine): out.append(('hole', ou))
        for ly, s in mine:
            if any(s.Collide(e, iu(EDGE_CLR) - 1) for e in self.edges): out.append(('edge', None)); break
        return out

# ---------------------------------------------------------------- 3. S0: rip violators, fix neck-downs, drop dangling
EX = Exact()
log(f'exact index: {len(EX.recs)} shapes')
unlocked = [t for t in b.GetTracks() if not t.IsLocked()]
rip, rip_why = set(), collections.Counter()
for t in unlocked:
    v = EX.violations(t)
    if v: rip.add(uid(t)); rip_why[('clearance', t.GetNetname())] += 1
# neck-downs: widen to the class width, else 0.15, else rip
widened, narrow_rip = [], []
for t in unlocked:
    if t.Type() != pcbnew.PCB_TRACE_T or uid(t) in rip or t.GetWidth() >= iu(0.15) - 1: continue
    w0 = t.GetWidth(); ok = False
    for w in sorted({CLASS_W.get(ncl(t.GetNetname())[1], 0.2), 0.2, 0.15}, reverse=True):
        if iu(w) <= w0: continue
        t.SetWidth(iu(w))
        if not EX.violations(t): ok = True; widened.append((t.GetNetname(), w0 / MM, w)); break
    if not ok:
        t.SetWidth(w0); rip.add(uid(t)); narrow_rip.append(t.GetNetname()); rip_why[('narrow', t.GetNetname())] += 1
# rip whole branches: delete the offenders, then iteratively delete dangling unlocked copper
# autorouted copper that cuts a PWR_* pour into islands (Freerouting saw the pours as planes and routed through them)
splitters = collections.Counter()
if RIP_POUR:
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    for z in sorted([z for z in b.Zones() if z.GetZoneName().startswith('PWR_')], key=lambda z: z.GetZoneName()):
        for ly in z.GetLayerSet().CuStack():
            if ly not in LI or z.GetFilledPolysList(ly).OutlineCount() < 2: continue
            for t in unlocked:
                if uid(t) in rip or t.GetNetCode() == z.GetNetCode(): continue
                if t.Type() == pcbnew.PCB_VIA_T: hit = z.Outline().Collide(t.GetPosition(), t.GetWidth(ly) // 2)
                else: hit = t.GetLayer() == ly and z.Outline().Collide(pcbnew.SEG(t.GetStart(), t.GetEnd()), t.GetWidth() // 2)
                if hit: rip.add(uid(t)); splitters[t.GetNetname()] += 1; rip_why[('pour', t.GetNetname())] += 1
by_uid = {uid(t): t for t in b.GetTracks()}
for u in rip: drop(by_uid[u])
log(f'S0: ripped {len(rip)} violators {dict(rip_why)}; widened {len(widened)} neck-downs')

def dangling_pass():
    """Remove unlocked tracks with a free end / unlocked vias with < 2 connections (geometric, conservative)."""
    removed = 0
    zone_outl = collections.defaultdict(list)
    for z in b.Zones():
        if z.GetIsRuleArea(): continue
        for ly in z.GetLayerSet().CuStack():
            if ly in LI: zone_outl[(z.GetNetCode(), ly)].append(z.GetFilledPolysList(ly))   # the fill, as KiCad sees it
    while True:
        tr = list(b.GetTracks())
        idx = collections.defaultdict(list)
        def key(x, y): return (int(x // 1000000), int(y // 1000000))
        for t in tr:
            bb = t.GetBoundingBox()
            for cx in range(bb.GetX() // 1000000, bb.GetRight() // 1000000 + 1):
                for cy in range(bb.GetY() // 1000000, bb.GetBottom() // 1000000 + 1): idx[(cx, cy)].append(t)
        pads = collections.defaultdict(list)
        for f in b.GetFootprints():
            for p in f.Pads():
                bb = p.GetBoundingBox()
                for cx in range(bb.GetX() // 1000000, bb.GetRight() // 1000000 + 1):
                    for cy in range(bb.GetY() // 1000000, bb.GetBottom() // 1000000 + 1): pads[(cx, cy)].append(p)
        def touches(pt, layer, net, me):
            n = 0
            v = pcbnew.VECTOR2I(pt.x, pt.y)
            for p in pads.get(key(pt.x, pt.y), ()):
                if p.GetNetCode() == net and p.IsOnLayer(layer) and p.GetEffectiveShape(layer).Collide(v, 0): n += 1
            for t in idx.get(key(pt.x, pt.y), ()):
                if t is me or t.GetNetCode() != net: continue
                if t.Type() == pcbnew.PCB_VIA_T:
                    if t.GetEffectiveShape(layer).Collide(v, 0): n += 1
                elif t.GetLayer() == layer and t.GetEffectiveShape(layer).Collide(v, 0): n += 1
            return n
        dead = []
        for t in tr:
            if t.IsLocked(): continue
            if t.Type() == pcbnew.PCB_VIA_T:
                c = 0; v = t.GetPosition()
                for ly in CU:
                    for o in idx.get(key(v.x, v.y), ()):
                        if o is t or o.GetNetCode() != t.GetNetCode() or o.Type() == pcbnew.PCB_VIA_T or o.GetLayer() != ly: continue
                        if o.GetEffectiveShape(ly).Collide(pcbnew.VECTOR2I(o.GetStart()), t.GetWidth(ly) // 2) or \
                           o.GetEffectiveShape(ly).Collide(pcbnew.VECTOR2I(o.GetEnd()), t.GetWidth(ly) // 2):
                            if t.GetEffectiveShape(ly).Collide(o.GetEffectiveShape(ly), 0): c += 1
                    for p in pads.get(key(v.x, v.y), ()):
                        if p.GetNetCode() == t.GetNetCode() and p.IsOnLayer(ly) and p.GetEffectiveShape(ly).Collide(v, 0): c += 1
                inz = any(o.Collide(v, 0) for ly in CU for o in zone_outl.get((t.GetNetCode(), ly), ()))
                if c == 0 or (c == 1 and not inz): dead.append(t)
                continue
            ly = t.GetLayer()
            for pt in (t.GetStart(), t.GetEnd()):
                if touches(pt, ly, t.GetNetCode(), t): continue
                if any(o.Collide(pcbnew.VECTOR2I(pt.x, pt.y), 0) for o in zone_outl.get((t.GetNetCode(), ly), ())): continue
                dead.append(t); break
        if not dead: return removed
        for t in dead: drop(t)
        removed += len(dead)
n_dang = dangling_pass()
log(f'S0: removed {n_dang} dangling unlocked items')

def drc(path):
    out = tempfile.mktemp(suffix='.json', dir=os.path.dirname(os.path.abspath(path)))
    _sp.run(['kicad-cli', 'pcb', 'drc', '--refill-zones', '--format', 'json', '-o', out, path], capture_output=True)
    d = json.load(open(out)); os.remove(out); return d
ERR = {'clearance', 'shorting_items', 'track_width', 'tracks_crossing', 'track_dangling', 'via_dangling', 'hole_clearance',
       'courtyards_overlap', 'copper_edge_clearance', 'isolated_copper', 'solder_mask_bridge', 'items_not_allowed',
       'annular_width', 'hole_to_hole', 'holes_co_located', 'drill_out_of_range', 'via_diameter', 'connection_width'}

def fill():
    pcbnew.ZONE_FILLER(b).Fill(b.Zones()); b.BuildConnectivity()
# baseline DRC of S0 (no added copper): KiCad's dangling verdicts on unlocked copper are applied too (until none),
# and the starved thermals / islands that already exist are recorded
while True:
    fill(); b.Save(P)
    d0 = drc(P)
    tu = {uid(t): t for t in b.GetTracks() if not t.IsLocked()}
    dd = {i['uuid'] for v in d0['violations'] if v['type'] in ('track_dangling', 'via_dangling') for i in v['items'] if i['uuid'] in tu}
    if not dd: break
    for u in dd: drop(tu[u])
    n_dang += len(dd) + dangling_pass(); log(f'S0: KiCad dangling: removed {len(dd)} more (+ their chains)')
base_starved = {it['uuid'] for v in d0['violations'] if v['type'] == 'starved_thermal' for it in v['items']}
base_iso = {(round(v['items'][0]['pos']['x'], 1), round(v['items'][0]['pos']['y'], 1)) for v in d0['violations'] if v['type'] == 'isolated_copper'}
base_err = collections.Counter(v['type'] for v in d0['violations'] if v['type'] in ERR)
log(f'S0 DRC: errors {dict(base_err)}, starved {sum(v["type"] == "starved_thermal" for v in d0["violations"])}, unrouted {len(d0["unconnected_items"])}')

# ---------------------------------------------------------------- 4. raster obstacle maps
bbe = b.GetBoardEdgesBoundingBox()
X0 = math.floor(bbe.GetX() / MM / G) * G - 10 * G
Y0 = math.floor(bbe.GetY() / MM / G) * G - 10 * G
W = int(math.ceil((bbe.GetRight() / MM - X0) / G)) + 20
H = int(math.ceil((bbe.GetBottom() / MM - Y0) / G)) + 20
def cx(i): return X0 + i * G
def rng(x0, y0, x1, y1):
    i0 = max(0, int(math.floor((x0 - X0) / G))); i1 = min(W, int(math.ceil((x1 - X0) / G)) + 1)
    j0 = max(0, int(math.floor((y0 - Y0) / G))); j1 = min(H, int(math.ceil((y1 - Y0) / G)) + 1)
    return i0, i1, j0, j1

def poly_list(ps):
    out = []
    for i in range(ps.OutlineCount()):
        o = ps.COutline(i)
        pts = np.array([(o.CPoint(k).x / MM, o.CPoint(k).y / MM) for k in range(o.PointCount())])
        if len(pts) >= 3: out.append(pts)
    return out
def item_polys(item, layer):
    ps = pcbnew.SHAPE_POLY_SET(); item.TransformShapeToPolygon(ps, layer, 0, iu(0.002), pcbnew.ERROR_OUTSIDE)
    return poly_list(ps)

class Prim:
    __slots__ = ('kind', 'layers', 'net', 'clr', 'cap', 'pts', 'path', 'bb', 'fp', 'pad', 'owner')
    def __init__(self, kind, layers, net, clr, cap=None, pts=None, fp=-1, pad=False, owner=None):
        self.kind, self.layers, self.net, self.clr, self.cap, self.fp, self.pad, self.owner = kind, layers, net, clr, cap, fp, pad, owner
        self.pts = pts; self.path = Path(pts) if pts is not None else None
        if cap is not None:
            ax, ay, bx, by, r = cap; self.bb = (min(ax, bx) - r, min(ay, by) - r, max(ax, bx) + r, max(ay, by) + r)
        else:
            self.bb = (pts[:, 0].min(), pts[:, 1].min(), pts[:, 0].max(), pts[:, 1].max())
    def dist(self, px, py):
        if self.cap is not None:
            ax, ay, bx, by, r = self.cap; dx, dy = bx - ax, by - ay; l2 = dx * dx + dy * dy
            if l2 == 0: return np.hypot(px - ax, py - ay) - r
            t = np.clip(((px - ax) * dx + (py - ay) * dy) / l2, 0, 1)
            return np.hypot(px - ax - t * dx, py - ay - t * dy) - r
        a = self.pts; c = np.roll(a, -1, 0); d = c - a; l2 = (d * d).sum(1); l2[l2 == 0] = 1e-12
        X = px.reshape(-1, 1); Y = py.reshape(-1, 1)
        t = np.clip(((X - a[:, 0]) * d[:, 0] + (Y - a[:, 1]) * d[:, 1]) / l2, 0, 1)
        dd = np.hypot(X - a[:, 0] - t * d[:, 0], Y - a[:, 1] - t * d[:, 1]).min(1)
        inside = self.path.contains_points(np.stack([px.ravel(), py.ravel()], 1))
        dd[inside] = 0
        return dd.reshape(px.shape)

PRIMS = []
FPS = sorted(b.GetFootprints(), key=lambda f: (f.GetReference(), uid(f))); FPI = {uid(f): i for i, f in enumerate(FPS)}
def nlabel(n): return n if n > 0 else -1
def prims_of_track(t, owner=None):
    out = []
    if t.Type() == pcbnew.PCB_VIA_T:
        p = t.GetPosition(); x, y = p.x / MM, p.y / MM
        out.append(Prim('cu', (0, 1, 2, 3), nlabel(t.GetNetCode()), t.GetOwnClearance(pcbnew.F_Cu) / MM, cap=(x, y, x, y, t.GetWidth(pcbnew.F_Cu) / MM / 2), owner=owner))
        out.append(Prim('hole', (0, 1, 2, 3), nlabel(t.GetNetCode()), 0, cap=(x, y, x, y, t.GetDrill() / MM / 2), owner=owner))
    else:
        s, e = t.GetStart(), t.GetEnd()
        out.append(Prim('cu', (LI[t.GetLayer()],), nlabel(t.GetNetCode()), t.GetOwnClearance(t.GetLayer()) / MM,
                        cap=(s.x / MM, s.y / MM, e.x / MM, e.y / MM, t.GetWidth() / MM / 2), owner=owner))
    return out
def build_prims():
    for fi, f in enumerate(FPS):
        for p in f.Pads():
            for ly in CU:
                if p.IsOnLayer(ly) and p.FlashLayer(ly):
                    for pts in item_polys(p, ly):
                        PRIMS.append(Prim('cu', (LI[ly],), nlabel(p.GetNetCode()), p.GetOwnClearance(ly) / MM, pts=pts, fp=fi, pad=True))
            if p.HasHole():
                hs = p.GetEffectiveHoleShape(); sg = hs.GetSeg()
                PRIMS.append(Prim('hole', (0, 1, 2, 3), nlabel(p.GetNetCode()), 0,
                                  cap=(sg.A.x / MM, sg.A.y / MM, sg.B.x / MM, sg.B.y / MM, hs.GetWidth() / MM / 2), fp=fi))
        for s in f.GraphicalItems():
            if s.GetLayer() in LI:
                for pts in item_polys(s, s.GetLayer()): PRIMS.append(Prim('cu', (LI[s.GetLayer()],), -1, 0.15, pts=pts, fp=fi))
            elif s.GetLayer() in (pcbnew.F_CrtYd, pcbnew.B_CrtYd): pass
        for side in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
            cy = f.GetCourtyard(side)
            for pts in poly_list(cy): PRIMS.append(Prim('court', (0, 1, 2, 3), -1, 0, pts=pts, fp=fi))
        for z in f.Zones():
            if z.GetIsRuleArea(): add_rule_area(z)
    for t in b.GetTracks(): PRIMS.extend(prims_of_track(t))
    for z in b.Zones():
        if z.GetIsRuleArea(): add_rule_area(z)
        elif z.GetZoneName().startswith('PWR_'):
            ls = tuple(LI[ly] for ly in z.GetLayerSet().CuStack() if ly in LI)
            for pts in poly_list(z.Outline()): PRIMS.append(Prim('pz', ls, nlabel(z.GetNetCode()), 0, pts=pts))
    ps = pcbnew.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(ps, False)
    for pts in poly_list(ps):
        for k in range(len(pts)):
            a, c = pts[k], pts[(k + 1) % len(pts)]
            PRIMS.append(Prim('edge', (0, 1, 2, 3), -1, 0, cap=(a[0], a[1], c[0], c[1], 0)))
    return ps
def add_rule_area(z):
    ls = tuple(LI[ly] for ly in z.GetLayerSet().CuStack() if ly in LI)
    for pts in poly_list(z.Outline()):
        if z.GetDoNotAllowTracks(): PRIMS.append(Prim('keept', ls, -1, 0, pts=pts))
        if z.GetDoNotAllowVias(): PRIMS.append(Prim('keepv', ls, -1, 0, pts=pts))

OUTLINE = build_prims()
log(f'raster prims: {len(PRIMS)}')
# inside-board mask (cell centres inside the outline)
yy, xx = np.mgrid[0:H, 0:W]
INB = np.zeros((H, W), bool)
for pts in poly_list(OUTLINE): INB |= Path(pts).contains_points(np.stack([X0 + xx.ravel() * G, Y0 + yy.ravel() * G], 1)).reshape(H, W)
del xx, yy

def stamp(arr, pr, req, val):
    x0, y0, x1, y1 = pr.bb
    i0, i1, j0, j1 = rng(x0 - req, y0 - req, x1 + req, y1 + req)
    if i0 >= i1 or j0 >= j1: return
    px, py = np.meshgrid(X0 + np.arange(i0, i1) * G, Y0 + np.arange(j0, j1) * G)
    m = pr.dist(px, py) < req
    if not m.any(): return
    sub = arr[j0:j1, i0:i1]
    if arr.dtype == bool: sub[m] = True; return
    sub[m & (sub == 0)] = val
    sub[m & (sub != 0) & (sub != val)] = -2

MODES = {}
def track_req(pr, li, cnew, hw, m):
    k = pr.kind
    if k == 'cu' and li in pr.layers: return max(cnew, pr.clr) + hw + m
    if k == 'hole': return HOLE_CLR + hw + m
    if k == 'edge': return EDGE_CLR + hw + m
    if k == 'keept' and li in pr.layers: return hw + m
    if k == 'pz' and li in pr.layers: return hw + m
    return None
def via_req(pr, rv, rh, cnew, m):
    k = pr.kind
    if k == 'cu': return max(max(cnew, pr.clr) + rv, HOLE_CLR + rh) + m
    if k == 'hole': return max(HOLE_CLR + rv, H2H + rh) + m
    if k == 'edge': return EDGE_CLR + rv + m
    if k in ('keepv', 'pz'): return rv + m
    return None
def stamp_track_mode(key, arr, pr):
    li, cnew, hw, m = key[1:]
    r = track_req(pr, li, cnew, hw, m)
    if r is not None: stamp(arr, pr, r, pr.net)
def stamp_via_mode(key, arrs, pr):
    rv, rh, cnew, m = key[1:]
    lab, court, padm = arrs
    r = via_req(pr, rv, rh, cnew, m)
    if r is not None: stamp(lab, pr, r, -1 if pr.kind == 'hole' else pr.net)   # hole-to-hole: any net
    if pr.kind == 'court': stamp(court, pr, rv, pr.fp + 1)
    if pr.kind == 'cu' and pr.pad and pr.layers[0] in RL: stamp(padm, pr, rv + 0.1, True)
def mode(key):
    if key in MODES: return MODES[key]
    t = time.time()
    if key[0] == 'T':
        arr = np.zeros((H, W), np.int32); arr[~INB] = -2
        for pr in PRIMS: stamp_track_mode(key, arr, pr)
        MODES[key] = arr
    else:
        arrs = (np.zeros((H, W), np.int32), np.zeros((H, W), np.int32), np.zeros((H, W), bool)); arrs[0][~INB] = -2
        for pr in PRIMS: stamp_via_mode(key, arrs, pr)
        MODES[key] = arrs
    log(f'  mode {key} built in {time.time() - t:.1f}s')
    return MODES[key]
def add_prims(prs):
    PRIMS.extend(prs)
    for key, a in MODES.items():
        for pr in prs: (stamp_track_mode if key[0] == 'T' else stamp_via_mode)(key, a, pr)

# plane coverage masks (via centre inside the plane outline, >= 0.7 mm from its edge and from other-net zones of
# the same or higher priority on that layer)
PLANE_MASK = {}
def plane_mask(net):
    if net in PLANE_MASK: return PLANE_MASK[net]
    lay = pcbnew.In1_Cu if PLANE_NETS[net] == 'In1' else pcbnew.In2_Cu
    zs = [z for z in b.Zones() if not z.GetIsRuleArea() and z.IsOnLayer(lay)]
    mine = [z for z in zs if z.GetNetname() == net]
    m = np.zeros((H, W), bool)
    for z in mine:
        for pts in poly_list(z.Outline()):
            pr = Prim('x', (0,), 0, 0, pts=pts)
            x0, y0, x1, y1 = pr.bb; i0, i1, j0, j1 = rng(x0, y0, x1, y1)
            px, py = np.meshgrid(X0 + np.arange(i0, i1) * G, Y0 + np.arange(j0, j1) * G)
            inside = pr.path.contains_points(np.stack([px.ravel(), py.ravel()], 1)).reshape(px.shape)
            a = pr.pts; c = np.roll(a, -1, 0)
            e = min_edge_dist(px, py, a, c)
            m[j0:j1, i0:i1] |= inside & (e >= 0.7)
    pr_min = min(z.GetAssignedPriority() for z in mine) if mine else 0
    neg = np.zeros((H, W), bool)
    for z in zs:
        if z.GetNetname() == net or z.GetAssignedPriority() < pr_min: continue
        for pts in poly_list(z.Outline()): stamp(neg, Prim('x', (0,), 0, 0, pts=pts), 0.7, True)
    m &= ~neg
    PLANE_MASK[net] = m
    return m
def min_edge_dist(px, py, a, c):
    out = np.full(px.shape, 1e9)
    for k in range(len(a)):
        pr = Prim('x', (0,), 0, 0, cap=(a[k][0], a[k][1], c[k][0], c[k][1], 0)); out = np.minimum(out, pr.dist(px, py))
    return out

# ---------------------------------------------------------------- 5. A* on a window
NB = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0), (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]
def astar(w, h, free, via_ok, srcs, tgt, via_cost, max_cost, hbox=None, max_exp=2500000):
    """free: {layer: bytearray(w*h)}, via_ok: bytearray or None, srcs: [(ly, k)], tgt: {layer: bytearray}.
    Returns [(ly, k), ...] from a source to a target, or None."""
    N = w * h; layers = sorted(free)
    INF = float('inf'); gs = {}
    par = {}
    heap = []
    def hfun(k):
        if hbox is None: return 0.0
        i, j = k % w, k // w; ti0, ti1, tj0, tj1 = hbox
        dx = max(ti0 - i, 0, i - ti1); dy = max(tj0 - j, 0, j - tj1)
        return max(dx, dy) + 0.4142 * min(dx, dy)
    for ly, k in srcs:
        s = ly * N + k
        if gs.get(s, INF) > 0: gs[s] = 0.0; par[s] = -1; heapq.heappush(heap, (hfun(k), 0.0, s))
    exp = 0
    while heap:
        f, g, s = heapq.heappop(heap)
        if g > gs.get(s, INF): continue
        ly, k = divmod(s, N)
        if tgt[ly][k]:
            path = []
            while s != -1: path.append(divmod(s, N)); s = par[s]
            return path[::-1]
        exp += 1
        if exp > max_exp or g > max_cost: return None
        fr = free[ly]; i, j = k % w, k // w
        for di, dj, c in NB:
            ni, nj = i + di, j + dj
            if ni < 0 or nj < 0 or ni >= w or nj >= h: continue
            nk = nj * w + ni
            if not fr[nk]: continue
            if di and dj and not (fr[j * w + ni] and fr[nj * w + i]): continue
            ns = ly * N + nk; ng = g + c
            if ng < gs.get(ns, INF): gs[ns] = ng; par[ns] = s; heapq.heappush(heap, (ng + hfun(nk), ng, ns))
        if via_ok is not None and via_ok[k]:
            for ol in layers:
                if ol == ly or not free[ol][k]: continue
                ns = ol * N + k; ng = g + via_cost
                if ng < gs.get(ns, INF): gs[ns] = ng; par[ns] = s; heapq.heappush(heap, (ng + hfun(k), ng, ns))
    return None

def los(fr, w, h, a, c):
    """Line of sight between cell coords a, c: every sample's 4 surrounding cell centres are free."""
    (ai, aj), (ci, cj) = a, c
    n = int(max(abs(ci - ai), abs(cj - aj)) * 2) + 1
    for s in range(n + 1):
        fi = ai + (ci - ai) * s / n; fj = aj + (cj - aj) * s / n
        i0, j0 = int(math.floor(fi)), int(math.floor(fj))
        for ii in (i0, i0 + 1) if fi != i0 else (i0,):
            for jj in (j0, j0 + 1) if fj != j0 else (j0,):
                if ii < 0 or jj < 0 or ii >= w or jj >= h or not fr[jj * w + ii]: return False
    return True
def pull(fr, w, h, pts):
    """Greedy string pulling of a cell path (same layer)."""
    out = [pts[0]]; i = 0
    while i < len(pts) - 1:
        j = len(pts) - 1
        while j > i + 1 and not los(fr, w, h, pts[i], pts[j]): j -= 1
        out.append(pts[j]); i = j
    return out

# ---------------------------------------------------------------- 6. board items, units
GRP = pcbnew.PCB_GROUP(b); GRP.SetName(GROUP); b.Add(GRP)
UNITS = {}        # unit id -> dict(items=[...], prims=[...], job=...)
UOF = {}          # item uuid -> unit id
def new_track(net, layer, a, c, w):
    t = pcbnew.PCB_TRACK(b); t.SetLayer(layer); t.SetNet(b.FindNet(net)); t.SetWidth(iu(w))
    t.SetStart(pcbnew.VECTOR2I(iu(a[0]), iu(a[1]))); t.SetEnd(pcbnew.VECTOR2I(iu(c[0]), iu(c[1]))); b.Add(t); GRP.AddItem(t)
    return t
def new_via(net, x, y, d, dr):
    v = pcbnew.PCB_VIA(b); v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetPosition(pcbnew.VECTOR2I(iu(x), iu(y))); v.SetWidth(iu(d)); v.SetDrill(iu(dr)); v.SetNet(b.FindNet(net)); b.Add(v); GRP.AddItem(v)
    return v
def commit_unit(job, items):
    u = len(UNITS); prs = []
    for it in items: prs.extend(prims_of_track(it, owner=u)); UOF[uid(it)] = u
    UNITS[u] = dict(items=items, job=job); add_prims(prs)
    return u
def kill_unit(u):
    for it in UNITS[u]['items']:
        GRP.RemoveItem(it); drop(it); UOF.pop(uid(it), None)
    UNITS[u]['dead'] = True       # its stamps stay in the maps (conservative, deterministic, no rebuild)

# ---------------------------------------------------------------- 7. clusters / jobs
def clusters():
    """{net: [cluster]}, cluster = dict(pads=[pad], items=[tracks/vias], zones=set(names), plane=bool)."""
    conn = b.GetConnectivity()
    out = collections.defaultdict(list)
    seen = set()
    plane_zone = {}
    for z in b.Zones():
        if z.GetIsRuleArea() or z.GetZoneName().startswith('PWR_'): continue
        n = z.GetNetname()
        if n in PLANE_NETS and z.IsOnLayer(pcbnew.In1_Cu if PLANE_NETS[n] == 'In1' else pcbnew.In2_Cu): plane_zone.setdefault(n, set()).add(uid(z))
    for f in FPS:
        for p in f.Pads():
            n = p.GetNetname()
            if p.GetNetCode() <= 0 or n.startswith('unconnected-') or uid(p) in seen: continue
            items = conn.GetConnectedItems(p)
            cl = dict(pads=[p], items=[], zones=set(), plane=False, net=n, pwr=False)
            seen.add(uid(p))
            for it in items:
                it = it.Cast(); c = it.GetClass()
                if c == 'PAD':
                    if uid(it) not in seen: seen.add(uid(it)); cl['pads'].append(it)
                elif c == 'ZONE':
                    cl['zones'].add(uid(it)); cl['pwr'] |= it.GetZoneName().startswith('PWR_')
                    if uid(it) in plane_zone.get(n, ()): cl['plane'] = True
                else: cl['items'].append(it)
            cl['pads'].sort(key=pad_name); cl['items'].sort(key=uid)     # deterministic order across re-runs
            out[n].append(cl)
    return {n: sorted(cs, key=lambda c: pad_name(c['pads'][0])) for n, cs in out.items() if len(cs) > 1}
def pad_name(p): return f'{p.GetParentFootprint().GetReference()}.{p.GetNumber()}'

# ---------------------------------------------------------------- 8. routing primitives (cells of a cluster)
def pad_center(p, ly):
    ps = item_polys(p, ly)
    if not ps: q = p.GetPosition(); return q.x / MM, q.y / MM
    pts = np.vstack(ps); return float((pts[:, 0].min() + pts[:, 0].max()) / 2), float((pts[:, 1].min() + pts[:, 1].max()) / 2)
def endpoint_cells(cl, layers, win, freeL):
    """{(ly, k): anchor} -- cells inside the cluster's pads / vias / tracks that are free; anchor = point to join."""
    i0, j0, w, h = win; out = {}
    def add_region(pr, li, anchor_fn, shrink):
        x0, y0, x1, y1 = pr.bb
        a0, a1, b0, b1 = rng(x0, y0, x1, y1)
        a0, a1, b0, b1 = max(a0, i0), min(a1, i0 + w), max(b0, j0), min(b1, j0 + h)
        if a0 >= a1 or b0 >= b1: return
        px, py = np.meshgrid(X0 + np.arange(a0, a1) * G, Y0 + np.arange(b0, b1) * G)
        m = pr.dist(px, py) < -shrink if pr.cap is not None else pr.dist(px, py) <= 0
        jj, ii = np.nonzero(m)
        fr = freeL[li]
        for jx, ix in zip(jj, ii):
            k = (b0 + jx - j0) * w + (a0 + ix - i0)
            if fr[k]: out.setdefault((li, k), anchor_fn(px[jx, ix], py[jx, ix]))
    for p in cl['pads']:
        for li in layers:
            ly = CU[li]
            if not (p.IsOnLayer(ly) and p.FlashLayer(ly)): continue
            c = pad_center(p, ly)
            for pts in item_polys(p, ly):
                pr = Prim('x', (li,), 0, 0, pts=pts)
                if pr.path.contains_point(c):
                    add_region(pr, li, lambda x, y, c=c: c, 0)
                else:
                    add_region(pr, li, lambda x, y: None, 0)
    for t in cl['items']:
        if t.Type() == pcbnew.PCB_VIA_T:
            q = t.GetPosition(); x, y = q.x / MM, q.y / MM; r = t.GetWidth(pcbnew.F_Cu) / MM / 2
            for li in layers: add_region(Prim('x', (li,), 0, 0, cap=(x, y, x, y, r)), li, lambda px_, py_, x=x, y=y: (x, y), 0.02)
        elif LI.get(t.GetLayer()) in layers:
            s, e = t.GetStart(), t.GetEnd(); ax, ay, bx, by = s.x / MM, s.y / MM, e.x / MM, e.y / MM
            r = t.GetWidth() / MM / 2
            def proj(px_, py_, ax=ax, ay=ay, bx=bx, by=by):
                dx, dy = bx - ax, by - ay; l2 = dx * dx + dy * dy
                tt = 0 if l2 == 0 else max(0, min(1, ((px_ - ax) * dx + (py_ - ay) * dy) / l2))
                return (ax + tt * dx, ay + tt * dy)
            add_region(Prim('x', (LI[t.GetLayer()],), 0, 0, cap=(ax, ay, bx, by, r)), LI[t.GetLayer()], proj, 0.02)
    return out

def el_bbs(cl):
    if '_bbs' not in cl:
        out = []
        for p in cl['pads']:
            bb = p.GetBoundingBox(); out.append((bb.GetX() / MM, bb.GetY() / MM, bb.GetRight() / MM, bb.GetBottom() / MM, 0, p))
        for t in cl['items']:
            bb = t.GetBoundingBox(); out.append((bb.GetX() / MM, bb.GetY() / MM, bb.GetRight() / MM, bb.GetBottom() / MM, 1, t))
        cl['_bbs'] = out
    return cl['_bbs']
def rdist(a, c): return max(c[0] - a[2], a[0] - c[2], 0) + max(c[1] - a[3], a[1] - c[3], 0)
def local(cl, box, r):
    """The part of cluster cl within r mm (manhattan) of box."""
    es = [e for e in el_bbs(cl) if rdist(box, e) <= r]
    return dict(pads=[e[5] for e in es if e[4] == 0], items=[e[5] for e in es if e[4] == 1], net=cl['net'])
def cl_bbox(cl):
    xs, ys = [], []
    for p in cl['pads']:
        bb = p.GetBoundingBox(); xs += [bb.GetX() / MM, bb.GetRight() / MM]; ys += [bb.GetY() / MM, bb.GetBottom() / MM]
    for t in cl['items']:
        bb = t.GetBoundingBox(); xs += [bb.GetX() / MM, bb.GetRight() / MM]; ys += [bb.GetY() / MM, bb.GetBottom() / MM]
    return min(xs), min(ys), max(xs), max(ys)

def window(x0, y0, x1, y1, pad):
    i0, i1, j0, j1 = rng(x0 - pad, y0 - pad, x1 + pad, y1 + pad)
    return i0, j0, i1 - i0, j1 - j0
def win_free(key, net, win):
    i0, j0, w, h = win
    a = MODES[key] if key in MODES else mode(key)
    s = a[j0:j0 + h, i0:i0 + w]; nl = nlabel(net)
    return bytearray(((s == 0) | (s == nl)).astype(np.uint8).ravel().tobytes())
def win_via(key, net, win, allow_fp):
    i0, j0, w, h = win
    lab, court, padm = mode(key)
    s = lab[j0:j0 + h, i0:i0 + w]; c = court[j0:j0 + h, i0:i0 + w]; nl = nlabel(net)
    ok = ((s == 0) | (s == nl)) & ~padm[j0:j0 + h, i0:i0 + w]
    cok = c == 0
    for fi in allow_fp: cok |= c == fi + 1
    return ok & cok

def emit(net, cells, anchors, win, layer_w, via_sz, freeL):
    """Cell path -> tracks + vias. anchors: {(ly,k): point} for the two ends."""
    i0, j0, w, h = win
    def xy(k): return (X0 + (i0 + k % w) * G, Y0 + (j0 + k // w) * G)
    runs = []; cur = [cells[0]]
    for c in cells[1:]:
        if c[0] != cur[-1][0]: runs.append(cur); cur = [c]
        else: cur.append(c)
    runs.append(cur)
    items = []
    for ri, run in enumerate(runs):
        ly = run[0][0]
        pts = [(k % w, k // w) for _, k in run]
        pts = pull(freeL[ly], w, h, pts)
        geo = [(X0 + (i0 + i) * G, Y0 + (j0 + j) * G) for i, j in pts]
        def free_at(pt, end, fr=freeL[ly]):   # an anchor (pad centre / track projection) only where the track fits
            ii, jj = int(round((pt[0] - X0) / G)) - i0, int(round((pt[1] - Y0) / G)) - j0
            return 0 <= ii < w and 0 <= jj < h and fr[jj * w + ii] and los(fr, w, h, (ii, jj), end)
        a0 = anchors.get(run[0]) if ri == 0 else None
        a1 = anchors.get(run[-1]) if ri == len(runs) - 1 else None
        if a0 is not None and free_at(a0, pts[0]): geo.insert(0, a0)
        if a1 is not None and free_at(a1, pts[-1]): geo.append(a1)
        for a, c in zip(geo, geo[1:]):
            if abs(a[0] - c[0]) + abs(a[1] - c[1]) > 1e-6: items.append(new_track(net, CU[ly], a, c, layer_w))
        if ri < len(runs) - 1:
            x, y = xy(run[-1][1]); items.append(new_via(net, x, y, *via_sz))
    return items

# ---------------------------------------------------------------- 9. jobs
def width_list(net, dmin=99.0):
    cls = ncl(net)[1]
    if net in ('/Brakes/VM_BRK',) or net.startswith('/Brakes/BRK_OUT') or net in ('+24V', '+12V'):
        return [1.5, 1.0, 0.6] + ([0.4, 0.3] if dmin <= 2.0 else [])      # a neck only for a pad-to-pad hop
    if net in ('+BATT', 'VBUS', 'VBAT_IN'): return [1.0, 0.5, 0.3, 0.2]
    if cls == 'Power_LV': return [0.5, 0.3, 0.2]
    if cls in ('Power_HV', 'Power_Shunt'): return [0.3, 0.2]       # phase / shunt sense taps carry signal current
    if cls == 'Gate_Drive': return [0.4, 0.3]
    return [0.2, 0.15]
def via_size(net):
    if net in PLANE_NETS and net != 'GND': return VIA_PWR
    if ncl(net)[1] in ('Power_HV', 'Power_Shunt'): return VIA_PWR
    return VIA_SIG

def fanout(cl, margin, blacklist, why='plane'):
    """Stub + via from one pad of cluster cl into its plane. Returns unit id or None."""
    net = cl['net']; cnew = ncl(net)[0]
    pm = plane_mask(net)
    sizes = [VIA_PWR, VIA_LV] if net == '+3V3' else [via_size(net)]
    widths = {'GND': [0.3, 0.2]}.get(net, [0.5, 0.3, 0.2] if net == '+3V3' else [1.0, 0.5, 0.3])
    pads = sorted(cl['pads'], key=lambda p: (p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD, p.GetParentFootprint().GetReference(), p.GetNumber()))
    for vs in sizes:
        vkey = ('V', vs[0] / 2, vs[1] / 2, cnew, margin)
        for wdt in widths:
            tkeys = {li: ('T', li, cnew, wdt / 2, margin) for li in RL}
            for p in pads:
                pp = p.GetPosition(); x, y = pp.x / MM, pp.y / MM
                win = window(x, y, x, y, 5.5)
                i0, j0, w, h = win
                freeL = {li: win_free(tkeys[li], p.GetNetCode(), win) for li in RL if p.IsOnLayer(CU[li]) and p.FlashLayer(CU[li])}
                if not freeL: continue
                vok = win_via(vkey, p.GetNetCode(), win, {FPI[uid(p.GetParentFootprint())]}) & pm[j0:j0 + h, i0:i0 + w]
                for (bx, by) in blacklist:
                    bi, bj = int(round((bx - X0) / G)) - i0, int(round((by - Y0) / G)) - j0
                    vok[max(0, bj - 10):bj + 11, max(0, bi - 10):bi + 11] = False
                tgt = {li: bytearray((vok & np.frombuffer(bytes(freeL[li]), np.uint8).reshape(h, w).astype(bool)).astype(np.uint8).ravel().tobytes()) for li in freeL}
                sub = dict(pads=[p], items=[])
                src = endpoint_cells(sub, list(freeL), win, freeL)
                if not src: continue
                path = astar(w, h, freeL, None, list(src), tgt, 0, 5.0 / G)
                if path is None: continue
                k = path[-1][1]; vx, vy = X0 + (i0 + k % w) * G, Y0 + (j0 + k // w) * G
                items = emit(net, path, {path[0]: src[path[0]]}, win, wdt, vs, freeL) if len(path) > 1 else []
                if len(path) == 1:     # via right at the pad edge: stub from the pad centre
                    c = src[path[0]]
                    if c and math.hypot(c[0] - vx, c[1] - vy) > 1e-6: items.append(new_track(net, CU[path[0][0]], c, (vx, vy), wdt))
                items.append(new_via(net, vx, vy, *vs))
                return commit_unit(dict(kind=why, net=net, pad=f'{p.GetParentFootprint().GetReference()}.{p.GetNumber()}', at=(vx, vy)), items)
    return None

WHY = {}
def route(net, src_cl, dst_cls, margin, pad_mm=4.0, reach=None):
    cnew = ncl(net)[0]; vs = via_size(net)
    sb = cl_bbox(src_cl)
    dmin = min(cl_dist(src_cl, c) for c in dst_cls)
    dst_cls = [d for d in (local(c, sb, dmin + (reach or 6.0)) for c in dst_cls) if d['pads'] or d['items']]
    tb = [cl_bbox(c) for c in dst_cls]
    why = []
    fps = {FPI[uid(p.GetParentFootprint())] for c in [src_cl] + dst_cls for p in c['pads']}
    for wdt in width_list(net, dmin):
        tkeys = {li: ('T', li, cnew, wdt / 2, margin) for li in RL}
        vkey = ('V', vs[0] / 2, vs[1] / 2, cnew, margin)
        x0 = min([sb[0]] + [t[0] for t in tb]); y0 = min([sb[1]] + [t[1] for t in tb])
        x1 = max([sb[2]] + [t[2] for t in tb]); y1 = max([sb[3]] + [t[3] for t in tb])
        win = window(x0, y0, x1, y1, pad_mm); i0, j0, w, h = win
        nc = b.FindNet(net).GetNetCode()
        freeL = {li: win_free(tkeys[li], nc, win) for li in RL}
        vok = bytearray(win_via(vkey, nc, win, fps).astype(np.uint8).ravel().tobytes())
        src = endpoint_cells(src_cl, list(RL), win, freeL)
        dst = {}
        for c in dst_cls: dst.update(endpoint_cells(c, list(RL), win, freeL))
        for k in list(dst):
            if k in src: del dst[k]
        if not src or not dst: why.append(f'w{wdt}: no free {"start" if not src else "end"} cell'); continue
        tgt = {li: bytearray(w * h) for li in RL}
        for (li, k) in dst: tgt[li][k] = 1
        ks = [k for _, k in dst]; ii = [k % w for k in ks]; jj = [k // w for k in ks]
        path = astar(w, h, freeL, vok, list(src), tgt, 1.5 / G, 4 * (w + h), (min(ii), max(ii), min(jj), max(jj)), max(2500000, w * h))
        if path is None: why.append(f'w{wdt}: no path in {w * G:.0f}x{h * G:.0f} mm'); continue
        nv = sum(1 for a, c in zip(path, path[1:]) if a[0] != c[0])
        if nv > 2 + int(dmin / 25): why.append(f'w{wdt}: {nv} vias over budget'); continue
        anchors = {path[0]: src.get(path[0]), path[-1]: dst.get(path[-1])}
        items = emit(net, path, anchors, win, wdt, vs, freeL)
        return commit_unit(dict(kind='route', net=net, w=wdt, vias=nv), items)
    WHY[(net, cl_name(src_cl))] = '; '.join(why)
    return None

# ---------------------------------------------------------------- 10. run
def cl_name(c):
    if c['pads']:
        p = c['pads'][0]; return f"{p.GetParentFootprint().GetReference()}.{p.GetNumber()}" + (f'+{len(c["pads"]) - 1}' if len(c['pads']) > 1 else '')
    return 'tracks'
def cl_dist(a, c):
    ab = cl_bbox(a)
    return min(rdist(ab, e) for e in el_bbs(c))

starved_pads = []
pad_by_uid = {uid(p): p for f in FPS for p in f.Pads()}
for v in d0['violations']:
    if v['type'] != 'starved_thermal': continue
    for it in v['items']:
        p = pad_by_uid.get(it['uuid'])
        if p is not None and p.GetNetname() == 'GND' and p not in starved_pads: starved_pads.append(p)
starved_pads.sort(key=pad_name)

def stitch_islands(margin, blacklist):
    """A via to In1 in every GND pour island (F/B, >= 1 mm2) that holds no GND via or PTH pad."""
    anchors = [(t.GetPosition().x / MM, t.GetPosition().y / MM) for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == 'GND']
    anchors += [(p.GetPosition().x / MM, p.GetPosition().y / MM) for f in FPS for p in f.Pads()
                if p.GetNetname() == 'GND' and p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH]
    A = np.array(anchors); made = 0; vs = VIA_SIG
    vkey = ('V', vs[0] / 2, vs[1] / 2, ncl('GND')[0], margin)
    pm = plane_mask('GND')
    for z in sorted([z for z in b.Zones() if not z.GetIsRuleArea() and z.GetNetname() == 'GND'], key=lambda z: (z.GetZoneName(), uid(z))):
        for ly in (pcbnew.F_Cu, pcbnew.B_Cu):
            if not z.IsOnLayer(ly): continue
            fps_ = z.GetFilledPolysList(ly)
            for i in range(fps_.OutlineCount()):
                o = fps_.COutline(i)
                pts = np.array([(o.CPoint(k).x / MM, o.CPoint(k).y / MM) for k in range(o.PointCount())])
                if len(pts) < 3: continue
                pr = Prim('x', (0,), 0, 0, pts=pts)
                x0, y0, x1, y1 = pr.bb
                area = 0.5 * abs(np.dot(pts[:, 0], np.roll(pts[:, 1], 1)) - np.dot(pts[:, 1], np.roll(pts[:, 0], 1)))
                if area < 1.0: continue
                near = A[(A[:, 0] >= x0) & (A[:, 0] <= x1) & (A[:, 1] >= y0) & (A[:, 1] <= y1)] if len(A) else A
                if len(near) and pr.path.contains_points(near).any(): continue
                key = ('i', 'GND', f'{z.GetZoneName() or "GND"}@{pcbnew.LayerName(ly)}:{x0:.1f},{y0:.1f}')
                if key in LIVE or key in NOPATH or len(failed[key]) > 3: continue
                win = window(x0, y0, x1, y1, 0); i0, j0, w, h = win
                if w <= 0 or h <= 0: continue
                px, py = np.meshgrid(X0 + np.arange(i0, i0 + w) * G, Y0 + np.arange(j0, j0 + h) * G)
                inside = pr.path.contains_points(np.stack([px.ravel(), py.ravel()], 1)).reshape(h, w)
                e = min_edge_dist(px, py, pts, np.roll(pts, -1, 0))
                ok = inside & (e >= vs[0] / 2 + 0.1) & win_via(vkey, b.FindNet('GND').GetNetCode(), win, set()) & pm[j0:j0 + h, i0:i0 + w]
                for (bx, by) in failed[key]:
                    ok &= np.hypot(px - bx, py - by) > 0.5
                jj, ii = np.nonzero(ok)
                if not len(jj): NOPATH.add(key); continue
                cxm, cym = pts[:, 0].mean(), pts[:, 1].mean()
                k = int(np.argmin(np.hypot(px[jj, ii] - cxm, py[jj, ii] - cym) + 1e-3 * (jj * w + ii)))
                vx, vy = float(px[jj[k], ii[k]]), float(py[jj[k], ii[k]])
                u = commit_unit(dict(kind='island', net='GND', at=(vx, vy), zone=key[2]), [new_via('GND', vx, vy, *vs)])
                UNITS[u]['key'] = key; LIVE.add(key); made += 1
    return made

failed = collections.defaultdict(list)     # job key -> blacklisted via spots / DRC failures
margin_of = collections.defaultdict(lambda: MARGIN)
LIVE, NOPATH = set(), set()                 # job keys with a live unit / that found no path (not retried)
prev_bad = True
for it in range(6):
    CL = clusters()
    jobs_f = [c for net in sorted(CL) if net in PLANE_NETS for c in CL[net] if not c['plane']]
    log(f'iteration {it}: {len(jobs_f)} plane fanouts, {len(CL)} nets split, unconnected {b.GetConnectivity().GetUnconnectedCount(True)}')
    made = nf = nr = 0
    for c in sorted(jobs_f, key=lambda c: (c['net'], cl_name(c))):
        key = ('f', c['net'], cl_name(c))
        if key in LIVE or key in NOPATH or len(failed[key]) > 3: continue
        u = fanout(c, margin_of[key], failed[key])
        if u is not None: UNITS[u]['key'] = key; LIVE.add(key); made += 1
        else: nf += 1; NOPATH.add(key)
    for p in starved_pads:
        key = ('s', 'GND', f'{p.GetParentFootprint().GetReference()}.{p.GetNumber()}')
        if key in LIVE or key in NOPATH or len(failed[key]) > 3: continue
        u = fanout(dict(pads=[p], items=[], net='GND'), margin_of[key], failed[key], why='starved')
        if u is not None: UNITS[u]['key'] = key; LIVE.add(key); made += 1
        else: NOPATH.add(key)
    made += stitch_islands(MARGIN, failed)
    # plane nets whose isolated cluster could not reach the plane, and all other nets: route cluster to cluster
    for phase in (0, 1):      # short connections first, then the long hauls
        CLr = clusters()
        for net in sorted(CLr):
            cs = CLr[net]
            if net in PLANE_NETS and all(c['plane'] for c in cs): continue
            rest = list(cs)
            while len(rest) > 1:
                rest.sort(key=lambda c: (c['plane'], len(c['pads']), cl_name(c)))
                src = rest[0]
                if net in PLANE_NETS and src['plane']: break
                others = sorted(rest[1:], key=lambda c: (cl_dist(src, c), cl_name(c)))
                dmin = cl_dist(src, others[0])
                key = ('r', net, cl_name(src))
                lim = MAX_ROUTE
                if phase == 0 and dmin > 45: rest.remove(src); continue
                if dmin > lim or key in LIVE or key in NOPATH or len(failed[key]) > 2:
                    if dmin > lim: WHY.setdefault((net, cl_name(src)), f'{dmin:.0f} mm away (router limit {lim:.0f} mm)')
                    rest.remove(src); continue
                near = [c for c in others if cl_dist(src, c) <= dmin + 8.0]
                if src['pwr']:            # never bridge two islands of a high-current pour with a track
                    near = [c for c in near if not c['pwr']]
                    if not near:
                        WHY.setdefault((net, cl_name(src)), 'PWR_ pour split into islands (by autorouted tracks): needs copper, not a track')
                        rest.remove(src); continue
                u = route(net, src, near, margin_of[key], pad_mm=4.0 if dmin < 45 else 8.0)
                if u is None and dmin < 15: u = route(net, src, near, margin_of[key], pad_mm=9.0)
                if u is None: nr += 1; NOPATH.add(key)
                else:
                    UNITS[u]['key'] = key; LIVE.add(key); made += 1
                    tgt = near[0]; tgt['pads'] += src['pads']; tgt['items'] += src['items'] + UNITS[u]['items']; tgt.pop('_bbs', None)
                rest.remove(src)
    log(f'iteration {it}: added {made} units ({nf} fanouts / {nr} routes found no path)')
    if made == 0 and not prev_bad: break
    # fill + DRC: drop the units that show up in an error or create new starved thermals / islands
    fill(); b.Save(P)
    d = drc(P)
    bad = {}
    def mark(u, why):
        bad.setdefault(u, why)
    for v in d['violations']:
        t = v['type']
        us = {UOF[i['uuid']] for i in v['items'] if i['uuid'] in UOF}
        if t in ERR and us:
            for u in us: mark(u, t)
        elif t == 'starved_thermal':
            news = [i for i in v['items'] if i['uuid'] in pad_by_uid and i['uuid'] not in base_starved]
            for i in news:
                x, y = i['pos']['x'], i['pos']['y']
                for u, U in UNITS.items():
                    if U.get('dead'): continue
                    if any(math.hypot(pr.cap[0] - x, pr.cap[1] - y) < 2.0 or math.hypot(pr.cap[2] - x, pr.cap[3] - y) < 2.0
                           for pr in PRIMS if pr.owner == u and pr.cap is not None): mark(u, 'new starved thermal')
        elif t == 'isolated_copper':
            x, y = v['items'][0]['pos']['x'], v['items'][0]['pos']['y']
            if (round(x, 1), round(y, 1)) in base_iso: continue
            for u, U in UNITS.items():
                if U.get('dead'): continue
                if any(abs(pr.cap[0] - x) < 3 and abs(pr.cap[1] - y) < 3 for pr in PRIMS if pr.owner == u and pr.cap is not None): mark(u, 'new island')
    # vias of plane fanouts / island stitches must have reached the plane
    conn = b.GetConnectivity()
    for u, U in UNITS.items():
        if U.get('dead') or U['job']['kind'] not in ('plane', 'starved', 'island'): continue
        via = U['items'][-1]
        if not any(i.Cast().GetClass() == 'ZONE' and (i.IsOnLayer(pcbnew.In1_Cu) or i.IsOnLayer(pcbnew.In2_Cu)) for i in conn.GetConnectedItems(via)):
            mark(u, 'via not on the plane')
    log(f'iteration {it}: DRC errors {collections.Counter(v["type"] for v in d["violations"] if v["type"] in ERR)}, '
        f'unrouted {len(d["unconnected_items"])}, units to drop {len(bad)} {dict(collections.Counter(bad.values()))}')
    for v in d['violations']:
        if v['type'] in ERR: log('   ', v['type'], ' / '.join(f"{i['description'][:50]} ({i['pos']['x']:.2f},{i['pos']['y']:.2f})" for i in v['items']))
    prev_bad = bool(bad)
    for u in sorted(bad):
        U = UNITS[u]; key = U['key']
        failed[key].append(U['job'].get('at'))
        margin_of[key] = margin_of[key] + 0.03
        LIVE.discard(key); kill_unit(u)

fill(); b.Save(P)
live = [U for U in UNITS.values() if not U.get('dead')]
cnt = collections.Counter(U['job']['kind'] for U in live)
print(json.dumps(dict(
    removed_old=old, ripped=len(rip), rip_why={f'{a}:{n}': c for (a, n), c in rip_why.items()}, widened=widened,
    dangling_removed=n_dang, units=dict(cnt), vias=sum(1 for U in live for i in U['items'] if i.Type() == pcbnew.PCB_VIA_T),
    tracks=sum(1 for U in live for i in U['items'] if i.Type() == pcbnew.PCB_TRACE_T),
    unconnected=b.GetConnectivity().GetUnconnectedCount(True),
    not_routed={f'{n} {c}': w for (n, c), w in sorted(WHY.items())},
    no_plane_spot=sorted(f'{k[1]} {k[2]}' for k in NOPATH if k[0] in ('f', 's', 'i')),
    jobs=[U['job'] for U in live]), indent=1, default=str))
log('saved', P)
