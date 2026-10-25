"""Simple 3D bodies for packages KiCad ships no model for: PowerDI-5 (D520/D521) and TI DGX0019A VSSOP-19 (U801).
usage: <ocp-python> models3d_ic.py <outdir>   (footprint frame: X right, Y = -footprint y, Z up)"""
import sys
from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
from OCP.gp import gp_Pnt
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
out = sys.argv[1]
def box(x0, y0, z0, x1, y1, z1): return BRepPrimAPI_MakeBox(gp_Pnt(x0, y0, z0), gp_Pnt(x1, y1, z1)).Shape()
def fuse(*s):
    r = s[0]
    for q in s[1:]: r = BRepAlgoAPI_Fuse(r, q).Shape()
    return r
def save(shape, name):
    w = STEPControl_Writer(); w.Transfer(shape, STEPControl_AsIs); w.Write(f'{out}/{name}.step'); print('wrote', name)
# PowerDI-5 (Diodes Inc): cathode tab under pad 1 (x -1.12), two anode leads at pad 2 (x 2.86, y +-0.92); body ~5.3 x 4.0 x 1.1
save(fuse(box(-3.2, -2.0, 0.0, 2.1, 2.0, 1.1), box(-3.5, -1.6, 0.0, -1.0, 1.6, 0.15),
          box(2.1, -1.2, 0.0, 3.4, -0.62, 0.15), box(2.1, 0.62, 0.0, 3.4, 1.2, 0.15)), 'D_PowerDI-5_simple')
# DGX0019A VSSOP-19: body 3.0 (x) x 5.1 (y) x 1.0, gull-wing leads in two rows at x +-2.2, pitch 0.5 (20 positions, 16 absent)
leads = [box(sx * 1.5 if sx > 0 else -2.6, -2.25 + 0.5 * i - 0.12, 0.0, 2.6 if sx > 0 else -1.5, -2.25 + 0.5 * i + 0.12, 0.15)
         for sx in (-1, 1) for i in range(10)]
save(fuse(box(-1.5, -2.55, 0.05, 1.5, 2.55, 1.0), *leads), 'TI_DGX0019A_VSSOP-19_simple')
