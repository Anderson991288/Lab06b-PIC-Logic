"""Original full pre-DRC deck + geometric optical/electrical graph checks."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,hashlib,shutil,subprocess,xml.etree.ElementTree as ET,re,csv
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;OUT=HERE/'out'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
C=load(ROOT/'config/m2_verification.json');paths=load(ROOT/'EDA_paths.json');exe=Path(paths['windows']['klayout_exe']);exe=exe if exe.is_absolute() else ROOT/exe
deck=ROOT/C['deck'];assert sha(deck)==C['deck_sha256']
source_pointer=OUT/'source_chip_index.json'
if source_pointer.is_file():current=load(source_pointer)
else:current=load(ROOT/C['source_chip_index']);assert current['accepted_at_step']=='M2 S5';save(source_pointer,current)
for rel,d in current['files'].items():assert sha(ROOT/rel)==d,rel
source=next(ROOT/p for p in current['files'] if p.endswith('.gds'));shutil.copy2(source,OUT/'before/b7_ec_pad.gds')
info=load(ROOT/'work/m2_s5/out/chip_info.json');width,height=info['chip_size_um']
def execute(script,args,log):
    cmd=[str(exe),'-b','-r',str(script)]
    for k,v in args.items():cmd+=['-rd',str(k)+'='+str(v)]
    r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
    log.parent.mkdir(parents=True,exist_ok=True);log.write_text(r.stdout+'\n'+r.stderr,encoding='utf-8')
    if r.returncode:raise RuntimeError(script.name+': '+r.stderr[-1600:])
    return r.stdout.strip()
def drc(gds,folder):
    folder.mkdir(parents=True,exist_ok=True);report=folder/'pre_drc.lyrdb'
    execute(deck,dict(input=gds,report=report,dw=width,dh=height),folder/'pre_drc.log')
    tree=ET.parse(report);categories=[c.findtext('name') for c in tree.findall('.//categories/category')];items=[]
    for number,item in enumerate(tree.findall('.//items/item'),1):
        values=[v.text for v in item.findall('values/value')];coords=[(float(x),float(y)) for s in values for x,y in re.findall(r'(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)',s or '')]
        items.append(dict(id=number,category=(item.findtext('category') or '').strip("'"),cell=item.findtext('cell'),multiplicity=int(item.findtext('multiplicity') or 1),values=values,
            bbox_um=[min(x for x,y in coords),min(y for x,y in coords),max(x for x,y in coords),max(y for x,y in coords)] if coords else None))
    counts={cat:sum(r['category']==cat for r in items) for cat in categories}
    result=dict(gds_sha256=sha(gds),deck_sha256=sha(deck),report=str(report.relative_to(ROOT)),categories=categories,category_count=len(categories),items=items,counts=counts,
        total_records=len(items),total_occurrences=sum(r['multiplicity'] for r in items),declared_size_um=[width,height],
        deck_rules_changed=False,foundry_full_signoff=False,scope='All categories of installed CORNERSTONE v3.1 pre-DRC; original deck explicitly excludes foundry full DRC signoff.')
    save(folder/'drc_result.json',result);return result
before=drc(OUT/'before/b7_ec_pad.gds',OUT/'before')
print('Before: pre-DRC',before['total_records'],'records',flush=True)
print(execute(HERE/'prepare_gds.py',{},OUT/'label_patch.log'),flush=True)
after=drc(OUT/'after/b7_ec_pad.gds',OUT/'after');print('After: pre-DRC',after['total_records'],'records',flush=True)
for version in ['before','after']:
    folder=OUT/version
    print(execute(HERE/'check_connectivity.py',dict(gds_path=folder/'b7_ec_pad.gds',result_path=folder/'connectivity.json'),folder/'connectivity.log'),flush=True)
save(OUT/'verification_build.json',dict(timestamp=datetime.now(timezone(timedelta(hours=8))).isoformat(),root=str(ROOT),before=before,after=after,
    source_chip_index=current,source_hashes={p:sha(ROOT/p) for p in ['config/m2_verification.json','work/m2_s6/run_verification.py','work/m2_s6/prepare_gds.py','work/m2_s6/connectivity.py','work/m2_s6/check_connectivity.py',C['deck']]}))
