from report_policy import clean_course_html
"""Student-facing CORNERSTONE circuit build, scope audit and 80-case comparison."""
from pathlib import Path
from html import escape
import json,re
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/m2_s2/out'
D=json.loads((OUT/'pdk_results.json').read_text(encoding='utf-8'))
CASES=json.loads((OUT/'comparison.json').read_text(encoding='utf-8'))
MATRICES=json.loads((OUT/'matrices.json').read_text(encoding='utf-8'))
NET=json.loads((OUT/'netlist.json').read_text(encoding='utf-8'))
CFG=json.loads((ROOT/'config/course.json').read_text(encoding='utf-8'))
FIG=ROOT/'course/figures/m2_s2';FIG.mkdir(parents=True,exist_ok=True)

def table(caption,headers,rows):
    return '<div class="scroll"><table><caption>'+caption+'</caption><thead><tr>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def pre(s):return '<pre><code>'+escape(s)+'</code></pre>'
def fmt(v):return f'{v:.3e}'

(FIG/'pdk_mzi.svg').write_text('''<svg xmlns="http://www.w3.org/2000/svg" width="1180" height="390" viewBox="0 0 1180 390" role="img" aria-labelledby="t d"><title id="t">PDK MZI 埠位與相位位置</title><desc id="d">上路 in0 先經 phi 再到 MMI1 in2，MMI1 out2 經 theta 到 MMI2 in2；下路 in1 到 MMI1 in1，再從 out1 到 MMI2 in1。輸出上路 out0 對應 MMI2 out2，下路 out1 對應 out1。光線為邏輯連線，沒有長度。</desc><rect width="1180" height="390" rx="10" fill="#f4f7fc"/><g stroke="#155bd0" stroke-width="4" fill="none"><path d="M80 130H330 M80 260H330 M440 130H790 M440 260H790 M900 130H1110 M900 260H1110"/></g><g fill="white" stroke="#155bd0" stroke-width="2"><rect x="330" y="75" width="110" height="240" rx="8"/><rect x="790" y="75" width="110" height="240" rx="8"/></g><g fill="#fff3d7" stroke="#b78019" stroke-width="2"><rect x="170" y="100" width="105" height="60" rx="8"/><rect x="555" y="100" width="105" height="60" rx="8"/></g><g font-family="Microsoft JhengHei,Arial" fill="#17263b" font-size="19" text-anchor="middle"><text x="385" y="194">PDK MMI1</text><text x="845" y="194">PDK MMI2</text><text x="222" y="138">φ · 理想</text><text x="608" y="138">θ · 理想</text><text x="95" y="105">in0 上</text><text x="95" y="300">in1 下</text><text x="1065" y="105">out0 上</text><text x="1065" y="300">out1 下</text><text x="385" y="112">in2 → out2</text><text x="385" y="286">in1 → out1</text><text x="845" y="112">in2 → out2</text><text x="845" y="286">in1 → out1</text><text x="590" y="40" font-size="23">T = H · P(θ) · H · P(φ)，矩陣從右向左作用</text><text x="590" y="365" font-size="17">7 個 MZI → 14 個 PDK MMI＋14 個理想相位元件；藍線是零長度邏輯連線。</text></g></svg>''',encoding='utf-8')
state='PDK 電路與 80 筆對照通過' if D['core_passed'] else 'PDK 電路有待解決項'
reg=sum(v['passed'] for v in D['regression'].values())
body=f'''<div class="callout {'good' if D['core_passed'] else 'warn'}"><b>本輪實跑：</b>{D['passed']}/{D['total']} 筆真值通過；五個完整複數矩陣的最大差 {fmt(D['max_abs_U_error'])}，最大 |ΔPDK−Δ理想| 為 {fmt(D['max_abs_delta_error'])}。M1 規格、相位與交接 ZIP 雜湊不變，沒有重調相位。</div>
<h2 id="predict">1．先預測，再跑電路</h2><p>建議 60 分鐘：模型範圍 10 分、單顆 MZI 15 分、B7 接線 10 分、80 筆比較 15 分、錯誤實驗與交付 10 分。前置完成 <a href="m2_s1.html">M2 S1 邊界／I/O</a>，沿用 <a href="m1_s5.html">M1 S5 交接包</a>。</p><ol><li>兩個 50:50 MMI 不等於把功率各分一半後直接相加：光場仍保留相位。</li><li>預測同一份相位在 PDK 電路中是否通過；先查 PDK 模型內容，再解釋結果。</li><li>寫下上路的 PDK 埠名，以及 φ／θ 的位置。錯一個位置，即使總功率守恆也可能算錯邏輯。</li></ol>
<h2 id="scope">2．先查實際載入的模型</h2><div class="callout warn"><b>重要發現：</b>本機 CORNERSTONE 的這顆 MMI 繼承 <code>{escape(D['pdk_audit']['compact_model'])}</code>，本輪載入的預設值形成理想 H。不是量測或 FEM／FDTD 擬合的實體 MMI 響應。80/80 證明這個模型範圍下的電路轉接正確，不能用來宣稱實際晶片良率、頻寬或製程容差。</div>'''
body+=table('表 1｜本輪工具與模型範圍',['項目','實際內容'],[
    ('工具',f"CORNERSTONE {D['pdk_audit']['pdk_version']}；IPKISS {D['pdk_audit']['ipkiss_version']}；Caphe 頻域 get_smatrix，validate_netlist=True。"),
    ('設計點','1550 nm（1.55 µm）TE；單波長驗證。'),
    ('PDK 元件',D['pdk_audit']['cell']+'，實例共 14 顆；單一 PCell 可被重用。'),
    ('相位與連線','14 個自訂理想互易相位元件 exp(iψ)；零長度理想接線；6 個直通層段是接線角色，沒有新增傳播元件。'),
    ('沿用 M1','x1～x4 OOK 場振幅 0／1、R=3、core 參考面；out1−out3、threshold=0、epsilon=1e−10。'),
    ('尚未包含','實際波導長度／損耗／相位、EC、heater 電壓與熱串擾、PAD、製程角落、DRC。')])
