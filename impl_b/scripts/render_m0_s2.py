from report_policy import clean_course_html
"""M0 S2 lesson and progress integration, generated from physics_results.json."""
from pathlib import Path
from html import escape
import json,math,re

ROOT=Path(__file__).resolve().parents[1]
DATA=json.loads((ROOT/'work/m0_s2/out/physics_results.json').read_text(encoding='utf-8'))
FEM=DATA['fem'];FINE=FEM['convergence'][-1];SCALAR=DATA['new_scalar_propagation']['grids'][-1]
INHERITED=DATA['inherited_fdtd']


def table(title,headers,rows):
    return '<div class="scroll"><table><caption>'+title+'</caption><thead><tr>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(c)+'</td>' for c in r)+'</tr>' for r in rows)+'</tbody></table></div>'


def pre(text):return '<pre><code>'+escape(text)+'</code></pre>'


status='核心實作通過；Meep FDTD 未重跑' if DATA['core_passed'] else '核心檢查尚有未通過項'
body=f'''<div class="callout good"><b>本步要回答：</b>為什麼光被束縛在波導內？模態的有效折射率與材料折射率有什麼差別？MMI 如何自成像？MZI 的相位又如何改變輸出去向？<br><b>本輪狀態：</b>{status}。學員作答另行提交。</div>
<h2 id="goals">1．預測 → 操作 → 觀察 → 解釋</h2><p>建議 90 分鐘：預測 10 分、執行與讀圖 25 分、模型比較 25 分、相位與功率練習 15 分、整理證據 15 分。</p><ol><li>先預測：0.35、0.45、0.55 µm 三種波導寬度，哪一種的 n_eff 最高？</li><li>先看截面模態，再看沿 z 方向的場圖，辨認座標與色階。</li><li>核對網格和計算區域比較，知道數字能支持到什麼程度。</li><li>用 θ=0、π/2、π 和兩路相對相位，解釋 MZI 的切換、分光、合光。</li></ol>
<h2 id="scope">2．三類資料，分別回答三個問題</h2>'''
body+=table('表 1｜本輪實算與引用範圍',['資料','方法／來源','能回答的問題','限制'],[
('本輪 FEM 截面模態','femwell 全向量、二階有限元素；本輪重新求解','450×220 nm Si strip 的 n_eff、準 TE 比例、模場、寬度趨勢','均勻 SiO₂ 包覆；有限 PEC 計算邊界；不含實際 BOX／基板／空氣與 heater。'),
('本輪 MMI 傳播','均勻 6 µm 主體的標量 Helmholtz 模態展開','不同模態累積相位後，如何形成干涉與自成像','不含 taper、實際輸出波導、反射與垂直結構；不是完整 PDK 或 FDTD。'),
('Lab01a §7.6 原始場圖','既有 Meep 2D-EIM FDTD；本輪重新讀 NPZ 計算指標','完整 MZI 的切換、分光與相干合光；與理想模型比較','引用既有場資料。執行介面回報 Wsl/E_ACCESSDENIED；Meep 安裝狀態未驗證，未重跑 FDTD。')])
body+='''<h2 id="run">3．學員實際執行</h2><p>使用根目錄 EDA_paths.json 的 physics_python。本步已有 femwell，不需要在 IPKISS 環境安裝套件；啟動腳本會為本次執行設定所需 DLL 路徑，結束後還原。</p>'''+pre(r'''Set-Location -LiteralPath 'C:\EDA_Codex\Lab06b'
& .\scripts\run_m0_s2.ps1''')
body+='''<p>先看 <a href="../config/m0_s2.json">m0_s2.json</a>。第一次維持參數不變；完成基準後可把 strip_width_um 從 0.45 改為 0.50，並把 width_sweep_um 的中間值一起改為 0.50，再執行並比較。修改前請複製原設定與 out/ 的結果到自己的 learner/ 紀錄。</p><p><a href="../work/m0_s2/physics_lab.py">閱讀本輪求解程式</a> · <a href="../scripts/run_m0_s2.ps1">啟動腳本</a> · <a href="../work/m0_s2/out/physics_results.json">完整數值、版本與來源雜湊</a></p>
<h2 id="mode">4．截面模態：光不只存在於矽核心</h2>'''
body+=f'''<figure><img src="figures/m0_s2/strip_mode.png" alt="本輪有限元素求得的波導截面模態與三角形網格"><figcaption>圖 1｜本輪重新計算。左圖為時間平均縱向 Poynting 密度，除以本圖峰值；青色框為 0.45×0.22 µm 矽核心。右圖為實際有限元素網格。傳播方向垂直於截面，即 z；此圖不是光沿晶片前進的影片。</figcaption></figure><p>本輪準 TE 模態 n_eff=<b>{FINE['neff']:.6f}</b>，TE fraction=<b>{FINE['te_fraction']:.6f}</b>。femwell 的 TE fraction 是橫向 Ex／Ey 場的比例判據，不代表 97% 的總功率留在矽內。電場延伸到包覆層是導模的一部分。</p>'''
body+=table('表 2｜三個容易混淆的折射率',['數值／符號','本輪用途','正確理解'],[
(f"n_Si={DATA['parameters']['n_si']}",'矽材料折射率假設','這是單一波長的材料模型輸入，未做材料色散擬合。'),
(f"n_eff(strip)={FINE['neff']:.6f}",'450×220 nm 截面導模的 β/k₀','由核心與包覆共同決定，不能直接當成材料折射率。'),
('n_core,EIM=2.85','MMI 平面教學模型的等效核心','為近似垂直束縛的既有 EIM 假設；不是上列窄 strip 的 n_eff。')])
body+=table('表 3｜波導寬度掃描：本輪實算',['寬度 [µm]','n_eff','TE fraction','核心電能比例代理'],[
(f"{r['width_um']:.2f}",f"{r['neff']:.6f}",f"{r['te_fraction']:.6f}",f"{r['electric_energy_core_fraction']:.6f}") for r in FEM['width_sweep']])
body+='<p>最後一欄是非色散假設下的 ∫core ε|E|²／∫all ε|E|²；它不是輸出功率或傳輸效率。求解與選模方式參考 <a href="https://helgegehring.github.io/femwell/photonics/examples/selecting_modes.html">Femwell 官方範例</a>，本輪以 TE fraction 與有效折射率共同挑選導模。</p>'
body+='<h3>先檢查網格與有限計算邊界</h3>'
body+=table('表 4｜二階 FEM 網格比較',['網格','核心 x／y 分割','三角形數','場自由度','n_eff'],[
(r['label'],str(r['core_divisions']),r['triangles'],r['field_dofs'],f"{r['neff']:.9f}") for r in FEM['convergence']])
body+=f'''<p>細／中網格差為 <b>{FEM['mesh_neff_delta']:.3e}</b>；把半區域從 ±1.5×±1.0 µm 擴大至 ±2.0×±1.5 µm 後，n_eff 差為 <b>{FEM['domain_neff_delta']:.3e}</b>。本課門檻為兩者皆小於 10⁻³。這只支持此理想截面模型的比較，不是實際製程的精度或基板洩漏驗證。</p>
<h2 id="mmi">5．本輪 MMI 模態展開：看見多模干涉</h2><p>在均勻 MMI 主體內求解橫向模態 φₘ(y)，每個模態有自己的 βₘ。將同一個入射高斯光場分解，再沿傳播方向累積相位：</p>'''+pre('ψ(y,z) = Σ aₘ φₘ(y) exp(i βₘ z)\naₘ = ∫ φₘ*(y) ψ_in(y) dy\nMMI 寬度 W=6 µm；入射中心 y=−1.015 µm；振幅 1/e 半徑=0.35 µm')
body+=f'''<figure><img src="figures/m0_s2/mmi_modal_field.png" alt="本輪標量 MMI 模態展開傳播圖"><figcaption>圖 2｜本輪計算，共保留 {SCALAR['guided_modes']} 個標量導引模態。色階為 |ψ|²／輸入峰值，顯示上限 0.5，紅色可能飽和。z=42.5 µm 的虛線僅對照 PDK MMI 主體長度；此模型沒有 taper 或實際輸出波導。</figcaption></figure>'''
body+=table('表 5｜標量模型的橫向網格比較',['dy [µm]','導引模態數','投影後輸入範數','z=42.5 µm 上半平面比例','沿 z 範數最大差'],[
(f"{r['dy_um']:.3f}",r['guided_modes'],f"{r['projected_input_norm']:.8f}",f"{r['upper_half_fraction']:.8f}",f"{r['longitudinal_norm_max_error']:.2e}") for r in DATA['new_scalar_propagation']['grids']])
body+='''<div class="callout warn">上半平面比例是 ∫y&gt;0 |ψ|²dy／∫all |ψ|²dy，並非 out1／out2 波導的耦合功率。投影後的範數守恆也不是完整元件的插入損耗驗證；本模型沒有計入反射、輻射連續譜與輸出端接收。請不要把這張圖用來宣稱 PDK 分光比或器件損耗。</div>
<h2 id="phase">6．MZI：相位如何變成輸出去向</h2><figure><img src="figures/m0_s2/phase_power.png" alt="本輪理想 MZI 的相位與輸出功率曲線"><figcaption>圖 3｜本輪重新計算的理想無損 MZI。上臂施加 θ；圖與 Lab01a 的局部埠定義一致：out1 在下、out2 在上。兩路輸入各為半功率，相對相位改變時總入射功率保持 1。</figcaption></figure>'''
body+=table('表 6｜相位、輸入與理想輸出',['條件','P(out1)','P(out2)','要解釋的物理意義'],[
('只打 in1；θ=0','0','1','兩臂再干涉，走到 cross 輸出。'),('只打 in1；θ=π/2','0.5','0.5','相位決定連續分光比例。'),('只打 in1；θ=π','1','0','切換到另一輸出。'),('雙路等功率；相差 π；θ=π/2','1','0','總功率不變，相干合到 out1。'),('雙路等功率；相差 0；θ=π/2','0','1','輸入功率相同，改相位即可改合光方向。')])
body+='''<p>在這個約定下，單路輸入的兩個功率為 sin²(θ/2)、cos²(θ/2)。M0 S1 測試 GDS 的上方外部埠叫 in0／out0；比較圖與程式時先核對上下位置，再對照埠名。</p><details><summary>手算題：100 µm 有效相位長度，要 π 相移需要多少 Δn_eff？</summary><p>θ=2π Δn_eff L／λ。取 L=100 µm、λ=1.55 µm，Δn_eff=0.00775。這是模態有效折射率變化，不是矽核心材料 Δn，也不能直接換算成 heater 電壓；後者還需要熱模型與校正。</p></details>
<h2 id="compare">7．與 Lab01a §7.6 的原始 FDTD 比較</h2>'''
body+=table('表 7｜本輪重算的既有 FDTD 指標',['引用案例','P(out1)／P(out2)','T','out1／已穿透總量','ER [dB]'],[
(r['case'],f"{r['power'][0]:.6f}／{r['power'][1]:.6f}",f"{r['T']:.6f}",f"{r['out1_fraction']:.6f}",f"{r['ER_dB']:.3f}") for r in INHERITED])
body+='''<p>完整原圖、幾何與限制見 <a href="../analysis/lab01a_7_6.html#mzi">Lab01a §7.6 分析</a>。原始場存於 sources/Lab01a/out，本輪重算各檔案的 SHA-256。T≈0.77–0.79 的差額不能全部歸因於數值損耗，也不能直接作為實際器件損耗。</p><div class="callout warn"><b>Meep 分支：</b>本輪執行介面的 WSL 清單查詢回報 Wsl/E_ACCESSDENIED，因此未驗證 Meep 安裝、未重新執行 FDTD，也沒有修改既有 WSL 使用者或環境。官方對 Windows 建議透過 WSL 使用 Meep，見 <a href="https://meep.readthedocs.io/en/latest/Installation/#installation-on-windows">Meep 官方安裝說明</a>。本輪 FEM、標量傳播、理想矩陣與引用 FDTD 的標示分開保留。</div>
<h2 id="submit">8．學員作答與可交付成果</h2><p>請用自己的話記錄：哪一張是截面模態、哪一張是傳播場？網格比較支持什麼？n_Si、n_eff、EIM n_core 為何不同？半平面積分為何不是輸出波導功率？</p><section class="panel"><label for="s2-name">學員姓名</label><input id="s2-name"><label for="s2-notes">預測、實際數據、模型差異與未完成事項</label><textarea id="s2-notes" placeholder="記錄三種寬度、網格差、相位輸出與資料來源。"></textarea><button id="s2-generate">產生 M0 S2 學習記錄 JSON</button><textarea id="s2-json" hidden readonly aria-label="M0 S2 學習記錄 JSON" style="min-height:220px"></textarea><p class="muted">產生後複製，以 UTF-8 存到 learner/m0_s2_observations.json。離開頁面前請保存。</p></section>
<script>document.querySelector('#s2-generate').addEventListener('click',()=>{const o=document.querySelector('#s2-json');o.hidden=false;o.value=JSON.stringify({step:'M0 S2',learner_name:document.querySelector('#s2-name').value,observations:document.querySelector('#s2-notes').value,date:new Date().toISOString(),instructor_review:'pending'},null,2);o.focus();o.select();});</script>
<h2 id="acceptance">9．本步驗收與 M0 S3 交接</h2>'''
body+=table('表 8｜本輪數值檢查',['檢查','狀態'],[(escape(k),'通過' if v else '未通過') for k,v in DATA['checks'].items()])
body+='''<p>核心成果：本輪 FEM 模態與網格／區域比較、本輪標量傳播場與網格比較、五個理想相位案例、引用 FDTD 指標、來源版本與學員觀察。Meep FDTD 重跑另列為未完成分支，不以標量模型替代它的驗證。</p><p><b>下一步 M0 S3：</b>把 MZI 的 θ／φ、複數光場與埠序整理成共用 2×2 傳輸矩陣；在固定約定下測試么正性、相位掃描與逐層傳播，交給後續 B7 模型。學員本人完成作答並經講師確認後，才記為本步學習通過。</p>'''
body=body.replace('450×220 nm',f"{round(DATA['parameters']['strip_width_um']*1000)}×{round(DATA['parameters']['strip_height_um']*1000)} nm")
body=body.replace('0.45×0.22 µm',f"{DATA['parameters']['strip_width_um']:.2f}×{DATA['parameters']['strip_height_um']:.2f} µm")
body=body.replace('Meep 官方安裝說明</a>。','Meep 官方安裝說明</a>；<a href="../work/m0_s2/out/wsl_inventory.json">本輪 WSL 查詢證據</a>。')
nav=''.join(f'<a href="{href}">{label}</a>' for href,label in [('../Lab06b_index.html','總覽與報告入口'),('plan.html','完整規劃'),('m0_s1.html','M0 S1｜工具鏈'),('m0_s2.html','M0 S2｜元件物理與光場'),('../analysis/lab01a_7_6.html','Lab01a §7.6 分析')])
html=f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M0 S2｜元件物理與光場分析｜Lab06b</title><link rel="stylesheet" href="../assets/course.css"></head><body><header class="top"><a href="../Lab06b_index.html"><b>LAB06b</b>　PIC Chip 學員實作課程</a><small>2026-10-31 · M0 S2</small></header><div class="layout"><aside><strong>學習與實作入口</strong>{nav}<strong>本輪證據</strong><a href="../work/m0_s2/out/physics_results.json">計算結果與版本 JSON</a><a href="../work/m0_s2/out/strip_mode_raw.npz">FEM 原始陣列 NPZ</a><a href="../work/m0_s2/out/mmi_modal_field.npz">標量傳播原始陣列 NPZ</a><p class="muted">{status}</p></aside><main><button class="print" onclick="window.print()">列印／另存 PDF</button><div class="hero"><div class="eyebrow">MODULE 0 · STEP 2 · 90 MIN</div><h1>M0 S2｜元件物理與光場分析</h1><p class="lead">先算出一個導模，再看懂多模干涉，最後用相位解釋 MZI 如何切換、分光與合光。</p><span class="tag ok">本輪 FEM／標量模型實算</span><span class="tag">原始資料可追溯</span><span class="tag wait">Meep FDTD 未重跑</span></div>{body}<footer>根目錄 C:\\EDA_Codex\\Lab06b · 2026-10-31（Asia/Taipei）<br>頁面由本輪 JSON 產生；單一模型的數值檢查不代表 Chip、熱模型或製程送件已完成。</footer></main></div></body></html>'''
(ROOT/'course/m0_s2.html').write_text(clean_course_html(html),encoding='utf-8')

# Integrate the step without erasing the verified S1 results.
for relative in ['Lab06b_index.html','course/plan.html','course/m0_s1.html','course/m0_s1_foundation.html','analysis/lab01a_7_6.html','reference/source_context.html']:
    p=ROOT/relative;text=p.read_text(encoding='utf-8');prefix='../' if '/' in relative else ''
    href=prefix+'course/m0_s2.html'
    if f'href="{href}"' not in text:
        text=text.replace('</aside>',f'<a href="{href}">M0 S2｜元件物理與光場</a></aside>',1)
    if relative=='Lab06b_index.html':
        text=text.replace('<h3>看懂光場傳播</h3><p>五張原圖、原始 NPZ、切換／分光／合光與耦合分析。</p><a href="analysis/lab01a_7_6.html">閱讀 Lab01a §7.6 →</a>',
                          '<h3>M0 S2｜元件物理</h3><p>本輪 FEM 模態、MMI 模態展開與相位分析；比較原始 FDTD 圖。</p><a href="course/m0_s2.html">進入 M0 S2 →</a>')
        marker='<!-- M0S2:STATUS -->'
        panel=f'{marker}<div class="callout good"><b>M0 S2 已建立：</b>{status}。<a href="course/m0_s2.html">前往新實作頁 →</a></div><!-- /M0S2:STATUS -->'
        if marker not in text:
            text=text.replace('<h2 id="goal">',panel+'<h2 id="goal">',1)
        else:
            text=re.sub(r'<!-- M0S2:STATUS -->.*?<!-- /M0S2:STATUS -->',lambda m:panel,text,flags=re.S)
        label='S1 工具鏈通過；S2 核心實作通過' if DATA['core_passed'] else 'S1 工具鏈通過；S2 待修正'
        text=text.replace('S1 核心工具鏈通過</td>',label+'</td>')
        text=re.sub(r'S1 工具鏈通過；S2 [^<]+</td>',lambda m:label+'</td>',text)
    text=text.replace('本輪只開始 M0 S1；','目前已完成 M0 S1，M0 S2 依本輪檢查結果驗收；')
    p.write_text(text,encoding='utf-8')
config=json.loads((ROOT/'config/course.json').read_text(encoding='utf-8'))
config['progress']['M0_S2']='core physics passed; FDTD rerun not performed; learner submission pending' if DATA['core_passed'] else 'physics checks unresolved'
config['progress']['M0_S3']='next step: shared optical model and unit checks'
(ROOT/'config/course.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
print('M0 S2 page rendered; core checks:',DATA['core_passed'])
