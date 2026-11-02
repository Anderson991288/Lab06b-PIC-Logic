from pathlib import Path
import json,hashlib,subprocess,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;OUT=HERE/'out'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
tools=load(ROOT/'EDA_paths.json')['windows'];exe=ROOT/tools['klayout_exe'];deck=ROOT/tools['drc_deck'];sha=hashlib.sha256(deck.read_bytes()).hexdigest();assert sha==load(ROOT/'config/m2_verification.json')['deck_sha256'];results=[]
for name,relative in [('oa_200','exports/B7_max200.gds'),('oa_8191','exports/B7_max8191.gds'),('crosscad','input/B7_crosscad_labels.gds'),('gui_auto','gui_auto/lab06b_b7_ec_pad_chip.calibre.db'),('final','exports_final/B7_crosscad_final.gds')]:
    folder=OUT/('pre_drc_'+name);folder.mkdir(exist_ok=True);report=folder/'pre_drc.lyrdb';source=OUT/relative
    cmd=[str(exe),'-b','-r',str(deck),'-rd','input='+str(source),'-rd','report='+str(report),'-rd','dw=3860','-rd','dh=1640'];r=subprocess.run(cmd,capture_output=True,text=True,timeout=180);(folder/'run.log').write_text(r.stdout+'\n'+r.stderr,encoding='utf-8');assert r.returncode==0,r.stderr
    tree=ET.parse(report);items=tree.findall('.//items/item');categories=[x.findtext('name') for x in tree.findall('.//categories/category')];counts={k:0 for k in categories}
    for item in items:
        cat=(item.findtext('category') or '').strip("'");counts[cat]=counts.get(cat,0)+1
    results.append(dict(name=name,gds=relative,gds_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),deck_sha256=sha,categories=len(categories),records=len(items),counts=counts,report=str(report.relative_to(ROOT)).replace('\\','/')));print(name,'original pre-DRC',len(items),'records',flush=True)
(OUT/'roundtrip_pre_drc.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
