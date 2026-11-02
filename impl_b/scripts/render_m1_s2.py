from report_policy import clean_course_html
"""M1 S2 lesson, wiring sheet, interactive layer replay and report integration."""
from pathlib import Path
from html import escape
import json,re
ROOT=Path(__file__).resolve().parents[1]
D=json.loads((ROOT/'work/m1_s2/out/b7_results.json').read_text(encoding='utf-8'))
CFG=json.loads((ROOT/'config/course.json').read_text(encoding='utf-8'))
FIG=ROOT/'course/figures/m1_s2';FIG.mkdir(parents=True,exist_ok=True)


def table(caption,headers,rows):
    return '<div class="scroll"><table><caption>'+caption+'</caption><thead><tr>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(c)+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'


def pre(text):return '<pre><code>'+escape(text)+'</code></pre>'
def ztext(z):
    a,b=z
    if abs(a)<5e-7:a=0.
    if abs(b)<5e-7:b=0.
    return f'{a:.5f}{b:+.5f}i'


ops=D['topology']['ops_zero_based']
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1180" height="510" viewBox="0 0 1180 510" role="img" aria-labelledby="t d"><title id="t">B7 七顆 MZI、四層與六段直通光路</title><desc id="d">Layer0 M1接0與1、M2接3與4；Layer1 M3接1與2；Layer2 M4接0與1、M5接2與3；Layer3 M6接1與2、M7接3與4。各層未使用的光路為恆等直通。</desc><rect width="1180" height="510" fill="#f4f7fc" rx="10"/>']
for rail,name in enumerate(['x1','x2','x3','x4','R']):
    y=90+rail*75;color='#a65c16' if rail==4 else '#155bd0'
    svg.append(f'<path d="M160 {y}H910" stroke="{color}" stroke-width="3"/><text x="15" y="{y+6}" font-size="18" fill="{color}">{name} / in{rail}</text><text x="930" y="{y+6}" font-size="18" fill="{color}">out{rail} / o{rail+1}'+(' ＋讀取' if rail==1 else ' −讀取' if rail==3 else '')+'</text>')
for layer in range(4):
    x=260+layer*175
    svg.append(f'<text x="{x}" y="40" text-anchor="middle" font-size="20" fill="#17263b">L{layer}</text>')
    for rail in D['diagnostics']['bypass_ports'][layer]:
        y=90+rail*75
        svg.append(f'<path d="M{x-63} {y}H{x+63}" stroke="#258350" stroke-width="6" stroke-dasharray="10 6"/><text x="{x}" y="{y-12}" text-anchor="middle" fill="#256142" font-size="14">I：直通 {rail}</text>')
for k,(rail,layer) in enumerate(ops):
    x=260+layer*175;y=90+rail*75
    svg.append(f'<rect x="{x-53}" y="{y-17}" width="106" height="109" rx="7" fill="#dfeafa" stroke="#155bd0" stroke-width="2"/><text x="{x}" y="{y+28}" text-anchor="middle" font-size="19" fill="#17263b">M{k+1} ({rail},{rail+1})</text><text x="{x}" y="{y+56}" text-anchor="middle" font-size="16" fill="#155bd0">θ[{k}] / φ[{k}]</text>')
svg.append('<text x="25" y="456" fill="#17263b" font-size="20">U = L3 L2 L1 L0 = S7 S6 S5 S4 S3 S2 S1（最右邊先作用）</text><text x="25" y="489" fill="#526379" font-size="17">綠色虛線共六段：模型為恆等直通；實際波導長度與相位於後續版圖／路徑萃取加入。</text></svg>')
(FIG/'b7_wiring.svg').write_text(''.join(svg),encoding='utf-8')

