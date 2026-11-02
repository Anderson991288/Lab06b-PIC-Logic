from pathlib import Path
import sys,json,time
HERE=Path(__file__).resolve().parents[1];ROOT=HERE.parents[1];sys.path.insert(0,str(HERE))
from independent_geometry import read_material,measure_facing
r={}
for layer,w,s in [(3,.8,4),(39,2,80),(41,12,80)]:
    start=time.monotonic();mat,meta=read_material(ROOT/'work/m2_s6/out/after/b7_ec_pad.gds',layer);measured=measure_facing(mat,w,s);r[str(layer)]=dict(meta=meta,measured=measured,seconds=time.monotonic()-start);print(layer,r[str(layer)]['seconds'],{k:measured[k]['minimum'] for k in ['width','space']},flush=True)
(HERE/'out/probe.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
