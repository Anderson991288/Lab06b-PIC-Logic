"""Render M1 S1 from numerical evidence and preserve navigation on rebuild."""
from pathlib import Path
from html import escape
import json, re
ROOT = Path(__file__).resolve().parents[1]
D = json.loads((ROOT/'work/m1_s1/out/encoding_results.json').read_text(encoding='utf-8'))
CFG = json.loads((ROOT/'config/course.json').read_text(encoding='utf-8'))
FIG = ROOT/'course/figures/m1_s1'; FIG.mkdir(parents=True, exist_ok=True)


def table(caption, headers, rows):
    return '<div class="scroll"><table><caption>'+caption+'</caption><thead><tr>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(c)+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'


def pre(text): return '<pre><code>'+escape(text)+'</code></pre>'


def bit(value): return '邊界' if value is None else str(value)


def truth_rows(kind):
    return [(''.join(map(str, r['bits'])), ' / '.join(f'{p:.6f}' for p in r['output_powers']),
             f"{r['readout'].get('delta', r['readout'].get('power')):.6f}",
             f"{r['readout']['margin']:.6f}", bit(r['readout']['bit']), r['expected']) for r in D['baseline'][kind]]


# B7 orientation sheet only. Construction of the 5x5 U remains M1 S2.
svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="470" viewBox="0 0 1120 470" role="img" aria-labelledby="t d"><title id="t">B7 輸入與判讀埠標註圖</title><desc id="d">五條光路由上往下是 x1 x2 x3 x4 與參考光 R。七顆 MZI 分四層。輸出讀取 index 1 減 index 3，分別為一基編號 o2 與 o4。</desc><rect width="1120" height="470" rx="10" fill="#f4f7fc"/>']
for layer in range(4):
    x = 280+layer*175
    svg.append(f'<text x="{x}" y="43" text-anchor="middle" fill="#526379" font-size="17">Layer {layer}</text>')
for rail, name in enumerate(['x1', 'x2', 'x3', 'x4', 'R']):
    y = 92+rail*66
    color = '#a65c16' if rail == 4 else '#155bd0'
    label = f'{name} · in{rail}' + (' (振幅 3)' if rail == 4 else '')
    out = f'out{rail} / o{rail+1}' + ('  ＋讀取' if rail == 1 else '  −讀取' if rail == 3 else '')
    svg.append(f'<path d="M195 {y}H875" stroke="{color}" stroke-width="4"/><text x="15" y="{y+6}" fill="{color}" font-size="18">{label}</text><text x="893" y="{y+6}" fill="{color}" font-size="18">{out}</text>')
    if rail in [1, 3]: svg.append(f'<circle cx="873" cy="{y}" r="8" fill="#258350"/>')
for number, (rail, layer) in enumerate(CFG['architecture']['ops_zero_based'], 1):
    x = 280+layer*175; y = 92+rail*66
    svg.append(f'<rect x="{x-33}" y="{y-15}" width="66" height="96" rx="7" fill="#e0eafa" stroke="#155bd0" stroke-width="2"/><text x="{x}" y="{y+39}" text-anchor="middle" font-size="18" fill="#17263b">M{number}</text>')
svg.append('<text x="25" y="424" fill="#17263b" font-size="19">編碼 v=[x1,x2,x3,x4,R]ᵀ → 光路 y=Uv → Pk=|yk|² → ΔP=P(out1)−P(out3)</text><text x="25" y="455" fill="#526379" font-size="16">依 config/course.json 繪製的接線導覽；非新 PDK 電路、非 GDS 版圖。</text></svg>')
(FIG/'b7_encoding_map.svg').write_text(''.join(svg), encoding='utf-8')