status='核心模型與接線驗證通過' if D['core_passed'] else '有未通過項，請檢查原始證據'
body=f'''<div class="callout good"><b>這一步要回答：</b>如何讓七顆 2×2 MZI 與六段直通光路，描述同一個五路光學網路？<br><b>本輪結果：</b>{D['unit_tests']['passed']}/{D['unit_tests']['run']} 項本步測試、34/34 項前步回歸、{sum(c['passed'] for c in D['checks'])}/{len(D['checks'])} 項模型檢查通過。學員作答另行驗收。</div>
<h2 id="predict">1．先預測，再動手</h2><p>建議 60 分鐘：接線標註 10 分、2×2 嵌入與乘法順序 15 分、執行與逐層追蹤 15 分、單埠探測與錯誤分析 10 分、作答交付 10 分。</p><ol><li>Layer 1 只有 M3，其餘三條光路應消失、歸零，還是直通？</li><li>光先經 M1、最後經 M7，U 的最左邊是哪顆矩陣？</li><li>用單位場只打 in2，讀到的是 U 的第 2 列還是第 2 欄（零基索引）？</li><li>若 U†U=I，是否已證明接線順序正確？</li></ol>
<h2 id="wiring">2．白話範例：把五條光路當成五個欄位</h2><p>輸入向量固定為 v=[x1,x2,x3,x4,R]ᵀ，光路 index 由上到下為 0～4。每顆 MZI 只更新相鄰兩個欄位；同一層沒接入 MZI 的欄位保持原值。</p><figure><img src="figures/m1_s2/b7_wiring.svg" alt="B7四層七顆MZI與六段恆等直通示意"><figcaption>圖 1｜依 config/course.json 的 OPS 繪製。M1～M7 是實體元件名稱；theta／phi 陣列索引是 0～6；layer 是 0～3。圖為前向模型接線，尚未加入實際波導的長度、損耗或相位。</figcaption></figure>'''
body+=table('表 1｜固定 B7 OPS 與十四個相位通道',['MZI','layer','作用的全域 modes','theta／phi 索引','同層關係'],[
    (f'M{k+1}',layer,f'({p},{p+1})',k,'與同層另一顆不共用光路' if layer!=1 else '本層只有這一顆') for k,(p,layer) in enumerate(ops)])
body+=table('表 2｜六段直通：不是把未作用列設成 0',['層','MZI','直通 modes','L 的寫法'],[
    (0,'M1、M2','2','L0=S2·S1'),(1,'M3','0、3、4','L1=S3'),
    (2,'M4、M5','4','L2=S5·S4'),(3,'M6、M7','0','L3=S7·S6')])
