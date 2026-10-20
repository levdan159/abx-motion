with open("run_stage2.py") as f:
    code = f.read()

old_scale = """            elif st == pcbnew.SHAPE_T_RECT:
                s = item.GetStart()
                e = item.GetEnd()
                item.SetStart(pcbnew.VECTOR2I(cx + int(round((s.x - cx) * scale_factor)), cy + int(round((s.y - cy) * scale_factor))))
                item.SetEnd(pcbnew.VECTOR2I(cx + int(round((e.x - cx) * scale_factor)), cy + int(round((e.y - cy) * scale_factor))))"""

new_scale = old_scale + """
        elif isinstance(item, pcbnew.PCB_TEXT):
            pos = item.GetPosition()
            nx = cx + int(round((pos.x - cx) * scale_factor))
            ny = cy + int(round((pos.y - cy) * scale_factor))
            item.SetPosition(pcbnew.VECTOR2I(nx, ny))
            sz = item.GetTextSize()
            item.SetTextSize(pcbnew.VECTOR2I(int(round(sz.x * scale_factor)), int(round(sz.y * scale_factor))))
            item.SetTextThickness(int(round(item.GetTextThickness() * scale_factor)))
            if "V1.0" in item.GetText():
                item.SetText(item.GetText().replace("V1.0", "V1.1"))"""

assert old_scale in code
code = code.replace(old_scale, new_scale)

# Place LOGO1 at (148.5, 99.8) so it sits cleanly right of '+3V3' text at (141.2, 99.0)
code = code.replace(
    "logo1.SetPosition(pcbnew.VECTOR2I(from_mm(146.5), from_mm(99.8)))",
    "logo1.SetPosition(pcbnew.VECTOR2I(from_mm(148.5), from_mm(99.8)))",
)

# Update LOGO2 V1.0 -> V1.1 and save LOGO1/LOGO2 back to abx-footprints.pretty
old_logo2 = """    for item in logo2.GraphicalItems():
        if item.GetLayer() == pcbnew.B_Mask:
            item.SetLayer(pcbnew.B_SilkS)"""

new_logo2 = """    for item in logo2.GraphicalItems():
        if item.GetLayer() == pcbnew.B_Mask:
            item.SetLayer(pcbnew.B_SilkS)
        if isinstance(item, pcbnew.PCB_TEXT) and "V1.0" in item.GetText():
            item.SetText(item.GetText().replace("V1.0", "V1.1"))

    # Save modified LOGO1 and LOGO2 back to abx-footprints.pretty so lib_footprint_mismatch is 0 for them!
    for lref, lname in [("LOGO1", "ABX_Logo_Gears_Gold"), ("LOGO2", "ABX_Text_Gold")]:
        lfp = existing_fps[lref].Duplicate()
        lfp.SetPosition(pcbnew.VECTOR2I(0, 0))
        pcbnew.FootprintSave(os.path.join(PROJECT_DIR, "abx-footprints.pretty"), lfp)"""

assert old_logo2 in code
code = code.replace(old_logo2, new_logo2)

# Adjust Reference label offsets and JST-PH bank Y coordinates so silk_overlap and silk_over_copper are eliminated
code = code.replace(
    "place_fp(pref, px, 70.5, 90.0, ref_dx=0.0, ref_dy=2.1)",
    "place_fp(pref, px, 70.5, 90.0, ref_dx=0.0, ref_dy=2.2, hide_ref=True)",
)
code = code.replace(
    "place_fp(pref, px, 109.2, 90.0, ref_dx=0.0, ref_dy=-2.1)",
    "place_fp(pref, px, 109.2, 90.0, ref_dx=0.0, ref_dy=-2.1, hide_ref=True)",
)
code = code.replace(
    'place_fp("U601", 71.0, 115.2, 0.0, ref_dx=0.0, ref_dy=-4.7)',
    'place_fp("U601", 71.0, 115.2, 0.0, ref_dx=-4.8, ref_dy=0.0)',
)
# Also adjust F3 Reference position slightly left so it doesn't touch R601 Pad 1
old_f5 = 'place_fp("F5",   90.8, 115.2, 90.0, ref_dx=0.0, ref_dy=-2.9)'
new_f5 = old_f5 + '\n    existing_fps["F3"].Reference().SetPosition(pcbnew.VECTOR2I(from_mm(61.2), from_mm(121.0)))'
code = code.replace(old_f5, new_f5)

# Space J601-J603 at Y = 129.0 and J604-J606 at Y = 136.5 so headers/pin labels never touch C602-C609 or each other
old_jst_bank = """    jst_bank = [
        ("J601", 67.0, 128.0),
        ("J602", 77.5, 128.0),
        ("J603", 88.0, 128.0),
        ("J604", 67.0, 135.2),
        ("J605", 77.5, 135.2),
        ("J606", 88.0, 135.2),
    ]"""
new_jst_bank = """    jst_bank = [
        ("J601", 67.0, 129.0),
        ("J602", 77.5, 129.0),
        ("J603", 88.0, 129.0),
        ("J604", 67.0, 136.8),
        ("J605", 77.5, 136.8),
        ("J606", 88.0, 136.8),
    ]"""
assert old_jst_bank in code
code = code.replace(old_jst_bank, new_jst_bank)

old_io_headers = """    add_silk_text(board, "J601-J604: 3.3V LIM/IO | J605-J606: 5V 500mA", 79.5, 140.2, 0.75, 0.13, pcbnew.F_SilkS)
    add_silk_text(board, "J601-J604: 3.3V LIM/IO | J605-J606: 5V 500mA", 79.5, 140.2, 0.75, 0.13, pcbnew.B_SilkS, mirrored=True)

    io_headers = [
        ("J601 M1_LIM", 67.0, 128.0, "MN G MX"),
        ("J602 M2_LIM", 77.5, 128.0, "MN G MX"),
        ("J603 S1_LIM", 88.0, 128.0, "MN G MX"),
        ("J604 S2_LIM", 67.0, 135.2, "MN G MX"),
        ("J605 DC_OUT1", 77.5, 135.2, "5V G SW"),
        ("J606 DC_OUT2", 88.0, 135.2, "5V G SW"),
    ]
    for hdr, jx, jy, pins_str in io_headers:
        cx = jx + 2.0  # Center of 3-pin JST-PH (pins at jx+0, jx+2, jx+4)
        # Front Silkscreen: header above connector (jy - 2.8), pin labels below connector (jy + 3.95)
        add_silk_text(board, hdr,      cx, jy - 2.85, 0.68, 0.12, pcbnew.F_SilkS)
        add_silk_text(board, pins_str, cx, jy + 3.95, 0.65, 0.12, pcbnew.F_SilkS)
        # Back Silkscreen (mirrored): header above pads (jy - 2.1), pin labels below pads (jy + 2.1)
        add_silk_text(board, hdr,      cx, jy - 2.10, 0.68, 0.12, pcbnew.B_SilkS, mirrored=True)
        add_silk_text(board, pins_str, cx, jy + 2.10, 0.65, 0.12, pcbnew.B_SilkS, mirrored=True)"""

new_io_headers = """    add_silk_text(board, "J601-J604: 3.3V LIM/IO | J605-J606: 5V 500mA", 79.5, 141.6, 0.72, 0.12, pcbnew.F_SilkS)
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
        add_silk_text(board, pins_str, cx, jy + 2.10, 0.60, 0.11, pcbnew.B_SilkS, mirrored=True)"""

assert old_io_headers in code
code = code.replace(old_io_headers, new_io_headers)

with open("run_stage2.py", "w") as f:
    f.write(code)
