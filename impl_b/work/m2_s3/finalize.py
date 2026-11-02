"""Record completed M2 S3 evidence and export a verified reading mirror."""
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
r=load(ROOT/'work/m2_s3/out/layout_results.json');browser=load(ROOT/'evidence/browser_checks.json');links=load(ROOT/'evidence/report_checks.json')
assert ROOT.resolve()==Path('C:/EDA_Codex/Lab06b').resolve()
assert r['core_passed'] and r['unit_tests']['passed']==12
assert sum(v['passed'] for v in r['regression'].values())==124 and all(c['passed'] for c in r['checks'])
assert r['M1_sources_and_zip_unchanged'] and r['M2S2_sources_unchanged'] and r['M1_baseline_replay_passed']==80
assert browser['status']==links['status']=='passed' and browser['m2_s3_cases']==70 and browser['m2_s3_worksheet']
for rel,expected in r['source_hashes'].items():assert sha(ROOT/rel)==expected,rel
for rel,expected in r['gds_files'].items():assert sha(ROOT/'work/m2_s3/out'/rel)==expected,rel
assert r['gds_readback']['gds_sha256']==r['gds_files']['b7_core.gds']
assert r['gds_readback']['passed'] and len(r['gds_readback']['joints'])==81 and all(j['covered'] for j in r['gds_readback']['joints'])
previous=load(ROOT/'work/m1_s5/out/handoff_results.json')
for rel,expected in previous['source_hashes'].items():assert sha(ROOT/rel)==expected,rel
assert sha(ROOT/previous['zip'])==previous['zip_sha256']
backup=Path(load(ROOT/'work/m2_s3/backup_record.json')['backup']);records=load(backup/'backup_manifest.json')
for row in records:assert sha(backup/row.get('backup_path',row['path']))==row['sha256']
prior_manifest=load(backup/'manifest.json')
prior_s2=[row for row in prior_manifest['files'] if row['path'].startswith('work/m2_s2/')]
for row in prior_s2:assert sha(ROOT/row['path'])==row['sha256'],row['path']
for name in ['README.md','manifest.json']:
    dest=backup/'root_files'/name;assert not dest.exists();dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(BASE/name,dest);assert sha(dest)==sha(BASE/name)
    records.append(dict(scope=str(BASE),path=name,backup_path='root_files/'+name,sha256=sha(dest)))
save(backup/'backup_manifest.json',records)
stamp=datetime.now(timezone(timedelta(hours=8))).isoformat()
extra_sources=['scripts/run_m2_s3.ps1','scripts/render_m2_s3.py','scripts/render_course.py','work/m2_s3/plot_layout.py','work/m2_s3/browser_qa.cjs']
all_sources={**r['source_hashes'],**{p:sha(ROOT/p) for p in extra_sources}}
verification=dict(timestamp=stamp,step='M2 S3',status='passed',root=str(ROOT),D_writes=False,
    counts=r['counts'],dimensions=r['dimensions'],unit_summary=r['unit_summary'],gds_files=r['gds_files'],
    independent_GDS_readback=r['gds_readback'],unit_tests=r['unit_tests'],regression=r['regression'],checks=r['checks'],
    source_hashes=all_sources,source_hashes_verified=True,M1_source_files_and_zip_unchanged=True,
    M2S2_files_verified_unchanged=len(prior_s2),M1_baseline_replay_passed=80,
    html_files=links['html_files'],local_links=links['local_links_checked'],browser_phase_coordinate_cases=70,
    learner_worksheet_verified=True,backup=str(backup),learner_submission='pending',scope=r['scope'],next_step='M2 S4')
save(ROOT/'evidence/m2_s3_verification.json',verification)
prov=load(ROOT/'evidence/provenance.json')
prov['m2_s3']=dict(timestamp=stamp,current_execution_root=str(ROOT),result='work/m2_s3/out/layout_results.json',
    core_gds='work/m2_s3/out/b7_core.gds',single_unit_gds='work/m2_s3/out/mzi_core.gds',
    counts=r['counts'],dimensions=r['dimensions'],gds_hashes=r['gds_files'],unit_tests_passed=12,regression_passed=124,
    M1_sources_and_zip_unchanged=True,M2S2_sources_and_results_unchanged=True,source_hashes=all_sources,
    limitations=r['scope'],learner_submission='pending',
    api_reference='https://academy.lucedaphotonics.com/training/getting_started/5_component_layout/1_tutorials')
