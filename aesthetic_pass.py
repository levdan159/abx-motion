#!/usr/bin/env python3
"""Apply the compact V1.1 visual layout without regenerating or resetting routing.

Use /usr/bin/python3 and explicit --input/--output paths. The library directory
must belong to the OUTPUT project. This pass repairs only the STEP1_DIR segment
that crosses the requested gold-artwork location; other electrical defects are
reported separately by KiCad DRC.
"""
import argparse
from pathlib import Path

import pcbnew


def point(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


def segment_key(track):
    ends = sorted(((track.GetStart().x, track.GetStart().y),
                   (track.GetEnd().x, track.GetEnd().y)))
    return tuple(ends)


def path_keys(path):
    return [tuple(sorted(((point(*a).x, point(*a).y),
                          (point(*b).x, point(*b).y))))
            for a, b in zip(path, path[1:])]


def relocate_direction_trace(board):
    """Detour two original direction segments around the artwork on F.Cu."""
    old_path = [(101.0, 103.5), (107.5, 110.0), (107.5, 115.5)]
    new_path = [(101.0, 103.5), (108.6, 103.5), (109.2, 104.1),
                (109.2, 112.3), (107.5, 114.0), (107.5, 115.5)]
    tracks = [t for t in board.GetTracks()
              if not isinstance(t, pcbnew.PCB_VIA)
              and t.GetLayer() == pcbnew.F_Cu
              and t.GetNetname() == "/STEP1_DIR"]
    old_keys = set(path_keys(old_path))
    old = [t for t in tracks if segment_key(t) in old_keys]
    if not old:
        if not set(path_keys(new_path)).issubset({segment_key(t) for t in tracks}):
            raise RuntimeError("STEP1_DIR differs from the inspected checkpoint; review locally")
        return []
    if len(old) != 2:
        raise RuntimeError("Partial STEP1_DIR match; refusing to change an unknown route")
    net = old[0].GetNet()
    width = old[0].GetWidth()
    for track in old:
        board.Remove(track)
    for a, b in zip(new_path, new_path[1:]):
        track = pcbnew.PCB_TRACK(board)
        track.SetStart(point(*a))
        track.SetEnd(point(*b))
        track.SetLayer(pcbnew.F_Cu)
        track.SetWidth(width)
        track.SetNet(net)
        board.Add(track)
    return old


def resize_logo(footprint, width_mm):
    origin = footprint.GetPosition()
    factor = width_mm / pcbnew.ToMM(footprint.GetBoundingBox(False, False).GetWidth())

    def scaled(p):
        return pcbnew.VECTOR2I(origin.x + round((p.x - origin.x) * factor),
                              origin.y + round((p.y - origin.y) * factor))

    for item in footprint.GraphicalItems():
        if not isinstance(item, pcbnew.PCB_SHAPE):
            continue
        if item.GetShape() == pcbnew.SHAPE_T_POLY:
            poly = item.GetPolyShape()
            for oi in range(poly.OutlineCount()):
                rings = [poly.Outline(oi)]
                rings += [poly.Hole(oi, hi) for hi in range(poly.HoleCount(oi))]
                for ring in rings:
                    for pi in range(ring.PointCount()):
                        ring.SetPoint(pi, scaled(ring.GetPoint(pi)))
        else:
            item.SetStart(scaled(item.GetStart()))
            item.SetEnd(scaled(item.GetEnd()))


def add_text(board, text, x, y, *, layer=pcbnew.F_SilkS, size=0.7,
             thickness=0.12, left=False, bold=False):
    item = pcbnew.PCB_TEXT(board)
    item.SetText(text)
    item.SetPosition(point(x, y))
    item.SetLayer(layer)
    item.SetTextSize(point(size, size))
    item.SetTextThickness(pcbnew.FromMM(thickness))
    item.SetMirrored(layer == pcbnew.B_SilkS)
    item.SetBold(bold)
    item.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT if left
                        else pcbnew.GR_TEXT_H_ALIGN_CENTER)
    item.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    board.Add(item)
    return item


