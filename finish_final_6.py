#!/usr/bin/env python3
"""
finish_final_6.py
Standalone surgical completion script for ABX-Motion V1.1:
1. Backs up abx-motion.kicad_pcb to /tmp/codex_aesthetic_base.kicad_pcb.
2. Removes leftover 2.34mm stubs/vias at X=65.8..68.14, Y=113..118 on U601 limit nets,
   orphan ENC2_B vias/stubs near (97.5, 73.1), dangling tracks/vias, and duplicate co-located same-net vias (<0.45mm apart).
3. Routes the 6 remaining unconnected links using a fast, bounded 0.20mm-grid A* router across F.Cu, B.Cu, and In2.Cu
   (high-cost micro-underpass only, keeping In1.Cu GND plane 100% free of signal tracks!),
   exiting U601 Pads 7, 8, 9 strictly horizontally at exact Y = pad_y before snapping to the 0.20mm grid,
   and saving abx-motion.kicad_pcb incrementally after each routed net!
4. Refills all copper zones, runs kicad-cli DRC with --schematic-parity, and verifies 0 DRC errors, 0 unconnected items, 0 parity issues.
5. Regenerates all manufacturing deliverables in production/ and renders/.
"""

import os
import sys
import math
import json
import heapq
import shutil
import subprocess
import pcbnew

PCB_PATH = "/home/daniel/Documents/kicad/abx-motion/abx-motion.kicad_pcb"
BACKUP_PATH = "/tmp/codex_aesthetic_base.kicad_pcb"


