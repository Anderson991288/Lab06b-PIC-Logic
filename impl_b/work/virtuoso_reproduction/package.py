from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,hashlib,shutil,zipfile
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;OUT=HERE/'out';DEST=ROOT/'delivery/virtuoso_calibre';DEST.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(p,q):q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
copy(HERE/'README_reproduction.md',DEST/'README.md')
copy(OUT/'exports_final/B7_crosscad_final.gds',DEST/'B7_crosscad_final.gds')
for name in ['input','import','exports','exports_final','cli_accepted','cli_negative','cli_crosscad','gui_auto','gui_fixed','pre_drc_oa_200','pre_drc_oa_8191','pre_drc_crosscad','pre_drc_gui_auto','pre_drc_final','clean_replay']:
 shutil.copytree(OUT/name,DEST/'evidence'/name,dirs_exist_ok=True)
for name in ['reproduction_results.json','oa_cell_name_map.json','oa_final_readback.txt','roundtrip_geometry.json','roundtrip_pre_drc.json','label_revision.json','final_geometry.json','clean_replay.json','GDS100_angle_diagnosis.json','GUI_auto_saved.runset','GUI_fixed_saved.runset','report_colors.drf']:
 copy(OUT/name,DEST/'evidence'/name)
copy(OUT/'rules/cornerstone_basic_draft.svrf',DEST/'rules/cornerstone_basic_draft.svrf')
for name in ['virtuoso_final','virtuoso_core','calibre_auto_inputs','calibre_fixed_inputs','rve_final']:
 meta=json.loads((OUT/'screenshots'/(name+'.json')).read_text(encoding='utf-8'))
 chosen=[]
 for row in meta:
  if row['file'].endswith(('calibre_fixed_inputs_1.png','calibre_fixed_inputs_2.png')):continue
  copy(OUT/row['file'],DEST/row['file']);chosen.append(row)
 (DEST/'screenshots'/(name+'.json')).write_text(json.dumps(chosen,ensure_ascii=False,indent=2),encoding='utf-8')
for name in ['replay_prepare.py','replay_native.sh','verify_clean.py','verify_clean_geometry.py','patch_labels.py','import_crosscad.sh','open_review.sh','open_review.il','roundtrip_check.py','run_klayout.py','final_geometry.py','run_final_check.py','summarize.py','capture_native.py']:
 copy(HERE/name,DEST/'sources'/name)
files=[dict(path=p.relative_to(DEST).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='manifest.json']
manifest=dict(schema='lab06b.virtuoso_calibre_package.v1',timestamp=datetime.now(timezone(timedelta(hours=8))).isoformat(),source='Fresh 2026-10-31 execution in C:/EDA_Codex/Lab06b',final_gds_sha256=sha(DEST/'B7_crosscad_final.gds'),portable_evidence=True,runtime='Replay sources are a canonical project overlay; use full C project with locally installed/licensed EDA tools. Runset paths must be edited after relocation.',OA_database_included=False,files=files)
(DEST/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
archive=ROOT/'delivery/Lab06b_Virtuoso_Calibre_reproduction.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for p in sorted(DEST.rglob('*')):
  if p.is_file():z.write(p,'virtuoso_calibre/'+p.relative_to(DEST).as_posix())
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for row in files:assert hashlib.sha256(z.read('virtuoso_calibre/'+row['path'])).hexdigest()==row['sha256']
(ROOT/'config/virtuoso_package.json').write_text(json.dumps(dict(archive=archive.relative_to(ROOT).as_posix(),sha256=sha(archive),bytes=archive.stat().st_size,manifest='delivery/virtuoso_calibre/manifest.json',files=len(files),verified=True),indent=2)+'\n')
print('Packaged and verified',len(files),'files',archive.stat().st_size,'bytes')
