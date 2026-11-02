"""Eight isolated real GDS controls; keep all device hierarchy for graph tests."""
from pathlib import Path
import pya,json,hashlib
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;WORK=HERE/'work/faults';WORK.mkdir(parents=True,exist_ok=True)
src=pya.Layout();src.read(str(HERE/'out/after/b7_ec_pad.gds'))
records=[]
variants=[('D1_Si_width','drc','GDS3< 350nm'),('D2_grid','drc','grid violations'),('D3_HT_gap','drc','GDS39<10micro'),('D4_PAD_width','drc','GDS41<2micro'),
    ('E1_signal_ground_short','electrical',None),('E2_return_open','electrical',None),('O1_lead_open','optical',None),('O2_optical_bridge','optical',None)]
for name,target,category in variants:
    lay=pya.Layout();lay.dbu=.0005 if name=='D2_grid' else src.dbu;t=lay.create_cell(src.top_cell().name);t.copy_tree(src.top_cell());db=lay.dbu
    def box(x0,y0,x1,y1):return pya.Box(*(round(v/db) for v in [x0,y0,x1,y1]))
    def add(layer,b):t.shapes(lay.layer(layer,0)).insert(b)
    if name=='D1_Si_width':add(3,box(-850,650,-830,650.2))
    elif name=='D2_grid':add(3,box(-850.0005,650.0005,-830.0005,650.4505))
    elif name=='D3_HT_gap':
        add(39,box(-850,650,-830,650.9));add(39,box(-850,656,-830,656.9))
    elif name=='D4_PAD_width':add(41,box(-850,650,-830,651))
    elif name=='E1_signal_ground_short':add(41,box(166,-2,190,2))
    elif name=='E2_return_open':
        c=lay.cell('LAB06B_CHIP_INTERFACES');li=lay.layer(41,0);old=pya.Region(c.shapes(li));cut=old-pya.Region(box(412.5,-39,424.5,-19))
        assert not (old^cut).is_empty();c.shapes(li).clear();c.shapes(li).insert(cut)
    elif name=='O1_lead_open':
        c=lay.cell('WG_in0');li=lay.layer(3,0);old=pya.Region(c.shapes(li))
        assert not old.is_empty() and (old^pya.Region(c.begin_shapes_rec(li))).is_empty(),'Unexpected WG leaf structure'
        cut=old-pya.Region(box(-31,-1,-29,1));assert not (old^cut).is_empty();c.shapes(li).clear();c.shapes(li).insert(cut)
    elif name=='O2_optical_bridge':add(3,box(-50.225,-30,-49.775,0))
    path=WORK/(name+'.gds');options=pya.SaveLayoutOptions();options.gds2_max_vertex_count=4000;lay.write(str(path),options)
    records.append(dict(id=name,target=target,expected_category_fragment=category,path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
(HERE/'out/fault_manifest.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
print('Generated',len(records),'isolated fault GDS files')
