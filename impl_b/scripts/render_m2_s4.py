from report_policy import clean_course_html
"""KLayout review lesson: scoped evidence, a real revision and pending gates."""
from pathlib import Path
from html import escape
import json,re
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/m2_s4/out'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
D=load(OUT/'review_results.json');CFG=load(ROOT/'config/course.json')
def table(caption,headers,rows):
    return '<div class="scroll"><table><caption>'+caption+'</caption><thead><tr>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def pre(s):return '<pre><code>'+escape(s)+'</code></pre>'
before,after=D['versions']['before'],D['versions']['after'];reg=sum(v['passed'] for v in D['regression'].values())
state='檢視與修改記錄核對通過，採用裕量改善版 core' if D['core_passed'] else '檢視有未解決項'
body=f'''<div class="callout {'good' if D['core_passed'] else 'warn'}"><b>本輪結論：</b>{state}。S 彎水平長 20 → 24 µm，連續解析最小曲率半徑 {before['radius_um']:.6f} → {after['radius_um']:.6f} µm；水平光學跨度 2076 → 2140 µm。原 S3 GDS 與 M1 規格／相位未改。<br>兩版的六項局部線寬／間距篩查皆零警示；保留 24 張 KLayout 原生視圖、修改前後 GDS 與座標／長度變更表。</div>
<h2 id="predict">1．本步目標：把「看起來可以」變成可追溯的檢視記錄</h2><p>建議 60 分鐘：載入 GDS 與圖層 10 分、逐項檢視 20 分、比較修改 15 分、確認交接與記錄 15 分。前置：<a href="m2_s3.html">M2 S3 初版 core 與 GDS</a>。</p><ol><li>核對埠序、四欄七顆實例與六段直通，追蹤 out1 正／out3 負的接收角色。</li><li>放大 MMI 接縫與 S 彎，分層看 Si、HT、局部金屬，記錄數值與來源。</li><li>評估幾何裕量與面積代價，修改 Python 參數後重出 GDS，保存修改前後。</li><li>將仍未完成的 EC、外部 PAD／共地、完整 DRC／LVS 與相位回註明確留給後關。</li></ol>
<h2 id="decision">2．為何修改？這是裕量改善，並非把合格版說成違規</h2><div class="callout warn"><b>原版已符合既有規劃值：</b>S3 的連續解析 Rmin 約 5.23 µm，高於 5 µm。本課程額外採 7.5 µm 作幾何裕量目標，因此延長 S 彎。7.5 µm 是本步的教學設計選擇，沒有宣稱它是新的 foundry 規則，也未驗證彎曲損耗或製程良率改善。</div>
<figure><img src="figures/m2_s4/margin_tradeoff.svg" alt="修改前後解析最小曲率半徑與 core 水平跨度的比較"><figcaption>圖 1｜幾何裕量增加的代價是 core 光學端點水平跨度增加 64 µm。既有 2200 × 220 µm 設計區仍可容納新版，外框沒有加大。</figcaption></figure>'''
labels={'S_bend_horizontal':'S 彎水平長','continuous_min_radius':'連續解析最小曲率半徑','column_length':'單欄長度','core_optical_span_x':'core 光學水平跨度','upper_singlemode_waveguide_per_MZI':'每顆 MZI 上臂單模波導總長','inter_MMI_upper':'MMI 間上臂長','design_frame_x':'設計區寬'}
body+=table('表 1｜幾何修改記錄（µm）',['項目','修改前','修改後','差值'],[(labels[r['metric']],f"{r['before']:.6f}",f"{r['after']:.6f}",f"{r['delta']:+.6f}") for r in D['metrics']])
body+='''<figure><img src="figures/m2_s4/bend_comparison.svg" alt="由兩版實際 GDS 多邊形繪製的同尺度 S 彎修改前後圖"><figcaption>圖 2｜以 KLayout 回讀的 Si 多邊形作同尺度比較；虛線是產生版圖的中心線。解析曲率針對連續餘弦設計，不把 1 nm 格點後的三點曲率當作可靠量測。</figcaption></figure>
<p>只改 <a href="../config/m2_review_layout.json">新版幾何設定</a> 的 S 彎長；41 點取樣、30 µm 軌道間距、MMI 標準元件、heater 尺寸與十四個相位通道名稱維持。S3 原設定與原結果均保留。<a href="../work/m2_s4/out/change_metrics.csv">完整修改指標 CSV</a>。</p>
<h2 id="klayout">3．用 KLayout 分層、放大與比較</h2><p>本輪以 KLayout 的 LayoutView 載入磁碟上的實際 GDS，呼叫 zoom_box 與 save_image 匯出原生視圖；以下不是手畫示意圖。顏色：Si／GDS 3 藍色、HT／39 橘色、局部金屬／41 綠色。視圖隱藏 99 設計區與 100 文字層，以免填色覆蓋光路；原 GDS 仍保留這兩層。</p>
<figure><img src="figures/m2_s4/after_overview_combined.png" alt="KLayout 原生視圖顯示修改後四欄 B7 core 的 Si heater 與金屬接觸"><figcaption>圖 3｜修改後 core 原生視圖；完整幾何、單位與埠位以 GDS／sidecar 為準。版圖檢視仍需同時對照 M1 拓樸。</figcaption></figure>
<h3>原生視圖檢查器：同一個視窗範圍比較兩版</h3><section class="panel"><label for="review-version">版次</label><select id="review-version"><option value="before">修改前：S3 20 µm S 彎</option><option value="after" selected>修改後：24 µm S 彎</option></select><label for="review-scene">檢視位置</label><select id="review-scene"><option value="overview">整個 core</option><option value="bend">第一個輸入 S 彎</option><option value="mmi">第一顆 MMI 與接縫</option><option value="heater">φ heater 與局部落墊</option></select><label for="review-mode">可見圖層</label><select id="review-mode"><option value="combined">Si＋HT＋金屬</option><option value="optical">只有 Si</option><option value="thermal">只有 HT＋金屬</option></select><figure style="margin:16px 0"><img id="review-image" src="figures/m2_s4/after_overview_combined.png" alt="KLayout 原生檢視區域"><figcaption id="review-caption"></figcaption></figure><div id="review-live" class="answers" aria-live="polite" style="overflow-wrap:anywhere"></div><p class="muted">MMI 區域只有 Si；切到 HT＋金屬時空白是正確結果。顯示圖層空白不代表載入失敗，也不代表該區域沒有其他層。</p></section>'''
body+='<script>const REVIEW_DATA='+json.dumps(D)+';</script>'
body+='''<script>(()=>{const ver=document.querySelector('#review-version'),scene=document.querySelector('#review-scene'),mode=document.querySelector('#review-mode');function show(){const r=REVIEW_DATA.native_images.find(x=>x.version===ver.value&&x.scene===scene.value&&x.mode===mode.value),v=REVIEW_DATA.versions[ver.value],image=document.querySelector('#review-image');image.src='figures/m2_s4/'+r.file;image.alt='KLayout '+ver.value+' '+scene.value+' '+mode.value;document.querySelector('#review-caption').textContent='原生 LayoutView 匯出；請求視窗 [xmin,ymin,xmax,ymax] = ['+r.requested_box_um.join(', ')+'] µm。匯出視口可能依像素長寬比補白。';const result={version:r.version,scene:r.scene,mode:r.mode,file:r.file,layers:r.layers,requested_box_um:r.requested_box_um,radius_um:v.radius_um,optical_span_um:v.optical_span_um,layout_truth_replay:'pending'};const box=document.querySelector('#review-live');box.dataset.result=JSON.stringify(result);box.replaceChildren();for(const text of ['可見層：'+r.layers.join(', ')+'；視窗位置見圖說','連續解析 Rmin '+v.radius_um.toFixed(6)+' µm；core 光學跨度 '+v.optical_span_um.join(' × ')+' µm','本版六項線寬／間距篩查警示：'+v.scoped_rules.reduce((s,x)=>s+x.violations,0),'路徑取樣未覆蓋數：'+v.route_coverage.uncovered+'；完整 LVS／DRC／相位回註待後續']){const el=document.createElement('div');el.textContent=text;box.append(el);}}for(const c of [ver,scene,mode])c.addEventListener('change',show);show();})();</script>
<h3>學員在 KLayout 需要親自做的操作</h3><ol><li>開啟 out/after/b7_core.gds，選 LAB06B_B7_CORE，再展開至葉節點；另開 before 版作比較。</li><li>載入同資料夾的 review_layers.lyp，先只顯示 GDS 3，核對 MMI in2／out2 為上路，以及十個端點的上下順序。</li><li>放大第一個 S 彎與 MMI 接縫；以相同視窗與倍率比較兩版，切換 HT／金屬後確認局部接觸的位置。</li><li>顯示 99 設計區與 100 文字層作位置核對，避免將框當成 die／EC 端面。保存自己的截圖與量測記錄。</li></ol>
<h2 id="checklist">4．逐項檢視記錄：通過與待辦分開</h2>'''
status={'passed':'本步通過','improved':'裕量已改善','passed_with_scope':'限定範圍通過','pending_M2_S5':'待 M2 S5','pending_M2_S6':'待 M2 S6','pending_M2_S7':'待 M2 S7'}
body+=table('表 2｜十項檢視記錄',['ID','項目','狀態','證據與範圍'],[(r['id'],r['topic'],status[r['status']],r['evidence']) for r in D['review_checklist']])
body+=table('表 3｜KLayout 局部規則篩查；兩版皆使用同一門檻',['圖層','項目','門檻 µm','修改前警示','修改後警示'],[(r['layer'],'線寬' if r['kind']=='width' else '間距',r['limit_um'],r['violations'],q['violations']) for r,q in zip(before['scoped_rules'],after['scoped_rules'])])
body+=f'''<p>局部 HT 及金屬接觸之間的距離以 KLayout isolated_check 做 1 nm 二分界定；修改後 HT 最小間距落在 {after['gap_bounds']['HT']['lower_bound_um']:.3f}～{after['gap_bounds']['HT']['upper_bound_um']:.3f} µm，局部金屬為 {after['gap_bounds']['local_metal']['lower_bound_um']:.3f}～{after['gap_bounds']['local_metal']['upper_bound_um']:.3f} µm。這些是不同連通區之間的幾何間距，不是熱串擾或電氣隔離性能。</p>
<p>另核對兩版各 81 個接點小區域，以及各 {after['route_coverage']['samples']} 個路徑取樣。中心線頂點與每一段中點使用 2 nm 方框；物理端面處先沿路徑往內 10 nm，避免方框故意跨出端面。中心線兩兩交集的分析來自產生幾何時的 sidecar，沒有冒充完整 GDS 拓樸抽取。</p>
<div class="callout warn"><b>尚不能據此宣稱：</b>完整 foundry DRC／LVS 通過、EC／外部 PAD／GND 已接完、heater 已校正、光學彎曲損耗已量測，或新版實體光路已通過 80 筆。這些仍待後續關卡驗證。</div>
<h2 id="faults">5．用真正的錯誤 GDS 測試篩查器</h2>'''
fault_labels={'narrow_Si':'插入 0.2 µm 寬 Si 窄線','close_metal':'新增與既有落墊距離 2 µm 的金屬','gapped_input':'在 in0 引線中間切除 2 µm Si'}
body+=table('表 4｜隔離的錯誤 GDS，正式交付未被改寫',['錯誤','預期偵測','結果'],[(fault_labels[r['name']],r['expected'],'已偵測' if r['detected'] else '未偵測') for r in D['controlled_faults']])
body+='''<p>每個負例先寫成獨立 GDS，再由 KLayout 回讀篩查；負例位於本步的 work/controlled_gds，未列入採用版 GDS。窄線測試檢查 layer3_width，過近接觸檢查 layer41_space，斷口檢查路徑取樣。它們不涵蓋所有可能的錯誤。</p>
<h2 id="handoff">6．修改後哪些交接資料必須更新？</h2>'''
body+=f'''<p>五個輸出埠向右移 64 µm，輸入埠不動；{D['changed_phase_centers']}／14 個 heater 中心的 x 座標改變。十四個通道名稱及正／負接收角色保留，但後續 EC／PAD 扇出必須讀新版座標。所有單模波導的長度變化都有記錄；相位程式沒有因本步幾何修改而重新優化。</p>'''
body+=table('表 5｜可下載證據與下一步採用版',['檔案','用途'],[
    ('<a href="../work/m2_s4/out/before/b7_core.gds">修改前 B7 GDS</a> · <a href="../work/m2_s4/out/after/b7_core.gds">修改後 B7 GDS</a>','前者與 S3 原 GDS 位元一致；後者作為後續 core 基礎。'),
    ('<a href="../work/m2_s4/out/after/mzi_core.gds">修改後單顆 MZI GDS</a> · <a href="../work/m2_s4/out/after/review_layers.lyp">KLayout 圖層設定</a>','支援親自檢視、分層與量測。'),
    ('<a href="../work/m2_s4/out/after/layout_info.json">新版完整幾何 JSON</a> · <a href="../config/m2_current_core.json">目前採用版索引</a>','索引記錄路徑、設定與 GDS／sidecar SHA-256；M2 S5 應讀取此索引。'),
    ('<a href="../work/m2_s4/out/port_changes.csv">埠位變更 CSV</a> · <a href="../work/m2_s4/out/phase_region_changes.csv">相位區變更 CSV</a>','更新 EC 與局部接觸座標，外部 PAD 保持 pending。'),
    ('<a href="../work/m2_s4/out/length_changes.csv">58 段長度變更 CSV</a>','供後續傳播與相位回註；不把 MMI x 跨度當作單模傳播長。'),
    ('<a href="../work/m2_s4/out/review_checklist.csv">十項檢視 CSV</a> · <a href="../work/m2_s4/out/review_results.json">本輪完整結果</a>','包括局部規則、原生視圖索引、負例、來源雜湊與限制。')])
