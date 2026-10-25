import pcbnew
b=pcbnew.LoadBoard('/home/mark/Documents/abx-motion/abx-motion-brushless.kicad_pcb'); MM=1e6
fp={f.GetReference():f for f in b.GetFootprints()}
for r in ['J205','J207','J102','J501','J502','J1','LOGO1','LOGO2','H3','H4','F1','J210','J211','J202']:
    f=fp[r]; print(r,f.GetX()/MM,f.GetY()/MM,f.GetOrientationDegrees(),f.GetLayerName(),[(p.GetNumber(),p.GetNetname(),round(p.GetX()/MM,1),round(p.GetY()/MM,1)) for p in f.Pads()][:3])
f=fp['LOGO2']; print(set(i.GetLayerName() for i in f.GraphicalItems()), len(list(f.Pads())))
