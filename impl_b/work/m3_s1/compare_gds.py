"""Independent KLayout comparison, including text; reference is validation-only."""
import pya,json,hashlib
from pathlib import Path
def read(p):l=pya.Layout();l.read(str(p));return l
a=read(reference_gds);b=read(rebuilt_gds)
assert a.dbu==b.dbu and a.top_cell().name==b.top_cell().name
layers=sorted({(x.layer,x.datatype) for l in [a,b] for x in l.layer_infos()});result=[]
def region(l,layer,datatype):return pya.Region(l.top_cell().begin_shapes_rec(l.layer(layer,datatype))).merged()
def texts(l,layer,datatype):
    it=l.top_cell().begin_shapes_rec(l.layer(layer,datatype));rows=[]
    while not it.at_end():
        s=it.shape()
        if s.is_text():rows.append(str(s.text.transformed(it.trans())))
        it.next()
    return sorted(rows)
for layer,datatype in layers:
    xor=region(a,layer,datatype)^region(b,layer,datatype)
    result.append(dict(layer=layer,datatype=datatype,XOR_polygons=xor.size(),text_identical=texts(a,layer,datatype)==texts(b,layer,datatype),passed=xor.is_empty() and texts(a,layer,datatype)==texts(b,layer,datatype)))
record=dict(reference_sha256=hashlib.sha256(Path(reference_gds).read_bytes()).hexdigest(),rebuilt_sha256=hashlib.sha256(Path(rebuilt_gds).read_bytes()).hexdigest(),dbu_um=b.dbu,top_cell=b.top_cell().name,layers=result,passed=all(x['passed'] for x in result))
Path(output_json).write_text(json.dumps(record,indent=2),encoding='utf-8');print('All-layer GDS XOR / text:',record['passed'])
