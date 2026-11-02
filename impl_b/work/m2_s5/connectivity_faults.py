from pathlib import Path
import pya,json,copy,sys,hashlib
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE));from electrical_geometry import evaluate
OUT=HERE/'out';WORK=HERE/'work/controlled';WORK.mkdir(parents=True,exist_ok=True)
info=json.loads((OUT/'chip_info.json').read_text(encoding='utf-8'));layout=pya.Layout();layout.read(str(OUT/'b7_ec_pad.gds'));top=layout.top_cell();db=layout.dbu
def reg(l):return pya.Region(top.begin_shapes_rec(layout.layer(l,0))).merged()
def box(x0,y0,x1,y1):return pya.Box(*(round(v/db) for v in [x0,y0,x1,y1]))
base=reg(41);variants=[('signal_GND_short',base+pya.Region(box(166,-2,190,2))),('theta1_return_open',base-pya.Region(box(412.5,-21,424.5,-19)))]
results=[]
for name,metal in variants:
    fault=pya.Layout();fault.dbu=db;t=fault.create_cell('CONTROLLED_'+name)
    for layer in [3,4,5,39,41,99]:t.shapes(fault.layer(layer,0)).insert(metal if layer==41 else reg(layer))
    path=WORK/(name+'.gds');options=pya.SaveLayoutOptions();options.gds2_max_vertex_count=4000;fault.write(str(path),options)
    read=pya.Layout();read.read(str(path));rt=read.top_cell()
    result=evaluate(pya.Region(rt.begin_shapes_rec(read.layer(41,0))).merged(),pya.Region(rt.begin_shapes_rec(read.layer(39,0))).merged(),info,read.dbu)
    results.append(dict(name=name,type='actual_fault_GDS',detected=not result['passed'],metal_nets=result['metal_nets'],failed_checks=[r['name'] for r in result['checks'] if not r['passed']],gds_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
bad=copy.deepcopy(info);p=next(p for p in bad['pads'] if p.get('channel')=='theta1');p['signal_contact_um'],p['return_contact_um']=p['return_contact_um'],p['signal_contact_um']
result=evaluate(base,reg(39),bad,db)
results.append(dict(name='theta1_A_B_mapping_swapped',type='sidecar_fault_only',detected=not result['passed'],failed_checks=[r['name'] for r in result['checks'] if not r['passed']]))
(OUT/'connectivity_faults.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print('Connectivity negative controls:',[r['detected'] for r in results])
if not all(r['detected'] for r in results):raise RuntimeError('Connectivity fault was not detected')
