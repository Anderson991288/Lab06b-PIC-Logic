from pathlib import Path
import os,sys,json
ROOT=Path(__file__).resolve().parents[2]
os.environ['MPLCONFIGDIR']=str(ROOT/'work/m2_s2/work/matplotlib')
HANDLE=os.add_dll_directory(str(Path(sys.prefix)/'Library/bin')) if os.name=='nt' else None
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
D=json.loads((ROOT/'work/m2_s2/out/comparison.json').read_text(encoding='utf-8'))
fig,axes=plt.subplots(2,1,figsize=(12,6.8),sharex=True,gridspec_kw={'height_ratios':[2,1]},constrained_layout=True)
for n,(g,rows) in enumerate(D.items()):
    x=np.arange(16)+n*16
    axes[0].plot(x,[(2*r['expected']-1)*r['ideal_delta'] for r in rows],'o',mfc='none',color='#155bd0',ms=6,label='M1 ideal' if n==0 else None)
    axes[0].plot(x,[r['signed_margin'] for r in rows],'x',color='#ca6410',ms=5,label='PDK / Caphe' if n==0 else None)
    axes[1].plot(x,[r['delta_error'] for r in rows],'.-',lw=.8,color='#155bd0')
    for ax in axes:ax.axvline(n*16-.5,color='#bfc9d8',lw=.8);ax.grid(axis='y',alpha=.2)
    axes[0].text(n*16+7.5,1.01,g,ha='center',transform=axes[0].get_xaxis_transform())
axes[0].axhline(1e-10,color='#b83737',ls='--',lw=1,label='Acceptance epsilon = 1e-10')
axes[0].set_ylabel('Signed margin (normalized power)');axes[0].legend(loc='upper left',ncol=3,fontsize=9)
axes[1].set_ylabel('Delta PDK - Delta ideal');axes[1].ticklabel_format(axis='y',style='sci',scilimits=(0,0))
axes[1].set_xlabel('Case index = 16 * gate index + input index (x1 is LSB)');axes[1].set_xlim(-1,80);axes[1].set_xticks(np.arange(0,80,4))
fig.suptitle('Fixed M1 phases: installed CORNERSTONE default MMI vs ideal B7',fontsize=14)
out=ROOT/'course/figures/m2_s2';out.mkdir(parents=True,exist_ok=True)
fig.savefig(out/'comparison.svg');fig.savefig(out/'comparison.png',dpi=150)
plt.close(fig)
