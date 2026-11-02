from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT.parent
OUTPUT=Path(r'C:/Users/yangc/Documents/Codex/2026-10-30/d-lab-lab06b-codex-c01-codex/outputs/EDA_Codex_Current')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,value):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
r=load(ROOT/'work/m1_s4/out/logic_results.json');browser=load(ROOT/'evidence/browser_checks.json');links=load(ROOT/'evidence/report_checks.json')
assert ROOT.resolve()==Path('C:/EDA_Codex/Lab06b').resolve()
assert r['core_passed'] and r['root_matches_plan'] and r['unit_tests']['passed']==18
assert sum(v['passed'] for v in r['regression'].values())==66
assert all(c['passed'] for c in r['checks'])
assert sum(v['summary']['passed'] for v in r['baseline'].values())==80
assert all(g['passed'] for groups in r['unused_inputs'].values() for g in groups)
assert browser['status']==links['status']=='passed' and browser['m1_s4_interactive_cases']==95
assert browser['m1_s4_worksheet'] and browser['m1_s4_reset']
assert r['topology']==load(ROOT/'config/course.json')['architecture']
for rel,expected in r['source_hashes'].items():assert sha(ROOT/rel)==expected,rel
prov=load(ROOT/'evidence/provenance.json')
prior=prov['m1_s3']['source_hashes']
for rel in ['work/common/mzi.py','work/common/b7.py','work/common/linear_network.py','work/common/encoding.py']:
    assert sha(ROOT/rel)==prior[rel],rel
backup=Path(load(ROOT/'work/m1_s4/backup_record.json')['backup'])
records=load(backup/'backup_manifest.json')
for name in ['README.md','manifest.json']:
    dest=backup/'root_files'/name;assert not dest.exists()
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(BASE/name,dest)
    assert sha(dest)==sha(BASE/name)
    records.append(dict(scope=str(BASE),path=name,backup_path='root_files/'+name,sha256=sha(dest)))
save(backup/'backup_manifest.json',records)
stamp=datetime.now(timezone(timedelta(hours=8))).isoformat()
worst=min(r['baseline'],key=lambda g:r['baseline'][g]['summary']['minimum_signed_margin'])
prov['m1_s4']=dict(timestamp=stamp,current_execution_root=str(ROOT),result='work/m1_s4/out/logic_results.json',
    phase_source=r['phase_source'],unit_tests_passed=18,regression_passed=66,truth_passed=80,unused_groups_passed=12,
    minimum_margin_gate=worst,minimum_signed_margin=r['baseline'][worst]['summary']['minimum_signed_margin'],
    source_hashes=r['source_hashes'],limitations=r['scope'],learner_submission='pending')
prov['current_execution_scope']='C:/EDA_Codex/Lab06b: M0 S1 through M1 S4, including full five-program 80-case ideal truth acceptance; D is read-only.'
save(ROOT/'evidence/provenance.json',prov)
verification=dict(timestamp=stamp,step='M1 S4',status='passed',root=str(ROOT),D_drive_policy='read-only; no D writes in this step',
    unit_tests=r['unit_tests'],regression=r['regression'],checks=r['checks'],
    function_summaries={g:v['summary'] for g,v in r['baseline'].items()},unused_groups=12,
    source_hashes_verified=True,previous_shared_models_unchanged=True,phase_source=r['phase_source'],
    html_files=links['html_files'],local_links=links['local_links_checked'],browser_interactive_cases=95,
    learner_worksheet_verified=True,backup=str(backup),learner_submission='pending',next_step='M1 S5')
save(ROOT/'evidence/m1_s4_verification.json',verification)
with (ROOT/'history/CHANGELOG.md').open('a',encoding='utf-8') as f:
    f.write('\n## 2026-10-31 M1 S4\n'
            '- 僅在 C:\\EDA_Codex 實作；D 槽唯讀，沒有 D 槽寫入。\n'
            '- 從 C 槽快照擷取五組完整精度相位，使用共用 B7 重新驗收 80／80。\n'
            '- 加入 logic_validation.py、有號裕量、12 組未作用輸入與三種受控對照。\n'
            '- 18 項本步測試、66 項前步回歸、13 項檢查與 95 組瀏覽器計算通過。\n'
            '- 14 份 HTML、652 個本機連結及桌面／手機版面通過；下一步 M1 S5 規格交接。\n'
            '- 最小有號裕量為 XOR2 約 0.25；數值結果不等同實體 PIC 誤差容許。\n')
readme=(BASE/'README.md').read_text(encoding='utf-8').replace('M0 S1～M1 S3','M0 S1～M1 S4').replace('scripts/run_m1_s3.ps1','scripts/run_m1_s4.ps1')
readme=readme.replace('後續只更新 C:\\EDA_Codex；D 槽依還原紀錄回復已確認的變更。','後續只更新 C:\\EDA_Codex；D 槽唯讀。\n下一步：M1 S5，規格與相位程式交接 M2。')
(BASE/'README.md').write_text(readme,encoding='utf-8')
def include(p):
    rel=p.relative_to(ROOT)
    return p.is_file() and p.name!='manifest.json' and p.suffix!='.pyc' and not any(x in ('tools','history','__pycache__','.matplotlib') or x.startswith('browser-profile') for x in rel.parts) and not (rel.parts[0]=='work' and 'work' in rel.parts[1:])
manifest=dict(root=str(ROOT),current_step='M1 S4',policy='C-only work; D read-only',
    files=[dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(ROOT.rglob('*')) if include(p)])
save(ROOT/'manifest.json',manifest)
save(BASE/'manifest.json',dict(root=str(BASE),project='Lab06b',current_step='M1 S4',
    root_files=[dict(path=rel,sha256=sha(BASE/rel)) for rel in ['AGENTS.md','EDA_paths.json','Lab06b_index.html','README.md','Lab06b/manifest.json']],
    verification='Lab06b/evidence/m1_s4_verification.json',D_restore='migration_archive/d_restore_result.json'))
# Export a review copy; canonical source, logs and backups remain under C:/EDA_Codex.
ignore=shutil.ignore_patterns('__pycache__','*.pyc','.matplotlib','browser-profile*','work')
for folder in ['course','analysis','config','scripts','evidence','learner','reference']:
    shutil.copytree(ROOT/folder,OUTPUT/'Lab06b'/folder,dirs_exist_ok=True,ignore=ignore)
for folder in ['common','m0_s1','m0_s2','m0_s3','m1_s1','m1_s2','m1_s3','m1_s4']:
    shutil.copytree(ROOT/'work'/folder,OUTPUT/'Lab06b/work'/folder,dirs_exist_ok=True,ignore=ignore)
for name in ['Lab06b_index.html','EDA_paths.json','README_Lab06b_Course.md','manifest.json']:shutil.copy2(ROOT/name,OUTPUT/'Lab06b'/name)
for name in ['AGENTS.md','EDA_paths.json','Lab06b_index.html','README.md','manifest.json']:shutil.copy2(BASE/name,OUTPUT/name)
for row in manifest['files']:
    dest=OUTPUT/'Lab06b'/row['path']
    if dest.is_file():assert sha(dest)==row['sha256'],row['path']
print(json.dumps(dict(status='passed',root=str(ROOT),step='M1 S4',truth_cases=80,unused_groups=12,
    minimum_gate=worst,minimum_signed_margin=r['baseline'][worst]['summary']['minimum_signed_margin'],
    D_writes=False,next_step='M1 S5',review_copy=str(OUTPUT/'Lab06b/course/m1_s4.html')),ensure_ascii=False,indent=2))
