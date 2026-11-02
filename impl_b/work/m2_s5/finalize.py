"""Record M2 S5 evidence, verify prior artifacts and refresh reading mirror."""
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
r=load(ROOT/'work/m2_s5/out/interface_results.json');browser=load(ROOT/'evidence/browser_checks.json');links=load(ROOT/'evidence/report_checks.json')
assert ROOT.resolve()==Path('C:/EDA_Codex/Lab06b').resolve()
assert r['core_passed'] and r['unit_tests']['passed']==8 and sum(v['passed'] for v in r['regression'].values())==136
assert all(c['passed'] for c in r['checks']) and r['accepted_core_files_unchanged']
assert r['M1_sources_and_zip_unchanged'] and r['M1_baseline_replay_passed']==80
assert browser['status']==links['status']=='passed' and browser['m2_s5_pad_cases']==80 and browser['m2_s5_optical_cases']==10 and browser['m2_s5_worksheet']
for rel,expected in r['source_hashes'].items():assert sha(ROOT/rel)==expected,rel
assert sha(ROOT/'work/m2_s5/out/b7_ec_pad.gds')==r['gds_sha256']==r['readback']['gds_sha256']
current=load(ROOT/'config/m2_current_chip.json');assert current['accepted_at_step']=='M2 S5'
assert current['m1_spec_sha256']==sha(ROOT/'pic_spec.json')
for rel,expected in current['files'].items():assert (ROOT/rel).resolve().is_relative_to(ROOT) and sha(ROOT/rel)==expected,rel
core=load(ROOT/'config/m2_current_core.json')
for rel,expected in core['files'].items():assert sha(ROOT/rel)==expected,rel
for row in r['controlled_faults']:
    assert row['detected']
    if row['type']=='actual_fault_GDS':assert sha(ROOT/'work/m2_s5/work/controlled'/(row['name']+'.gds'))==row['gds_sha256']
assert all(p['identical'] for p in r['readback']['core_layer_comparison'])
previous=load(ROOT/'work/m1_s5/out/handoff_results.json')
for rel,expected in previous['source_hashes'].items():assert sha(ROOT/rel)==expected,rel
assert sha(ROOT/previous['zip'])==previous['zip_sha256']
backup=Path(load(ROOT/'work/m2_s5/backup_record.json')['backup']);records=load(backup/'backup_manifest.json')
for row in records:assert sha(backup/row.get('backup_path',row['path']))==row['sha256']
prior=load(backup/'manifest.json')
prior_files=[row for row in prior['files'] if row['path'].startswith(('work/m2_s2/','work/m2_s3/','work/m2_s4/')) or row['path'] in ['config/m2_current_core.json','work/common/core_layout.py']]
for row in prior_files:assert sha(ROOT/row['path'])==row['sha256'],row['path']
for name in ['README.md','manifest.json']:
    dest=backup/'root_files'/name;assert not dest.exists();dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(BASE/name,dest);assert sha(dest)==sha(BASE/name)
    records.append(dict(scope=str(BASE),path=name,backup_path='root_files/'+name,sha256=sha(dest)))
save(backup/'backup_manifest.json',records)
stamp=datetime.now(timezone(timedelta(hours=8))).isoformat()
extra=['scripts/run_m2_s5.ps1','scripts/render_m2_s5.py','scripts/render_course.py','work/m2_s5/plot_chip.py','work/m2_s5/browser_qa.cjs']
sources={**r['source_hashes'],**{p:sha(ROOT/p) for p in extra}}
save(ROOT/'evidence/m2_s5_verification.json',dict(timestamp=stamp,step='M2 S5',status='passed',root=str(ROOT),D_writes=False,
    counts=r['counts'],chip_size_um=r['chip_size_um'],unit_tests=r['unit_tests'],regression=r['regression'],checks=r['checks'],
    selected_GDS_readback=r['readback'],EC_audit=r['EC_audit'],current_chip=current,source_hashes=sources,source_hashes_verified=True,
    M1_sources_and_zip_unchanged=True,accepted_core_files_and_geometry_unchanged=True,prior_files_verified=len(prior_files),
    M1_baseline_replay_passed=80,browser_pad_cases=80,browser_optical_cases=10,worksheet_verified=True,
    html_files=links['html_files'],local_links=links['local_links_checked'],backup=str(backup),learner_submission='pending',scope=r['scope'],next_step='M2 S6'))
prov=load(ROOT/'evidence/provenance.json')
prov['m2_s5']=dict(timestamp=stamp,current_execution_root=str(ROOT),result='work/m2_s5/out/interface_results.json',
    current_chip_index='config/m2_current_chip.json',counts=r['counts'],chip_size_um=r['chip_size_um'],
    EC='custom_reference_geometry; no validated compact model',core_geometry_unchanged=True,signal_terminal='A',return_terminal='B',
    unit_tests_passed=8,regression_passed=136,M1_sources_and_zip_unchanged=True,source_hashes=sources,
    limitations=r['scope'],learner_submission='pending',references=['https://cornerstone.sotonfab.co.uk/mpw/technology-platforms/','https://www.klayout.de/doc/code/class_Cell.html'])