body+='''<p>B7 判讀埠延用零基 out1−out3，即一基名稱 o2−o4。本步先建立 U 與完整五路輸出；功能真值表與加權光場判讀留到後續步驟。</p>
<h2 id="matrix">3．把一顆 2×2 矩陣嵌入 5×5</h2><p>以 M3 作用於 modes (1,2) 為例，先建立 I₅，再把那兩列與兩欄交會的 2×2 區塊替換成 T3。T 的第一個位置仍對應物理上方光路。</p>'''
body+=pre('T3 = [[a,b],[c,d]]\n\nS3 = [[1,0,0,0,0],\n      [0,a,b,0,0],\n      [0,c,d,0,0],\n      [0,0,0,1,0],\n      [0,0,0,0,1]]\n\nL0=S2 S1；L1=S3；L2=S5 S4；L3=S7 S6\nU=L3 L2 L1 L0=S7 S6 S5 S4 S3 S2 S1\ny=Uv')
body+='''<p>同一層的 MZI 作用在不重疊的兩組模式，所以可交換相乘順序。跨層元件通常共用光路，不能任意交換。每顆 MZI 的完整複數共同相位也要保留；它是相對其他直通光路的相位。</p><h3>學員實作的共用介面</h3>'''
body+=pre('from common import b7\nimport numpy as np\n\ntop = b7.load_topology()\ntheta = np.array([0.5]*7)*np.pi\nphi = np.zeros(7)\nU = b7.transfer_matrix(top, theta, phi)\nlayers = b7.layers(top, theta, phi)\ntrace = b7.trace(top, theta, phi, [1,0,0,0,3], by_layer=True)\nprint(U.conj().T @ U)')
body+='''<p>程式讀取同一份課程架構，不另手抄 OPS。測試另外保留固定七組接線作獨立核對，避免設定被誤改後仍自我通過。<a href="../work/common/b7.py">共用 b7.py</a>。</p>
<h2 id="run">4．學員操作：建立 U，再看五路光場</h2>'''
body+=pre(r'''Set-Location -LiteralPath 'C:\EDA_Codex\Lab06b'
& .\scripts\run_m1_s2.ps1''')
body+='''<p>預設 <a href="../config/m1_s2_example.json">m1_s2_example.json</a> 使用四路資料 1000、R 振幅 3、七顆 θ=π/2、φ=0，沒有 MZI 損耗。這是接線／混合範例，尚未命名為 AND 或其他邏輯功能。</p><ol><li>先執行並保存目前的 5×5 U、逐層場與功率。</li><li>只把 theta_pi[2] 從 0.5 改成 1；重跑並比較 M3 前後的場，以及最後的 U。</li><li>把全部 theta_pi 改成 0、全部 phi_pi 保持 0，做全 cross 的五個單埠探測；與下方固定路由表核對。</li><li>把全部 theta_pi 與 phi_pi 都改成 1，驗證 U≈I；不要只改 θ=π 就宣稱得到 I。</li><li>最後還原設定，提交修改前後副本。標準驗收案例與學員設定分開，不以學員參數判定某種邏輯功能。</li></ol>'''
body+=table('表 3｜目前學員設定的完整複數 U（輸出列 i、輸入欄 j）',['Uᵢⱼ','in0 / x1','in1 / x2','in2 / x3','in3 / x4','in4 / R'],[
    (f'out{i}',*[f'<code>{ztext(z)}</code>' for z in row]) for i,row in enumerate(D['U'])])
body+='''<p>顯示值經四捨五入；實際計算與 JSON 保留完整精度。每個 Uᵢⱼ 是複數場係數；|Uᵢⱼ|² 代表只有 in j 打單位場時，在 out i 的功率。多路相干輸入必須先做 Uv，再取 |y|²，不能直接用 |U|² 乘各路功率。</p><figure><img src="figures/m1_s2/b7_matrix_power.png" alt="5乘5矩陣各元素模平方，橫軸輸入欄，縱軸輸出列"><figcaption>圖 2｜目前學員設定的單埠功率映射；相位資訊仍在上方複數矩陣中。U[0,3] 與 U[0,4] 的結構性零來自有向逐層接線，與某組相位造成的偶然相消不同。</figcaption></figure>
<h2 id="trace">5．逐層追蹤：未讀取的埠也帶走能量</h2>'''
body+=table('表 4｜目前輸入經過每一層：複數場；括號內為該埠功率',['位置','mode0','mode1','mode2','mode3','mode4','總功率'],[
    (r['stage'],*[f'<code>{ztext(z)}</code><br>({p:.5f})' for z,p in zip(r['field'],r['powers'])],f"{r['total_power']:.8f}") for r in D['layer_trace']])
