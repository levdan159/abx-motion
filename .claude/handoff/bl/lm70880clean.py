"""PCB cleanup after the LM70880 change of the +24V buck U511 (2026-10-25), run AFTER f8.py, KiCad CLOSED.
f8 replaced U511 in place (TPS54560B SO-8 PowerPAD -> LM70880 VQFN-29 with a different pinout), deleted the catch
diode D520 and moved L520 pad 2 from +24V to the new net ISNS_24 (shunt R538 between L520 and +24V). This deletes the
copper that belonged to the old block and would now short or dangle:
  - tracks/vias of the U511 small-signal nets BOOT_24, EN_24, RT_24, FB_24, COMP_24, CZ_24 (critical.py routes them
    again for the new pinout after buckplace.py);
  - the old block's pours (pours.py section 5 rebuilds them): PWR_BATT_U511, PWR_BATT_R520, PWR_SW_24, PWR_GND_U511,
    PWR_GND_EP_U511_*, PWR_GND_P7_U511_F, PWR_24V_L520, and the PWR_VIAS vias inside them (same net);
  - any other track/via with an end inside the new U511 body (6x6 mm + 0.5) or on L520 pad 2 (old +24V copper);
  - then, repeatedly, track ends left dangling by the above or by D520's removal (only on the block's nets);
  - finally moves U511 off-board (x 395): in place it would short the old FB/COMP/RT row until buckplace.py runs.
Locked groups critical_routes / PWR_VIAS lose only these items. Re-runnable (a second run removes nothing).
python lm70880clean.py [board.kicad_pcb]"""
import subprocess as _sp; assert all(_sp.run(['pgrep', '-x', x], capture_output=True).returncode for x in ('kicad', 'eeschema', 'pcbnew')), 'KiCad is running: close it (without saving) first'
import sys, pcbnew
PCB = sys.argv[1] if len(sys.argv) > 1 else '/home/mark/Documents/abx-motion/abx-motion-brushless.kicad_pcb'
MM = 1e6
B = '/Brakes/'
SIG = {B + n for n in ('BOOT_24', 'EN_24', 'RT_24', 'FB_24', 'COMP_24', 'CZ_24')}
BLOCK = SIG | {B + 'SW_24', B + 'ISNS_24', '+24V', '+BATT', 'GND'}
ZONES = ('BATT_U511', 'BATT_R520', 'SW_24', 'GND_U511', 'GND_EP_U511_F', 'GND_EP_U511_B', 'GND_P7_U511_F', '24V_L520')
b = pcbnew.LoadBoard(PCB)
fp = {f.GetReference(): f for f in b.GetFootprints()}
gone = {}; _keep = []          # RemoveNative + keep the python refs (b.Remove + GC segfaults; see espclean.py)
def drop(it, why):
    g = it.GetParentGroup()
    if g: g.RemoveItem(it)
    gone[why] = gone.get(why, 0) + 1; b.RemoveNative(it); _keep.append(it)

# 1. old small-signal routes
for t in list(b.GetTracks()):
    if t.GetNetname() in SIG: drop(t, 'signal ' + t.GetNetname().split('/')[-1])
# 2. old block pours + their vias
zs = [z for z in b.Zones() if z.GetZoneName().startswith('PWR_') and any(p in ZONES for p in z.GetZoneName()[4:].split('+'))]
for z in zs:
    o = z.Outline()
    for t in list(b.GetTracks()):
        if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == z.GetNetname() and o.Contains(t.GetPosition()):
            g = t.GetParentGroup()
            if g and g.GetName() == 'PWR_VIAS': drop(t, 'pour via ' + z.GetZoneName())
    drop(z, 'zone')
# 3. copper ending inside the new U511 body or on L520 pad 2 (other net)
u = fp['U511']; bb = u.GetBoundingBox(False); bb.Inflate(int(0.5 * MM))
l2 = [p for p in fp['L520'].Pads() if p.GetNumber() == '2'][0]
def ends(t): return (t.GetStart(), t.GetEnd()) if t.Type() != pcbnew.PCB_VIA_T else (t.GetPosition(),)
for t in list(b.GetTracks()):
    if any(bb.Contains(p) for p in ends(t)): drop(t, 'in U511 body ' + t.GetNetname())
    elif t.GetNetname() != l2.GetNetname() and any(l2.HitTest(p) for p in ends(t)): drop(t, 'on L520 pad 2 ' + t.GetNetname())
