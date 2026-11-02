from pathlib import Path
import pya,json,sys
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/virtuoso_reproduction/out'
stage=Path(json.loads((OUT/'clean_replay_stage.json').read_text())['windows'])
sys.path[:0]=[str(ROOT/'work/m2_s6'),str(ROOT/'work/m2_s5')]
from connectivity import analyze
from electrical_geometry import evaluate
def read(p):l=pya.Layout();l.read(str(p));return l
def reg(l,n):return pya.Region(l.top_cell().begin_shapes_rec(l.layer(n,0))).merged()
reference=read(OUT/'input/B7_source.gds');final=read(OUT/'exports_final/B7_crosscad_final.gds');rows=[]
for filename,base in [('source_200.gds',reference),('source_8191.gds',reference),('final.gds',final)]:
 l=read(stage/filename);rows.append(dict(file=filename,layers=[dict(layer=n,XOR_nm2=(reg(base,n)^reg(l,n)).area()) for n in [3,4,5,39,41,99,100]],cell_names_identical=sorted(c.name for c in base.each_cell())==sorted(c.name for c in l.each_cell())))
assert sum(x['XOR_nm2'] for x in rows[0]['layers'])==25744
assert all(x['XOR_nm2']==0 for row in rows[1:] for x in row['layers'])
info=json.loads((ROOT/'work/m2_s5/out/chip_info.json').read_text());spec=json.loads((ROOT/'pic_spec.json').read_text());core=json.loads((ROOT/'work/m2_s4/out/after/layout_info.json').read_text())
conn=analyze(read(stage/'final.gds'),info,spec,core,evaluate);assert conn['passed']
(stage/'geometry.json').write_text(json.dumps(dict(comparisons=rows,connectivity=conn),indent=2))
print('Clean replay geometry and final connectivity passed')
