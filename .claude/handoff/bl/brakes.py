import re,sys,uuid,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); import sx
U=lambda:str(uuid.uuid4())
ROOT='f9149098-3f23-438d-bdc2-2e278b5ca35b'; SU=U()
def libsym(path,name,rename=None):
    t=open(path).read(); ls=[x for x in sx.spans(t) if x[2]=='lib_symbols']
    inner=t[ls[0][0]:ls[0][1]] if ls else t
    for s,e,h in sx.spans(inner,depth=1):
        b=inner[s:e]
        if b.startswith(f'(symbol "{name}"'):
            return b.replace(f'(symbol "{name}"',f'(symbol "{rename}"',1) if rename else b
def pinsof(b):
    out={}
    for m in re.finditer(r'\(pin (\w+) (\w+)\s+\(at ([-\d.]+) ([-\d.]+) (\d+)\)',b):
        k=b.index('(number "',m.start()); n=re.match(r'\(number "([^"]*)"',b[k:]).group(1); out[n]=(float(m.group(3)),float(m.group(4)),int(m.group(5)))
    return out
SYS='/usr/share/kicad/symbols/Device.kicad_sym'
LIBS={'Regulator_Switching:LMR33630ADDA':libsym('Power.kicad_sch','Regulator_Switching:LMR33630ADDA'),
 'Device:R':libsym('Power.kicad_sch','Device:R'),'Device:C':libsym('Power.kicad_sch','Device:C'),'Device:L':libsym('Power.kicad_sch','Device:L'),
 'Connector:Conn_01x02_Pin':libsym('Power.kicad_sch','Connector:Conn_01x02_Pin'),
 '74xGxx:74LVC1G08':libsym('ESC_Channel.kicad_sch','74xGxx:74LVC1G08'),
 'Device:Q_NMOS_GSD':libsym(SYS,'Q_NMOS_GSD','Device:Q_NMOS_GSD'),'Device:D_Schottky':libsym(SYS,'D_Schottky','Device:D_Schottky')}
PINS={k:pinsof(v) for k,v in LIBS.items()}
GLOBAL={'+BATT','GND','+3V3'}
HIER={'BRAKE1_EN':'input','BRAKE2_EN':'input','ESTOP_SENSE':'output','+3V3_DRV_EN':'input'}
body=''; nets={}
def g(v): return round(round(v/1.27)*1.27,2)
def place(lib,ref,val,fp,x,y,pm):
    global body
    x,y=g(x),g(y)
    pin_uu=''.join(f'\t\t(pin "{n}"\n\t\t\t(uuid "{U()}")\n\t\t)\n' for n in PINS[lib])
    body+=f'''\t(symbol
\t\t(lib_id "{lib}")
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
\t\t\t(at {x+2.54} {y-2.54} 0)
\t\t\t(effects (font (size 1.27 1.27)) (justify left))
\t\t)
\t\t(property "Value" "{val}"
\t\t\t(at {x+2.54} {y+2.54} 0)
\t\t\t(effects (font (size 1.27 1.27)) (justify left))
\t\t)
\t\t(property "Footprint" "{fp}"
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
{pin_uu}\t\t(instances
\t\t\t(project "abx-motion-brushless"
\t\t\t\t(path "/{ROOT}/{SU}"
\t\t\t\t\t(reference "{ref}")
\t\t\t\t\t(unit 1)
\t\t\t\t)
\t\t\t)
\t\t)
\t)
'''
    for n,net in pm.items():
        px,py,a=PINS[lib][n]; lx,ly=round(x+px,2),round(y-py,2); la=(a+180)%360
        body+=label(net,lx,ly,la)
def label(net,x,y,a):
    j='right' if a==180 else 'left'
    if net=='NC': return f'\t(no_connect\n\t\t(at {x} {y})\n\t\t(uuid "{U()}")\n\t)\n'
    if net in HIER: return f'\t(hierarchical_label "{net}"\n\t\t(shape {HIER[net]})\n\t\t(at {x} {y} {a})\n\t\t(effects (font (size 1.27 1.27)) (justify {j}))\n\t\t(uuid "{U()}")\n\t)\n'
    if net in GLOBAL: return f'\t(global_label "{net}"\n\t\t(shape passive)\n\t\t(at {x} {y} {a})\n\t\t(effects (font (size 1.27 1.27)) (justify {j}))\n\t\t(uuid "{U()}")\n\t)\n'
    return f'\t(label "{net}"\n\t\t(at {x} {y} {a})\n\t\t(effects (font (size 1.27 1.27)) (justify {j} bottom))\n\t\t(uuid "{U()}")\n\t)\n'
