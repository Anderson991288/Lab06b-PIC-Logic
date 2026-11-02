"""Verify evidence, record C-only changes and refresh review mirror."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import os,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT.parent
OUTPUT=Path(r'C:/Users/yangc/Documents/Codex/2026-10-30/d-lab-lab06b-codex-c01-codex/outputs/EDA_Codex_Current')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
r=load(ROOT/'work/m2_s2/out/pdk_results.json');browser=load(ROOT/'evidence/browser_checks.json');links=load(ROOT/'evidence/report_checks.json')
assert ROOT.resolve()==Path('C:/EDA_Codex/Lab06b').resolve()
assert r['core_passed'] and r['passed']==80 and r['total']==80 and r['unit_tests']['passed']==10
assert sum(v['passed'] for v in r['regression'].values())==114 and all(c['passed'] for c in r['checks'])
assert r['M1_sources_and_zip_unchanged'] and browser['status']==links['status']=='passed'
assert browser['m2_s2_cases']==80 and browser['m2_s2_worksheet']
for rel,expected in r['source_hashes'].items():assert sha(ROOT/rel)==expected,rel
for row in r['pdk_audit']['source_files']:assert sha(Path(row['path']))==row['sha256']
previous=load(ROOT/'work/m1_s5/out/handoff_results.json')
for rel,expected in previous['source_hashes'].items():assert sha(ROOT/rel)==expected,rel
assert sha(ROOT/previous['zip'])==previous['zip_sha256']
backup=Path(load(ROOT/'work/m2_s2/backup_record.json')['backup']);records=load(backup/'backup_manifest.json')
for row in records:assert sha(backup/row.get('backup_path',row['path']))==row['sha256']
for name in ['README.md','manifest.json']:
    dest=backup/'root_files'/name;assert not dest.exists();dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(BASE/name,dest);assert sha(dest)==sha(BASE/name)
    records.append(dict(scope=str(BASE),path=name,backup_path='root_files/'+name,sha256=sha(dest)))
save(backup/'backup_manifest.json',records)
stamp=datetime.now(timezone(timedelta(hours=8))).isoformat()
extra_sources=['scripts/run_m2_s2.ps1','scripts/render_m2_s2.py','scripts/render_course.py','work/m2_s2/plot_comparison.py','work/m2_s2/browser_qa.cjs']
all_sources={**r['source_hashes'],**{p:sha(ROOT/p) for p in extra_sources}}
verification=dict(timestamp=stamp,step='M2 S2',status='passed',root=str(ROOT),D_writes=False,
    engine=r['engine'],pdk_version=r['pdk_audit']['pdk_version'],ipkiss_version=r['pdk_audit']['ipkiss_version'],
    passed=80,total=80,max_abs_U_error=r['max_abs_U_error'],max_abs_delta_error=r['max_abs_delta_error'],
    functions=r['functions'],unit_tests=r['unit_tests'],regression=r['regression'],checks=r['checks'],
    source_hashes=all_sources,source_hashes_verified=True,M1_source_files_and_zip_unchanged=True,
    html_files=links['html_files'],local_links=links['local_links_checked'],browser_cases=80,
    learner_worksheet_verified=True,backup=str(backup),learner_submission='pending',scope=r['scope'],next_step='M2 S3')
save(ROOT/'evidence/m2_s2_verification.json',verification)
prov=load(ROOT/'evidence/provenance.json')
prov['m2_s2']=dict(timestamp=stamp,current_execution_root=str(ROOT),result='work/m2_s2/out/pdk_results.json',
    pdk_audit='work/m2_s2/out/pdk_model_audit.json',comparison_csv='work/m2_s2/out/comparison_80.csv',
    engine=r['engine'],passed=80,total=80,unit_tests_passed=10,regression_passed=114,M1_sources_and_zip_unchanged=True,
    source_hashes=all_sources,limitations=r['scope'],learner_submission='pending',
    api_reference='https://academy.lucedaphotonics.com/tutorials/circuitmodels/')
prov['current_execution_scope']='C:/EDA_Codex/Lab06b: M0/M1 cores and M2 S1 boundary, M2 S2 actual CORNERSTONE/Caphe circuit replay; installed MMI uses default ideal model. D read-only.'
save(ROOT/'evidence/provenance.json',prov)
with (ROOT/'history/CHANGELOG.md').open('a',encoding='utf-8') as f:
    f.write('\n## 2026-10-31 M2 S2\n'
            '- 僅在 C:\\EDA_Codex 工作；D 槽沒有寫入。\n'
            '- 實際呼叫 CORNERSTONE 2.6.luceda1／IPKISS 2026.03.3 Caphe，建立 14 MMI、14 理想相位的 B7 邏輯電路。\n'
            '- 稽核顯示本機 MMI 繼承預設理想 Coupler2x2Model；未宣稱包含量測／製程容差或實體波導傳播。\n'
            '- 原相位固定，80/80 真值通過，完整複數 U 最大差 2.559e-16；產生逐路場／功率／Δ 比較 CSV 與 S 矩陣。\n'
            '- 10 項本步測試、114 項回歸、13 項檢查及 5 種錯誤偵測通過；M1 原檔及 ZIP 雜湊不變。\n'
            '- 17 份 HTML、788 個連結及 80 組瀏覽器逐筆比較通過；新增圖表與學員記錄；下一步 M2 S3。\n')
p=BASE/'README.md';text=p.read_text(encoding='utf-8').replace('目前教材與核心實驗：M0、M1 全步及 M2 S1；','目前教材與核心實驗：M0、M1 全步及 M2 S1～S2；').replace('scripts/run_m2_s1.ps1','scripts/run_m2_s2.ps1')
text=text.replace('下一步：M2 S2，CORNERSTONE PDK 電路與 80 筆比較。','M2 S2：work/m2_s2/out/comparison_80.csv，80/80 通過；本機 PDK MMI 為預設理想模型。\n下一步：M2 S3，七顆 MZI 實體 core 版圖與 GDS。');p.write_text(text,encoding='utf-8')
omitted={'tools','history','__pycache__','.matplotlib','controlled_cases','test_temp'};files=[]
for directory,dirs,names in os.walk(ROOT):
    current=Path(directory)
    dirs[:]=[d for d in dirs if d not in omitted and not d.startswith('browser-profile') and not (d=='work' and current!=ROOT)]
    for name in names:
        path=current/name
        if path==ROOT/'manifest.json' or path.suffix=='.pyc':continue
        files.append(dict(path=path.relative_to(ROOT).as_posix(),bytes=path.stat().st_size,sha256=sha(path)))
manifest=dict(root=str(ROOT),current_step='M2 S2',policy='C-only work; D read-only',
    scope='course, models, M1 handoff, M2 boundary, PDK circuit comparison and evidence; vendor tools and temporary files excluded',files=sorted(files,key=lambda r:r['path']))
save(ROOT/'manifest.json',manifest)
save(BASE/'manifest.json',dict(root=str(BASE),project='Lab06b',current_step='M2 S2',
    root_files=[dict(path=rel,sha256=sha(BASE/rel)) for rel in ['AGENTS.md','EDA_paths.json','Lab06b_index.html','README.md','Lab06b/manifest.json']],
    verification='Lab06b/evidence/m2_s2_verification.json',D_restore='migration_archive/d_restore_result.json'))
ignore=shutil.ignore_patterns('__pycache__','*.pyc','.matplotlib','browser-profile*','work','controlled_cases','test_temp')
for folder in ['course','analysis','config','scripts','evidence','learner','reference','delivery']:
    shutil.copytree(ROOT/folder,OUTPUT/'Lab06b'/folder,dirs_exist_ok=True,ignore=ignore)
for folder in ['common','m0_s1','m0_s2','m0_s3','m1_s1','m1_s2','m1_s3','m1_s4','m1_s5','m2_s1','m2_s2']:
    shutil.copytree(ROOT/'work'/folder,OUTPUT/'Lab06b/work'/folder,dirs_exist_ok=True,ignore=ignore)
for name in ['Lab06b_index.html','EDA_paths.json','README_Lab06b_Course.md','pic_spec.json','phase_settings.json','manifest.json']:shutil.copy2(ROOT/name,OUTPUT/'Lab06b'/name)
for name in ['AGENTS.md','EDA_paths.json','Lab06b_index.html','README.md','manifest.json']:shutil.copy2(BASE/name,OUTPUT/name)
copied=0
for row in manifest['files']:
    p=OUTPUT/'Lab06b'/row['path']
    if p.is_file():assert sha(p)==row['sha256'],row['path'];copied+=1
print(json.dumps(dict(status='passed',step='M2 S2',root=str(ROOT),truths='80/80',unit_tests=10,regression=114,
    M1_unchanged=True,D_writes=False,review_files_verified=copied,next_step='M2 S3',
    review_copy=str(OUTPUT/'Lab06b/course/m2_s2.html')),ensure_ascii=False,indent=2))
