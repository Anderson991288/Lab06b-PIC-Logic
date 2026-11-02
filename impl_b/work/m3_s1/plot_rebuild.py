"""Actual clean-build timings and a source/output/validation flow diagram."""
from pathlib import Path
import json,os,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];FIG=ROOT/'course/figures/m3_s1';FIG.mkdir(parents=True,exist_ok=True)
os.environ['MPLCONFIGDIR']=str(HERE/'work/.matplotlib')
HANDLE=os.add_dll_directory(str(Path(sys.prefix)/'Library/bin')) if os.name=='nt' else None
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
r=json.loads((HERE/'out/rebuild_results.json').read_text(encoding='utf-8'))
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
fig,ax=plt.subplots(figsize=(12,4.8),layout='constrained');labels=['Core + M1\nbundle','Core GDS\nreadback','EC / PAD /\nGND + merge','Pre-DRC /\nlabel fix / graph','68 paths /\n33 connections','400-case\nreplay + tests','Reference\nXOR + text']
for j,b in enumerate(r['builds']):
    values=[c['seconds'] for c in r['commands'] if c['build']==b['build']];bars=ax.bar([k+(j-.5)*.36 for k in range(7)],values,width=.34,label='Clean build '+b['build'],color=['#155bd0','#087f8c'][j])
    for bar,n in zip(bars,values):ax.text(bar.get_x()+bar.get_width()/2,n+.7,f'{n:.1f}',ha='center',va='bottom',fontsize=8)
ax.set(xticks=range(7),xticklabels=labels,ylabel='Measured wall time / seconds',title='Two fresh source trees; preinstalled licensed runtime; no old output seeded');ax.legend();ax.set_ylim(0,max(c['seconds'] for c in r['commands'])*1.22)
fig.savefig(FIG/'timings.svg');plt.close(fig)
boxes=[(20,30,185,'Author source + inputs','No GDS / sidecar / report'),(235,30,185,'Build core + interfaces','Installed PDK / IPKISS'),(450,30,185,'Fix labels + verify','Unchanged full pre-DRC'),(665,30,185,'Extract + replay','68 paths / 400 cases')]
svg=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 875 230" role="img" aria-label="Clean source build and validation-only reference"><defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6" fill="#64748b"/></marker></defs><rect width="875" height="230" fill="white"/>']
for x,y,w,a,b in boxes:
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="75" rx="8" fill="#edf4ff" stroke="#155bd0"/><text x="{x+w/2}" y="{y+29}" text-anchor="middle" font-family="Arial" font-size="14" fill="#12304d">{a}</text><text x="{x+w/2}" y="{y+52}" text-anchor="middle" font-family="Arial" font-size="11" fill="#475569">{b}</text>')
    if x<665:svg.append(f'<path d="M{x+w+2},67 H{x+w+26}" stroke="#64748b" stroke-width="2" marker-end="url(#arrow)"/>')
svg+=['<rect x="240" y="155" width="390" height="55" rx="8" fill="#fff7e8" stroke="#d97706"/><text x="435" y="179" text-anchor="middle" font-family="Arial" font-size="14">Accepted S6 / S7 reference: validation ONLY</text><text x="435" y="198" text-anchor="middle" font-family="Arial" font-size="11">Raw + timestamp-only SHA, all-layer XOR/text, CSV and numerical checks</text><path d="M750,106 V183 H632" fill="none" stroke="#64748b" stroke-width="2" marker-end="url(#arrow)"/></svg>']
(FIG/'pipeline.svg').write_text(''.join(svg),encoding='utf-8');print('M3 S1 pipeline and measured timing figures exported')
