"""Derive a proposed pin/net contract and measured placement distances; no PCB edits."""
from pathlib import Path
import pcbnew,json,math,hashlib
R=Path(__file__).resolve().parents[2];O=R/'variants/ABX-Motion-ETH';A=Path(__file__).resolve().parent
b=pcbnew.LoadBoard(str(O/'abx-motion-eth-placement.kicad_pcb'));fs={f.GetReference():f for f in b.GetFootprints()}
N={}
def bind(ref,pins):
 for p,n in pins.items():N[f'{ref}.{p}']=n
bind('U802',{1:'ETH_VCC_INT',2:'NC',3:'ETH_BUCK_EN',4:'+BATT',5:'ETH_SW',6:'ETH_BOOT',7:'ETH_VCC_INT',8:'3V3_ETH',9:'GND'})
bind('L801',{1:'3V3_ETH',2:'ETH_SW'})
for r in ['C821','C822']:bind(r,{1:'+BATT',2:'GND'})
bind('C823',{1:'GND',2:'+BATT'});bind('C824',{1:'ETH_BOOT',2:'ETH_SW'});bind('C825',{1:'ETH_VCC_INT',2:'GND'})
for r in ['C826','C827']:bind(r,{1:'GND',2:'3V3_ETH'})
bind('R817',{1:'+3V3',2:'ETH_BUCK_EN'});bind('R818',{1:'ETH_BUCK_EN',2:'GND'})
bind('TP_ETH_3V3',{1:'3V3_ETH'})
bind('U804',{1:'+3V3',2:'STEP_SPI_SCLK',3:'STEP_SPI_MOSI',4:'MCU_ETH_CS_N',5:'ETH_MISO_BUF',6:'NC',7:'GND',8:'ETH_SPI_OE',9:'NC',10:'ETH_MISO',11:'ETH_CS_N',12:'ETH_MOSI_BUF',13:'ETH_SCLK_BUF',14:'3V3_ETH'})
bind('C828',{1:'+3V3',2:'GND'});bind('C829',{1:'GND',2:'3V3_ETH'})
bind('Q802',{1:'MCU_ETH_CS_N',2:'GND',3:'ETH_SPI_OE'})
bind('R820',{1:'+3V3',2:'ETH_SPI_OE'});bind('R821',{1:'+3V3',2:'MCU_ETH_CS_N'})
bind('R813',{1:'ETH_SCLK',2:'ETH_SCLK_BUF'});bind('R814',{1:'ETH_MOSI',2:'ETH_MOSI_BUF'});bind('R815',{1:'STEP_SPI_MISO',2:'ETH_MISO_BUF'})
bind('R809',{1:'3V3_ETH',2:'ETH_CS_N'})
bind('U803',{1:'ETH_RESET_N',2:'GND',3:'ETH_MR_N',4:'NC',5:'3V3_ETH',6:'3V3_ETH'})
bind('Q801',{1:'ETH_RESET_REQ',2:'GND',3:'ETH_MR_N'})
bind('C819',{1:'3V3_ETH',2:'GND'});bind('R810',{1:'ETH_RESET_N',2:'3V3_ETH'});bind('R816',{1:'ETH_RESET_REQ',2:'GND'});bind('R819',{1:'3V3_ETH',2:'ETH_MR_N'})
bind('U801',{18:'NC',20:'ETH_TOCAP',22:'ETH_1V2O',32:'ETH_CS_N',33:'ETH_SCLK',34:'ETH_MISO',35:'ETH_MOSI',37:'ETH_RESET_N'})
bind('C809',{1:'GND',2:'ETH_TOCAP'});bind('C810',{1:'GND',2:'ETH_1V2O'})
# Documented proposed nets ONLY. Every new PCB pad remains net0 until schematic.
def pad(key):
 r,n=key.split('.');ps=[p for p in fs[r].Pads() if p.GetNumber()==n];assert len(ps)==1,key
 return ps[0]
rows=[]
for key,n in N.items():
 p=pad(key);pos=p.GetPosition();rows.append(dict(pin=key,proposed_net=n,position_mm=[pos.x/1e6,pos.y/1e6],pcb_net=p.GetNetname()))
assert all(not r['pcb_net'] for r in rows)
links=[('U802.4','C823.2','VIN-to-HF input pad'),('U802.9','C823.1','HF capacitor ground-to-IC ground'),('U802.6','C824.1','BOOT local loop'),('U802.5','C824.2','SW bootstrap return'),('U802.5','L801.2','SW output to inductor'),('U802.7','C825.1','internal VCC bypass'),('L801.1','C827.2','inductor output to first output cap'),('U804.1','C828.1','main3V3 isolator bypass'),('U804.14','C829.2','Ethernet3V3 isolator bypass'),('U801.20','C809.2','TOCAP local capacitor'),('U801.22','C810.2','1V2O local capacitor'),('U803.6','C819.1','supervisor VDD bypass')]
measures=[]
for x,y,desc in links:
 p=pad(x).GetPosition();q=pad(y).GetPosition();measures.append(dict(from_pin=x,to_pin=y,role=desc,straight_pad_center_distance_mm=round(math.hypot(p.x-q.x,p.y-q.y)/1e6,3)))
report=dict(date='2026-10-24',status='PROPOSED CONNECTIONS ONLY; NOT A CONNECTED SCHEMATIC OR ROUTED BOARD',input_net='+BATT = Q1 sources/U1 VIN protected battery node; do not use V_FUSED',input_normal_max_v=32,output_v=3.3,converter_current_rating_a=.6,ethernet_planned_allocation_a=.3,usb_only_behavior='Ethernet off without VBAT. Main logic/USB may remain on; U804 isolates domains.',pin_net_table=rows,placement_distances=measures,NC=['U802.2 PG unused','U803.4 CT float for20ms nominal delay','U804.6','U804.9','U801.18 VBG float'],remaining_pin_definitions='Other W5500 pins/MDI, crystal, ESD and shield topology still require reference schematic integration.',
firmware_contract=dict(spi_mode=0,initial_spi_mhz=10,qualify_spi_mhz=20,cs_setup_hold_turnaround_us=2,oe='HIGH only when MCU_ETH_CS_N is LOW. Q802 inverter; R820 pullup to MAIN +3V3.',miso='U804 outputs high-Z whenever deselected or a supply is absent. Do not tie OE permanently high.',cs_timing='Configure hardware CS setup/hold/guard time if supported, otherwise manual GPIO CS under shared SPI lock. Verify enable/disable latency at both domain voltages.',reset='Assert U601 IO1_6 through Q801 for >=1ms, release, wait >=30ms, then check VERSIONR and link; supervisor CT open defaults20ms nominal.',shared_bus_lock='Acquire before any expander-controlled stepper CS assertion; keep until CS deasserted; serialize Ethernet too.',mcu_changes_pending='GPIO3/LED_STAT repurpose and U601 pads18/19 currently GND must be changed in BOTH schematic and PCB, with boot strap review.'),
source_files=[dict(file=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in (A/'sources').glob('*.pdf')])
(O/'layout-review/power-interface-design.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(measures,indent=1))