body+='''<p>工具路徑由 <a href="../EDA_paths.json">EDA_paths.json</a> 讀取。<a href="../work/m2_s2/out/pdk_model_audit.json">模型稽核 JSON</a> 記錄本機來源檔路徑、SHA-256、compact model 名稱與所有實際參數；沒有把其他同名 MMI 模型當成本次使用的模型。</p>'''
body+=pre('H = (1/√2) [[1, i], [i, 1]]\nP(ψ) = diag(exp(iψ), 1)\nT(θ,φ) = H @ P(θ) @ H @ P(φ)')
body+='''<h2 id="mzi">3．先做一顆 MZI：埠名與相位</h2><figure><img src="figures/m2_s2/pdk_mzi.svg" alt="PDK MZI 上下路埠位及 phi 在輸入、theta 在內臂的接線圖"><figcaption>圖 1｜這是邏輯電路圖，沒有代表波導長度或版圖尺寸。PDK in2／out2 在上方；本課程局部 in0／out0 代表上路。</figcaption></figure>'''
body+=table('表 2｜單顆 MZI 的四個外露埠',['課程局部埠','PDK／相位端點','位置'],[
    ('in0','phi:in → phi:out → mmi1:in2','上輸入'),('in1','mmi1:in1','下輸入'),
    ('out0','mmi2:out2','上輸出'),('out1','mmi2:out1','下輸出')])
