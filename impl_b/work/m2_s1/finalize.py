from pathlib import Path
from datetime import datetime,timezone,timedelta
import os,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT.parent
OUTPUT=Path(r'C:/Users/yangc/Documents/Codex/2026-10-30/d-lab-lab06b-codex-c01-codex/outputs/EDA_Codex_Current')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
r=load(ROOT/'work/m2_s1/out/boundary_results.json');browser=load(ROOT/'evidence/browser_checks.json');links=load(ROOT/'evidence/report_checks.json')
assert ROOT.resolve()==Path('C:/EDA_Codex/Lab06b').resolve()
assert r['core_passed'] and r['root_matches_plan'] and r['unit_tests']['passed']==15
assert sum(v['passed'] for v in r['regression'].values())==99 and all(c['passed'] for c in r['checks'])
assert r['M1_source_hashes_unchanged'] and sum(v['passed'] for v in r['M1_replay'].values())==80
assert browser['status']==links['status']=='passed' and browser['m2_s1_block_cases']==12 and browser['m2_s1_interface_cases']==125 and browser['m2_s1_worksheet']
for rel,expected in r['source_hashes'].items():assert sha(ROOT/rel)==expected,rel
previous=load(ROOT/'work/m1_s5/out/handoff_results.json')
for rel,expected in previous['source_hashes'].items():assert sha(ROOT/rel)==expected,rel
assert sha(ROOT/previous['zip'])==previous['zip_sha256']
for row in r['delivery_manifest']['files']:assert sha(ROOT/'delivery/m2_s1_io'/row['path'])==row['sha256']
backup=Path(load(ROOT/'work/m2_s1/backup_record.json')['backup']);records=load(backup/'backup_manifest.json')
for name in ['README.md','manifest.json']:
    dest=backup/'root_files'/name;assert not dest.exists();dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(BASE/name,dest);assert sha(dest)==sha(BASE/name)
    records.append(dict(scope=str(BASE),path=name,backup_path='root_files/'+name,sha256=sha(dest)))
save(backup/'backup_manifest.json',records)
stamp=datetime.now(timezone(timedelta(hours=8))).isoformat();prov=load(ROOT/'evidence/provenance.json')
prov['m2_s1']=dict(timestamp=stamp,current_execution_root=str(ROOT),result='work/m2_s1/out/boundary_results.json',
    boundary_plan='config/m2_boundary.json',delivery='delivery/m2_s1_io',summary=r['boundary_summary'],
    unit_tests_passed=15,regression_passed=99,M1_replay_passed=80,M1_sources_unchanged=True,
    source_hashes=r['source_hashes'],limitations=r['scope'],learner_submission='pending',
    physics_references=['https://interactivetextbooks.tudelft.nl/tn2421/content/Chap5_Interference/InterferenceCoherence_2022_01Clean.html',
        'https://hub.hamamatsu.com/us/en/technical-notes/detector-selection/the-wits-guide-to-selecting-a-photodetector.html'])
prov['current_execution_scope']='C:/EDA_Codex/Lab06b: M0 and M1 cores, plus M2 S1 logical PIC boundary and proposed optical/electrical I/O. M1 immutable files unchanged; D is read-only.'
save(ROOT/'evidence/provenance.json',prov)
save(ROOT/'evidence/m2_s1_verification.json',dict(timestamp=stamp,step='M2 S1',status='passed',root=str(ROOT),D_writes=False,
    summary=r['boundary_summary'],unit_tests=r['unit_tests'],regression=r['regression'],checks=r['checks'],
    source_hashes_verified=True,M1_source_files_and_zip_unchanged=True,M1_replay=r['M1_replay'],
    html_files=links['html_files'],local_links=links['local_links_checked'],browser_block_cases=12,browser_interface_cases=125,
    learner_worksheet_verified=True,backup=str(backup),learner_submission='pending',next_step='M2 S2'))
