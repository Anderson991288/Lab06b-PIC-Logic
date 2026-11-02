from pathlib import Path
from html import escape
from urllib.parse import urlsplit, unquote
import hashlib
import json
import math
import re
import shutil
import zipfile
import numpy as np

WORK = Path(__file__).resolve().parent
ROOT = WORK.parent / 'outputs/EDA_Codex/Lab06b'
OLD = Path('D:/LAB/Lab06b/C01')
LAB01 = Path('D:/LAB/Lab01a')
DATE = '2026-10-30'


def put(name, text):
    path = ROOT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def copy(source, name):
    dest = ROOT / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


CSS = '''
:root{--paper:#f4f6f9;--ink:#17263b;--muted:#526379;--blue:#155bd0;--line:#d9e1ec;--mint:#e8f5ee;--amber:#fff3d7;--white:#fff}*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:28px}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.8 "Microsoft JhengHei","Noto Sans TC",Arial,sans-serif}a{color:var(--blue);text-underline-offset:4px}a:hover{color:#073b8f}button,input,textarea{font:inherit}button,.button{display:inline-block;padding:9px 17px;background:var(--blue);color:white;border:0;border-radius:6px;text-decoration:none;cursor:pointer}button:hover,.button:hover{background:#0b429c;color:white}.button.secondary{background:#eaf0fc;color:#124a9e}.top{background:#10233e;color:white;padding:14px max(24px,calc((100vw - 1400px)/2));display:flex;justify-content:space-between;align-items:center;gap:20px}.top a{color:#d9e7ff;text-decoration:none}.top small{color:#afc2de}.layout{max-width:1400px;margin:auto;display:grid;grid-template-columns:240px minmax(0,1fr)}aside{padding:32px 22px;position:sticky;top:0;height:100vh;overflow:auto;border-right:1px solid var(--line)}aside a{display:block;padding:8px 10px;margin:3px 0;text-decoration:none;border-radius:5px;color:var(--muted);font-size:14px}aside a.active{background:#dfeafe;color:#124caa;font-weight:bold}aside strong{display:block;font-size:12px;letter-spacing:1.3px;color:#63748b;margin:20px 10px 10px}main{min-width:0;padding:36px 42px 70px}.eyebrow{font-size:12px;font-weight:bold;letter-spacing:1.7px;color:var(--blue);text-transform:uppercase}.hero{padding:28px 32px;background:white;border:1px solid var(--line);border-top:4px solid var(--blue);border-radius:8px;margin-bottom:24px}h1{font-size:clamp(27px,3vw,39px);line-height:1.35;letter-spacing:-.6px;margin:10px 0 15px}h2{font-size:25px;margin:36px 0 15px;line-height:1.5}h3{font-size:19px;margin:20px 0 10px}p{margin:10px 0 17px}.lead{font-size:18px;max-width:860px}.muted,figcaption,footer{color:var(--muted);font-size:14px}.tag{font-size:12px;display:inline-block;background:#e8effa;color:#174780;padding:3px 9px;border-radius:4px;margin:3px 6px 3px 0}.tag.ok{background:var(--mint);color:#256142}.tag.wait{background:var(--amber);color:#77530d}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin:20px 0}.card,section.panel{background:white;border:1px solid var(--line);border-radius:8px;padding:22px}.card h3{margin-top:8px}.card .num{font-size:30px;color:var(--blue);font-weight:bold;line-height:1.4}.callout{border-left:4px solid var(--blue);padding:14px 18px;background:#eaf1fd;margin:18px 0}.callout.warn{background:var(--amber);border-color:#c18b12}.callout.good{background:var(--mint);border-color:#3b8a5b}table{width:100%;border-collapse:collapse;background:white;font-size:14px;margin:12px 0 22px}caption{text-align:left;font-weight:bold;padding:10px 0;color:#31465e}th,td{padding:12px 13px;border:1px solid var(--line);text-align:left;vertical-align:top}th{background:#edf2f9}td:first-child{font-weight:600}pre{background:#11263f;color:#e4edfa;padding:18px 20px;border-radius:6px;overflow:auto;line-height:1.65;font-size:13px;tab-size:2}code{font-family:Consolas,monospace;overflow-wrap:anywhere}p code,li code,td code{background:#eaf0f8;padding:1px 4px;border-radius:3px}figure{margin:22px 0;padding:18px;border:1px solid var(--line);border-radius:6px;background:white}figure img{max-width:100%;height:auto;display:block;margin:auto}figcaption{padding-top:12px;line-height:1.7}details{background:white;border:1px solid var(--line);padding:12px 18px;margin:12px 0;border-radius:6px}summary{font-weight:bold;cursor:pointer}ul,ol{padding-left:24px}li{margin:7px 0}.scroll{overflow-x:auto}textarea{width:100%;min-height:100px;border:1px solid #b4c5dd;padding:12px;border-radius:5px;background:#fbfdff}label{display:block;margin:14px 0 6px}.step{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:20px;background:#eef3fb;border-radius:6px}.step span{background:white;border:1px solid #c3d1e6;padding:8px 13px;border-radius:5px}.split{display:grid;grid-template-columns:1fr 1fr;gap:18px}svg.diagram{width:100%;height:auto;display:block}.progress{height:7px;background:#d9e3f3;border-radius:10px;margin:14px 0}.progress div{height:100%;background:#2264d9;width:5.56%;border-radius:10px}.answers{font-variant-numeric:tabular-nums;font-family:Consolas,monospace;background:#eaf3fc;padding:16px;border-radius:6px}footer{border-top:1px solid var(--line);margin-top:38px;padding-top:20px}.print{float:right;background:#e5ecf7;color:#183d73}a:focus-visible,button:focus-visible,summary:focus-visible{outline:3px solid #e2a400;outline-offset:3px}@media(max-width:1000px){main{padding:26px}.grid{grid-template-columns:1fr 1fr}.layout{grid-template-columns:205px minmax(0,1fr)}}@media(max-width:760px){.layout{display:block}aside{height:auto;position:static;padding:15px;border-bottom:1px solid var(--line);border-right:0}aside strong{display:none}aside a{display:inline-block;padding:6px;font-size:13px}main{padding:18px}.hero{padding:21px}.grid,.split{grid-template-columns:1fr}.top{padding:12px 18px}.top small{display:none}figure{padding:10px}th,td{padding:9px;min-width:100px}.print{float:none;margin-bottom:10px}}@media print{aside,.top,.print,button,.no-print{display:none!important}.layout{display:block}body,main{background:white;padding:0;font-size:11pt}.hero{border:0;padding:0}h1{font-size:24pt}h2{break-after:avoid}figure,.card,tr{break-inside:avoid}a{color:inherit}pre{white-space:pre-wrap;background:#f1f1f1;color:black}.grid{grid-template-columns:1fr 1fr}details{display:block}.scroll{overflow:visible}}
'''


NAV = [('home', 'Lab06b_index.html', '總覽與學習入口'), ('plan', 'course/plan.html', '完整規劃／路徑方案'),
       ('m0', 'course/m0_s1.html', 'M0 S1｜第一個可重現實驗'), ('field', 'analysis/lab01a_7_6.html', 'Lab01a §7.6｜光場圖分析'),
       ('source', 'reference/source_context.html', '來源與舊教材對照')]


def page(name, title, eyebrow, intro, body, active, tags=''):
    prefix = '../' if '/' in name else ''
    nav = ''.join(f'<a class="{"active" if key == active else ""}" href="{prefix}{url}">{label}</a>' for key, url, label in NAV)
    html = f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}｜Lab06b</title><link rel="stylesheet" href="{prefix}assets/course.css"></head><body>
