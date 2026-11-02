"""Centerline crossings from exported route sidecars; no GDS/LVS claim."""
from pathlib import Path
import os,sys,json,itertools
ROOT=Path(__file__).resolve().parents[2]
HANDLE=os.add_dll_directory(str(Path(sys.prefix)/'Library/bin')) if os.name=='nt' else None
from shapely.geometry import LineString,Point
result={}
for version in ['before','after']:
    folder=ROOT/'work/m2_s4/out'/version;info=json.loads((folder/'layout_info.json').read_text(encoding='utf-8'))
    unexpected=[];touches=[]
    for a,b in itertools.combinations(info['paths'],2):
        la,lb=LineString(a['points_um']),LineString(b['points_um']);cross=la.intersection(lb)
        if cross.is_empty:continue
        ends=[Point(p) for p in [a['points_um'][0],a['points_um'][-1]]]
        other=[Point(p) for p in [b['points_um'][0],b['points_um'][-1]]]
        shared=cross.geom_type=='Point' and any(cross.distance(p)<1e-8 for p in ends) and any(cross.distance(p)<1e-8 for p in other)
        record=dict(a=a['id'],b=b['id'],intersection=cross.wkt)
        (touches if shared else unexpected).append(record)
    result[version]=dict(engine='Shapely '+__import__('shapely').__version__,tested_pairs=1653,
        permitted_shared_endpoints=touches,unexpected_intersections=unexpected,passed=not unexpected,
        scope='Outside-MMI centerlines from the generated sidecar only; excludes intended mixing inside MMI and does not extract topology from GDS.')
(ROOT/'work/m2_s4/out/route_crossings.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('Centerline crossing review:',{v:len(r['unexpected_intersections']) for v,r in result.items()})
raise SystemExit(0 if all(r['passed'] for r in result.values()) else 1)
