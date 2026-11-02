from pathlib import Path
import os,sys,json
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
os.environ['MPLCONFIGDIR']=str(HERE/'work/matplotlib')
HANDLE=os.add_dll_directory(str(Path(sys.prefix)/'Library/bin')) if os.name=='nt' else None
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Rectangle
from matplotlib.collections import PatchCollection
plt.rcParams.update({'font.family':['Microsoft JhengHei','DejaVu Sans'],'axes.unicode_minus':False,'svg.fonttype':'path','font.size':10})
P=json.loads((HERE/'out/label_polygons.json').read_text(encoding='utf-8'));R=json.loads((HERE/'out/verification_results.json').read_text(encoding='utf-8'))
FIG=ROOT/'course/figures/m2_s6';FIG.mkdir(parents=True,exist_ok=True)
fig,axes=plt.subplots(1,2,figsize=(14,5))
for ax,version in zip(axes,['before','after']):
    ax.add_collection(PatchCollection([Polygon(p['points_um'],closed=True) for p in P[version]],facecolor='#993c9c',edgecolor='none'))
    ax.set(xlim=(-63,-50),ylim=(-3,4),xlabel='x (µm)',ylabel='y (µm)',title='修改前：4 µm 埠標籤' if version=='before' else '修改後：5 µm 埠標籤')
    ax.set_aspect('equal');ax.grid(alpha=.15)
    if version=='before':
        b=R['before']['items'][0]['bbox_um'];ax.add_patch(Rectangle((b[0]-.08,b[1]-.08),b[2]-b[0]+.16,b[3]-b[1]+.16,fill=False,ec='#c93030',lw=1.5))
        ax.annotate('原始 pre-DRC 間距 marker',xy=((b[0]+b[2])/2,b[1]),xytext=(-57.5,-2.5),ha='center',arrowprops=dict(arrowstyle='->',color='#c93030'),fontsize=9)
fig.suptitle('相同座標尺度比較實際 GDS 100：只放大十個埠標籤，六個實體圖層不變',fontsize=14)
fig.tight_layout()
for ext in ['png','svg']:fig.savefig(FIG/('label_fix.'+ext),dpi=160,bbox_inches='tight',facecolor='white')
plt.close(fig)
fig,ax=plt.subplots(figsize=(12,4))
labels=[r['id'] for r in R['negative_controls']];values=[r['drc_records'] for r in R['negative_controls']]
bars=ax.bar(range(len(values)),values,color=['#155bd0' if r['target']=='drc' else '#df7c16' for r in R['negative_controls']]);ax.bar_label(bars,padding=3)
ax.set_xticks(range(len(values)),labels,rotation=20,ha='right');ax.set(ylabel='原始 pre-DRC marker 記錄數',title='八種真實 GDS 負例：DRC 為零仍可能有接線錯誤',ylim=(0,max(values)+max(2,max(values)*.15)))
ax.grid(axis='y',alpha=.15);fig.tight_layout()
for ext in ['png','svg']:fig.savefig(FIG/('controls.'+ext),dpi=160,bbox_inches='tight',facecolor='white')
plt.close(fig)
print('Label fix and negative-control plots generated')
