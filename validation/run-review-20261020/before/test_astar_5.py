#!/usr/bin/env python3
"""
Test localized obstacle-aware A* routing for ONLY the 5 missing connections:
- /Industrial_IO/M1_MIN_RAW
- /Industrial_IO/M2_MAX_IN
- /Industrial_IO/S1_MIN_IN
- /Industrial_IO/S1_MAX_IN
- /MCU_and_Encoders/BTN_HOME
"""
import shutil
import math
import heapq
import pcbnew

BASE_PCB = "/tmp/checkpoint_base.kicad_pcb"
OUT_PCB = "/home/daniel/Documents/kicad/abx-motion/abx-motion.kicad_pcb"

def pt(x_mm, y_mm):
    return pcbnew.VECTOR2I(pcbnew.FromMM(round(x_mm, 4)), pcbnew.FromMM(round(y_mm, 4)))

def near(val1, val2, tol=0.025):
    return abs(val1 - val2) <= tol

def near_pt(p, x_mm, y_mm, tol=0.03):
    return near(pcbnew.ToMM(p.x), x_mm, tol) and near(pcbnew.ToMM(p.y), y_mm, tol)

def match_seg(t, layer, net, x1, y1, x2, y2, tol=0.03):
    if t.GetClass() == "PCB_VIA" or t.GetLayer() != layer or t.GetNetname() != net:
        return False
    s, e = t.GetStart(), t.GetEnd()
    return (near_pt(s, x1, y1, tol) and near_pt(e, x2, y2, tol)) or (near_pt(s, x2, y2, tol) and near_pt(e, x1, y1, tol))

def match_via(t, net, x, y, tol=0.03):
    if t.GetClass() != "PCB_VIA" or t.GetNetname() != net:
        return False
    return near_pt(t.GetPosition(), x, y, tol)

def add_seg(board, net_code, layer, x1, y1, x2, y2, width_mm=0.20):
    seg = pcbnew.PCB_TRACK(board)
    seg.SetStart(pt(x1, y1))
    seg.SetEnd(pt(x2, y2))
    seg.SetLayer(layer)
    seg.SetWidth(pcbnew.FromMM(width_mm))
    seg.SetNetCode(net_code)
    board.Add(seg)
    return seg

def add_chain(board, net_code, layer, pts, width_mm=0.20):
    for i in range(len(pts) - 1):
        add_seg(board, net_code, layer, pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1], width_mm)

def add_via(board, net_code, x, y, size_mm=0.60, drill_mm=0.30):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pt(x, y))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetWidth(pcbnew.FromMM(size_mm))
    v.SetDrill(pcbnew.FromMM(drill_mm))
    v.SetNetCode(net_code)
    board.Add(v)
    return v

def dist_point_to_seg(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))

def dist_point_to_rect(px, py, cx, cy, sx, sy):
    dx = max(0.0, abs(px - cx) - sx * 0.5)
    dy = max(0.0, abs(py - cy) - sy * 0.5)
    return math.hypot(dx, dy)

