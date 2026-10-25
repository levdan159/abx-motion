"""Route the CRITICAL signal traces of abx-motion-brushless as tracks + vias (re-runnable, edits the given board file).

Usage: ~/.cache/mark-mods/kicad-mcp-big-venv/bin/python critical.py <board.kicad_pcb>   (KiCad must be closed)

What it routes (only these):
  1. gate drive per phase: DRV GHx -> R -> high FET gate, GLx -> R -> low FET gate, SHx Kelvin -> high FET source pin
  2. shunt Kelvin pairs SPx/SNx from the inner pad edges of each shunt to the DRV sense pins
  3. DRV local nets: CPH/CPL, VCP, VM (+ VBUS vias), DVDD, VREF (the DRV8323S has no VGLS/AVDD pins)
  4. STM32 crystal Y701 + load caps, VCAP1/2, NRST cap
  5. aux bucks U511/U512: FB, COMP, CZ, RT, EN, BOOT
Everything it makes sits in the PCB group 'critical_routes'; a re-run deletes that group's tracks/vias first (verified:
two runs give identical copper). Placement it changes (absolute positions, so re-runs are stable): MOVE1 (DRV-local
caps, gate resistors; ESC2 = point reflection about (140,107)), MOVE2 (ESC2-only nudge), EVICT (sense/hall passives
moved out of the gate-escape area), MOVE3 (crystal load caps, VCAP2 cap). The aux-buck parts are placed by
buckplace.py, which runs before this script.
ESC1: hand-made 0.5 mm-pitch escape fans (FAN) + a grid A* router (0.1 mm grid; clearances from each pad's netclass,
checked on a 25 um distance raster against foreign pads/tracks/vias/holes/board edge; vias barred under courtyards).
ESC2 = the ESC1 copper point-reflected, nets mapped 3xx -> 4xx; every reflected end that sits in a pad is checked
against the matching ESC2 pad. Buck FB/COMP/CZ (and any EN/RT/BOOT) are only routed when a short path exists that
keeps 1 mm from the SW copper and stays off other parts' bodies; the rest is logged as SKIP/FAIL (placement)."""
import subprocess as _sp; assert _sp.run(['pgrep', '-x', 'kicad'], capture_output=True).returncode, 'KiCad is running: close it (without saving) first'
import sys, math, heapq, re
from array import array
import numpy as np
from scipy import ndimage
from matplotlib.path import Path
import pcbnew

BOARD = sys.argv[1]
assert BOARD.endswith('.kicad_pcb')
b = pcbnew.LoadBoard(BOARD)
MM = 1e6
FCU, BCU = pcbnew.F_Cu, pcbnew.B_Cu
LAY = (FCU, BCU)
GROUP = 'critical_routes'
RES, FINE, MARGIN, PAD_MARGIN = 0.1, 0.025, 0.035, 0.015   # pads: axis-aligned on the raster, near exact    # route grid, distance raster, discretisation margin (mm)
SUB = int(round(RES / FINE))
EDGE_CL, HOLE_CL = 0.3, 0.25
VIA_D, VIA_DRILL = 0.6, 0.3
LOG = []
def log(*a):
    s = ' '.join(str(x) for x in a); print(s); LOG.append(s)

# ------------------------------------------------------------------ clean previous run
grp = None
for g in b.Groups():
    if g.GetName() == GROUP: grp = g
if grp is not None:
    old = [it for it in grp.GetItems() if it.GetClass() in ('PCB_TRACK', 'PCB_VIA', 'PCB_ARC')]
    for it in old: grp.RemoveItem(it); b.Remove(it)
    log('removed', len(old), 'old tracks/vias')
else:
    grp = pcbnew.PCB_GROUP(b); grp.SetName(GROUP); b.Add(grp)

fp = {f.GetReference(): f for f in b.GetFootprints()}
def m2(r): return re.sub(r'(\d{3})$', lambda m: str(int(m.group(1)) + 100), r)
def refl(x, y): return 280.0 - x, 214.0 - y

# ------------------------------------------------------------------ placement tweaks (ESC1; ESC2 = reflection)
# low-side gate resistors move into the channel beside their FET gate (pad 2 next to pin 4); the DRV VM/VCP/CP caps
# are re-stacked on the DRV's right side (VM pins -> C320, VCP -> C317, CPH/CPL -> C316 below) so the top-side
# gate pins can escape; high-side gate resistors sit just outside the DRV escape fan.
MOVE1 = {
    'R311': (166.85, 66.0, 90), 'R313': (149.0, 66.0, 90), 'R315': (131.0, 66.0, 90),
    'C320': (145.5, 87.1, 0), 'C317': (145.9, 88.75, 0), 'C316': (144.6, 90.7, 180),
    'R310': (149.0, 86.25, 0), 'R312': (141.0, 79.6, 90), 'R314': (139.0, 79.6, 90),
}
# ESC2-only overrides (its D401 sits where the exact reflection of R311 would overlap it by 0.03 mm)
MOVE2 = {'R411': (113.18, 148.0, 270)}
# sense/hall passives that sat in the gate-escape area: moved to free spots (found once by a courtyard spiral search,
# ESC1 right of J703, ESC2 left of the bucks: the two ESCs are not mirror images there)
EVICT = {'C331': (163.5, 85.0, 0), 'C341': (163.95, 86.7, 0), 'C342': (163.05, 83.3, 0), 'R316': (166.1, 83.5, 90), 'R319': (164.4, 88.4, 0),
         'R318': (163.5, 80.75, 0), 'R325': (163.5, 90.0, 0), 'R326': (166.4, 80.0, 90),
         'C431': (157.0, 128.0, 0), 'C441': (157.45, 129.7, 0), 'C442': (156.55, 126.3, 0), 'R416': (160.0, 128.0, 90), 'R419': (154.6, 128.65, 90),
         'R418': (157.0, 131.5, 0), 'R425': (156.1, 124.6, 0), 'R426': (159.65, 125.35, 0)}
