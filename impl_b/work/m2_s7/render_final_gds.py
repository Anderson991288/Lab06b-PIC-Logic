"""Native KLayout render of the unchanged accepted S6 delivery GDS."""
from pathlib import Path
import pya,json
ROOT=Path(__file__).resolve().parents[2];FIG=ROOT/'course/figures/m2_s7';FIG.mkdir(parents=True,exist_ok=True)
index=json.loads((ROOT/'config/m2_current_chip.json').read_text(encoding='utf-8'));gds=next(ROOT/p for p in index['files'] if p.endswith('.gds'))
view=pya.LayoutView();view.load_layout(str(gds),0);view.max_hier()
for k,v in [('background-color','#ffffff'),('grid-visible','false'),('text-visible','false'),('cell-box-visible','false')]:view.set_config(k,v)
colors={3:0x155bd0,4:0x74a8d6,5:0xa7c9e2,39:0xd97706,41:0x75818b,100:0x993c9c}
for lp in view.each_layer():
    lp.visible=lp.source_layer in colors;lp.fill_color=colors.get(lp.source_layer,0x888888);lp.frame_color=lp.fill_color;lp.dither_pattern=0
view.zoom_fit();view.save_image(str(FIG/'final_chip.png'),1800,850)
view.save_layer_props(str(ROOT/'work/m2_s7/out/delivery_layers.lyp'))
print('Final S6 accepted chip rendered without frame layer 99')
