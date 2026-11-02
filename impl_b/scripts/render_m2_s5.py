from report_policy import clean_course_html
"""Student lesson: reference ECs, physical PADs and selected GND connectivity."""
from pathlib import Path
from html import escape
import json,re
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/m2_s5/out'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
D=load(OUT/'interface_results.json');I=load(OUT/'chip_info.json');PH=load(ROOT/'phase_settings.json');CFG=load(ROOT/'config/course.json')
def table(caption,headers,rows):
    return '<div class="scroll"><table><caption>'+caption+'</caption><thead><tr>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def pre(s):return '<pre><code>'+escape(s)+'</code></pre>'
reg=sum(v['passed'] for v in D['regression'].values());R=D['readback'];state='EC／PAD／GND 初版幾何與指定連通檢查通過' if D['core_passed'] else '介面檢查有未解決項'
body=f'''<div class="callout {'good' if D['core_passed'] else 'warn'}"><b>本輪成果：</b>10 個參考 EC、14 個訊號 PAD、2 個 GND PAD；初版設計區 {D['chip_size_um'][0]:g} × {D['chip_size_um'][1]:g} µm。KLayout 從實際 GDS 回讀得到 14 個獨立訊號金屬網＋1 個共地網；十四個 heater 各接到自己的訊號與 GND。<br>沿用 S1 的 A 端驅動／B 端回地，S4 採用版 core 逐層幾何完全一致。EC 耦合效率、heater 偏壓及共地阻抗仍未校正。</div>
<h2 id="predict">1．學員目標：把 core 接到光纖與驅動器</h2><p>建議 90 分鐘：接口與參考面 15 分、EC／光學扇出 20 分、PAD／共地 25 分、回讀與對照 20 分、記錄 10 分。前置：<a href="m2_s1.html">S1 邊界與 I/O</a>、<a href="m2_s4.html">S4 採用版 core</a>。</p><ol><li>先預測 10 個光學埠的去向，以及 14 路相位驅動與 GND 對應多少個實體 PAD。</li><li>由目前採用版 core 的 GDS 加入 EC、光學扇出與電氣接口，不重新改造 core 軌距或 heater 位置。</li><li>逐一追蹤外部 DRV → PAD → heater A／B → GND PAD → DRV_RETURN。</li><li>匯出晶片 GDS 與對照表，再從磁碟檔案回讀幾何及指定連通關係。</li></ol>
<h2 id="chip">2．完整介面配置與範圍</h2><figure><img src="figures/m2_s5/chip_annotated.svg" alt="實際 GDS 多邊形繪製的左右十個參考 EC、十四個訊號 PAD 與兩個共地 PAD"><figcaption>圖 1｜以 KLayout 回讀的多邊形繪製。上方有 8 個訊號 PAD＋2 個 GND PAD，下方有 6 個訊號 PAD。外框是本步設計區與名義端面位置，未代表已完成切割、封裝或製程簽核。</figcaption></figure>
<p>程式先核對 <a href="../config/m2_current_core.json">S4 採用版索引</a> 的 SHA-256，再把原 GDS 階層複製到新晶片中。KLayout 對內嵌 core 的 GDS 3／39／41／99／100 做 XOR 比較，皆無幾何差異；原檔與原設定也保留。新增介面參數位於 <a href="../config/m2_chip_interfaces.json">m2_chip_interfaces.json</a>，本步採用索引為 <a href="../config/m2_current_chip.json">m2_current_chip.json</a>。</p>
<h2 id="ec">3．EC 是參考幾何，不能直接當作已驗證耦合器</h2><div class="callout warn"><b>本機 PDK 查核結果：</b>未在已安裝 CORNERSTONE 的匯出介面找到可直接使用的標準 EC cell。本步依課程原始參考做 thin-Si taper 幾何，使用本機 PDK 的實際圖層映射；沒有建立經量測或電磁模擬驗證的 EC compact model。耦合損耗與相位響應均保持 pending，未宣稱特定光纖型號或耦合效率。</div>
<figure><img src="figures/m2_s5/EC_geometry.svg" alt="參考 EC 的 SLAB taper 與 strip 轉接俯視 mask 幾何"><figcaption>圖 2｜俯視幾何的縱軸放大，以便辨識 tip 與各層。名義 220 nm Si、120 nm rib 蝕刻可留下 100 nm Si；此堆疊說明不替代製程窗口、模式轉換及切割端面的驗證。參考 <a href="../analysis/lab01a_7_6.html">Lab01a §7.6 光場分析</a> 理解為何幾何相接仍需光場驗證。</figcaption></figure>'''
body+=table('表 1｜本輪參考 EC 的幾何與圖層',['項目','內容'],[
    ('長度／facet tip','260 µm／0.25 µm；tip 位於 SLAB 層，不是把 strip 最小線寬放寬為 0.25 µm。'),
    ('GDS 5：SLAB','tip 直段 30 µm，再展寬至 1 µm，最後轉接到 0.45 µm。'),
    ('GDS 4：WG HOLE','230 × 20 µm 的參考 partial-etch window；實際製程層組合仍待驗證。'),
    ('GDS 3：WG','末段 strip 從 0.35 µm 轉接到 0.45 µm；接到 600 µm 扇出。'),
    ('光學陣列','左右各五路，名義 pitch 250 µm；未指定實際光纖 MFD 或對準公差。'),
    ('驗證範圍','檢查 facet 內側 SLAB、EC strip 端與 core 接縫的幾何覆蓋；不等於 3D 模式連續性。')])
