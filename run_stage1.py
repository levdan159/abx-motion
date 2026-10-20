#!/usr/bin/env python3
"""
STAGE 1/4: Complete & Validate V1.1 Schematic and Netlist (generate_schematics.py)
"""
import os
import re
import subprocess
import json
import xml.etree.ElementTree as ET

PROJECT_DIR = "/home/daniel/Documents/kicad/abx-motion"

def main():
    print("[STAGE 1/4] Updating generate_schematics.py and building 6-sheet Rev 1.1 schematics...")
    sch_path = os.path.join(PROJECT_DIR, "generate_schematics.py")
    with open(sch_path, "r", encoding="utf-8") as f:
        code = f.read()

    if "Industrial_IO" not in code:
        # 1. Add Industrial_IO to SHEET_UUIDS and FILE_UUIDS
        assert '"Steppers": "4a23d317-7151-447b-a577-c4acfecd7f3f",\n}' in code
        code = code.replace(
            '"Steppers": "4a23d317-7151-447b-a577-c4acfecd7f3f",\n}',
            '"Steppers": "4a23d317-7151-447b-a577-c4acfecd7f3f",\n    "Industrial_IO": "5b34e428-8262-458c-b688-d5bdfede8a4e",\n}',
        )
        assert '"Steppers_Relays.kicad_sch": "4d7b0a34-63ea-4c1d-9a34-9e0f1a2b3c4d",\n}' in code
        code = code.replace(
            '"Steppers_Relays.kicad_sch": "4d7b0a34-63ea-4c1d-9a34-9e0f1a2b3c4d",\n}',
            '"Steppers_Relays.kicad_sch": "4d7b0a34-63ea-4c1d-9a34-9e0f1a2b3c4d",\n    "Industrial_IO.kicad_sch": "5e8c1b45-74fb-4d2e-8b45-af102b3c4d5e",\n}',
        )

        # 2. In SymbolLibraryCache, make PCA9555PW unused/input I/O pins input to avoid ERC bidirectional warnings
        old_pin_hook = """                        pnum = num[1][1]
                        pname = name[1][1]
                        pins_by_unit.setdefault(unit_num, {})[pnum] = {"""
        new_pin_hook = """                        pnum = num[1][1]
                        pname = name[1][1]
                        if lib_id == "Interface_Expansion:PCA9555PW" and pnum in {"17", "18", "19", "20"}:
                            item[1] = ("sym", "input")
                            ptype = "input"
                        pins_by_unit.setdefault(unit_num, {})[pnum] = {"""
        assert old_pin_hook in code
        code = code.replace(old_pin_hook, new_pin_hook)

        # 3. Update MCU.kicad_sch: GPIO 21 -> BTN_BACK, GPIO 36 -> IO_INT_N, I2C_SDA/I2C_SCL hier_shape, R206 -> IO_INT_N
        old_u3_23 = 'sb.stub_net(u3, "23", "STEP_ENABLE", length=7.62, hier_shape="output")'
        assert old_u3_23 in code
        code = code.replace(
            old_u3_23,
            'sb.stub_net(u3, "23", "BTN_BACK", length=7.62)      # GPIO 21 (moved from GPIO 36)',
        )

        old_u3_29 = 'sb.stub_net(u3, "29", "BTN_BACK", length=7.62)      # GPIO 36'
        assert old_u3_29 in code
        code = code.replace(
            old_u3_29,
            'sb.stub_net(u3, "29", "IO_INT_N", length=7.62, hier_shape="input")  # GPIO 36 (~INT from PCA9555PW)',
        )

        old_i2c = 'sb.stub_net(u3, "34", "I2C_SDA", length=7.62)       # GPIO 41\n    sb.stub_net(u3, "35", "I2C_SCL", length=7.62)       # GPIO 42'
        assert old_i2c in code
        code = code.replace(
            old_i2c,
            'sb.stub_net(u3, "34", "I2C_SDA", length=7.62, hier_shape="bidirectional")  # GPIO 41\n    sb.stub_net(u3, "35", "I2C_SCL", length=7.62, hier_shape="output")         # GPIO 42',
        )

        old_r206 = '("R206", "10k", "STEP_ENABLE", "+3V3"),'
        assert old_r206 in code
        code = code.replace(
            old_r206,
            '("R206", "10k", "IO_INT_N", "+3V3"),',
        )

        # 4. Update Steppers_Relays.kicad_sch: STEP1_EN_GATED, STEP2_EN_GATED, Q503, Q504, R507, R508
        old_step_en = 'sb.stub_net(u_step, "9", "STEP_ENABLE", length=6.35, hier_shape="input" if ch == 1 else None)'
        new_step_en = 'sb.stub_net(u_step, "9", f"STEP{ch}_EN_GATED", length=6.35)'
        assert old_step_en in code
        code = code.replace(old_step_en, new_step_en)

        old_r_slp = """        sb.stub_net(r_slp, "1", "+3V3_DRV_EN", hier_shape="input" if ch == 1 else None)
        sb.stub_net(r_slp, "2", f"STEP{ch}_nSLP_RST")"""
        new_r_slp = """        sb.stub_net(r_slp, "1", "+3V3_DRV_EN", hier_shape="input" if ch == 1 else None)
        sb.stub_net(r_slp, "2", f"STEP{ch}_nSLP_RST")

        # Hardware E-Stop Gating Pass-FET Q503/Q504 (AO3400A) + 10k Pull-up R507/R508 on STEP{ch}_EN_GATED (Drain side)
        q_en = sb.place_sym(
            "Transistor_FET:Q_NMOS_GSD",
            f"Q50{2 + ch}",
            "AO3400A",
            "Package_TO_SOT_SMD:SOT-23",
            ux - 60.96,
            uy - 25.4,
            0,
        )
        sb.stub_net(q_en, "1", "+3V3_DRV_EN")
        sb.stub_net(q_en, "2", f"STEP{ch}_EN", hier_shape="input")
        sb.stub_net(q_en, "3", f"STEP{ch}_EN_GATED")

        r_en_pu = sb.place_sym(
            "Device:R",
            f"R50{6 + ch}",
            "10k",
            "Resistor_SMD:R_0603_1608Metric",
            ux - 60.96,
            uy + 5.08,
            0,
        )
        sb.stub_power(r_en_pu, "1", "+3V3")
        sb.stub_net(r_en_pu, "2", f"STEP{ch}_EN_GATED")"""
        assert old_r_slp in code
        code = code.replace(old_r_slp, new_r_slp)

        old_j_ext = 'sb.stub_net(j_ext, "1", "STEP_ENABLE")'
        assert old_j_ext in code
        code = code.replace(
            old_j_ext,
            'sb.stub_net(j_ext, "1", f"STEP{ch}_EN_GATED")',
        )

        # 5. Add build_industrial_io_sheet and update build_root_sheet + main
        ind_io_func = '''
def build_industrial_io_sheet(cache: SymbolLibraryCache):
    path = f"/{ROOT_UUID}/{SHEET_UUIDS['Industrial_IO']}"
    sb = SchematicBuilder("Industrial_IO.kicad_sch", cache, [(path, 0)], paper="A3")
    sb.add_text("SHEET 5: 6x 3-PIN JST-PH INDUSTRIAL I/O (8x LIMIT/GPIO + 2x 5V/500mA DC OUTPUTS) & PCA9555PW EXPANDER", 25.4, 17.78, 3.0)

    # 1. U601: PCA9555PW,118 (Address 0x20: A0=A1=A2=GND)
    u601 = sb.place_sym(
        "Interface_Expansion:PCA9555PW",
        "U601",
        "PCA9555PW,118",
        "Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm",
        215.9,
        127.0,
        0,
    )
    sb.stub_power(u601, "24", "+3V3", length=6.35)
    sb.stub_power(u601, "12", "GND", length=6.35)
    sb.stub_power(u601, "21", "GND", length=6.35)  # A0
    sb.stub_power(u601, "2", "GND", length=6.35)   # A1
    sb.stub_power(u601, "3", "GND", length=6.35)   # A2
    sb.stub_net(u601, "22", "I2C_SCL", length=7.62, hier_shape="input")
    sb.stub_net(u601, "23", "I2C_SDA", length=7.62, hier_shape="bidirectional")
    sb.stub_net(u601, "1", "IO_INT_N", length=7.62, hier_shape="output")

    # C601: 100nF Decoupling for U601
    c601 = sb.place_sym("Device:C", "C601", "100nF", "Capacitor_SMD:C_0603_1608Metric", 177.8, 127.0, 0)
    sb.stub_power(c601, "1", "+3V3")
    sb.stub_power(c601, "2", "GND")

    # 2. J601-J604: 4x 3-Pin JST-PH Limit / Digital I/O Sockets (8 Channels feeding IO0_0..IO0_7)
    lim_connectors = [
        ("J601", "B3B-PH-K-S", "M1_MIN", "M1_MAX", 1, 2, "4", "5", 40.64),
        ("J602", "B3B-PH-K-S", "M2_MIN", "M2_MAX", 3, 4, "6", "7", 101.6),
        ("J603", "B3B-PH-K-S", "S1_MIN", "S1_MAX", 5, 6, "8", "9", 162.56),
        ("J604", "B3B-PH-K-S", "S2_MIN", "S2_MAX", 7, 8, "10", "11", 223.52),
    ]
    for jref, jval, ch_a, ch_b, idx_a, idx_b, pin_a, pin_b, jy in lim_connectors:
        j_lim = sb.place_sym(
            "Connector:Conn_01x03_Pin",
            jref,
            jval,
            "Connector_JST:JST_PH_B3B-PH-K_1x03_P2.00mm_Vertical",
            40.64,
            jy,
            0,
        )
        sb.stub_net(j_lim, "1", f"{ch_a}_RAW")
        sb.stub_power(j_lim, "2", "GND")
        sb.stub_net(j_lim, "3", f"{ch_b}_RAW")

        for ch_name, ch_idx, u_pin, dy in [(ch_a, idx_a, pin_a, -12.7), (ch_b, idx_b, pin_b, 12.7)]:
            cy = round(jy + dy, 2)
            r_pu = sb.place_sym("Device:R", f"R60{ch_idx}", "4.7k", "Resistor_SMD:R_0603_1608Metric", 76.2, cy, 0)
            sb.stub_power(r_pu, "1", "+3V3")
            sb.stub_net(r_pu, "2", f"{ch_name}_RAW")

            r_ser = sb.place_sym("Device:R", f"R6{ch_idx + 8:02d}", "1k", "Resistor_SMD:R_0603_1608Metric", 106.68, cy, 90)
            sb.stub_net(r_ser, "1", f"{ch_name}_RAW")
            sb.stub_net(r_ser, "2", f"{ch_name}_IN")

            c_flt = sb.place_sym("Device:C", f"C60{ch_idx + 1}", "10nF", "Capacitor_SMD:C_0603_1608Metric", 137.16, cy, 0)
            sb.stub_net(c_flt, "1", f"{ch_name}_IN")
            sb.stub_power(c_flt, "2", "GND")

            sb.stub_net(u601, u_pin, f"{ch_name}_IN", length=7.62)

    # 3. J605, J606: 2x 3-Pin JST-PH Protected 5V / 500mA DC Outputs
    # F5: 500mA 1206 PTC from +5V to +5V_OUT
    f5 = sb.place_sym("Device:Polyfuse", "F5", "1206L050/15YR", "Fuse:Fuse_1206_3216Metric", 284.48, 40.64, 90)
    sb.stub_power(f5, "1", "+5V")
    sb.stub_net(f5, "2", "+5V_OUT")

    dc_outs = [
        (1, "J605", "B3B-PH-K-S", "13", "R617", "R619", "Q601", "D601", 88.9),
        (2, "J606", "B3B-PH-K-S", "14", "R618", "R620", "Q602", "D602", 165.1),
    ]
    for ch, jref, jval, u_pin, r_pd_ref, r_g_ref, q_ref, d_ref, oy in dc_outs:
        sb.stub_net(u601, u_pin, f"OUT{ch}_CMD", length=7.62)

        # 1k gate pull-down to GND (overcomes PCA9555 internal 100k pull-up at boot)
        r_pd = sb.place_sym("Device:R", r_pd_ref, "1k", "Resistor_SMD:R_0603_1608Metric", 279.4, oy + 15.24, 0)
        sb.stub_net(r_pd, "1", f"OUT{ch}_CMD")
        sb.stub_power(r_pd, "2", "GND")

        # 100R gate resistor
        r_g = sb.place_sym("Device:R", r_g_ref, "100", "Resistor_SMD:R_0603_1608Metric", 304.8, oy, 90)
        sb.stub_net(r_g, "1", f"OUT{ch}_CMD")
        sb.stub_net(r_g, "2", f"OUT{ch}_GATE")

        # AO3400A N-MOSFET
        q_sw = sb.place_sym("Transistor_FET:Q_NMOS_GSD", q_ref, "AO3400A", "Package_TO_SOT_SMD:SOT-23", 335.28, oy, 0)
        sb.stub_net(q_sw, "1", f"OUT{ch}_GATE")
        sb.stub_power(q_sw, "2", "GND")
        sb.stub_net(q_sw, "3", f"OUT{ch}_SW")

        # B5819W 1A Schottky Flyback Diode (SOD-123: Pin 1 Cathode = +5V_OUT, Pin 2 Anode = OUTx_SW)
        d_fb = sb.place_sym("Device:D_Schottky", d_ref, "B5819W", "Diode_SMD:D_SOD-123", 360.68, oy - 12.7, 270)
        sb.stub_net(d_fb, "1", "+5V_OUT")
        sb.stub_net(d_fb, "2", f"OUT{ch}_SW")

        # 3-Pin JST-PH Output Connector: Pin 1 = +5V_OUT, Pin 2 = GND, Pin 3 = OUTx_SW
        j_out = sb.place_sym(
            "Connector:Conn_01x03_Pin",
            jref,
            jval,
            "Connector_JST:JST_PH_B3B-PH-K_1x03_P2.00mm_Vertical",
            391.16,
            oy,
            0,
        )
        sb.stub_net(j_out, "1", "+5V_OUT")
        sb.stub_power(j_out, "2", "GND")
        sb.stub_net(j_out, "3", f"OUT{ch}_SW")

    # 4. Independent Stepper Enables (IO1_2=Pin 15 -> STEP1_EN, IO1_3=Pin 16 -> STEP2_EN) with 10k pull-ups R621, R622 to +3V3 & ESTOP_SENSE (IO1_4=Pin 17)
    sb.stub_net(u601, "15", "STEP1_EN", length=7.62, hier_shape="output")
    sb.stub_net(u601, "16", "STEP2_EN", length=7.62, hier_shape="output")

    r621 = sb.place_sym("Device:R", "R621", "10k", "Resistor_SMD:R_0603_1608Metric", 279.4, 215.9, 0)
    sb.stub_power(r621, "1", "+3V3")
    sb.stub_net(r621, "2", "STEP1_EN")

    r622 = sb.place_sym("Device:R", "R622", "10k", "Resistor_SMD:R_0603_1608Metric", 304.8, 215.9, 0)
    sb.stub_power(r622, "1", "+3V3")
    sb.stub_net(r622, "2", "STEP2_EN")

    sb.stub_net(u601, "17", "+3V3_DRV_EN", length=7.62, hier_shape="input")

    # Tie unused IO1_5..IO1_7 (Pins 18, 19, 20) to GND
    for upin in ["18", "19", "20"]:
        sb.stub_power(u601, upin, "GND", length=6.35)

    sb.save()
'''
        assert "def build_root_sheet():" in code
        code = code.replace("def build_root_sheet():", ind_io_func + "\n\ndef build_root_sheet():")

        old_root_mcu_pins = """                ("STEP2_DIR", "output", "STEP2_DIR"),
                ("STEP_ENABLE", "output", "STEP_ENABLE"),
                ("RELAY_1", "output", "RELAY_1"),
                ("RELAY_2", "output", "RELAY_2"),"""
        new_root_mcu_pins = """                ("STEP2_DIR", "output", "STEP2_DIR"),
                ("RELAY_1", "output", "RELAY_1"),
                ("RELAY_2", "output", "RELAY_2"),
                ("I2C_SDA", "bidirectional", "I2C_SDA"),
                ("I2C_SCL", "output", "I2C_SCL"),
                ("IO_INT_N", "input", "IO_INT_N"),"""
        assert old_root_mcu_pins in code
        code = code.replace(old_root_mcu_pins, new_root_mcu_pins)

        old_root_step_pins = """                ("STEP2_DIR", "input", "STEP2_DIR"),
                ("STEP_ENABLE", "input", "STEP_ENABLE"),
                ("RELAY_1", "input", "RELAY_1"),"""
        new_root_step_pins = """                ("STEP2_DIR", "input", "STEP2_DIR"),
                ("STEP1_EN", "input", "STEP1_EN"),
                ("STEP2_EN", "input", "STEP2_EN"),
                ("RELAY_1", "input", "RELAY_1"),"""
        assert old_root_step_pins in code
        code = code.replace(old_root_step_pins, new_root_step_pins)

        old_sheets_end = """                ("RELAY_2", "input", "RELAY_2"),
            ],
        ),
    ]"""
        new_sheets_end = """                ("RELAY_2", "input", "RELAY_2"),
            ],
        ),
        make_sheet(
            "Industrial_IO",
            "Industrial_IO.kicad_sch",
            SHEET_UUIDS["Industrial_IO"],
            "7",
            124.46,
            116.84,
            [
                ("I2C_SDA", "bidirectional", "I2C_SDA"),
                ("I2C_SCL", "input", "I2C_SCL"),
                ("+3V3_DRV_EN", "input", "+3V3_DRV_EN"),
            ],
            [
                ("IO_INT_N", "output", "IO_INT_N"),
                ("STEP1_EN", "output", "STEP1_EN"),
                ("STEP2_EN", "output", "STEP2_EN"),
            ],
        ),
    ]"""
        assert old_sheets_end in code
        code = code.replace(old_sheets_end, new_sheets_end)

        old_sheet_inst = """\t\t(path "/{ROOT_UUID}/{SHEET_UUIDS['Steppers']}"
\t\t\t(page "6")
\t\t)
\t)"""
        new_sheet_inst = """\t\t(path "/{ROOT_UUID}/{SHEET_UUIDS['Steppers']}"
\t\t\t(page "6")
\t\t)
\t\t(path "/{ROOT_UUID}/{SHEET_UUIDS['Industrial_IO']}"
\t\t\t(page "7")
\t\t)
\t)"""
        assert old_sheet_inst in code
        code = code.replace(old_sheet_inst, new_sheet_inst)

        old_main_calls = "build_steppers_relays_sheet(cache)\n    build_root_sheet()"
        assert old_main_calls in code
        code = code.replace(
            old_main_calls,
            "build_steppers_relays_sheet(cache)\n    build_industrial_io_sheet(cache)\n    build_root_sheet()",
        )

        with open(sch_path, "w", encoding="utf-8") as f:
            f.write(code)

    # Run generate_schematics.py
    subprocess.run(["python3", "generate_schematics.py"], cwd=PROJECT_DIR, check=True)

    # Run ERC
    subprocess.run(
        ["/usr/bin/kicad-cli", "sch", "erc", "--format", "json", "--output", "erc.json", "abx-motion.kicad_sch"],
        cwd=PROJECT_DIR,
        check=True,
    )
    subprocess.run(
        ["/usr/bin/kicad-cli", "sch", "erc", "--output", "erc.rpt", "abx-motion.kicad_sch"],
        cwd=PROJECT_DIR,
        check=True,
    )
    with open(os.path.join(PROJECT_DIR, "erc.json")) as f:
        erc_data = json.load(f)

    total_erc_errors = 0
    total_erc_warnings = 0
    for sheet in erc_data.get("sheets", []):
        for v in sheet.get("violations", []):
            if v.get("severity") == "error":
                total_erc_errors += 1
            elif v.get("severity") == "warning":
                total_erc_warnings += 1
            print(f"  ERC [{v.get('severity')}] {v.get('type')}: {v.get('description')}")

    print(f"[STAGE 1/4] ERC Summary: {total_erc_errors} Errors, {total_erc_warnings} Warnings")
    assert total_erc_errors == 0 and total_erc_warnings == 0, "ERC must have 0 Errors and 0 Warnings!"

    # Export netlist (both XML for easy parsing and S-expr .net)
    subprocess.run(
        ["/usr/bin/kicad-cli", "sch", "export", "netlist", "--output", "abx-motion.net", "abx-motion.kicad_sch"],
        cwd=PROJECT_DIR,
        check=True,
    )
    subprocess.run(
        ["/usr/bin/kicad-cli", "sch", "export", "netlist", "--format", "kicadxml", "--output", "abx-motion.xml", "abx-motion.kicad_sch"],
        cwd=PROJECT_DIR,
        check=True,
    )

    # Parse XML netlist to explicitly verify required nets and component values
    tree = ET.parse(os.path.join(PROJECT_DIR, "abx-motion.xml"))
    root = tree.getroot()

    comp_vals = {}
    comp_fps = {}
    for comp in root.findall(".//comp"):
        ref = comp.attrib["ref"]
        val_el = comp.find("value")
        fp_el = comp.find("footprint")
        comp_vals[ref] = val_el.text if val_el is not None else ""
        comp_fps[ref] = fp_el.text if fp_el is not None else ""

    # Verify v1.0-production locked values
    expected_vals = {
        "Q1": "SQJ459EP-T1_GE3",
        "D2": "SMCJ30A",
        "U3": "ESP32-S3-WROOM-1-N8R2",
        "U203": "THVD1450DR",
        "R222": "330R",
        "R223": "330R",
        "R309": "10mR_3W",
        "R409": "10mR_3W",
        "C310": "2.2nF",
        "C410": "2.2nF",
        "R312": "200k",
        "R412": "200k",
        "U601": "PCA9555PW,118",
        "J601": "B3B-PH-K-S",
        "J602": "B3B-PH-K-S",
        "J603": "B3B-PH-K-S",
        "J604": "B3B-PH-K-S",
        "J605": "B3B-PH-K-S",
        "J606": "B3B-PH-K-S",
        "Q503": "AO3400A",
        "Q504": "AO3400A",
        "R507": "10k",
        "R508": "10k",
        "R621": "10k",
        "R622": "10k",
    }
    for ref, exp_v in expected_vals.items():
        actual_v = comp_vals.get(ref)
        assert actual_v == exp_v, f"Component {ref} value mismatch: expected {exp_v}, got {actual_v}"
    assert comp_fps.get("F1") == "abx-footprints:Fuseholder_Keystone_3557-2", f"F1 footprint mismatch: {comp_fps.get('F1')}"
    assert "H5" in comp_vals and "H6" in comp_vals, "H5/H6 missing!"

    # Map (ref, pin) -> net_name and net_name -> set of (ref, pin)
    pin_to_net = {}
    net_to_pins = {}
    for net in root.findall(".//net"):
        nname = net.attrib["name"]
        nodes = set()
        for node in net.findall("node"):
            rp = (node.attrib["ref"], node.attrib["pin"])
            pin_to_net[rp] = nname
            nodes.add(rp)
        net_to_pins[nname] = nodes

    # 1. Verify BTN_BACK on U3.23 and SW203.1
    btn_back_net = pin_to_net.get(("U3", "23"))
    assert btn_back_net and "BTN_BACK" in btn_back_net, f"U3.23 net is {btn_back_net}"
    assert ("SW203", "1") in net_to_pins[btn_back_net], "SW203.1 not connected to U3.23 on BTN_BACK!"
    assert "STEP_ENABLE" not in net_to_pins and "/STEP_ENABLE" not in net_to_pins, "Obsolete STEP_ENABLE net still present!"

    # 2. Verify IO_INT_N on U3.29, R206.1, U601.1
    io_int_net = pin_to_net.get(("U3", "29"))
    assert io_int_net == "/IO_INT_N", f"U3.29 net is {io_int_net}"
    assert ("R206", "2") in net_to_pins[io_int_net] and pin_to_net.get(("R206", "1")) == "+3V3", "R206.1 not on IO_INT_N"
    assert ("U601", "1") in net_to_pins[io_int_net], "U601.1 not on IO_INT_N"

    # 3. Verify all 8 limit inputs (J601-J604 -> R601-R608 -> R609-R616 -> C602-C609 -> U601.4..11)
    lim_checks = [
        ("J601", "1", "R601", "R609", "C602", "4"),
        ("J601", "3", "R602", "R610", "C603", "5"),
        ("J602", "1", "R603", "R611", "C604", "6"),
        ("J602", "3", "R604", "R612", "C605", "7"),
        ("J603", "1", "R605", "R613", "C606", "8"),
        ("J603", "3", "R606", "R614", "C607", "9"),
        ("J604", "1", "R607", "R615", "C608", "10"),
        ("J604", "3", "R608", "R616", "C609", "11"),
    ]
    for jref, jpin, rpu, rser, cflt, upin in lim_checks:
        raw_net = pin_to_net.get((jref, jpin))
        assert (rpu, "2") in net_to_pins[raw_net] and (rser, "1") in net_to_pins[raw_net], f"Broken raw net on {jref}.{jpin}"
        assert pin_to_net.get((rpu, "1")) == "+3V3"
        assert pin_to_net.get((jref, "2")) == "GND"
        in_net = pin_to_net.get((u601_ref := "U601", upin))
        assert (rser, "2") in net_to_pins[in_net] and (cflt, "1") in net_to_pins[in_net], f"Broken filter net on U601.{upin}"
        assert pin_to_net.get((cflt, "2")) == "GND"

    # 4. Verify both auxiliary 5V/500mA DC outputs (F5, J605, J606, R617-R620, Q601-Q602, D601-D602)
    assert pin_to_net.get(("F5", "1")) == "+5V"
    v5_out_net = pin_to_net.get(("F5", "2"))
    for ch, jref, upin, rpd, rg, qref, dref in [
        (1, "J605", "13", "R617", "R619", "Q601", "D601"),
        (2, "J606", "14", "R618", "R620", "Q602", "D602"),
    ]:
        cmd_net = pin_to_net.get(("U601", upin))
        assert (rpd, "1") in net_to_pins[cmd_net] and (rg, "1") in net_to_pins[cmd_net]
        assert pin_to_net.get((rpd, "2")) == "GND"
        gate_net = pin_to_net.get((rg, "2"))
        assert (qref, "1") in net_to_pins[gate_net]
        assert pin_to_net.get((qref, "2")) == "GND"
        sw_net = pin_to_net.get((qref, "3"))
        assert (jref, "3") in net_to_pins[sw_net] and (dref, "2") in net_to_pins[sw_net]
        assert (jref, "1") in net_to_pins[v5_out_net] and (dref, "1") in net_to_pins[v5_out_net]
        assert pin_to_net.get((jref, "2")) == "GND"

    # 5. Verify E-Stop-gated stepper enables (U601.15/16 -> R621/R622 + Q503/Q504.2 Source; +3V3_DRV_EN -> Q503/Q504.1 Gate & U601.17; Q503/Q504.3 Drain -> R507/R508 + U501/U502.9 + J502/J504.1)
    for ch, upin, r_exp, q_en, r_drn, u_stp, j_stp in [
        (1, "15", "R621", "Q503", "R507", "U501", "J502"),
        (2, "16", "R622", "Q504", "R508", "U502", "J504"),
    ]:
        en_net = pin_to_net.get(("U601", upin))
        assert en_net == f"/STEP{ch}_EN", f"Expected /STEP{ch}_EN, got {en_net}"
        assert (r_exp, "2") in net_to_pins[en_net] and (q_en, "2") in net_to_pins[en_net]
        assert pin_to_net.get((r_exp, "1")) == "+3V3"
        assert pin_to_net.get((q_en, "1")) == "/+3V3_DRV_EN"
        gated_net = pin_to_net.get((q_en, "3"))
        assert (r_drn, "2") in net_to_pins[gated_net]
        assert (u_stp, "9") in net_to_pins[gated_net]
        assert (j_stp, "1") in net_to_pins[gated_net]
        assert pin_to_net.get((r_drn, "1")) == "+3V3"

    assert pin_to_net.get(("U601", "17")) == "/+3V3_DRV_EN"
    for upin in ["18", "19", "20", "2", "3", "12", "21"]:
        assert pin_to_net.get(("U601", upin)) == "GND"
    assert pin_to_net.get(("U601", "24")) == "+3V3"
    assert pin_to_net.get(("U601", "22")) == "/I2C_SCL" and ("U3", "35") in net_to_pins["/I2C_SCL"]
    assert pin_to_net.get(("U601", "23")) == "/I2C_SDA" and ("U3", "34") in net_to_pins["/I2C_SDA"]

    print(f"[STAGE 1/4] SUCCESS! Total components in netlist: {len(comp_vals)}. All netlist & value assertions passed with 0 ERC errors/warnings!")

if __name__ == "__main__":
    main()
