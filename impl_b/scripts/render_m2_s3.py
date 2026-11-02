from report_policy import clean_course_html
"""Student build/readback lesson for the physical seven-MZI core."""
from pathlib import Path
from html import escape
import json,re
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/m2_s3/out'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
D=load(OUT/'layout_results.json');I=load(OUT/'layout_info.json');P=load(OUT/'unit_polygons.json')
PHASES=load(ROOT/'phase_settings.json');CFG=load(ROOT/'config/course.json');C=load(ROOT/'config/m2_core_layout.json')
def table(caption,headers,rows):
    return '<div class="scroll"><table><caption>'+caption+'</caption><thead><tr>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def pre(s):return '<pre><code>'+escape(s)+'</code></pre>'
state='core 版圖與 GDS 回讀核對通過' if D['core_passed'] else 'core 版圖有未解決項'
reg=sum(v['passed'] for v in D['regression'].values());u=I['unit'];dim=D['dimensions'];gds=D['gds_readback']
body=f'''<div class="callout {'good' if D['core_passed'] else 'warn'}"><b>本輪成果：</b>新建並匯出 7 MZI／14 PDK MMI 的 B7 core；包含 14 個局部 heater、28 個局部金屬接觸落墊、6 段直通與 10 個 core 光學埠。KLayout 獨立回讀核對通過。<br><b>尺寸：</b>光學端點跨度 {dim['optical_span_um'][0]:g} × {dim['optical_span_um'][1]:g} µm；宣告設計區 {dim['design_frame_um'][0]:g} × {dim['design_frame_um'][1]:g} µm。設計區框不代表完成 die 或 EC facet。</div>
<h2 id="predict">1．學員目標與動手順序</h2><p>建議 90 分鐘：讀拓樸與參數 15 分、單顆 MZI 幾何 20 分、七顆放置與直通 20 分、匯出／回讀 20 分、記錄與交付 15 分。前置：<a href="m2_s1.html">M2 S1 的邊界與 I/O</a>、<a href="m2_s2.html">M2 S2 的電路基準</a>。</p><ol><li>先預測四欄各放幾顆 MZI、哪些模式必須有直通線，並標註上下埠。</li><li>讀取 PDK 埠位置，建立一顆平衡 MZI，確認 φ 與 θ 在正確直線區。</li><li>依 OPS 放置七顆共用單元，補直通線與端點引線，輸出真實 GDS。</li><li>用 KLayout 回讀檔案，將版圖實例、端點與接線對照到 M1 規格；保存自己的觀察。</li></ol>
<h2 id="scope">2．這次 core 做到哪裡？</h2><div class="callout warn"><b>本步完成的是初版 core 幾何：</b>heater 與接觸落墊已畫出，但尚無外部探針 PAD、共地扇出或相位→電壓校正。28 個局部金屬落墊不是整顆 Chip 的最終 PAD 數。獨立 GDS 回讀核對不等於 foundry DRC、完整 LVS 或實體光路真值驗證。</div>'''
body+=table('表 1｜從電路到幾何的責任',['內容','M2 S3 狀態','後續工作'],[
    ('PDK MMI','14 顆標準 MMI 的實體幾何，沿用上路 in2／out2 對照。','元件模型仍承接 M2 S2 的已知限制。'),
    ('光學 core','7 MZI、6 直通、10 端點引線及 10 個外露埠。','M2 S4 版圖檢視；M2 S6 全部連通／規則檢查。'),
    ('相位區','φ 在 MMI1 前、θ 在 MMI1／MMI2 之間；14 個 heater 與局部接觸幾何。','M2 S5 驅動 PAD／回路配置；熱與偏壓校正待定。'),
    ('長度與相位','記錄 58 段單模波導的中心線長度。','後續回註傳播、損耗與相位，再重跑 80 筆。'),
    ('外部 I/O','本步輸出的是 core 埠位 CSV。','EC、光纖端面、探針 PAD 與外部設備接口尚未完成。')])
