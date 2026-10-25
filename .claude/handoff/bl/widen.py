"""Widen the board 12 mm to the right (owner decision 2026-10-24): Edge.Cuts x 202 -> 214, zone outlines x 201.5 -> 213.5,
J1 / H2 / H4 moved +12 mm to stay on the edge. KiCad must be CLOSED."""
import subprocess as _sp; assert _sp.run(['pgrep', '-x', 'kicad'], capture_output=True).returncode, 'KiCad is running: close it (without saving) first'
import pcbnew
P = '/home/mark/Documents/abx-motion/abx-motion-brushless.kicad_pcb'; MM = 1e6; DX = 12.0
b = pcbnew.LoadBoard(P)
for d in b.GetDrawings():
    if d.GetLayer() == pcbnew.Edge_Cuts:
        s, e = d.GetStart(), d.GetEnd()
        if abs(s.x / MM - 202) < .01: d.SetStart(pcbnew.VECTOR2I(int((202 + DX) * MM), s.y))
        if abs(e.x / MM - 202) < .01: d.SetEnd(pcbnew.VECTOR2I(int((202 + DX) * MM), e.y))
for z in b.Zones():
    o = z.Outline()
    for i in range(o.TotalVertices()):
        v = o.CVertex(i)
        if abs(v.x / MM - 201.5) < .01: o.SetVertex(i, pcbnew.VECTOR2I(int((201.5 + DX) * MM), v.y))
for r in ('J1', 'H2', 'H4'):
    f = b.FindFootprintByReference(r); p = f.GetPosition(); f.SetPosition(pcbnew.VECTOR2I(p.x + int(DX * MM), p.y))
b.Save(P); print('widened to', b.GetBoardEdgesBoundingBox().GetRight() / MM)
