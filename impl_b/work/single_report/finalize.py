"""Verify the integrated reader and publish its local review mirror."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import os,json,hashlib,shutil,sys
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT.parent;HERE=Path(__file__).resolve().parent
OUTPUT=Path(r'C:/Users/yangc/Documents/Codex/2026-10-30/d-lab-lab06b-codex-c01-codex/outputs/EDA_Codex_Current')
sys.path.insert(0,str(ROOT/'scripts'))
from report_policy import Tree
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
source=load(HERE/'out/report_sources.json');browser=load(ROOT/'evidence/single_report_browser.json');links=load(ROOT/'evidence/report_checks.json')
assert ROOT.resolve()==Path('C:/EDA_Codex/Lab06b').resolve()
assert browser['status']==links['status']=='passed' and browser['source_sections']==19 and browser['select_option_changes']==394 and browser['numeric_input_changes']==42
assert browser['structure']['images']==50 and browser['structure']['articles']==19 and not browser['structure']['duplicateIds'] and not browser['structure']['badImages'] and not browser['structure']['overflow']
assert browser['study_alias'] and browser['print_navigation_hidden'] and not browser['mobile_overflow']
assert source['course_steps']==17 and source['appendices']==2 and not source['technical_reexecution'] and not source['original_D_written']
assert sha(ROOT/'Lab06b_index.html')==source['report_sha256'] and sha(ROOT/'scripts/render_study.py')==source['generator_sha256'] and sha(ROOT/'assets/study.css')==source['css_sha256']
for row in source['source_pages']:
    assert sha(ROOT/row['page'])==row['sha256']
    if row.get('proof'):assert sha(ROOT/row['proof'])==row['proof_sha256']
for rel,h in source['technical_bindings'].items():assert sha(ROOT/rel)==h
report=(ROOT/'Lab06b_index.html').read_text(encoding='utf-8');assert 'data-report="lab06b-single-page"' in report and '學員驗收與交付' not in report and '學員姓名' not in report
tree=Tree(report);assert len([n for n in tree.nodes if n.tag=='article' and n.attrs.get('class')=='report-step'])==19
backup=Path(load(HERE/'backup_record.json')['backup']);records=load(backup/'backup_manifest.json')
for row in records:assert sha(backup/row.get('backup_path',row['path']))==row['sha256']
prior=load(backup/'manifest.json');prior_by_path={r['path']:r for r in prior['files']}
technical=[r for r in prior['files'] if r['path'].startswith(('work/','delivery/','sources/','reference/C01/')) or r['path'] in ['pic_spec.json','phase_settings.json','config/m2_current_core.json','config/m2_current_chip.json','config/m2_delivery.json','config/m3_acceptance.json','config/m3_crosscheck_result.json']]
for row in technical:assert sha(ROOT/row['path'])==row['sha256'],row['path']
for row in source['source_pages']:assert sha(ROOT/row['page'])==prior_by_path[row['page']]['sha256']
for name in ['README.md','manifest.json']:
    dest=backup/'root_files'/name
    if not dest.exists():
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(BASE/name,dest);records.append(dict(scope=str(BASE),path=name,backup_path='root_files/'+name,sha256=sha(dest)))
save(backup/'backup_manifest.json',records)
stamp=datetime.now(timezone(timedelta(hours=8))).isoformat()
verification=dict(timestamp=stamp,status='passed',report='Lab06b_index.html',alias='study.html',previous_overview='course_overview.html',narrator='Codex as learner/implementer',course_steps=17,full_appendices=2,
    content_source_sections=19,source_hashes_verified=True,technical_files_unchanged=len(technical),technical_reexecution=False,report_sha256=source['report_sha256'],
    inputs='work/single_report/out/report_sources.json',browser='evidence/single_report_browser.json',select_parity_changes=394,numeric_input_parity_changes=42,
    images=50,desktop_mobile_print_checked=True,html_files=links['html_files'],local_links=links['local_links_checked'],learner_acceptance_sections_removed=True,D_writes=False,backup=str(backup),
    scope='One continuous first-person report, full current technical content embedded with isolated scripts and namespaced IDs; original execution dates retained, archived outputs unchanged.',
    source_hashes={p:sha(ROOT/p) for p in ['scripts/render_study.py','scripts/render_course.py','assets/study.css','work/single_report/check_browser.cjs','work/single_report/finalize.py']})
save(ROOT/'evidence/single_report_verification.json',verification);save(ROOT/'evidence/browser_checks.json',browser)
prov=load(ROOT/'evidence/provenance.json');prov['single_page_report']=verification;save(ROOT/'evidence/provenance.json',prov)
with (ROOT/'history/CHANGELOG.md').open('a',encoding='utf-8') as f:f.write('\n## 2026-10-31 單頁完整實作總報告\n'
    '- 依使用者指示，以 Codex 作為學員／實作者，將 M0～M3 全 17 步整理為連續總報告；每步加入實際操作與學習結論，保留原始執行日期。\n'
    '- Lab06b_index.html 現為完整單頁；study.html 為別名，舊導覽留在 course_overview.html。根層入口不變。\n'
    '- 17 章＋Lab01a §7.6／理想 MZI 兩個完整附錄；50 張圖、公式、程式／證據連結與互動範例直接內嵌，沒有 iframe。\n'
    '- 所有章節 ID 與互動作用域獨立；394 選單／42 數值輸入與原分頁逐項一致，修正動態版圖圖像的相對路徑。\n'
    '- 桌面／手機目錄／列印樣式通過；26 HTML／1627 本機連結核對通過。\n'
    '- 延續移除學員驗收／交付段落的要求；本次只整合閱讀資料，未重跑 EDA 或改動採用 GDS／交接包；D 槽唯讀。\n')
for p in [ROOT/'README_Lab06b_Course.md',BASE/'README.md']:
    text=p.read_text(encoding='utf-8');marker='## 單頁完整實作總報告'
    if marker not in text:text+='\n'+marker+'\nLab06b_index.html 現為以我（Codex）作為學員的完整實作報告，含 M0～M3 17 步、Lab01a §7.6 與理想 MZI 附錄。\nstudy.html 為同一報告別名；原本導覽保留為 course_overview.html。\n重新整理閱讀內容：使用專案 scripts/render_course.py，或 scripts/render_study.py。\n';p.write_text(text,encoding='utf-8')
files=[];omit={'tools','history','__pycache__','.matplotlib','controlled_cases','test_temp'}
for directory,dirs,names in os.walk(ROOT):
    directory=Path(directory);dirs[:]=[d for d in dirs if d not in omit and not d.startswith('browser-profile') and not (d=='work' and directory!=ROOT)]
    for name in names:
        p=directory/name
        if p==ROOT/'manifest.json' or p.suffix=='.pyc':continue
        files.append(dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
save(ROOT/'manifest.json',dict(root=str(ROOT),current_step='M3 S2',current_report='Lab06b_index.html',report_type='single continuous first-person report',reader_revision='17 steps plus two full appendices; no learner acceptance/submission forms',policy='C-only work; D read-only',files=sorted(files,key=lambda r:r['path'])))
root_manifest=load(BASE/'manifest.json');root_manifest.update(current_report='Lab06b/Lab06b_index.html',reader_revision='Single continuous first-person report',reader_verification='Lab06b/evidence/single_report_verification.json');root_manifest['root_files']=[dict(path=r['path'],sha256=sha(BASE/r['path'])) for r in root_manifest['root_files']];save(BASE/'manifest.json',root_manifest)
ignore=shutil.ignore_patterns('__pycache__','*.pyc','.matplotlib','browser-profile*','work','controlled_cases','test_temp')
for folder in ['assets','course','analysis','scripts','config','evidence','reference','delivery']:shutil.copytree(ROOT/folder,OUTPUT/'Lab06b'/folder,dirs_exist_ok=True,ignore=ignore)
shutil.copytree(HERE,OUTPUT/'Lab06b/work/single_report',dirs_exist_ok=True,ignore=ignore)
for name in ['Lab06b_index.html','study.html','course_overview.html','README_Lab06b_Course.md','manifest.json']:shutil.copy2(ROOT/name,OUTPUT/'Lab06b'/name)
for name in ['Lab06b_index.html','README.md','manifest.json']:shutil.copy2(BASE/name,OUTPUT/name)
for row in files:
    p=OUTPUT/'Lab06b'/row['path'];assert p.is_file() and sha(p)==row['sha256'],row['path']
print(json.dumps(dict(status='passed',single_report=str(ROOT/'Lab06b_index.html'),steps=17,appendices=2,images=50,parity_selects=394,parity_inputs=42,technical_files_unchanged=len(technical),review_files_verified=len(files),D_writes=False,review_copy=str(OUTPUT/'Lab06b/Lab06b_index.html')),ensure_ascii=False,indent=2))
