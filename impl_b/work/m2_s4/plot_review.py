"""Scientific before/after plots from independent KLayout polygon readback."""
from pathlib import Path
import os,sys,json
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
os.environ['MPLCONFIGDIR']=str(HERE/'work/matplotlib')
HANDLE=os.add_dll_directory(str(Path(sys.prefix)/'Library/bin')) if os.name=='nt' else None
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon
plt.rcParams.update({'font.family':['Microsoft JhengHei','DejaVu Sans'],'axes.unicode_minus':False,'svg.fonttype':'path','font.size':11})
OUT=ROOT/'course/figures/m2_s4';OUT.mkdir(parents=True,exist_ok=True)
D=json.loads((HERE/'out/review_results.json').read_text(encoding='utf-8'))
def load(v,name):return json.loads((HERE/'out'/v/name).read_text(encoding='utf-8'))
def save(fig,name):
    fig.tight_layout()
    for ext in ['svg','png']:fig.savefig(OUT/(name+'.'+ext),dpi=160,bbox_inches='tight',facecolor='white')
    plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(13,5))
for v,color in [('before','#155bd0'),('after','#df7c16')]:
    poly=load(v,'gds_readback_polygons.json')['unit'];info=load(v,'layout_info.json');ax=axes[0 if v=='before' else 1]
    for layer,c in [(3,'#155bd0'),(39,'#df7c16'),(41,'#258350')]:
        ax.add_collection(PatchCollection([Polygon(p['points_um'],closed=True) for p in poly if p['layer']==layer],facecolor=c,ec='none',alpha=.9))
    points=info['unit']['segments'][0]['points_um'];ax.plot(*np.array(points).T,ls='--',lw=.8,color='#6b304f',label='設計中心線')
    ax.set(xlim=(116,151),ylim=(-19,4),xlabel='x (µm)',ylabel='y (µm)',title=('修改前：20 µm' if v=='before' else '修改後：24 µm')+f"\n連續解析 Rmin = {info['unit']['continuous_s_bend_min_radius_um']:.6f} µm")
    ax.set_aspect('equal');ax.grid(alpha=.15)
    ax.axvline(122,color='#b5bdca',ls=':',lw=.8);ax.legend(loc='lower left',fontsize=9)
fig.suptitle('同尺度比較實際 Si 多邊形：延長 S 彎以增加曲率半徑裕量',fontsize=15)
save(fig,'bend_comparison')
fig,axes=plt.subplots(1,2,figsize=(12,4.5))
r=[D['versions'][v]['radius_um'] for v in ['before','after']]
bars=axes[0].bar(['修改前','修改後'],r,color=['#155bd0','#df7c16'],width=.55)
axes[0].bar_label(bars,fmt='%.3f',padding=4);axes[0].axhline(5,ls=':',color='#526379',label='既有規劃值 5 µm')
axes[0].axhline(D['course_radius_target_um'],ls='--',color='#9c2d7c',label='本課程額外目標 7.5 µm')
axes[0].set(ylabel='連續中心線解析最小曲率半徑 (µm)',ylim=(0,10));axes[0].legend(fontsize=9,loc='lower right')
spans=[D['versions'][v]['optical_span_um'][0] for v in ['before','after']]
bars=axes[1].bar(['修改前','修改後'],spans,color=['#155bd0','#df7c16'],width=.55);axes[1].bar_label(bars,fmt='%.0f',padding=4)
axes[1].set(ylabel='core 光學端點的水平跨度 (µm)',ylim=(0,2450));axes[1].text(.5,2350,'代價：水平跨度增加 64 µm',ha='center',fontsize=11)
fig.suptitle('幾何裕量與面積代價；未宣稱已驗證彎曲損耗或製程良率',fontsize=14)
save(fig,'margin_tradeoff')
print('Before/after review plots generated')
