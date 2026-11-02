from pathlib import Path
import json,hashlib,subprocess,shutil,xml.etree.ElementTree as ET,collections
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/m2_s6/out/before'
pointer=json.loads((ROOT/'config/m2_current_chip.json').read_text(encoding='utf-8'))
for rel,d in pointer['files'].items():assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==d
src=next(ROOT/p for p in pointer['files'] if p.endswith('.gds'));dst=OUT/'b7_ec_pad.gds';shutil.copy2(src,dst)
info=json.loads((ROOT/'work/m2_s5/out/chip_info.json').read_text(encoding='utf-8'));w,h=info['chip_size_um']
paths=json.loads((ROOT/'EDA_paths.json').read_text(encoding='utf-8'));exe=ROOT/paths['windows']['klayout_exe'];deck=ROOT/paths['windows']['drc_deck'];report=OUT/'pre_drc.lyrdb'
cmd=[str(exe),'-b','-r',str(deck),'-rd','input='+str(dst),'-rd','report='+str(report),'-rd','dw='+str(w),'-rd','dh='+str(h)]
r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
(OUT/'pre_drc.log').write_text(r.stdout+'\n'+r.stderr,encoding='utf-8')
if r.returncode:raise RuntimeError(r.stderr[-2000:])
tree=ET.parse(report);cats=[c.findtext('name') for c in tree.findall('.//categories/category')];counts=collections.Counter(item.findtext('category') for item in tree.findall('.//items/item'))
result=dict(deck_sha256=hashlib.sha256(deck.read_bytes()).hexdigest(),gds_sha256=hashlib.sha256(dst.read_bytes()).hexdigest(),rules=len(cats),violations=sum(counts.values()),counts=dict(counts))
(OUT/'probe_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False,indent=2))