body+=pre("# 實作位置：work/common/pdk_circuit.py\nlinks = [('phi:out', 'mmi1:in2'),\n         ('mmi1:out2', 'theta:in'),\n         ('theta:out', 'mmi2:in2'),\n         ('mmi1:out1', 'mmi2:in1')]\n# 以 named ports 讀取 S；列是輸出，欄是輸入。\nT = [[S[out_port, in_port][0] for in_port in inputs]\n     for out_port in outputs]")
single=json.loads((OUT/'single_mzi_checks.json').read_text(encoding='utf-8'))
body+=table('表 3｜先驗證四組單顆 MZI',['θ rad','φ rad','max |TCaphe−T理想|'],[(f"{s['theta']:.6f}",f"{s['phi']:.6f}",fmt(s['max_abs_error'])) for s in single])
body+='''<p>保留每顆 MZI 的整體相位 i·exp(iθ/2)。它相對其他直通路徑仍會造成干涉，不能逐顆刪除。φ 位於第一個 MMI 之前；放到輸出端會改變算式。此步 φ、θ 都是 rad，尚未轉成 heater 電壓。</p>
<h2 id="b7">4．把七顆 MZI 接成 B7</h2><p>沿 <a href="m1_s2.html">M1 S2 的四層拓樸</a>，逐模式更新目前的輸出端點，再接到下一顆 MZI。外層有 7 個 MZI 實例、9 條 MZI 之間的連線與 10 個外露埠。內部每顆 MZI 各有 4 條連線。相位向量依通道名稱映射，不能把交接檔的 θ1～7、φ1～7 誤當成逐顆 θφ 交錯排列。</p>'''
body+=table('表 4｜B7 外層連接（源端 → 目的端）',['模式','源端','目的端'],[(r['mode'],r['source'],r['destination']) for r in NET['edges']])
body+='''<p><a href="../work/m2_s2/out/netlist.json">完整邏輯接線 JSON</a> · <a href="../work/common/pdk_circuit.py">電路建構原始碼</a>。in0～4／out0～4 都是 core 埠，沒有新增 EC；接收器與驅動器仍在外部。</p>
<h2 id="run">5．自己重跑 80 筆</h2>'''
body+=pre(r"""Set-Location -LiteralPath 'C:\EDA_Codex\Lab06b'
& .\scripts\run_m2_s2.ps1""")
body+='''<p>Runner 讀取交接包並核對雜湊，從 PDK 的 CircuitModel 取得五組完整 10×10 S，再擷取 5×5 前向 U。每組 U 對 16 組完整四位元輸入計算複數場、五路功率及 Δ。x1 是索引最低位，因此 index=1 的 pattern 是 1000。AND2／OR2／XOR2 仍遍歷 x3、x4 的四種實際入光組合。</p>'''
body+=pre('a = [x1, x2, x3, x4, 3]  # 相干場；未正規化成單位總功率\nb = U @ a\nPk = abs(b[k])**2\nΔ = P1 - P3\nbit = None if abs(Δ) <= 1e-10 else int(Δ > 0)\nsigned_margin = (2*truth - 1)*Δ  # 必須 > epsilon')
body+=table('表 5｜五個函數使用原相位；各 16 筆',['函數','真值通過','最大複數 U 差','最大 |Δ 差|','最小 signed margin','最差 pattern'],[(s['gate'],f"{s['passed']}/16",fmt(s['max_abs_U_error']),fmt(s['max_abs_delta_error']),f"{s['minimum_signed_margin']:.12g}",s['worst_pattern']) for s in D['functions']])
body+='''<figure><img src="figures/m2_s2/comparison.svg" alt="五個函數各十六個輸入的理想與 PDK signed margin，以及功率差殘差"><figcaption>圖 2｜上圖兩種模型的 signed margin 疊合；全部高於 epsilon。下圖為 Δ 的直接相減殘差，量級接近浮點運算誤差；沒有作相位對齊或重新擬合。</figcaption></figure>
<p><a href="../work/m2_s2/out/comparison_80.csv">下載完整 80 筆 CSV</a>（含五路理想／PDK 功率、Δ、bit、margin、場差）· <a href="../work/m2_s2/out/comparison.json">複數場 JSON</a> · <a href="../work/m2_s2/out/matrices.json">五組 U</a> · <a href="../work/m2_s2/out/smatrices.json">完整 S 與埠序</a>。</p>
<h3>逐筆比較：同一份輸入的場、功率與判讀</h3><section class="panel"><label for="pdk-gate">函數</label><select id="pdk-gate">'''+''.join(f'<option>{g}</option>' for g in CASES)+'''</select><label for="pdk-pattern">完整四位元 pattern（x1 在左）</label><select id="pdk-pattern">'''+''.join(f'<option value="{r["pattern"]}">{r["index_lsb_x1"]:02d} · {r["pattern"]}</option>' for r in next(iter(CASES.values())))+'''</select><div id="pdk-live" class="answers" aria-live="polite" style="overflow-wrap:anywhere"></div><div id="pdk-power"></div><details><summary>此函數的完整 PDK 複數 U（上路到下路）</summary><div id="pdk-matrix"></div></details></section>'''
body+='<script>const PDK_CASES='+json.dumps(CASES)+';const PDK_MATRICES='+json.dumps(MATRICES)+';</script>'
body+='''<script>(()=>{const g=document.querySelector('#pdk-gate'),p=document.querySelector('#pdk-pattern');function table(headers,rows,caption){const scroll=document.createElement('div');scroll.className='scroll';const t=document.createElement('table'),cap=document.createElement('caption');cap.textContent=caption;t.append(cap);const h=document.createElement('thead'),hr=document.createElement('tr');for(const v of headers){const x=document.createElement('th');x.textContent=v;hr.append(x);}h.append(hr);t.append(h);const b=document.createElement('tbody');for(const row of rows){const tr=document.createElement('tr');for(const v of row){const td=document.createElement('td');td.textContent=v;tr.append(td);}b.append(tr);}t.append(b);scroll.append(t);return scroll;}function show(){const r=PDK_CASES[g.value].find(x=>x.pattern===p.value),box=document.querySelector('#pdk-live');box.dataset.result=JSON.stringify(r);box.replaceChildren();for(const text of [g.value+' / '+r.pattern+'：truth '+r.expected+'；PDK bit '+r.pdk_bit+'；'+(r.passed?'通過':'未通過'),'Δ 理想 '+r.ideal_delta.toPrecision(12)+'；Δ PDK '+r.pdk_delta.toPrecision(12),'signed margin '+r.signed_margin.toPrecision(12)+'；Δ 殘差 '+r.delta_error.toExponential(3),'輸入總功率 '+r.input_total_power+'；輸出 '+r.pdk_total_power.toPrecision(12)+'（規一化單位）']){const d=document.createElement('div');d.textContent=text;box.append(d);}const z=v=>v[0].toFixed(6)+(v[1]<0?'':' + ')+v[1].toFixed(6)+'i';document.querySelector('#pdk-power').replaceChildren(table(['輸出','理想場','PDK 場','理想功率','PDK 功率'],Array.from({length:5},(_,k)=>['out'+k,z(r.ideal_field[k]),z(r.pdk_field[k]),r['ideal_P'+k].toPrecision(9),r['pdk_P'+k].toPrecision(9)]),'逐路複數場與功率'));document.querySelector('#pdk-matrix').replaceChildren(table(['輸出／輸入','in0','in1','in2','in3','in4'],PDK_MATRICES[g.value].pdk.map((row,k)=>['out'+k,...row.map(z)]),'PDK U：列為輸出，欄為輸入'));}g.addEventListener('change',show);p.addEventListener('change',show);show();})();</script>
<h2 id="checks">6．不只看 bit：接線、能量與錯誤實驗</h2>'''
body+=table('表 6｜自動檢查',['項目','結果'],[
    ('本步結構／輸入測試',f"{D['unit_tests']['passed']}/{D['unit_tests']['run']}；<a href=\"../work/m2_s2/out/unit_tests.log\">log</a>。"),
    ('M0／M1／M2 S1 回歸',f'{reg}/{sum(v["run"] for v in D["regression"].values())} 通過。'),
    ('完整複數／功率／CSV／來源核對',f"{sum(r['passed'] for r in D['checks'])}/{len(D['checks'])}；<a href=\"../work/m2_s2/out/pdk_results.json\">完整結果</a>。"),
    ('10×10 S 的一致性','檢查左右兩側完整 5×5 反射區塊、S=Sᵀ 與 S†S=I，不只看對角反射。這是本輪理想預設模型下的結果。')])
