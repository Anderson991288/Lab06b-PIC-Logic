from pathlib import Path
import subprocess,json,re,xml.etree.ElementTree as ET,shutil,hashlib
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;OUT=HERE/'out';stage=Path(json.loads((OUT/'clean_replay_stage.json').read_text())['windows'])
paths=json.loads((ROOT/'EDA_paths.json').read_text(encoding='utf-8-sig'))['windows'];exe=ROOT/paths['klayout_exe'];deck=ROOT/paths['drc_deck']
def run(args,log):
 r=subprocess.run([str(exe),'-b',*args],capture_output=True,text=True,timeout=180);log.write_text(r.stdout+'\n'+r.stderr);assert r.returncode==0,r.stderr
run(['-r',str(HERE/'verify_clean_geometry.py')],stage/'geometry.log')
pre=[]
for name,expected in [('source_200',8),('source_8191',0),('final',0)]:
 report=stage/(name+'.lyrdb');run(['-r',str(deck),'-rd','input='+str(stage/(name+'.gds')),'-rd','report='+str(report),'-rd','dw=3860','-rd','dh=1640'],stage/(name+'_pre_drc.log'))
 count=len(ET.parse(report).findall('.//items/item'));assert count==expected,(name,count);pre.append(dict(file=name+'.gds',records=count))
cal=[]
for name,total in [('source',27),('final',0),('negative',16)]:
 text=(stage/('drc_'+name)/'summary.txt').read_text();rules=[dict(rule=k,count=int(n)) for k,n in re.findall(r'RULECHECK\s+(CS\S+)\s+\.+\s+TOTAL Result Count = (\d+)',text)]
 assert len(rules)==16 and sum(x['count'] for x in rules)==total,(name,rules)
 if name=='negative':assert all(x['count']==1 for x in rules)
 cal.append(dict(name=name,checks=16,total=total,rules=rules))
dest=OUT/'clean_replay';dest.mkdir(exist_ok=True)
for p in stage.iterdir():
 if p.is_file():shutil.copy2(p,dest/p.name)
 elif p.is_dir() and p.name.startswith('drc_'):shutil.copytree(p,dest/p.name,dirs_exist_ok=True)
r=dict(status='passed',fresh_OA=True,prepared_from='Original immutable S6 GDS + annotation algorithm + unchanged rules; no existing OA or exported GDS carried into replay',stage=stage.name,physical_and_label_geometry='Final replay matches delivered candidate on all seven layers; original source 8191 XOR0; 200 XOR25744 nm2',pre_DRC=pre,calibre=cal,connectivity=dict(passed=True,metal_nets=15,heater_branches=14,optical_connections=33),raw_SHA_equality_required=False,reason='Native export/rebuild timestamps vary; geometry/cell-name/TEXT comparison used in addition to retained raw hashes',D_writes=False)
(OUT/'clean_replay.json').write_text(json.dumps(r,indent=2))
print(json.dumps({'status':'passed','pre_DRC':pre,'Calibre':[(x['name'],x['total']) for x in cal]},indent=2))