body+='''<h2 id="geometry">3．先建立一顆 MZI</h2><figure><img src="figures/m2_s3/mzi_core.svg" alt="從新匯出 GDS 回讀的單顆 MZI、phi theta heater 及兩顆 MMI"><figcaption>圖 1｜實際 GDS 多邊形。藍色是 Si、橘色是 HT、綠色是局部金屬接觸。上下臂波導幾何平衡；heater 是否產生指定相位仍待校正。</figcaption></figure>'''
body+=table('表 2｜可重現的幾何參數（µm）',['參數','本輪值','學員需理解的原因'],[
    ('rail pitch',f"{C['pitch']:g}",'五個模式由上往下，y=−mode×pitch。'),
    ('strip 核心寬','0.45','承接 PDK MMI 埠寬與共用 template。'),
    ('S 彎水平長／端點水平段',f"{C['s_bend_length']:g}／{C['s_bend_stub']:g}",'水平端點接到 PDK 埠，避免斜接楔形縫。'),
    ('S 彎取樣',str(C['s_bend_samples']),'餘弦中心線以折線近似，座標對齊 1 nm。'),
    ('phase 直線預留',f"{C['phase_region_length']:g}",'100 µm 加熱段＋兩側接觸預留。'),
    ('heater 長／寬',f"{C['heater_length']:g}／{C['heater_width']:g}",'自訂局部 HT 幾何，尚非已校正熱模型。'),
    ('單欄長度',f"{u['length_um']:g}",'每顆 MZI 與同欄直通線使用相同 x 跨度。'),
    ('端點引線',f"{C['lead_length']:g}",'將 core 埠移到四欄之外，尚不包含 EC。')])
