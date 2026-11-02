import pya,json
from pathlib import Path
l=pya.Layout();l.read(r'C:/EDA_Codex/Lab06b/work/m2_s6/out/after/b7_ec_pad.gds');db=l.dbu
out={'doc':pya.Region.width_check.__doc__[:6500],'layers':{}}
for layer in [3,39,41]:
    r=pya.Region(l.top_cell().begin_shapes_rec(l.layer(layer,0))).merged()
    def first(kind,high):
        low=0
        def check(d):return getattr(r,kind+'_check')(d,False,pya.Region.Euclidian,45.0)
        while check(high).is_empty():high*=2
        while high-low>1:
            mid=(low+high)//2
            if check(mid).is_empty():low=mid
            else:high=mid
        pairs=list(check(high).each())
        return {'lower_um':low*db,'upper_um':high*db,'pairs':[[[[e.p1.x*db,e.p1.y*db],[e.p2.x*db,e.p2.y*db]] for e in [pair.first,pair.second]] for pair in pairs[:4]]}
    out['layers'][str(layer)]={'area':r.area()*db*db,'perimeter':r.perimeter()*db,'components':r.size(),'width':first('width',800 if layer==3 else 12000),'space':first('space',80000)}
Path(r'C:/EDA_Codex/Lab06b/work/m3_s2/out/probe_klayout.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
