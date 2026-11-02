from report_policy import clean_course_html
"""Generate M0 S3 and integrate its evidence into the course report."""
from pathlib import Path
from html import escape
import json,re

ROOT=Path(__file__).resolve().parents[1]
DATA=json.loads((ROOT/'work/m0_s3/out/model_results.json').read_text(encoding='utf-8'))
TESTS=DATA['unit_tests'];COMPAT=DATA['b7_compatibility'];EXAMPLE=DATA['trace_example']
FIG=ROOT/'course/figures/m0_s3';FIG.mkdir(parents=True,exist_ok=True)


def table(title,headers,rows):
    return '<div class="scroll"><table><caption>'+title+'</caption><thead><tr>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(c)+'</td>' for c in r)+'</tr>' for r in rows)+'</tbody></table></div>'


def pre(text):return '<pre><code>'+escape(text)+'</code></pre>'


def complex_text(pair):
    real,imag=pair
    if abs(real)<5e-7:real=0.
    if abs(imag)<5e-7:imag=0.
    return f'{real:.6f}{imag:+.6f}i'


diagram='''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="300" viewBox="0 0 1000 300" role="img" aria-labelledby="title desc"><title id="title">MZI 共用模型：上埠在前，phi 在輸入，theta 在兩耦合器之間</title><desc id="desc">光沿左至右經上方輸入相位 phi、耦合器 C1、上方內臂相位 theta、耦合器 C2，再得到上方 out0 及下方 out1。</desc><defs><marker id="arrow" markerWidth="8" markerHeight="7" refX="7" refY="3.5" orient="auto"><path d="M0 0L7 3.5L0 7" fill="#155bd0"/></marker></defs><rect width="1000" height="300" fill="#f4f7fc" rx="10"/><g fill="none" stroke="#155bd0" stroke-width="4"><path d="M95 85H335 M95 175H335 M410 85H695 M410 175H695 M770 85H895 M770 175H895" marker-end="url(#arrow)"/></g><g fill="#dce8fb" stroke="#155bd0" stroke-width="2"><rect x="340" y="48" width="70" height="164" rx="7"/><rect x="700" y="48" width="70" height="164" rx="7"/></g><rect x="165" y="64" width="115" height="42" fill="#aa5a13" rx="5"/><rect x="505" y="64" width="115" height="42" fill="#173f79" rx="5"/><g font-family="Microsoft JhengHei,Arial" font-size="18" fill="#17263b"><text x="18" y="60">in0 上</text><text x="18" y="207">in1 下</text><text x="900" y="60">out0 上</text><text x="900" y="207">out1 下</text><text x="360" y="135">C₁</text><text x="720" y="135">C₂</text><text x="225" y="255">Eout = a C₂ Pθ C₁ Pφ Ein（最右邊先作用）</text></g><g font-family="Arial" fill="white" font-size="18"><text x="181" y="91">φ (input)</text><text x="513" y="91">θ (internal)</text></g></svg>'''
(FIG/'mzi_convention.svg').write_text(diagram,encoding='utf-8')

