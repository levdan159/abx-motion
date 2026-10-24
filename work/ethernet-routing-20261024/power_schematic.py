"""Create an isolated ETH variant project and integrate the defined power circuit.
Uses only pure legacy schematic helpers; never calls the full generator.
"""
from pathlib import Path
import ast,copy,math,re,uuid,json,os,shutil
R=Path.cwd();A=R/'work/ethernet-routing-20261024';O=R/'variants/ABX-Motion-ETH'
source=ast.parse((R/'generate_schematics.py').read_text());wanted={'det_uuid','parse_sexp','format_sexp','fmt_num','SymbolLibraryCache','SchematicBuilder'}
for n in source.body:
 if isinstance(n,ast.Assign):
  for t in n.targets:
   if isinstance(t,ast.Name) and t.id in ['ROOT_UUID','SHEET_UUIDS','FILE_UUIDS']:globals()[t.id]=ast.literal_eval(n.value)
PROJECT_DIR=str(O);SYM_DIR='/usr/share/kicad/symbols';HARDWARE_REVISION='1.2b INTEGRATION DRAFT'
exec(compile(ast.Module(body=[n for n in source.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in wanted],type_ignores=[]),'pure_helpers','exec'))
T=lambda n:n[0][1] if isinstance(n,list) and n and isinstance(n[0],tuple) else '';S=lambda n,k:next((q for q in n if T(q)==k),None)
for file in R.glob('*.kicad_sch'):
 dst=O/('abx-motion-eth-placement.kicad_sch' if file.name=='abx-motion.kicad_sch' else file.name)
 if dst.exists():continue
 dst.write_text(file.read_text().replace('(project "abx-motion"','(project "abx-motion-eth-placement"'))
shutil.copy2(R/'abx-symbols.kicad_sym',O/'abx-symbols.kicad_sym')
name='Ethernet_Power.kicad_sch';sid=det_uuid('eth.sheet.power');FILE_UUIDS[name]=det_uuid('eth.file.power');path=f'/{ROOT_UUID}/{sid}'
cache=SymbolLibraryCache();lid='abx-eth:LMR36506R3RPER'
pins={'4':('VIN','power_in',-15.24,7.62,0),'3':('EN_UVLO','input',-15.24,0,0),'1':('RT','input',-15.24,-7.62,0),'9':('GND','power_in',0,-27.94,90),'5':('SW','power_out',15.24,7.62,180),'6':('BOOT','passive',15.24,0,180),'7':('VCC','power_out',15.24,-7.62,180),'8':('VOUT_BIAS','power_in',15.24,-15.24,180),'2':('PG','open_collector',15.24,-22.86,180)}
body=[];pd={}
for num,(pname,typ,x,y,ang) in pins.items():
 body.append(f'(pin {typ} line (at {x} {y} {ang}) (length 2.54) (name "{pname}" (effects (font (size 1 1)))) (number "{num}" (effects (font (size 1 1)))))');pd[num]=dict(num=num,name=pname,type=typ,x=x,y=y,ang=ang)
