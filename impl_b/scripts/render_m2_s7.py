from report_policy import clean_course_html
"""Package delivery, explicit core-plane length replay, and learner evidence."""
from pathlib import Path
from html import escape
import json,re
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/m2_s7/out'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
R=load(OUT/'replay_results.json');P=load(OUT/'paths.json');D=load(OUT/'delivery_results.json');CFG=load(ROOT/'config/course.json')
LABELS={'ideal_baseline':'理想原始基準','length_original':'線長＋原始相位','length_compensated':'線長＋模型補償','loss_original':'3 dB/cm＋原始相位','loss_compensated':'3 dB/cm＋模型補償'}
def table(caption,headers,rows):
    return '<div class="scroll"><table><caption>'+caption+'</caption><thead><tr>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def pre(s):return '<pre><code>'+escape(s)+'</code></pre>'
body='''<div class="callout good"><b>本輪交付：</b>沿用 S6 採用版 GDS，封裝規格、原始／候選相位、接口表、路徑、原始報告與 SHA-256 清單；搬到含中文及空白的新路徑後，400 筆比較與幾何／現有 pre-DRC 重播一致。<br><b>功能判讀：</b>理想基準 80/80 → 線長回註後原設定 53/80 → 解析模型補償後 80/80。這是有明確假設的 core 端教學模型，實體晶片光學功能尚未驗證。</div>
<h2 id="goal">1．本步目標與學員操作</h2><p>建議 60 分鐘：辨識交付版本 10 分、追蹤線長與參考面 15 分、比較原相位／模型候選 15 分、搬移重播與交付 20 分。前置：<a href="m2_s6.html">M2 S6 規則／幾何連通證據</a>。</p><ol><li>從索引定位 S6 採用晶片，核對封裝 GDS 位元一致。</li><li>從 68 段中心線追到 33 條實際 GDS 連接，辨識 core 與 EC fan 的參考面。</li><li>先看原始相位回註後失敗的案例，再推導相位補償，保留原相位不變。</li><li>將 ZIP 解壓到新位置，核對完整性並重播；記錄軟體、結果與尚未驗證事項。</li></ol>
<h2 id="package">2．交付包與版本鏈</h2><p><a href="../delivery/Lab06b_M2_PIC_delivery.zip"><b>下載 M2 PIC 設計交付 ZIP</b></a> · <a href="../delivery/m2_pic_delivery/manifest.json">封裝 manifest</a> · <a href="../delivery/m2_pic_delivery/README.md">使用說明</a> · <a href="../config/m2_current_chip.json">S6 晶片採用索引</a>。</p>'''
body+=table('表 1｜交付內容與責任',['路徑（ZIP 內）','內容／用途'],[
('layout/B7_final.gds','S6 修正版，沒有再變更實體版圖或埠標籤。'),
('data/','原始 M1 規格／相位、模型、S4 core 與 S5 chip 幾何、68 路徑、另存的模型候選相位、M0 FEM 參考。'),
('interfaces/','10 個光學 I/O、14 個 heater 訊號 PAD、2 個共地 PAD，以及 68 段／33 連接線長 CSV。'),
('reports/','400 筆比較、靈敏度、S6 驗證／連通、零 marker .lyrdb、修正 log、12 項模型測試與 144 項既有回歸結果。'),
('models/、geometry/、source/project/','本課程自寫模型、幾何檢查與選定來源；不附 PDK、專有 deck、工具、授權或安裝環境。'),
('verify_delivery.py、replay_delivery.py','SHA／版本綁定檢查；使用相對於腳本的路徑重播五情境。'),
('recheck_geometry.py、geometry_engine.py','另提供已安裝 KLayout 與同 SHA 的外部 deck，重跑 pre-DRC 與實際 GDS 幾何網表。')])
body+=f'''<p>manifest 列出 <b>{D['files']}</b> 個內容檔；ZIP 另含 manifest 本身。GDS SHA-256：<code style="overflow-wrap:anywhere">{D['gds_sha256']}</code>。ZIP SHA-256：<code style="overflow-wrap:anywhere">{D['zip_sha256']}</code>。SHA 可檢查位元與版本一致性；這份清單不是數位簽章。</p>
<figure><img src="figures/m2_s7/final_chip.png" alt="KLayout 原生渲染的最終 S6 採用晶片，包含七個 MZI、十個參考 EC、heater PAD 與共地"><figcaption>圖 1｜從採用 GDS 以 KLayout 原生繪出；GDS 99 外框層隱藏以看清實體圖形。S7 封裝不改 S6 晶片。</figcaption></figure>
<h2 id="length">3．路徑回註：68 段中心線不是 68 條獨立光路</h2><p>沿用已綁定雜湊的 S4／S5 sidecar，把 1 nm 格點中心線逐段重算長度，再以路徑中點歸屬到 S6 實際 GDS 的材料連通區。實際接線仍採 S6 的 MMI 黑盒切分方式，66 個端點形成 33 個連通區；名義線長來自中心線，不能把這個程序稱為經製程校準的光學 PEX。</p>'''
body+=pre('58 段 core = 7 MZI × 6 波導 + 6 bypass + 10 core lead\n68 段總路徑 = 58 core + 10 EC fan\n33 條 GDS 連接 = 14 MZI 內臂 + 19 其餘外部連接\nEC taper 與 MMI 本體不計入這些中心線長度')
body+='''<figure><img src="figures/m2_s7/route_lengths.svg" alt="33 個實際 GDS 連通區的 core 與 fan 中心線長度分解"><figcaption>圖 2｜一條 GDS 連接可能合併多段中心線。淺色 fan 已列入交付線長表，但在 M1 core 參考面之外，不加入本輪傳輸矩陣。</figcaption></figure>
<section class="panel"><label for="delivery-path">檢視 68 段路徑</label><select id="delivery-path" style="max-width:100%;width:100%;min-width:0">'''+''.join(f'<option value="{i}">{escape(p["id"])} · {p["length_um"]:.3f} µm</option>' for i,p in enumerate(P['paths']))+'''</select><div id="delivery-path-live" class="answers" aria-live="polite" style="overflow-wrap:anywhere"></div></section>
<p><a href="../work/m2_s7/out/paths.json">完整綁定／路徑 JSON</a> · <a href="../work/m2_s7/out/path_lengths.csv">68 段 CSV</a> · <a href="../work/m2_s7/out/route_lengths.csv">33 連接 CSV</a>。</p>
<h2 id="model">4．先固定參考面、相位與單位</h2>'''
body+=table('表 2｜本輪模型的明示條件',['參數','來源與限制'],[
('參考面','M1 的五個 core 輸入／輸出；[x1,x2,x3,x4,R]，R 振幅 3。不是光纖端輸入功率。'),
('λ = 1.55 µm；n_eff = 2.353499831254645','M0 S2 均勻氧化層 FEM 的 fine 網格結果；不是校準後的 CORNERSTONE 波導折射率。'),
('β = 2πn_eff/λ；g(L) = 10^(−αL/10000/20) exp(+iβL)','L 用 µm；α 用 dB/cm。振幅損耗除以 20；不要以功率因子直接乘場。'),
('MMI：H = [[1,i],[i,1]]/√2','延用已安裝 PDK 預設理想 H；保留複數全域相位，不再加 β×MMI 縱向尺寸。尚無量測絕對相位與色散。'),
('無損與 α = 3 dB/cm','零損耗為相位比較；3 dB/cm 只是教學情境，不宣稱製程傳播損耗。'),
('不含 EC／fan、彎曲專屬 n_eff／損耗及 heater','EC 響應與模式、熱串擾、電阻／Vπ、共地壓降、封裝與製程簽核仍待驗證。')])
body+=pre('T_MZI = D_post · H · D_inter · P(theta) · H · D_pre · P(phi)\nP(a) = diag(exp(i a), 1)\n依 B7 層次串接，包含 bypass 與 core lead；保留全部複數相位。')
body+='''<h2 id="replay">5．回註後先比較失敗，再另存模型補償</h2><p>將原 M1 相位直接套入線長傳播，只有 53/80 通過。不能拿理想基準的 80/80 代替這次回註結果。每個 MZI 以進入兩軌的相位與前段長差推導 φ 偏移，以兩內臂長差推導 θ 偏移；這是幾何與模型的解析相位追蹤，不使用真值標籤重新擬合。候選相位另存，沒有覆寫 phase_settings.json。</p>'''
body+=pre('Δφ = −(a_upper − a_lower) − β(L_pre,upper − L_pre,lower)\nΔθ = −β(L_inter,upper − L_inter,lower)\n候選 = 原 M1 相位 + 偏移（mod 2π）；追蹤其餘軌與 bypass 的共同相位。\nU_candidate = diag(exp(i δ_out)) · U_ideal\n輸出各軌僅差相位時，各軌功率相同；候選仍不是 heater 偏壓。')
body+=table('表 3｜五情境 × 五功能 × 十六輸入＝400 筆實際比較',['情境','通過','最小 signed margin'],[(LABELS[k],f'{v["passed"]}/80',f'{min(x["minimum_signed_margin"] for x in v["functions"].values()):.9g}') for k,v in R['cases'].items()])
body+=f'''<p>完整複數矩陣的相位規範等式最大誤差 <b>{R['complex_gauge_error']:.3g}</b>；12 項新模型測試、144 項既有回歸通過。無損能量守恆與有損被動性亦核對通過。損耗情境候選仍 80/80，但最小 margin 從 0.25 降至約 0.222；這些結果沒有建立實際製程容差。</p>
<figure><img src="figures/m2_s7/replay.svg" alt="五情境的通過數及八十個案例的 signed margin"><figcaption>圖 3｜原設定的線長回註錯誤必須留下；補償 80/80 的適用範圍由模型定義。</figcaption></figure>
<section class="panel"><label for="delivery-case">模型情境</label><select id="delivery-case" style="max-width:100%;width:100%;min-width:0">'''+''.join(f'<option value="{k}">{v}</option>' for k,v in LABELS.items())+'''</select><label for="delivery-gate">邏輯功能</label><select id="delivery-gate">'''+''.join(f'<option>{g}</option>' for g in R['cases']['ideal_baseline']['functions'])+'''</select><label for="delivery-pattern">輸入順序 x1 x2 x3 x4（x1 為 index 的最低位）</label><select id="delivery-pattern">'''+''.join(f'<option value="{i}">'+''.join(str((i>>k)&1) for k in range(4))+'</option>' for i in range(16))+'''</select><div id="delivery-live" class="answers" aria-live="polite" style="overflow-wrap:anywhere"></div></section>
<p>差分 Δ=P(out1)−P(out3)，正為 1、負為 0；|Δ|≤10⁻¹⁰ 為邊界。signed margin=(2×真值−1)Δ，正值才在正確一側。功率為與 M1 一致的正規化值，未換算光纖 mW。</p>
<p><a href="../work/m2_s7/out/replay_400.csv">400 筆 CSV</a> · <a href="../work/m2_s7/out/replay_results.json">完整複數矩陣與結果</a> · <a href="../work/m2_s7/out/phase_settings_backannotated.json">模型候選相位（rad，非電壓）</a>。</p>
<h2 id="sensitivity">6．凍結候選的折射率擾動</h2><p>只在名義 n_eff 推導一次候選相位，之後凍結設定，對七個 Δn_eff 點重播。這些點的候選均為 80/80，但最小 margin 在兩端降到約 0.0835 與 0.0822。這是均勻 n_eff 的示範擾動，沒有逐點重調相位，也不代表實際線寬／厚度／溫度容差或波長頻寬。</p>
<figure><img src="figures/m2_s7/sensitivity.svg" alt="七個均勻折射率擾動點的通過數與最小 margin，候選相位保持固定"><figcaption>圖 4｜功能通過數相同，margin 仍會改變。若要判斷製程良率，還需要局部與相關變異的校準模型。</figcaption></figure>
<h2 id="portable">7．解壓到新路徑，驗證與重播</h2><p>先將 ZIP 解壓到 C:\\EDA_Codex 下另一個資料夾，再用數值 Python 執行。以下命令只依賴解壓後的包內路徑；腳本會以自己的位置找資料。重播需要 NumPy（本輪 1.26.4），不需要載入 IPKISS／PDK。</p>'''
body+=pre(r'''# 在「解壓後」資料夾執行
& 'C:\luceda\luceda_2026033\envs\device_sim\python.exe' .\verify_delivery.py
& 'C:\luceda\luceda_2026033\envs\device_sim\python.exe' .\replay_delivery.py --out .\my_replay
# 如要重查幾何，另提供已安裝 KLayout 與相同 SHA 的外部 deck：
& 'C:\luceda\luceda_2026033\envs\device_sim\python.exe' .\recheck_geometry.py `
  --klayout 'C:\EDA_Codex\Lab06b\tools\KLayout\klayout-0.30.12-win64\klayout_app.exe' `
  --deck 'C:\EDA_Codex\Lab06b\work\common\drc\cornerstone_Si220_passive.lydrc' --out .\my_geometry
# 從正式專案重做 S7（需要前步輸出與本機環境）：
Set-Location -LiteralPath 'C:\EDA_Codex\Lab06b'
& .\scripts\run_m2_s7.ps1''')
body+='''<p>實測搬移到 <code>work/m2_s7/work/relocated package 測試</code>，使用新程序、移除繼承的 Conda 設定，完整性、400 筆數值及外部工具幾何重播均通過。重播最大 |Δ差|=0；pre-DRC 0 筆，金屬 15 網、光學 33 連接。此項是交付包重播；從零建立工具／PDK 並重建 GDS 的獨立驗收留給 M3 S1。</p>'''
body+=table('表 4｜隔離副本的四項負例',['副本改動','攔截原因'],[(escape(x['case']),escape(x['reason'])) for x in D['tamper_controls']])
body+='''<p>這些副本不放入交付 ZIP。即使重新計算某檔 SHA，模型與候選的交叉綁定、400 案例完整性仍會檢查。<a href="../work/m2_s7/out/delivery_results.json">搬移／負例／幾何結果</a> · <a href="../work/m2_s7/out/unit_tests.log">12 項模型測試</a> · <a href="../work/m2_s7/out/regression.json">144 項既有回歸</a>。</p>
<h2 id="ready">8．交付成熟度：哪些可驗收，哪些仍待驗證？</h2>'''
body+=table('表 5｜當前資格邊界',['項目','狀態'],[
('版本封裝／SHA／中文空白路徑重播','本輪通過；GDS 沿用 S6，50 個檔案與完整案例可追溯。'),
('現有全套 pre-DRC／幾何光電接線','重播通過；這不是 foundry 完整簽核、製程專用 LVS 或校準光學 PEX。'),
('名義 core 線長模型／解析候選','80→53→80 的差異已記錄；原始 M1 相位與交接 ZIP 不變。'),
('EC／MMI 真實響應、波導與彎曲校準','待驗證；目前 n_eff、H 與損耗情境只支持明示模型。'),
('heater 偏壓、電阻、熱串擾與共地壓降','待驗證；候選只含 rad，不含可直接施加的電壓。'),
('foundry、切割、光纖／電氣封裝及量測','待驗證；本 ZIP 是教學設計／審查交付包，尚無流片功能資格。'),
('學員獨立作答／講師驗收','待提交；完成教材與程式不代表學員已通過。')])
body+='''<h2 id="submit">9．學員交付與下一步</h2><ol><li>交付 ZIP 與 manifest，寫出採用 GDS 的雜湊來源。</li><li>各選一段 core、一段 EC fan，記錄來源路徑、所屬 GDS 連通區、長度與參考面。</li><li>從 400 筆比較中挑一筆原設定回註失敗的輸入，解釋複數干涉與 signed margin 的改變。</li><li>說明解析補償為何可保留輸出功率，以及為何 80/80 還不能當作實體晶片驗收。</li><li>解壓到新位置，留下完整性、數值與（有工具時）幾何重播紀錄；列出仍需量測／製程校準的項目。</li></ol>
<section class="panel"><label for="delivery-name">學員姓名</label><input id="delivery-name"><label for="delivery-path-notes">版本、路徑與參考面觀察</label><textarea id="delivery-path-notes"></textarea><label for="delivery-replay-notes">失敗案例、補償與搬移重播證據</label><textarea id="delivery-replay-notes"></textarea><label for="delivery-limit-notes">仍待驗證的模型／實體條件</label><textarea id="delivery-limit-notes"></textarea><button id="delivery-generate">產生 M2 S7 學習記錄 JSON</button><textarea id="delivery-json" hidden readonly aria-label="M2 S7 學習記錄 JSON" style="min-height:220px"></textarea><p class="muted">複製到 learner/m2_s7_observations.json；<a href="../learner/m2_s7_observations.template.json">空白範本</a>。</p></section>
<p><b>下一步 M3 S1：從零重建與驗收。</b>由獨立重建流程比對 GDS 雜湊與功能結果，將本步交付包的可重播證據接到完整專案重建。</p>'''
payload={k:{'rows':v['rows'],'passed':v['passed']} for k,v in R['cases'].items()}
body+='<script>const DELIVERY_CASES='+json.dumps(payload,separators=(',',':'))+';const DELIVERY_PATHS='+json.dumps(P,separators=(',',':'))+';</script>'
body+='''<script>(()=>{const which=document.querySelector('#delivery-case'),gate=document.querySelector('#delivery-gate'),pattern=document.querySelector('#delivery-pattern'),path=document.querySelector('#delivery-path');function show(){const row=DELIVERY_CASES[which.value].rows.find(r=>r.gate===gate.value&&r.index_lsb_x1===Number(pattern.value)),box=document.querySelector('#delivery-live');box.dataset.result=JSON.stringify({case_id:which.value,...row,physical_function_qualified:false});box.replaceChildren();for(const text of [gate.value+' · x1x2x3x4='+row.pattern+' · '+(row.passed?'通過':'失敗'),'真值 '+row.expected+'；判讀 '+(row.bit===null?'邊界':row.bit)+'；Δ='+row.delta.toPrecision(8)+'；signed margin='+row.signed_margin.toPrecision(8),'五軌功率：'+row.powers.map(x=>x.toPrecision(6)).join(', '),'總輸入 '+row.input_power.toPrecision(7)+'；總輸出 '+row.output_power.toPrecision(7),'僅為明示 core 模型；實體功能資格未驗證']){const d=document.createElement('div');d.textContent=text;box.append(d);}}function showPath(){const p=DELIVERY_PATHS.paths[Number(path.value)],route=DELIVERY_PATHS.routes.find(r=>r.component===p.gds_route_component),box=document.querySelector('#delivery-path-live');box.dataset.result=JSON.stringify({...p,terminals:route.terminals,in_core_replay:p.source_class==='core',optical_PEX_or_calibrated_lengths:false});box.replaceChildren();for(const text of [p.id+' · '+p.kind+' · '+p.length_um.toFixed(6)+' µm','GDS component '+p.gds_route_component+'：'+route.terminals.join(' ↔ '),p.source_class==='core'?'core 內，加入本輪模型':'EC fan，列入線長表但在本輪 core 參考面之外','名義中心線長度，不是校準光學 PEX']){const d=document.createElement('div');d.textContent=text;box.append(d);}}[which,gate,pattern].forEach(el=>el.addEventListener('change',show));path.addEventListener('change',showPath);show();showPath();document.querySelector('#delivery-generate').addEventListener('click',()=>{const box=document.querySelector('#delivery-json');box.hidden=false;box.value=JSON.stringify({step:'M2 S7',learner_name:document.querySelector('#delivery-name').value,path_and_reference_plane:document.querySelector('#delivery-path-notes').value,replay_and_compensation:document.querySelector('#delivery-replay-notes').value,remaining_qualification:document.querySelector('#delivery-limit-notes').value,physical_function_qualified:false,instructor_review:'pending',date:new Date().toISOString()},null,2);box.focus();box.select();});})();</script>'''
nav=''.join(f'<a href="{h}">{t}</a>' for h,t in [('../Lab06b_index.html','總覽與報告入口'),('plan.html','完整規劃'),('m2_s6.html','M2 S6｜規則與連通'),('#package','交付包與版本'),('#length','路徑與參考面'),('#model','複數傳播模型'),('#replay','400 筆比較與補償'),('#sensitivity','凍結候選靈敏度'),('#portable','搬移重播與負例'),('#ready','資格邊界'),('#submit','學員交付')])
html=f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M2 S7｜交付封裝、路徑回註與重播｜Lab06b</title><link rel="stylesheet" href="../assets/course.css"></head><body><header class="top"><a href="../Lab06b_index.html"><b>LAB06b</b>　PIC Chip 學員實作課程</a><small>2026-10-31 · M2 S7</small></header><div class="layout"><aside><strong>學習與實作入口</strong>{nav}<p class="muted">教學交付包／模型重播通過<br>學員作答待提交</p></aside><main><button class="print" onclick="window.print()">列印／另存 PDF</button><div class="hero"><div class="eyebrow">MODULE 2 · STEP 7 · 60 MIN</div><h1>M2 S7｜交付封裝、路徑回註與重播</h1><p class="lead">把採用版圖、參考面、模型假設與功能比較一起交付；讓另一個路徑中的重播能回答同一個問題。</p><span class="tag ok">50 檔案／400 比較</span><span class="tag">80 → 53 → 80</span><span class="tag wait">實體功能未驗證</span></div>{body}<footer>正式工作區 C:\\EDA_Codex\\Lab06b；D 槽唯讀。本步為版本封裝與明示模型重播；foundry、EC、MMI 與熱電資格仍待建立。</footer></main></div></body></html>'''
(ROOT/'course/m2_s7.html').write_text(clean_course_html(html),encoding='utf-8')
for rel in ['Lab06b_index.html','course/plan.html','course/m0_s1.html','course/m0_s1_foundation.html','course/m0_s2.html','course/m0_s3.html','course/m1_s1.html','course/m1_s2.html','course/m1_s3.html','course/m1_s4.html','course/m1_s5.html','course/m2_s1.html','course/m2_s2.html','course/m2_s3.html','course/m2_s4.html','course/m2_s5.html','course/m2_s6.html','analysis/lab01a_7_6.html','reference/source_context.html']:
    p=ROOT/rel;text=p.read_text(encoding='utf-8');href=('../' if '/' in rel else '')+'course/m2_s7.html'
    if f'href="{href}"' not in text:text=text.replace('</aside>',f'<a href="{href}">M2 S7｜封裝、回註與重播</a></aside>',1)
    if rel=='Lab06b_index.html':
        panel='<!-- M2S7:STATUS --><div class="callout good"><b>目前進度：</b>M2 S7 教學交付包與搬移重播通過；68 段路徑對照 33 條 GDS 連接，400 筆比較完整。<a href="course/m2_s7.html">進入 M2 S7 →</a><br>理想 80/80 → 原相位線長回註 53/80 → 模型候選 80/80；尚未建立實體功能資格。下一步 M3 S1：從零重建與驗收。</div><!-- /M2S7:STATUS -->'
        text=re.sub(r'<!-- (?:M2S6|M2S7):STATUS -->.*?<!-- /(?:M2S6|M2S7):STATUS -->',lambda m:panel,text,count=1,flags=re.S)
        text=text.replace('S1～S6 邊界、電路、介面與現有規則／連通驗證通過；S7 待實作','S1～S7 教材、版圖、現有檢查與模型交付完成；實體功能資格待驗證')
        text=text.replace('M0、M1 與 M2 S1～S6 核心已實跑','M0、M1 與 M2 S1～S7 核心已實跑').replace('後續交付封裝、路徑回註與重播依關卡進行；foundry 與 EC／熱電資格邊界維持明示。','M2 交付包可重播；下一步 M3 獨立重建與驗收，foundry、EC／MMI／熱電資格邊界維持明示。')
        if '<td>M2 S7 主實作</td>' not in text:text=text.replace('<tr><td>M2 S6 主實作</td>','<tr><td>M2 S7 主實作</td><td><a href="course/m2_s7.html">交付封裝、路徑回註與重播</a></td><td>50 檔案、68 路徑、400 筆比較與搬移重播</td></tr><tr><td>M2 S6 主實作</td>',1)
        card='<article class="card"><div class="num">M2 S7</div><h3>封裝、路徑回註與重播</h3><p>保留原設定的回註失敗，另存模型候選；搬移交付包核對相同結果。</p><a href="course/m2_s7.html">進入本步 →</a></article>'
        text=re.sub(r'<!-- (?:M2S6|M2S7):CARD -->.*?<!-- /(?:M2S6|M2S7):CARD -->',lambda m:'<!-- M2S7:CARD -->'+card+'<!-- /M2S7:CARD -->',text,flags=re.S)
    if rel=='course/plan.html':text=text.replace('<td>M2 s7<br>1 h</td>','<td><a href="m2_s7.html">M2 s7</a><br>1 h</td>')
    p.write_text(text,encoding='utf-8')
CFG['progress']['M2_S7']='teaching delivery packaged; relocated integrity, 400-case uniform-neff core replay and external pre-DRC/geometric recheck passed; physical function unqualified; learner submission pending'
CFG['progress']['M3_S1']='next step: clean project rebuild and acceptance'
(ROOT/'config/course.json').write_text(json.dumps(CFG,ensure_ascii=False,indent=2),encoding='utf-8')
template=dict(step='M2 S7',learner_name='',path_and_reference_plane='',replay_and_compensation='',remaining_qualification='',physical_function_qualified=False,instructor_review='pending')
(ROOT/'learner/m2_s7_observations.template.json').write_text(json.dumps(template,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=ROOT/'README_Lab06b_Course.md';text=p.read_text(encoding='utf-8').replace('下一步 M2 S7：交付封裝、路徑回註與重播。','M2 S7：scripts/run_m2_s7.ps1；交付包 delivery/Lab06b_M2_PIC_delivery.zip，原設定線長回註 53/80，另存模型候選 80/80；實體資格未驗證。\n下一步 M3 S1：從零重建與驗收。');p.write_text(text,encoding='utf-8')
print('M2 S7 course rendered; packaged model replay, not physical acceptance')