<header class="top"><a href="{prefix}Lab06b_index.html"><b>LAB06b</b>　PIC Chip 實作課程</a><small>單顆 B7 · 學員版 · {DATE}</small></header><div class="layout"><aside><strong>LEARNING WORKSPACE</strong>{nav}<strong>本輪進度</strong><p class="muted">全課程已規劃<br>M0 S1 已建置並驗證基礎實驗<br>EDA 工具鏈待 M0 S2 驗證</p><a href="{prefix}evidence/m0_s1/environment.json">查看環境盤點 JSON</a><a href="{prefix}evidence/m0_s1/smoke_mzi.json">查看基礎實驗 JSON</a></aside><main><button class="print" onclick="window.print()">列印／另存 PDF</button><div class="hero"><div class="eyebrow">{eyebrow}</div><h1>{title}</h1><p class="lead">{intro}</p>{tags}</div>{body}<footer>Lab06b 學員實作版 v1 · {DATE}（Asia/Taipei）<br>主目錄：<code>C:\\EDA_Codex\\Lab06b</code>。新實作、歷史證據與學員作答分開記錄；尚未進行的製程／版圖檢查均標示為待完成。</footer></main></div></body></html>'''
    put(name, html)


def table(caption, headers, rows):
    return f'<div class="scroll"><table><caption>{caption}</caption><thead><tr>'+''.join(f'<th>{h}</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{v}</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'


def pre(text):
    return '<pre><code>'+escape(text)+'</code></pre>'


ROOT.mkdir(parents=True, exist_ok=True)
put('assets/course.css', CSS)
for folder in ['course', 'analysis', 'config', 'scripts', 'src/components', 'src/circuits', 'src/layout', 'src/verification', 'learner', 'evidence/m0_s1', 'evidence/field', 'results/simulation', 'results/layout', 'results/drc', 'delivery', 'history']:
    (ROOT / folder).mkdir(parents=True, exist_ok=True)
    if folder.startswith(('src/', 'results/', 'delivery')):
        put(folder+'/README.md', '# '+folder+'\n\n此目錄保留給後續實作；目前未產生新的 PIC／GDS／DRC 結果。\n')
for script in ['env_audit.py', 'smoke_mzi.py']:
    copy(WORK / ('env_audit_codex.py' if script == 'env_audit.py' else script), 'scripts/'+script)

put('scripts/run_m0_s1.ps1', r'''param([string]$PythonExe)
$ErrorActionPreference = 'Stop'
$courseRoot = Split-Path -Parent $PSScriptRoot
if (-not $PythonExe) {
    $pathConfig = Join-Path (Split-Path -Parent $courseRoot) 'EDA_paths.json'
    if (-not (Test-Path -LiteralPath $pathConfig -PathType Leaf)) { throw 'Missing independent EDA_paths.json. Supply -PythonExe explicitly.' }
    $toolPaths = Get-Content -LiteralPath $pathConfig -Raw | ConvertFrom-Json
    $PythonExe = $toolPaths.windows.python_executable
}
if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) { throw "Python executable not found: $PythonExe" }
Push-Location -LiteralPath $courseRoot
try {
    & $PythonExe scripts/env_audit.py
    if ($LASTEXITCODE -ne 0) { throw 'Environment baseline failed. Read evidence/m0_s1/environment.json.' }
    & $PythonExe scripts/smoke_mzi.py
    if ($LASTEXITCODE -ne 0) { throw 'MZI check failed. Read evidence/m0_s1/smoke_mzi.json.' }
} finally { Pop-Location }
''')
course_config = {'version': 1, 'date': DATE, 'planned_root': 'C:\\EDA_Codex\\Lab06b', 'source_course_actual': str(OLD),
                 'source_course_requested': 'D:\\LAB\\Lab06b\\.codex\\C01', 'source_path_note': 'Requested .codex/C01 not found; actual C01 verified read-only.',
                 'architecture': {'macro': 'B7', 'modes': 5, 'mzi_count': 7, 'phase_count': 14,
                                  'ops_zero_based': [[0, 0], [3, 0], [1, 1], [0, 2], [2, 2], [1, 3], [3, 3]],
                                  'inputs': ['x1', 'x2', 'x3', 'x4', 'R'], 'readout_zero_based': [1, 3]},
                 'functions': ['AND2', 'OR2', 'XOR2', 'AND4', 'OR4'], 'reference_amplitude': 3,
                 'decision': 'delta=P(out1)-P(out3); delta>0 => 1; delta<0 => 0; |delta|<=epsilon => boundary',
                 'acceptance': {'patterns_per_function': 16, 'total_patterns': 80, 'epsilon': 1e-10},
                 'progress': {'M0_S1': 'material and baseline experiment implemented; learner submission pending', 'M0_S2': 'EDA prerequisites not yet validated', 'remaining': 'planned'}}
put('config/course.json', json.dumps(course_config, ensure_ascii=False, indent=2))
put('config/tools.example.json', json.dumps({'python_executable': '', 'ipkiss_python_executable': '', 'pdk_module': 'cornerstone', 'pdk_version': '', 'klayout_executable': '', 'drc_deck': '', 'drc_deck_sha256': '', 'wsl_distribution': '', 'meep_environment': '', 'note': 'Fill with actual installation paths and versions; this file does not install or validate tools.'}, indent=2))
put('learner/m0_s1_observations.template.json', json.dumps({'learner_name': '', 'date': '', 'python_executable': '', 'actual_course_root': '', 'smoke_cases_passed': None, 'field_vs_power_explanation': '', 'theta_zero_output_port': '', 'pi_input_phase_combines_to': '', 'eda_missing_items': [], 'evidence_paths': [], 'instructor_review': 'pending'}, ensure_ascii=False, indent=2))

# Original C01 remains unchanged; the readable adaptation is a distinct filename.
shutil.copytree(OLD, ROOT / 'reference/C01', dirs_exist_ok=True,
                ignore=shutil.ignore_patterns('__pycache__', '.matplotlib', 'study.html', 'study.candidate.html', 'outline.html', 'history', 'AGENTS.md'))
(ROOT / 'sources').mkdir(exist_ok=True)
with zipfile.ZipFile(ROOT / 'sources/C01_original.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for file in OLD.rglob('*'):
        if file.is_file() and not any(part in ('__pycache__', '.matplotlib') for part in file.relative_to(OLD).parts):
            z.write(file, 'C01/'+file.relative_to(OLD).as_posix())
for filename, newname in [('study.html', 'reader.html'), ('outline.html', 'outline.reader.html')]:
    text = (OLD / filename).read_text(encoding='utf-8')
    text = text.replace('outline.html', 'outline.reader.html')
    def remap(match):
        url = match.group(1)
        if url.startswith('../../../Lab06a/'):
            return 'href="../source_context.html#b7"'
        if url.startswith('../../../Lab01a/'):
            return 'href="../source_context.html#lab01a"'
        return match.group(0)
    text = re.sub(r'href="([^"]+)"', remap, text)
    if filename == 'outline.html':
        counter = [0]
        def add_caption(match):
            counter[0] += 1
            return '<table><caption>原大綱表 '+str(counter[0])+'</caption>'
        text = re.sub(r'<table>', add_caption, text)
    banner = '<div style="padding:16px;background:#fff0c9;color:#413313;font:16px/1.7 Microsoft JhengHei,sans-serif;border-bottom:2px solid #c59926"><b>歷史教材閱讀版</b>：本頁保留原 C01 課程內容與歷史結果；不代表本輪已重跑 EDA。跨實驗室連結改由來源對照頁說明；可執行的新主線從 M0 S1 開始。 <a href="../../Lab06b_index.html">返回新版總入口</a> · <a href="../../sources/C01_original.zip">下載未修改原始教材封存</a></div>'
    text = text.replace('<body>', '<body>'+banner, 1)
    put('reference/C01/'+newname, text)

provenance = {'date': DATE, 'source_course': str(OLD), 'source_study_sha256': sha(OLD / 'study.html'),
              'source_outline_sha256': sha(OLD / 'outline.html'), 'original_files_modified': False,
              'archive': 'sources/C01_original.zip', 'readable_adaptation': 'reference/C01/reader.html',
              'readable_changes': ['Added historical-result banner', 'Rebound cross-lab links to portable source context page', 'Linked adapted outline', 'Added captions to original outline tables'],
              'field_figures': [], 'raw_field_data': []}
for file in ['meep_tbu_field.png', 'edge_coupler_side.svg', 'ec_tip_modes.png', 'meep_mmi_paper_a.png', 'meep_mmi_paper_b.png']:
    source = LAB01 / 'figures' / file
    copy(source, 'assets/field/'+file)
    provenance['field_figures'].append({'original': str(source), 'sha256': sha(source), 'copied_to': 'assets/field/'+file})
for file in ['meep_tbu_field.py', 'meep_mmi_paper.py', 'ec_mode_plot.py']:
    copy(LAB01 / file, 'reference/Lab01a/'+file)
copy(LAB01 / 'out/bend_shapes.json', 'reference/Lab01a/out/bend_shapes.json')
copy(LAB01 / 'out/meep_mmi_paper.log', 'evidence/field/meep_mmi_paper.original.log')
field_rows = []
for name in ['in1_t0', 'in1_tpi2', 'in12_tpi2']:
    source = LAB01 / f'out/tbu_field_{name}.npz'
    with np.load(source) as d:
        po = [float(v) for v in d['p_out']]
        row = {'case': name, 'theta_rad': float(d['theta']), 'number_of_sources': int(d['n_src']),
               'output_power': po, 'total_transmission': sum(po), 'out1_fraction_of_transmitted': po[0]/sum(po),
               'extinction_db': 10*math.log10(max(po)/min(po)), 'source_sha256': sha(source)}
    field_rows.append(row)
    provenance['raw_field_data'].append({'original': str(source), 'sha256': sha(source), 'included': False,
                                        'note': 'Summary extracted from existing NPZ; no FDTD rerun. Raw arrays remain at source.'})
put('evidence/field/derived_metrics.json', json.dumps({'scope': 'new arithmetic derived from inherited NPZ; no new EM simulation', 'cases': field_rows}, indent=2))
put('evidence/provenance.json', json.dumps(provenance, ensure_ascii=False, indent=2))
for file in ['mzi.py', 'macro4.py', 'bigmesh.py']:
    copy(Path('D:/LAB/Lab06a/design/common') / file, 'reference/Lab06a/'+file)

modules = [
('M0', '環境與第一個實驗', '2 h', [
('S1', '建立工作目錄、盤點工具、跑理想 MZI', '1 h', 'environment.json、smoke_mzi.json、學習記錄', '文件可讀、證據可寫、五個理想案例通過；能解釋場與功率', '已實作／學員待提交'),
('S2', '驗證 IPKISS／PDK／KLayout 與執行環境', '1 h', '版本／授權實測、PDK cell 清單、規則檔 hash', '實際 Python 能建立 PDK MMI、求 S、輸出並回讀最小 GDS；工具缺漏先補齊', '待開始')]),
('M1', '先理解光，再理解 B7 邏輯', '5 h', [
('S1', '讀 Lab01a §7.6，追蹤 MMI → MZI 光場', '1.5 h', '場圖標註、相位／歸一化／flux 判讀表', '分清場圖亮度、總穿透、分光比與相干條件', '待開始；補充分析已可閱讀'),
('S2', '從單顆 MZI 到七顆 B7 與十四個相位', '1.5 h', 'B7 五路埠圖、OPS 表、逐層光場記錄', '標對 in0–4、out0–4；讀取 out1／out3；矩陣連乘與逐層追蹤一致', '待開始'),
('S3', '固定讀取規則，切換五種邏輯', '2 h', '相位設定、80 筆真值表、最小 margin', 'AND2／OR2／XOR2／AND4／OR4 各 16 筆通過，零附近視為邊界；保留未作用輸入的測試', '待開始')]),
('M2', '把功能轉為可驗證的電路規格', '4 h', [
('S1', '畫出 PIC／外部設備邊界與完整 I/O', '1 h', '功能規格、光學埠表、14 路控制表', '光源、調變、接收比較器與 heater driver 邊界清楚；R 振幅 3 對應功率 9', '待開始'),
('S2', 'PDK／Caphe 電路模擬與理想模型對照', '1.5 h', 'S／U 矩陣、80 筆模擬、模型限制', '核對上下埠映射、波長與相位順序；所有指定功能通過；差異能追溯', '待開始'),
('S3', '元件場模擬計畫與光學預算', '1.5 h', 'MMI／彎道／相位器驗證計畫、損耗與讀取裕量表', '依裝妥環境選跑場模擬；相位與反射正規化清楚；未做收斂不得宣稱損耗已驗證', '待開始')]),
('M3', '從單元做出 Chip 版圖', '7 h', [
('S1', '建立 PDK MMI／相位器／MZI 單元', '1.5 h', '單元 Python、MZI GDS、ports/layers 表', '版圖和模型採同一埠序／相位位置；PDK 層與幾何有來源', '待開始'),
('S2', '放置七顆 MZI，路由五路 B7', '2 h', 'B7 core GDS、netlist、路徑長度', 'OPS 與連線一一對應；無遺漏或錯接；依規則處理彎道與間距', '待開始'),
('S3', '加入十路 EC、heater、金屬與 PAD', '2 h', 'Chip GDS、EC 表、PAD↔heater↔相位對照', '五入五出皆有去向；14 個相位控制可追蹤；PAD／共地數依設計決定', '待開始'),
('S4', '在 KLayout 做版圖審查並修正', '1.5 h', '帶座標的 review、修正前後圖、回讀結果', '接點、曲線、金屬、EC 端面逐項檢查；每個問題有關閉證據', '待開始')]),
('M4', '驗證、回填模型、交付', '6 h', [
('S1', '執行指定製程 DRC，定位與修正', '2 h', 'deck hash、log、lyrdb／summary、修正版 GDS', '本次適用的所有規則無未解違規；deck 覆蓋範圍與例外留存', '待開始'),
('S2', '光學連線與電氣開短路獨立檢查', '1.5 h', '光學拓撲、PAD 名稱、短路／斷路注入結果', '正常設計通過；注入錯接／斷路／短路能被抓到；DRC 不替代連接驗證', '待開始'),
('S3', '版圖路徑回填、重跑功能與裕量', '1.5 h', '更新後模型、80 筆結果、差異說明', '納入可取得的傳播相位與損耗；重新確認功能。無模型者列為交付缺口', '待開始'),
('S4', '產生可重現 PIC 設計包與總報告', '1 h', 'GDS、原始碼、config、manifest、報告', '從乾淨目錄可重建；model／GDS／ports／PAD／DRC 版本一致', '待開始')])]

path_tree = r'''C:\EDA_Codex\
├─ EDA_paths.json              # 本版獨立工具設定
├─ Lab06b_index.html           # 根目錄快捷入口
├─ README.md                   # 使用方式
└─ Lab06b\                    # 實體課程目錄
   ├─ Lab06b_index.html        # 完整報告入口
   ├─ course\                 # 全課程規劃與分步教材
   ├─ analysis\               # Lab01a 7.6 場圖分析
   ├─ assets\                 # 樣式、原圖
   ├─ config\                 # B7 規格與工具範本
   ├─ scripts\                # M0 S1 執行與檢查入口
   ├─ src\                    # components/circuits/layout/verification
   ├─ learner\                # 學員作答
   ├─ evidence\               # 本版重新執行的證據
   ├─ results\                # 後續 simulation/layout/drc
   ├─ delivery\               # 最終 PIC 設計包
   ├─ reference\              # 歷史閱讀資料
   ├─ sources\                # 原始封存、場圖 NPZ
   └─ history\                # 修改記錄與備份'''

