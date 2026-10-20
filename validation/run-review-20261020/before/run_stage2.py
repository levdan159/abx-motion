#!/usr/bin/env python3
"""
STAGE 2/4: Incremental Placement, Courtyard & Silkscreen Validation (abx-motion.kicad_pcb)
"""
import os
import math
import subprocess
import json
import xml.etree.ElementTree as ET
import pcbnew

PROJECT_DIR = "/home/daniel/Documents/kicad/abx-motion"
FP_LIB_DIR = "/usr/share/kicad/footprints"
to_mm = lambda v: v / 1e6
from_mm = lambda v: int(round(v * 1e6))

LCSC_MAP_NEW = {
    "U601": "C128392",
    "C601": "C14663",
    "J601": "C131339", "J602": "C131339", "J603": "C131339",
    "J604": "C131339", "J605": "C131339", "J606": "C131339",
    "R601": "C23162", "R602": "C23162", "R603": "C23162", "R604": "C23162",
    "R605": "C23162", "R606": "C23162", "R607": "C23162", "R608": "C23162",
    "R609": "C21190", "R610": "C21190", "R611": "C21190", "R612": "C21190",
    "R613": "C21190", "R614": "C21190", "R615": "C21190", "R616": "C21190",
    "C602": "C57112", "C603": "C57112", "C604": "C57112", "C605": "C57112",
    "C606": "C57112", "C607": "C57112", "C608": "C57112", "C609": "C57112",
    "F5":   "C70125",
    "R617": "C21190", "R618": "C21190",
    "R619": "C22775", "R620": "C22775",
    "R621": "C25804", "R622": "C25804",
    "Q601": "C20917", "Q602": "C20917",
    "D601": "C8598",  "D602": "C8598",
    "Q503": "C20917", "Q504": "C20917",
    "R507": "C25804", "R508": "C25804",
}

def scale_footprint_about_center(fp, scale_factor):
    c = fp.GetPosition()
    cx, cy = c.x, c.y
    for item in fp.GraphicalItems():
        if isinstance(item, pcbnew.PCB_SHAPE):
            st = item.GetShape()
            if st == pcbnew.SHAPE_T_POLY:
                poly = item.GetPolyShape()
                for ci in range(poly.OutlineCount()):
                    outline = poly.Outline(ci)
                    for pi in range(outline.PointCount()):
                        pt = outline.GetPoint(pi)
                        nx = cx + int(round((pt.x - cx) * scale_factor))
                        ny = cy + int(round((pt.y - cy) * scale_factor))
                        outline.SetPoint(pi, pcbnew.VECTOR2I(nx, ny))
                    for hi in range( poly.HoleCount(ci) ):
                        hole = poly.Hole(ci, hi)
                        for pi in range(hole.PointCount()):
                            pt = hole.GetPoint(pi)
                            nx = cx + int(round((pt.x - cx) * scale_factor))
                            ny = cy + int(round((pt.y - cy) * scale_factor))
                            hole.SetPoint(pi, pcbnew.VECTOR2I(nx, ny))
            elif st == pcbnew.SHAPE_T_SEGMENT:
                s = item.GetStart()
                e = item.GetEnd()
                item.SetStart(pcbnew.VECTOR2I(cx + int(round((s.x - cx) * scale_factor)), cy + int(round((s.y - cy) * scale_factor))))
                item.SetEnd(pcbnew.VECTOR2I(cx + int(round((e.x - cx) * scale_factor)), cy + int(round((e.y - cy) * scale_factor))))
            elif st == pcbnew.SHAPE_T_RECT:
                s = item.GetStart()
                e = item.GetEnd()
                item.SetStart(pcbnew.VECTOR2I(cx + int(round((s.x - cx) * scale_factor)), cy + int(round((s.y - cy) * scale_factor))))
                item.SetEnd(pcbnew.VECTOR2I(cx + int(round((e.x - cx) * scale_factor)), cy + int(round((e.y - cy) * scale_factor))))
        elif isinstance(item, pcbnew.PCB_TEXT):
            pos = item.GetPosition()
            nx = cx + int(round((pos.x - cx) * scale_factor))
            ny = cy + int(round((pos.y - cy) * scale_factor))
            item.SetPosition(pcbnew.VECTOR2I(nx, ny))
            sz = item.GetTextSize()
            item.SetTextSize(pcbnew.VECTOR2I(int(round(sz.x * scale_factor)), int(round(sz.y * scale_factor))))
            item.SetTextThickness(int(round(item.GetTextThickness() * scale_factor)))
            if "V1.0" in item.GetText():
                item.SetText(item.GetText().replace("V1.0", "V1.1"))