def apply(board):
    footprints = {f.GetReference(): f for f in board.GetFootprints()}
    # Keep removed SWIG objects alive until after saving. KiCad's wrappers can
    # otherwise be collected while further board operations are in progress.
    removed_items = relocate_direction_trace(board)
    logo = footprints["LOGO1"]
    resize_logo(logo, 8.5)
    logo.SetPosition(point(104.5, 108.0))
    logo.Reference().SetVisible(False)
    logo.Value().SetVisible(False)

    old_legends = {"MN G MX", "5V G SW", "MIN", "G", "MAX", "MN", "MX", "5V", "SW"}
    for item in list(board.GetDrawings()):
        if not isinstance(item, pcbnew.PCB_TEXT):
            continue
        text = item.GetText()
        x, y = pcbnew.ToMM(item.GetPosition().x), pcbnew.ToMM(item.GetPosition().y)
        io_legend = (62 <= x <= 95 and 125 <= y <= 142
                     and (text in old_legends or text.startswith(tuple(f"J{n} " for n in range(601, 607)))))
        footer = text.startswith("J601-J604:") or text.startswith("LIMITS 3V3 ONLY")
        front_brand = (item.GetLayer() == pcbnew.F_SilkS
                       and text in {"AUTOBOTIX", "ABX-Motion V1.1"})
        if io_legend or footer or front_brand:
            removed_items.append(item)
            board.Remove(item)
        elif item.GetLayer() == pcbnew.F_SilkS and text in {
                "J501 STEP1", "J502 EXT1", "J503 STEP2", "J504 EXT2"}:
            item.SetPosition(point(x, 143.1))
        elif item.GetLayer() == pcbnew.B_SilkS:
            if text.startswith("ABX-MOTION V1.1"):
                item.SetText("ABX-MOTION V1.1 — SPECS & I/O (DESIGN TARGETS)")
            elif text.startswith("VBAT (J1 XT60):"):
                item.SetText("VBAT (J1 XT60): 12-32V target (25A Fuse, SMCJ30A)")
            elif text.startswith("DC Servo 1&2:"):
                item.SetText("DC Servo 1&2: 2x 100W target (DRV8701E, 15A Chop)")
            elif text.startswith("J601-J604 ("):
                item.SetText("LIMITS J601-J604: 8x dry contact / 3V3 logic ONLY")
            elif text.startswith("J605-J606 ("):
                item.SetText("AUX J605-J606: 5V / G / SW, 0.5A shared supply")

    add_text(board, "AUTOBOTIX", 110.8, 107.0, size=1.35,
             thickness=0.22, left=True, bold=True)
    add_text(board, "ABX-Motion V1.1", 110.8, 109.6, size=0.95,
             thickness=0.15, left=True)

    names = {"J601": "M1 LIM", "J602": "M2 LIM", "J603": "S1 LIM",
             "J604": "S2 LIM", "J605": "OUT1", "J606": "OUT2"}
    for ref, name in names.items():
        connector = footprints[ref]
        connector.Reference().SetVisible(False)
        connector.Value().SetVisible(False)
        pads = {p.GetNumber(): p for p in connector.Pads()}
        labels = ("MIN", "G", "MAX") if ref <= "J604" else ("5V", "G", "SW")
        cx = pcbnew.ToMM(pads["2"].GetPosition().x)
        y = pcbnew.ToMM(pads["2"].GetPosition().y)
        for layer, header_dy, pin_dy in [(pcbnew.F_SilkS, -2.65, 3.8),
                                         (pcbnew.B_SilkS, -2.1, 2.1)]:
            add_text(board, f"{ref} {name}", cx, y + header_dy,
                     layer=layer, size=0.72)
            for number, label in zip(("1", "2", "3"), labels):
                add_text(board, label, pcbnew.ToMM(pads[number].GetPosition().x),
                         y + pin_dy, layer=layer, size=0.68, thickness=0.11)
    for layer in (pcbnew.F_SilkS, pcbnew.B_SilkS):
        add_text(board, "LIMITS 3V3 ONLY | OUT 5V / 0.5A TOTAL", 79.5, 141.75,
                 layer=layer, size=0.68, thickness=0.11)

    for footprint in footprints.values():
        footprint.Value().SetVisible(False)
        for field in footprint.GetFields():
            if field.GetName() == "LCSC":
                field.SetVisible(False)

    back_logo = footprints["LOGO2"]
    back_origin = back_logo.GetPosition()
    back_width = pcbnew.ToMM(back_logo.GetBoundingBox(False, False).GetWidth())
    if abs(back_width - 17.5) > 0.2:
        factor = 17.5 / back_width
        resize_logo(back_logo, 17.5)
        for item in back_logo.GraphicalItems():
            if isinstance(item, pcbnew.PCB_TEXT):
                p = item.GetPosition()
                item.SetPosition(pcbnew.VECTOR2I(
                    back_origin.x + round((p.x - back_origin.x) * factor),
                    back_origin.y + round((p.y - back_origin.y) * factor)))
                sz = item.GetTextSize()
                item.SetTextSize(pcbnew.VECTOR2I(round(sz.x * factor), round(sz.y * factor)))
                item.SetTextThickness(round(item.GetTextThickness() * factor))
    back_logo.SetPosition(point(186.0, 138.0))
    back_logo.Reference().SetVisible(False)
    back_logo.Value().SetVisible(False)
    has_b_mask = any(isinstance(g, pcbnew.PCB_SHAPE) and g.GetLayer() == pcbnew.B_Mask
                     for g in back_logo.GraphicalItems())
    for item in list(back_logo.GraphicalItems()):
        if isinstance(item, pcbnew.PCB_SHAPE) and item.GetLayer() == pcbnew.B_SilkS:
            item.SetLayer(pcbnew.B_Cu)
            if not has_b_mask:
                mask_item = pcbnew.Cast_to_PCB_SHAPE(item.Duplicate())
                mask_item.SetLayer(pcbnew.B_Mask)
                back_logo.Add(mask_item)
    return logo, back_logo, removed_items


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--library-dir", required=True, type=Path)
    args = parser.parse_args()
    board = pcbnew.LoadBoard(str(args.input.resolve()))
    logo, back_logo, removed_items = apply(board)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pcbnew.SaveBoard(str(args.output.resolve()), board)
    for fp, flip_to_front in [(logo, False), (back_logo, True)]:
        lib_fp = pcbnew.Cast_to_FOOTPRINT(fp.Duplicate(False))
        lib_fp.SetPosition(point(0, 0))
        if flip_to_front and lib_fp.IsFlipped():
            lib_fp.Flip(point(0, 0), False)
        pcbnew.FootprintSave(str(args.library_dir.resolve()), lib_fp)
    print(f"Saved aesthetic candidate: {args.output}")
    print("Check fresh DRC before replacing the working board.")


if __name__ == "__main__":
    main()

