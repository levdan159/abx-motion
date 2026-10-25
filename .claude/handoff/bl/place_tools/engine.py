"""Copper-aware pose search on a routed board (pcbnew). Used to FIND poses; the result is written as absolute
coordinates into bl/newplace.py, which is what runs on the boards.

Blocked for a new part's PADS (inflated by CL): foreign-net F.Cu tracks/vias/pads (B.Cu too for THT pads), F.Cu PWR_
zones of another net, board edge (EDGE mm). Blocked for its COURTYARD: other courtyards (placed parts + already placed
new parts), keep-out rects. 'Removable' copper = GND tracks/vias of cleanup_routes or no group (pour stitches / stubs):
never blocks; newplace.py deletes what a new pad would touch."""
import math
import numpy as np
from scipy import ndimage
import pcbnew
from matplotlib.path import Path

MM = 1e6
R = 0.1
X0, Y0, X1, Y1 = 44.925, 47.925, 214.075, 166.075
CL = 0.32          # pad-to-foreign-copper (Power_HV 0.25 + raster slack)
EDGE = 0.6         # pad copper to board edge
PROT = ('critical_routes', 'PWR_VIAS')


def removable(t):
    g = t.GetParentGroup()
    g = g.GetName() if g else None
    return t.GetNetname() == 'GND' and g in (None, 'cleanup_routes')


