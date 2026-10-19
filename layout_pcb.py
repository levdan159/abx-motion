#!/usr/bin/env python3
"""
Ergonomic, Alligator-Clip & Routability 4-Layer PCB Layout for ABX-Motion
"""

import os
import subprocess
import pcbnew

PROJECT_DIR = "/home/daniel/Documents/kicad/abx-motion"
PCB_PATH = os.path.join(PROJECT_DIR, "abx-motion.kicad_pcb")


def fix_fp_lib_table():
    table_content = """(fp_lib_table
  (version 7)
  (lib (name "abx-footprints")(type "KiCad")(uri "${KIPRJMOD}/abx-footprints.pretty")(options "")(descr "ABX Custom Branding & Hardware Footprints"))
)
"""
    with open(os.path.join(PROJECT_DIR, "fp-lib-table"), "w", encoding="utf-8") as f:
        f.write(table_content)


def replace_footprint_preserve_nets(board: pcbnew.BOARD, old_fp: pcbnew.FOOTPRINT, lib_path: str, fp_name: str, lib_nickname: str):
    ref = old_fp.GetReference()
    val = old_fp.GetValue()
    path = old_fp.GetPath()
    pad_nets = {}
    for p in old_fp.Pads():
        pad_nets[p.GetNumber()] = p.GetNet()

    new_fp = pcbnew.FootprintLoad(lib_path, fp_name)
    new_fp.SetParent(board)
    new_fp.SetReference(ref)
    new_fp.SetValue(val)
    new_fp.SetPath(path)
    new_fp.SetFPID(pcbnew.LIB_ID(lib_nickname, fp_name))
    for p in new_fp.Pads():
        num = p.GetNumber()
        if num in pad_nets and pad_nets[num] is not None:
            p.SetNet(pad_nets[num])

    board.Delete(old_fp)
    board.Add(new_fp)
    return new_fp


def upgrade_testpoints_to_gold_edge_pads(board: pcbnew.BOARD, fps_by_ref: dict):
    tp_refs = ["TP_BATT1", "TP_5V1", "TP_3V3_1", "TP_GND1", "TP_GND2", "TP_CS1", "TP_CS2"]
    lset = pcbnew.LSET()
    for lyr in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu, pcbnew.F_Mask, pcbnew.B_Mask):
        lset.addLayer(lyr)

    for ref in tp_refs:
        if ref not in fps_by_ref:
            continue
        fp = fps_by_ref[ref]
        for p in fp.Pads():
            p.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
            p.SetShape(pcbnew.PAD_SHAPE_ROUNDRECT)
            p.SetRoundRectRadiusRatio(0.15)
            p.SetSize(pcbnew.VECTOR2I_MM(2.5, 3.6))
            p.SetDrillSize(pcbnew.VECTOR2I_MM(1.0, 1.0))
            p.SetLayerSet(lset)


def fix_3d_models(board: pcbnew.BOARD):
    model_fixes = {
        "J201": "${KICAD9_3DMODEL_DIR}/Connector_USB.3dshapes/USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal.step",
        "U1": "${KICAD9_3DMODEL_DIR}/Package_SO.3dshapes/Texas_HTSOP-8-1EP_3.9x4.9mm_P1.27mm_EP2.95x4.9mm_Mask2.4x3.1mm_ThermalVias.step",
        "L1": "${KICAD9_3DMODEL_DIR}/Inductor_SMD.3dshapes/L_Bourns_SRP6060FA.step",
        "F1": "${KICAD9_3DMODEL_DIR}/Fuse.3dshapes/Fuseholder_Blade_Mini_Keystone_3568.step",
    }
    pinsocket_model = "${KICAD9_3DMODEL_DIR}/Connector_PinSocket_2.54mm.3dshapes/PinSocket_1x08_P2.54mm_Vertical.step"

    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref in model_fixes:
            fp.Models().clear()
            m = pcbnew.FP_3DMODEL()
            m.m_Filename = model_fixes[ref]
            m.m_Show = True
            fp.Add3DModel(m)
        elif ref in ("U501", "U502"):
            fp.Models().clear()
            for col_x_mm in (0.0, 12.70):
                m = pcbnew.FP_3DMODEL()
                m.m_Filename = pinsocket_model
                m.m_Show = True
                m.m_Offset.x = col_x_mm
                m.m_Offset.y = 0.0
                m.m_Offset.z = 0.0
                fp.Add3DModel(m)


def get_fp_courtyard_polys(fp: pcbnew.FOOTPRINT):
    ref = fp.GetReference()
    if ref.startswith("TP_"):
        pos = fp.GetPosition()
        ps = pcbnew.SHAPE_POLY_SET()
        ps.NewOutline()
        x0 = pos.x - pcbnew.FromMM(1.4)
        x1 = pos.x + pcbnew.FromMM(1.4)
        y0 = pos.y - pcbnew.FromMM(1.9)
        y1 = pos.y + pcbnew.FromMM(1.9)
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            ps.Append(x, y)
        return ps
    if ref == "U3":
        pos = fp.GetPosition()
        ps = pcbnew.SHAPE_POLY_SET()
        ps.NewOutline()
        x0 = pos.x - pcbnew.FromMM(9.8)
        x1 = pos.x + pcbnew.FromMM(9.8)
        y0 = pos.y - pcbnew.FromMM(13.5)
        y1 = pos.y + pcbnew.FromMM(13.5)
        ps.Append(x0, y0)
        ps.Append(x1, y0)
        ps.Append(x1, y1)
        ps.Append(x0, y1)
        return ps
    if ref in ("J501", "J502", "J503", "J504"):
        pos = fp.GetPosition()
        ps = pcbnew.SHAPE_POLY_SET()
        ps.NewOutline()
        x0 = pos.x - pcbnew.FromMM(1.5)
        x1 = pos.x + pcbnew.FromMM(9.0)
        y0 = pos.y - pcbnew.FromMM(2.5)
        y1 = pos.y + pcbnew.FromMM(3.5)
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            ps.Append(x, y)
        return ps
    if ref in ("J505", "J506"):
        pos = fp.GetPosition()
        ps = pcbnew.SHAPE_POLY_SET()
        ps.NewOutline()
        x0 = pos.x - pcbnew.FromMM(2.6)
        x1 = pos.x + pcbnew.FromMM(12.8)
        y0 = pos.y - pcbnew.FromMM(5.0)
        y1 = pos.y + pcbnew.FromMM(4.5)
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            ps.Append(x, y)
        return ps
    if ref in ("K501", "K502"):
        pos = fp.GetPosition()
        ps = pcbnew.SHAPE_POLY_SET()
        ps.NewOutline()
        x0 = pos.x - pcbnew.FromMM(8.25)
        x1 = pos.x + pcbnew.FromMM(8.25)
        y0 = pos.y - pcbnew.FromMM(2.5)
        y1 = pos.y + pcbnew.FromMM(19.5)
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            ps.Append(x, y)
        return ps

    layer = pcbnew.B_Cu if fp.GetLayer() == pcbnew.B_Cu else pcbnew.F_Cu
    poly = fp.GetCourtyard(layer)
    if not poly.IsEmpty():
        return poly
    bb = fp.GetBoundingBox(False, False)
    ps = pcbnew.SHAPE_POLY_SET()
    ps.NewOutline()
    ps.Append(bb.GetLeft(), bb.GetTop())
    ps.Append(bb.GetRight(), bb.GetTop())
    ps.Append(bb.GetRight(), bb.GetBottom())
    ps.Append(bb.GetLeft(), bb.GetBottom())
    return ps


