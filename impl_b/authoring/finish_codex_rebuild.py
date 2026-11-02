from pathlib import Path
import hashlib
import json
import shutil

WORK = Path(__file__).resolve().parent
BASE = WORK.parent / 'outputs/EDA_Codex'
ROOT = BASE / 'Lab06b'

native_python = Path('C:/luceda/luceda_2026033/envs/ipkiss3/python.exe')
if not native_python.is_file():
    raise SystemExit('Configured native Python was not found; do not use an old project alias.')
config = {'schema': 'EDA_Codex independent path scheme v1', 'root': 'C:\\EDA_Codex',
          'projects': {'Lab06b': 'C:\\EDA_Codex\\Lab06b'},
          'windows': {'python_executable': str(native_python), 'ipkiss_python': str(native_python),
                      'pdk_cornerstone': 'C:\\Users\\yangc\\luceda\\libraries\\cornerstone_2.6.luceda1',
                      'klayout_exe': '', 'drc_deck': 'Lab06b/reference/Lab06a/cornerstone_Si220_passive.lydrc'},
          'wsl': {'meep_distribution': '', 'meep_environment': ''},
          'note': 'Independent settings. Installed native tools may be shared; project files are physical copies. EDA readiness must be validated separately.'}
(BASE / 'EDA_paths.json').write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
deck = Path('D:/LAB/Lab06a/design/common/drc/cornerstone_Si220_passive.lydrc')
if deck.is_file():
    shutil.copy2(deck, ROOT / 'reference/Lab06a'/deck.name)
provenance_path = ROOT / 'evidence/provenance.json'
provenance = json.loads(provenance_path.read_text(encoding='utf-8'))
for row in provenance['raw_field_data']:
    original = Path(row['original'])
    dest = ROOT / 'sources/Lab01a/out' / original.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(original, dest)
    if hashlib.sha256(dest.read_bytes()).hexdigest() != row['sha256']:
        raise SystemExit('Raw field copy verification failed.')
    row.update(included=True, copied_to=dest.relative_to(ROOT).as_posix(),
               note='Physical copy included; existing simulation data, no new FDTD run.')
provenance['deployment_root'] = 'C:\\EDA_Codex\\Lab06b'
provenance['independent_project_files'] = True
provenance_path.write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding='utf-8')
shutil.copy2(WORK / 'check_report.py', ROOT / 'scripts/check_report.py')

# Include the authoring sources so future edits can be rebuilt from this version.
authoring = ROOT / 'authoring'
authoring.mkdir(exist_ok=True)
for name in ['build_codex_course.py', 'finish_codex_rebuild.py', 'env_audit_codex.py', 'smoke_mzi.py', 'check_report.py']:
    shutil.copy2(WORK / name, authoring / name)
(authoring / 'README.md').write_text('''# 教材重建來源

這些檔案是本版的編寫與核對來源；build_codex_course.py 在作者工作目錄執行時會從 D:/LAB 唯讀取得原始教材。
學員執行入口是 ../scripts/run_m0_s1.ps1，不需要執行作者建置程式。
課程 HTML、圖片、原始 NPZ 與歷史封存均已實體包含在本版，日常閱讀與 M0 S1 不依賴 D 槽。
''', encoding='utf-8')
(BASE / 'Lab06b_index.html').write_text('''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0;url=Lab06b/Lab06b_index.html"><title>EDA_Codex｜Lab06b 課程入口</title></head><body><p><a href="Lab06b/Lab06b_index.html">開啟 Lab06b 完整報告</a></p></body></html>''', encoding='utf-8')
(BASE / 'README.md').write_text('''# EDA_Codex 獨立課程

正式位置：C:\\EDA_Codex
完整報告：Lab06b/Lab06b_index.html（也可直接開根目錄 Lab06b_index.html）
完整規劃：Lab06b/course/plan.html
第一步：Lab06b/course/m0_s1.html
光場分析：Lab06b/analysis/lab01a_7_6.html

## 執行 M0 S1

在 PowerShell 執行：

    Set-Location -LiteralPath 'C:\\EDA_Codex\\Lab06b'
    & .\\scripts\\run_m0_s1.ps1

工具路徑從本根目錄 EDA_paths.json 讀取，或以 -PythonExe 指定另一個實際 Python。
本課程是獨立實體副本；原教材留在原位置。歷史結果存 reference/，本輪新結果存 evidence/。
目前完成完整規劃、M0 S1 基礎實驗與 Lab01a 7.6 分析；後續 PDK／版圖／DRC 依規劃逐步進行。
''', encoding='utf-8')
print('Independent root completed:', BASE)
