from pathlib import Path
import re,json,xml.etree.ElementTree as ET
import pcbnew
R=Path.cwd();O=R/'work/drc-cleanup-20261024';b=pcbnew.LoadBoard(str(R/'abx-motion.kicad_pcb'));fs={f.GetReference():f for f in b.GetFootprints()};j=json.loads((O/'detail-drc.json').read_text());refs={v['items'][0]['description'].replace('Footprint ','') for v in j['violations'] if v['type']=='lib_footprint_mismatch'};refs.add('TIM_ESP');mapping={};plug=pcbnew.PCB_IO_KICAD_SEXPR();saved=set();hold=[]
for ref in sorted(refs):
 f=fs[ref];old=f.GetFPID().GetLibItemName();name='DRV8701_RGE_Thermal_ABX' if ref in ['U301','U401'] else 'MKDS_2Pin_Motor_ABX' if ref in ['J301','J401'] else 'TestPoint_PTH_2.5x3.6_D1.0_CS_ABX' if ref in ['TP_CS1','TP_CS2'] else 'TIM_GND_4x4_Bottom' if ref=='TIM_ESP' else re.sub(r'[^A-Za-z0-9_.-]','_',f'ABX_{ref}_{old}')
 newid='abx-footprints:'+name;mapping[ref]=newid;f.SetFPID(pcbnew.LIB_ID('abx-footprints',name))
 if name not in saved:
  copy=pcbnew.Cast_to_FOOTPRINT(f.Duplicate(False));hold.append(copy);copy.SetPosition(pcbnew.VECTOR2I(0,0));copy.SetOrientationDegrees(0);plug.FootprintSave(str(R/'abx-footprints.pretty'),copy);saved.add(name)
# Use the real instantiated symbol UUIDs, including the shared motor sheet.
uuidmap={}
for comp in ET.parse(R/'validation/root-ethernet-promotion-20261024/netlist.xml').findall('.//components/comp'):
 ref=comp.get('ref')
 if ref in mapping:
  u=comp.findtext('tstamps');assert u not in uuidmap or uuidmap[u]==mapping[ref];uuidmap[u]=mapping[ref]
changed=set()
for file in R.glob('*.kicad_sch'):
 text=file.read_text()
 def patch(m):
  block=m.group();u=re.search(r'^\t\t\(uuid "([^"]+)"',block,re.M)
  if not u or u[1] not in uuidmap:return block
  block,n=re.subn(r'\(property "Footprint" "[^"]*"','(property "Footprint" "'+uuidmap[u[1]]+'"',block,count=1);assert n==1;changed.add(u[1]);return block
 new=re.sub(r'^\t\(symbol\s.*?^\t\)',patch,text,flags=re.S|re.M)
 if new!=text:file.write_text(new)
assert set(uuidmap)==changed,(set(uuidmap)-changed)
# Explicitly identify unwired placement reserves as board-only. This is their
# actual CAD state, protects them on schematic sync, and is not a DRC exclusion.
parts=set(json.load(open(R/'variants/ABX-Motion-ETH/layout-review/parts.json')));power=set(json.load(open(R/'work/ethernet-routing-20261024/power-refs.json')));draft=parts-power
for ref in draft:
 f=fs[ref];assert all(p.GetNetCode()==0 for p in f.Pads());f.SetAttributes(f.GetAttributes()|pcbnew.FP_BOARD_ONLY)
tb=b.GetTitleBlock();tb.SetComment(0,'ETHERNET DRAFT: 49 board-only reserves have no nets; NOT FOR MANUFACTURING');b.SetTitleBlock(tb)
pcbnew.SaveBoard(str(R/'abx-motion.kicad_pcb'),b);(O/'reviewed-library-map.json').write_text(json.dumps(mapping,indent=2)+'\n');(O/'board-only-reserves.json').write_text(json.dumps(sorted(draft),indent=2)+'\n');print('Saved',len(saved),'reviewed footprints, synchronized',len(changed),'symbol definitions;',len(draft),'unwired board-only reserves')
