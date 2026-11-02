"""Independent KLayout readback. Run by klayout_app -b -r, no IPKISS."""
import pya,json,hashlib
from pathlib import Path
gds=Path(input_gds);info=json.loads(Path(info_json).read_text(encoding='utf-8'))
layout=pya.Layout();layout.read(str(gds));top=layout.top_cell();db=layout.dbu
if top is None:raise RuntimeError('No unique top in '+str(gds)+'; cells='+str([cell.name for cell in layout.each_cell()]))
def region(layer):return pya.Region(top.begin_shapes_rec(layout.layer(layer,0))).merged()
si,ht,metal,frame=map(region,[3,39,41,99])
def box(x0,y0,x1,y1):return pya.Box(*(round(v/db) for v in [x0,y0,x1,y1]))
port_hits=[]
for p in info['ports']:
    x,y=p['position_um'];x+=.01 if p['direction']=='in' else -.01
    probe=box(x-.001,y-.1,x+.001,y+.1)
    port_hits.append(dict(port=p['id'],covered=(pya.Region(probe)-si).is_empty()))
joints=[]
for j in info['joints']:
    x,y=j['position_um'];probe=box(x-.01,y-.05,x+.01,y+.05)
    joints.append(dict(id=j['id'],covered=(pya.Region(probe)-si).is_empty()))
insts=list(top.each_inst());mzi_refs=[i for i in insts if layout.cell(i.cell_index).name=='LAB06B_MZI_CORE']
unit=layout.cell('LAB06B_MZI_CORE')
mmis=[i for i in unit.each_inst() if 'MMI' in layout.cell(i.cell_index).name.upper()]
placements=sorted([[round(i.trans.disp.x*db,3),round(i.trans.disp.y*db,3)] for i in mzi_refs])
expected=sorted([p['origin_um'] for p in info['placement']])
outside=sum((region(l)-frame).size() for l in [3,39,41,100])
preview_layout=pya.Layout();preview_layout.read(str(gds.with_name('mzi_core.gds')))
preview_top=preview_layout.top_cell()
preview_ok=preview_top is not None and preview_top.name=='LAB06B_MZI_PREVIEW'
if preview_ok:
    preview_ok=pya.Region(preview_top.begin_shapes_rec(preview_layout.layer(39,0))).merged().size()==2 and pya.Region(preview_top.begin_shapes_rec(preview_layout.layer(41,0))).merged().size()==4
checks=[('top_cell',top.name=='LAB06B_B7_CORE'),('one_nm_dbu',abs(db-.001)<1e-12),
    ('seven_actual_mzi_refs',len(mzi_refs)==7),('two_mmis_per_unit',len(mmis)==2),('mzi_placements_match',placements==expected),
    ('six_actual_bypasses',sum(layout.cell(i.cell_index).name.startswith('WG_BYP') for i in insts)==6),
    ('ten_actual_leads',sum(layout.cell(i.cell_index).name.startswith(('WG_in','WG_out')) for i in insts)==10),
    ('fourteen_heater_regions',ht.size()==14),('twentyeight_local_contacts',metal.size()==28),
    ('ten_port_covers',all(r['covered'] for r in port_hits)),('all_joint_corridors_covered',all(r['covered'] for r in joints)),
    ('inside_declared_frame',outside==0),('frame_matches_declaration',frame.bbox()==box(*info['core_frame_um'])),
    ('single_mzi_preview_geometry',preview_ok)]
result=dict(engine='KLayout independent GDS readback',version=pya.Application.instance().version(),gds=str(gds),
    gds_sha256=hashlib.sha256(gds.read_bytes()).hexdigest(),top_cell=top.name,dbu_um=db,cell_count=layout.cells(),
    actual_mzi_instances=len(mzi_refs),mmi_instances_per_mzi=len(mmis),actual_pdk_mmi_occurrences=len(mzi_refs)*len(mmis),
    actual_heater_regions=ht.size(),actual_local_metal_regions=metal.size(),silicon_connected_regions=si.size(),
    geometry_outside_frame=outside,ports=port_hits,joints=joints,checks=[dict(name=n,passed=bool(v)) for n,v in checks],
    passed=all(v for n,v in checks),scope='Counts, placements and local geometry coverage only; not LVS, foundry DRC, global optical topology extraction or phase replay.')
Path(output_json).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
def export_polygons(lay,cell):
    data=[]
    for layer in [3,39,41,99]:
        for polygon in pya.Region(cell.begin_shapes_rec(lay.layer(layer,0))).merged().each():
            # Bridge holes into a simple contour without filling optical loops.
            data.append(dict(layer=layer,points_um=[[p.x*lay.dbu,p.y*lay.dbu] for p in polygon.to_simple_polygon().each_point()]))
    return data
polygons=dict(engine='KLayout flattened regions from actual GDS; hole-preserving simple contours',
    core=export_polygons(layout,top),unit=export_polygons(preview_layout,preview_top))
Path(output_json).with_name(Path(output_json).stem+'_polygons.json').write_text(json.dumps(polygons,separators=(',',':')),encoding='utf-8')
print('GDS readback:',result['passed'],'joints',sum(j['covered'] for j in joints),'/',len(joints))
