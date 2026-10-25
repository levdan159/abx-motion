import pcbnew
P='/home/mark/Documents/abx-motion/abx-motion-brushless.kicad_pcb'
b=pcbnew.LoadBoard(P); MM=1000000
gnd=b.FindNet('GND')
pts=[(45.5,48.5),(201.5,48.5),(201.5,165.5),(45.5,165.5)]
for layer,prio in ((pcbnew.F_Cu,0),(pcbnew.In1_Cu,1),(pcbnew.B_Cu,0)):
    z=pcbnew.ZONE(b); z.SetLayer(layer); z.SetNet(gnd); z.SetAssignedPriority(prio)
    z.SetMinThickness(200000); z.SetLocalClearance(250000)
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL); z.SetThermalReliefGap(300000); z.SetThermalReliefSpokeWidth(400000)
    ol=z.Outline(); ol.NewOutline()
    for x,y in pts: ol.Append(int(x*MM),int(y*MM))
    b.Add(z)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(P); print('zones',len(list(b.Zones())))
