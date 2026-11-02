"""Verify M2 S4 evidence, preserve earlier steps, export readable review copy."""
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
r=load(ROOT/'work/m2_s4/out/review_results.json');browser=load(ROOT/'evidence/browser_checks.json');links=load(ROOT/'evidence/report_checks.json')
assert ROOT.resolve()==Path('C:/EDA_Codex/Lab06b').resolve()
assert r['core_passed'] and r['review_decision']=='accept_margin_improved_core'
assert sum(v['passed'] for v in r['regression'].values())==136 and all(c['passed'] for c in r['checks'])
assert r['M1_sources_and_zip_unchanged'] and r['S3_baseline_unchanged'] and r['M1_baseline_replay_passed']==80
assert browser['status']==links['status']=='passed' and browser['m2_s4_cases']==24 and browser['m2_s4_worksheet']
assert r['changed_ports']==5 and r['changed_phase_centers']==12 and all(v['route_coverage']['uncovered']==0 for v in r['versions'].values())
for rel,expected in r['source_hashes'].items():assert sha(ROOT/rel)==expected,rel
for name,expected in r['S3_baseline_hashes'].items():
    assert sha(ROOT/'work/m2_s3/out'/name)==expected and sha(ROOT/'work/m2_s4/out/before'/name)==expected,name
current=load(ROOT/'config/m2_current_core.json');assert current['accepted_at_step']=='M2 S4'
assert current['m1_spec_sha256']==sha(ROOT/'pic_spec.json') and current['layout_config_sha256']==sha(ROOT/current['layout_config'])
for rel,expected in current['files'].items():assert (ROOT/rel).resolve().is_relative_to(ROOT) and sha(ROOT/rel)==expected,rel
assert r['versions']['after']['readback']['gds_sha256']==current['files']['work/m2_s4/out/after/b7_core.gds']
native_hashes={p['file']:sha(ROOT/'course/figures/m2_s4'/p['file']) for p in r['native_images']};assert len(native_hashes)==24
for fault in r['controlled_faults']:
    assert fault['detected'] and sha(ROOT/'work/m2_s4/work/controlled_gds'/(fault['name']+'.gds'))==fault['gds_sha256']
previous=load(ROOT/'work/m1_s5/out/handoff_results.json')
for rel,expected in previous['source_hashes'].items():assert sha(ROOT/rel)==expected,rel
assert sha(ROOT/previous['zip'])==previous['zip_sha256']
backup=Path(load(ROOT/'work/m2_s4/backup_record.json')['backup']);records=load(backup/'backup_manifest.json')
for row in records:assert sha(backup/row.get('backup_path',row['path']))==row['sha256']
prior_manifest=load(backup/'manifest.json')
prior_steps=[row for row in prior_manifest['files'] if row['path'].startswith(('work/m2_s2/','work/m2_s3/')) or row['path']=='work/common/core_layout.py']
for row in prior_steps:assert sha(ROOT/row['path'])==row['sha256'],row['path']
for name in ['README.md','manifest.json']:
    dest=backup/'root_files'/name;assert not dest.exists();dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(BASE/name,dest);assert sha(dest)==sha(BASE/name)
    records.append(dict(scope=str(BASE),path=name,backup_path='root_files/'+name,sha256=sha(dest)))
save(backup/'backup_manifest.json',records)
stamp=datetime.now(timezone(timedelta(hours=8))).isoformat()
extra_sources=['scripts/run_m2_s4.ps1','scripts/render_m2_s4.py','scripts/render_course.py','work/m2_s4/plot_review.py','work/m2_s4/browser_qa.cjs']
sources={**r['source_hashes'],**{p:sha(ROOT/p) for p in extra_sources}}
save(ROOT/'evidence/m2_s4_verification.json',dict(timestamp=stamp,step='M2 S4',status='passed',root=str(ROOT),D_writes=False,
    review_decision=r['review_decision'],metrics=r['metrics'],regression=r['regression'],checks=r['checks'],
    accepted_core_index=current,native_image_hashes=native_hashes,source_hashes=sources,source_hashes_verified=True,
    S3_originals_unchanged=True,M1_source_files_and_zip_unchanged=True,prior_files_verified=len(prior_steps),
    M1_baseline_replay_passed=80,browser_views=24,worksheet_verified=True,
    html_files=links['html_files'],local_links=links['local_links_checked'],backup=str(backup),learner_submission='pending',scope=r['scope'],next_step='M2 S5'))
prov=load(ROOT/'evidence/provenance.json')
prov['m2_s4']=dict(timestamp=stamp,current_execution_root=str(ROOT),result='work/m2_s4/out/review_results.json',
    decision=r['review_decision'],metrics=r['metrics'],accepted_core_index='config/m2_current_core.json',
    native_view_engine='KLayout 0.30.12 LayoutView.save_image',native_views=24,regression_passed=136,
    S3_originals_unchanged=True,M1_sources_and_zip_unchanged=True,source_hashes=sources,limitations=r['scope'],learner_submission='pending',
    api_references=['https://www.klayout.org/downloads/master/doc-qt5/code/class_LayoutView.html','https://www.klayout.org/downloads/master/doc-qt5/code/class_Region.html'])