def check_all_overlaps(fps_by_ref: dict, margin_mm: float = 0.05):
    refs = sorted(fps_by_ref.keys())
    polys = {}
    bboxes = {}
    layers = {}
    for r in refs:
        fp = fps_by_ref[r]
        layers[r] = fp.GetLayer()
        ps = pcbnew.SHAPE_POLY_SET(get_fp_courtyard_polys(fp))
        if margin_mm > 0:
            ps.Inflate(pcbnew.FromMM(margin_mm / 2.0), pcbnew.CORNER_STRATEGY_ALLOW_ACUTE_CORNERS, pcbnew.FromMM(0.05))
        polys[r] = ps
        bboxes[r] = ps.BBox()

    overlaps = []
    for i in range(len(refs)):
        r1 = refs[i]
        b1 = bboxes[r1]
        for j in range(i + 1, len(refs)):
            r2 = refs[j]
            if layers[r1] != layers[r2]:
                continue
            b2 = bboxes[r2]
            if not b1.Intersects(b2):
                continue
            p_copy = pcbnew.SHAPE_POLY_SET(polys[r1])
            p_copy.BooleanIntersection(polys[r2])
            if not p_copy.IsEmpty() and p_copy.Area() > 0:
                ib = p_copy.BBox()
                overlaps.append((
                    r1,
                    r2,
                    round(ib.GetWidth() / 1e6, 2),
                    round(ib.GetHeight() / 1e6, 2),
                    (round(fps_by_ref[r1].GetPosition().x / 1e6, 2), round(fps_by_ref[r1].GetPosition().y / 1e6, 2)),
                    (round(fps_by_ref[r2].GetPosition().x / 1e6, 2), round(fps_by_ref[r2].GetPosition().y / 1e6, 2)),
                ))
    return overlaps


def add_line(board: pcbnew.BOARD, layer: int, x1: float, y1: float, x2: float, y2: float, width_mm: float = 0.15):
    seg = pcbnew.PCB_SHAPE(board)
    seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
    seg.SetLayer(layer)
    seg.SetStart(pcbnew.VECTOR2I_MM(x1, y1))
    seg.SetEnd(pcbnew.VECTOR2I_MM(x2, y2))
    seg.SetWidth(pcbnew.FromMM(width_mm))
    board.Add(seg)


def add_rect(board: pcbnew.BOARD, layer: int, x1: float, y1: float, x2: float, y2: float, width_mm: float = 0.15):
    add_line(board, layer, x1, y1, x2, y1, width_mm)
    add_line(board, layer, x2, y1, x2, y2, width_mm)
    add_line(board, layer, x2, y2, x1, y2, width_mm)
    add_line(board, layer, x1, y2, x1, y1, width_mm)


def add_text(
    board: pcbnew.BOARD,
    layer: int,
    text_str: str,
    x: float,
    y: float,
    size_mm: float = 1.0,
    thick_mm: float = 0.18,
    bold: bool = False,
    mirror: bool = False,
    rot_deg: float = 0.0,
    h_align: int = None,
):
    txt = pcbnew.PCB_TEXT(board)
    txt.SetLayer(layer)
    txt.SetText(text_str)
    txt.SetPosition(pcbnew.VECTOR2I_MM(x, y))
    txt.SetTextSize(pcbnew.VECTOR2I_MM(size_mm, size_mm))
    txt.SetTextThickness(pcbnew.FromMM(thick_mm))
    txt.SetBold(bold)
    txt.SetMirrored(mirror)
    txt.SetTextAngleDegrees(rot_deg)
    if h_align is not None:
        txt.SetHorizJustify(h_align)
    board.Add(txt)
    return txt


def draw_stepstick_silkscreen(board: pcbnew.BOARD, pin1_x: float, pin1_y: float, title: str):
    x_left = pin1_x - 1.45
    x_right = pin1_x + 12.70 + 1.45
    y_top = pin1_y - 1.6
    y_bot = pin1_y + 17.78 + 1.6
    add_rect(board, pcbnew.F_SilkS, x_left, y_top, x_right, y_bot, width_mm=0.22)

    add_text(board, pcbnew.F_SilkS, title, pin1_x + 6.35, pin1_y - 2.4, size_mm=0.75, thick_mm=0.14, bold=True)
    add_text(board, pcbnew.F_SilkS, "VMOT !", pin1_x + 6.35, pin1_y + 16.4, size_mm=0.7, thick_mm=0.14, bold=True)

    left_labels = ["GND", "FLT", "A2", "A1", "B1", "B2", "GND", "VM"]
    right_labels = ["DIR", "STP", "SLP", "RST", "M2", "M1", "M0", "EN"]

    for idx in range(8):
        py = pin1_y + idx * 2.54
        add_text(
            board,
            pcbnew.F_SilkS,
            left_labels[idx],
            pin1_x + 3.2,
            py,
            size_mm=0.68,
            thick_mm=0.12,
            bold=False,
        )
        add_text(
            board,
            pcbnew.F_SilkS,
            right_labels[idx],
            pin1_x + 6.35 + 2.8,
            py,
            size_mm=0.68,
            thick_mm=0.12,
            bold=False,
        )


def ensure_ptc_polyfuses(board: pcbnew.BOARD, fps_by_ref: dict):
    fuse_lib = "/usr/share/kicad/footprints/Fuse.pretty"
    fuse_fp_name = "Fuse_1206_3216Metric"
    net_by_name = {ni.GetNetname(): ni for _, ni in board.GetNetsByNetcode().items()}

    def get_or_create_net(net_name: str):
        if net_name in net_by_name:
            return net_by_name[net_name]
        ni = pcbnew.NETINFO_ITEM(board, net_name)
        board.Add(ni)
        net_by_name[net_name] = board.GetNetInfo().GetNetItem(net_name)
        return net_by_name[net_name]

    vbus_usb_net = get_or_create_net("/MCU_and_Encoders/VBUS_USB")
    vbus_fused_net = get_or_create_net("/MCU_and_Encoders/VBUS_FUSED")
    v5_net = get_or_create_net("+5V")
    v5_enc_net = get_or_create_net("/MCU_and_Encoders/+5V_ENC")
    v33_net = get_or_create_net("+3V3")
    v33_ext_net = get_or_create_net("/MCU_and_Encoders/+3V3_EXT")

    ptc_defs = [
        ("F2", "500mA_PTC", vbus_usb_net, vbus_fused_net),
        ("F3", "500mA_PTC", v5_net, v5_enc_net),
        ("F4", "250mA_PTC", v33_net, v33_ext_net),
    ]
    for f_ref, f_val, net1, net2 in ptc_defs:
        if f_ref in fps_by_ref:
            fp = fps_by_ref[f_ref]
        else:
            fp = pcbnew.FootprintLoad(fuse_lib, fuse_fp_name)
            fp.SetParent(board)
            fp.SetReference(f_ref)
            fp.SetFPID(pcbnew.LIB_ID("Fuse", fuse_fp_name))
            board.Add(fp)
            fps_by_ref[f_ref] = fp
        fp.SetValue(f_val)
        for p in fp.Pads():
            if p.GetNumber() == "1":
                p.SetNet(net1)
            elif p.GetNumber() == "2":
                p.SetNet(net2)

    if "D202" in fps_by_ref:
        for p in fps_by_ref["D202"].Pads():
            if p.GetNumber() == "2":
                p.SetNet(vbus_fused_net)
    for jref in ("J202", "J203"):
        if jref in fps_by_ref:
            for p in fps_by_ref[jref].Pads():
                if p.GetNumber() == "1":
                    p.SetNet(v5_enc_net)
    if "J209" in fps_by_ref:
        for p in fps_by_ref["J209"].Pads():
            if p.GetNumber() == "2":
                p.SetNet(v33_ext_net)


