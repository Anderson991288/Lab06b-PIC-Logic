from report_policy import clean_course_html
"""Complete installed pre-DRC run, real corrections and geometric graph compare."""
from pathlib import Path
from html import escape
import json,re
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/m2_s6/out'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
D=load(OUT/'verification_results.json');CFG=load(ROOT/'config/course.json');after=D['connectivity']['after'];reg=sum(r['passed'] for r in D['regression'].values())
def table(caption,headers,rows):
    return '<div class="scroll"><table><caption>'+caption+'</caption><thead><tr>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def pre(s):return '<pre><code>'+escape(s)+'</code></pre>'
state='現有 pre-DRC 與幾何網表比對通過' if D['core_passed'] else '驗證有未解決項'
body=f'''<div class="callout {'good' if D['core_passed'] else 'warn'}"><b>本輪結果：</b>執行現有原始 deck 的全部 {D['after']['category_count']} 個報告類別，找到 2 筆 GDS 100 埠標籤間距違規；將十個埠標籤由 4 放大為 5 µm 後，同一 deck 重跑為 0 筆。六個實體圖層完全不變。<br>實際 GDS 的幾何比對確認 15 個金屬網、14 個 heater 支路及 33 段 MMI 外光路；八種錯誤 GDS 全被對應檢查抓到，{reg}/{sum(r['run'] for r in D['regression'].values())} 項既有回歸通過。</div>
<h2 id="predict">1．本步目標：從違規到修正，再到接線證據</h2><p>建議 90 分鐘：範圍與 deck 10 分、讀違規 marker 20 分、修正／重跑 15 分、光電網表比對 25 分、負例與交付 20 分。前置：<a href="m2_s5.html">M2 S5 的 EC／PAD／GND 晶片</a>。</p><ol><li>讀清楚 deck 的版本、檢查範圍及設計區參數，保存原始報告。</li><li>在 KLayout 以 marker 找到實際問題，修正圖形後重跑相同規則。</li><li>把實際幾何抽取出的接線，對照 M1 的 B7 拓樸與 S1／S5 電氣定義。</li><li>以已知錯誤副本確認檢查器能抓到短路、斷口與跨接；留下未驗證項。</li></ol>
<h2 id="scope">2．「完整執行現有 deck」的精確範圍</h2><div class="callout warn"><b>原始 deck 自身註明這是 pre-DRC：</b>CORNERSTONE v3.1、2025-03-03 版本；完整 foundry DRC 由 CORNERSTONE 團隊處理。本步執行整份已安裝 deck，沒有放寬門檻、刪除錯誤項或隱藏圖層，但結果不等於 foundry 完整簽核。</div>'''
body+=table('表 1｜可重現的執行條件',['項目','本輪設定'],[
    ('原始 deck','work/common/drc/cornerstone_Si220_passive.lydrc；前後 SHA-256 相同。'),
    ('範圍','全套既有格點、設計面積、線寬／間距／overlap 等類別；有些規則對應本設計未使用的圖層。31 是報告類別數，不是 31 項都由本晶片正負例完整覆蓋。'),
    ('製造格點','1 nm；沿用原 deck。'),
    ('宣告設計區','3860 × 1640 µm；使用 deck 原有的 dw／dh 參數核對課程外框。未由此證明符合 MPW 半／全 block 配額。'),
    ('電氣比對','GDS 41 金屬網與 GDS 39 heater 接觸：14 個獨立訊號網＋1 共地網、14 個電阻支路。'),
    ('光學比對','從實際 GDS 3／5 材料抽取 MMI 外連接；14 顆 MMI 作黑盒，對照 B7 的全部 33 組接線。'),
    ('資格邊界','沒有 foundry 專用 LVS／製程簽核、寄生抽取、EC 模式／效率、熱電校正或光學相位真值驗收。')])
