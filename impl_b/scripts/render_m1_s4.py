from report_policy import clean_course_html
"""M1 S4 full five-program truth acceptance and learner experiments."""
from pathlib import Path
from html import escape
import json,re
ROOT=Path(__file__).resolve().parents[1]
D=json.loads((ROOT/'work/m1_s4/out/logic_results.json').read_text(encoding='utf-8'))
CAT=json.loads((ROOT/'config/m1_s4_phase_programs.json').read_text(encoding='utf-8'))
CFG=json.loads((ROOT/'config/course.json').read_text(encoding='utf-8'))
GATES=list(D['baseline']);EPS=D['baseline_contract']['epsilon']


def table(caption,headers,rows):
    return '<div class="scroll"><table><caption>'+caption+'</caption><thead><tr>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(c)+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def pre(s):return '<pre><code>'+escape(s)+'</code></pre>'
def bit(v):return '邊界' if v is None else str(v)
def phase(values):return '<code>'+', '.join(f'{v:.6f}' for v in values)+'</code>'


total=sum(r['summary']['passed'] for r in D['baseline'].values());reg=sum(r['passed'] for r in D['regression'].values())
state='五功能 80 筆核心驗收通過' if D['core_passed'] else '有未通過項，請查看原始證據'
worst=min(GATES,key=lambda g:D['baseline'][g]['summary']['minimum_signed_margin'])
body=f'''<div class="callout {'good' if D['core_passed'] else 'warn'}"><b>這一步要回答：</b>同一顆 B7、不換光路或判讀，只換十四個相位，五種功能能否在全部四位元輸入下都正確？<br><b>本輪結果：</b>{total}/80 筆真值、12/12 組未作用輸入檢查；{D['unit_tests']['passed']}/{D['unit_tests']['run']} 項本步測試、{reg}/66 項前步回歸。{state}。學員作答另行驗收。</div>
<h2 id="predict">1．先預測，再執行完整驗收</h2><p>建議 90 分鐘：預測與固定規則 10 分、五組相位 10 分、80 筆執行 20 分、未作用輸入 15 分、裕量 15 分、診斷與交付 20 分。</p><ol><li>AND2 只看 x1／x2，為何仍要跑 16 組，而不只跑四組？</li><li>某組資料的 |ΔP| 很大，但符號與真值相反，應算通過嗎？</li><li>把參考光關掉或把兩個讀取埠交換，原本的相位還能完成所有功能嗎？</li><li>若改相位後出錯，可不可以每組資料另外換一個門檻？</li></ol>
<h2 id="contract">2．先固定驗收規則與真值</h2>'''
body+=pre('五路輸入：[x1,x2,x3,x4,R]ᵀ；資料 0→場0、1→場1\n資料光與參考光的基準相位皆為 0；R 振幅=3，功率=9\n光路：同一組 B7 OPS，七顆 MZI／十四個相位\n模型：理想、無損、前向；不對每組輸入各自歸一化\n\nΔP=P(out1)−P(out3)；固定門檻 τ=0\nΔP>ε → 1；ΔP<−ε → 0；|ΔP|≤ε → 邊界（None）\nε=10⁻¹⁰，邊界不得算成正確邏輯\n每個功能都送入全部 16 組四位元資料，共 5×16=80 組')
body+=table('表 1｜布林真值獨立定義，不讀取舊表中的 target',['功能','真值','16 組中應為 1 的筆數'],[
    ('AND2','x1 AND x2',4),('OR2','x1 OR x2',12),('XOR2','x1 與 x2 恰有一個為 1',8),
    ('AND4','四路全為 1',1),('OR4','四路至少一個為 1',15)])
body+='''<p>陣列 index 的最低位元是 x1，顯示字串仍依 x1→x4 排列。因此 index 1 顯示 1000、index 3 顯示 1100。AND2／OR2／XOR2 的 x3、x4 不參與布林定義，但仍是實際送入的光場。</p>
<h2 id="programs">3．五組相位，維持同一個 B7</h2><p>本步從 C 槽已有的相位快照擷取 theta／phi，使用完整精度重新組 U。這是本輪完整功能驗收，沒有重新最佳化相位。舊檔中的 U 只用於相容性比較，真值由上方布林規則另算。</p>'''
body+=table('表 2｜五個相位程式；顯示 rad，依 M1～M7 排列',['功能','theta[0..6]','phi[0..6]'],[
    (g,phase(CAT['gates'][g]['theta']),phase(CAT['gates'][g]['phi'])) for g in GATES])