body+='''<h2 id="run">7．完整重跑方式與檢核</h2>'''
body+=pre(r"""Set-Location -LiteralPath 'C:\EDA_Codex\Lab06b'
& .\scripts\run_m2_s4.ps1""")
body+=f'''<p>Runner 保存 S3 基準副本、建立修改版、呼叫 KLayout 回讀與原生視圖匯出，再執行中心線分析、輸出變更表及重建教材。{reg}／{sum(v['run'] for v in D['regression'].values())} 項既有回歸通過；其中 M2 S3 的 12 項幾何測試在新版參數下重跑。M1 原規格、相位與 ZIP 雜湊未變，基準仍重播 80/80；這不是新版版圖的真值驗收。</p>'''
body+='''
<p><a href="../work/m2_s4/run_review.py">建構與 KLayout 呼叫</a> · <a href="../work/m2_s4/klayout_review.py">原生視圖與局部篩查</a> · <a href="../work/m2_s4/analyze_paths.py">中心線交集分析</a> · <a href="../work/m2_s4/summarize_review.py">決策與變更表</a>。</p>
<h2 id="submit">8．學員交付與下一關</h2><ol><li>以 KLayout 親自開啟兩版 GDS，至少保存整體、S 彎、MMI 接縫與 heater 分層四種截圖。</li><li>逐項完成十項檢視記錄，指出通過的檢查依據，以及仍待 EC／PAD／GND、完整驗證及相位回註的項目。</li><li>解釋 5 µm 既有規劃值與 7.5 µm 課程額外裕量目標的差別，列出增加跨度的代價。</li><li>說明五個輸出埠和 heater 座標變動如何影響 M2 S5；提交修改前後 GDS、設定檔與變更 CSV。</li><li>附上自己的量測、判斷與未解決問題；本輪自動檢查不取代學員操作與講師驗收。</li></ol>
<section class="panel"><label for="review-name">學員姓名</label><input id="review-name"><label for="review-evidence">KLayout 檢視、量測與截圖檔名</label><textarea id="review-evidence"></textarea><label for="review-reason">修改理由、裕量目標及面積代價</label><textarea id="review-reason"></textarea><label for="review-handoff">新版座標交接與尚未完成項目</label><textarea id="review-handoff"></textarea><button id="review-generate">產生 M2 S4 學習記錄 JSON</button><textarea id="review-json" hidden readonly aria-label="M2 S4 學習記錄 JSON" style="min-height:220px"></textarea><p class="muted">複製到 learner/m2_s4_observations.json；<a href="../learner/m2_s4_observations.template.json">空白範本</a>。</p></section>
<script>document.querySelector('#review-generate').addEventListener('click',()=>{const box=document.querySelector('#review-json');box.hidden=false;box.value=JSON.stringify({step:'M2 S4',learner_name:document.querySelector('#review-name').value,klayout_evidence:document.querySelector('#review-evidence').value,revision_reason_and_tradeoff:document.querySelector('#review-reason').value,handoff_and_pending:document.querySelector('#review-handoff').value,instructor_review:'pending',date:new Date().toISOString()},null,2);box.focus();box.select();});</script>
<p><b>下一步 M2 S5：</b>從目前採用版索引載入 reviewed core，配置 EC 光學 I/O、heater PAD 與 GND，建立 PAD↔heater↔θ／φ 對照表。</p>
<p class="muted">API 參考：<a href="https://www.klayout.org/downloads/master/doc-qt5/code/class_LayoutView.html">KLayout LayoutView</a>、<a href="https://www.klayout.org/downloads/master/doc-qt5/code/class_Region.html">KLayout Region</a>。線上文件可能較新；本輪以安裝的 KLayout 0.30.12 實跑為準。</p>'''
nav=''.join(f'<a href="{h}">{t}</a>' for h,t in [('../Lab06b_index.html','總覽與報告入口'),('plan.html','完整規劃'),('m2_s3.html','M2 S3｜初版 core'),('#decision','修改理由與代價'),('#klayout','KLayout 原生分層檢視'),('#checklist','十項檢視記錄'),('#faults','錯誤 GDS 實驗'),('#handoff','採用版與交接'),('#run','重跑與檢核'),('#submit','學員交付')])
html=f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M2 S4｜KLayout 版圖檢視與修改記錄｜Lab06b</title><link rel="stylesheet" href="../assets/course.css"></head><body><header class="top"><a href="../Lab06b_index.html"><b>LAB06b</b>　PIC Chip 學員實作課程</a><small>2026-10-31 · M2 S4</small></header><div class="layout"><aside><strong>學習與實作入口</strong>{nav}<p class="muted">{state}<br>學員作答待提交</p></aside><main><button class="print" onclick="window.print()">列印／另存 PDF</button><div class="hero"><div class="eyebrow">MODULE 2 · STEP 4 · 60 MIN</div><h1>M2 S4｜KLayout 版圖檢視與修改記錄</h1><p class="lead">逐項看證據、增加彎道設計裕量，並保留可追溯的修改前後 GDS 與交接資料。</p><span class="tag ok">KLayout 原生視圖 24 張</span><span class="tag">修改前後保留</span><span class="tag wait">完整驗證仍待後關</span></div>{body}<footer>正式工作區 C:\\EDA_Codex\\Lab06b；D 槽唯讀。S3 原版保留，本步採用新版索引；額外曲率裕量目標不是新的 foundry 規則。</footer></main></div></body></html>'''
(ROOT/'course/m2_s4.html').write_text(clean_course_html(html),encoding='utf-8')
for rel in ['Lab06b_index.html','course/plan.html','course/m0_s1.html','course/m0_s1_foundation.html','course/m0_s2.html','course/m0_s3.html','course/m1_s1.html','course/m1_s2.html','course/m1_s3.html','course/m1_s4.html','course/m1_s5.html','course/m2_s1.html','course/m2_s2.html','course/m2_s3.html','analysis/lab01a_7_6.html','reference/source_context.html']:
    p=ROOT/rel;text=p.read_text(encoding='utf-8');href=('../' if '/' in rel else '')+'course/m2_s4.html'
    if f'href="{href}"' not in text:text=text.replace('</aside>',f'<a href="{href}">M2 S4｜KLayout 檢視與修改</a></aside>',1)
    if rel=='Lab06b_index.html':
        panel='<!-- M2S4:STATUS --><div class="callout good"><b>目前進度：</b>M2 S4 KLayout 檢視與修改記錄核對通過；保留前後 GDS，採用 S 彎 24 µm 的裕量改善版。<a href="course/m2_s4.html">進入 M2 S4 →</a><br>EC／外部 PAD／GND、完整 DRC／LVS 及相位回註待後續。下一步 M2 S5。</div><!-- /M2S4:STATUS -->'
        text=re.sub(r'<!-- (?:M2S3|M2S4):STATUS -->.*?<!-- /(?:M2S3|M2S4):STATUS -->',lambda m:panel,text,count=1,flags=re.S)
        text=text.replace('S1～S3 邊界、電路及初版 core 通過；S4～S7 待實作','S1～S4 邊界、電路、core 與檢視通過；S5～S7 待實作')
        text=text.replace('M0、M1 與 M2 S1～S3 核心已實跑','M0、M1 與 M2 S1～S4 核心已實跑').replace('後續版圖檢視、EC／PAD／GND、路徑回註與最終交付依關卡進行。','後續 EC／PAD／GND、完整驗證、路徑回註與最終交付依關卡進行。')
        if '<td>M2 S4 主實作</td>' not in text:text=text.replace('<tr><td>M2 S3 主實作</td>','<tr><td>M2 S4 主實作</td><td><a href="course/m2_s4.html">KLayout 檢視與修改記錄</a></td><td>分層檢視、彎道裕量改善、前後 GDS 與座標變更</td></tr><tr><td>M2 S3 主實作</td>',1)
        card='<article class="card"><div class="num">M2 S4</div><h3>KLayout 檢視與修改記錄</h3><p>對照原生視圖與量測，增加彎道裕量並保存修改前後。</p><a href="course/m2_s4.html">進入本步 →</a></article>'
        text=re.sub(r'<!-- (?:M2S3|M2S4):CARD -->.*?<!-- /(?:M2S3|M2S4):CARD -->',lambda m:'<!-- M2S4:CARD -->'+card+'<!-- /M2S4:CARD -->',text,flags=re.S)
    if rel=='course/plan.html':text=text.replace('<td>M2 s4<br>1 h</td>','<td><a href="m2_s4.html">M2 s4</a><br>1 h</td>')
    p.write_text(text,encoding='utf-8')
CFG['progress']['M2_S4']='scoped KLayout review and margin-improved revision accepted; before/after retained; full DRC/LVS pending; learner submission pending' if D['core_passed'] else 'review unresolved'
CFG['progress']['M2_S5']='next step: EC optical I/O, heater PAD and GND mapping'
(ROOT/'config/course.json').write_text(json.dumps(CFG,ensure_ascii=False,indent=2),encoding='utf-8')
p=ROOT/'README_Lab06b_Course.md';text=p.read_text(encoding='utf-8').replace('下一步 M2 S4：KLayout 版圖檢視與修改記錄。','M2 S4：scripts/run_m2_s4.ps1；採用版見 config/m2_current_core.json；修改前後見 work/m2_s4/out/。\n下一步 M2 S5：EC 光學 I/O、heater PAD 與 GND。');p.write_text(text,encoding='utf-8')
print('M2 S4 page rendered; core:',D['core_passed'])
