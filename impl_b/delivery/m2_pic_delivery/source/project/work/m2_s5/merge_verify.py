"""Merge exact accepted core and new interfaces, independently verify actual GDS."""
from pathlib import Path
import json,hashlib,pya,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from electrical_geometry import evaluate
OUT=Path(out_folder);info=json.loads((OUT/'chip_info.json').read_text(encoding='utf-8'))
src=pya.Layout();src.read(core_gds);ext=pya.Layout();ext.read(str(OUT/'chip_interfaces.gds'))
layout=pya.Layout();layout.dbu=src.dbu
core=layout.create_cell('LAB06B_B7_CORE');core.copy_tree(src.top_cell())
interfaces=layout.create_cell('LAB06B_CHIP_INTERFACES');interfaces.copy_tree(ext.top_cell())
chip=layout.create_cell('LAB06B_B7_EC_PAD_CHIP')
chip.insert(pya.CellInstArray(core.cell_index(),pya.Trans()));chip.insert(pya.CellInstArray(interfaces.cell_index(),pya.Trans()))
gds=OUT/'b7_ec_pad.gds';layout.write(str(gds))
actual=pya.Layout();actual.read(str(gds));top=actual.top_cell();db=actual.dbu
def reg(layer):return pya.Region(top.begin_shapes_rec(actual.layer(layer,0))).merged()
def box(x,y,d=.1):return pya.Box(round((x-d)/db),round((y-d)/db),round((x+d)/db),round((y+d)/db))
metal=reg(41);heaters=reg(39);electric=evaluate(metal,heaters,info,db)
pad_hits=electric['pad_components'];connections=electric['connections'];heater_nets=electric['heater_contact_nets']
core_actual=actual.cell('LAB06B_B7_CORE');same=[]
for layer in [3,39,41,99,100]:
    a=pya.Region(core_actual.begin_shapes_rec(actual.layer(layer,0)));b=pya.Region(src.top_cell().begin_shapes_rec(src.layer(layer,0)))
    same.append(dict(layer=layer,identical=(a^b).is_empty()))
optical=[];si=reg(3);slab=reg(5);material=si+slab
for p in info['optical_io']:
    facet=p['facet_um'];inside=[facet[0]+(.1 if p['direction']=='in' else -.1),facet[1]]
    probes=[('facet_SLAB',inside,slab),('EC_strip',p['strip_um'],si),('core_join',p['core_um'],si)]
    for tag,xy,r in probes:
        optical.append(dict(interface=p['interface_id'],probe=tag,passed=(pya.Region(box(*xy,d=.05))-r).is_empty()))
covered=[]
for route in info['optical_routes']:
    pts=route['points_um'];samples=pts[1:-1]+[[.5*(a[0]+b[0]),.5*(a[1]+b[1])] for a,b in zip(pts,pts[1:])]
    bad=sum(not (pya.Region(box(*xy,d=.001))-si).is_empty() for xy in samples)
    covered.append(dict(route=route['id'],samples=len(samples),uncovered=bad))
frame=reg(99);outside={str(l):(reg(l)-frame).size() for l in [3,4,5,39,41]}
rules=[]
for l,width,gap in [(3,.35,.2),(39,.6,10),(41,2,10)]:
    r=reg(l)
    rules.append(dict(layer=l,width_limit_um=width,width_warnings=r.width_check(round(width/db)).size(),space_limit_um=gap,space_warnings=r.space_check(round(gap/db)).size()))
checks=[('core_geometry_unchanged',all(p['identical'] for p in same)),*[(r['name'],r['passed']) for r in electric['checks']],
    ('thirty_optical_endpoint_probes',len(optical)==30 and all(p['passed'] for p in optical)),('fan_route_samples',all(p['uncovered']==0 for p in covered)),
    ('inside_chip_frame',not any(outside.values()))]
def polys(layer):return [dict(layer=layer,points_um=[[p.x*db,p.y*db] for p in poly.to_simple_polygon().each_point()]) for poly in reg(layer).each()]
(OUT/'chip_polygons.json').write_text(json.dumps([p for l in [3,4,5,39,41,99] for p in polys(l)],separators=(',',':')),encoding='utf-8')
result=dict(engine=pya.Application.instance().version(),gds_sha256=hashlib.sha256(gds.read_bytes()).hexdigest(),top_cell=top.name,
    core_layer_comparison=same,metal_nets=electric['metal_nets'],heater_regions=heaters.size(),pad_components=pad_hits,connections=connections,heater_contact_nets=heater_nets,
    optical_endpoint_probes=optical,fan_coverage=covered,outside=outside,scoped_rules=rules,checks=[dict(name=n,passed=bool(v)) for n,v in checks],
    passed=all(v for n,v in checks),scope='Actual GDS metal components, heater contacts and selected optical geometry; not full LVS, fabrication/EC qualification, optical mode continuity or calibrated response.')
(OUT/'chip_readback.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
view=pya.LayoutView();view.load_layout(str(gds),0);view.max_hier()
for key,value in [('background-color','#ffffff'),('grid-visible','false'),('text-visible','false'),('cell-box-visible','false')]:view.set_config(key,value)
colors={3:0x155bd0,4:0xe9ce78,5:0x993c9c,39:0xdf7c16,41:0x258350}
fig=Path(figure_folder);fig.mkdir(parents=True,exist_ok=True)
scenes={'chip':info['chip_bounds_um'],'ground':[-100,-140,1550,60],
    'EC':[info['chip_bounds_um'][0]-10,410,info['chip_bounds_um'][0]+280,470]}
for name,bounds in scenes.items():
    for lp in view.each_layer():
        lp.visible=lp.source_layer in colors;lp.fill_color=colors.get(lp.source_layer,0x888888);lp.frame_color=lp.fill_color;lp.dither_pattern=0
    view.zoom_box(pya.DBox(*bounds));view.save_image(str(fig/('native_'+name+'.png')),1800,850 if name=='chip' else 500)
view.save_layer_props(str(OUT/'chip_layers.lyp'))
print('Chip readback',result['passed'],'metal nets',electric['metal_nets'],'heater regions',heaters.size(),'rules',rules)