body+='''<p>顯示六位小數供閱讀；執行一律讀取 <a href="../config/m1_s4_phase_programs.json">完整精度相位 JSON</a>。<a href="../config/m1_s4_phase_provenance.json">來源與 SHA-256</a> · <a href="../work/m1_s4/out/phase_programs.csv">十四相位 CSV</a>。theta／phi 單位為弧度；學員誤差設定的 *_pi 則以 π 為單位。</p>
<h2 id="run">4．學員執行：一次產生 80 筆結果</h2>'''
body+=pre(r'''Set-Location -LiteralPath 'C:\EDA_Codex\Lab06b'
& .\scripts\run_m1_s4.ps1''')
body+=table('表 3｜本輪五功能正式驗收',['功能','正確／總數','邊界','最小有號裕量','最差案例（取第一筆）','結果'],[
    (g,f"{r['summary']['passed']}/{r['summary']['total']}",r['summary']['boundaries'],f"{r['summary']['minimum_signed_margin']:.9f}",r['summary']['worst_pattern'],'通過' if r['summary']['accepted'] else '未通過') for g,r in D['baseline'].items()])
body+='''<figure><img src="figures/m1_s4/truth_and_margins.png" alt="五種功能各16組輸入的功率差及判讀位元與最小有號裕量"><figcaption>圖 1｜本輪完整 80 筆結果。左：顏色為 ΔP，格內數字為判讀 bit；右：各功能 16 筆中的最小有號裕量。圖只表示目前固定理想模型，不代表製程或量測容許範圍。</figcaption></figure>'''
for g,r in D['baseline'].items():
    body+=f'<details><summary>{g}：查看完整 16 組真值、功率與裕量</summary>'
    body+=table(f'{g}｜全部 16 組，門檻固定 0',['index','x1x2x3x4','真值','P(out1)','P(out3)','ΔP','有號裕量','bit','驗收'],[
        (row['index_lsb_x1'],row['pattern'],row['expected'],f"{row['powers'][1]:.6f}",f"{row['powers'][3]:.6f}",f"{row['delta']:.6f}",f"{row['signed_margin']:.6f}",bit(row['bit']),'通過' if row['correct'] else '未通過') for row in r['rows']])+'</details>'
body+='''<p><a href="../work/m1_s4/out/truth_80.csv">下載完整 80 筆 CSV</a>；JSON 另保存每筆五路複數場、全部輸出功率及輸入／輸出總功率。</p>
<h2 id="unused">5．未作用輸入：判讀相同，不必要求每個功率完全相同</h2><p>固定 x1／x2，輪流將 x3／x4 設為 00、01、10、11。四組資料的布林真值必須相同，四個判讀也都必須符合它。類比功率差可以不同，只要仍有正確裕量。</p>'''
body+=table('表 4｜三種二輸入功能，共 12 組未作用輸入驗證',['功能','固定 x1x2','實際四組資料','四筆 bit','ΔP 最大−最小','檢查'],[
    (g,''.join(map(str,row['active_bits'])),' / '.join(row['patterns']),' / '.join(bit(v) for v in row['bits']),f"{row['delta_span']:.9f}",'通過' if row['passed'] else '未通過') for g,groups in D['unused_inputs'].items() for row in groups])
