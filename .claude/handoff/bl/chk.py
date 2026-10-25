import re,subprocess,sys
subprocess.run(['kicad-cli','sch','export','netlist','--format','kicadsexpr','-o','/tmp/claude-1000/nl3.net','abx-motion-brushless.kicad_sch'],capture_output=True)
t=open('/tmp/claude-1000/nl3.net').read(); body=t[t.index('\t(nets'):]; nets={}
for chunk in re.split(r'\n\t\t\(net\n',body)[1:]:
    n=re.search(r'\(name "([^"]+)"\)',chunk).group(1)
    nets[n]=set(f'{r}.{p}' for r,p in re.findall(r'\(node\s+\(ref "([^"]+)"\)\s+\(pin "([^"]+)"',chunk))
def net_of(pin,prefix):
    for n,s in nets.items():
        if pin in s and (n.startswith(prefix) or not n.startswith('/')): return n,s
    return None,set()
E={'PH_A':['Q#01.1','Q#01.2','Q#01.3','Q#02.5','U#02.7','R#16.1','J#01.1'],'PH_B':['Q#03.1','Q#04.5','U#02.14','R#17.1','J#02.1'],'PH_C':['Q#05.1','Q#06.5','U#02.17','R#18.1','J#03.1'],
'SPA':['Q#02.1','U#02.9','R#07.1'],'SPB':['Q#04.1','U#02.12','R#08.1'],'SPC':['Q#06.1','U#02.19','R#09.1'],
'GHA':['U#02.6','R#10.1'],'GHA_G':['R#10.2','Q#01.4'],'GLA':['U#02.8','R#11.1'],'GLA_G':['R#11.2','Q#02.4'],'GHB':['U#02.15','R#12.1'],'GHB_G':['R#12.2','Q#03.4'],'GLB':['U#02.13','R#13.1'],'GLB_G':['R#13.2','Q#04.4'],'GHC':['U#02.16','R#14.1'],'GHC_G':['R#14.2','Q#05.4'],'GLC':['U#02.18','R#15.1'],'GLC_G':['R#15.2','Q#06.4'],
'INHA':['U#01.41','U#02.34'],'INLA':['U#01.34','U#02.35'],'INHB':['U#01.42','U#02.36'],'INLB':['U#01.35','U#02.37'],'INHC':['U#01.43','U#02.38'],'INLC':['U#01.36','U#02.39'],
'DRV_nSCS':['U#01.40','U#02.29','R#03.2'],'DRV_SCLK':['U#01.56','U#02.28'],'DRV_SDI':['U#01.53','U#02.27'],'DRV_SDO':['U#01.55','U#02.26','R#02.2'],'nFAULT':['U#01.59','U#02.25','R#01.2'],'ENABLE':['U#03.4','U#02.30'],'ENABLE_MCU':['U#01.57','U#03.1','R#05.1'],
'SOA':['U#02.23','U#01.8'],'SOB':['U#02.22','U#01.9'],'SOC':['U#02.21','U#01.10'],'SENS_A':['R#16.2','R#19.1','C#30.1','U#01.14'],'SENS_B':['R#17.2','R#20.1','C#31.1','U#01.15'],'SENS_C':['R#18.2','R#21.1','C#32.1','U#01.16'],
'VIN_SENS':['R#22.2','R#23.1','C#33.1','U#01.11'],'TEMP_PCB':['NT#01.2','R#24.1','U#01.17'],'TEMP_MOT':['R#25.2','C#34.1','J#04.5','U#01.24'],'CAN_TX':['U#01.62','U#04.1'],'CAN_RX':['U#01.61','U#04.4'],
'HALL1':['R#26.2','R#29.2','C#40.1','U#01.37'],'HALL2':['R#27.2','R#30.2','C#41.1','U#01.38'],'HALL3':['R#28.2','R#31.2','C#42.1','U#01.39'],'HALL1_IN':['R#26.1','J#04.2'],
'CPH':['U#02.2','C#16.1'],'CPL':['U#02.1','C#16.2'],'VCP':['U#02.3','C#17.1'],'DVDD':['U#02.33','C#18.1'],'VDDA_ESC':['U#01.13','C#07.1','C#08.1','FB#01.2'],'VCAP1':['U#01.31','C#09.1'],'VCAP2':['U#01.47','C#10.1'],
'OSC_IN':['U#01.5','Y#01.1','C#11.1'],'OSC_OUT':['U#01.6','Y#01.3','C#12.1'],'NRST':['U#01.7','C#01.1','J#07.4'],'BOOT0':['U#01.60','R#32.1','J#08.1'],'SWDIO':['U#01.46','J#07.2'],'SWCLK':['U#01.49','J#07.3'],
'LED_G':['U#01.26','R#33.1'],'LED_R':['U#01.27','R#34.1'],'ENC_CS':['U#01.20','J#05.6'],'ENC_SCK':['U#01.21','J#05.3'],'ENC_MISO':['U#01.22','J#05.4'],'ENC_MOSI':['U#01.23','J#05.5'],'UART_TX':['U#01.29','J#06.2'],'UART_RX':['U#01.30','J#06.3'],
'+3V3_ESC':['U#05.5','U#01.1','U#01.19','U#01.32','U#01.48','U#01.64','U#02.24','U#03.5','U#04.5','U#04.4' if False else 'U#04.5','R#01.1','R#29.1','NT#01.1','J#05.1','J#07.1','J#08.2'],
}
bad=0
for pre,d in (('/ESC_Motor_1/','3'),('/ESC_Motor_2/','4')):
    for netname,pins in E.items():
        pins=[re.sub(r'#(\d\d)',d+r'\1',x) for x in pins]
        n,s=net_of(pins[0],pre); miss=[p for p in pins if p not in s]
        if miss: bad+=1; print(pre,netname,'->',n,'MISSING',miss)
G={'VBUS':['U302.4','U302.5','Q301.5','Q303.5','Q305.5','R322.1','C321.1','C328.1','U402.4','Q401.5','R422.1'],'GND':['U302.32','U302.40','U302.41','U302.10','R307.2','U301.12','U301.18','U301.63','U304.2','U304.8','J304.6','U402.32','C340.2','C440.2','C315.2' if False else 'C302.2'],'+5V':['U305.1','U305.3','U304.3','J304.1','J306.1','U405.1','U404.3'],'+3V3_DRV_EN':['U303.2','R306.1','U403.2']}
for g,pins in G.items():
    ns=[k for k,s in nets.items() if pins[0] in s]
    s=nets[ns[0]]; miss=[p for p in pins if p not in s]; print('global',g,ns[0],'missing',miss)
print('ESC mismatches',bad)