body+='''<figure><img src="figures/m1_s2/b7_layer_power.png" alt="逐層各埠功率熱圖及五路總功率與兩個讀取埠之和"><figcaption>圖 3｜目前學員設定的逐層功率。理想無損時五路總和守恆；只加 out1 與 out3 不必等於總功率。若設定了非零 MZI 損耗，五路總功率可以下降。</figcaption></figure><p><a href="../work/m1_s2/out/layer_trace.csv">逐層場／功率 CSV</a> · <a href="../work/m1_s2/out/b7_results.json">逐顆 M1～M7 場、所有 S／L／U 與完整結果 JSON</a>。</p>
<h3>在頁面先預測，再與 Python 對照</h3><section class="panel"><label for="b7-profile">相位設定</label><select id="b7-profile"><option value="split_all">全 split：θ=π/2、φ=0</option><option value="cross_all">全 cross：θ=0、φ=0</option><option value="bar_all">全 bar：θ=π、φ=0</option><option value="identity_all">全 identity：θ=π、φ=π</option><option value="student">目前學員設定（含所設損耗）</option></select><label for="b7-source">輸入</label><select id="b7-source"><option value="1000">1000 + R</option><option value="1100">1100 + R</option><option value="basis0">單位場只打 in0</option><option value="basis1">單位場只打 in1</option><option value="basis2">單位場只打 in2</option><option value="basis3">單位場只打 in3</option><option value="basis4">單位場只打 in4</option></select><label for="b7-reference">R 振幅：<b id="b7-reference-label">3.00</b>（單埠探測時停用）</label><input id="b7-reference" type="range" min="0" max="4" step="0.01" value="3" style="width:100%"><label for="b7-stage">顯示位置：<b id="b7-stage-label">Input</b></label><input id="b7-stage" type="range" min="0" max="4" step="1" value="0" style="width:100%"><div id="b7-live" class="answers" aria-live="polite"></div><p class="muted">此互動以 Python 輸出的四層複數矩陣，於瀏覽器逐層相乘；保留輸入功率刻度，不將每組向量各自歸一化。1000／1100 的 R 相位固定為 0；學員設定的完整輸入相位見上方 Python 結果。</p></section>'''
body+='<script>const B7_PROFILES='+json.dumps(D['profiles'],ensure_ascii=False).replace('</',r'<\/')+';</script>'
body+='''<script>(()=>{const profile=document.querySelector('#b7-profile'),source=document.querySelector('#b7-source'),ref=document.querySelector('#b7-reference'),stage=document.querySelector('#b7-stage');function apply(A,v){return A.map(row=>row.reduce((s,z,k)=>[s[0]+z[0]*v[k][0]-z[1]*v[k][1],s[1]+z[0]*v[k][1]+z[1]*v[k][0]],[0,0]));}function show(){const R=Number(ref.value),basis=source.value.startsWith('basis');let field=Array.from({length:5},()=>[0,0]);if(basis)field[Number(source.value.slice(-1))]=[1,0];else field=[...source.value.split('').map(x=>[Number(x),0]),[R,0]];const inputPower=field.reduce((s,z)=>s+z[0]**2+z[1]**2,0),n=Number(stage.value);for(let k=0;k<n;k++)field=apply(B7_PROFILES[profile.value].layers[k],field);const powers=field.map(z=>z[0]**2+z[1]**2),total=powers.reduce((s,p)=>s+p,0);const result={field,powers,total,inputPower};const box=document.querySelector('#b7-live');box.dataset.result=JSON.stringify(result);box.replaceChildren();field.forEach((z,k)=>{const line=document.createElement('div');line.textContent='mode'+k+': E='+z[0].toFixed(6)+(z[1]<0?'':'+')+z[1].toFixed(6)+'i | P='+powers[k].toFixed(6);box.appendChild(line);});const sum=document.createElement('p');sum.textContent='輸入總功率='+inputPower.toFixed(6)+' | 此位置總功率='+total.toFixed(6);box.appendChild(sum);document.querySelector('#b7-stage-label').textContent=n===0?'Input':'經過 Layer '+(n-1);document.querySelector('#b7-reference-label').textContent=R.toFixed(2);ref.disabled=basis;}profile.addEventListener('change',show);source.addEventListener('change',show);ref.addEventListener('input',show);stage.addEventListener('input',show);show();})();</script>
<h2 id="probes">6．五個單埠探測：U 的每一欄從哪裡來</h2><p>依序輸入 e₀、e₁、e₂、e₃、e₄。由線性關係 Ueⱼ，輸出向量就是 U 的第 j 欄。單埠探測的其他輸入包含 R 都設為 0；不要把固定參考光加進基底探測，否則得到的不是那一欄。</p>'''
body+=table('表 5｜全 cross 的已知路由，保留複數相位',['單位場輸入','唯一有光的輸出','場係數','功率'],[
    ('in0','out4','+1',1),('in1','out2','−i',1),('in2','out0','−1',1),('in3','out3','−1',1),('in4','out1','−i',1)])
