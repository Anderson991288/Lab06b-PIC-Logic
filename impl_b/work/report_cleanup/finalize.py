from pathlib import Path
from datetime import datetime,timezone,timedelta
import os,json,hashlib,shutil,sys
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT.parent;HERE=Path(__file__).resolve().parent
OUTPUT=Path(r'C:/Users/yangc/Documents/Codex/2026-10-30/d-lab-lab06b-codex-c01-codex/outputs/EDA_Codex_Current')
sys.path.insert(0,str(ROOT/'scripts'))
from report_policy import clean_course_html,Tree,plain
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
browser=load(ROOT/'evidence/report_cleanup_browser.json');links=load(ROOT/'evidence/report_checks.json');assert browser['status']==links['status']=='passed' and browser['select_option_changes']==394
backup=Path(load(HERE/'backup_record.json')['backup']);records=load(backup/'backup_manifest.json')
for r in records:assert sha(backup/r['path'])==r['sha256']
old=load(backup/'manifest.json');technical=[r for r in old['files'] if r['path'].startswith(('work/','delivery/','sources/','work/common/')) or r['path'] in ['pic_spec.json','phase_settings.json','config/m2_current_chip.json','config/m2_current_core.json','config/m2_delivery.json','config/m3_acceptance.json','config/m3_crosscheck_result.json']]
for row in technical:assert sha(ROOT/row['path'])==row['sha256'],row['path']
changed=[]
for record in records:
    p=ROOT/record['path']
    if p.suffix!='.html':continue
    text=p.read_text(encoding='utf-8');assert clean_course_html(text)==text,p
    tree=Tree(text)
    assert not any(n.tag=='h2' and n.attrs.get('id')=='submit' for n in tree.nodes),p
    assert '學員姓名' not in text and '學員驗收與交付' not in text,p
    if sha(p)!=record['sha256']:changed.append(dict(path=record['path'],before_sha256=record['sha256'],after_sha256=sha(p)))
assert len(changed)==18
stamp=datetime.now(timezone(timedelta(hours=8))).isoformat()
report=dict(timestamp=stamp,status='passed',change='Remove learner acceptance/submission sections and worksheets from all reader pages',changed_pages=changed,policy='scripts/report_policy.py',
    changed_renderers=[r['path'] for r in records if r['path'].startswith('scripts/') and sha(ROOT/r['path'])!=r['sha256']],
    backup=str(backup),technical_files_unchanged=len(technical),D_writes=False,html_files=links['html_files'],local_links=links['local_links_checked'],browser=browser,
    scope='Presentation change only; technical content, model outputs, GDS and original delivery packages retained; archived source/evidence snapshots remain historical.')
save(ROOT/'evidence/report_cleanup.json',report);save(HERE/'out/removal_results.json',report)
save(ROOT/'evidence/browser_checks.json',browser)
prov=load(ROOT/'evidence/provenance.json');prov['reader_revision_remove_learner_sections']=dict(timestamp=stamp,report='evidence/report_cleanup.json',backup=str(backup),changed_pages=18,technical_results_unchanged=True,policy='scripts/report_policy.py',D_writes=False);save(ROOT/'evidence/provenance.json',prov)
with (ROOT/'history/CHANGELOG.md').open('a',encoding='utf-8') as f:f.write('\n## 2026-10-31 閱讀版段落移除\n- 依使用者指示，移除全部學員驗收／交付段落、表單及相關導覽；18 個頁面更新。\n- 增加統一輸出政策並接入 17 個產生程式，重建後維持移除；技術檢查、資料／GDS 交付與下一步導覽保留。\n- 24 HTML／1163 連結與 394 個既有選單切換核對通過；計算結果、GDS 與原始交接包不變。\n- 僅在 C:\\EDA_Codex 工作，D 槽唯讀。\n')
omitted={'tools','history','__pycache__','.matplotlib','controlled_cases','test_temp'};files=[]
for directory,dirs,names in os.walk(ROOT):
    directory=Path(directory);dirs[:]=[d for d in dirs if d not in omitted and not d.startswith('browser-profile') and not (d=='work' and directory!=ROOT)]
    for name in names:
        p=directory/name
        if p==ROOT/'manifest.json' or p.suffix=='.pyc':continue
        files.append(dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
manifest=dict(root=str(ROOT),current_step='M3 S2',reader_revision='Learner acceptance/submission sections and worksheets removed',policy='C-only work; D read-only',files=sorted(files,key=lambda x:x['path']));save(ROOT/'manifest.json',manifest)
root_manifest=load(BASE/'manifest.json');root_manifest['reader_revision']='Learner acceptance/submission sections removed';root_manifest['root_files']=[dict(path=r['path'],sha256=sha(BASE/r['path'])) for r in root_manifest['root_files']];root_manifest['reader_verification']='Lab06b/evidence/report_cleanup.json';save(BASE/'manifest.json',root_manifest)
ignore=shutil.ignore_patterns('__pycache__','*.pyc','.matplotlib','browser-profile*','work','controlled_cases','test_temp')
for folder in ['course','scripts','evidence']:shutil.copytree(ROOT/folder,OUTPUT/'Lab06b'/folder,dirs_exist_ok=True,ignore=ignore)
shutil.copytree(HERE,OUTPUT/'Lab06b/work/report_cleanup',dirs_exist_ok=True,ignore=ignore)
for rel in ['Lab06b_index.html','analysis/lab01a_7_6.html','reference/source_context.html','config/course.json','README_Lab06b_Course.md','manifest.json']:
    shutil.copy2(ROOT/rel,OUTPUT/'Lab06b'/rel)
shutil.copy2(BASE/'manifest.json',OUTPUT/'manifest.json')
for row in files:
    p=OUTPUT/'Lab06b'/row['path'];assert p.is_file() and sha(p)==row['sha256'],row['path']
print(json.dumps(dict(status='passed',pages=18,renderers=len(report['changed_renderers']),technical_files_unchanged=len(technical),review_files_verified=len(files),D_writes=False),ensure_ascii=False))