home = '''<div class="callout good"><b>本輪完成：</b>全課程規劃、C:\\EDA_Codex 路徑方案、M0 S1 教材與可執行基礎實驗，以及 Lab01a §7.6 的原圖分析。學員作答尚待提交；IPKISS／PDK、FDTD 與新 Chip 版圖尚未執行。</div>
<div class="grid"><article class="card"><div class="num">01</div><h3>先看完整規劃</h3><p>24 小時、5 個模組、16 個步驟。每步都有輸入、操作、交付與驗收。</p><a href="course/plan.html">查看路徑與全課程 →</a></article><article class="card"><div class="num">02</div><h3>開始 M0 S1</h3><p>用選定的 Python 建立可重現紀錄，親手驗證光場相加、相位與功率。</p><a class="button" href="course/m0_s1.html">開始第一個實驗</a></article><article class="card"><div class="num">03</div><h3>補上光場傳播分析</h3><p>從原圖、原始 NPZ 與程式，讀懂切換、分光、合光和模場耦合。</p><a href="analysis/lab01a_7_6.html">閱讀 Lab01a §7.6 →</a></article></div>
<h2 id="target">我們要做出的 PIC 是什麼？</h2><p>主作業固定為單顆 <b>B7（Brick 7）</b>：七顆可調 Mach–Zehnder Interferometer（MZI），五條光路，其中四路承載資料 x1–x4，第五路是相干參考光 R。學員會把功能模型，逐步實作成具有光學 EC、heater 控制、金屬與 PAD 的 Chip 設計。</p>
<div class="step"><span>看懂光場</span> → <span>算出邏輯</span> → <span>完成電路</span> → <span>建立版圖</span> → <span>驗證並交付</span></div>
'''
home += table('表 1｜固定的設計主線', ['項目', '課程約定'], [
('光學輸入', 'x1–x4 → in0–in3；R → in4。R=3 指歸一化光場振幅。'),
('光學輸出', 'out0–out4 全部保留並規劃去向；邏輯讀取 out1／out3（教學名稱 o2／o4）。'),
('可程式化控制', '七顆 MZI × θ／φ，共十四個相位。先設定功能，再輸入光資料；不把 heater 熱速度當資料頻寬。'),
('學習目標', 'AND2、OR2、XOR2、AND4、OR4；每個函數檢查四路資料的全部 16 組，共 80 筆。'),
('最終成果', '可重現、可審查的 PIC 設計包；晶片製造、封裝與實測須另行安排。')])
home += '''<h2 id="map">整份報告從這裡讀</h2>'''
home += table('表 2｜報告導覽與目前狀態', ['內容', '位置', '狀態'], [
('完整課程與路徑方案', '<a href="course/plan.html">course/plan.html</a>', '已完成規劃'),
('M0 S1 學員實作', '<a href="course/m0_s1.html">course/m0_s1.html</a>', '教材與基礎實驗已驗證；學員待提交'),
('Lab01a §7.6 光場分析', '<a href="analysis/lab01a_7_6.html">analysis/lab01a_7_6.html</a>', '原圖已補入；既有 NPZ 數值已重新計算'),
('原課程完整閱讀版', '<a href="reference/C01/reader.html">reference/C01/reader.html</a>', '歷史教材；非本輪重跑結果'),
('原課程大綱閱讀版', '<a href="reference/C01/outline.reader.html">reference/C01/outline.reader.html</a>', '保留作來源對照'),
('環境與基礎實驗紀錄', '<a href="evidence/m0_s1/environment.json">environment.json</a> ／ <a href="evidence/m0_s1/smoke_mzi.json">smoke_mzi.json</a>', '本輪實際執行'),
('來源／檔案完整性', '<a href="evidence/provenance.json">provenance.json</a> ／ <a href="evidence/report_checks.json">report_checks.json</a>', '來源 hash、連結與結構檢查'),
('後續 Chip 成果', '<a href="delivery/README.md">delivery/</a>', '尚未產生；M4 S4 交付')])
home += '''<h2>如何使用這份教材</h2><ol><li>先在規劃頁確認目錄、工具需求與各階段通過條件。</li><li>打開 M0 S1，依序「先預測 → 親手操作 → 看輸出 → 解釋 → 留證據」。</li><li>學員作答保存到 learner/；本輪執行輸出保存到 evidence/。舊課程結果只用於比較。</li><li>每步通過才更新進度；尚未完成的模組由規劃頁查看，不建立空白的假成果頁。</li></ol><div class="callout">所有課程頁以相對路徑連結，可直接開啟本機 HTML。互動示範在瀏覽器計算；腳本請從 PowerShell 使用明確的 Python 路徑執行。</div>'''
page('Lab06b_index.html', '從第一個光場實驗，做到 PIC Chip', 'LEARN → BUILD → VERIFY', '以學員親手操作為主線，從 MZI 的光場與功率，走到單顆 B7 的模型、版圖、介面與設計交付。', home, 'home', '<span class="tag">24 h 建議課程</span><span class="tag">7 MZIs / 5 optical modes</span><span class="tag ok">目前：M0 S1</span>')