body+='''<p><a href="../work/m2_s5/out/EC_audit.json">本機 EC／圖層稽核 JSON</a>。十段光學扇出共核對 8030 個中心線頂點／線段中點小區域；長度另列 <a href="../work/m2_s5/out/fan_lengths.csv">fan_lengths.csv</a>，供後續損耗與相位回註。</p>'''
body+=table('表 2｜十個光學接口與去向',['接口／EC','core 埠','facet x,y µm','外部去向'],[(p['interface_id']+'／'+p['EC_id'],p['core_port'],str(p['facet_um']),escape(p['external_endpoint'])) for p in I['optical_io']])
body+='''<div class="callout warn"><b>參考面要保留：</b>M1 的 data=1 場振幅 1、R 場振幅 3／功率 9，定義在 core 輸入面，並非雷射端或光纖端的功率。不同 EC 與扇出會帶來不同複數傳輸，未校正前不能假設光纖端直接設定 R=3 就能維持原真值表。out1／out3 經輸出路徑與接收器後，仍需回推到等效 core 功率差。</div>
<h2 id="pads">4．14 個驅動 PAD＋2 個 GND PAD</h2><p>S1 的 14 路驅動＋1 個邏輯共地角色，在本步實作成 16 個實體 PAD：14 個訊號、2 個同網 GND。兩個 GND PAD 不是兩條獨立回路，也沒有因此驗證共地壓降或熱串擾。PAD 為 80 × 80 µm，走線寬 8 µm。</p>
<figure><img src="figures/m2_s5/drive_return.svg" alt="DRV00 經 PAD_DRV00 到 theta1 heater A，再由 B 回共地 PAD 與外部回流的路徑"><figcaption>圖 3｜每個 heater 是有意義的電阻支路。只看 GDS 41 金屬時應有 15 個網；不能把 HT 電阻也當成理想金屬一起合併，再把整個電阻網路判成訊號短路。</figcaption></figure>'''
signals=[p for p in I['pads'] if p['net']!='GND']
body+=table('表 3｜PAD↔driver↔heater↔相位；A 驅動、B 回地',['PAD','driver','相位通道','heater','PAD x,y µm'],[(p['pad_id'],p['driver_channel'],p['channel'],p['heater_logical_id'],str(p['center_um'])) for p in signals])
body+='''<p><a href="../work/m2_s5/out/pad_heater_map.csv">完整 PAD 對照 CSV</a> 包含每個 PAD、heater 中心與 A／B 接觸座標，按 θ1～7、φ1～7 向量順序輸出。相位值由通道名稱映射，沒有誤當成 θφ 交錯排列；偏壓校正欄位仍是 pending。</p>
<h2 id="ground">5．保留 core，以分欄轉折的 GND 配線避開訊號</h2><p>core 只有 30 µm 軌距，局部接觸占用一部分垂直空間。這裡依四欄 heater 的位置選擇不同回地 y，並在欄界前轉折；沒有將 core 改成另一個軌距。訊號由 A 接觸向上／下外圍 PAD，B 接觸則向欄內共地走線。</p>
<figure><img src="figures/m2_s5/ground_routing.svg" alt="按四欄轉折的共地線與獨立訊號走線，保留原 core 軌距"><figcaption>圖 4｜紫虛線只標出已存在金屬的共地中心線。Si 與金屬在俯視圖的交疊屬不同製程層；這不等同同層短路，也不表示已驗證金屬對光學損耗或熱的影響。</figcaption></figure>'''
body+=table('表 4｜共地位置與兩個實體 GND PAD',['項目','數值'],[(f'L{k} GND y',f'{y:g} µm') for k,y in enumerate(I['ground_column_y'])]+[(p['pad_id'],str(p['center_um'])+' µm → DRV_RETURN') for p in I['pads'] if p['net']=='GND'])
body+='''<h3>逐一追蹤 PAD：相位不是電壓</h3><section class="panel"><label for="chip-pad">實體 PAD</label><select id="chip-pad">'''+''.join(f'<option>{p["pad_id"]}</option>' for p in I['pads'])+'''</select><label for="chip-gate">沿用 M1 相位程式</label><select id="chip-gate">'''+''.join(f'<option>{g}</option>' for g in PH['programs'])+'''</select><div id="chip-live" class="answers" aria-live="polite" style="overflow-wrap:anywhere"></div></section>
<h3>逐一追蹤光學接口：facet → core → 外部設備</h3><section class="panel"><label for="chip-optical">光學接口</label><select id="chip-optical">'''+''.join(f'<option>{p["interface_id"]}</option>' for p in I['optical_io'])+'''</select><div id="chip-optical-live" class="answers" aria-live="polite" style="overflow-wrap:anywhere"></div></section>'''
body+='<script>const CHIP_INFO='+json.dumps(I)+';const CHIP_READBACK='+json.dumps(R)+';const CHIP_PHASES='+json.dumps(PH)+';</script>'
body+='''<script>(()=>{const pad=document.querySelector('#chip-pad'),gate=document.querySelector('#chip-gate'),opt=document.querySelector('#chip-optical');function show(){const p=CHIP_INFO.pads.find(r=>r.pad_id===pad.value),channel=p.channel||null,phase=channel===null?null:CHIP_PHASES.programs[gate.value][CHIP_PHASES.channel_order.indexOf(channel)],component=CHIP_READBACK.pad_components[p.pad_id][0];const result={pad_id:p.pad_id,channel,phase_rad:phase,center_um:p.center_um,drive_endpoint:p.drive_endpoint||null,return_endpoint:p.return_endpoint||null,metal_component:component,voltage:null,return_net:'GND'};const box=document.querySelector('#chip-live');box.dataset.result=JSON.stringify(result);box.replaceChildren();const texts=channel===null?[p.pad_id+'：共地網 → DRV_RETURN；與另一個 GND PAD 同網','沒有相位設定，也不是第 15／16 路相位']:['外部 '+p.driver_channel+' → '+p.pad_id+' → '+p.drive_endpoint,p.return_endpoint+' → 分欄 GND → PAD_GND_W／E → DRV_RETURN',channel+' / '+gate.value+' = '+phase.toFixed(9)+' rad；偏壓校正仍待完成','A 接觸 '+p.signal_contact_um.join(', ')+'；B 接觸 '+p.return_contact_um.join(', ')+' µm'];for(const text of [...texts,'PAD 中心 '+p.center_um.join(', ')+' µm；GDS 41 元件 '+component+'（本次回讀編號）']){const div=document.createElement('div');div.textContent=text;box.append(div);}}function optical(){const p=CHIP_INFO.optical_io.find(r=>r.interface_id===opt.value),box=document.querySelector('#chip-optical-live');box.dataset.result=JSON.stringify(p);box.replaceChildren();for(const text of [p.interface_id+' / '+p.EC_id+' ↔ '+p.core_port,p.direction==='in'?p.external_endpoint+' → facet → EC → 扇出 → '+p.core_port:p.core_port+' → 扇出 → EC → '+p.external_endpoint,'facet '+p.facet_um.join(', ')+' µm；strip '+p.strip_um.join(', ')+' µm；core '+p.core_um.join(', ')+' µm','EC 響應與路徑相位：pending；R=3 與 data=1 均指 core 參考面']){const d=document.createElement('div');d.textContent=text;box.append(d);}}for(const el of [pad,gate])el.addEventListener('change',show);opt.addEventListener('change',optical);show();optical();})();</script>
<h2 id="checks">6．從實際 GDS 回讀指定連通關係</h2>'''
body+=table('表 5｜本輪驗證與限制',['項目','結果'],[
    ('core 原幾何','五個層的內嵌 core XOR 比較為空；S4 原檔雜湊不變。'),
    ('16 個實體 PAD','14 個訊號 PAD 分別落在 14 個獨立 GDS 41 金屬網；兩個 GND PAD 同在第 15 個網。'),
    ('heater 接觸','每個 HT 區只接觸自己的訊號網與共地網；逐一確認 PAD→A、B→GND。'),
    ('光學端點與扇出','30 個端點覆蓋核對、10 段扇出共 8030 個中心線取樣通過；沒有以 buffer 填補幾何缺口。'),
    ('局部規則篩查','Si／HT／金屬各做一組線寬與間距篩查，六項皆零警示；EC 的製程／SLAB 規則尚未完整驗證。'),
    ('本步測試／既有回歸',f"{D['unit_tests']['passed']}/{D['unit_tests']['run']} 新介面測試；{reg}/{sum(v['run'] for v in D['regression'].values())} 既有回歸通過。"),
    ('M1 基準','原規格、相位、ZIP 未改，基準仍重播 80/80；未將此當成加上 EC 後的實體光路驗收。')])
