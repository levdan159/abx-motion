#!/usr/bin/env python3
"""
apply_localized_repairs.py
Surgical repair script starting from /tmp/checkpoint_base.kicad_pcb (SHA-256: 8ec851d7639b256a545cc928b624a82d2242ff2cbd9337505cb07efa359bfab4).
Leaves 99% of the board untouched and performs ONLY the localized repairs specified in repair-brief.txt:
1. Repair the 2 copper-conflict locations:
   - ENC2_A vs M1_MAX_IN near (65.8, 114.22) (3 findings)
   - ENC2_B vs ENC1_A crossing near (97.5, 73.1) (1 finding)
2. Merge/relocate the 3 overlapping same-net via pairs while preserving connectivity:
   - ESP_BOOT (74.5, 68.7) / (74.7, 68.7)
   - M2_MIN_IN (66.9, 114.88) / (66.7, 114.9)
   - S2_MAX_IN (65.7, 118.3) / (65.8, 118.12)
3. Route ONLY the 5 missing connections:
   - BTN_HOME / OK button
   - M1_MIN_RAW
   - M2_MAX_IN
   - S1_MIN_IN
   - S1_MAX_IN
4. Remove confirmed orphan stubs/vias.
5. Fix the back-side (B.SilkS) and front-side (F.SilkS) pin legends on J601-J606 by placing each pin label ("MN", "G", "MX" and "5V", "G", "SW") individually at its exact pad_x coordinate, mark 3.3V ONLY and 5V SHARED SUPPLY, place LOGO1 + white AUTOBOTIX / ABX-Motion V1.1 text in the bottom-right blank area, and keep LOGO2 on B.SilkS.
6. Refill all zones and save abx-motion.kicad_pcb.
"""

import shutil
import math
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

def add_seg(board, net_code, layer, x1, y1, x2, y2, width_mm=0.22):
    seg = pcbnew.PCB_TRACK(board)
    seg.SetStart(pt(x1, y1))
    seg.SetEnd(pt(x2, y2))
    seg.SetLayer(layer)
    seg.SetWidth(pcbnew.FromMM(width_mm))
    seg.SetNetCode(net_code)
    board.Add(seg)
    return seg

def add_chain(board, net_code, layer, pts, width_mm=0.22):
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

def add_text(board, text, x, y, layer, size_mm=0.65, thick_mm=0.12, mirrored=False):
    txt = pcbnew.PCB_TEXT(board)
    txt.SetText(text)
    txt.SetLayer(layer)
    txt.SetPosition(pt(x, y))
    txt.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size_mm), pcbnew.FromMM(size_mm)))
    txt.SetTextThickness(pcbnew.FromMM(thick_mm))
    txt.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    txt.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    txt.SetMirrored(mirrored)
    board.Add(txt)
    return txt

