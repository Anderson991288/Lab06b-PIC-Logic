from pathlib import Path
from datetime import datetime
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
dest=ROOT/'history'/('before_virtuoso_report_'+datetime.now().strftime('%Y%m%d_%H%M%S'));dest.mkdir(parents=True,exist_ok=False)
records=[]
for rel in ['Lab06b_index.html','study.html','scripts/render_study.py','scripts/render_course.py','manifest.json','evidence/provenance.json','evidence/single_report_verification.json','README_Lab06b_Course.md','work/single_report/out/report_sources.json']:
 p=ROOT/rel;q=dest/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q);records.append(dict(path=rel,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
for name in ['README.md','manifest.json']:
 p=ROOT.parent/name;q=dest/'root_files'/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
(dest/'backup_manifest.json').write_text(json.dumps(records,indent=2))
(HERE/'backup_record.json').write_text(json.dumps({'backup':str(dest)},indent=2))
print('Report and prior manifest backed up:',dest)
