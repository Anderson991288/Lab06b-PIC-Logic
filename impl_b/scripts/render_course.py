from report_policy import clean_course_html
"""Build readable index, complete plan and M0 S1 from this project's evidence."""
from pathlib import Path
from html import escape
import json
import re

ROOT=Path(__file__).resolve().parents[1]
DATA_PATH=ROOT/'work/m0_s1/out/toolchain_check.json'
DATA=json.loads(DATA_PATH.read_text(encoding='utf-8')) if DATA_PATH.exists() else {'items':[],'core_passed':False,'summary':{},'timestamp':'尚未執行'}
LAYOUT_PATH=ROOT/'work/m0_s1/out/mzi_drc_result.json'
LAYOUT=json.loads(LAYOUT_PATH.read_text(encoding='utf-8')) if LAYOUT_PATH.exists() else {}
SMOKE_PATH=ROOT/'evidence/m0_s1/smoke_mzi.json'
SMOKE=json.loads(SMOKE_PATH.read_text(encoding='utf-8')) if SMOKE_PATH.exists() else {'passed':False}


def table(title,headers,rows):
    return '<div class="scroll"><table><caption>'+title+'</caption><thead><tr>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(c)+'</td>' for c in r)+'</tr>' for r in rows)+'</tbody></table></div>'


def pre(text):
    return '<pre><code>'+escape(text)+'</code></pre>'