custom=parse_sexp(f'''(symbol "{lid}" (pin_names (offset .5)) (in_bom yes) (on_board yes)
(property "Reference" "U" (at 0 13 0) (effects (font (size 1.27 1.27))))
(property "Value" "LMR36506R3RPER" (at 0 -28 0) (effects (font (size 1.27 1.27))))
(symbol "LMR36506R3RPER_0_1" (rectangle (start -12.7 10.16) (end 12.7 -25.4) (stroke (width .254) (type default)) (fill (type background))))
(symbol "LMR36506R3RPER_1_1" {''.join(body)}))''')
cache._flattened[lid]=custom;cache._pins[lid]={1:pd}
# Save editable custom symbol library as well as the embedded sheet definition.
libnode=copy.deepcopy(custom);libnode[1]=('str','LMR36506R3RPER');(O/'ethernet-symbols.kicad_sym').write_text('(kicad_symbol_lib (version 20231120) (generator "abx-incremental")\n'+format_sexp(libnode)+'\n)\n')
(O/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "abx-eth")(type "KiCad")(uri "${KIPRJMOD}/ethernet-symbols.kicad_sym")(options "")(descr "ETH power circuit")) (lib (name "abx")(type "KiCad")(uri "${KIPRJMOD}/abx-symbols.kicad_sym")(options "")(descr "Existing board symbols")) (lib (name "abx-r12")(type "KiCad")(uri "${KIPRJMOD}/abx-r12-symbols.kicad_sym")(options "")(descr "Existing reviewed symbols")))\n')
sb=SchematicBuilder(name,cache,[(path,0)],paper='A3');parts=json.loads((O/'layout-review/parts.json').read_text());contract=json.loads((O/'layout-review/power-interface-design.json').read_text());pn={r['pin']:r['proposed_net'] for r in contract['pin_net_table']}
refs=['U802','L801']+[f'C{i}' for i in range(821,828)]+['R817','R818','TP_ETH_3V3'];placed={}
pos={'U802':(125,85,0),'L801':(230,77.38,90),'R817':(55,220,90),'R818':(125,220,0),'TP_ETH_3V3':(245,220,0)}
for i,r in enumerate(f'C{n}' for n in range(821,828)):pos[r]=(45+i*48,165,0)
for r in refs:
 q=parts[r];symbol=lid if r=='U802' else 'Device:L' if r=='L801' else 'Device:C' if r.startswith('C') else 'Device:R' if r.startswith('R') else 'Connector:TestPoint'
 sx,sy,rot=pos[r];sx=round(round(sx/1.27)*1.27,2);sy=round(round(sy/1.27)*1.27,2)
 f=sb.place_sym(symbol,r,q['value'],q['footprint'],sx,sy,rot,in_bom='no');placed[r]=f
 for num in f['pins']:
  net=pn[r+'.'+num]
  if net=='NC':sb.no_conn(f,num)
  else:sb.stub_net(f,num,net,5.08)
# Explicit power flag: passive output inductor does not propagate ERC power drive.
f=sb.place_sym('power:PWR_FLAG','#FLG_ETH801','PWR_FLAG','',330.2,219.71,0,in_bom='no');sb.stub_net(f,'1','3V3_ETH',5.08)
sb.add_text('ETHERNET DEDICATED 3.3V SUPPLY — Rev 1.2b routing in progress',30,25,2)
sb.add_text('Protected +BATT input / fixed 3.3V / 300mA allocated / TI 600mA converter class',30,33,1.3)
sb.add_text('RT tied to VCC selects 1MHz. PGOOD unused. EN follows MAIN +3V3.',30,42,1.2)
sb.add_text('Input bulk / HF        Bootstrap and internal VCC                 Output bulk',35,142,1.3)
sb.add_text('USB only: Ethernet supply OFF without VBAT. SPI isolation integration pending.',30,255,1.2)
sb.add_text('New Ethernet controller/interface/magjack are not yet integrated. NOT FOR MANUFACTURING.',30,264,1.2)
sb.save()
tree=parse_sexp((O/name).read_text())
for n in tree:
 if T(n)=='label':n[0]=('sym','global_label');n.insert(2,[('sym','shape'),('sym','bidirectional')])
# Existing builders hardcode instance project name; use the real variant root name.
(O/name).write_text(format_sexp(tree).replace('(project "abx-motion"','(project "abx-motion-eth-placement"')+'\n')
rootpath=O/'abx-motion-eth-placement.kicad_sch';root=parse_sexp(rootpath.read_text())
if not any(T(n)=='sheet' and S(n,'uuid')[1][1]==sid for n in root):root.append(parse_sexp(f'''(sheet (at 220.98 165.1) (size 66.04 20.32) (stroke (width 0) (type default)) (fill (color 0 0 0 0)) (uuid "{sid}")
(property "Sheetname" "Ethernet_Power" (at 220.98 164.49 0) (effects (font (size 1.27 1.27)) (justify left bottom)))
(property "Sheetfile" "{name}" (at 220.98 186.03 0) (effects (font (size 1.27 1.27)) (justify left top)))
(instances (project "abx-motion-eth-placement" (path "/{ROOT_UUID}" (page "8")))))'''))
rootpath.write_text(format_sexp(root)+'\n')
(A/'power-refs.json').write_text(json.dumps(refs,indent=2)+'\n');print('Created complete variant schematic hierarchy with12-component Ethernet power sheet.')
