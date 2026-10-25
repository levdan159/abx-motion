"""Attach 3D models: Degson DG135T (lib + J1/J301/J401), XT60PW-F (J510), and re-copy library models onto board
footprints whose model list is empty. KiCad must be CLOSED."""
import subprocess as _sp; assert _sp.run(['pgrep', '-x', 'kicad'], capture_output=True).returncode, 'KiCad is running: close it (without saving) first'
import pcbnew, os
P = os.path.expanduser('~/Documents/abx-motion'); PCB = f'{P}/abx-motion-brushless.kicad_pcb'
M = {'ABX_Degson_DG135T-10.16-02P': '${KIPRJMOD}/3dmodels/Degson_DG135T-10.16-02P.step',
     'ABX_Degson_DG135T-10.16-03P': '${KIPRJMOD}/3dmodels/Degson_DG135T-10.16-03P.step',
     'AMASS_XT60PW-F_1x02_P7.20mm_Horizontal': '${KIPRJMOD}/3dmodels/AMASS_XT60PW-F_simple.step'}
def setmodel(f, path):
    f.Models().clear(); m = pcbnew.FP_3DMODEL(); m.m_Filename = path; m.m_Show = True; f.Models().push_back(m)
lib = f'{P}/abx-footprints.pretty'
for name in ('ABX_Degson_DG135T-10.16-02P', 'ABX_Degson_DG135T-10.16-03P'):
    f = pcbnew.FootprintLoad(lib, name); setmodel(f, M[name]); pcbnew.FootprintSave(lib, f)
b = pcbnew.LoadBoard(PCB); n = 0
for f in b.GetFootprints():
    lid = f.GetFPID(); name = lid.GetLibItemName().wx_str()
    if name in M: setmodel(f, M[name]); n += 1; continue
    if len(f.Models()) == 0 and lid.GetLibNickname().wx_str() not in ('abx-footprints', 'MountingHole', 'TestPoint', 'Jumper'):
        src = pcbnew.FootprintLoad(f'/usr/share/kicad/footprints/{lid.GetLibNickname().wx_str()}.pretty', name)
        if src is not None and len(src.Models()):
            setmodel(f, src.Models()[0].m_Filename); n += 1; print('  lib model ->', f.GetReference())
b.Save(PCB); print('models set on', n, 'footprints')