plan = '<h2 id="paths">一、C:\\EDA_Codex 路徑方案</h2><p>正式根目錄採用 <code>C:\\EDA_Codex\\Lab06b</code>。學員從根目錄的 <code>Lab06b_index.html</code> 開始；教材、原始碼與實作證據分別保存。課程以相對路徑定位檔案，不將製作教材時的 Python 路徑寫死在程式內。</p>'+pre(path_tree)
plan += '''<p><b>獨立重建：</b>本版建立在全新的實體根目錄；課程、工具設定、報告、原圖與原始場資料都有自己的檔案。工具設定只引用已核對的原生安裝位置。原 C01 與 Lab01a 僅作唯讀來源，其教材及場資料已封存至本版 sources/，學員閱讀與 M0 S1 執行不依賴來源磁碟。</p><div class="callout">本次先完成全課程規劃並開始 M0 S1。後續模組照下表分步實作；不將舊 GDS、DRC 或 Caphe 紀錄當作本輪完成證據。</div>
<h2 id="pedagogy">二、教學設計與 HTML 優化</h2><ol><li><b>固定一條主線：</b>用單顆 B7 做到 Chip，不在學員主線引入多架構搜尋或涵蓋率最佳化。</li><li><b>每步五段：</b>問題與預測 → 觀念圖 → 學員操作 → 可觀察結果 → 驗收與下一步。</li><li><b>雙層閱讀：</b>新版以短頁面與共同導覽呈現；需要細節時連到原課程閱讀版、程式與證據。</li><li><b>圖有依據：</b>圖說包含來源、方法、單位、歸一化、輸入條件與限制。示意圖、數值模擬及量測分開標示。</li><li><b>可追溯：</b>新結果放 evidence／results；原教材放 reference／sources。記錄版本、輸入、程式、工具與 SHA-256。</li><li><b>方便本機閱讀：</b>離線相對連結、繁體中文、手機版與列印樣式；表格加標題，互動練習提供文字數值。</li></ol>
<h2 id="curriculum">三、完整課程規劃：24 小時、16 步</h2><p>時間為教學建議，未包含軟體安裝、授權申請、長時間場模擬與製造等待。已有 Python 與 EDA 經驗者可縮短練習時間；工具尚未具備者在 M0 S2 先補齊。</p>'''
for module, title, hours, rows in modules:
    plan += f'<h3 id="{module.lower()}">{module}　{title} · {hours}</h3>'
    plan += table(f'{module}｜操作、成果與通過條件', ['步驟／建議時間', '學員操作', '交付成果', '通過條件', '目前狀態'], [(f'{module} {s}<br>{time}', name, output, acceptance, status) for s, name, time, output, acceptance, status in rows])
