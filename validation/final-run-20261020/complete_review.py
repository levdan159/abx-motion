from pathlib import Path
import pcbnew,csv,json,re,hashlib,shutil,zipfile,xml.etree.ElementTree as ET,collections,math
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'validation/final-run-20261020'; PROD=ROOT/'production/final-20261020'
b=pcbnew.LoadBoard(str(ROOT/'abx-motion.kicad_pcb'));fps={f.GetReference():f for f in b.GetFootprints()}
# Rebuild the BOM from the saved board, with both real socket strips represented.
groups={};expected=set()
for ref,f in fps.items():
 if ref.startswith(('H','LOGO','TP_')):continue
 fields={x.GetName():x.GetText() for x in f.GetFields()};code=fields.get('LCSC','');assert re.fullmatch('C[0-9]+',code),(ref,code)
 refs=[ref+'_L',ref+'_R'] if ref in ['U501','U502'] else [ref];expected.update(refs)
 key=('PinSocket_1x08','PinSocket_1x08_P2.54mm_Vertical',code) if len(refs)==2 else (f.GetValue(),str(f.GetFPID().GetLibItemName()),code)
 groups.setdefault(key,[]).extend(refs)
with (PROD/'abx-motion-jlcpcb-bom.csv').open('w',newline='') as h:
 w=csv.writer(h);w.writerow(['Comment','Designator','Footprint','LCSC Part #'])
 for (v,p,c),refs in sorted(groups.items(),key=lambda x:x[1][0]):w.writerow([v,','.join(sorted(refs)),p,c])
old=list(csv.DictReader((OUT/'before/production/abx-motion-jlcpcb-cpl.csv').open()));assert len(old)==len(expected)==237
assert {r['Designator'] for r in old}==expected
fixes=[]
for r in old:
 ref=r['Designator']
 if ref in ['J1','LED201','LED202','LED_FLT1','LED_FLT2']:
  fixes.append({'ref':ref,'old_rotation':r['Rotation'],'new_rotation':'180.0','basis':'Saved supplier footprint pad positions: pad 1 opposite PCB at 0 degrees; 180 aligns it. Confirm physical polarity in assembler preview.'});r['Rotation']='180.0'
 if ref=='F5':r['Val']='1206L050/15YR'
with (PROD/'abx-motion-jlcpcb-cpl.csv').open('w',newline='') as h:
 w=csv.DictWriter(h,fieldnames=list(old[0]));w.writeheader();w.writerows(old)
(OUT/'cpl-corrections.json').write_text(json.dumps(fixes,indent=2)+'\n')
# Netlist-driven functional review, independent of the router's completion count.
tree=ET.parse(OUT/'netlist-after.xml');pn={(n.get('ref'),n.get('pin')):net.get('name') for net in tree.findall('.//nets/net') for n in net.findall('node')};checks=[]
def same(label,*pins):
 ns=[pn[p] for p in pins];assert len(set(ns))==1,(label,ns);checks.append(label)