def page(rel,title,lead,content,active):
    prefix='../' if '/' in rel else ''
    links=[('home','Lab06b_index.html','總覽與報告入口'),('plan','course/plan.html','完整規劃與路徑'),('m0','course/m0_s1.html','M0 S1｜工具鏈實作'),('field','analysis/lab01a_7_6.html','Lab01a §7.6 光場分析'),('foundation','course/m0_s1_foundation.html','補充｜理想 MZI 實驗'),('source','reference/source_context.html','來源與舊教材')]
    nav=''.join(f'<a class="{"active" if k==active else ""}" href="{prefix}{url}">{label}</a>' for k,url,label in links)
    text=f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}｜Lab06b</title><link rel="stylesheet" href="{prefix}assets/course.css"></head><body><header class="top"><a href="{prefix}Lab06b_index.html"><b>LAB06b</b>　PIC Chip 學員實作課程</a><small>2026-10-31 · C 槽版</small></header><div class="layout"><aside><strong>學習與實作入口</strong>{nav}<strong>本輪狀態</strong><p class="muted">課程 17 步已規劃<br>M0 S1：{'核心工具鏈通過' if DATA['core_passed'] else '執行中／見檢查結果'}<br>理想 MZI：{'5/5 通過' if SMOKE['passed'] else '待執行'}</p><a href="{prefix}work/m0_s1/out/toolchain_check.json">工具鏈原始證據 JSON</a><a href="{prefix}work/m0_s1/out/mzi_drc_result.json">GDS／DRC 原始證據 JSON</a></aside><main><button class="print" onclick="window.print()">列印／另存 PDF</button><div class="hero"><div class="eyebrow">LEARN → BUILD → VERIFY</div><h1>{title}</h1><p class="lead">{lead}</p><span class="tag">17 步 · 建議 18 小時</span><span class="tag">單顆 B7／7 MZIs</span></div>{content}<footer>正式根目錄：<code>C:\\EDA_Codex\\Lab06b</code>。教材、程式、設定與結果保存於本專案；原 C01 保留作來源。<br>本輪只開始 M0 S1；後續 B7 電路、Chip 版圖與最終交付依關卡進行。學員作答需本人完成。</footer></main></div></body></html>'''
    target=ROOT/rel
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(clean_course_html(text),encoding='utf-8')


tree=r'''C:\EDA_Codex\Lab06b\
├─ Lab06b_index.html          # 整份可讀報告入口
├─ EDA_paths.json             # 本專案工具位置設定
├─ course\                   # 每步教材、完整規劃、版圖圖片
├─ analysis\                 # Lab01a 7.6 完整圖文分析
├─ assets\                   # 共用樣式、五張原始場圖
├─ config\                   # B7 規格、步驟定義
├─ scripts\                  # 一鍵執行 M0 S1、由證據產生報告
├─ work\common\              # PDK、GDS、DRC 共用程式與 deck
├─ work\m0_s1\out\           # 本輪 GDS、DRC、工具鏈 JSON 與 log
├─ tools\KLayout\            # 本專案可攜式工具
├─ evidence\                 # 理想模型、場圖數值、驗證、來源雜湊
├─ learner\                  # 學員記錄與作答
├─ results\ / delivery\      # 後續 B7 模擬／Chip／交付成果
├─ reference\ / sources\     # 舊教材閱讀版、原始封存與 NPZ
├─ history\                  # 更新前備份與變更紀錄
└─ C01\                      # 原課程，保持原位'''
status='核心工具鏈通過' if DATA['core_passed'] else '部分通過，待完成項見 M0 S1'
home=f'''<div class="callout good"><b>本輪範圍：</b>完整課程規劃、C:\\EDA_Codex\\Lab06b 路徑方案、開始 M0 S1，以及 Lab01a §7.6 原圖與數據分析。<br><b>目前 M0 S1：</b>{status}。結果直接由本輪 JSON 產生。</div><div class="grid"><article class="card"><div class="num">01</div><h3>先看完整規劃</h3><p>四個模組、17 步；從學員操作、可觀察結果到驗收。</p><a href="course/plan.html">完整規劃與路徑 →</a></article><article class="card"><div class="num">02</div><h3>開始 M0 S1</h3><p>驗證工具，建立帶 heater 的 MZI，檢查正常與故障版 GDS。</p><a class="button" href="course/m0_s1.html">開始實作</a></article><article class="card"><div class="num">03</div><h3>看懂光場傳播</h3><p>五張原圖、原始 NPZ、切換／分光／合光與耦合分析。</p><a href="analysis/lab01a_7_6.html">閱讀 Lab01a §7.6 →</a></article></div><h2 id="goal">學員最後要完成什麼？</h2><p>完成一顆具有光學 I/O、heater、金屬與 PAD 的單 B7 光邏輯 PIC 設計包。B7 由七顆 MZI、五條光路與十四個 θ／φ 控制組成；四路資料 x1–x4 加相干參考光 R，最後比較 out1／out3 的功率差。</p><div class="step"><span>M0 環境與元件</span> → <span>M1 光學邏輯</span> → <span>M2 Chip 實作</span> → <span>M3 重建與驗收</span></div>'''
home+=table('表 1｜全課程總覽',['模組','建議時間／步數','學員成果','目前狀態'],[
('M0 環境與元件','3.5 h／3 步','工具鏈、MZI 測試件、光場分析、共用模型','S1 '+status),
('M1 光訊號做邏輯','5 h／5 步','B7 接線、相位設定、五函數共 80 筆真值表','規劃完成'),
('M2 PIC 實作','8 h／7 步','PDK 電路、B7 core、EC／PAD、DRC、連接與交付包','規劃完成'),
('M3 驗收與延伸','1.5 h／2 步','乾淨目錄重建、獨立檢查與差異說明','規劃完成')])
home+=table('表 2｜整份可讀取報告',['內容','入口','性質'],[
('完整規劃與路徑','<a href="course/plan.html">完整規劃</a>','全部 17 步操作、成果、關卡與時間'),
('M0 S1 主實作','<a href="course/m0_s1.html">工具鏈與 GDS／DRC</a>','本輪重新執行與驗證'),
('理想 MZI 補充','<a href="course/m0_s1_foundation.html">五個案例與互動相位</a>','標準函式庫基礎實驗'),
('Lab01a §7.6','<a href="analysis/lab01a_7_6.html">完整光場分析</a>','引用原場資料；本輪重新計算指標'),
('舊 C01 全文','<a href="reference/C01/reader.html">歷史教材閱讀版</a>','歷史成果，非本輪 Chip 重跑'),
('原始資料與來源','<a href="evidence/provenance.json">來源 JSON</a> ／ <a href="sources/C01_original.zip">原教材封存</a>','原圖與原始 NPZ 已包含於本版'),
('驗證紀錄','<a href="evidence/report_checks.json">連結／結構檢查</a>','檢查本版報告的可讀性與完整性')])
home+='<div class="callout">每一步採「問題 → 預測 → 親手操作 → 觀察輸出 → 解釋差異 → 留存證據」。學員的觀察記錄保存在 learner/；後續 Chip 版圖尚未完成，不能把歷史 GDS 視為本輪成果。</div>'
page('Lab06b_index.html','從 MZI 實驗，完成自己的 PIC Chip','以學員親手操作為主線，從光場與邏輯，走到電路、版圖、DRC 與可重現的交付。',home,'home')