prov['current_execution_scope']='C:/EDA_Codex/Lab06b: M0/M1 and M2 S1-S5. Actual chip GDS with 10 custom reference ECs, 14 signal PADs and two GND PADs; accepted S4 core embedded unchanged. Selected metal/HT connectivity and geometry checked; qualified EC/full DRC/LVS/thermal calibration/layout phase replay pending. D read-only.'
save(ROOT/'evidence/provenance.json',prov)
with (ROOT/'history/CHANGELOG.md').open('a',encoding='utf-8') as f:
    f.write('\n## 2026-10-31 M2 S5\n'
            '- 僅在 C:\\EDA_Codex 工作；D 槽沒有寫入。\n'
            '- 由採用版索引讀取 S4 原 GDS，不改軌距或重建 core；合併後 GDS 3／39／41／99／100 的內嵌 core XOR 比較無差異。\n'
            '- 配置左右各 5 個自訂參考 EC、10 段 600 µm 光學扇出、14 個驅動 PAD＋2 個共地 PAD；設計區 3860×1640 µm。\n'
            '- 沿用 A 端驅動／B 端回地，以分欄 GND 走線保留 30 µm 軌距；實際 GDS 41 有 14 訊號網＋1 共地網，14 個 HT 區各接正確兩網。\n'
            '- 匯出 PAD↔heater↔θ／φ、光學 I/O、GND 與扇出長度 CSV；新增 config/m2_current_chip.json 給 S6 承接。\n'
            '- 30 個光學端點覆蓋、8030 個扇出取樣、6 項局部線寬／間距篩查、8 項新測試及 136 項回歸通過。\n'
            '- 短路與回地斷口真實負例 GDS，以及 A／B 對照誤換副本皆被偵測；正式晶片 GDS 未改。\n'
            '- 20 份 HTML、948 個連結、80 組 PAD／相位與 10 個光學接口瀏覽器核對通過。\n'
            '- EC 尚未具製程／模式／耦合響應資格；完整 DRC／LVS、封裝、熱與共地校正及光學相位回註待後續，M1 80/80 仍僅為基準。\n')
p=BASE/'README.md';text=p.read_text(encoding='utf-8').replace('目前教材與核心實驗：M0、M1 全步及 M2 S1～S4；','目前教材與核心實驗：M0、M1 全步及 M2 S1～S5；').replace('scripts/run_m2_s4.ps1','scripts/run_m2_s5.ps1')
text=text.replace('下一步：M2 S5，EC 光學 I/O、heater PAD 與 GND。','M2 S5：目前晶片 GDS／接口表見 Lab06b/config/m2_current_chip.json。\n初版設計區 3860×1640 µm；10 個參考 EC、14 訊號 PAD＋2 GND PAD；core 幾何保留，EC／熱電響應及完整驗證待後續。\n下一步：M2 S6，完整規則／連通檢查與違規記錄。');p.write_text(text,encoding='utf-8')
omitted={'tools','history','__pycache__','.matplotlib','controlled_cases','test_temp'};files=[]
for directory,dirs,names in os.walk(ROOT):
    directory=Path(directory);dirs[:]=[d for d in dirs if d not in omitted and not d.startswith('browser-profile') and not (d=='work' and directory!=ROOT)]
    for name in names:
        path=directory/name
        if path==ROOT/'manifest.json' or path.suffix=='.pyc':continue
        files.append(dict(path=path.relative_to(ROOT).as_posix(),bytes=path.stat().st_size,sha256=sha(path)))
manifest=dict(root=str(ROOT),current_step='M2 S5',policy='C-only work; D read-only',
    scope='course, models, handoff, reviewed core, reference chip interfaces and evidence; vendor tools and temporary/controlled copies excluded',files=sorted(files,key=lambda r:r['path']))
save(ROOT/'manifest.json',manifest)
save(BASE/'manifest.json',dict(root=str(BASE),project='Lab06b',current_step='M2 S5',
    root_files=[dict(path=rel,sha256=sha(BASE/rel)) for rel in ['AGENTS.md','EDA_paths.json','Lab06b_index.html','README.md','Lab06b/manifest.json']],
    verification='Lab06b/evidence/m2_s5_verification.json',D_restore='migration_archive/d_restore_result.json'))
ignore=shutil.ignore_patterns('__pycache__','*.pyc','.matplotlib','browser-profile*','work','controlled_cases','test_temp')
for folder in ['course','analysis','config','scripts','evidence','learner','reference','delivery']:
    shutil.copytree(ROOT/folder,OUTPUT/'Lab06b'/folder,dirs_exist_ok=True,ignore=ignore)
for folder in ['common','m0_s1','m0_s2','m0_s3','m1_s1','m1_s2','m1_s3','m1_s4','m1_s5','m2_s1','m2_s2','m2_s3','m2_s4','m2_s5']:
    shutil.copytree(ROOT/'work'/folder,OUTPUT/'Lab06b/work'/folder,dirs_exist_ok=True,ignore=ignore)
for name in ['Lab06b_index.html','EDA_paths.json','README_Lab06b_Course.md','pic_spec.json','phase_settings.json','manifest.json']:shutil.copy2(ROOT/name,OUTPUT/'Lab06b'/name)
for name in ['AGENTS.md','EDA_paths.json','Lab06b_index.html','README.md','manifest.json']:shutil.copy2(BASE/name,OUTPUT/name)
copied=0
for row in manifest['files']:
    p=OUTPUT/'Lab06b'/row['path']
    if p.is_file():assert sha(p)==row['sha256'],row['path'];copied+=1
print(json.dumps(dict(status='passed',step='M2 S5',root=str(ROOT),counts=r['counts'],chip_size_um=r['chip_size_um'],
    unit_tests=8,regression=136,prior_files_verified=len(prior_files),review_files_verified=copied,M1_unchanged=True,accepted_core_unchanged=True,D_writes=False,next_step='M2 S6',
    review_copy=str(OUTPUT/'Lab06b/course/m2_s5.html')),ensure_ascii=False,indent=2))
