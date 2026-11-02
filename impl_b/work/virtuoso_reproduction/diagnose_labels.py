from pathlib import Path
import pya,json,math
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/virtuoso_reproduction/out'
l=pya.Layout();l.read(str(OUT/'input/B7_source.gds'));db=l.dbu;r=pya.Region(l.top_cell().begin_shapes_rec(l.layer(100,0))).merged();out={}
for angle in [45.,45.01,46.,90.]:
    pairs=r.space_check(249,False,pya.Region.Euclidian,angle);rows=[]
    for p in pairs.each():
        a=p.first.p2-p.first.p1;b=p.second.p2-p.second.p1;dot=a.x*b.x+a.y*b.y;cross=a.x*b.y-a.y*b.x;aa=math.degrees(math.atan2(abs(cross),abs(dot)))
        rows.append(dict(angle_deg=aa,edges=[[[e.p1.x*db,e.p1.y*db],[e.p2.x*db,e.p2.y*db]] for e in [p.first,p.second]]))
    out[str(angle)]=dict(markers=pairs.size(),edges=rows)
(OUT/'GDS100_angle_diagnosis.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('GDS100 by angle:',{k:v['markers'] for k,v in out.items()})
