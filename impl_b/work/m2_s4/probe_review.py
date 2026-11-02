import pya,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/m2_s4/work'
path=ROOT/'work/m2_s3/out/b7_core.gds'
lay=pya.Layout();lay.read(str(path));top=lay.top_cell()
checks={}
for layer,width,gap in [(3,.35,.2),(39,.6,10),(41,2,10)]:
    region=pya.Region(top.begin_shapes_rec(lay.layer(layer,0))).merged()
    checks[str(layer)]=dict(width=region.width_check(round(width/lay.dbu)).size(),space=region.space_check(round(gap/lay.dbu)).size())
(OUT/'probe_checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
print(checks)
view=pya.LayoutView()
view.load_layout(str(path),0)
view.max_hier()
view.set_config('background-color','#ffffff');view.set_config('grid-visible','false');view.set_config('text-visible','false')
for layer in view.each_layer():
    layer.visible=layer.source_layer in [3,39,41]
    layer.fill_color={3:0x155bd0,39:0xdf7c16,41:0x258350,99:0x8a648d}.get(layer.source_layer,0x888888)
    layer.frame_color=layer.fill_color
    layer.dither_pattern=0
view.zoom_box(pya.DBox(115,-23,150,5))
view.save_image(str(OUT/'probe_klayout.png'),1200,700)
print('Saved KLayout image')