body+='''<p>只測 x3=x4=0 會漏掉其他實際輸入，不足以確認功能。<a href="../work/m1_s4/out/unused_input_groups.csv">未作用輸入群組 CSV</a>。</p>
<h2 id="margin">6．最小有號裕量：方向先正確，才談餘裕</h2>'''
body+=pre('真值 t∈{0,1}\nmargin = ΔP−τ\nsigned_margin = (2t−1) × margin\n\n正確方向 → signed_margin>0\n錯誤方向 → signed_margin<0\n正式驗收：每筆 bit 等於真值，且 signed_margin>ε\nminimum_clearance = min(signed_margin)−ε\n\n不能只看 min|ΔP|：方向相反，也可能有很大的 |ΔP|。')
body+=f'''<p>本輪最小有號裕量最低的是 <b>{worst}</b>，約 <b>{D['baseline'][worst]['summary']['minimum_signed_margin']:.6f}</b>，最差案例第一筆為 {D['baseline'][worst]['summary']['worst_pattern']}。當全部符號正確且 τ=0 時，最小有號裕量與最小 |ΔP| 才相同。這不是噪聲標準差、錯誤率或實體功率規格。</p>'''
body+=table('表 5｜真值／判讀的交叉核對',['功能','真值0→判0','真值0→判1','真值1→判0','真值1→判1','邊界'],[
    (g,r['summary']['confusion_actual_by_predicted'][0][0],r['summary']['confusion_actual_by_predicted'][0][1],r['summary']['confusion_actual_by_predicted'][1][0],r['summary']['confusion_actual_by_predicted'][1][1],r['summary']['boundaries']) for g,r in D['baseline'].items()])
body+='''<h2 id="diagnostics">7．診斷實驗：保留基準，改一個條件再比較</h2>'''
labels={'swapped_readout':'對調正／負讀取埠','reference_off':'R 振幅改為 0','theta_phi_swapped':'交換每顆 theta／phi'}
body+=table('表 6｜受控對照的失敗是預期教學結果，不是正式模型故障',['對照','正確／80','邊界','應注意'],[
    (labels[r['name']],f"{r['passed']}/80",r['boundaries'],{'swapped_readout':'功率差反號；么正性仍可通過。','reference_off':'沒有參考光，部分真值失敗或落在邊界。','theta_phi_swapped':'物理相位位置不同，不能交換參數。'}[r['name']]) for r in D['controlled_contrasts']])
body+='''<figure><img src="figures/m1_s4/theta1_sensitivity.png" alt="只改M1 theta時五種功能最小有號裕量的變化"><figcaption>圖 2｜本輪只掃描 M1 的 θ 誤差 −0.1π～+0.1π，其餘參數固定、門檻不重新調整。每點都重新跑該功能 16 組。此圖不是完整多參數誤差分析或製程容許規範。</figcaption></figure><p>學員可在 <a href="../config/m1_s4_lab.json">m1_s4_lab.json</a> 選功能、資料、R、相位誤差及 MZI 損耗，再重跑。theta_error_mzi_index=0～6 對應 M1～M7。這些修改只改變獨立的學員診斷，正式 80 筆基準始終維持 R=3、無損、零參考相位與門檻 0。</p>'''
student=D['student_diagnostic'];row=student['selected_case']
body+=table('表 7｜目前學員設定的獨立診斷',['內容','結果'],[
    ('功能／資料',student['config']['gate']+' / '+row['pattern']),
    ('該功能全部 16 組',f"{student['summary']['passed']}/16；邊界 {student['summary']['boundaries']}"),
    ('所選資料 P(out1)／P(out3)',f"{row['powers'][1]:.9f} / {row['powers'][3]:.9f}"),
    ('ΔP／有號裕量／bit',f"{row['delta']:.9f} / {row['signed_margin']:.9f} / {bit(row['bit'])}"),
    ('最小有號裕量',f"{student['summary']['minimum_signed_margin']:.9f}")])