body+='''<h2 id="markers">3．先讀兩筆真實違規，再修正圖形</h2>'''
body+=table('表 2｜修改前的原始 marker',['ID','類別','cell','座標外框 µm'],[(r['id'],escape(r['category']),r['cell'],str(r['bbox_um'])) for r in D['before']['items']])
body+='''<p>兩筆都位於 core 的 in0／out0 小字形附近。S5 的局部規則只篩查 Si／HT／金屬，沒有檢查 GDS 100 文字，因此這次全 deck 才發現問題。<a href="../work/m2_s6/out/before/pre_drc.lyrdb">修改前原始 .lyrdb</a> · <a href="../work/m2_s6/out/violations_before.csv">違規 CSV</a>。</p>
<figure><img src="figures/m2_s6/label_fix.svg" alt="實際 GDS 100 的 in0 標籤修改前後同尺度比較，紅框是原始間距 marker"><figcaption>圖 1｜紅框來自原始 report 的 edge-pair 座標；只放大字形，沒有移動光路、heater、PAD 或回地走線。</figcaption></figure>
<p>修正設定為 <a href="../config/m2_verification.json">port_label_scale=1.25</a>。程式在十個原埠標籤的局部視窗內，以各自原錨點放大字形，輸出仍對齊 1 nm。原 S5 GDS 保留；新 GDS 的 GDS 3／4／5／39／41／99 XOR 比較全空，GDS 100 的變化也只在這十個標籤視窗內。</p>'''
body+=table('表 3｜同一份原始 deck 重跑',['指標','修改前','修改後'],[
    ('執行的報告類別',D['before']['category_count'],D['after']['category_count']),
    ('pre-DRC marker 記錄',D['before']['total_records'],D['after']['total_records']),
    ('實體圖層差異','原版','六層 XOR 全空'),('幾何光電接線','通過','通過')])