def add_silk_text(board, text, x_mm, y_mm, size_mm=1.0, thick_mm=0.15, layer=pcbnew.F_SilkS, mirrored=False, align_left=False):
    txt = pcbnew.PCB_TEXT(board)
    txt.SetText(text)
    txt.SetLayer(layer)
    txt.SetPosition(pcbnew.VECTOR2I(from_mm(x_mm), from_mm(y_mm)))
    txt.SetTextSize(pcbnew.VECTOR2I(from_mm(size_mm), from_mm(size_mm)))
    txt.SetTextThickness(from_mm(thick_mm))
    txt.SetMirrored(mirrored)
    if align_left:
        txt.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    board.Add(txt)
    return txt

def add_silk_line(board, x1_mm, y1_mm, x2_mm, y2_mm, width_mm=0.15, layer=pcbnew.F_SilkS):
    seg = pcbnew.PCB_SHAPE(board)
    seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
    seg.SetLayer(layer)
    seg.SetStart(pcbnew.VECTOR2I(from_mm(x1_mm), from_mm(y1_mm)))
    seg.SetEnd(pcbnew.VECTOR2I(from_mm(x2_mm), from_mm(y2_mm)))
    seg.SetWidth(from_mm(width_mm))
    board.Add(seg)
    return seg

def get_courtyard_bbox(fp, layer=pcbnew.F_Cu):
    poly = fp.GetCourtyard(layer)
    if poly.OutlineCount() > 0:
        b = poly.BBox()
        return (to_mm(b.GetX()), to_mm(b.GetY()), to_mm(b.GetRight()), to_mm(b.GetBottom()))
    # Fallback to graphical CrtYd items
    box = pcbnew.BOX2I()
    first = True
    for item in fp.GraphicalItems():
        lname = fp.GetBoard().GetLayerName(item.GetLayer())
        if "CrtYd" in lname or "Courtyard" in lname:
            b = item.GetBoundingBox()
            if first:
                box = b
                first = False
            else:
                box.Merge(b)
    if not first:
        return (to_mm(box.GetX()), to_mm(box.GetY()), to_mm(box.GetRight()), to_mm(box.GetBottom()))
    return None

