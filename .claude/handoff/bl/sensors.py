import re,sys,uuid,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); import sx
U=lambda:str(uuid.uuid4())
ROOT='f9149098-3f23-438d-bdc2-2e278b5ca35b'; SU=U()
# ---- A. Sensors.kicad_sch
esc=open('ESC_Channel.kicad_sch').read(); ls=[x for x in sx.spans(esc) if x[2]=='lib_symbols'][0]; inner=esc[ls[0]:ls[1]]
conn=[inner[s:e] for s,e,h in sx.spans(inner,depth=1) if inner[s:e].startswith('(symbol "Connector_Generic:Conn_01x06"')][0]
def jsym(ref,val,x,y):
    return f'''\t(symbol
\t\t(lib_id "Connector_Generic:Conn_01x06")
\t\t(at {x} {y} 0)
\t\t(unit 1)
\t\t(body_style 1)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(in_pos_files yes)
\t\t(dnp no)
\t\t(uuid "{U()}")
\t\t(property "Reference" "{ref}"
\t\t\t(at {x-5.08} {y-1.27} 0)
\t\t\t(effects (font (size 1.27 1.27)))
\t\t)
\t\t(property "Value" "{val}"
\t\t\t(at {x-5.08} {y+3.81} 0)
\t\t\t(effects (font (size 1.27 1.27)))
\t\t)
\t\t(property "Footprint" "Connector_JST:JST_PH_B6B-PH-K_1x06_P2.00mm_Vertical"
\t\t\t(at {x} {y} 0)
\t\t\t(effects (font (size 1.27 1.27)) (hide yes))
\t\t)
\t\t(property "Datasheet" ""
\t\t\t(at {x} {y} 0)
\t\t\t(effects (font (size 1.27 1.27)) (hide yes))
\t\t)
\t\t(property "Description" ""
\t\t\t(at {x} {y} 0)
\t\t\t(effects (font (size 1.27 1.27)) (hide yes))
\t\t)
'''+''.join(f'\t\t(pin "{k}"\n\t\t\t(uuid "{U()}")\n\t\t)\n' for k in range(1,7))+f'''\t\t(instances
\t\t\t(project "abx-motion-brushless"
\t\t\t\t(path "/{ROOT}/{SU}"
\t\t\t\t\t(reference "{ref}")
\t\t\t\t\t(unit 1)
\t\t\t\t)
\t\t\t)
\t\t)
\t)
'''
def pinxy(x,y,k): return round(x-5.08,2), round(y-5.08+2.54*(k-1),2)
body=''
J210=(66.04,63.5); J211=(66.04,109.22)
body+=jsym('J210','GPS',*J210)+jsym('J211','IMU',*J211)
def hl(name,shape,px,py): return f'\t(hierarchical_label "{name}"\n\t\t(shape {shape})\n\t\t(at {px} {py} 180)\n\t\t(effects (font (size 1.27 1.27)) (justify right))\n\t\t(uuid "{U()}")\n\t)\n'
def gl(name,px,py): return f'\t(global_label "{name}"\n\t\t(shape passive)\n\t\t(at {px} {py} 180)\n\t\t(effects (font (size 1.27 1.27)) (justify right))\n\t\t(uuid "{U()}")\n\t)\n'
for (x,y),pins in ((J210,{1:('g','+5V'),2:('g','+3V3'),3:('g','GND'),4:('h','GPS_RX','output'),5:('h','GPS_TX','input'),6:('h','GPS_PPS','output')}),
                   (J211,{1:('g','+3V3'),2:('g','GND'),3:('h','I2C_SCL','input'),4:('h','I2C_SDA','bidirectional'),5:('h','IMU_INT','output'),6:('h','IMU_RST','input')})):
    for k,v in pins.items():
        px,py=pinxy(x,y,k)
        body+= gl(v[1],px,py) if v[0]=='g' else hl(v[1],v[2],px,py)
def txt(s,x,y,size=1.27): return f'\t(text "{s}"\n\t\t(exclude_from_sim no)\n\t\t(at {x} {y} 0)\n\t\t(effects (font (size {size} {size})) (justify left bottom))\n\t\t(uuid "{U()}")\n\t)\n'
body+=txt('SENSORS: GPS + 9-DoF IMU headers (modules are off-board)',30,30,2)
body+=txt('GPS (J210): u-blox class module on ESP32 UART1, 115200 8N1; PPS to GPIO. Pin 4 = module TX, pin 5 = module RX. Powered from +5V or +3V3 per module.',30,40)
body+=txt('IMU (J211): 9-DoF breakout (BNO085 / ICM-20948 class) on the shared I2C bus; INT and RST to GPIO. Pull-ups live on the MCU sheet.',30,46)
body+=txt('Mount the IMU away from the motors, battery and power wiring: the magnetometer reads their fields. Use GPS course over ground as a heading cross-check.',30,52)
sensors=f'''(kicad_sch
\t(version 20250114)
\t(generator "eeschema")
\t(generator_version "10.0")
\t(uuid "{U()}")
\t(paper "A4")
\t(lib_symbols
\t\t{conn}
\t)
{body}\t(sheet_instances
\t\t(path "/"
\t\t\t(page "1")
\t\t)
\t)
\t(embedded_fonts no)
)
'''
open('Sensors.kicad_sch','w').write(sensors)
# ---- C. MCU hier labels at the free ESP32 pins
def mcu(t):
    add=''
    for name,shape,x,y,a in (('GPS_TX','output',104.14,71.12,0),('GPS_RX','input',104.14,73.66,0),('GPS_PPS','input',73.66,91.44,180),('IMU_INT','input',73.66,81.28,180),('IMU_RST','output',73.66,83.82,180)):
        j='left' if a==0 else 'right'
        add+=f'\t(hierarchical_label "{name}"\n\t\t(shape {shape})\n\t\t(at {x} {y} {a})\n\t\t(effects (font (size 1.27 1.27)) (justify {j}))\n\t\t(uuid "{U()}")\n\t)\n'
    i=t.index('\t(sheet_instances') if '\t(sheet_instances' in t else len(t)-2
    return t[:i]+add+t[i:]