body+='''<p><a href="../work/m2_s6/out/after/pre_drc.lyrdb">修改後原始 .lyrdb</a> · <a href="../work/m2_s6/out/rule_comparison.csv">全部類別前後 CSV</a> · <a href="../work/m2_s6/out/violations_after.csv">零違規 CSV（保留欄名）</a> · <a href="../work/m2_s6/out/fix_log.csv">修正記錄</a>。</p>
<details><summary>KLayout 原生視圖：in0 埠標籤</summary><figure><img src="figures/m2_s6/before_in0.png" alt="KLayout 原生視圖的修改前 in0 埠字形"><figcaption>修改前：GDS 100 紫色字形、GDS 3 藍色波導。</figcaption></figure><figure><img src="figures/m2_s6/after_in0.png" alt="KLayout 原生視圖的修改後 in0 埠字形"><figcaption>修改後：相同請求視窗，標籤由 4 放大為 5 µm。</figcaption></figure></details>
<h2 id="electrical">4．電氣幾何網表：15 網與 14 個 heater 支路</h2><p>先對 GDS 41 做精確合併，得到 15 個金屬連通區；以實際 PAD 中心、A／B 接觸及 HT 區域比對對照表。十四個訊號 PAD 各落在自己的網，兩個 GND PAD 在同一網。每個 heater 的 HT 區只能接觸自己的訊號與 GND 這兩網。</p>'''
body+=table('表 4｜十四個指定支路的實際回讀',['相位通道','PAD','PAD／A 元件','B 元件','結果'],[(r['channel'],r['pad_id'],str(r['pad_component'])+'／'+str(r['signal_A_components']),str(r['return_B_components']),'通過' if r['passed'] else '失敗') for r in after['electrical']['connections']])
body+='''<p>這裡將 HT 當作有意義的電阻支路，而非直接與金屬合併成短路。比對沒有填入未知 heater 電阻、Vπ、寄生或共地壓降。<a href="../work/m2_s6/out/electrical_connections.csv">電氣接線 CSV</a> · <a href="../work/m2_s6/out/after/connectivity.json">完整幾何網表比對 JSON</a>。</p>
<h2 id="optical">5．光學幾何網表：切開 MMI 黑盒後比對 33 組接線</h2><p>把整片 Si 直接做 union，會透過 MMI 多模區接成大區塊，無法表示真正的多埠接線。因此本步先找到實際階層中的 7 顆 MZI 與 14 顆 MMI，扣除 MMI 本體幾何，再把外部材料連通區對照宣告網表。</p>'''
body+=pre('14 MMI × 4 個幾何端點 + 10 個 EC facet = 66 個端點\n66 個端點 ÷ 每條連接 2 個端點 = 33 條外部連接\n33 = 14 條 MZI 內部臂連接 + 19 條 B7／外部 I/O 連接')
body+='''<p>期望網表由原 M1 規格的實例／模式順序產生；觀察網表則從實際 GDS 材料區取得，不用產生中心線的 sidecar 代替抽取。每個 MMI 的幾何與其餘同型元件一致，接點也做覆蓋核對。MMI 混光、EC 模式轉換與複數相位仍屬不同層次的光學模型驗證。</p>
<section class="panel"><label for="verify-route">檢視 33 條光學接線</label><select id="verify-route" style="max-width:100%;width:100%;min-width:0">'''+''.join(f'<option value="{k}">{k+1:02d} · {escape(p[0])} ↔ {escape(p[1])}</option>' for k,p in enumerate(after['optical']['expected_pairs']))+'''</select><div id="verify-route-live" class="answers" aria-live="polite" style="overflow-wrap:anywhere"></div></section>
<p><a href="../work/m2_s6/out/optical_connections.csv">全部光學連接 CSV</a>。33 條外部連接不是 5×5 傳輸矩陣的 25 個係數；這一關驗證幾何拓樸，沒有以幾何相接宣稱模式或相位驗證。</p>
<h2 id="controls">6．八種真實錯誤 GDS：DRC 零筆仍可能接錯</h2>'''
names={'D1_Si_width':'Si 窄線 0.2 µm','D2_grid':'0.5 nm 偏移的格點錯誤','D3_HT_gap':'HT 間距不足','D4_PAD_width':'PAD 金屬線寬不足','E1_signal_ground_short':'訊號接到 GND','E2_return_open':'heater 回地斷路','O1_lead_open':'in0 光路斷口','O2_optical_bridge':'in0／in1 非預期光學橋接'}
body+=table('表 5｜八種負例均先寫成 GDS，再重讀執行相同檢查',['負例','DRC 記錄','電氣比對','光學比對','指定偵測'],[(names[r['id']],r['drc_records'],'通過' if r['electrical_passed'] else '失敗','通過' if r['optical_passed'] else '失敗','已抓到' if r['detected'] else '漏檢') for r in D['negative_controls']])
body+='''<figure><img src="figures/m2_s6/controls.svg" alt="八種錯誤 GDS 的 pre-DRC 記錄數，後四種接線錯誤的 DRC 皆為零"><figcaption>圖 2｜訊號短路、回地斷路、光路斷口與橋接的 DRC 都是零筆，但網表比對失敗。只有規則篩查，無法證明功能接線正確。</figcaption></figure>
<p>負例存在隔離的 work/m2_s6/work/faults，沒有列入採用版；<a href="../work/m2_s6/out/negative_controls.csv">控制案例 CSV</a> 與 <a href="../work/m2_s6/out/control_results.json">完整結果 JSON</a> 記錄各檢查的實際反應。這八種負例不是對整份 deck 所有規則的完整覆蓋。</p>
<h3>比對正式版與負例的判讀</h3><section class="panel"><label for="verify-case">案例</label><select id="verify-case"><option value="after">正式修正版</option><option value="before">正式修改前</option>'''+''.join(f'<option value="{r["id"]}">{names[r["id"]]}</option>' for r in D['negative_controls'])+'''</select><div id="verify-case-live" class="answers" aria-live="polite" style="overflow-wrap:anywhere"></div></section>'''
body+='<script>const VERIFICATION='+json.dumps(D)+';</script>'
body+='''<script>(()=>{const route=document.querySelector('#verify-route'),which=document.querySelector('#verify-case');function showRoute(){const p=VERIFICATION.connectivity.after.optical.expected_pairs[Number(route.value)],observed=VERIFICATION.connectivity.after.optical.observed_groups.some(q=>JSON.stringify(q)===JSON.stringify(p)),box=document.querySelector('#verify-route-live');box.dataset.result=JSON.stringify({route_index:Number(route.value),terminals:p,observed_match:observed,phase_verified:false});box.replaceChildren();for(const text of [p.join(' ↔ '),observed?'宣告與 GDS 抽取的幾何端點組合一致':'不一致','此處僅比對外部連接；MMI／EC 模式與相位仍待驗證']){const d=document.createElement('div');d.textContent=text;box.append(d);}}function showCase(){const id=which.value,formal=id==='before'||id==='after',r=formal?null:VERIFICATION.negative_controls.find(x=>x.id===id),result={case_id:id,drc_records:formal?VERIFICATION[id].total_records:r.drc_records,electrical_passed:formal?VERIFICATION.connectivity[id].electrical.passed:r.electrical_passed,optical_passed:formal?VERIFICATION.connectivity[id].optical.passed:r.optical_passed,expected_fault_detected:formal?null:r.detected,foundry_full_signoff:false},box=document.querySelector('#verify-case-live');box.dataset.result=JSON.stringify(result);box.replaceChildren();for(const text of [formal?'正式檔案（前後版均保留）':'隔離負例，不可當作採用版','pre-DRC '+result.drc_records+' 筆；電氣比對 '+(result.electrical_passed?'通過':'失敗')+'；光學比對 '+(result.optical_passed?'通過':'失敗'),formal?'修正後仍需保留完整資格邊界':result.expected_fault_detected?'指定錯誤已被對應檢查抓到':'漏檢，需停止驗收','foundry 完整簽核／EC 與熱電校正／相位真值重播：未完成']){const d=document.createElement('div');d.textContent=text;box.append(d);}}route.addEventListener('change',showRoute);which.addEventListener('change',showCase);showRoute();showCase();})();</script>
<h2 id="run">7．重跑、違規記錄與採用版</h2>'''
body+=pre(r"""Set-Location -LiteralPath 'C:\EDA_Codex\Lab06b'
& .\scripts\run_m2_s6.ps1
# KLayout 開啟 out\before 與 out\after 的 b7_ec_pad.gds。
# 在 Marker Database Browser 載入各自的 pre_drc.lyrdb。
# 選 GDS100 gap 類別，再對照 marker 的 cell 與座標。""")
body+=table('表 6｜交付與追溯',['檔案','用途'],[
    ('<a href="../work/m2_s6/out/before/b7_ec_pad.gds">原版 GDS</a> · <a href="../work/m2_s6/out/after/b7_ec_pad.gds">修正版 GDS</a>','原 S5 位元不變；新檔只改十個埠標籤。'),
    ('<a href="../work/m2_s6/out/before/drc_result.json">修改前 DRC JSON</a> · <a href="../work/m2_s6/out/after/drc_result.json">修改後 DRC JSON</a>','含原始 deck SHA、類別、marker 與設計區參數。'),
    ('<a href="../work/m2_s6/out/label_patch.json">字形修正與 XOR 記錄</a> · <a href="../work/m2_s6/out/fix_log.json">修正 log</a>','保留問題、原因、動作與重跑證據。'),
    ('<a href="../config/m2_current_chip.json">目前採用版索引</a>','M2 S7 使用 S6 修正版與位元一致的接口表。'),
    ('<a href="../work/m2_s6/out/verification_results.json">完整驗證結果</a>','連通網表、負例、來源雜湊與資格邊界。'),
    ('<a href="../work/m2_s6/run_verification.py">deck 執行入口</a> · <a href="../work/m2_s6/connectivity.py">幾何抽取／比對</a> · <a href="../work/m2_s6/generate_faults.py">負例產生器</a>','可由來源重建本步結果。')])
