from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,hashlib,shutil,zipfile
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT.parent
OUTPUT=Path(r'C:/Users/yangc/Documents/Codex/2026-10-30/d-lab-lab06b-codex-c01-codex/outputs/EDA_Codex_Current')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
r=load(ROOT/'work/m1_s5/out/handoff_results.json');browser=load(ROOT/'evidence/browser_checks.json');links=load(ROOT/'evidence/report_checks.json')
fresh=load(ROOT/'work/m1_s5/out/fresh_shell_replay.json')
assert r['core_passed'] and r['root_matches_plan'] and r['unit_tests']['passed']==15
assert sum(v['passed'] for v in r['regression'].values())==84 and all(c['passed'] for c in r['checks'])
assert r['direct_replay']['truth_passed']==r['isolated_replay']['truth_passed']==fresh['truth_passed']==80
assert fresh['status']=='passed' and Path(fresh['loaded_model']).is_relative_to(Path(fresh['bundle'])/'model')
assert browser['status']==links['status']=='passed'
assert browser['m1_s5_consumer_cases']==80 and browser['m1_s5_channel_cases']==70 and browser['m1_s5_worksheet']
for rel,expected in r['source_hashes'].items():assert sha(ROOT/rel)==expected,rel
assert sha(ROOT/r['zip'])==r['zip_sha256']
with zipfile.ZipFile(ROOT/r['zip']) as z:
    for row in r['package_manifest']['files']:assert hashlib.sha256(z.read(row['path'])).hexdigest()==row['sha256']
prov=load(ROOT/'evidence/provenance.json')
for rel in ['work/common/b7.py','work/common/mzi.py','work/common/linear_network.py','work/common/encoding.py','work/common/logic_validation.py']:
    assert sha(ROOT/rel)==prov['m1_s4']['source_hashes'][rel],rel
backup=Path(load(ROOT/'work/m1_s5/backup_record.json')['backup']);records=load(backup/'backup_manifest.json')
for name in ['README.md','manifest.json']:
    dest=backup/'root_files'/name;assert not dest.exists()
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(BASE/name,dest);assert sha(dest)==sha(BASE/name)
    records.append(dict(scope=str(BASE),path=name,backup_path='root_files/'+name,sha256=sha(dest)))
save(backup/'backup_manifest.json',records)
stamp=datetime.now(timezone(timedelta(hours=8))).isoformat()
prov['m1_s5']=dict(timestamp=stamp,current_execution_root=str(ROOT),result='work/m1_s5/out/handoff_results.json',
    spec='pic_spec.json',phase_settings='phase_settings.json',bundle=r['bundle'],zip=r['zip'],zip_sha256=r['zip_sha256'],
    spec_sha256=r['spec_sha256'],unit_tests_passed=15,regression_passed=84,standalone_truths_passed=80,
    source_hashes=r['source_hashes'],limitations=r['scope'],learner_submission='pending')
prov['current_execution_scope']='C:/EDA_Codex/Lab06b: M0 and all M1 steps, including versioned logical specification, named phase mapping and portable 80-case replay; D is read-only.'
save(ROOT/'evidence/provenance.json',prov)
save(ROOT/'evidence/m1_s5_verification.json',dict(timestamp=stamp,step='M1 S5',status='passed',root=str(ROOT),D_writes=False,
    unit_tests=r['unit_tests'],regression=r['regression'],checks=r['checks'],source_hashes_verified=True,
    previous_shared_models_unchanged=True,spec_sha256=r['spec_sha256'],zip_sha256=r['zip_sha256'],
    independent_replay=r['isolated_replay'],fresh_shell_replay=fresh,
    html_files=links['html_files'],local_links=links['local_links_checked'],browser_consumer_cases=80,browser_channel_cases=70,
    learner_worksheet_verified=True,backup=str(backup),learner_submission='pending',next_step='M2 S1'))
