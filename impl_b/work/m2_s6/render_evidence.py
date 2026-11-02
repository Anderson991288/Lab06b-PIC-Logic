"""KLayout native label views and original GDS label polygons for the report."""
from pathlib import Path
import pya,json
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;FIG=ROOT/'course/figures/m2_s6';FIG.mkdir(parents=True,exist_ok=True)
records={}
for version in ['before','after']:
    path=HERE/'out'/version/'b7_ec_pad.gds';layout=pya.Layout();layout.read(str(path));top=layout.top_cell();db=layout.dbu
    labels=pya.Region(top.begin_shapes_rec(layout.layer(100,0))).merged()
    records[version]=[dict(points_um=[[p.x*db,p.y*db] for p in poly.to_simple_polygon().each_point()]) for poly in labels.each()]
    view=pya.LayoutView();view.load_layout(str(path),0);view.max_hier()
    for key,value in [('background-color','#ffffff'),('grid-visible','false'),('text-visible','false'),('cell-box-visible','false')]:view.set_config(key,value)
    for lp in view.each_layer():
        lp.visible=lp.source_layer in [3,100];lp.fill_color=0x993c9c if lp.source_layer==100 else 0x155bd0;lp.frame_color=lp.fill_color;lp.dither_pattern=0
    for name,bounds in [('in0',[-64,-3,-49,5]),('out0',[2050,-3,2071,5])]:
        view.zoom_box(pya.DBox(*bounds));view.save_image(str(FIG/(version+'_'+name+'.png')),1500,700)
    view.save_layer_props(str(HERE/'out'/version/'verification_layers.lyp'))
(HERE/'out/label_polygons.json').write_text(json.dumps(records,separators=(',',':')),encoding='utf-8')
print('Four native KLayout label views exported')
