"""Cross-CAD annotation revision only; no physical optical/electrical mask edit."""
from pathlib import Path
import json,hashlib,pya
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/virtuoso_reproduction/out';source=Path(globals().get('source_path',OUT/'input/B7_source.gds'))
l=pya.Layout();l.read(str(source));li=l.layer(100,0);db=l.dbu;changes=[]
for name,expected in [('LAB06B_MZI_CORE',2),('LAB06B_B7_CORE',17)]:
    cell=l.cell(name);original=pya.Region(cell.shapes(li)).merged();clusters=list(original.sized(3000).merged().each());assert len(clusters)==expected,(name,len(clusters))
    updated=pya.Region();covered=pya.Region()
    for k,cluster in enumerate(clusters):
        part=original.interacting(pya.Region(cluster));box=part.bbox();center=box.center();scale=1.3
        trans=pya.ICplxTrans(scale,0,False,round((1-scale)*center.x),round((1-scale)*center.y));enlarged=part.transformed(trans);updated+=enlarged;covered+=part
        changes.append(dict(cell=name,cluster=k,scale=scale,center_um=[center.x*db,center.y*db],bbox_before_um=[v*db for v in [box.left,box.bottom,box.right,box.top]],area_before_um2=part.area()*db*db,area_after_um2=enlarged.area()*db*db))
    assert (covered^original).is_empty();cell.shapes(li).clear();cell.shapes(li).insert(updated)
dest=Path(globals().get('dest_path',OUT/'input/B7_crosscad_labels.gds'));l.write(str(dest));b=pya.Layout();b.read(str(source));a=pya.Layout();a.read(str(dest))
def reg(x,layer):return pya.Region(x.top_cell().begin_shapes_rec(x.layer(layer,0))).merged()
comparison=[dict(layer=n,XOR_nm2=(reg(a,n)^reg(b,n)).area()) for n in [3,4,5,39,41,99]]
assert all(x['XOR_nm2']==0 for x in comparison)
def texts(x):
    it=x.top_cell().begin_shapes_rec(x.layer(1002,0));r=[]
    while not it.at_end():
        if it.shape().is_text():r.append(str(it.shape().text.transformed(it.trans())))
        it.next()
    return sorted(r)
assert texts(a)==texts(b) and len(texts(a))==16
r=dict(change='GDS100 annotation clusters scaled 1.3 about original centers; same 16-rule Calibre draft and original KLayout deck retained',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),candidate_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),changes=changes,physical_mask_XOR=comparison,texts1002_unchanged=True,text_count=16,labels100_XOR_nm2=(reg(a,100)^reg(b,100)).area(),source_adopted_chip_unchanged=True)
Path(globals().get('record_path',OUT/'label_revision.json')).write_text(json.dumps(r,indent=2),encoding='utf-8');print('Cross-CAD labels revised:',len(changes),'clusters; physical masks and 16 TEXT unchanged')
