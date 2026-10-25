import pcbnew, sys
for p in sys.argv[1:]:
    b=pcbnew.LoadBoard(p); b.BuildConnectivity(); c=b.GetConnectivity()
    print(p.rsplit('/',2)[-2]+'/'+p.rsplit('/',1)[1], 'unconnected (ratsnest edges):', c.GetUnconnectedCount(True))
