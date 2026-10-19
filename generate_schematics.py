#!/usr/bin/env python3
"""
Deterministic KiCad 10.0 Schematic Generator for ABX-Motion.
Parses exact pin coordinates from /usr/share/kicad/symbols/*.kicad_sym,
builds abx-symbols.kicad_sym, Power.kicad_sch, MCU.kicad_sch,
Motor_Channel.kicad_sch, Steppers_Relays.kicad_sch, and abx-motion.kicad_sch.
"""

import copy
import math
import os
import re
import uuid

PROJECT_DIR = "/home/daniel/Documents/kicad/abx-motion"
SYM_DIR = "/usr/share/kicad/symbols"
ROOT_UUID = "f9149098-3f23-438d-bdc2-2e278b5ca35b"

SHEET_UUIDS = {
    "Power": "383ff9ef-8565-4c62-b17f-0912fd19804f",
    "MCU": "c81c9d86-49aa-496e-8f70-b852842466ca",
    "Motor1": "92b8d963-008c-44ee-80dc-a4ddc2493923",
    "Motor2": "40d2ba13-688c-4a36-ae2b-0996c3aab01d",
    "Steppers": "4a23d317-7151-447b-a577-c4acfecd7f3f",
    "Industrial_IO": "5b34e428-8262-458c-b688-d5bdfede8a4e",
}

FILE_UUIDS = {
    "Power.kicad_sch": "8cc4c544-296c-46c1-9686-d35546713905",
    "MCU.kicad_sch": "2b5f8e12-41c8-4a9b-9e12-7c8d9e0f1a2b",
    "Motor_Channel.kicad_sch": "3c6a9f23-52d9-4b0c-8f23-8d9e0f1a2b3c",
    "Steppers_Relays.kicad_sch": "4d7b0a34-63ea-4c1d-9a34-9e0f1a2b3c4d",
    "Industrial_IO.kicad_sch": "5e8c1b45-74fb-4d2e-8b45-af102b3c4d5e",
}


def det_uuid(seed: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"abx-motion.{seed}"))