def net(label,pin,name):assert pn[pin]==name,(label,pn[pin]);checks.append(label)
same('BACK reaches GPIO21',('U3','23'),('SW203','1'))
same('INT reaches GPIO36 and pull-up',('U3','29'),('U601','1'),('R206','2'))
same('SDA reaches GPIO41',('U3','34'),('U601','23'))
same('SCL reaches GPIO42',('U3','35'),('U601','22'))
for i in range(8):
 j='J'+str(601+i//2);jp='1' if i%2==0 else '3';pu='R'+str(601+i);sr='R'+str(609+i);cap='C'+str(602+i)
 same(f'Limit {i+1} connector/pullup/series',(j,jp),(pu,'2'),(sr,'1'))
 same(f'Limit {i+1} filtered expander path',(sr,'2'),(cap,'1'),('U601',str(4+i)))
 net(f'Limit {i+1} pullup',(pu,'1'),'+3V3');net(f'Limit {i+1} filter ground',(cap,'2'),'GND');net(f'Limit {i+1} connector ground',(j,'2'),'GND')
for i in range(2):
 j='J'+str(605+i);q='Q'+str(601+i);d='D'+str(601+i);pd='R'+str(617+i);rg='R'+str(619+i)
 same(f'Aux {i+1} command and boot pull-down',('U601',str(13+i)),(pd,'1'),(rg,'1'));net(f'Aux {i+1} boot off',(pd,'2'),'GND')
 same(f'Aux {i+1} MOSFET gate',(rg,'2'),(q,'1'));net(f'Aux {i+1} MOSFET source',(q,'2'),'GND')
 same(f'Aux {i+1} flyback anode/drain/header',(d,'2'),(q,'3'),(j,'3'));same(f'Aux {i+1} flyback cathode/fused supply',(d,'1'),(j,'1'),('F5','2'));net(f'Aux {i+1} header ground',(j,'2'),'GND')
 q='Q'+str(503+i);rp='R'+str(621+i);rd='R'+str(507+i);st='U'+str(501+i);ext='J'+str(502+2*i)
 same(f'Stepper {i+1} command/source',('U601',str(15+i)),(rp,'2'),(q,'2'))
 same(f'Stepper {i+1} hardware E-stop gate',(q,'1'),('U601','17'),('J102','2'))
 same(f'Stepper {i+1} gated enable reaches onboard/external',(q,'3'),(rd,'2'),(st,'9'),(ext,'1'))
 net(f'Stepper {i+1} command pullup',(rp,'1'),'+3V3');net(f'Stepper {i+1} disabled pullup',(rd,'1'),'+3V3')
for pin in ['2','3','12','18','19','20','21']:net('PCA ground/address/unused '+pin,('U601',pin),'GND')
net('PCA supply',('U601','24'),'+3V3');net('AUX fuse input',('F5','1'),'+5V')
# Every schematic pin appears with the same net on the PCB (intentional NCs included).
boardpn={(f.GetReference(),p.GetNumber()):p.GetNetname() for f in fps.values() for p in f.Pads() if p.GetNumber()}
assert all(boardpn[p]==n for p,n in pn.items()),[(p,n,boardpn.get(p)) for p,n in pn.items() if boardpn.get(p)!=n]
assert not any(t.GetLayer()==pcbnew.In1_Cu for t in b.GetTracks())
back=fps['LOGO2'];assert all(g.GetLayer() in [pcbnew.B_SilkS,pcbnew.B_CrtYd] for g in back.GraphicalItems());assert not list(back.Pads())
# Gerber set deliberately excludes drill maps and combined mixed-plating drills.
files=sorted(p for p in (PROD/'gerbers').iterdir() if p.suffix in ['.gtl','.g1','.g2','.gbl','.gtp','.gbp','.gto','.gbo','.gts','.gbs','.gm1','.drl'])
assert len(files)==13 and {p.name for p in files if p.suffix=='.drl'}=={'abx-motion-PTH.drl','abx-motion-NPTH.drl'}
with zipfile.ZipFile(PROD/'abx-motion-gerbers.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,p.name)
# Verify copper/mask/paste/drills have not changed in this metadata/silk pass.
def norm(p):return '\n'.join(x for x in p.read_text().splitlines() if not any(k in x for k in ['CreationDate','GenerationSoftware','Created by KiCad','; DRILL file','TF.FileFunction','FILE_FORMAT','F5,1206L050','F5,500mA','1206L050/15YR','500mA_PTC']) and not x.startswith('; #@! TF.CreationDate'))
export_comparison={}
for p in files:
 oldpath=OUT/'before/production/gerbers'/p.name
 if oldpath.exists():export_comparison[p.name]=norm(p)==norm(oldpath)
# Record actual dimensions and OLED mechanical assumptions.
h5=fps['H5'].GetPosition();h6=fps['H6'].GetPosition();oled=fps['J208'];op=list(oled.Pads());oy=sum(pcbnew.ToMM(p.GetPosition().y) for p in op)/len(op)
audit={'functional_checks':len(checks),'checks':checks,'schematic_pins_matched_to_PCB':len(pn),'BOM_groups':len(groups),'placements':len(old),'duplicate_designators':0,'In1_signal_tracks':0,'back_logo_silkscreen_only':True,'OLED_hole_X_spacing_mm':pcbnew.ToMM(abs(h6.x-h5.x)),'OLED_hole_row_minus_header_row_mm':pcbnew.ToMM(h5.y)-oy,'export_comparison_to_before':export_comparison,'scope':'CPL catalogue coverage and reference matching are checked. Complete supplier placement/polarity approval is still required, especially U601/J601-J606. Cached supplier pads do not certify all land patterns.'}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print(json.dumps({k:v for k,v in audit.items() if k not in ['checks','export_comparison_to_before']},indent=2))
# Save evidence used for AO3400/diode and corrected polarity entries locally.
cache=json.load(open('/tmp/easyeda_cache.json'))
for code in ['C98733','C2287','C2286','C20917','C8598']:(OUT/'supplier'/(code+'-cached-footprint.json')).write_text(json.dumps(cache[code],indent=2)+'\n')