plan += '''<h2 id="gates">四、關卡、依賴與修正流程</h2>'''
plan += table('表｜各階段的交接', ['關卡', '必要依賴', '未通過時'], [
('G0：工作環境', 'M0 S1 的本機基礎實驗 → M0 S2 的 PDK／授權／最小 GDS 實測', '可先學觀念；M2 PDK 模擬與 M3 版圖待工具實測通過。'),
('G1：功能基準', '相干輸入、B7 OPS、相位檔、埠序、80 筆真值表', '核對輸入編碼、相位順序、上下埠與判讀門檻，再談元件損耗。'),
('G2：可審查版圖', '功能規格、PDK cells、EC／PAD 介面、review 清單', '回到對應單元或路由參數修改，保留前後圖與版本。'),
('G3：幾何與連接', '指定 deck 的 DRC、光路連接、電氣開短路與命名', '修正並重跑；不同規則引擎／匯出版本的結果分開保存。'),
('G4：交付一致', '回填後功能、最終 GDS、埠表、PAD 表、工具版本與 manifest', '缺少元件或傳播模型即列缺口，不把理想模型通過視為實體功能保證。')])
plan += '''<h2 id="tools">五、工具與備援安排</h2>'''
plan += table('表｜工具用途與目前要求', ['工具', '用途', '何時必須具備'], [
('Python 3.10+ 標準函式庫', 'M0 S1 環境盤點與理想 MZI；不需 pip 套件', 'M0 S1'),
('IPKISS／Caphe ＋ CORNERSTONE PDK', 'PDK 元件、電路與版圖；以實際授權相容環境為準', 'M0 S2 實測後供 M2／M3 使用'),
('NumPy／Matplotlib', '矩陣運算、結果分析與繪圖；使用同一授課環境的版本', 'M1 S2 起'),
('KLayout ＋ 指定製程規則', 'GDS 回讀、版圖審查、DRC', 'M0 S2 盤點；M3／M4 執行'),
('WSL／Meep 或已授權等效工具', '選做元件場模擬；本輪只分析既有場資料', 'M2 S3 場模擬支線'),
('Virtuoso／Calibre', '若實際交付平台需要，安排進階匯入與檢查', '選修；不作為 M0 S1 的前置條件')])
plan += '''<p>將實際路徑與版本填入 <a href="../config/tools.example.json">tools.example.json</a> 的副本。環境盤點中的「模組可找到」只表示 Python 能定位模組；授權、cell 建立、S-matrix 與 GDS 仍須在 M0 S2 實際驗證。</p>
<h2 id="delivery">六、最終交付規格</h2><p>delivery/ 最終收錄：重建入口與說明、功能與工具設定、Python 原始碼、最終 GDS、光學與 PAD CSV、相位設定、回填後 80 筆真值表、DRC 規則 hash 與報告、連接檢查與失敗注入、review 修正記錄，以及檔案 manifest。這代表完成可審查的設計資料包；製造／封裝與量測成果在另行實作後才加入。</p><p><a class="button" href="m0_s1.html">依規劃開始 M0 S1 →</a></p>'''
page('course/plan.html', '完整規劃與 C:\\EDA_Codex 路徑方案', 'COURSE PLAN · 16 STEPS', '將舊 C01 重整為「學員實際設計一顆 PIC」的學習流程；先建立可重現環境，再逐關完成模型、版圖與交付。', plan, 'plan')

