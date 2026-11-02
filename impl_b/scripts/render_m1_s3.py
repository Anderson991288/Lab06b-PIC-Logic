from report_policy import clean_course_html
"""Render weighted sums and fixed differential readout from M1 S3 evidence."""
from pathlib import Path
from html import escape
import json,re
ROOT=Path(__file__).resolve().parents[1]
D=json.loads((ROOT/'work/m1_s3/out/readout_results.json').read_text(encoding='utf-8'))
CFG=json.loads((ROOT/'config/course.json').read_text(encoding='utf-8'))
LABELS=['x1','x2','x3','x4','R']


def table(caption,headers,rows):
    return '<div class="scroll"><table><caption>'+caption+'</caption><thead><tr>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(c)+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'


def pre(text):return '<pre><code>'+escape(text)+'</code></pre>'
def ztext(z):
    a,b=z
    if abs(a)<.5e-6:a=0.
    if abs(b)<.5e-6:b=0.
    return f'{a:.6f}{b:+.6f}i'
def bit(value):return '邊界（None）' if value is None else str(value)
def fmt(value):return f'{value:.9f}'


reg_pass=sum(r['passed'] for r in D['regression'].values());reg_run=sum(r['run'] for r in D['regression'].values())
state='核心加權和與判讀驗證通過' if D['core_passed'] else '有未通過項，請檢查原始證據'
body=f'''<div class="callout {'good' if D['core_passed'] else 'warn'}"><b>這一步要回答：</b>為什麼兩個讀取埠的功率差會由負轉正？每一路輸入對這個結果貢獻了什麼？<br><b>本輪結果：</b>{D['unit_tests']['passed']}/{D['unit_tests']['run']} 項本步測試、{reg_pass}/{reg_run} 項前步回歸、{sum(c['passed'] for c in D['checks'])}/{len(D['checks'])} 項加權和檢查；{state}。學員作答另行驗收。</div>
<h2 id="predict">1．先預測：先加場，還是先加功率？</h2><p>建議 60 分鐘：複習埠位與相位來源 5 分、手算 1000／1100 各 10 分、功率與干涉項 10 分、程式與互動核對 15 分、交付 10 分。</p><ol><li>R 振幅為 3，對 out1 的貢獻是 3、9，還是 3U[1,4]？</li><li>同一個埠的兩個場方向相反，功率的干涉項可以是負值嗎？實際功率呢？</li><li>ΔP=0 或接近 0 時，能否直接宣稱輸出有效邏輯 1？</li><li>若把 U 的一列做複數共軛，是否仍是 y=Uv 的同一個加權和？</li></ol>
<h2 id="setup">2．固定條件：接續 B7，沿用一組已知相位</h2><p>本步由共用 b7.py 重新建立 U，沿用舊教材 AND2 的十四個完整精度相位。僅以 1000／1100 做手算範例，不重新合成相位；五種功能的完整 80 筆驗收留到 M1 S4。</p>'''
body+=pre('輸入順序：v=[x1,x2,x3,x4,R]ᵀ\n1000 → v=[1,0,0,0,3]ᵀ，總功率=10\n1100 → v=[1,1,0,0,3]ᵀ，總功率=11\n本步資料光及 R 的基準相位皆為 0\n\n正讀取：out1（零基）= o2（一基）\n負讀取：out3（零基）= o4（一基）\nΔP = |y_out1|²−|y_out3|²\n固定門檻 τ=0；邊界容許 ε=10⁻¹⁰（歸一化功率單位）')
body+='''<p>本頁的 y_out1／y_out3 使用程式零基索引；原課程的 y2／y4 對應同兩個埠。<a href="../config/m0_s3_reference_provenance.json">原相位來源及 SHA-256</a> · <a href="m1_s2.html">回看 B7 接線與矩陣</a>。</p>'''
body+=table('表 1｜本輪 U 的兩個讀取列：保留複數係數',['輸入 index / 名稱','U[1,j] → out1','U[3,j] → out3'],[
    (f'{j} / {name}',f'<code>{ztext(D["U"][1][j])}</code>',f'<code>{ztext(D["U"][3][j])}</code>') for j,name in enumerate(LABELS)])