prov['current_execution_scope']='C:/EDA_Codex/Lab06b: M0/M1, M2 S1-S4. Scoped KLayout native review; S-bend 20 to 24 um for an explicitly educational radius-margin target. Original S3 preserved; current core index points to S4 accepted revision. Full DRC/LVS and layout phase replay pending. D read-only.'
save(ROOT/'evidence/provenance.json',prov)
with (ROOT/'history/CHANGELOG.md').open('a',encoding='utf-8') as f:
    f.write('\n## 2026-10-31 M2 S4\n'
            '- 僅在 C:\\EDA_Codex 工作；D 槽沒有寫入。\n'
            '- KLayout 0.30.12 原生 LayoutView 匯出 24 張前後／區域／圖層視圖；十項檢視記錄區分通過、改善與後關待辦。\n'
            '- 原 S3 符合既有 5 µm 規劃值；為達本課程額外 7.5 µm 裕量目標，S 彎 20→24 µm，連續解析 Rmin 5.230883→7.665199 µm。\n'
            '- core 光學水平跨度 2076→2140 µm；設計區維持 2200×220 µm。5 個輸出埠與 12 個相位中心 x 座標改變，匯出變更表。\n'
            '- 兩版獨立回讀、六項局部線寬／間距篩查、全部路徑取樣及中心線交集核對通過；3 種隔離錯誤 GDS 被對應檢查抓到。\n'
            '- 136 項既有回歸通過；M1 與 S3 原檔保留，80/80 為 M1 基準重播，未當作新版實體光路驗收。\n'
            '- 新增 config/m2_current_core.json，綁定採用版設定、GDS 與 sidecar 雜湊；下一步 M2 S5 應讀取此索引。\n'
            '- 19 份 HTML、890 個連結與 24 組原生視圖瀏覽器核對通過。完整 DRC／LVS、EC／PAD／GND、熱校正及相位回註仍待後關。\n')
p=BASE/'README.md';text=p.read_text(encoding='utf-8').replace('目前教材與核心實驗：M0、M1 全步及 M2 S1～S3；','目前教材與核心實驗：M0、M1 全步及 M2 S1～S4；').replace('scripts/run_m2_s3.ps1','scripts/run_m2_s4.ps1')
text=text.replace('光學跨度 2076×120 µm；','S3 初版光學跨度 2076×120 µm；')
text=text.replace('下一步：M2 S4，KLayout 版圖檢視與修改記錄。','M2 S4：KLayout 檢視與修改記錄通過；目前採用版見 Lab06b/config/m2_current_core.json。\nS4 採用版光學跨度 2140×120 µm；S 彎 24 µm，連續解析最小曲率半徑 7.665199 µm。\n下一步：M2 S5，EC 光學 I/O、heater PAD 與 GND。');p.write_text(text,encoding='utf-8')
omitted={'tools','history','__pycache__','.matplotlib','controlled_cases','test_temp'};files=[]
for directory,dirs,names in os.walk(ROOT):
    directory=Path(directory)
    dirs[:]=[d for d in dirs if d not in omitted and not d.startswith('browser-profile') and not (d=='work' and directory!=ROOT)]
    for name in names:
        path=directory/name
        if path==ROOT/'manifest.json' or path.suffix=='.pyc':continue
        files.append(dict(path=path.relative_to(ROOT).as_posix(),bytes=path.stat().st_size,sha256=sha(path)))
manifest=dict(root=str(ROOT),current_step='M2 S4',policy='C-only work; D read-only',
    scope='course, models, handoff, M2 core and reviewed before/after evidence; vendor tools and temporary/controlled copies excluded',files=sorted(files,key=lambda r:r['path']))
save(ROOT/'manifest.json',manifest)
save(BASE/'manifest.json',dict(root=str(BASE),project='Lab06b',current_step='M2 S4',
    root_files=[dict(path=rel,sha256=sha(BASE/rel)) for rel in ['AGENTS.md','EDA_paths.json','Lab06b_index.html','README.md','Lab06b/manifest.json']],
    verification='Lab06b/evidence/m2_s4_verification.json',D_restore='migration_archive/d_restore_result.json'))
ignore=shutil.ignore_patterns('__pycache__','*.pyc','.matplotlib','browser-profile*','work','controlled_cases','test_temp')
for folder in ['course','analysis','config','scripts','evidence','learner','reference','delivery']:
    shutil.copytree(ROOT/folder,OUTPUT/'Lab06b'/folder,dirs_exist_ok=True,ignore=ignore)
for folder in ['common','m0_s1','m0_s2','m0_s3','m1_s1','m1_s2','m1_s3','m1_s4','m1_s5','m2_s1','m2_s2','m2_s3','m2_s4']:
    shutil.copytree(ROOT/'work'/folder,OUTPUT/'Lab06b/work'/folder,dirs_exist_ok=True,ignore=ignore)
for name in ['Lab06b_index.html','EDA_paths.json','README_Lab06b_Course.md','pic_spec.json','phase_settings.json','manifest.json']:shutil.copy2(ROOT/name,OUTPUT/'Lab06b'/name)
for name in ['AGENTS.md','EDA_paths.json','Lab06b_index.html','README.md','manifest.json']:shutil.copy2(BASE/name,OUTPUT/name)
copied=0
for row in manifest['files']:
    p=OUTPUT/'Lab06b'/row['path']
    if p.is_file():assert sha(p)==row['sha256'],row['path'];copied+=1
print(json.dumps(dict(status='passed',step='M2 S4',root=str(ROOT),decision=r['review_decision'],radius_before_um=r['versions']['before']['radius_um'],radius_after_um=r['versions']['after']['radius_um'],
    native_views=24,regression=136,prior_files_verified=len(prior_steps),review_files_verified=copied,M1_unchanged=True,S3_unchanged=True,D_writes=False,next_step='M2 S5',
    review_copy=str(OUTPUT/'Lab06b/course/m2_s4.html')),ensure_ascii=False,indent=2))
