"""Verify clean rebuild acceptance and export the complete reading mirror."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import sys,os,json,csv,hashlib,shutil
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT.parent;HERE=Path(__file__).resolve().parent;OUT=HERE/'out'
OUTPUT=Path(r'C:/Users/yangc/Documents/Codex/2026-10-30/d-lab-lab06b-codex-c01-codex/outputs/EDA_Codex_Current')
sys.path.insert(0,str(HERE))
from rebuild_support import sha,normalized_digest
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
r=load(OUT/'rebuild_results.json');controls=load(OUT/'acceptance_controls.json');browser=load(ROOT/'evidence/browser_checks.json');links=load(ROOT/'evidence/report_checks.json')
assert ROOT.resolve()==Path('C:/EDA_Codex/Lab06b').resolve()
assert r['status']==controls['status']==browser['status']==links['status']=='passed'
assert len(r['builds'])==2 and r['generated_outputs_seeded']==0 and r['two_clean_builds_equivalent']
assert r['physical_function_qualified'] is False and r['foundry_full_signoff'] is False and not r['D_writes']
assert controls['tests']['run']==controls['tests']['passed']==10 and len(controls['controls'])==4 and all(c['passed'] for c in controls['controls'])
assert all(x['unchanged'] and x['files']==33 for x in controls['seed_files_after_build'])
assert browser['m3_s1_acceptance_cases']==26 and browser['m3_s1_truth_cases']==800 and browser['m3_s1_worksheet']
assert browser['m2_s7_replay_cases']==400 and browser['m2_s7_path_cases']==68 and links['html_files']==23
for rel,h in {**r['source_hashes'],**r['reference_hashes'],**controls['source_hashes']}.items():assert sha(ROOT/rel)==h,rel
assert sha(Path(r['external_dependencies']['deck']))==r['external_dependencies']['deck_sha256']
assert sha(Path(r['external_dependencies']['klayout']))==r['external_dependencies']['klayout_sha256']
targets=[]
for b in r['builds']:
    target=Path(b['target']).resolve();assert target.is_relative_to(HERE/'work');targets.append(target)
    assert b['passed'] and len(b['checks'])==13 and all(c['passed'] for c in b['checks'])
    assert b['pre_DRC_before']==2 and b['pre_DRC_after']==0 and b['pre_DRC_categories']==31 and b['metal_nets']==15 and b['optical_connections']==33
    assert b['model_tests']['run']==b['model_tests']['passed']==12 and b['max_abs_numeric_error']==0 and b['candidate_max_abs_rad_error']==0
    assert list(b['replay_counts'].values())==[80,53,80,53,80]
    assert not b['raw_sha_identical'] and b['normalized']['sha256']==b['reference_normalized']['sha256'] and b['normalized']['date_records']==44
    folder=OUT/('build_'+b['build']);assert sha(folder/'b7_rebuilt.gds')==b['raw_sha256'] and normalized_digest(folder/'b7_rebuilt.gds')==b['normalized']
    assert b['geometry']['passed'] and len(b['geometry']['layers'])==8 and all(x['XOR_polygons']==0 and x['text_identical'] for x in b['geometry']['layers'])
    seed=load(folder/'seed_manifest.json');assert seed['generated_outputs_seeded']==0
    for entry in seed['files']:assert sha(target/entry['path'])==entry['sha256']
    for p,h in b['runtime']['external_module_sources'].items():assert sha(Path(p))==h
assert targets[0]!=targets[1] and all(c['returncode']==0 for c in r['commands']) and len(r['commands'])==14
with (ROOT/'delivery/m3_s1_acceptance/checklist.csv').open(encoding='utf-8-sig',newline='') as f:checklist=list(csv.DictReader(f))
assert len(checklist)==26 and all(c['passed']=='True' for c in checklist)
backup=Path(load(HERE/'backup_record.json')['backup']);records=load(backup/'backup_manifest.json')
for row in records:assert sha(backup/row.get('backup_path',row['path']))==row['sha256']
prior=load(backup/'manifest.json')
prior_files=[x for x in prior['files'] if x['path'].startswith(('work/','sources/','reference/C01/')) or x['path'] in ['pic_spec.json','phase_settings.json','config/m2_current_core.json','config/m2_current_chip.json','config/m2_delivery.json'] or x['path'].endswith('.zip')]
for row in prior_files:assert sha(ROOT/row['path'])==row['sha256'],row['path']
for name in ['README.md','manifest.json']:
    dest=backup/'root_files'/name
    if not dest.exists():
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(BASE/name,dest);records.append(dict(scope=str(BASE),path=name,backup_path='root_files/'+name,sha256=sha(dest)))
save(backup/'backup_manifest.json',records)
stamp=datetime.now(timezone(timedelta(hours=8))).isoformat()
index=dict(schema='lab06b.m3_acceptance.v1',step='M3 S1',status='clean_source_rebuild_accepted',source_chip_index='config/m2_current_chip.json',source_delivery_index='config/m2_delivery.json',
    result='work/m3_s1/out/rebuild_results.json',result_sha256=sha(OUT/'rebuild_results.json'),controls='work/m3_s1/out/acceptance_controls.json',controls_sha256=sha(OUT/'acceptance_controls.json'),
    normalized_sha256=r['builds'][0]['normalized']['sha256'],date_records_per_file=44,raw_byte_identical=False,geometry_and_text_identical=True,
    builds=[dict(build=b['build'],gds='work/m3_s1/out/build_'+b['build']+'/b7_rebuilt.gds',sha256=b['raw_sha256'],checks=13,replay_cases=400) for b in r['builds']],
    physical_function_qualified=False,foundry_full_signoff=False,learner_submission='pending',next_step='M3 S2')
save(ROOT/'config/m3_acceptance.json',index)
extra=['scripts/rebuild_all.py','scripts/run_m3_s1.ps1','scripts/render_m3_s1.py','scripts/render_course.py',*['work/m3_s1/'+x for x in ['plot_rebuild.py','prepare_browser_qa.py','browser_qa.cjs','finalize.py']]]
sources={**r['source_hashes'],**controls['source_hashes'],**{p:sha(ROOT/p) for p in extra}}
evidence=dict(timestamp=stamp,step='M3 S1',status='passed',root=str(ROOT),D_writes=False,backup=str(backup),source_hashes=sources,source_hashes_verified=True,prior_files_verified=len(prior_files),
    acceptance_index=index,clean_builds=2,generated_outputs_seeded=0,accepted_checks=26,model_tests_run=24,support_tests=controls['tests'],controls=controls['controls'],
    seed_files_after_build=controls['seed_files_after_build'],reference_hashes=r['reference_hashes'],external_dependencies=r['external_dependencies'],
    pre_DRC_each='2 -> 0, 31 categories',metal_nets_each=15,optical_connections_each=33,all_layer_XOR_polygons=0,text_identical=True,
    raw_byte_identical=False,timestamp_only_normalized_sha256=index['normalized_sha256'],date_records_per_GDS=44,case_comparisons_each=400,maximum_numeric_error=0,
    browser_acceptance_cases=26,browser_truth_cases=800,worksheet_verified=True,html_files=links['html_files'],local_links=links['local_links_checked'],
    old_chip_and_handoff_unchanged=True,physical_function_qualified=False,foundry_full_signoff=False,learner_submission='pending',scope=r['scope'],next_step='M3 S2')
save(ROOT/'evidence/m3_s1_verification.json',evidence)
prov=load(ROOT/'evidence/provenance.json');prov['m3_s1']=evidence
prov['current_execution_scope']='C:/EDA_Codex/Lab06b: M0/M1, M2 S1-S7, M3 S1. Two empty source/design-input trees rebuild core, EC/PAD/GND, label fix, full installed pre-DRC/geometric graph, paths and replay. Raw GDS bytes differ; only date-normalized SHA and all-layer XOR/text match accepted S6. Each 400-case model comparison has zero numerical difference. Preinstalled licensed tools; no FEM/FDTD re-solve or physical/foundry qualification. D read-only.'
save(ROOT/'evidence/provenance.json',prov)
log=ROOT/'history/CHANGELOG.md';text=log.read_text(encoding='utf-8')
if '## 2026-10-31 M3 S1' not in text:
    with log.open('a',encoding='utf-8') as f:f.write('\n## 2026-10-31 M3 S1\n'
        '- 僅在 C:\\EDA_Codex 工作；D 槽唯讀。M1／M2 交接 ZIP、原始相位與 S6 晶片採用索引不變。\n'
        '- 新增 scripts/rebuild_all.py 與 run_m3_s1.ps1；兩個空目錄各放 33 個來源／設計／工具位置設定檔，未複製 GDS、舊 sidecar、out 或 ZIP。\n'
        '- 重新生成邏輯交接表、PDK core、EC／PAD／GND、標籤修正版、全套原始 pre-DRC／幾何接線、68 路徑與功能重播；每輪 13 條件通過。\n'
        '- 原始 GDS SHA 因 44 筆日期記錄不同而不相同；只統一 BGNLIB／BGNSTR 日期 payload 後，三者其餘位元相同；八層 XOR 全空／文字相同，三份接口 CSV 位元相同。\n'
        '- 每輪原始基準 80/80，五情境 400 筆與 S7 差為 0；線長原設定 53/80，解析模型候選 80/80。兩輪共 24 項模型測試，另 10 項輔助測試與 4 種控制通過。\n'
        '- 23 HTML／1130 本機連結與兩輪 800 筆功能／26 驗收互動核對通過；學員作答待講師驗收。\n'
        '- 使用預先安裝工具／授權及作者設計輸入；未重解 FEM/FDTD、安裝新環境或完成 foundry／EC／MMI／熱電校準。下一步 M3 S2 獨立幾何量測與交叉驗證。\n')
p=BASE/'README.md';text=p.read_text(encoding='utf-8').replace('目前教材與核心實驗：M0、M1 全步及 M2 S1～S7；','目前教材與核心實驗：M0、M1 全步、M2 S1～S7 及 M3 S1；').replace('scripts/run_m2_s7.ps1','scripts/run_m3_s1.ps1')
text=text.replace('下一步：M3 S1，從零重建與驗收。','M3 S1：scripts/rebuild_all.py；兩個空目錄從來源／設計輸入重建，各 13 項條件與 400 筆比較通過。\n原始 GDS SHA 因日期不同而不相同；僅統一日期後 SHA、全圖層 XOR／文字與接口一致。\n驗收索引：Lab06b/config/m3_acceptance.json；本輪沒有建立新的物理功能或 foundry 資格。\n下一步：M3 S2，獨立幾何量測與交叉驗證。');p.write_text(text,encoding='utf-8')
omitted={'tools','history','__pycache__','.matplotlib','controlled_cases','test_temp'};files=[]
for directory,dirs,names in os.walk(ROOT):
    directory=Path(directory);dirs[:]=[x for x in dirs if x not in omitted and not x.startswith('browser-profile') and not (x=='work' and directory!=ROOT)]
    for name in names:
        p=directory/name
        if p==ROOT/'manifest.json' or p.suffix=='.pyc':continue
        files.append(dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
manifest=dict(root=str(ROOT),current_step='M3 S1',policy='C-only work; D read-only',scope='course, source, accepted chip, two clean rebuild outputs and evidence; tools, history, nested scratch excluded',files=sorted(files,key=lambda x:x['path']));save(ROOT/'manifest.json',manifest)
save(BASE/'manifest.json',dict(root=str(BASE),project='Lab06b',current_step='M3 S1',root_files=[dict(path=p,sha256=sha(BASE/p)) for p in ['AGENTS.md','EDA_paths.json','Lab06b_index.html','README.md','Lab06b/manifest.json']],verification='Lab06b/evidence/m3_s1_verification.json',D_restore='migration_archive/d_restore_result.json'))
ignore=shutil.ignore_patterns('__pycache__','*.pyc','.matplotlib','browser-profile*','work','controlled_cases','test_temp')
for folder in ['assets','course','analysis','config','scripts','evidence','learner','reference','delivery']:
    shutil.copytree(ROOT/folder,OUTPUT/'Lab06b'/folder,dirs_exist_ok=True,ignore=ignore)
for folder in ['common','m0_s1','m0_s2','m0_s3','m1_s1','m1_s2','m1_s3','m1_s4','m1_s5','m2_s1','m2_s2','m2_s3','m2_s4','m2_s5','m2_s6','m2_s7','m3_s1']:
    shutil.copytree(ROOT/'work'/folder,OUTPUT/'Lab06b/work'/folder,dirs_exist_ok=True,ignore=ignore)
for name in ['Lab06b_index.html','EDA_paths.json','README_Lab06b_Course.md','pic_spec.json','phase_settings.json','manifest.json']:shutil.copy2(ROOT/name,OUTPUT/'Lab06b'/name)
for name in ['AGENTS.md','EDA_paths.json','Lab06b_index.html','README.md','manifest.json']:shutil.copy2(BASE/name,OUTPUT/name)
for row in files:
    p=OUTPUT/'Lab06b'/row['path'];assert p.is_file() and sha(p)==row['sha256'],row['path']
print(json.dumps(dict(status='passed',step='M3 S1',files_verified=len(files),prior_files_verified=len(prior_files),clean_builds=2,checks=26,model_tests=24,support_tests=10,controls=4,browser_truth_cases=800,D_writes=False,raw_byte_identical=False,normalized_GDS_identical=True,physical_function_qualified=False,next_step='M3 S2',review_copy=str(OUTPUT/'Lab06b/course/m3_s1.html')),ensure_ascii=False,indent=2))
