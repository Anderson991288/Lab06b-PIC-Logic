"""Verify S7 delivery provenance, preserve previous stages, export reading copy."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import os,json,hashlib,shutil,zipfile,importlib.util
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT.parent;HERE=Path(__file__).resolve().parent
OUTPUT=Path(r'C:/Users/yangc/Documents/Codex/2026-10-30/d-lab-lab06b-codex-c01-codex/outputs/EDA_Codex_Current')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
assert ROOT.resolve()==Path('C:/EDA_Codex/Lab06b').resolve()
r=load(HERE/'out/replay_results.json');d=load(HERE/'out/delivery_results.json');reg=load(HERE/'out/regression.json')
b=load(ROOT/'evidence/browser_checks.json');links=load(ROOT/'evidence/report_checks.json')
assert r['core_passed'] and all(c['passed'] for c in r['checks']) and r['unit_tests']['run']==r['unit_tests']['passed']==12
assert [c['passed'] for c in r['cases'].values()]==[80,53,80,53,80]
assert r['complex_gauge_error']<1e-9 and not r['physical_function_qualified']
assert all(x['frozen_candidate_passed']==80 for x in r['sensitivity']) and len(r['sensitivity'])==7
assert sum(x['passed'] for x in reg['regression'].values())==144 and all(x['successful'] for x in reg['regression'].values())
assert reg['M1_sources_and_zip_unchanged'] and reg['M1_baseline_replay_passed']==80
assert d['status']==d['portable_replay']['status']==d['portable_geometry']['status']=='passed'
assert d['portable_geometry']['pre_DRC_records']==0 and d['portable_geometry']['metal_nets']==15 and d['portable_geometry']['optical_connections']==33
assert len(d['tamper_controls'])==4 and all(x['rejected'] for x in d['tamper_controls'])
assert d['files']==50 and not d['physical_function_qualified'] and not d['portable_geometry']['foundry_full_signoff']
assert b['status']==links['status']=='passed' and b['m2_s7_replay_cases']==400 and b['m2_s7_path_cases']==68 and b['m2_s7_worksheet']
assert links['html_files']==22
for rel,h in {**r['source_hashes'],**d['source_hashes']}.items():assert sha(ROOT/rel)==h,rel
zipfile_path=ROOT/d['zip'];assert sha(zipfile_path)==d['zip_sha256']
with zipfile.ZipFile(zipfile_path) as archive:
    assert archive.testzip() is None
    manifest=load(ROOT/d['delivery']/'manifest.json')
    assert set(archive.namelist())=={'m2_pic_delivery/'+x['path'] for x in manifest['files']}|{'m2_pic_delivery/manifest.json'}
    for entry in manifest['files']:assert hashlib.sha256(archive.read('m2_pic_delivery/'+entry['path'])).hexdigest()==entry['sha256']
spec=importlib.util.spec_from_file_location('verify_s7_delivery',HERE/'verify_delivery.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
integrity=module.verify(ROOT/d['delivery']);assert integrity['files']==50
assert sha(ROOT/d['delivery']/'manifest.json')==d['manifest_sha256']
current=load(ROOT/'config/m2_current_chip.json');assert current['accepted_at_step']=='M2 S6'
for rel,h in current['files'].items():assert sha(ROOT/rel)==h,rel
assert sha(ROOT/'work/m2_s6/out/after/b7_ec_pad.gds')==sha(ROOT/d['delivery']/'layout/B7_final.gds')==d['gds_sha256']==r['gds_sha256']
previous=load(ROOT/'work/m1_s5/out/handoff_results.json')
for rel,h in previous['source_hashes'].items():assert sha(ROOT/rel)==h,rel
assert sha(ROOT/previous['zip'])==previous['zip_sha256']
backup=Path(load(HERE/'backup_record.json')['backup']);records=load(backup/'backup_manifest.json')
for row in records:assert sha(backup/row.get('backup_path',row['path']))==row['sha256']
prior=load(backup/'manifest.json')
prior_files=[x for x in prior['files'] if x['path'].startswith(('work/common/','work/m0_','work/m1_','work/m2_')) or x['path'] in ['config/m2_current_core.json','config/m2_current_chip.json']]
for row in prior_files:assert sha(ROOT/row['path'])==row['sha256'],row['path']
for name in ['README.md','manifest.json']:
    dest=backup/'root_files'/name
    if not dest.exists():
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(BASE/name,dest)
        records.append(dict(scope=str(BASE),path=name,backup_path='root_files/'+name,sha256=sha(dest)))
save(backup/'backup_manifest.json',records)
stamp=datetime.now(timezone(timedelta(hours=8))).isoformat()
delivery_index=dict(schema='lab06b.m2_delivery.v1',step='M2 S7',kind='teaching_design_review_and_model_replay',source_chip_index='config/m2_current_chip.json',source_chip_step='M2 S6',
    zip=Path(d['zip']).as_posix(),zip_sha256=d['zip_sha256'],manifest=(Path(d['delivery'])/'manifest.json').as_posix(),manifest_sha256=d['manifest_sha256'],gds_sha256=d['gds_sha256'],
    model='config/m2_backannotation.json',model_sha256=sha(ROOT/'config/m2_backannotation.json'),candidate='work/m2_s7/out/phase_settings_backannotated.json',
    candidate_sha256=sha(HERE/'out/phase_settings_backannotated.json'),reference_plane='M1_core_ports',physical_function_qualified=False,foundry_full_signoff=False,
    limitations=r['model']['excluded'],next_step='M3 S1')
save(ROOT/'config/m2_delivery.json',delivery_index)
extra=['scripts/run_m2_s7.ps1','scripts/render_m2_s7.py','scripts/render_course.py','work/m2_s7/plot_delivery.py','work/m2_s7/render_final_gds.py','work/m2_s7/browser_qa.cjs','work/m2_s7/prepare_browser_qa.py','work/m2_s7/finalize.py']
sources={**r['source_hashes'],**d['source_hashes'],**{p:sha(ROOT/p) for p in extra}}
evidence=dict(timestamp=stamp,step='M2 S7',status='passed',root=str(ROOT),D_writes=False,backup=str(backup),
    source_hashes=sources,source_hashes_verified=True,prior_files_verified=len(prior_files),current_chip_unchanged=True,M1_sources_and_zip_unchanged=True,
    delivery_index=delivery_index,files=50,zip_CRC_and_member_hashes_verified=True,integrity=integrity,portable_replay=d['portable_replay'],portable_geometry=d['portable_geometry'],
    tamper_controls=d['tamper_controls'],model_tests=r['unit_tests'],regression=reg['regression'],replay_counts={k:v['passed'] for k,v in r['cases'].items()},
    core_paths=58,fan_paths=10,gds_connections=33,complex_gauge_error=r['complex_gauge_error'],sensitivity=r['sensitivity'],
    browser_replay_cases=400,browser_path_cases=68,worksheet_verified=True,html_files=links['html_files'],local_links=links['local_links_checked'],
    learner_submission='pending',physical_function_qualified=False,foundry_full_signoff=False,scope=r['scope'],next_step='M3 S1')
save(ROOT/'evidence/m2_s7_verification.json',evidence)
prov=load(ROOT/'evidence/provenance.json');prov['m2_s7']=evidence
prov['current_execution_scope']='C:/EDA_Codex/Lab06b: M0/M1 and M2 S1-S7. S6 GDS unchanged; package integrity/400-case uniform-neff core-plane model replay and external pre-DRC/geometric check passed after relocation. Raw length original 53/80; separate analytic model candidate 80/80. No calibrated chip function, EC/MMI/heater response, optical PEX or foundry signoff. D read-only.'
save(ROOT/'evidence/provenance.json',prov)
log=ROOT/'history/CHANGELOG.md';text=log.read_text(encoding='utf-8')
if '## 2026-10-31 M2 S7' not in text:
    with log.open('a',encoding='utf-8') as f:f.write('\n## 2026-10-31 M2 S7\n'
        '- 僅在 C:\\EDA_Codex 工作；D 槽唯讀。S6 晶片 GDS 與採用索引不變；新建 config/m2_delivery.json。\n'
        '- 58 core＋10 fan 中心線重算，對照實際 GDS 的 33 條 MMI 外連接；名義線長不是校準光學 PEX。\n'
        '- λ=1.55 µm、M0 FEM n_eff=2.353499831254645、保留預設 H，core 參考面模型：理想 80/80→原相位線長 53/80→解析候選 80/80。候選另存，未覆寫原相位或推定電壓。\n'
        '- 3 dB/cm 教學損耗與七點凍結候選折射率擾動；保留 signed margin、完整複數矩陣與 400 筆結果。\n'
        '- 12 項模型測試、144 項既有回歸通過，M1 原始交接 ZIP 不變。\n'
        '- 50 檔案封裝與 SHA 清單；搬到中文／空白路徑的新程序重播一致，外部完整現有 pre-DRC 為 0、15 金屬網與 33 光路一致。四種隔離竄改／缺漏均被抓到。\n'
        '- 22 HTML、400 筆與 68 段互動、學員記錄及桌面／手機顯示核對通過。\n'
        '- foundry、EC、MMI 絕對相位、熱電／偏壓與實體功能仍待驗證；下一步 M3 S1 從零重建與驗收。\n')
p=BASE/'README.md';text=p.read_text(encoding='utf-8').replace('目前教材與核心實驗：M0、M1 全步及 M2 S1～S6；','目前教材與核心實驗：M0、M1 全步及 M2 S1～S7；').replace('scripts/run_m2_s6.ps1','scripts/run_m2_s7.ps1')
text=text.replace('下一步：M2 S7，交付封裝、路徑回註與重播。','M2 S7：Lab06b/delivery/Lab06b_M2_PIC_delivery.zip；50 檔案，中文／空白路徑搬移重播與 pre-DRC／幾何重查通過。\n線長 core 模型：理想 80/80→原設定 53/80→另存解析候選 80/80；候選非 heater 電壓，實體功能資格未驗證。\n交付索引：Lab06b/config/m2_delivery.json；S6 晶片採用索引與 GDS 未變。\n下一步：M3 S1，從零重建與驗收。');p.write_text(text,encoding='utf-8')
omitted={'tools','history','__pycache__','.matplotlib','controlled_cases','test_temp'};files=[]
for directory,dirs,names in os.walk(ROOT):
    directory=Path(directory);dirs[:]=[x for x in dirs if x not in omitted and not x.startswith('browser-profile') and not (x=='work' and directory!=ROOT)]
    for name in names:
        p=directory/name
        if p==ROOT/'manifest.json' or p.suffix=='.pyc':continue
        files.append(dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
manifest=dict(root=str(ROOT),current_step='M2 S7',policy='C-only work; D read-only',scope='course, authored sources, GDS, model replay, delivery and verification evidence; vendor tools, history and nested scratch excluded',files=sorted(files,key=lambda x:x['path']))
save(ROOT/'manifest.json',manifest)
save(BASE/'manifest.json',dict(root=str(BASE),project='Lab06b',current_step='M2 S7',root_files=[dict(path=p,sha256=sha(BASE/p)) for p in ['AGENTS.md','EDA_paths.json','Lab06b_index.html','README.md','Lab06b/manifest.json']],verification='Lab06b/evidence/m2_s7_verification.json',D_restore='migration_archive/d_restore_result.json'))
ignore=shutil.ignore_patterns('__pycache__','*.pyc','.matplotlib','browser-profile*','work','controlled_cases','test_temp')
for folder in ['assets','course','analysis','config','scripts','evidence','learner','reference','delivery']:
    shutil.copytree(ROOT/folder,OUTPUT/'Lab06b'/folder,dirs_exist_ok=True,ignore=ignore)
for folder in ['common','m0_s1','m0_s2','m0_s3','m1_s1','m1_s2','m1_s3','m1_s4','m1_s5','m2_s1','m2_s2','m2_s3','m2_s4','m2_s5','m2_s6','m2_s7']:
    shutil.copytree(ROOT/'work'/folder,OUTPUT/'Lab06b/work'/folder,dirs_exist_ok=True,ignore=ignore)
for name in ['Lab06b_index.html','EDA_paths.json','README_Lab06b_Course.md','pic_spec.json','phase_settings.json','manifest.json']:shutil.copy2(ROOT/name,OUTPUT/'Lab06b'/name)
for name in ['AGENTS.md','EDA_paths.json','Lab06b_index.html','README.md','manifest.json']:shutil.copy2(BASE/name,OUTPUT/name)
for row in manifest['files']:
    p=OUTPUT/'Lab06b'/row['path'];assert p.is_file() and sha(p)==row['sha256'],row['path']
print(json.dumps(dict(status='passed',step='M2 S7',root=str(ROOT),files_verified=len(files),prior_files_verified=len(prior_files),delivery_files=50,old_tests=144,new_tests=12,browser_cases=400,browser_paths=68,D_writes=False,physical_function_qualified=False,next_step='M3 S1',review_copy=str(OUTPUT/'Lab06b/course/m2_s7.html')),ensure_ascii=False,indent=2))