body+='''<h2 id="weighted">3．手算兩個案例：逐項乘，再做複數相加</h2>'''
body+=pre('tᵢⱼ = U[i,j] v[j]\nyᵢ = Σⱼ tᵢⱼ\n\ny_out1(1000) = U[1,0] + 3U[1,4]\ny_out3(1000) = U[3,0] + 3U[3,4]\ny_out1(1100) = U[1,0] + U[1,1] + 3U[1,4]\ny_out3(1100) = U[3,0] + U[3,1] + 3U[3,4]')
for number,c in enumerate(D['worked_cases'],2):
    a=c['result'];plus=a['positive'];minus=a['negative']
    body+=f'<h3>{c["pattern"]}：先遮住最後一列的結果，自己算一次</h3>'
    body+=table(f'表 {number}｜{c["pattern"]} 的五項貢獻與累加',['來源','v[j]','out1 貢獻 t','out1 累加','out3 貢獻 t','out3 累加'],[
        (name,f'<code>{ztext(c["input"][j])}</code>',f'<code>{ztext(plus["terms"][j])}</code>',f'<code>{ztext(plus["cumulative"][j])}</code>',f'<code>{ztext(minus["terms"][j])}</code>',f'<code>{ztext(minus["cumulative"][j])}</code>') for j,name in enumerate(LABELS)])
    body+=f'<p><b>累加結果：</b>y_out1=<code>{ztext(plus["field"])}</code>；y_out3=<code>{ztext(minus["field"])}</code>。<b>注意：</b>R 的場先乘 3，之後才計算整個和的模平方。</p>'
body+='''<figure><img src="figures/m1_s3/phasor_sums.png" alt="1000與1100的兩個讀取埠，複數場貢獻首尾相接"><figcaption>圖 1｜本輪複數平面上的首尾相接。彩色箭頭為各路 tᵢⱼ；虛線為從原點到總場 yᵢ。振幅為 0 的輸入不畫箭頭，但計算表保留五個位置。箭頭方向代表相位，圖不是空間光場傳播圖。</figcaption></figure>
<h2 id="power">4．取模平方：把漏掉的干涉項找回來</h2>'''
body+=pre('若 y=a+ib，則 P=|y|²=a²+b²\n\nPᵢ = |Σⱼ tᵢⱼ|²\n   = Σⱼ |tᵢⱼ|² + Σⱼ<ₖ 2 Re(tᵢⱼ conj(tᵢₖ))\n   = 自項功率 + 成對干涉項\n\n干涉項可正可負；完整 Pᵢ 必須非負。')
body+=table('表 4｜各埠功率的展開，不能先把每項功率相加',['資料','讀取埠','自項功率','干涉項總和','實際功率'],[
    (c['pattern'],f'out{r["output"]}',fmt(r['self_power']),fmt(r['interference_power']),fmt(r['power']))
    for c in D['worked_cases'] for r in [c['result']['positive'],c['result']['negative']]])
body+='<details><summary>查看非零的成對干涉貢獻</summary>'
body+=table('表 5｜成對干涉項；完整 10 對／埠保存在 CSV',['資料','埠','輸入對','2 Re(tⱼ conj(tₖ))'],[
    (c['pattern'],f'out{r["output"]}',LABELS[p['j']]+' × '+LABELS[p['k']],fmt(p['power']))
    for c in D['worked_cases'] for r in [c['result']['positive'],c['result']['negative']] for p in r['pairs'] if abs(p['power'])>1e-8])+'</details>'
