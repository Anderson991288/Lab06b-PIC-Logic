"""Actual Virtuoso OA stream-out geometry and text comparison."""
from pathlib import Path
import pya,json,hashlib
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/virtuoso_reproduction/out'
def read(path):l=pya.Layout();l.read(str(path));return l
def region(l,n):return pya.Region(l.top_cell().begin_shapes_rec(l.layer(n,0))).merged()
def texts(l):
    it=l.top_cell().begin_shapes_rec(l.layer(1002,0));rows=[]
    while not it.at_end():
        if it.shape().is_text():rows.append(str(it.shape().text.transformed(it.trans())))
        it.next()
    return sorted(rows)
source=read(OUT/'input/B7_source.gds');results=[]
for limit in [200,8191]:
    path=OUT/f'exports/B7_max{limit}.gds';l=read(path);layers=[]
    for n in [3,4,5,39,41,99,100]:
        difference=region(source,n)^region(l,n);layers.append(dict(layer=n,XOR_nm2=difference.area(),XOR_polygons=difference.size()))
    results.append(dict(maxVertices=limit,gds_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),top=l.top_cell().name,cells=l.cells(),cell_names_identical=sorted(c.name for c in source.each_cell())==sorted(c.name for c in l.each_cell()),layers=layers,texts_identical=texts(source)==texts(l),text_count=len(texts(l))))
(OUT/'roundtrip_geometry.json').write_text(json.dumps(results,indent=2),encoding='utf-8');print('OA export comparison:',[(r['maxVertices'],sum(x['XOR_nm2'] for x in r['layers'])) for r in results])