t=open('MCU.kicad_sch').read(); open('MCU.kicad_sch','w').write(mcu(t))
# ---- B. root
t=open('abx-motion-brushless.kicad_sch').read()
def shift_block(b,dx,dy):
    return re.sub(r'\(at ([-\d.]+) ([-\d.]+)( \d+)?\)',lambda m:'(at %g %g%s)'%(round(float(m.group(1))+dx,4),round(float(m.group(2))+dy,4),m.group(3) or ''),b)
for s,e,h in sx.spans(t):
    if h=='sheet' and sx.prop(t[s:e],'Sheetname')=='Industrial_IO':
        t=t[:s]+shift_block(t[s:e],88.9,-86.36)+t[e:]; break
for s,e,h in sx.spans(t):
    if h=='sheet' and sx.prop(t[s:e],'Sheetname')=='MCU_and_Encoders':
        b=t[s:e]; tmpl=re.search(r'\t\t\(pin "VBAT_SENSE".*?\n\t\t\)\n',b,re.S).group(0); pins=''
        for name,typ,y in (('GPS_TX','output',45.72),('GPS_RX','input',50.8),('GPS_PPS','input',55.88),('IMU_INT','input',60.96),('IMU_RST','output',66.04)):
            p=re.sub(r'"VBAT_SENSE" \w+','"%s" %s'%(name,typ),tmpl); p=re.sub(r'\(at ([\d.]+) ([\d.]+) (\d+)\)','(at 124.46 %g 180)'%y,p,count=1)
            pins+=re.sub(r'\(uuid "[^"]+"\)','(uuid "%s")'%U(),p)
        i=b.index('\t\t(instances'); t=t[:s]+b[:i]+pins+b[i:]+t[e:]; break
spins=[('GPS_TX','input',88.9),('GPS_RX','output',93.98),('GPS_PPS','output',99.06),('IMU_INT','output',104.14),('IMU_RST','input',109.22),('I2C_SDA','bidirectional',114.3),('I2C_SCL','input',119.38)]
blk=f'''\t(sheet
\t\t(at 213.36 80.01)
\t\t(size 55.88 45.72)
\t\t(fields_autoplaced yes)
\t\t(stroke
\t\t\t(width 0.1524)
\t\t\t(type solid)
\t\t)
\t\t(fill
\t\t\t(color 0 0 0 0.0000)
\t\t)
\t\t(uuid "{SU}")
\t\t(property "Sheetname" "Sensors"
\t\t\t(at 213.36 78.74 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(justify left bottom)
\t\t\t)
\t\t)
\t\t(property "Sheetfile" "Sensors.kicad_sch"
\t\t\t(at 213.36 126.49 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(justify left top)
\t\t\t)
\t\t)
'''+''.join(f'\t\t(pin "{n}" {ty}\n\t\t\t(at 213.36 {y} 180)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(justify left)\n\t\t\t)\n\t\t\t(uuid "{U()}")\n\t\t)\n' for n,ty,y in spins)+f'''\t\t(instances
\t\t\t(project "abx-motion-brushless"
\t\t\t\t(path "/{ROOT}"
\t\t\t\t\t(page "10")
\t\t\t\t)
\t\t\t)
\t\t)
\t)
'''
i=t.index('\t(sheet_instances') if '\t(sheet_instances' in t else len(t)-2
t=t[:i]+blk+t[i:]
rm=[(s,e) for s,e,h in sx.spans(t) if h in('wire','label')]
def cut(t,s,e):
    j=s
    while t[j-1] in ' \t': j-=1
    if t[j-1]=='\n': j-=1
    return t[:j]+t[e:]
for s,e in sorted(rm,reverse=True): t=cut(t,s,e)
add=[]
for s,e,h in sx.spans(t):
    if h!='sheet': continue
    for name,x,y,a in re.findall(r'\(pin "([^"]+)" \w+\s*\(at ([\d.]+) ([\d.]+) (\d+)\)',t[s:e]):
        x=float(x);y=float(y);a=int(a); x2=x+7.62 if a==0 else x-7.62; j='left' if a==0 else 'right'
        add.append(f'\t(wire (pts (xy {x:g} {y:g}) (xy {x2:g} {y:g})) (stroke (width 0) (type default)) (uuid "{U()}"))\n\t(label "{name}" (at {x2:g} {y:g} {a}) (fields_autoplaced yes) (effects (font (size 1.27 1.27)) (justify {j} bottom)) (uuid "{U()}"))\n')
i=t.index('(sheet\n'); i=t.rfind('\n',0,i)+1
open('abx-motion-brushless.kicad_sch','w').write(t[:i]+''.join(add)+t[i:])
print('ok sheet uuid',SU)
