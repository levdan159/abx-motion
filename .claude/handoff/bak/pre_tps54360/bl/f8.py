"""Scripted F8 (Update PCB from Schematic) on the SAVED board, KiCad closed:
add new footprints (staged right of the board), replace footprints whose lib id changed (keeps position),
delete footprints whose symbol is gone, set ref/value, re-assign every pad net from a fresh kicadxml netlist.
A symbol moved to another sheet (new path, same ref + footprint) keeps its footprint (re-pathed: position, copper kept).
Copper (tracks/vias/zones) of a net whose pads all moved to ONE other net follows them (like GUI F8); copper on nets
with no pads left is only reported (delete it separately).
python f8.py [board.kicad_pcb]   ->  then DRC --schematic-parity must report 0 parity issues."""
import subprocess as _sp; assert _sp.run(['pgrep', '-x', 'kicad'], capture_output=True).returncode, 'KiCad is running: close it (without saving) first'
import os, subprocess, xml.etree.ElementTree as ET, pcbnew, sys
sys.path.insert(0, os.path.dirname(__file__)); import sx
P = os.path.expanduser('~/Documents/abx-motion'); PCB = sys.argv[1] if len(sys.argv) > 1 else f'{P}/abx-motion-brushless.kicad_pcb'
NET = '/tmp/claude-1000/-home-mark-Documents-VE-V3/412ee8fb-27c0-4acd-98aa-e7fcd601bdf3/scratchpad/f8_net.xml'
subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadxml', '-o', NET, f'{P}/abx-motion-brushless.kicad_sch'], check=True, capture_output=True)
LIBS = {'abx-footprints': f'{P}/abx-footprints.pretty'}
def libpath(nick): return LIBS.get(nick, f'/usr/share/kicad/footprints/{nick}.pretty')
MM = 1e6
r = ET.parse(NET).getroot()
comps = {}
for c in r.iter('comp'):
    sp = c.find('sheetpath').get('tstamps'); ts = c.find('tstamps').text.split()[0]
    comps[sp + ts] = dict(ref=c.get('ref'), value=c.findtext('value'), fp=c.findtext('footprint') or '', sheet=c.find('sheetpath').get('names'),
                          sfile=next((q.get('value') for q in c.iter('property') if q.get('name') == 'Sheetfile'), ''))
b = pcbnew.LoadBoard(PCB)
have = {f.GetPath().AsString(): f for f in b.GetFootprints()}
added, replaced, removed, repathed = [], [], [], []
stage = [225.0, 60.0]       # off-board: outline is x45-214 since the 12 mm widening
_off = [f.GetPosition().x / 1e6 for f in b.GetFootprints() if f.GetPosition().x / 1e6 > 214]
if _off: stage = [max(225.0, max(_off) + 15), 60.0]   # next free column right of parts already staged (2026-10-24)
oldnet = {(f.GetReference(), p.GetNumber()): p.GetNetname() for f in b.GetFootprints() for p in f.Pads()}
orph = {f.GetReference(): (pth, f) for pth, f in have.items() if pth and pth not in comps}
def load(fpid):
    nick, name = fpid.split(':', 1); f = pcbnew.FootprintLoad(libpath(nick), name)
    assert f is not None, fpid
    f.SetFPID(pcbnew.LIB_ID(nick, name)); f.SetExcludedFromBOM(False)   # symbols here: in_bom yes, dnp no
    return f
for path, c in comps.items():
    if not c['fp']: continue                       # power flags etc.
    old = have.get(path)
    if old is None and c['ref'] in orph and orph[c['ref']][1].GetFPIDAsString() == c['fp']:   # moved to another sheet
        opth, old = orph.pop(c['ref']); del have[opth]
        old.SetPath(pcbnew.KIID_PATH(path)); old.SetSheetname(c['sheet']); old.SetSheetfile(c['sfile']); have[path] = old
        repathed.append(c['ref'])
    if old is not None and old.GetFPIDAsString() == c['fp']:
        old.SetReference(c['ref']); old.SetValue(c['value']); continue
    f = load(c['fp']); f.SetPath(pcbnew.KIID_PATH(path)); f.SetReference(c['ref']); f.SetValue(c['value']); f.SetSheetname(c['sheet']); f.SetSheetfile(c['sfile'])
    if old is not None:
        f.SetPosition(old.GetPosition()); f.SetOrientation(old.GetOrientation())
        if old.IsFlipped(): f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        b.Remove(old); replaced.append(c['ref'])
    else:
        f.SetPosition(pcbnew.VECTOR2I(int(stage[0] * MM), int(stage[1] * MM))); stage[1] += 12
        if stage[1] > 200: stage = [stage[0] + 25, 60.0]
        added.append(c['ref'])
    b.Add(f)
for path, f in have.items():
    if path and path not in comps: removed.append(f.GetReference()); b.Remove(f)
# nets
def net(name):
    ni = b.FindNet(name)
    if ni is None: ni = pcbnew.NETINFO_ITEM(b, name); b.Add(ni)
    return ni
byref = {f.GetReference(): f for f in b.GetFootprints()}
seen = set()
for n in r.iter('net'):
    ni = net(n.get('name'))
    for nd in n.iter('node'):
        f = byref.get(nd.get('ref'))
        if f is None: continue
        for p in f.Pads():
            if p.GetNumber() == nd.get('pin'): p.SetNet(ni); seen.add((nd.get('ref'), nd.get('pin')))
# copper follows re-netted pads (GUI F8 behaviour) when an old net's surviving pads all went to one new net
newnet = {(f.GetReference(), p.GetNumber()): p.GetNetname() for f in b.GetFootprints() for p in f.Pads()}
still = set(newnet.values()); moved = {}
for k, o in oldnet.items():
    if k in newnet and o and o not in still: moved.setdefault(o, set()).add(newnet[k])
renamed, dead = {}, {}
for it in list(b.GetTracks()) + list(b.Zones()):
    n = it.GetNetname()
    if not n or n in still: continue
    tgt = moved.get(n)
    if tgt and len(tgt) == 1:
        it.SetNet(b.FindNet(next(iter(tgt)))); renamed[n] = next(iter(tgt))
    else: dead[n] = dead.get(n, 0) + 1
b.Save(PCB)
print('repathed (moved sheet)', repathed)
print('copper renamed', renamed)
print('copper left on nets without pads', len(dead), sorted(dead.items()))
print('added', len(added), added); print('replaced', replaced); print('removed', len(removed), removed)
