from pathlib import Path
import os,json,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];FIG=ROOT/'course/figures/m3_s2';FIG.mkdir(parents=True,exist_ok=True)
os.environ['MPLCONFIGDIR']=str(HERE/'work/.matplotlib')
HANDLE=os.add_dll_directory(str(Path(sys.prefix)/'Library/bin')) if os.name=='nt' else None
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Patch
import numpy as np,shapely
from independent_geometry import read_material
r=json.loads((HERE/'out/crosscheck_results.json').read_text(encoding='utf-8'));rows=r['comparison'];cfg=r['config'];plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
fig,ax=plt.subplots(figsize=(12,4.6),layout='constrained');x=np.arange(6);ratios=[z['independent_um']/z['effective_limit_um'] for z in rows]
ax.bar(x-.16,ratios,width=.30,color='#155bd0',label='gdstk / Shapely')
mid=[(z['KLayout_lower_um']+z['KLayout_upper_um'])/2/z['effective_limit_um'] for z in rows];err=[(z['KLayout_upper_um']-z['KLayout_lower_um'])/2/z['effective_limit_um'] for z in rows]
ax.errorbar(x+.16,mid,yerr=err,fmt='o',capsize=5,color='#d97706',label='KLayout 1 nm bracket')
for k,z in enumerate(rows):ax.text(k-.16,ratios[k]+.12,f'{z["independent_um"]:.3f} um',ha='center',fontsize=9)
ax.axhline(1,color='#b91c1c',linestyle='--',label='Effective rule limit (nominal - 1 nm)')
ax.set(xticks=x,xticklabels=['Si width','Si space','HT width','HT space','Metal width','Metal space'],ylabel='Measured minimum / effective limit',ylim=(0,6.1),title='Six scoped measurements; independent coordinates vs native KLayout');ax.legend(fontsize=9,loc='upper left')
fig.savefig(FIG/'measurements.svg');plt.close(fig)
fig,axs=plt.subplots(3,2,figsize=(12,12),layout='constrained');mats={}
source=ROOT/'work/m2_s6/out/after/b7_ec_pad.gds'
for ax,z in zip(axs.flat,rows):
    layer=z['layer'];mat=mats.setdefault(layer,read_material(source,layer)[0]);w=z['witness'];a=np.array(w['point_A_um']);b=np.array(w['point_B_um']);d=z['independent_um'];margin=max(.65,d*.25)
    bounds=[float(min(a[0],b[0])-margin),float(min(a[1],b[1])-margin),float(max(a[0],b[0])+margin),float(max(a[1],b[1])+margin)]
    clip=shapely.clip_by_rect(mat,*bounds)
    for p in clip.geoms if hasattr(clip,'geoms') else [clip]:
        if p.geom_type!='Polygon':continue
        ax.add_patch(Patch(np.array(p.exterior.coords),facecolor='#b9d5ef',edgecolor='#155bd0',linewidth=.8))
        for hole in p.interiors:ax.add_patch(Patch(np.array(hole.coords),facecolor='white',edgecolor='#155bd0',linewidth=.8))
    ax.plot([a[0],b[0]],[a[1],b[1]],'o-',color='#b91c1c',lw=2,ms=4);ax.set(xlim=(bounds[0],bounds[2]),ylim=(bounds[1],bounds[3]),xlabel='x / um',ylabel='y / um',title=f'GDS {layer} {z["kind"]}: {d:.3f} um\n'+w['visibility'].replace('_',' '));ax.set_aspect('equal');ax.ticklabel_format(useOffset=False,style='plain')
fig.suptitle('Witnesses from independently read GDS boundaries; red segments are measured distances')
fig.savefig(FIG/'witnesses.svg');plt.close(fig);print('Independent measurement comparison and six coordinate witnesses exported')
