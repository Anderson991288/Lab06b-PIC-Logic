"""Run inside an installed KLayout process using packaged authored graph code."""
from pathlib import Path
import sys,json,pya
ROOT=Path(bundle_root);sys.path.insert(0,str(ROOT/'geometry'))
from connectivity import analyze
from electrical_geometry import evaluate
def load(p):return json.loads(p.read_text(encoding='utf-8'))
l=pya.Layout();l.read(str(ROOT/'layout/B7_final.gds'));r=analyze(l,load(ROOT/'data/chip_info.json'),load(ROOT/'data/pic_spec.json'),load(ROOT/'data/core_geometry.json'),evaluate)
Path(output_json).write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print('Portable geometric graph:',r['passed'])
if not r['passed']:raise RuntimeError('Packaged geometry graph mismatch')