with (ROOT/'history/CHANGELOG.md').open('a',encoding='utf-8') as f:
    f.write('\n## 2026-10-31 M2 S1\n'
            '- 僅在 C:\\EDA_Codex 工作；D 槽沒有寫入。\n'
            '- 新增 config/m2_boundary.json overlay，綁定 M1 規格，界定 4 個 PIC 規劃區塊與 8 個外部功能區塊。\n'
            '- 10 個規劃光學接口、14 路相位驅動＋1 邏輯共地、14 條 heater B 端回路；實際 PAD 數量與校正待定。\n'
            '- 匯出光學／電氣 I/O、系統分工與回路 CSV，產生兩張功能圖與學員記錄。\n'
            '- 15 項本步測試、99 項回歸、11 項檢查與 5 種錯誤副本拒絕通過；M1 仍重播 80／80、來源與 ZIP 雜湊不變。\n'
            '- 12 個區塊分類、125 組介面預覽、16 份 HTML 及 744 個連結通過；下一步 M2 S2。\n')
p=BASE/'README.md';text=p.read_text(encoding='utf-8').replace('目前教材與核心實驗：M0 S1～M1 S5；','目前教材與核心實驗：M0、M1 全步及 M2 S1；').replace('scripts/run_m1_s5.ps1','scripts/run_m2_s1.ps1')
text=text.replace('下一步：M2 S1，PIC 邊界與 I/O 表。','邊界與 I/O：Lab06b/delivery/m2_s1_io/。\n下一步：M2 S2，CORNERSTONE PDK 電路與 80 筆比較。');p.write_text(text,encoding='utf-8')
omitted={'tools','history','__pycache__','.matplotlib','controlled_cases','test_temp'}
files=[]
for directory,dirs,names in os.walk(ROOT):
    current=Path(directory)
    dirs[:]=[d for d in dirs if d not in omitted and not d.startswith('browser-profile') and not (d=='work' and current!=ROOT)]
    for name in names:
        path=current/name
        if path==ROOT/'manifest.json' or path.suffix=='.pyc':continue
        files.append(dict(path=path.relative_to(ROOT).as_posix(),bytes=path.stat().st_size,sha256=sha(path)))
manifest=dict(root=str(ROOT),current_step='M2 S1',policy='C-only work; D read-only',
    scope='course, models, M1 handoff, M2 logical boundary and evidence; vendor tools and temporary test copies excluded',files=sorted(files,key=lambda r:r['path']))
save(ROOT/'manifest.json',manifest)
save(BASE/'manifest.json',dict(root=str(BASE),project='Lab06b',current_step='M2 S1',
    root_files=[dict(path=rel,sha256=sha(BASE/rel)) for rel in ['AGENTS.md','EDA_paths.json','Lab06b_index.html','README.md','Lab06b/manifest.json']],
    verification='Lab06b/evidence/m2_s1_verification.json',D_restore='migration_archive/d_restore_result.json'))
ignore=shutil.ignore_patterns('__pycache__','*.pyc','.matplotlib','browser-profile*','work','controlled_cases','test_temp')
for folder in ['course','analysis','config','scripts','evidence','learner','reference','delivery']:
    shutil.copytree(ROOT/folder,OUTPUT/'Lab06b'/folder,dirs_exist_ok=True,ignore=ignore)
for folder in ['common','m0_s1','m0_s2','m0_s3','m1_s1','m1_s2','m1_s3','m1_s4','m1_s5','m2_s1']:
    shutil.copytree(ROOT/'work'/folder,OUTPUT/'Lab06b/work'/folder,dirs_exist_ok=True,ignore=ignore)
for name in ['Lab06b_index.html','EDA_paths.json','README_Lab06b_Course.md','pic_spec.json','phase_settings.json','manifest.json']:shutil.copy2(ROOT/name,OUTPUT/'Lab06b'/name)
for name in ['AGENTS.md','EDA_paths.json','Lab06b_index.html','README.md','manifest.json']:shutil.copy2(BASE/name,OUTPUT/name)
for row in manifest['files']:
    p=OUTPUT/'Lab06b'/row['path']
    if p.is_file():assert sha(p)==row['sha256'],row['path']
print(json.dumps(dict(status='passed',step='M2 S1',root=str(ROOT),optical_interfaces=10,phase_drives=14,logical_returns=1,
    physical_pad_count=None,M1_unchanged=True,D_writes=False,next_step='M2 S2',
    review_copy=str(OUTPUT/'Lab06b/course/m2_s1.html')),ensure_ascii=False,indent=2))