body+='''<p>把所有輸入的相對相位獨立平均，交叉項才會全部消失。只讓 R 的相位平均，資料光彼此的干涉仍可能保留。本步測試也核對這個差異。背景公式見 <a href="https://interactivetextbooks.tudelft.nl/tn2421/content/Chap5_Interference/InterferenceCoherence_2022_01Clean.html">TU Delft：相干場總和與干涉項</a>；本頁數值由本課程程式重新計算。</p>
<h2 id="decision">5．功率差、裕量與固定門檻</h2>'''
body+=pre('ΔP = P(out1)−P(out3)\nmargin = ΔP−τ\nmargin > ε   → bit=1\nmargin < −ε  → bit=0\n|margin|≤ε   → bit=None，邊界，不能算有效真值\n\n基準 τ=0、ε=10⁻¹⁰；不對每組輸入另調門檻或各自歸一化。')
body+=table('表 6｜兩個固定基準案例的完整判讀',['資料','P(out1)','P(out3)','ΔP','門檻 τ','bit','AND2 真值','五路總功率'],[
    (c['pattern'],fmt(c['result']['positive']['power']),fmt(c['result']['negative']['power']),fmt(c['result']['readout']['delta']),0,bit(c['result']['readout']['bit']),c['expected'],fmt(sum(c['result']['output_powers']))) for c in D['worked_cases']])
body+='''<p>1000 的兩個讀取埠都亮，但 out3 較強，所以判 0；1100 的 out1 較強，所以判 1。正負差分不等於亮／暗單埠判定。所有五路總功率分別仍是 10 與 11。</p><details><summary>進階：用一個 Hermitian 矩陣重算功率差</summary>'''
body+=pre('令 r+=U 的 out1 那一列，r−=U 的 out3 那一列\nQ = r+†r+ − r−†r−\nΔP = v†Qv\n\nQ 的非對角元素保留輸入間的干涉；\n此式是同一個功率差的代數重寫，不是另一套判讀規則。')
body+='''<p>注意外積中需要共軛；原本的 y=Uv 加權和不把 U 的列先取共軛。程式核對 Q=Q† 與 v†Qv 的結果。</p></details>'''
body+=table('表 7｜邊界示例：兩埠單位矩陣，τ=0、ε=10⁻¹⁰',['刻意設定的 ΔP','浮點實算 ΔP','結果'],[
    (f"{r['intended_delta']:.2e}",f"{r['actual_delta']:.3e}",bit(r['bit'])) for r in D['boundary_examples']])
body+='''<p>ε 是本模型的絕對數值容許，不是量測雜訊或錯誤率規格。即使門檻 0 的符號在共同縮放下保持，極小功率仍可能落入 ε 邊界；實際偵測器的雜訊、偏移與頻寬需另外建模。</p><figure><img src="figures/m1_s3/power_readout.png" alt="自項、干涉與實際功率比較，及參考相位對功率差的影響"><figcaption>圖 2｜左：兩個案例的功率分解。右：固定同一組 AND2 元件相位，只改輸入 R 的相位；基準是相位 0。這是理想穩態敏感度示範，未估計 BER 或實體控制容許範圍。</figcaption></figure>
<h2 id="run">6．學員執行與修改範例</h2>'''
body+=pre(r'''Set-Location -LiteralPath 'C:\EDA_Codex\Lab06b'
& .\scripts\run_m1_s3.ps1''')
body+='''<p>開啟 <a href="../config/m1_s3_example.json">m1_s3_example.json</a>。phase_setting 固定 AND2；本步只改輸入、參考光與讀取條件。</p><ol><li>先以 bits=[1,1,0,0]、R=3、所有輸入相位 0 重跑，對照表 3～6。</li><li>把 bits 改成 [1,0,0,0]，對照另一張手算表。</li><li>把 reference_phase_pi 改成 0.5，再改成 1；觀察複數貢獻、干涉項與 ΔP。</li><li>把相位還原 0，將 reference_amplitude 改成 0；再以同一個 U 計算。不要順便調整門檻。</li><li>另存自己的設定與結果，完成後還原基準。頁面顯示六位小數，正式判讀使用完整精度與 ε。</li></ol>'''
sample=D['student_example']['result']
body+=table('表 8｜目前學員設定的程式結果（與固定驗收案例分開）',['項目','結果'],[
    ('輸入場',escape(str(D['student_example']['config']['bits']))+f"；R={D['student_example']['config']['reference_amplitude']}"),
    ('y_out1 / y_out3',f'<code>{ztext(sample["positive"]["field"])}</code> / <code>{ztext(sample["negative"]["field"])}</code>'),
    ('P(out1) / P(out3)',fmt(sample['positive']['power'])+' / '+fmt(sample['negative']['power'])),
    ('ΔP / margin / bit',fmt(sample['readout']['delta'])+' / '+fmt(sample['readout']['margin'])+' / '+bit(sample['readout']['bit']))])