# STM32: crystal load caps beside the crystal (C714 above OSC_OUT pad 3, C713 right of OSC_IN pad 1, C701 takes
# C713's old spot), VCAP2 cap into the free corner notch next to pin 73. The buck parts (incl. BOOT caps C528/C540 and
# CZ caps C526/C538) are placed by buckplace.py, run before this script.
MOVE3 = {'C713': (143.65, 107.95, 90), 'C714': (140.9, 104.45, 0), 'C701': (146.32, 107.63, 90), 'C712': (122.0, 114.95, 270)}
def place(ref, x, y, rot):
    f = fp[ref]; f.SetOrientationDegrees(rot); f.SetPosition(pcbnew.VECTOR2I(int(round(x * MM)), int(round(y * MM))))
for r, (x, y, rot) in MOVE1.items():
    place(r, x, y, rot); x2, y2 = refl(x, y); place(m2(r), x2, y2, (rot + 180) % 360)
for r, (x, y, rot) in list(MOVE2.items()) + list(EVICT.items()) + list(MOVE3.items()): place(r, x, y, rot)

# ------------------------------------------------------------------ geometry cache
NETCL = {}
for _f in b.GetFootprints():
    for _q in _f.Pads():
        if _q.IsOnCopperLayer(): NETCL[_q.GetNetname()] = max(NETCL.get(_q.GetNetname(), 0.0), _q.GetOwnClearance(FCU) / MM)
def net_cl(netname): return NETCL.get(netname, 0.15)      # netclass clearance, as the pads resolve it
class Item:
    __slots__ = ('net', 'layers', 'kind', 'g', 'bb', 'cl', 'hole')
    def __init__(s, net, layers, kind, g, bb, cl, hole=None): s.net, s.layers, s.kind, s.g, s.bb, s.cl, s.hole = net, layers, kind, g, bb, cl, hole
ITEMS = []
PADS = {}
def poly_of(ps):
    out = []
    for i in range(ps.OutlineCount()):
        o = ps.Outline(i); out.append(np.array([(o.CPoint(k).x / MM, o.CPoint(k).y / MM) for k in range(o.PointCount())]))
    return out
def build_items():
    ITEMS.clear(); PADS.clear()
    for f in b.GetFootprints():
        for q in f.Pads():
            net = q.GetNetname(); cl = q.GetOwnClearance(FCU) / MM if q.IsOnCopperLayer() else 0.0
            hole = None
            if q.HasHole():
                c = q.GetPosition(); d = q.GetDrillSize(); hole = (c.x / MM, c.y / MM, max(d.x, d.y) / 2 / MM)
            for li, L in enumerate(LAY):
                if not q.IsOnLayer(L) or not q.IsOnCopperLayer(): continue
                ps = pcbnew.SHAPE_POLY_SET(); q.TransformShapeToPolygon(ps, L, 0, 2000, pcbnew.ERROR_INSIDE)
                for P in poly_of(ps):
                    it = Item(net, (li,), 'poly', P, (P[:, 0].min(), P[:, 1].min(), P[:, 0].max(), P[:, 1].max()), cl)
                    ITEMS.append(it); PADS.setdefault((f.GetReference(), q.GetNumber()), []).append((li, P, net))
            if hole:
                x, y, r = hole
                ITEMS.append(Item(net, (0, 1), 'hole', (x, y, r), (x - r, y - r, x + r, y + r), HOLE_CL))
    for t in b.GetTracks():
        add_track_item(t)
def add_track_item(t):
    net = t.GetNetname(); cl = net_cl(net)
    if t.GetClass() == 'PCB_VIA':
        c = t.GetPosition(); x, y = c.x / MM, c.y / MM; r = t.GetWidth(FCU) / 2 / MM; hr = t.GetDrillValue() / 2 / MM
        ITEMS.append(Item(net, (0, 1), 'circ', (x, y, r), (x - r, y - r, x + r, y + r), cl))
        ITEMS.append(Item(net, (0, 1), 'hole', (x, y, hr), (x - hr, y - hr, x + hr, y + hr), HOLE_CL))
    else:
        L = t.GetLayer()
        if L not in LAY: return
        s, e = t.GetStart(), t.GetEnd(); w = t.GetWidth() / MM
        g = (s.x / MM, s.y / MM, e.x / MM, e.y / MM, w / 2)
        ITEMS.append(Item(net, (LAY.index(L),), 'seg', g, (min(g[0], g[2]) - w / 2, min(g[1], g[3]) - w / 2, max(g[0], g[2]) + w / 2, max(g[1], g[3]) + w / 2), cl))
ps = pcbnew.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(ps, False)
OUTLINE = Path(poly_of(ps)[0])

# ------------------------------------------------------------------ obstacle rasters
class Win:
    """route window: grid cell (ix,iy) centre = (x0 + ix*RES, y0 + iy*RES); fine pixel k centre = x0 + k*FINE."""
    def __init__(s, x0, y0, x1, y1):
        s.x0 = math.floor((x0 - 0.05) / RES) * RES + 0.05; s.y0 = math.floor((y0 - 0.05) / RES) * RES + 0.05
        s.nx = int((x1 - s.x0) / RES) + 2; s.ny = int((y1 - s.y0) / RES) + 2
        s.fnx, s.fny = (s.nx - 1) * SUB + 1, (s.ny - 1) * SUB + 1
    def cell(s, x, y): return int(round((x - s.x0) / RES)), int(round((y - s.y0) / RES))
    def xy(s, ix, iy): return round(s.x0 + ix * RES, 4), round(s.y0 + iy * RES, 4)
def fine_slice(W, bb, pad):
    i0 = max(0, int((bb[0] - pad - W.x0) / FINE)); i1 = min(W.fnx, int((bb[2] + pad - W.x0) / FINE) + 2)
    j0 = max(0, int((bb[1] - pad - W.y0) / FINE)); j1 = min(W.fny, int((bb[3] + pad - W.y0) / FINE) + 2)
    return i0, i1, j0, j1
