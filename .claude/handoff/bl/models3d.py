"""Build 3D models (OCP / cadquery-ocp venv):
- Degson DG135T-10.16-02P from Degson's STEP (download id 2151301; header says 03P, geometry is 2-pole), re-oriented to the
  footprint frame (X = pole axis, pole 1 at 0 / 10.16; Y = -footprint y, rows at 0 / -10.16 -> Y 0 / 10.16; Z up).
  STEP frame: x = depth (wire entry at x=0, rows x 6.4 / 16.2: 9.8 mm, drawing says 10.16), y = height, z = pole axis (5.08 / 15.24).
- DG135T-10.16-03P = 02P fused with a copy shifted one pitch.
- AMASS XT60PW-F simple body (KiCad ships no horizontal XT60 model).
usage: <ocp-python> models3d.py <degson.step> <outdir>"""
import sys
from OCP.STEPControl import STEPControl_Reader, STEPControl_Writer, STEPControl_AsIs
from OCP.gp import gp_Trsf, gp_Vec, gp_Pnt, gp_Dir, gp_GTrsf, gp_Mat
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform, BRepBuilderAPI_GTransform
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCP.gp import gp_Ax2
src, out = sys.argv[1], sys.argv[2]
r = STEPControl_Reader(); r.ReadFile(src); r.TransferRoots(); s = r.OneShape()
# permutation (x, y, z) -> (z, x, y) then shift: X = z - 5.08, Y = x - 6.4 (front row on Y 0), Z = y
g = gp_GTrsf(); g.SetVectorialPart(gp_Mat(0, 0, 1, 1, 0, 0, 0, 1, 0)); g.SetTranslationPart(gp_Pnt(-5.08, -6.4, 0).XYZ())
two = BRepBuilderAPI_GTransform(s, g, True).Shape()
def save(shape, name):
    w = STEPControl_Writer(); w.Transfer(shape, STEPControl_AsIs); w.Write(f'{out}/{name}.step'); print('wrote', name)
save(two, 'Degson_DG135T-10.16-02P')
t = gp_Trsf(); t.SetTranslation(gp_Vec(10.16, 0, 0))
f = BRepAlgoAPI_Fuse(two, BRepBuilderAPI_Transform(two, t, True).Shape()); f.Build()
save(f.Shape(), 'Degson_DG135T-10.16-03P')
# XT60PW-F (horizontal, female): pins at X 0 / -7.2, mouth toward +Y (footprint -y), body 16 x 15.9 x 8.2 mm
body = BRepPrimAPI_MakeBox(gp_Pnt(-11.6, 0.6, 0.0), 15.8, 15.3, 8.2).Shape()
for px in (0.0, -7.2):
    pin = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(px, 0.0, -3.0), gp_Dir(0, 0, 1)), 0.75, 7.0).Shape()
    body = BRepAlgoAPI_Fuse(body, pin).Shape()
save(body, 'AMASS_XT60PW-F_simple')