fault_names={'signal_GND_short':'訊號接到 GND 的金屬短路','theta1_return_open':'theta1 的 B 回地走線斷口','theta1_A_B_mapping_swapped':'theta1 A／B 對照誤換'}
body+=table('表 6｜負例只在隔離副本',['負例','類型','被抓到的檢查'],[(fault_names[r['name']],'實際錯誤 GDS' if r['type']=='actual_fault_GDS' else '錯誤 sidecar 對照',', '.join(r['failed_checks'])) for r in D['controlled_faults']])
body+='''<p>前兩種負例先產生獨立 GDS、重新讀取，再使用同一份電氣幾何核對器；第三種只交換對照資料中的 A／B。正式晶片 GDS 未被修改。<a href="../work/m2_s5/out/connectivity_faults.json">負例結果</a> · <a href="../work/m2_s5/out/chip_readback.json">實際 GDS 回讀結果</a>。</p>
<div class="callout warn"><b>本步的選定連通檢查不是完整 LVS／製程簽核。</b>尚需驗證 EC 製程層與模式響應、完整 DRC／連通、切割與封裝條件、heater 電阻／相位→偏壓、共地阻抗／熱串擾，以及光學路徑損耗與相位。沒有在此填入假設的 Vπ、驅動電流或耦合損耗。</div>
<h2 id="run">7．重跑與交付檔案</h2>'''
body+=pre(r"""Set-Location -LiteralPath 'C:\EDA_Codex\Lab06b'
& .\scripts\run_m2_s5.ps1
# KLayout 開啟 work\m2_s5\out\b7_ec_pad.gds
# top cell：LAB06B_B7_EC_PAD_CHIP
# 載入同資料夾 chip_layers.lyp 作分層檢視。""")
body+=table('表 7｜可下載成果',['檔案','用途'],[
    ('<a href="../work/m2_s5/out/b7_ec_pad.gds">b7_ec_pad.gds</a> · <a href="../work/m2_s5/out/chip_layers.lyp">KLayout 圖層設定</a>','初版 EC／PAD／GND 介面幾何，非製程簽核完成版。'),
    ('<a href="../work/m2_s5/out/pad_heater_map.csv">PAD↔heater↔相位 CSV</a> · <a href="../work/m2_s5/out/ground_pads.csv">GND PAD CSV</a>','驅動通道、A/B 接觸、PAD 中心與待校正欄位。'),
    ('<a href="../work/m2_s5/out/optical_io.csv">光學 I/O CSV</a> · <a href="../work/m2_s5/out/fan_lengths.csv">扇出長度 CSV</a>','十個光學接口、外部去向、參考面與幾何長度。'),
    ('<a href="../work/m2_s5/out/chip_info.json">完整介面 JSON</a> · <a href="../config/m2_current_chip.json">本步採用版索引</a>','M2 S6 讀取此索引及雜湊，承接本步圖形與對照。'),
    ('<a href="../work/m2_s5/out/interface_results.json">完整驗證結果</a>','本步測試、回歸、指定連通與來源雜湊。'),
    ('<a href="../work/common/chip_interfaces.py">介面建構原始碼</a> · <a href="../work/m2_s5/merge_verify.py">合併與回讀</a>','可重跑的幾何產生與獨立核對。')])