# 4. dangling ends on the block nets (iterate: removing one stub can free the next)
def on_centreline(p, o, tol=0.005 * MM):
    a, c = o.GetStart(), o.GetEnd(); dx, dy = c.x - a.x, c.y - a.y; l2 = dx * dx + dy * dy
    k = 0 if l2 == 0 else max(0.0, min(1.0, ((p.x - a.x) * dx + (p.y - a.y) * dy) / l2))
    return ((p.x - a.x - k * dx) ** 2 + (p.y - a.y - k * dy) ** 2) ** 0.5 <= tol
def connected(p, t, net, items, pads):
    for o in items:
        if o is t: continue
        if o.Type() == pcbnew.PCB_VIA_T:
            if o.GetPosition() == p or o.HitTest(p): return True
        elif o.GetLayer() == t.GetLayer() and on_centreline(p, o): return True   # end-to-end or T on its centre line
    return any(pd.HitTest(p) and (t.Type() == pcbnew.PCB_VIA_T or pd.IsOnLayer(t.GetLayer())) for pd in pads) or \
        any(z.GetNetname() == net and (t.Type() == pcbnew.PCB_VIA_T or z.IsOnLayer(t.GetLayer())) and z.HitTestFilledArea(t.GetLayer() if t.Type() != pcbnew.PCB_VIA_T else z.GetLayer(), p) for z in b.Zones())
pcbnew.ZONE_FILLER(b).Fill(b.Zones())      # fresh fills: a stub or via may have hung on a deleted pour's old fill
reg = pcbnew.BOX2I(pcbnew.VECTOR2I(int(160 * MM), int(104 * MM)), pcbnew.VECTOR2I(int(46 * MM), int(36 * MM)))   # the buck block area
for _ in range(10):
    n0 = sum(gone.values())
    for net in BLOCK:
        items = [t for t in b.GetTracks() if t.GetNetname() == net]
        pads = [p for f in b.GetFootprints() for p in f.Pads() if p.GetNetname() == net]
        for t in items:
            if t.Type() == pcbnew.PCB_VIA_T or not reg.Contains(t.GetStart()): continue
            if not all(connected(p, t, net, items, pads) for p in ends(t)): drop(t, 'dangling ' + net)
        items = [t for t in b.GetTracks() if t.GetNetname() == net]
        for v in [t for t in items if t.Type() == pcbnew.PCB_VIA_T and reg.Contains(t.GetPosition())]:
            p = v.GetPosition()
            if v.GetParentGroup() and v.GetParentGroup().GetName() == 'PWR_VIAS': continue      # pour vias: left to pours.py
            lay = {o.GetLayer() for o in items if o is not v and o.Type() != pcbnew.PCB_VIA_T and on_centreline(p, o)}
            for pd in pads:
                if pd.HitTest(p): lay |= {l for l in pd.GetLayerSet().CuStack()}
            for z in b.Zones():
                if z.GetNetname() == net: lay |= {l for l in z.GetLayerSet().Seq() if z.HitTestFilledArea(l, p)}
            if len(lay) < 2: drop(v, 'dangling via ' + net)      # as DRC via_dangling: copper on fewer than two layers
    if sum(gone.values()) == n0: break
# 5. stage the new U511 off-board: in place its pads would sit on the old FB/COMP/RT row (R522-R524, C527) and short
#    them; buckplace.py puts it (and that row) at the new layout. Staging column of f8.py (x 395, below R540).
if u.GetPosition().x < 214 * MM:
    u.SetPosition(pcbnew.VECTOR2I(int(395.0 * MM), int(122.0 * MM))); gone['U511 staged off-board at (395, 122)'] = 1
b.Save(PCB)
print('removed', dict(sorted(gone.items())))