names={'phi_on_wrong_input':'交換 MZI 上下輸入對照','theta_phi_vector_swapped':'θ／φ 向量交換','theta_sign_reversed':'θ 正負號反轉','discard_each_MZI_global_phase':'逐顆刪除整體相位','receiver_polarity_reversed':'接收正負極性反轉'}
body+=table('表 7｜錯誤只存在於副本；正式相位未改',['變體','偵測依據','結果'],[(names[r['name']],('max |U差|='+fmt(r['max_abs_U_error'])) if 'max_abs_U_error' in r else f"{r['failed']} 筆真值錯誤",'已偵測' if r['detected'] else '未偵測') for r in D['controlled_errors']])
body+='''<p>前三種接線／參數變體由 Caphe 實際求解；刪除整體相位使用 NumPy 副本；極性反轉使用 80 筆輸出重判。先找場或矩陣差異，再追到功率與 bit；總功率守恆不保證邏輯正確。<a href="../work/m2_s2/out/controlled_errors.json">錯誤實驗 JSON</a>。</p>
<h2 id="submit">7．學員交付與 M2 S3 交接</h2><ol><li>標註單顆 MZI 的四個 PDK 埠與 θ／φ 位置，解釋矩陣順序。</li><li>自行執行 runner，保存 comparison_80.csv 與 pdk_model_audit.json，指出 XOR2 最小 margin 和最差 pattern。</li><li>各挑一筆 truth=0、truth=1，比較五路場、功率、Δ 與 bit；解釋為何不能把相干功率直接加總。</li><li>挑一個錯誤變體，描述錯誤如何從連接影響 U，再影響判讀。</li><li>說明這版 PDK 預設 MMI 模型的限制，列出版圖長度、路徑相位與 heater 校正待辦。學員作答仍待講師驗收。</li></ol>
<section class="panel"><label for="pdk-name">學員姓名</label><input id="pdk-name"><label for="pdk-mapping-notes">埠位、θ／φ 位置與電路建構</label><textarea id="pdk-mapping-notes"></textarea><label for="pdk-comparison-notes">80 筆結果與逐筆場／功率觀察</label><textarea id="pdk-comparison-notes"></textarea><label for="pdk-scope-notes">錯誤實驗、模型限制及下一步待辦</label><textarea id="pdk-scope-notes"></textarea><button id="pdk-generate">產生 M2 S2 學習記錄 JSON</button><textarea id="pdk-json" hidden readonly aria-label="M2 S2 學習記錄 JSON" style="min-height:220px"></textarea><p class="muted">複製到 learner/m2_s2_observations.json；<a href="../learner/m2_s2_observations.template.json">空白範本</a>。</p></section>
<script>document.querySelector('#pdk-generate').addEventListener('click',()=>{const box=document.querySelector('#pdk-json');box.hidden=false;box.value=JSON.stringify({step:'M2 S2',learner_name:document.querySelector('#pdk-name').value,port_and_phase_mapping:document.querySelector('#pdk-mapping-notes').value,comparison_observations:document.querySelector('#pdk-comparison-notes').value,limitations_and_errors:document.querySelector('#pdk-scope-notes').value,instructor_review:'pending',date:new Date().toISOString()},null,2);box.focus();box.select();});</script>
<p><b>下一步 M2 S3：</b>建立七顆 MZI 的實體 core 版圖與 GDS。保留這份電路基準，後續抽取實際長度時重新計算路徑相位；14 個相位元件在本步仍是理想模型，並未完成 heater 版圖或電壓校正。</p>
<p class="muted">API 參考：<a href="https://academy.lucedaphotonics.com/tutorials/circuitmodels/">Luceda：Creating a First Circuit Simulation</a>。線上文件為較新版本；本輪以安裝的 IPKISS 2026.03.3 實跑 API 與本機模型稽核為準。</p>'''
nav=''.join(f'<a href="{h}">{t}</a>' for h,t in [('../Lab06b_index.html','總覽與報告入口'),('plan.html','完整規劃'),('m2_s1.html','M2 S1｜PIC 邊界／I/O'),('#scope','模型範圍稽核'),('#mzi','單顆 MZI 與埠位'),('#b7','B7 接線'),('#run','80 筆執行／比較'),('#checks','檢查與錯誤變體'),('#submit','學員交付')])
html=f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M2 S2｜CORNERSTONE PDK 電路與 80 筆比較｜Lab06b</title><link rel="stylesheet" href="../assets/course.css"></head><body><header class="top"><a href="../Lab06b_index.html"><b>LAB06b</b>　PIC Chip 學員實作課程</a><small>2026-10-31 · M2 S2</small></header><div class="layout"><aside><strong>學習與實作入口</strong>{nav}<p class="muted">{state}<br>學員作答待提交</p></aside><main><button class="print" onclick="window.print()">列印／另存 PDF</button><div class="hero"><div class="eyebrow">MODULE 2 · STEP 2 · 60 MIN</div><h1>M2 S2｜CORNERSTONE PDK 電路與 80 筆比較</h1><p class="lead">把 M1 的複數運算轉接到真正載入的 PDK 電路模型，逐筆核對場、功率與差分判讀。</p><span class="tag ok">Caphe {D['passed']}/80</span><span class="tag">原相位未改</span><span class="tag wait">PDK 預設理想 MMI</span></div>{body}<footer>正式工作區 C:\\EDA_Codex\\Lab06b；D 槽唯讀。本步是單波長電路模型驗證，實體 PIC 尚待後續版圖、傳播與製程檢查。</footer></main></div></body></html>'''
(ROOT/'course/m2_s2.html').write_text(clean_course_html(html),encoding='utf-8')
for rel in ['Lab06b_index.html','course/plan.html','course/m0_s1.html','course/m0_s1_foundation.html','course/m0_s2.html','course/m0_s3.html','course/m1_s1.html','course/m1_s2.html','course/m1_s3.html','course/m1_s4.html','course/m1_s5.html','course/m2_s1.html','analysis/lab01a_7_6.html','reference/source_context.html']:
    p=ROOT/rel;text=p.read_text(encoding='utf-8');href=('../' if '/' in rel else '')+'course/m2_s2.html'
    if f'href="{href}"' not in text:text=text.replace('</aside>',f'<a href="{href}">M2 S2｜PDK 電路與 80 筆</a></aside>',1)
    if rel=='Lab06b_index.html':
        panel=f'<!-- M2S2:STATUS --><div class="callout good"><b>目前進度：</b>M0 與 M1 核心已建立；M2 S1 邊界核對、M2 S2 PDK 電路 {D["passed"]}/80 通過。<a href="course/m2_s2.html">進入 M2 S2 →</a><br>本機 MMI 是預設理想模型；實體長度、EC、heater／PAD 與製程驗證仍待後續。下一步 M2 S3。</div><!-- /M2S2:STATUS -->'
        text=re.sub(r'<!-- (?:M2S1|M2S2):STATUS -->.*?<!-- /(?:M2S1|M2S2):STATUS -->',lambda m:panel,text,count=1,flags=re.S)
        text=text.replace('S1 邊界／I/O 核對通過；S2～S7 待實作','S1～S2 邊界與 PDK 電路通過；S3～S7 待實作')
        text=text.replace('M0 三步與 M1 五步核心已實算，學員作答各自驗收；後續 B7 電路、Chip 版圖與最終交付依關卡進行。','M0、M1 與 M2 S1～S2 核心已實跑，學員作答各自驗收；後續實體 Chip 版圖、路徑回註與最終交付依關卡進行。')
        if '<td>M2 S2 主實作</td>' not in text:text=text.replace('<tr><td>M2 S1 主實作</td>','<tr><td>M2 S2 主實作</td><td><a href="course/m2_s2.html">CORNERSTONE PDK 電路與 80 筆比較</a></td><td>PDK 模型稽核、Caphe 複數矩陣與全真值比較</td></tr><tr><td>M2 S1 主實作</td>',1)
        card='<article class="card"><div class="num">M2 S2</div><h3>PDK 電路與 80 筆比較</h3><p>固定原相位，實跑 Caphe，核對複數場、功率與真值。</p><a href="course/m2_s2.html">進入本步 →</a></article>'
        text=re.sub(r'<!-- (?:M2S1|M2S2):CARD -->.*?<!-- /(?:M2S1|M2S2):CARD -->',lambda m:'<!-- M2S2:CARD -->'+card+'<!-- /M2S2:CARD -->',text,flags=re.S)
    if rel=='course/plan.html':text=text.replace('<td>M2 s2<br>1 h</td>','<td><a href="m2_s2.html">M2 s2</a><br>1 h</td>')
    p.write_text(text,encoding='utf-8')
CFG['progress']['M2_S2']='Caphe PDK circuit and all 80 comparisons passed; installed default ideal MMI; learner submission pending' if D['core_passed'] else 'PDK circuit checks unresolved'
CFG['progress']['M2_S3']='next step: seven-MZI physical core layout and GDS'
(ROOT/'config/course.json').write_text(json.dumps(CFG,ensure_ascii=False,indent=2),encoding='utf-8')
p=ROOT/'README_Lab06b_Course.md';text=p.read_text(encoding='utf-8').replace('下一步 M2 S2：CORNERSTONE PDK 電路與 80 筆比較。','M2 S2：scripts/run_m2_s2.ps1；work/m2_s2/out/comparison_80.csv（80/80，PDK 預設理想 MMI）。\n下一步 M2 S3：七顆 MZI 實體 core 版圖與 GDS。');p.write_text(text,encoding='utf-8')
print('M2 S2 page rendered; core:',D['core_passed'])
