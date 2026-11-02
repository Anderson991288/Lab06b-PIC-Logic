"""Scoped KLayout geometry screening, route samples and native LayoutView images.

Invoked with -b -r by run_review.py; not the complete foundry deck or LVS.
"""
import pya,json,hashlib,math
from pathlib import Path
folder=Path(folder_path);info=json.loads((folder/'layout_info.json').read_text(encoding='utf-8'))
gds=folder/'b7_core.gds';lay=pya.Layout();lay.read(str(gds));top=lay.top_cell();db=lay.dbu
def reg(layer):return pya.Region(top.begin_shapes_rec(lay.layer(layer,0))).merged()
def box(x0,y0,x1,y1):return pya.Box(*(round(v/db) for v in [x0,y0,x1,y1]))
def scan(si,ht,metal):
    data=[]
    for layer,r,width,gap in [(3,si,.35,.2),(39,ht,.6,10),(41,metal,2.,10.)]:
        for kind,limit,edges in [('width',width,r.width_check(round(width/db))),('space',gap,r.space_check(round(gap/db)))]:
            data.append(dict(layer=layer,kind=kind,limit_um=limit,violations=edges.size(),
                boxes_um=[[round(v*db,6) for v in [e.bbox().left,e.bbox().bottom,e.bbox().right,e.bbox().top]] for e in list(edges.each())[:20]]))
    return data
def coverage(si):
    failed=[];total=0
    for path in info['paths']:
        pts=path['points_um']
        # Midpoints on every exported straight segment, plus all centerline vertices.
        samples=list(pts[1:-1])
        # External port faces are physical endpoints: probe just inside the route,
        # so the 2 nm box does not intentionally extend past the silicon endface.
        for end,neighbor in [(pts[0],pts[1]),(pts[-1],pts[-2])]:
            distance=math.dist(end,neighbor)
            samples.append([end[k]+.01*(neighbor[k]-end[k])/distance for k in [0,1]])
        samples+=[[.5*(a[0]+b[0]),.5*(a[1]+b[1])] for a,b in zip(pts,pts[1:])]
        for x,y in samples:
            total+=1
            if not (pya.Region(box(x-.001,y-.001,x+.001,y+.001))-si).is_empty():failed.append(dict(path=path['id'],point_um=[x,y]))
    return dict(samples=total,uncovered=len(failed),examples=failed[:20],scope='2 nm boxes at vertices and segment midpoints, not a continuous global topology extraction')
si,ht,metal=reg(3),reg(39),reg(41)
rules=scan(si,ht,metal);covered=coverage(si)
# Geometric separations between distinct local contacts/heaters, binary search to 1 nm.
def minimum_isolated_gap(r):
    low,high=0,100000
    if r.isolated_check(high).is_empty():return None
    while high-low>1:
        mid=(low+high)//2
        if r.isolated_check(mid).is_empty():low=mid
        else:high=mid
    return dict(lower_bound_um=low*db,upper_bound_um=high*db)
gaps=dict(HT=minimum_isolated_gap(ht),local_metal=minimum_isolated_gap(metal))
faults=[]
if str(make_faults)=='1':
    bad=Path(fault_folder);bad.mkdir(parents=True,exist_ok=True)
    variants=[('narrow_Si',si+pya.Region(box(10,-145,30,-144.8)),metal,'layer3_width'),
              ('close_metal',si,metal+pya.Region(box(13,-6,24,6)),'layer41_space'),
              ('gapped_input',si-pya.Region(box(-31,-1,-29,1)),metal,'route_coverage')]
    for name,s,m,expected in variants:
        # Actual isolated fault GDS, outside the accepted deliverable directory.
        temp=pya.Layout();temp.dbu=db;t=temp.create_cell('CONTROLLED_'+name)
        for layer,r in [(3,s),(39,ht),(41,m),(99,reg(99))]:t.shapes(temp.layer(layer,0)).insert(r)
        dest=bad/(name+'.gds');options=pya.SaveLayoutOptions();options.gds2_max_vertex_count=4000
        temp.write(str(dest),options)
        reread=pya.Layout();reread.read(str(dest));rt=reread.top_cell()
        def rr(layer):return pya.Region(rt.begin_shapes_rec(reread.layer(layer,0))).merged()
        scans=scan(rr(3),rr(39),rr(41));cov=coverage(rr(3))
        caught=(cov['uncovered']>0) if expected=='route_coverage' else any(r['layer']==int(expected[5:expected.index('_')]) and r['kind']==expected.split('_')[1] and r['violations']>0 for r in scans)
        faults.append(dict(name=name,expected=expected,detected=bool(caught),rules=scans,route_coverage=cov,
            gds_sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))

images=[]
if str(render_images)=='1':
    fig=Path(image_folder);fig.mkdir(parents=True,exist_ok=True)
    view=pya.LayoutView();view.load_layout(str(gds),0);view.max_hier()
    for key,value in [('background-color','#ffffff'),('grid-visible','false'),('text-visible','false'),('cell-box-visible','false')]:view.set_config(key,value)
    colors={3:0x155bd0,39:0xdf7c16,41:0x258350}
    modes={'combined':[3,39,41],'optical':[3],'thermal':[39,41]}
    scenes={'overview':([-100,-170,2150,70],2000,330),'bend':([115,-23,153,5],1100,700),
            'mmi':([135,-24,237,-6],1500,400),'heater':([-2,-10,124,12],1500,400)}
    for scene,(bounds,w,h) in scenes.items():
        for mode,layers in modes.items():
            for lp in view.each_layer():
                lp.visible=lp.source_layer in layers;lp.fill_color=colors.get(lp.source_layer,0x888888)
                lp.frame_color=lp.fill_color;lp.dither_pattern=0
            view.zoom_box(pya.DBox(*bounds));filename=version_name+'_'+scene+'_'+mode+'.png'
            view.save_image(str(fig/filename),w,h)
            images.append(dict(version=version_name,scene=scene,mode=mode,layers=layers,requested_box_um=bounds,file=filename,width_px=w,height_px=h))
    # Default learner layer settings; frame and text hidden for optical inspection.
    for lp in view.each_layer():lp.visible=lp.source_layer in [3,39,41]
    view.save_layer_props(str(folder/'review_layers.lyp'))
result=dict(engine='KLayout '+pya.Application.instance().version(),gds_sha256=hashlib.sha256(gds.read_bytes()).hexdigest(),
    rules=rules,route_coverage=covered,isolated_gap_bounds=gaps,controlled_faults=faults,images=images,
    all_scoped_rules_passed=all(r['violations']==0 for r in rules),route_samples_covered=covered['uncovered']==0,
    scope='Si/HT/local-metal width and spacing screening, sampled route coverage and native LayoutView images; not the full foundry deck, LVS, optical loss or layout phase replay.')
(folder/'review_geometry.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(version_name,'scoped warnings',sum(r['violations'] for r in rules),'route samples uncovered',covered['uncovered'],'native images',len(images))