body = f'''<div class="callout good"><b>這一步要回答：</b>位元在哪裡變成光？參考光提供什麼？光偵測器怎麼把功率變成 0／1？<br><b>本輪結果：</b>{D['unit_tests']['passed']}/{D['unit_tests']['run']} 項本步測試、{D['m0_s3_regression']['passed']}/18 項前步回歸、8/8 實驗檢查通過；學員作答待驗收。</div>
<h2 id="predict">1．先預測：場、功率、位元是三個不同量</h2><p>核心 30 分鐘：預測 5 分、輸入編碼與 B7 標註 10 分、AND2 操作 10 分、交付 5 分。兩顆 MZI 的 NAND2 與相位掃描可再用 15 分鐘深入。</p><ol><li>R=3 是 3 倍光功率，還是 9 個功率單位？</li><li>兩路振幅都是 1，為何混合後可以有一個埠的功率為 2？</li><li>輸入 00 且沒有參考光，線性被動光路能否自己產生亮光？</li><li>輸出兩埠都暗時，ΔP=0 應該一律判成 1 嗎？</li></ol>
<h2 id="encoding">2．白話範例：用亮／暗編碼，保留複數相位</h2>'''
body += pre('資料位元 b ∈ {0,1}\nE = b √P_on exp(iα)       # 本步 P_on=1；相位 α 以 rad 表示\nP = |E|²                  # 偵測器讀取功率，不直接讀複數 E\nv = [x1,x2,x3,x4, R exp(iψ)]ᵀ\nB7 基準：R=3、ψ=0 → P_R=9；各資料 1 的功率為 1')
body += '''<p>本課程採開關振幅編碼（OOK）：0 對應零場，1 對應振幅 1；資料光具有受控相對相位。此處不使用 ±1 編碼。若以 1 個歸一化功率單位代表 1 µW，則單路資料 1 為 1 µW、B7 的 R=3 為 9 µW，四路全 1 的總輸入為 13 µW。</p><div class="callout">每組資料使用相同的功率刻度與固定門檻。不要把每個輸入向量各自除以其長度；那會使參考光隨資料變動，改變原本的邏輯實驗。</div>'''
body += table('表 1｜先看幾組五路編碼',['資料 x1x2x3x4','輸入場 v','資料功率','參考光功率','總功率'],[
    ('0000','[0,0,0,0,3]ᵀ',0,9,9), ('1000','[1,0,0,0,3]ᵀ',1,9,10),
    ('1100','[1,1,0,0,3]ᵀ',2,9,11), ('1111','[1,1,1,1,3]ᵀ',4,9,13)])
body += '''<p><a href="../work/m1_s1/out/b7_input_encoding.csv">完整 16 組編碼 CSV</a>：pattern_index 的最低位元對應 x1；顯示字串仍依 x1→x4 排列，因此 index 1 顯示 1000。</p>
<h2 id="ports">3．在 B7 上標出輸入、混合與讀取</h2><figure><img src="figures/m1_s1/b7_encoding_map.svg" alt="B7 五路輸入、參考光、七顆 MZI 與兩個讀取埠"><figcaption>圖 1｜由課程 OPS 規格繪製的導覽圖。x1–x4 在資料光輸入端；R 在第五路。heater 設定 θ／φ，資料位元不靠每次切換 heater 編碼。接收端固定讀兩個輸出功率，其他輸出也帶走能量。</figcaption></figure>'''
body += table('表 2｜埠名對照，避免差一個編號',['用途','程式零基索引','文字一基名稱','判讀'],[
    ('資料光','in0～in3','x1～x4','位元 → 場'), ('參考光','in4','R','固定複數場'),
    ('B7 正讀取','out1','o2','＋P(out1)'), ('B7 負讀取','out3','o4','−P(out3)'),
    ('本頁局部 AND2','out0／out1','upper／lower','＋P(out0)−P(out1)')])