sections=(ROOT/'config/plan_sections.html.txt').read_text(encoding='utf-8')
sections=re.sub(r'<a href="#lab01a">.*?</a>','<a href="../analysis/lab01a_7_6.html">光場分析頁</a>',sections)
sections=re.sub(r'(<table>.*?</table>)',lambda m:'<div class="scroll">'+m[1]+'</div>',sections,flags=re.S)
plan='<h2 id="paths">一、C:\\EDA_Codex\\Lab06b 路徑方案</h2><p>使用本專案根目錄的 EDA_paths.json；工具引用實際安裝位置，可攜工具放 tools/。專案檔案為實體檔案，程式以自身位置求相對路徑。原課程來源為 D:/LAB/Lab06b/C01，已封存於 sources/ 並提供 reference/ 閱讀版；日常操作使用本 C 槽專案。</p>'+pre(tree)
plan+='<h2>二、HTML 與教學優化</h2><ol><li>根目錄入口串接短頁面、原圖、程式與 JSON，方便逐步學習。</li><li>每步保留「先預測、再操作、看結果、能解釋」；不用已完成的歷史結果替代學員實作。</li><li>工具鏈與版圖結果由 JSON 產生頁面；場圖數字附 NPZ 來源與計算方法。</li><li>分開標示實算、引用、未執行與待驗證；圖的顏色不直接當作損耗。</li><li>備份原頁面、記錄 SHA-256；支援本機相對連結、手機與列印閱讀。</li></ol><h2>三、完整課程</h2>'+sections
plan+=table('表｜關卡與交接',['關卡','通過條件','未通過時'],[
('G0 工具鏈','IPKISS／PDK 實測、正常 MZI DRC 0 違規、F1–F8 故障命中、原始 log 留存','確認實際路徑、授權、deck 與版本，修正後重跑。'),
('G1 邏輯','固定 B7 OPS、埠序與判讀；AND2／OR2／XOR2／AND4／OR4 各 16 組，共 80 組','核對輸入編碼、相位與上下埠；零附近功率差視為邊界。'),
('G2 版圖','模型和 GDS 共用埠名與相位標籤；EC、PAD、共地與未讀取輸出皆有去向','保留問題座標與前後圖，修改 Python 參數。'),
('G3 幾何與連接','指定 deck 之適用規則通過；光學接線、電氣開短路與 PAD 命名另外驗證','幾何 DRC 不替代電路連接檢查。'),
('G4 交付','路徑回填後功能重跑，GDS、相位、埠／PAD 表、工具版本與 manifest 一致','缺少真實傳播／元件模型時，記錄限制；製造送件仍依平台簽核。')])
plan+='<h2>最終交付內容</h2><p>重建入口、Python 原始碼、工具與功能設定、最終 GDS、光學／PAD CSV、相位設定、80 筆真值表、DRC deck hash 與報告、連接檢查、故障注入、修正記錄及 manifest。這是 PIC 設計資料包；實體製造、封裝與量測在另行實作後才加入。</p><p><a class="button" href="m0_s1.html">開始 M0 S1 →</a></p>'
page('course/plan.html','完整規劃與 C 槽路徑方案','四個模組、17 個步驟，建議 18 小時；每一步都有操作、成果、依賴與驗收。',plan,'plan')

