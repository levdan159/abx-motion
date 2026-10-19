#!/usr/bin/env python3
import sys
import os
import math
import heapq
import subprocess
import json
from collections import defaultdict
import pcbnew

PCB_PATH = "/home/daniel/Documents/kicad/abx-motion/abx-motion.kicad_pcb"

def mm(val):
    return pcbnew.FromMM(val)

def to_mm(val):
    return pcbnew.ToMM(val)

def seg_dist_sq(x1, y1, x2, y2, px, py):
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return (px - x1)**2 + (py - y1)**2
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return (px - proj_x)**2 + (py - proj_y)**2

def seg_to_seg_dist(ax1, ay1, ax2, ay2, bx1, by1, bx2, by2):
    def ccw(x1, y1, x2, y2, x3, y3):
        return (y3 - y1) * (x2 - x1) > (y2 - y1) * (x3 - x1)
    if (ax1, ay1) != (ax2, ay2) and (bx1, by1) != (bx2, by2):
        if (ccw(ax1, ay1, bx1, by1, bx2, by2) != ccw(ax2, ay2, bx1, by1, bx2, by2) and
            ccw(ax1, ay1, ax2, ay2, bx1, by1) != ccw(ax1, ay1, ax2, ay2, bx2, by2)):
            return 0.0
    d1 = seg_dist_sq(ax1, ay1, ax2, ay2, bx1, by1)
    d2 = seg_dist_sq(ax1, ay1, ax2, ay2, bx2, by2)
    d3 = seg_dist_sq(bx1, by1, bx2, by2, ax1, ay1)
    d4 = seg_dist_sq(bx1, by1, bx2, by2, ax2, ay2)
    return math.sqrt(min(d1, d2, d3, d4))

def point_to_rect_dist(px, py, rx1, ry1, rx2, ry2):
    dx = max(rx1 - px, 0.0, px - rx2)
    dy = max(ry1 - py, 0.0, py - ry2)
    return math.sqrt(dx * dx + dy * dy)

def seg_to_rect_dist(x1, y1, x2, y2, rx1, ry1, rx2, ry2):
    if rx1 <= x1 <= rx2 and ry1 <= y1 <= ry2:
        return 0.0
    if rx1 <= x2 <= rx2 and ry1 <= y2 <= ry2:
        return 0.0
    d1 = seg_to_seg_dist(x1, y1, x2, y2, rx1, ry1, rx2, ry1)
    if d1 == 0.0: return 0.0
    d2 = seg_to_seg_dist(x1, y1, x2, y2, rx2, ry1, rx2, ry2)
    if d2 == 0.0: return 0.0
    d3 = seg_to_seg_dist(x1, y1, x2, y2, rx2, ry2, rx1, ry2)
    if d3 == 0.0: return 0.0
    d4 = seg_to_seg_dist(x1, y1, x2, y2, rx1, ry2, rx1, ry1)
    if d4 == 0.0: return 0.0
    return min(d1, d2, d3, d4)