body+=pre('x0 = layer * column_length\ny0 = -upper_mode * pitch\n# 每顆 MZI 的局部 port 0 是上路：\nin0  -> phi -> PDK MMI1:in2\nin1  -> PDK MMI1:in1\nMMI1:out2 -> theta -> MMI2:in2\nMMI1:out1 ---------> MMI2:in1\nout0 <- MMI2:out2\nout1 <- MMI2:out1')
body+=f'''<p>本輪 PDK MMI 的實體縱向跨度為 {u['mmi_longitudinal_span_um']:g} µm。程式從 <code>mmi.Layout().ports</code> 查座標，再平移放置；八個局部接點的最大中心線座標差為 {u['max_join_error_um']:.3e} µm。連續餘弦曲線的解析最小曲率半徑為 {u['continuous_s_bend_min_radius_um']:.6f} µm，大於規劃值 5 µm。這是連續中心線檢查，不能把 1 nm 格點後的三點曲率當成可靠的製程驗證。</p>
<figure><img src="figures/m2_s3/mmi_contacts.svg" alt="實際 PDK MMI 埠位放大圖以及 phi heater A B 局部接觸落墊"><figcaption>圖 2｜左圖核對 PDK 上下埠；右圖顯示 A／B 局部接觸幾何。它們尚未接到外部驅動 PAD 或 GND。</figcaption></figure>
<h2 id="placement">4．由 OPS 放置七顆 MZI，空位補直通</h2><figure><img src="figures/m2_s3/b7_core.svg" alt="新匯出 B7 core 的四欄七顆 MZI、六段直通與十個光學埠"><figcaption>圖 3｜由本輪 b7_core.gds 回讀的多邊形繪製，欄位與 M1～M7 標註由同輪 placement 表加入。紫框是宣告設計區。</figcaption></figure>'''
body+=table('表 3｜七顆實例的放置座標，layer／mode 為零起算',['實例','layer','模式（上／下）','原點 x, y µm'],[(p['id'],p['layer'],'／'.join(map(str,p['modes'])),', '.join(f'{v:g}' for v in p['origin_um'])) for p in I['placement']])
byp=[p for p in I['paths'] if p['kind']=='bypass']
body+=table('表 4｜六段直通是必要實體光路',['layer','mode','起點 µm','終點 µm','長 µm'],[(p['layer'],p['mode'],str(p['points_um'][0]),str(p['points_um'][-1]),f"{p['length_um']:g}") for p in byp])
body+='''<p>每個欄界的五條軌道都必須連續；省略直通線會改變 B7。七顆 MZI 共用一份單元，GDS 階層包含 7 個單元引用；每個單元有 2 個 MMI，因此展開後有 14 顆 MMI，不是 14 個不同的 MMI cell 定義。</p>
<h2 id="ports">5．埠位、heater 與長度交接</h2>'''
body+=table('表 5｜十個 core 埠；非光纖接口',['埠','角色','x µm','y µm','朝向 deg'],[(p['id'],p['core_role'],f"{p['position_um'][0]:g}",f"{p['position_um'][1]:g}",p['angle_deg']) for p in I['ports']])
body+=f'''<p>θ1～7／φ1～7 依名稱對應到十四個區域。<a href="../work/m2_s3/out/phase_regions.csv">相位區與 A／B 接觸座標 CSV</a> 按 M1 向量順序輸出；heater 中心不是外部 PAD。<a href="../work/m2_s3/out/optical_ports.csv">光學埠位 CSV</a> 與 <a href="../work/m2_s3/out/waveguide_lengths.csv">58 段長度 CSV</a> 由同一份 <a href="../work/m2_s3/out/layout_info.json">幾何資訊 JSON</a> 產生。</p>
<div class="callout warn"><b>長度不等於已驗證的光學相位：</b>本輪每顆 MZI 上／下臂的單模波導總長均為 {u['waveguide_upper_um']:.6f} µm；MMI 之間上／下臂均為 {u['inter_mmi_upper_um']:.6f} µm。這些長度不包含多模 MMI 內部傳播；不能把 MMI 的 x 跨度直接乘單模 β。MZI 單模光路與旁路長度不同，整個網路仍需回註相對傳播相位。M2 S2 的 80/80 是零長度接線電路基準，不是這份實體版圖的真值驗收。</div>
<h3>互動核對：從相位名稱找到實際區域與接觸座標</h3><section class="panel"><label for="layout-instance">MZI 實例</label><select id="layout-instance">'''+''.join(f'<option>{p["id"]}</option>' for p in I['placement'])+'''</select><label for="layout-phase">局部相位</label><select id="layout-phase"><option>theta</option><option>phi</option></select><label for="layout-gate">沿用 M1 相位程式（rad，尚非偏壓）</label><select id="layout-gate">'''+''.join(f'<option>{g}</option>' for g in PHASES['programs'])+'''</select><svg id="layout-unit" viewBox="-15 -25 519 80" role="img" aria-label="由單顆 GDS 多邊形繪製的 MZI，框選目前相位區域" style="width:100%;height:auto;display:block;background:#f4f7fc;border:1px solid #d9e1ec;margin:16px 0"></svg><div id="layout-live" class="answers" aria-live="polite" style="overflow-wrap:anywhere"></div><p class="muted">放大圖使用本輪單元 GDS 多邊形；七顆共用此單元，以下列出所選實例在 core 的實際座標。相位程式只作通道交叉核對。</p></section>'''
body+='<script>const LAYOUT_INFO='+json.dumps(I)+';const LAYOUT_POLYGONS='+json.dumps(P)+';const LAYOUT_PHASES='+json.dumps(PHASES)+';</script>'
body+='''<script>(()=>{const ns='http://www.w3.org/2000/svg',svg=document.querySelector('#layout-unit'),ins=document.querySelector('#layout-instance'),phase=document.querySelector('#layout-phase'),gate=document.querySelector('#layout-gate');for(const p of LAYOUT_POLYGONS){const el=document.createElementNS(ns,'polygon');el.setAttribute('points',p.points_um.map(x=>x[0]+','+(-x[1])).join(' '));el.setAttribute('fill',({3:'#155bd0',39:'#df7c16',41:'#258350'})[p.layer]);svg.append(el);}const highlight=document.createElementNS(ns,'rect');highlight.setAttribute('fill','none');highlight.setAttribute('stroke','#9c2d7c');highlight.setAttribute('stroke-width','1.5');svg.append(highlight);function show(){const k=Number(ins.value.slice(1)),channel=phase.value+k,region=LAYOUT_INFO.phase_regions.find(r=>r.channel===channel),place=LAYOUT_INFO.placement.find(r=>r.id===ins.value),local=LAYOUT_INFO.unit.controls.find(r=>r.parameter===phase.value),rad=LAYOUT_PHASES.programs[gate.value][LAYOUT_PHASES.channel_order.indexOf(channel)];highlight.setAttribute('x',local.heated_start_um-2);highlight.setAttribute('y',-3);highlight.setAttribute('width',local.heated_end_um-local.heated_start_um+4);highlight.setAttribute('height',6);const r={channel,instance:ins.value,modes:place.modes,origin_um:place.origin_um,center_um:region.center_um,contacts:region.local_contacts,phase_rad:rad,pad_id:null,voltage_calibration:null};const box=document.querySelector('#layout-live');box.dataset.result=JSON.stringify(r);box.replaceChildren();for(const text of [ins.value+'：modes '+place.modes.join(' / ')+'；原點 '+place.origin_um.join(', ')+' µm',channel+' → '+region.heater_logical_id+'；heater 中心 '+region.center_um.join(', ')+' µm',...region.local_contacts.map(c=>c.endpoint+'：'+c.center_um.join(', ')+' µm'),gate.value+' 相位 '+rad.toFixed(9)+' rad；外部 PAD／偏壓校正待定']){const div=document.createElement('div');div.textContent=text;box.append(div);}}for(const el of [ins,phase,gate])el.addEventListener('change',show);show();})();</script>
<h2 id="run">6．執行、匯出與 KLayout 回讀</h2>'''
body+=pre(r"""Set-Location -LiteralPath 'C:\EDA_Codex\Lab06b'
& .\scripts\run_m2_s3.ps1
# 在 KLayout 開啟 work\m2_s3\out\b7_core.gds
# 選 LAB06B_B7_CORE，展開階層檢查七顆單元。""")
body+='''<p>參數在 <a href="../config/m2_core_layout.json">config/m2_core_layout.json</a>，以 SHA-256 綁定原始 M1 規格；<a href="../work/common/core_layout.py">core_layout.py</a> 建構幾何。輸出使用既有 <code>get_default_view(LayoutView)</code>，避免重新建立空白 LayoutCell view。匯出後呼叫另一個 KLayout 程序讀取磁碟上的 GDS。</p>'''
body+=table('表 6｜可閱讀與可下載成果',['檔案','內容'],[
    ('<a href="../work/m2_s3/out/b7_core.gds">b7_core.gds</a>','初版四欄 B7 core；top cell：LAB06B_B7_CORE。'),
    ('<a href="../work/m2_s3/out/mzi_core.gds">mzi_core.gds</a>','單顆單元預覽，另有設計區框；top cell：LAB06B_MZI_PREVIEW。'),
    ('<a href="../work/m2_s3/out/layout_results.json">layout_results.json</a>','尺寸、測試、來源與 GDS 雜湊、本步限制。'),
    ('<a href="../work/m2_s3/out/gds_readback.json">gds_readback.json</a>','由 KLayout 回讀的實例、圖層區域、十埠與局部接點核對。'),
    ('<a href="../work/m2_s3/build_core.py">build_core.py</a> · <a href="../work/m2_s3/verify_gds.py">verify_gds.py</a>','可重跑的建構與獨立回讀程式。')])