def distance_maps(W, mynet):
    """per layer: {clearance: distance-to-foreign-copper map on the ROUTE grid}, plus edge distance."""
    masks = [dict(), dict()]
    for it in ITEMS:
        if it.net == mynet and it.kind != 'hole': continue
        if it.net == mynet and it.kind == 'hole': continue
        i0, i1, j0, j1 = fine_slice(W, it.bb, 0.05)
        if i0 >= i1 or j0 >= j1: continue
        xs = W.x0 + np.arange(i0, i1) * FINE; ys = W.y0 + np.arange(j0, j1) * FINE
        X, Y = np.meshgrid(xs, ys)
        if it.kind == 'poly':
            m = Path(it.g).contains_points(np.c_[X.ravel(), Y.ravel()]).reshape(X.shape)
        elif it.kind in ('circ', 'hole'):
            x, y, r = it.g; m = (X - x) ** 2 + (Y - y) ** 2 <= r * r
        else:
            ax, ay, bx, by, hw = it.g; dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy
            t = np.clip(((X - ax) * dx + (Y - ay) * dy) / L2, 0, 1) if L2 > 0 else np.zeros_like(X)
            m = (X - ax - t * dx) ** 2 + (Y - ay - t * dy) ** 2 <= hw * hw
        key = ('h', it.cl) if it.kind == 'hole' else (it.cl, 'p' if it.kind == 'poly' else 't')
        for li in it.layers:
            M = masks[li].get(key)
            if M is None: M = masks[li][key] = np.zeros((W.fny, W.fnx), bool)
            M[j0:j1, i0:i1] |= m
    out = [dict(), dict()]
    for li in (0, 1):
        for key, M in masks[li].items():
            out[li][key] = (ndimage.distance_transform_edt(~M) * FINE)[::SUB, ::SUB]
    gx = W.x0 + np.arange(W.nx) * RES; gy = W.y0 + np.arange(W.ny) * RES
    X, Y = np.meshgrid(gx, gy)
    inside = OUTLINE.contains_points(np.c_[X.ravel(), Y.ravel()]).reshape(X.shape)
    edge = ndimage.distance_transform_edt(inside) * RES       # coarse but conservative enough with the 0.3 rule + margin
    return out, edge
def blocked(dm, edge, mycl, hw):
    bl = []
    for li in (0, 1):
        B = edge < EDGE_CL + hw + RES
        for key, D in dm[li].items():
            if key[0] == 'h': B |= D < key[1] + hw + MARGIN                # copper to a foreign hole: hole clearance
            else: B |= D < max(key[0], mycl) + hw + (PAD_MARGIN if key[1] == 'p' else MARGIN)
        bl.append(B)
    return bl