rows=[(escape(i['id']),escape(i['name']),'通過' if i['status']=='pass' else '待完成',escape(i['detail'])) for i in DATA['items']]
m0='<div class="callout"><b>本步問題：</b>能否在自己的專案目錄，從工具設定開始，實際做出一顆可開啟、可檢查的 MZI 測試件？<br>先完成工具鏈與測試件，再進入 M0 S2 的元件物理及光場。</div><h2 id="paths">1．根目錄與工具設定</h2><p>所有學員操作從 C:\\EDA_Codex\\Lab06b 開始，EDA_paths.json 與教材同根目錄。IPKISS 與 PDK 使用原生安裝路徑，KLayout 放本專案 tools/KLayout。程式不借用其他課程的設定根目錄。</p>'+pre(tree)
m0+='<h2 id="predict">2．先預測再操作</h2><ol><li>若正常版 MZI 外框內有兩個 heater，應看到幾個 MMI、哪幾個光學埠？</li><li>波導太窄、金屬太近及圖形超出外框，分別應由哪一種檢查抓到？</li><li>正常版沒有違規，是否足以證明檢查器真的有作用？請用故障注入回答。</li></ol><h2 id="do">3．學員實際執行</h2>'
m0+=pre(r'''Set-Location -LiteralPath 'C:\EDA_Codex\Lab06b'
& .\scripts\run_m0_s1.ps1''')
m0+='<p>若 PowerShell 阻擋腳本，使用實際 Python 執行以下命令；不需要變更整部電腦的執行原則：</p>'+pre(r'''$cfg = Get-Content -LiteralPath '.\EDA_paths.json' -Raw | ConvertFrom-Json
$pythonExe = $cfg.windows.ipkiss_python
& $pythonExe scripts/smoke_mzi.py
& $pythonExe work/m0_s1/build_mzi_drc.py
& $pythonExe work/m0_s1/check_toolchain.py
& $pythonExe scripts/render_course.py''')
m0+='<p>先跑 <a href="m0_s1_foundation.html">理想 MZI 五個案例</a>；再用 PDK 建正常與故障版 GDS、回讀外框、執行 DRC，最後從本輪 JSON 更新頁面。這一顆是 MZI 測試件，尚不是七顆 MZI 組成的 B7 Chip。</p><h2 id="results">4．本輪工具鏈結果</h2><p class="muted">時間：'+escape(DATA['timestamp'])+'；'+status+'。每個結果均來自本輪輸出。</p>'+table('表 1｜工具與測試件實際檢查',['編號','項目','狀態','輸出'],rows)
if LAYOUT:
    clean,fault=LAYOUT['drc_clean'],LAYOUT['drc_fault']
    m0+='<h2 id="layout">5．實際版圖與故障注入</h2>'
    m0+=f'<figure><img src="figures/m0_s1/mzi_layout.png" alt="本輪正常版帶 heater 的 MZI 測試版圖"><figcaption>圖 1｜本輪重新產生的 MZI_HT；總長 {LAYOUT["mzi"]["length"]} µm。MMI 間上／下臂長依序為 {LAYOUT["mzi"]["arm_between_mmi_upper_um"]:.3f}／{LAYOUT["mzi"]["arm_between_mmi_lower_um"]:.3f} µm。</figcaption></figure><figure><img src="figures/m0_s1/fault_layout.png" alt="本輪 MZI 故障注入版圖"><figcaption>圖 2｜MZI_HT_FAULT，F1–F4、F7–F8 為刻意違規幾何；F5 檢查宣告設計區與外框差異；F6 檢查外框外圖形。</figcaption></figure>'
    m0+=table('表｜本測試件與原 PDK 的埠名對照',['測試件外部埠','位置','相接的 PDK MMI 埠'],[('in0','上方輸入','第一顆 in2'),('in1','下方輸入','第一顆 in1'),('out0','上方輸出','第二顆 out2'),('out1','下方輸出','第二顆 out1')])
    m0+='<p>理想 MZI 補充與 Lab01a 場圖採「in1／out1 在下、in2／out2 在上」；本測試件外部埠採 0 起算。比較結果時先核對物理上下位置，再比埠名。基礎理想模型沒有包含本版圖的傳播相位與損耗。</p>'
    faultmap=[('F1','GDS39 TiN 線寬'),('F2','GDS41 金屬間距'),('F3','GDS3 波導線寬'),('F4','GDS39 TiN 間距'),('F5','宣告設計區尺寸'),('F6','外框外圖形'),('F7','GDS3 波導間距'),('F8','GDS41 金屬線寬')]
    m0+=table('表 2｜故障注入與實際命中',['故障','檢查項目','本輪命中數'],[(f,desc,fault.get('hit',{}).get(f,'DRC 未執行')) for f,desc in faultmap])
    m0+='<div class="callout">正常版 DRC：'+escape(str(clean.get('total','未執行')))+' 個標記；外框外圖形 '+str(clean['outside'])+' 個。故障版各規則須有實際命中，不能只看正常版為 CLEAN。此 deck 是製程前檢查，製造平台仍會做正式 DRC。</div>'