body+='''<h3>頁面互動：看每項貢獻如何改變</h3><section class="panel"><label for="read-pattern">資料 x1x2x3x4</label><select id="read-pattern"><option>0000</option><option>1000</option><option selected>1100</option><option>1111</option></select><label for="read-R">R 振幅：<b id="read-R-label">3.00</b></label><input id="read-R" type="range" min="0" max="4" step="0.01" value="3" style="width:100%"><label for="read-reference-phase">R 相位：<b id="read-reference-label">0.00 π</b></label><input id="read-reference-phase" type="range" min="0" max="2" step="0.01" value="0" style="width:100%"><label for="read-data-phase">x2 相位：<b id="read-data-label">0.00 π</b></label><input id="read-data-phase" type="range" min="0" max="2" step="0.01" value="0" style="width:100%"><label for="read-threshold">功率差門檻 τ（基準 0）</label><input id="read-threshold" type="number" step="any" value="0"><div id="read-live" class="answers" aria-live="polite"></div><div class="scroll"><table><caption>互動表｜各路複數貢獻</caption><thead><tr><th>來源</th><th>out1 貢獻</th><th>out3 貢獻</th></tr></thead><tbody id="read-terms"></tbody></table></div><p class="muted">使用本輪 U 的完整精度；資料與 R 共享固定功率刻度。此互動的 x1／x3／x4 相位固定 0、ε 固定 10⁻¹⁰。偏離基準後的 bit 是這組光場的判讀，不代表原 AND2 真值已重新驗收。</p></section>'''
body+='<script>const READOUT_U='+json.dumps(D['U'],ensure_ascii=False).replace('</',r'<\/')+';</script>'
body+='''<script>(()=>{const pattern=document.querySelector('#read-pattern'),R=document.querySelector('#read-R'),ref=document.querySelector('#read-reference-phase'),data=document.querySelector('#read-data-phase'),threshold=document.querySelector('#read-threshold');const mul=(a,b)=>[a[0]*b[0]-a[1]*b[1],a[0]*b[1]+a[1]*b[0]],abs2=z=>z[0]**2+z[1]**2,format=z=>z[0].toFixed(6)+(z[1]<0?'':'+')+z[1].toFixed(6)+'i';function explain(row,v){const terms=row.map((z,k)=>mul(z,v[k])),field=terms.reduce((s,z)=>[s[0]+z[0],s[1]+z[1]],[0,0]),self=terms.reduce((s,z)=>s+abs2(z),0);let interference=0;for(let j=0;j<5;j++)for(let k=j+1;k<5;k++)interference+=2*(terms[j][0]*terms[k][0]+terms[j][1]*terms[k][1]);return {terms,field,power:abs2(field),self,interference};}function show(){const tau=Number(threshold.value),box=document.querySelector('#read-live');if(threshold.value===''||!Number.isFinite(tau)){box.textContent='請輸入有限的門檻。';delete box.dataset.result;return;}const dp=Number(data.value)*Math.PI,rp=Number(ref.value)*Math.PI;let v=pattern.value.split('').map((b,k)=>k===1?[Number(b)*Math.cos(dp),Number(b)*Math.sin(dp)]:[Number(b),0]);v.push([Number(R.value)*Math.cos(rp),Number(R.value)*Math.sin(rp)]);const rows=READOUT_U.map(row=>explain(row,v)),plus=rows[1],minus=rows[3],powers=rows.map(r=>r.power),delta=plus.power-minus.power,margin=delta-tau,bit=Math.abs(margin)<=1e-10?null:Number(margin>0),result={plus,minus,powers,delta,margin,bit,selfDelta:plus.self-minus.self,interferenceDelta:plus.interference-minus.interference};box.dataset.result=JSON.stringify(result);box.replaceChildren();for(const text of ['y_out1='+format(plus.field)+' | P='+plus.power.toFixed(9),'y_out3='+format(minus.field)+' | P='+minus.power.toFixed(9),'ΔP='+delta.toFixed(9)+' | margin='+margin.toFixed(9)+' | bit='+(bit===null?'邊界':bit),'ΔP 自項='+result.selfDelta.toFixed(9)+' + 干涉項='+result.interferenceDelta.toFixed(9),'五路總功率='+powers.reduce((s,p)=>s+p,0).toFixed(9)]){const line=document.createElement('div');line.textContent=text;box.appendChild(line);}const tbody=document.querySelector('#read-terms');tbody.replaceChildren();['x1','x2','x3','x4','R'].forEach((name,k)=>{const tr=document.createElement('tr');for(const text of [name,format(plus.terms[k]),format(minus.terms[k])]){const td=document.createElement('td');td.textContent=text;tr.appendChild(td);}tbody.appendChild(tr);});document.querySelector('#read-R-label').textContent=Number(R.value).toFixed(2);document.querySelector('#read-reference-label').textContent=Number(ref.value).toFixed(2)+' π';document.querySelector('#read-data-label').textContent=Number(data.value).toFixed(2)+' π';}pattern.addEventListener('change',show);for(const x of [R,ref,data,threshold])x.addEventListener('input',show);show();})();</script>
<h2 id="checks">7．檢查結果與常見錯誤</h2>'''
body+=table('表 9｜本輪驗證',['檢查','結果','證據'],[
    ('本步單元測試',f"{D['unit_tests']['passed']}/{D['unit_tests']['run']}",'<a href="../work/m1_s3/out/unit_tests.log">加權和／干涉／Q／邊界測試 log</a>'),
    ('前步回歸',f'{reg_pass}/{reg_run}','M0 S3、M1 S1、M1 S2；完整 log 見 out/。'),
    ('固定手算案例','2/2 對應 0／1','重新組 U，完整複數和與矩陣乘法一致。'),
    ('功率及差分交叉核對','通過','P=自項+干涉項；ΔP=v†Qv；五路總功率守恆。')])
