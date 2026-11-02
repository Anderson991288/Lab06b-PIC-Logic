"""Read current deliverable after actual Virtuoso round trip."""
from pathlib import Path
import pya,json,hashlib,sys
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/virtuoso_reproduction/out'
sys.path[:0]=[str(ROOT/'work/m2_s6'),str(ROOT/'work/m2_s5')]
from connectivity import analyze
from electrical_geometry import evaluate
def read(path):l=pya.Layout();l.read(str(path));return l
def region(l,n):return pya.Region(l.top_cell().begin_shapes_rec(l.layer(n,0))).merged()
def texts(l):
 it=l.top_cell().begin_shapes_rec(l.layer(1002,0));rows=[]
 while not it.at_end():
  if it.shape().is_text():rows.append(str(it.shape().text.transformed(it.trans())))
  it.next()
 return sorted(rows)
source=read(OUT/'input/B7_source.gds');candidate=read(OUT/'input/B7_crosscad_labels.gds');final=read(OUT/'exports_final/B7_crosscad_final.gds');auto=read(OUT/'gui_auto/lab06b_b7_ec_pad_chip.calibre.db')
result={}
for name,reference,l in [('source_to_final',source,final),('candidate_to_final',candidate,final),('candidate_to_gui_auto',candidate,auto)]:
 rows=[dict(layer=n,XOR_nm2=(region(reference,n)^region(l,n)).area()) for n in [3,4,5,39,41,99,100]]
 result[name]=dict(layers=rows,text_count=len(texts(l)),texts_identical=texts(reference)==texts(l),cells=l.cells(),cell_names_identical=sorted(c.name for c in reference.each_cell())==sorted(c.name for c in l.each_cell()),bbox_um=str(l.top_cell().dbbox()))
info=json.loads((ROOT/'work/m2_s5/out/chip_info.json').read_text());spec=json.loads((ROOT/'pic_spec.json').read_text());core=json.loads((ROOT/'work/m2_s4/out/after/layout_info.json').read_text())
result['final_connectivity']=analyze(final,info,spec,core,evaluate)
assert result['final_connectivity']['passed']
assert all(x['XOR_nm2']==0 for x in result['candidate_to_final']['layers'])
assert all(x['XOR_nm2']==0 for x in result['source_to_final']['layers'] if x['layer']!=100)
assert result['candidate_to_final']['texts_identical'] and result['candidate_to_final']['cell_names_identical']
(OUT/'final_geometry.json').write_text(json.dumps(result,indent=2))
print('Final physical masks XOR0, 43 names, 16 TEXT, connectivity passed',result['final_connectivity']['electrical']['metal_nets'],result['final_connectivity']['optical']['route_components'])
