"""Stage 3 (Freerouting) for the routed-by-script board. KiCad must be CLOSED.
  autoroute.py export <board> <out.dsn>   lock every track/via (pre-routes go out as `type fix`), In1/In2 as power layers
                                          (copy only: the board file is NOT saved), fill zones (pours go out as planes)
  autoroute.py import <board> <in.ses>    lock all existing tracks/vias, import the session (KiCad keeps locked items and
                                          adds only the new wiring; groups critical_routes / PWR_VIAS survive), save
Run Freerouting in between (~2.2 h for 20 passes on this board):
  java -jar ~/.kicad-mcp/freerouting.jar --gui.enabled=false -de out.dsn -do in.ses -mp 20 -mt 12
Pipeline: planes -> buckplace -> critical -> pours -> autoroute export/FR/import -> cleanup."""
import subprocess as _sp; assert _sp.run(['pgrep', '-x', 'kicad'], capture_output=True).returncode, 'KiCad is running: close it (without saving) first'
import sys  # noqa: E402
import pcbnew  # noqa: E402
mode, P, F = sys.argv[1:4]
b = pcbnew.LoadBoard(P)
for t in b.GetTracks(): t.SetLocked(True)
if mode == 'export':
    for L in (pcbnew.In1_Cu, pcbnew.In2_Cu): b.SetLayerType(L, pcbnew.LT_POWER)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    assert pcbnew.ExportSpecctraDSN(b, F), 'DSN export failed'
else:
    n = len(b.GetTracks())
    assert pcbnew.ImportSpecctraSES(b, F), 'SES import failed'
    b.Save(P); print('imported', len(b.GetTracks()) - n, 'items; saved', P)
