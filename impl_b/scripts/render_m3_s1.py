from report_policy import clean_course_html
"""Evidence-led clean rebuild lesson; reproducibility is distinct from calibration."""
from pathlib import Path
from html import escape
import json,re,csv
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/m3_s1/out'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
R=load(OUT/'rebuild_results.json');C=load(OUT/'acceptance_controls.json');CFG=load(ROOT/'config/course.json');A,B=R['builds']
CASES={'ideal_baseline':'理想原始基準','length_original':'線長＋原始相位','length_compensated':'線長＋模型候選','loss_original':'3 dB/cm＋原始相位','loss_compensated':'3 dB/cm＋模型候選'}
CHECK_LABELS={'zero_generated_seed':'輸入未含既有生成檔','independent_staged_common':'使用本輪暫存來源模組','core_readback':'新 core 的 KLayout 回讀','core_geometry_sidecar_exact':'新 core 幾何描述相同','all_layer_XOR_and_text':'全圖層 XOR／文字相同','timestamp_only_normalized_sha_exact':'只統一日期後 SHA 相同','three_interface_csv_exact':'三份接口 CSV 位元相同','original_pre_DRC_2_to_0':'同 deck、31 類、marker 2→0','geometric_netlist':'15 金屬網／33 光學連接','68_paths_and_33_assignments_exact':'68 段與 33 組路徑歸屬相同','400_case_comparison':'400 筆離散值與數值相同','candidate_radians_exact':'重新推導候選相位相同','12_model_tests':'12 項模型測試通過'}
def table(caption,headers,rows):return '<div class="scroll"><table><caption>'+caption+'</caption><thead><tr>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def pre(s):return '<pre><code>'+escape(s)+'</code></pre>'
body='''<div class="callout good"><b>本輪結果：</b>兩個全新來源目錄各自重建七顆 MZI core、EC／PAD／GND、標籤修正版與路徑模型，均通過 13 個驗收項。原始 GDS 雜湊因時間戳不同而不相同；只統一日期欄位後，與採用版及彼此的 SHA 完全一致。<br>全圖層 XOR 為空、文字相同、三份接口 CSV 位元一致；每輪 400 筆比較與 S7 的最大數值差為 0。兩輪共執行 24 項模型測試，另有 10 項重建輔助測試及 4 種控制案例通過。</div>
<h2 id="goal">1．「從零」的起點與學員任務</h2><p>建議 60 分鐘：辨識輸入 10 分、一鍵重建／讀 log 15 分、雜湊與 XOR 判讀 15 分、功能與驗收清單 20 分。前置：<a href="m2_s7.html">M2 S7 交付封裝與回註</a>。</p><p>本步從<b>沒有生成檔的空目錄</b>開始，帶入作者設計規格、原始相位、版圖／模型設定與自寫程式，使用本機已安裝且有授權的工具。M1 相位是設計輸入；本步不重新求解相位最佳化、FEM／FDTD，也不從零安裝 Windows、工具或 PDK。重建相同設計與建立新的製程／量測資格是不同的驗收問題。</p><ol><li>檢查 seed manifest：沒有 GDS、舊 sidecar、out、ZIP 或歷史報告。</li><li>執行兩次互相獨立的來源重建，讀取每階段的命令、回傳碼、耗時及 log。</li><li>分別回答「原始位元相同嗎」「除了日期是否相同」「幾何／接線／功能是否相同」。</li><li>故意比較時間戳副本與幾何錯誤副本，確認比較器不會把兩者混為一談。</li></ol>
<h2 id="inputs">2．輸入、外部工具與驗收參考分開</h2>'''
body+=table('表 1｜重建的依賴邊界',['種類','本輪內容'],[
('作者設計輸入','pic_spec.json、phase_settings.json；M2 邊界、core、晶片介面、標籤修正與回註模型設定。'),
('自寫來源','work/common 及選定的 core／接口／合併／標籤修正／幾何連通／線長／重播程式。逐檔記錄 SHA。'),
('外部已安裝依賴','IPKISS／CORNERSTONE 授權環境、數值 Python／NumPy、KLayout 0.30.12 與固定 SHA 的原始 pre-DRC deck。沒有重新安裝或再散布。'),
('明示路徑調整','在 staged EDA_paths.json 與 pre-DRC 設定寫入外部工具／deck 位置；設計參數與 deck 位元未改。'),
('驗收參考','S6 採用 GDS、S7 的路徑與 400 筆結果，只在產出後做比對；不當作新 GDS 或 sidecar 的建置輸入。'),
('保留版本','原 S6 晶片索引、原始 M1 相位與 M1／M2 ZIP 未改；新產物存在 M3 S1 的獨立目錄。')])
body+='''<figure><img src="figures/m3_s1/pipeline.svg" alt="從作者來源重建 core、接口、標籤與路徑，再使用驗收參考比對的流程"><figcaption>圖 1｜參考檔只用於驗收。新 M1 邏輯交接表、core sidecar、接口、路徑與報告均在乾淨目錄重新生成。</figcaption></figure>
<p><a href="../work/m3_s1/out/build_A/seed_manifest.json">A 的來源清單</a> · <a href="../work/m3_s1/out/build_B/seed_manifest.json">B 的來源清單</a> · <a href="../work/m3_s1/out/build_A/runtime.json">A 執行環境與 PDK 來源 SHA</a> · <a href="../work/m3_s1/out/build_B/runtime.json">B 執行環境</a>。</p>
<h2 id="run">3．一鍵執行與乾淨目錄政策</h2>'''
body+=pre(r'''Set-Location -LiteralPath 'C:\EDA_Codex\Lab06b'
& .\scripts\run_m3_s1.ps1
# 核心入口：scripts/rebuild_all.py
# 每次建立新識別碼及 A、B 兩個目錄：
# work/m3_s1/work/clean build 測試/<識別碼>/A
# work/m3_s1/work/clean build 測試/<識別碼>/B
# 所有輸出只在 C:\EDA_Codex；已存在的目標一律拒絕重用。''')
body+='''<p>每個階段使用新的程序，清空 PYTHONPATH、停用 user site，明示數值／授權環境的 DLL 路徑。共同模型由 staged 來源載入，並核對其位置。軟體仍使用本機授權與已安裝套件，這不是隔離作業系統或容器測試。</p>'''
body+=table('表 2｜每輪的實際重建順序',['順序','操作與產物'],[
('01','由 M1 原始規格／相位重新生成邏輯交接表與 manifest；用 PDK MMI 建立 core／單顆預覽及幾何描述。'),
('02','KLayout 回讀新 core，核對 7 顆 MZI、14 顆 MMI、heater／接觸、埠及局部接點。'),
('03','由新 core sidecar 建立 EC／PAD／GND，合併新 core GDS，生成接口 CSV 與回讀證據。'),
('04','執行原始全套 pre-DRC；重做十個埠標籤 4→5 µm 的修正，再重跑 deck 與幾何網表。'),
('05','用新 GDS 與新 sidecar 重算 68 段路徑，對照 33 個實際 MMI 外連通區。'),
('06','用新路徑重播五情境共 400 筆，解析推導模型候選，執行 12 項模型測試。'),
('07','以驗收參考核對全圖層 XOR、文字、原始／日期統一後 SHA、接口與全部數值。')])
body+=f'''<figure><img src="figures/m3_s1/timings.svg" alt="A B 兩次乾淨重建七個階段的實際耗時"><figcaption>圖 2｜A 工具階段合計 {A['seconds']:.1f} 秒，B 為 {B['seconds']:.1f} 秒；不含來源複製、Python 端比對及報告整理，也不作效能保證。</figcaption></figure>
<p><a href="../work/m3_s1/out/commands.json">完整命令／log 索引</a> · <a href="../work/m3_s1/out/build_A/03_interfaces.log">A 接口建置 log</a> · <a href="../work/m3_s1/out/build_A/04_pre_DRC_and_graph.log">A 規則／接線 log</a>。</p>
<h2 id="hash">4．原始 SHA 不同：只差日期，還是版圖變了？</h2><p>GDS 的 BGNLIB／BGNSTR 記錄含建立與修改時間。新輸出保留真實時間，不改寫已採用 GDS。驗收另在記憶體中將這兩種日期記錄的 24-byte payload 統一為 2000-01-01 00:00:00，再計算 SHA；其他位元一律保留。此規則不忽略座標、名稱、文字、圖層或記錄順序。</p>'''
body+=table('表 3｜原始位元與日期統一後的比較',['檔案','原始 SHA-256','僅統一日期後 SHA-256'],[
('S6 採用版',f'<code style="overflow-wrap:anywhere">{A["geometry"]["reference_sha256"]}</code>',f'<code style="overflow-wrap:anywhere">{A["reference_normalized"]["sha256"]}</code>'),
*[(x['build']+' 新重建',f'<code style="overflow-wrap:anywhere">{x["raw_sha256"]}</code>',f'<code style="overflow-wrap:anywhere">{x["normalized"]["sha256"]}</code>') for x in R['builds']]])
body+=f'''<p>每份最終 GDS 都有 {A['normalized']['date_records']} 筆日期記錄。三個日期統一後 SHA 相同，代表依此明示規則，<b>除了日期 payload，其餘所有位元相同</b>；原始 SHA 不同的事實仍列入報告，沒有宣稱原始檔完全相同。</p>'''
body+=table('表 4｜獨立 KLayout 全圖層比對',['GDS layer/datatype','A XOR 多邊形','B XOR 多邊形','文字'],[(f'{x["layer"]}/{x["datatype"]}',x['XOR_polygons'],y['XOR_polygons'],'兩輪相同' if x['text_identical'] and y['text_identical'] else '不同') for x,y in zip(A['geometry']['layers'],B['geometry']['layers'])])
body+='''<p><a href="../work/m3_s1/out/build_A/gds_comparison.json">A 全圖層原始比較</a> · <a href="../work/m3_s1/out/build_B/gds_comparison.json">B 全圖層原始比較</a>。XOR 比較圖形；另外逐圖層比對文字，避免把文字標籤遺漏在驗收之外。</p>
<h2 id="checks">5．兩輪驗收清單：從原檔到功能</h2>'''
body+=table('表 5｜13 項條件 × 2 輪',['條件','A','B'],[(CHECK_LABELS[x['name']],'通過' if x['passed'] else '失敗','通過' if y['passed'] else '失敗') for x,y in zip(A['checks'],B['checks'])])
body+='''<section class="panel"><label for="rebuild-build">重建輪次</label><select id="rebuild-build"><option>A</option><option>B</option></select><label for="rebuild-check">驗收項目</label><select id="rebuild-check" style="max-width:100%;width:100%;min-width:0">'''+''.join(f'<option value="{i}">{escape(CHECK_LABELS[x["name"]])}</option>' for i,x in enumerate(A['checks']))+'''</select><div id="rebuild-check-live" class="answers" aria-live="polite" style="overflow-wrap:anywhere"></div></section>
<p>每輪 pre-DRC 仍完整執行 31 個報告類別，標籤修正前 2 筆、修正後 0 筆；幾何網表為 15 個金屬網與 33 組光學連接。這些是相同已安裝 pre-DRC 與課程幾何比對，不等於 foundry 完整簽核。</p>
<h2 id="truth">6．原始 80 筆與回註 400 筆都要保留</h2><p>新產生的 M1 理想交接基準為 80/80。新路徑再做五情境重播：原相位線長回註仍只有 53/80；另行解析推導的模型候選仍 80/80。M3 S1 驗收的是「重建得到相同結論」，不能因可重現就把這個均勻 n_eff 模型升格為實體晶片校準結果。</p>'''
body+=table('表 6｜每輪五情境的實際比較',['情境','A','B'],[(CASES[k],str(A['replay_counts'][k])+'/80',str(B['replay_counts'][k])+'/80') for k in CASES])
body+='''<section class="panel"><label for="rebuild-case">模型情境</label><select id="rebuild-case" style="max-width:100%;width:100%;min-width:0">'''+''.join(f'<option value="{k}">{v}</option>' for k,v in CASES.items())+'''</select><label for="rebuild-gate">功能</label><select id="rebuild-gate">'''+''.join(f'<option>{g}</option>' for g in ['AND2','OR2','XOR2','AND4','OR4'])+'''</select><label for="rebuild-pattern">輸入 x1 x2 x3 x4（x1 為 index 最低位）</label><select id="rebuild-pattern">'''+''.join(f'<option value="{i}">'+''.join(str((i>>k)&1) for k in range(4))+'</option>' for i in range(16))+'''</select><div id="rebuild-truth-live" class="answers" aria-live="polite" style="overflow-wrap:anywhere"></div></section>
<p>上述輪次選單同時控制功能檢視器；資料讀取本輪新輸出，與 S7 的每個離散值／功率／Δ／margin 逐筆比對。兩輪最大差均為 0；候選相位的最大 rad 差也為 0。每輪 12 項模型測試獨立通過，不重複宣稱先前 144 項回歸是本步重新執行。</p>
<p><a href="../work/m3_s1/out/build_A/replay_400.csv">A 的 400 筆 CSV</a> · <a href="../work/m3_s1/out/build_B/replay_400.csv">B 的 400 筆 CSV</a> · <a href="../work/m3_s1/out/build_A/model_tests.log">A 模型測試</a> · <a href="../work/m3_s1/out/build_B/model_tests.log">B 模型測試</a>。</p>
<h2 id="controls">7．控制案例：能接受日期差，也要抓到真實圖形差</h2>'''
body+=table('表 7｜四種隔離控制',['控制','本輪觀察'],[
('只改日期的 GDS 副本','原始 SHA 改變；日期統一後 SHA 相同，可判讀為相同版圖。'),
('在 GDS 3 加入 10 µm Si 方塊','全圖層 XOR 出現真實差異，日期統一後 SHA 也不同，不能通過幾何驗收。'),
('再次指定已存在的重建目錄','直接拒絕，不沿用舊輸出。'),
('來源清單要求的檔案缺漏','清單稽核拒絕；此控制只測稽核，不啟動授權工具。')])
body+='''<p>另有 10 項輔助測試：日期統一保留座標／名稱差異、截斷／錯誤長度／錯誤日期／尾隨位元拒絕、生成檔與跳脫路徑拒絕、舊目錄及越界目錄拒絕。兩個目錄的 seed 檔案在建置後仍逐檔 SHA 一致。</p>
<p><a href="../work/m3_s1/out/acceptance_controls.json">控制與來源稽核結果</a> · <a href="../work/m3_s1/out/geometry_fault_comparison.json">Si 方塊負例的實際 XOR</a> · <a href="../work/m3_s1/out/support_tests.log">10 項輔助測試 log</a>。</p>
<h2 id="delivery">8．重建證據與驗收邊界</h2>'''
body+=table('表 8｜可讀取交付與新產物',['資料','用途'],[
('<a href="../work/m3_s1/out/rebuild_results.json">完整重建結果 JSON</a>','兩輪雜湊、26 項條件、工具命令、數值比較、版本與範圍。'),
('<a href="../work/m3_s1/out/build_A/b7_rebuilt.gds">A 重建 GDS</a> · <a href="../work/m3_s1/out/build_B/b7_rebuilt.gds">B 重建 GDS</a>','新產生的最終檔，含本輪時間戳；原 S6 採用版保留。'),
('<a href="../work/m3_s1/out/build_A/layout_info.json">新 core 幾何</a> · <a href="../work/m3_s1/out/build_A/chip_info.json">新 chip 幾何</a> · <a href="../work/m3_s1/out/build_A/paths.json">新路徑</a>','由本輪來源實際產生，不複製 S4／S5／S7 輸出。'),
('<a href="../work/m3_s1/out/build_A/pre_drc.lyrdb">A 的 pre-DRC</a> · <a href="../work/m3_s1/out/build_A/connectivity.json">A 的幾何接線</a>','新 GDS 的原始報告與網表比對。'),
('<a href="../delivery/m3_s1_acceptance/checklist.csv">機器驗收清單 CSV</a> · <a href="../delivery/m3_s1_acceptance/README.md">驗收說明</a>','可供學員與講師逐項核對。'),
('<a href="../scripts/rebuild_all.py">一鍵核心來源</a> · <a href="../scripts/run_m3_s1.ps1">學員入口</a>','正式 C 專案重做本關，使用 EDA_paths.json 的本機工具。')])
body+='''<div class="callout warn"><b>可重現不等於已校準：</b>本輪沒有重新求解 FEM／FDTD、安裝全新工具環境、建立新的波導／EC／MMI 量測模型、heater 偏壓與熱串擾校正，也沒有完成 foundry 全 DRC／專用 LVS／流片簽核。M2 S7 的模型假設與資格邊界持續適用。</div>
<h2 id="submit">9．學員交付與下一步</h2><ol><li>執行自己的兩輪重建，交付 seed 清單、執行環境、命令 log 與驗收 CSV。</li><li>列出原始與日期統一後 SHA，解釋 44 筆日期記錄的處理及其證明範圍。</li><li>核對三份接口表、全圖層 XOR、文字、33 組光學接線與 400 筆比較，挑一筆回註失敗案例說明。</li><li>解釋為何日期差可以接受，新增 Si 方塊不能接受；保留實體功能與 foundry 的未驗證項。</li><li>提交學習記錄，由講師驗收；本頁程式通過不代表學員已通過。</li></ol>
<section class="panel"><label for="rebuild-name">學員姓名</label><input id="rebuild-name"><label for="rebuild-source-notes">空目錄、來源與工具依賴</label><textarea id="rebuild-source-notes"></textarea><label for="rebuild-hash-notes">原始／日期 SHA、XOR 與控制案例</label><textarea id="rebuild-hash-notes"></textarea><label for="rebuild-truth-notes">功能比較與仍待驗證項目</label><textarea id="rebuild-truth-notes"></textarea><button id="rebuild-generate">產生 M3 S1 學習記錄 JSON</button><textarea id="rebuild-json" hidden readonly aria-label="M3 S1 學習記錄 JSON" style="min-height:220px"></textarea><p class="muted">複製到 learner/m3_s1_observations.json；<a href="../learner/m3_s1_observations.template.json">空白範本</a>。</p></section>
<p><b>下一步 M3 S2：獨立幾何量測與交叉驗證。</b>以 Python／Shapely 回讀最終 GDS，量測波導最小線寬／間距與 heater 間距，逐項對照 KLayout 結果。</p>'''
payload={b['build']:load(OUT/('build_'+b['build'])/'replay.json')['cases'] for b in R['builds']}
body+='<script>const REBUILD='+json.dumps(R,separators=(',',':'))+';const REBUILD_CASES='+json.dumps(payload,separators=(',',':'))+';</script>'
body+='''<script>(()=>{const build=document.querySelector('#rebuild-build'),check=document.querySelector('#rebuild-check'),which=document.querySelector('#rebuild-case'),gate=document.querySelector('#rebuild-gate'),pattern=document.querySelector('#rebuild-pattern');function show(){const b=REBUILD.builds.find(x=>x.build===build.value),c=b.checks[Number(check.value)],box=document.querySelector('#rebuild-check-live');box.dataset.result=JSON.stringify({build:b.build,check_index:Number(check.value),...c,raw_sha_identical:b.raw_sha_identical,normalized_sha_identical:b.normalized.sha256===b.reference_normalized.sha256,physical_function_qualified:false});box.replaceChildren();for(const text of ['輪次 '+b.build+' · '+check.options[check.selectedIndex].text+'：'+(c.passed?'通過':'失敗'),'原始 SHA '+(b.raw_sha_identical?'相同':'不同（保留實際日期）')+'；僅統一日期後 SHA 相同','13 項驗收均通過；pre-DRC '+b.pre_DRC_before+'→'+b.pre_DRC_after+'；400 筆最大數值差 '+b.max_abs_numeric_error,'本步是重建一致性，實體功能資格仍未驗證']){const d=document.createElement('div');d.textContent=text;box.append(d);}showTruth();}function showTruth(){const row=REBUILD_CASES[build.value][which.value].rows.find(r=>r.gate===gate.value&&r.index_lsb_x1===Number(pattern.value)),box=document.querySelector('#rebuild-truth-live');box.dataset.result=JSON.stringify({build:build.value,case_id:which.value,...row,physical_function_qualified:false});box.replaceChildren();for(const text of ['輪次 '+build.value+' · '+gate.value+' · '+row.pattern+' · '+(row.passed?'通過':'失敗'),'真值 '+row.expected+'；判讀 '+(row.bit===null?'邊界':row.bit)+'；Δ='+row.delta.toPrecision(8)+'；signed margin='+row.signed_margin.toPrecision(8),'五軌功率：'+row.powers.map(x=>x.toPrecision(6)).join(', '),'均勻 n_eff core 模型，尚無 EC／MMI／熱電校準']){const d=document.createElement('div');d.textContent=text;box.append(d);}}build.addEventListener('change',show);check.addEventListener('change',show);[which,gate,pattern].forEach(el=>el.addEventListener('change',showTruth));show();document.querySelector('#rebuild-generate').addEventListener('click',()=>{const box=document.querySelector('#rebuild-json');box.hidden=false;box.value=JSON.stringify({step:'M3 S1',learner_name:document.querySelector('#rebuild-name').value,clean_sources_and_tools:document.querySelector('#rebuild-source-notes').value,hash_XOR_and_controls:document.querySelector('#rebuild-hash-notes').value,truth_replay_and_limits:document.querySelector('#rebuild-truth-notes').value,instructor_review:'pending',physical_function_qualified:false,date:new Date().toISOString()},null,2);box.focus();box.select();});})();</script>'''
nav=''.join(f'<a href="{h}">{t}</a>' for h,t in [('../Lab06b_index.html','總覽與報告入口'),('plan.html','完整規劃'),('m2_s7.html','M2 S7｜交付封裝'),('#inputs','來源與外部依賴'),('#run','一鍵重建'),('#hash','SHA／XOR／文字'),('#checks','26 項驗收'),('#truth','兩輪功能比較'),('#controls','四種控制案例'),('#delivery','重建證據與邊界'),('#submit','學員交付')])
html=f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M3 S1｜從零重建與驗收｜Lab06b</title><link rel="stylesheet" href="../assets/course.css"></head><body><header class="top"><a href="../Lab06b_index.html"><b>LAB06b</b>　PIC Chip 學員實作課程</a><small>2026-10-31 · M3 S1</small></header><div class="layout"><aside><strong>學習與實作入口</strong>{nav}<p class="muted">兩輪乾淨來源重建通過<br>學員作答待提交</p></aside><main><button class="print" onclick="window.print()">列印／另存 PDF</button><div class="hero"><div class="eyebrow">MODULE 3 · STEP 1 · 60 MIN</div><h1>M3 S1｜從零重建與驗收</h1><p class="lead">從空目錄重新產生晶片，用位元、幾何、接線與功能證據，驗收相同設計是否能被重做。</p><span class="tag ok">2 輪 × 13 條件</span><span class="tag">每輪 400 筆一致</span><span class="tag wait">實體功能未驗證</span></div>{body}<footer>正式工作區 C:\\EDA_Codex\\Lab06b；D 槽唯讀。工具與授權預先安裝，設計來源重建通過；製程與量測資格仍依明示邊界。</footer></main></div></body></html>'''
(ROOT/'course/m3_s1.html').write_text(clean_course_html(html),encoding='utf-8')
for rel in ['Lab06b_index.html',*['course/'+p.name for p in sorted((ROOT/'course').glob('*.html')) if p.name!='m3_s1.html'],'analysis/lab01a_7_6.html','reference/source_context.html']:
    p=ROOT/rel;text=p.read_text(encoding='utf-8');href=('../' if '/' in rel else '')+'course/m3_s1.html'
    if f'href="{href}"' not in text:text=text.replace('</aside>',f'<a href="{href}">M3 S1｜從零重建與驗收</a></aside>',1)
    if rel=='Lab06b_index.html':
        panel='<!-- M3S1:STATUS --><div class="callout good"><b>目前進度：</b>M3 S1 兩輪乾淨來源重建均通過 13 項驗收；只統一日期後 GDS SHA 相同，全圖層 XOR／文字與接口一致，每輪 400 筆數值差為 0。<a href="course/m3_s1.html">進入 M3 S1 →</a><br>原始 GDS SHA 因時間戳不同而不相同；實體功能資格仍未驗證。下一步 M3 S2：獨立幾何量測與交叉驗證。</div><!-- /M3S1:STATUS -->'
        text=re.sub(r'<!-- (?:M2S7|M3S1):STATUS -->.*?<!-- /(?:M2S7|M3S1):STATUS -->',lambda m:panel,text,count=1,flags=re.S)
        if '<td>M3 S1 主實作</td>' not in text:text=text.replace('<tr><td>M2 S7 主實作</td>','<tr><td>M3 S1 主實作</td><td><a href="course/m3_s1.html">從零重建與驗收</a></td><td>兩輪乾淨來源、26 條件、全圖層比對與功能重播</td></tr><tr><td>M2 S7 主實作</td>',1)
        card='<article class="card"><div class="num">M3 S1</div><h3>從零重建與驗收</h3><p>兩個空目錄重新產生晶片，區分日期差異與真實版圖差異。</p><a href="course/m3_s1.html">進入本步 →</a></article>'
        text=re.sub(r'<!-- (?:M2S7|M3S1):CARD -->.*?<!-- /(?:M2S7|M3S1):CARD -->',lambda m:'<!-- M3S1:CARD -->'+card+'<!-- /M3S1:CARD -->',text,flags=re.S)
        text=text.replace('M2 交付包可重播；下一步 M3 獨立重建與驗收，foundry、EC／MMI／熱電資格邊界維持明示。','M3 S1 兩輪來源重建通過；下一步 M3 S2 獨立幾何量測，foundry、EC／MMI／熱電資格邊界維持明示。')
        text=text.replace('<td>M3 驗收與延伸</td><td>1.5 h／2 步</td><td>乾淨目錄重建、獨立檢查與差異說明</td><td>規劃完成</td>','<td>M3 驗收與延伸</td><td>1.5 h／2 步</td><td>乾淨目錄重建、獨立檢查與差異說明</td><td>S1 兩輪來源重建通過；S2 待實作</td>')
    if rel=='course/plan.html':text=text.replace('<td>M3 s1<br>1 h</td>','<td><a href="m3_s1.html">M3 s1</a><br>1 h</td>')
    p.write_text(text,encoding='utf-8')
CFG['progress']['M3_S1']='two clean authored-source builds accepted: timestamp-only GDS digest and all-layer XOR/text exact; interface CSV exact; 400-case replay identical; 4 controls and 10 support tests passed; physical function unqualified; learner submission pending'
CFG['progress']['M3_S2']='next step: independent Python/Shapely geometry measurements vs KLayout'
(ROOT/'config/course.json').write_text(json.dumps(CFG,ensure_ascii=False,indent=2),encoding='utf-8')
template=dict(step='M3 S1',learner_name='',clean_sources_and_tools='',hash_XOR_and_controls='',truth_replay_and_limits='',instructor_review='pending',physical_function_qualified=False)
(ROOT/'learner/m3_s1_observations.template.json').write_text(json.dumps(template,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
delivery=ROOT/'delivery/m3_s1_acceptance';delivery.mkdir(parents=True,exist_ok=True)
with (delivery/'checklist.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['build','check','passed']);w.writeheader();w.writerows(dict(build=b['build'],check=c['name'],passed=c['passed']) for b in R['builds'] for c in b['checks'])
(delivery/'README.md').write_text('M3 S1：兩輪乾淨來源重建驗收。\n入口 scripts/run_m3_s1.ps1；核心 scripts/rebuild_all.py。\n清單 26 項均通過；原始 GDS SHA 不同，44 筆日期 payload 統一後 SHA 相同，全圖層 XOR／文字一致。\n每輪 400 筆功能比較與 S7 差為 0。兩輪 24 項模型測試、10 項輔助測試、4 種控制通過。\n完整結果 work/m3_s1/out/rebuild_results.json；新 GDS 與表格在 out/build_A 及 out/build_B。\n預先安裝的授權工具與 M1 設計輸入為前提；不是 FEM/FDTD 重解、工具重新安裝或製程／實體功能簽核。\n學員作答與講師驗收待完成。下一步 M3 S2。\n',encoding='utf-8')
p=ROOT/'README_Lab06b_Course.md';text=p.read_text(encoding='utf-8').replace('下一步 M3 S1：從零重建與驗收。','M3 S1：scripts/run_m3_s1.ps1；兩輪乾淨來源重建、GDS 日期統一 SHA／全圖層 XOR／接口／400 筆比較通過。\n下一步 M3 S2：獨立幾何量測與交叉驗證。');p.write_text(text,encoding='utf-8')
print('M3 S1 lesson rendered; source rebuild reproducible, physical qualification pending')
