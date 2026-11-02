"""Scientific plots from actual saved backannotation results."""
from pathlib import Path
import json,os
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
os.environ['MPLCONFIGDIR']=str(HERE/'work/.matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
def load(p):return json.loads(p.read_text(encoding='utf-8'))
r=load(HERE/'out/replay_results.json');paths=load(HERE/'out/paths.json');figdir=ROOT/'course/figures/m2_s7';figdir.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
names=list(r['cases']);labels=['Ideal\noriginal','Length\noriginal','Length\ncompensated','3 dB/cm\noriginal','3 dB/cm\ncompensated']
fig,axs=plt.subplots(1,2,figsize=(13,4.8),layout='constrained')
counts=[r['cases'][n]['passed'] for n in names]
bars=axs[0].bar(range(5),counts,color=['#64748b','#d97706','#087f8c','#d97706','#087f8c'])
axs[0].set(ylim=(0,90),ylabel='Passed / 80 core-plane cases',xticks=range(5),xticklabels=labels,title='Saved replay results; 3 dB/cm is illustrative')
for b,n in zip(bars,counts):axs[0].text(b.get_x()+b.get_width()/2,n+1,str(n),ha='center')
for n,label,color in zip(names[:3],['Ideal original','Length original','Length compensated'],['#64748b','#d97706','#087f8c']):
    axs[1].plot([row['signed_margin'] for row in r['cases'][n]['rows']],label=label,color=color,linewidth=1.25)
axs[1].axhline(0,color='#111827',linewidth=.8);axs[1].set(xlabel='Case index (5 gates × 16 patterns)',ylabel='Signed differential-power margin',title='Positive margin = correct decision');axs[1].legend(fontsize=9)
fig.savefig(figdir/'replay.svg');plt.close(fig)
s=r['sensitivity'];fig,axs=plt.subplots(1,2,figsize=(12,4.3),layout='constrained')
for key,label,col in [('original','Original M1 phases','#d97706'),('frozen_candidate','Frozen nominal candidate','#087f8c')]:
    axs[0].plot([x['neff_offset']*1000 for x in s],[x[key+'_passed'] for x in s],'o-',label=label,color=col)
    axs[1].plot([x['neff_offset']*1000 for x in s],[x[key+'_minimum_margin'] for x in s],'o-',label=label,color=col)
axs[0].set(xlabel='Uniform effective-index perturbation / 10⁻³',ylabel='Passed / 80',ylim=(0,85));axs[1].set(xlabel='Uniform effective-index perturbation / 10⁻³',ylabel='Minimum signed margin');axs[1].axhline(0,color='#111827',lw=.8);axs[0].legend(fontsize=9)
for ax in axs:ax.set_xticks([-1,-.5,0,.5,1])
fig.suptitle('Teaching sensitivity sweep; candidate is NOT retuned; not process bounds')
fig.savefig(figdir/'sensitivity.svg');plt.close(fig)
routes=sorted(paths['routes'],key=lambda x:x['component']);fig,ax=plt.subplots(figsize=(12,4.6),layout='constrained')
x=[p['component'] for p in routes];core=[p['core_length_um'] for p in routes]
ax.bar(x,core,label='Core centerline',color='#155bd0');ax.bar(x,[p['fan_length_um'] for p in routes],bottom=core,label='Fan centerline (outside replay plane)',color='#b7c9e2')
ax.set(xlabel='Actual GDS wire-component index (MMI bodies removed)',ylabel='Nominal polyline length / µm',title='68 source paths assigned to 33 GDS connections; EC taper response excluded');ax.legend(fontsize=9)
fig.savefig(figdir/'route_lengths.svg');plt.close(fig)
print('Three evidence plots exported')
