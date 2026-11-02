"""Pin independent checks, preserve accepted work and export final course mirror."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import os,json,csv,hashlib,shutil,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT.parent;HERE=Path(__file__).resolve().parent;OUT=HERE/'out'
OUTPUT=Path(r'C:/Users/yangc/Documents/Codex/2026-10-30/d-lab-lab06b-codex-c01-codex/outputs/EDA_Codex_Current')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
assert ROOT.resolve()==Path('C:/EDA_Codex/Lab06b').resolve()
r=load(OUT/'crosscheck_results.json');b=load(ROOT/'evidence/browser_checks.json');links=load(ROOT/'evidence/report_checks.json');cfg=load(ROOT/'config/course.json')
assert r['status']==b['status']==links['status']=='passed' and all(c['passed'] for c in r['checks'])
assert len(r['comparison'])==6 and r['rule_comparisons']==54 and all(x['numeric_agreement'] and x['rule_agreement'] for x in r['comparison'])
assert [round(x['independent_um'],6) for x in r['comparison']]==[.35,.53,.9,50,8,13.5]
assert r['tests']['run']==r['tests']['passed']==12 and r['tests']['successful']
assert len(r['controls'])==8 and all(x['passed'] for x in r['controls']) and sum(not x['expected_rule_passed'] for x in r['controls'])==7
assert r['pre_DRC_records']==0 and r['pre_DRC_categories']==31
assert not ET.parse(OUT/'pre_drc.lyrdb').findall('.//items/item') and len(ET.parse(OUT/'pre_drc.lyrdb').findall('.//categories/category'))==31
assert r['physical_function_qualified'] is False and r['foundry_full_signoff'] is False and not r['D_writes']
assert r['method_difference']['strict_connector_only_um']>1.5 and abs(r['method_difference']['corrected_um']-.53)<1e-9
assert b['m3_s2_geometry_cases']==54 and b['m3_s2_method_cases']==2 and b['m3_s2_worksheet'] and b['m3_s1_truth_cases']==800
assert links['html_files']==24
for rel,h in r['source_hashes'].items():assert sha(ROOT/rel)==h,rel
current=load(ROOT/'config/m2_current_chip.json');assert current['accepted_at_step']=='M2 S6'
for rel,h in current['files'].items():assert sha(ROOT/rel)==h
gds=next(ROOT/p for p in current['files'] if p.endswith('.gds'));assert sha(gds)==r['gds_sha256']
tools=load(ROOT/'EDA_paths.json')['windows'];assert sha(ROOT/tools['drc_deck'])==r['deck_sha256']
independent=load(OUT/'independent_results.json');native=load(OUT/'klayout_results.json');cases=load(OUT/'case_inventory.json');control_files={}
for x,y,c in zip(independent,native,cases):
    assert x['id']==y['id']==c['id'] and x['gds_sha256']==y['gds_sha256']==c['sha256']==sha(Path(c['gds']))
    if c['id']!='accepted':
        rel='delivery/m3_s2_crosscheck/controls/'+c['id']+'.gds';assert sha(ROOT/rel)==c['sha256'];control_files[rel]=c['sha256']
with (OUT/'comparison_54.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
assert len(rows)==54 and all(x['rule_agreement']=='True' for x in rows)
assert sha(OUT/'comparison_54.csv')==sha(ROOT/'delivery/m3_s2_crosscheck/comparison_54.csv')
backup=Path(load(HERE/'backup_record.json')['backup']);records=load(backup/'backup_manifest.json')
for row in records:assert sha(backup/row.get('backup_path',row['path']))==row['sha256']
prior=load(backup/'manifest.json');prior_files=[x for x in prior['files'] if x['path'].startswith(('work/','sources/','reference/C01/')) or x['path'] in ['pic_spec.json','phase_settings.json','config/m2_current_core.json','config/m2_current_chip.json','config/m2_delivery.json','config/m3_acceptance.json'] or x['path'].endswith('.zip')]
for row in prior_files:assert sha(ROOT/row['path'])==row['sha256'],row['path']
for name in ['README.md','manifest.json']:
    dest=backup/'root_files'/name
    if not dest.exists():
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(BASE/name,dest);records.append(dict(scope=str(BASE),path=name,backup_path='root_files/'+name,sha256=sha(dest)))
save(backup/'backup_manifest.json',records)
stamp=datetime.now(timezone(timedelta(hours=8))).isoformat()
index=dict(schema='lab06b.independent_geometry_result.v1',step='M3 S2',status='selected_independent_geometry_crosscheck_passed',source_chip_index='config/m2_current_chip.json',gds_sha256=r['gds_sha256'],
    result='work/m3_s2/out/crosscheck_results.json',result_sha256=sha(OUT/'crosscheck_results.json'),comparison='delivery/m3_s2_crosscheck/comparison_54.csv',comparison_sha256=sha(OUT/'comparison_54.csv'),
    selected_measurements=6,rule_comparisons=54,GDS_controls=8,tests=12,original_pre_DRC_records=0,original_pre_DRC_categories=31,control_files=control_files,
    physical_function_qualified=False,foundry_full_signoff=False,learner_submission='pending',scope=r['scope'])
save(ROOT/'config/m3_crosscheck_result.json',index)
progress={k:v for k,v in cfg['progress'].items() if k.startswith(('M0_','M1_','M2_','M3_'))};assert len(progress)==17
closeout=dict(schema='lab06b.course_closeout.v1',status='17_teaching_steps_implemented',timestamp=stamp,steps=17,hours=18,progress=progress,
    final_lesson='course/m3_s2.html',chip_index='config/m2_current_chip.json',M2_delivery_index='config/m2_delivery.json',rebuild_acceptance_index='config/m3_acceptance.json',geometry_crosscheck_index='config/m3_crosscheck_result.json',
    learner_submission='pending',instructor_review='pending',physical_function_qualified=False,foundry_full_signoff=False,
    remaining=['Learner independent observations, modifications, reruns and full delivery; instructor review','M0 Meep FDTD was not rerun','Calibrated EC/MMI/waveguide/bend response and heater electrical/thermal/common-ground calibration','Foundry full signoff, process-qualified LVS and packaging/measurement acceptance'])
save(ROOT/'config/course_closeout.json',closeout)
extra=['scripts/run_m3_s2.ps1','scripts/render_m3_s2.py','scripts/render_course.py',*['work/m3_s2/'+n for n in ['plot_crosscheck.py','prepare_browser_qa.py','browser_qa.cjs','finalize.py']]]
sources={**r['source_hashes'],**{p:sha(ROOT/p) for p in extra}}
evidence=dict(timestamp=stamp,step='M3 S2',status='passed',root=str(ROOT),D_writes=False,backup=str(backup),source_hashes=sources,source_hashes_verified=True,prior_files_verified=len(prior_files),
    old_chip_handoffs_and_M3S1_unchanged=True,acceptance_index=index,comparison=r['comparison'],controls=r['controls'],method_difference=r['method_difference'],tests=r['tests'],
    source_engines=[x['metadata'] for x in independent[0]['layers']],original_pre_DRC_records=0,original_pre_DRC_categories=31,deck_sha256=r['deck_sha256'],checks=r['checks'],
    browser_cases=54,browser_method_cases=2,worksheet_verified=True,html_files=links['html_files'],local_links=links['local_links_checked'],
    course_core_steps_implemented=17,learner_submission='pending',instructor_review='pending',physical_function_qualified=False,foundry_full_signoff=False,scope=r['scope'])
save(ROOT/'evidence/m3_s2_verification.json',evidence)
prov=load(ROOT/'evidence/provenance.json');prov['m3_s2']=evidence;prov['course_closeout']=closeout
prov['current_execution_scope']='C:/EDA_Codex/Lab06b: 17 teaching steps implemented through M3 S2. Independent gdstk/Shapely directly reads accepted S6 GDS, six facing-edge width/space minima agree with native KLayout 1 nm brackets, 54 rule outcomes / 8 real GDS controls / 12 tests passed. Closed-notch boundary-limit omission corrected and retained. Original unchanged full installed pre-DRC 31 categories zero. Learner/instructor review and physical/foundry qualification pending; M0 FDTD not rerun. D read-only.'
save(ROOT/'evidence/provenance.json',prov)
log=ROOT/'history/CHANGELOG.md';text=log.read_text(encoding='utf-8')
if '## 2026-10-31 M3 S2' not in text:
    with log.open('a',encoding='utf-8') as f:f.write('\n## 2026-10-31 M3 S2\n'
        '- 僅在 C:\\EDA_Codex 工作；D 槽唯讀。採用晶片、M1／M2 ZIP 與 M3 S1 產物均未改。\n'
        '- gdstk 1.0.2／Shapely 2.1.2 直接讀 GDS，不經 KLayout polygon export；材料面積／外框／連通區數一致。\n'
        '- 六項 µm 最小見證：Si 0.350／0.530，HT 0.900／50.000，PAD 8.000／13.500；與 KLayout Euclidian／45° 的 1 nm 搜尋區間一致。\n'
        '- 保留封閉 notch 初版 1.579456→單側極限修正 0.530000 的方法差異；旋轉端面的可見性浮點保護不更動量測距離。\n'
        '- 八個真實 GDS 控制含七個指定違規與一個容差邊界通過；正式版＋控制共 54 項門檻判讀一致，12 項讀檔／解析幾何測試通過。\n'
        '- 原始未改 deck 重跑 31 類、0 筆；獨立方法僅覆蓋六類 facing-edge 量測，不宣稱全製程 DRC 等價。\n'
        '- 24 HTML／1195 本機連結、54 互動比較、2 方法狀態、學員記錄及桌面／手機檢查通過。\n'
        '- 17 步教材與核心示範已建立；學員自主提交與講師驗收、FDTD 未重跑及 foundry／光學／熱電資格維持明示。\n')
p=BASE/'README.md';text=p.read_text(encoding='utf-8').replace('目前教材與核心實驗：M0、M1 全步、M2 S1～S7 及 M3 S1；','目前教材與核心實驗：M0、M1、M2、M3 全部 17 步已建立；').replace('scripts/run_m3_s1.ps1','scripts/run_m3_s2.ps1')
text=text.replace('下一步：M3 S2，獨立幾何量測與交叉驗證。','M3 S2：獨立六項幾何最小見證與 KLayout 一致；54 判讀、8 個實際控制 GDS、12 測試通過，原始完整 pre-DRC 0 筆。\n驗收索引：Lab06b/config/m3_crosscheck_result.json；課程收尾：Lab06b/config/course_closeout.json。\n17 步教材與核心示範已建立；下一步：學員自主提交與講師整體驗收。實體校準／foundry 資格仍待完成。');p.write_text(text,encoding='utf-8')
omitted={'tools','history','__pycache__','.matplotlib','controlled_cases','test_temp'};files=[]
for directory,dirs,names in os.walk(ROOT):
    directory=Path(directory);dirs[:]=[x for x in dirs if x not in omitted and not x.startswith('browser-profile') and not (x=='work' and directory!=ROOT)]
    for name in names:
        p=directory/name
        if p==ROOT/'manifest.json' or p.suffix=='.pyc':continue
        files.append(dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
manifest=dict(root=str(ROOT),current_step='M3 S2',policy='C-only work; D read-only',scope='course, authored source, accepted chip, independent checks and labeled control deliverables; tools, history, nested scratch excluded',files=sorted(files,key=lambda x:x['path']));save(ROOT/'manifest.json',manifest)
save(BASE/'manifest.json',dict(root=str(BASE),project='Lab06b',current_step='M3 S2',root_files=[dict(path=p,sha256=sha(BASE/p)) for p in ['AGENTS.md','EDA_paths.json','Lab06b_index.html','README.md','Lab06b/manifest.json']],verification='Lab06b/evidence/m3_s2_verification.json',D_restore='migration_archive/d_restore_result.json'))
ignore=shutil.ignore_patterns('__pycache__','*.pyc','.matplotlib','browser-profile*','work','controlled_cases','test_temp')
for folder in ['assets','course','analysis','config','scripts','evidence','learner','reference','delivery']:
    shutil.copytree(ROOT/folder,OUTPUT/'Lab06b'/folder,dirs_exist_ok=True,ignore=ignore)
for folder in ['common','m0_s1','m0_s2','m0_s3','m1_s1','m1_s2','m1_s3','m1_s4','m1_s5','m2_s1','m2_s2','m2_s3','m2_s4','m2_s5','m2_s6','m2_s7','m3_s1','m3_s2']:
    shutil.copytree(ROOT/'work'/folder,OUTPUT/'Lab06b/work'/folder,dirs_exist_ok=True,ignore=ignore)
for name in ['Lab06b_index.html','EDA_paths.json','README_Lab06b_Course.md','pic_spec.json','phase_settings.json','manifest.json']:shutil.copy2(ROOT/name,OUTPUT/'Lab06b'/name)
for name in ['AGENTS.md','EDA_paths.json','Lab06b_index.html','README.md','manifest.json']:shutil.copy2(BASE/name,OUTPUT/name)
for row in files:
    p=OUTPUT/'Lab06b'/row['path'];assert p.is_file() and sha(p)==row['sha256'],row['path']
print(json.dumps(dict(status='passed',step='M3 S2',files_verified=len(files),prior_files_verified=len(prior_files),measurements=6,rule_comparisons=54,GDS_controls=8,tests=12,original_pre_DRC_records=0,teaching_steps=17,learner_review='pending',D_writes=False,physical_function_qualified=False,review_copy=str(OUTPUT/'Lab06b/course/m3_s2.html')),ensure_ascii=False,indent=2))
