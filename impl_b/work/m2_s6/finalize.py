"""Verify S6 provenance, preserve prior work and refresh the reading mirror."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import os,json,hashlib,shutil,csv
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT.parent
OUTPUT=Path(r'C:/Users/yangc/Documents/Codex/2026-10-30/d-lab-lab06b-codex-c01-codex/outputs/EDA_Codex_Current')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
r=load(ROOT/'work/m2_s6/out/verification_results.json');browser=load(ROOT/'evidence/browser_checks.json');links=load(ROOT/'evidence/report_checks.json')
assert ROOT.resolve()==Path('C:/EDA_Codex/Lab06b').resolve()
assert r['core_passed'] and r['before']['total_records']==2 and r['after']['total_records']==0
assert r['before']['category_count']==r['after']['category_count']==31 and sum(v['passed'] for v in r['regression'].values())==144
assert all(c['passed'] for c in r['checks']) and all(v['passed'] for v in r['connectivity'].values())
assert r['foundry_full_signoff'] is False and r['formal_foundry_LVS'] is False and r['optical_mode_phase_verified'] is False
assert r['M1_sources_and_zip_unchanged'] and r['M1_baseline_replay_passed']==80
assert browser['status']==links['status']=='passed' and browser['m2_s6_route_cases']==33 and browser['m2_s6_control_cases']==10 and browser['m2_s6_worksheet']
for rel,digest in r['source_hashes'].items():assert sha(ROOT/rel)==digest,rel
current=load(ROOT/'config/m2_current_chip.json');assert current['accepted_at_step']=='M2 S6' and current['m1_spec_sha256']==sha(ROOT/'pic_spec.json')
for rel,digest in current['files'].items():assert (ROOT/rel).resolve().is_relative_to(ROOT) and sha(ROOT/rel)==digest,rel
assert sha(ROOT/'work/m2_s6/out/after/b7_ec_pad.gds')==r['gds_sha256']==r['after']['gds_sha256']==r['connectivity']['after']['gds_sha256']
assert sha(ROOT/'work/m2_s6/out/before/b7_ec_pad.gds')==sha(ROOT/'work/m2_s5/out/b7_ec_pad.gds')==r['before']['gds_sha256']
assert all(p['identical'] for p in r['label_patch']['physical_mask_comparison']) and r['label_patch']['only_port_label_windows_changed']
assert len(rows(ROOT/'work/m2_s6/out/violations_before.csv'))==2 and not rows(ROOT/'work/m2_s6/out/violations_after.csv')
assert len(rows(ROOT/'work/m2_s6/out/rule_comparison.csv'))==31
assert len(rows(ROOT/'work/m2_s6/out/optical_connections.csv'))==33 and all(p['observed_match']=='True' for p in rows(ROOT/'work/m2_s6/out/optical_connections.csv'))
assert len(rows(ROOT/'work/m2_s6/out/electrical_connections.csv'))==14 and all(p['passed']=='True' for p in rows(ROOT/'work/m2_s6/out/electrical_connections.csv'))
for fault in r['negative_controls']:
    assert fault['detected'] and sha(ROOT/fault['path'])==fault['sha256']
    assert (ROOT/fault['report']).is_file()
assert sum(c['drc_records']==0 and c['target']!='drc' for c in r['negative_controls'])==4
previous=load(ROOT/'work/m1_s5/out/handoff_results.json')
for rel,digest in previous['source_hashes'].items():assert sha(ROOT/rel)==digest,rel
assert sha(ROOT/previous['zip'])==previous['zip_sha256']
backup=Path(load(ROOT/'work/m2_s6/backup_record.json')['backup']);records=load(backup/'backup_manifest.json')
for row in records:assert sha(backup/row.get('backup_path',row['path']))==row['sha256']
prior=load(backup/'manifest.json')
prior_files=[row for row in prior['files'] if row['path'].startswith(('work/m2_s2/','work/m2_s3/','work/m2_s4/','work/m2_s5/')) or row['path'] in ['config/m2_current_core.json','work/common/core_layout.py','work/common/chip_interfaces.py']]
for row in prior_files:assert sha(ROOT/row['path'])==row['sha256'],row['path']
for name in ['README.md','manifest.json']:
    dest=backup/'root_files'/name;assert not dest.exists();dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(BASE/name,dest);assert sha(dest)==sha(BASE/name)
    records.append(dict(scope=str(BASE),path=name,backup_path='root_files/'+name,sha256=sha(dest)))
save(backup/'backup_manifest.json',records)
stamp=datetime.now(timezone(timedelta(hours=8))).isoformat()
extra=['scripts/run_m2_s6.ps1','scripts/render_m2_s6.py','scripts/render_course.py','work/m2_s6/render_evidence.py','work/m2_s6/plot_verification.py','work/m2_s6/browser_qa.cjs']
sources={**r['source_hashes'],**{p:sha(ROOT/p) for p in extra}}
save(ROOT/'evidence/m2_s6_verification.json',dict(timestamp=stamp,step='M2 S6',status='passed',root=str(ROOT),D_writes=False,
    original_pre_DRC_categories=31,violations_before=2,violations_after=0,regression=r['regression'],checks=r['checks'],
    metal_nets=15,heater_branches=14,optical_route_pairs=33,optical_terminals=66,negative_controls_detected=8,DRC_zero_but_wrong_connectivity_controls=4,
    current_chip=current,source_hashes=sources,source_hashes_verified=True,prior_files_verified=len(prior_files),
    M1_sources_and_zip_unchanged=True,M1_baseline_replay_passed=80,physical_layers_unchanged=True,
    browser_route_cases=33,browser_control_cases=10,worksheet_verified=True,html_files=links['html_files'],local_links=links['local_links_checked'],
    backup=str(backup),learner_submission='pending',foundry_full_signoff=False,formal_foundry_LVS=False,optical_mode_phase_verified=False,scope=r['scope'],next_step='M2 S7'))
prov=load(ROOT/'evidence/provenance.json')
prov['m2_s6']=dict(timestamp=stamp,current_execution_root=str(ROOT),result='work/m2_s6/out/verification_results.json',
    current_chip_index='config/m2_current_chip.json',original_deck_sha256=r['after']['deck_sha256'],categories=31,declared_size_um=r['after']['declared_size_um'],
    records_before=2,records_after=0,physical_layers_unchanged=True,geometric_metal_nets=15,heater_branches=14,geometric_optical_routes=33,
    negative_controls=8,regression_passed=144,M1_sources_and_zip_unchanged=True,source_hashes=sources,
    limitations=r['scope'],learner_submission='pending',references=['https://www.klayout.org/downloads/master/doc-qt5/manual/drc_basic.html','https://www.klayout.de/doc/manual/lvs_overview.html'])
prov['current_execution_scope']='C:/EDA_Codex/Lab06b: M0/M1, M2 S1-S6. Entire installed unchanged CORNERSTONE pre-DRC at declared custom area, two real text markers corrected to zero; geometric electrical and MMI-black-box optical netlist compared, eight real GDS controls. No foundry full signoff or EC/thermal/phase qualification. D read-only.'
save(ROOT/'evidence/provenance.json',prov)
with (ROOT/'history/CHANGELOG.md').open('a',encoding='utf-8') as f:
    f.write('\n## 2026-10-31 M2 S6\n'
            '- 僅在 C:\\EDA_Codex 工作；D 槽沒有寫入。\n'
            '- 執行完整已安裝 CORNERSTONE v3.1 pre-DRC 原始 deck，31 個報告類別；宣告課程設計區 3860×1640 µm，未宣稱 MPW 配額或 foundry 全簽核。\n'
            '- 實際發現 in0／out0 的兩筆 GDS100 gap marker；十個埠標籤 4→5 µm，同 deck 重跑 2→0。六個實體圖層 XOR 不變，原 S5 檔案保留。\n'
            '- 15 金屬網／14 個 heater 支路對照一致；以 14 MMI 黑盒從實際材料抽取 66 端點／33 連接，與 B7 宣告網表比對一致。\n'
            '- 八種真實錯誤 GDS 被對應檢查抓到；四種短路／斷口／跨接在 DRC=0 時仍被網表比對判定失敗。\n'
            '- 144 項既有回歸通過；M1 80/80 為不變基準，未列為物理相位回註驗收。\n'
            '- 保存前後 GDS／原始 .lyrdb、31 類比較、違規／修正記錄、光電接線表與負例資料；目前晶片索引更新至 S6。\n'
            '- 21 份 HTML、1010 個連結、33 組光路及 10 個正式／負例判讀瀏覽器核對通過。\n'
            '- foundry full DRC／專用 LVS、EC 模式／響應、熱電校正與路徑相位重播仍待驗證；下一步 M2 S7。\n')
p=BASE/'README.md';text=p.read_text(encoding='utf-8').replace('目前教材與核心實驗：M0、M1 全步及 M2 S1～S5；','目前教材與核心實驗：M0、M1 全步及 M2 S1～S6；').replace('scripts/run_m2_s5.ps1','scripts/run_m2_s6.ps1')
text=text.replace('下一步：M2 S6，完整規則／連通檢查與違規記錄。','M2 S6：全套現有 pre-DRC 原始 deck 2→0；15 金屬網／33 光路幾何網表比對通過，目前晶片索引已更新至 S6。\n只改埠標籤，六個實體圖層不變；foundry 簽核與 EC／熱電／光學相位資格邊界維持明示。\n下一步：M2 S7，交付封裝、路徑回註與重播。');p.write_text(text,encoding='utf-8')
omitted={'tools','history','__pycache__','.matplotlib','controlled_cases','test_temp'};files=[]
for directory,dirs,names in os.walk(ROOT):
    directory=Path(directory);dirs[:]=[d for d in dirs if d not in omitted and not d.startswith('browser-profile') and not (d=='work' and directory!=ROOT)]
    for name in names:
        path=directory/name
        if path==ROOT/'manifest.json' or path.suffix=='.pyc':continue
        files.append(dict(path=path.relative_to(ROOT).as_posix(),bytes=path.stat().st_size,sha256=sha(path)))
manifest=dict(root=str(ROOT),current_step='M2 S6',policy='C-only work; D read-only',scope='course, models, handoff, chip GDS, pre-DRC and geometric netlist evidence; vendor tools and temporary/controlled GDS copies excluded',files=sorted(files,key=lambda r:r['path']))
save(ROOT/'manifest.json',manifest)
save(BASE/'manifest.json',dict(root=str(BASE),project='Lab06b',current_step='M2 S6',
    root_files=[dict(path=rel,sha256=sha(BASE/rel)) for rel in ['AGENTS.md','EDA_paths.json','Lab06b_index.html','README.md','Lab06b/manifest.json']],
    verification='Lab06b/evidence/m2_s6_verification.json',D_restore='migration_archive/d_restore_result.json'))
ignore=shutil.ignore_patterns('__pycache__','*.pyc','.matplotlib','browser-profile*','work','controlled_cases','test_temp')
for folder in ['course','analysis','config','scripts','evidence','learner','reference','delivery']:
    shutil.copytree(ROOT/folder,OUTPUT/'Lab06b'/folder,dirs_exist_ok=True,ignore=ignore)
for folder in ['common','m0_s1','m0_s2','m0_s3','m1_s1','m1_s2','m1_s3','m1_s4','m1_s5','m2_s1','m2_s2','m2_s3','m2_s4','m2_s5','m2_s6']:
    shutil.copytree(ROOT/'work'/folder,OUTPUT/'Lab06b/work'/folder,dirs_exist_ok=True,ignore=ignore)
for name in ['Lab06b_index.html','EDA_paths.json','README_Lab06b_Course.md','pic_spec.json','phase_settings.json','manifest.json']:shutil.copy2(ROOT/name,OUTPUT/'Lab06b'/name)
for name in ['AGENTS.md','EDA_paths.json','Lab06b_index.html','README.md','manifest.json']:shutil.copy2(BASE/name,OUTPUT/name)
copied=0
for row in manifest['files']:
    p=OUTPUT/'Lab06b'/row['path']
    if p.is_file():assert sha(p)==row['sha256'],row['path'];copied+=1
print(json.dumps(dict(status='passed',step='M2 S6',root=str(ROOT),pre_DRC='2 -> 0',metal_nets=15,optical_route_pairs=33,controls=8,regression=144,
    prior_files_verified=len(prior_files),review_files_verified=copied,M1_unchanged=True,physical_layers_unchanged=True,D_writes=False,foundry_full_signoff=False,next_step='M2 S7',
    review_copy=str(OUTPUT/'Lab06b/course/m2_s6.html')),ensure_ascii=False,indent=2))