def dist_point_to_seg(px, py, x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def dist_seg_to_seg(ax1, ay1, ax2, ay2, bx1, by1, bx2, by2):
    def ccw(x1, y1, x2, y2, x3, y3):
        return (y3 - y1) * (x2 - x1) > (y2 - y1) * (x3 - x1)
    if (ccw(ax1, ay1, bx1, by1, bx2, by2) != ccw(ax2, ay2, bx1, by1, bx2, by2) and
            ccw(ax1, ay1, ax2, ay2, bx1, by1) != ccw(ax1, ay1, ax2, ay2, bx2, by2)):
        return 0.0
    return min(
        dist_point_to_seg(ax1, ay1, bx1, by1, bx2, by2),
        dist_point_to_seg(ax2, ay2, bx1, by1, bx2, by2),
        dist_point_to_seg(bx1, by1, ax1, ay1, ax2, ay2),
        dist_point_to_seg(bx2, by2, ax1, ay1, ax2, ay2),
    )


def dist_point_to_rect(px, py, rx1, ry1, rx2, ry2):
    dx = max(rx1 - px, 0.0, px - rx2)
    dy = max(ry1 - py, 0.0, py - ry2)
    return math.hypot(dx, dy)


def dist_seg_to_rect(x1, y1, x2, y2, rx1, ry1, rx2, ry2):
    if rx1 <= x1 <= rx2 and ry1 <= y1 <= ry2:
        return 0.0
    if rx1 <= x2 <= rx2 and ry1 <= y2 <= ry2:
        return 0.0
    return min(
        dist_point_to_rect(x1, y1, rx1, ry1, rx2, ry2),
        dist_point_to_rect(x2, y2, rx1, ry1, rx2, ry2),
        dist_seg_to_seg(x1, y1, x2, y2, rx1, ry1, rx2, ry1),
        dist_seg_to_seg(x1, y1, x2, y2, rx2, ry1, rx2, ry2),
        dist_seg_to_seg(x1, y1, x2, y2, rx2, ry2, rx1, ry2),
        dist_seg_to_seg(x1, y1, x2, y2, rx1, ry2, rx1, ry1),
    )


class FastBoundedRouter:
    """Fast 0.20mm-grid A* router across F.Cu (0), B.Cu (1), and In2.Cu (2 = high-cost micro-underpass only)."""

    def __init__(self, board):
        self.board = board
        self.f_cu = board.GetLayerID("F.Cu")
        self.b_cu = board.GetLayerID("B.Cu")
        self.in2_cu = board.GetLayerID("In2.Cu")
        self.layer_ids = {0: self.f_cu, 1: self.b_cu, 2: self.in2_cu}
        self.rebuild_obstacles()

    def rebuild_obstacles(self):
        self.pads = []      # (net, layer_mask, rx1, ry1, rx2, ry2, is_hole)
        self.segs = []      # (net, lid, x1, y1, x2, y2, half_w, bx1, by1, bx2, by2)
        self.vias = []      # (net, x, y, half_w)

        for fp in self.board.GetFootprints():
            for pad in fp.Pads():
                net = pad.GetNetname()
                bb = pad.GetBoundingBox()
                rx1 = pcbnew.ToMM(bb.GetLeft())
                ry1 = pcbnew.ToMM(bb.GetTop())
                rx2 = pcbnew.ToMM(bb.GetRight())
                ry2 = pcbnew.ToMM(bb.GetBottom())
                lset = pad.GetLayerSet()
                mask = 0
                if lset.Contains(self.f_cu):
                    mask |= 1
                if lset.Contains(self.b_cu):
                    mask |= 2
                if lset.Contains(self.in2_cu):
                    mask |= 4
                is_hole = pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
                if is_hole:
                    mask = 7
                self.pads.append((net, mask, rx1, ry1, rx2, ry2, is_hole))

        for t in self.board.GetTracks():
            net = t.GetNetname()
            if t.GetClass() == "PCB_VIA":
                p = t.GetPosition()
                x = pcbnew.ToMM(p.x)
                y = pcbnew.ToMM(p.y)
                hw = pcbnew.ToMM(t.GetWidth(self.f_cu)) * 0.5
                self.vias.append((net, x, y, hw))
            else:
                tl = t.GetLayer()
                lid = None
                for k, v in self.layer_ids.items():
                    if v == tl:
                        lid = k
                        break
                if lid is None:
                    continue
                s = t.GetStart()
                e = t.GetEnd()
                x1, y1 = pcbnew.ToMM(s.x), pcbnew.ToMM(s.y)
                x2, y2 = pcbnew.ToMM(e.x), pcbnew.ToMM(e.y)
                hw = pcbnew.ToMM(t.GetWidth()) * 0.5
                self.segs.append((
                    net, lid, x1, y1, x2, y2, hw,
                    min(x1, x2) - hw, min(y1, y2) - hw, max(x1, x2) + hw, max(y1, y2) + hw
                ))

    def seg_clear(self, net, lid, x1, y1, x2, y2, half_w=0.10, clr=0.165):
        bx1 = min(x1, x2) - half_w - clr - 0.5
        by1 = min(y1, y2) - half_w - clr - 0.5
        bx2 = max(x1, x2) + half_w + clr + 0.5
        by2 = max(y1, y2) + half_w + clr + 0.5
        bit = 1 << lid

        for p_net, mask, rx1, ry1, rx2, ry2, _ in self.pads:
            if p_net == net or not (mask & bit):
                continue
            if rx2 < bx1 or rx1 > bx2 or ry2 < by1 or ry1 > by2:
                continue
            if dist_seg_to_rect(x1, y1, x2, y2, rx1, ry1, rx2, ry2) < half_w + clr:
                return False

        for v_net, vx, vy, vhw in self.vias:
            if v_net == net:
                continue
            if vx < bx1 or vx > bx2 or vy < by1 or vy > by2:
                continue
            if dist_point_to_seg(vx, vy, x1, y1, x2, y2) < half_w + vhw + clr:
                return False

        for s_net, s_lid, sx1, sy1, sx2, sy2, shw, sbx1, sby1, sbx2, sby2 in self.segs:
            if s_net == net or s_lid != lid:
                continue
            if sbx2 < bx1 or sbx1 > bx2 or sby2 < by1 or sby1 > by2:
                continue
            if dist_seg_to_seg(x1, y1, x2, y2, sx1, sy1, sx2, sy2) < half_w + shw + clr:
                return False

        return True

    def via_clear(self, net, x, y, via_r=0.25, clr=0.165):
        bx1 = x - via_r - clr - 0.5
        by1 = y - via_r - clr - 0.5
        bx2 = x + via_r + clr + 0.5
        by2 = y + via_r + clr + 0.5

        for p_net, mask, rx1, ry1, rx2, ry2, is_hole in self.pads:
            if rx2 < bx1 or rx1 > bx2 or ry2 < by1 or ry1 > by2:
                continue
            d = dist_point_to_rect(x, y, rx1, ry1, rx2, ry2)
            if p_net == net:
                # Avoid placing via directly over SMD pad or too close to PTH hole
                if d < 0.15:
                    return False
            else:
                req = via_r + (0.25 if is_hole else clr)
                if d < req:
                    return False

        for v_net, vx, vy, vhw in self.vias:
            d = math.hypot(x - vx, y - vy)
            if v_net == net:
                if d < 0.50:
                    return False
            else:
                if d < max(via_r + vhw + clr, 0.50):
                    return False

        for s_net, s_lid, sx1, sy1, sx2, sy2, shw, sbx1, sby1, sbx2, sby2 in self.segs:
            if s_net == net:
                continue
            if sbx2 < bx1 or sbx1 > bx2 or sby2 < by1 or sby1 > by2:
                continue
            if dist_point_to_seg(x, y, sx1, sy1, sx2, sy2) < via_r + shw + clr:
                return False

        return True

    def add_seg(self, net, lid, x1, y1, x2, y2, width=0.20):
        if math.hypot(x2 - x1, y2 - y1) < 1e-4:
            return
        ni = self.board.GetNetInfo().GetNetItem(net)
        t = pcbnew.PCB_TRACK(self.board)
        t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(float(x1)), pcbnew.FromMM(float(y1))))
        t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(float(x2)), pcbnew.FromMM(float(y2))))
        t.SetWidth(pcbnew.FromMM(float(width)))
        t.SetLayer(self.layer_ids[lid])
        t.SetNet(ni)
        self.board.Add(t)
        hw = width * 0.5
        self.segs.append((
            net, lid, x1, y1, x2, y2, hw,
            min(x1, x2) - hw, min(y1, y2) - hw, max(x1, x2) + hw, max(y1, y2) + hw
        ))

    def add_via(self, net, x, y, size=0.50, drill=0.25):
        ni = self.board.GetNetInfo().GetNetItem(net)
        v = pcbnew.PCB_VIA(self.board)
        v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(float(x)), pcbnew.FromMM(float(y))))
        v.SetWidth(pcbnew.FromMM(float(size)))
        v.SetDrill(pcbnew.FromMM(float(drill)))
        v.SetLayerPair(self.f_cu, self.b_cu)
        v.SetNet(ni)
        self.board.Add(v)
        self.vias.append((net, x, y, size * 0.5))

    def route_astar(self, net, sx, sy, s_lid, gx, gy, g_lid,
                    bbox, allow_in2=True, pre_segs=None, post_segs=None, width=0.20):
        """
        Routes on a 0.20mm grid inside bbox = (xmin, ymin, xmax, ymax) from (sx, sy, s_lid) to (gx, gy, g_lid).
        """
        grid = 0.20
        sx_g = round(round(sx / grid) * grid, 3)
        sy_g = round(round(sy / grid) * grid, 3)
        gx_g = round(round(gx / grid) * grid, 3)
        gy_g = round(round(gy / grid) * grid, 3)

        xmin, ymin, xmax, ymax = bbox
        layers = [0, 1, 2] if allow_in2 else [0, 1]

        start_node = (sx_g, sy_g, s_lid)
        goal_node = (gx_g, gy_g, g_lid)

        open_heap = [(0.0, 0.0, start_node)]
        g_score = {start_node: 0.0}
        came_from = {}
        edge_cache = {}
        via_cache = {}

        dirs = [
            (grid, 0.0, 0.20), (-grid, 0.0, 0.20),
            (0.0, grid, 0.20), (0.0, -grid, 0.20),
            (grid, grid, 0.2828), (grid, -grid, 0.2828),
            (-grid, grid, 0.2828), (-grid, -grid, 0.2828),
        ]

        hw = width * 0.5
        steps = 0
        max_steps = 120000

        while open_heap and steps < max_steps:
            steps += 1
            _, cur_g, curr = heapq.heappop(open_heap)
            if cur_g > g_score.get(curr, 1e18):
                continue
            if curr == goal_node:
                break

            cx, cy, cl = curr

            # Planar steps
            for dx, dy, step_len in dirs:
                nx = round(cx + dx, 3)
                ny = round(cy + dy, 3)
                if nx < xmin or nx > xmax or ny < ymin or ny > ymax:
                    continue
                ekey = (cl, cx, cy, nx, ny) if (cx, cy) < (nx, ny) else (cl, nx, ny, cx, cy)
                ok = edge_cache.get(ekey)
                if ok is None:
                    ok = self.seg_clear(net, cl, cx, cy, nx, ny, half_w=hw)
                    edge_cache[ekey] = ok
                if not ok:
                    continue

                # High-cost penalty on In2.Cu so it is only used for short micro-underpasses
                layer_mult = 8.0 if cl == 2 else (1.15 if cl == 1 else 1.0)
                ng = cur_g + step_len * layer_mult
                nxt = (nx, ny, cl)
                if ng < g_score.get(nxt, 1e18):
                    g_score[nxt] = ng
                    h = math.hypot(gx_g - nx, gy_g - ny)
                    heapq.heappush(open_heap, (ng + h, ng, nxt))
                    came_from[nxt] = curr

            # Layer transitions via through-via
            vkey = (cx, cy)
            v_ok = via_cache.get(vkey)
            if v_ok is None:
                v_ok = self.via_clear(net, cx, cy)
                via_cache[vkey] = v_ok
            if v_ok:
                for nl in layers:
                    if nl == cl:
                        continue
                    via_cost = 6.0 if (nl == 2 or cl == 2) else 1.8
                    ng = cur_g + via_cost
                    nxt = (cx, cy, nl)
                    if ng < g_score.get(nxt, 1e18):
                        g_score[nxt] = ng
                        h = math.hypot(gx_g - cx, gy_g - cy)
                        heapq.heappush(open_heap, (ng + h, ng, nxt))
                        came_from[nxt] = curr

        if goal_node not in came_from and start_node != goal_node:
            print(f"  [!] A* failed for {net} after {steps} steps")
            return False

        # Reconstruct path
        path = [goal_node]
        curr = goal_node
        while curr != start_node:
            curr = came_from[curr]
            path.append(curr)
        path.reverse()

        # Commit pre_segs
        if pre_segs:
            for lid, x1, y1, x2, y2 in pre_segs:
                self.add_seg(net, lid, x1, y1, x2, y2, width=width)
        if math.hypot(sx - sx_g, sy - sy_g) > 1e-4:
            self.add_seg(net, s_lid, sx, sy, sx_g, sy_g, width=width)

        # Commit A* segments and vias (simplifying collinear segments)
        i = 0
        while i < len(path) - 1:
            x1, y1, l1 = path[i]
            x2, y2, l2 = path[i + 1]
            if l1 != l2:
                self.add_via(net, x1, y1)
                i += 1
            else:
                j = i + 1
                dx = round(x2 - x1, 3)
                dy = round(y2 - y1, 3)
                while j + 1 < len(path) and path[j + 1][2] == l1:
                    nx, ny, _ = path[j + 1]
                    px, py, _ = path[j]
                    if round(nx - px, 3) == dx and round(ny - py, 3) == dy:
                        j += 1
                    else:
                        break
                ex, ey, _ = path[j]
                self.add_seg(net, l1, x1, y1, ex, ey, width=width)
                i = j

        if math.hypot(gx - gx_g, gy - gy_g) > 1e-4:
            self.add_seg(net, g_lid, gx_g, gy_g, gx, gy, width=width)
        if post_segs:
            for lid, x1, y1, x2, y2 in post_segs:
                self.add_seg(net, lid, x1, y1, x2, y2, width=width)

        print(f"  [+] Routed {net} in {steps} steps ({len(path)} nodes)")
        return True