with (ROOT/'history/CHANGELOG.md').open('a',encoding='utf-8') as f:
    f.write('\n## 2026-10-31 M1 S5\n'
            '- 僅在 C:\\EDA_Codex 工作；D 槽沒有寫入。\n'
            '- 產生 pic_spec.json 與綁定 SHA-256 的 phase_settings.json；10 個光學埠、14 個相位通道、6 段直通。\n'
            '- 邏輯 heater 名稱固定，實體接口、PAD 與校正明確待 M2；交接包不是實體 PIC 完成證明。\n'
            '- 直接、獨立資料夾及新命令列重播皆為 80／80；ZIP 固定檔案雜湊一致。\n'
            '- 15 項本步測試、84 項前步回歸、13 項檢查與四種錯誤副本拒絕通過。\n'
            '- 80 組前端重播、70 組通道對照、15 份 HTML 與 700 個連結通過；下一步 M2 S1。\n')
p=BASE/'README.md';text=p.read_text(encoding='utf-8').replace('M0 S1～M1 S4','M0 S1～M1 S5').replace('scripts/run_m1_s4.ps1','scripts/run_m1_s5.ps1')
text=text.replace('下一步：M1 S5，規格與相位程式交接 M2。','交接包：Lab06b/delivery/m1_handoff.zip。\n下一步：M2 S1，PIC 邊界與 I/O 表。')
p.write_text(text,encoding='utf-8')
def included(p):
    if not p.is_file() or p==ROOT/'manifest.json' or p.suffix=='.pyc':return False
    rel=p.relative_to(ROOT)
    if any(x in ('tools','history','__pycache__','.matplotlib','controlled_cases','test_temp') or x.startswith('browser-profile') for x in rel.parts):return False
    return not (rel.parts[0]=='work' and 'work' in rel.parts[1:])
manifest=dict(root=str(ROOT),current_step='M1 S5',policy='C-only work; D read-only',
    scope='course, model sources, verified handoff and evidence; vendor tools and transient test copies excluded',
    files=[dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(ROOT.rglob('*')) if included(p)])
save(ROOT/'manifest.json',manifest)
save(BASE/'manifest.json',dict(root=str(BASE),project='Lab06b',current_step='M1 S5',
    root_files=[dict(path=rel,sha256=sha(BASE/rel)) for rel in ['AGENTS.md','EDA_paths.json','Lab06b_index.html','README.md','Lab06b/manifest.json']],
    verification='Lab06b/evidence/m1_s5_verification.json',D_restore='migration_archive/d_restore_result.json'))
ignore=shutil.ignore_patterns('__pycache__','*.pyc','.matplotlib','browser-profile*','work','controlled_cases','test_temp')
for folder in ['course','analysis','config','scripts','evidence','learner','reference','delivery']:
    shutil.copytree(ROOT/folder,OUTPUT/'Lab06b'/folder,dirs_exist_ok=True,ignore=ignore)
for folder in ['common','m0_s1','m0_s2','m0_s3','m1_s1','m1_s2','m1_s3','m1_s4','m1_s5']:
    shutil.copytree(ROOT/'work'/folder,OUTPUT/'Lab06b/work'/folder,dirs_exist_ok=True,ignore=ignore)
for name in ['Lab06b_index.html','EDA_paths.json','README_Lab06b_Course.md','pic_spec.json','phase_settings.json','manifest.json']:shutil.copy2(ROOT/name,OUTPUT/'Lab06b'/name)
for name in ['AGENTS.md','EDA_paths.json','Lab06b_index.html','README.md','manifest.json']:shutil.copy2(BASE/name,OUTPUT/name)
for row in manifest['files']:
    path=OUTPUT/'Lab06b'/row['path']
    if path.is_file():assert sha(path)==row['sha256'],row['path']
assert sha(OUTPUT/'Lab06b/delivery/m1_handoff.zip')==r['zip_sha256']
print(json.dumps(dict(status='passed',step='M1 S5',root=str(ROOT),package=str(ROOT/r['zip']),
    spec_ports=10,phase_channels=14,independent_truths=80,D_writes=False,next_step='M2 S1',
    review_copy=str(OUTPUT/'Lab06b/course/m1_s5.html')),ensure_ascii=False,indent=2))