body += '''<p>B7 仍沿用 ΔP=P(out1)−P(out3)、門檻 0、ε=10⁻¹⁰；本頁先用小網路理解編碼與讀取。B7 的 5×5 U 建立留到 M1 S2；不要把局部 AND2 的門檻與埠位直接套到 B7。</p>
<h2 id="run">4．學員操作：從固定相位的單顆 MZI 看 AND2</h2>'''
body += pre(r'''Set-Location -LiteralPath 'C:\EDA_Codex\Lab06b'
& .\scripts\run_m1_s1.ps1''')
body += '''<p>沿用 M0 S3 的 T(θ,φ)，固定 θ=π/2、φ=0。資料光由兩個輸入進入；功能設定在四組資料之間維持不變。</p>'''
body += pre('k = (−1+i)/2\nE_upper = k(x1+x2)\nE_lower = k(x1−x2)\nΔP = P_upper−P_lower = 2x1x2       # 兩路同相\nmargin = ΔP−T；固定 T=1\nmargin>ε → 1；margin<−ε → 0；其餘 → 邊界（bit=None）')
body += table('表 3｜本輪單顆 MZI AND2：固定功率差門檻 1',['x1x2','P upper / lower','ΔP','margin','判讀','真值'], truth_rows('AND2'))
body += '''<p>11 的兩個輸入總功率是 2，輸出是 2+0，仍然守恆。01／10 的輸出是 0.5+0.5。相干光場先相加／相消，再取模平方；不能先把每一路輸入功率相加當成某一埠的功率。</p>
<h3>修改設定，再重跑</h3><ol><li>開啟 <a href="../config/m1_s1_example.json">m1_s1_example.json</a>，保留 bits=[1,1]；先記錄基準。</li><li>把 and_relative_phase_pi 從 0 改成 0.5，再改成 1，觀察兩個功率及固定門檻判讀。</li><li>還原相位 0，把 and_loss_db 改成 3 與 4；門檻仍為 1。比較 3 dB 時 ΔP≈1.002374 與 4 dB 時 ΔP≈0.796214，說明接近門檻的餘裕。</li><li>修改只改變「學員範例」；固定基準測試仍使用標準案例。完成後還原設定，再保存自己的設定副本。</li></ol>
<h2 id="reference">5．參考光：讓 00 仍有可混合的光場</h2><p>沒有參考光時，OOK 的 00 是零向量；任何固定線性光路都將它映射為零。若要求 NAND2 的 00 在選定輸出呈亮光，需要額外光源。這不表示所有電子判讀方式都無法對黑暗輸出邏輯 1；此處限定亮光為 1、正功率門檻的編碼方式。</p><p>深入實驗使用三路 [x1,x2,R]、兩顆共用 MZI。第一顆混合資料，第二顆混合第一顆上輸出與 R；另外兩個輸出完整保留。此處 R=2，與 B7 的 R=3 是不同網路設定。</p>'''
body += pre('MZI1：θ1=π/2，φ1=0，作用於 modes (0,1)\nMZI2：θ2=2 asin(√(2/3))，φ2=π/4，作用於 modes (0,2)\nU3 = embed(T2) · embed(T1)\nEout0 = q (R exp(iψ)−x1−x2)/√3，|q|=1\nPout0 = |R exp(iψ)−x1−x2|²/3\n基準 R=2、ψ=0；固定單埠功率門檻 T=1/6')
body += table('表 4｜本輪兩顆 MZI＋R：NAND2 單埠判讀',['x1x2','P out0 / out1 / out2','P out0','margin','判讀','真值'], truth_rows('NAND2'))
body += '''<p>係數 [−1,−1,1]/√3 的範數為 1，且程式核對完整 U3 的么正性與三個輸出總功率。選定輸出的抵消代表能量流到其他埠。與原 C01 的 E=(R−x1−x2)/2 概念式相比，本步使用可由兩顆無損 MZI 實現的 1/√3 係數，功率與門檻一起重新計算。</p>'''
body += table('表 5｜擾動實驗：固定功能與門檻，不重新調參',['擾動','符合原真值／4','觀察'],[
    ('AND2：資料相對相位 π', f"{sum(r['correct'] for r in D['perturbations']['AND2_relative_phase_pi'])}/4", '11 的光轉到 lower；ΔP=−2。'),
    ('NAND2：移除 R', f"{sum(r['correct'] for r in D['perturbations']['NAND2_reference_off'])}/4", '00 沒光，11 失去抵消；兩組錯誤。'),
    ('NAND2：R 相位改成 π', f"{sum(r['correct'] for r in D['perturbations']['NAND2_reference_phase_pi'])}/4", '11 從相消變相長。'),
    ('NAND2：R 振幅改成 3', f"{sum(r['correct'] for r in D['perturbations']['NAND2_reference_amplitude_3'])}/4", '參考光更強不保證原門檻仍正確。')])