def parse_sexp(text: str):
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|\(|\)|[^\s()"]+', text)
    stack = [[]]
    for tok in tokens:
        if tok == "(":
            new_list = []
            stack[-1].append(new_list)
            stack.append(new_list)
        elif tok == ")":
            stack.pop()
        else:
            if tok.startswith('"') and tok.endswith('"'):
                val = tok[1:-1].replace('\\"', '"').replace("\\\\", "\\")
                stack[-1].append(("str", val))
            else:
                stack[-1].append(("sym", tok))
    return stack[0][0]


def format_sexp(node, indent=0) -> str:
    ind = "\t" * indent
    if isinstance(node, tuple):
        kind, val = node
        if kind == "str":
            escaped = val.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
        return str(val)
    if not isinstance(node, list) or not node:
        return "()"
    head = format_sexp(node[0])
    # Compact simple nodes
    if all(isinstance(x, tuple) for x in node):
        return f"{ind}(" + " ".join(format_sexp(x) for x in node) + ")"
    parts = [f"{ind}({head}"]
    # Put leading atoms on same line as head
    idx = 1
    while idx < len(node) and isinstance(node[idx], tuple):
        parts[0] += " " + format_sexp(node[idx])
        idx += 1
    for child in node[idx:]:
        parts.append(format_sexp(child, indent + 1))
    parts.append(f"{ind})")
    return "\n".join(parts)


class SymbolLibraryCache:
    def __init__(self):
        self._trees = {}
        self._flattened = {}
        self._pins = {}

    def _get_lib_tree(self, lib_name: str):
        if lib_name not in self._trees:
            if lib_name == "abx":
                path = os.path.join(PROJECT_DIR, "abx-symbols.kicad_sym")
            else:
                path = os.path.join(SYM_DIR, f"{lib_name}.kicad_sym")
            with open(path, "r", encoding="utf-8") as f:
                self._trees[lib_name] = parse_sexp(f.read())
        return self._trees[lib_name]

    def get_symbol_and_pins(self, lib_id: str):
        if lib_id in self._flattened:
            return self._flattened[lib_id], self._pins[lib_id]
        lib_name, sym_name = lib_id.split(":")
        tree = self._get_lib_tree(lib_name)
        syms = {
            item[1][1]: item
            for item in tree[1:]
            if isinstance(item, list) and item and item[0] == ("sym", "symbol")
        }
        raw_sym = copy.deepcopy(syms[sym_name])
        ext_nodes = [
            c for c in raw_sym[2:]
            if isinstance(c, list) and c and c[0] == ("sym", "extends")
        ]
        if ext_nodes:
            parent_name = ext_nodes[0][1][1]
            parent_sym = copy.deepcopy(syms[parent_name])
            # Merge properties from child over parent
            child_props = {
                c[1][1]: c
                for c in raw_sym[2:]
                if isinstance(c, list) and c and c[0] == ("sym", "property")
            }
            merged = [("sym", "symbol"), ("str", lib_id)]
            for c in parent_sym[2:]:
                if isinstance(c, list) and c:
                    if c[0] == ("sym", "property"):
                        pname = c[1][1]
                        merged.append(child_props.pop(pname, c))
                    elif c[0] == ("sym", "symbol"):
                        sub = copy.deepcopy(c)
                        old_subname = sub[1][1]
                        suffix = old_subname[len(parent_name):]
                        sub[1] = ("str", f"{sym_name}{suffix}")
                        merged.append(sub)
                    else:
                        merged.append(c)
            for rem_prop in child_props.values():
                merged.append(rem_prop)
            flat_sym = merged
        else:
            flat_sym = copy.deepcopy(raw_sym)
            flat_sym[1] = ("str", lib_id)

        # Parse pins per unit
        pins_by_unit = {}
        for c in flat_sym[2:]:
            if isinstance(c, list) and c and c[0] == ("sym", "symbol"):
                subname = c[1][1]
                m = re.search(r"_(\d+)_(\d+)$", subname)
                unit_num = int(m.group(1)) if m else 1
                for item in c[2:]:
                    if isinstance(item, list) and item and item[0] == ("sym", "pin"):
                        ptype = item[1][1]
                        at = [x for x in item if isinstance(x, list) and x[0] == ("sym", "at")][0]
                        name = [x for x in item if isinstance(x, list) and x[0] == ("sym", "name")][0]
                        num = [x for x in item if isinstance(x, list) and x[0] == ("sym", "number")][0]
                        px = float(at[1][1])
                        py = float(at[2][1])
                        pang = float(at[3][1])
                        pnum = num[1][1]
                        pname = name[1][1]
                        if lib_id == "Interface_Expansion:PCA9555PW" and pnum in {"17", "18", "19", "20"}:
                            item[1] = ("sym", "input")
                            ptype = "input"
                        pins_by_unit.setdefault(unit_num, {})[pnum] = {
                            "num": pnum,
                            "name": pname,
                            "type": ptype,
                            "x": px,
                            "y": py,
                            "ang": pang,
                        }
        self._flattened[lib_id] = flat_sym
        self._pins[lib_id] = pins_by_unit
        return flat_sym, pins_by_unit


def build_abx_symbols_lib():
    """Creates abx-symbols.kicad_sym containing DRV8701ERGER, CSD18540Q5B, AONS21357, ABX_Logo and sym-lib-table."""
    left_pins = [
        ("1", "VM", "power_in", 12.70),
        ("2", "VCP", "passive", 10.16),
        ("3", "CPH", "passive", 7.62),
        ("4", "CPL", "passive", 5.08),
        ("7", "AVDD", "power_out", 2.54),
        ("8", "DVDD", "power_out", 0.00),
        ("6", "VREF", "input", -2.54),
        ("13", "nSLEEP", "input", -5.08),
        ("14", "EN", "input", -7.62),
        ("15", "PH", "input", -10.16),
        ("12", "IDRIVE", "input", -12.70),
        ("5", "AGND", "power_in", -15.24),
    ]
    right_pins = [
        ("17", "GH1", "output", 12.70),
        ("18", "SH1", "bidirectional", 10.16),
        ("19", "GL1", "output", 7.62),
        ("24", "GH2", "output", 5.08),
        ("23", "SH2", "bidirectional", 2.54),
        ("22", "GL2", "output", 0.00),
        ("21", "SP", "input", -2.54),
        ("20", "SN", "input", -5.08),
        ("11", "SO", "output", -7.62),
        ("9", "nFAULT", "output", -10.16),
        ("10", "SNSOUT", "output", -12.70),
        ("16", "PGND", "power_in", -15.24),
        ("25", "EP", "power_in", -17.78),
    ]
    pin_sexps = []
    for num, name, ptype, y in left_pins:
        pin_sexps.append(f"""
				(pin {ptype} line
					(at -15.24 {y:.2f} 0)
					(length 2.54)
					(name "{name}" (effects (font (size 1.27 1.27))))
					(number "{num}" (effects (font (size 1.27 1.27))))
				)""")
    for num, name, ptype, y in right_pins:
        pin_sexps.append(f"""
				(pin {ptype} line
					(at 15.24 {y:.2f} 180)
					(length 2.54)
					(name "{name}" (effects (font (size 1.27 1.27))))
					(number "{num}" (effects (font (size 1.27 1.27))))
				)""")

    content = f"""(kicad_symbol_lib
	(version 20231120)
	(generator "abx_generator")
	(generator_version "10.0")
	(symbol "DRV8701ERGER"
		(pin_names (offset 1.016))
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(property "Reference" "U" (at 0 16.51 0) (effects (font (size 1.27 1.27))))
		(property "Value" "DRV8701ERGER" (at 0 -21.59 0) (effects (font (size 1.27 1.27))))
		(property "Footprint" "Package_DFN_QFN:Texas_RGE0024C_VQFN-24-1EP_4x4mm_P0.5mm_EP2.1x2.1mm_ThermalVias" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
		(property "Datasheet" "https://www.ti.com/lit/ds/symlink/drv8701.pdf" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
		(symbol "DRV8701ERGER_0_1"
			(rectangle (start -12.7 15.24) (end 12.7 -20.32)
				(stroke (width 0.254) (type default))
				(fill (type background))
			)
		)
		(symbol "DRV8701ERGER_1_1"{''.join(pin_sexps)}
		)
		(embedded_fonts no)
	)
	(symbol "CSD18540Q5B"
		(pin_names (offset 0) (hide yes))
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(property "Reference" "Q" (at 5.08 1.905 0) (effects (font (size 1.27 1.27)) (justify left)))
		(property "Value" "CSD18540Q5B" (at 5.08 0 0) (effects (font (size 1.27 1.27)) (justify left)))
		(property "Footprint" "Package_TO_SOT_SMD:TDSON-8-1" (at 5.08 -1.905 0) (effects (font (size 1.27 1.27)) (hide yes)))
		(property "Datasheet" "https://www.ti.com/lit/ds/symlink/csd18540q5b.pdf" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
		(symbol "CSD18540Q5B_0_1"
			(polyline (pts (xy 0.254 1.905) (xy 0.254 -1.905)) (stroke (width 0.254) (type default)) (fill (type none)))
			(polyline (pts (xy 0.254 0) (xy -2.54 0)) (stroke (width 0) (type default)) (fill (type none)))
			(polyline (pts (xy 0.762 2.286) (xy 0.762 1.27)) (stroke (width 0.254) (type default)) (fill (type none)))
			(polyline (pts (xy 0.762 0.508) (xy 0.762 -0.508)) (stroke (width 0.254) (type default)) (fill (type none)))
			(polyline (pts (xy 0.762 -1.27) (xy 0.762 -2.286)) (stroke (width 0.254) (type default)) (fill (type none)))
			(polyline (pts (xy 0.762 -1.778) (xy 3.302 -1.778) (xy 3.302 1.778) (xy 0.762 1.778)) (stroke (width 0) (type default)) (fill (type none)))
			(polyline (pts (xy 1.016 0) (xy 2.032 0.381) (xy 2.032 -0.381) (xy 1.016 0)) (stroke (width 0) (type default)) (fill (type outline)))
			(circle (center 1.651 0) (radius 2.794) (stroke (width 0.254) (type default)) (fill (type none)))
			(polyline (pts (xy 2.54 2.54) (xy 2.54 1.778)) (stroke (width 0) (type default)) (fill (type none)))
			(polyline (pts (xy 2.54 -2.54) (xy 2.54 0) (xy 0.762 0)) (stroke (width 0) (type default)) (fill (type none)))
		)
		(symbol "CSD18540Q5B_1_1"
			(pin input line (at -5.08 0 0) (length 2.54) (name "G" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
			(pin passive line (at 2.54 5.08 270) (length 2.54) (name "D" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
			(pin passive line (at 2.54 -5.08 90) (length 2.54) (name "S" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
			(pin passive line (at 2.54 -5.08 90) (length 2.54) (hide yes) (name "S" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
			(pin passive line (at 2.54 -5.08 90) (length 2.54) (hide yes) (name "S" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
		)
		(embedded_fonts no)
	)
	(symbol "AONS21357"
		(pin_names (offset 0) (hide yes))
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(property "Reference" "Q" (at 5.08 1.905 0) (effects (font (size 1.27 1.27)) (justify left)))
		(property "Value" "AONS21357" (at 5.08 0 0) (effects (font (size 1.27 1.27)) (justify left)))
		(property "Footprint" "Package_TO_SOT_SMD:TDSON-8-1" (at 5.08 -1.905 0) (effects (font (size 1.27 1.27)) (hide yes)))
		(property "Datasheet" "https://aosmd.com/res/data_sheets/AONS21357.pdf" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
		(symbol "AONS21357_0_1"
			(polyline (pts (xy 0.254 1.905) (xy 0.254 -1.905)) (stroke (width 0.254) (type default)) (fill (type none)))
			(polyline (pts (xy 0.254 0) (xy -2.54 0)) (stroke (width 0) (type default)) (fill (type none)))
			(polyline (pts (xy 0.762 2.286) (xy 0.762 1.27)) (stroke (width 0.254) (type default)) (fill (type none)))
			(polyline (pts (xy 0.762 0.508) (xy 0.762 -0.508)) (stroke (width 0.254) (type default)) (fill (type none)))
			(polyline (pts (xy 0.762 -1.27) (xy 0.762 -2.286)) (stroke (width 0.254) (type default)) (fill (type none)))
			(polyline (pts (xy 0.762 1.778) (xy 3.302 1.778) (xy 3.302 -1.778) (xy 0.762 -1.778)) (stroke (width 0) (type default)) (fill (type none)))
			(polyline (pts (xy 2.286 0) (xy 1.27 0.381) (xy 1.27 -0.381) (xy 2.286 0)) (stroke (width 0) (type default)) (fill (type outline)))
			(circle (center 1.651 0) (radius 2.794) (stroke (width 0.254) (type default)) (fill (type none)))
			(polyline (pts (xy 2.54 2.54) (xy 2.54 1.778)) (stroke (width 0) (type default)) (fill (type none)))
			(polyline (pts (xy 2.54 -2.54) (xy 2.54 0) (xy 0.762 0)) (stroke (width 0) (type default)) (fill (type none)))
		)
		(symbol "AONS21357_1_1"
			(pin input line (at -5.08 0 0) (length 2.54) (name "G" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
			(pin passive line (at 2.54 5.08 270) (length 2.54) (name "D" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
			(pin passive line (at 2.54 -5.08 90) (length 2.54) (name "S" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
			(pin passive line (at 2.54 -5.08 90) (length 2.54) (hide yes) (name "S" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
			(pin passive line (at 2.54 -5.08 90) (length 2.54) (hide yes) (name "S" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
		)
		(embedded_fonts no)
	)
	(symbol "ABX_Logo"
		(pin_names (offset 1.016))
		(exclude_from_sim yes)
		(in_bom no)
		(on_board yes)
		(property "Reference" "LOGO" (at 0 3.81 0) (effects (font (size 1.27 1.27))))
		(property "Value" "ABX_Logo" (at 0 -3.81 0) (effects (font (size 1.27 1.27))))
		(property "Footprint" "abx-footprints:ABX_Logo_Gears_Gold" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
		(property "Datasheet" "~" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
		(symbol "ABX_Logo_0_1"
			(rectangle (start -5.08 2.54) (end 5.08 -2.54)
				(stroke (width 0.254) (type default))
				(fill (type background))
			)
		)
		(symbol "ABX_Logo_1_1")
		(embedded_fonts no)
	)
)
"""
    with open(os.path.join(PROJECT_DIR, "abx-symbols.kicad_sym"), "w", encoding="utf-8") as f:
        f.write(content)

    sym_table = """(sym_lib_table
  (version 7)
  (lib (name "abx")(type "KiCad")(uri "${KIPRJMOD}/abx-symbols.kicad_sym")(options "")(descr "ABX Custom Symbols"))
)
"""
    with open(os.path.join(PROJECT_DIR, "sym-lib-table"), "w", encoding="utf-8") as f:
        f.write(sym_table)


def fmt_num(v: float) -> str:
    r = round(v, 2)
    if abs(r - round(r)) < 1e-6:
        return str(int(round(r)))
    return f"{r:.2f}".rstrip("0").rstrip(".")


class SchematicBuilder:
    all_placed_components = []
    pwr_counter = 1
    def __init__(self, filename: str, cache: SymbolLibraryCache, sheet_paths: list, paper="A3"):
        self.filename = filename
        self.file_uuid = FILE_UUIDS[filename]
        self.cache = cache
        self.sheet_paths = sheet_paths  # list of (path_str, ref_map_or_None)
        self.paper = paper
        self.used_lib_ids = []
        self.symbols = []
        self.placed_components = []
        self.stubbed_coords = set()
        self.wires = []
        self.labels = []
        self.hier_labels = []
        self.no_connects = []
        self.junctions = []
        self.texts = []
        pass
        self.stubbed_coords = set()

    def _ensure_lib(self, lib_id: str):
        if lib_id not in self.used_lib_ids:
            self.used_lib_ids.append(lib_id)

    def add_text(self, text: str, x: float, y: float, size=2.54):
        seed = f"{self.filename}.text.{len(self.texts)}.{text}"
        self.texts.append(
            f"""	(text "{text}"
		(exclude_from_sim no)
		(at {fmt_num(x)} {fmt_num(y)} 0)
		(effects
			(font
				(size {fmt_num(size)} {fmt_num(size)})
				(bold yes)
			)
			(justify left bottom)
		)
		(uuid "{det_uuid(seed)}")
	)"""
        )

    def place_sym(
        self,
        lib_id: str,
        ref: str,
        val: str,
        footprint: str,
        x: float,
        y: float,
        rot: int = 0,
        unit: int = 1,
        alt_refs: dict = None,
        in_bom: str = "yes",
    ):
        self._ensure_lib(lib_id)
        _, pins_by_unit = self.cache.get_symbol_and_pins(lib_id)
        unit_pins = {}
        if 0 in pins_by_unit:
            unit_pins.update(pins_by_unit[0])
        if unit in pins_by_unit:
            unit_pins.update(pins_by_unit[unit])
        if not ref.startswith("#") and footprint:
            SchematicBuilder.all_placed_components.append((self.filename, ref, lib_id, footprint, sorted(list(unit_pins.keys()))))

        # Compute exact schematic coordinates for every pin in this unit
        rad = math.radians(rot)
        cos_r = round(math.cos(rad))
        sin_r = round(math.sin(rad))
        transformed_pins = {}
        for pnum, pinfo in unit_pins.items():
            px, py, pang = pinfo["x"], pinfo["y"], pinfo["ang"]
            rx = px * cos_r - py * sin_r
            ry = px * sin_r + py * cos_r
            sch_x = round(x + rx, 2)
            sch_y = round(y - ry, 2)
            out_ang_sym = int(round(pang + 180 + rot)) % 360
            if out_ang_sym == 0:
                dx, dy, lbl_ang = 1, 0, 0
            elif out_ang_sym == 180:
                dx, dy, lbl_ang = -1, 0, 180
            elif out_ang_sym == 90:
                dx, dy, lbl_ang = 0, -1, 90
            else:
                dx, dy, lbl_ang = 0, 1, 270
            transformed_pins[pnum] = {
                "x": sch_x,
                "y": sch_y,
                "dx": dx,
                "dy": dy,
                "lbl_ang": lbl_ang,
                "name": pinfo["name"],
                "type": pinfo["type"],
            }

        seed = f"{self.filename}.sym.{ref}.u{unit}.{len(self.symbols)}"
        sym_uuid = det_uuid(seed)

        # Position Reference & Value cleanly without overlapping pins or vertical wire stubs
        hide_ref = "yes" if ref.startswith("#") else "no"
        ref_just = ""
        is_two_pin = len(transformed_pins) == 2 and not lib_id.startswith("Connector:")
        is_vert_two_pin = is_two_pin and all(p["dx"] == 0 for p in transformed_pins.values())
        is_horiz_two_pin = is_two_pin and all(p["dy"] == 0 for p in transformed_pins.values())
        if lib_id.startswith("power:"):
            ref_x, ref_y = x, (y + 3.81 if val == "GND" else y - 3.81)
            val_x, val_y = x, (y + 2.54 if val == "GND" else y - 2.54)
        elif is_vert_two_pin:
            # Vertical 2-pin passive (R, C, D, LED, etc.): place Reference & Value to the right of body
            ref_x, ref_y = round(x + 2.54, 2), round(y - 1.27, 2)
            val_x, val_y = round(x + 2.54, 2), round(y + 1.27, 2)
            ref_just = "\n\t\t\t\t(justify left)"
        elif is_horiz_two_pin:
            # Horizontal 2-pin passive (Fuse, L, series R, etc.): place Reference above and Value below body
            ref_x, ref_y = x, round(y - 3.81, 2)
            val_x, val_y = x, round(y + 3.81, 2)
        else:
            # Multi-pin IC, MOSFET, Relay, or Connector: place Reference above top edge and Value below bottom edge
            ys = [p["y"] for p in transformed_pins.values()] if transformed_pins else [y]
            min_y = min(ys + [y - 3.81])
            max_y = max(ys + [y + 3.81])
            has_top_pin = any(p["dy"] == -1 for p in transformed_pins.values())
            has_bot_pin = any(p["dy"] == 1 for p in transformed_pins.values())
            ref_x = round(x + 3.81, 2) if has_top_pin else x
            val_x = round(x + 3.81, 2) if has_bot_pin else x
            ref_y = round(min_y - 3.81, 2)
            val_y = round(max_y + 3.81, 2)
            if has_top_pin or has_bot_pin:
                ref_just = "\n\t\t\t\t(justify left)"

        inst_lines = []
        for path_str, path_idx in self.sheet_paths:
            inst_ref = alt_refs[path_idx] if (alt_refs and path_idx in alt_refs) else ref
            inst_lines.append(
                f"""				(path "{path_str}"
					(reference "{inst_ref}")
					(unit {unit})
				)"""
            )
        instances_block = "\n".join(inst_lines)

        pin_uuids = []
        for pnum in sorted(unit_pins.keys()):
            p_uuid = det_uuid(f"{seed}.pin.{pnum}")
            pin_uuids.append(f'\t\t(pin "{pnum}"\n\t\t\t(uuid "{p_uuid}")\n\t\t)')
        pins_block = "\n".join(pin_uuids)

        sym_sexp = f"""	(symbol
		(lib_id "{lib_id}")
		(at {fmt_num(x)} {fmt_num(y)} {rot})
		(unit {unit})
		(exclude_from_sim no)
		(in_bom {in_bom})
		(on_board yes)
		(dnp no)
		(fields_autoplaced yes)
		(uuid "{sym_uuid}")
		(property "Reference" "{ref}"
			(at {fmt_num(ref_x)} {fmt_num(ref_y)} 0)
			(effects
				(font
					(size 1.27 1.27)
				){ref_just}
				(hide {hide_ref})
			)
		)
		(property "Value" "{val}"
			(at {fmt_num(val_x)} {fmt_num(val_y)} 0)
			(effects
				(font
					(size 1.27 1.27)
				){ref_just}
			)
		)
		(property "Footprint" "{footprint}"
			(at {fmt_num(x)} {fmt_num(y)} 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
		(property "Datasheet" "~"
			(at {fmt_num(x)} {fmt_num(y)} 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(hide yes)
			)
		)
{pins_block}
		(instances
			(project "abx-motion"
{instances_block}
			)
		)
	)"""
        self.symbols.append(sym_sexp)
        return {"ref": ref, "x": x, "y": y, "pins": transformed_pins}

    def add_wire(self, x1: float, y1: float, x2: float, y2: float):
        if abs(x1 - x2) < 1e-4 and abs(y1 - y2) < 1e-4:
            return
        seed = f"{self.filename}.wire.{len(self.wires)}.{x1}.{y1}.{x2}.{y2}"
        self.wires.append(
            f"""	(wire
		(pts
			(xy {fmt_num(x1)} {fmt_num(y1)}) (xy {fmt_num(x2)} {fmt_num(y2)})
		)
		(stroke
			(width 0)
			(type default)
		)
		(uuid "{det_uuid(seed)}")
	)"""
        )

    def add_junction(self, x: float, y: float):
        seed = f"{self.filename}.junc.{len(self.junctions)}.{x}.{y}"
        self.junctions.append(
            f"""	(junction
		(at {fmt_num(x)} {fmt_num(y)})
		(diameter 0)
		(color 0 0 0 0)
		(uuid "{det_uuid(seed)}")
	)"""
        )

    def add_label(self, net: str, x: float, y: float, ang: int = 0):
        just = "left bottom"
        if ang == 180:
            just = "right bottom"
        elif ang == 90:
            just = "left bottom"
        elif ang == 270:
            just = "right bottom"
        seed = f"{self.filename}.lbl.{len(self.labels)}.{net}.{x}.{y}"
        self.labels.append(
            f"""	(label "{net}"
		(at {fmt_num(x)} {fmt_num(y)} {ang})
		(fields_autoplaced yes)
		(effects
			(font
				(size 1.27 1.27)
			)
			(justify {just})
		)
		(uuid "{det_uuid(seed)}")
	)"""
        )

    def add_hier_label(self, net: str, shape: str, x: float, y: float, ang: int = 0):
        just = "left" if ang in (0, 90) else "right"
        seed = f"{self.filename}.hlbl.{len(self.hier_labels)}.{net}.{x}.{y}"
        self.hier_labels.append(
            f"""	(hierarchical_label "{net}"
		(shape {shape})
		(at {fmt_num(x)} {fmt_num(y)} {ang})
		(fields_autoplaced yes)
		(effects
			(font
				(size 1.27 1.27)
			)
			(justify {just})
		)
		(uuid "{det_uuid(seed)}")
	)"""
        )

    def stub_net(self, sym: dict, pin_num: str, net: str, length: float = 5.08, hier_shape: str = None):
        p = sym["pins"][str(pin_num)]
        key = (p["x"], p["y"])
        ex = round(p["x"] + p["dx"] * length, 2)
        ey = round(p["y"] + p["dy"] * length, 2)
        if key not in self.stubbed_coords:
            self.stubbed_coords.add(key)
            self.add_wire(p["x"], p["y"], ex, ey)
            if hier_shape:
                self.add_hier_label(net, hier_shape, ex, ey, p["lbl_ang"])
            else:
                self.add_label(net, ex, ey, p["lbl_ang"])

    def stub_power(self, sym: dict, pin_num: str, pwr_name: str, length: float = 3.81):
        p = sym["pins"][str(pin_num)]
        key = (p["x"], p["y"])
        if key in self.stubbed_coords:
            return
        self.stubbed_coords.add(key)
        ex = round(p["x"] + p["dx"] * length, 2)
        ey = round(p["y"] + p["dy"] * length, 2)
        self.add_wire(p["x"], p["y"], ex, ey)
        rot = 0
        if p["dx"] == 1:
            rot = 90 if pwr_name == "GND" else 270
        elif p["dx"] == -1:
            rot = 270 if pwr_name == "GND" else 90
        elif p["dy"] == -1 and pwr_name == "GND":
            rot = 180
        elif p["dy"] == 1 and pwr_name != "GND":
            rot = 180
        ref_num = SchematicBuilder.pwr_counter
        SchematicBuilder.pwr_counter += 1
        alt_refs = None
        if len(self.sheet_paths) > 1:
            alt_refs = {0: f"#PWR{ref_num:03d}", 1: f"#PWR{ref_num + 500:03d}"}
        self.place_sym(f"power:{pwr_name}", f"#PWR{ref_num:03d}", pwr_name, "", ex, ey, rot, 1, alt_refs=alt_refs)

    def place_power_flag(self, pwr_name: str, x: float, y: float):
        ref1 = SchematicBuilder.pwr_counter
        SchematicBuilder.pwr_counter += 1
        ref2 = SchematicBuilder.pwr_counter
        SchematicBuilder.pwr_counter += 1
        self.place_sym(f"power:{pwr_name}", f"#PWR{ref1:03d}", pwr_name, "", x, y, 0, 1)
        wy = round(y + 2.54, 2) if pwr_name != "GND" else round(y - 2.54, 2)
        self.add_wire(x, y, x, wy)
        self.place_sym("power:PWR_FLAG", f"#FLG{ref2:03d}", "PWR_FLAG", "", x, wy, 0, 1)

    def no_conn(self, sym: dict, pin_num: str):
        p = sym["pins"][str(pin_num)]
        key = (p["x"], p["y"])
        if key in self.stubbed_coords:
            return
        self.stubbed_coords.add(key)
        seed = f"{self.filename}.nc.{len(self.no_connects)}.{p['x']}.{p['y']}"
        self.no_connects.append(
            f"""	(no_connect
		(at {fmt_num(p['x'])} {fmt_num(p['y'])})
		(uuid "{det_uuid(seed)}")
	)"""
        )

    def save(self):
        lib_sexps = []
        for lib_id in self.used_lib_ids:
            flat_sym, _ = self.cache.get_symbol_and_pins(lib_id)
            lib_sexps.append(format_sexp(flat_sym, indent=2))
        lib_block = "\n".join(lib_sexps)
        body = "\n".join(
            self.texts
            + self.junctions
            + self.no_connects
            + self.wires
            + self.labels
            + self.hier_labels
            + self.symbols
        )
        out = f"""(kicad_sch
	(version 20250114)
	(generator "eeschema")
	(generator_version "10.0")
	(uuid "{self.file_uuid}")
	(paper "{self.paper}")
	(lib_symbols
{lib_block}
	)
{body}
	(embedded_fonts no)
)
"""
        with open(os.path.join(PROJECT_DIR, self.filename), "w", encoding="utf-8") as f:
            f.write(out)


def build_power_sheet(cache: SymbolLibraryCache):
    path = f"/{ROOT_UUID}/{SHEET_UUIDS['Power']}"
    sb = SchematicBuilder("Power.kicad_sch", cache, [(path, 0)], paper="A3")
    sb.add_text("SHEET 1: BATTERY INPUT, REVERSE POLARITY PROTECTION, 5V BUCK & 3.3V LDO", 25.4, 20.32, 3.0)

    # Power flags for +BATT, +5V, GND
    sb.place_power_flag("+BATT", 30.48, 35.56)
    sb.place_power_flag("+5V", 45.72, 35.56)
    sb.place_power_flag("GND", 60.96, 35.56)

    # 1. Input connector J1 & Fuse F1 & Reverse Polarity P-MOSFET Q1
    j1 = sb.place_sym("Connector:Conn_01x02_Pin", "J1", "XT60_BAT", "Connector_AMASS:AMASS_XT60-M_1x02_P7.20mm_Vertical", 40.64, 71.12, 0)
    sb.stub_net(j1, "1", "V_RAW_IN")
    sb.stub_power(j1, "2", "GND")

    f1 = sb.place_sym("Device:Fuse", "F1", "25A", "abx-footprints:Fuseholder_Keystone_3557-2", 71.12, 71.12, 90)
    sb.stub_net(f1, "1", "V_RAW_IN")
    sb.stub_net(f1, "2", "V_FUSED")

    q1 = sb.place_sym("abx:AONS21357", "Q1", "SQJ459EP-T1_GE3", "Package_TO_SOT_SMD:TDSON-8-1", 114.3, 71.12, 0)
    sb.stub_net(q1, "4", "Q1_GATE")
    sb.stub_net(q1, "5", "V_FUSED")
    for spin in ["1", "2", "3"]:
        sb.stub_power(q1, spin, "+BATT")

    d1 = sb.place_sym("Device:D_Zener", "D1", "BZT52C12S", "Diode_SMD:D_SOD-323", 114.3, 96.52, 270)
    sb.stub_power(d1, "1", "+BATT")
    sb.stub_net(d1, "2", "Q1_GATE")

    r1 = sb.place_sym("Device:R", "R1", "47k", "Resistor_SMD:R_0603_1608Metric", 114.3, 121.92, 0)
    sb.stub_net(r1, "1", "Q1_GATE")
    sb.stub_power(r1, "2", "GND")

    d2 = sb.place_sym("Device:D_TVS", "D2", "SMCJ30A", "Diode_SMD:D_SMC", 142.24, 71.12, 270)
    sb.stub_power(d2, "1", "+BATT")
    sb.stub_power(d2, "2", "GND")

    # 2. VBAT_SENSE Divider (R2 100k, R3 10k, C1 100nF)
    r2 = sb.place_sym("Device:R", "R2", "100k", "Resistor_SMD:R_0603_1608Metric", 167.64, 66.04, 0)
    sb.stub_power(r2, "1", "+BATT")
    sb.stub_net(r2, "2", "VBAT_SENSE", hier_shape="output")

    r3 = sb.place_sym("Device:R", "R3", "10k", "Resistor_SMD:R_0603_1608Metric", 167.64, 91.44, 0)
    sb.stub_net(r3, "1", "VBAT_SENSE")
    sb.stub_power(r3, "2", "GND")

    c1 = sb.place_sym("Device:C", "C1", "100nF", "Capacitor_SMD:C_0603_1608Metric", 193.04, 91.44, 0)
    sb.stub_net(c1, "1", "VBAT_SENSE")
    sb.stub_power(c1, "2", "GND")

    # 3. 65V -> 5V 2A Buck (U1 LMR36520FADDA)
    u1 = sb.place_sym(
        "Regulator_Switching:LMR33630ADDA",
        "U1",
        "LMR36520FADDA",
        "Package_SO:Texas_HSOP-8-1EP_3.9x4.9mm_P1.27mm_ThermalVias",
        254.0,
        76.2,
        0,
    )
    sb.stub_power(u1, "2", "+BATT", length=6.35)
    sb.stub_power(u1, "3", "+BATT", length=6.35)
    sb.stub_net(u1, "6", "U1_VCC", length=6.35)
    sb.stub_power(u1, "1", "GND", length=5.08)
    sb.stub_power(u1, "9", "GND", length=5.08)
    sb.stub_net(u1, "7", "U1_BOOT", length=6.35)
    sb.stub_net(u1, "8", "U1_SW", length=6.35)
    sb.stub_net(u1, "5", "U1_FB", length=6.35)
    sb.no_conn(u1, "4")

    # Input decoupling C2, C3 (4.7uF 50V 1206), C4 (100nF 50V 0603)
    for idx, (cref, cval, cfp) in enumerate([
        ("C2", "4.7uF", "Capacitor_SMD:C_1206_3216Metric"),
        ("C3", "4.7uF", "Capacitor_SMD:C_1206_3216Metric"),
        ("C4", "100nF", "Capacitor_SMD:C_0603_1608Metric"),
    ]):
        c_in = sb.place_sym("Device:C", cref, cval, cfp, 40.64 + idx * 25.4, 152.4, 0)
        sb.stub_power(c_in, "1", "+BATT")
        sb.stub_power(c_in, "2", "GND")

    # VCC cap C5 (1uF 16V 0603) & BOOT cap C6 (100nF 50V 0603) & Inductor L1 (15uH)
    c5 = sb.place_sym("Device:C", "C5", "1uF", "Capacitor_SMD:C_0603_1608Metric", 116.84, 152.4, 0)
    sb.stub_net(c5, "1", "U1_VCC")
    sb.stub_power(c5, "2", "GND")

    c6 = sb.place_sym("Device:C", "C6", "100nF", "Capacitor_SMD:C_0603_1608Metric", 142.24, 152.4, 0)
    sb.stub_net(c6, "1", "U1_BOOT")
    sb.stub_net(c6, "2", "U1_SW")

    l1 = sb.place_sym("Device:L", "L1", "15uH", "Inductor_SMD:L_Bourns_SRP7028A_7.3x6.6mm", 304.8, 76.2, 90)
    sb.stub_net(l1, "1", "U1_SW")
    sb.stub_power(l1, "2", "+5V")

    # Feedback divider R4 (100k to +5V), R5 (24.9k to GND) & Output caps C7, C8 (22uF 16V 1206)
    r4 = sb.place_sym("Device:R", "R4", "100k", "Resistor_SMD:R_0603_1608Metric", 172.72, 144.78, 0)
    sb.stub_power(r4, "1", "+5V")
    sb.stub_net(r4, "2", "U1_FB")

    r5 = sb.place_sym("Device:R", "R5", "24.9k", "Resistor_SMD:R_0603_1608Metric", 172.72, 170.18, 0)
    sb.stub_net(r5, "1", "U1_FB")
    sb.stub_power(r5, "2", "GND")

    for idx, cref in enumerate(["C7", "C8"]):
        c_out = sb.place_sym("Device:C", cref, "22uF", "Capacitor_SMD:C_1206_3216Metric", 203.2 + idx * 25.4, 152.4, 0)
        sb.stub_power(c_out, "1", "+5V")
        sb.stub_power(c_out, "2", "GND")

    # 4. 3.3V LDO U2 (AP2112K-3.3) with C9 (1uF 0603) and C10 (10uF 0805)
    u2 = sb.place_sym("Regulator_Linear:AP2112K-3.3", "U2", "AP2112K-3.3", "Package_TO_SOT_SMD:SOT-23-5", 284.48, 152.4, 0)
    sb.stub_power(u2, "1", "+5V", length=6.35)
    sb.stub_power(u2, "3", "+5V", length=6.35)
    sb.stub_power(u2, "2", "GND", length=5.08)
    sb.no_conn(u2, "4")
    sb.stub_power(u2, "5", "+3V3", length=6.35)

    c9 = sb.place_sym("Device:C", "C9", "1uF", "Capacitor_SMD:C_0603_1608Metric", 330.2, 152.4, 0)
    sb.stub_power(c9, "1", "+5V")
    sb.stub_power(c9, "2", "GND")

    c10 = sb.place_sym("Device:C", "C10", "10uF", "Capacitor_SMD:C_0805_2012Metric", 355.6, 152.4, 0)
    sb.stub_power(c10, "1", "+3V3")
    sb.stub_power(c10, "2", "GND")

    # 5. Power Rail Status LEDs: LED_PWR_BATT (Green + 10k), LED_PWR_5V (Green + 1k), LED_PWR_3V3 (Green + 1k)
    pwr_leds = [
        ("+BATT", "R6", "10k", "LED_PWR_BATT1", "BATT_LED_A", 40.64),
        ("+5V", "R7", "1k", "LED_PWR_5V1", "5V_LED_A", 91.44),
        ("+3V3", "R8", "1k", "LED_PWR_3V3_1", "3V3_LED_A", 142.24),
    ]
    for rail, r_ref, r_val, led_ref, mid_net, lx in pwr_leds:
        r_led = sb.place_sym("Device:R", r_ref, r_val, "Resistor_SMD:R_0603_1608Metric", lx, 210.82, 0)
        sb.stub_power(r_led, "1", rail)
        sb.stub_net(r_led, "2", mid_net)
        d_led = sb.place_sym("Device:LED", led_ref, "LED_GRN", "LED_SMD:LED_0603_1608Metric", lx, 236.22, 90)
        sb.stub_net(d_led, "2", mid_net)
        sb.stub_power(d_led, "1", "GND")

    # 6. Hardware E-Stop Terminal J102 (switches +3V3 onto +3V3_DRV_EN for motor/stepper driver sleep pullups) + R9 10k pull-down
    j102 = sb.place_sym(
        "Connector:Conn_01x02_Pin",
        "J102",
        "E_STOP",
        "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal",
        198.12,
        215.9,
        0,
    )
    sb.stub_power(j102, "1", "+3V3")
    sb.stub_net(j102, "2", "+3V3_DRV_EN", hier_shape="output")

    r9 = sb.place_sym("Device:R", "R9", "10k", "Resistor_SMD:R_0603_1608Metric", 198.12, 246.38, 0)
    sb.stub_net(r9, "1", "+3V3_DRV_EN")
    sb.stub_power(r9, "2", "GND")

    # 7. Bench Test Points (TP_GND1, TP_GND2, TP_BATT, TP_5V, TP_3V3)
    tps = [
        ("TP_GND1", "GND", 243.84, 215.9),
        ("TP_GND2", "GND", 264.16, 215.9),
        ("TP_BATT1", "+BATT", 284.48, 215.9),
        ("TP_5V1", "+5V", 304.8, 215.9),
        ("TP_3V3_1", "+3V3", 325.12, 215.9),
    ]
    for tp_ref, tp_rail, tx, ty in tps:
        tp_sym = sb.place_sym("Connector:TestPoint", tp_ref, tp_ref, "TestPoint:TestPoint_Pad_D1.5mm", tx, ty, 0)
        sb.stub_power(tp_sym, "1", tp_rail)

    # 8. Mounting Holes H1-H4 (connected to GND) & Branding Logos LOGO1, LOGO2 (in_bom no)
    for idx, href in enumerate(["H1", "H2", "H3", "H4"]):
        h_sym = sb.place_sym(
            "Mechanical:MountingHole_Pad",
            href,
            "M3_Mount",
            "MountingHole:MountingHole_3.2mm_M3_Pad_Via",
            243.84 + idx * 25.4,
            254.0,
            0,
        )
        sb.stub_power(h_sym, "1", "GND")

    sb.place_sym("abx:ABX_Logo", "LOGO1", "ABX_Logo_Gears_Gold", "abx-footprints:ABX_Logo_Gears_Gold", 355.6, 215.9, 0, in_bom="no")
    sb.place_sym("abx:ABX_Logo", "LOGO2", "ABX_Text_Gold", "abx-footprints:ABX_Text_Gold", 355.6, 254.0, 0, in_bom="no")

    sb.save()


def build_mcu_sheet(cache: SymbolLibraryCache):
    path = f"/{ROOT_UUID}/{SHEET_UUIDS['MCU']}"
    sb = SchematicBuilder("MCU.kicad_sch", cache, [(path, 0)], paper="A3")
    sb.add_text("SHEET 2: ESP32-S3-WROOM-1, USB-C, 74LVC14A ENCODERS, CAN, RS-485, OLED & UI BUTTONS", 25.4, 15.24, 3.0)

    # U3: ESP32-S3-WROOM-1
    u3 = sb.place_sym("RF_Module:ESP32-S3-WROOM-1", "U3", "ESP32-S3-WROOM-1-N8R2", "RF_Module:ESP32-S3-WROOM-1", 88.9, 88.9, 0)
    sb.stub_power(u3, "2", "+3V3", length=5.08)
    sb.stub_power(u3, "1", "GND", length=5.08)
    sb.stub_power(u3, "40", "GND", length=5.08)
    sb.stub_power(u3, "41", "GND", length=5.08)

    # Left side pins of U3
    sb.stub_net(u3, "3", "ESP_EN", length=7.62)
    sb.stub_net(u3, "27", "ESP_BOOT", length=7.62)
    sb.stub_net(u3, "39", "VBAT_SENSE", length=7.62, hier_shape="input")
    sb.stub_net(u3, "38", "M2_nFAULT", length=7.62, hier_shape="input")
    sb.stub_net(u3, "15", "LED_STAT", length=7.62)  # GPIO 3 Heartbeat LED
    sb.stub_net(u3, "4", "M1_PWM_PH", length=7.62, hier_shape="output")
    sb.stub_net(u3, "5", "M1_PWM_EN", length=7.62, hier_shape="output")
    sb.stub_net(u3, "6", "M1_CS", length=7.62, hier_shape="input")
    sb.stub_net(u3, "7", "M1_nFAULT", length=7.62, hier_shape="input")
    sb.stub_net(u3, "12", "M2_CS", length=7.62, hier_shape="input")
    sb.stub_net(u3, "17", "ENC2_A", length=7.62)
    sb.stub_net(u3, "18", "ENC2_B", length=7.62)
    sb.stub_net(u3, "19", "STEP1_PUL", length=7.62, hier_shape="output")
    sb.stub_net(u3, "20", "STEP1_DIR", length=7.62, hier_shape="output")
    sb.stub_net(u3, "21", "STEP2_PUL", length=7.62, hier_shape="output")
    sb.stub_net(u3, "22", "STEP2_DIR", length=7.62, hier_shape="output")
    sb.stub_net(u3, "8", "ENC1_A", length=7.62)
    sb.stub_net(u3, "9", "ENC1_B", length=7.62)

    # Right side pins of U3 (All expansion pins connected!)
    sb.stub_net(u3, "37", "RS485_TX", length=7.62)      # GPIO 43 (TXD0)
    sb.stub_net(u3, "36", "RS485_RX", length=7.62)      # GPIO 44 (RXD0)
    sb.stub_net(u3, "10", "M2_PWM_PH", length=7.62, hier_shape="output")
    sb.stub_net(u3, "11", "M2_PWM_EN", length=7.62, hier_shape="output")
    sb.stub_net(u3, "13", "USB_DN", length=7.62)
    sb.stub_net(u3, "14", "USB_DP", length=7.62)
    sb.stub_net(u3, "23", "BTN_BACK", length=7.62)      # GPIO 21 (moved from GPIO 36)
    sb.stub_net(u3, "28", "RS485_DIR", length=7.62)     # GPIO 35
    sb.stub_net(u3, "29", "IO_INT_N", length=7.62, hier_shape="input")  # GPIO 36 (~INT from PCA9555PW)
    sb.stub_net(u3, "30", "BTN_NEXT", length=7.62)      # GPIO 37
    sb.stub_net(u3, "31", "CAN_TX", length=7.62)        # GPIO 38
    sb.stub_net(u3, "32", "CAN_RX", length=7.62)        # GPIO 39
    sb.stub_net(u3, "33", "BTN_HOME", length=7.62)      # GPIO 40
    sb.stub_net(u3, "34", "I2C_SDA", length=7.62, hier_shape="bidirectional")  # GPIO 41
    sb.stub_net(u3, "35", "I2C_SCL", length=7.62, hier_shape="output")         # GPIO 42
    sb.no_conn(u3, "26")                                # IO45 strapping pin unused
    sb.no_conn(u3, "16")                                # IO46 strapping pin unused
    sb.stub_net(u3, "24", "RELAY_1", length=7.62, hier_shape="output")
    sb.stub_net(u3, "25", "RELAY_2", length=7.62, hier_shape="output")

    # U3 Decoupling caps C201 (10uF 0805), C202 (100nF 0603)
    c201 = sb.place_sym("Device:C", "C201", "10uF", "Capacitor_SMD:C_0805_2012Metric", 35.56, 152.4, 0)
    sb.stub_power(c201, "1", "+3V3")
    sb.stub_power(c201, "2", "GND")

    c202 = sb.place_sym("Device:C", "C202", "100nF", "Capacitor_SMD:C_0603_1608Metric", 60.96, 152.4, 0)
    sb.stub_power(c202, "1", "+3V3")
    sb.stub_power(c202, "2", "GND")

    # Reset (EN) & Boot (GPIO0) circuits
    r203 = sb.place_sym("Device:R", "R203", "10k", "Resistor_SMD:R_0603_1608Metric", 86.36, 152.4, 0)
    sb.stub_power(r203, "1", "+3V3")
    sb.stub_net(r203, "2", "ESP_EN")

    c203 = sb.place_sym("Device:C", "C203", "100nF", "Capacitor_SMD:C_0603_1608Metric", 111.76, 152.4, 0)
    sb.stub_net(c203, "1", "ESP_EN")
    sb.stub_power(c203, "2", "GND")

    sw201 = sb.place_sym("Switch:SW_Push", "SW201", "RESET", "Button_Switch_SMD:SW_SPST_B3U-1000P", 88.9, 182.88, 0)
    sb.stub_net(sw201, "1", "ESP_EN")
    sb.stub_power(sw201, "2", "GND")

    c204 = sb.place_sym("Device:C", "C204", "100nF", "Capacitor_SMD:C_0603_1608Metric", 137.16, 152.4, 0)
    sb.stub_net(c204, "1", "ESP_BOOT")
    sb.stub_power(c204, "2", "GND")

    sw202 = sb.place_sym("Switch:SW_Push", "SW202", "BOOT", "Button_Switch_SMD:SW_SPST_B3U-1000P", 137.16, 182.88, 0)
    sb.stub_net(sw202, "1", "ESP_BOOT")
    sb.stub_power(sw202, "2", "GND")

    # USB-C Receptacle J201 + 2x 5.1k CC resistors + USBLC6-2SC6 ESD
    j201 = sb.place_sym(
        "Connector:USB_C_Receptacle_USB2.0_16P",
        "J201",
        "USB-C",
        "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
        167.64,
        68.58,
        0,
    )
    for gpin in ["S1", "A1", "A12", "B1", "B12"]:
        sb.stub_power(j201, gpin, "GND")
    for vpin in ["A4", "A9", "B4", "B9"]:
        sb.stub_net(j201, vpin, "VBUS_USB", length=6.35)
    sb.stub_net(j201, "A5", "USB_CC1", length=6.35)
    sb.stub_net(j201, "B5", "USB_CC2", length=6.35)
    sb.stub_net(j201, "A7", "USB_CONN_DN", length=6.35)
    sb.stub_net(j201, "B7", "USB_CONN_DN", length=6.35)
    sb.stub_net(j201, "A6", "USB_CONN_DP", length=6.35)
    sb.stub_net(j201, "B6", "USB_CONN_DP", length=6.35)
    sb.no_conn(j201, "A8")
    sb.no_conn(j201, "B8")

    r201 = sb.place_sym("Device:R", "R201", "5.1k", "Resistor_SMD:R_0603_1608Metric", 170.18, 127.0, 0)
    sb.stub_net(r201, "1", "USB_CC1")
    sb.stub_power(r201, "2", "GND")

    r202 = sb.place_sym("Device:R", "R202", "5.1k", "Resistor_SMD:R_0603_1608Metric", 195.58, 127.0, 0)
    sb.stub_net(r202, "1", "USB_CC2")
    sb.stub_power(r202, "2", "GND")

    u201 = sb.place_sym("Power_Protection:USBLC6-2SC6", "U201", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6", 228.6, 68.58, 0)
    sb.stub_net(u201, "1", "USB_CONN_DN", length=6.35)
    sb.stub_net(u201, "3", "USB_CONN_DP", length=6.35)
    sb.stub_net(u201, "5", "VBUS_USB", length=5.08)
    sb.stub_power(u201, "2", "GND", length=5.08)
    sb.stub_net(u201, "6", "USB_DN", length=6.35)
    sb.stub_net(u201, "4", "USB_DP", length=6.35)

    # Resettable Polyfuse F2 (500mA_PTC) & USB-C VBUS Schottky Diode D202 (B5819W, SOD-123: Anode=VBUS_FUSED, Cathode=+5V)
    f2 = sb.place_sym("Device:Polyfuse", "F2", "500mA_PTC", "Fuse:Fuse_1206_3216Metric", 215.9, 104.14, 0)
    sb.stub_net(f2, "1", "VBUS_USB")
    sb.stub_net(f2, "2", "VBUS_FUSED")

    d202 = sb.place_sym("Device:D_Schottky", "D202", "B5819W", "Diode_SMD:D_SOD-123", 228.6, 127.0, 270)
    sb.stub_power(d202, "1", "+5V")
    sb.stub_net(d202, "2", "VBUS_FUSED")

    # Pull-ups and Pull-downs required by GEMINI.md
    pull_configs = [
        ("R204", "10k", "M1_PWM_EN", "GND"),
        ("R205", "10k", "M2_PWM_EN", "GND"),
        ("R206", "10k", "IO_INT_N", "+3V3"),
        ("R207", "10k", "RELAY_1", "GND"),
        ("R208", "10k", "RELAY_2", "GND"),
        ("R209", "10k", "M1_nFAULT", "+3V3"),
        ("R210", "10k", "M2_nFAULT", "+3V3"),
        ("R231", "10k", "RS485_DIR", "GND"),
        ("R232", "10k", "CAN_TX", "+3V3"),
    ]
    for idx, (rref, rval, sig_net, pwr_net) in enumerate(pull_configs):
        rx = 165.1 + idx * 20.32
        ry = 167.64
        r_sym = sb.place_sym("Device:R", rref, rval, "Resistor_SMD:R_0603_1608Metric", rx, ry, 0)
        if pwr_net == "+3V3":
            sb.stub_power(r_sym, "1", "+3V3")
            sb.stub_net(r_sym, "2", sig_net)
        else:
            sb.stub_net(r_sym, "1", sig_net)
            sb.stub_power(r_sym, "2", "GND")

    # Resettable Polyfuse F3 (500mA_PTC) for +5V_ENC + Encoder connectors J202 (ENC1) and J203 (ENC2)
    f3 = sb.place_sym("Device:Polyfuse", "F3", "500mA_PTC", "Fuse:Fuse_1206_3216Metric", 243.84, 48.26, 0)
    sb.stub_power(f3, "1", "+5V")
    sb.stub_net(f3, "2", "+5V_ENC")

    j202 = sb.place_sym("Connector:Conn_01x04_Pin", "J202", "ENC1_CONN", "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical", 269.24, 48.26, 0)
    sb.stub_net(j202, "1", "+5V_ENC")
    sb.stub_net(j202, "2", "ENC1_A_RAW")
    sb.stub_net(j202, "3", "ENC1_B_RAW")
    sb.stub_power(j202, "4", "GND")

    j203 = sb.place_sym("Connector:Conn_01x04_Pin", "J203", "ENC2_CONN", "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical", 269.24, 88.9, 0)
    sb.stub_net(j203, "1", "+5V_ENC")
    sb.stub_net(j203, "2", "ENC2_A_RAW")
    sb.stub_net(j203, "3", "ENC2_B_RAW")
    sb.stub_power(j203, "4", "GND")

    # U4: 74LVC14A (using 74xx:74HC14 symbol, all 7 units placed!)
    enc_channels = [
        (1, "1", "2", "ENC1_A_RAW", "ENC1_A_FILT", "ENC1_A", "R211", "R212", "C205", 35.56),
        (2, "3", "4", "ENC1_B_RAW", "ENC1_B_FILT", "ENC1_B", "R213", "R214", "C206", 68.58),
        (3, "5", "6", "ENC2_A_RAW", "ENC2_A_FILT", "ENC2_A", "R215", "R216", "C207", 101.6),
        (4, "9", "8", "ENC2_B_RAW", "ENC2_B_FILT", "ENC2_B", "R217", "R218", "C208", 134.62),
    ]
    for unit_num, in_pin, out_pin, raw_net, filt_net, out_net, r_pu, r_ser, c_flt, cy in enc_channels:
        rpu = sb.place_sym("Device:R", r_pu, "4.7k", "Resistor_SMD:R_0603_1608Metric", 312.42, cy, 0)
        sb.stub_power(rpu, "1", "+5V")
        sb.stub_net(rpu, "2", raw_net)
        rser = sb.place_sym("Device:R", r_ser, "1k", "Resistor_SMD:R_0603_1608Metric", 340.36, cy, 90)
        sb.stub_net(rser, "1", raw_net)
        sb.stub_net(rser, "2", filt_net)
        cflt = sb.place_sym("Device:C", c_flt, "1nF", "Capacitor_SMD:C_0603_1608Metric", 368.3, cy, 0)
        sb.stub_net(cflt, "1", filt_net)
        sb.stub_power(cflt, "2", "GND")
        u4_gate = sb.place_sym("74xx:74HC14", "U4", "74LVC14A", "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm", 396.24, cy, 0, unit=unit_num)
        sb.stub_net(u4_gate, in_pin, filt_net)
        sb.stub_net(u4_gate, out_pin, out_net)

    # Units 5 & 6: Unused inputs (Pins 11, 13) tied to GND, outputs no_connect
    u4_u5 = sb.place_sym("74xx:74HC14", "U4", "74LVC14A", "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm", 368.3, 165.1, 0, unit=5)
    sb.stub_power(u4_u5, "11", "GND")
    sb.no_conn(u4_u5, "10")

    u4_u6 = sb.place_sym("74xx:74HC14", "U4", "74LVC14A", "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm", 396.24, 165.1, 0, unit=6)
    sb.stub_power(u4_u6, "13", "GND")
    sb.no_conn(u4_u6, "12")

    # Unit 7: Power pins (Pin 14 VCC -> +3V3, Pin 7 GND -> GND) + Decoupling cap C209
    u4_u7 = sb.place_sym("74xx:74HC14", "U4", "74LVC14A", "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm", 340.36, 165.1, 0, unit=7)
    sb.stub_power(u4_u7, "14", "+3V3")
    sb.stub_power(u4_u7, "7", "GND")

    c209 = sb.place_sym("Device:C", "C209", "100nF", "Capacitor_SMD:C_0603_1608Metric", 312.42, 165.1, 0)
    sb.stub_power(c209, "1", "+3V3")
    sb.stub_power(c209, "2", "GND")

    # =========================================================================
    # EXPANSION PERIPHERALS: CAN BUS, RS-485, OLED I2C, UI BUTTONS & HEARTBEAT
    # =========================================================================

    # 1. CAN Bus Transceiver U202 (TCAN1042V-Q1, SOIC-8) + 120R Term Jumper J204 + 3-Pin Terminal J205 + Activity LED201
    u202 = sb.place_sym(
        "Interface_CAN_LIN:CA-IF1042LVS",
        "U202",
        "TCAN1042V-Q1",
        "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        48.26,
        228.6,
        0,
    )
    sb.stub_net(u202, "1", "CAN_TX", length=6.35)
    sb.stub_power(u202, "2", "GND", length=5.08)
    sb.stub_power(u202, "3", "+5V", length=5.08)
    sb.stub_net(u202, "4", "CAN_RX", length=6.35)
    sb.stub_power(u202, "5", "+3V3", length=6.35)  # VIO
    sb.stub_net(u202, "6", "CAN_L", length=6.35)
    sb.stub_net(u202, "7", "CAN_H", length=6.35)
    sb.stub_power(u202, "8", "GND", length=6.35)   # STB -> GND (Normal high-speed mode)

    c210 = sb.place_sym("Device:C", "C210", "100nF", "Capacitor_SMD:C_0603_1608Metric", 20.32, 228.6, 0)
    sb.stub_power(c210, "1", "+5V")
    sb.stub_power(c210, "2", "GND")

    # CAN 120 Ohm Termination Jumper J204 + R219
    j204 = sb.place_sym("Connector:Conn_01x02_Pin", "J204", "CAN_TERM", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", 88.9, 215.9, 0)
    sb.stub_net(j204, "1", "CAN_H")
    sb.stub_net(j204, "2", "CAN_TERM_SW")

    r219 = sb.place_sym("Device:R", "R219", "120", "Resistor_SMD:R_0603_1608Metric", 88.9, 241.3, 0)
    sb.stub_net(r219, "1", "CAN_TERM_SW")
    sb.stub_net(r219, "2", "CAN_L")

    # CAN 3-Pin 5.08mm Terminal J205 (CAN_H, CAN_L, GND)
    j205 = sb.place_sym(
        "Connector:Conn_01x03_Pin",
        "J205",
        "CAN_BUS",
        "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-3-5.08_1x03_P5.08mm_Horizontal",
        119.38,
        218.44,
        0,
    )
    sb.stub_net(j205, "1", "CAN_H")
    sb.stub_net(j205, "2", "CAN_L")
    sb.stub_power(j205, "3", "GND")

    # CAN Activity LED201 (Yellow) on CAN_TX (Active-low dominant pulse indicator to +3V3)
    r220 = sb.place_sym("Device:R", "R220", "1k", "Resistor_SMD:R_0603_1608Metric", 119.38, 246.38, 0)
    sb.stub_power(r220, "1", "+3V3")
    sb.stub_net(r220, "2", "CAN_LED_A")

    led201 = sb.place_sym("Device:LED", "LED201", "LED_YEL_CAN", "LED_SMD:LED_0603_1608Metric", 119.38, 269.24, 90)
    sb.stub_net(led201, "2", "CAN_LED_A")
    sb.stub_net(led201, "1", "CAN_TX")

    # 2. RS-485 Transceiver U203 (THVD1450DR, SOIC-8) + 120R Term Jumper J206 + Fail-safe Bias + TVS + Terminal J207 + LED202
    u203 = sb.place_sym(
        "Interface_UART:LTC2850xS8",
        "U203",
        "THVD1450DR",
        "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        177.8,
        228.6,
        0,
    )
    sb.stub_net(u203, "1", "RS485_RX", length=6.35)
    sb.stub_net(u203, "2", "RS485_DIR", length=6.35)  # ~RE
    sb.stub_net(u203, "3", "RS485_DIR", length=6.35)  # DE
    sb.stub_net(u203, "4", "RS485_TX", length=6.35)
    sb.stub_power(u203, "5", "GND", length=5.08)
    sb.stub_net(u203, "6", "RS485_A", length=6.35)
    sb.stub_net(u203, "7", "RS485_B", length=6.35)
    sb.stub_power(u203, "8", "+3V3", length=5.08)

    c211 = sb.place_sym("Device:C", "C211", "100nF", "Capacitor_SMD:C_0603_1608Metric", 149.86, 228.6, 0)
    sb.stub_power(c211, "1", "+3V3")
    sb.stub_power(c211, "2", "GND")

    # RS-485 120 Ohm Termination Jumper J206 + R221
    j206 = sb.place_sym("Connector:Conn_01x02_Pin", "J206", "RS485_TERM", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", 215.9, 213.36, 0)
    sb.stub_net(j206, "1", "RS485_A")
    sb.stub_net(j206, "2", "RS485_TERM_SW")

    r221 = sb.place_sym("Device:R", "R221", "120", "Resistor_SMD:R_0603_1608Metric", 215.9, 238.76, 0)
    sb.stub_net(r221, "1", "RS485_TERM_SW")
    sb.stub_net(r221, "2", "RS485_B")

    # Fail-safe bias resistors: R222 (330R to +3V3 on A), R223 (330R to GND on B)
    r222 = sb.place_sym("Device:R", "R222", "330R", "Resistor_SMD:R_0603_1608Metric", 241.3, 213.36, 0)
    sb.stub_power(r222, "1", "+3V3")
    sb.stub_net(r222, "2", "RS485_A")

    r223 = sb.place_sym("Device:R", "R223", "330R", "Resistor_SMD:R_0603_1608Metric", 241.3, 238.76, 0)
    sb.stub_net(r223, "1", "RS485_B")
    sb.stub_power(r223, "2", "GND")

    # TVS Diode D201 across RS485_A and RS485_B + 3-Pin 5.08mm Terminal J207 (A, B, GND)
    d201 = sb.place_sym("Device:D_TVS", "D201", "SMBJ6.5CA", "Diode_SMD:D_SMB", 241.3, 264.16, 90)
    sb.stub_net(d201, "1", "RS485_A")
    sb.stub_net(d201, "2", "RS485_B")

    j207 = sb.place_sym(
        "Connector:Conn_01x03_Pin",
        "J207",
        "RS485_BUS",
        "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-3-5.08_1x03_P5.08mm_Horizontal",
        269.24,
        215.9,
        0,
    )
    sb.stub_net(j207, "1", "RS485_A")
    sb.stub_net(j207, "2", "RS485_B")
    sb.stub_power(j207, "3", "GND")

    # RS-485 Activity LED202 (Yellow) on RS485_TX
    r224 = sb.place_sym("Device:R", "R224", "1k", "Resistor_SMD:R_0603_1608Metric", 269.24, 243.84, 0)
    sb.stub_power(r224, "1", "+3V3")
    sb.stub_net(r224, "2", "RS485_LED_A")

    led202 = sb.place_sym("Device:LED", "LED202", "LED_YEL_485", "LED_SMD:LED_0603_1608Metric", 269.24, 266.7, 90)
    sb.stub_net(led202, "2", "RS485_LED_A")
    sb.stub_net(led202, "1", "RS485_TX")

    # 3. I2C OLED Socket J208 (1x4 2.54mm Female Header: 1=GND, 2=+3V3, 3=I2C_SCL, 4=I2C_SDA) + 4.7k Pull-ups
    j208 = sb.place_sym(
        "Connector:Conn_01x04_Socket",
        "J208",
        "OLED_I2C",
        "Connector_PinSocket_2.54mm:PinSocket_1x04_P2.54mm_Vertical",
        314.96,
        215.9,
        0,
    )
    sb.stub_power(j208, "1", "GND")
    sb.stub_power(j208, "2", "+3V3")
    sb.stub_net(j208, "3", "I2C_SCL")
    sb.stub_net(j208, "4", "I2C_SDA")

    r225 = sb.place_sym("Device:R", "R225", "4.7k", "Resistor_SMD:R_0603_1608Metric", 314.96, 246.38, 0)
    sb.stub_power(r225, "1", "+3V3")
    sb.stub_net(r225, "2", "I2C_SCL")

    r226 = sb.place_sym("Device:R", "R226", "4.7k", "Resistor_SMD:R_0603_1608Metric", 314.96, 269.24, 0)
    sb.stub_power(r226, "1", "+3V3")
    sb.stub_net(r226, "2", "I2C_SDA")

    # Resettable Polyfuse F4 (250mA_PTC) for +3V3_EXT + Parallel 4-pin JST-XH I2C Expansion Header J209
    f4 = sb.place_sym("Device:Polyfuse", "F4", "250mA_PTC", "Fuse:Fuse_1206_3216Metric", 292.1, 190.5, 0)
    sb.stub_power(f4, "1", "+3V3")
    sb.stub_net(f4, "2", "+3V3_EXT")

    j209 = sb.place_sym(
        "Connector:Conn_01x04_Pin",
        "J209",
        "I2C_EXP",
        "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical",
        292.1,
        215.9,
        0,
    )
    sb.stub_power(j209, "1", "GND")
    sb.stub_net(j209, "2", "+3V3_EXT")
    sb.stub_net(j209, "3", "I2C_SCL")
    sb.stub_net(j209, "4", "I2C_SDA")

    # 4. Navigation Buttons SW203 (Back), SW204 (Next), SW205 (Home) with 10k Pull-ups and 100nF Debounce Caps
    nav_buttons = [
        ("SW203", "BTN_BACK", "R227", "C212", 347.98),
        ("SW204", "BTN_NEXT", "R228", "C213", 373.38),
        ("SW205", "BTN_HOME", "R229", "C214", 398.78),
    ]
    for sw_ref, btn_net, r_ref, c_ref, bx in nav_buttons:
        r_pu = sb.place_sym("Device:R", r_ref, "10k", "Resistor_SMD:R_0603_1608Metric", bx, 210.82, 0)
        sb.stub_power(r_pu, "1", "+3V3")
        sb.stub_net(r_pu, "2", btn_net)

        c_db = sb.place_sym("Device:C", c_ref, "100nF", "Capacitor_SMD:C_0603_1608Metric", bx, 236.22, 0)
        sb.stub_net(c_db, "1", btn_net)
        sb.stub_power(c_db, "2", "GND")

        sw_b = sb.place_sym("Switch:SW_Push", sw_ref, btn_net, "Button_Switch_SMD:SW_SPST_B3U-1000P", bx, 264.16, 0)
        sb.stub_net(sw_b, "1", btn_net)
        sb.stub_power(sw_b, "2", "GND")

    # 5. Heartbeat LED203 (Blue) + 1k Resistor R230 on GPIO 3 (LED_STAT)
    r230 = sb.place_sym("Device:R", "R230", "1k", "Resistor_SMD:R_0603_1608Metric", 35.56, 185.42, 0)
    sb.stub_net(r230, "1", "LED_STAT")
    sb.stub_net(r230, "2", "STAT_LED_A")

    led203 = sb.place_sym("Device:LED", "LED203", "LED_BLU_STAT", "LED_SMD:LED_0603_1608Metric", 60.96, 185.42, 90)
    sb.stub_net(led203, "2", "STAT_LED_A")
    sb.stub_power(led203, "1", "GND")

    # 6. OLED M2 Support Holes H5 & H6 (23.0mm horizontal pitch centered at X=79.5mm -> 68.0mm and 91.0mm)
    sb.place_sym("Mechanical:MountingHole", "H5", "M2_OLED", "MountingHole:MountingHole_2.2mm_M2", 347.98, 185.42, 0, in_bom="no")
    sb.place_sym("Mechanical:MountingHole", "H6", "M2_OLED", "MountingHole:MountingHole_2.2mm_M2", 373.38, 185.42, 0, in_bom="no")

    sb.save()


def build_motor_channel_sheet(cache: SymbolLibraryCache):
    path1 = f"/{ROOT_UUID}/{SHEET_UUIDS['Motor1']}"
    path2 = f"/{ROOT_UUID}/{SHEET_UUIDS['Motor2']}"
    sb = SchematicBuilder("Motor_Channel.kicad_sch", cache, [(path1, 0), (path2, 1)], paper="A3")
    sb.add_text("SHEET 3: 100W BRUSHED DC SERVO CHANNEL (DRV8701ERGER + 4x CSD18540Q5B 60V H-BRIDGE)", 25.4, 17.78, 3.0)

    def mref(suffix: str):
        return f"{suffix[0]}3{suffix[1:]}", {0: f"{suffix[0]}3{suffix[1:]}", 1: f"{suffix[0]}4{suffix[1:]}"}

    # 1. DRV8701ERGER Pre-Driver (U301 / U401)
    r, alt = mref("U01")
    udrv = sb.place_sym(
        "abx:DRV8701ERGER",
        r,
        "DRV8701ERGER",
        "Package_DFN_QFN:Texas_RGE0024C_VQFN-24-1EP_4x4mm_P0.5mm_EP2.1x2.1mm_ThermalVias",
        76.2,
        78.74,
        0,
        alt_refs=alt,
    )
    sb.stub_power(udrv, "1", "+BATT", length=7.62)
    sb.stub_net(udrv, "2", "DRV_VCP", length=7.62)
    sb.stub_net(udrv, "3", "DRV_CPH", length=7.62)
    sb.stub_net(udrv, "4", "DRV_CPL", length=7.62)
    sb.stub_net(udrv, "7", "DRV_AVDD", length=7.62)
    sb.stub_net(udrv, "8", "DRV_DVDD", length=7.62)
    sb.stub_net(udrv, "6", "DRV_VREF", length=7.62)
    sb.stub_net(udrv, "13", "DRV_nSLEEP", length=7.62)
    sb.stub_net(udrv, "14", "PWM_EN", length=7.62, hier_shape="input")
    sb.stub_net(udrv, "15", "PWM_PH", length=7.62, hier_shape="input")
    sb.stub_net(udrv, "12", "DRV_IDRIVE", length=7.62)  # Configurable IDRIVE via 200k R312/R412 to GND
    sb.stub_power(udrv, "5", "GND", length=7.62)   # AGND

    # R12 (R312 / R412): 200k 0603 from DRV_IDRIVE (Pin 12) to GND -> 25mA/50mA gate drive & bench-tunable
    r, alt = mref("R12")
    r_idrv = sb.place_sym("Device:R", r, "200k", "Resistor_SMD:R_0603_1608Metric", 198.12, 175.26, 0, alt_refs=alt)
    sb.stub_net(r_idrv, "1", "DRV_IDRIVE")
    sb.stub_power(r_idrv, "2", "GND")

    sb.stub_net(udrv, "17", "GH1_RAW", length=7.62)
    sb.stub_net(udrv, "18", "MOT_OUT1", length=7.62)
    sb.stub_net(udrv, "19", "GL1_RAW", length=7.62)
    sb.stub_net(udrv, "24", "GH2_RAW", length=7.62)
    sb.stub_net(udrv, "23", "MOT_OUT2", length=7.62)
    sb.stub_net(udrv, "22", "GL2_RAW", length=7.62)
    sb.stub_net(udrv, "21", "SHUNT_SP", length=7.62)  # Pin 21 (SP) -> low-side MOSFET source node (top of R309)
    sb.stub_power(udrv, "20", "GND", length=7.62)     # Pin 20 (SN) -> GND Kelvin side of R309
    sb.stub_net(udrv, "11", "SO_RAW", length=7.62)
    sb.stub_net(udrv, "9", "nFAULT", length=7.62, hier_shape="output")
    sb.no_conn(udrv, "10")  # SNSOUT
    sb.stub_power(udrv, "16", "GND", length=7.62)  # PGND
    sb.stub_power(udrv, "25", "GND", length=7.62)  # EP

    # Charge pump & regulator passives:
    # CRITICAL: C01 (1uF 16V) from VCP (Pin 2) to VM (+BATT), NOT GND!
    r, alt = mref("C01")
    c_vcp = sb.place_sym("Device:C", r, "1uF", "Capacitor_SMD:C_0603_1608Metric", 38.1, 149.86, 0, alt_refs=alt)
    sb.stub_power(c_vcp, "1", "+BATT")
    sb.stub_net(c_vcp, "2", "DRV_VCP")

    # C02 (100nF 50V) between CPH and CPL
    r, alt = mref("C02")
    c_cp = sb.place_sym("Device:C", r, "100nF", "Capacitor_SMD:C_0603_1608Metric", 63.5, 149.86, 0, alt_refs=alt)
    sb.stub_net(c_cp, "1", "DRV_CPH")
    sb.stub_net(c_cp, "2", "DRV_CPL")

    # C03 (1uF 16V) AVDD to GND, C04 (1uF 16V) DVDD to GND
    r, alt = mref("C03")
    c_avdd = sb.place_sym("Device:C", r, "1uF", "Capacitor_SMD:C_0603_1608Metric", 88.9, 149.86, 0, alt_refs=alt)
    sb.stub_net(c_avdd, "1", "DRV_AVDD")
    sb.stub_power(c_avdd, "2", "GND")

    r, alt = mref("C04")
    c_dvdd = sb.place_sym("Device:C", r, "1uF", "Capacitor_SMD:C_0603_1608Metric", 114.3, 149.86, 0, alt_refs=alt)
    sb.stub_net(c_dvdd, "1", "DRV_DVDD")
    sb.stub_power(c_dvdd, "2", "GND")

    # VREF divider: R01 (18k to AVDD) and R02 (30k to GND) -> 3.0V (15A chop limit)
    r, alt = mref("R01")
    r_vref_hi = sb.place_sym("Device:R", r, "18k", "Resistor_SMD:R_0603_1608Metric", 142.24, 139.7, 0, alt_refs=alt)
    sb.stub_net(r_vref_hi, "1", "DRV_AVDD")
    sb.stub_net(r_vref_hi, "2", "DRV_VREF")

    r, alt = mref("R02")
    r_vref_lo = sb.place_sym("Device:R", r, "30k", "Resistor_SMD:R_0603_1608Metric", 142.24, 165.1, 0, alt_refs=alt)
    sb.stub_net(r_vref_lo, "1", "DRV_VREF")
    sb.stub_power(r_vref_lo, "2", "GND")

    # nSLEEP 10k pullup to +3V3_DRV_EN (R03)
    r, alt = mref("R03")
    r_slp = sb.place_sym("Device:R", r, "10k", "Resistor_SMD:R_0603_1608Metric", 170.18, 149.86, 0, alt_refs=alt)
    sb.stub_net(r_slp, "1", "+3V3_DRV_EN", hier_shape="input")
    sb.stub_net(r_slp, "2", "DRV_nSLEEP")

    # SO 1k series isolation resistor (R04) BEFORE 10nF ADC filter cap (C05) to GND -> CS + TestPoint TP_CS1/TP_CS2
    r, alt = mref("R04")
    r_so = sb.place_sym("Device:R", r, "1k", "Resistor_SMD:R_0603_1608Metric", 198.12, 149.86, 90, alt_refs=alt)
    sb.stub_net(r_so, "1", "SO_RAW")
    sb.stub_net(r_so, "2", "CS", hier_shape="output")

    r, alt = mref("C05")
    c_so = sb.place_sym("Device:C", r, "10nF", "Capacitor_SMD:C_0603_1608Metric", 228.6, 149.86, 0, alt_refs=alt)
    sb.stub_net(c_so, "1", "CS")
    sb.stub_power(c_so, "2", "GND")

    tp_cs = sb.place_sym(
        "Connector:TestPoint",
        "TP_CS1",
        "TP_CS",
        "TestPoint:TestPoint_Pad_D1.5mm",
        228.6,
        124.46,
        0,
        alt_refs={0: "TP_CS1", 1: "TP_CS2"},
    )
    sb.stub_net(tp_cs, "1", "CS")

    # 2. 4x CSD18540Q5B 60V N-MOSFETs + 10 Ohm Gate Resistors
    fets = [
        ("Q01", "R05", "GH1_RAW", "GH1_GATE", "+BATT", "MOT_OUT1", 190.5, 53.34),
        ("Q02", "R06", "GL1_RAW", "GL1_GATE", "MOT_OUT1", "SHUNT_SP", 190.5, 101.6),
        ("Q03", "R07", "GH2_RAW", "GH2_GATE", "+BATT", "MOT_OUT2", 289.56, 53.34),
        ("Q04", "R08", "GL2_RAW", "GL2_GATE", "MOT_OUT2", "SHUNT_SP", 289.56, 101.6),
    ]
    for q_suf, r_suf, g_raw, g_net, d_net, s_net, qx, qy in fets:
        r_ref, r_alt = mref(r_suf)
        rg = sb.place_sym("Device:R", r_ref, "10", "Resistor_SMD:R_0603_1608Metric", qx - 38.1, qy, 90, alt_refs=r_alt)
        sb.stub_net(rg, "1", g_raw)
        sb.stub_net(rg, "2", g_net)

        q_ref, q_alt = mref(q_suf)
        q_sym = sb.place_sym(
            "abx:CSD18540Q5B",
            q_ref,
            "CSD18540Q5B",
            "Package_TO_SOT_SMD:TDSON-8-1",
            qx,
            qy,
            0,
            alt_refs=q_alt,
        )
        sb.stub_net(q_sym, "4", g_net)
        if d_net == "+BATT":
            sb.stub_power(q_sym, "5", "+BATT")
        else:
            sb.stub_net(q_sym, "5", d_net)
        for spin in ["1", "2", "3"]:
            sb.stub_net(q_sym, spin, s_net)

    # 3. 10mOhm 3W 2512 Kelvin Shunt (R09: Bourns CRA2512-FZ-R010ELF)
    r, alt = mref("R09")
    r_shunt = sb.place_sym("Device:R", r, "10mR_3W", "Resistor_SMD:R_2512_6332Metric", 259.08, 149.86, 0, alt_refs=alt)
    sb.stub_net(r_shunt, "1", "SHUNT_SP")
    sb.stub_power(r_shunt, "2", "GND")

    # 4. Bulk + Ceramic Decoupling on +BATT: 220uF 50V Elec (C06) + 2x 4.7uF 50V 1206 (C07, C08) + 100nF (C09)
    r, alt = mref("C06")
    c_bulk = sb.place_sym("Device:C_Polarized", r, "220uF", "Capacitor_SMD:CP_Elec_10x10.5", 289.56, 149.86, 0, alt_refs=alt)
    sb.stub_power(c_bulk, "1", "+BATT")
    sb.stub_power(c_bulk, "2", "GND")

    for idx, (csuf, cval, cfp) in enumerate([
        ("C07", "4.7uF", "Capacitor_SMD:C_1206_3216Metric"),
        ("C08", "4.7uF", "Capacitor_SMD:C_1206_3216Metric"),
        ("C09", "100nF", "Capacitor_SMD:C_0603_1608Metric"),
    ]):
        r, alt = mref(csuf)
        cb = sb.place_sym("Device:C", r, cval, cfp, 314.96 + idx * 25.4, 149.86, 0, alt_refs=alt)
        sb.stub_power(cb, "1", "+BATT")
        sb.stub_power(cb, "2", "GND")

    # 5. RC Snubber (R10 10 Ohm 0805 + C10 2.2nF 100V 0805) & Motor Terminal Block J01
    r, alt = mref("R10")
    r_snub = sb.place_sym("Device:R", r, "10", "Resistor_SMD:R_0805_2012Metric", 342.9, 55.88, 0, alt_refs=alt)
    sb.stub_net(r_snub, "1", "MOT_OUT1")
    sb.stub_net(r_snub, "2", "SNUB_MID")

    r, alt = mref("C10")
    c_snub = sb.place_sym("Device:C", r, "2.2nF", "Capacitor_SMD:C_0805_2012Metric", 342.9, 86.36, 0, alt_refs=alt)
    sb.stub_net(c_snub, "1", "SNUB_MID")
    sb.stub_net(c_snub, "2", "MOT_OUT2")

    r, alt = mref("J01")
    j_mot = sb.place_sym(
        "Connector:Conn_01x02_Pin",
        r,
        "MOTOR_OUT",
        "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal",
        378.46,
        68.58,
        0,
        alt_refs=alt,
    )
    sb.stub_net(j_mot, "1", "MOT_OUT1")
    sb.stub_net(j_mot, "2", "MOT_OUT2")

    # 6. Fault Indicator LED_FLT (Red + 1k) across +3V3 and nFAULT
    r, alt = mref("R11")
    r_flt = sb.place_sym("Device:R", r, "1k", "Resistor_SMD:R_0603_1608Metric", 378.46, 124.46, 0, alt_refs=alt)
    sb.stub_power(r_flt, "1", "+3V3")
    sb.stub_net(r_flt, "2", "FLT_LED_A")

    d_flt = sb.place_sym(
        "Device:LED",
        "LED_FLT1",
        "LED_RED_FLT",
        "LED_SMD:LED_0603_1608Metric",
        378.46,
        149.86,
        90,
        alt_refs={0: "LED_FLT1", 1: "LED_FLT2"},
    )
    sb.stub_net(d_flt, "2", "FLT_LED_A")
    sb.stub_net(d_flt, "1", "nFAULT")

    sb.save()


def build_steppers_relays_sheet(cache: SymbolLibraryCache):
    path = f"/{ROOT_UUID}/{SHEET_UUIDS['Steppers']}"
    sb = SchematicBuilder("Steppers_Relays.kicad_sch", cache, [(path, 0)], paper="A3")
    sb.add_text("SHEET 4: DUAL STEPSTICK STEPPER CHANNELS & DUAL 5V OMRON G5LE RELAY OUTPUTS", 25.4, 17.78, 3.0)

    # 1. Dual StepStick Sockets (U501, U502) + 100uF 50V Bulk Caps + Coil & External Driver Terminals
    for idx, ch in enumerate([1, 2]):
        ux = 68.58 + idx * 147.32
        uy = 78.74
        u_step = sb.place_sym(
            "Driver_Motor:Pololu_Breakout_DRV8825",
            f"U50{ch}",
            "StepStick_DRV8825",
            "Module:Pololu_Breakout-16_15.2x20.3mm",
            ux,
            uy,
            0,
        )
        sb.no_conn(u_step, "2")  # ~FLT
        sb.stub_net(u_step, "13", f"STEP{ch}_nSLP_RST", length=6.35)  # ~RST
        sb.stub_net(u_step, "14", f"STEP{ch}_nSLP_RST", length=6.35)  # ~SLP
        sb.stub_net(u_step, "9", f"STEP{ch}_EN_GATED", length=6.35)
        sb.stub_net(u_step, "15", f"STEP{ch}_PUL", length=6.35, hier_shape="input")
        sb.stub_net(u_step, "16", f"STEP{ch}_DIR", length=6.35, hier_shape="input")
        sb.stub_net(u_step, "10", f"STEP{ch}_M0", length=6.35)  # M0
        sb.stub_net(u_step, "11", f"STEP{ch}_M1", length=6.35)  # M1
        sb.stub_net(u_step, "12", f"STEP{ch}_M2", length=6.35)  # M2

        # 10k pull-up resistor to +3V3_DRV_EN on ~SLEEP/~RESET so E-Stop disables steppers
        r_slp = sb.place_sym(
            "Device:R",
            f"R50{4 + ch}",
            "10k",
            "Resistor_SMD:R_0603_1608Metric",
            ux - 35.56,
            uy - 25.4,
            0,
        )
        sb.stub_net(r_slp, "1", "+3V3_DRV_EN", hier_shape="input" if ch == 1 else None)
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
        sb.stub_net(r_en_pu, "2", f"STEP{ch}_EN_GATED")

        # 3-channel DIP switch SW501/SW502 on M0, M1, M2 to +3V3 for user-selectable microstepping (up to 1/32)
        sw_dip = sb.place_sym(
            "Switch:SW_DIP_x03",
            f"SW50{ch}",
            "MICROSTEP_CFG",
            "Button_Switch_SMD:SW_DIP_SPSTx03_Slide_9.78x9.8mm_W8.61mm_P2.54mm",
            ux - 35.56,
            uy + 20.32,
            0,
        )
        sb.stub_power(sw_dip, "1", "+3V3", length=5.08)
        sb.stub_power(sw_dip, "2", "+3V3", length=5.08)
        sb.stub_power(sw_dip, "3", "+3V3", length=5.08)
        sb.stub_net(sw_dip, "6", f"STEP{ch}_M0", length=5.08)
        sb.stub_net(sw_dip, "5", f"STEP{ch}_M1", length=5.08)
        sb.stub_net(sw_dip, "4", f"STEP{ch}_M2", length=5.08)
        sb.stub_power(u_step, "8", "+BATT", length=5.08)  # VMOT
        sb.stub_power(u_step, "1", "GND", length=5.08)
        sb.stub_power(u_step, "7", "GND", length=5.08)
        sb.stub_net(u_step, "4", f"STEP{ch}_A1", length=6.35)
        sb.stub_net(u_step, "3", f"STEP{ch}_A2", length=6.35)
        sb.stub_net(u_step, "5", f"STEP{ch}_B1", length=6.35)
        sb.stub_net(u_step, "6", f"STEP{ch}_B2", length=6.35)

        # 100uF 50V Bulk Electrolytic on +BATT
        c_elec = sb.place_sym(
            "Device:C_Polarized",
            f"C50{ch}",
            "100uF",
            "Capacitor_SMD:CP_Elec_8x10.5",
            ux + 45.72,
            uy - 33.02,
            0,
        )
        sb.stub_power(c_elec, "1", "+BATT")
        sb.stub_power(c_elec, "2", "GND")

        # 4-Pin Motor Coil Output Terminal
        j_coil = sb.place_sym(
            "Connector:Conn_01x04_Pin",
            f"J50{ch * 2 - 1}",
            f"STEP{ch}_MOTOR",
            "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical",
            ux + 45.72,
            uy,
            0,
        )
        sb.stub_net(j_coil, "1", f"STEP{ch}_A1")
        sb.stub_net(j_coil, "2", f"STEP{ch}_A2")
        sb.stub_net(j_coil, "3", f"STEP{ch}_B1")
        sb.stub_net(j_coil, "4", f"STEP{ch}_B2")

        # Parallel 4-Pin External Stepper Driver Breakout Terminal
        j_ext = sb.place_sym(
            "Connector:Conn_01x04_Pin",
            f"J50{ch * 2}",
            f"STEP{ch}_EXT",
            "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical",
            ux + 45.72,
            uy + 33.02,
            0,
        )
        sb.stub_net(j_ext, "1", f"STEP{ch}_EN_GATED")
        sb.stub_net(j_ext, "2", f"STEP{ch}_PUL")
        sb.stub_net(j_ext, "3", f"STEP{ch}_DIR")
        sb.stub_power(j_ext, "4", "GND")

    # 2. Dual 5V Relay Channels (K501, K502 Omron G5LE-14-DC5 + AO3400A + 1N4148WS + LED + 3-pin Terminal)
    for idx, ch in enumerate([1, 2]):
        rx = 50.8 + idx * 182.88
        ry = 172.72

        r_gate = sb.place_sym(
            "Device:R",
            f"R50{ch * 2 - 1}",
            "100",
            "Resistor_SMD:R_0603_1608Metric",
            rx,
            ry,
            90,
        )
        sb.stub_net(r_gate, "1", f"RELAY_{ch}", hier_shape="input")
        sb.stub_net(r_gate, "2", f"RLY{ch}_GATE")

        q_drv = sb.place_sym(
            "Transistor_FET:Q_NMOS_GSD",
            f"Q50{ch}",
            "AO3400A",
            "Package_TO_SOT_SMD:SOT-23",
            rx + 40.64,
            ry,
            0,
        )
        sb.stub_net(q_drv, "1", f"RLY{ch}_GATE")
        sb.stub_net(q_drv, "3", f"RLY{ch}_COIL_N")
        sb.stub_power(q_drv, "2", "GND")

        d_fly = sb.place_sym(
            "Diode:1N4148WS",
            f"D50{ch * 2 - 1}",
            "1N4148WS",
            "Diode_SMD:D_SOD-323",
            rx + 68.58,
            ry - 15.24,
            270,
        )
        sb.stub_power(d_fly, "1", "+5V")
        sb.stub_net(d_fly, "2", f"RLY{ch}_COIL_N")

        r_led = sb.place_sym(
            "Device:R",
            f"R50{ch * 2}",
            "1k",
            "Resistor_SMD:R_0603_1608Metric",
            rx + 68.58,
            ry + 12.7,
            0,
        )
        sb.stub_power(r_led, "1", "+5V")
        sb.stub_net(r_led, "2", f"RLY{ch}_LED_A")

        d_led = sb.place_sym(
            "Device:LED",
            f"D50{ch * 2}",
            "LED_GRN",
            "LED_SMD:LED_0603_1608Metric",
            rx + 96.52,
            ry + 12.7,
            90,
        )
        sb.stub_net(d_led, "2", f"RLY{ch}_LED_A")
        sb.stub_net(d_led, "1", f"RLY{ch}_COIL_N")

        k_rly = sb.place_sym(
            "Relay:G5LE-1",
            f"K50{ch}",
            "G5LE-14-DC5",
            "Relay_THT:Relay_SPDT_Omron-G5LE-1",
            rx + 114.3,
            ry - 12.7,
            0,
        )
        sb.stub_power(k_rly, "5", "+5V")
        sb.stub_net(k_rly, "2", f"RLY{ch}_COIL_N")
        sb.stub_net(k_rly, "4", f"RLY{ch}_NC")
        sb.stub_net(k_rly, "1", f"RLY{ch}_COM")
        sb.stub_net(k_rly, "3", f"RLY{ch}_NO")

        j_rly = sb.place_sym(
            "Connector:Conn_01x03_Pin",
            f"J50{4 + ch}",
            f"RELAY{ch}_OUT",
            "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-3-5.08_1x03_P5.08mm_Horizontal",
            rx + 149.86,
            ry - 12.7,
            0,
        )
        sb.stub_net(j_rly, "1", f"RLY{ch}_NO")
        sb.stub_net(j_rly, "2", f"RLY{ch}_COM")
        sb.stub_net(j_rly, "3", f"RLY{ch}_NC")

    sb.save()



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


def build_root_sheet():
    """Builds root abx-motion.kicad_sch with all 5 sub-sheets, sheet pins, and interconnecting stubs."""
    wires = []
    labels = []

    def add_sheet_pin_and_stub(sheet_name, pin_name, pin_dir, sx, sy, side, idx):
        py = round(sy + 7.62 + idx * 5.08, 2)
        if side == "right":
            px = round(sx + 55.88, 2)
            wx = round(px + 7.62, 2)
            ang = 0
            just = "right"
            lbl_just = "left bottom"
            lbl_ang = 0
        else:
            px = sx
            wx = round(px - 7.62, 2)
            ang = 180
            just = "left"
            lbl_just = "right bottom"
            lbl_ang = 180

        pin_uuid = det_uuid(f"root.sheetpin.{sheet_name}.{pin_name}")
        pin_sexp = f"""		(pin "{pin_name}" {pin_dir}
			(at {fmt_num(px)} {fmt_num(py)} {ang})
			(effects
				(font
					(size 1.27 1.27)
				)
				(justify {just})
			)
			(uuid "{pin_uuid}")
		)"""
        return pin_sexp, (px, py, wx, py, lbl_ang, lbl_just)

    def make_sheet(name, file, s_uuid, page, sx, sy, left_pins, right_pins):
        pin_blocks = []
        for idx, (pname, pdir, net) in enumerate(left_pins):
            p_sexp, (x1, y1, x2, y2, lang, ljust) = add_sheet_pin_and_stub(name, pname, pdir, sx, sy, "left", idx)
            pin_blocks.append(p_sexp)
            w_uuid = det_uuid(f"root.w.{name}.{pname}")
            l_uuid = det_uuid(f"root.l.{name}.{pname}")
            wires.append(f'\t(wire (pts (xy {fmt_num(x1)} {fmt_num(y1)}) (xy {fmt_num(x2)} {fmt_num(y2)})) (stroke (width 0) (type default)) (uuid "{w_uuid}"))')
            labels.append(f'\t(label "{net}" (at {fmt_num(x2)} {fmt_num(y2)} {lang}) (fields_autoplaced yes) (effects (font (size 1.27 1.27)) (justify {ljust})) (uuid "{l_uuid}"))')

        for idx, (pname, pdir, net) in enumerate(right_pins):
            p_sexp, (x1, y1, x2, y2, lang, ljust) = add_sheet_pin_and_stub(name, pname, pdir, sx, sy, "right", idx)
            pin_blocks.append(p_sexp)
            w_uuid = det_uuid(f"root.w.{name}.{pname}")
            l_uuid = det_uuid(f"root.l.{name}.{pname}")
            wires.append(f'\t(wire (pts (xy {fmt_num(x1)} {fmt_num(y1)}) (xy {fmt_num(x2)} {fmt_num(y2)})) (stroke (width 0) (type default)) (uuid "{w_uuid}"))')
            labels.append(f'\t(label "{net}" (at {fmt_num(x2)} {fmt_num(y2)} {lang}) (fields_autoplaced yes) (effects (font (size 1.27 1.27)) (justify {ljust})) (uuid "{l_uuid}"))')

        height = max(35.56, (max(len(left_pins), len(right_pins)) + 2) * 5.08)
        pins_str = "\n".join(pin_blocks)
        return f"""	(sheet
		(at {fmt_num(sx)} {fmt_num(sy)})
		(size 55.88 {fmt_num(height)})
		(fields_autoplaced yes)
		(stroke
			(width 0.1524)
			(type solid)
		)
		(fill
			(color 0 0 0 0.0000)
		)
		(uuid "{s_uuid}")
		(property "Sheetname" "{name}"
			(at {fmt_num(sx)} {fmt_num(sy - 1.27)} 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(justify left bottom)
			)
		)
		(property "Sheetfile" "{file}"
			(at {fmt_num(sx)} {fmt_num(sy + height + 1.27)} 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(justify left top)
			)
		)
{pins_str}
		(instances
			(project "abx-motion"
				(path "/{ROOT_UUID}"
					(page "{page}")
				)
			)
		)
	)"""

    sheets = [
        make_sheet(
            "Power_Supply",
            "Power.kicad_sch",
            SHEET_UUIDS["Power"],
            "2",
            20.32,
            30.48,
            [],
            [
                ("VBAT_SENSE", "output", "VBAT_SENSE"),
                ("+3V3_DRV_EN", "output", "+3V3_DRV_EN"),
            ],
        ),
        make_sheet(
            "MCU_and_Encoders",
            "MCU.kicad_sch",
            SHEET_UUIDS["MCU"],
            "3",
            124.46,
            30.48,
            [
                ("VBAT_SENSE", "input", "VBAT_SENSE"),
                ("M1_CS", "input", "M1_CS"),
                ("M1_nFAULT", "input", "M1_nFAULT"),
                ("M2_CS", "input", "M2_CS"),
                ("M2_nFAULT", "input", "M2_nFAULT"),
            ],
            [
                ("M1_PWM_PH", "output", "M1_PWM_PH"),
                ("M1_PWM_EN", "output", "M1_PWM_EN"),
                ("M2_PWM_PH", "output", "M2_PWM_PH"),
                ("M2_PWM_EN", "output", "M2_PWM_EN"),
                ("STEP1_PUL", "output", "STEP1_PUL"),
                ("STEP1_DIR", "output", "STEP1_DIR"),
                ("STEP2_PUL", "output", "STEP2_PUL"),
                ("STEP2_DIR", "output", "STEP2_DIR"),
                ("RELAY_1", "output", "RELAY_1"),
                ("RELAY_2", "output", "RELAY_2"),
                ("I2C_SDA", "bidirectional", "I2C_SDA"),
                ("I2C_SCL", "output", "I2C_SCL"),
                ("IO_INT_N", "input", "IO_INT_N"),
            ],
        ),
        make_sheet(
            "DC_Motor_1",
            "Motor_Channel.kicad_sch",
            SHEET_UUIDS["Motor1"],
            "4",
            220.98,
            30.48,
            [
                ("PWM_PH", "input", "M1_PWM_PH"),
                ("PWM_EN", "input", "M1_PWM_EN"),
                ("+3V3_DRV_EN", "input", "+3V3_DRV_EN"),
            ],
            [
                ("CS", "output", "M1_CS"),
                ("nFAULT", "output", "M1_nFAULT"),
            ],
        ),
        make_sheet(
            "DC_Motor_2",
            "Motor_Channel.kicad_sch",
            SHEET_UUIDS["Motor2"],
            "5",
            220.98,
            96.52,
            [
                ("PWM_PH", "input", "M2_PWM_PH"),
                ("PWM_EN", "input", "M2_PWM_EN"),
                ("+3V3_DRV_EN", "input", "+3V3_DRV_EN"),
            ],
            [
                ("CS", "output", "M2_CS"),
                ("nFAULT", "output", "M2_nFAULT"),
            ],
        ),
        make_sheet(
            "Steppers_and_Relays",
            "Steppers_Relays.kicad_sch",
            SHEET_UUIDS["Steppers"],
            "6",
            20.32,
            96.52,
            [],
            [
                ("+3V3_DRV_EN", "input", "+3V3_DRV_EN"),
                ("STEP1_PUL", "input", "STEP1_PUL"),
                ("STEP1_DIR", "input", "STEP1_DIR"),
                ("STEP2_PUL", "input", "STEP2_PUL"),
                ("STEP2_DIR", "input", "STEP2_DIR"),
                ("STEP1_EN", "input", "STEP1_EN"),
                ("STEP2_EN", "input", "STEP2_EN"),
                ("RELAY_1", "input", "RELAY_1"),
                ("RELAY_2", "input", "RELAY_2"),
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
    ]

    content = f"""(kicad_sch
	(version 20250114)
	(generator "eeschema")
	(generator_version "10.0")
	(uuid "{ROOT_UUID}")
	(paper "A4")
	(lib_symbols)
{chr(10).join(wires)}
{chr(10).join(labels)}
{chr(10).join(sheets)}
	(sheet_instances
		(path "/"
			(page "1")
		)
		(path "/{ROOT_UUID}/{SHEET_UUIDS['Power']}"
			(page "2")
		)
		(path "/{ROOT_UUID}/{SHEET_UUIDS['MCU']}"
			(page "3")
		)
		(path "/{ROOT_UUID}/{SHEET_UUIDS['Motor1']}"
			(page "4")
		)
		(path "/{ROOT_UUID}/{SHEET_UUIDS['Motor2']}"
			(page "5")
		)
		(path "/{ROOT_UUID}/{SHEET_UUIDS['Steppers']}"
			(page "6")
		)
		(path "/{ROOT_UUID}/{SHEET_UUIDS['Industrial_IO']}"
			(page "7")
		)
	)
	(embedded_fonts no)
)
"""
    with open(os.path.join(PROJECT_DIR, "abx-motion.kicad_sch"), "w", encoding="utf-8") as f:
        f.write(content)


def audit_symbol_pins_to_footprint_pads():
    import re
    all_placed = SchematicBuilder.all_placed_components


    fp_pad_cache = {}
    mismatches = []
    checked = 0
    for sch_file, ref, lib_id, fp, pins in all_placed:
        if fp not in fp_pad_cache:
            lib_nick, fp_name = fp.split(":", 1)
            if lib_nick == "abx-footprints":
                fp_path = os.path.join(PROJECT_DIR, "abx-footprints.pretty", f"{fp_name}.kicad_mod")
            else:
                fp_path = os.path.join("/usr/share/kicad/footprints", f"{lib_nick}.pretty", f"{fp_name}.kicad_mod")
                if not os.path.exists(fp_path):
                    fp_path = os.path.join(PROJECT_DIR, "abx-footprints.pretty", f"{fp_name}.kicad_mod")
            with open(fp_path, "r", encoding="utf-8") as f:
                mod_text = f.read()
            pads = set(re.findall(r'\(pad\s+"([^"]+)"', mod_text))
            fp_pad_cache[fp] = pads
        pads = fp_pad_cache[fp]
        missing = [p for p in pins if p not in pads]
        checked += 1
        if missing:
            mismatches.append((sch_file, ref, lib_id, fp, missing, sorted(list(pads))))

    print(f"Symbol-to-Footprint Pad Audit: checked {checked} symbol instances across all sheets -> {len(mismatches)} mismatches.")
    for m in mismatches:
        print("  MISMATCH:", m)
    assert len(mismatches) == 0, f"Found {len(mismatches)} symbol-to-footprint pad mismatches!"


def main():
    build_abx_symbols_lib()
    cache = SymbolLibraryCache()
    build_power_sheet(cache)
    build_mcu_sheet(cache)
    build_motor_channel_sheet(cache)
    build_steppers_relays_sheet(cache)
    build_industrial_io_sheet(cache)
    build_root_sheet()
    print("Successfully generated all 5 schematic sheets and abx-symbols.kicad_sym!")
    audit_symbol_pins_to_footprint_pads()


if __name__ == "__main__":
    main()
