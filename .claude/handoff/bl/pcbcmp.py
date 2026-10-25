import pcbnew,re,subprocess,sys
SP='/tmp/claude-1000/-home-mark-Documents-VE-V3/ca86dfbf-052d-499b-8b8f-07944423ef8f/scratchpad/'
subprocess.run(['kicad-cli','sch','export','netlist','--format','kicadsexpr','-o',SP+'n3.net','abx-motion-brushless.kicad_sch'],capture_output=True)
t=open(SP+'n3.net').read()
sch=set(re.findall(r'\(comp\s+\(ref "([^"]*)"\)',t))
b=pcbnew.LoadBoard(sys.argv[1])
pcb={f.GetReference():f for f in b.GetFootprints()}
extra=sorted(set(pcb)-sch); miss=sorted(sch-set(pcb))
print('sch',len(sch),'pcb',len(pcb)); print('in PCB not in sch:',len(extra))
for r in extra: f=pcb[r]; print(' ',r,f.GetValue(),f.GetFPIDAsString(),round(f.GetX()/1e6),round(f.GetY()/1e6))
print('in sch not in PCB:',miss)