m0+='<h2 id="field">6．對照 Lab01a §7.6</h2><p><a href="../analysis/lab01a_7_6.html">完整分析頁</a>附五張原圖、三份原始 NPZ 的衍生數值。請分清理想矩陣的能量守恆、場模擬的 flux，以及 GDS 的幾何檢查：三者回答不同問題。切換態以原始值算出的 ER 約 25.0 dB，合光態約 26.15 dB；沒有重跑 FDTD。</p>'
m0+='<h2 id="acceptance">7．學員交付與驗收</h2>'+table('表 3｜本步完成條件',['成果','通過條件'],[
('工具設定與 JSON','路徑可用，IPKISS／PDK 與 KLayout 實測通過，原始 log 留存。'),
('正常版 GDS','可回讀，外框外 0；指定 deck 的正常版 DRC 0 標記。'),
('故障版 GDS','F1–F8 全部命中，沒有未說明的額外規則；保留檢查報告。'),
('理想 MZI 基礎實驗','五個案例通過；能分清光場、功率及相位。'),
('學員觀察記錄','使用 learner/ 範本，寫出預測、實際輸出、差異、工具版本與修正。講師驗收後才算本人完成。')])
m0+='<h2 id="files">8．程式、證據與下一步</h2><p><a href="../work/m0_s1/build_mzi_drc.py">版圖與故障注入程式</a> · <a href="../work/m0_s1/check_toolchain.py">工具鏈檢查</a> · <a href="../work/m0_s1/out/toolchain_check.json">本輪工具鏈 JSON</a> · <a href="../work/m0_s1/out/mzi_drc_result.json">本輪版圖／DRC JSON</a> · <a href="../work/m0_s1/out/MZI_HT.gds">正常版 GDS</a> · <a href="../work/m0_s1/out/MZI_HT_FAULT.gds">故障版 GDS</a> · <a href="../learner/m0_s1_observations.template.json">學員記錄範本</a></p><p>下一步 M0 S2：解讀場圖並驗證元件物理；femwell／Meep 依該步需要獨立盤點，未完成場模擬前以引用方式呈現。M0 S1 工具鏈通過不代表 B7 邏輯、Chip 連接或製造送件已完成。</p>'
page('course/m0_s1.html','M0 S1｜工具鏈、MZI 版圖與故障注入','從一份本機設定開始，建立正常與故障版 MZI，讓每一個通過標記都有可追溯的實際證據。',m0,'m0')

# Add captions to the inherited step-definition tables.
path=ROOT/'course/plan.html'
text=path.read_text(encoding='utf-8')
counter=[0]
def caption(match):
    counter[0]+=1
    return '<table><caption>課程步驟表 '+str(counter[0])+'</caption>'
text=re.sub(r'<table>(?!<caption)',caption,text)
path.write_text(text,encoding='utf-8')
for rel in ['analysis/lab01a_7_6.html','reference/source_context.html','course/m0_s1_foundation.html']:
    p=ROOT/rel
    text=p.read_text(encoding='utf-8')
    if 'foundation' not in rel:
        text=text.replace('evidence/m0_s1/environment.json','work/m0_s1/out/toolchain_check.json')
    text=text.replace('本輪僅驗證 M0 S1 基礎實驗和場圖衍生數值','本輪進行 M0 S1 工具鏈、MZI 測試件與理想實驗；實際狀態以主頁 JSON 為準')
    p.write_text(clean_course_html(text),encoding='utf-8')
