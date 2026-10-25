import pcbnew,collections,sys
b=pcbnew.LoadBoard(sys.argv[1])
fps=list(b.GetFootprints()); print('footprints',len(fps))
print('DRV',[f.GetReference() for f in fps if 'DRV' in f.GetValue()][:4],'CSD',sum('CSD' in f.GetValue() for f in fps))
tr=list(b.GetTracks()); print('tracks',len(tr))
used=set()
for f in fps:
    for p in f.Pads():
        if p.GetNetname(): used.add(p.GetNetname())
cnt=collections.Counter()
for t in tr: cnt[t.GetNetname()]+=1
orph={n:c for n,c in cnt.items() if n not in used}
print('tracks on nets with no pad:',sum(orph.values()),'nets',len(orph)); print(sorted(orph.items(),key=lambda x:-x[1])[:30])
zs=[(z.GetNetname(),z.GetLayerName()) for z in b.Zones()]
print('zones',len(zs)); print('zones on unused nets',[z for z in zs if z[0] not in used])
print('at origin:',sum(1 for f in fps if f.GetPosition().x==0 and f.GetPosition().y==0))
bb=b.GetBoardEdgesBoundingBox(); print('outline mm',bb.GetWidth()/1e6,bb.GetHeight()/1e6,'at',bb.GetX()/1e6,bb.GetY()/1e6)
bb=b.GetBoundingBox(); print('all items bbox mm',bb.GetWidth()/1e6,bb.GetHeight()/1e6,bb.GetX()/1e6,bb.GetY()/1e6)