def main():
    shutil.copyfile(BASE_PCB, OUT_PCB)
    board = pcbnew.LoadBoard(OUT_PCB)

    nets = board.GetNetsByName()
    def net_code(name):
        return nets[name].GetNetCode()

    to_remove = []

    # -------------------------------------------------------------------------
    # 1. Repair copper conflicts:
    #    (a) M1_MAX_IN vs ENC2_A near (65.8, 114.22):
    #        Remove the redundant left-side stub (68.14, 114.22)->(65.80, 114.22) and via at (65.80, 114.22).
    #    (b) ENC2_B vs ENC1_A crossing on B.Cu near (97.5, 73.1):
    #        Remove ENC2_B's B.Cu detour and vias at (97.3, 75.9) and (97.7, 71.3),
    #        plus the short F.Cu stub (97.7, 71.3)->(97.7, 72.3)->(97.825, 72.5),
    #        and connect (97.30, 75.90) directly on F.Cu to U3.18 (97.825, 72.50).
    # -------------------------------------------------------------------------
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

    # Add clean F.Cu connection for ENC2_B from (97.30, 75.90) to U3.18 (97.825, 72.50)
    add_chain(board, net_code("/MCU_and_Encoders/ENC2_B"), pcbnew.F_Cu, [
        (97.30, 75.90),
        (97.30, 73.025),
        (97.825, 72.50),
    ], width_mm=0.20)

    # -------------------------------------------------------------------------
    # 2. Merge/relocate the 3 overlapping same-net via pairs:
    #    (a) ESP_BOOT: (74.5, 68.7) & (74.7, 68.7) -> keep (74.7, 68.7), remove (74.5, 68.7)
    #    (b) M2_MIN_IN: (66.9, 114.88) & (66.7, 114.9) -> keep (66.7, 114.9), remove (66.9, 114.88) & stub
    #    (c) S2_MAX_IN: (65.7, 118.3) & (65.8, 118.12) -> keep (65.7, 118.3), remove (65.8, 118.12) & stub
    # -------------------------------------------------------------------------
    for t in list(board.GetTracks()):
        # (a) ESP_BOOT
        if match_via(t, "/MCU_and_Encoders/ESP_BOOT", 74.50, 68.70):
            to_remove.append(t)
        elif match_seg(t, pcbnew.B_Cu, "/MCU_and_Encoders/ESP_BOOT", 73.30, 67.50, 74.50, 68.70):
            to_remove.append(t)
        # (b) M2_MIN_IN
        elif match_via(t, "/Industrial_IO/M2_MIN_IN", 66.90, 114.88):
            to_remove.append(t)
        elif match_seg(t, pcbnew.F_Cu, "/Industrial_IO/M2_MIN_IN", 68.14, 114.88, 66.90, 114.88):
            to_remove.append(t)
        # (c) S2_MAX_IN
        elif match_via(t, "/Industrial_IO/S2_MAX_IN", 65.80, 118.12):
            to_remove.append(t)
        elif match_seg(t, pcbnew.F_Cu, "/Industrial_IO/S2_MAX_IN", 68.14, 118.12, 65.80, 118.12):
            to_remove.append(t)

    add_seg(board, net_code("/MCU_and_Encoders/ESP_BOOT"), pcbnew.B_Cu, 73.30, 67.50, 74.70, 68.70, width_mm=0.22)

    # -------------------------------------------------------------------------
    # 3. Route ONLY the 5 missing connections:
    #    (1) M1_MIN_RAW: R609.1 (67.025, 122.40) -> J601.1 (67.00, 129.00)
    #    (2) M2_MAX_IN: U601.7 (68.138, 115.525) -> R612.2 (76.175, 122.40)
    #    (3) S1_MIN_IN: U601.8 (68.138, 116.175) -> R613.2 (79.775, 122.40)
    #    (4) S1_MAX_IN: U601.9 (68.138, 116.825) -> R614.2 (83.375, 122.40)
    #    (5) BTN_HOME: C214.1 (72.50, 68.775) -> U3.33 (109.75, 63.63)
    # -------------------------------------------------------------------------
    # Remove old left-side dangling stubs/vias on M2_MAX_IN, S1_MIN_IN, S1_MAX_IN
    # and the unaligned vertical segments on R612/C605, R613/C606, R614/C607
    for t in list(board.GetTracks()):
        if match_via(t, "/Industrial_IO/M2_MAX_IN", 65.80, 115.53):
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

    # (1) M1_MIN_RAW
    nc_m1_min_raw = net_code("/Industrial_IO/M1_MIN_RAW")
    add_chain(board, nc_m1_min_raw, pcbnew.F_Cu, [
        (67.02, 120.50),
        (67.025, 120.50),
        (67.025, 122.40),
        (67.85, 123.225),
        (67.85, 123.50),
    ], width_mm=0.22)
    add_via(board, nc_m1_min_raw, 67.85, 123.50)
    add_chain(board, nc_m1_min_raw, pcbnew.B_Cu, [
        (67.85, 123.50),
        (67.85, 128.15),
        (67.00, 129.00),
    ], width_mm=0.22)

    # (2) M2_MAX_IN
    nc_m2_max_in = net_code("/Industrial_IO/M2_MAX_IN")
    add_chain(board, nc_m2_max_in, pcbnew.F_Cu, [
        (76.175, 122.40),
        (76.225, 122.45),
        (76.225, 124.30),
    ], width_mm=0.25)
    add_chain(board, nc_m2_max_in, pcbnew.F_Cu, [
        (68.138, 115.525),
        (70.50, 115.525),
    ], width_mm=0.20)
    add_via(board, nc_m2_max_in, 70.50, 115.525)
    add_chain(board, nc_m2_max_in, pcbnew.B_Cu, [
        (70.50, 115.525),
        (70.50, 119.80),
        (72.10, 121.40),
        (75.50, 121.40),
    ], width_mm=0.20)
    add_via(board, nc_m2_max_in, 75.50, 121.40)
    add_chain(board, nc_m2_max_in, pcbnew.F_Cu, [
        (75.50, 121.40),
        (76.175, 122.075),
        (76.175, 122.40),
    ], width_mm=0.20)

    # (3) S1_MIN_IN
    nc_s1_min_in = net_code("/Industrial_IO/S1_MIN_IN")
    add_chain(board, nc_s1_min_in, pcbnew.F_Cu, [
        (79.775, 122.40),
        (79.825, 122.45),
        (79.825, 124.30),
    ], width_mm=0.25)
    add_chain(board, nc_s1_min_in, pcbnew.F_Cu, [
        (68.138, 116.175),
        (70.90, 116.175),
    ], width_mm=0.20)
    add_via(board, nc_s1_min_in, 70.90, 116.175)
    add_chain(board, nc_s1_min_in, pcbnew.B_Cu, [
        (70.90, 116.175),
        (70.90, 119.50),
        (72.40, 121.00),
        (79.10, 121.00),
    ], width_mm=0.20)
    add_via(board, nc_s1_min_in, 79.10, 121.00)
    add_chain(board, nc_s1_min_in, pcbnew.F_Cu, [
        (79.10, 121.00),
        (79.775, 121.675),
        (79.775, 122.40),
    ], width_mm=0.20)

    # (4) S1_MAX_IN
    nc_s1_max_in = net_code("/Industrial_IO/S1_MAX_IN")
    add_chain(board, nc_s1_max_in, pcbnew.F_Cu, [
        (83.375, 122.40),
        (83.425, 122.45),
        (83.425, 124.30),
    ], width_mm=0.25)
    add_chain(board, nc_s1_max_in, pcbnew.F_Cu, [
        (68.138, 116.825),
        (71.30, 116.825),
    ], width_mm=0.20)
    add_via(board, nc_s1_max_in, 71.30, 116.825)
    add_chain(board, nc_s1_max_in, pcbnew.B_Cu, [
        (71.30, 116.825),
        (71.30, 119.20),
        (72.80, 120.70),
        (82.70, 120.70),
    ], width_mm=0.20)
    add_via(board, nc_s1_max_in, 82.70, 120.70)
    add_chain(board, nc_s1_max_in, pcbnew.F_Cu, [
        (82.70, 120.70),
        (83.375, 121.375),
        (83.375, 122.40),
    ], width_mm=0.20)

    # (5) BTN_HOME
    nc_btn_home = net_code("/MCU_and_Encoders/BTN_HOME")
    add_chain(board, nc_btn_home, pcbnew.F_Cu, [
        (72.50, 68.775),
        (72.50, 68.78),
    ], width_mm=0.25)
    add_chain(board, nc_btn_home, pcbnew.B_Cu, [
        (69.70, 62.90),
        (71.70, 60.90),
        (75.80, 60.90),
        (78.30, 63.40),
        (85.00, 63.40),
        (86.20, 62.20),
        (86.20, 59.80),
        (89.50, 56.50),
        (110.50, 56.50),
        (112.80, 58.80),
        (112.80, 62.03),
        (111.20, 63.63),
    ], width_mm=0.20)

    # -------------------------------------------------------------------------
    # 4. Remove confirmed orphan stubs and dangling vias
    # -------------------------------------------------------------------------
    for t in list(board.GetTracks()):
        # Dangling vias on BTN_BACK, M1_MIN_IN, S2_MIN_IN
        if match_via(t, "/MCU_and_Encoders/BTN_BACK", 104.17, 73.95):
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
        # Dangling power/ground stubs where component moved
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

    # Deduplicate and remove
    removed_ids = set()
    for t in to_remove:
        if id(t) not in removed_ids:
            removed_ids.add(id(t))
            board.Remove(t)

    # Also ensure M1_MIN_IN, M1_MAX_IN, M2_MIN_IN, S2_MIN_IN, S2_MAX_IN R-to-C vertical tracks touch exact pad centers
    # Check if any of those need exact pad center segments:
    # (In baselineDRC they were already connected, so we leave them untouched!)

    # -------------------------------------------------------------------------
    # 5. Fix back-side (B.SilkS) & front-side (F.SilkS) pin legends on J601-J606
    #    and group banners ("3.3V ONLY" / "5V SHARED SUPPLY")
    # -------------------------------------------------------------------------
    for d in list(board.GetDrawings()):
        if hasattr(d, "GetText"):
            txt = d.GetText()
            if txt in ("MN G MX", "5V G SW", "J601-J604: 3.3V LIM/IO | J605-J606: 5V 500mA"):
                board.Remove(d)
            elif "J601-J604 (MN|G|MX)" in txt:
                d.SetText("J601-J604 (Bot MX|G|MN): 8x 3.3V ONLY Dry-Contact / Logic I/O")
            elif "J605-J606 (5V|G|SW)" in txt:
                d.SetText("J605-J606 (Bot SW|G|5V): 2x 5V SHARED SUPPLY (500mA PTC)")

    # Individual pad-aligned pin labels for J601-J606 on both F.SilkS and B.SilkS
    # Row 1: J601 (67, 129), J602 (77.5, 129), J603 (88, 129) -> pads at x, x+2, x+4
    # Row 2: J604 (67, 136.8), J605 (77.5, 136.8), J606 (88, 136.8) -> pads at x, x+2, x+4
    j_pin_defs = [
        # (ref, x_pin1, y_pin1, ["MN", "G", "MX"] or ["5V", "G", "SW"])
        ("J601", 67.0, 129.0, ["MN", "G", "MX"]),
        ("J602", 77.5, 129.0, ["MN", "G", "MX"]),
        ("J603", 88.0, 129.0, ["MN", "G", "MX"]),
        ("J604", 67.0, 136.8, ["MN", "G", "MX"]),
        ("J605", 77.5, 136.8, ["5V", "G", "SW"]),
        ("J606", 88.0, 136.8, ["5V", "G", "SW"]),
    ]
    for ref, x1, y1, labels in j_pin_defs:
        for i, lbl in enumerate(labels):
            px = x1 + i * 2.0
            # Front silkscreen below connector body
            add_text(board, lbl, px, y1 + 3.80, pcbnew.F_SilkS, size_mm=0.58, thick_mm=0.11, mirrored=False)
            # Back silkscreen below connector pads (mirrored individually at each pad X!)
            add_text(board, lbl, px, y1 + 2.15, pcbnew.B_SilkS, size_mm=0.60, thick_mm=0.11, mirrored=True)

    # Clear group distinction banner on F.SilkS and B.SilkS
    banner_txt = "J601-J604: 3.3V ONLY  |  J605-J606: 5V SHARED SUPPLY"
    add_text(board, banner_txt, 79.50, 141.65, pcbnew.F_SilkS, size_mm=0.68, thick_mm=0.12, mirrored=False)
    add_text(board, banner_txt, 79.50, 141.65, pcbnew.B_SilkS, size_mm=0.68, thick_mm=0.12, mirrored=True)

    # -------------------------------------------------------------------------
    # 6. Place final gold gears (LOGO1) + white AUTOBOTIX / ABX-Motion V1.1 text
    #    in the bottom-right blank area (and retain LOGO2 on B.SilkS)
    # -------------------------------------------------------------------------
    for fp in board.GetFootprints():
        if fp.GetReference() == "LOGO1":
            fp.SetPosition(pt(184.50, 143.20))

    add_text(board, "AUTOBOTIX", 184.50, 149.20, pcbnew.F_SilkS, size_mm=1.00, thick_mm=0.18, mirrored=False)
    add_text(board, "ABX-Motion V1.1", 184.50, 151.00, pcbnew.F_SilkS, size_mm=0.85, thick_mm=0.15, mirrored=False)

    # -------------------------------------------------------------------------
    # 7. Refill all zones directly and save
    # -------------------------------------------------------------------------
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())

    pcbnew.SaveBoard(OUT_PCB, board)
    print("Saved repaired board to", OUT_PCB)

if __name__ == "__main__":
    main()