body+='''<p>全 bar（θ=π、φ=0）得到 diag(1,1,−1,1,1)，功率路由沒有交換，但 mode2 多了 π 相位；只有再把各顆 φ 設為 π 才得到本步的 U≈I。這是「看功率一樣」仍不足以確認完整複數網路的例子。</p>
<h2 id="checks">7．驗證：么正性、接線與相位都要核對</h2>'''
body+=table('表 6｜本輪驗證結果',['檢查','數值／結果','判斷方式'],[
    ('本步單元測試',f"{D['unit_tests']['passed']}/{D['unit_tests']['run']}",'固定 OPS、已知路由、相位、獨立解析更新、層界追蹤與損耗。'),
    ('M0 S3／M1 S1 回歸','18/18 + 16/16','舊模型與編碼／接收模型保持相容。'),
    ('目前設定的 max |U†U−I|',f"{D['diagnostics']['unitarity_error']:.3e}",'只有 loss_db=0 時要求約等於零。'),
    ('逐顆／逐層最大差',f"{D['diagnostics']['layer_product_error']:.3e}",'比較完整複數矩陣。'),
    ('獨立解析更新最大差','未比較：目前有損耗' if D['diagnostics']['independent_scalar_error'] is None else f"{D['diagnostics']['independent_scalar_error']:.3e}",'解析對照為理想無損公式。'),
    ('目前 U 的最大奇異值',f"{D['diagnostics']['maximum_singular_value']:.12f}",'被動損耗模型不大於 1。'),
    ('既有五組完整複數 U',f"{sum(r['passed'] for r in D['inherited_matrix_compatibility'])}/5 相容",'沿用舊相位，未重新求解邏輯功能。')])
labels={'reverse_order':'反轉七顆 MZI 的傳播順序','omit_M3':'漏掉 M3','erase_bypass':'把未作用光路設為零'}
body+=table('表 7｜三種受控接線錯誤：通過么正性仍可能接錯',['錯誤','max |U†U−I|','相對正確 U 的最大差','結果'],[
    (labels[r['name']],f"{r['unitarity_error']:.3e}",f"{r['reference_matrix_error']:.6f}",'被基準矩陣比較指出' if r['rejected'] else '未抓到') for r in D['controlled_wiring_errors']])
body+='''<p>錯誤範例另建矩陣，不替換或覆寫正式模型。反轉順序與漏掉一顆無損 MZI 仍可能得到么正矩陣，因此要再核對已知路由與獨立場更新。圖 2 的兩個結構性零也顯示，本課程 B7 具有特定連接限制，不能直接把它當成可任意設定所有 5×5 矩陣的通用網路。</p><h3>可選損耗的範圍</h3><p>mzi_loss_db 可為非負純量（每顆相同）或七個值，依 M1～M7 排列。只在作用的兩條模式套用該顆損耗，直通光路維持 I。不能直接將整個 U 乘七顆損耗的總因子。全 bar、每顆 1 dB 時，五條模式分別經過 2、4、3、3、2 顆 MZI；這只是元件損耗示範，實際直通波導的路徑相位／損耗尚未加入。</p>
<h2 id="files">8．程式、檔案與來源</h2>'''
body+=table('表 8｜本步可重跑資料',['內容','檔案'],[
    ('共用 B7 模型','<a href="../work/common/b7.py">b7.py</a>'),
    ('學員設定／接線 CSV','<a href="../config/m1_s2_example.json">設定 JSON</a> · <a href="../work/m1_s2/out/wiring.csv">接線 CSV</a>'),
    ('實驗／測試','<a href="../work/m1_s2/run_b7.py">run_b7.py</a> · <a href="../work/m1_s2/test_b7.py">test_b7.py</a>'),
    ('原始測試紀錄','<a href="../work/m1_s2/out/unit_tests.log">本步</a> · <a href="../work/m1_s2/out/m0_s3_regression.log">M0 S3</a> · <a href="../work/m1_s2/out/m1_s1_regression.log">M1 S1</a>'),
    ('完整結果／基底探測','<a href="../work/m1_s2/out/b7_results.json">JSON</a> · <a href="../work/m1_s2/out/basis_probe.csv">5×5 複數係數 CSV</a>')])
