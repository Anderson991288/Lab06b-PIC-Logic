"""Native reference measurements; original deck is run separately unchanged."""
from pathlib import Path
import json,hashlib,pya
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;OUT=HERE/'out'
cfg=json.loads((ROOT/'config/m3_crosscheck.json').read_text(encoding='utf-8'));cases=json.loads((OUT/'case_inventory.json').read_text(encoding='utf-8'));all_results=[]
for case in cases:
    l=pya.Layout();l.read(case['gds']);db=l.dbu;top=l.top_cell();layers=[]
    for c in cfg['layers']:
        r=pya.Region(top.begin_shapes_rec(l.layer(c['layer'],0))).merged();box=r.bbox();metrics={}
        def check(kind,d):return getattr(r,kind+'_check')(int(d),False,pya.Region.Euclidian,cfg['angle_limit_deg'])
        for kind in ['width','space']:
            nominal=c[kind+'_um'];effective=nominal+cfg['deck_feature_margin_um'];edges=check(kind,round(effective/db))
            data=dict(nominal_um=nominal,effective_limit_um=effective,violations=edges.size(),rule_passed=edges.is_empty())
            if case['id']=='accepted':
                low=0;high=round(c[kind+'_search_cap_um']/db)
                if check(kind,high).is_empty():raise ValueError('No minimum bracket found within configured cap')
                while high-low>1:
                    mid=(low+high)//2
                    if check(kind,mid).is_empty():low=mid
                    else:high=mid
                witnesses=list(check(kind,high).each())
                data.update(lower_bound_um=low*db,upper_bound_um=high*db,witness_edges_um=[[[[e.p1.x*db,e.p1.y*db],[e.p2.x*db,e.p2.y*db]] for e in [p.first,p.second]] for p in witnesses[:4]])
            metrics[kind]=data
        layers.append(dict(layer=c['layer'],area_um2=r.area()*db*db,bbox_um=[v*db for v in [box.left,box.bottom,box.right,box.top]],merged_components=r.size(),metrics=metrics))
    all_results.append(dict(id=case['id'],gds_sha256=hashlib.sha256(Path(case['gds']).read_bytes()).hexdigest(),engine='KLayout '+pya.Application.instance().version(),dbu_um=db,top_cell=top.name,layers=layers))
(OUT/'klayout_results.json').write_text(json.dumps(all_results,indent=2),encoding='utf-8');print('KLayout independently measured',len(all_results),'GDS cases')
