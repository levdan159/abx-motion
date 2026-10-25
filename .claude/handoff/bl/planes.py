"""In2.Cu power planes (split by function, from the pad map 2026-10-24). KiCad must be CLOSED.
 +3V3    left logic column (ESP32 / IO / logic power)                      x 45.5-100
 VBUS    both ESC power stages + STM32 strip (+3V3_ESC / +5V stay traces)  x 100-178 (to 189 at the breaker output)
 VBAT_IN breaker + J1 BAT+ column                                           top right
 +BATT   Q1 / D2 / C525 / buck inputs                                       x 162-198, y 91-150
 +24V    24 V buck output caps -> J510, brake supply corner                 x 162-203, y 105.5-165.5
+12V, VM_BRK, +5V, +3V3_ESC: traces/outer pours (short or low current). Re-running replaces the In2 zones."""
import subprocess as _sp; assert _sp.run(['pgrep', '-x', 'kicad'], capture_output=True).returncode, 'KiCad is running: close it (without saving) first'
import pcbnew
P = '/home/mark/Documents/abx-motion/abx-motion-brushless.kicad_pcb'; MM = 1e6
b = pcbnew.LoadBoard(P)
ref = [z for z in b.Zones() if z.GetNetname() == 'GND'][0]
for z in [z for z in b.Zones() if z.GetLayer() == pcbnew.In2_Cu]: b.Remove(z)
X1, Y0, Y1 = 213.5, 48.5, 165.5
PLANES = [  # (net, priority, outline)
    ('+3V3', 1, [(45.5, Y0), (100, Y0), (100, Y1), (45.5, Y1)]),
    ('VBUS', 1, [(100, Y0), (189, Y0), (189, 75), (178, 75), (178, 95), (162, 95), (162, Y1), (100, Y1)]),
    ('VBAT_IN', 2, [(189, Y0), (X1, Y0), (X1, 104), (198, 104), (198, 91), (178, 91), (178, 75), (189, 75)]),
    ('+BATT', 2, [(162, 95), (178, 95), (178, 91), (198, 91), (198, 104), (185.5, 104), (185.5, 113.5), (181, 113.5), (181, 150), (162, 150)]),
    ('+24V', 2, [(185.5, 105.5), (203, 105.5), (203, Y1), (162, Y1), (162, 150), (181, 150), (181, 113.5), (185.5, 113.5)]),
]
for net, prio, pts in PLANES:
    z = pcbnew.ZONE(b); z.SetLayer(pcbnew.In2_Cu); z.SetNet(b.FindNet(net)); z.SetAssignedPriority(prio)
    z.SetLocalClearance(ref.GetLocalClearance()); z.SetMinThickness(ref.GetMinThickness())
    z.SetThermalReliefGap(ref.GetThermalReliefGap()); z.SetThermalReliefSpokeWidth(ref.GetThermalReliefSpokeWidth())
    z.SetPadConnection(ref.GetPadConnection()); z.SetIslandRemovalMode(ref.GetIslandRemovalMode())
    z.SetZoneName(f'In2_{net}')
    o = z.Outline(); o.NewOutline()
    for x, y in pts: o.Append(int(x * MM), int(y * MM))
    b.Add(z)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(P)
for z in b.Zones():
    if z.GetLayer() == pcbnew.In2_Cu: print(f'{z.GetNetname():8s} filled {z.GetFilledArea() / MM / MM:7.0f} mm2')