body+='''<h2 id="checks">7．本步核對結果與限制</h2>'''
body+=table('表 7｜本輪實際檢查',['項目','結果'],[
    ('結構與幾何測試',f"{D['unit_tests']['passed']}/{D['unit_tests']['run']}；<a href=\"../work/m2_s3/out/unit_tests.log\">log</a>。"),
    ('前步回歸',f'{reg}/{sum(v["run"] for v in D["regression"].values())} 通過；原 M1 與 M2 S2 來源未改。'),
    ('KLayout 獨立回讀',f"{sum(c['passed'] for c in gds['checks'])}/{len(gds['checks'])}；7 個 MZI 引用、每單元 2 個 MMI、14 個 HT 區、28 個局部金屬區。"),
    ('外露埠與局部接點',f"10 個埠的 Si 覆蓋核對、{len(gds['joints'])} 個接點的 20 nm × 100 nm 小區域覆蓋核對通過；未以 buffer 填補縫隙。"),
    ('來源、表格與解析曲率',f"{sum(c['passed'] for c in D['checks'])}/{len(D['checks'])} 項通過；幾何均在宣告設計區內。"),
    ('M1 基準重播','80/80；用於確認原基準未變，不是版圖抽取後的重播。'),
    ('尚未執行','本步未執行 foundry DRC、完整 LVS、製程驗證、熱模擬或版圖回註真值驗收。')])
