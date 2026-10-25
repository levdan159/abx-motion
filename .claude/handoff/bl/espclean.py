"""Copper cleanup after the ESP32 / Industrial_IO / Sensors + 12 V buck removal (2026-10-24), run after f8.py.
Usage: ~/.cache/mark-mods/kicad-mcp-big-venv/bin/python espclean.py <board.kicad_pcb> --baseline <pre-F8 board> [--drc drc.json]
(KiCad CLOSED). Tracks that were already 'dangling' on the baseline board (12 tiny Freerouting stubs inside pads, which
KiCad DRC does not flag) are left alone.
 1. tracks / vias / zones on nets that have no pad left (the removed parts' nets) are deleted;
 2. the 12 V buck's PWR_ pours on surviving nets (+BATT input, GND / EP pours of U512) + the PWR_VIAS vias inside them;
 2b. tracks / vias of another net that end inside a pad (a pad F8 re-netted, e.g. U706 A4/A5 GND -> VBAT_SENSE / BUS_IMON);
 3. tracks with a dangling end and dangling vias are trimmed, repeatedly, until none is left (the removed parts' stubs on GND/+3V3/...);
 4. with a DRC json: items it reports as track_dangling / via_dangling are deleted too (then step 3 again).
Never touches the locked groups critical_routes / PWR_VIAS (and PWR_* zones) except copper of the removed 12 V block
(nets +12V / /Brakes/*_12 and the U512 pours): such items are only reported. Idempotent (a 2nd run deletes nothing)."""
import subprocess as _sp; assert _sp.run(['pgrep', '-x', 'kicad'], capture_output=True).returncode, 'KiCad is running: close it (without saving) first'
import sys, json, collections  # noqa: E402
import pcbnew  # noqa: E402

a = sys.argv[1:]; P = a[0]
BASE = a[a.index('--baseline') + 1]; DRC = a[a.index('--drc') + 1] if '--drc' in a else None
assert P.endswith('.kicad_pcb') and BASE.endswith('.kicad_pcb')
MM = 1e6
_b0 = pcbnew.LoadBoard(BASE); _b0.BuildConnectivity(); _c0 = _b0.GetConnectivity()
OLD_DANGLING = {t.m_Uuid.AsString() for t in _b0.GetTracks() if _c0.TestTrackEndpointDangling(t, False)}
b = pcbnew.LoadBoard(P)
PROTECT = ('critical_routes', 'PWR_VIAS')
U512_ZONES = ('PWR_BATT_C536', 'PWR_BATT_R526', 'PWR_BATT_U512', 'PWR_GND_U512', 'PWR_GND_EP_U512_F+GND_P7_U512_F',
              'PWR_GND_EP_U512_B', 'PWR_SW_12', 'PWR_12V_F', 'PWR_12V_B')
def is12(n): return n == '+12V' or (n.startswith('/Brakes/') and n.endswith('_12'))
grp = {}
for g in b.Groups():
    for it in g.GetItems(): grp[it.m_Uuid.AsString()] = g
_gone = []                                   # keep removed items referenced (SWIG frees -> crashes, see pours.py)
stats = collections.Counter(); kept = collections.Counter()
def drop(it, why):
    g = grp.get(it.m_Uuid.AsString())
    if g is not None: g.RemoveItem(it)
    b.RemoveNative(it); _gone.append(it); stats[why] += 1
def protected(it): g = grp.get(it.m_Uuid.AsString()); return g is not None and g.GetName() in PROTECT

padnets = {p.GetNetname() for f in b.GetFootprints() for p in f.Pads()}
# 1. copper on nets without pads
for it in list(b.GetTracks()):
    n = it.GetNetname()
    if n and n not in padnets:
        if protected(it) and not is12(n): kept['protected, dead net ' + n] += 1; continue
        drop(it, 'dead-net track/via')