body += '''<h2 id="coherence">6．相干與相位：同樣功率不保證相同邏輯</h2><figure><img src="figures/m1_s1/encoding_readout.png" alt="AND相對相位、NAND參考相位與振幅對判讀裕量的影響"><figcaption>圖 2｜本輪全部曲線由共用複數矩陣計算。左：11 的 ΔP=2cos(α)。中：改 R 相位後，原本相消的 11 變亮。右：各輸入依真值取有號裕量，再取最小值；大於 0 才表示四組都有正確餘裕。</figcaption></figure><p>若相位在接收平均期間均勻遍歷 0～2π，交叉干涉項平均為零。本輪用 64 個等間隔相位示範，AND2 的 11 平均功率為 [1,1]、平均 ΔP≈0，無法通過原本的門檻 1。這是相位集合平均，沒有宣稱實際雷射的相干時間、頻寬或錯誤率。</p>
<section class="panel"><h3>互動預測：固定門檻，改位元／相位／R</h3><label for="logic-kind">實驗</label><select id="logic-kind"><option>AND2</option><option>NAND2</option></select><label for="logic-bits">資料 x1x2</label><select id="logic-bits"><option>00</option><option>01</option><option>10</option><option selected>11</option></select><label for="logic-phase">相位：<b id="logic-phase-label">0.00 π</b>（AND2 改 x2；NAND2 改 R）</label><input id="logic-phase" type="range" min="0" max="2" step="0.01" value="0" style="width:100%"><label for="logic-reference">參考光振幅 R：<b id="logic-reference-label">2.00</b>（僅 NAND2）</label><input id="logic-reference" type="range" min="0" max="3.2" step="0.01" value="2" style="width:100%"><div id="logic-result" class="answers" aria-live="polite"></div><p class="muted">頁面用解析式預測；下方 JSON 的 Python 複數矩陣結果為正式證據。此互動固定無損、資料 1 功率為 1。</p></section>
<script>(()=>{const kind=document.querySelector('#logic-kind'),bits=document.querySelector('#logic-bits'),phase=document.querySelector('#logic-phase'),ref=document.querySelector('#logic-reference');function show(){const [a,b]=bits.value.split('').map(Number),p=Number(phase.value)*Math.PI,R=Number(ref.value);let powers,metric,T;if(kind.value==='AND2'){powers=[(a*a+b*b+2*a*b*Math.cos(p))/2,(a*a+b*b-2*a*b*Math.cos(p))/2];metric=powers[0]-powers[1];T=1;}else{powers=[(R*R+(a+b)**2-2*R*(a+b)*Math.cos(p))/3,(a-b)**2/2];powers.push(a+b+R*R-powers[0]-powers[1]);metric=powers[0];T=1/6;}powers=powers.map(x=>Math.abs(x)<1e-12?0:x);const margin=metric-T,bit=Math.abs(margin)<=1e-10?null:Number(margin>0);const data={kind:kind.value,powers,metric,threshold:T,margin,bit};const box=document.querySelector('#logic-result');box.dataset.result=JSON.stringify(data);box.textContent='P(out0…): ['+powers.map(x=>x.toFixed(6)).join(', ')+'] | '+(kind.value==='AND2'?'ΔP':'P(out0)')+'='+metric.toFixed(6)+' | margin='+margin.toFixed(6)+' | 判讀 '+(bit===null?'邊界':bit);document.querySelector('#logic-phase-label').textContent=Number(phase.value).toFixed(2)+' π';document.querySelector('#logic-reference-label').textContent=R.toFixed(2);ref.disabled=kind.value==='AND2';}for(const x of [kind,bits])x.addEventListener('change',show);for(const x of [phase,ref])x.addEventListener('input',show);show();})();</script>
<h2 id="receiver">7．從功率走到光電流、電壓與判讀</h2>'''
body += pre('假設匹配 PD，且此處定義接收端正向差分增益：\nI+ = ℛ P+；I− = ℛ P−\nΔI = ℛ (P+−P−)\nVdiff = Zt ΔI；Vthreshold = Zt ℛ P_unit T\n示例：P_unit=1 µW、ℛ=0.8 A/W、Zt=10 kV/A\nAND2 的 11：ΔP=2 → ΔI=1.6 µA → Vdiff=16 mV\n固定 T=1 → Vthreshold=8 mV')
body += '''<p>上述參數是單位換算練習，沒有選定真實偵測器或聲稱頻寬。實際 TIA 的正負極性、兩顆 PD 響應差異、偏移、暗電流、雜訊、飽和與時間響應都需要校正。電子判讀規則提供非線性；被動線性光路本身不會直接輸出數位位元。</p><p>物理依據：<a href="https://hub.hamamatsu.com/us/en/technical-notes/detector-selection/the-wits-guide-to-selecting-a-photodetector.html">Hamamatsu：PD 響應度與光功率／光電流</a>；<a href="https://www.thorlabs.de/newgrouppage9.cfm?objectgroup_id=5201&amp;pn=PDB835C">Thorlabs：匹配 PD 的平衡偵測與 TIA</a>；<a href="https://interactivetextbooks.tudelft.nl/tn2421/content/Chap5_Interference/InterferenceCoherence_2022_01Clean.html">TU Delft：干涉與相干</a>。本頁公式推導、參數及實驗結果由本課程程式核對。</p>
<h2 id="evidence">8．檢查結果與檔案</h2>'''
body += table('表 6｜本輪驗證與可追溯檔案',['內容','結果／用途','檔案'],[
    ('本步單元測試',f"{D['unit_tests']['passed']}/{D['unit_tests']['run']}；場／功率、編碼、相位、三路么正、門檻與電子單位",'<a href="../work/m1_s1/out/unit_tests.log">log</a>'),
    ('M0 S3 回歸',f"{D['m0_s3_regression']['passed']}/18；原共用模型與舊 B7 相容案例",'<a href="../work/m1_s1/out/m0_s3_regression.log">log</a>'),
    ('固定與擾動實驗','兩組基準真值表、四種擾動，共 24 筆；擾動錯誤是教學結果','<a href="../work/m1_s1/out/truth_tables.csv">CSV</a>'),
    ('完整結果','中間複數場、全部輸出功率、範例接收電壓、版本與 SHA-256','<a href="../work/m1_s1/out/encoding_results.json">JSON</a>'),
    ('共用編碼／偵測','接續 M0 S3，不改動原 mzi.py 與 linear_network.py','<a href="../work/common/encoding.py">encoding.py</a> · <a href="../work/common/photodetection.py">photodetection.py</a>'),
    ('實驗與測試入口','可讀的小網路、解析回歸與守恆測試','<a href="../work/m1_s1/experiments.py">experiments.py</a> · <a href="../work/m1_s1/test_encoding_readout.py">test_encoding_readout.py</a>')])