status='核心模型與測試通過' if DATA['core_passed'] else '模型檢查有未通過項'
body=f'''<div class="callout good"><b>本步問題：</b>能否用一份共用的複數傳輸矩陣，描述同一顆 MZI，並讓測試驗證埠序、相位、功率與串接都一致？<br><b>本輪結果：</b>{TESTS['passed']}/{TESTS['run']} 個測試方法通過；{sum(r['detected'] for r in DATA['controlled_mutations'])}/5 種受控錯誤被抓到；舊相位設定相容性回放 {COMPAT['passed']}/{COMPAT['total']}。學員作答另行提交。</div>
<h2 id="predict">1．先預測，再看程式</h2><p>建議 60 分鐘：讀圖與預測 10 分、共用模型 10 分、執行測試 10 分、修改範例 10 分、分析錯誤 10 分、交接記錄 10 分。</p><ol><li>只打上埠、θ=0，光應從上埠還是下埠離開？</li><li>只打一路時，φ 改變會不會改變兩路輸出功率？若兩路同時打光呢？</li><li>每一顆元件都通過功率守恆，是否代表相位與埠序一定正確？</li><li>兩個矩陣依序作用時，為何後遇到的元件乘在左邊？</li></ol>
<h2 id="convention">2．先固定埠序與物理位置</h2><figure><img src="figures/m0_s3/mzi_convention.svg" alt="共用 MZI 的埠序和相位順序示意"><figcaption>圖 1｜本步共用約定：向量 [upper, lower]；φ 在上方輸入，θ 在上方內臂。這是模型示意，非版圖。與 M0 S1 外部埠 in0／in1、out0／out1 對齊。</figcaption></figure>'''
body+=table('表 1｜三種編號的對照',['物理位置','本步／M0 S1 外部埠','PDK MMI 埠','M0 S2 場圖局部埠'],[
('上方','index 0，in0／out0','in2／out2','in2／out2，但在向量 index 1'),
('下方','index 1，in1／out1','in1／out1','in1／out1，但在向量 index 0')])
body+='''<p>M0 S2 的局部向量以 [lower, upper] 排列。本步使用交換矩陣 P 同時變換輸入、輸出：T_lower=P·T_upper·P。只換輸出兩列會代表另一個映射。這個 2×2 換序用於單顆 MZI；B7 使用另外的五路全域埠表。</p>
<h2 id="matrix">3．把結構寫成複數矩陣</h2>'''+pre('H = (1/√2) [[1, i], [i, 1]]\nPφ = diag(exp(iφ), 1)\nPθ = diag(exp(iθ), 1)\na = 10^(−loss_db/20)\nT(θ, φ) = a · C₂ · Pθ · C₁ · Pφ\n理想時 C₁=C₂=H')
body+='''<p>理想矩陣可獨立展開為：</p>'''+pre('T = a i exp(iθ/2) [[exp(iφ) sin(θ/2),   cos(θ/2)],\n                   [exp(iφ) cos(θ/2),  −sin(θ/2)]]')
body+='''<p>先算 Eout=T·Ein，再算各埠 P=|E|²。單路上埠輸入時，bar 功率為 sin²(θ/2)，cross 為 cos²(θ/2)。程式使用弧度；範例設定的 theta_pi、phi_pi 則以 π 為單位，讀取後才轉成弧度。</p><div class="callout">對整個輸入向量乘共同相位，不改變輸出功率。但單顆 MZI 嵌入含旁路的多路網路時，其共同相位是兩條作用線相對其他線的相位，必須保留。因此本步連完整複數矩陣一起核對。</div>
<h3>共用模組放在哪裡？</h3>'''
body+=table('表 2｜本步公開介面',['模組／函式','用途','輸入約定'],[
('<a href="../work/common/mzi.py">common/mzi.py</a> · T2／transfer_matrix','MZI 複數 2×2 矩陣','θ／φ 為弧度；loss_db≥0；兩個 coupler 誤差各在 [−0.5,0.5]。'),
('mzi.apply_matrix／powers／trace','求光場、功率與中間步驟','使用複數場；輸入不會被函式改寫。'),
('mzi.to_lower_first','與 M0 S2 局部埠序相容','同時交換輸入與輸出。'),
('mzi.theta_for_bar','由目標 bar 比例求 θ∈[0,π]','比例限 [0,1]；超出範圍回報 ValueError。'),
('mzi.propagation_factor','均勻段的相位與可選插入損耗','n_eff 為實數；長度與波長使用相同單位。'),
('<a href="../work/common/linear_network.py">common/linear_network.py</a>','2×2 嵌入、依序串接與固定功率差判讀','傳播順序列在前的元件先遇到；零裕量回傳 bit=None。')])
body+='''<div class="callout warn">模型範圍：前向集總 MZI；可選均勻插入損耗與無損 coupler 分光誤差。尚未加入反射、色散、版圖路徑萃取或 heater 校正。M0 S2 的 n_eff 不會自動成為完整 PDK 模型。</div>
<h2 id="run">4．學員執行與修改範例</h2>'''+pre(r'''Set-Location -LiteralPath 'C:\EDA_Codex\Lab06b'
& .\scripts\run_m0_s3.ps1''')
body+='''<p>使用 <a href="../config/m0_s3_example.json">m0_s3_example.json</a>，可觀察與修改輸入、θ、φ、loss_db 和兩顆耦合器的誤差。這些設定只作用於教學範例；標準測試及相容性回放使用各自固定案例。</p><ol><li>基準：theta_pi=0.5、phi_pi=1、兩路同相等振幅、loss_db=0。預測輸出後再執行。</li><li>只將 phi_pi 改為 0，再執行；記錄光轉到哪個埠。</li><li>把 phi_pi 還原為 1，再把 loss_db 改為 3；輸出方向相同，總功率應為輸入的 10⁻⁰·³≈0.501187 倍。</li><li>完成後還原範例設定；把自己的設定副本與觀察存入 learner/。</li></ol><p>測試入口：<a href="../work/m0_s3/test_optical_models.py">test_optical_models.py</a>；執行與證據入口：<a href="../work/m0_s3/run_models.py">run_models.py</a>。</p>
<h3>本輪範例：沿光路逐步追蹤</h3>'''
body+=f'''<p>目前 θ={EXAMPLE['theta']/3.141592653589793:.3f}π、φ={EXAMPLE['phi']/3.141592653589793:.3f}π、loss_db={EXAMPLE['loss_db']:.3f}。複數場以 real±imag·i 表示。</p>'''
body+=table('表 3｜本輪中間光場與功率',['位置','E upper','E lower','P upper','P lower','總功率'],[
(r['stage'],complex_text(r['field'][0]),complex_text(r['field'][1]),f"{r['power'][0]:.6f}",f"{r['power'][1]:.6f}",f"{r['total_power']:.6f}") for r in EXAMPLE['rows']])
body+='''<h2 id="response">5．θ／φ 如何改變輸出</h2><figure><img src="figures/m0_s3/mzi_response.png" alt="單路輸入的 theta 功率曲線及雙路輸入的 theta phi 功率圖"><figcaption>圖 2｜本輪由共用矩陣計算的理想參考圖。左：單路上埠輸入，φ 不改變功率；右：兩路同相等功率、總功率 1，θ／φ 共同決定上埠輸出。此圖不使用上方範例的額外損耗或分光誤差。</figcaption></figure>
<section class="panel"><h3>先在頁面預測</h3><label for="s3-input">輸入</label><select id="s3-input"><option value="single">只打上埠，總功率 1</option><option value="equal">雙路同相等功率，總功率 1</option></select><label for="s3-theta">θ：<b id="s3-theta-label">0.00 π</b></label><input id="s3-theta" type="range" min="0" max="2" step="0.01" value="0" style="width:100%"><label for="s3-phi">φ：<b id="s3-phi-label">0.00 π</b></label><input id="s3-phi" type="range" min="0" max="2" step="0.01" value="0" style="width:100%"><div id="s3-power" class="answers" aria-live="polite"></div><p class="muted">這是解析功率式的互動預習；Python 複數矩陣與測試 JSON 為正式證據。輸入總功率固定為 1，模型為理想無損。</p></section>
<script>(()=>{const t=document.querySelector('#s3-theta'),p=document.querySelector('#s3-phi'),input=document.querySelector('#s3-input');function show(){const theta=Number(t.value)*Math.PI,phi=Number(p.value)*Math.PI;let upper=input.value==='single'?Math.sin(theta/2)**2:(1+Math.sin(theta)*Math.cos(phi))/2;upper=Math.min(1,Math.max(0,upper));document.querySelector('#s3-theta-label').textContent=Number(t.value).toFixed(2)+' π';document.querySelector('#s3-phi-label').textContent=Number(p.value).toFixed(2)+' π';document.querySelector('#s3-power').textContent='P(out0 / upper) = '+upper.toFixed(6)+'   |   P(out1 / lower) = '+(1-upper).toFixed(6);}t.addEventListener('input',show);p.addEventListener('input',show);input.addEventListener('change',show);show();})();</script>
<h2 id="tests">6．單元測試與受控錯誤</h2>'''
body+=table('表 4｜本輪測試結果',['項目','結果','證據'],[
('正常模型的單元測試',f"{TESTS['passed']}/{TESTS['run']} 個測試方法；{TESTS['failures']} 失敗、{TESTS['errors']} 錯誤",'<a href="../work/m0_s3/out/unit_tests.log">原始測試 log</a>'),
('受控錯誤注入',f"{sum(r['detected'] for r in DATA['controlled_mutations'])}/5 被對應測試指出",'每次暫時替換函式，測試後於 finally 還原。'),
('還原後的整套測試','通過' if TESTS['after_mutation_restoration_passed'] else '未通過','<a href="../work/m0_s3/out/unit_tests_after_restoration.log">還原驗證 log</a>')])
body+='''<p>測試包含：完整複數矩陣、耦合器 90° 相位、切換／分光、隨機相位與分光誤差下的么正性、損耗換算、共同／相對相位、2π 週期、埠序轉換、非法參數、非相鄰埠嵌入、串接順序、邊界判讀、S2 相容及舊 B7 回放。18 個測試方法內含多組參數案例。</p><details><summary>查看全部測試方法</summary>'''
body+=table('測試方法清單',['方法','結果'],[(f'<code>{escape(r["name"])}</code>','通過' if r['status']=='pass' else '未通過') for r in TESTS['cases']])+'</details>'
labels={'real_coupler':'用實數 Hadamard 取代光學耦合器','theta_phi_swapped':'交換 θ／φ 的物理位置','power_factor_as_amplitude':'把功率衰減因子套到光場','reversed_cascade':'反轉矩陣串接順序','tie_counted_as_one':'把零裕量誤判成 1'}
body+=table('表 5｜五個受控錯誤如何被發現',['錯誤','對應測試','本輪結果'],[
(labels[r['name']],f'<a href="../work/m0_s3/out/mutation_{r["name"]}.log"><code>{r["test"]}</code></a>','已抓到；已還原' if r['detected'] else '未抓到') for r in DATA['controlled_mutations']])
body+='''<p>這些注入 log 內的失敗是預期證據，不代表正式模型未通過。實數 Hadamard 仍可通過么正性，卻不符合本課程的光學相位約定；因此需要複數矩陣與已知切換態的測試。</p>
<h2 id="compatibility">7．舊 B7 設定的相容性回放</h2><p>本段供講師確認共用模型與既有資料一致；B7 組網的學員主實作仍在 M1。沿用舊課程的七顆 MZI 排程與十四相位，重新計算五個函數各 16 組四路輸入，並核對儲存的完整複數 U。</p>'''
body+=table('表 6｜相容性回放：不是新的相位求解',['函數','通過／總數','最小有號裕量','複數 U 最大差'],[
(r['gate'],f"{r['passed']}/{r['total']}",f"{r['minimum_signed_margin']:.6f}",f"{r['max_complex_U_error']:.2e}") for r in COMPAT['functions']])
body+='''<p>判讀為 ΔP=P(out1)−P(out3)，正值判 1、負值判 0；|ΔP|≤ε 時 bit=None。回放使用理想無損模型、參考光振幅 R=3；未驗證新 PDK、熱控制或實體 Chip。<a href="../work/m0_s3/out/b7_compatibility.csv">80 筆 CSV</a> · <a href="../config/m0_s3_reference_provenance.json">舊相位來源與 SHA-256</a>。</p>
<h2 id="s2">8．接回 S2 的物理參數</h2>'''
body+=f'''<p>沿用 S2 的 n_eff={DATA['s2_connection']['neff']:.6f}、λ={DATA['s2_connection']['wavelength_um']:.2f} µm，均勻段相位為 βL=2πn_effL／λ。若兩臂只差幾何長度，π 相位差對應 ΔL≈<b>{DATA['s2_connection']['geometrical_length_for_pi_um']:.6f} µm</b>。</p><p>固定長度上改折射率，則使用 Δθ=2πΔn_effL／λ；與上列幾何長度差是兩種參數變化。這些公式不直接給出 heater 電壓，也沒有包含真實路徑的色散或損耗校正。</p>'''
body+='''<h2 id="submit">9．學員記錄與交付</h2><section class="panel"><label for="s3-name">學員姓名</label><input id="s3-name"><label for="s3-notes">埠序、相位預測、範例變更、測試結果與錯誤分析</label><textarea id="s3-notes" placeholder="記錄 phi_pi=1→0 的輸出變化、3 dB 的總功率，以及一項受控錯誤為何被抓到。"></textarea><button id="s3-generate">產生 M0 S3 學習記錄 JSON</button><textarea id="s3-json" hidden readonly aria-label="M0 S3 學習記錄 JSON" style="min-height:220px"></textarea><p class="muted">產生後複製到 learner/m0_s3_observations.json；離開頁面前請保存。</p></section>
<script>document.querySelector('#s3-generate').addEventListener('click',()=>{const out=document.querySelector('#s3-json');out.hidden=false;out.value=JSON.stringify({step:'M0 S3',learner_name:document.querySelector('#s3-name').value,observations:document.querySelector('#s3-notes').value,date:new Date().toISOString(),instructor_review:'pending'},null,2);out.focus();out.select();});</script>'''
body+=table('表 7｜本步交付與驗收',['交付','通過條件'],[
('共用 mzi.py 與 linear_network.py','向量順序、相位位置、單位與範圍寫清楚；輸入不會被函式修改。'),
('單元測試、錯誤注入與回放 JSON','正式模型全通過、受控錯誤被抓到、還原後通過；邊界不得算有效邏輯。'),
('θ／φ 圖、範例中間場與觀察記錄','能解釋單路／雙路輸入差異、光場與功率、矩陣乘法順序。'),
('學員提交','還原範例設定，提交自己的修改前後結果，由講師確認。')])
body+='''<p><a href="../work/m0_s3/out/model_results.json">本輪完整結果、版本、程式雜湊與互動對照樣本</a></p><p><b>下一步 M1 S1：</b>光訊號做邏輯：輸入編碼、相干參考光 R、混合與功率差讀取。此處完成的是共用模型與測試基準，後續仍需建立 B7、PDK 模擬、Chip 版圖與驗證。</p>'''
nav=''.join(f'<a href="{href}">{label}</a>' for href,label in [('../Lab06b_index.html','總覽與報告入口'),('plan.html','完整規劃'),('m0_s1.html','M0 S1｜工具鏈'),('m0_s2.html','M0 S2｜元件物理'),('m0_s3.html','M0 S3｜共用模型與測試')])
html=f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M0 S3｜共用光學模型與單元測試｜Lab06b</title><link rel="stylesheet" href="../assets/course.css"></head><body><header class="top"><a href="../Lab06b_index.html"><b>LAB06b</b>　PIC Chip 學員實作課程</a><small>2026-10-31 · M0 S3</small></header><div class="layout"><aside><strong>學習與實作入口</strong>{nav}<strong>本輪證據</strong><a href="../work/m0_s3/out/model_results.json">模型／測試 JSON</a><a href="../work/m0_s3/out/unit_tests.log">單元測試 log</a><a href="../work/m0_s3/out/b7_compatibility.csv">相容性回放 CSV</a><p class="muted">{status}<br>學員作答待提交</p></aside><main><button class="print" onclick="window.print()">列印／另存 PDF</button><div class="hero"><div class="eyebrow">MODULE 0 · STEP 3 · 60 MIN</div><h1>M0 S3｜共用光學模型與單元測試</h1><p class="lead">統一埠序與複數相位，用可重現的模型、測試與受控錯誤，建立後續光邏輯的計算基準。</p><span class="tag ok">{TESTS['passed']}/{TESTS['run']} 單元測試</span><span class="tag">5 種錯誤注入</span><span class="tag">{COMPAT['passed']}/80 相容回放</span></div>{body}<footer>根目錄 C:\\EDA_Codex\\Lab06b · 2026-10-31（Asia/Taipei）<br>集總前向模型；數值測試通過不替代 PDK、熱控制、DRC 或 Chip 實體驗證。</footer></main></div></body></html>'''
(ROOT/'course/m0_s3.html').write_text(clean_course_html(html),encoding='utf-8')

for relative in ['Lab06b_index.html','course/plan.html','course/m0_s1.html','course/m0_s1_foundation.html','course/m0_s2.html','analysis/lab01a_7_6.html','reference/source_context.html']:
    p=ROOT/relative;text=p.read_text(encoding='utf-8');prefix='../' if '/' in relative else ''
    href=prefix+'course/m0_s3.html'
    if f'href="{href}"' not in text:text=text.replace('</aside>',f'<a href="{href}">M0 S3｜共用模型與測試</a></aside>',1)
    if relative=='Lab06b_index.html':
        panel=f'<!-- M0S3:STATUS --><div class="callout good"><b>目前進度：</b>M0 S1 工具鏈、M0 S2 物理核心與 M0 S3 共用模型已建立。<b>S3：{status}</b>；學員作答各自驗收。Meep FDTD 仍保留未重跑標記。<a href="course/m0_s3.html">前往 M0 S3 →</a></div><!-- /M0S3:STATUS -->'
        if '<!-- M0S3:STATUS -->' in text:text=re.sub(r'<!-- M0S3:STATUS -->.*?<!-- /M0S3:STATUS -->',lambda m:panel,text,flags=re.S)
        else:text=re.sub(r'<div class="callout good"><b>本輪範圍：</b>.*?</div>',lambda m:panel,text,count=1,flags=re.S)
        text=text.replace('<h3>M0 S2｜元件物理</h3><p>本輪 FEM 模態、MMI 模態展開與相位分析；比較原始 FDTD 圖。</p><a href="course/m0_s2.html">進入 M0 S2 →</a>',
                          '<h3>M0 S3｜共用模型</h3><p>統一複數矩陣與埠序，執行單元測試、受控錯誤與相容性回放。</p><a href="course/m0_s3.html">進入 M0 S3 →</a>')
        label='S1 工具鏈通過；S2 核心實作通過；S3 模型測試通過' if DATA['core_passed'] else 'S1／S2 見前步；S3 待修正'
        text=re.sub(r'S1 工具鏈通過；S2 [^<]+</td>',lambda m:label+'</td>',text)
    text=text.replace('目前已完成 M0 S1，M0 S2 依本輪檢查結果驗收；','M0 三步依各步實算與學員作答驗收；')
    p.write_text(text,encoding='utf-8')
config=json.loads((ROOT/'config/course.json').read_text(encoding='utf-8'))
config['progress']['M0_S3']='shared models and unit tests passed; learner submission pending' if DATA['core_passed'] else 'model tests unresolved'
config['progress']['M1_S1']='next step: optical encoding, coherent reference and power readout'
(ROOT/'config/course.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'README_Lab06b_Course.md').write_text('''# Lab06b C 槽課程

根目錄：C:\\EDA_Codex\\Lab06b；入口 Lab06b_index.html。
完整規劃：四模組、17 步，建議 18 小時。
M0 S1：scripts/run_m0_s1.ps1；工具鏈與正常／故障 MZI。
M0 S2：scripts/run_m0_s2.ps1；FEM、標量傳播與場圖分析；Meep FDTD 未重跑。
M0 S3：scripts/run_m0_s3.ps1；共用模型、單元測試與相容回放。
工具設定 EDA_paths.json；共用模型 work/common/mzi.py、linear_network.py。
下一步 M1 S1：光訊號編碼、相干參考與功率判讀。
原 C01 保留原位，更新備份放 history/。
''',encoding='utf-8')
print('M0 S3 page rendered; core:',DATA['core_passed'])