class ExactGeometryRouter:
    def __init__(self, board):
        self.board = board
        self.pads = []   # (net, f_cu, b_cu, is_hole, cx, cy, sx, sy, drill_r)
        self.vias = []   # (net, cx, cy, r_cu, r_drill)
        self.segs = {pcbnew.F_Cu: [], pcbnew.B_Cu: []}  # (net, x1, y1, x2, y2, r_cu)
        self.refresh_from_board()

    def refresh_from_board(self):
        self.pads.clear()
        self.vias.clear()
        self.segs[pcbnew.F_Cu].clear()
        self.segs[pcbnew.B_Cu].clear()

        for fp in self.board.GetFootprints():
            for p in fp.Pads():
                net = p.GetNetname()
                pos = p.GetPosition()
                cx, cy = pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)
                sz = p.GetSize()
                sx, sy = pcbnew.ToMM(sz.x), pcbnew.ToMM(sz.y)
                rot = p.GetOrientation().AsDegrees()
                if abs(rot % 180 - 90) < 10:
                    sx, sy = sy, sx
                lset = p.GetLayerSet()
                f_cu = lset.Contains(pcbnew.F_Cu)
                b_cu = lset.Contains(pcbnew.B_Cu)
                drill = pcbnew.ToMM(p.GetDrillSize().x)
                is_hole = drill > 0.0
                self.pads.append((net, f_cu, b_cu, is_hole, cx, cy, sx, sy, drill * 0.5))

        for t in self.board.GetTracks():
            net = t.GetNetname()
            if t.GetClass() == "PCB_VIA":
                pos = t.GetPosition()
                cx, cy = pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)
                r_cu = pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) * 0.5
                r_drill = pcbnew.ToMM(t.GetDrillValue()) * 0.5
                self.vias.append((net, cx, cy, r_cu, r_drill))
            else:
                ly = t.GetLayer()
                if ly in (pcbnew.F_Cu, pcbnew.B_Cu):
                    s, e = t.GetStart(), t.GetEnd()
                    x1, y1 = pcbnew.ToMM(s.x), pcbnew.ToMM(s.y)
                    x2, y2 = pcbnew.ToMM(e.x), pcbnew.ToMM(e.y)
                    r_cu = pcbnew.ToMM(t.GetWidth()) * 0.5
                    self.segs[ly].append((net, x1, y1, x2, y2, r_cu))

    def is_pt_valid(self, layer, net, x, y, tr_r=0.10, clr=0.175):
        # 1. Check pads on layer
        for p_net, f_cu, b_cu, is_hole, cx, cy, sx, sy, drill_r in self.pads:
            if p_net == net:
                continue
            on_layer = (f_cu if layer == pcbnew.F_Cu else b_cu) or is_hole
            if not on_layer:
                continue
            if abs(x - cx) > sx * 0.5 + tr_r + clr + 0.5 or abs(y - cy) > sy * 0.5 + tr_r + clr + 0.5:
                continue
            if dist_point_to_rect(x, y, cx, cy, sx, sy) < tr_r + clr:
                return False
        # 2. Check vias
        for v_net, cx, cy, r_cu, r_drill in self.vias:
            if v_net == net:
                continue
            if abs(x - cx) > r_cu + tr_r + clr + 0.2 or abs(y - cy) > r_cu + tr_r + clr + 0.2:
                continue
            if math.hypot(x - cx, y - cy) < r_cu + tr_r + clr:
                return False
        # 3. Check segments on layer
        for s_net, x1, y1, x2, y2, r_cu in self.segs[layer]:
            if s_net == net:
                continue
            if x < min(x1, x2) - (r_cu + tr_r + clr) or x > max(x1, x2) + (r_cu + tr_r + clr):
                continue
            if y < min(y1, y2) - (r_cu + tr_r + clr) or y > max(y1, y2) + (r_cu + tr_r + clr):
                continue
            if dist_point_to_seg(x, y, x1, y1, x2, y2) < r_cu + tr_r + clr:
                return False
        return True

    def is_via_valid(self, net, x, y, v_cu_r=0.30, v_drill_r=0.15, clr=0.175, hole_clr=0.27):
        # Must be valid on both F.Cu and B.Cu with radius v_cu_r
        if not self.is_pt_valid(pcbnew.F_Cu, net, x, y, tr_r=v_cu_r, clr=clr):
            return False
        if not self.is_pt_valid(pcbnew.B_Cu, net, x, y, tr_r=v_cu_r, clr=clr):
            return False
        #Also enforce hole-to-pad and hole-to-hole clearance regardless of net!
        for p_net, f_cu, b_cu, is_hole, cx, cy, sx, sy, drill_r in self.pads:
            if is_hole:
                if math.hypot(x - cx, y - cy) < v_drill_r + drill_r + hole_clr:
                    return False
            if p_net != net:
                # KiCad hole_clearance: via drill edge to different-net pad copper edge >= 0.25mm
                if dist_point_to_rect(x, y, cx, cy, sx, sy) < v_drill_r + hole_clr:
                    return False
        for v_net, cx, cy, r_cu, r_drill in self.vias:
            # Same-net or different-net via drill spacing!
            if math.hypot(x - cx, y - cy) < v_drill_r + r_drill + hole_clr:
                return False
            if v_net != net and math.hypot(x - cx, y - cy) < v_drill_r + r_cu + hole_clr:
                return False
        for ly in (pcbnew.F_Cu, pcbnew.B_Cu):
            for s_net, x1, y1, x2, y2, r_cu in self.segs[ly]:
                if s_net != net:
                    if dist_point_to_seg(x, y, x1, y1, x2, y2) < v_drill_r + r_cu + hole_clr:
                        return False
        return True

    def route(self, net, x_start, y_start, l_start, x_end, y_end, l_end, bbox, step=0.10, width_mm=0.20):
        xmin, ymin, xmax, ymax = bbox
        nx = int(round((xmax - xmin) / step)) + 1
        ny = int(round((ymax - ymin) / step)) + 1
        tr_r = width_mm * 0.5

        def to_idx(x, y):
            return int(round((x - xmin) / step)), int(round((y - ymin) / step))

        def to_xy(ix, iy):
            return round(xmin + ix * step, 4), round(ymin + iy * step, 4)

        sx, sy = to_idx(x_start, y_start)
        ex, ey = to_idx(x_end, y_end)
        if not (0 <= sx < nx and 0 <= sy < ny and 0 <= ex < nx and 0 <= ey < ny):
            raise ValueError(f"Endpoints out of bbox for {net}")

        layers = [pcbnew.F_Cu, pcbnew.B_Cu]
        sl_idx = 0 if l_start == pcbnew.F_Cu else 1
        el_idx = 0 if l_end == pcbnew.F_Cu else 1

        # Precompute validity cache lazily
        valid_cache = {}
        via_cache = {}

        def check_node(l_idx, ix, iy):
            if (ix, iy) in ((sx, sy), (ex, ey)):
                # Still enforce other-net clearance even at endpoints!
                pass
            key = (l_idx, ix, iy)
            if key not in valid_cache:
                x, y = to_xy(ix, iy)
                valid_cache[key] = self.is_pt_valid(layers[l_idx], net, x, y, tr_r=tr_r, clr=0.175)
            return valid_cache[key]

        def check_via(ix, iy):
            if (ix, iy) not in via_cache:
                x, y = to_xy(ix, iy)
                via_cache[(ix, iy)] = self.is_via_valid(net, x, y)
            return via_cache[(ix, iy)]

        # 8-direction neighbors
        dirs = [
            (1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
            (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)
        ]

        start_state = (sl_idx, sx, sy)
        goal_state = (el_idx, ex, ey)

        g_score = {start_state: 0.0}
        came_from = {}
        pq = [(math.hypot(ex - sx, ey - sy), 0.0, start_state, 0)]

        while pq:
            f, g, cur, last_dir = heapq.heappop(pq)
            if cur == goal_state:
                # Reconstruct path
                path = [cur]
                while cur in came_from:
                    cur = came_from[cur]
                    path.append(cur)
                path.reverse()
                self._commit_path(net, x_start, y_start, x_end, y_end, path, to_xy, layers, width_mm)
                self.refresh_from_board()
                return True

            if g > g_score.get(cur, 1e18):
                continue

            cl, cx, cy = cur

            # 1. Same-layer step
            for d_idx, (dx, dy, cost) in enumerate(dirs, 1):
                nx_, ny_ = cx + dx, cy + dy
                if not (0 <= nx_ < nx and 0 <= ny_ < ny):
                    continue
                if not check_node(cl, nx_, ny_):
                    continue
                # For diagonal step, also check midpoint & cardinal corners to prevent corner-cutting
                if dx != 0 and dy != 0:
                    mx, my = round(xmin + (cx + 0.5 * dx) * step, 4), round(ymin + (cy + 0.5 * dy) * step, 4)
                    if not self.is_pt_valid(layers[cl], net, mx, my, tr_r=tr_r, clr=0.175):
                        continue
                bend_penalty = 0.15 if (last_dir != 0 and last_dir != d_idx) else 0.0
                ng = g + cost + bend_penalty
                nxt = (cl, nx_, ny_)
                if ng < g_score.get(nxt, 1e18):
                    g_score[nxt] = ng
                    came_from[nxt] = cur
                    h = math.hypot(ex - nx_, ey - ny_) + (8.0 if cl != el_idx else 0.0)
                    heapq.heappush(pq, (ng + h, ng, nxt, d_idx))

            # 2. Via transition
            other_l = 1 - cl
            if check_via(cx, cy):
                ng = g + 18.0
                nxt = (other_l, cx, cy)
                if ng < g_score.get(nxt, 1e18):
                    g_score[nxt] = ng
                    came_from[nxt] = cur
                    h = math.hypot(ex - cx, ey - cy) + (8.0 if other_l != el_idx else 0.0)
                    heapq.heappush(pq, (ng + h, ng, nxt, 0))

        return False

    def _commit_path(self, net, x_start, y_start, x_end, y_end, path, to_xy, layers, width_mm):
        nc = self.board.GetNetsByName()[net].GetNetCode()
        # Simplify collinear segments per layer
        i = 0
        n = len(path)
        while i < n:
            cl = path[i][0]
            j = i
            pts = []
            while j < n and path[j][0] == cl:
                ix, iy = path[j][1], path[j][2]
                x, y = to_xy(ix, iy)
                if j == 0:
                    x, y = x_start, y_start
                if j == n - 1:
                    x, y = x_end, y_end
                pts.append((x, y))
                j += 1
            # Simplify collinear points in pts
            simp = [pts[0]]
            for k in range(1, len(pts) - 1):
                dx1 = pts[k][0] - simp[-1][0]
                dy1 = pts[k][1] - simp[-1][1]
                dx2 = pts[k+1][0] - pts[k][0]
                dy2 = pts[k+1][1] - pts[k][1]
                if abs(dx1 * dy2 - dy1 * dx2) > 1e-5:
                    simp.append(pts[k])
            if len(pts) > 1:
                simp.append(pts[-1])
            add_chain(self.board, nc, layers[cl], simp, width_mm=width_mm)
            if j < n:
                # Add via at transition point
                vx, vy = to_xy(path[j][1], path[j][2])
                add_via(self.board, nc, vx, vy)
            i = j

print("Defined ExactGeometryRouter.")

def run_test():
    shutil.copyfile(BASE_PCB, OUT_PCB)
    board = pcbnew.LoadBoard(OUT_PCB)
    nets = board.GetNetsByName()
    def net_code(name):
        return nets[name].GetNetCode()

    to_remove = []
    # 1. Copper conflicts & 2. Overlapping vias & 4. Dangling stubs
    for t in list(board.GetTracks()):
        # (a) M1_MAX_IN conflict stub & via
        if match_seg(t, pcbnew.F_Cu, "/Industrial_IO/M1_MAX_IN", 68.14, 114.22, 65.80, 114.22):
            to_remove.append(t)
        elif match_via(t, "/Industrial_IO/M1_MAX_IN", 65.80, 114.22):
            to_remove.append(t)
        # (b) ENC2_B B.Cu crossing & vias
        elif t.GetNetname() == "/MCU_and_Encoders/ENC2_B":
            if t.GetClass() == "PCB_VIA" and (near_pt(t.GetPosition(), 97.30, 75.90) or near_pt(t.GetPosition(), 97.70, 71.30)):
                to_remove.append(t)
            elif t.GetClass() != "PCB_VIA" and t.GetLayer() == pcbnew.B_Cu:
                to_remove.append(t)
            elif match_seg(t, pcbnew.F_Cu, "/MCU_and_Encoders/ENC2_B", 97.70, 71.30, 97.70, 72.30):
                to_remove.append(t)
            elif match_seg(t, pcbnew.F_Cu, "/MCU_and_Encoders/ENC2_B", 97.70, 72.30, 97.825, 72.50):
                to_remove.append(t)
        # Overlapping vias
        elif match_via(t, "/MCU_and_Encoders/ESP_BOOT", 74.50, 68.70):
            to_remove.append(t)
        elif match_seg(t, pcbnew.B_Cu, "/MCU_and_Encoders/ESP_BOOT", 73.30, 67.50, 74.50, 68.70):
            to_remove.append(t)
        elif match_via(t, "/Industrial_IO/M2_MIN_IN", 66.90, 114.88):
            to_remove.append(t)
        elif match_seg(t, pcbnew.F_Cu, "/Industrial_IO/M2_MIN_IN", 68.14, 114.88, 66.90, 114.88):
            to_remove.append(t)
        elif match_via(t, "/Industrial_IO/S2_MAX_IN", 65.80, 118.12):
            to_remove.append(t)
        elif match_seg(t, pcbnew.F_Cu, "/Industrial_IO/S2_MAX_IN", 68.14, 118.12, 65.80, 118.12):
            to_remove.append(t)
        # Old stubs on the 3 unrouted expander inputs
        elif match_via(t, "/Industrial_IO/M2_MAX_IN", 65.80, 115.53):
            to_remove.append(t)
        elif match_seg(t, pcbnew.F_Cu, "/Industrial_IO/M2_MAX_IN", 68.14, 115.53, 65.80, 115.53):
            to_remove.append(t)
        elif match_seg(t, pcbnew.F_Cu, "/Industrial_IO/M2_MAX_IN", 76.20, 122.40, 76.20, 124.30):
            to_remove.append(t)
        elif match_via(t, "/Industrial_IO/S1_MIN_IN", 66.90, 116.17):
            to_remove.append(t)
        elif match_seg(t, pcbnew.F_Cu, "/Industrial_IO/S1_MIN_IN", 68.14, 116.17, 66.90, 116.17):
            to_remove.append(t)
        elif match_seg(t, pcbnew.F_Cu, "/Industrial_IO/S1_MIN_IN", 79.80, 122.40, 79.80, 124.30):
            to_remove.append(t)
        elif match_via(t, "/Industrial_IO/S1_MAX_IN", 65.80, 116.83):
            to_remove.append(t)
        elif match_seg(t, pcbnew.F_Cu, "/Industrial_IO/S1_MAX_IN", 68.14, 116.83, 65.80, 116.83):
            to_remove.append(t)
        elif match_seg(t, pcbnew.F_Cu, "/Industrial_IO/S1_MAX_IN", 83.40, 122.40, 83.40, 124.30):
            to_remove.append(t)
        # Dangling vias/stubs
        elif match_via(t, "/MCU_and_Encoders/BTN_BACK", 104.17, 73.95):
            to_remove.append(t)
        elif match_seg(t, pcbnew.F_Cu, "/MCU_and_Encoders/BTN_BACK", 104.17, 72.50, 104.17, 73.95):
            to_remove.append(t)
        elif match_via(t, "/Industrial_IO/M1_MIN_IN", 66.90, 113.58):
            to_remove.append(t)
        elif match_seg(t, pcbnew.F_Cu, "/Industrial_IO/M1_MIN_IN", 68.14, 113.58, 66.90, 113.58):
            to_remove.append(t)
        elif match_via(t, "/Industrial_IO/S2_MIN_IN", 66.90, 117.47):
            to_remove.append(t)
        elif match_seg(t, pcbnew.F_Cu, "/Industrial_IO/S2_MIN_IN", 68.14, 117.47, 66.90, 117.47):
            to_remove.append(t)
        elif match_seg(t, pcbnew.F_Cu, "GND", 66.775, 57.20, 67.45, 57.20):
            to_remove.append(t)
        elif match_via(t, "GND", 67.45, 57.20):
            to_remove.append(t)
        elif match_seg(t, pcbnew.F_Cu, "GND", 77.775, 57.20, 78.45, 57.20):
            to_remove.append(t)
        elif match_via(t, "GND", 78.45, 57.20):
            to_remove.append(t)
        elif match_seg(t, pcbnew.F_Cu, "+3V3", 109.675, 97.50, 110.30, 97.50):
            to_remove.append(t)
        elif match_via(t, "+3V3", 110.30, 97.50):
            to_remove.append(t)

    removed_ids = set()
    for t in to_remove:
        if id(t) not in removed_ids:
            removed_ids.add(id(t))
            board.Remove(t)

    # Local fixes for ENC2_B and ESP_BOOT
    add_chain(board, net_code("/MCU_and_Encoders/ENC2_B"), pcbnew.F_Cu, [
        (97.30, 75.90),
        (97.30, 73.025),
        (97.825, 72.50),
    ], width_mm=0.20)
    add_seg(board, net_code("/MCU_and_Encoders/ESP_BOOT"), pcbnew.B_Cu, 73.30, 67.50, 74.70, 68.70, width_mm=0.22)

    # Exact pad center ties for R601-R609, R612-C605, R613-C606, R614-C607, C214
    add_chain(board, net_code("/Industrial_IO/M1_MIN_RAW"), pcbnew.F_Cu, [
        (67.02, 120.50), (67.025, 120.50), (67.025, 122.40)
    ], width_mm=0.22)
    add_chain(board, net_code("/Industrial_IO/M2_MAX_IN"), pcbnew.F_Cu, [
        (76.175, 122.40), (76.225, 122.45), (76.225, 124.30)
    ], width_mm=0.25)
    add_chain(board, net_code("/Industrial_IO/S1_MIN_IN"), pcbnew.F_Cu, [
        (79.775, 122.40), (79.825, 122.45), (79.825, 124.30)
    ], width_mm=0.25)
    add_chain(board, net_code("/Industrial_IO/S1_MAX_IN"), pcbnew.F_Cu, [
        (83.375, 122.40), (83.425, 122.45), (83.425, 124.30)
    ], width_mm=0.25)
    add_chain(board, net_code("/MCU_and_Encoders/BTN_HOME"), pcbnew.F_Cu, [
        (72.50, 68.775), (72.50, 68.78)
    ], width_mm=0.25)

    router = ExactGeometryRouter(board)

    tasks = [
        ("/Industrial_IO/M1_MIN_RAW", 67.00, 122.40, pcbnew.F_Cu, 67.00, 129.00, pcbnew.B_Cu, (63.5, 118.0, 74.0, 131.0)),
        ("/Industrial_IO/M2_MAX_IN",  68.10, 115.50, pcbnew.F_Cu, 76.20, 122.40, pcbnew.F_Cu, (63.5, 111.0, 88.0, 128.0)),
        ("/Industrial_IO/S1_MIN_IN",  68.10, 116.20, pcbnew.F_Cu, 79.80, 122.40, pcbnew.F_Cu, (63.5, 111.0, 88.0, 128.0)),
        ("/Industrial_IO/S1_MAX_IN",  68.10, 116.80, pcbnew.F_Cu, 83.40, 122.40, pcbnew.F_Cu, (63.5, 111.0, 88.0, 128.0)),
        ("/MCU_and_Encoders/BTN_HOME", 69.70, 62.90, pcbnew.B_Cu, 111.20, 63.60, pcbnew.B_Cu, (66.0, 52.0, 114.0, 76.0)),
    ]

    # Exact tiny endpoint snaps to the 0.1mm grid
    add_seg(board, net_code("/Industrial_IO/M1_MIN_RAW"), pcbnew.F_Cu, 67.025, 122.40, 67.00, 122.40, 0.20)
    add_seg(board, net_code("/Industrial_IO/M2_MAX_IN"),  pcbnew.F_Cu, 68.138, 115.525, 68.10, 115.50, 0.20)
    add_seg(board, net_code("/Industrial_IO/M2_MAX_IN"),  pcbnew.F_Cu, 76.175, 122.40, 76.20, 122.40, 0.20)
    add_seg(board, net_code("/Industrial_IO/S1_MIN_IN"),  pcbnew.F_Cu, 68.138, 116.175, 68.10, 116.20, 0.20)
    add_seg(board, net_code("/Industrial_IO/S1_MIN_IN"),  pcbnew.F_Cu, 79.775, 122.40, 79.80, 122.40, 0.20)
    add_seg(board, net_code("/Industrial_IO/S1_MAX_IN"),  pcbnew.F_Cu, 68.138, 116.825, 68.10, 116.80, 0.20)
    add_seg(board, net_code("/Industrial_IO/S1_MAX_IN"),  pcbnew.F_Cu, 83.375, 122.40, 83.40, 122.40, 0.20)
    add_seg(board, net_code("/MCU_and_Encoders/BTN_HOME"), pcbnew.B_Cu, 111.20, 63.63, 111.20, 63.60, 0.20)
    router.refresh_from_board()

    for net, xs, ys, ls, xe, ye, le, bbox in tasks:
        ok = router.route(net, xs, ys, ls, xe, ye, le, bbox, step=0.10, width_mm=0.20)
        print(f"Route {net}: {'OK' if ok else 'FAILED'}")

    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(OUT_PCB, board)

if __name__ == "__main__":
    run_test()
