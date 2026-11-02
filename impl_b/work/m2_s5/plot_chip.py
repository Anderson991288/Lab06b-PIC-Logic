from pathlib import Path
import os,sys,json
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
os.environ['MPLCONFIGDIR']=str(HERE/'work/matplotlib')
HANDLE=os.add_dll_directory(str(Path(sys.prefix)/'Library/bin')) if os.name=='nt' else None
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Patch
from matplotlib.collections import PatchCollection
plt.rcParams.update({'font.family':['Microsoft JhengHei','DejaVu Sans'],'axes.unicode_minus':False,'svg.fonttype':'path','font.size':10})
I=json.loads((HERE/'out/chip_info.json').read_text(encoding='utf-8'));P=json.loads((HERE/'out/chip_polygons.json').read_text(encoding='utf-8'))
FIG=ROOT/'course/figures/m2_s5';FIG.mkdir(parents=True,exist_ok=True)
colors={3:'#155bd0',4:'#e9ce78',5:'#993c9c',39:'#df7c16',41:'#258350'}
def draw(ax,layers):
    for l in layers:
        ax.add_collection(PatchCollection([Polygon(p['points_um'],closed=True) for p in P if p['layer']==l],facecolor=colors[l],edgecolor='none',alpha=.9))
def save(fig,name):
    fig.tight_layout()
    for ext in ['svg','png']:fig.savefig(FIG/(name+'.'+ext),dpi=160,bbox_inches='tight',facecolor='white')
    plt.close(fig)
west,bottom,east,top=I['chip_bounds_um']
fig,ax=plt.subplots(figsize=(16,7.5));draw(ax,[4,5,3,39,41])
ax.add_patch(Polygon([(west,bottom),(east,bottom),(east,top),(west,top)],fill=False,edgecolor='#8a648d',lw=1))
for p in I['pads']:
    x,y=p['center_um'];offset=110 if p['net']=='GND' else 65 if y>0 else -65
    ax.text(x,y+offset,p['pad_id']+'\n'+p['net'],ha='center',va='bottom' if y>0 else 'top',fontsize=7.5)
for p in I['optical_io']:
    x,y=p['facet_um'];label=p['core_port']+(' / '+['x1','x2','x3','x4','R'][p['mode']] if p['direction']=='in' else ' / '+('PD+' if p['mode']==1 else 'PD−' if p['mode']==3 else 'LOAD'))
    ax.text(x+(-20 if p['direction']=='in' else 20),y,label,ha='right' if p['direction']=='in' else 'left',va='center',fontsize=9)
ax.set(xlim=(west-160,east+180),ylim=(bottom-70,top+90),xlabel='x (µm)',ylabel='y (µm)',title='M2 S5：10 個參考 EC／14 個訊號 PAD／2 個 GND PAD；保留 S4 core 幾何')
ax.set_aspect('equal');ax.grid(alpha=.12)
save(fig,'chip_annotated')
fig,ax=plt.subplots(figsize=(14,4));draw(ax,[3,39,41])
bus=I['ground_bus'];ax.plot([p[0] for p in bus],[p[1] for p in bus],color='#9c2d7c',lw=1.2,ls='--',label='共地中心線（實際金屬已畫出）')
for k,y in enumerate(I['ground_column_y']):ax.text(k*505+300,y-16,f'L{k}: GND y={y:g}',ha='center',fontsize=10,bbox=dict(fc='white',ec='none',alpha=.85,pad=1))
ax.set(xlim=(-60,2050),ylim=(-132,32),xlabel='x (µm)',ylabel='y (µm)',title='按欄轉折的共地：保留 30 µm 軌距，與 14 個獨立訊號網分開')
ax.set_aspect('equal');ax.grid(alpha=.12);ax.legend(loc='upper right',fontsize=9)
save(fig,'ground_routing')
fig,ax=plt.subplots(figsize=(14,3.8))
draw(ax,[5,3])
for p in P:
    if p['layer']==4:ax.add_patch(Polygon(p['points_um'],closed=True,fill=False,ec=colors[4],ls='--',lw=1))
y=I['optical_io'][0]['facet_um'][1]
ax.set(xlim=(west-5,west+270),ylim=(y-1.6,y+1.6),xlabel='x (µm)',ylabel='y (µm，視覺放大)',title='參考 EC 俯視 mask 幾何：SLAB（紫）→ strip（藍）；不是已驗證的耦合場')
ax.text(west+15,y+.7,'tip 0.25 µm',fontsize=10);ax.text(west+150,y+.7,'SLAB taper',fontsize=10);ax.text(west+235,y-.8,'strip 0.45 µm',fontsize=10,ha='center')
ax.grid(alpha=.12)
save(fig,'EC_geometry')
(FIG/'drive_return.svg').write_text('''<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="340" viewBox="0 0 1100 340" role="img" aria-labelledby="t d"><title id="t">PAD 到 heater A 與 B 回地的路徑</title><desc id="d">DRV00 經 PAD_DRV00 到 H_M1_theta.A，電流穿過 heater 到 B，再經分欄共地線到兩個共地 PAD 及外部驅動器回流。相位 rad 需要尚未完成的電壓校正。</desc><rect width="1100" height="340" rx="8" fill="#f4f7fc"/><g font-family="Microsoft JhengHei,Arial" text-anchor="middle" font-size="18" fill="#17263b"><rect x="20" y="55" width="170" height="90" rx="7" fill="#fff3d7" stroke="#b78019"/><text x="105" y="90">外部 DRV00</text><text x="105" y="123">偏壓尚待校正</text><rect x="245" y="55" width="200" height="90" rx="7" fill="white" stroke="#155bd0"/><text x="345" y="91">PAD_DRV00</text><text x="345" y="123">theta1，phase 是 rad</text><rect x="500" y="55" width="300" height="90" rx="7" fill="#fff3d7" stroke="#df7c16"/><text x="650" y="91">H_M1_theta：A → B</text><text x="650" y="123">HT 是電阻支路，非金屬短路</text><rect x="850" y="55" width="225" height="90" rx="7" fill="#e8f5ee" stroke="#258350"/><text x="962" y="90">分欄共地金屬</text><text x="962" y="123">單一 GND 網</text><text x="650" y="235">PAD_GND_W／PAD_GND_E → 外部 DRV_RETURN</text><text x="550" y="303">16 個實體 PAD = 14 個訊號＋2 個共地；GDS 41 有 15 個獨立金屬網。</text></g><g fill="none" stroke="#258350" stroke-width="4"><path d="M190 100H240 M445 100H495 M800 100H845 M962 145V190H105V145"/></g></svg>''',encoding='utf-8')
print('Annotated chip, EC and PAD/GND figures generated')