def txt(s,x,y,size=1.27): 
    global body; body+=f'\t(text "{s}"\n\t\t(exclude_from_sim no)\n\t\t(at {x} {y} 0)\n\t\t(effects (font (size {size} {size})) (justify left bottom))\n\t\t(uuid "{U()}")\n\t)\n'
C0603='Capacitor_SMD:C_0603_1608Metric'; R0603='Resistor_SMD:R_0603_1608Metric'
# --- 24 V buck (same topology as the 5 V buck on the Power sheet; divider changed)
place('Regulator_Switching:LMR33630ADDA','U501','LMR36520FADDA','Package_SO:Texas_HSOP-8-1EP_3.9x4.9mm_P1.27mm',68.58,60.96,{'2':'+BATT','3':'+BATT','6':'BR_VCC','1':'GND','9':'GND','7':'BR_BOOT','8':'BR_SW','5':'BR_FB','4':'NC'})
place('Device:C','C505','4.7uF/100V','Capacitor_SMD:C_1206_3216Metric',25.4,101.6,{'1':'+BATT','2':'GND'})
place('Device:C','C506','4.7uF/100V','Capacitor_SMD:C_1206_3216Metric',40.64,101.6,{'1':'+BATT','2':'GND'})
place('Device:C','C507','100nF/100V',C0603,55.88,101.6,{'1':'+BATT','2':'GND'})
place('Device:C','C501','100nF',C0603,76.2,101.6,{'1':'BR_BOOT','2':'BR_SW'})
place('Device:C','C502','1uF',C0603,91.44,101.6,{'1':'BR_VCC','2':'GND'})
place('Device:L','L501','47uH 3A','Inductor_SMD:L_Bourns_SRP7028A_7.3x6.6mm',106.68,101.6,{'1':'BR_SW','2':'+24V_BRAKE'})
place('Device:R','R501','100k',R0603,121.92,101.6,{'1':'+24V_BRAKE','2':'BR_FB'})
place('Device:R','R502','4.32k',R0603,137.16,101.6,{'1':'BR_FB','2':'GND'})
place('Device:C','C503','22uF/50V','Capacitor_SMD:C_1210_3225Metric',152.4,101.6,{'1':'+24V_BRAKE','2':'GND'})
place('Device:C','C504','22uF/50V','Capacitor_SMD:C_1210_3225Metric',167.64,101.6,{'1':'+24V_BRAKE','2':'GND'})
# --- two brake drivers: coil on while (MCU enable AND hardware E-stop). Fail-safe: no power / E-stop / MCU fault -> MOSFET off -> spring brake applied.
for i,(y,en,u,rg,rp,q,d,j,c) in enumerate(((152.4,'BRAKE1_EN','U502','R503','R504','Q501','D501','J501','C508'),(190.5,'BRAKE2_EN','U503','R505','R506','Q502','D502','J502','C509')),1):
    place('74xGxx:74LVC1G08',u,'74LVC1G08','Package_TO_SOT_SMD:SOT-23-5',48.26,y,{'1':en,'2':'+3V3_DRV_EN','3':'GND','4':f'BRK{i}_G','5':'+3V3'})
    place('Device:C',c,'100nF',C0603,25.4,y,{'1':'+3V3','2':'GND'})
    place('Device:R',rg,'22',R0603,83.82,y,{'1':f'BRK{i}_G','2':f'BRK{i}_GR'})
    place('Device:R',rp,'100k',R0603,99.06,y+7.62,{'1':f'BRK{i}_GR','2':'GND'})
    place('Device:Q_NMOS_GSD',q,'SI2318CDS','Package_TO_SOT_SMD:SOT-23',119.38,y,{'1':f'BRK{i}_GR','2':'GND','3':f'BRK{i}_COIL_N'})
    place('Device:D_Schottky',d,'SS34','Diode_SMD:D_SMA',144.78,y,{'1':'+24V_BRAKE','2':f'BRK{i}_COIL_N'})
    place('Connector:Conn_01x02_Pin',j,f'BRAKE{i}','TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal',177.8,y,{'1':'+24V_BRAKE','2':f'BRK{i}_COIL_N'})