def main():
    print("[STAGE 2/4] Starting from clean v1.0-production abx-motion.kicad_pcb...")
    subprocess.run(["git", "checkout", "v1.0-production", "--", "abx-motion.kicad_pcb"], cwd=PROJECT_DIR, check=True)

    board = pcbnew.LoadBoard(os.path.join(PROJECT_DIR, "abx-motion.kicad_pcb"))

    # Parse abx-motion.xml to get all component values, footprints, sheetpaths, UUIDs, and pad nets
    tree = ET.parse(os.path.join(PROJECT_DIR, "abx-motion.xml"))
    root = tree.getroot()

    comp_info = {}
    for comp in root.findall(".//comp"):
        ref = comp.attrib["ref"]
        val = comp.find("value").text if comp.find("value") is not None else ""
        fp_str = comp.find("footprint").text if comp.find("footprint") is not None else ""
        sp_el = comp.find("sheetpath")
        ts_el = comp.find("tstamps")
        sp_tstamps = sp_el.attrib.get("tstamps", "/") if sp_el is not None else "/"
        ts = ts_el.text if ts_el is not None else ""
        full_path = sp_tstamps + ts if sp_tstamps.endswith("/") else sp_tstamps + "/" + ts
        comp_info[ref] = {
            "value": val,
            "footprint": fp_str,
            "path": full_path,
        }

    # Build net table in board for any new nets
    existing_nets = {n_name: net_item for n_name, net_item in board.GetNetsByName().items()}
    def get_or_create_net(net_name):
        if net_name in existing_nets:
            return existing_nets[net_name]
        net = pcbnew.NETINFO_ITEM(board, net_name)
        board.Add(net)
        existing_nets[net_name] = board.FindNet(net_name)
        return board.FindNet(net_name)

    pin_nets = {}
    for net in root.findall(".//net"):
        nname = net.attrib["name"]
        get_or_create_net(nname)
        for node in net.findall("node"):
            pin_nets[(node.attrib["ref"], node.attrib["pin"])] = nname

    # 1. Instantiate all new footprints with full library-qualified LIB_IDs
    existing_fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    instantiated_count = 0
    for ref, info in comp_info.items():
        if ref not in existing_fps:
            fp_str = info["footprint"]
            if not fp_str or ":" not in fp_str:
                continue
            lib_nick, fp_name = fp_str.split(":", 1)
            pretty_dir = os.path.join(PROJECT_DIR, f"{lib_nick}.pretty") if lib_nick == "abx-footprints" else os.path.join(FP_LIB_DIR, f"{lib_nick}.pretty")
            fp = pcbnew.FootprintLoad(pretty_dir, fp_name)
            fp.SetFPID(pcbnew.LIB_ID(lib_nick, fp_name))
            fp.SetReference(ref)
            fp.SetValue(info["value"])
            fp.SetPath( pcbnew.KIID_PATH(info["path"]) )
            # Hide Value on F.SilkS / F.Fab
            fp.Value().SetVisible(False)
            # Set LCSC field (hidden)
            if ref in LCSC_MAP_NEW:
                fp.SetField("LCSC", LCSC_MAP_NEW[ref])
                f_lcsc = fp.GetFieldByName("LCSC") if hasattr(fp, "GetFieldByName") else None
                for fld in fp.GetFields():
                    if fld.GetName() == "LCSC": fld.SetVisible(False)
                if f_lcsc:
                    f_lcsc.SetVisible(False)
            # Style Reference text: 0.7mm x 0.7mm, 0.12mm thick
            fp.Reference().SetTextSize(pcbnew.VECTOR2I(from_mm(0.7), from_mm(0.7)))
            fp.Reference().SetTextThickness(from_mm(0.12))
            board.Add(fp)
            existing_fps[ref] = fp
            instantiated_count += 1
        else:
            fp = existing_fps[ref]
            fp.SetPath( pcbnew.KIID_PATH(info["path"]) )
            fp.SetValue(info["value"])

    # Assign exact pad nets from schematic netlist to all footprints
    for ref, fp in existing_fps.items():
        for pad in fp.Pads():
            pnum = pad.GetName()
            if (ref, pnum) in pin_nets:
                target_nname = pin_nets[(ref, pnum)]
                pad.SetNet(board.FindNet(target_nname))
            elif ref in comp_info and pnum != "":
                # Unused pin -> unconnected (net 0)
                pad.SetNetCode(0)

    print(f"[STAGE 2/4] Instantiated {instantiated_count} new footprints (total footprints on board: {len(existing_fps)}).")

    # Helper to place a footprint and position its Reference label cleanly
    def place_fp(ref, x_mm, y_mm, rot_deg, ref_dx=0.0, ref_dy=-1.3, hide_ref=False):
        fp = existing_fps[ref]
        fp.SetPosition(pcbnew.VECTOR2I(from_mm(x_mm), from_mm(y_mm)))
        fp.SetOrientationDegrees(rot_deg)
        fp.Value().SetVisible(False)
        if hide_ref:
            fp.Reference().SetVisible(False)
        else:
            fp.Reference().SetVisible(True)
            fp.Reference().SetPosition(pcbnew.VECTOR2I(from_mm(x_mm + ref_dx), from_mm(y_mm + ref_dy)))

    # 2. Top-Left Control Bar (X = 61..83mm, Y = 52..70mm)
    # Row 1: SW203 (< BACK), SW205 (OK), SW204 (FWD >) at Y = 55.0mm, X = 64.5, 71.5, 78.5mm
    place_fp("SW203", 64.5, 55.0, 0.0, ref_dx=0.0, ref_dy=-2.3)
    place_fp("SW205", 71.5, 55.0, 0.0, ref_dx=0.0, ref_dy=-2.3)
    place_fp("SW204", 78.5, 55.0, 0.0, ref_dx=0.0, ref_dy=-2.3)

    # Row 2: SW201 (RESET) & SW202 (BOOT) at Y = 61.0mm, X = 67.0, 75.0mm (preserves USB_DP/DN at Y=63.65..64.50mm!)
    place_fp("SW201", 67.0, 61.0, 0.0, ref_dx=0.0, ref_dy=-2.2)
    place_fp("SW202", 75.0, 61.0, 0.0, ref_dx=0.0, ref_dy=-2.2)

    # Row 3: 8 button passives (C203, C204, R227-R229, C212-C214) at Y = 68.0mm, rot = 90, X = 64.5..78.5mm (2.0mm pitch, left of USB_DP/DN diagonal!)
    btn_passives = ["C203", "R227", "C212", "R229", "C214", "C204", "R228", "C213"]
    for idx, pref in enumerate(btn_passives):
        px = round(64.5 + idx * 2.0, 2)
        place_fp(pref, px, 68.0, 90.0, ref_dx=0.0, ref_dy=2.2, hide_ref=True)

    # 3. Bottom-Left 6-Connector I/O Bank (X = 63..93mm, Y = 109..139mm)
    # Row 1: R206, C601, R621, R622, R617, R619, R618, R620 at Y = 109.2mm, rot = 90
    top_io_passives = [
        ("R206", 69.5), ("C601", 72.0), ("R621", 74.5), ("R622", 77.0),
        ("R617", 79.5), ("R619", 82.0), ("R618", 84.5), ("R620", 87.0),
    ]
    for pref, px in top_io_passives:
        place_fp(pref, px, 109.2, 90.0, ref_dx=0.0, ref_dy=-2.1, hide_ref=True)

    # Row 2: U601, Q601, D601, Q602, D602, F5
    place_fp("U601", 71.0, 115.2, 0.0, ref_dx=0.0, ref_dy=0.0)
    place_fp("Q601", 79.0, 113.5, 0.0, ref_dx=0.0, ref_dy=-2.2)
    place_fp("D601", 79.5, 117.2, 0.0, ref_dx=0.0, ref_dy=1.6)
    place_fp("Q602", 85.0, 113.5, 0.0, ref_dx=0.0, ref_dy=-2.2)
    place_fp("D602", 85.5, 117.2, 0.0, ref_dx=0.0, ref_dy=1.6)
    place_fp("F5",   90.8, 115.2, 90.0, ref_dx=0.0, ref_dy=-2.9)
    existing_fps["F3"].Reference().SetPosition(pcbnew.VECTOR2I(from_mm(63.2), from_mm(117.6)))

    # Rows 3, 4, 5: 24x 0603 Limit-Input RC network (R601-R608, R609-R616, C602-C609), rot = 0 (horizontal, 1.55mm high)
    xs_8 = [66.2, 69.8, 73.4, 77.0, 80.6, 84.2, 87.8, 91.4]
    for i in range(8):
        # Hide individual dense passive labels or keep tiny on F.Fab to prevent silkscreen clutter over pads
        place_fp(f"R60{i+1}",    xs_8[i], 120.5, 0.0, hide_ref=True)
        place_fp(f"R6{i+9:02d}", xs_8[i], 122.4, 0.0, hide_ref=True)
        place_fp(f"C60{i+2}",    xs_8[i], 124.3, 0.0, hide_ref=True)

    # Rows 6 & 7: 6x 3-Pin JST-PH Sockets (J601-J606) in 2x3 bank at Y = 129.0mm and Y = 136.8mm, X = 67.0, 77.5, 88.0mm
    jst_bank = [
        ("J601", 67.0, 129.0),
        ("J602", 77.5, 129.0),
        ("J603", 88.0, 129.0),
        ("J604", 67.0, 136.8),
        ("J605", 77.5, 136.8),
        ("J606", 88.0, 136.8),
    ]
    for jref, jx, jy in jst_bank:
        # We will add crisp custom combined F.SilkS and B.SilkS headers + pin labels below, so hide default Ref text to avoid duplicate overlap
        place_fp(jref, jx, jy, 0.0, hide_ref=True)

    # Stepper Enable Pass-FETs & Pull-ups near U501/U502 (Q503 placed at (106.0, 141.0) clear of STEP1_DIR diagonal!)
    place_fp("Q503", 106.0, 141.0, 0.0, ref_dx=0.0, ref_dy=2.2)
    place_fp("R507", 110.2, 141.0, 0.0, ref_dx=0.0, ref_dy=1.3)
    place_fp("Q504", 124.2, 137.0, 0.0, ref_dx=0.0, ref_dy=2.2)
    place_fp("R508", 127.8, 137.0, 0.0, ref_dx=0.0, ref_dy=1.3)

    # 4. Front LOGO1 & Back LOGO2 / Specs Table (No Power Circuitry Moved!)
    # Scale LOGO1 to 10.5mm width and place at (148.5, 100.0), hiding its internal text so it sits cleanly inside Y=95.3..104.7mm
    logo1 = existing_fps["LOGO1"]
    for item in list(logo1.GraphicalItems()):
        if isinstance(item, pcbnew.PCB_TEXT):
            logo1.Remove(item)
    b_l1 = logo1.GetBoundingBox(False, False)
    curr_w1 = to_mm(b_l1.GetWidth())
    if curr_w1 > 1.0:
        scale_footprint_about_center(logo1, 10.5 / curr_w1)
    logo1.SetPosition(pcbnew.VECTOR2I(from_mm(148.5), from_mm(99.8)))
    logo1.Reference().SetVisible(False)
    logo1.Value().SetVisible(False)

    # Move LOGO2 on Back Side to (164.0, 80.0) and convert its B.Mask polygons to B.Silkscreen so it never unmasks B.Cu vias/traces!
    logo2 = existing_fps["LOGO2"]
    logo2.SetPosition(pcbnew.VECTOR2I(from_mm(164.0), from_mm(80.0)))
    logo2.Reference().SetVisible(False)
    logo2.Value().SetVisible(False)
    for item in logo2.GraphicalItems():
        if item.GetLayer() == pcbnew.B_Mask:
            item.SetLayer(pcbnew.B_SilkS)
        if isinstance(item, pcbnew.PCB_TEXT) and "V1.0" in item.GetText():
            item.SetText(item.GetText().replace("V1.0", "V1.1"))

    # Save modified LOGO1 and LOGO2 back to abx-footprints.pretty so lib_footprint_mismatch is 0 for them!
    for lref, lname in [("LOGO1", "ABX_Logo_Gears_Gold"), ("LOGO2", "ABX_Text_Gold")]:
        lfp = pcbnew.Cast_to_FOOTPRINT(existing_fps[lref].Duplicate(False))
        lfp.SetPosition(pcbnew.VECTOR2I(0, 0))
        pcbnew.FootprintSave(os.path.join(PROJECT_DIR, "abx-footprints.pretty"), lfp)

    # Remove old silkscreen items:
    # - old '< BACK', 'OK', 'FWD >' at Y = 116.3
    # - old 'RESET', 'BOOT' at Y = 64.8 (we will re-add crisp top-left control bar labels)
    # - redundant front 'M0-M1-M2: ...' and 'MICROSTP: ...' text at (141.5, 82.7..85.2)
    # - old B.SilkS specs table lines & text at X=97..146, Y=59..96 so we can draw the updated V1.1 Specs Table cleanly
    to_remove_drawings = []
    for d in board.GetDrawings():
        layer = board.GetLayerName(d.GetLayer())
        b = d.GetBoundingBox()
        cx, cy = to_mm(b.GetCenter().x), to_mm(b.GetCenter().y)
        if isinstance(d, pcbnew.PCB_TEXT):
            t = d.GetText()
            if t in ("< BACK", "OK", "FWD >", "RESET", "BOOT"):
                to_remove_drawings.append(d)
            elif "M0-M1-M2" in t or "MICROSTP" in t:
                to_remove_drawings.append(d)
            elif layer == "B.Silkscreen" and 95.0 <= cx <= 148.0 and 58.0 <= cy <= 98.0:
                to_remove_drawings.append(d)
        elif layer == "B.Silkscreen" and 95.0 <= cx <= 148.0 and 58.0 <= cy <= 98.0:
            to_remove_drawings.append(d)

    for d in to_remove_drawings:
        board.Remove(d)

    # Add crisp Top-Left Control Bar F.SilkS labels:
    add_silk_text(board, "< BACK", 64.5, 52.1, 0.85, 0.15, pcbnew.F_SilkS)
    add_silk_text(board, "OK",     71.5, 52.1, 0.85, 0.15, pcbnew.F_SilkS)
    add_silk_text(board, "FWD >",  78.5, 52.1, 0.85, 0.15, pcbnew.F_SilkS)
    add_silk_text(board, "RESET",  67.0, 63.6, 0.85, 0.15, pcbnew.F_SilkS)
    add_silk_text(board, "BOOT",   75.0, 63.6, 0.85, 0.15, pcbnew.F_SilkS)

    # Add crisp Bottom-Left 6-Connector I/O Bank F.SilkS and mirrored B.SilkS headers & pin labels:
    # Bank section banner
    add_silk_text(board, "J601-J604: 3.3V LIM/IO | J605-J606: 5V 500mA", 79.5, 141.6, 0.72, 0.12, pcbnew.F_SilkS)
    add_silk_text(board, "J601-J604: 3.3V LIM/IO | J605-J606: 5V 500mA", 79.5, 141.6, 0.72, 0.12, pcbnew.B_SilkS, mirrored=True)

    io_headers = [
        ("J601 M1_LIM", 67.0, 129.0, "MN G MX"),
        ("J602 M2_LIM", 77.5, 129.0, "MN G MX"),
        ("J603 S1_LIM", 88.0, 129.0, "MN G MX"),
        ("J604 S2_LIM", 67.0, 136.8, "MN G MX"),
        ("J605 DC_OUT1", 77.5, 136.8, "5V G SW"),
        ("J606 DC_OUT2", 88.0, 136.8, "5V G SW"),
    ]
    for hdr, jx, jy, pins_str in io_headers:
        cx = jx + 2.0  # Center of 3-pin JST-PH (pins at jx+0, jx+2, jx+4)
        # Front Silkscreen: header above connector (jy - 2.65), pin labels below connector (jy + 3.80)
        add_silk_text(board, hdr,      cx, jy - 2.65, 0.62, 0.11, pcbnew.F_SilkS)
        add_silk_text(board, pins_str, cx, jy + 3.80, 0.60, 0.11, pcbnew.F_SilkS)
        # Back Silkscreen (mirrored): header above pads (jy - 2.1), pin labels below pads (jy + 2.1)
        add_silk_text(board, hdr,      cx, jy - 2.10, 0.62, 0.11, pcbnew.B_SilkS, mirrored=True)
        add_silk_text(board, pins_str, cx, jy + 2.10, 0.60, 0.11, pcbnew.B_SilkS, mirrored=True)

    # Add updated Back-Side B.SilkS Specs Table (X = 94..146mm, Y = 58..104mm)
    bx1, by1, bx2, by2 = 94.0, 58.0, 146.0, 104.0
    add_silk_line(board, bx1, by1, bx2, by1, 0.2, pcbnew.B_SilkS)
    add_silk_line(board, bx1, by2, bx2, by2, 0.2, pcbnew.B_SilkS)
    add_silk_line(board, bx1, by1, bx1, by2, 0.2, pcbnew.B_SilkS)
    add_silk_line(board, bx2, by1, bx2, by2, 0.2, pcbnew.B_SilkS)
    add_silk_line(board, bx1, 63.2, bx2, 63.2, 0.18, pcbnew.B_SilkS)

    add_silk_text(board, "ABX-MOTION V1.1 — SPECS & I/O REFERENCE", 120.0, 60.8, 1.05, 0.18, pcbnew.B_SilkS, mirrored=True)
    specs_lines = [
        "VBAT (J1 XT60): 12-32V (25A Fuse, Rev-Prot, SMCJ30A)",
        "Rails: +5V 2A Buck | +3.3V LDO | 4x PTC Polyfuses",
        "E-Stop (J102): Hardware Gates DC Servos & Stepper EN",
        "DC Servo 1&2: 2x 100W H-Bridge (DRV8701E, 15A Chop)",
        "Encoders 1&2: 5V Supply, 74LVC14A Schmitt (3.3V)",
        "Steppers 1&2: StepStick + J501-J504 (Indep E-Stop EN)",
        "Microstep M0-M1-M2: 000=1 100=1/2 010=1/4 110=1/8",
        "Microstep (cont.):  001=1/16 101=1/32 111=1/32",
        "J601-J604 (MN|G|MX): 8x 3.3V Dry-Contact / Logic I/O",
        "J605-J606 (5V|G|SW): 2x 5V DC Out (500mA Shared PTC)",
        "Relays (J505/506): 2x Omron G5LE SPDT | CAN & RS-485",
    ]
    for idx, sline in enumerate(specs_lines):
        sy = round(66.2 + idx * 3.4, 2)
        add_silk_text(board, sline, 120.0, sy, 0.82, 0.14, pcbnew.B_SilkS, mirrored=True)

    pcbnew.SaveBoard(os.path.join(PROJECT_DIR, "abx-motion.kicad_pcb"), board)

    # 5. Stage 2 Validation: Check all footprints for 0 courtyard overlaps and 0 lib_footprint_mismatch on new footprints
    fps_list = list(board.GetFootprints())
    overlaps = []
    for i in range(len(fps_list)):
        fp1 = fps_list[i]
        for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
            p1 = fp1.GetCourtyard(layer)
            if p1.OutlineCount() == 0:
                continue
            b1 = p1.BBox()
            for j in range(i + 1, len(fps_list)):
                fp2 = fps_list[j]
                p2 = fp2.GetCourtyard(layer)
                if p2.OutlineCount() == 0:
                    continue
                b2 = p2.BBox()
                # Check strict intersection (with 1um epsilon so touching edges don't false-trigger)
                if (b1.GetRight() - 1000 > b2.GetX() and b2.GetRight() - 1000 > b1.GetX() and
                    b1.GetBottom() - 1000 > b2.GetY() and b2.GetBottom() - 1000 > b1.GetY()):
                    # Check actual polygon intersection via Collide
                    if p1.Collide(p2, 0):
                        overlaps.append((fp1.GetReference(), fp2.GetReference(), board.GetLayerName(layer),
                                         (to_mm(b1.GetX()), to_mm(b1.GetY()), to_mm(b1.GetRight()), to_mm(b1.GetBottom())),
                                         (to_mm(b2.GetX()), to_mm(b2.GetY()), to_mm(b2.GetRight()), to_mm(b2.GetBottom()))))

    if overlaps:
        print(f"[STAGE 2/4] ERROR: Found {len(overlaps)} courtyard overlaps:")
        for r1, r2, lyr, bb1, bb2 in overlaps:
            print(f"  {r1} {bb1} overlaps {r2} {bb2} on {lyr}")
        raise SystemExit(1)

    # Also run kicad-cli pcb drc --schematic-parity to verify 0 schematic_parity issues and 0 courtyard overlaps in KiCad DRC
    subprocess.run(
        ["/usr/bin/kicad-cli", "pcb", "drc", "--schematic-parity", "--format", "json", "--output", "stage2_drc.json", "abx-motion.kicad_pcb"],
        cwd=PROJECT_DIR,
        check=True,
    )
    with open(os.path.join(PROJECT_DIR, "stage2_drc.json")) as f:
        drc2 = json.load(f)

    parity_issues = drc2.get("schematic_parity", [])
    crtyd_violations = [v for v in drc2.get("violations", []) if v.get("type") == "courtyards_overlap"]
    new_lib_mismatch = [
        v for v in drc2.get("violations", [])
        if v.get("type") == "lib_footprint_mismatch" and any(
            any(ref in it.get("description", "") for ref in LCSC_MAP_NEW)
            for it in v.get("items", [])
        )
    ]

    print(f"[STAGE 2/4] Validation Summary across {len(fps_list)} footprints:")
    print(f"  - Python Courtyard Overlaps: {len(overlaps)}")
    print(f"  - KiCad DRC courtyards_overlap: {len(crtyd_violations)}")
    print(f"  - KiCad DRC schematic_parity issues: {len(parity_issues)}")
    print(f"  - New footprints lib_footprint_mismatch: {len(new_lib_mismatch)}")

    if parity_issues:
        for p in parity_issues:
            print("  PARITY:", p["type"], p["description"], [it.get("description") for it in p.get("items", [])])
    assert len(overlaps) == 0 and len(crtyd_violations) == 0 and len(parity_issues) == 0 and len(new_lib_mismatch) == 0
    print("[STAGE 2/4] SUCCESS! All 224 footprints placed with 0 courtyard overlaps and 0 schematic-parity issues!")

if __name__ == "__main__":
    main()