prov['current_execution_scope']='C:/EDA_Codex/Lab06b: M0/M1 and M2 S1-S3; physical initial B7 core GDS exported, independently read back and plotted using KLayout flattened polygons. Full DRC/LVS and layout-extracted replay pending. D read-only.'
save(ROOT/'evidence/provenance.json',prov)
with (ROOT/'history/CHANGELOG.md').open('a',encoding='utf-8') as f:
    f.write('\n## 2026-10-31 M2 S3\n'
            '- 僅在 C:\\EDA_Codex 工作；D 槽沒有寫入。\n'
            '- 新建 B7 core：7 MZI／14 PDK MMI、6 段直通、10 端點引線及十個 core 埠；光學跨度 2076×120 µm，宣告設計區 2200×220 µm。\n'
            '- 畫出 14 個局部 heater 與 28 個局部接觸落墊；外部 EC／PAD／GND 與熱校正待後續。\n'
            '- 匯出 b7_core.gds、mzi_core.gds、埠位／相位區／58 段波導長度 CSV；單模波導長度不含 MMI。\n'
            '- KLayout 獨立回讀實例、圖層、十埠及 81 個局部接點；出圖改用 KLayout 完整攤平與保留孔洞的多邊形資料。\n'
            '- 12 項本步測試、124 項回歸及 3 種錯誤座標副本偵測通過；原 M1 與 M2 S2 來源／結果未改。\n'
            '- 18 份 HTML、837 個連結及 70 組相位／實體座標瀏覽器核對通過；下一步 M2 S4。\n'
            '- 本步不是完整 DRC／LVS／製程驗證，也未將原基準 80/80 誤列為版圖回註真值驗收。\n')
p=BASE/'README.md';text=p.read_text(encoding='utf-8').replace('目前教材與核心實驗：M0、M1 全步及 M2 S1～S2；','目前教材與核心實驗：M0、M1 全步及 M2 S1～S3；').replace('scripts/run_m2_s2.ps1','scripts/run_m2_s3.ps1')
text=text.replace('下一步：M2 S3，七顆 MZI 實體 core 版圖與 GDS。','M2 S3：work/m2_s3/out/b7_core.gds，初版 core 與獨立 GDS 回讀核對通過。\n光學跨度 2076×120 µm；14 局部 heater／28 局部接觸；EC、外部 PAD／GND、DRC 與相位回註待後續。\n下一步：M2 S4，KLayout 版圖檢視與修改記錄。');p.write_text(text,encoding='utf-8')
omitted={'tools','history','__pycache__','.matplotlib','controlled_cases','test_temp'};files=[]
for directory,dirs,names in os.walk(ROOT):
    current=Path(directory)
    dirs[:]=[d for d in dirs if d not in omitted and not d.startswith('browser-profile') and not (d=='work' and current!=ROOT)]
    for name in names:
        path=current/name
        if path==ROOT/'manifest.json' or path.suffix=='.pyc':continue
        files.append(dict(path=path.relative_to(ROOT).as_posix(),bytes=path.stat().st_size,sha256=sha(path)))
manifest=dict(root=str(ROOT),current_step='M2 S3',policy='C-only work; D read-only',
    scope='course, models, M1 handoff, M2 boundary/circuit, physical core GDS and evidence; vendor tools and temporary files excluded',files=sorted(files,key=lambda r:r['path']))
save(ROOT/'manifest.json',manifest)
save(BASE/'manifest.json',dict(root=str(BASE),project='Lab06b',current_step='M2 S3',
    root_files=[dict(path=rel,sha256=sha(BASE/rel)) for rel in ['AGENTS.md','EDA_paths.json','Lab06b_index.html','README.md','Lab06b/manifest.json']],
    verification='Lab06b/evidence/m2_s3_verification.json',D_restore='migration_archive/d_restore_result.json'))
ignore=shutil.ignore_patterns('__pycache__','*.pyc','.matplotlib','browser-profile*','work','controlled_cases','test_temp')
for folder in ['course','analysis','config','scripts','evidence','learner','reference','delivery']:
    shutil.copytree(ROOT/folder,OUTPUT/'Lab06b'/folder,dirs_exist_ok=True,ignore=ignore)
for folder in ['common','m0_s1','m0_s2','m0_s3','m1_s1','m1_s2','m1_s3','m1_s4','m1_s5','m2_s1','m2_s2','m2_s3']:
    shutil.copytree(ROOT/'work'/folder,OUTPUT/'Lab06b/work'/folder,dirs_exist_ok=True,ignore=ignore)
for name in ['Lab06b_index.html','EDA_paths.json','README_Lab06b_Course.md','pic_spec.json','phase_settings.json','manifest.json']:shutil.copy2(ROOT/name,OUTPUT/'Lab06b'/name)
for name in ['AGENTS.md','EDA_paths.json','Lab06b_index.html','README.md','manifest.json']:shutil.copy2(BASE/name,OUTPUT/name)
copied=0
for row in manifest['files']:
    p=OUTPUT/'Lab06b'/row['path']
    if p.is_file():assert sha(p)==row['sha256'],row['path'];copied+=1
print(json.dumps(dict(status='passed',step='M2 S3',root=str(ROOT),counts=r['counts'],dimensions=r['dimensions'],
    unit_tests=12,regression=124,M1_unchanged=True,M2S2_files_verified_unchanged=len(prior_s2),D_writes=False,
    review_files_verified=copied,next_step='M2 S4',review_copy=str(OUTPUT/'Lab06b/course/m2_s3.html')),ensure_ascii=False,indent=2))
