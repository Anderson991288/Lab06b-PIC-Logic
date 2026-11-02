"""Selected GDS41 nets / GDS39 heater contacts, used for baseline and faults."""
import pya
def evaluate(metal,heaters,info,db):
    nets=list(metal.each());signals=[p for p in info['pads'] if p['net']!='GND'];grounds=[p for p in info['pads'] if p['net']=='GND']
    def hits(point):return [k for k,p in enumerate(nets) if p.inside(pya.Point(*(round(v/db) for v in point)))]
    pads={p['pad_id']:hits(p['center_um']) for p in info['pads']}
    gids={h[0] for p in grounds if len(h:=pads[p['pad_id']])==1};gid=next(iter(gids)) if len(gids)==1 else None
    connections=[];contacts=[]
    for p in signals:
        ids=pads[p['pad_id']];a=hits(p['signal_contact_um']);b=hits(p['return_contact_um'])
        connections.append(dict(channel=p['channel'],pad_id=p['pad_id'],pad_component=ids,signal_A_components=a,return_B_components=b,
            passed=len(ids)==1 and ids==a and b==[gid] and ids[0]!=gid))
        h=[poly for poly in heaters.each() if poly.inside(pya.Point(*(round(v/db) for v in p['heater_center_um'])))]
        touched=[] if len(h)!=1 else [k for k,poly in enumerate(nets) if not (pya.Region(h[0])&pya.Region(poly)).is_empty()]
        expected=set(ids+([gid] if gid is not None else []))
        contacts.append(dict(channel=p['channel'],contacted_metal_components=touched,passed=len(h)==1 and set(touched)==expected and len(touched)==2))
    checks=[('sixteen_pad_centers',len(pads)==16 and all(len(x)==1 for x in pads.values())),
        ('fourteen_independent_signal_nets',len({pads[p['pad_id']][0] for p in signals if len(pads[p['pad_id']])==1})==14),
        ('one_shared_GND_two_pads',len(grounds)==2 and gid is not None and all(pads[p['pad_id']]==[gid] for p in grounds)),
        ('fifteen_metal_nets',len(nets)==15),('all_PAD_A_and_B_GND',all(p['passed'] for p in connections)),
        ('each_heater_touches_two_correct_nets',heaters.size()==14 and all(p['passed'] for p in contacts))]
    return dict(metal_nets=len(nets),pad_components=pads,connections=connections,heater_contact_nets=contacts,
        checks=[dict(name=n,passed=bool(v)) for n,v in checks],passed=all(v for n,v in checks))
