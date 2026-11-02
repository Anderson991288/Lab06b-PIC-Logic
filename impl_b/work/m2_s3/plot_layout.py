"""Annotated figures from the newly exported GDS polygons, not a mockup."""
from pathlib import Path
import os,sys,json
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
os.environ['MPLCONFIGDIR']=str(HERE/'work/matplotlib')
HANDLE=os.add_dll_directory(str(Path(sys.prefix)/'Library/bin')) if os.name=='nt' else None
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Patch
from matplotlib.collections import PatchCollection
plt.rcParams.update({'font.family':['Microsoft JhengHei','DejaVu Sans'],'axes.unicode_minus':False,'svg.fonttype':'path','font.size':11})
INFO=json.loads((HERE/'out/layout_info.json').read_text(encoding='utf-8'));OUT=ROOT/'course/figures/m2_s3';OUT.mkdir(parents=True,exist_ok=True)
POLYGONS=json.loads((HERE/'out/gds_readback_polygons.json').read_text(encoding='utf-8'))
def polygons(name):return [(p['layer'],np.asarray(p['points_um'])) for p in POLYGONS[name]]
colors={3:'#155bd0',39:'#df7c16',41:'#258350',99:'#8a648d'}
def base(ax,polys,bounds):
    for l in [3,39,41]:
        ax.add_collection(PatchCollection([Polygon(xy,closed=True) for layer,xy in polys if layer==l],facecolor=colors[l],edgecolor='none',alpha=.9))
    for layer,xy in polys:
        if layer==99:ax.add_patch(Polygon(xy,closed=True,fill=False,ec=colors[99],lw=1))
    ax.set(xlim=bounds[:2],ylim=bounds[2:],xlabel='x (µm)',ylabel='y (µm)');ax.set_aspect('equal');ax.grid(alpha=.12)
def save(fig,name):
    fig.tight_layout()
    for ext in ['png','svg']:fig.savefig(OUT/(name+'.'+ext),dpi=160,bbox_inches='tight',facecolor='white')
    plt.close(fig)
core=polygons('core');unit=polygons('unit')
(HERE/'out/unit_polygons.json').write_text(json.dumps([dict(layer=l,points_um=xy.tolist()) for l,xy in unit if l in [3,39,41]],separators=(',',':')),encoding='utf-8')
L=INFO['column_length_um'];end=INFO['core_end_x_um'];pitch=INFO['unit']['pitch_um']
fig,ax=plt.subplots(figsize=(16,4.2));base(ax,core,(-110,INFO['core_frame_um'][2]+30,-180,90))
for p in INFO['placement']:
    x,y=p['origin_um'];ax.text(x+L/2,y-pitch/2,p['id'],ha='center',va='center',fontsize=11,bbox=dict(fc='white',ec='none',alpha=.85,pad=1.))
for n in range(4):
    ax.text(n*L+L/2,45,f'L{n}',ha='center',fontsize=13,color='#155bd0')
    if n:ax.axvline(n*L,color='#98abc5',ls=':',lw=.9)
for p in INFO['ports']:
    x,y=p['position_um'];ax.plot(x,y,'o',ms=3,color='#17263b')
    ax.text(x+(-10 if p['direction']=='in' else 10),y+3,p['id'],ha='right' if p['direction']=='in' else 'left',fontsize=9)
for p in INFO['paths']:
    if p['kind']=='bypass':
        x,y=p['points_um'][0];ax.text(x+L/2,y-6,'bypass',ha='center',color='#526379',fontsize=8)
ax.set_title('新匯出 B7 core GDS：四欄七顆 MZI／6 段直通／10 個 core 光學埠',fontsize=15)
fig.legend([Patch(color=colors[k]) for k in [3,39,41,99]],['GDS 3：Si 光路','GDS 39：局部 heater','GDS 41：局部接觸落墊','GDS 99：設計區框（非 die／facet）'],loc='lower center',ncol=4,bbox_to_anchor=(.5,-.01),fontsize=10)
save(fig,'b7_core')
fig,ax=plt.subplots(figsize=(15,4.8));base(ax,unit,(-15,L+15,-50,35))
for c in INFO['unit']['controls']:
    x,y=c['center_um'];ax.annotate(c['parameter']+'：上臂 100 µm heater',xy=(x,y),xytext=(x,23),ha='center',arrowprops=dict(arrowstyle='->',color='#df7c16'),fontsize=11)
for k,(x,y) in enumerate(INFO['unit']['mmi_positions_um'],1):ax.text(x+20,-17,f'MMI{k}',ha='center',fontsize=11,bbox=dict(fc='white',ec='none',alpha=.8))
for name,x,y in [('in0',0,0),('in1',0,-pitch),('out0',L,0),('out1',L,-pitch)]:ax.text(x,y-8,name,ha='center',fontsize=10)
ax.set_title('實際 MZI GDS：φ 在 MMI1 之前，θ 在兩顆 MMI 之間；上下臂幾何平衡',fontsize=14)
save(fig,'mzi_core')
mx,my=INFO['unit']['mmi_positions_um'][0]
fig,axes=plt.subplots(1,2,figsize=(14,5),gridspec_kw={'width_ratios':[1.2,1]})
base(axes[0],unit,(mx-25,mx+68,my-8,my+8));axes[0].set_title('第一顆 PDK MMI：實際幾何與查得的埠')
for name,(px,py) in INFO['unit']['mmi_ports'].items():
    x,y=mx+px,my+py;axes[0].plot(x,y,'o',ms=3,c='#17263b')
    axes[0].annotate(name,xy=(x,y),xytext=(x,y+(4 if py>0 else -4)),ha='center',arrowprops=dict(arrowstyle='->',lw=.8),fontsize=10)
base(axes[1],unit,(4,119,-9,15));axes[1].set_title('φ 的 HT 與局部金屬落墊：尚無外部 PAD')
axes[1].annotate('A 接觸',xy=(5.5,0),xytext=(23,10),ha='center',arrowprops=dict(arrowstyle='->'),fontsize=10)
axes[1].annotate('B 接觸',xy=(116.5,0),xytext=(95,10),ha='center',arrowprops=dict(arrowstyle='->'),fontsize=10)
save(fig,'mmi_contacts')
print('GDS figures generated from b7_core.gds and mzi_core.gds')