def main():
    fix_fp_lib_table()
    board = pcbnew.LoadBoard(PCB_PATH)

    # 1. Clean previous drawings, zones, tracks, and old LOGO1/LOGO2 instances
    for t in list(board.GetTracks()):
        board.Delete(t)
    for d in list(board.GetDrawings()):
        if d.GetLayer() in (pcbnew.Edge_Cuts, pcbnew.F_SilkS, pcbnew.B_SilkS, pcbnew.F_Fab, pcbnew.B_Fab):
            board.Delete(d)
    for z in list(board.Zones()):
        board.Delete(z)
    for fp in list(board.GetFootprints()):
        if fp.GetReference() in ("LOGO1", "LOGO2"):
            board.Delete(fp)

    # 2. Configure 4 Copper Layers & 150mm x 105mm Board Outline (X = 45..195, Y = 48..153)
    board.SetCopperLayerCount(4)
    board.GetDesignSettings().SetCopperLayerCount(4)
    add_rect(board, pcbnew.Edge_Cuts, 45.0, 48.0, 202.0, 153.0, width_mm=0.15)

    # 3. Replace J501-J504 with top-entry 4-pin shrouded JST-XH sockets (preserving nets)
    fps_by_ref = {fp.GetReference(): fp for fp in board.GetFootprints()}
    jst_lib = "/usr/share/kicad/footprints/Connector_JST.pretty"
    jst_name = "JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical"
    for jref in ("J501", "J502", "J503", "J504"):
        old_fp = fps_by_ref[jref]
        if str(old_fp.GetFPID().GetLibItemName()) != jst_name:
            fps_by_ref[jref] = replace_footprint_preserve_nets(board, old_fp, jst_lib, jst_name, "Connector_JST")

    # 3b. Upgrade TP_BATT1..TP_CS2 to Alligator-Clip Gold Edge Pads (2.5mm x 3.6mm PTH with 1.0mm drill)
    upgrade_testpoints_to_gold_edge_pads(board, fps_by_ref)
    ensure_ptc_polyfuses(board, fps_by_ref)

    # 4. Load updated LOGO1 (18mm Front Gold Badge) and LOGO2 (42mm Back Giant Gold Logo)
    lib_dir = os.path.join(PROJECT_DIR, "abx-footprints.pretty")
    for ref, fp_name in [("LOGO1", "ABX_Logo_Gears_Gold"), ("LOGO2", "ABX_Text_Gold")]:
        fp = pcbnew.FootprintLoad(lib_dir, fp_name)
        fp.SetParent(board)
        fp.SetReference(ref)
        fp.SetValue(fp_name)
        fp.SetFPID(pcbnew.LIB_ID("abx-footprints", fp_name))
        fp.SetAttributes(pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        board.Add(fp)
        fps_by_ref[ref] = fp

    # 5. Fix 3D model paths & attach dual PinSocket_1x08 3D female headers to U501 & U502
    fix_3d_models(board)

    # 6. Complete 196-Footprint Ergonomic, Alligator-Clip & Routability Placement
    placements = {
        # --- 4 Corner M3 Mounting Holes (4.5mm inset from 45..202 x 48..153) + 2 OLED M2 Support Holes ---
        "H1": (49.5, 52.5, 0),
        "H2": (197.5, 52.5, 0),
        "H3": (49.5, 148.5, 0),
        "H4": (197.5, 148.5, 0),
        "H5": (67.85, 105.30, 0),
        "H6": (91.15, 105.30, 0),

        # --- Front & Back Branding Logos ---
        "LOGO1": (79.5, 131.0, 0),     # Front 18mm Gold Badge centered on X=79.5 below < BACK | OK | FWD > buttons!
        "LOGO2": (77.5, 120.0, 0),     # Back 22mm Logo at (156.0, 68.0) on uninterrupted ground plate

        # =====================================================================
        # TOP EDGE ALLIGATOR-CLIP GOLD TEST PADS (X = 116.0..149.0mm, Y = 49.8mm)
        # =====================================================================
        "TP_BATT1": (116.0, 50.4, 0),
        "TP_5V1":   (121.5, 50.4, 0),
        "TP_3V3_1": (127.0, 50.4, 0),
        "TP_GND1":  (132.5, 50.4, 0),
        "TP_GND2":  (138.0, 50.4, 0),
        "TP_CS1":   (143.5, 50.4, 0),
        "TP_CS2":   (149.0, 50.4, 0),

        # =====================================================================
        # TOP-LEFT & LEFT EDGE: ESP32-S3, RESET/BOOT, USB-C, CAN, RS-485, Encoders
        # =====================================================================
        # U3 ESP32-S3-WROOM-1 at (101.0, 60.0) with >=5.0mm clear moat on all sides!
        "U3": (101.0, 60.0, 0),
        "C201": (85.0, 53.5, 0),
        "C202": (85.0, 56.2, 0),
        "R203": (85.0, 58.9, 0),

        "R230": (85.0, 61.8, 0),
        "LED203": (85.0, 64.5, 0),
        "R231": (85.0, 67.2, 0),
        "R232": (85.0, 69.8, 0),

        # Short-trace RESET (SW201) & BOOT (SW202) right between USB-C J201 and U3 (Y = 62.0mm)
        "SW201": (66.0, 62.0, 0),      # RESET
        "C203":  (66.0, 57.2, 0),
        "SW202": (77.0, 62.0, 0),      # BOOT
        "C204":  (77.0, 57.2, 0),

        # Left Edge Top-to-Bottom: USB-C J201 + Resettable PTC Polyfuse F2
        "J201": (49.5, 61.5, 270),
        "F2":   (58.0, 54.5, 0),
        "D202": (58.0, 58.0, 0),
        "U201": (58.0, 62.0, 0),
        "R201": (58.5, 65.5, 0),
        "R202": (58.5, 67.8, 0),

        # Left Edge Screw Terminals (rot=270 -> wire entry mouths face West / Outward off X=45!)
        "J205": (50.0, 71.0, 270),     # CAN screw terminal
        "U202": (60.0, 76.5, 0),
        "C210": (60.0, 72.0, 0),
        "J204": (61.0, 81.2, 90),
        "R219": (60.0, 84.8, 0),
        "R220": (66.5, 74.2, 0),
        "LED201": (66.5, 77.0, 0),

        "J207": (50.0, 88.0, 270),     # RS-485 screw terminal
        "D201": (59.5, 89.0, 0),
        "U203": (59.8, 95.0, 0),
        "C211": (59.5, 100.0, 0),
        "J206": (61.0, 104.2, 90),
        "R221": (57.5, 108.0, 0),
        "R222": (57.5, 110.4, 0),
        "R223": (57.5, 112.8, 0),
        "R224": (57.5, 115.2, 0),
        "LED202": (57.5, 117.8, 0),

        # Left Edge JST-XH Sockets: J209 (I2C_EXP + F4), J202 (ENC1 + F3), J203 (ENC2) at X=49.5, rot=270
        "J209": (49.5, 105.0, 270),
        "F4":   (63.2, 112.0, 90),
        "J202": (49.5, 119.5, 270),
        "F3":   (63.2, 121.0, 90),
        "J203": (49.5, 134.0, 270),

        # Encoder Schmitt Trigger U4 (74LVC14A) + RC Filters in clean lower-left bay (Y = 120..149mm, X <= 62.5 clear of LOGO1)
        "U4": (58.0, 125.0, 0),
        "C209": (62.0, 139.7, 0),
        "R211": (57.2, 132.5, 0),
        "R212": (57.2, 134.9, 0),
        "C205": (57.2, 137.3, 0),
        "R213": (57.2, 139.7, 0),
        "R214": (57.2, 142.1, 0),
        "C206": (57.2, 144.5, 0),
        "R215": (62.0, 132.5, 0),
        "R216": (62.0, 134.9, 0),
        "C207": (62.0, 137.3, 0),
        "R217": (62.0, 142.1, 0),
        "R218": (62.0, 144.5, 0),
        "C208": (62.0, 146.9, 0),

        # =====================================================================
        # FRONT-LEFT INTERACTIVE CONTROL PANEL: OLED (X=65.5..93.5, Y=79..107) & UI Buttons (Y=113.5)
        # =====================================================================
        "J208": (75.69, 81.5, 90),
        "R225": (75.5, 76.5, 0),
        "R226": (83.5, 76.5, 0),

        # UI Buttons at Y = 113.5mm (X = 68.0, 79.5, 91.0mm): SW203 (< BACK), SW205 (OK), SW204 (FWD >)
        "SW203": (68.0, 113.5, 0),     # < BACK
        "R227":  (68.0, 108.7, 0),
        "C212":  (68.0, 118.5, 0),

        "SW205": (79.5, 113.5, 0),     # OK
        "R229":  (79.5, 108.7, 0),
        "C214":  (79.5, 118.5, 0),

        "SW204": (91.0, 113.5, 0),     # FWD >
        "R228":  (91.0, 108.7, 0),
        "C213":  (91.0, 118.5, 0),

        # =====================================================================
        # MIDDLE-RIGHT ZONE: 5V Buck (U1), 3.3V LDO (U2) & Power LEDs (X = 132..155, Y = 60..96)
        # =====================================================================
        "C2": (132.5, 62.5, 0),
        "C3": (132.5, 66.0, 0),
        "C4": (132.5, 69.0, 0),
        "U1": (139.5, 65.0, 0),
        "C5": (139.5, 60.2, 0),
        "C6": (144.5, 60.2, 0),
        "L1": (149.0, 65.0, 0),
        "R4": (139.5, 70.0, 0),
        "R5": (144.5, 70.0, 0),
        "C7": (149.0, 72.5, 0),
        "C8": (149.0, 76.0, 0),

        "U2": (138.0, 78.5, 0),
        "C9": (132.5, 77.2, 0),
        "C10": (132.5, 80.2, 0),
        "R2": (144.0, 78.5, 0),
        "R3": (144.0, 81.2, 0),
        "C1": (149.0, 79.8, 0),

        # Power Status LEDs below Buck/LDO & Microstep Table (Y = 91..99mm)
        "R6": (132.0, 91.0, 0),
        "LED_PWR_BATT1": (137.0, 91.0, 0),
        "R7": (132.0, 95.0, 0),
        "LED_PWR_5V1": (137.0, 95.0, 0),
        "R8": (132.0, 99.0, 0),
        "LED_PWR_3V3_1": (137.0, 99.0, 0),

        # =====================================================================
        # RIGHT EDGE: High-Current Power & Dual 100W H-Bridges (X = 158..199mm)
        # =====================================================================
        "J1": (189.0, 53.5, 180),
        "F1": (162.0, 54.0, 0),
        "Q1": (165.0, 63.5, 0),
        "D1": (172.0, 62.5, 0),
        "R1": (172.0, 65.5, 0),
        "D2": (182.0, 63.5, 0),
        "J102": (197.0, 70.0, 90),     # E-Stop screw terminal on Right edge
        "R9": (188.5, 70.0, 0),

        # Mid-Right: DC Motor 1 (U301 at (165.0, 80.0) with >=3.5mm clear moat on all 4 sides!)
        "U301": (165.0, 80.0, 0),
        # LEFT of U301 (u_x - 5.5mm = 159.5, facing Pins 1-6):
        "C309": (159.5, 74.6, 0),
        "C301": (159.5, 77.3, 0),
        "C302": (159.5, 80.0, 0),
        "R301": (159.5, 82.7, 0),
        "R302": (159.5, 85.4, 0),
        # BOTTOM of U301 (>=4.5mm right of left column so R302 and C303 labels never touch!):
        "C303": (164.5, 85.8, 0),
        "C304": (164.5, 88.5, 0),
        "R209": (164.5, 91.2, 0),      # M1_nFAULT pull-up right at U301!
        "R304": (169.5, 85.8, 0),
        "R312": (168.5, 83.8, 0),      # Configurable 200k IDRIVE resistor right beside U301.12!
        "C305": (169.5, 88.5, 0),
        # RIGHT / TOP of U301 (facing Pins 13-24 toward Q301-Q304, spaced >=3.0mm vertically):
        "R303": (172.5, 87.2, 0),
        "R204": (172.5, 84.2, 0),      # M1_PWM_EN pull-down right at U301!
        "R305": (172.5, 81.2, 0),
        "R306": (172.5, 78.2, 0),
        "R308": (172.5, 75.2, 0),
        "R307": (166.5, 74.2, 0),
        # H-Bridge 1 MOSFETs & Bulk Caps
        "Q301": (178.5, 77.0, 0),
        "Q302": (178.5, 84.0, 0),
        "Q303": (186.5, 77.0, 0),
        "Q304": (186.5, 84.0, 0),
        "R309": (178.5, 90.5, 0),
        "C307": (186.5, 89.2, 0),
        "C308": (186.5, 92.2, 0),
        "C306": (185.0, 99.0, 0),
        "J301": (197.0, 89.0, 90),     # Motor 1 screw terminal on Right edge
        "R310": (197.0, 95.5, 0),
        "C310": (197.0, 98.5, 0),
        "LED_FLT1": (197.0, 101.5, 0),
        "R311": (197.0, 104.2, 0),

        # Lower-Right: DC Motor 2 (U401 at (165.0, 106.0) with >=3.5mm clear moat on all 4 sides!)
        "U401": (165.0, 106.0, 0),
        # LEFT of U401 (u_x - 5.5mm = 159.5, facing Pins 1-6):
        "C409": (159.5, 100.6, 0),
        "C401": (159.5, 103.3, 0),
        "C402": (159.5, 106.0, 0),
        "R401": (159.5, 108.7, 0),
        "R402": (159.5, 111.4, 0),
        # BOTTOM of U401 (>=4.5mm right of left column so R402 and C403 labels never touch!):
        "C403": (165.0, 111.8, 0),
        "C404": (165.0, 114.5, 0),
        "R210": (169.5, 117.2, 0),     # M2_nFAULT pull-up right at U401!
        "R404": (169.5, 111.8, 0),
        "R412": (168.2, 109.42, 0),    # Configurable 200k IDRIVE resistor right beside U401.12!
        "C405": (169.5, 114.5, 0),
        # RIGHT / TOP of U401 (facing Pins 13-24 toward Q401-Q404, spaced >=3.0mm vertically):
        "R403": (172.5, 113.2, 0),
        "R205": (172.5, 110.2, 0),     # M2_PWM_EN pull-down right at U401!
        "R405": (172.5, 107.2, 0),
        "R406": (172.5, 104.2, 0),
        "R408": (172.5, 101.2, 0),
        "R407": (166.5, 100.2, 0),
        # H-Bridge 2 MOSFETs & Bulk Caps
        "Q401": (178.5, 108.0, 0),
        "Q402": (178.5, 115.0, 0),
        "Q403": (186.5, 108.0, 0),
        "Q404": (186.5, 115.0, 0),
        "R409": (178.5, 121.5, 0),
        "C407": (186.5, 120.5, 0),
        "C408": (186.5, 123.8, 0),
        "C406": (185.0, 132.5, 0),
        "J401": (197.0, 119.0, 90),    # Motor 2 screw terminal on Right edge
        "R410": (197.0, 125.5, 0),
        "C410": (197.0, 128.5, 0),
        "LED_FLT2": (197.0, 131.5, 0),
        "R411": (197.0, 134.2, 0),

        # =====================================================================
        # BOTTOM-CENTER: StepStick 1 & 2 (U501 at 94,115.5; U502 at 115.5,115.5) + J501-J504
        # =====================================================================
        "J501": (82.0, 148.0, 0),
        "J502": (96.0, 148.0, 0),
        "J503": (110.0, 148.0, 0),
        "J504": (124.0, 148.0, 0),

        "U501": (100.5, 115.5, 0),
        "SW501": (100.5, 84.0, 0),
        "C501": (100.5, 97.5, 0),
        "R505": (109.5, 84.0, 0),
        "R206": (110.5, 97.5, 0),      # STEP_ENABLE pull-up right between U501 & U502!

        "U502": (121.0, 115.5, 0),
        "SW502": (121.0, 84.0, 0),
        "C502": (121.0, 97.5, 0),
        "R506": (129.5, 97.5, 0),

        # =====================================================================
        # BOTTOM-RIGHT: Dual 5V Relays (K501 at 146,127; K502 at 165,127) & J505, J506
        # =====================================================================
        "J505": (146.0, 148.0, 0),
        "J506": (165.0, 148.0, 0),

        "K501": (146.0, 122.0, 0),
        "K502": (165.0, 122.0, 0),

        # Relay 1 & 2 Drivers, Flyback Diodes, Pull-downs & LEDs above K501/K502
        "Q501": (140.0, 114.5, 0),
        "R501": (145.5, 115.2, 0),
        "R207": (145.5, 112.5, 0),     # RELAY_1 pull-down right at Q501!
        "D501": (140.0, 110.2, 0),
        "R502": (145.5, 109.8, 0),
        "D502": (140.0, 107.0, 0),

        "Q502": (155.5, 114.5, 0),
        "R503": (155.5, 110.2, 0),
        "R208": (150.5, 115.2, 0),     # RELAY_2 pull-down right at Q502!
        "D503": (150.5, 112.5, 0),
        "R504": (150.5, 109.8, 0),
        "D504": (150.5, 107.0, 0),

        # OLED M2 Mounting Holes (23.0mm horizontal pitch centered at X=79.5mm)
        "H5": (67.85, 105.30, 0),
        "H6": (91.15, 105.30, 0),
    }

    missing_refs = [r for r in fps_by_ref if r not in placements]
    assert not missing_refs, f"Missing placements for: {missing_refs}"

    # Update BOM values & DRV8701ERGER Pad 14=EN / Pad 15=PH nets on PCB
    for ref_v, val_v in [
        ("Q1", "SQJ459EP-T1_GE3"),
        ("D2", "SMCJ28A"),
        ("U3", "ESP32-S3-WROOM-1-N8R2"),
        ("U203", "THVD1450DR"),
        ("R222", "330R"),
        ("R223", "330R"),
        ("R309", "10mR_3W"),
        ("R409", "10mR_3W"),
        ("R312", "200k"),
        ("R412", "200k"),
    ]:
        if ref_v in fps_by_ref:
            fps_by_ref[ref_v].SetValue(val_v)
    net_lookup = {ni.GetNetname(): ni for _, ni in board.GetNetsByNetcode().items()}
    for u_ref, r_ref, en_net_name, ph_net_name in [
        ("U301", "R204", "/M1_PWM_EN", "/M1_PWM_PH"),
        ("U401", "R205", "/M2_PWM_EN", "/M2_PWM_PH"),
    ]:
        fp_u = fps_by_ref.get(u_ref)
        fp_r = fps_by_ref.get(r_ref)
        en_net = net_lookup.get(en_net_name)
        ph_net = net_lookup.get(ph_net_name)
        if fp_u and en_net and ph_net:
            for p in fp_u.Pads():
                if p.GetNumber() == "14":
                    p.SetNet(en_net)
                elif p.GetNumber() == "15":
                    p.SetNet(ph_net)
        if fp_r and en_net:
            for p in fp_r.Pads():
                if p.GetNumber() == "1":
                    p.SetNet(en_net)

    for ref, (px, py, rot) in placements.items():
        fp = fps_by_ref[ref]
        fp.SetPosition(pcbnew.VECTOR2I_MM(px, py))
        fp.SetOrientationDegrees(rot)

    if "J208" in fps_by_ref:
        j208_fp = fps_by_ref["J208"]
        pad_xs = [pcbnew.ToMM(p.GetPosition().x) for p in j208_fp.Pads()]
        pad_ys = [pcbnew.ToMM(p.GetPosition().y) for p in j208_fp.Pads()]
        dx_j208 = 79.5 - (sum(pad_xs) / len(pad_xs))
        dy_j208 = 81.5 - (sum(pad_ys) / len(pad_ys))
        cur_p = j208_fp.GetPosition()
        j208_fp.SetPosition(pcbnew.VECTOR2I_MM(pcbnew.ToMM(cur_p.x) + dx_j208, pcbnew.ToMM(cur_p.y) + dy_j208))

    # Verify strict 0-overlap 3D courtyard clearance
    overlaps = check_all_overlaps(fps_by_ref, margin_mm=0.05)
    print(f"Total footprints placed: {len(fps_by_ref)}, 3D Courtyard overlaps found: {len(overlaps)}")
    for ov in overlaps:
        print("  OVERLAP:", ov)
    assert len(overlaps) == 0, f"Found {len(overlaps)} courtyard overlaps!"

    # 7. StepStick Socket Outlines, Polarity Callouts & Inner Pin Labels (U501 & U502)
    draw_stepstick_silkscreen(board, 100.5, 115.5, "U501 STEPSTICK 1")
    draw_stepstick_silkscreen(board, 121.0, 115.5, "U502 STEPSTICK 2")

    # 7b. SW501 & SW502 Microstepping Slider Labels (M0, M1, M2) & Truth-Table Legend (F.SilkS)
    for sw_ref, sw_hdr in [
        ("SW501", "STEP 1 (<-ON)"),
        ("SW502", "STEP 2 (<-ON)"),
    ]:
        sw_fp = fps_by_ref[sw_ref]
        sw_fp.Reference().SetVisible(False)
        sw_pos = sw_fp.GetPosition()
        sw_x, sw_y = pcbnew.ToMM(sw_pos.x), pcbnew.ToMM(sw_pos.y)
        add_text(board, pcbnew.F_SilkS, sw_hdr, sw_x, sw_y - 6.4, size_mm=0.85, thick_mm=0.15, bold=True)
        pad_y_by_num = {p.GetNumber(): pcbnew.ToMM(p.GetPosition().y) for p in sw_fp.Pads()}
        for pnum, row_lbl in [("1", "M0"), ("2", "M1"), ("3", "M2")]:
            ry = pad_y_by_num[pnum]
            add_text(board, pcbnew.F_SilkS, row_lbl, sw_x - 6.8, ry, size_mm=0.75, thick_mm=0.14, bold=True)

    # Compact 2-Line Boxed Microstep Table on F.SilkS at X = 129.0..154.0mm, Y = 81.0..87.0mm
    add_rect(board, pcbnew.F_SilkS, 129.0, 81.0, 154.0, 87.0, width_mm=0.15)
    add_text(
        board,
        pcbnew.F_SilkS,
        "M0-M1-M2: 000=1/1  100=1/2  010=1/4",
        141.5,
        82.7,
        size_mm=0.66,
        thick_mm=0.12,
        bold=True,
    )
    add_text(
        board,
        pcbnew.F_SilkS,
        "MICROSTP: 110=1/8  001=1/16 111=1/32",
        141.5,
        85.2,
        size_mm=0.66,
        thick_mm=0.12,
        bold=True,
    )

    # 8. Add Front Ergonomic Silkscreen Labels & OLED 28x28mm Box
    # OLED 28x28mm module overhang outline (X = 65.5..93.5mm, Y = 79.0..107.0mm, centered on X = 79.5mm)
    add_rect(board, pcbnew.F_SilkS, 65.85, 79.50, 93.15, 107.30, width_mm=0.2)
    add_text(board, pcbnew.F_SilkS, "0.96 / 1.3 OLED MODULE", 79.5, 94.0, size_mm=1.15, thick_mm=0.2, bold=True)

    # UI Button Legends (0.90mm bold centered below SW203, SW205, SW204 at Y = 113.5mm)
    add_text(board, pcbnew.F_SilkS, "< BACK", 68.0, 116.3, size_mm=0.9, thick_mm=0.17, bold=True)
    add_text(board, pcbnew.F_SilkS, "OK", 79.5, 116.3, size_mm=0.9, thick_mm=0.17, bold=True)
    add_text(board, pcbnew.F_SilkS, "FWD >", 91.0, 116.3, size_mm=0.9, thick_mm=0.17, bold=True)

    # Short-Trace Reset & Boot Button Legends (centered below SW201, SW202 at Y = 62.0mm)
    add_text(board, pcbnew.F_SilkS, "RESET", 66.0, 64.8, size_mm=0.85, thick_mm=0.16, bold=True)
    add_text(board, pcbnew.F_SilkS, "BOOT", 77.0, 64.8, size_mm=0.85, thick_mm=0.16, bold=True)

    # Status LEDs clean 0.85mm F.SilkS labels
    led_silk_labels = [
        (141.2, 91.0, "+BATT"),
        (141.2, 95.0, "+5V"),
        (141.2, 99.0, "+3V3"),
        (81.2, 64.5, "STAT"),
        (70.2, 77.2, "CAN"),
        (53.2, 117.8, "485"),
        (192.5, 101.5, "M1 FLT"),
        (192.5, 131.5, "M2 FLT"),
        (140.0, 105.5, "RLY1"),
        (150.5, 105.5, "RLY2"),
    ]
    for lx, ly, ltxt in led_silk_labels:
        add_text(board, pcbnew.F_SilkS, ltxt, lx, ly, size_mm=0.82, thick_mm=0.15, bold=True)

    # Alligator-Clip Gold Edge Test Pad F.SilkS & B.SilkS Labels at Y = 53.5mm
    tp_silk_labels = [
        (116.0, 53.5, "+BATT"),
        (121.5, 53.5, "+5V"),
        (127.0, 53.5, "+3V3"),
        (132.5, 53.5, "GND1"),
        (138.0, 53.5, "GND2"),
        (143.5, 53.5, "CS1"),
        (149.0, 53.5, "CS2"),
    ]
    for tx, ty, ttxt in tp_silk_labels:
        add_text(board, pcbnew.F_SilkS, ttxt, tx, ty, size_mm=0.75, thick_mm=0.14, bold=True)
        add_text(board, pcbnew.B_SilkS, ttxt, tx, ty, size_mm=0.75, thick_mm=0.14, bold=True, mirror=True)

    def get_pad_coords(ref_name: str, pin_map: dict):
        fp = fps_by_ref[ref_name]
        out = []
        for p in fp.Pads():
            pnum = p.GetNumber()
            if pnum in pin_map:
                pos = p.GetPosition()
                out.append((int(pnum), pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y), pin_map[pnum]))
        out.sort(key=lambda item: item[0])
        return out

    # 8b. Per-Pad Alignment on Front-Side (F.SilkS) Edge Connectors
    j1_pads = get_pad_coords("J1", {"1": "+BATT", "2": "-GND"})
    for _, px, py, ptxt in j1_pads:
        add_text(board, pcbnew.F_SilkS, ptxt, px, 59.5, size_mm=0.75, thick_mm=0.14, bold=True)
    add_text(board, pcbnew.F_SilkS, "J1 XT60", sum(x for _, x, _, _ in j1_pads) / len(j1_pads), 61.5, size_mm=0.8, thick_mm=0.15, bold=True)

    for ref_name, hdr_txt, pin_map in [
        ("J205", "J205 CAN", {"1": "H", "2": "L", "3": "G"}),
        ("J207", "J207 485", {"1": "A", "2": "B", "3": "G"}),
    ]:
        pads = get_pad_coords(ref_name, pin_map)
        top_y = min(y for _, _, y, _ in pads)
        add_text(board, pcbnew.F_SilkS, hdr_txt, 49.5, top_y - 4.0, size_mm=0.72, thick_mm=0.13, bold=True)
        for _, px, py, ptxt in pads:
            add_text(board, pcbnew.F_SilkS, ptxt, 55.2, py, size_mm=0.72, thick_mm=0.13, bold=True)

    for ref_name, hdr_txt, pin_map in [
        ("J209", "J209 I2C", {"1": "G", "2": "3V", "3": "C", "4": "D"}),
        ("J202", "J202 ENC1", {"1": "5V", "2": "A", "3": "B", "4": "G"}),
        ("J203", "J203 ENC2", {"1": "5V", "2": "A", "3": "B", "4": "G"}),
    ]:
        pads = get_pad_coords(ref_name, pin_map)
        top_y = min(y for _, _, y, _ in pads)
        add_text(board, pcbnew.F_SilkS, hdr_txt, 49.5, top_y - 2.3, size_mm=0.68, thick_mm=0.12, bold=True)
        for _, px, py, ptxt in pads:
            add_text(board, pcbnew.F_SilkS, ptxt, 53.6, py, size_mm=0.65, thick_mm=0.12, bold=True)

    for ref_name, hdr_txt, x_off, pin_map in [
        ("J102", "J102 E-STOP", -5.8, {"1": "3V3", "2": "EN"}),
        ("J301", "J301 MOT1", -5.8, {"1": "M1+", "2": "M1-"}),
        ("J401", "J401 MOT2", -5.8, {"1": "M2+", "2": "M2-"}),
    ]:
        pads = get_pad_coords(ref_name, pin_map)
        top_y = min(y for _, _, y, _ in pads)
        add_text(board, pcbnew.F_SilkS, hdr_txt, 196.5, top_y - 4.2, size_mm=0.75, thick_mm=0.14, bold=True)
        for _, px, py, ptxt in pads:
            add_text(board, pcbnew.F_SilkS, ptxt, px + x_off, py, size_mm=0.72, thick_mm=0.13, bold=True)

    for ref_name, hdr_txt, pin_map in [
        ("J505", "J505 RLY1", {"1": "NO", "2": "COM", "3": "NC"}),
        ("J506", "J506 RLY2", {"1": "NO", "2": "COM", "3": "NC"}),
    ]:
        pads = get_pad_coords(ref_name, pin_map)
        for _, px, py, ptxt in pads:
            add_text(board, pcbnew.F_SilkS, ptxt, px, 142.3, size_mm=0.68, thick_mm=0.12, bold=True)

    for ref_name, hdr_txt, pin_map in [
        ("J501", "J501 STEP1", {"1": "A1", "2": "A2", "3": "B1", "4": "B2"}),
        ("J502", "J502 EXT1", {"1": "EN", "2": "PU", "3": "DR", "4": "G"}),
        ("J503", "J503 STEP2", {"1": "A1", "2": "A2", "3": "B1", "4": "B2"}),
        ("J504", "J504 EXT2", {"1": "EN", "2": "PU", "3": "DR", "4": "G"}),
    ]:
        pads = get_pad_coords(ref_name, pin_map)
        avg_x = sum(x for _, x, _, _ in pads) / len(pads)
        add_text(board, pcbnew.F_SilkS, hdr_txt, avg_x, 142.5, size_mm=0.68, thick_mm=0.12, bold=True)
        for _, px, py, ptxt in pads:
            add_text(board, pcbnew.F_SilkS, ptxt, px, 144.3, size_mm=0.60, thick_mm=0.11, bold=False)

    # 9. Add Back Silkscreen (B.SilkS, mirrored!) Boxed Specs Table at X = 98.0..146.0mm, Y = 60.0..96.0mm
    add_rect(board, pcbnew.B_SilkS, 98.0, 60.0, 146.0, 96.0, width_mm=0.25)
    add_line(board, pcbnew.B_SilkS, 98.0, 65.5, 146.0, 65.5, width_mm=0.2)
    add_text(
        board,
        pcbnew.B_SilkS,
        "ABX-MOTION V1.0 — SPECS & CONNECTIONS",
        122.0,
        62.8,
        size_mm=0.88,
        thick_mm=0.16,
        bold=True,
        mirror=True,
    )
    spec_rows_with_y = [
        (68.2, "VBAT (J1 XT60): 12-32V (25A Fuse, Rev-Prot, SMCJ28A)"),
        (71.8, "Rails: +5V 2A Buck | +3.3V LDO | 3x PTC Polyfuses"),
        (75.4, "E-Stop (J102): Loops +3V3 to +3V3_DRV_EN"),
        (79.0, "DC Servo 1&2: 2x 100W H-Bridge (DRV8701E, 15A)"),
        (82.6, "Encoders 1&2: 5V Supply, 74LVC14A Schmitt (3.3V)"),
        (86.2, "Steppers 1&2: StepStick (<=36V) + J501-J504"),
        (89.8, "Relays (J505/506): 2x Omron G5LE SPDT (10A)"),
        (93.4, "Buses: CAN (J205) | RS-485 (J207) | I2C OLED"),
    ]
    for ry, line_str in spec_rows_with_y:
        add_text(board, pcbnew.B_SilkS, line_str, 122.0, ry, size_mm=0.72, thick_mm=0.13, bold=False, mirror=True)

    # 9b. Per-Pad Coordinate Alignment on B.SilkS (Mirrored)
    for ref_name, hdr_txt, pin_map in [
        ("J205", "J205 CAN BUS", {"1": "H", "2": "L", "3": "GND"}),
        ("J207", "J207 RS-485", {"1": "A", "2": "B", "3": "GND"}),
        ("J209", "J209 I2C EXP", {"1": "GND", "2": "3V3", "3": "SCL", "4": "SDA"}),
        ("J202", "J202 ENC 1", {"1": "5V", "2": "A", "3": "B", "4": "GND"}),
        ("J203", "J203 ENC 2", {"1": "5V", "2": "A", "3": "B", "4": "GND"}),
    ]:
        pads = get_pad_coords(ref_name, pin_map)
        top_x = pads[0][1]
        top_y = min(y for _, _, y, _ in pads)
        add_text(board, pcbnew.B_SilkS, hdr_txt, top_x + 5.5, top_y - 2.2, size_mm=0.85, thick_mm=0.15, bold=True, mirror=True)
        for _, px, py, ptxt in pads:
            add_text(board, pcbnew.B_SilkS, ptxt, px + 4.5, py, size_mm=0.75, thick_mm=0.13, bold=False, mirror=True)

    for ref_name, hdr_txt, pin_map in [
        ("J102", "J102 E-STOP", {"1": "+3V3", "2": "DRV_EN"}),
        ("J301", "J301 MOTOR 1", {"1": "M1+", "2": "M1-"}),
        ("J401", "J401 MOTOR 2", {"1": "M2+", "2": "M2-"}),
    ]:
        pads = get_pad_coords(ref_name, pin_map)
        top_x = pads[0][1]
        top_y = min(y for _, _, y, _ in pads)
        add_text(board, pcbnew.B_SilkS, hdr_txt, top_x - 5.5, top_y - 2.5, size_mm=0.9, thick_mm=0.16, bold=True, mirror=True)
        for _, px, py, ptxt in pads:
            add_text(board, pcbnew.B_SilkS, ptxt, px - 5.5, py, size_mm=0.85, thick_mm=0.15, bold=False, mirror=True)

    for ref_name, hdr_txt, fsize, pin_map in [
        ("J505", "J505 RELAY 1", 0.72, {"1": "NO", "2": "COM", "3": "NC"}),
        ("J506", "J506 RELAY 2", 0.72, {"1": "NO", "2": "COM", "3": "NC"}),
        ("J501", "J501 STEP1", 0.62, {"1": "A1", "2": "A2", "3": "B1", "4": "B2"}),
        ("J502", "J502 EXT1", 0.62, {"1": "EN", "2": "PU", "3": "DR", "4": "G"}),
        ("J503", "J503 STEP2", 0.62, {"1": "A1", "2": "A2", "3": "B1", "4": "B2"}),
        ("J504", "J504 EXT2", 0.62, {"1": "EN", "2": "PU", "3": "DR", "4": "G"}),
    ]:
        pads = get_pad_coords(ref_name, pin_map)
        avg_x = sum(x for _, x, _, _ in pads) / len(pads)
        pad_y = pads[0][2]
        add_text(board, pcbnew.B_SilkS, hdr_txt, avg_x, pad_y - 5.0, size_mm=0.78, thick_mm=0.14, bold=True, mirror=True)
        for _, px, py, ptxt in pads:
            add_text(board, pcbnew.B_SilkS, ptxt, px, py - 2.6, size_mm=fsize, thick_mm=0.12, bold=False, mirror=True)

    j1_back_pads = get_pad_coords("J1", {"1": "+BATT", "2": "GND"})
    j1_avg_x = sum(x for _, x, _, _ in j1_back_pads) / len(j1_back_pads)
    j1_py = j1_back_pads[0][2]
    for _, px, py, ptxt in j1_back_pads:
        add_text(board, pcbnew.B_SilkS, ptxt, px, py + 4.2, size_mm=0.8, thick_mm=0.14, bold=False, mirror=True)
    add_text(board, pcbnew.B_SilkS, "J1 XT60 BATT", j1_avg_x, j1_py + 6.2, size_mm=0.85, thick_mm=0.15, bold=True, mirror=True)

    j208_back_pads = get_pad_coords("J208", {"1": "G", "2": "3V", "3": "C", "4": "D"})
    j208_avg_x = sum(x for _, x, _, _ in j208_back_pads) / len(j208_back_pads)
    j208_py = j208_back_pads[0][2]
    for _, px, py, ptxt in j208_back_pads:
        add_text(board, pcbnew.B_SilkS, ptxt, px, py - 2.2, size_mm=0.65, thick_mm=0.12, bold=False, mirror=True)
    add_text(board, pcbnew.B_SilkS, "J208 I2C OLED", j208_avg_x, j208_py - 4.2, size_mm=0.85, thick_mm=0.15, bold=True, mirror=True)

    # 10. Tidy Component Reference Designators
    fab_only_refs = {
        "LOGO1", "LOGO2",
        "SW201", "SW202", "SW203", "SW204", "SW205",
        "LED_PWR_BATT1", "LED_PWR_5V1", "LED_PWR_3V3_1",
        "LED201", "LED202", "LED203",
        "LED_FLT1", "LED_FLT2",
        "D502", "D504",
        "TP_BATT1", "TP_5V1", "TP_3V3_1", "TP_GND1", "TP_GND2", "TP_CS1", "TP_CS2",
        "U501", "U502", "SW501", "SW502",
        "J1", "J102", "J301", "J401",
        "J201", "J205", "J207", "J209", "J202", "J203",
        "J501", "J502", "J503", "J504", "J505", "J506",
    }

    for fp in board.GetFootprints():
        ref = fp.GetReference()
        fp.Value().SetVisible(False)
        ref_item = fp.Reference()

        if ref in ("LOGO1", "LOGO2", "SW501", "SW502"):
            ref_item.SetVisible(False)
            ref_item.SetLayer(pcbnew.F_Fab)
            continue

        if ref in fab_only_refs:
            ref_item.SetLayer(pcbnew.F_Fab)
            ref_item.SetTextSize(pcbnew.VECTOR2I_MM(0.65, 0.65))
            ref_item.SetTextThickness(pcbnew.FromMM(0.12))
            continue

        ref_item.SetLayer(pcbnew.F_SilkS)
        fpid = str(fp.GetFPID().GetLibItemName())
        pos = fp.GetPosition()
        px, py = pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)
        rot = fp.GetOrientationDegrees()

        if any(k in fpid for k in ("0603", "0805", "SOD-323", "SOT-23")):
            ref_item.SetTextSize(pcbnew.VECTOR2I_MM(0.62, 0.62))
            ref_item.SetTextThickness(pcbnew.FromMM(0.11))
            ref_item.SetTextAngleDegrees(0)
            if rot in (90.0, 270.0, -90.0):
                ref_item.SetPosition(pcbnew.VECTOR2I_MM(px, py - 1.9))
            else:
                ref_item.SetPosition(pcbnew.VECTOR2I_MM(px - 2.3, py))
        else:
            ref_item.SetTextSize(pcbnew.VECTOR2I_MM(0.68, 0.68))
            ref_item.SetTextThickness(pcbnew.FromMM(0.12))
            if ref == "U4":
                ref_item.SetPosition(pcbnew.VECTOR2I_MM(px, py + 5.2))
            elif ref == "D2":
                ref_item.SetPosition(pcbnew.VECTOR2I_MM(px, py + 3.8))
            elif ref == "U202":
                ref_item.SetPosition(pcbnew.VECTOR2I_MM(px + 2.8, py - 2.2))
        if ref in ("R221", "R311", "C203", "C204", "R304", "C305", "R404", "C405",
                   "R303", "R204", "R305", "R306", "R308", "R403", "R205", "R405", "R406", "R408"):
            ref_item.SetPosition(pcbnew.VECTOR2I_MM(px, py - 1.25))
        elif ref in ("R307", "R407"):
            ref_item.SetPosition(pcbnew.VECTOR2I_MM(px, py - 1.25))
        elif ref == "C210":
            ref_item.SetPosition(pcbnew.VECTOR2I_MM(px - 1.8, py - 1.1))
        elif ref in ("R201", "R202"):
            ref_item.SetPosition(pcbnew.VECTOR2I_MM(px - 2.1, py))

    # 11. Add Copper Pour Zones & Keepout Windows (U3 Antenna Keepout + Back LOGO2 Keepout)
    def add_rect_zone(net_name: str, layer_id: int, zx0: float, zy0: float, zx1: float, zy1: float, priority: int = 0):
        netinfo = board.GetNetInfo().GetNetItem(net_name)
        zone = pcbnew.ZONE(board)
        zone.SetNet(netinfo)
        zone.SetLayer(layer_id)
        zone.SetAssignedPriority(priority)
        zone.SetLocalClearance(pcbnew.FromMM(0.25))
        zone.SetMinThickness(pcbnew.FromMM(0.25))
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        zone.SetThermalReliefGap(pcbnew.FromMM(0.3))
        zone.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.4))
        zone.SetIsRuleArea(False)
        outline = zone.Outline()
        outline.NewOutline()
        outline.Append(pcbnew.VECTOR2I_MM(zx0, zy0))
        outline.Append(pcbnew.VECTOR2I_MM(zx1, zy0))
        outline.Append(pcbnew.VECTOR2I_MM(zx1, zy1))
        outline.Append(pcbnew.VECTOR2I_MM(zx0, zy1))
        board.Add(zone)
        return zone

    def add_keepout_zone(layers: list, zx0: float, zy0: float, zx1: float, zy1: float):
        zone = pcbnew.ZONE(board)
        zone.SetIsRuleArea(True)
        zone.SetDoNotAllowZoneFills(True)
        zone.SetDoNotAllowTracks(False)
        zone.SetDoNotAllowVias(False)
        lset = pcbnew.LSET()
        for lyr in layers:
            lset.addLayer(lyr)
        zone.SetLayerSet(lset)
        outline = zone.Outline()
        outline.NewOutline()
        outline.Append(pcbnew.VECTOR2I_MM(zx0, zy0))
        outline.Append(pcbnew.VECTOR2I_MM(zx1, zy0))
        outline.Append(pcbnew.VECTOR2I_MM(zx1, zy1))
        outline.Append(pcbnew.VECTOR2I_MM(zx0, zy1))
        board.Add(zone)
        return zone

    # 4-layer copper keepout under U3 ESP32-S3 antenna (X = 91..111mm, Y = 48..53.5mm)
    add_keepout_zone([pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu], 91.0, 48.0, 111.0, 53.5)
    # No B.Cu keepout for LOGO2 so central B.Cu routing highway is 100% unobstructed

    # Copper Pour Zones inside 45..202 x 48..153 outline
    add_rect_zone("GND", pcbnew.In1_Cu, 46.0, 49.0, 201.0, 152.0, priority=1)
    add_rect_zone("GND", pcbnew.B_Cu, 46.0, 49.0, 201.0, 152.0, priority=1)
    add_rect_zone("+5V", pcbnew.In2_Cu, 46.0, 49.0, 157.0, 152.0, priority=1)
    add_rect_zone("+BATT", pcbnew.In2_Cu, 158.0, 49.0, 201.0, 152.0, priority=2)

    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())

    pcbnew.SaveBoard(PCB_PATH, board)
    print("Successfully saved 4-layer layout to abx-motion.kicad_pcb!")

    # 12. Export Front (pcb_top.png) and Back (pcb_bottom.png) 2D Renders
    os.makedirs(os.path.join(PROJECT_DIR, "renders"), exist_ok=True)
    top_pdf = os.path.join(PROJECT_DIR, "renders/pcb_top.pdf")
    bot_pdf = os.path.join(PROJECT_DIR, "renders/pcb_bottom.pdf")
    top_layers = "F.Cu,F.Mask,F.SilkS,F.CrtYd,Edge.Cuts"
    bot_layers = "B.Cu,B.Mask,B.SilkS,B.CrtYd,Edge.Cuts"

    subprocess.run(["/usr/bin/kicad-cli", "pcb", "export", "pdf", "--output", top_pdf, "--layers", top_layers, PCB_PATH], check=True)
    subprocess.run(["pdftoppm", "-png", "-r", "300", "-singlefile", top_pdf, os.path.join(PROJECT_DIR, "renders/pcb_top")], check=True)

    subprocess.run(["/usr/bin/kicad-cli", "pcb", "export", "pdf", "--output", bot_pdf, "--layers", bot_layers, "--mirror", PCB_PATH], check=True)
    subprocess.run(["pdftoppm", "-png", "-r", "300", "-singlefile", bot_pdf, os.path.join(PROJECT_DIR, "renders/pcb_bottom")], check=True)
    print("Successfully exported renders/pcb_top.png and renders/pcb_bottom.png!")


if __name__ == "__main__":
    main()
