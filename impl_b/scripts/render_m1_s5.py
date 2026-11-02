from report_policy import clean_course_html
"""Readable M1/M2 specification handoff and read-only consumer preview."""
from pathlib import Path
from html import escape
import json,re
ROOT=Path(__file__).resolve().parents[1]
D=json.loads((ROOT/'work/m1_s5/out/handoff_results.json').read_text(encoding='utf-8'))
SPEC=json.loads((ROOT/'pic_spec.json').read_text(encoding='utf-8'))
PHASES=json.loads((ROOT/'phase_settings.json').read_text(encoding='utf-8'))
CFG=json.loads((ROOT/'config/course.json').read_text(encoding='utf-8'))
FIG=ROOT/'course/figures/m1_s5';FIG.mkdir(parents=True,exist_ok=True)


def table(title,headers,rows):
    return '<div class="scroll"><table><caption>'+title+'</caption><thead><tr>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(c)+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def pre(s):return '<pre><code>'+escape(s)+'</code></pre>'


(FIG/'handoff_flow.svg').write_text('''<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="350" viewBox="0 0 1100 350" role="img" aria-labelledby="t d"><title id="t">M1 邏輯規格交接 M2</title><desc id="d">M1相位與驗收產生規格和相位檔，打包本地模型及表格，在獨立目錄重播80筆，再交給M2完成PDK與幾何。邏輯通道有名稱，PAD和heater校正待定。</desc><rect width="1100" height="350" fill="#f4f7fc" rx="10"/><g fill="#e3edfc" stroke="#155bd0" stroke-width="2"><rect x="20" y="60" width="225" height="160" rx="8"/><rect x="300" y="60" width="225" height="160" rx="8"/><rect x="580" y="60" width="225" height="160" rx="8"/></g><rect x="860" y="60" width="220" height="160" rx="8" fill="#fff3d7" stroke="#b78019" stroke-width="2"/><g font-family="Microsoft JhengHei,Arial" font-size="19" fill="#17263b" text-anchor="middle"><text x="132" y="97">M1 已驗證資料</text><text x="132" y="137">5 組相位 · 80 筆真值</text><text x="132" y="176">固定光路與判讀</text><text x="412" y="97">交接規格與檔案綁定</text><text x="412" y="137">10 光學埠 · 14 通道</text><text x="412" y="176" font-size="16">spec SHA-256 ↔ phases</text><text x="692" y="97">獨立目錄重播</text><text x="692" y="137">只讀包內模型與表格</text><text x="692" y="176">80/80 · 無父層課程依賴</text><text x="970" y="97">M2 待實作</text><text x="970" y="137">PDK · 光路 · heater</text><text x="970" y="176">EC／PAD · DRC／連接</text></g><g stroke="#155bd0" stroke-width="4" fill="#155bd0"><path d="M250 140H285 M530 140H565 M810 140H845"/><path d="M278 133L288 140L278 147 M558 133L568 140L558 147 M838 133L848 140L838 147"/></g><g font-family="Microsoft JhengHei,Arial" font-size="18" fill="#526379"><text x="28" y="272">theta1 → M1 上臂相位 → H_M1_theta（邏輯名稱）→ PAD 與校正：M2 待定</text><text x="28" y="313">交接完成的是邏輯介面與可重播資料；不表示已建立實體 PIC 或通過 PDK／製程簽核。</text></g></svg>''',encoding='utf-8')
reg=sum(v['passed'] for v in D['regression'].values())
state='規格交接與獨立重播通過' if D['core_passed'] else '交接有未通過項，請檢查原始證據'
body=f'''<div class="callout {'good' if D['core_passed'] else 'warn'}"><b>這一步要回答：</b>M2 能否只拿一份規格與相位程式，就知道如何接線、命名、模擬及讀取同一個 B7？<br><b>本輪結果：</b>直接交接包與獨立資料夾均重播 80/80；{D['unit_tests']['passed']}/{D['unit_tests']['run']} 項本步測試、{reg}/84 項前步回歸，四種錯誤副本均被拒絕。{state}；學員作答另行驗收。</div>
<h2 id="predict">1．先預測：規格交接要交什麼？</h2><p>建議 60 分鐘：規格與版本 10 分、光學埠及相位通道 15 分、獨立重播 15 分、錯誤辨識 10 分、M2 交接記錄 10 分。</p><ol><li>相位向量只有十四個數字，沒有通道名稱，M2 能否確定哪個數字送到哪顆 heater？</li><li>theta=π 是 π V 嗎？目前能不能填入 PAD1 與 Vπ？</li><li>相位檔來自另一份規格，即使檔名相同，能否直接混用？</li><li>交接包在沒有父層 course.json 的資料夾，能否仍重跑全部 80 筆？</li></ol>
<h2 id="contract">2．固定邏輯規格，將 M2 未完成項目寫清楚</h2><figure><img src="figures/m1_s5/handoff_flow.svg" alt="M1規格與相位交接經過獨立重播，再由M2實作PDK與版圖"><figcaption>圖 1｜本步交接流程。heater 名稱先固定為邏輯識別碼；實際 heater、PAD、光學接口與校正仍待 M2 建立。</figcaption></figure>'''
body+=table('表 1｜兩份正式來源檔與責任',['檔案','固定內容','本步未宣稱'],[
    ('<a href="../pic_spec.json">pic_spec.json</a>','版本、B7 接線、10 個光學埠、14 相位通道、編碼／判讀及 80 筆驗收規則','尚未建立 EC、PAD、實體 heater 或幾何。'),
    ('<a href="../phase_settings.json">phase_settings.json</a>','五種功能的完整精度相位，rad、通道順序、spec_sha256','相位不是電壓；沒有新相位最佳化或熱校正。')])