bad=D['controlled_calculation_errors']
body+=table('表 10｜刻意錯算的對照',['錯誤','本輪觀察'],[
    ('先加每項功率，漏掉干涉',f"1100 的錯誤 ΔP={bad[0]['value']:.6f}，正確為 {bad[0]['correct_delta']:.6f}；連符號都改變。"),
    ('拿振幅差當成功率差',f"1100 得到 {bad[1]['value']:.6f}；這與功率差 {bad[1]['correct_delta']:.6f} 是不同量。"),
    ('把 U 的列先取共軛',f"相位測例的場最大差 {bad[2]['field_max_error']:.6f}，但 ΔP 差僅 {bad[2]['delta_error']:.2e}；只看功率可能漏掉複數場錯誤。")])
body+='''<p>這些錯算另建結果，沒有修改正式模型。U 的共軛錯誤在某些實數或近共線係數案例中，功率可能看起來相同；所以測試使用獨立的複數算例，不能只靠兩個數位位元判斷計算正確。</p>
<h2 id="files">8．程式與可追溯檔案</h2>'''
body+=table('表 11｜本步檔案',['內容','入口'],[
    ('共用加權和／差分分析','<a href="../work/common/weighted_readout.py">weighted_readout.py</a>'),
    ('學員範例設定','<a href="../config/m1_s3_example.json">m1_s3_example.json</a>'),
    ('實驗與單元測試','<a href="../work/m1_s3/run_readout.py">run_readout.py</a> · <a href="../work/m1_s3/test_weighted_readout.py">test_weighted_readout.py</a>'),
    ('逐項貢獻／成對干涉','<a href="../work/m1_s3/out/weighted_terms.csv">20 筆貢獻 CSV</a> · <a href="../work/m1_s3/out/interference_pairs.csv">40 筆干涉項 CSV</a>'),
    ('摘要／完整證據','<a href="../work/m1_s3/out/readout_summary.csv">判讀 CSV</a> · <a href="../work/m1_s3/out/readout_results.json">JSON、版本與程式雜湊</a>')])
