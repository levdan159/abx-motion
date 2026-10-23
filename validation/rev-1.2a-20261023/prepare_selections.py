from pathlib import Path
import json
O=Path(__file__).resolve().parent
rs=json.loads((O/'inventory.json').read_text());sel={}
values={'100':'C22775','10k':'C25804','1k':'C21190','4.7k':'C23162','10nF':'C57112','100nF 16V X7R':'C14663','100nF 63V X7R':'C77058','10nF 63V X7R':'C162275','1uF 10V X7R':'C59782','1uF 16V X7R':'C59782','100uF 63V':'C88747','B3B-PH-K-S':'C131339','DRV8462DDWR':'C5930226','PCA9555PW,118':'C128392','SN74AHCT14PWR':'C7481','SN74HC08PWR':'C7642','SN74HC74PWR':'C6761','SN74LVC2G08DCUR':'C91875','TPS3431SDRBR':'C702145','ONBOARD / EXT':'C492402','EXT 5V TTL EN_N STEP DIR GND':'C492403','JST-XH MOTOR 1':'C566014','JST-XH MOTOR 2':'C566014','JST-XH MOTOR 3':'C566014'}
for r in rs:
 if r['ref'].startswith(('H','TP_')):continue
 if r['ref']=='J208':continue
 c=r['props'].get('LCSC','') or values.get(r['value'])
 assert c,r
 sel[r['ref']]=c
(O/'selections.json').write_text(json.dumps(sel,indent=2)+'\n')
print(len(sel),'catalogued placements',len(set(sel.values())),'unique SKUs; J208 separately sourced')