body+='''<h2 id="submit">8．學員交付與 M2 S6 交接</h2><ol><li>提交 GDS、PAD／GND／光學 I/O／長度 CSV，並在 KLayout 分別截取光學、HT 與金屬圖層。</li><li>任選兩個相位通道，從外部 driver 追到 PAD、A、B、GND 與回流；說明為何 16 個 PAD 對應 15 個金屬網。</li><li>解釋兩個 GND PAD 共網與 HT 電阻支路，列出共地阻抗及熱校正尚未完成的量。</li><li>解釋 EC 參考幾何、名義蝕刻堆疊與模式／耦合效率驗證的差別，指出 R=3 的參考面。</li><li>提交自己的觀察與下一關檢查清單；學員作答由講師另行驗收。</li></ol>
<section class="panel"><label for="chip-name">學員姓名</label><input id="chip-name"><label for="chip-io-notes">EC／光學接口與參考面觀察</label><textarea id="chip-io-notes"></textarea><label for="chip-pad-notes">PAD／heater A／B／共地路徑</label><textarea id="chip-pad-notes"></textarea><label for="chip-pending-notes">校正、製程與下一關待辦</label><textarea id="chip-pending-notes"></textarea><button id="chip-generate">產生 M2 S5 學習記錄 JSON</button><textarea id="chip-json" hidden readonly aria-label="M2 S5 學習記錄 JSON" style="min-height:220px"></textarea><p class="muted">複製到 learner/m2_s5_observations.json；<a href="../learner/m2_s5_observations.template.json">空白範本</a>。</p></section>
<script>document.querySelector('#chip-generate').addEventListener('click',()=>{const box=document.querySelector('#chip-json');box.hidden=false;box.value=JSON.stringify({step:'M2 S5',learner_name:document.querySelector('#chip-name').value,optical_interfaces:document.querySelector('#chip-io-notes').value,pad_heater_ground:document.querySelector('#chip-pad-notes').value,calibration_and_pending:document.querySelector('#chip-pending-notes').value,instructor_review:'pending',date:new Date().toISOString()},null,2);box.focus();box.select();});</script>
<p><b>下一步 M2 S6：</b>從目前採用的晶片 GDS 與對照表執行完整規則／連通檢查，處理並記錄實際違規，再進行最終路徑回註。</p>
<p class="muted">技術參考：<a href="https://cornerstone.sotonfab.co.uk/mpw/technology-platforms/">CORNERSTONE 技術平台</a>、<a href="https://academy.lucedaphotonics.com/pdks/cornerstone/cornerstone">Luceda CORNERSTONE PDK 文件</a>、<a href="https://www.klayout.de/doc/code/class_Cell.html">KLayout Cell.copy_tree</a>。本輪元件可用性與圖層以已安裝 PDK 稽核為準，沒有把其他版本或其他 PDK 的 EC 當成本機元件。</p>'''
nav=''.join(f'<a href="{h}">{t}</a>' for h,t in [('../Lab06b_index.html','總覽與報告入口'),('plan.html','完整規劃'),('m2_s4.html','M2 S4｜採用版 core'),('#chip','整體介面配置'),('#ec','參考 EC／光學 I/O'),('#pads','PAD 與相位對照'),('#ground','共地與路徑追蹤'),('#checks','GDS 回讀與負例'),('#run','執行與下載'),('#submit','學員交付')])
html=f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M2 S5｜EC 光學 I/O、heater PAD 與 GND｜Lab06b</title><link rel="stylesheet" href="../assets/course.css"></head><body><header class="top"><a href="../Lab06b_index.html"><b>LAB06b</b>　PIC Chip 學員實作課程</a><small>2026-10-31 · M2 S5</small></header><div class="layout"><aside><strong>學習與實作入口</strong>{nav}<p class="muted">{state}<br>學員作答待提交</p></aside><main><button class="print" onclick="window.print()">列印／另存 PDF</button><div class="hero"><div class="eyebrow">MODULE 2 · STEP 5 · 90 MIN</div><h1>M2 S5｜EC 光學 I/O、heater PAD 與 GND</h1><p class="lead">保留已檢視的 core，接出光學與電氣接口，從 GDS 回讀每個 PAD 與回流的去向。</p><span class="tag ok">10 EC／14 signal PAD／2 GND PAD</span><span class="tag">core 幾何不變</span><span class="tag wait">參考 EC，響應待驗證</span></div>{body}<footer>正式工作區 C:\\EDA_Codex\\Lab06b；D 槽唯讀。此為初版介面幾何及選定連通核對；完整製程、封裝、光學與熱電校正仍待完成。</footer></main></div></body></html>'''
(ROOT/'course/m2_s5.html').write_text(clean_course_html(html),encoding='utf-8')
for rel in ['Lab06b_index.html','course/plan.html','course/m0_s1.html','course/m0_s1_foundation.html','course/m0_s2.html','course/m0_s3.html','course/m1_s1.html','course/m1_s2.html','course/m1_s3.html','course/m1_s4.html','course/m1_s5.html','course/m2_s1.html','course/m2_s2.html','course/m2_s3.html','course/m2_s4.html','analysis/lab01a_7_6.html','reference/source_context.html']:
    p=ROOT/rel;text=p.read_text(encoding='utf-8');href=('../' if '/' in rel else '')+'course/m2_s5.html'
    if f'href="{href}"' not in text:text=text.replace('</aside>',f'<a href="{href}">M2 S5｜EC／PAD／GND</a></aside>',1)
    if rel=='Lab06b_index.html':
        panel='<!-- M2S5:STATUS --><div class="callout good"><b>目前進度：</b>M2 S5 初版 EC／PAD／GND 幾何與選定連通核對通過；10 個參考 EC、14 個訊號 PAD＋2 個 GND PAD。<a href="course/m2_s5.html">進入 M2 S5 →</a><br>EC 響應、完整製程 DRC／LVS、熱電校正與相位回註仍待驗證。下一步 M2 S6。</div><!-- /M2S5:STATUS -->'
        text=re.sub(r'<!-- (?:M2S4|M2S5):STATUS -->.*?<!-- /(?:M2S4|M2S5):STATUS -->',lambda m:panel,text,count=1,flags=re.S)
        text=text.replace('S1～S4 邊界、電路、core 與檢視通過；S5～S7 待實作','S1～S5 邊界、電路、core 與介面通過；S6～S7 待實作')
        text=text.replace('M0、M1 與 M2 S1～S4 核心已實跑','M0、M1 與 M2 S1～S5 核心已實跑').replace('後續 EC／PAD／GND、完整驗證、路徑回註與最終交付依關卡進行。','後續完整規則／連通驗證、EC／熱電響應、路徑回註與最終交付依關卡進行。')
        if '<td>M2 S5 主實作</td>' not in text:text=text.replace('<tr><td>M2 S4 主實作</td>','<tr><td>M2 S5 主實作</td><td><a href="course/m2_s5.html">EC 光學 I/O、heater PAD 與 GND</a></td><td>晶片 GDS、PAD↔heater↔相位與光學接口表</td></tr><tr><td>M2 S4 主實作</td>',1)
        card='<article class="card"><div class="num">M2 S5</div><h3>EC 光學 I/O、PAD 與 GND</h3><p>保留 core 接出十個參考 EC、十四路驅動與兩個共地 PAD。</p><a href="course/m2_s5.html">進入本步 →</a></article>'
        text=re.sub(r'<!-- (?:M2S4|M2S5):CARD -->.*?<!-- /(?:M2S4|M2S5):CARD -->',lambda m:'<!-- M2S5:CARD -->'+card+'<!-- /M2S5:CARD -->',text,flags=re.S)
    if rel=='course/plan.html':text=text.replace('<td>M2 s5<br>1.5 h</td>','<td><a href="m2_s5.html">M2 s5</a><br>1.5 h</td>')
    p.write_text(text,encoding='utf-8')
CFG['progress']['M2_S5']='initial reference EC/PAD/GND geometry and selected GDS connectivity passed; calibration and full validation pending; learner submission pending' if D['core_passed'] else 'interface checks unresolved'
CFG['progress']['M2_S6']='next step: full rule and connectivity checks with actual violation records'
(ROOT/'config/course.json').write_text(json.dumps(CFG,ensure_ascii=False,indent=2),encoding='utf-8')
p=ROOT/'README_Lab06b_Course.md';text=p.read_text(encoding='utf-8').replace('下一步 M2 S5：EC 光學 I/O、heater PAD 與 GND。','M2 S5：scripts/run_m2_s5.ps1；晶片與對照表見 config/m2_current_chip.json。\n下一步 M2 S6：完整規則／連通檢查與違規記錄。');p.write_text(text,encoding='utf-8')
print('M2 S5 page rendered; core:',D['core_passed'])