diagram = '''<svg class="diagram" viewBox="0 0 900 250" role="img" aria-labelledby="mzi-title"><title id="mzi-title">理想 MZI：兩個 MMI、上臂相位與兩個輸出。索引零為下埠。</title><defs><marker id="arrow" markerWidth="9" markerHeight="7" refX="7" refY="3.5" orient="auto"><path d="M0 0L7 3.5L0 7" fill="#155bd0"/></marker></defs><rect width="900" height="250" rx="8" fill="#f5f8fd"/><g fill="none" stroke="#155bd0" stroke-width="5"><path d="M100 170H240 M100 80H240 M310 80H580 M310 170H580 M650 80H795 M650 170H795" marker-end="url(#arrow)"/></g><g fill="#dbe8ff" stroke="#155bd0" stroke-width="2"><rect x="240" y="47" width="70" height="156" rx="8"/><rect x="580" y="47" width="70" height="156" rx="8"/></g><rect x="390" y="60" width="120" height="40" rx="5" fill="#102c55"/><g font-family="Microsoft JhengHei,Arial" font-size="18" fill="#17263b"><text x="32" y="75">in2</text><text x="32" y="165">in1</text><text x="805" y="75">out2</text><text x="805" y="165">out1</text><text x="252" y="132">MMI</text><text x="592" y="132">MMI</text><text x="365" y="222">相位加在上臂；光由左向右</text></g><text x="437" y="87" fill="white" font-family="Arial" font-size="21">θ</text></svg>'''
commands = r'''Set-Location -LiteralPath 'C:\EDA_Codex\Lab06b'
# 讀取現有工具路徑；其他電腦上課時，先填入該機設定。
$ToolPaths = Get-Content -LiteralPath 'C:\EDA_Codex\EDA_paths.json' -Raw | ConvertFrom-Json
$PythonExe = $ToolPaths.windows.python_executable
& $PythonExe --version
& .\scripts\run_m0_s1.ps1 -PythonExe $PythonExe'''
m0 = '''<div class="callout"><b>本步問題：</b>我能否在自己的工作目錄執行同一份程式、得到相同的相位／功率結果，並把環境與輸出留下來？<br><b>預計 60 分鐘：</b>讀目標 5 分 → 盤點 15 分 → 實驗 20 分 → 比較原圖 10 分 → 作答 10 分。</div>
<h2 id="goal">1．今天要完成什麼</h2><ol><li>能指出根目錄、主報告、程式、config 與 evidence 分別在哪裡。</li><li>記錄實際 Python 路徑與版本，知道 EDA 工具有哪些尚待驗證。</li><li>親手跑五個理想 MZI 案例，分清光場相加與功率相加。</li><li>用自己的話解釋「改相位會改輸出」，並提交學習記錄。</li></ol><p>不需先裝 IPKISS、Meep 或 NumPy；本步腳本僅使用 Python 標準函式庫。這讓第一個實驗可以先建立可重現的基準，下一步再驗證實際製程工具。</p>
<h2 id="predict">2．先預測，再執行</h2><p>先看圖，將答案記在下方學習記錄：光只從下方 in1 輸入，θ=0 時，最後會從哪一個輸出離開？若 θ=π/2，會不會每路各得到一半？兩路同時輸入時，總輸入功率應如何固定？</p><figure>'''+diagram+'''<figcaption>圖 1｜教學示意，非製程版圖。為了對照 Lab01a 場圖，本步使用下埠 index 0、上埠 index 1；θ 加在上臂。B7 的 in0–in4 命名會在 M1 另行對照。</figcaption></figure>
<p>一顆理想 MMI 的光場混合規則為 H=[[1,i],[i,1]]/√2；此處 MZI=H·diag(1,e<sup>iθ</sup>)·H。先將兩路<b>複數光場</b>相加，輸出功率才是 |E|²。兩個相同功率、不同相位的輸入，可能完全走向不同輸出。</p>
<h2 id="setup">3．確認目錄與 Python</h2><p>先直接開啟 <code>C:\\EDA_Codex\\Lab06b\\Lab06b_index.html</code>，確認能從導覽來到本頁。再開 PowerShell，使用以下命令。Python 路徑請從已安裝環境確認；若尚未安裝，可由講師提供 Python 3.10+ 或後續 Luceda 相容環境。</p>'''+pre(commands)+'''
<p>若系統阻擋 PowerShell 腳本，可直接執行以下兩個 Python 命令，不必調整全機 ExecutionPolicy：</p>'''+pre('& $PythonExe .\\scripts\\env_audit.py\n& $PythonExe .\\scripts\\smoke_mzi.py')+'''
<p><a href="../scripts/env_audit.py">閱讀環境盤點程式</a> · <a href="../scripts/smoke_mzi.py">閱讀 MZI 實驗程式</a> · <a href="../scripts/run_m0_s1.ps1">閱讀 PowerShell 入口</a></p>
<h2 id="observe">4．檢查五個實際輸出</h2>'''
m0 += table('表 1｜理想模型的預期結果', ['案例', '輸入條件', 'θ', 'P(out1), P(out2)', '學員要觀察的事'], [
('cross', '[1, 0]，總功率 1', '0', '0, 1', '兩臂再合流後，能量集中到交叉輸出。'),
('split', '[1, 0]，總功率 1', 'π/2', '0.5, 0.5', '相位改變，分配變成一半一半。'),
('bar', '[1, 0]，總功率 1', 'π', '1, 0', '相位再改變，能量切換到另一埠。'),
('combine_pi', '[1/√2, −1/√2]，相對相位 π', 'π/2', '1, 0', '每路功率 0.5；先混合光場，全部合到 out1。'),
('combine_0', '[1/√2, +1/√2]，相對相位 0', 'π/2', '0, 1', '每路功率完全一樣，相位改變就合到 out2。')])
m0 += pre('M0 S1 baseline: PASS\n...\ncross [\'0.000000\', \'1.000000\'] PASS\nsplit [\'0.500000\', \'0.500000\'] PASS\nbar [\'1.000000\', \'0.000000\'] PASS\ncombine_pi [\'1.000000\', \'0.000000\'] PASS\ncombine_0 [\'0.000000\', \'1.000000\'] PASS\n5/5 PASS')
m0 += '''<p>預期輸出是程式的檢查基準；你自己的執行結果要在 evidence/m0_s1/ 裡確認。浮點數可能接近 0 而非恰好 0，程式以 10⁻¹² 誤差容限核對功率分配與總功率守恆。</p>
<h2 id="interactive">5．先在瀏覽器轉動相位</h2><section class="panel"><p>這是同一個理想模型的快速預習；請仍執行上方 Python，才能留下你所用環境的證據。</p><label for="theta">θ：<b id="angle">0.00 π</b></label><input id="theta" type="range" min="0" max="2" step="0.01" value="0" style="width:100%"><label for="input-mode">輸入狀態</label><select id="input-mode"><option value="single">單路 in1，總功率 1</option><option value="anti">兩路等功率，相對相位 π</option><option value="same">兩路等功率，相對相位 0</option></select><div id="live-result" class="answers" aria-live="polite"></div><p class="muted">P(out1)+P(out2)=1；本圖沒有損耗、反射或雜訊。相位與埠定義同圖 1。</p></section>
<script>
(()=>{const theta=document.querySelector('#theta'),mode=document.querySelector('#input-mode');function refresh(){let t=Number(theta.value)*Math.PI,p;if(mode.value==='single')p=Math.sin(t/2)**2;else if(mode.value==='anti')p=(1+Math.sin(t))/2;else p=(1-Math.sin(t))/2;document.querySelector('#angle').textContent=Number(theta.value).toFixed(2)+' π';document.querySelector('#live-result').textContent='P(out1) = '+p.toFixed(6)+'   |   P(out2) = '+(1-p).toFixed(6);}theta.addEventListener('input',refresh);mode.addEventListener('change',refresh);refresh()})();
</script>
<h2 id="field">6．和 Lab01a 的原圖比較</h2><p>打開 <a href="../analysis/lab01a_7_6.html#mzi">§7.6 MZI 三態分析</a>：原圖切換態的總穿透約 0.7886，分光態約 0.7727，並非理想模型的 1。先指出它們的<b>輸出去向是否一致</b>，再解釋為何不能直接把差額當作真實 Chip 損耗。</p><div class="callout warn">基礎實驗通過只證明理想模型與目前 Python 可執行。它沒有驗證 PDK、授權、元件尺寸、heater 電壓、GDS、DRC 或實際 Chip 功能。</div>
<h2 id="submit">7．留下你的學習記錄</h2><p>填寫下面的欄位後產生 JSON，複製到文字編輯器，以 UTF-8 存為 learner/m0_s1_observations.json；也可直接複製 <a href="../learner/m0_s1_observations.template.json">作答範本</a>。作答只保留在本頁記憶體，離開頁面前請自行保存。</p>
<section class="panel"><label for="learner-name">學員姓名</label><input id="learner-name" autocomplete="name"><label for="learner-python">我的 Python 完整路徑與版本</label><input id="learner-python" style="width:100%"><label for="learner-notes">預測、五筆結果、光場與功率的差別、還缺哪些工具</label><textarea id="learner-notes" placeholder="請先記下預測，再寫出執行結果與自己的解釋。"></textarea><button id="generate-notes">產生學習記錄 JSON</button><p id="notes-status" role="status"></p><textarea id="notes-json" aria-label="可複製的學習記錄 JSON" readonly hidden style="min-height:220px"></textarea></section>
<script>document.querySelector('#generate-notes').addEventListener('click',()=>{let obj={learner_name:document.querySelector('#learner-name').value,python:document.querySelector('#learner-python').value,observations:document.querySelector('#learner-notes').value,date:new Date().toISOString(),step:'M0 S1',instructor_review:'pending'};let output=document.querySelector('#notes-json');output.hidden=false;output.value=JSON.stringify(obj,null,2);output.focus();output.select();document.querySelector('#notes-status').textContent='已產生並選取 JSON。按 Ctrl+C 複製，存為 learner/m0_s1_observations.json。';});</script>
<h2 id="acceptance">8．本步驗收與下一步</h2>'''
m0 += table('表 2｜M0 S1 驗收清單', ['項目', '證據', '如何判定'], [
('檔案與環境', '<a href="../evidence/m0_s1/environment.json">environment.json</a>', 'baseline_passed=true；actual root 與 Python 路徑明確。若在預覽資料夾執行，root_matches_plan=false 是正常且必須保留的紀錄。'),
('理想模型', '<a href="../evidence/m0_s1/smoke_mzi.json">smoke_mzi.json</a>', '五筆全通過，知道總功率固定為 1。'),
('概念理解', 'learner/m0_s1_observations.json', '能說明相位不同但輸入功率相同時，輸出為何不同；能說明 field intensity 與 flux 的差別。'),
('工具缺口', 'environment.json 的 packages／eda_probes', '列出尚缺工具；不把 available=true 等同授權成功。'),
('進度', '學員提交＋講師確認', '本輪已完成教材與作者端驗證；學員本人完成後才記為學習通過。')])
m0 += '''<p><b>接續 M0 S2：</b>在實際 IPKISS 環境選擇 Python，必要時執行 <code>env_audit.py --probe-eda</code>（可能連線到已設定的授權服務），再實測 PDK MMI 的 S-matrix、最小 GDS 輸出／回讀與 DRC deck。尚缺授權或 PDK 時，先保留盤點結果，不能將工具關卡標為完成。</p><details><summary>常見問題與修正</summary><ul><li><b>python 指向 Windows Store：</b>改用確實存在的 python.exe 完整路徑；盤點 JSON 會記錄 sys.executable。</li><li><b>ModuleNotFoundError：</b>本步兩個腳本不需第三方套件。若是後續 EDA，確認目前 Python 是否是授課環境。</li><li><b>找不到檔案：</b>確認根目錄是 C:\\EDA_Codex\\Lab06b，腳本會以自身位置計算相對路徑。</li><li><b>5/5 失敗：</b>先核對上下埠順序、θ 加在哪一臂、MMI 的 i 與 1/√2，以及是否先求光場再取模平方。</li><li><b>EDA readiness 未驗證：</b>在未提供 EDA 工具鏈的環境為預期狀態；它不影響理想模型基礎實驗的執行。</li></ul></details>'''
page('course/m0_s1.html', 'M0 S1｜建立可重現的第一個光場實驗', 'MODULE 0 · STEP 1 · 60 MIN', '先不用製程工具，親手跑一個理想 MZI：確認環境、預測輸出、驗證結果，並留下自己的學習證據。', m0, 'm0', '<span class="tag ok">教材與基礎實驗已驗證</span><span class="tag wait">學員提交待完成</span>')

