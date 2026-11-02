"""Back up reader sources, wire output policy and remove worksheet sections."""
from pathlib import Path
from datetime import datetime
import json,hashlib,shutil,sys,re
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'scripts'))
from report_policy import clean_course_html
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
backup=ROOT/'history'/('before_remove_learner_sections_'+datetime.now().strftime('%Y%m%d_%H%M%S'));backup.mkdir(parents=True)
pages=[ROOT/'Lab06b_index.html',*sorted((ROOT/'course').glob('*.html')),ROOT/'analysis/lab01a_7_6.html',ROOT/'reference/source_context.html']
renderers=[p for p in sorted((ROOT/'scripts').glob('render*.py')) if p.name!='render_migration_context.py'];sources=pages+renderers+[ROOT/'manifest.json',ROOT/'evidence/browser_checks.json',ROOT/'evidence/report_checks.json',ROOT/'evidence/provenance.json',ROOT/'history/CHANGELOG.md']
records=[]
for p in sources:
    rel=p.relative_to(ROOT);dest=backup/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);assert sha(dest)==sha(p);records.append(dict(path=rel.as_posix(),sha256=sha(p)))
save(backup/'backup_manifest.json',records);save(HERE/'backup_record.json',dict(backup=str(backup)))
patched=[]
for p in renderers:
    text=p.read_text(encoding='utf-8');before=text
    # These are only HTML write statements; config/evidence writers are untouched.
    if 'write_text(html,encoding=' in text:text=text.replace('write_text(html,encoding=','write_text(clean_course_html(html),encoding=')
    if p.name=='render_course.py':
        text=text.replace('target.write_text(text,encoding=','target.write_text(clean_course_html(text),encoding=')
        text=text.replace('    p.write_text(text,encoding=','    p.write_text(clean_course_html(text),encoding=')
    if text!=before:
        text='from report_policy import clean_course_html\n'+text;p.write_text(text,encoding='utf-8');patched.append(p.name)
changes=[]
for p in pages:
    old=p.read_text(encoding='utf-8');new=clean_course_html(old)
    if new!=old:p.write_text(new,encoding='utf-8');changes.append(dict(page=p.relative_to(ROOT).as_posix(),before_sha256=hashlib.sha256(old.encode()).hexdigest(),after_sha256=sha(p)))
save(HERE/'out/removal_results.json',dict(status='applied',backup=str(backup),changed_pages=changes,patched_renderers=patched,scope='All learner submission/acceptance sections, worksheets, related worksheet click handlers and navigation; numerical demonstrations and technical evidence retained'))
print(json.dumps(dict(pages=len(changes),renderers=len(patched),backup=str(backup)),ensure_ascii=False))
