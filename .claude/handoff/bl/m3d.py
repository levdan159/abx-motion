import pcbnew,os,re
b=pcbnew.LoadBoard('/home/mark/Documents/abx-motion/abx-motion-brushless.kicad_pcb')
env={'KICAD10_3DMODEL_DIR':'/usr/share/kicad/3dmodels','KICAD9_3DMODEL_DIR':'/usr/share/kicad/3dmodels','KICAD8_3DMODEL_DIR':'/usr/share/kicad/3dmodels','KICAD7_3DMODEL_DIR':'/usr/share/kicad/3dmodels','KIPRJMOD':'/home/mark/Documents/abx-motion'}
print('footprints',len(b.GetFootprints()))
miss={}
for f in b.GetFootprints():
    ms=list(f.Models()); fn=f.GetFPID().GetLibItemName().wx_str()
    if not ms: miss.setdefault(('NO MODEL',fn),[]).append(f.GetReference()); continue
    for m in ms:
        p=re.sub(r'\$\{(\w+)\}',lambda x:env.get(x.group(1),x.group(0)),m.m_Filename)
        if not os.path.exists(p) and not os.path.exists(p.rsplit('.',1)[0]+'.step'): miss.setdefault((m.m_Filename,fn),[]).append(f.GetReference())
for k,v in miss.items(): print(k,v)