class Occ:
    def __init__(self, board, moving=()):
        self.b = board
        self.nx, self.ny = int((X1 - X0) / R) + 2, int((Y1 - Y0) / R) + 2
        self.Fn = {}   # net -> not needed; we keep per-cell net id (-1 = several / any)
        self.F = np.full((self.ny, self.nx), 0, np.int32)    # 0 free, >0 netcode, -1 multi
        self.B = np.full((self.ny, self.nx), 0, np.int32)
        self.C = np.zeros((self.ny, self.nx), bool)
        self.K = np.zeros((self.ny, self.nx), bool)          # keep-out for courtyards
        self.moving = set(moving)
        self.exact = []
        yy, xx = np.mgrid[0:self.ny, 0:self.nx]
        self.px, self.py = X0 + xx * R, Y0 + yy * R
        for t in board.GetTracks():
            if removable(t):
                continue
            nc = t.GetNetCode()
            if t.Type() == pcbnew.PCB_VIA_T:
                p = t.GetPosition(); r = t.GetWidth(pcbnew.F_Cu) / MM / 2
                self.seg(self.F, p.x / MM, p.y / MM, p.x / MM, p.y / MM, r, nc)
                self.seg(self.B, p.x / MM, p.y / MM, p.x / MM, p.y / MM, r, nc)
            else:
                s, e = t.GetStart(), t.GetEnd(); r = t.GetWidth() / MM / 2
                A = self.F if t.GetLayer() == pcbnew.F_Cu else self.B if t.GetLayer() == pcbnew.B_Cu else None
                if A is not None:
                    self.seg(A, s.x / MM, s.y / MM, e.x / MM, e.y / MM, r, nc)
        for f in board.GetFootprints():
            if f.GetReference() in self.moving or f.GetPosition().x / MM > 216:
                continue
            self.add_fp(f)
        for z in board.Zones():
            if not z.GetZoneName().startswith('PWR_'):
                continue
            o = z.Outline().COutline(0)
            pts = [(o.CPoint(k).x / MM, o.CPoint(k).y / MM) for k in range(o.PointCount())]
            if z.GetLayer() == pcbnew.F_Cu:
                self.poly(self.F, pts, z.GetNetCode())
            if z.GetLayer() == pcbnew.B_Cu:
                self.poly(self.B, pts, z.GetNetCode())

    # ---- raster primitives (value v; overlapping different nets -> -1)
    def _win(self, x0, y0, x1, y1):
        i0 = max(int((x0 - X0) / R), 0); i1 = min(int((x1 - X0) / R) + 2, self.nx)
        j0 = max(int((y0 - Y0) / R), 0); j1 = min(int((y1 - Y0) / R) + 2, self.ny)
        return i0, i1, j0, j1

    def _mark(self, A, j0, j1, i0, i1, m, v):
        if A.dtype == bool:
            A[j0:j1, i0:i1] |= m; return
        sub = A[j0:j1, i0:i1]
        other = m & (sub != 0) & (sub != v)
        sub[m & (sub == 0)] = v
        sub[other] = -1

    def seg(self, A, ax, ay, bx, by, r, v=1):
        i0, i1, j0, j1 = self._win(min(ax, bx) - r, min(ay, by) - r, max(ax, bx) + r, max(ay, by) + r)
        if i0 >= i1 or j0 >= j1: return
        X = self.px[j0:j1, i0:i1]; Y = self.py[j0:j1, i0:i1]; dx, dy = bx - ax, by - ay; l2 = dx * dx + dy * dy
        t = np.zeros_like(X) if l2 == 0 else np.clip(((X - ax) * dx + (Y - ay) * dy) / l2, 0, 1)
        self._mark(A, j0, j1, i0, i1, np.hypot(X - ax - t * dx, Y - ay - t * dy) <= r, v)

    def poly(self, A, pts, v=1):
        p = np.array(pts)
        i0, i1, j0, j1 = self._win(p[:, 0].min(), p[:, 1].min(), p[:, 0].max(), p[:, 1].max())
        if i0 >= i1 or j0 >= j1: return
        m = Path(p).contains_points(np.c_[self.px[j0:j1, i0:i1].ravel(), self.py[j0:j1, i0:i1].ravel()]).reshape(j1 - j0, i1 - i0)
        self._mark(A, j0, j1, i0, i1, m, v)

    def rect(self, A, x0, y0, x1, y1, v=1):
        self.poly(A, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], v)

    def add_fp(self, f):
        cy = f.GetCourtyard(pcbnew.B_CrtYd if f.IsFlipped() else pcbnew.F_CrtYd)
        if not f.IsFlipped() and cy.OutlineCount():
            c = pcbnew.SHAPE_POLY_SET(cy); self.exact.append((c, c.BBox(), f.GetReference()))
        if not f.IsFlipped():
            if cy.OutlineCount():
                for k in range(cy.OutlineCount()):
                    o = cy.COutline(k)
                    self.poly(self.C, [(o.CPoint(i).x / MM, o.CPoint(i).y / MM) for i in range(o.PointCount())])
            elif f.Pads():
                bb = f.GetBoundingBox(False, False)
                self.rect(self.C, bb.GetX() / MM, bb.GetY() / MM, bb.GetRight() / MM, bb.GetBottom() / MM)
        for q in f.Pads():
            for lay, A in ((pcbnew.F_Cu, self.F), (pcbnew.B_Cu, self.B)):
                if q.IsOnLayer(lay):
                    for (x0, y0, x1, y1) in pad_rects(q):
                        self.rect(A, x0, y0, x1, y1, q.GetNetCode() or -1)
            if q.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
                bb = q.GetBoundingBox()
                self.rect(self.F, bb.GetX() / MM, bb.GetY() / MM, bb.GetRight() / MM, bb.GetBottom() / MM, -1)
                self.rect(self.B, bb.GetX() / MM, bb.GetY() / MM, bb.GetRight() / MM, bb.GetBottom() / MM, -1)

    # ---- legality of a footprint at its CURRENT pose
    def check(self, f, why=None):
        bad = []
        for q in f.Pads():
            nc = q.GetNetCode()
            th = q.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
            for (x0, y0, x1, y1) in pad_rects(q):
                if x0 < X0 + EDGE or y0 < Y0 + EDGE or x1 > X1 - EDGE or y1 > Y1 - EDGE:
                    bad.append(('edge', q.GetNumber())); continue
                i0, i1, j0, j1 = self._win(x0 - CL, y0 - CL, x1 + CL, y1 + CL)
                for lay, A in ((pcbnew.F_Cu, self.F), (pcbnew.B_Cu, self.B)):
                    if not (q.IsOnLayer(lay) or th): continue
                    sub = A[j0:j1, i0:i1]
                    hit = (sub != 0) & ((sub != nc) | (nc == 0))
                    if hit.any(): bad.append(('cu' + ('F' if lay == pcbnew.F_Cu else 'B'), q.GetNumber()))
        cy = f.GetCourtyard(pcbnew.F_CrtYd)
        for k in range(cy.OutlineCount()):
            o = cy.COutline(k)
            pts = np.array([(o.CPoint(i).x / MM, o.CPoint(i).y / MM) for i in range(o.PointCount())])
            # shrink by one cell: touching courtyards are legal
            cx, cyy = pts.mean(0)
            i0, i1, j0, j1 = self._win(pts[:, 0].min(), pts[:, 1].min(), pts[:, 0].max(), pts[:, 1].max())
            m = Path(pts).contains_points(np.c_[self.px[j0:j1, i0:i1].ravel(), self.py[j0:j1, i0:i1].ravel()]).reshape(j1 - j0, i1 - i0)
            m = ndimage.binary_erosion(m, iterations=2)
            if (m & self.C[j0:j1, i0:i1]).any(): bad.append(('crt', ''))
            elif self.exact:
                me = pcbnew.SHAPE_POLY_SET(cy); bb = me.BBox()
                for g in self.exact:
                    gb = g[1]
                    if gb.GetRight() < bb.GetX() or gb.GetX() > bb.GetRight() or gb.GetBottom() < bb.GetY() or gb.GetY() > bb.GetBottom(): continue
                    s = pcbnew.SHAPE_POLY_SET(me); s.BooleanIntersection(g[0])
                    if s.OutlineCount() and s.Area() > 0: bad.append(('crtx', g[2])); break
            if (m & self.K[j0:j1, i0:i1]).any(): bad.append(('keepout', ''))
            if pts[:, 0].min() < X0 - 0.3 or pts[:, 1].min() < Y0 - 0.3 or pts[:, 0].max() > X1 + 0.3 or pts[:, 1].max() > Y1 + 0.3:
                bad.append(('outline', ''))
        return bad


def pad_rects(q):
    bb = q.GetBoundingBox()
    return [(bb.GetX() / MM, bb.GetY() / MM, bb.GetRight() / MM, bb.GetBottom() / MM)]


def pose(f, x, y, rot):
    f.SetOrientationDegrees(rot)
    f.SetPosition(pcbnew.VECTOR2I(int(round(x * MM)), int(round(y * MM))))


def rel(ax, ay, arot, dx, dy):
    """offset (dx, dy) in the anchor's rot-0 frame -> board coords for an anchor at (ax, ay, arot)"""
    a = math.radians(arot)
    return ax + dx * math.cos(a) + dy * math.sin(a), ay - dx * math.sin(a) + dy * math.cos(a)