body+=pre('pic_spec.schema = lab06b.pic_spec.v1\nphase_settings.schema = lab06b.phase_settings.v1\n\nphase_settings.spec_sha256 = SHA256(pic_spec.json 的完整檔案位元組)\nchannel_order 與 spec.phase_vector_order 必須一致\n\n固定：[x1,x2,x3,x4,R]ᵀ，R 振幅=3、相位=0\n固定：ΔP=P(out1)−P(out3)，τ=0、ε=10⁻¹⁰\n範圍：理想前向模型、七顆 MZI、六段恆等直通\n待定：實體接口、PAD、heater 校正與路徑傳播')
body+='''<p>這是本課程的版本化 JSON 格式，由 Python 驗證器逐欄與跨檔檢查。修改規格後，必須更新相位檔綁定及重新驗收；只改檔名不能表示資料相容。</p>
<h2 id="ports">3．光學埠：十個都保留，不能只交兩個讀取埠</h2>'''
body+=table('表 2｜光學 core I/O；所有實體接口目前為待定',['ID','方向','mode index','一基別名','角色','實體接口'],[
    (p['id'],p['direction'],p['mode_index'],p['alias'],p['role'],'M2 待定') for p in SPEC['optical_ports']])
body+='''<p>out1／out3 是差分判讀埠；out0、out2、out4 仍是輸出光路，不能從模型或版圖中消失。後續是否接 EC、終端或其他監測方式，需由 M2 邊界與實體設計決定。</p>
<h2 id="channels">4．相位通道：名稱連到 MZI，再連到邏輯 heater</h2>'''
by_id={c['id']:c for c in SPEC['phase_channels']}
body+=table('表 3｜十四個相位通道與向量索引',['vector index','通道 ID','MZI','參數／物理位置','邏輯 heater ID','PAD／校正'],[
    (k,name,by_id[name]['instance'],by_id[name]['parameter']+'：'+('上臂、兩顆 MMI 之間' if by_id[name]['parameter']=='theta' else '上方輸入、第一顆 MMI 之前'),by_id[name]['heater_logical_id'],'M2 待定') for k,name in enumerate(SPEC['phase_vector_order'])])