config=json.loads((ROOT/'config/course.json').read_text(encoding='utf-8'))
config['progress']['M0_S1']='core toolchain passed; learner submission pending' if DATA['core_passed'] else 'core toolchain partially complete; see evidence'
(ROOT/'config/course.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'README_Lab06b_Course.md').write_text('''# Lab06b C 槽課程

根目錄：C:\\EDA_Codex\\Lab06b；入口 Lab06b_index.html。
完整規劃 course/plan.html：四模組、17 步、建議 18 小時。
開始 M0 S1：scripts/run_m0_s1.ps1。
本機工具位置由根目錄 EDA_paths.json 管理。
Lab01a 7.6 分析在 analysis/lab01a_7_6.html。
原 C01 保留原位；更新前的頁面與程式備份在 history/。
''',encoding='utf-8')
print('Rendered main report, complete 17-step plan and M0 S1:', 'PASS' if DATA['core_passed'] else 'BLOCKED')

# Keep M0 S2 lesson and progress when rebuilding the common report.
if (ROOT/"work/m0_s2/out/physics_results.json").is_file():
    import runpy
    runpy.run_path(str(ROOT/"scripts/render_m0_s2.py"),run_name="__main__")

# Preserve M0 S3 model results and navigation on every common report rebuild.
if (ROOT/"work/m0_s3/out/model_results.json").is_file():
    import runpy
    runpy.run_path(str(ROOT/"scripts/render_m0_s3.py"),run_name="__main__")

# Preserve M1 S1 on every common report rebuild.
if (ROOT/'work/m1_s1/out/encoding_results.json').is_file():
    import runpy
    runpy.run_path(str(ROOT/'scripts/render_m1_s1.py'),run_name='__main__')

# Preserve M1 S2 topology and matrix evidence on common report rebuild.
if (ROOT/'work/m1_s2/out/b7_results.json').is_file():
    import runpy
    runpy.run_path(str(ROOT/'scripts/render_m1_s2.py'),run_name='__main__')

# Preserve M1 S3 weighted sums and readout on common report rebuild.
if (ROOT/'work/m1_s3/out/readout_results.json').is_file():
    import runpy
    runpy.run_path(str(ROOT/'scripts/render_m1_s3.py'),run_name='__main__')

# Preserve M1 S4 full truth acceptance on report rebuild.
if (ROOT/'work/m1_s4/out/logic_results.json').is_file():
    import runpy
    runpy.run_path(str(ROOT/'scripts/render_m1_s4.py'),run_name='__main__')

# Preserve M1 S5 logical handoff on report rebuild.
if (ROOT/'work/m1_s5/out/handoff_results.json').is_file():
    import runpy
    runpy.run_path(str(ROOT/'scripts/render_m1_s5.py'),run_name='__main__')

# Preserve M2 S1 boundary and I/O on report rebuild.
if (ROOT/'work/m2_s1/out/boundary_results.json').is_file():
    import runpy
    runpy.run_path(str(ROOT/'scripts/render_m2_s1.py'),run_name='__main__')

# Preserve M2 S2 PDK circuit and 80-case comparison on rebuild.
if (ROOT/'work/m2_s2/out/pdk_results.json').is_file():
    import runpy
    runpy.run_path(str(ROOT/'scripts/render_m2_s2.py'),run_name='__main__')

# Preserve M2 S3 physical core and GDS readback on rebuild.
if (ROOT/'work/m2_s3/out/layout_results.json').is_file():
    import runpy
    runpy.run_path(str(ROOT/'scripts/render_m2_s3.py'),run_name='__main__')

# Preserve M2 S4 KLayout review and before/after evidence on rebuild.
if (ROOT/'work/m2_s4/out/review_results.json').is_file():
    import runpy
    runpy.run_path(str(ROOT/'scripts/render_m2_s4.py'),run_name='__main__')

# Preserve M2 S5 reference EC, PAD and GND interfaces on rebuild.
if (ROOT/'work/m2_s5/out/interface_results.json').is_file():
    import runpy
    runpy.run_path(str(ROOT/'scripts/render_m2_s5.py'),run_name='__main__')

# Preserve M2 S6 full installed pre-DRC and geometric netlist verification.
if (ROOT/'work/m2_s6/out/verification_results.json').is_file():
    import runpy
    runpy.run_path(str(ROOT/'scripts/render_m2_s6.py'),run_name='__main__')

# Preserve M2 S7 package and explicit core-plane backannotation evidence.
if (ROOT/'work/m2_s7/out/delivery_results.json').is_file():
    import runpy
    runpy.run_path(str(ROOT/'scripts/render_m2_s7.py'),run_name='__main__')

# Preserve M3 S1 clean-source rebuild and acceptance evidence.
if (ROOT/'work/m3_s1/out/acceptance_controls.json').is_file():
    import runpy
    runpy.run_path(str(ROOT/'scripts/render_m3_s1.py'),run_name='__main__')

# Preserve M3 S2 independent gdstk/Shapely crosscheck and course closeout.
if (ROOT/'work/m3_s2/out/crosscheck_results.json').is_file():
    import runpy
    runpy.run_path(str(ROOT/'scripts/render_m3_s2.py'),run_name='__main__')

# Keep the C-only workspace policy visible on report rebuild.
if (ROOT/'evidence/c_path_verification.json').is_file():
    import runpy
    runpy.run_path(str(ROOT/'scripts/render_migration_context.py'),run_name='__main__')

# Include the freshly executed native Virtuoso/Calibre extension when available.
if (ROOT/'work/virtuoso_reproduction/out/reproduction_results.json').is_file():
    import runpy
    runpy.run_path(str(ROOT/'scripts/render_virtuoso.py'),run_name='__main__')

# Finish with the continuous first-person report; keep the former hub separately.
if (ROOT/'scripts/render_study.py').is_file():
    import runpy
    runpy.run_path(str(ROOT/'scripts/render_study.py'),run_name='__main__')