# ------------------------------------------------------------------ A*
DIRS = [(1, 0, 1.0), (1, 1, math.sqrt(2)), (0, 1, 1.0), (-1, 1, math.sqrt(2)), (-1, 0, 1.0), (-1, -1, math.sqrt(2)), (0, -1, 1.0), (1, -1, math.sqrt(2))]
def astar(W, free, costs, starts, goals, viaok, viacost, turnpen=0.35):
    nx, ny = W.nx, W.ny; N = nx * ny
    offs = [dx + dy * nx for dx, dy, _ in DIRS]
    g = array('d', [1e18]) * (2 * N); par = array('l', [-1]) * (2 * N); dirr = bytearray(b'\xff') * (2 * N)
    gl = list(goals); gx = sum(s % N % nx for s in gl) / len(gl); gy = sum(s % N // nx for s in gl) / len(gl)
    grad = max(math.hypot(s % N % nx - gx, s % N // nx - gy) for s in gl)
    def h(i):
        dx = abs(i % nx - gx); dy = abs(i // nx - gy)
        return max(0.0, (max(dx, dy) + 0.4142 * min(dx, dy)) - grad)
    heap = []
    for s in starts:
        g[s] = 0.0; heapq.heappush(heap, (h(s % N), 0.0, s))
    goal = set(goals); end = -1; n = 0
    while heap:
        f, gs, s = heapq.heappop(heap)
        if gs > g[s]: continue
        if s in goal: end = s; break
        n += 1
        if n > 3_000_000: break
        l = s // N; i = s - l * N; d0 = dirr[s]; fr = free[l]; co = costs[l]
        for k in range(8):
            j = i + offs[k]
            if not fr[j]: continue
            c = DIRS[k][2] * co[j]
            if d0 != 255 and d0 != k:
                dd = (k - d0) % 8; dd = min(dd, 8 - dd)
                if dd > 2: continue
                c += turnpen * dd
            t = l * N + j; ng = gs + c
            if ng < g[t]:
                g[t] = ng; par[t] = s; dirr[t] = k; heapq.heappush(heap, (ng + h(j), ng, t))
        if viaok is not None and viaok[i]:
            t = (1 - l) * N + i; ng = gs + viacost
            if free[1 - l][i] and ng < g[t]:
                g[t] = ng; par[t] = s; dirr[t] = 255; heapq.heappush(heap, (ng + h(i), ng, t))
    if end < 0: return None
    path = [end]
    while par[path[-1]] >= 0: path.append(par[path[-1]])
    return [(s // N, (s % N) % nx, (s % N) // nx) for s in reversed(path)]

# ------------------------------------------------------------------ route one connection
NEW = []     # (kind, data) of what this run made, for the ESC2 reflection
def net_of(name):
    n = b.FindNet(name); assert n, name; return n
def add_track(net, layer, x0, y0, x1, y1, w, rec=True):
    if (x0, y0) == (x1, y1): return
    t = pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I(int(round(x0 * MM)), int(round(y0 * MM))))
    t.SetEnd(pcbnew.VECTOR2I(int(round(x1 * MM)), int(round(y1 * MM)))); t.SetWidth(int(round(w * MM)))
    t.SetLayer(layer); t.SetNet(net_of(net)); b.Add(t); grp.AddItem(t); add_track_item(t)
    if rec: NEW.append(('t', net, layer, x0, y0, x1, y1, w))
def add_via(net, x, y, rec=True, d=None, drill=None):
    d = d or VIA_D; drill = drill or VIA_DRILL
    v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(int(round(x * MM)), int(round(y * MM))))
    try: v.SetWidth(int(round(d * MM)))
    except TypeError: v.SetWidth(FCU, int(round(d * MM)))
    v.SetDrill(int(round(drill * MM))); v.SetLayerPair(FCU, BCU); v.SetNet(net_of(net)); b.Add(v); grp.AddItem(v); add_track_item(v)
    if rec: NEW.append(('v', net, x, y, d, drill))

def pad_cells(W, ref, num, free):
    out = []
    for li, P, net in PADS[(ref, num)]:
        pth = Path(P); x0, y0 = P[:, 0].min(), P[:, 1].min(); x1, y1 = P[:, 0].max(), P[:, 1].max()
        i0, j0 = W.cell(x0, y0); i1, j1 = W.cell(x1, y1)
        for iy in range(max(1, j0 - 1), min(W.ny - 1, j1 + 2)):
            for ix in range(max(1, i0 - 1), min(W.nx - 1, i1 + 2)):
                x, y = W.xy(ix, iy)
                if pth.contains_point((x, y), radius=-0.05) and free[li][iy * W.nx + ix]: out.append((li, ix, iy))
    return out
def endpoint(W, spec, free):
    """('pad', ref, num) | ('pt', x, y, layer_index)"""
    if spec[0] == 'pad': return pad_cells(W, spec[1], spec[2], free)
    _, x, y, li = spec; ix, iy = W.cell(x, y); return [(li, ix, iy)]
def spec_xy(spec):
    if spec[0] == 'pad':
        f = fp[spec[1]]; q = [p for p in f.Pads() if p.GetNumber() == spec[2]][0].GetPosition(); return q.x / MM, q.y / MM
    return spec[1], spec[2]

def route(net, A, B, w, neck=None, nw=0.2, layers='F', fnear=2.5, viacost=6.0, bcost=1.4, hug=None, hugd=0.8, hugm=1.6, win=4.0, avoid=None, vd=None, repel=None, keep=None, keepd=1.0, maxratio=None, maxlen=None, keep_pads=None, nocrt=False, tag=''):
    """net: net name. A, B: endpoint specs. w: track width (nw inside the `neck` rects). layers: 'F', or 'FB' (B.Cu
    everywhere, F.Cu only within fnear mm of A/B and vias allowed). hug: list of (x,y,layer) points of a partner
    track to stay beside. Returns list of cells or None."""
    ax, ay = spec_xy(A); bx_, by_ = spec_xy(B)
    W = Win(min(ax, bx_) - win, min(ay, by_) - win, max(ax, bx_) + win, max(ay, by_) + win)
    mycl = net_cl(net)
    dm, edge = distance_maps(W, net)
    fw = blocked(dm, edge, mycl, w / 2); fn = blocked(dm, edge, mycl, nw / 2); fv = blocked(dm, edge, mycl, (vd or VIA_D) / 2)
    gx = W.x0 + np.arange(W.nx) * RES; gy = W.y0 + np.arange(W.ny) * RES; X, Y = np.meshgrid(gx, gy)
    nm = np.zeros((W.ny, W.nx), bool)
    for r in (neck or []): nm |= (X >= r[0]) & (X <= r[2]) & (Y >= r[1]) & (Y <= r[3])
    kp = np.zeros((W.ny, W.nx), bool)
    for it in ITEMS:              # keep-out round noisy nets (buck SW nodes) for quiet nets such as FB / COMP
        if keep and it.net in keep and it.kind == 'poly':
            x0, y0, x1, y1 = it.bb; d = keepd + w / 2; kp |= (X >= x0 - d) & (X <= x1 + d) & (Y >= y0 - d) & (Y <= y1 + d)
    for (ref, num) in (keep_pads or []):   # pads whose pour connection must stay free (input-cap GND pads)
        for li, P, pn in PADS[(ref, num)]:
            d = 0.6 + w / 2; kp |= (X >= P[:, 0].min() - d) & (X <= P[:, 0].max() + d) & (Y >= P[:, 1].min() - d) & (Y <= P[:, 1].max() + d)
    free = []
    for li in (0, 1):
        B_ = np.where(nm, fn[li], fw[li]) | kp; B_[0, :] = B_[-1, :] = True; B_[:, 0] = B_[:, -1] = True
        free.append(~B_)
    if layers == 'F':
        free[1][:] = False
    elif layers == 'B':
        free[0][:] = False
    else:
        near = np.zeros_like(nm)
        for (px, py) in ((ax, ay), (bx_, by_)): near |= (X - px) ** 2 + (Y - py) ** 2 <= fnear ** 2
        free[0] &= near
    costs = [np.ones((W.ny, W.nx)), np.full((W.ny, W.nx), bcost)]
    if hug:
        hm = [np.zeros((W.ny, W.nx), bool), np.zeros((W.ny, W.nx), bool)]
        for (x, y, li) in hug:
            ix, iy = W.cell(x, y)
            if 0 <= ix < W.nx and 0 <= iy < W.ny: hm[li][iy, ix] = True
        for li in (0, 1):
            if hm[li].any():
                d = ndimage.distance_transform_edt(~hm[li]) * RES; costs[li] = costs[li] * np.where(d <= hugd, 1.0, hugm)
    if layers != 'B':
        # F.Cu: stay out from under other parts' bodies (courtyards not holding an endpoint)
        pts = np.c_[X.ravel(), Y.ravel()]
        for cbb, cpath in CRTYD:
            if cbb[2] < W.x0 or cbb[0] > W.x0 + W.nx * RES or cbb[3] < W.y0 or cbb[1] > W.y0 + W.ny * RES: continue
            if cpath.contains_point((ax, ay)) or cpath.contains_point((bx_, by_)): continue
            inside = cpath.contains_points(pts).reshape(X.shape)
            costs[0] = costs[0] * np.where(inside, 4.0, 1.0)
            if nocrt: free[0] &= ~inside      # quiet nets: never between another part's pads
    if layers != 'F':
        # keep B.Cu runs out from under the power pads (FET, shunt, bus-cap pads): the power-pour job puts via arrays there
        pm = np.zeros((W.ny, W.nx), bool)
        for it in BIGPADS:
            if it.bb[2] < W.x0 - 1 or it.bb[0] > W.x0 + W.nx * RES + 1 or it.bb[3] < W.y0 - 1 or it.bb[1] > W.y0 + W.ny * RES + 1: continue
            x0, y0, x1, y1 = it.bb; pm |= (X >= x0 - 0.6) & (X <= x1 + 0.6) & (Y >= y0 - 0.6) & (Y <= y1 + 0.6)
        costs[1] = costs[1] * np.where(pm, 6.0, 1.0)
    if repel:      # (path, distance, multiplier): leave room beside another track (for a pair partner)
        rp, rd, rmul = repel; hm = np.zeros((W.ny, W.nx), bool)
        for (x, y, li) in rp:
            ix, iy = W.cell(x, y)
            if 0 <= ix < W.nx and 0 <= iy < W.ny and li == 0: hm[iy, ix] = True
        if hm.any(): costs[0] = costs[0] * np.where(ndimage.distance_transform_edt(~hm) * RES < rd, rmul, 1.0)
    if avoid:
        for (x0, y0, x1, y1, li, mult) in avoid: costs[li] = costs[li] * np.where((X >= x0) & (X <= x1) & (Y >= y0) & (Y <= y1), mult, 1.0)
    viaok = None
    if layers == 'FB':
        vo = ~fv[0] & ~fv[1]
        pts = np.c_[X.ravel(), Y.ravel()]
        for cbb, cpath in CRTYD:          # no via under a part body (courtyard), terminal blocks excepted
            if cbb[2] < W.x0 or cbb[0] > W.x0 + W.nx * RES or cbb[3] < W.y0 or cbb[1] > W.y0 + W.ny * RES: continue
            vo &= ~cpath.contains_points(pts).reshape(X.shape)
        viaok = vo.ravel().tolist()
    fr = [bytearray(f.ravel().astype(np.uint8).tobytes()) for f in free]
    S = endpoint(W, A, [f.ravel() for f in free]); G = endpoint(W, B, [f.ravel() for f in free])
    if not S or not G:
        log(f'  FAIL {tag} {net}: no free endpoint cell (start {len(S)} goal {len(G)})'); return None
    N = W.nx * W.ny
    path = astar(W, fr, [c.ravel().tolist() for c in costs], [li * N + iy * W.nx + ix for li, ix, iy in S],
                 [li * N + iy * W.nx + ix for li, ix, iy in G], viaok, viacost / RES)
    if path is None:
        log(f'  FAIL {tag} {net}: no path'); return None
    if maxratio or maxlen:
        maxratio = maxratio or 1e9
        L = sum(math.hypot(path[i + 1][1] - path[i][1], path[i + 1][2] - path[i][2]) for i in range(len(path) - 1)) * RES
        if L > maxratio * math.hypot(ax - bx_, ay - by_) + 2.0 or (maxlen and L > maxlen):
            log(f'  SKIP {tag} {net}: {L:.1f} mm detour for {math.hypot(ax - bx_, ay - by_):.1f} mm (placement)'); return None
    # endpoints given as points: connect the exact point
    def exact(spec, cell):
        if spec[0] == 'pt':
            x, y = W.xy(cell[1], cell[2])
            if abs(x - spec[1]) > 1e-6 or abs(y - spec[2]) > 1e-6: add_track(net, LAY[cell[0]], spec[1], spec[2], x, y, nw if nm[cell[2], cell[1]] else w)
    exact(A, path[0]); exact(B, path[-1])
    # emit segments
    runs = []; cur = [path[0]]
    for c in path[1:]:
        if c[0] != cur[-1][0]:
            runs.append(cur); x, y = W.xy(c[1], c[2]); add_via(net, x, y, d=vd, drill=(0.25 if vd and vd < 0.6 else None)); cur = [c]
        else: cur.append(c)
    runs.append(cur)
    nseg = 0
    for run in runs:
        li = run[0][0]; k = 0
        while k < len(run) - 1:
            d = (run[k + 1][1] - run[k][1], run[k + 1][2] - run[k][2])
            wk = nw if (nm[run[k][2], run[k][1]] or nm[run[k + 1][2], run[k + 1][1]]) else w
            m = k + 1
            while m < len(run) - 1:
                d2 = (run[m + 1][1] - run[m][1], run[m + 1][2] - run[m][2])
                w2 = nw if (nm[run[m][2], run[m][1]] or nm[run[m + 1][2], run[m + 1][1]]) else w
                if d2 != d or w2 != wk: break
                m += 1
            x0, y0 = W.xy(run[k][1], run[k][2]); x1, y1 = W.xy(run[m][1], run[m][2])
            add_track(net, LAY[li], x0, y0, x1, y1, wk); nseg += 1; k = m
    L = sum(math.hypot(path[i + 1][1] - path[i][1], path[i + 1][2] - path[i][2]) for i in range(len(path) - 1) if path[i][0] == path[i + 1][0]) * RES
    nv = sum(1 for i in range(len(path) - 1) if path[i][0] != path[i + 1][0])
    log(f'  ok {tag} {net}: {L:.1f} mm, {nseg} seg, {nv} via')
    return [(*W.xy(c[1], c[2]), c[0]) for c in path]

build_items()
CRTYD = []
for f in b.GetFootprints():
    if f.GetReference() in ('J301', 'J401') or f.IsFlipped(): continue
    cy = f.GetCourtyard(pcbnew.F_CrtYd)
    for P in poly_of(cy):
        CRTYD.append(((P[:, 0].min(), P[:, 1].min(), P[:, 0].max(), P[:, 1].max()), Path(P)))
BIGPADS = [it for it in ITEMS if it.kind == 'poly' and 0 in it.layers and (it.bb[2] - it.bb[0]) * (it.bb[3] - it.bb[1]) >= 2.0
           and (it.net in ('VBUS', 'GND') or '/PH_' in it.net or re.search(r'/SP[ABC]$', it.net))]
ROUTED, FAILED = [], []
def R(net, A, B, w, tag='', **kw):
    p = route(net, A, B, w, tag=tag, **kw)
    (ROUTED if p else FAILED).append((tag, net)); return p

# ================================================================== ESC1 (refs 3xx)
E = '/ESC_Motor_1/'
DRVC = (140.0, 86.5)
NECK = [(DRVC[0] - 4.2, DRVC[1] - 4.2, DRVC[0] + 4.2, DRVC[1] + 4.2)]    # 0.2 mm escape width round the DRV
PHASES = (('A', 'Q301', 'Q302', 'R310', 'R311', '6', '7', '8', 'R307', '9', '10'),
          ('B', 'Q303', 'Q304', 'R312', 'R313', '15', '14', '13', 'R308', '12', '11'),
          ('C', 'Q305', 'Q306', 'R314', 'R315', '16', '17', '18', 'R309', '19', '20'))
def padxy(ref, num):
    q = [p for p in fp[ref].Pads() if p.GetNumber() == num][0].GetPosition(); return q.x / MM, q.y / MM
def g5(v): return round(round((v - 0.05) / RES) * RES + 0.05, 2)       # snap to the route grid
def poly(net, pts, w, layer=FCU):
    """explicit track polyline; w = one width or a list (one per segment)"""
    ws = w if isinstance(w, (list, tuple)) else [w] * (len(pts) - 1)
    for (a, c), wk in zip(zip(pts, pts[1:]), ws): add_track(net, layer, a[0], a[1], c[0], c[1], wk)
# DRV escape fans (ESC1 coordinates, DRV U302 at (140, 86.5) rot 180), designed by hand: 0.2 mm inside the
# 0.5 mm-pitch fan, vias 0.5/0.25 mm. Each entry: net suffix, points, widths, via at the last point (or None).
VS = (0.5, 0.25)
KW = 0.25          # Kelvin pair width
FAN = [
    # top side, phase B (right half): pair lanes, GLB via, SHB via, GHB straight to R312 pad 1 (ends on the 0.1 grid)
    ('GND',  [(142.25, 83.6), (142.25, 83.2), (143.15, 82.3), (143.15, 81.65)], 0.2, None),
    ('SPB',  [(141.75, 83.6), (141.75, 83.1), (142.65, 82.2), (142.65, 81.65)], 0.2, None),
    ('GLB',  [(141.25, 83.6), (141.25, 83.0), (141.95, 82.3), (141.95, 81.65)], 0.2, 'via'),
    ('PH_B', [(140.75, 83.6), (140.75, 82.8), (141.15, 82.4), (141.15, 81.65)], 0.2, 'via'),
    ('GHB',  [(140.25, 83.6), (140.25, 81.0), (140.6, 80.65)], 0.2, None),
    # top side, phase C (left half, mirror about x = 140); GLC stays on F.Cu and runs on past R314
    ('GND',  [(137.75, 83.6), (137.75, 83.2), (136.85, 82.3), (136.85, 81.65)], 0.2, None),
    ('SPC',  [(138.25, 83.6), (138.25, 83.1), (137.35, 82.2), (137.35, 81.65)], 0.2, None),
    ('GLC',  [(138.75, 83.6), (138.75, 83.0), (138.05, 82.3), (138.05, 81.6), (138.05, 80.05)], [0.2, 0.2, 0.2, 0.4], None),
    ('PH_C', [(139.25, 83.6), (139.25, 82.8), (138.85, 82.4), (138.85, 81.65)], 0.2, 'via'),
    ('GHC',  [(139.75, 83.6), (139.75, 81.0), (139.4, 80.65)], 0.2, None),
    # right side, phase A: pair turns NE at once, GLA / SHA vias in the strip above GHA, GHA straight to R310
    ('GND',  [(142.9, 84.25), (143.35, 84.25), (144.25, 83.35)], 0.2, None),
    ('SPA',  [(142.9, 84.75), (143.75, 84.75), (144.65, 83.85)], 0.2, None),
    ('GLA',  [(142.9, 85.25), (146.05, 85.25), (146.25, 85.05)], 0.2, 'via'),
    ('PH_A', [(142.9, 85.75), (146.95, 85.75), (147.25, 85.45)], 0.2, 'via'),
    ('GHA',  [(142.9, 86.25), (148.1, 86.25)], 0.2, None),
]
GHG_VIA = {'A': ('R310', (150.95, 86.25)), 'B': ('R312', (141.0, 77.65)), 'C': ('R314', (139.0, 77.65))}
def esc1():
    log('ESC1')
    T = {}
    nm = lambda n: n if n == 'GND' else E + n
    # --- FET side (fixed): high-side gate via above pin 4, SH via in the phase gap beside source pin 3, low-side
    #     gate via under the channel resistor's pad 1 (phase C: none, GLC is on F.Cu); gate resistor pad 2 -> pin 4
    for ph, qh, ql, rh, rl, gh, sh, gl, rs, sp, sn in PHASES:
        x4, y4 = padxy(qh, '4'); x3, y3 = padxy(qh, '3'); xr, yr = padxy(rl, '1')
        T[f'VGH{ph}'] = (g5(x4), g5(y4 - 1.35)); T[f'VSH{ph}'] = (g5(x3 + 1.15), g5(y3)); T[f'VGL{ph}'] = (g5(xr), g5(yr + 1.45))
        add_via(E + f'GH{ph}_G', *T[f'VGH{ph}']); R(E + f'GH{ph}_G', ('pt', *T[f'VGH{ph}'], 0), ('pad', qh, '4'), 0.4, tag=f'GH{ph}_Gstub')
        add_via(E + f'PH_{ph}', *T[f'VSH{ph}']); R(E + f'PH_{ph}', ('pt', *T[f'VSH{ph}'], 0), ('pad', qh, '3'), 0.3, tag=f'SH{ph}stub')
        if ph != 'C':
            add_via(E + f'GL{ph}', *T[f'VGL{ph}']); R(E + f'GL{ph}', ('pt', *T[f'VGL{ph}'], 0), ('pad', rl, '1'), 0.4, tag=f'GL{ph}stub')
        R(E + f'GL{ph}_G', ('pad', rl, '2'), ('pad', ql, '4'), 0.4, tag=f'GL{ph}_G')
    # --- DRV local: VM -> VBUS via + C320, VCP, CPH/CPL, DVDD, VREF
    add_via('VBUS', 143.75, 87.05)
    R('VBUS', ('pad', 'U302', '4'), ('pt', 143.75, 87.05, 0), 0.3, neck=NECK, tag='VM4')
    R('VBUS', ('pad', 'U302', '5'), ('pt', 143.75, 87.05, 0), 0.3, neck=NECK, tag='VM5')
    R('VBUS', ('pt', 143.75, 87.05, 0), ('pad', 'C320', '1'), 0.4, neck=NECK, tag='VMcap')
    add_via('VBUS', 147.65, 88.75)
    R('VBUS', ('pad', 'C317', '2'), ('pt', 147.65, 88.75, 0), 0.4, tag='VCPcapVBUS')
    R(E + 'VCP', ('pad', 'U302', '3'), ('pad', 'C317', '1'), 0.4, neck=NECK, tag='VCP')
    R(E + 'CPH', ('pad', 'U302', '2'), ('pad', 'C316', '1'), 0.4, neck=NECK, tag='CPH')
    R(E + 'CPL', ('pad', 'U302', '1'), ('pad', 'C316', '2'), 0.4, neck=NECK, tag='CPL')
    R(E + 'DVDD', ('pad', 'U302', '33'), ('pad', 'C318', '1'), 0.3, neck=NECK, tag='DVDD')
    R('+3V3_ESC', ('pad', 'U302', '24'), ('pad', 'C319', '1'), 0.3, neck=NECK, tag='VREF')
    # --- the hand-made escape fans + their vias; high-side gate resistor pad 2 -> via
    END = {}
    for n, pts, w, via in FAN:
        poly(nm(n), pts, w)
        if via: add_via(nm(n), *pts[-1], d=VS[0], drill=VS[1])
        END.setdefault(n, []).append(pts[-1])
    ROUTED.append(('fans', len(FAN)))
    for ph, (rh, v) in GHG_VIA.items():
        add_via(E + f'GH{ph}_G', *v); R(E + f'GH{ph}_G', ('pad', rh, '2'), ('pt', *v, 0), 0.4, tag=f'GH{ph}_Gvia')
    # --- F.Cu continuations: GLC down channel C|B to R315; Kelvin pairs to the shunt lead-ins (SNB hops the SPB lane)
    glc = R(E + 'GLC', ('pt', *END['GLC'][0], 0), ('pad', 'R315', '1'), 0.4, avoid=[(126.0, 80.3, 137.6, 84.0, 0, 6.0)], tag='GLC')
    gnd = {'B': END['GND'][0], 'C': END['GND'][1], 'A': END['GND'][2]}
    for ph in ('B', 'C', 'A'):
        _, qh, ql, rh, rl, gh, sh, gl, rs, sp_pin, sn_pin = [p for p in PHASES if p[0] == ph][0]
        cx, cy = fp[rs].GetPosition().x / MM, fp[rs].GetPosition().y / MM
        sgn = 1 if padxy(rs, '1')[0] > cx else -1
        xsp, xsn = round(cx + sgn * 0.45, 2), round(cx - sgn * 0.45, 2)
        add_track(E + f'SP{ph}', FCU, cx + sgn * 2.45, cy, xsp, cy, KW); add_track('GND', FCU, cx - sgn * 2.45, cy, xsn, cy, KW)
        if ph == 'B':      # SNB has to hop the SPB lane (pins are SP-left / SN-right, the shunt pads the other way)
            sp = R(E + f'SP{ph}', ('pt', xsp, cy, 0), ('pt', *END[f'SP{ph}'][0], 0), KW, tag=f'SP{ph}')
            R('GND', ('pt', xsn, cy, 0), ('pt', *gnd[ph], 0), KW, hug=sp, layers='FB', fnear=40, vd=0.5, tag=f'SN{ph}')
        elif ph == 'C':    # SNC (outer) keeps a lane free beside GLC for SPC, which then hugs SNC
            sn = R('GND', ('pt', xsn, cy, 0), ('pt', *gnd[ph], 0), KW, repel=(glc, 1.15, 8.0), tag=f'SN{ph}')
            R(E + f'SP{ph}', ('pt', xsp, cy, 0), ('pt', *END[f'SP{ph}'][0], 0), KW, hug=sn, tag=f'SP{ph}')
        else:              # outer track (SN) first, SP hugs it
            sn = R('GND', ('pt', xsn, cy, 0), ('pt', *gnd[ph], 0), KW, tag=f'SN{ph}')
            R(E + f'SP{ph}', ('pt', xsp, cy, 0), ('pt', *END[f'SP{ph}'][0], 0), KW, hug=sn, tag=f'SP{ph}')
    # --- B.Cu runs between the DRV-side vias and the FET-side vias; high-side gate beside its SH Kelvin
    SH = {}
    for ph in ('B', 'C', 'A'):
        SH[ph] = R(E + f'PH_{ph}', ('pt', *END[f'PH_{ph}'][0], 1), ('pt', *T[f'VSH{ph}'], 1), 0.3, layers='B', tag=f'SH{ph}')
        R(E + f'GH{ph}_G', ('pt', *GHG_VIA[ph][1], 1), ('pt', *T[f'VGH{ph}'], 1), 0.4, layers='B', hug=SH[ph], hugd=0.9, hugm=3.0, tag=f'GH{ph}_G')
    for ph in ('B', 'A'):
        R(E + f'GL{ph}', ('pt', *END[f'GL{ph}'][0], 1), ('pt', *T[f'VGL{ph}'], 1), 0.4, layers='B', tag=f'GL{ph}')

def pad_at(x, y, li, net):
    """(ref, num) of a pad of `net` on layer li containing (x, y), else None"""
    for (ref, num), lst in PADS.items():
        for pl, P, pn in lst:
            if pl == li and pn == net and P[:, 0].min() - 1e-6 <= x <= P[:, 0].max() + 1e-6 and P[:, 1].min() - 1e-6 <= y <= P[:, 1].max() + 1e-6 \
               and Path(P).contains_point((x, y), radius=1e-4) | Path(P).contains_point((x, y), radius=-1e-4):
                return ref, num
    return None
def net2(n): return n.replace('/ESC_Motor_1/', '/ESC_Motor_2/')
def esc2_reflect(items):
    """ESC2 = ESC1 point-reflected about (140, 107). Every ESC1 track end that sits in a pad must land in the
    matching ESC2 pad (ref +100, same pad number) of the mapped net."""
    log('ESC2 (reflection of ESC1)')
    bad = hits = 0
    for it in items:
        if it[0] != 't': continue
        _, net, L, x0, y0, x1, y1, w = it
        for x, y in ((x0, y0), (x1, y1)):
            hit = pad_at(x, y, LAY.index(L), net)
            if not hit: continue
            hits += 1; rx, ry = refl(x, y); h2 = pad_at(rx, ry, LAY.index(L), net2(net))
            if h2 != (m2(hit[0]), hit[1]):
                bad += 1; log(f'  LANDING MISMATCH {net} {hit} -> {h2} at ({rx:.3f},{ry:.3f})')
    for it in items:
        if it[0] == 't':
            _, net, L, x0, y0, x1, y1, w = it; a, c = refl(x0, y0), refl(x1, y1)
            add_track(net2(net), L, a[0], a[1], c[0], c[1], w)
        else:
            _, net, x, y, d, dr = it; add_via(net2(net), *refl(x, y), d=d, drill=dr)
    log(f'  reflected {len(items)} items; {hits} track ends sit in ESC1 pads, landing mismatches in ESC2: {bad}')
    return bad

def mcu():
    log('STM32 crystal / VCAP / NRST')
    R('/ESC_MCU/OSC_OUT', ('pad', 'U701', '13'), ('pad', 'Y701', '3'), 0.25, tag='OSC_OUT')
    R('/ESC_MCU/OSC_IN', ('pad', 'U701', '12'), ('pad', 'Y701', '1'), 0.25, tag='OSC_IN')
    R('/ESC_MCU/OSC_OUT', ('pad', 'Y701', '3'), ('pad', 'C714', '1'), 0.25, tag='C714')
    R('/ESC_MCU/OSC_IN', ('pad', 'Y701', '1'), ('pad', 'C713', '1'), 0.25, tag='C713')
    R('/ESC_MCU/VCAP1', ('pad', 'U701', '49'), ('pad', 'C711', '1'), 0.25, tag='VCAP1')
    # VCAP2 runs inside the pin row (under the package) so GND pin 74 and +3V3 pin 75 keep their outward exits
    poly('/ESC_MCU/VCAP2', [(122.6, 112.0), (123.5, 112.0), (123.5, 114.175), (122.3, 114.175)], 0.25); ROUTED.append(('VCAP2', 'poly'))
    # NRST crosses the crystal lines: one B.Cu hop
    R('/ESC_NRST', ('pad', 'U701', '14'), ('pad', 'C715', '1'), 0.25, layers='FB', fnear=2.0, vd=0.5, win=3.0, tag='NRST')
def bucks():
    log('aux bucks (U511 24 V, U512 12 V): small-signal nets')
    B = '/Brakes/'; SW = (B + 'SW_24', B + 'SW_12')
    CAPG = [(c, '2') for c in ('C520', 'C521', 'C522', 'C523', 'C534', 'C535', 'C536')] + [('C537', '2'), ('C524', '2')]
    q = dict(keep=SW, keepd=1.0, maxratio=1.6, maxlen=12.0, keep_pads=CAPG, nocrt=True)   # EN / RT: DC, may run a little longer
    qs = dict(keep=SW, keepd=1.0, maxratio=2.0, maxlen=8.0, keep_pads=CAPG, nocrt=True)     # FB / COMP / CZ: short and quiet, or not at all
    for u, v, cb, ena, enb, rt, fbl, fbh, cc, rz, cz in (('U511', '24', 'C528', 'R520', 'R521', 'R522', 'R524', 'R523', 'C527', 'R525', 'C526'),
                                                        ('U512', '12', 'C540', 'R526', 'R527', 'R528', 'R530', 'R529', 'C539', 'R531', 'C538')):
        R(B + f'BOOT_{v}', ('pad', u, '1'), ('pad', cb, '1'), 0.3, keep_pads=CAPG, tag=f'BOOT_{v}')
        R(B + f'EN_{v}', ('pad', u, '3'), ('pad', ena, '2'), 0.25, **q, tag=f'EN_{v}')
        R(B + f'EN_{v}', ('pad', enb, '1'), ('pad', ena, '2'), 0.25, **q, tag=f'EN_{v}b')
        R(B + f'RT_{v}', ('pad', u, '4'), ('pad', rt, '1'), 0.25, **q, tag=f'RT_{v}')
        R(B + f'FB_{v}', ('pad', u, '5'), ('pad', fbl, '1'), 0.25, **qs, tag=f'FB_{v}')
        R(B + f'FB_{v}', ('pad', fbh, '2'), ('pad', fbl, '1'), 0.25, **qs, tag=f'FB_{v}b')
        R(B + f'COMP_{v}', ('pad', u, '6'), ('pad', cc, '1'), 0.25, **qs, tag=f'COMP_{v}')
        R(B + f'COMP_{v}', ('pad', rz, '1'), ('pad', u, '6'), 0.25, **qs, tag=f'COMP_{v}b')
        R(B + f'CZ_{v}', ('pad', rz, '2'), ('pad', cz, '1'), 0.25, **qs, tag=f'CZ_{v}')

esc1()
N1 = list(NEW)
esc2_reflect(N1)
mcu()
bucks()
b.Save(BOARD)
log('saved', BOARD, 'routed', len(ROUTED), 'failed', FAILED)
