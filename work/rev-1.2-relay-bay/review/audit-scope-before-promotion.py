import pcbnew as p,json,hashlib,pathlib
r=pathlib.Path.cwd(); d=r/'work/rev-1.2-relay-bay'; v=d/'review'; c=json.loads((v/'changes.json').read_text()); hashes=json.loads((v/'baseline-hashes.json').read_text())
assert all(hashlib.sha256((r/k).read_bytes()).hexdigest()==h for k,h in hashes.items())
a=p.LoadBoard(str(v/'before.kicad_pcb')); b=p.LoadBoard(str(d/'abx-motion.kicad_pcb'))
allowed={x['ref'] for x in c['moved']}; af={f.GetReference():f for f in a.GetFootprints()}; bf={f.GetReference():f for f in b.GetFootprints()}; assert af.keys()==bf.keys()
for ref,f in af.items():
 g=bf[ref]; assert f.GetValue()==g.GetValue()
 if ref not in allowed: assert f.GetPosition()==g.GetPosition() and f.GetOrientationDegrees()==g.GetOrientationDegrees(),ref
 assert sorted((x.GetNumber(),x.GetNetname(),x.GetDrillSize().x,x.GetDrillSize().y) for x in f.Pads())==sorted((x.GetNumber(),x.GetNetname(),x.GetDrillSize().x,x.GetDrillSize().y) for x in g.Pads()),ref
at={t.m_Uuid.AsString():t for t in a.GetTracks()}; bt={t.m_Uuid.AsString():t for t in b.GetTracks()}
removed=set(at)-set(bt); listed=set()
for key in ('removed_private_tracks','removed_shared_terminal_stubs','removed_unused_local_vias'):
 listed.update(c.get(key,[]))
assert removed<=listed,(removed-listed)
for uid in set(at)&set(bt):
 x,y=at[uid],bt[uid]; assert (x.GetStart(),x.GetEnd(),x.GetWidth(),x.GetLayer(),x.GetNetname())==(y.GetStart(),y.GetEnd(),y.GetWidth(),y.GetLayer(),y.GetNetname()),uid
allowednets=set(c['private_nets'])|{'+5V','GND','/RELAY_1','/RELAY_2'}
for uid in set(bt)-set(at): assert bt[uid].GetNetname() in allowednets,bt[uid].GetNetname()
assert (r/'abx-motion.kicad_pro').read_bytes()==(d/'abx-motion.kicad_pro').read_bytes()
result={'unchanged_footprints':len(af)-len(allowed),'moved_footprints':len(allowed),'preserved_tracks_and_vias':len(set(at)&set(bt)),'removed_local_tracks_and_vias':len(removed),'added_local_tracks_and_vias':len(set(bt)-set(at)),'protected_hashes_verified':len(hashes),'design_rules_unchanged':True}
(v/'scope-audit.json').write_text(json.dumps(result,indent=2));print(result)