# --- E-stop sense for the MCU
place('Device:R','R507','1k',R0603,226.06,60.96,{'1':'+3V3_DRV_EN','2':'ESTOP_SENSE'})
txt('BRAKES: fail-safe (spring-applied, power-off) holding brakes for the 2 drive motors',25.4,25.4,2)
txt('+24V_BRAKE: LMR36520FADDA buck from +BATT (F1/Q1 protected). Vout = 1.0 V x (1 + R501/R502) = 24.1 V. Check brake coil voltage; use 12 V by changing R502 to 9.09k.',25.4,33.02)
txt('Coil is ENERGISED (brake released) only while BRAKEn_EN = 1 AND +3V3_DRV_EN (hardware E-stop) = 1. Any E-stop, MCU reset or power loss -> MOSFET off -> brake applies.',25.4,38.1)
txt('D501/D502 freewheel the coil: slow engage after power off. Add a series zener for faster decay if the brake must stop the robot quickly.',25.4,43.18)
txt('R507: ESTOP_SENSE reads the E-stop state (+3V3_DRV_EN) on an ESP32 input. Brake rating assumed <= 1 A per coil at 24 V.',25.4,48.26)
libtxt='\n\t\t'.join(LIBS.values())
sheet=f'''(kicad_sch
\t(version 20250114)
\t(generator "eeschema")
\t(generator_version "10.0")
\t(uuid "{U()}")
\t(paper "A4")
\t(lib_symbols
\t\t{libtxt}
\t)
{body}\t(sheet_instances
\t\t(path "/"
\t\t\t(page "1")
\t\t)
\t)
\t(embedded_fonts no)
)
'''
open('Brakes.kicad_sch','w').write(sheet)
# --- Q_NMOS_GSD lib fix in Industrial_IO
t=open('Industrial_IO.kicad_sch').read(); t=t.replace('Transistor_FET:Q_NMOS_GSD','Device:Q_NMOS_GSD'); open('Industrial_IO.kicad_sch','w').write(t)
# --- MCU hier labels
def mcu(t):
    add=''
    for name,shape,x,y,a in (('BRAKE1_EN','output',73.66,99.06,180),('BRAKE2_EN','output',73.66,101.6,180),('ESTOP_SENSE','input',73.66,104.14,180),('ESC1_NRST','output',73.66,106.68,180),('ESC2_NRST','output',104.14,109.22,0)):
        j='left' if a==0 else 'right'
        add+=f'\t(hierarchical_label "{name}"\n\t\t(shape {shape})\n\t\t(at {x} {y} {a})\n\t\t(effects (font (size 1.27 1.27)) (justify {j}))\n\t\t(uuid "{U()}")\n\t)\n'
    ef=[s for s,e,h in sx.spans(t) if h=='embedded_fonts']; i=t.rfind('\n',0,ef[-1])+1 if ef else len(t)-2
    return t[:i]+add+t[i:]
