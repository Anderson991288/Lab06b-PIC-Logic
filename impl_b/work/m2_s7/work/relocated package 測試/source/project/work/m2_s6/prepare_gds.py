"""Only resize ten core port labels; preserve previous GDS and physical masks."""
import pya,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/m2_s6/out'
C=json.loads((ROOT/'config/m2_verification.json').read_text(encoding='utf-8'))
pointer=json.loads((OUT/'source_chip_index.json').read_text(encoding='utf-8'))
source=OUT/'before/b7_ec_pad.gds';layout=pya.Layout();layout.read(str(source));db=layout.dbu
core_info=json.loads((ROOT/'work/m2_s4/out/after/layout_info.json').read_text(encoding='utf-8'))
cell=layout.cell('LAB06B_B7_CORE');li=layout.layer(C['label_layer'],0);old=pya.Region(cell.shapes(li)).merged();remaining=old.dup();added=pya.Region();windows=pya.Region();changes=[]
scale=C['port_label_scale']
for p in core_info['ports']:
    x,y=p['position_um'];ax=x+(3 if p['direction']=='in' else -20);ay=y+3
    b=pya.Box(round((ax-20)/db),round((ay-8)/db),round((ax+20)/db),round((ay+8)/db));mask=pya.Region(b)
    selected=old.interacting(mask)
    if selected.is_empty() or not (selected-mask).is_empty():raise RuntimeError('Port label selection failed '+p['id'])
    transform=pya.ICplxTrans(scale,0,False,round((1-scale)*ax/db),round((1-scale)*ay/db))
    resized=selected.transformed(transform);remaining-=selected;added+=resized;windows+=mask
    changes.append(dict(port=p['id'],anchor_um=[ax,ay],scale=scale,old_bbox_um=[v*db for v in [selected.bbox().left,selected.bbox().bottom,selected.bbox().right,selected.bbox().top]],new_bbox_um=[v*db for v in [resized.bbox().left,resized.bbox().bottom,resized.bbox().right,resized.bbox().top]]))
cell.shapes(li).clear();cell.shapes(li).insert(remaining+added)
target=OUT/'after/b7_ec_pad.gds';layout.write(str(target))
reread=pya.Layout();reread.read(str(target));before=pya.Layout();before.read(str(source))
def region(lay,layer):return pya.Region(lay.top_cell().begin_shapes_rec(lay.layer(layer,0))).merged()
comparisons=[dict(layer=l,identical=(region(before,l)^region(reread,l)).is_empty()) for l in C['physical_layers_to_preserve']]
outside=(region(before,100)^region(reread,100))-windows
print('Mask comparison',comparisons,'outside label windows',outside.size())
assert all(p['identical'] for p in comparisons) and outside.is_empty()
result=dict(change='Ten port labels scaled 1.25 about their original anchors, 4 to 5 um; no rule relaxation',ports=changes,
    physical_mask_comparison=comparisons,only_port_label_windows_changed=outside.is_empty(),
    before_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),after_sha256=hashlib.sha256(target.read_bytes()).hexdigest())
(OUT/'label_patch.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('Label-only correction:',len(changes),'physical masks unchanged:',all(p['identical'] for p in comparisons))