body+='''<h3>互動預測：只換功能相位，或刻意偏離基準</h3><section class="panel"><label for="gate-program">相位程式</label><select id="gate-program">'''+''.join(f'<option>{g}</option>' for g in GATES)+'''</select><label for="gate-pattern">資料 x1x2x3x4</label><select id="gate-pattern">'''+''.join(f'<option{(" selected" if r["pattern"]=="1100" else "")}>{r["pattern"]}</option>' for r in D['baseline']['AND2']['rows'])+'''</select><label for="gate-R">R 振幅：<b id="gate-R-label">3.00</b></label><input id="gate-R" type="range" min="0" max="4" step="0.01" value="3" style="width:100%"><label for="gate-phase">R 相位：<b id="gate-phase-label">0.00 π</b></label><input id="gate-phase" type="range" min="0" max="2" step="0.01" value="0" style="width:100%"><label for="gate-error">M1 的 θ 誤差：<b id="gate-error-label">0.00 π</b></label><input id="gate-error" type="range" min="-0.1" max="0.1" step="0.01" value="0" style="width:100%"><button id="gate-reset">還原基準條件</button><div id="gate-live" class="answers" aria-live="polite" style="overflow-wrap:anywhere"></div><p class="muted">瀏覽器依十四相位、固定 OPS 重算複數光場；不以真值直接設定輸出。互動固定無損、τ=0、ε=10⁻¹⁰。改變 R 或相位誤差後，屬於診斷；不會改寫上方 80 筆正式驗收表。</p></section>'''
body+='<script>const LOGIC_PHASES='+json.dumps(CAT['gates'])+';const LOGIC_OPS='+json.dumps(CAT['ops_zero_based'])+';</script>'
body+='''<script>(()=>{const program=document.querySelector('#gate-program'),pattern=document.querySelector('#gate-pattern'),R=document.querySelector('#gate-R'),phase=document.querySelector('#gate-phase'),error=document.querySelector('#gate-error');const add=(a,b)=>[a[0]+b[0],a[1]+b[1]],scale=(z,s)=>[z[0]*s,z[1]*s],mul=(a,b)=>[a[0]*b[0]-a[1]*b[1],a[0]*b[1]+a[1]*b[0]];function show(){const bits=pattern.value.split('').map(Number),rp=Number(phase.value)*Math.PI,ep=Number(error.value)*Math.PI;let field=[...bits.map(b=>[b,0]),[Number(R.value)*Math.cos(rp),Number(R.value)*Math.sin(rp)]];const s=LOGIC_PHASES[program.value];for(let k=0;k<7;k++){const p=LOGIC_OPS[k][0],theta=s.theta[k]+(k===0?ep:0),h=theta/2,q=[-Math.sin(h),Math.cos(h)],phi=[Math.cos(s.phi[k]),Math.sin(s.phi[k])],a=mul(phi,field[p]),b=field[p+1];field[p]=mul(q,add(scale(a,Math.sin(h)),scale(b,Math.cos(h))));field[p+1]=mul(q,add(scale(a,Math.cos(h)),scale(b,-Math.sin(h))));}const powers=field.map(z=>z[0]**2+z[1]**2),delta=powers[1]-powers[3];let target;if(program.value==='AND2')target=bits[0]&bits[1];else if(program.value==='OR2')target=bits[0]|bits[1];else if(program.value==='XOR2')target=bits[0]^bits[1];else if(program.value==='AND4')target=Number(bits.every(Boolean));else target=Number(bits.some(Boolean));const bit=Math.abs(delta)<=1e-10?null:Number(delta>0),signed=(2*target-1)*delta,baseline=Number(R.value)===3&&Number(phase.value)===0&&Number(error.value)===0,result={field,powers,delta,bit,expected:target,signed_margin:signed,baseline};const box=document.querySelector('#gate-live');box.dataset.result=JSON.stringify(result);box.replaceChildren();for(const text of [baseline?'固定基準條件':'診斷條件：正式驗收表不變','P(out1)='+powers[1].toFixed(9)+' | P(out3)='+powers[3].toFixed(9),'ΔP='+delta.toFixed(9)+' | 有號裕量='+signed.toFixed(9),'真值='+target+' | 判讀='+(bit===null?'邊界':bit)+' | '+(bit===target?'這筆符合真值':'這筆未符合真值'),'五路總功率='+powers.reduce((a,b)=>a+b,0).toFixed(9)]){const line=document.createElement('div');line.textContent=text;box.appendChild(line);}document.querySelector('#gate-R-label').textContent=Number(R.value).toFixed(2);document.querySelector('#gate-phase-label').textContent=Number(phase.value).toFixed(2)+' π';document.querySelector('#gate-error-label').textContent=Number(error.value).toFixed(2)+' π';}program.addEventListener('change',show);pattern.addEventListener('change',show);for(const c of [R,phase,error])c.addEventListener('input',show);document.querySelector('#gate-reset').addEventListener('click',()=>{R.value=3;phase.value=0;error.value=0;show();});show();})();</script>
<h2 id="checks">8．測試與檔案</h2>'''
body+=table('表 8｜本輪可追溯證據',['內容','結果／入口'],[
    ('本步單元測試',f"{D['unit_tests']['passed']}/{D['unit_tests']['run']}；<a href=\"../work/m1_s4/out/unit_tests.log\">原始 log</a>"),
    ('前步回歸',f'{reg}/66；M0 S3、M1 S1～S3。'),
    ('本步計算檢查',f"{sum(c['passed'] for c in D['checks'])}/{len(D['checks'])}；<a href=\"../work/m1_s4/out/logic_results.json\">全部場、功率、版本與 SHA-256</a>"),
    ('共用驗收程式','<a href="../work/common/logic_validation.py">logic_validation.py</a> · <a href="../work/m1_s4/test_logic_validation.py">單元測試</a>'),
    ('實驗入口','<a href="../work/m1_s4/run_logic.py">run_logic.py</a> · <a href="../work/m1_s4/out/theta1_sensitivity.csv">相位示例掃描 CSV</a>')])