t=open('MCU.kicad_sch').read(); open('MCU.kicad_sch','w').write(mcu(t))
# --- ESC_Channel: ESC_NRST hier label on the NRST net
t=open('ESC_Channel.kicad_sch').read()
m=re.search(r'\(label "NRST"\s*\(at ([-\d.]+) ([-\d.]+) (\d+)\)',t)
x,y,a=m.group(1),m.group(2),int(m.group(3)); j='right' if a==180 else 'left'
hl=f'\t(hierarchical_label "NRST"\n\t\t(shape input)\n\t\t(at {x} {y} {a})\n\t\t(effects (font (size 1.27 1.27)) (justify {j}))\n\t\t(uuid "{U()}")\n\t)\n'
ef=[s for s,e,h in sx.spans(t) if h=='embedded_fonts']; i=t.rfind('\n',0,ef[-1])+1 if ef else len(t)-2
open('ESC_Channel.kicad_sch','w').write(t[:i]+hl+t[i:]); print('ESC NRST label at',x,y,a)
# --- root
t=open('abx-motion-brushless.kicad_sch').read()
tmpl_pin=lambda b: re.search(r'\t\t\(pin "VBAT_SENSE".*?\n\t\t\)\n',b,re.S).group(0)
def addpins(t,sheetname,pins):
    for s,e,h in sx.spans(t):
        if h=='sheet' and sx.prop(t[s:e],'Sheetname')==sheetname:
            b=t[s:e]; tm=re.search(r'\t\t\(pin "[^"]+" \w+.*?\n\t\t\)\n',b,re.S).group(0); out=''
            for name,typ,x,y,a in pins:
                p=re.sub(r'\(pin "[^"]+" \w+','(pin "%s" %s'%(name,typ),tm,count=1); p=re.sub(r'\(at [\d.]+ [\d.]+ \d+\)','(at %g %g %d)'%(x,y,a),p,count=1)
                p=re.sub(r'\(justify \w+\)','(justify %s)'%('left' if a==180 else 'right'),p)
                out+=re.sub(r'\(uuid "[^"]+"\)','(uuid "%s")'%U(),p)
            i=re.search(r'\n[ \t]*\(instances',b).start()+1; return t[:s]+b[:i]+out+b[i:]+t[e:]
t=addpins(t,'MCU_and_Encoders',[('BRAKE1_EN','output',124.46,71.12,180),('BRAKE2_EN','output',124.46,76.2,180),('ESTOP_SENSE','input',124.46,81.28,180),('ESC1_NRST','output',124.46,86.36,180),('ESC2_NRST','output',124.46,91.44,180)])
t=addpins(t,'ESC_Motor_1',[('NRST','input',76.2,144.78,0)]); t=addpins(t,'ESC_Motor_2',[('NRST','input',180.34,144.78,0)])
spins=[('BRAKE1_EN','input',137.16),('BRAKE2_EN','input',142.24),('ESTOP_SENSE','output',147.32),('+3V3_DRV_EN','input',152.4)]
blk=f'''\t(sheet
\t\t(at 213.36 129.54)
\t\t(size 55.88 30.48)
\t\t(fields_autoplaced yes)
\t\t(stroke
\t\t\t(width 0.1524)
\t\t\t(type solid)
\t\t)
\t\t(fill
\t\t\t(color 0 0 0 0.0000)
\t\t)
\t\t(uuid "{SU}")
\t\t(property "Sheetname" "Brakes"
\t\t\t(at 213.36 128.27 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(justify left bottom)
\t\t\t)
\t\t)
\t\t(property "Sheetfile" "Brakes.kicad_sch"
\t\t\t(at 213.36 160.78 0)
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
\t\t\t\t\t(page "11")
\t\t\t\t)
\t\t\t)
\t\t)
\t)
'''
i=t.index('\t(sheet_instances'); t=t[:i]+blk+t[i:]
# regenerate stubs
def cut(t,s,e):
    j=s
    while t[j-1] in ' \t': j-=1
    if t[j-1]=='\n': j-=1
    return t[:j]+t[e:]
for s,e in sorted([(s,e) for s,e,h in sx.spans(t) if h in('wire','label')],reverse=True): t=cut(t,s,e)
add=[]
for s,e,h in sx.spans(t):
    if h!='sheet': continue
    sname=sx.prop(t[s:e],'Sheetname')
    for name,x,y,a in re.findall(r'\(pin "([^"]+)" \w+\s*\(at ([\d.]+) ([\d.]+) (\d+)\)',t[s:e]):
        lab=name
        if name=='NRST': lab='ESC1_NRST' if sname=='ESC_Motor_1' else 'ESC2_NRST'
        x=float(x);y=float(y);a=int(a); x2=x+7.62 if a==0 else x-7.62; j='left' if a==0 else 'right'
        add.append(f'\t(wire (pts (xy {x:g} {y:g}) (xy {x2:g} {y:g})) (stroke (width 0) (type default)) (uuid "{U()}"))\n\t(label "{lab}" (at {x2:g} {y:g} {a}) (fields_autoplaced yes) (effects (font (size 1.27 1.27)) (justify {j} bottom)) (uuid "{U()}"))\n')
i=t.index('(sheet\n'); i=t.rfind('\n',0,i)+1
open('abx-motion-brushless.kicad_sch','w').write(t[:i]+''.join(add)+t[i:]); print('done',SU)
