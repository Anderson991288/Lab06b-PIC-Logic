from pathlib import Path
from datetime import datetime
import json,hashlib,shutil,os
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;OUT=HERE/'out';WSL='/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
current=load(ROOT/'config/m2_current_chip.json');assert current['accepted_at_step']=='M2 S6'
for p,h in current['files'].items():assert sha(ROOT/p)==h
source=next(ROOT/p for p in current['files'] if p.endswith('.gds'))
for folder in ['input','rules','cli_accepted','cli_negative','import','exports','screenshots']:(OUT/folder).mkdir(parents=True,exist_ok=True)
shutil.copy2(source,OUT/'input/B7_source.gds')
rules=ROOT/'reference/C01/outputs/virtuoso_drc/cornerstone_basic_draft.svrf';shutil.copy2(rules,OUT/'rules/cornerstone_basic_draft.svrf')
library='LAB06B_REPRO_20261031';oa=HERE/'work/oa'
(oa/'cds.lib').write_text('DEFINE '+library+' '+WSL+'/work/oa/'+library+'\n',encoding='utf-8',newline='\n')
for name,input_path,cell in [('accepted',WSL+'/out/input/B7_source.gds','LAB06B_B7_EC_PAD_CHIP'),('negative',WSL+'/out/input/negative_controls.gds','LAB06B_NEGATIVE_16')]:
    deck='\n'.join(['LAYOUT SYSTEM GDSII','LAYOUT PATH "'+input_path+'"','LAYOUT PRIMARY "'+cell+'"','DRC RESULTS DATABASE "'+WSL+'/out/cli_'+name+'/results.db" ASCII','DRC SUMMARY REPORT "'+WSL+'/out/cli_'+name+'/summary.txt"','INCLUDE "'+WSL+'/out/rules/cornerstone_basic_draft.svrf"',''])
    (OUT/'rules'/(name+'.svrf')).write_text(deck,encoding='utf-8',newline='\n')
os.add_dll_directory(str(Path(os.sys.prefix)/'Library/bin')) if os.name=='nt' else None
import gdstk
lib=gdstk.Library(unit=1e-6,precision=1e-9);top=lib.new_cell('LAB06B_NEGATIVE_16')
for k,(layer,width,gap) in enumerate([(60,.059,.059),(6,.199,.249),(3,.349,.199),(4,.199,.349),(5,.249,.249),(39,.599,9.999),(41,1.999,9.999),(100,.249,.249)]):
    x=k*100;w=max(.001,round(width/2,3));g=max(.001,round(gap/2,3))
    top.add(gdstk.rectangle((x,0),(x+10,w),layer=layer));top.add(gdstk.rectangle((x,100),(x+20,120),layer=layer));top.add(gdstk.rectangle((x+20+g,100),(x+40+g,120),layer=layer))
lib.write_gds(str(OUT/'input/negative_controls.gds'))
save(OUT/'input_manifest.json',dict(step='Virtuoso/Calibre current-design reproduction',library=library,top_cell='LAB06B_B7_EC_PAD_CHIP',source_gds=source.relative_to(ROOT).as_posix(),source_gds_sha256=sha(source),copied_gds_sha256=sha(OUT/'input/B7_source.gds'),draft_rule_source=rules.relative_to(ROOT).as_posix(),draft_rule_sha256=sha(rules),negative_gds_sha256=sha(OUT/'input/negative_controls.gds'),scope='New execution on current S6 GDS, imported into a new OA library; limited 16-rule local Calibre draft, unchanged original KLayout pre-DRC remains authoritative in its stated pre-signoff scope',D_writes=False))
print('Prepared current GDS and new 16-rule controls in C workspace')
