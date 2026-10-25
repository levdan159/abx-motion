"""PCB cleanup after the TPS54360B / precharge change (2026-10-24), run AFTER f8.py, KiCad CLOSED:
- deletes the tracks/vias of the old LMR36520 U1 loop (nets U1_SW, U1_BOOT, U1_FB, U1_VCC): the TPS54360B needs a new
  layout (catch diode D3 in the SW loop, RT/EN/COMP parts), and U1/L1 are new footprints staged off-board by f8;
- deletes the old U1 exposed-pad GND zones PWR_GND_EP_U1_F/_B (pours.py rebuilds them once U1 is placed on the board);
- deletes the PRE_M copper between R803 and R804 (R804 pad 1 is now PRE_M3: R830/R831 go in between).
Locked groups are not touched except these items (all belong to removed parts / changed nets).
python tpsclean.py [board.kicad_pcb]"""
import subprocess as _sp; assert _sp.run(['pgrep', '-x', 'kicad'], capture_output=True).returncode, 'KiCad is running: close it (without saving) first'
import sys, pcbnew
PCB = sys.argv[1] if len(sys.argv) > 1 else '/home/mark/Documents/abx-motion/abx-motion-brushless.kicad_pcb'
NETS = {'/Power_Supply/U1_SW', '/Power_Supply/U1_BOOT', '/Power_Supply/U1_FB', '/Power_Supply/U1_VCC', '/Power_Supply/U1_COMP', '/Bus_Breaker/PRE_M'}   # f8 renames the old U1_VCC copper to U1_COMP (U1 pad 6)
b = pcbnew.LoadBoard(PCB)
gone = {}; _keep = []   # RemoveNative + keep the python refs alive (b.Remove + GC segfaults; espclean.py does the same)
for t in list(b.GetTracks()):
    if t.GetNetname() in NETS:
        g = t.GetParentGroup()
        if g: g.RemoveItem(t)
        gone[t.GetNetname()] = gone.get(t.GetNetname(), 0) + 1; b.RemoveNative(t); _keep.append(t)
# the +BATT track from C4 pad 1 (79.46, 121.46) to the old U1 VIN pins 2/3 (U1 was at 75.5,116.72 rot 90): a stub now
# (DRC track_dangling); group cleanup_routes (not locked)
for t in list(b.GetTracks()):
    if t.GetNetname() == '+BATT' and t.Type() == pcbnew.PCB_TRACE_T and \
       all(74.5 <= p.x / 1e6 <= 79.47 and 118.8 <= p.y / 1e6 <= 121.5 for p in (t.GetStart(), t.GetEnd())):
        g = t.GetParentGroup()
        if g: g.RemoveItem(t)
        gone['+BATT stub'] = gone.get('+BATT stub', 0) + 1; b.RemoveNative(t); _keep.append(t)
zs = [z for z in b.Zones() if z.GetZoneName() in ('PWR_GND_EP_U1_F', 'PWR_GND_EP_U1_B')]
for z in zs: b.RemoveNative(z); _keep.append(z)
b.Save(PCB)
print('tracks/vias removed', gone, '| zones removed', len(zs))