field = '''<div class="callout"><b>資料性質：</b>本頁分析 D:\\LAB\\Lab01a\\design_report_v2.html 的 §7.6 與 §7.6.1。圖與電磁場來自既有模擬；本輪重新讀取 NPZ 計算穿透、分光與消光比，沒有重新執行 FDTD。<a href="../evidence/field/derived_metrics.json">數值 JSON</a> · <a href="../evidence/provenance.json">來源與 hash</a>。</div>
<h2 id="read">1．先辨認這是哪一種圖</h2><p>沿傳播方向 x 與橫向 y 展開的彩色圖，是元件內部場分佈，不是晶片照片或 GDS。這些原圖使用 Meep 2D 有效折射率近似（EIM）與連續波場，外觀可類似 BPM 圖；求解方法仍是 FDTD，不能只憑外觀將它稱為 BPM 計算。</p>'''
field += table('表 1｜讀光場圖前先核對', ['欄位', '本資料的條件', '判讀限制'], [
('橫軸／縱軸', 'x、y，單位 µm；光大致由左向右', 'MMI 場圖為平面圖；edge coupler 模場圖是截面，不能共用座標解讀。'),
('波長／偏振', '1550 nm；2D TE 為 Ex、Ey、Hz', 'TE 是此 2D 軸向約定；不等於完整三維偏振與模式驗證。'),
('MMI／MZI 色階', '|Ex|²+|Ey|² 除以輸入波導峰值；上限 0.5', '紅色可能已飽和；寬區單點變暗，不代表相同程度的功率損耗。'),
('複數 CW 場', '穩態複數光場的模平方包絡，比例於時間平均場強', '物理場的時間平均帶 1/2 因子；在相同歸一化比值中抵消。不是任意瞬時實場的平方。'),
('輸出功率', '原程式由 flux monitor 積分後除以輸入截面的淨 flux', '亮度不是功率積分；若反射顯著，淨 flux 不等於獨立參考模擬的入射功率。'),
('EC 色階', '|E| 振幅、峰值正規化', '不能把它與 |E|² 場圖的顏色或 1/e² 輪廓直接等同。')])
field += '''<p>複數穩態場的時間平均關係見 <a href="https://meep.readthedocs.io/en/latest/FAQ/#how-do-i-compute-the-time-average-of-the-harmonic-fields">Meep 官方 FAQ</a>。若需分出前向、後向及特定導模功率，應採 <a href="https://meep.readthedocs.io/en/latest/Mode_Decomposition/">Meep 官方模態分解</a>，不能只看場圖顏色。</p>
<h2 id="mzi">2．完整 MZI：切換、分光、相干合光</h2><figure><img src="../assets/field/meep_tbu_field.png" alt="Lab01a 原始 MZI 三種狀態光場，單路切換、50:50 分光、兩路相干合光"><figcaption>圖 1｜沿用 Lab01a 圖 7-12。每個 MZI 含兩顆 CORNERSTONE 幾何 2×2 MMI；上臂施加等效 θ。原圖使用共同的單路全功率輸入波導峰值作為強度基準；合光案例兩個輸入各為半功率。圖中較窄臂長為示範模型，非完整 Chip 實體尺寸。</figcaption></figure><p>從左到右追蹤：輸入 taper → 第一個 MMI 的多模干涉 → 兩條臂 → 上臂相位改變 → 第二個 MMI 再干涉 → 輸出。第一個 MMI 會把單路光分到兩臂，第二個 MMI 依兩臂相位關係把光重新分配；不能將它解釋成光只走某一臂。</p>'''
field += table('表 2｜本輪由既有 NPZ 重新計算（非新場模擬）', ['狀態', 'P(out1)／P(out2)', '總穿透 T', '判讀'], [
('a．單路 in1，θ=0', '0.002488／0.786129', '0.788618', '主輸出 out2；ER=24.996 dB，約 25.0 dB。原報告用粗略值寫約 26 dB，本頁改用原始數值。'),
('b．單路 in1，θ=π/2', '0.382475／0.390191', '0.772667', '以已穿透總功率為分母，out1／out2=49.501%／50.499%；不是各佔輸入 50%。'),
('c．等功率雙路，相對相位 π，θ=π/2', '0.770549／0.001869', '0.772418', '主輸出 out1；ER=26.151 dB。兩路振幅各 1/√2，保持總輸入功率 1。')])
field += '''<p>公式：T=P₁+P₂；η₁=P₁/T；ER=10 log₁₀(P主/P漏)。這裡的 P 已按原程式的輸入淨 flux 歸一化，因此 T 應讀為<b>該監測配置下的傳輸比</b>。要作嚴格入射功率、反射與損耗評估，需要參考直波導正規化與模態／反射監測。</p><div class="callout warn"><b>不能直接沿用的結論：</b>T≈0.77–0.79 的差額不能全部歸因於「粗網格數值損耗」，也不能當成實際器件插入損耗。尚需網格／時間／PML 收斂、導模分解、監測截面與能量收支，才能區分反射、輻射、未收集模態和數值誤差。</div>
<p><b>與實際 Chip 的差別：</b>原程式將相位臂直段縮為 20 µm（報告實際為 184 µm），用核心折射率變化等效相移，並以 GAMMA=1.07 校正。此係數屬該 2D 模型的經驗修正，不是普遍材料常數；不能從此推算 heater 電壓、熱功率或熱頻寬。</p>
<h2 id="mmi">3．單顆 MMI：看自成像，也看幾何差異</h2><div class="split"><figure><img src="../assets/field/meep_mmi_paper_a.png" alt="一入二出 MMI 的時間平均場包絡原圖"><figcaption>圖 2｜Lab01a 圖 7-15，教學 1×2 MMI：W=6 µm，既有掃描最佳 L=31 µm；不是 B7 使用的 2×2 MMI。</figcaption></figure><figure><img src="../assets/field/meep_mmi_paper_b.png" alt="CORNERSTONE 幾何二入二出 MMI 的時間平均場包絡原圖"><figcaption>圖 3｜Lab01a 圖 7-16，2×2 MMI：W=6 µm、L=42.5 µm，taper 20 µm（0.45→1.5 µm）、埠 y=±1.015 µm。</figcaption></figure></div>
<p>窄波導進入寬 MMI 後會激發多個橫向模態；沿 x 方向累積不同相位，再於設計輸出位置重建光場。兩張圖的入射條件、輸出位置與長度不同，花紋本來就不必相同。<b>不要因為 1×2 圖較平滑，就拿它替換 B7 的 2×2 元件模型。</b></p>'''
field += table('表 3｜既有 MMI log 所記錄的結果', ['元件', '總穿透／比例', '如何使用'], [
('1×2 教學元件', 'T=0.988；兩路穿透比例 0.500／0.500；−10log₁₀T≈0.052 dB', '用來理解對稱自成像與長度掃描；31 µm 是此掃描的最佳值。'),
('2×2 CORNERSTONE 幾何', 'T=0.966；bar／cross=0.500／0.500；−10log₁₀T≈0.150 dB', '數值來自既有四捨五入 log；不代表 3D 製程量測或模型已收斂。'),
('輸出 taper 明暗拍頻', '原文解釋為導模與輻射場拍頻', '本輪視為待驗證的物理解釋；應以模態頻譜、監測位置、時間與網格收斂排除反射／數值假象。')])
field += '''<p>可核對 <a href="../evidence/field/meep_mmi_paper.original.log">原始 MMI 執行 log</a> 與 <a href="../reference/Lab01a/meep_mmi_paper.py">原始程式</a>。圖使用雙線性插值，顯示平滑程度會受繪圖方式影響；不要把視覺平滑當作模擬收斂的證據。</p>
<h2 id="ec">4．邊緣耦合器：場變大，還要算耦合</h2><figure><img src="../assets/field/edge_coupler_side.svg" alt="晶片端面、inverse taper 與光纖的側視概念圖"><figcaption>圖 4｜Lab01a 圖 7-13，耦合側視概念示意，未按比例。這是介面說明，不是沿器件的實算場傳播圖。</figcaption></figure><figure><img src="../assets/field/ec_tip_modes.png" alt="三種晶片尖端截面與光纖模場輪廓的原始比較圖"><figcaption>圖 5｜Lab01a 圖 7-14，femwell 截面模態，1550 nm、TE。色階為振幅 |E|；原報告指出薄矽尖端模場約 2.7×1.9 µm。尺寸與重疊結果屬既有模型輸出。</figcaption></figure><p>尖端變薄、變窄可讓模態擴展到包覆層，改善與小模場光纖的空間匹配，但也可能增加有限 BOX 下的基板洩漏與對位敏感度。場看起來更大，並不自動代表總耦合損耗更小。</p><p>課程要學員分別檢查：① 規範化模式重疊；② taper 沿長度的轉換／反射；③ substrate leakage；④ 水平／垂直位移與偏振；⑤ 端面、膠材與封裝條件。截面重疊只回答其中一部分，不能替代完整光纖到 Chip 的耦合驗證。</p>
<h2 id="rerun">5．後續重跑的驗證計畫</h2>'''
field += table('表 4｜M2 S3 場模擬支線的操作規劃', ['項目', '操作', '預定保留證據'], [
('幾何來源', '核對 PDK cell 的版本、上下埠、主體與 taper 尺寸；與版圖一致', '幾何 JSON、PDK 版本、截圖與 source hash'),
('相位與輸入', '分別跑單路 θ=0、π/2、π 與雙路相位掃描，保持相同總入射功率', 'theta／input phase／source amplitudes／output powers'),
('功率正規化', '建立直波導參考；分開量入射、反射、前向導模與輻射', 'reference run、mode coefficients、flux 與能量收支'),
('收斂', '至少比較三組解析度、穩態／DFT 時窗、PML 厚度與監測位置；確認主要指標趨勢', '收斂表與差異；授課目標建議 T 絕對差 <1% 且相位差 <0.01 rad，ER 另訂絕對誤差'),
('模型對照', '將場模擬取得的複數傳輸／反射與電路模型比較，而非只對照亮度', 'S-matrix、參考面定義、差異與未納入效應')])
field += '''<p>原腳本備查：<a href="../reference/Lab01a/meep_tbu_field.py">meep_tbu_field.py</a>、<a href="../reference/Lab01a/meep_mmi_paper.py">meep_mmi_paper.py</a>、<a href="../reference/Lab01a/ec_mode_plot.py">ec_mode_plot.py</a>。本包附 MZI 使用的 bend_shapes.json；原始大型 NPZ 已獨立複製到 sources/Lab01a/out，來源 hash 可核對。原腳本需適用的 Meep／femwell 環境，並非 M0 S1 的執行項目。</p>
<h2 id="exercise">6．學員分析題</h2><ol><li>在圖 1 圈出第一個 MMI、相位臂、第二個 MMI，以及各狀態的主輸出。</li><li>用 b 的原始數字算 T 與分光比，解釋「每路約一半」的分母是什麼。</li><li>比較 c 與 M0 S1 的 combine_pi；說明為何兩個輸入各用 1/√2，而不是各用 1。</li><li>兩個相同輸入功率，改相位為何能從 out1 換到 out2？先用光場作答，再談功率。</li><li>列出要把本圖結果用於 B7 Chip 預算前，仍須補做的三項驗證。</li></ol><p><a class="button" href="../course/m0_s1.html#field">回到 M0 S1，完成比較與作答</a></p>'''
page('analysis/lab01a_7_6.html', 'Lab01a §7.6｜光場傳播圖分析', 'FIELD MAPS · SOURCE-BASED ANALYSIS', '用原圖、程式與既有數據，讀懂光在 MMI、MZI 與邊緣耦合器裡如何傳播，以及每張圖真正能證明的範圍。', field, 'field', '<span class="tag">既有場圖</span><span class="tag ok">原始 NPZ 數值已核對</span><span class="tag wait">未重跑 FDTD</span>')