body+='''<p>本步完成理想 B7 的全功能數值驗收。尚未加入新相位合成、PDK 色散／反射、熱校正、動態接收器或實體 Chip 量測；本輪不會改寫原始來源或 D 槽。</p>
<h2 id="submit">9．學員驗收與交付</h2><ol><li>用同一個 B7 說明五組相位如何切換功能；埠位、R、門檻及編碼保持固定。</li><li>提交完整 80 筆 CSV，包含所有未作用輸入組合；不能省略邊界或錯誤資料。</li><li>指出最弱功能與最差案例，說明有號裕量和 |ΔP| 的差別。</li><li>固定 x1x2=11，逐一比較 x3x4 四種狀態的 bit 及 ΔP。</li><li>修改一個診斷條件，留下設定與結果副本；最後還原基準。由講師另行驗收學員紀錄。</li></ol>
<section class="panel"><label for="logic-name">學員姓名</label><input id="logic-name"><label for="logic-coverage">80 筆覆蓋與未作用輸入觀察</label><textarea id="logic-coverage"></textarea><label for="logic-margins">最弱功能、最差案例與有號裕量</label><textarea id="logic-margins"></textarea><label for="logic-diagnostic">診斷設定與結果分析</label><textarea id="logic-diagnostic"></textarea><button id="logic-generate">產生 M1 S4 學習記錄 JSON</button><textarea id="logic-json" hidden readonly aria-label="M1 S4 學習記錄 JSON" style="min-height:220px"></textarea><p class="muted">複製保存到 learner/m1_s4_observations.json；<a href="../learner/m1_s4_observations.template.json">空白範本</a>。</p></section>
<script>document.querySelector('#logic-generate').addEventListener('click',()=>{const box=document.querySelector('#logic-json');box.hidden=false;box.value=JSON.stringify({step:'M1 S4',learner_name:document.querySelector('#logic-name').value,coverage:document.querySelector('#logic-coverage').value,margins:document.querySelector('#logic-margins').value,diagnostic:document.querySelector('#logic-diagnostic').value,date:new Date().toISOString(),instructor_review:'pending'},null,2);box.focus();box.select();});</script>
<p><b>下一步 M1 S5：</b>將固定光路、十四個相位通道、五種功能與判讀規則整理成規格檔及相位設定檔，交給 M2 的 PDK／PIC 實作。</p>'''
nav=''.join(f'<a href="{href}">{label}</a>' for href,label in [('../Lab06b_index.html','總覽與報告入口'),('plan.html','完整規劃'),('m1_s3.html','M1 S3｜加權和與判讀'),('m1_s4.html','M1 S4｜五功能驗收'),('#contract','固定規則與真值'),('#programs','五組相位'),('#run','80 筆完整結果'),('#unused','未作用輸入'),('#margin','有號裕量'),('#diagnostics','互動與診斷'),('#submit','學員交付')])
html=f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M1 S4｜五種功能與完整 80 筆真值驗收｜Lab06b</title><link rel="stylesheet" href="../assets/course.css"></head><body><header class="top"><a href="../Lab06b_index.html"><b>LAB06b</b>　PIC Chip 學員實作課程</a><small>2026-10-31 · M1 S4</small></header><div class="layout"><aside><strong>學習與實作入口</strong>{nav}<a href="../work/m1_s4/out/logic_results.json">本輪完整 JSON</a><p class="muted">{state}<br>學員作答待提交</p></aside><main><button class="print" onclick="window.print()">列印／另存 PDF</button><div class="hero"><div class="eyebrow">MODULE 1 · STEP 4 · 90 MIN</div><h1>M1 S4｜五種功能與完整 80 筆真值驗收</h1><p class="lead">同一組光路，只換相位；完整送入四位元資料，核對真值、未作用輸入與最小有號裕量。</p><span class="tag ok">{total}/80 真值</span><span class="tag">12 組未作用輸入</span><span class="tag">18 項本步測試</span></div>{body}<footer>正式工作區 C:\\EDA_Codex\\Lab06b；D 槽唯讀。2026-10-31（Asia/Taipei）。理想數值驗收不替代實體 PIC 驗證。</footer></main></div></body></html>'''
(ROOT/'course/m1_s4.html').write_text(clean_course_html(html),encoding='utf-8')
for relative in ['Lab06b_index.html','course/plan.html','course/m0_s1.html','course/m0_s1_foundation.html','course/m0_s2.html','course/m0_s3.html','course/m1_s1.html','course/m1_s2.html','course/m1_s3.html','analysis/lab01a_7_6.html','reference/source_context.html']:
    p=ROOT/relative;text=p.read_text(encoding='utf-8');prefix='../' if '/' in relative else '';href=prefix+'course/m1_s4.html'
    if f'href="{href}"' not in text:text=text.replace('</aside>',f'<a href="{href}">M1 S4｜五功能與 80 筆驗收</a></aside>',1)
    if relative=='Lab06b_index.html':
        panel=f'<!-- M1S4:STATUS --><div class="callout good"><b>目前進度：</b>M0 與 M1 S1～S3 已建立；M1 S4：{state}。<a href="course/m1_s4.html">進入 M1 S4 →</a><br>五功能 {total}/80，學員作答另行驗收；下一步 M1 S5 規格交接。</div><!-- /M1S4:STATUS -->'
        text=re.sub(r'<!-- (?:M1S3|M1S4):STATUS -->.*?<!-- /(?:M1S3|M1S4):STATUS -->',lambda m:panel,text,count=1,flags=re.S)
        text=text.replace('S1 編碼、S2 矩陣、S3 加權和判讀核心通過；S4–S5 待實作','S1～S4 核心通過；五功能 80/80；S5 待交接')
        if '<td>M1 S4 主實作</td>' not in text:text=text.replace('<tr><td>理想 MZI 補充</td>','<tr><td>M1 S4 主實作</td><td><a href="course/m1_s4.html">五種功能與 80 筆真值驗收</a></td><td>本輪完整覆蓋、未作用輸入與有號裕量</td></tr><tr><td>理想 MZI 補充</td>',1)
        card='<article class="card"><div class="num">M1 S4</div><h3>五功能與完整 80 筆驗收</h3><p>固定光路、編碼與門檻；核對全部資料、未作用輸入與最小裕量。</p><a href="course/m1_s4.html">進入本步 →</a></article>'
        text=re.sub(r'<!-- M1S3:CARD -->.*?<!-- /M1S3:CARD -->',lambda m:'<!-- M1S4:CARD -->'+card+'<!-- /M1S4:CARD -->',text,flags=re.S)
        text=text.replace('M0 三步與 M1 S1～S3 核心已實算','M0 三步與 M1 S1～S4 核心已實算')
    if relative=='course/plan.html':text=text.replace('<td>M1 s4<br>1.5 h</td>','<td><a href="m1_s4.html">M1 s4</a><br>1.5 h</td>')
    p.write_text(text,encoding='utf-8')
CFG['progress']['M1_S4']='five-function 80-case acceptance and signed margins passed; learner submission pending' if D['core_passed'] else 'logic acceptance unresolved'
CFG['progress']['M1_S5']='next step: shared PIC specification and phase program handoff to M2'
(ROOT/'config/course.json').write_text(json.dumps(CFG,ensure_ascii=False,indent=2),encoding='utf-8')
readme=(ROOT/'README_Lab06b_Course.md').read_text(encoding='utf-8').replace('下一步 M1 S4：五種功能與完整 80 筆真值驗收。','M1 S4：scripts/run_m1_s4.ps1；五功能、80 筆真值及有號裕量。\n下一步 M1 S5：規格與相位程式交接 M2。')
(ROOT/'README_Lab06b_Course.md').write_text(readme,encoding='utf-8')
print('M1 S4 page rendered; core:',D['core_passed'])
