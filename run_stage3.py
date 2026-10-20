#!/usr/bin/env python3
"""
STAGE 3/4: Incremental Rip-Up, Obstacle-Aware Routing & DRC Closure (abx-motion.kicad_pcb)
"""
import os
import math
import heapq
import subprocess
import json
from collections import defaultdict
import pcbnew

PROJECT_DIR = "/home/daniel/Documents/kicad/abx-motion"
to_mm = lambda v: v / 1e6
from_mm = lambda v: int(round(v * 1e6))

def seg_dist_sq(px, py, x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return (px - x1)**2 + (py - y1)**2
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    cx = x1 + t * dx
    cy = y1 + t * dy
    return (px - cx)**2 + (py - cy)**2

def add_track(board, net, layer, x1_mm, y1_mm, x2_mm, y2_mm, width_mm=0.25):
    if abs(x1_mm - x2_mm) < 1e-4 and abs(y1_mm - y2_mm) < 1e-4:
        return None
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(from_mm(x1_mm), from_mm(y1_mm)))
    t.SetEnd(pcbnew.VECTOR2I(from_mm(x2_mm), from_mm(y2_mm)))
    t.SetWidth(from_mm(width_mm))
    t.SetLayer(layer)
    t.SetNet(net)
    board.Add(t)
    return t

def add_polyline(board, net, layer, pts_mm, width_mm=0.25):
    tracks = []
    for i in range(len(pts_mm) - 1):
        t = add_track(board, net, layer, pts_mm[i][0], pts_mm[i][1], pts_mm[i+1][0], pts_mm[i+1][1], width_mm)
        if t:
            tracks.append(t)
    return tracks

def add_via(board, net, x_mm, y_mm, drill_mm=0.3, size_mm=0.6):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(from_mm(x_mm), from_mm(y_mm)))
    v.SetDrill(from_mm(drill_mm))
    v.SetWidth(from_mm(size_mm))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(net)
    board.Add(v)
    return v