body+='''<p>目前向量順序為 theta1～theta7、phi1～phi7。讀取程式依名稱建立對照表，再取得每顆的 θ／φ，避免只依固定位置猜測意義。測試也確認：通道名稱與相位值一起一致重排時，U 不變；只改其中一邊則拒絕。</p><p>H_M1_theta 只是邏輯名稱，不表示已畫出 heater。pad_id、calibration 與 physical_interface 皆為 null；驗證器不接受在 M1 規格內填入未驗證的 PAD 或電壓校正值。</p>
<h2 id="package">5．交接包與學員執行</h2>'''
body+=pre(r'''Set-Location -LiteralPath 'C:\EDA_Codex\Lab06b'
& .\scripts\run_m1_s5.ps1''')
body+=pre('delivery/m1_handoff/\n├─ pic_spec.json              # 固定邏輯與 M2 待定欄位\n├─ phase_settings.json        # 五功能相位＋spec SHA-256\n├─ optical_ports.csv          # 10 個光學埠\n├─ phase_channels.csv         # 14 個相位通道\n├─ acceptance_truth.csv       # M1 S4 的 80 筆對照\n├─ model/common/              # 本包自己的理想模型與驗證器\n├─ replay_handoff.py          # 獨立消費端\n├─ manifest.json              # 固定檔案清單及 SHA-256\n├─ README.md\n└─ verification/replay_results.json  # 可重新產生的輸出')
body+='''<p>可直接下載 <a href="../delivery/m1_handoff.zip">m1_handoff.zip</a>。Python 需為 3.10 以上並有 NumPy；本機建議使用 EDA_paths.json 的 physics_python。消費端只在本次 Python 程序補上 Windows 數值 DLL 路徑，不修改父層環境或工具安裝。</p>'''
body+=pre(r'''$cfg = Get-Content -LiteralPath '.\EDA_paths.json' -Raw | ConvertFrom-Json
& $cfg.windows.physics_python '.\delivery\m1_handoff\replay_handoff.py' --gate XOR2 --bits 1010''')
body+=r'''<p>學員練習：將 ZIP 解壓到 C:\EDA_Codex 下另一個新資料夾，使用相同數值 Python 執行 replay_handoff.py。消費端先核對 manifest、版本、規格綁定與 CSV 對照，再重新計算五種功能共 80 筆；不讀父層課程設定。</p>'''
body+=table('表 4｜本輪獨立消費端驗證',['項目','結果','證據'],[
    ('正式交接包重播',f"{D['direct_replay']['truth_passed']}/80",'<a href="../work/m1_s5/out/direct_replay.log">log</a>'),
    ('C 槽另一資料夾，以 Python -I 重播',f"{D['isolated_replay']['truth_passed']}/80",'<a href="../work/m1_s5/out/isolated_replay.log">log</a>'),
    ('輸入資料只使用包內模型','通過；載入路徑已記錄','<a href="../delivery/m1_handoff/verification/replay_results.json">包內結果 JSON</a>'),
    ('對照 M1 S4 的最大數值差',f"{D['csv_max_error']:.3e}",'由新 spec／相位檔重算，對照 80 筆 CSV。'),
    ('ZIP 固定檔案雜湊','全部一致','<a href="../delivery/m1_handoff/manifest.json">manifest.json</a>')])
body+='<details><summary>M2 程式如何讀取交接檔？</summary>'
body+=pre('from pathlib import Path\nimport sys\nbundle = Path("delivery/m1_handoff").resolve()\nsys.path.insert(0, str(bundle / "model"))\nfrom common import handoff, b7\n\nspec, phases = handoff.load_bundle(bundle)\ntop = handoff.validate_spec(spec)\nprograms = handoff.phase_catalog(spec, phases)\np = programs["AND2"]\nU = b7.transfer_matrix(top, p["theta"], p["phi"])\n# M2 以相同 spec 的 instances、光學埠及通道建立 PDK 電路／版圖。')
body+='''<p>此片段仍是理想 U。M2 必須改以 PDK 元件與實際路徑驗證，不能把理想重播結果當成 PDK 模擬。</p></details>
<h2 id="errors">6．四種錯誤副本，必須在交接時指出</h2>'''
names={'phase_digest_change':'相位檔內容變動，未更新 manifest','semantic_wrong_unit':'相位單位改成 degree，並重算所有檔案雜湊','csv_channel_mismatch':'通道 CSV 的 heater 名稱錯配，並重算雜湊','wrong_spec_binding':'相位檔綁到錯誤的 spec SHA-256'}
body+=table('表 5｜本輪受控錯誤；正式檔案未被修改',['錯誤','驗證結果','實際原因'],[
    (names[r['name']],'已拒絕' if r['rejected'] else '未拒絕',escape(r['reason'])) for r in D['rejection_examples']])