def main():
    print("[1/5] Backing up abx-motion.kicad_pcb to /tmp/codex_aesthetic_base.kicad_pcb...")
    if not os.path.exists(BACKUP_PATH):
        shutil.copy2(PCB_PATH, BACKUP_PATH)
    else:
        # Ensure we start cleanly from the backed up aesthetic base
        shutil.copy2(BACKUP_PATH, PCB_PATH)

    board = pcbnew.LoadBoard(PCB_PATH)

    print("[2/5] Removing leftover 2.34mm U601 stubs/vias, ENC2_B crossing stubs, dangling items, and duplicate vias...")
    to_remove = []

    # Collect vias to check for duplicate co-located same-net vias (<0.45mm)
    vias_by_net = {}
    for t in list(board.GetTracks()):
        nn = t.GetNetname()
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition()
            vx, vy = pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)

            # Remove orphan/leftover vias on U601 limit nets at X=65.8..68.14, Y=113..118.2
            # (except valid M2_MIN_IN via at (66.70, 114.90) and valid S2_MAX_IN via at (65.70, 118.30))
            if nn in ("/Industrial_IO/M1_MIN_IN", "/Industrial_IO/M1_MAX_IN",
                      "/Industrial_IO/M2_MIN_IN", "/Industrial_IO/M2_MAX_IN",
                      "/Industrial_IO/S1_MIN_IN", "/Industrial_IO/S1_MAX_IN",
                      "/Industrial_IO/S2_MIN_IN", "/Industrial_IO/S2_MAX_IN"):
                if (math.hypot(vx - 66.90, vy - 113.58) < 0.15 or
                        math.hypot(vx - 65.80, vy - 114.22) < 0.15 or
                        math.hypot(vx - 66.90, vy - 114.88) < 0.15 or
                        math.hypot(vx - 66.90, vy - 117.47) < 0.15 or
                        math.hypot(vx - 65.80, vy - 118.12) < 0.15):
                    to_remove.append(t)
                    continue

            # Remove dangling vias on ENC2_B near (97.3, 75.9) and (97.7, 71.3)
            if nn == "/MCU_and_Encoders/ENC2_B" and 96.0 <= vx <= 99.0 and 70.0 <= vy <= 77.0:
                to_remove.append(t)
                continue

            # Remove dangling via on BTN_BACK at (104.17, 73.95)
            if nn == "/MCU_and_Encoders/BTN_BACK" and math.hypot(vx - 104.17, vy - 73.95) < 0.3:
                to_remove.append(t)
                continue

            # Remove dangling via on +3V3 at (110.30, 97.50)
            if nn == "+3V3" and math.hypot(vx - 110.30, vy - 97.50) < 0.3:
                to_remove.append(t)
                continue

            # Remove dangling via on BTN_HOME at (111.20, 63.63) so we can route cleanly from (109.75, 63.63)
            if nn == "/MCU_and_Encoders/BTN_HOME" and math.hypot(vx - 111.20, vy - 63.63) < 0.3:
                to_remove.append(t)
                continue

            vias_by_net.setdefault(nn, []).append((vx, vy, t))
        else:
            s, e = t.GetStart(), t.GetEnd()
            sx, sy = pcbnew.ToMM(s.x), pcbnew.ToMM(s.y)
            ex, ey = pcbnew.ToMM(e.x), pcbnew.ToMM(e.y)
            lname = board.GetLayerName(t.GetLayer())

            # Remove leftover 2.34mm horizontal left-going stubs on U601 limit nets at X=65.8..68.14, Y=113..118.2
            if nn in ("/Industrial_IO/M1_MIN_IN", "/Industrial_IO/M1_MAX_IN",
                      "/Industrial_IO/M2_MIN_IN", "/Industrial_IO/M2_MAX_IN",
                      "/Industrial_IO/S1_MIN_IN", "/Industrial_IO/S1_MAX_IN",
                      "/Industrial_IO/S2_MIN_IN", "/Industrial_IO/S2_MAX_IN"):
                if (65.75 <= min(sx, ex) and max(sx, ex) <= 68.15 and
                        113.0 <= min(sy, ey) and max(sy, ey) <= 118.2 and
                        abs(sy - ey) < 0.05):
                    # Keep S2_MIN_IN valid segment (65.5, 117.5)->(67.9, 117.5)->(68.14, 117.47) and S2_MAX_IN valid segment (66.1, 118.1)->(67.9, 118.1)->(68.14, 118.12)
                    if (nn == "/Industrial_IO/S2_MIN_IN" and math.isclose(min(sx, ex), 66.90, abs_tol=0.05)) or \
                       (nn == "/Industrial_IO/S2_MAX_IN" and math.isclose(min(sx, ex), 65.80, abs_tol=0.05)) or \
                       (nn == "/Industrial_IO/M1_MIN_IN" and math.isclose(min(sx, ex), 66.90, abs_tol=0.05)) or \
                       (nn == "/Industrial_IO/M1_MAX_IN" and math.isclose(min(sx, ex), 65.80, abs_tol=0.05)) or \
                       (nn == "/Industrial_IO/M2_MIN_IN" and math.isclose(min(sx, ex), 66.90, abs_tol=0.05)):
                        to_remove.append(t)
                        continue

            # Remove ENC2_B stub (97.7, 71.3) -> (97.7, 72.3) and any B.Cu crossing near (97.5, 73.1)
            if nn == "/MCU_and_Encoders/ENC2_B":
                if lname == "B.Cu" and 96.0 <= min(sx, ex) <= 99.0 and 70.0 <= min(sy, ey) <= 77.0:
                    to_remove.append(t)
                    continue
                if lname == "F.Cu" and math.hypot(sx - 97.7, sy - 71.3) < 0.2 and math.hypot(ex - 97.7, ey - 72.3) < 0.2:
                    to_remove.append(t)
                    continue

            # Remove BTN_BACK dangling stub (104.17, 72.50) -> (104.17, 73.95)
            if nn == "/MCU_and_Encoders/BTN_BACK" and math.hypot(sx - 104.17, sy - 72.50) < 0.3 and math.hypot(ex - 104.17, ey - 73.95) < 0.3:
                to_remove.append(t)
                continue

            # Remove BTN_HOME stub to dangling via (109.75, 63.63) -> (111.20, 63.63)
            if nn == "/MCU_and_Encoders/BTN_HOME" and math.hypot(sx - 109.75, sy - 63.63) < 0.2 and math.hypot(ex - 111.20, ey - 63.63) < 0.2:
                to_remove.append(t)
                continue

            # Remove dangling GND and +3V3 F.Cu stubs
            if nn == "GND" and lname == "F.Cu" and math.isclose(t.GetLength() / 1e6, 0.675, abs_tol=0.02):
                if (65.0 <= sx <= 79.0 and 56.0 <= sy <= 58.0):
                    to_remove.append(t)
                    continue
            if nn == "+3V3" and lname == "F.Cu" and math.isclose(t.GetLength() / 1e6, 0.625, abs_tol=0.02):
                if (108.0 <= sx <= 111.0 and 96.0 <= sy <= 99.0):
                    to_remove.append(t)
                    continue

    # Check duplicate co-located same-net vias (<0.45mm apart)
    for nn, vlist in vias_by_net.items():
        kept = []
        for vx, vy, vt in vlist:
            if any(math.hypot(vx - kx, vy - ky) < 0.45 for kx, ky, _ in kept):
                to_remove.append(vt)
            else:
                kept.append((vx, vy, vt))

    for item in to_remove:
        board.RemoveNative(item)
    print(f"  Removed {len(to_remove)} leftover/dangling stubs and duplicate vias.")

    print("[3/5] Routing the 6 remaining unconnected links incrementally...")
    router = FastBoundedRouter(board)
    # Restore M2_MIN_IN via at exact (66.70, 114.90) where F.Cu (66.70, 114.90) meets B.Cu (66.70, 114.90)
    router.add_via("/Industrial_IO/M2_MIN_IN", 66.70, 114.90)
    pcbnew.SaveBoard(PCB_PATH, board)

    def commit_verified_or_astar(net, sx, sy, s_lid, gx, gy, g_lid, bbox, allow_in2, pre_segs, post_segs, verified_nodes):
        # Verify every segment and via of verified_nodes against current obstacles; if clear, commit directly in O(1), else run A*
        ok = True
        for i in range(len(verified_nodes) - 1):
            x1, y1, l1 = verified_nodes[i]
            x2, y2, l2 = verified_nodes[i + 1]
            if l1 != l2:
                if not router.via_clear(net, x1, y1):
                    ok = False
                    break
            else:
                if not router.seg_clear(net, l1, x1, y1, x2, y2):
                    ok = False
                    break
        if ok:
            if pre_segs:
                for lid, x1, y1, x2, y2 in pre_segs:
                    router.add_seg(net, lid, x1, y1, x2, y2)
            for i in range(len(verified_nodes) - 1):
                x1, y1, l1 = verified_nodes[i]
                x2, y2, l2 = verified_nodes[i + 1]
                if l1 != l2:
                    router.add_via(net, x1, y1)
                else:
                    router.add_seg(net, l1, x1, y1, x2, y2)
            if post_segs:
                for lid, x1, y1, x2, y2 in post_segs:
                    router.add_seg(net, lid, x1, y1, x2, y2)
            print(f"  [+] Routed {net} (verified 0.20mm-grid A* path, {len(verified_nodes)} waypoints)")
            return True
        return router.route_astar(net, sx, sy, s_lid, gx, gy, g_lid, bbox=bbox, allow_in2=allow_in2, pre_segs=pre_segs, post_segs=post_segs)

    # 1. /MCU_and_Encoders/ENC2_B: (97.30, 75.90) -> (97.70, 72.30) on F.Cu
    print(" -> Routing 1/6: /MCU_and_Encoders/ENC2_B...")
    ok1 = commit_verified_or_astar(
        "/MCU_and_Encoders/ENC2_B",
        97.30, 75.90, 0,
        97.70, 72.30, 0,
        bbox=(95.0, 71.0, 99.0, 77.0),
        allow_in2=False,
        pre_segs=[(0, 97.30, 75.90, 97.20, 76.00)],
        post_segs=[(0, 97.60, 72.20, 97.70, 72.30)],
        verified_nodes=[
            (97.20, 76.00, 0), (97.20, 73.60, 0), (97.40, 73.40, 0),
            (97.40, 72.60, 0), (97.60, 72.40, 0), (97.60, 72.20, 0),
        ]
    )
    assert ok1, "Failed to route ENC2_B"
    pcbnew.SaveBoard(PCB_PATH, board)

    # 2. /Industrial_IO/M1_MIN_RAW: Track (67.02, 120.50) -> J601 Pad 1 (67.00, 129.00)
    print(" -> Routing 2/6: /Industrial_IO/M1_MIN_RAW...")
    ok2 = commit_verified_or_astar(
        "/Industrial_IO/M1_MIN_RAW",
        67.02, 120.50, 0,
        67.00, 129.00, 0,
        bbox=(63.0, 119.0, 72.0, 130.5),
        allow_in2=True,
        pre_segs=[(0, 67.02, 120.50, 67.00, 120.40)],
        post_segs=None,
        verified_nodes=[
            (67.00, 120.40, 0), (67.00, 121.40, 0), (66.80, 121.60, 0),
            (66.80, 121.60, 2), (66.80, 121.80, 2), (65.60, 123.00, 2),
            (65.20, 123.00, 2), (64.80, 123.40, 2), (64.80, 123.40, 1),
            (64.80, 125.00, 1), (65.00, 125.20, 1), (65.00, 125.40, 1),
            (65.20, 125.60, 1), (65.20, 125.80, 1), (67.00, 127.60, 1),
            (67.00, 127.60, 0), (67.00, 129.00, 0),
        ]
    )
    assert ok2, "Failed to route M1_MIN_RAW"
    pcbnew.SaveBoard(PCB_PATH, board)

    # 3. /Industrial_IO/M2_MAX_IN: U601 Pad 7 (68.1375, 115.525) left at exact Y=pad_y to X=66.8 -> R612 Pad 2 (76.175, 122.40)
    print(" -> Routing 3/6: /Industrial_IO/M2_MAX_IN...")
    ok3 = commit_verified_or_astar(
        "/Industrial_IO/M2_MAX_IN",
        66.80, 115.60, 0,
        76.20, 122.40, 0,
        bbox=(62.0, 111.0, 80.0, 126.0),
        allow_in2=True,
        pre_segs=[
            (0, 68.1375, 115.525, 66.80, 115.525),
            (0, 66.80, 115.525, 66.80, 115.60),
        ],
        post_segs=[
            (0, 76.20, 122.40, 76.175, 122.40),
        ],
        verified_nodes=[
            (66.80, 115.60, 0), (66.60, 115.60, 0), (66.00, 115.00, 0),
            (66.00, 114.80, 0), (66.60, 114.20, 0), (66.80, 114.20, 0),
            (66.80, 114.20, 1), (71.20, 118.60, 1), (71.20, 119.60, 1),
            (71.20, 119.60, 2), (71.80, 119.60, 2), (72.40, 120.20, 2),
            (73.40, 120.20, 2), (73.40, 120.20, 0), (73.40, 120.00, 0),
            (73.80, 119.60, 0), (74.60, 119.60, 0), (75.20, 120.20, 0),
            (75.20, 120.40, 0), (75.40, 120.60, 0), (75.40, 121.00, 0),
            (75.80, 121.40, 0), (75.80, 121.60, 0), (76.00, 121.80, 0),
            (76.00, 122.00, 0), (76.20, 122.20, 0), (76.20, 122.40, 0),
        ]
    )
    assert ok3, "Failed to route M2_MAX_IN"
    pcbnew.SaveBoard(PCB_PATH, board)

    # 4. /Industrial_IO/S1_MIN_IN: U601 Pad 8 (68.1375, 116.175) inward right under U601 at exact Y=pad_y to X=69.20 -> R613 Pad 2 (79.775, 122.40)
    print(" -> Routing 4/6: /Industrial_IO/S1_MIN_IN...")
    ok4 = commit_verified_or_astar(
        "/Industrial_IO/S1_MIN_IN",
        69.20, 116.20, 0,
        79.80, 122.40, 0,
        bbox=(63.0, 111.0, 84.0, 126.0),
        allow_in2=True,
        pre_segs=[
            (0, 68.1375, 116.175, 69.20, 116.175),
            (0, 69.20, 116.175, 69.20, 116.20),
        ],
        post_segs=[
            (0, 79.80, 122.40, 79.775, 122.40),
        ],
        verified_nodes=[
            (69.20, 116.20, 0), (67.20, 116.20, 0), (67.20, 116.20, 1),
            (66.00, 115.00, 1), (66.00, 114.80, 1), (66.20, 114.60, 1),
            (66.20, 114.00, 1), (66.60, 113.60, 1), (67.00, 113.60, 1),
            (68.60, 115.20, 1), (72.60, 115.20, 1), (73.00, 115.60, 1),
            (75.20, 115.60, 1), (75.20, 115.60, 2), (75.20, 118.60, 2),
            (75.20, 118.60, 0), (75.40, 118.80, 0), (76.20, 118.80, 0),
            (76.40, 119.00, 0), (76.60, 119.00, 0), (77.20, 119.60, 0),
            (78.20, 119.60, 0), (78.80, 120.20, 0), (78.80, 120.40, 0),
            (79.00, 120.60, 0), (79.00, 121.00, 0), (79.40, 121.40, 0),
            (79.40, 121.60, 0), (79.60, 121.80, 0), (79.60, 122.00, 0),
            (79.80, 122.20, 0), (79.80, 122.40, 0),
        ]
    )
    assert ok4, "Failed to route S1_MIN_IN"
    pcbnew.SaveBoard(PCB_PATH, board)

    # 5. /Industrial_IO/S1_MAX_IN: U601 Pad 9 (68.1375, 116.825) left at exact Y=pad_y to X=66.8 -> R614 Pad 2 (83.375, 122.40)
    print(" -> Routing 5/6: /Industrial_IO/S1_MAX_IN...")
    ok5 = commit_verified_or_astar(
        "/Industrial_IO/S1_MAX_IN",
        66.80, 116.80, 0,
        83.40, 122.40, 0,
        bbox=(61.0, 111.0, 87.0, 126.5),
        allow_in2=True,
        pre_segs=[
            (0, 68.1375, 116.825, 66.80, 116.825),
            (0, 66.80, 116.825, 66.80, 116.80),
        ],
        post_segs=[
            (0, 83.40, 122.40, 83.375, 122.40),
        ],
        verified_nodes=[
            (66.80, 116.80, 0), (66.80, 116.80, 1), (67.00, 117.00, 1),
            (67.00, 118.80, 1), (68.80, 120.60, 1), (68.80, 121.40, 1),
            (68.80, 121.40, 2), (70.60, 121.40, 2), (70.80, 121.20, 2),
            (71.20, 121.20, 2), (71.60, 120.80, 2), (72.60, 120.80, 2),
            (73.20, 121.40, 2), (73.20, 121.40, 1), (82.00, 121.40, 1),
            (82.00, 121.40, 0), (82.80, 122.20, 0), (83.00, 122.20, 0),
            (83.20, 122.40, 0), (83.40, 122.40, 0),
        ]
    )
    assert ok5, "Failed to route S1_MAX_IN"
    pcbnew.SaveBoard(PCB_PATH, board)

    # 6. /MCU_and_Encoders/BTN_HOME: C214 Pad 1 (72.50, 68.775) -> Track (109.75, 63.63)
    print(" -> Routing 6/6: /MCU_and_Encoders/BTN_HOME...")
    ok6 = commit_verified_or_astar(
        "/MCU_and_Encoders/BTN_HOME",
        72.60, 68.80, 0,
        109.80, 63.60, 0,
        bbox=(68.0, 49.0, 114.0, 73.0),
        allow_in2=True,
        pre_segs=[
            (0, 72.50, 68.775, 72.60, 68.80),
        ],
        post_segs=[
            (0, 109.80, 63.60, 109.75, 63.63),
        ],
        verified_nodes=[
            (72.60, 68.80, 0), (73.40, 68.00, 0), (73.40, 67.00, 0),
            (73.80, 66.60, 0), (73.80, 65.80, 0), (74.40, 65.20, 0),
            (77.20, 65.20, 0), (77.80, 64.60, 0), (78.00, 64.60, 0),
            (78.00, 64.60, 1), (78.20, 64.60, 1), (78.80, 64.00, 1),
            (79.80, 64.00, 1), (80.00, 63.80, 1), (82.20, 63.80, 1),
            (82.60, 63.40, 1), (86.60, 63.40, 1), (86.80, 63.20, 1),
            (88.60, 63.20, 1), (88.80, 63.00, 1), (89.60, 63.00, 1),
            (91.00, 61.60, 1), (91.00, 61.60, 2), (93.40, 61.60, 2),
            (93.60, 61.80, 2), (93.60, 61.80, 0), (94.60, 61.80, 0),
            (96.80, 64.00, 0), (96.80, 64.20, 0), (97.40, 64.80, 0),
            (107.20, 64.80, 0), (107.40, 64.60, 0), (107.80, 64.60, 0),
            (108.00, 64.40, 0), (108.20, 64.40, 0), (108.40, 64.20, 0),
            (108.60, 64.20, 0), (108.80, 64.00, 0), (109.00, 64.00, 0),
            (109.20, 63.80, 0), (109.40, 63.80, 0), (109.60, 63.60, 0),
            (109.80, 63.60, 0),
        ]
    )
    assert ok6, "Failed to route BTN_HOME"
    pcbnew.SaveBoard(PCB_PATH, board)

    print("[4/5] Refilling all copper zones and running kicad-cli DRC...")
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(PCB_PATH, board)

    subprocess.run([
        "/usr/bin/kicad-cli", "pcb", "drc",
        "--schematic-parity", "--format", "json",
        "--output", "drc.json", PCB_PATH
    ], check=True)

    drc = json.load(open("drc.json"))
    violations = drc.get("violations", [])
    errors = [v for v in violations if v.get("severity") == "error"]
    warnings = [v for v in violations if v.get("severity") == "warning"]
    unconnected = drc.get("unconnected_items", [])
    parity = drc.get("schematic_parity", [])

    print(f"DRC Summary: Errors={len(errors)} | Unconnected={len(unconnected)} | Parity={len(parity)} | Warnings={len(warnings)}")
    for e in errors:
        print("  ERROR:", e["type"], e["description"], [i["description"] for i in e.get("items", [])])
    for u in unconnected:
        print("  UNCONN:", u["description"], [i["description"] for i in u.get("items", [])])
    for w in warnings:
        if w["type"] not in ("lib_footprint_mismatch", "silk_edge_clearance"):
            print("  WARN:", w["type"], w["description"], [i["description"] for i in w.get("items", [])])

    assert len(errors) == 0 and len(unconnected) == 0 and len(parity) == 0, "DRC / Unconnected / Parity not zero!"

    print("[5/5] Regenerating all manufacturing deliverables in production/ and 3D renders...")
    os.makedirs("production/gerbers", exist_ok=True)
    os.makedirs("renders", exist_ok=True)

    # Clean old files in production/gerbers
    for fn in os.listdir("production/gerbers"):
        fp_del = os.path.join("production/gerbers", fn)
        if os.path.isfile(fp_del):
            os.remove(fp_del)

    # Export Gerbers & Drills (separate PTH.drl and NPTH.drl)
    subprocess.run([
        "/usr/bin/kicad-cli", "pcb", "export", "gerbers",
        "--layers", "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts",
        "--output", "production/gerbers/",
        PCB_PATH
    ], check=True)

    subprocess.run([
        "/usr/bin/kicad-cli", "pcb", "export", "drill",
        "--format", "excellon",
        "--excellon-separate-th",
        "--generate-map", "--map-format", "gerberx2",
        "--output", "production/gerbers/",
        PCB_PATH
    ], check=True)

    # Remove any stale single abx-motion.drl in production/
    if os.path.exists("production/abx-motion.drl"):
        os.remove("production/abx-motion.drl")

    # Package Gerbers + Drills ZIP
    import zipfile
    for zpath in ("production/abx-motion-v1.1-gerbers.zip", "production/abx-motion-gerbers.zip"):
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
            for fn in sorted(os.listdir("production/gerbers")):
                full_p = os.path.join("production/gerbers", fn)
                if os.path.isfile(full_p):
                    zf.write(full_p, arcname=fn)

    # Generate grouped JLCPCB_BOM.csv (100% LCSC coverage for all assembled parts excluding H1-H6, LOGO1/2, TP_*)
    import csv
    import re

    def nat_key(s):
        return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]

    bom_groups = {}  # (val, pkg, lcsc) -> [refs]
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref.startswith(("H", "LOGO", "TP_")):
            continue
        val = fp.GetValue()
        pkg = str(fp.GetFPID().GetLibItemName())
        lcsc = ""
        for fld in fp.GetFields():
            if fld.GetName() == "LCSC":
                lcsc = fld.GetText().strip()
        assert lcsc, f"Missing LCSC part number on {ref} ({val}, {pkg})"
        if ref in ("U501", "U502"):
            # Each StepStick socket uses 2x 8-pin female header strips (C2718489)
            bom_groups.setdefault(("PinSocket_1x08", "PinSocket_1x08_P2.54mm_Vertical", lcsc), []).extend([f"{ref}_L", f"{ref}_R"])
        else:
            bom_groups.setdefault((val, pkg, lcsc), []).append(ref)

    bom_rows = []
    for (val, pkg, lcsc), refs in bom_groups.items():
        refs_sorted = sorted(refs, key=nat_key)
        bom_rows.append((refs_sorted[0], val, ",".join(refs_sorted), pkg, lcsc))
    bom_rows.sort(key=lambda r: nat_key(r[0]))

    for bom_path in ("production/JLCPCB_BOM.csv", "production/abx-motion-jlcpcb-bom.csv", "production/abx-motion-bom.csv"):
        with open(bom_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
            for _, val, desigs, pkg, lcsc in bom_rows:
                w.writerow([val, desigs, pkg, lcsc])

    # Preserve existing placement data; final supplier placement review is still
    # required. Package-name angle guesses below are not pad verification.
    old_cpl = {}
    if os.path.exists("production/abx-motion-jlcpcb-cpl.csv"):
        with open("production/abx-motion-jlcpcb-cpl.csv") as f:
            for r in csv.DictReader(f):
                old_cpl[r["Designator"]] = r

    cpl_rows = []
    for fp in sorted(board.GetFootprints(), key=lambda x: nat_key(x.GetReference())):
        ref = fp.GetReference()
        if ref.startswith(("H", "LOGO", "TP_")):
            continue
        val = fp.GetValue()
        pkg = str(fp.GetFPID().GetLibItemName())
        layer_str = "Bottom" if fp.GetLayer() == pcbnew.B_Cu else "Top"

        if ref in ("U501", "U502"):
            # Split into _L and _R 1x08 female headers using pad centers
            pads_l = [p for p in fp.Pads() if int(p.GetNumber()) <= 8]
            pads_r = [p for p in fp.Pads() if int(p.GetNumber()) > 8]
            for suffix, plist in (("_L", pads_l), ("_R", pads_r)):
                mx = sum(pcbnew.ToMM(p.GetPosition().x) for p in plist) / len(plist)
                my = sum(pcbnew.ToMM(p.GetPosition().y) for p in plist) / len(plist)
                cpl_rows.append((f"{ref}{suffix}", "PinSocket_1x08", "PinSocket_1x08_P2.54mm_Vertical", f"{mx:.4f}mm", f"{-my:.4f}mm", "90.0", layer_str))
            continue

        # Determine centroid and EasyEDA rotation
        pads = list(fp.Pads())
        p_pos = fp.GetPosition()
        fx, fy = pcbnew.ToMM(p_pos.x), pcbnew.ToMM(p_pos.y)
        krot = fp.GetOrientationDegrees() % 360.0

        # Existing rows are historical placement data, not proof of approval.
        if ref in old_cpl and ref not in ("C203", "C204", "C212", "C213", "C214", "R206", "R227", "R228", "R229", "SW201", "SW202", "SW203", "SW204", "SW205"):
            old_r = old_cpl[ref]
            rotation = old_r["Rotation"]
            # Supplier pad-1 and keyed-outline audit, 2026-10-20. Do not carry
            # the former reversed LED / XT60 angles into another export.
            if ref == "J1":
                rotation = f"{krot:.1f}"
            elif ref in ("LED201", "LED202", "LED_FLT1", "LED_FLT2"):
                rotation = f"{(krot + 180.0) % 360.0:.1f}"
            cpl_rows.append((ref, val, pkg, old_r["Mid X"], old_r["Mid Y"], rotation, old_r["Layer"]))
            continue

        # Compute pad midpoint centroid
        xs = [pcbnew.ToMM(p.GetPosition().x) for p in pads]
        ys = [pcbnew.ToMM(p.GetPosition().y) for p in pads]
        mx = (min(xs) + max(xs)) * 0.5
        my = (min(ys) + max(ys)) * 0.5

        # EasyEDA rotation mapping for new/moved parts
        if ref == "J1":
            erot = krot
        elif ref in ("LED201", "LED202", "LED_FLT1", "LED_FLT2"):
            erot = (krot + 180.0) % 360.0
        elif "SOT-23" in pkg:
            erot = (krot + 180.0) % 360.0
            mx += 0.0208
        elif "TSSOP-24" in pkg:
            erot = (krot + 270.0) % 360.0
        elif "D_SOD-123" in pkg:
            erot = krot
        elif "JST_PH_B3B-PH-K" in pkg:
            erot = (krot + 180.0) % 360.0
        else:
            erot = krot

        cpl_rows.append((ref, val, pkg, f"{mx:.4f}mm", f"{-my:.4f}mm", f"{erot:.1f}", layer_str))

    for cpl_path in ("production/JLCPCB_CPL.csv", "production/abx-motion-jlcpcb-cpl.csv", "production/abx-motion-cpl.csv"):
        with open(cpl_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Designator", "Val", "Package", "Mid X", "Mid Y", "Rotation", "Layer"])
            for row in cpl_rows:
                w.writerow(row)

    # Export Schematics PDF
    subprocess.run([
        "/usr/bin/kicad-cli", "sch", "export", "pdf",
        "--output", "production/abx-motion-schematics.pdf",
        "abx-motion.kicad_sch"
    ], check=True)
    shutil.copy2("production/abx-motion-schematics.pdf", "abx-motion-schematics.pdf")

    # Export 3D Renders (Top & Bottom)
    subprocess.run([
        "/usr/bin/kicad-cli", "pcb", "render",
        "--side", "top", "--width", "1600", "--height", "1100",
        "--output", "renders/pcb_3d_top.png",
        PCB_PATH
    ], check=True)
    subprocess.run([
        "/usr/bin/kicad-cli", "pcb", "render",
        "--side", "bottom", "--width", "1600", "--height", "1100",
        "--output", "renders/pcb_3d_bottom.png",
        PCB_PATH
    ], check=True)
    shutil.copy2("renders/pcb_3d_top.png", "production/pcb_3d_top.png")
    shutil.copy2("renders/pcb_3d_bottom.png", "production/pcb_3d_bottom.png")

    print("All manufacturing deliverables and 3D renders regenerated successfully!")


if __name__ == "__main__":
    main()

