"""Verify new native-CAD evidence, preserve prior design, and mirror deliverables."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,hashlib,shutil,os,sys
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT.parent;HERE=Path(__file__).resolve().parent;OUT=HERE/'out'
REVIEW=Path(r'C:/Users/yangc/Documents/Codex/2026-10-30/d-lab-lab06b-codex-c01-codex/outputs/EDA_Codex_Current')
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
r=load(OUT/'reproduction_results.json');src=load(ROOT/'work/single_report/out/report_sources.json');browser=load(ROOT/'evidence/virtuoso_report_browser.json');links=load(ROOT/'evidence/report_checks.json');package=load(ROOT/'config/virtuoso_package.json')
assert r['status']==browser['status']==links['status']=='passed' and package['verified']
assert browser['source_sections']==20 and browser['structure']['articles']==20 and browser['structure']['images']==55
assert browser['select_option_changes']==394 and browser['numeric_input_changes']==42 and not browser['errors']
assert src['course_steps']==17 and src['appendices']==2 and src['native_CAD_extensions']==1 and not src['original_D_written']
assert sha(ROOT/'Lab06b_index.html')==src['report_sha256'] and sha(ROOT/'scripts/render_study.py')==src['generator_sha256']
for row in src['source_pages']:
 assert sha(ROOT/row['page'])==row['sha256']
 if row.get('proof'):assert sha(ROOT/row['proof'])==row['proof_sha256']
for rel,h in r['preserved_bindings'].items():assert sha(ROOT/rel)==h
for rel,h in r['proofs'].items():assert sha(HERE/rel)==h,rel
assert sha(ROOT/package['archive'])==package['sha256']
for row in load(ROOT/package['manifest'])['files']:assert sha(ROOT/'delivery/virtuoso_calibre'/row['path'])==row['sha256']
backup=Path(load(HERE/'backup_record.json')['backup']);prior=load(backup/'manifest.json');prior_sources=load(backup/'work/single_report/out/report_sources.json')
for row in load(backup/'backup_manifest.json'):assert sha(backup/row['path'])==row['sha256']
unchanged=[]
for row in prior['files']:
 rel=row['path']
 if rel.startswith(('work/','delivery/','sources/','reference/','course/figures/')) and rel!='work/single_report/out/report_sources.json':
  assert sha(ROOT/rel)==row['sha256'],rel;unchanged.append(rel)
for row in prior_sources['source_pages']:assert sha(ROOT/row['page'])==row['sha256'],row['page']
text=(ROOT/'Lab06b_index.html').read_text(encoding='utf-8');assert '學員驗收與交付' not in text and '學員姓名' not in text
review_log=(OUT/'virtuoso_review_CDS.log').read_text(encoding='utf-8',errors='replace')
assert '\\t window:2' in review_log and '*Error*' not in review_log
stamp=datetime.now(timezone(timedelta(hours=8))).isoformat()
verification=dict(schema='lab06b.native_CAD_report_verification.v1',timestamp=stamp,status='passed',course_steps=17,native_CAD_extension=1,appendices=2,source_sections=20,images=55,report_sha256=sha(ROOT/'Lab06b_index.html'),
 report='Lab06b_index.html',chapter='course/virtuoso_calibre.html',proof='work/virtuoso_reproduction/out/reproduction_results.json',browser='evidence/virtuoso_report_browser.json',links='evidence/report_checks.json',package=package,
 previous_technical_files_unchanged=len(unchanged),previous_19_source_pages_unchanged=True,original_S6_spec_phase_M1_M2_ZIP_unchanged=True,native_review_launcher_smoke='opened read-only layout; no SKILL error; expected auto-tech/XL warnings retained in log',D_writes=False,backup=str(backup))
save(ROOT/'evidence/virtuoso_reproduction.json',verification)
prov=load(ROOT/'evidence/provenance.json');prov['native_CAD_reproduction']=verification;prov['current_report_verification']='evidence/virtuoso_reproduction.json';save(ROOT/'evidence/provenance.json',prov)
save(ROOT/'evidence/browser_checks.json',browser)
index=load(ROOT/'config/virtuoso_reproduction.json');index['package']=package;save(ROOT/'config/virtuoso_reproduction.json',index)
for p in [ROOT/'README_Lab06b_Course.md',BASE/'README.md']:
 text=p.read_text(encoding='utf-8');marker='## 本日 Virtuoso／Calibre 完整重現'
 if marker not in text:
  text+='\n'+marker+'\n2026-10-31 已在現行 C 版本新跑 Virtuoso 匯入／顯示、classic Interactive／RVE、XStream 200→8191、註記跨引擎修正與空白 OA 重播。\n總報告 Lab06b/Lab06b_index.html（專案內為 Lab06b_index.html），實機章節 #cad-reproduction；分頁 course/virtuoso_calibre.html。\n新互通 GDS、證據、原生截圖與重播來源在 Lab06b/work/virtuoso_reproduction；封裝在 Lab06b/delivery/Lab06b_Virtuoso_Calibre_reproduction.zip。\n原 S6 採用版、規格／相位、M1／M2 ZIP 保留；D 槽唯讀。\n';p.write_text(text,encoding='utf-8')
with (ROOT/'history/CHANGELOG.md').open('a',encoding='utf-8') as f:f.write('\n## 2026-10-31 新版 Virtuoso／Calibre 完整實機重現\n- 新跑 43-cell OA 匯入／原生顯示、classic Interactive／RVE 16 項全 0。\n- 原始 S6 在 Calibre 自寫草稿得到 GDS100 27 筆；19 註記群放大 1.3 另存、實體六層 XOR0、16 TEXT 不變，同規則降為 0。\n- 原始版 OA 明確 200／8191 與 GUI 自動匯出交叉檢查：200／預設出現 GDS3 XOR25744 nm²、原始 pre-DRC 8 筆；8191 全層 XOR0、0 筆。\n- 空白 OA 再重建、15 金屬網／14 heater／33 光學連接、16 負例均通過；保留實際 CAD 畫面、Runset、log 與可追溯封裝。\n- 單頁總報告新增實機章節，現為 20 個完整來源區塊／55 圖；394 選項／42 數值輸入與原分頁一致，桌機／手機／列印／連結檢查通過。\n- 舊 19 技術分頁、原 S6／規格相位／M1 M2 ZIP 保留；D 槽唯讀。\n')
files=[];omit={'tools','history','__pycache__','.matplotlib','controlled_cases','test_temp'}
for directory,dirs,names in os.walk(ROOT):
 directory=Path(directory);dirs[:]=[d for d in dirs if d not in omit and not d.startswith('browser-profile') and not (d=='work' and directory!=ROOT)]
 for name in names:
  p=directory/name
  if p==ROOT/'manifest.json' or p.suffix=='.pyc' or name=='.cgidrcdb':continue
  files.append(dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
save(ROOT/'manifest.json',dict(root=str(ROOT),current_step='M3 S2 + native Virtuoso/Calibre reproduction',current_report='Lab06b_index.html',report_type='single continuous first-person report',reader_revision='17 steps + fresh native-CAD extension + 2 full appendices; 55 images; no learner acceptance/submission forms',policy='C-only work; D read-only',files=sorted(files,key=lambda r:r['path'])))
root_manifest=load(BASE/'manifest.json');root_manifest.update(current_step='M3 S2 + native CAD reproduction',reader_revision='Single continuous report with actual Virtuoso/Calibre reproduction',reader_verification='Lab06b/evidence/virtuoso_reproduction.json');root_manifest['root_files']=[dict(path=r['path'],sha256=sha(BASE/r['path'])) for r in root_manifest['root_files']];save(BASE/'manifest.json',root_manifest)
ignore=shutil.ignore_patterns('__pycache__','*.pyc','.matplotlib','browser-profile*','work','controlled_cases','test_temp','.cgidrcdb')
for folder in ['assets','course','analysis','scripts','config','evidence','reference','delivery']:shutil.copytree(ROOT/folder,REVIEW/'Lab06b'/folder,dirs_exist_ok=True,ignore=ignore)
shutil.copytree(HERE,REVIEW/'Lab06b/work/virtuoso_reproduction',dirs_exist_ok=True,ignore=ignore)
shutil.copy2(ROOT/'work/single_report/out/report_sources.json',REVIEW/'Lab06b/work/single_report/out/report_sources.json')
for name in ['Lab06b_index.html','study.html','course_overview.html','README_Lab06b_Course.md','manifest.json']:shutil.copy2(ROOT/name,REVIEW/'Lab06b'/name)
for name in ['Lab06b_index.html','README.md','manifest.json']:shutil.copy2(BASE/name,REVIEW/name)
for row in files:
 p=REVIEW/'Lab06b'/row['path'];assert p.is_file() and sha(p)==row['sha256'],row['path']
print(json.dumps(dict(status='passed',previous_technical_files_unchanged=len(unchanged),mirrored_files_verified=len(files),sections=20,images=55,zip_files=package['files'],D_writes=False,review=str(REVIEW/'Lab06b/Lab06b_index.html')),ensure_ascii=False,indent=2))