body+='''<p>檔案雜湊只確認內容一致，單位、通道及數值仍需另外檢查。上述副本存於 work/m1_s5/controlled_cases/；請勿在正式交接檔上直接製造錯誤。</p>
<h2 id="preview">7．唯讀預覽：從通道名稱到相位，再到判讀</h2><section class="panel"><label for="handoff-function">功能</label><select id="handoff-function">'''+''.join(f'<option>{g}</option>' for g in PHASES['programs'])+'''</select><label for="handoff-pattern">資料 x1x2x3x4</label><select id="handoff-pattern">'''+''.join(f'<option{(" selected" if n==3 else "")}>{"".join(str((n>>j)&1) for j in range(4))}</option>' for n in range(16))+'''</select><label for="handoff-channel">相位通道</label><select id="handoff-channel">'''+''.join(f'<option>{name}</option>' for name in SPEC['phase_vector_order'])+'''</select><div id="handoff-live" class="answers" aria-live="polite" style="overflow-wrap:anywhere"></div><p class="muted">依正式 JSON 的命名通道及 OPS 重新計算；此處不修改檔案。完整的雜湊、跨檔及獨立重播驗證由 Python 消費端執行。</p></section>'''
body+='<script>const HANDOFF_SPEC='+json.dumps(SPEC)+';const HANDOFF_PHASES='+json.dumps(PHASES)+';</script>'
body+='''<script>(()=>{const gate=document.querySelector('#handoff-function'),pattern=document.querySelector('#handoff-pattern'),channel=document.querySelector('#handoff-channel');const add=(a,b)=>[a[0]+b[0],a[1]+b[1]],scale=(z,s)=>[z[0]*s,z[1]*s],mul=(a,b)=>[a[0]*b[0]-a[1]*b[1],a[0]*b[1]+a[1]*b[0]];function show(){const map=Object.fromEntries(HANDOFF_PHASES.channel_order.map((id,k)=>[id,HANDOFF_PHASES.programs[gate.value][k]])),bits=pattern.value.split('').map(Number);let field=[...bits.map(b=>[b,0]),[3,0]];for(const inst of HANDOFF_SPEC.architecture.instances){const p=inst.modes[0],h=map[inst.theta_channel]/2,phi=map[inst.phi_channel],q=[-Math.sin(h),Math.cos(h)],a=mul([Math.cos(phi),Math.sin(phi)],field[p]),b=field[p+1];field[p]=mul(q,add(scale(a,Math.sin(h)),scale(b,Math.cos(h))));field[p+1]=mul(q,add(scale(a,Math.cos(h)),scale(b,-Math.sin(h))));}const powers=field.map(z=>z[0]**2+z[1]**2),delta=powers[1]-powers[3],bit=Math.abs(delta)<=1e-10?null:Number(delta>0),info=HANDOFF_SPEC.phase_channels.find(c=>c.id===channel.value),value=map[channel.value],result={field,powers,delta,bit,channel:info,vector_index:HANDOFF_SPEC.phase_vector_order.indexOf(channel.value),phase_rad:value};const box=document.querySelector('#handoff-live');box.dataset.result=JSON.stringify(result);box.replaceChildren();for(const text of ['通道 '+info.id+' → '+info.instance+' / '+info.parameter+' → '+info.heater_logical_id,'vector index='+result.vector_index+' | 相位='+value.toFixed(9)+' rad = '+(value/Math.PI).toFixed(6)+' π','物理位置：'+info.location,'PAD／校正：M2 待定','P(out1)='+powers[1].toFixed(9)+' | P(out3)='+powers[3].toFixed(9),'ΔP='+delta.toFixed(9)+' | bit='+(bit===null?'邊界':bit)]){const div=document.createElement('div');div.textContent=text;box.appendChild(div);}}for(const c of [gate,pattern,channel])c.addEventListener('change',show);show();})();</script>
<h2 id="pending">8．M2 的輸入、工作與待交付項</h2>'''
body+=table('表 6｜交接界面，不把尚未完成項目填成已驗證',['M2 使用的資料','M2 需要完成的工作','目前狀態'],[
    ('core 10 光學埠、角色與差分埠','決定 PIC 邊界、外部光源／接收器、EC 或終端去向','待 M2 S1／S5'),
    ('7 個 MZI、6 段 bypass、14 相位通道','以 CORNERSTONE PDK 建電路，加入真實模型比較 80 筆','待 M2 S2'),
    ('instance／channel／heater 邏輯名稱','放置與繞線、路徑相位、heater 實體幾何','待 M2 S3'),
    ('pad_id=null、calibration=null','建立 PAD／共地與驅動校正對照','待 M2 S5'),
    ('M1 理想 80 筆與裕量','PDK／路徑回填後重跑，再做 DRC 與連接檢查','待 M2 S6／S7')])