# 2. zones on dead nets + the U512 pours (and the power vias inside them)
rmz = []
for z in list(b.Zones()):
    n = z.GetNetname()
    if z.GetZoneName() in U512_ZONES or (n and n not in padnets):
        if z.GetZoneName().startswith('PWR_') and not (z.GetZoneName() in U512_ZONES or is12(n)):
            kept['protected zone ' + z.GetZoneName()] += 1; continue
        rmz.append((n, pcbnew.SHAPE_POLY_SET(z.Outline()), z.GetLayer())); drop(z, 'zone ' + (z.GetZoneName() or n))
for v in list(b.GetTracks()):
    if v.Type() != pcbnew.PCB_VIA_T: continue
    g = grp.get(v.m_Uuid.AsString())
    if g is None or g.GetName() != 'PWR_VIAS': continue
    if any(n == v.GetNetname() and s.Contains(v.GetPosition()) for n, s, _l in rmz): drop(v, 'U512 pour via')
# 2b. foreign-net copper ending in a pad
CELL = int(2 * MM); grid = collections.defaultdict(list)
for f in b.GetFootprints():
    for p in f.Pads():
        bb = p.GetBoundingBox()
        for gx in range(bb.GetX() // CELL, bb.GetRight() // CELL + 1):
            for gy in range(bb.GetY() // CELL, bb.GetBottom() // CELL + 1): grid[(gx, gy)].append(p)
for t in list(b.GetTracks()):
    pts = [t.GetPosition()] if t.Type() == pcbnew.PCB_VIA_T else [t.GetStart(), t.GetEnd()]
    hit = None
    for q in pts:
        for p in grid.get((q.x // CELL, q.y // CELL), ()):
            if p.GetNetname() != t.GetNetname() and p.GetNetname() and (t.Type() == pcbnew.PCB_VIA_T or p.IsOnLayer(t.GetLayer())) and p.HitTest(q, (t.GetWidth(pcbnew.F_Cu) if t.Type() == pcbnew.PCB_VIA_T else t.GetWidth()) // 2):
                hit = p; break
        if hit: break
    if hit is None: continue
    if protected(t): kept[f'protected, ends in foreign pad {hit.GetParentFootprint().GetReference()}.{hit.GetNumber()}'] += 1; continue
    print(f'  foreign-pad copper: {t.GetNetname()} in {hit.GetParentFootprint().GetReference()}.{hit.GetNumber()} [{hit.GetNetname()}]')
    drop(t, 'foreign-net copper in a pad')
# 3. trim dangling track ends (iterate: a removed stub can expose the next segment)
def trim():
  global kept
  while True:
      b.BuildConnectivity(); c = b.GetConnectivity(); n0 = sum(stats.values())
      for t in list(b.GetTracks()):
          if t.m_Uuid.AsString() in OLD_DANGLING or not c.TestTrackEndpointDangling(t, False): continue
          kind = 'via' if t.Type() == pcbnew.PCB_VIA_T else 'track'
          if protected(t) and not is12(t.GetNetname()): kept[f'protected dangling {kind} ' + t.GetNetname()] += 1; continue
          drop(t, 'dangling ' + kind)
      if sum(stats.values()) == n0: break
      kept = collections.Counter({k: v for k, v in kept.items() if not k.startswith('protected dangling')})
trim()
# 4. DRC-reported dangling items
if DRC:
    bad = set()
    for v in json.load(open(DRC))['violations']:
        if v['type'] in ('track_dangling', 'via_dangling'): bad |= {i['uuid'] for i in v['items']}
    for t in list(b.GetTracks()):
        if t.m_Uuid.AsString() in bad:
            if protected(t) and not is12(t.GetNetname()): kept['protected DRC-dangling ' + t.GetNetname()] += 1; continue
            drop(t, 'DRC dangling ' + ('via' if t.Type() == pcbnew.PCB_VIA_T else 'track'))
    trim()
b.Save(P)
for k, v in sorted(stats.items()): print(f'deleted {v:5d}  {k}')
for k, v in sorted(kept.items()): print(f'KEPT    {v:5d}  {k}')
print('saved', P)