context = '''<h2 id="b7">1．C01 與 Lab06a 的來源對照</h2><p>使用者指定的 .codex/C01 不存在；本輪確認實際教材在 D:\\LAB\\Lab06b\\C01。新版主線從該目錄的 study.html、outline.html、pic_spec.json 及教學程式整理而來。</p><p><a href="C01/reader.html">完整舊課程閱讀版</a> · <a href="C01/outline.reader.html">舊課程大綱閱讀版</a> · <a href="../sources/C01_original.zip">未修改的原始 C01 封存 ZIP</a></p><p>舊教材存在多處 ../../../Lab06a、../../../Lab01a 的跨目錄連結，與目前實體 C01 位置不相符。新閱讀版把這些連結轉到本頁的來源對照，維持離線閱讀；原始 HTML 的位元內容保留在 ZIP，可用 provenance 的 SHA-256 核對。</p>'''
context += table('表 1｜主要來源與新課程用途', ['來源', '用途', '本包位置'], [
('C01/study.html、outline.html', 'MZI 邏輯、B7、電路／版圖／DRC 歷史教學', '<a href="C01/reader.html">reader.html</a> ／ <a href="C01/outline.reader.html">outline.reader.html</a>'),
('C01/pic_spec.json', '五路埠位、十四相位、五個函數與 80 筆驗收', '<a href="C01/pic_spec.json">原規格 JSON</a> ／ <a href="../config/course.json">新課程 config</a>'),
('Lab06a/design/common/mzi.py', '原 MZI 理想傳輸矩陣、嵌入方法', '<a href="Lab06a/mzi.py">mzi.py</a>'),
('Lab06a/design/common/macro4.py', 'B7 OPS 排程與架構定義', '<a href="Lab06a/macro4.py">macro4.py</a>'),
('Lab06a/design/common/bigmesh.py', '既有模型與相位求解程式參考', '<a href="Lab06a/bigmesh.py">bigmesh.py</a>'),
('C01 的歷史結果', '對照既有相位、S／U、版圖、DRC 與修正方式', 'reference/C01/outputs、evidence；皆為歷史紀錄')])
context += '''<div class="callout warn">舊課程中的完成標記、Caphe 通過、GDS、Calibre／KLayout 紀錄與架構涵蓋率，均屬歷史內容。本輪未重驗 181／222 等涵蓋統計，也未把它列為學員主作業；本輪僅驗證 M0 S1 基礎實驗和場圖衍生數值。</div>
<h2 id="lab01a">2．Lab01a 的來源與補充</h2><p>主要來源為 D:\\LAB\\Lab01a\\design_report_v2.html 的 §7.6／§7.6.1；該報告其他章節（例如 §6.11 相位或熱模型）仍以原檔為準。本包新增的 <a href="../analysis/lab01a_7_6.html">光場分析頁</a> 提供五張原圖、NPZ 衍生數值、原程式與限制說明。</p><p>本輪特別修正：以既有原始 NPZ 算出切換態 ER≈25.0 dB；將強度包絡與功率 flux 分開；對未經收斂的損耗歸因與 taper 拍頻解釋保留不確定性。</p>
<h2 id="official">3．官方方法參考</h2><ul><li><a href="https://meep.readthedocs.io/en/latest/FAQ/">Meep FAQ</a>：複數 CW 場、時間平均與收斂。</li><li><a href="https://meep.readthedocs.io/en/latest/Mode_Decomposition/">Meep Mode Decomposition</a>：前／後向模式與模態功率正規化。</li></ul><p>官方頁面供方法核對；離線教學所需的主要敘述、圖與既有數據已寫在本課程內。程式與數值的來源細節見 <a href="../evidence/provenance.json">provenance.json</a>。</p>
<h2>4．可執行範圍</h2><p>本輪新建且已驗證的入口是 scripts/env_audit.py、scripts/smoke_mzi.py 與 scripts/run_m0_s1.ps1。reference/ 的 Python 與歷史 shell 腳本保留作閱讀參考，可能含舊的相對路徑、WSL 使用者名稱或授權環境；後續每步重新整理後才放入 src／scripts。</p>'''
page('reference/source_context.html', '來源、版本與舊教材對照', 'PROVENANCE · READABLE ARCHIVE', '保留舊課程的內容與證據，同時清楚標示本輪重新實作的範圍，讓學員知道每個數字從哪裡來。', context, 'source')

put('README_Lab06b_Course.md', '''# Lab06b 學員實作課程

正式根目錄：C:\\EDA_Codex\\Lab06b

請先開啟 Lab06b_index.html。完整規劃在 course/plan.html；本輪實作 M0 S1。

1. 選擇 Python 3.10+ 的實際 python.exe。
2. 執行 scripts/run_m0_s1.ps1 -PythonExe '實際 python.exe 完整路徑'。
3. 檢查 evidence/m0_s1/ 的 environment.json 與 smoke_mzi.json。
4. 學員作答存 learner/，不要將作者端驗證當作學員本人完成。

Lab01a §7.6 已補五張原圖與原始 NPZ 衍生分析。無新 FDTD、PDK、Chip 版圖或 DRC。
reference/ 是歷史教材及其既有結果；sources/C01_original.zip 是未修改原始封存。
後續依 M0 S2 → M1 → M2 → M3 → M4 逐步實作。
''')
put('history/CHANGELOG.md', f'''# 修改記錄\n\n## {DATE}\n\n- 新建完整課程規劃、C:\\EDA_Codex 路徑方案與根目錄入口。\n- 開始 M0 S1：環境盤點、理想 MZI 實驗、互動預習與學員記錄。\n- 補入 Lab01a §7.6 原圖與既有 NPZ 數值分析。\n- 舊 study.html 未修改；獨立產生 reader.html，保留原始封存與 SHA-256。\n- 本輪未執行 PDK／FDTD／版圖生成／DRC。\n''')
print('Built:', ROOT)
print('New lesson pages: 5; source figures: 5; MZI inherited cases:', len(field_rows))
