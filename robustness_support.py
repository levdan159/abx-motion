"""Reviewed schematic primitives for the local 7S robustness revision.

TVS3300DRVR is a pulse clamp, not a continuous regenerative-energy sink.
DRV package: GND pins 1/2/3 and EP; protected input pins 4/5/6.
Source: TI SLVSDO2C, pin table and DRV0006A land pattern.
"""
TVS_FP = 'abx-footprints:TVS3300_DRV0006A_2x2mm'
TVS_SKU = 'C2863624'

def tvs3300_symbol():
    pins = []
    for number, name, x, y, angle in [
        (4,'IN',-7.62,2.54,0),(5,'IN',-7.62,0,0),(6,'IN',-7.62,-2.54,0),
        (1,'GND',7.62,2.54,180),(2,'GND',7.62,0,180),(3,'GND',7.62,-2.54,180),
        (7,'EP_GND',0,-7.62,90)]:
        pins.append(f'''(pin passive line (at {x} {y} {angle}) (length 2.54)
            (name "{name}" (effects (font (size 1.0 1.0))))
            (number "{number}" (effects (font (size 1.0 1.0)))))''')
    return f'''(symbol "TVS3300DRVR"
        (pin_names (offset 0.5)) (in_bom yes) (on_board yes)
        (property "Reference" "D" (at 0 6.35 0) (effects (font (size 1.27 1.27))))
        (property "Value" "TVS3300DRVR" (at 0 -10.16 0) (effects (font (size 1.27 1.27))))
        (property "Footprint" "{TVS_FP}" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
        (property "Datasheet" "https://www.ti.com/lit/ds/symlink/tvs3300.pdf" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
        (symbol "TVS3300DRVR_0_1" (rectangle (start -5.08 5.08) (end 5.08 -5.08)
            (stroke (width 0.254) (type default)) (fill (type background))))
        (symbol "TVS3300DRVR_1_1" {''.join(pins)})
        (embedded_fonts no))'''

def place_tvs3300(sb):
    d = sb.place_sym('abx:TVS3300DRVR', 'D2', 'TVS3300DRVR', TVS_FP, 142.24, 71.12, 0)
    # One visible power symbol per pin bank keeps the drawing legible.
    for pins,x,net,ey in [(['4','5','6'],130.81,'+BATT',64.77),
                          (['1','2','3'],153.67,'GND',77.47)]:
        ys=[]
        for pin in pins:
            q=d['pins'][pin];ys.append(q['y'])
            sb.add_wire(q['x'],q['y'],x,q['y'])
        sb.add_wire(x,min(ys),x,max(ys))
        sb.add_junction(x,71.12)
        sy=min(ys) if net=='+BATT' else max(ys)
        sb.add_wire(x,sy,x,ey)
        ref=f'#PWR{type(sb).pwr_counter:03d}';type(sb).pwr_counter+=1
        sb.place_sym('power:'+net,ref,net,'',x,ey,0)
    sb.stub_power(d,'7','GND')
    return d