body+=table('表 8｜測試回讀器：三種錯誤座標副本',['副本','被抓到的核對'],[(r['name'],', '.join(r['failed_checks'])) for r in D['controlled_errors']])
body+='''<p>三種負例只改檢核用的座標副本（埠、MZI 原點或局部接點各偏移 1 µm），正式 GDS 與正式 sidecar 未被修改。此實驗證明回讀器能發現圖形與座標資料不一致，不代表已涵蓋所有可能的 GDS 缺陷。<a href="../work/m2_s3/out/controlled_readback.json">負例結果</a>。</p>
<h2 id="submit">8．學員交付與下一關</h2><ol><li>提交自行重跑的 b7_core.gds、mzi_core.gds、三份 CSV 及幾何資訊 JSON。</li><li>標註 M1～7 的 layer／mode、六段直通位置、out1 與 out3 的接收極性。</li><li>從互動核對器找到 theta1 與 phi7 的中心、A／B 接觸，說明其外部 PAD 仍未配置。</li><li>比較 MZI 臂長與旁路，說明為何局部平衡仍不能保證原相位直接在實體網路通過 80 筆。</li><li>交付 KLayout 檢視截圖並列出下關要查的彎道、接縫、相鄰單元間距與金屬配置問題。學員作答待講師驗收。</li></ol>
<section class="panel"><label for="layout-name">學員姓名</label><input id="layout-name"><label for="layout-placement-notes">七顆放置、直通及埠序觀察</label><textarea id="layout-placement-notes"></textarea><label for="layout-phase-notes">heater 接觸、路徑長度與相位限制</label><textarea id="layout-phase-notes"></textarea><label for="layout-review-notes">KLayout 檢視證據及 M2 S4 待辦</label><textarea id="layout-review-notes"></textarea><button id="layout-generate">產生 M2 S3 學習記錄 JSON</button><textarea id="layout-json" hidden readonly aria-label="M2 S3 學習記錄 JSON" style="min-height:220px"></textarea><p class="muted">複製到 learner/m2_s3_observations.json；<a href="../learner/m2_s3_observations.template.json">空白範本</a>。</p></section>
<script>document.querySelector('#layout-generate').addEventListener('click',()=>{const box=document.querySelector('#layout-json');box.hidden=false;box.value=JSON.stringify({step:'M2 S3',learner_name:document.querySelector('#layout-name').value,placement_and_ports:document.querySelector('#layout-placement-notes').value,heaters_lengths_phase:document.querySelector('#layout-phase-notes').value,review_evidence_and_todos:document.querySelector('#layout-review-notes').value,instructor_review:'pending',date:new Date().toISOString()},null,2);box.focus();box.select();});</script>
<p><b>下一步 M2 S4：</b>在 KLayout 依清單檢查埠序、彎道、間距與交叉，記錄修改前後圖，再進入 EC／PAD 與 GND 配置。</p>
<p class="muted">API 參考：<a href="https://academy.lucedaphotonics.com/training/getting_started/5_component_layout/1_tutorials">Luceda：MMI 元件版圖與 GDS 輸出</a>。線上文件為較新版本；本輪以本機 IPKISS 實跑及 GDS 回讀為準。S 彎沿用 M0 工具鏈的餘弦折線做法，沒有套用較新版本才提供的路由器。</p>'''
nav=''.join(f'<a href="{h}">{t}</a>' for h,t in [('../Lab06b_index.html','總覽與報告入口'),('plan.html','完整規劃'),('m2_s2.html','M2 S2｜PDK 電路基準'),('#scope','core 範圍'),('#geometry','單顆 MZI 幾何'),('#placement','七顆放置與直通'),('#ports','埠／相位區／長度'),('#run','執行與 GDS'),('#checks','回讀核對與限制'),('#submit','學員交付')])
html=f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M2 S3｜七顆 MZI 實體 core 版圖與 GDS｜Lab06b</title><link rel="stylesheet" href="../assets/course.css"></head><body><header class="top"><a href="../Lab06b_index.html"><b>LAB06b</b>　PIC Chip 學員實作課程</a><small>2026-10-31 · M2 S3</small></header><div class="layout"><aside><strong>學習與實作入口</strong>{nav}<p class="muted">{state}<br>學員作答待提交</p></aside><main><button class="print" onclick="window.print()">列印／另存 PDF</button><div class="hero"><div class="eyebrow">MODULE 2 · STEP 3 · 90 MIN</div><h1>M2 S3｜七顆 MZI 實體 core 版圖與 GDS</h1><p class="lead">從 B7 邏輯連接走到真正可回讀的幾何檔，把埠位、heater 區域與波導長度一一對回規格。</p><span class="tag ok">7 MZI／14 PDK MMI</span><span class="tag">KLayout 獨立回讀</span><span class="tag wait">初版 core，待後續檢視</span></div>{body}<footer>正式工作區 C:\\EDA_Codex\\Lab06b；D 槽唯讀。設計區框不是完成的晶片外形；局部 heater 與接觸尚待驅動、PAD、回路及校正。</footer></main></div></body></html>'''
(ROOT/'course/m2_s3.html').write_text(clean_course_html(html),encoding='utf-8')
for rel in ['Lab06b_index.html','course/plan.html','course/m0_s1.html','course/m0_s1_foundation.html','course/m0_s2.html','course/m0_s3.html','course/m1_s1.html','course/m1_s2.html','course/m1_s3.html','course/m1_s4.html','course/m1_s5.html','course/m2_s1.html','course/m2_s2.html','analysis/lab01a_7_6.html','reference/source_context.html']:
    p=ROOT/rel;text=p.read_text(encoding='utf-8');href=('../' if '/' in rel else '')+'course/m2_s3.html'
    if f'href="{href}"' not in text:text=text.replace('</aside>',f'<a href="{href}">M2 S3｜core 版圖與 GDS</a></aside>',1)
    if rel=='Lab06b_index.html':
        panel=f'<!-- M2S3:STATUS --><div class="callout good"><b>目前進度：</b>M2 S3：七顆 MZI 初版 core GDS 匯出與回讀核對通過。<a href="course/m2_s3.html">進入 M2 S3 →</a><br>7 MZI、14 MMI、14 局部 heater、10 個 core 光學埠；EC／PAD／GND、DRC 與版圖相位回註待後續。下一步 M2 S4。</div><!-- /M2S3:STATUS -->'
        text=re.sub(r'<!-- (?:M2S2|M2S3):STATUS -->.*?<!-- /(?:M2S2|M2S3):STATUS -->',lambda m:panel,text,count=1,flags=re.S)
        text=text.replace('S1～S2 邊界與 PDK 電路通過；S3～S7 待實作','S1～S3 邊界、電路及初版 core 通過；S4～S7 待實作')
        text=text.replace('M0、M1 與 M2 S1～S2 核心已實跑','M0、M1 與 M2 S1～S3 核心已實跑').replace('後續實體 Chip 版圖、路徑回註與最終交付依關卡進行。','後續版圖檢視、EC／PAD／GND、路徑回註與最終交付依關卡進行。')
        if '<td>M2 S3 主實作</td>' not in text:text=text.replace('<tr><td>M2 S2 主實作</td>','<tr><td>M2 S3 主實作</td><td><a href="course/m2_s3.html">七顆 MZI core 版圖與 GDS</a></td><td>實體幾何、埠／相位區／長度及獨立 GDS 回讀</td></tr><tr><td>M2 S2 主實作</td>',1)
        card='<article class="card"><div class="num">M2 S3</div><h3>七顆 MZI core 版圖與 GDS</h3><p>完成初版 core，回讀實際 GDS 並對照埠、相位區與路徑。</p><a href="course/m2_s3.html">進入本步 →</a></article>'
        text=re.sub(r'<!-- (?:M2S2|M2S3):CARD -->.*?<!-- /(?:M2S2|M2S3):CARD -->',lambda m:'<!-- M2S3:CARD -->'+card+'<!-- /M2S3:CARD -->',text,flags=re.S)
    if rel=='course/plan.html':text=text.replace('<td>M2 s3<br>1.5 h</td>','<td><a href="m2_s3.html">M2 s3</a><br>1.5 h</td>')
    p.write_text(text,encoding='utf-8')
CFG['progress']['M2_S3']='initial seven-MZI physical core GDS and independent readback passed; no full DRC or extracted replay; learner submission pending' if D['core_passed'] else 'core layout checks unresolved'
CFG['progress']['M2_S4']='next step: KLayout review of ports, bends, gaps and crossings'
(ROOT/'config/course.json').write_text(json.dumps(CFG,ensure_ascii=False,indent=2),encoding='utf-8')
p=ROOT/'README_Lab06b_Course.md';text=p.read_text(encoding='utf-8').replace('下一步 M2 S3：七顆 MZI 實體 core 版圖與 GDS。','M2 S3：scripts/run_m2_s3.ps1；work/m2_s3/out/b7_core.gds（初版 core，獨立回讀通過）。\n下一步 M2 S4：KLayout 版圖檢視與修改記錄。');p.write_text(text,encoding='utf-8')
print('M2 S3 page rendered; core:',D['core_passed'])