body+='''<h2 id="files">9．測試與交付檔案</h2>'''
body+=table('表 7｜本步程式、表格與原始證據',['內容','入口'],[
    ('正式規格／相位','<a href="../pic_spec.json">pic_spec.json</a> · <a href="../phase_settings.json">phase_settings.json</a>'),
    ('可攜交接包','<a href="../delivery/m1_handoff.zip">ZIP</a> · <a href="../delivery/m1_handoff/README.md">README</a>'),
    ('光學埠／相位通道','<a href="../delivery/m1_handoff/optical_ports.csv">10 埠 CSV</a> · <a href="../delivery/m1_handoff/phase_channels.csv">14 通道 CSV</a>'),
    ('共用驗證器／消費端','<a href="../work/common/handoff.py">handoff.py</a> · <a href="../delivery/m1_handoff/replay_handoff.py">replay_handoff.py</a>'),
    ('本步單元測試',f"{D['unit_tests']['passed']}/{D['unit_tests']['run']}；<a href=\"../work/m1_s5/out/unit_tests.log\">log</a>"),
    ('前步回歸',f'{reg}/84；M0 S3、M1 S1～S4。'),
    ('完整結果／版本／雜湊','<a href="../work/m1_s5/out/handoff_results.json">handoff_results.json</a> · <a href="../work/m1_s5/test_handoff.py">本步測試原始碼</a>')])