body+=f'''<p>144 項既有回歸通過；M1 規格／相位與交接 ZIP 未改，原基準仍重播 80/80。修正版的物理介面與 PAD 座標沒有改動，S5 sidecar／CSV 以原位元承接；字形修改並未被當成光學相位回註。</p>'''
body+='''<h2 id="limits">8．還有哪些驗證不能被打勾？</h2><ul><li>foundry 完整簽核與專用製程 LVS／寄生抽取：本步只有現有 pre-DRC 與自訂幾何網表比對。</li><li>EC 製程／模式轉換、耦合效率、光纖與切割／封裝條件。</li><li>heater 相位→偏壓、電阻、共地阻抗、熱串擾及穩定度。</li><li>實際路徑的複數傳輸、相位回註及五功能 80 筆物理光路驗收。</li></ul>
<h2 id="submit">9．學員交付</h2><ol><li>提交兩版 GDS、原始 .lyrdb、違規前後 CSV 與修正 log，附上 in0／out0 marker 截圖。</li><li>解釋為何修正文字可以消除本次規則違規，以及六層 XOR 比較能證明什麼。</li><li>各挑一條 MZI 內臂與 B7 外部連接，從宣告網表對照到實際 GDS 抽取的端點組合。</li><li>挑一個 DRC=0 的錯誤副本，說明其短路／斷路／跨接如何被幾何網表比對抓到。</li><li>列出尚未完成的製程、EC、熱電與相位驗證，提交自己的判讀；學員作答待講師驗收。</li></ol>
<section class="panel"><label for="verify-name">學員姓名</label><input id="verify-name"><label for="verify-drc-notes">違規 marker、修正與重跑證據</label><textarea id="verify-drc-notes"></textarea><label for="verify-net-notes">光學／電氣幾何網表觀察</label><textarea id="verify-net-notes"></textarea><label for="verify-limit-notes">負例判讀與尚未完成項目</label><textarea id="verify-limit-notes"></textarea><button id="verify-generate">產生 M2 S6 學習記錄 JSON</button><textarea id="verify-json" hidden readonly aria-label="M2 S6 學習記錄 JSON" style="min-height:220px"></textarea><p class="muted">複製到 learner/m2_s6_observations.json；<a href="../learner/m2_s6_observations.template.json">空白範本</a>。</p></section>
<script>document.querySelector('#verify-generate').addEventListener('click',()=>{const box=document.querySelector('#verify-json');box.hidden=false;box.value=JSON.stringify({step:'M2 S6',learner_name:document.querySelector('#verify-name').value,drc_markers_and_fix:document.querySelector('#verify-drc-notes').value,optical_and_electrical_netlist:document.querySelector('#verify-net-notes').value,negative_controls_and_limits:document.querySelector('#verify-limit-notes').value,instructor_review:'pending',date:new Date().toISOString()},null,2);box.focus();box.select();});</script>
<p><b>下一步 M2 S7：</b>交付封裝、路徑回註與重播；承接本步修正版與完整資格邊界。</p>
<p class="muted">技術參考：<a href="https://www.klayout.org/downloads/master/doc-qt5/manual/drc_basic.html">KLayout DRC</a>、<a href="https://www.klayout.de/doc/manual/lvs_overview.html">KLayout LVS 與網表比對概念</a>。本步使用安裝的 0.30.12 與本機原始 pre-DRC deck；光學比對是此課程的幾何黑盒方法。</p>'''
nav=''.join(f'<a href="{h}">{t}</a>' for h,t in [('../Lab06b_index.html','總覽與報告入口'),('plan.html','完整規劃'),('m2_s5.html','M2 S5｜晶片介面'),('#scope','原始 deck 與範圍'),('#markers','違規與修正'),('#electrical','電氣幾何網表'),('#optical','33 組光學接線'),('#controls','八種錯誤 GDS'),('#run','重跑與交付'),('#limits','資格邊界'),('#submit','學員交付')])
html=f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M2 S6｜完整規則／連通檢查與違規記錄｜Lab06b</title><link rel="stylesheet" href="../assets/course.css"></head><body><header class="top"><a href="../Lab06b_index.html"><b>LAB06b</b>　PIC Chip 學員實作課程</a><small>2026-10-31 · M2 S6</small></header><div class="layout"><aside><strong>學習與實作入口</strong>{nav}<p class="muted">{state}<br>學員作答待提交</p></aside><main><button class="print" onclick="window.print()">列印／另存 PDF</button><div class="hero"><div class="eyebrow">MODULE 2 · STEP 6 · 90 MIN</div><h1>M2 S6｜完整規則／連通檢查與違規記錄</h1><p class="lead">完整執行現有 pre-DRC deck，修正真實 marker，並以幾何網表比對檢查 DRC 無法證明的接線。</p><span class="tag ok">pre-DRC 2 → 0</span><span class="tag">15 金屬網／33 光路</span><span class="tag wait">非 foundry 簽核</span></div>{body}<footer>正式工作區 C:\\EDA_Codex\\Lab06b；D 槽唯讀。現有 pre-DRC 與幾何網表比對已執行；foundry、EC、熱電與相位驗證的資格邊界維持明示。</footer></main></div></body></html>'''
(ROOT/'course/m2_s6.html').write_text(clean_course_html(html),encoding='utf-8')
for rel in ['Lab06b_index.html','course/plan.html','course/m0_s1.html','course/m0_s1_foundation.html','course/m0_s2.html','course/m0_s3.html','course/m1_s1.html','course/m1_s2.html','course/m1_s3.html','course/m1_s4.html','course/m1_s5.html','course/m2_s1.html','course/m2_s2.html','course/m2_s3.html','course/m2_s4.html','course/m2_s5.html','analysis/lab01a_7_6.html','reference/source_context.html']:
    p=ROOT/rel;text=p.read_text(encoding='utf-8');href=('../' if '/' in rel else '')+'course/m2_s6.html'
    if f'href="{href}"' not in text:text=text.replace('</aside>',f'<a href="{href}">M2 S6｜規則與連通驗證</a></aside>',1)
    if rel=='Lab06b_index.html':
        panel='<!-- M2S6:STATUS --><div class="callout good"><b>目前進度：</b>M2 S6 全套現有 pre-DRC 與幾何網表比對通過；文字違規 2→0，15 金屬網／33 光路與宣告接線一致。<a href="course/m2_s6.html">進入 M2 S6 →</a><br>foundry 簽核、EC／熱電響應及光學相位回註仍待完成。下一步 M2 S7。</div><!-- /M2S6:STATUS -->'
        text=re.sub(r'<!-- (?:M2S5|M2S6):STATUS -->.*?<!-- /(?:M2S5|M2S6):STATUS -->',lambda m:panel,text,count=1,flags=re.S)
        text=text.replace('S1～S5 邊界、電路、core 與介面通過；S6～S7 待實作','S1～S6 邊界、電路、介面與現有規則／連通驗證通過；S7 待實作')
        text=text.replace('M0、M1 與 M2 S1～S5 核心已實跑','M0、M1 與 M2 S1～S6 核心已實跑').replace('後續完整規則／連通驗證、EC／熱電響應、路徑回註與最終交付依關卡進行。','後續交付封裝、路徑回註與重播依關卡進行；foundry 與 EC／熱電資格邊界維持明示。')
        if '<td>M2 S6 主實作</td>' not in text:text=text.replace('<tr><td>M2 S5 主實作</td>','<tr><td>M2 S6 主實作</td><td><a href="course/m2_s6.html">完整規則／連通檢查與違規記錄</a></td><td>pre-DRC 2→0、幾何網表比對、八種錯誤 GDS</td></tr><tr><td>M2 S5 主實作</td>',1)
        card='<article class="card"><div class="num">M2 S6</div><h3>規則／連通與違規記錄</h3><p>修正真實 marker，用錯誤 GDS 驗證規則與接線比對。</p><a href="course/m2_s6.html">進入本步 →</a></article>'
        text=re.sub(r'<!-- (?:M2S5|M2S6):CARD -->.*?<!-- /(?:M2S5|M2S6):CARD -->',lambda m:'<!-- M2S6:CARD -->'+card+'<!-- /M2S6:CARD -->',text,flags=re.S)
    if rel=='course/plan.html':text=text.replace('<td>M2 s6<br>1.5 h</td>','<td><a href="m2_s6.html">M2 s6</a><br>1.5 h</td>')
    p.write_text(text,encoding='utf-8')
CFG['progress']['M2_S6']='original full installed pre-DRC zero after label fix; geometric electrical/optical netlist compare passed; foundry qualification pending; learner submission pending' if D['core_passed'] else 'verification unresolved'
CFG['progress']['M2_S7']='next step: package delivery, path backannotation and replay'
(ROOT/'config/course.json').write_text(json.dumps(CFG,ensure_ascii=False,indent=2),encoding='utf-8')
p=ROOT/'README_Lab06b_Course.md';text=p.read_text(encoding='utf-8').replace('下一步 M2 S6：完整規則／連通檢查與違規記錄。','M2 S6：scripts/run_m2_s6.ps1；全套現有 pre-DRC 與幾何網表比對、修正版見 config/m2_current_chip.json。\n下一步 M2 S7：交付封裝、路徑回註與重播。');p.write_text(text,encoding='utf-8')
print('M2 S6 page rendered; core:',D['core_passed'])