body+='''<h2 id="submit">9．學員驗收與交付</h2><ol><li>分別提交 1000／1100 的兩個讀取埠貢獻表、複數場和、功率、ΔP 與 bit。</li><li>指出 out1 與 out3 的正負干涉，解釋為何漏掉干涉會算錯。</li><li>說明固定門檻、ε 與邊界，並區分模平方、振幅差及功率差。</li><li>提交修改 R 相位前後的設定與結果；保留其他條件，完成後還原。</li><li>學員手算用自己的記錄提交，由講師另外驗收。</li></ol>
<section class="panel"><label for="read-name">學員姓名</label><input id="read-name"><label for="read-hand1000">1000 手算：兩個場、功率、ΔP、bit</label><textarea id="read-hand1000"></textarea><label for="read-hand1100">1100 手算：兩個場、功率、ΔP、bit</label><textarea id="read-hand1100"></textarea><label for="read-observations">干涉項、相位修改與邊界分析</label><textarea id="read-observations"></textarea><button id="read-generate">產生 M1 S3 學習記錄 JSON</button><textarea id="read-json" hidden readonly aria-label="M1 S3 學習記錄 JSON" style="min-height:220px"></textarea><p class="muted">複製保存到 learner/m1_s3_observations.json；<a href="../learner/m1_s3_observations.template.json">空白範本</a>。</p></section>
<script>document.querySelector('#read-generate').addEventListener('click',()=>{const box=document.querySelector('#read-json');box.hidden=false;box.value=JSON.stringify({step:'M1 S3',learner_name:document.querySelector('#read-name').value,hand_calculation_1000:document.querySelector('#read-hand1000').value,hand_calculation_1100:document.querySelector('#read-hand1100').value,observations:document.querySelector('#read-observations').value,date:new Date().toISOString(),instructor_review:'pending'},null,2);box.focus();box.select();});</script>
<p><b>下一步 M1 S4：</b>載入五種功能的已驗證相位，固定光路、編碼與判讀，跑完整 80 筆真值表，檢查最小有號裕量及未作用輸入。</p>'''
nav=''.join(f'<a href="{href}">{label}</a>' for href,label in [('../Lab06b_index.html','總覽與報告入口'),('plan.html','完整規劃'),('m1_s2.html','M1 S2｜B7 與矩陣'),('m1_s3.html','M1 S3｜加權和與判讀'),('#weighted','兩個手算案例'),('#power','功率與干涉項'),('#decision','功率差與邊界'),('#run','執行與互動預測'),('#checks','檢查與錯誤分析'),('#submit','學員交付')])
html=f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M1 S3｜複數加權和、光功率與差分判讀｜Lab06b</title><link rel="stylesheet" href="../assets/course.css"></head><body><header class="top"><a href="../Lab06b_index.html"><b>LAB06b</b>　PIC Chip 學員實作課程</a><small>2026-10-31 · M1 S3</small></header><div class="layout"><aside><strong>學習與實作入口</strong>{nav}<a href="../work/m1_s3/out/readout_results.json">本輪數值與測試 JSON</a><p class="muted">{state}<br>學員作答待提交</p></aside><main><button class="print" onclick="window.print()">列印／另存 PDF</button><div class="hero"><div class="eyebrow">MODULE 1 · STEP 3 · 60 MIN</div><h1>M1 S3｜複數加權和、光功率與差分判讀</h1><p class="lead">把每一路的複數貢獻攤開，手算兩個讀取埠，再用干涉項與固定門檻解釋 0／1 的來源。</p><span class="tag ok">{D['unit_tests']['passed']} 項本步測試</span><span class="tag">1000／1100 · R=3</span><span class="tag">場 → 功率 → ΔP → bit</span></div>{body}<footer>正式根目錄 C:\\EDA_Codex\\Lab06b · 2026-10-31（Asia/Taipei）。本步為理想穩態計算與舊相位回放；未加入新相位求解、PDK 或實體 Chip 驗證。</footer></main></div></body></html>'''
(ROOT/'course/m1_s3.html').write_text(clean_course_html(html),encoding='utf-8')
for relative in ['Lab06b_index.html','course/plan.html','course/m0_s1.html','course/m0_s1_foundation.html','course/m0_s2.html','course/m0_s3.html','course/m1_s1.html','course/m1_s2.html','analysis/lab01a_7_6.html','reference/source_context.html']:
    path=ROOT/relative;text=path.read_text(encoding='utf-8');prefix='../' if '/' in relative else ''
    href=prefix+'course/m1_s3.html'
    if f'href="{href}"' not in text:text=text.replace('</aside>',f'<a href="{href}">M1 S3｜加權和與判讀</a></aside>',1)
    if relative=='Lab06b_index.html':
        panel=f'<!-- M1S3:STATUS --><div class="callout good"><b>目前進度：</b>M0 三步與 M1 S1／S2 已建立；M1 S3：{state}。學員作答各自驗收。<a href="course/m1_s3.html">進入 M1 S3 →</a><br>本步核對兩個加權和案例；完整五功能 80 筆驗收接續 M1 S4。</div><!-- /M1S3:STATUS -->'
        text=re.sub(r'<!-- (?:M1S2|M1S3):STATUS -->.*?<!-- /(?:M1S2|M1S3):STATUS -->',lambda m:panel,text,count=1,flags=re.S)
        text=text.replace('S1 編碼、S2 B7 矩陣核心通過；S3–S5 待實作','S1 編碼、S2 矩陣、S3 加權和判讀核心通過；S4–S5 待實作')
        if '<td>M1 S3 主實作</td>' not in text:text=text.replace('<tr><td>理想 MZI 補充</td>','<tr><td>M1 S3 主實作</td><td><a href="course/m1_s3.html">複數加權和、光功率與差分判讀</a></td><td>本輪兩個手算案例、干涉分解與固定門檻</td></tr><tr><td>理想 MZI 補充</td>',1)
        card='<article class="card"><div class="num">M1 S3</div><h3>複數加權和與功率判讀</h3><p>手算 1000／1100，分解相干場、功率與干涉項，核對 ΔP。</p><a href="course/m1_s3.html">進入本步 →</a></article>'
        text=re.sub(r'<!-- M1S2:CARD -->.*?<!-- /M1S2:CARD -->',lambda m:'<!-- M1S3:CARD -->'+card+'<!-- /M1S3:CARD -->',text,flags=re.S)
        text=text.replace('M0 三步與 M1 S1／S2 核心已實算','M0 三步與 M1 S1～S3 核心已實算')
    if relative=='course/plan.html':text=text.replace('<td>M1 s3<br>1 h</td>','<td><a href="m1_s3.html">M1 s3</a><br>1 h</td>')
    path.write_text(text,encoding='utf-8')
CFG['progress']['M1_S3']='weighted complex sums and differential readout passed; learner submission pending' if D['core_passed'] else 'readout checks unresolved'
CFG['progress']['M1_S4']='next step: five phase programs, 80 truth cases and signed margins'
(ROOT/'config/course.json').write_text(json.dumps(CFG,ensure_ascii=False,indent=2),encoding='utf-8')
readme=(ROOT/'README_Lab06b_Course.md').read_text(encoding='utf-8').replace('下一步 M1 S3：複數加權和、光功率與差分判讀。','M1 S3：scripts/run_m1_s3.ps1；複數加權和、干涉分解與差分判讀。\n下一步 M1 S4：五種功能與完整 80 筆真值驗收。')
(ROOT/'README_Lab06b_Course.md').write_text(readme,encoding='utf-8')
print('M1 S3 page rendered; core:',D['core_passed'])