body+='''<h2 id="submit">10．學員驗收與交付</h2><ol><li>指出規格、相位檔、CSV 與 manifest 各自的用途，以及它們如何互相綁定。</li><li>由 theta1、phi1 說明 MZI 位置、通道索引與邏輯 heater 名稱；不可直接把相位填成電壓。</li><li>把交接包放到 C 槽另一個新資料夾重播，提交 80/80 結果與載入的模型路徑。</li><li>分析一個受控錯誤被拒絕的原因，保留正式資料與錯誤副本的區別。</li><li>列出 M2 尚待完成的光學、heater、PAD 與驗證事項，由講師驗收學員記錄。</li></ol>
<section class="panel"><label for="handoff-name">學員姓名</label><input id="handoff-name"><label for="handoff-mapping">埠位、相位通道與 heater／PAD 說明</label><textarea id="handoff-mapping"></textarea><label for="handoff-replay">獨立重播位置、結果與錯誤分析</label><textarea id="handoff-replay"></textarea><label for="handoff-todo">交給 M2 的待辦</label><textarea id="handoff-todo"></textarea><button id="handoff-generate">產生 M1 S5 學習記錄 JSON</button><textarea id="handoff-json" hidden readonly aria-label="M1 S5 學習記錄 JSON" style="min-height:220px"></textarea><p class="muted">複製保存到 learner/m1_s5_observations.json；<a href="../learner/m1_s5_observations.template.json">空白範本</a>。</p></section>
<script>document.querySelector('#handoff-generate').addEventListener('click',()=>{const box=document.querySelector('#handoff-json');box.hidden=false;box.value=JSON.stringify({step:'M1 S5',learner_name:document.querySelector('#handoff-name').value,mapping:document.querySelector('#handoff-mapping').value,independent_replay:document.querySelector('#handoff-replay').value,m2_todo:document.querySelector('#handoff-todo').value,date:new Date().toISOString(),instructor_review:'pending'},null,2);box.focus();box.select();});</script>
<p><b>下一步 M2 S1：</b>確認 PIC 與外部設備的邊界，建立功能方塊圖及 I/O 表，將本步邏輯 core 規格接到實際 PIC 實作。</p>'''
nav=''.join(f'<a href="{href}">{label}</a>' for href,label in [('../Lab06b_index.html','總覽與報告入口'),('plan.html','完整規劃'),('m1_s4.html','M1 S4｜80 筆驗收'),('m1_s5.html','M1 S5｜規格交接'),('#contract','規格與版本'),('#ports','10 個光學埠'),('#channels','14 個相位通道'),('#package','獨立重播包'),('#preview','命名通道預覽'),('#pending','M2 待辦'),('#submit','學員交付')])
html=f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M1 S5｜規格與相位程式交接 M2｜Lab06b</title><link rel="stylesheet" href="../assets/course.css"></head><body><header class="top"><a href="../Lab06b_index.html"><b>LAB06b</b>　PIC Chip 學員實作課程</a><small>2026-10-31 · M1 S5</small></header><div class="layout"><aside><strong>學習與實作入口</strong>{nav}<a href="../work/m1_s5/out/handoff_results.json">本輪交接結果 JSON</a><p class="muted">{state}<br>學員作答待提交</p></aside><main><button class="print" onclick="window.print()">列印／另存 PDF</button><div class="hero"><div class="eyebrow">MODULE 1 · STEP 5 · 60 MIN</div><h1>M1 S5｜規格與相位程式交接 M2</h1><p class="lead">將邏輯、接線、埠位、相位通道與驗收規則寫成一致的交接檔，從獨立重播確認 M2 能接續同一個設計。</p><span class="tag ok">交接包 80/80 重播</span><span class="tag">10 光學埠 · 14 相位通道</span><span class="tag">4 種錯誤副本拒絕</span></div>{body}<footer>正式工作區 C:\\EDA_Codex\\Lab06b；D 槽唯讀。2026-10-31（Asia/Taipei）。本步交付 M1 邏輯規格，M2 實體實作與驗證仍待完成。</footer></main></div></body></html>'''
(ROOT/'course/m1_s5.html').write_text(clean_course_html(html),encoding='utf-8')
for rel in ['Lab06b_index.html','course/plan.html','course/m0_s1.html','course/m0_s1_foundation.html','course/m0_s2.html','course/m0_s3.html','course/m1_s1.html','course/m1_s2.html','course/m1_s3.html','course/m1_s4.html','analysis/lab01a_7_6.html','reference/source_context.html']:
    p=ROOT/rel;text=p.read_text(encoding='utf-8');prefix='../' if '/' in rel else '';href=prefix+'course/m1_s5.html'
    if f'href="{href}"' not in text:text=text.replace('</aside>',f'<a href="{href}">M1 S5｜規格與相位交接</a></aside>',1)
    if rel=='Lab06b_index.html':
        panel=f'<!-- M1S5:STATUS --><div class="callout good"><b>目前進度：</b>M0 與 M1 五步核心已建立；M1 S5：{state}。<a href="course/m1_s5.html">進入 M1 S5 →</a><br>可攜交接包重播 80/80；學員作答另行驗收。下一步 M2 S1 邊界與 I/O。</div><!-- /M1S5:STATUS -->'
        text=re.sub(r'<!-- (?:M1S4|M1S5):STATUS -->.*?<!-- /(?:M1S4|M1S5):STATUS -->',lambda m:panel,text,count=1,flags=re.S)
        text=text.replace('S1～S4 核心通過；五功能 80/80；S5 待交接','S1～S5 核心通過；五功能 80/80；可攜交接包已驗證')
        if '<td>M1 S5 主實作</td>' not in text:text=text.replace('<tr><td>理想 MZI 補充</td>','<tr><td>M1 S5 主實作</td><td><a href="course/m1_s5.html">規格與相位程式交接 M2</a></td><td>正式 JSON、10 埠／14 通道、可攜重播包</td></tr><tr><td>理想 MZI 補充</td>',1)
        card='<article class="card"><div class="num">M1 S5</div><h3>規格與相位交接 M2</h3><p>命名埠與相位通道、綁定規格版本，獨立重播後交給 M2。</p><a href="course/m1_s5.html">進入本步 →</a></article>'
        text=re.sub(r'<!-- M1S4:CARD -->.*?<!-- /M1S4:CARD -->',lambda m:'<!-- M1S5:CARD -->'+card+'<!-- /M1S5:CARD -->',text,flags=re.S)
        text=text.replace('M0 三步與 M1 S1～S4 核心已實算','M0 三步與 M1 五步核心已實算')
    if rel=='course/plan.html':text=text.replace('<td>M1 s5<br>1 h</td>','<td><a href="m1_s5.html">M1 s5</a><br>1 h</td>')
    p.write_text(text,encoding='utf-8')
CFG['progress']['M1_S5']='logical spec, phase mapping and portable 80-case replay passed; learner submission pending' if D['core_passed'] else 'handoff checks unresolved'
CFG['progress']['M2_S1']='next step: PIC/external-system boundary and optical/electrical I/O table'
(ROOT/'config/course.json').write_text(json.dumps(CFG,ensure_ascii=False,indent=2),encoding='utf-8')
p=ROOT/'README_Lab06b_Course.md';text=p.read_text(encoding='utf-8').replace('下一步 M1 S5：規格與相位程式交接 M2。','M1 S5：scripts/run_m1_s5.ps1；pic_spec.json、phase_settings.json 與 delivery/m1_handoff.zip。\n下一步 M2 S1：PIC 邊界與 I/O 表。');p.write_text(text,encoding='utf-8')
(ROOT/'delivery/README.md').write_text('# M1 → M2 交接\n\nm1_handoff/ 為獨立的理想模型交接包；m1_handoff.zip 可解壓後重播。\n正式來源：根目錄 pic_spec.json 與 phase_settings.json。\n本包不是 M3 最終 PIC 交付，也未完成 PDK、幾何、PAD／heater 或實體驗證。\n',encoding='utf-8')
print('M1 S5 page rendered; core:',D['core_passed'])