def point_in_poly(x, y, poly):
    inside = False
    n = len(poly)
    p1x, p1y = poly[0]
    for i in range(1, n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside

def in_keepout(x, y, margin=0.0):
    if (91.0 - margin) <= x <= (111.0 + margin) and (48.0 - margin) <= y <= (53.5 + margin):
        return True
    if x < 46.2 + margin or x > 200.8 - margin or y < 49.2 + margin or y > 151.8 - margin:
        return True
    for mhx, mhy in [(49.5, 52.5), (197.5, 52.5), (49.5, 148.5), (197.5, 148.5)]:
        if math.hypot(x - mhx, y - mhy) < 3.4 + margin:
            return True
    return False

def seg_in_keepout(x1, y1, x2, y2, margin=0.0):
    if seg_to_rect_dist(x1, y1, x2, y2, 91.0 - margin, 48.0 - margin, 111.0 + margin, 53.5 + margin) <= 0.01:
        return True
    for mhx, mhy in [(49.5, 52.5), (197.5, 52.5), (49.5, 148.5), (197.5, 148.5)]:
        if math.sqrt(seg_dist_sq(x1, y1, x2, y2, mhx, mhy)) < 3.4 + margin:
            return True
    return False

def add_zone_poly(board, net_name, layer, pts, clearance_mm=0.25, min_thick_mm=0.22, priority=0, pad_conn=pcbnew.ZONE_CONNECTION_FULL):
    net_item = board.GetNetInfo().GetNetItem(net_name)
    zone = pcbnew.ZONE(board)
    zone.SetNet(net_item)
    zone.SetLayer(layer)
    zone.SetLocalClearance(mm(clearance_mm))
    zone.SetMinThickness(mm(min_thick_mm))
    zone.SetPadConnection(pad_conn)
    zone.SetThermalReliefGap(mm(0.25))
    zone.SetThermalReliefSpokeWidth(mm(0.35))
    zone.SetAssignedPriority(priority)
    zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    outline = zone.Outline()
    outline.NewOutline()
    for x, y in pts:
        outline.Append(mm(x), mm(y))
    board.Add(zone)
    return zone

def main():
    print("Loading PCB...")
    board = pcbnew.LoadBoard(PCB_PATH)

    ds = board.GetDesignSettings()
    ds.m_HoleToHoleMin = mm(0.2)
    ds.m_ViasMinSize = mm(0.4)
    ds.m_MinThroughDrill = mm(0.18)
    ds.m_TextSizeMin = mm(0.6)

    tracks_to_remove = list(board.GetTracks())
    for t in tracks_to_remove:
        board.Delete(t)

    zones_to_remove = []
    for z in board.Zones():
        if not z.GetIsRuleArea():
            zones_to_remove.append(z)
    for z in zones_to_remove:
        board.Delete(z)

    for fp in board.GetFootprints():
        if fp.GetReference() == "U3":
            for z in fp.Zones():
                if z.GetIsRuleArea():
                    outline = z.Outline()
                    outline.RemoveAllContours()
                    outline.NewOutline()
                    for kx, ky in [(91.5, 46.0), (110.5, 46.0), (110.5, 53.5), (91.5, 53.5)]:
                        outline.Append(mm(kx), mm(ky))

    print(f"Removed {len(tracks_to_remove)} old tracks/vias and {len(zones_to_remove)} copper zones.")

    # 2. Configure 4-Layer Copper Planes (ISLAND_REMOVAL_MODE_ALWAYS + solid connection on internal planes)
    board_poly = [(46.0, 49.0), (90.8, 49.0), (90.8, 53.6), (111.2, 53.6), (111.2, 49.0), (201.0, 49.0), (201.0, 152.0), (46.0, 152.0)]
    add_zone_poly(board, "GND", pcbnew.In1_Cu, board_poly, clearance_mm=0.22, priority=1, pad_conn=pcbnew.ZONE_CONNECTION_FULL)
    add_zone_poly(board, "GND", pcbnew.B_Cu, board_poly, clearance_mm=0.22, priority=1, pad_conn=pcbnew.ZONE_CONNECTION_FULL)

    # Remove any old B.Cu keepout zone so central B.Cu routing highway is 100% unobstructed
    for z in list(board.Zones()):
        if z.GetIsRuleArea() and z.GetLayerSet().Contains(pcbnew.B_Cu) and not z.GetLayerSet().Contains(pcbnew.F_Cu):
            board.Delete(z)

    batt_poly = [
        (114.0, 49.0), (201.0, 49.0), (201.0, 152.0), (173.0, 152.0),
        (173.0, 116.0), (156.0, 116.0), (156.0, 70.0), (129.0, 70.0),
        (129.0, 56.0), (114.0, 56.0)
    ]
    v33_poly = [
        (46.0, 49.0), (90.8, 49.0), (90.8, 53.6), (113.5, 53.6),
        (113.5, 56.5), (128.5, 56.5), (128.5, 96.0), (132.0, 96.0),
        (132.0, 130.5), (69.5, 130.5), (69.5, 116.5), (46.0, 116.5)
    ]
    v5_poly = [
        (46.0, 117.0), (69.0, 117.0), (69.0, 131.0), (132.5, 131.0),
        (132.5, 96.5), (135.0, 96.5), (135.0, 70.5), (155.5, 70.5),
        (155.5, 116.5), (172.5, 116.5), (172.5, 152.0), (46.0, 152.0)
    ]

    add_zone_poly(board, "+BATT", pcbnew.In2_Cu, batt_poly, clearance_mm=0.25, priority=3, pad_conn=pcbnew.ZONE_CONNECTION_FULL)
    add_zone_poly(board, "+5V", pcbnew.In2_Cu, v5_poly, clearance_mm=0.22, priority=2, pad_conn=pcbnew.ZONE_CONNECTION_FULL)
    add_zone_poly(board, "+3V3", pcbnew.In2_Cu, v33_poly, clearance_mm=0.22, priority=1, pad_conn=pcbnew.ZONE_CONNECTION_FULL)

    net_map = {}
    for net_code, net_item in board.GetNetsByNetcode().items():
        net_map[net_item.GetNetname()] = net_code

    # 3. Collect all Pads (using pad.GetBoundingBox() for exact copper dimensions)
    all_pads = []
    nets_pads = defaultdict(list)

    for fp in board.GetFootprints():
        ref = fp.GetReference()
        seen_ref_num_pos = {}
        for pad in fp.Pads():
            num = pad.GetNumber()
            nc = pad.GetNetCode()
            is_npth = (pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH)
            is_pth = (pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH)
            is_thru = is_pth or is_npth

            if nc <= 0 and not is_npth and (num == "" or not (pad.IsOnLayer(pcbnew.F_Cu) or pad.IsOnLayer(pcbnew.B_Cu))):
                continue

            pos = pad.GetPosition()
            px, py = round(to_mm(pos.x), 4), round(to_mm(pos.y), 4)
            bb = pad.GetBoundingBox()
            sx = round(to_mm(bb.GetWidth()), 4)
            sy = round(to_mm(bb.GetHeight()), 4)

            if num != "" and nc > 0:
                dup_coord = None
                for existing_p in nets_pads[nc]:
                    if existing_p["ref"] == ref and math.hypot(px - existing_p["x"], py - existing_p["y"]) < 0.05:
                        dup_coord = existing_p
                        break
                if dup_coord is not None:
                    if is_thru:
                        dup_coord["is_thru"] = True
                        dup_coord["layers"].update([pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu])
                    continue

                if (ref, num) in seen_ref_num_pos:
                    prev_p = seen_ref_num_pos[(ref, num)]
                    if math.hypot(px - prev_p["x"], py - prev_p["y"]) < 1.8:
                        if is_thru:
                            prev_p["is_thru"] = True
                            prev_p["layers"].update([pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu])
                        if sx * sy > prev_p["w"] * prev_p["h"]:
                            prev_p["x"], prev_p["y"] = px, py
                            prev_p["w"], prev_p["h"] = sx, sy
                            prev_p["rx1"], prev_p["ry1"] = px - sx / 2.0, py - sy / 2.0
                            prev_p["rx2"], prev_p["ry2"] = px + sx / 2.0, py + sy / 2.0
                        continue

            layers = set()
            if is_thru:
                layers.update([pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu])
            else:
                if pad.IsOnLayer(pcbnew.F_Cu): layers.add(pcbnew.F_Cu)
                if pad.IsOnLayer(pcbnew.B_Cu): layers.add(pcbnew.B_Cu)

            pad_id = len(all_pads)
            pinfo = {
                "id": pad_id,
                "ref": ref,
                "num": num,
                "nc": nc if nc > 0 else -1,
                "net": pad.GetNetname(),
                "x": px,
                "y": py,
                "w": sx,
                "h": sy,
                "rx1": px - sx / 2.0,
                "ry1": py - sy / 2.0,
                "rx2": px + sx / 2.0,
                "ry2": py + sy / 2.0,
                "is_thru": is_thru,
                "layers": layers,
            }
            all_pads.append(pinfo)
            if nc > 0:
                nets_pads[nc].append(pinfo)
                if num != "":
                    seen_ref_num_pos[(ref, num)] = pinfo

        if ref == "LOGO1":
            all_pads.append({
                "id": len(all_pads),
                "ref": "LOGO1",
                "num": "LOGO_CU",
                "nc": -999,
                "net": "<logo>",
                "x": 79.5,
                "y": 131.0,
                "w": 20.0,
                "h": 16.0,
                "rx1": 69.5,
                "ry1": 123.0,
                "rx2": 89.5,
                "ry2": 139.0,
                "is_thru": False,
                "layers": {pcbnew.F_Cu},
            })
        elif ref == "LOGO2":
            all_pads.append({
                "id": len(all_pads),
                "ref": "LOGO2",
                "num": "LOGO_CU",
                "nc": -998,
                "net": "<logo>",
                "x": 77.5,
                "y": 120.0,
                "w": 22.0,
                "h": 16.0,
                "rx1": 66.5,
                "ry1": 112.0,
                "rx2": 88.5,
                "ry2": 128.0,
                "is_thru": False,
                "layers": {pcbnew.B_Cu},
            })


    # Spatial bucket for pads (2mm cells)
    PAD_CELL = 2.0
    pad_grid = defaultdict(list)
    for p in all_pads:
        gx1 = int(math.floor((p["rx1"] - 1.5) / PAD_CELL))
        gx2 = int(math.floor((p["rx2"] + 1.5) / PAD_CELL))
        gy1 = int(math.floor((p["ry1"] - 1.5) / PAD_CELL))
        gy2 = int(math.floor((p["ry2"] + 1.5) / PAD_CELL))
        for gx in range(gx1, gx2 + 1):
            for gy in range(gy1, gy2 + 1):
                pad_grid[(gx, gy)].append(p)

    placed_segs = defaultdict(list)
    seg_grid = defaultdict(lambda: defaultdict(list))
    placed_vias = []
    via_grid = defaultdict(list)
    net_routed_nodes = defaultdict(list)

    def register_seg(layer, x1, y1, x2, y2, w, nc):
        idx = len(placed_segs[layer])
        s = (x1, y1, x2, y2, w, nc)
        placed_segs[layer].append(s)
        gx1 = int(math.floor((min(x1, x2) - w - 1.0) / PAD_CELL))
        gx2 = int(math.floor((max(x1, x2) + w + 1.0) / PAD_CELL))
        gy1 = int(math.floor((min(y1, y2) - w - 1.0) / PAD_CELL))
        gy2 = int(math.floor((max(y1, y2) + w + 1.0) / PAD_CELL))
        for gx in range(gx1, gx2 + 1):
            for gy in range(gy1, gy2 + 1):
                seg_grid[layer][(gx, gy)].append(idx)

    def register_via(x, y, dia, nc):
        idx = len(placed_vias)
        v = (x, y, dia, nc)
        placed_vias.append(v)
        gx1 = int(math.floor((x - dia - 1.0) / PAD_CELL))
        gx2 = int(math.floor((x + dia + 1.0) / PAD_CELL))
        gy1 = int(math.floor((y - dia - 1.0) / PAD_CELL))
        gy2 = int(math.floor((y + dia + 1.0) / PAD_CELL))
        for gx in range(gx1, gx2 + 1):
            for gy in range(gy1, gy2 + 1):
                via_grid[(gx, gy)].append(idx)

    def add_track(board, x1, y1, x2, y2, layer, width_mm, nc):
        if math.hypot(x2 - x1, y2 - y1) < 0.005:
            return
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
        t.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
        t.SetLayer(layer)
        t.SetWidth(mm(width_mm))
        t.SetNetCode(nc)
        board.Add(t)
        register_seg(layer, x1, y1, x2, y2, width_mm, nc)

    def add_via(board, x, y, drill_mm, dia_mm, nc):
        for vx, vy, vdia, vnc in placed_vias:
            if vnc == nc and math.hypot(x - vx, y - vy) < 0.25:
                return
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetWidth(mm(dia_mm))
        v.SetDrill(mm(drill_mm))
        v.SetNetCode(nc)
        board.Add(v)
        register_via(x, y, dia_mm, nc)

    def is_via_clear(x, y, dia, nc, clr=0.25):
        if in_keepout(x, y, dia / 2.0 + clr):
            return False
        r = dia / 2.0 + clr
        gx = int(math.floor(x / PAD_CELL))
        gy = int(math.floor(y / PAD_CELL))
        seen_pads = set()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for p in pad_grid.get((gx + dx, gy + dy), ()):
                    pid = p["id"]
                    if pid in seen_pads: continue
                    seen_pads.add(pid)
                    if p["nc"] == nc:
                        if p["is_thru"] and math.hypot(x - p["x"], y - p["y"]) < 0.65:
                            return False
                        continue
                    eff_r = r + 0.15 if p["is_thru"] else r
                    if point_to_rect_dist(x, y, p["rx1"], p["ry1"], p["rx2"], p["ry2"]) < eff_r:
                        return False
                for vidx in via_grid.get((gx + dx, gy + dy), ()):
                    vx, vy, vdia, vnc = placed_vias[vidx]
                    if vnc == nc and math.hypot(x - vx, y - vy) < 0.25:
                        continue
                    min_d = (dia / 2.0 + vdia / 2.0 + 0.15) if vnc == nc else (dia / 2.0 + vdia / 2.0 + clr)
                    if math.hypot(x - vx, y - vy) < min_d:
                        return False
                for layer in (pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In2_Cu, pcbnew.In1_Cu):
                    for sidx in seg_grid[layer].get((gx + dx, gy + dy), ()):
                        sx1, sy1, sx2, sy2, sw, snc = placed_segs[layer][sidx]
                        if snc == nc: continue
                        if math.sqrt(seg_dist_sq(sx1, sy1, sx2, sy2, x, y)) < (dia / 2.0 + sw / 2.0 + clr):
                            return False
        return True

    def is_seg_clear(layer, x1, y1, x2, y2, w, nc, clr=0.25, allow_same_fp_ref=None):
        if in_keepout(x1, y1, w / 2.0 + 0.15) or in_keepout(x2, y2, w / 2.0 + 0.15):
            return False
        if seg_in_keepout(x1, y1, x2, y2, w / 2.0 + 0.15):
            return False
        gx1 = int(math.floor(min(x1, x2) / PAD_CELL)) - 1
        gx2 = int(math.floor(max(x1, x2) / PAD_CELL)) + 1
        gy1 = int(math.floor(min(y1, y2) / PAD_CELL)) - 1
        gy2 = int(math.floor(max(y1, y2) / PAD_CELL)) + 1

        seen_pads = set()
        seen_segs = set()
        seen_vias = set()
        for gx in range(gx1, gx2 + 1):
            for gy in range(gy1, gy2 + 1):
                cell = (gx, gy)
                for p in pad_grid.get(cell, ()):
                    pid = p["id"]
                    if pid in seen_pads: continue
                    seen_pads.add(pid)
                    if p["nc"] == nc: continue
                    if layer not in p["layers"]: continue
                    eff_clr = 0.14 if (allow_same_fp_ref is not None and p["ref"] == allow_same_fp_ref) else clr
                    if seg_to_rect_dist(x1, y1, x2, y2, p["rx1"], p["ry1"], p["rx2"], p["ry2"]) < (w / 2.0 + eff_clr):
                        return False
                for sidx in seg_grid[layer].get(cell, ()):
                    if sidx in seen_segs: continue
                    seen_segs.add(sidx)
                    sx1, sy1, sx2, sy2, sw, snc = placed_segs[layer][sidx]
                    if snc == nc: continue
                    if seg_to_seg_dist(x1, y1, x2, y2, sx1, sy1, sx2, sy2) < (w / 2.0 + sw / 2.0 + clr):
                        return False
                for vidx in via_grid.get(cell, ()):
                    if vidx in seen_vias: continue
                    seen_vias.add(vidx)
                    vx, vy, vdia, vnc = placed_vias[vidx]
                    if vnc == nc: continue
                    if math.sqrt(seg_dist_sq(x1, y1, x2, y2, vx, vy)) < (w / 2.0 + vdia / 2.0 + clr):
                        return False
        return True

    def in_target_plane(net_name, x, y):
        if net_name == "GND":
            return not in_keepout(x, y, 0.3)
        elif net_name == "+BATT":
            return point_in_poly(x, y, batt_poly)
        elif net_name == "+5V":
            return point_in_poly(x, y, v5_poly)
        elif net_name == "+3V3":
            return point_in_poly(x, y, v33_poly)
        return False

    gnd_nc = net_map.get("GND", -1)
    plane_nets = ["GND", "+BATT", "+5V", "+3V3"]
    connected_pad_ids = set()

    # 4. Pre-Fanout U301 and U401 GND pins (5, 16, 20 straight orthogonally into Pad 25; Pin 12 straight South; Pin 1 straight West)
    batt_nc = net_map.get("+BATT", -1)
    for drv_ref in ("U301", "U401"):
        p25 = next((p for p in all_pads if p["ref"] == drv_ref and p["num"] == "25"), None)
        if not p25:
            continue
        cx_drv, cy_drv = p25["x"], p25["y"]
        connected_pad_ids.add(p25["id"])
        for gpin, tx, ty in [
            ("5",  cx_drv - 0.8, cy_drv + 0.75),
            ("16", cx_drv + 0.8, cy_drv - 0.25),
            ("20", cx_drv + 0.75, cy_drv - 0.8),
        ]:
            gp = next((p for p in all_pads if p["ref"] == drv_ref and p["num"] == gpin), None)
            if gp:
                add_track(board, gp["x"], gp["y"], tx, ty, pcbnew.F_Cu, 0.20, gnd_nc)
                add_track(board, tx, ty, cx_drv, cy_drv, pcbnew.F_Cu, 0.20, gnd_nc)
                connected_pad_ids.add(gp["id"])

        # Pin 12 (GND) and Pin 1 (+BATT) are fanned out in Pass 4 after all fine-pitch signals route!




    # Connect R203.1 (+3V3 at 84.175, 58.90) to a dedicated +3V3 via at (83.6, 59.6) inside v33_poly:
    pr203_1 = next((p for p in all_pads if p["ref"] == "R203" and p["num"] == "1"), None)
    v33_nc = net_map.get("+3V3", -1)
    if pr203_1 and v33_nc > 0:
        add_track(board, pr203_1["x"], pr203_1["y"], 83.6, 59.6, pcbnew.F_Cu, 0.25, v33_nc)
        add_via(board, 83.6, 59.6, 0.3, 0.6, v33_nc)
        connected_pad_ids.add(pr203_1["id"])

    # Connect C7.1 and C8.1 (+5V) vertically on F.Cu and drop a +5V via at (147.5, 74.25) inside v5_poly!
    v5_nc = net_map.get("+5V", -1)
    if v5_nc > 0:
        p_c7 = next((p for p in all_pads if p["ref"] == "C7" and p["num"] == "1"), None)
        p_c8 = next((p for p in all_pads if p["ref"] == "C8" and p["num"] == "1"), None)
        if p_c7 and p_c8:
            add_track(board, p_c7["x"], p_c7["y"], p_c8["x"], p_c8["y"], pcbnew.F_Cu, 0.6, v5_nc)
            add_via(board, p_c7["x"], round((p_c7["y"] + p_c8["y"]) / 2.0, 3), 0.3, 0.6, v5_nc)
            connected_pad_ids.update([p_c7["id"], p_c8["id"]])

    # Strap sibling Source pins (1-2-3) on Q1, Q301..Q304, Q401..Q404 together on F.Cu with a 0.40mm strap
    for qref in ("Q1", "Q301", "Q302", "Q303", "Q304", "Q401", "Q402", "Q403", "Q404"):
        p1 = next((p for p in all_pads if p["ref"] == qref and p["num"] == "1"), None)
        p2 = next((p for p in all_pads if p["ref"] == qref and p["num"] == "2"), None)
        p3 = next((p for p in all_pads if p["ref"] == qref and p["num"] == "3"), None)
        if p1 and p2 and p3 and p1["nc"] > 0:
            add_track(board, p1["x"], p1["y"], p2["x"], p2["y"], pcbnew.F_Cu, 0.40, p1["nc"])
            add_track(board, p2["x"], p2["y"], p3["x"], p3["y"], pcbnew.F_Cu, 0.40, p1["nc"])

    # Pre-strap J201 reversible USB-C pairs (A6-B6 = USB_CONN_DP, A7-B7 = USB_CONN_DN) cleanly with horizontal F.Cu escapes!
    nc_dp = net_map.get("/MCU_and_Encoders/USB_CONN_DP", -1)
    nc_dn = net_map.get("/MCU_and_Encoders/USB_CONN_DN", -1)
    if nc_dp > 0:
        add_track(board, 53.545, 61.25, 54.6, 61.25, pcbnew.F_Cu, 0.20, nc_dp)
        add_track(board, 53.545, 62.25, 54.6, 62.25, pcbnew.F_Cu, 0.20, nc_dp)
        add_track(board, 54.6, 61.25, 54.6, 62.25, pcbnew.F_Cu, 0.20, nc_dp)
        add_track(board, 54.6, 62.25, 55.3, 62.95, pcbnew.F_Cu, 0.20, nc_dp)
        add_track(board, 55.3, 62.95, 56.8625, 62.95, pcbnew.F_Cu, 0.20, nc_dp)
    if nc_dn > 0:
        add_track(board, 53.545, 61.75, 52.5, 61.75, pcbnew.F_Cu, 0.20, nc_dn)
        add_track(board, 53.545, 60.75, 52.5, 60.75, pcbnew.F_Cu, 0.20, nc_dn)
        add_track(board, 52.5, 60.75, 52.5, 61.75, pcbnew.F_Cu, 0.20, nc_dn)
        add_track(board, 53.545, 60.75, 55.5, 60.75, pcbnew.F_Cu, 0.20, nc_dn)
        add_track(board, 55.5, 60.75, 55.8, 61.05, pcbnew.F_Cu, 0.20, nc_dn)
        add_track(board, 55.8, 61.05, 56.8625, 61.05, pcbnew.F_Cu, 0.20, nc_dn)





    # Mark PTH pads inside their target plane as connected (Pass 4 will fan out SMD power/GND pads LAST!)
    for net_name in plane_nets:
        nc = net_map.get(net_name, -1)
        if nc <= 0: continue
        for p in nets_pads[nc]:
            if p["is_thru"] and in_target_plane(net_name, p["x"], p["y"]):
                connected_pad_ids.add(p["id"])
            elif p["ref"] in ("H1", "H2", "H3", "H4"):
                connected_pad_ids.add(p["id"])

    # 5. Grid-based A* Router (3-Layer Routing: F.Cu, B.Cu, In2.Cu)
    LAYER_LIST = [pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In2_Cu]

    def get_net_width_and_via(net_name):
        if net_name in ("/Power_Supply/V_RAW_IN", "/Power_Supply/V_FUSED"):
            return 1.5, 0.4, 0.8
        if net_name in ("/DC_Motor_1/MOT_OUT1", "/DC_Motor_1/MOT_OUT2",
                        "/DC_Motor_2/MOT_OUT1", "/DC_Motor_2/MOT_OUT2",
                        "/DC_Motor_1/SHUNT_SP", "/DC_Motor_2/SHUNT_SP",
                        "+BATT"):
            return 0.6, 0.4, 0.8
        if net_name.startswith("/Steppers_and_Relays/RLY") and any(k in net_name for k in ("_NO", "_COM", "_NC")):
            return 0.8, 0.4, 0.8
        if net_name.startswith("/Steppers_and_Relays/STEP1_") or net_name.startswith("/Steppers_and_Relays/STEP2_"):
            if any(k in net_name for k in ("1A", "1B", "2A", "2B")):
                return 0.5, 0.3, 0.6
        if net_name in ("+5V", "+3V3", "+3V3_DRV_EN", "/Power_Supply/SW_NODE"):
            return 0.4, 0.3, 0.6
        return 0.25, 0.3, 0.6

    def route_two_pads_astar(nc, src_pads, dst_pads, width, v_drill, v_dia, grid_step=0.5, max_iter=25000, clr=0.18, use_routed_tree=False, allow_in2=False):
        def snap(v):
            return round(math.floor(v / grid_step + 0.5) * grid_step, 3)

        def get_valid_access_nodes(pinfo):
            valid = []
            px, py = pinfo["x"], pinfo["y"]
            sx, sy = snap(px), snap(py)
            stub_w = min(width, 0.20) if pinfo["ref"] in ("U301", "U401", "J201", "U201", "U3", "U4", "Q301", "Q302", "Q303", "Q304", "Q401", "Q402", "Q403", "Q404") else width

            if pinfo["ref"] in ("U301", "U401") and not pinfo["is_thru"] and pcbnew.F_Cu in pinfo["layers"]:
                num_i = int(pinfo["num"]) if pinfo["num"].isdigit() else 0
                if 1 <= num_i <= 6:
                    for dx in (-0.8125, -1.0625, -1.3125, -1.5625, -1.8125, -2.0625, -2.3125, -2.5625, -0.5625):
                        cx = snap(px + dx)
                        if is_seg_clear(pcbnew.F_Cu, px, py, cx, py, stub_w, nc, clr=0.15, allow_same_fp_ref=pinfo["ref"]) and is_seg_clear(pcbnew.F_Cu, cx, py, cx, sy, stub_w, nc, clr=0.15, allow_same_fp_ref=pinfo["ref"]):
                            valid.append((cx, sy, 0, px, py, stub_w, cx, py))
                elif 7 <= num_i <= 12:
                    for dy in (0.8125, 1.0625, 1.3125, 1.5625, 1.8125, 2.0625, 2.3125, 2.5625, 0.5625):
                        cy = snap(py + dy)
                        if is_seg_clear(pcbnew.F_Cu, px, py, px, cy, stub_w, nc, clr=0.15, allow_same_fp_ref=pinfo["ref"]) and is_seg_clear(pcbnew.F_Cu, px, cy, sx, cy, stub_w, nc, clr=0.15, allow_same_fp_ref=pinfo["ref"]):
                            valid.append((sx, cy, 0, px, py, stub_w, px, cy))
                elif 13 <= num_i <= 18:
                    if num_i == 13:
                        dxs_e = (0.5625, 0.8125, 1.0625, 1.3125, 1.5625)
                    elif num_i == 14:
                        dxs_e = (1.5625, 1.8125, 1.3125, 1.0625, 2.0625)
                    elif num_i == 15:
                        dxs_e = (0.8125, 1.0625, 1.3125, 1.5625, 1.8125, 2.0625, 0.5625)
                    elif num_i == 17:
                        dxs_e = (2.3125, 2.5625, 2.8125, 2.0625)
                    else:
                        dxs_e = (0.8125, 1.0625, 1.3125, 1.5625, 1.8125, 2.0625, 2.3125, 2.5625)
                    cys_e = (sy, round(sy - grid_step, 3), round(sy + grid_step, 3)) if num_i in (14, 15) else (sy,)
                    for cy in cys_e:
                        for dx in dxs_e:
                            cx = snap(px + dx)
                            if is_seg_clear(pcbnew.F_Cu, px, py, cx, py, stub_w, nc, clr=0.14, allow_same_fp_ref=pinfo["ref"]) and is_seg_clear(pcbnew.F_Cu, cx, py, cx, cy, stub_w, nc, clr=0.14, allow_same_fp_ref=pinfo["ref"]):
                                valid.append((cx, cy, 0, px, py, stub_w, cx, py))
                elif 19 <= num_i <= 24:
                    dys_n = (-2.0625, -2.3125, -2.5625) if num_i in (22, 24) else (-0.8125, -1.0625, -1.3125, -1.5625, -1.8125, -2.0625, -2.3125, -2.5625)
                    for dy in dys_n:
                        cy = snap(py + dy)
                        if is_seg_clear(pcbnew.F_Cu, px, py, px, cy, stub_w, nc, clr=0.14, allow_same_fp_ref=pinfo["ref"]) and is_seg_clear(pcbnew.F_Cu, px, cy, sx, cy, stub_w, nc, clr=0.14, allow_same_fp_ref=pinfo["ref"]):
                            valid.append((sx, cy, 0, px, py, stub_w, px, cy))
                if valid:
                    return valid


            if pinfo["ref"] == "J201":
                for cx in (51.0, 51.5, 52.0, 52.5, 53.0, 54.5, 55.0, 55.5, 56.0):
                    if is_seg_clear(pcbnew.F_Cu, px, py, cx, py, stub_w, nc, clr=0.19, allow_same_fp_ref="J201"):
                        if abs(py - sy) < 0.01:
                            valid.append((cx, sy, 0, px, py, stub_w, cx, py))
                if valid:
                    return valid

            if pinfo["ref"] == "U3" and pcbnew.F_Cu in pinfo["layers"]:
                pnum = int(pinfo["num"]) if pinfo["num"].isdigit() else 0
                u3_clr = 0.14 if allow_in2 else 0.15
                if 3 <= pnum <= 14:
                    dxs_u3w = (1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 1.25, -1.25, -1.5, -1.75, -2.0, -2.25, -2.5, -2.75, -3.0) if pnum in (4, 5, 10, 11) else (-1.25, -1.5, -1.75, -2.0, -2.25, -2.5, -2.75, -3.0, -3.5, 1.25, 1.5, 1.75, 2.0, 2.25, -1.0, -0.75)
                    for cy in (sy, round(sy - grid_step, 3), round(sy + grid_step, 3)):
                        for dx in dxs_u3w:
                            cx = snap(px + dx)
                            if is_seg_clear(pcbnew.F_Cu, px, py, cx, py, stub_w, nc, clr=u3_clr, allow_same_fp_ref="U3") and is_seg_clear(pcbnew.F_Cu, cx, py, cx, cy, stub_w, nc, clr=u3_clr, allow_same_fp_ref="U3"):
                                valid.append((cx, cy, 0, px, py, stub_w, cx, py))

                elif 27 <= pnum <= 39:
                    for cy in (sy, round(sy - grid_step, 3), round(sy + grid_step, 3)):
                        for dx in (1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.5, -1.25, -1.5, -1.75, -2.0, -2.25, 1.0, 0.75):
                            cx = snap(px + dx)
                            if is_seg_clear(pcbnew.F_Cu, px, py, cx, py, stub_w, nc, clr=u3_clr, allow_same_fp_ref="U3") and is_seg_clear(pcbnew.F_Cu, cx, py, cx, cy, stub_w, nc, clr=u3_clr, allow_same_fp_ref="U3"):
                                valid.append((cx, cy, 0, px, py, stub_w, cx, py))

                elif 15 <= pnum <= 26:
                    for cx in (sx, round(sx - grid_step, 3), round(sx + grid_step, 3)):
                        for dy in (1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.5, 1.0, 0.75):
                            cy = snap(py + dy)
                            if is_seg_clear(pcbnew.F_Cu, px, py, px, cy, stub_w, nc, clr=u3_clr, allow_same_fp_ref="U3") and is_seg_clear(pcbnew.F_Cu, px, cy, cx, cy, stub_w, nc, clr=u3_clr, allow_same_fp_ref="U3"):
                                valid.append((cx, cy, 0, px, py, stub_w, px, cy))
                if valid:
                    return valid


            if pinfo["ref"] == "U4" and pcbnew.F_Cu in pinfo["layers"]:
                pnum = int(pinfo["num"]) if pinfo["num"].isdigit() else 0
                if pnum in (2, 4, 6):
                    dxs = (1.225, 1.475, 1.725, 0.975, -1.025, -1.275, -1.525, -1.775)
                elif 1 <= pnum <= 7:
                    dxs = (-1.025, -1.275, -1.525, -1.775, -2.025, -2.275, -2.525, -0.775)
                else:
                    dxs = (1.025, 1.275, 1.525, 1.775, 2.025, 2.275, 2.525, 0.775)
                for cy in (sy, round(sy - grid_step, 3), round(sy + grid_step, 3)):
                    for dx in dxs:
                        cx = snap(px + dx)
                        if is_seg_clear(pcbnew.F_Cu, px, py, cx, py, stub_w, nc, clr=0.14, allow_same_fp_ref="U4") and is_seg_clear(pcbnew.F_Cu, cx, py, cx, cy, stub_w, nc, clr=0.14, allow_same_fp_ref="U4"):
                            valid.append((cx, cy, 0, px, py, stub_w, cx, py))
                if valid:
                    return valid


            candidates = [(sx, sy)]
            for d in (-grid_step, 0.0, grid_step):
                for e in (-grid_step, 0.0, grid_step):
                    if d != 0.0 or e != 0.0:
                        candidates.append((round(sx + d, 3), round(sy + e, 3)))
            for mult in (2, -2, 3, -3, 4, -4, 5, -5, 6, -6, 7, -7, 8, -8):
                d = mult * grid_step
                candidates.append((round(sx + d, 3), sy))
                candidates.append((sx, round(sy + d, 3)))
                for e in (-grid_step, grid_step, -2 * grid_step, 2 * grid_step):
                    candidates.append((round(sx + d, 3), round(sy + e, 3)))
                    candidates.append((round(sx + e, 3), round(sy + d, 3)))

            for li, lyr in enumerate(LAYER_LIST):
                if lyr not in pinfo["layers"]:
                    continue
                for cx, cy in candidates:
                    if math.hypot(cx - px, cy - py) < 0.01:
                        valid.append((cx, cy, li, px, py, stub_w, cx, cy))
                    else:
                        use_c = 0.14 if allow_in2 else min(clr, 0.16)
                        if is_seg_clear(lyr, px, py, cx, py, stub_w, nc, clr=use_c, allow_same_fp_ref=pinfo["ref"]) and is_seg_clear(lyr, cx, py, cx, cy, stub_w, nc, clr=use_c, allow_same_fp_ref=pinfo["ref"]):
                            valid.append((cx, cy, li, px, py, stub_w, cx, py))

                        elif is_seg_clear(lyr, px, py, px, cy, stub_w, nc, clr=use_c, allow_same_fp_ref=pinfo["ref"]) and is_seg_clear(lyr, px, cy, cx, cy, stub_w, nc, clr=use_c, allow_same_fp_ref=pinfo["ref"]):
                            valid.append((cx, cy, li, px, py, stub_w, px, cy))

            return valid

        start_nodes = {}
        start_origins = {}
        for p in src_pads:
            for cx, cy, li, ox, oy, sw, mx, my in get_valid_access_nodes(p):
                state = (cx, cy, li)
                if state not in start_nodes:
                    start_nodes[state] = 0.0
                    start_origins[state] = (ox, oy, sw, mx, my)

        goal_map = {}
        goal_pts = []
        for p in dst_pads:
            goal_pts.append((p["x"], p["y"]))
            for cx, cy, li, ox, oy, sw, mx, my in get_valid_access_nodes(p):
                if (cx, cy, li) not in goal_map:
                    goal_map[(cx, cy, li)] = (ox, oy, sw, mx, my)

        if use_routed_tree:
            for rx, ry, rli in net_routed_nodes.get(nc, ()):
                if abs(rx - snap(rx)) < 0.01 and abs(ry - snap(ry)) < 0.01:
                    st = (rx, ry, rli)
                    if st not in goal_map:
                        goal_map[st] = (rx, ry, width, rx, ry)
                        goal_pts.append((rx, ry))

        if not start_nodes or not goal_map:
            return False

        def emit_stub(ox, oy, mx, my, gx, gy, lyr, sw):
            if lyr != pcbnew.F_Cu:
                pad_is_f_only = any(abs(p["x"] - ox) < 0.01 and abs(p["y"] - oy) < 0.01 and not p["is_thru"] and pcbnew.F_Cu in p["layers"] and pcbnew.B_Cu not in p["layers"] for p in nets_pads[nc])
                if pad_is_f_only:
                    if math.hypot(ox - mx, oy - my) >= 0.005:
                        add_track(board, ox, oy, mx, my, pcbnew.F_Cu, sw, nc)
                    if math.hypot(mx - gx, my - gy) >= 0.005:
                        add_track(board, mx, my, gx, gy, pcbnew.F_Cu, sw, nc)
                    add_via(board, gx, gy, v_drill, v_dia, nc)
                    return
            if math.hypot(ox - mx, oy - my) >= 0.005:
                add_track(board, ox, oy, mx, my, lyr, sw, nc)
            if math.hypot(mx - gx, my - gy) >= 0.005:
                add_track(board, mx, my, gx, gy, lyr, sw, nc)

        for st in start_nodes:
            if st in goal_map:
                ox1, oy1, sw1, mx1, my1 = start_origins[st]
                ox2, oy2, sw2, mx2, my2 = goal_map[st]
                lyr = LAYER_LIST[st[2]]
                emit_stub(ox1, oy1, mx1, my1, st[0], st[1], lyr, sw1)
                emit_stub(ox2, oy2, mx2, my2, st[0], st[1], lyr, sw2)
                net_routed_nodes[nc].append(st)
                return True

        def h_cost(x, y):
            return min(math.hypot(x - gx, y - gy) for gx, gy in goal_pts)

        open_pq = []
        g_score = {}
        parent = {}

        for st, cost in start_nodes.items():
            g_score[st] = cost
            heapq.heappush(open_pq, (cost + h_cost(st[0], st[1]), cost, st[0], st[1], st[2]))

        dirs_8 = [
            (grid_step, 0.0, grid_step),
            (-grid_step, 0.0, grid_step),
            (0.0, grid_step, grid_step),
            (0.0, -grid_step, grid_step),
            (grid_step, grid_step, grid_step * 1.4142),
            (grid_step, -grid_step, grid_step * 1.4142),
            (-grid_step, grid_step, grid_step * 1.4142),
            (-grid_step, -grid_step, grid_step * 1.4142),
        ]

        iters = 0
        found_goal = None

        while open_pq and iters < max_iter:
            iters += 1
            f, g, x, y, li = heapq.heappop(open_pq)
            st = (x, y, li)
            if g > g_score.get(st, 1e18) + 1e-5:
                continue

            if st in goal_map:
                found_goal = st
                break

            lyr = LAYER_LIST[li]
            layer_factor = 1.0 if li == 0 else (1.06 if li == 1 else 10.0)
            prev_st = parent.get(st)
            pdx = round(x - prev_st[0], 3) if (prev_st is not None and prev_st[2] == li) else None
            pdy = round(y - prev_st[1], 3) if (prev_st is not None and prev_st[2] == li) else None

            for dx, dy, step_c in dirs_8:
                nx = round(x + dx, 3)
                ny = round(y + dy, 3)
                turn_pen = 0.35 if (pdx is not None and (dx != pdx or dy != pdy)) else 0.0
                nst = (nx, ny, li)
                ng = g + step_c * layer_factor + turn_pen
                if ng >= g_score.get(nst, 1e18):
                    continue
                if not is_seg_clear(lyr, x, y, nx, ny, width, nc, clr=clr):
                    continue
                g_score[nst] = ng
                parent[nst] = st
                heapq.heappush(open_pq, (ng + h_cost(nx, ny) * 1.15, ng, nx, ny, li))

            max_layers = 3 if allow_in2 else 2
            for other_li in range(max_layers):
                if other_li == li:
                    continue
                nst_v = (x, y, other_li)
                ng_v = g + 2.5
                if ng_v < g_score.get(nst_v, 1e18):
                    if is_via_clear(x, y, v_dia, nc, clr=clr):
                        g_score[nst_v] = ng_v
                        parent[nst_v] = st
                        heapq.heappush(open_pq, (ng_v + h_cost(x, y) * 1.15, ng_v, x, y, other_li))

        if found_goal is None:
            return False

        path = []
        curr = found_goal
        while curr in parent:
            path.append(curr)
            curr = parent[curr]
        path.append(curr)
        path.reverse()

        for pt in path[::2]:
            net_routed_nodes[nc].append(pt)
        net_routed_nodes[nc].append(path[-1])

        ox_start, oy_start, sw_start, mx_start, my_start = start_origins[path[0]]
        ox_end, oy_end, sw_end, mx_end, my_end = goal_map[found_goal]

        emit_stub(ox_start, oy_start, mx_start, my_start, path[0][0], path[0][1], LAYER_LIST[path[0][2]], sw_start)

        seg_start = path[0]
        for i in range(1, len(path)):
            prev = path[i - 1]
            cur = path[i]
            if cur[2] != prev[2]:
                if (seg_start[0], seg_start[1]) != (prev[0], prev[1]):
                    add_track(board, seg_start[0], seg_start[1], prev[0], prev[1], LAYER_LIST[prev[2]], width, nc)
                add_via(board, cur[0], cur[1], v_drill, v_dia, nc)
                seg_start = cur
            else:
                dx1 = prev[0] - seg_start[0]
                dy1 = prev[1] - seg_start[1]
                dx2 = cur[0] - prev[0]
                dy2 = cur[1] - prev[1]
                if abs(dx1 * dy2 - dy1 * dx2) > 1e-4:
                    add_track(board, seg_start[0], seg_start[1], prev[0], prev[1], LAYER_LIST[prev[2]], width, nc)
                    seg_start = prev
        if (seg_start[0], seg_start[1]) != (path[-1][0], path[-1][1]):
            add_track(board, seg_start[0], seg_start[1], path[-1][0], path[-1][1], LAYER_LIST[path[-1][2]], width, nc)

        emit_stub(ox_end, oy_end, mx_end, my_end, path[-1][0], path[-1][1], LAYER_LIST[path[-1][2]], sw_end)
        return True

    # 7. 4-Pass Ordered Routing:
    #    Pass 1: Short local signal connections (<15mm span) attached to U301, U401, U4, U201, U202, U203, U1 on a 100% via-free board
    #    Pass 2: Inter-zone MCU & control signal nets across F.Cu and unblocked B.Cu
    #    Pass 3: High-current nets (V_RAW_IN, V_FUSED, MOT_OUT1/2, SHUNT_SP, RLY1/2_NO/COM/NC)
    #    Pass 4 (LAST): SMD GND, +BATT, +5V, +3V3 plane fanout vias + A* fallback for any remaining power/GND pad
    high_current_nets = {
        "/Power_Supply/V_RAW_IN", "/Power_Supply/V_FUSED",
        "/DC_Motor_1/MOT_OUT1", "/DC_Motor_1/MOT_OUT2",
        "/DC_Motor_2/MOT_OUT1", "/DC_Motor_2/MOT_OUT2",
        "/DC_Motor_1/SHUNT_SP", "/DC_Motor_2/SHUNT_SP",
    }
    fine_ic_refs = {"U301", "U401", "U201", "U202", "U203", "U1", "F2", "F3", "F4"}

    pass1_tasks = []
    pass2_tasks = []
    pass3_tasks = []

    for nc, pad_list in nets_pads.items():
        net_name = pad_list[0]["net"]
        if net_name in ("/MCU_and_Encoders/USB_CONN_DP", "/MCU_and_Encoders/USB_CONN_DN"):
            continue
        if net_name in plane_nets:
            continue
        filtered_pads = [
            p for p in pad_list
            if not (p["ref"] in ("Q1", "Q301", "Q302", "Q303", "Q304", "Q401", "Q402", "Q403", "Q404") and p["num"] in ("1", "3"))
        ]
        if len(filtered_pads) < 2:
            continue
        xs = [p["x"] for p in filtered_pads]
        ys = [p["y"] for p in filtered_pads]
        span = (max(xs) - min(xs)) + (max(ys) - min(ys))
        is_hc = (net_name in high_current_nets) or (net_name.startswith("/Steppers_and_Relays/RLY") and any(k in net_name for k in ("_NO", "_COM", "_NC")))
        has_fine_ic = any(p["ref"] in fine_ic_refs for p in filtered_pads)

        if is_hc:
            drv_pads = [p for p in filtered_pads if p["ref"] in ("U301", "U401")]
            other_pads = [p for p in filtered_pads if p["ref"] not in ("U301", "U401")]
            if drv_pads and other_pads:
                dp = drv_pads[0]
                nearest_op = min(other_pads, key=lambda op: math.hypot(op["x"] - dp["x"], op["y"] - dp["y"]))
                d_span = abs(dp["x"] - nearest_op["x"]) + abs(dp["y"] - nearest_op["y"])
                pass1_tasks.append((d_span, nc, net_name, [dp, nearest_op]))
                pass3_tasks.append((span, nc, net_name, other_pads))
            else:
                pass3_tasks.append((span, nc, net_name, filtered_pads))
        elif net_name in ("/M1_PWM_EN", "/M2_PWM_EN"):
            drv_p = next((p for p in filtered_pads if p["ref"] in ("U301", "U401")), None)
            res_p = next((p for p in filtered_pads if p["ref"] in ("R204", "R205")), None)
            mcu_p = next((p for p in filtered_pads if p["ref"] == "U3"), None)
            if drv_p and res_p and mcu_p:
                pass1_tasks.append((8.0, nc, net_name, [drv_p, res_p]))
                pass2_tasks.append((-450.0 + span, nc, net_name, [mcu_p, res_p]))
            else:
                pass2_tasks.append((-450.0 + span, nc, net_name, filtered_pads))
        elif net_name in ("/M1_PWM_PH", "/M2_PWM_PH"):
            pass2_tasks.append((-500.0 + span, nc, net_name, filtered_pads))
        elif net_name in ("/MCU_and_Encoders/USB_DN", "/MCU_and_Encoders/USB_DP", "/M1_nFAULT", "/M2_nFAULT", "/M1_CS", "/M2_CS", "/MCU_and_Encoders/RS485_RX", "/MCU_and_Encoders/ENC1_B"):
            pass2_tasks.append((-350.0 + span, nc, net_name, filtered_pads))
        elif has_fine_ic and span < 22.0:
            pass1_tasks.append((span, nc, net_name, filtered_pads))
        else:
            prio = span - 100.0 if (net_name in ("/MCU_and_Encoders/ENC1_A", "/MCU_and_Encoders/ENC1_B", "/MCU_and_Encoders/ENC2_A", "/MCU_and_Encoders/ENC2_B", "/M1_PWM_PH", "/M2_PWM_PH", "/M1_nFAULT", "/M2_nFAULT", "/M1_CS", "/M2_CS")) else span
            pass2_tasks.append((prio, nc, net_name, filtered_pads))

    pass1_tasks.sort(key=lambda x: x[0])
    pass2_tasks.sort(key=lambda x: x[0])
    pass3_tasks.sort(key=lambda x: x[0])

    routed_connections = 0
    failed_connections = []

    def run_net_list(task_list, pass_label, force_thin=False):
        nonlocal routed_connections
        print(f"{pass_label}: routing {len(task_list)} nets...")
        for span, nc, net_name, plist in task_list:
            w, vd, vdia = get_net_width_and_via(net_name)
            if force_thin:
                w = min(w, 0.20)
                vd, vdia = 0.3, 0.6


            net_routed_nodes[nc].clear()
            best_pair = None
            best_d = 1e18
            for i in range(len(plist)):
                for j in range(i + 1, len(plist)):
                    d = math.hypot(plist[i]["x"] - plist[j]["x"], plist[i]["y"] - plist[j]["y"])
                    if d < best_d:
                        best_d = d
                        best_pair = (i, j)
            if best_pair is not None:
                conn = [plist[best_pair[0]]]
                unconn = [plist[k] for k in range(len(plist)) if k != best_pair[0]]
            else:
                conn = [plist[0]]
                unconn = plist[1:]

            while unconn:
                best_u = None
                best_d = 1e18
                for u in unconn:
                    d = min(math.hypot(u["x"] - c["x"], u["y"] - c["y"]) for c in conn)
                    if d < best_d:
                        best_d = d
                        best_u = u

                unconn.remove(best_u)
                touches_qfn = (best_u["ref"] in ("U301", "U401", "C310", "R310", "C410", "R410") or any(c["ref"] in ("U301", "U401") for c in conn) or net_name in ("/M1_PWM_EN", "/M2_PWM_EN"))
                touches_mcu = (best_u["ref"] in ("U3", "U4") or any(c["ref"] in ("U3", "U4") for c in conn))
                use_w = 0.20 if (touches_qfn or touches_mcu) else w
                if touches_qfn:
                    ok = route_two_pads_astar(nc, [best_u], conn, 0.20, 0.3, 0.6, grid_step=0.25, max_iter=70000, clr=0.15, use_routed_tree=True, allow_in2=False)
                else:
                    ok = route_two_pads_astar(nc, [best_u], conn, use_w, vd, vdia, grid_step=0.5, max_iter=25000, clr=(0.15 if touches_mcu else 0.18), use_routed_tree=True, allow_in2=False)
                    if not ok:
                        ok = route_two_pads_astar(nc, [best_u], conn, min(use_w, 0.20), 0.3, 0.6, grid_step=0.25, max_iter=60000, clr=0.15, use_routed_tree=True, allow_in2=False)
                if ok:
                    conn.append(best_u)
                    routed_connections += 1
                else:
                    failed_connections.append((nc, net_name, conn, best_u))

    net_routed_nodes.clear()
    run_net_list(pass1_tasks, "Pass 1 (Fine-Pitch Local Signals)", force_thin=True)
    run_net_list(pass2_tasks, "Pass 2 (Inter-Zone MCU & Control Signals)", force_thin=False)
    run_net_list(pass3_tasks, "Pass 3 (High-Current Motor & Relay Nets)", force_thin=False)

    # Pass 4 (LAST): Drop SMD GND, +BATT, +5V, +3V3 plane fanout vias + A* fallback
    for drv_ref in ("U301", "U401"):
        p25 = next((p for p in all_pads if p["ref"] == drv_ref and p["num"] == "25"), None)
        if not p25:
            continue
        cx_drv, cy_drv = p25["x"], p25["y"]
        p12 = next((p for p in all_pads if p["ref"] == drv_ref and p["num"] == "12"), None)
        if p12 and gnd_nc > 0 and p12["id"] not in connected_pad_ids:
            for vy_off in (2.25, 2.5, 2.75, 3.0):
                vy = round(cy_drv + vy_off, 3)
                if is_via_clear(p12["x"], vy, 0.6, gnd_nc, clr=0.16) and is_seg_clear(pcbnew.F_Cu, p12["x"], p12["y"], p12["x"], vy, 0.20, gnd_nc, clr=0.15, allow_same_fp_ref=drv_ref):
                    add_track(board, p12["x"], p12["y"], p12["x"], vy, pcbnew.F_Cu, 0.20, gnd_nc)
                    add_via(board, p12["x"], vy, 0.3, 0.6, gnd_nc)
                    connected_pad_ids.add(p12["id"])
                    break
        p1 = next((p for p in all_pads if p["ref"] == drv_ref and p["num"] == "1"), None)
        if p1 and batt_nc > 0 and p1["id"] not in connected_pad_ids:
            for vx_off in (-2.5, -2.75, -3.0, -3.25, -2.25):
                vx = round(cx_drv + vx_off, 3)
                if in_target_plane("+BATT", vx, p1["y"]) and is_via_clear(vx, p1["y"], 0.6, batt_nc, clr=0.16) and is_seg_clear(pcbnew.F_Cu, p1["x"], p1["y"], vx, p1["y"], 0.20, batt_nc, clr=0.15, allow_same_fp_ref=drv_ref):
                    add_track(board, p1["x"], p1["y"], vx, p1["y"], pcbnew.F_Cu, 0.20, batt_nc)
                    add_via(board, vx, p1["y"], 0.3, 0.6, batt_nc)
                    connected_pad_ids.add(p1["id"])
                    break
    dirs_16 = [(math.cos(i * math.pi / 8.0), math.sin(i * math.pi / 8.0)) for i in range(16)]
    radii = [0.65, 0.85, 1.1, 1.35, 1.65, 2.0, 2.4, 2.9, 3.4, 4.0, 4.6]
    fanout_count = 0

    for net_name in plane_nets:
        nc = net_map.get(net_name, -1)
        if nc <= 0:
            continue
        is_batt = (net_name == "+BATT")
        stub_w = 0.35 if is_batt else 0.25
        v_drill = 0.3
        v_dia = 0.6

        for p in nets_pads[nc]:
            if p["id"] in connected_pad_ids:
                continue
            if p["ref"] in ("Q1", "Q301", "Q302", "Q303", "Q304", "Q401", "Q402", "Q403", "Q404") and p["num"] in ("1", "3"):
                continue

            px, py = p["x"], p["y"]
            linked_local = False
            for other in nets_pads[nc]:
                if other["id"] in connected_pad_ids and other["id"] != p["id"] and in_target_plane(net_name, other["x"], other["y"]):
                    if math.hypot(px - other["x"], py - other["y"]) <= 2.2:
                        if is_seg_clear(pcbnew.F_Cu, px, py, other["x"], other["y"], stub_w, nc, clr=0.20, allow_same_fp_ref=p["ref"]):
                            add_track(board, px, py, other["x"], other["y"], pcbnew.F_Cu, stub_w, nc)
                            connected_pad_ids.add(p["id"])
                            fanout_count += 1
                            linked_local = True
                            break
            if linked_local:
                continue

            ordered_dirs = dirs_16
            if p["ref"] == "U3":
                cx_u3, cy_u3 = 102.0, 62.5
                ordered_dirs = sorted(dirs_16, key=lambda d: -((cx_u3 - px) * d[0] + (cy_u3 - py) * d[1]))

            placed = False
            for r in radii:
                if placed:
                    break
                for dx, dy in ordered_dirs:
                    vx = round((px + dx * r) * 20.0) / 20.0
                    vy = round((py + dy * r) * 20.0) / 20.0
                    if not in_target_plane(net_name, vx, vy):
                        continue
                    if is_via_clear(vx, vy, v_dia, nc, clr=0.22) and is_seg_clear(pcbnew.F_Cu, px, py, vx, vy, stub_w, nc, clr=0.20, allow_same_fp_ref=p["ref"]):
                        add_track(board, px, py, vx, vy, pcbnew.F_Cu, stub_w, nc)
                        add_via(board, vx, vy, v_drill, v_dia, nc)
                        connected_pad_ids.add(p["id"])
                        fanout_count += 1
                        placed = True
                        break

    print(f"Pass 4: Fanned out {fanout_count} power/GND SMD pads directly to planes.")

    # A* fallback for any power/GND pad that could not fit a local via
    for net_name in plane_nets:
        nc = net_map.get(net_name, -1)
        if nc <= 0:
            continue
        plist = [
            p for p in nets_pads[nc]
            if not (p["ref"] in ("Q1", "Q301", "Q302", "Q303", "Q304", "Q401", "Q402", "Q403", "Q404") and p["num"] in ("1", "3"))
        ]
        conn = [p for p in plist if p["id"] in connected_pad_ids]
        unconn = [p for p in plist if p["id"] not in connected_pad_ids]
        if not unconn:
            continue
        if not conn:
            conn = [unconn.pop(0)]
        while unconn:
            best_u = min(unconn, key=lambda u: min(math.hypot(u["x"] - c["x"], u["y"] - c["y"]) for c in conn))
            unconn.remove(best_u)
            ok = route_two_pads_astar(nc, [best_u], conn, 0.25, 0.3, 0.6, grid_step=0.5, max_iter=25000, clr=0.22, use_routed_tree=True)
            if not ok:
                ok = route_two_pads_astar(nc, [best_u], conn, 0.20, 0.3, 0.6, grid_step=0.25, max_iter=40000, clr=0.15, use_routed_tree=True, allow_in2=True)
            if ok:
                conn.append(best_u)
                routed_connections += 1
            else:
                failed_connections.append((nc, net_name, conn, best_u))

    # Final retry on 0.25mm grid with In2.Cu micro-underpass fallback (layer_factor = 10.0)
    if failed_connections:
        print(f"Retrying {len(failed_connections)} connections with In2.Cu micro-underpass fallback (layer_factor=10.0, clr=0.145)...")
        still_failed = []
        for nc, net_name, conn, best_u in failed_connections:
            targets = conn if conn else [p for p in nets_pads[nc] if p["id"] != best_u["id"]]
            ok = route_two_pads_astar(nc, [best_u], targets, 0.20, 0.3, 0.6, grid_step=0.25, max_iter=80000, clr=0.145, use_routed_tree=True, allow_in2=True)
            if ok:
                conn.append(best_u)
                routed_connections += 1
            else:
                still_failed.append((net_name, best_u["ref"], best_u["num"], best_u["x"], best_u["y"]))
        failed_connections = still_failed

    print(f"Routed {routed_connections} connections; {len(failed_connections)} remaining failed: {failed_connections}")

    # 8. Refill all copper zones
    print("Filling copper zones...")
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())

    pcbnew.SaveBoard(PCB_PATH, board)
    print(f"Saved routed board to {PCB_PATH}")

    # Run kicad-cli DRC
    print("Running kicad-cli DRC...")
    subprocess.run(["/usr/bin/kicad-cli", "pcb", "drc", "--format", "json", "--output", "drc.json", PCB_PATH], check=False)
    if os.path.exists("drc.json"):
        with open("drc.json") as f:
            drc = json.load(f)
        unconn_list = drc.get("unconnected_items", [])
        viols = drc.get("violations", [])
        by_type = defaultdict(int)
        for v in viols:
            by_type[v.get("type", "unknown")] += 1
        print(f"Unconnected count: {len(unconn_list)}")
        print(f"Violations by type: {dict(by_type)}")
        for u in unconn_list[:25]:
            items = [it.get("description", "") for it in u.get("items", [])]
            print("  UNCONN:", " -> ".join(items))
        for v in viols:
            if v.get("type") in ("shorting_items", "clearance", "solder_mask_bridge", "via_dangling", "track_dangling", "starved_thermal"):
                items = [it.get("description", "") for it in v.get("items", [])]
                print(f"  {v.get('type').upper()}: {v.get('description')} | {' -> '.join(items)}")

if __name__ == "__main__":
    main()
