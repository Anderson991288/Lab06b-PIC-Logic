"""Map bound centerline paths to actual GDS wire components; no optical PEX claim."""
from pathlib import Path
import pya,json,hashlib,math
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/m2_s7/out'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
current=load(ROOT/'config/m2_current_chip.json');assert current['accepted_at_step']=='M2 S6'
for p,h in current['files'].items():assert sha(ROOT/p)==h
gds=next(ROOT/p for p in current['files'] if p.endswith('.gds'));chip=load(next(ROOT/p for p in current['files'] if p.endswith('chip_info.json')))
core_index=load(ROOT/'config/m2_current_core.json')
for p,h in core_index['files'].items():assert sha(ROOT/p)==h
core_path=next(ROOT/p for p in core_index['files'] if p.endswith('layout_info.json'));core=load(core_path)
l=pya.Layout();l.read(str(gds));db=l.dbu;top=l.top_cell();unit=l.cell('LAB06B_MZI_CORE');core_cell=l.cell('LAB06B_B7_CORE')
def reg(layer):return pya.Region(top.begin_shapes_rec(l.layer(layer,0))).merged()
material=(reg(3)+reg(5)).merged();remove=pya.Region();terminals=[]
positions={tuple(round(v/db) for v in p['origin_um']):p['id'] for p in core['placement']}
mpos={tuple(round(v/db) for v in p):'MMI'+str(k+1) for k,p in enumerate(core['unit']['mmi_positions_um'])}
for mz in core_cell.each_inst():
    if l.cell(mz.cell_index).name!='LAB06B_MZI_CORE':continue
    name=positions[(mz.trans.disp.x,mz.trans.disp.y)]
    for inst in unit.each_inst():
        cell=l.cell(inst.cell_index)
        if 'MMI' not in cell.name.upper():continue
        local=mpos[(inst.trans.disp.x,inst.trans.disp.y)];trans=mz.trans*inst.trans
        remove+=pya.Region(cell.begin_shapes_rec(l.layer(3,0))).transformed(trans)
        for port,(x,y) in core['unit']['mmi_ports'].items():
            x+=-.01 if port.startswith('in') else .01
            terminals.append((name+':'+local+':'+port,trans*pya.Point(round(x/db),round(y/db))))
for p in chip['optical_io']:
    x,y=p['facet_um'];x+=.1 if p['direction']=='in' else -.1
    terminals.append((p['EC_id']+':facet',pya.Point(round(x/db),round(y/db))))
components=list((material-remove).merged().each());groups={k:[] for k in range(len(components))}
for name,point in terminals:
    ids=[k for k,poly in enumerate(components) if poly.inside(point)];assert len(ids)==1,(name,ids);groups[ids[0]].append(name)
raw=[dict(p,source_class='core') for p in core['paths']]+[dict(p,kind='fan',source_class='fan') for p in chip['optical_routes']]
paths=[]
for p in raw:
    pts=p['points_um'];length=sum(math.dist(a,b) for a,b in zip(pts,pts[1:]));assert abs(length-p['length_um'])<1e-8
    travel=length/2;mid=None
    for a,b in zip(pts,pts[1:]):
        segment=math.dist(a,b)
        if travel<=segment and segment>0:mid=[a[k]+(b[k]-a[k])*travel/segment for k in [0,1]];break
        travel-=segment
    assert mid is not None
    ids=[k for k,poly in enumerate(components) if poly.inside(pya.Point(*(round(v/db) for v in mid)))];assert len(ids)==1,(p['id'],ids)
    row={key:p[key] for key in ['id','kind','length_um','source_class']}
    row.update(gds_route_component=ids[0],midpoint_um=mid)
    for key in ['instance','stage','arm','layer','mode','direction']:
        if key in p:row[key]=p[key]
    paths.append(row)
routes=[]
for k,terms in groups.items():
    assigned=[p for p in paths if p['gds_route_component']==k];assert len(terms)==2 and assigned
    routes.append(dict(component=k,terminals=sorted(terms),path_ids=[p['id'] for p in assigned],
        centerline_length_um=sum(p['length_um'] for p in assigned),core_length_um=sum(p['length_um'] for p in assigned if p['source_class']=='core'),
        fan_length_um=sum(p['length_um'] for p in assigned if p['source_class']=='fan'),EC_response_unknown=any(t.endswith(':facet') for t in terms)))
expected=load(ROOT/'work/m2_s6/out/after/connectivity.json')['optical']['expected_pairs']
assert sorted(r['terminals'] for r in routes)==sorted(expected) and len(paths)==68 and len(routes)==33
result=dict(schema='lab06b.paths.v1',gds_sha256=sha(gds),core_geometry_sha256=sha(core_path),paths=paths,routes=routes,
    counts=dict(core_paths=58,fan_paths=10,all_paths=68,gds_route_components=33,MMI_occurrences=14,EC_unknown_routes=10),
    provenance='Centerline polyline lengths from immutable S4/S5 source data, recomputed and assigned to actual S6 GDS components. No MMI body length or EC taper optical length added.',
    optical_PEX_or_calibrated_lengths=False)
(OUT/'paths.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('Mapped',len(paths),'centerline paths to',len(routes),'actual GDS connections')