def main():
    print("[STAGE 3/4] Running Stage 2 placement baseline first...")
    subprocess.run(["python3", "run_stage2.py"], cwd=PROJECT_DIR, check=True)

    board = pcbnew.LoadBoard(os.path.join(PROJECT_DIR, "abx-motion.kicad_pcb"))
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}

    # 1. Strip ONLY tracks/vias that belonged to moved/modified nets OR any existing track/via that comes within 0.25mm of ANY pad/hole of a different net!
    strip_nets = {
        "/STEP_ENABLE",
        "/MCU_and_Encoders/BTN_BACK",
        "/MCU_and_Encoders/BTN_NEXT",
        "/MCU_and_Encoders/BTN_HOME",
        "/MCU_and_Encoders/ESP_EN",
        "/MCU_and_Encoders/ESP_BOOT",
        "/MCU_and_Encoders/ENC2_B",
        "/Steppers_and_Relays/STEP1_A1",
        "/Steppers_and_Relays/STEP1_A2",
        "/Steppers_and_Relays/STEP1_B1",
        "/Steppers_and_Relays/STEP1_B2",
        "/Industrial_IO/OUT1_SW",
    }

    # Collect all pad bounding boxes & holes for automatic 0.25mm collision check
    all_pads_info = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            pnet = p.GetNetname()
            bb = p.GetBoundingBox()
            px1, py1 = to_mm(bb.GetLeft()), to_mm(bb.GetTop())
            px2, py2 = to_mm(bb.GetRight()), to_mm(bb.GetBottom())
            lset = p.GetLayerSet()
            has_f = lset.Contains(pcbnew.F_Cu)
            has_b = lset.Contains(pcbnew.B_Cu)
            dr = 0.5 * to_mm(max(p.GetDrillSize().x, p.GetDrillSize().y))
            all_pads_info.append((pnet, px1, py1, px2, py2, has_f, has_b, dr > 0))

    def collides_with_any_pad(t_item):
        tnet = t_item.GetNetname()
        if isinstance(t_item, pcbnew.PCB_VIA):
            vx, vy = to_mm(t_item.GetPosition().x), to_mm(t_item.GetPosition().y)
            vr = 0.5 * to_mm(t_item.GetWidth(pcbnew.F_Cu)) + 0.25
            for pnet, px1, py1, px2, py2, has_f, has_b, is_hole in all_pads_info:
                if pnet == tnet:
                    continue
                if (px1 - vr) <= vx <= (px2 + vr) and (py1 - vr) <= vy <= (py2 + vr):
                    return True
            return False
        else:
            ln = board.GetLayerName(t_item.GetLayer())
            x1, y1 = to_mm(t_item.GetStart().x), to_mm(t_item.GetStart().y)
            x2, y2 = to_mm(t_item.GetEnd().x), to_mm(t_item.GetEnd().y)
            tr = 0.5 * to_mm(t_item.GetWidth()) + 0.25
            bx1, bx2 = min(x1, x2) - tr, max(x1, x2) + tr
            by1, by2 = min(y1, y2) - tr, max(y1, y2) + tr
            for pnet, px1, py1, px2, py2, has_f, has_b, is_hole in all_pads_info:
                if pnet == tnet:
                    continue
                if ln == "F.Cu" and not (has_f or is_hole):
                    continue
                if ln == "B.Cu" and not (has_b or is_hole):
                    continue
                if bx2 < px1 or bx1 > px2 or by2 < py1 or by1 > py2:
                    continue
                # Check segment distance to pad center/box
                pcx, pcy = 0.5 * (px1 + px2), 0.5 * (py1 + py2)
                prx, pry = 0.5 * (px2 - px1), 0.5 * (py2 - py1)
                if seg_dist_sq(pcx, pcy, x1, y1, x2, y2) <= (tr + max(prx, pry))**2:
                    return True
            return False

    to_delete = []
    for t in board.GetTracks():
        nname = t.GetNetname()
        if nname in strip_nets:
            to_delete.append(t)
            continue
        if collides_with_any_pad(t):
            to_delete.append(t)
            continue

        # Check old GND / +3V3 / +5V fanout stubs from moved components
        if isinstance(t, pcbnew.PCB_VIA):
            vx, vy = to_mm(t.GetPosition().x), to_mm(t.GetPosition().y)
            if nname in ("GND", "+3V3") and 65.0 <= vx <= 80.5 and 58.5 <= vy <= 63.2:
                to_delete.append(t)
            elif nname in ("GND", "+3V3") and 65.0 <= vx <= 94.0 and 107.5 <= vy <= 122.0:
                to_delete.append(t)
            elif nname == "+5V" and abs(vx - 65.0) < 0.2 and abs(vy - 116.0) < 0.2:
                to_delete.append(t)
        else:
            x1, y1 = to_mm(t.GetStart().x), to_mm(t.GetStart().y)
            x2, y2 = to_mm(t.GetEnd().x), to_mm(t.GetEnd().y)
            mx, my = 0.5 * (x1 + x2), 0.5 * (y1 + y2)
            if nname in ("GND", "+3V3") and 65.0 <= mx <= 80.5 and 58.5 <= my <= 63.2:
                to_delete.append(t)
            elif nname in ("GND", "+3V3") and 65.0 <= mx <= 94.0 and 107.5 <= my <= 122.0:
                to_delete.append(t)
            elif nname == "+5V" and 63.5 <= mx <= 65.5 and 115.5 <= my <= 122.6 and board.GetLayerName(t.GetLayer()) == "F.Cu":
                if max(x1, x2) > 63.90:
                    to_delete.append(t)

    for t in to_delete:
        if t in board.GetTracks():
            board.Remove(t)
    print(f"[STAGE 3/4] Incrementally removed {len(to_delete)} obsolete/colliding track/via items.")

    # 2. Update In2.Cu +3V3 and +5V zone boundary so +3V3 covers R601-R607 (X=65.38..86.98, Y=119.55..120.50)
    # while keeping (63.2..63.85, 122.4) and F5 Pad 1 (90.8, 116.6) inside +5V!
    for z in board.Zones():
        if board.GetLayerName(z.GetLayer()) == "In2.Cu":
            zn = z.GetNetname()
            poly = z.Outline()
            outline = poly.Outline(0)
            if zn == "+3V3":
                new_pts = [
                    (46.0, 49.0), (90.8, 49.0), (90.8, 53.6), (113.5, 53.6),
                    (113.5, 56.5), (128.5, 56.5), (128.5, 96.0), (132.0, 96.0),
                    (132.0, 130.5), (89.4, 130.5), (89.4, 114.6), (87.8, 114.6),
                    (87.8, 130.5), (69.5, 130.5), (69.5, 121.3), (64.6, 121.3),
                    (64.6, 116.5), (46.0, 116.5),
                ]
                outline.Clear()
                for px, py in new_pts:
                    outline.Append(from_mm(px), from_mm(py))
            elif zn == "+5V":
                new_pts = [
                    (46.0, 117.0), (64.2, 117.0), (64.2, 121.8), (69.0, 121.8),
                    (69.0, 131.0), (89.8, 131.0), (89.8, 115.2), (92.8, 115.2),
                    (92.8, 131.0), (132.5, 131.0), (132.5, 96.5), (135.0, 96.5),
                    (135.0, 70.5), (155.5, 70.5), (155.5, 116.5), (172.5, 116.5),
                    (172.5, 152.0), (46.0, 152.0),
                ]
                outline.Clear()
                for px, py in new_pts:
                    outline.Append(from_mm(px), from_mm(py))

    # 3. Route clean 0.50mm Stepper 1 Motor Coil Traces (STEP1_A2, STEP1_A1, STEP1_B1, STEP1_B2) around J603/J606
    add_polyline(board, board.FindNet("/Steppers_and_Relays/STEP1_A2"), pcbnew.B_Cu, [
        (100.50, 120.58), (94.00, 120.58), (94.00, 141.50), (84.50, 141.50), (84.50, 148.00)
    ], width_mm=0.50)

    add_polyline(board, board.FindNet("/Steppers_and_Relays/STEP1_A1"), pcbnew.F_Cu, [
        (100.50, 123.12), (94.20, 123.12), (94.20, 141.20), (82.00, 141.20), (82.00, 148.00)
    ], width_mm=0.50)

    add_polyline(board, board.FindNet("/Steppers_and_Relays/STEP1_B1"), pcbnew.F_Cu, [
        (100.50, 125.66), (95.10, 125.66), (95.10, 142.20), (87.00, 142.20), (87.00, 148.00)
    ], width_mm=0.50)

    add_polyline(board, board.FindNet("/Steppers_and_Relays/STEP1_B2"), pcbnew.F_Cu, [
        (100.50, 128.20), (96.00, 128.20), (96.00, 143.20), (89.50, 143.20), (89.50, 148.00)
    ], width_mm=0.50)

    # 4. Route Power/GND fanout vias for all new/moved components:
    net_gnd = board.FindNet("GND")
    net_3v3 = board.FindNet("+3V3")
    net_5v  = board.FindNet("+5V")

    for sx in (66.2, 73.2, 80.2):
        add_track(board, net_gnd, pcbnew.F_Cu, sx, 55.0, sx, 56.6, 0.25)
        add_via(board, net_gnd, sx, 56.6)
    for sx in (68.7, 76.7):
        add_track(board, net_gnd, pcbnew.F_Cu, sx, 61.0, sx, 59.5, 0.25)
        add_via(board, net_gnd, sx, 59.5)
    for cx in (64.5, 68.5, 72.5, 74.5, 78.5):
        add_track(board, net_gnd, pcbnew.F_Cu, cx, 67.22, cx, 65.90, 0.25)
        add_via(board, net_gnd, cx, 65.90)
    for rx in (66.5, 70.5, 76.5):
        add_track(board, net_3v3, pcbnew.F_Cu, rx, 68.83, rx, 70.00, 0.25)
        add_via(board, net_3v3, rx, 70.00)

    # Top I/O passives at Y=109.2: individual +3V3 vias
    add_track(board, net_3v3, pcbnew.F_Cu, 69.50, 110.03, 69.50, 110.80, 0.25)
    add_via(board, net_3v3, 69.50, 110.80)
    add_track(board, net_3v3, pcbnew.F_Cu, 72.00, 109.97, 72.00, 111.62, 0.25)
    add_track(board, net_3v3, pcbnew.F_Cu, 72.00, 111.62, 73.86, 111.62, 0.25)
    add_via(board, net_3v3, 72.00, 110.80)
    add_track(board, net_3v3, pcbnew.F_Cu, 74.50, 110.03, 74.50, 110.80, 0.25)
    add_via(board, net_3v3, 74.50, 110.80)
    add_track(board, net_3v3, pcbnew.F_Cu, 77.00, 110.03, 77.00, 110.80, 0.25)
    add_via(board, net_3v3, 77.00, 110.80)

    for gx, gy in [(72.0, 108.42), (79.5, 108.38), (84.5, 108.38)]:
        add_track(board, net_gnd, pcbnew.F_Cu, gx, gy, gx, 107.2, 0.25)
        add_via(board, net_gnd, gx, 107.2)

    # U601 GND pads:
    add_track(board, net_gnd, pcbnew.F_Cu, 68.14, 112.28, 68.14, 112.92, 0.25)
    add_track(board, net_gnd, pcbnew.F_Cu, 68.14, 112.60, 66.40, 112.60, 0.25)
    add_via(board, net_gnd, 66.40, 112.60)
    add_track(board, net_gnd, pcbnew.F_Cu, 68.14, 118.78, 66.40, 118.78, 0.25)
    add_via(board, net_gnd, 66.40, 118.78)
    add_track(board, net_gnd, pcbnew.F_Cu, 73.86, 113.58, 73.86, 115.53, 0.25)
    add_track(board, net_gnd, pcbnew.F_Cu, 73.86, 114.55, 75.50, 114.55, 0.25)
    add_via(board, net_gnd, 75.50, 114.55)

    for qx in (78.06, 84.06):
        add_track(board, net_gnd, pcbnew.F_Cu, qx, 114.45, qx, 115.65, 0.30)
        add_via(board, net_gnd, qx, 115.65)

    add_track(board, net_5v, pcbnew.F_Cu, 90.80, 116.60, 90.80, 118.00, 0.50)
    add_via(board, net_5v, 90.80, 118.00)
    add_polyline(board, net_5v, pcbnew.B_Cu, [(65.00, 116.00), (63.85, 117.15), (63.85, 122.40)], 0.50)

    xs_8 = [66.2, 69.8, 73.4, 77.0, 80.6, 84.2, 87.8, 91.4]
    for i in range(7):
        p1x = round(xs_8[i] - 0.82, 2)
        add_track(board, net_3v3, pcbnew.F_Cu, p1x, 120.50, p1x, 119.55, 0.25)
        add_via(board, net_3v3, p1x, 119.55)
    add_polyline(board, net_3v3, pcbnew.F_Cu, [(90.58, 120.50), (90.58, 119.55), (86.98, 119.55)], 0.25)

    for i in range(8):
        p2x = round(xs_8[i] + 0.78, 2)
        add_track(board, net_gnd, pcbnew.F_Cu, p2x, 124.30, p2x, 125.35, 0.25)
        add_via(board, net_gnd, p2x, 125.35)

    fps["R507"].SetOrientationDegrees(180.0)
    fps["R508"].SetOrientationDegrees(180.0)
    add_track(board, net_3v3, pcbnew.F_Cu, 111.03, 141.00, 111.80, 141.00, 0.25)
    add_via(board, net_3v3, 111.80, 141.00)
    add_polyline(board, net_3v3, pcbnew.B_Cu, [
        (111.80, 141.00), (111.00, 140.20), (111.00, 129.50)
    ], 0.25)
    add_via(board, net_3v3, 111.00, 129.50)
    add_polyline(board, net_3v3, pcbnew.F_Cu, [(128.62, 137.00), (128.62, 129.50)], 0.25)
    add_via(board, net_3v3, 128.62, 129.50)

    # 5. Direct Short Local Interconnects inside the 6-Connector I/O Bank:
    for i in range(8):
        r_ser = fps[f"R6{i+9:02d}"]
        r_ser.SetOrientationDegrees(180.0)
        raw_net = r_ser.FindPadByNumber("1").GetNet()
        in_net  = r_ser.FindPadByNumber("2").GetNet()
        rx_right = round(xs_8[i] + 0.82, 2)
        rx_left  = round(xs_8[i] - 0.82, 2)
        cx_left  = round(xs_8[i] - 0.78, 2)
        add_track(board, raw_net, pcbnew.F_Cu, rx_right, 120.50, rx_right, 122.40, 0.25)
        add_polyline(board, in_net, pcbnew.F_Cu, [(rx_left, 122.40), (cx_left, 122.45), (cx_left, 124.30)], 0.25)

    # Also route the 4 right-half U601 inputs (M2_MAX_IN Pad 7, S1_MIN_IN Pad 8, S1_MAX_IN Pad 9, S2_MIN_IN Pad 10, S2_MAX_IN Pad 11)
    # to staggered vias INSIDE U601's empty body (X=69.8..72.2, Y=115.53..118.12) so they have 100% open B.Cu access to R612..R616!
    u601_inner_vias = [
        ("/Industrial_IO/M2_MAX_IN", 115.53, 70.00, 115.53),
        ("/Industrial_IO/S1_MIN_IN", 116.17, 71.20, 116.17),
        ("/Industrial_IO/S1_MAX_IN", 116.83, 70.00, 116.83),
        ("/Industrial_IO/S2_MIN_IN", 117.47, 71.20, 117.47),
        ("/Industrial_IO/S2_MAX_IN", 118.12, 70.00, 118.12),
    ]
    for n_str, py_pad, vx_in, vy_in in u601_inner_vias:
        n_obj = board.FindNet(n_str)
        add_track(board, n_obj, pcbnew.F_Cu, 68.14, py_pad, vx_in, vy_in, 0.20)
        add_via(board, n_obj, vx_in, vy_in)

    # Auxiliary DC Output Gate networks:
    fps["R617"].SetOrientationDegrees(90.0)
    fps["R618"].SetOrientationDegrees(90.0)
    fps["R619"].SetOrientationDegrees(90.0)
    fps["R620"].SetOrientationDegrees(90.0)
    add_track(board, board.FindNet("/Industrial_IO/OUT1_CMD"), pcbnew.F_Cu, 79.50, 110.03, 82.00, 110.03, 0.25)
    add_track(board, board.FindNet("/Industrial_IO/OUT2_CMD"), pcbnew.F_Cu, 84.50, 110.03, 87.00, 110.03, 0.25)
    add_polyline(board, board.FindNet("/Industrial_IO/OUT1_GATE"), pcbnew.F_Cu, [
        (82.00, 108.38), (83.10, 108.38), (83.10, 111.50), (78.06, 111.50), (78.06, 112.55)
    ], 0.25)
    add_polyline(board, board.FindNet("/Industrial_IO/OUT2_GATE"), pcbnew.F_Cu, [
        (87.00, 108.38), (88.10, 108.38), (88.10, 111.50), (84.06, 111.50), (84.06, 112.55)
    ], 0.25)

    add_polyline(board, board.FindNet("/Industrial_IO/OUT1_SW"), pcbnew.F_Cu, [
        (79.94, 113.50), (81.15, 113.50), (81.15, 117.20)
    ], 0.40)
    add_polyline(board, board.FindNet("/Industrial_IO/OUT2_SW"), pcbnew.F_Cu, [
        (85.94, 113.50), (87.15, 113.50), (87.15, 117.20)
    ], 0.40)

    add_polyline(board, board.FindNet("/Industrial_IO/+5V_OUT"), pcbnew.F_Cu, [
        (90.80, 113.80), (88.80, 113.80), (88.80, 118.60), (83.85, 118.60), (83.85, 117.20)
    ], 0.50)
    add_polyline(board, board.FindNet("/Industrial_IO/+5V_OUT"), pcbnew.F_Cu, [
        (83.85, 118.60), (77.85, 118.60), (77.85, 117.20)
    ], 0.50)

    net_s1_gated = board.FindNet("/Steppers_and_Relays/STEP1_EN_GATED")
    add_track(board, net_s1_gated, pcbnew.F_Cu, 106.94, 141.00, 109.38, 141.00, 0.25)
    add_polyline(board, net_s1_gated, pcbnew.F_Cu, [
        (109.38, 141.00), (109.38, 135.80), (113.20, 135.80), (113.20, 133.28)
    ], 0.25)
    add_polyline(board, net_s1_gated, pcbnew.F_Cu, [
        (106.94, 141.00), (106.94, 150.10), (96.00, 150.10), (96.00, 148.00)
    ], 0.25)

    net_s2_gated = board.FindNet("/Steppers_and_Relays/STEP2_EN_GATED")
    add_track(board, net_s2_gated, pcbnew.F_Cu, 125.14, 137.00, 126.98, 137.00, 0.25)
    add_polyline(board, net_s2_gated, pcbnew.F_Cu, [
        (125.14, 137.00), (125.14, 142.50), (124.00, 143.64), (124.00, 148.00)
    ], 0.25)
    add_track(board, net_s2_gated, pcbnew.F_Cu, 126.98, 137.00, 126.98, 135.50, 0.25)
    add_via(board, net_s2_gated, 126.98, 135.50)
    add_polyline(board, net_s2_gated, pcbnew.B_Cu, [
        (126.98, 135.50), (131.48, 135.50), (133.70, 133.28)
    ], 0.25)

    add_polyline(board, board.FindNet("/MCU_and_Encoders/BTN_BACK"), pcbnew.F_Cu, [
        (66.50, 67.17), (67.35, 67.17), (67.35, 68.78), (68.50, 68.78)
    ], 0.25)
    add_polyline(board, board.FindNet("/MCU_and_Encoders/BTN_HOME"), pcbnew.F_Cu, [
        (70.50, 67.17), (71.35, 67.17), (71.35, 68.78), (72.50, 68.78)
    ], 0.25)
    add_polyline(board, board.FindNet("/MCU_and_Encoders/BTN_NEXT"), pcbnew.F_Cu, [
        (76.50, 67.17), (77.35, 67.17), (77.35, 68.78), (78.50, 68.78)
    ], 0.25)

    add_polyline(board, board.FindNet("/IO_INT_N"), pcbnew.F_Cu, [
        (69.50, 108.38), (68.14, 108.38), (68.14, 111.62)
    ], 0.25)

    # Escape vias for U3 Pad 23 (BTN_BACK at 104.17, 72.50) and C214 Pad 1 (BTN_HOME at 72.50, 68.78 -> via at 72.50, 70.00)
    add_track(board, board.FindNet("/MCU_and_Encoders/BTN_BACK"), pcbnew.F_Cu, 104.17, 72.50, 104.17, 73.95, 0.20)
    add_via(board, board.FindNet("/MCU_and_Encoders/BTN_BACK"), 104.17, 73.95)
    add_track(board, board.FindNet("/MCU_and_Encoders/BTN_HOME"), pcbnew.F_Cu, 109.75, 63.63, 111.20, 63.63, 0.20)
    add_via(board, board.FindNet("/MCU_and_Encoders/BTN_HOME"), 111.20, 63.63)
    add_track(board, board.FindNet("/MCU_and_Encoders/BTN_HOME"), pcbnew.F_Cu, 72.50, 68.78, 72.50, 70.00, 0.20)
    add_via(board, board.FindNet("/MCU_and_Encoders/BTN_HOME"), 72.50, 70.00)

    # First save and run DRC to get the exact list of remaining unconnected point-to-point pairs
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(os.path.join(PROJECT_DIR, "abx-motion.kicad_pcb"), board)

    subprocess.run([
        "/usr/bin/kicad-cli", "pcb", "drc",
        "--schematic-parity", "--format", "json",
        "--output", "drc_pre.json", "abx-motion.kicad_pcb"
    ], cwd=PROJECT_DIR, check=False)

    drc_pre = json.load(open(os.path.join(PROJECT_DIR, "drc_pre.json")))
    unconn = drc_pre.get("unconnected_items", [])
    print(f"[STAGE 3/4] Pre-router DRC Errors: {len([v for v in drc_pre.get('violations', []) if v.get('severity') == 'error'])} | Unconnected pairs to route: {len(unconn)}")

    # Build 2-Layer (F.Cu=0, B.Cu=1) Obstacle-Aware A* Grid Router
    X_MIN, X_MAX = 46.5, 138.0
    Y_MIN, Y_MAX = 49.5, 151.2
    STEP = 0.20
    NX = int(round((X_MAX - X_MIN) / STEP)) + 1
    NY = int(round((Y_MAX - Y_MIN) / STEP)) + 1

    gx_idx = lambda x: max(0, min(NX - 1, int(round((x - X_MIN) / STEP))))
    gy_idx = lambda y: max(0, min(NY - 1, int(round((y - Y_MIN) / STEP))))
    gx_mm = lambda ix: round(X_MIN + ix * STEP, 4)
    gy_mm = lambda iy: round(Y_MIN + iy * STEP, 4)

    buckets = [defaultdict(list), defaultdict(list)]
    pth_Master = []  # (cx, cy, drill_radius, net_str)

    def add_obs_box(layer_idx, net_s, x1, y1, x2, y2):
        item = ('box', net_s, (x1, y1, x2, y2))
        for bx in range(int(math.floor(x1 - 1.0)), int(math.ceil(x2 + 1.0)) + 1):
            for by in range(int(math.floor(y1 - 1.0)), int(math.ceil(y2 + 1.0)) + 1):
                buckets[layer_idx][(bx, by)].append(item)

    def add_obs_seg(layer_idx, net_s, x1, y1, x2, y2, r):
        item = ('seg', net_s, (x1, y1, x2, y2, r))
        bx1, bx2 = int(math.floor(min(x1, x2) - r - 1.0)), int(math.ceil(max(x1, x2) + r + 1.0))
        by1, by2 = int(math.floor(min(y1, y2) - r - 1.0)), int(math.ceil(max(y1, y2) + r + 1.0))
        for bx in range(bx1, bx2 + 1):
            for by in range(by1, by2 + 1):
                buckets[layer_idx][(bx, by)].append(item)

    def add_obs_cir(layer_idx, net_s, cx, cy, r):
        item = ('cir', net_s, (cx, cy, r))
        bx1, bx2 = int(math.floor(cx - r - 1.0)), int(math.ceil(cx + r + 1.0))
        by1, by2 = int(math.floor(cy - r - 1.0)), int(math.ceil(cy + r + 1.0))
        for bx in range(bx1, bx2 + 1):
            for by in range(by1, by2 + 1):
                buckets[layer_idx][(bx, by)].append(item)

    # Register all pads & holes
    for fp in board.GetFootprints():
        for p in fp.Pads():
            ns = p.GetNetname()
            bb = p.GetBoundingBox()
            x1, y1 = to_mm(bb.GetLeft()), to_mm(bb.GetTop())
            x2, y2 = to_mm(bb.GetRight()), to_mm(bb.GetBottom())
            lset = p.GetLayerSet()
            if lset.Contains(pcbnew.F_Cu):
                add_obs_box(0, ns, x1, y1, x2, y2)
            if lset.Contains(pcbnew.B_Cu):
                add_obs_box(1, ns, x1, y1, x2, y2)
            drill_r = 0.5 * to_mm(max(p.GetDrillSize().x, p.GetDrillSize().y))
            if drill_r > 0:
                cx, cy = to_mm(p.GetPosition().x), to_mm(p.GetPosition().y)
                pth_Master.append((cx, cy, drill_r, ns))
                if not lset.Contains(pcbnew.F_Cu):
                    add_obs_cir(0, ns, cx, cy, drill_r + 0.15)
                if not lset.Contains(pcbnew.B_Cu):
                    add_obs_cir(1, ns, cx, cy, drill_r + 0.15)

    # Register U3 antenna keepout on both layers
    add_obs_box(0, "__KEEPOUT__", 91.0, 48.0, 111.0, 55.6)
    add_obs_box(1, "__KEEPOUT__", 91.0, 48.0, 111.0, 55.6)

    # Register existing tracks and vias
    for t in board.GetTracks():
        ns = t.GetNetname()
        if isinstance(t, pcbnew.PCB_VIA):
            cx, cy = to_mm(t.GetPosition().x), to_mm(t.GetPosition().y)
            vr = 0.5 * to_mm(t.GetWidth(pcbnew.F_Cu))
            dr = 0.5 * to_mm(t.GetDrillValue())
            add_obs_cir(0, ns, cx, cy, vr)
            add_obs_cir(1, ns, cx, cy, vr)
            pth_Master.append((cx, cy, dr, ns))
        else:
            ln = board.GetLayerName(t.GetLayer())
            if ln in ("F.Cu", "B.Cu"):
                li = 0 if ln == "F.Cu" else 1
                x1, y1 = to_mm(t.GetStart().x), to_mm(t.GetStart().y)
                x2, y2 = to_mm(t.GetEnd().x), to_mm(t.GetEnd().y)
                tr = 0.5 * to_mm(t.GetWidth())
                add_obs_seg(li, ns, x1, y1, x2, y2, tr)

    def point_clear(li, net_s, px, py, radius, clr=0.20):
        b_key = (int(math.floor(px)), int(math.floor(py)))
        req = radius + clr
        for otype, ons, odata in buckets[li].get(b_key, ()):
            if ons == net_s:
                continue
            if otype == 'box':
                x1, y1, x2, y2 = odata
                if (x1 - req) <= px <= (x2 + req) and (y1 - req) <= py <= (y2 + req):
                    return False
            elif otype == 'cir':
                cx, cy, cr = odata
                if (px - cx)**2 + (py - cy)**2 < (req + cr)**2:
                    return False
            elif otype == 'seg':
                x1, y1, x2, y2, sr = odata
                if seg_dist_sq(px, py, x1, y1, x2, y2) < (req + sr)**2:
                    return False
        return True

    def via_clear(net_s, px, py):
        if not point_clear(0, net_s, px, py, 0.30, 0.20):
            return False
        if not point_clear(1, net_s, px, py, 0.30, 0.20):
            return False
        for cx, cy, dr, ons in pth_Master:
            if ons == net_s:
                continue
            if (px - cx)**2 + (py - cy)**2 < (0.15 + dr + 0.27)**2:
                return False
        return True

    def extract_net_name(desc):
        if "[" in desc and "]" in desc:
            return desc.split("[", 1)[1].split("]", 1)[0]
        return ""

    def infer_layer_mask(desc):
        if "PTH pad" in desc or "Via " in desc:
            return 3  # both F.Cu and B.Cu
        if "on B.Cu" in desc:
            return 2  # B.Cu
        return 1      # F.Cu

    def task_priority(net_s, d0, d1, dist):
        if net_s.endswith("_IN") and "/Industrial_IO/" in net_s:
            return (0, dist)
        if "of U601" in d0 or "of U601" in d1:
            return (1, dist)
        if "of U3" in d0 or "of U3" in d1:
            return (2, dist)
        return (3, dist)

    tasks = []
    for u in unconn:
        its = u.get("items", [])
        if len(its) < 2:
            continue
        p0, p1 = its[0]["pos"], its[1]["pos"]
        x0, y0 = p0["x"], p0["y"]
        x1, y1 = p1["x"], p1["y"]
        net_s = extract_net_name(its[0]["description"]) or extract_net_name(its[1]["description"])
        m0 = infer_layer_mask(its[0]["description"])
        m1 = infer_layer_mask(its[1]["description"])
        dist = math.hypot(x1 - x0, y1 - y0)
        prio = task_priority(net_s, its[0]["description"], its[1]["description"], dist)
        tasks.append((prio, dist, net_s, x0, y0, m0, x1, y1, m1, its[0]["description"], its[1]["description"]))

    tasks.sort(key=lambda item: item[0])

    DIRS = [
        (1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
        (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)
    ]

    routed_ok = 0
    failed_tasks = []

    for idx_t, (prio, dist, net_s, x0, y0, m0, x1, y1, m1, d0, d1) in enumerate(tasks):
        net_obj = board.FindNet(net_s)
        if net_s == "/Industrial_IO/+5V_OUT":
            w_mm = 0.50
        elif net_s in ("/Industrial_IO/OUT1_SW", "/Industrial_IO/OUT2_SW"):
            w_mm = 0.40
        else:
            w_mm = 0.22
        r_mm = 0.5 * w_mm

        sx, sy = gx_idx(x0), gy_idx(y0)
        tx, ty = gx_idx(x1), gy_idx(y1)

        pq = []
        g_score = {}
        parent = {}

        for li in (0, 1):
            if m0 & (1 << li):
                state = (li, sx, sy)
                g_score[state] = 0.0
                h = math.hypot(tx - sx, ty - sy)
                heapq.heappush(pq, (h, 0.0, state, 0, 0))

        goal_state = None
        max_expansions = 220000
        expansions = 0

        while pq and expansions < max_expansions:
            f, g, cur, pdx, pdy = heapq.heappop(pq)
            if g > g_score.get(cur, 1e18) + 1e-6:
                continue
            li, ix, iy = cur
            if ix == tx and iy == ty and (m1 & (1 << li)):
                goal_state = cur
                break
            expansions += 1

            px, py = gx_mm(ix), gy_mm(iy)

            # 1. Planar moves on same layer
            for dx, dy, step_cost in DIRS:
                nx, ny = ix + dx, iy + dy
                if not (0 <= nx < NX and 0 <= ny < NY):
                    continue
                npx, npy = gx_mm(nx), gy_mm(ny)
                near_start = ((npx - x0)**2 + (npy - y0)**2) <= 0.09
                near_goal  = ((npx - x1)**2 + (npy - y1)**2) <= 0.09
                if not (near_start or near_goal):
                    if not point_clear(li, net_s, npx, npy, r_mm, 0.20):
                        continue
                # Always check midpoint so a step into/out of a pad never crosses another net's pad!
                if not point_clear(li, net_s, 0.5 * (px + npx), 0.5 * (py + npy), r_mm, 0.18):
                    continue
                bend_pen = 0.15 if (pdx != 0 or pdy != 0) and (dx != pdx or dy != pdy) else 0.0
                ng = g + step_cost + bend_pen
                nstate = (li, nx, ny)
                if ng + 1e-6 < g_score.get(nstate, 1e18):
                    g_score[nstate] = ng
                    parent[nstate] = cur
                    h = math.hypot(tx - nx, ty - ny)
                    heapq.heappush(pq, (ng + 1.05 * h, ng, nstate, dx, dy))

            # 2. Layer transition via through-via
            oli = 1 - li
            nstate = (oli, ix, iy)
            via_pen = 14.0
            ng = g + via_pen
            if ng + 1e-6 < g_score.get(nstate, 1e18):
                if via_clear(net_s, px, py):
                    g_score[nstate] = ng
                    parent[nstate] = cur
                    h = math.hypot(tx - ix, ty - iy)
                    heapq.heappush(pq, (ng + 1.05 * h, ng, nstate, 0, 0))

        if goal_state is None:
            print(f"  [WARN] Could not route #{idx_t+1} {net_s}: ({x0:.2f},{y0:.2f}) -> ({x1:.2f},{y1:.2f})")
            failed_tasks.append((net_s, x0, y0, x1, y1, d0, d1))
            continue

        # Reconstruct path
        path = []
        cur = goal_state
        while cur in parent:
            path.append(cur)
            cur = parent[cur]
        path.append(cur)
        path.reverse()

        # Convert grid path to exact coordinates (snapping start and end to exact pad/track coordinates!)
        pts = []
        for idx_p, (li, ix, iy) in enumerate(path):
            if idx_p == 0:
                pts.append((li, x0, y0))
            elif idx_p == len(path) - 1:
                pts.append((li, x1, y1))
            else:
                pts.append((li, gx_mm(ix), gy_mm(iy)))

        # Emit segments and vias, and register them into the obstacle map immediately
        i_p = 0
        while i_p < len(pts) - 1:
            li0, px0, py0 = pts[i_p]
            li1, px1, py1 = pts[i_p + 1]
            if li0 != li1:
                # Via at (px0, py0)
                add_via(board, net_obj, px0, py0)
                add_obs_cir(0, net_s, px0, py0, 0.30)
                add_obs_cir(1, net_s, px0, py0, 0.30)
                pth_Master.append((px0, py0, 0.15, net_s))
                i_p += 1
            else:
                # Collinear run on layer li0
                j_p = i_p + 1
                while j_p + 1 < len(pts) and pts[j_p + 1][0] == li0:
                    dx1, dy1 = pts[j_p][1] - pts[j_p - 1][1], pts[j_p][2] - pts[j_p - 1][2]
                    dx2, dy2 = pts[j_p + 1][1] - pts[j_p][1], pts[j_p + 1][2] - pts[j_p][2]
                    if abs(dx1 * dy2 - dy1 * dx2) < 1e-4 and (dx1 * dx2 + dy1 * dy2) >= 0:
                        j_p += 1
                    else:
                        break
                ex, ey = pts[j_p][1], pts[j_p][2]
                layer_pcb = pcbnew.F_Cu if li0 == 0 else pcbnew.B_Cu
                add_track(board, net_obj, layer_pcb, px0, py0, ex, ey, w_mm)
                add_obs_seg(li0, net_s, px0, py0, ex, ey, r_mm)
                i_p = j_p

        routed_ok += 1

    print(f"[STAGE 3/4] A* Router routed {routed_ok}/{len(tasks)} point-to-point connections (failed: {len(failed_tasks)}).")

    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())

    pcbnew.SaveBoard(os.path.join(PROJECT_DIR, "abx-motion.kicad_pcb"), board)
    print("[STAGE 3/4] Saved routed abx-motion.kicad_pcb.")


if __name__ == "__main__":
    main()
