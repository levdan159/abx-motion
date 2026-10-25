"""Refill all zones in the saved board file (KiCad closed)."""
import subprocess as _sp; assert _sp.run(['pgrep', '-x', 'kicad'], capture_output=True).returncode, 'KiCad is running: close it (without saving) first'
import pcbnew
P = '/home/mark/Documents/abx-motion/abx-motion-brushless.kicad_pcb'
b = pcbnew.LoadBoard(P); pcbnew.ZONE_FILLER(b).Fill(b.Zones()); b.Save(P); print('zones filled')
