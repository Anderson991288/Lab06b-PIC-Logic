from pathlib import Path
import pya,sys,json,hashlib
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(ROOT/'work/m2_s5')]
from connectivity import analyze
from electrical_geometry import evaluate
layout=pya.Layout();layout.read(str(gds_path))
info=json.loads((ROOT/'work/m2_s5/out/chip_info.json').read_text(encoding='utf-8'))
spec=json.loads((ROOT/'pic_spec.json').read_text(encoding='utf-8'))
core=json.loads((ROOT/'work/m2_s4/out/after/layout_info.json').read_text(encoding='utf-8'))
r=analyze(layout,info,spec,core,evaluate);r.update(gds_sha256=hashlib.sha256(Path(gds_path).read_bytes()).hexdigest(),engine=pya.Application.instance().version())
Path(result_path).write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print('Connectivity:',r['passed'],'electrical nets',r['electrical']['metal_nets'],'optical routes',r['optical']['route_components'],'missing pairs',r['optical']['missing_pairs'],'unexpected',r['optical']['unexpected_groups'])