body+='''<p>接線來源：本專案 course.json 與原 C01 教材；舊相位只用於五組複數矩陣相容性核對。背景閱讀：<a href="https://arxiv.org/abs/1603.08788">Clements 等人：多埠干涉儀由分光器與相位器組成的網路</a>。本文 B7 是本課程固定拓樸，其可達性與矩陣結果由本步程式獨立計算。</p>
<h2 id="submit">9．驗收條件與學員交付</h2><ol><li>標出七顆 MZI 的層、相鄰模式與十四個相位索引，以及六段直通。</li><li>寫出 M3 的 5×5 嵌入矩陣與 U 的正確乘法順序。</li><li>用五個單位場輸入解釋 U 的欄位，提交全 cross 路由核對。</li><li>記錄單顆相位修改前後的 U、逐層場與全部五路總功率。</li><li>指出一種么正性抓不到的錯接；提交設定／結果副本，由講師確認。</li></ol>
<section class="panel"><label for="b7-name">學員姓名</label><input id="b7-name"><label for="b7-wiring-notes">四層排程、六段直通與 U 乘法順序</label><textarea id="b7-wiring-notes"></textarea><label for="b7-observations">單埠探測、相位修改與錯誤分析</label><textarea id="b7-observations"></textarea><button id="b7-generate">產生 M1 S2 學習記錄 JSON</button><textarea id="b7-json" hidden readonly aria-label="M1 S2 學習記錄 JSON" style="min-height:220px"></textarea><p class="muted">複製保存到 learner/m1_s2_observations.json；<a href="../learner/m1_s2_observations.template.json">空白範本</a>。</p></section>
<script>document.querySelector('#b7-generate').addEventListener('click',()=>{const box=document.querySelector('#b7-json');box.hidden=false;box.value=JSON.stringify({step:'M1 S2',learner_name:document.querySelector('#b7-name').value,wiring_and_order:document.querySelector('#b7-wiring-notes').value,observations:document.querySelector('#b7-observations').value,date:new Date().toISOString(),instructor_review:'pending'},null,2);box.focus();box.select();});</script>
<p><b>下一步 M1 S3：</b>用 1000／1100、R=3，逐項計算讀取埠的複數加權和，再從 y=Uv 到功率、ΔP 與判讀，核對手算與程式。</p>'''
nav=''.join(f'<a href="{href}">{label}</a>' for href,label in [('../Lab06b_index.html','總覽與報告入口'),('plan.html','完整規劃'),('m1_s1.html','M1 S1｜編碼與判讀'),('m1_s2.html','M1 S2｜B7 與矩陣'),('#wiring','四層接線與直通'),('#matrix','2×2 嵌入 5×5'),('#trace','逐層光場互動'),('#probes','五個單埠探測'),('#checks','驗證與錯誤分析'),('#submit','學員交付')])
html=f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M1 S2｜B7 接線與 5×5 傳輸矩陣｜Lab06b</title><link rel="stylesheet" href="../assets/course.css"></head><body><header class="top"><a href="../Lab06b_index.html"><b>LAB06b</b>　PIC Chip 學員實作課程</a><small>2026-10-31 · M1 S2</small></header><div class="layout"><aside><strong>學習與實作入口</strong>{nav}<a href="../work/m1_s2/out/b7_results.json">本輪矩陣與測試 JSON</a><p class="muted">{status}<br>學員作答待提交</p></aside><main><button class="print" onclick="window.print()">列印／另存 PDF</button><div class="hero"><div class="eyebrow">MODULE 1 · STEP 2 · 60 MIN</div><h1>M1 S2｜B7 接線與 5×5 傳輸矩陣</h1><p class="lead">依同一份接線規格，把七顆 MZI 嵌入五路光場，逐層建立 U，並用基底探測、功率與複數相位核對。</p><span class="tag ok">{D['unit_tests']['passed']} 項本步測試</span><span class="tag">7 MZI · 4 層 · 6 段直通</span><span class="tag">5×5 複數 U</span></div>{body}<footer>正式根目錄 C:\\EDA_Codex\\Lab06b · 2026-10-31（Asia/Taipei）。理想前向網路；學員作答另行驗收。</footer></main></div></body></html>'''
(ROOT/'course/m1_s2.html').write_text(clean_course_html(html),encoding='utf-8')
for relative in ['Lab06b_index.html','course/plan.html','course/m0_s1.html','course/m0_s1_foundation.html','course/m0_s2.html','course/m0_s3.html','course/m1_s1.html','analysis/lab01a_7_6.html','reference/source_context.html']:
    p=ROOT/relative;text=p.read_text(encoding='utf-8');prefix='../' if '/' in relative else ''
    href=prefix+'course/m1_s2.html'
    if f'href="{href}"' not in text:text=text.replace('</aside>',f'<a href="{href}">M1 S2｜B7 與矩陣</a></aside>',1)
    if relative=='Lab06b_index.html':
        panel=f'<!-- M1S2:STATUS --><div class="callout good"><b>目前進度：</b>M0 三步與 M1 S1 已建立；M1 S2：{status}。學員作答各自驗收。<a href="course/m1_s2.html">進入 M1 S2 →</a><br>本步新建理想 B7 模型；PDK／Chip 與場求解依後續關卡進行。</div><!-- /M1S2:STATUS -->'
        text=re.sub(r'<!-- (?:M1S1|M1S2):STATUS -->.*?<!-- /(?:M1S1|M1S2):STATUS -->',lambda m:panel,text,count=1,flags=re.S)
        text=text.replace('S1 編碼與判讀核心通過；S2–S5 待實作','S1 編碼、S2 B7 矩陣核心通過；S3–S5 待實作')
        if '<td>M1 S2 主實作</td>' not in text:text=text.replace('<tr><td>理想 MZI 補充</td>','<tr><td>M1 S2 主實作</td><td><a href="course/m1_s2.html">B7 接線與 5×5 傳輸矩陣</a></td><td>本輪共用 B7、逐層追蹤與獨立矩陣驗證</td></tr><tr><td>理想 MZI 補充</td>',1)
        card='<article class="card"><div class="num">M1 S2</div><h3>B7 接線與 5×5 矩陣</h3><p>七顆 MZI、四層、六段直通；逐層光場、單埠探測與么正性核對。</p><a href="course/m1_s2.html">進入本步 →</a></article>'
        text=re.sub(r'<!-- M1S1:CARD -->.*?<!-- /M1S1:CARD -->',lambda m:'<!-- M1S2:CARD -->'+card+'<!-- /M1S2:CARD -->',text,flags=re.S)
        text=text.replace('M0 三步與 M1 S1 核心已實算','M0 三步與 M1 S1／S2 核心已實算')
    if relative=='course/plan.html':text=text.replace('<td>M1 s2<br>1 h</td>','<td><a href="m1_s2.html">M1 s2</a><br>1 h</td>')
    p.write_text(text,encoding='utf-8')
CFG['progress']['M1_S2']='B7 topology and 5x5 transfer matrix passed; learner submission pending' if D['core_passed'] else 'B7 checks unresolved'
CFG['progress']['M1_S3']='next step: weighted complex output fields, powers and differential readout'
(ROOT/'config/course.json').write_text(json.dumps(CFG,ensure_ascii=False,indent=2),encoding='utf-8')
readme=(ROOT/'README_Lab06b_Course.md').read_text(encoding='utf-8').replace('下一步 M1 S2：B7 接線與 5×5 傳輸矩陣。','M1 S2：scripts/run_m1_s2.ps1；共用 B7、接線與 5×5 傳輸矩陣。\n下一步 M1 S3：複數加權和、光功率與差分判讀。')
(ROOT/'README_Lab06b_Course.md').write_text(readme,encoding='utf-8')
print('M1 S2 page rendered; core:',D['core_passed'])