sample = D['student_example']
body += table('表 7｜目前學員設定的重跑結果（與基準分開）',['項目','數值'],[
    ('輸入位元',escape(str(sample['config']['bits']))),
    ('AND2 功率差／margin／判讀',f"{sample['AND2']['readout']['delta']:.6f} / {sample['AND2']['readout']['margin']:.6f} / {bit(sample['AND2']['readout']['bit'])}"),
    ('NAND2 單埠功率／margin／判讀',f"{sample['NAND2']['readout']['power']:.6f} / {sample['NAND2']['readout']['margin']:.6f} / {bit(sample['NAND2']['readout']['bit'])}"),
    ('AND2 差分電壓／門檻',f"{sample['receiver']['differential_voltage_v']*1e3:.6f} mV / {sample['receiver']['threshold_voltage_v']*1e3:.6f} mV")])
body += '''<h2 id="submit">9．驗收條件與學員交付</h2><ol><li>在圖 1 標出 x1–x4、R、o2／o4，並說出「編碼 → 光場混合 → 功率與門檻」三步。</li><li>手算 1100 的 B7 輸入場、R 的功率與總功率；不要先套尚未建立的 B7 U。</li><li>提交 AND2 四組真值與 11 在相位 0／π/2／π 的功率差；解釋固定門檻。</li><li>深入題：說明沒有 R 的 00，以及 R 相位錯誤的 11；指出抵消後其他輸出仍有功率。</li><li>交付修改前後設定副本、執行結果與口述記錄；學員完成由講師另行確認。</li></ol>
<section class="panel"><label for="m1-name">學員姓名</label><input id="m1-name"><label for="m1-encoding">1100 的場、參考功率與總功率；B7 兩個讀取埠</label><textarea id="m1-encoding"></textarea><label for="m1-observation">AND2 相位／損耗結果，及 R 移除或改相位的觀察</label><textarea id="m1-observation"></textarea><button id="m1-generate">產生 M1 S1 學習記錄 JSON</button><textarea id="m1-json" hidden readonly aria-label="M1 S1 學習記錄 JSON" style="min-height:220px"></textarea><p class="muted">複製保存到 learner/m1_s1_observations.json；<a href="../learner/m1_s1_observations.template.json">空白範本</a>。</p></section>
<script>document.querySelector('#m1-generate').addEventListener('click',()=>{const box=document.querySelector('#m1-json');box.hidden=false;box.value=JSON.stringify({step:'M1 S1',learner_name:document.querySelector('#m1-name').value,encoding_and_ports:document.querySelector('#m1-encoding').value,observations:document.querySelector('#m1-observation').value,date:new Date().toISOString(),instructor_review:'pending'},null,2);box.focus();box.select();});</script>
<p><b>下一步 M1 S2：</b>依七顆 MZI 的 OPS 建立 B7 的 5×5 U，逐層追蹤五路光場並檢查么正性。後續再處理完整功能設定、PDK 與 PIC 版圖。</p>'''
nav = ''.join(f'<a href="{href}">{label}</a>' for href, label in [('../Lab06b_index.html','總覽與報告入口'),('plan.html','完整規劃'),('m0_s3.html','M0 S3｜共用模型'),('m1_s1.html','M1 S1｜編碼與判讀'),('#encoding','輸入編碼'),('#ports','B7 埠位'),('#run','AND2 操作'),('#reference','參考光與 NAND2'),('#receiver','PD 與功率判讀'),('#submit','學員交付')])
html = f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M1 S1｜光訊號編碼、參考光與功率判讀｜Lab06b</title><link rel="stylesheet" href="../assets/course.css"></head><body><header class="top"><a href="../Lab06b_index.html"><b>LAB06b</b>　PIC Chip 學員實作課程</a><small>2026-10-31 · M1 S1</small></header><div class="layout"><aside><strong>學習與實作入口</strong>{nav}<a href="../work/m1_s1/out/encoding_results.json">本輪數值證據</a><p class="muted">核心實驗已驗證<br>學員作答待提交</p></aside><main><button class="print" onclick="window.print()">列印／另存 PDF</button><div class="hero"><div class="eyebrow">MODULE 1 · STEP 1 · 30 MIN + OPTIONAL LAB</div><h1>M1 S1｜光訊號編碼、參考光與功率判讀</h1><p class="lead">從一個位元的複數光場出發，標清 B7 輸入與讀取埠，實際驗證相干混合、參考光與固定門檻的關係。</p><span class="tag ok">{D['unit_tests']['passed']} 項本步測試</span><span class="tag">16 組 B7 輸入編碼</span><span class="tag">AND2／NAND2 實驗</span></div>{body}<footer>正式根目錄 C:\\EDA_Codex\\Lab06b · 2026-10-31（Asia/Taipei）。理想穩態光路與示意接收模型；學員作答另行驗收。</footer></main></div></body></html>'''
from report_policy import clean_course_html
(ROOT/'course/m1_s1.html').write_text(clean_course_html(html), encoding='utf-8')

for relative in ['Lab06b_index.html','course/plan.html','course/m0_s1.html','course/m0_s1_foundation.html','course/m0_s2.html','course/m0_s3.html','analysis/lab01a_7_6.html','reference/source_context.html']:
    path = ROOT/relative; text = path.read_text(encoding='utf-8')
    prefix = '../' if '/' in relative else ''
    href = prefix+'course/m1_s1.html'
    if f'href="{href}"' not in text: text = text.replace('</aside>', f'<a href="{href}">M1 S1｜光編碼與判讀</a></aside>', 1)
    text = text.replace('本輪只開始 M0 S1；後續 B7 電路、Chip 版圖與最終交付依關卡進行。', '各步進度與本輪證據見總報告；後續 B7 電路、Chip 版圖與最終交付依關卡進行。')
    if relative == 'Lab06b_index.html':
        panel = '<!-- M1S1:STATUS --><div class="callout good"><b>目前進度：</b>M0 三步已建立；M1 S1 編碼、參考光與功率判讀核心通過。學員作答另行驗收。<a href="course/m1_s1.html">進入 M1 S1 →</a><br>本步理想實驗未加入新 PDK／Chip 驗證；Meep FDTD 維持未重跑標記。</div><!-- /M1S1:STATUS -->'
        pattern = r'<!-- (?:M0S3|M1S1):STATUS -->.*?<!-- /(?:M0S3|M1S1):STATUS -->'
        text = re.sub(pattern, lambda match: panel, text, count=1, flags=re.S)
        text = re.sub(r'<tr><td>M1 光訊號做邏輯</td>.*?</tr>',
                      lambda m: m[0].replace('<td>規劃完成</td>', '<td>S1 編碼與判讀核心通過；S2–S5 待實作</td>'), text, flags=re.S)
        if '<td>M1 S1 主實作</td>' not in text:
            rows = '<tr><td>M0 S2 主實作</td><td><a href="course/m0_s2.html">元件物理與光場</a></td><td>FEM、標量傳播與場圖分析</td></tr><tr><td>M0 S3 主實作</td><td><a href="course/m0_s3.html">共用模型與單元測試</a></td><td>複數矩陣、埠序、受控錯誤與相容回放</td></tr><tr><td>M1 S1 主實作</td><td><a href="course/m1_s1.html">光訊號編碼、參考光與功率判讀</a></td><td>本輪理想小網路實驗與學員練習</td></tr>'
            text = text.replace('<tr><td>理想 MZI 補充</td>', rows+'<tr><td>理想 MZI 補充</td>', 1)
        text = text.replace('M0 三步依各步實算與學員作答驗收；', 'M0 三步與 M1 S1 核心已實算，學員作答各自驗收；')
        if '<!-- M1S1:CARD -->' not in text:
            card = '<!-- M1S1:CARD --><article class="card"><div class="num">M1 S1</div><h3>光訊號編碼與功率判讀</h3><p>標出 x1–x4、R 與讀取埠；實驗 AND2、NAND2 的光場與固定門檻。</p><a href="course/m1_s1.html">進入本步 →</a></article><!-- /M1S1:CARD -->'
            text = text.replace('<div class="grid">', '<div class="grid">'+card, 1)
    if relative == 'course/plan.html':
        text = text.replace('<td>M1 s1<br>0.5 h</td>', '<td><a href="m1_s1.html">M1 s1</a><br>0.5 h</td>')
    path.write_text(text, encoding='utf-8')
CFG['progress']['M1_S1'] = 'optical encoding and reference/readout experiments passed; learner submission pending' if D['core_passed'] else 'experiment checks unresolved'
CFG['progress']['M1_S2'] = 'next step: seven-MZI B7 topology and 5x5 transfer matrix'
(ROOT/'config/course.json').write_text(json.dumps(CFG, ensure_ascii=False, indent=2), encoding='utf-8')
readme = (ROOT/'README_Lab06b_Course.md').read_text(encoding='utf-8')
readme = readme.replace('下一步 M1 S1：光訊號編碼、相干參考與功率判讀。', 'M1 S1：scripts/run_m1_s1.ps1；光訊號編碼、參考光與功率判讀。\n下一步 M1 S2：B7 接線與 5×5 傳輸矩陣。')
(ROOT/'README_Lab06b_Course.md').write_text(readme, encoding='utf-8')
print('M1 S1 page rendered; core:', D['core_passed'])
