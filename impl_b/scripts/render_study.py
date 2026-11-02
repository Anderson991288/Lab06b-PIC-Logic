"""One continuous, first-person PIC report from all current C-workspace evidence.

Rendering does not run EDA. The fresh native-CAD extension carries separate
execution evidence; prior source lessons retain their original execution dates.
"""
from pathlib import Path
from datetime import datetime,timezone,timedelta
from urllib.parse import urlsplit,unquote
from html import escape
import json,re,posixpath,hashlib
from report_policy import Tree,clean_course_html,plain
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/single_report/out';OUT.mkdir(parents=True,exist_ok=True)
def load(p):return json.loads((ROOT/p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def table(caption,heads,rows):return '<div class="scroll"><table><caption>'+caption+'</caption><thead><tr>'+''.join('<th>'+x+'</th>' for x in heads)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(v)+'</td>' for v in r)+'</tr>' for r in rows)+'</tbody></table></div>'
def pre(t):return '<pre><code>'+escape(t)+'</code></pre>'
STEPS=[
('m0_s1','工具鏈、MZI 版圖與故障注入','work/m0_s1/out/toolchain_check.json',
 '我先確認正式工作位置與 Python／PDK／KLayout 的實際路徑，再建立帶 heater 的單顆 MZI 測試件，回讀正常版與故障版 GDS。',
 '我保留正常版零標記與 F1～F8 故障注入的實際命中，學到「工具能啟動」和「檢查器能抓錯」要分開證明。這時我完成的是測試件，還不是七顆 MZI 的 B7。'),
('m0_s2','元件物理與光場分析','work/m0_s2/out/physics_results.json',
 '我用 femwell 做 450×220 nm Si strip 的截面模態與網格比較，並用標量模態展開觀察均勻 MMI 的干涉與自成像；另回讀 Lab01a §7.6 的既有 NPZ。',
 'fine 網格得到 n_eff=2.353499831254645。這是均勻 SiO₂ 包覆模型，不是校準後的製程波導。我把材料折射率、模態有效折射率和 EIM 參數分開；Meep FDTD 沒有重跑，原始場圖與新求解不混在一起。'),
('m0_s3','共用光學模型與單元測試','work/m0_s3/out/model_results.json',
 '我把單顆 MZI、光場串接、損耗與埠序收進共用模型，固定上下埠、正相位與複數矩陣的慣例，執行 18 項模型測試。',
 '我確認相位和複數全域因子不能任意丟掉；一顆元件看似相同的功率，在多路相干串接後可能有不同干涉。後續所有步驟沿用同一套模型。'),
('m1_s1','光訊號編碼、參考光與功率判讀','work/m1_s1/out/encoding_results.json',
 '我用 OOK 振幅 0／1 表示資料，分清光場、光功率與接收判讀，再比較參考光移除、改相位及加入損耗的結果。',
 '我採用的 B7 輸入為 [x1,x2,x3,x4,R]，R 的振幅是 3，所以它的正規化功率是 9。參考光提供相干背景；它的相位、振幅與門檻都會影響邏輯判讀。'),
('m1_s2','B7 接線與 5×5 傳輸矩陣','work/m1_s2/out/b7_results.json',
 '我依四層 Brick 接線建立七顆 MZI、五條模式軌與六段 bypass，組出 5×5 複數傳輸矩陣 U，並逐層追蹤光場。',
 '我的差分讀取是零起算 out1 與 out3；資料輸入和 R 的順序始終固定。幾何接線、矩陣乘法順序與實體埠位必須對得上。'),
('m1_s3','複數加權和、光功率與差分判讀','work/m1_s3/out/readout_results.json',
 '我對 1000／1100 逐項列出兩個讀取埠的複數場貢獻，先做加權和，再取模平方，分解自項、干涉項與差分 ΔP。',
 '我看到漏掉交叉干涉項會把 ΔP 的符號算錯；把振幅差當成功率差也不成立。我採用 ΔP=P(out1)−P(out3)，並保留 ε 邊界與 signed margin。'),
('m1_s4','五功能相位與完整 80 筆比較','work/m1_s4/out/logic_results.json',
 '我固定同一顆 B7、編碼、參考光與讀取門檻，只切換五組相位程式，逐一重播 AND2、OR2、XOR2、AND4、OR4 的十六組輸入。',
 '五功能共 80/80 通過；即使某功能只用 x1、x2，我仍保留 x3、x4 的所有組合。我以 signed margin 追蹤距離判讀邊界的餘裕，而非只看 0／1。'),
('m1_s5','規格、相位與可攜交接','work/m1_s5/out/handoff_results.json',
 '我把規格、14 個相位通道、光學埠、真值表和共用模型封裝，使用 SHA-256 把相位、規格與表格綁定，並測試搬到新位置的消費端重播。',
 'M1 交接包保留 80 筆基準；相位單位是 rad，沒有推定 heater 電壓。後續回註候選另存，原始 pic_spec.json、phase_settings.json 和交接 ZIP 維持不變。'),
('m2_s1','PIC 邊界與光電 I/O','work/m2_s1/out/boundary_results.json',
 '我先界定 PIC 內外分工，再列出十個光學埠、十四個相位驅動角色與一個邏輯共地角色，追蹤資料、R、差分接收與未讀取輸出的去向。',
 '十四個控制角色不等於十四顆實體 PAD 加一顆 GND；外部 PD 電流差也不能直接等同 core 功率差。這些規劃到 S5 才落成實際幾何與接口表。'),
('m2_s2','CORNERSTONE PDK 電路與 80 筆比較','work/m2_s2/out/pdk_results.json',
 '我查詢已安裝 CORNERSTONE 的 MMI 埠位，建立 IPKISS／Caphe 電路，固定原規格與相位，與 M1 理想矩陣逐筆比較。',
 '80/80 一致，但我確認本機預設 MMI 使用理想 H 模型。這支持電路接線與模型慣例一致，尚未建立實測 MMI 絕對相位、損耗或色散資格。'),
('m2_s3','七顆 MZI core 版圖與 GDS','work/m2_s3/out/layout_results.json',
 '我由實際 PDK MMI 接點建立單顆 MZI，再放置七顆、連上 bypass 與 lead，加入十四個局部 heater、二十八個局部接觸並輸出 GDS。',
 '初版 core 光學跨度為 2076×120 µm。我用 KLayout 回讀數量、接點、埠與外框；這一步產生 core，外部 EC、PAD、GND 與完整檢查接續完成。'),
('m2_s4','KLayout 檢視與修改記錄','work/m2_s4/out/review_results.json',
 '我保留 S3 初版，檢視 MMI 接點、S 彎、heater 與金屬，將 S 彎規劃長度調為 24 µm，再回讀修改後的 core 與負例。',
 '採用版 core 光學跨度為 2140×120 µm，宣告外框 2200×220 µm，連續解析最小曲率半徑約 7.665199 µm。我把修改前後 GDS、幾何描述與圖像一起保存。'),
('m2_s5','EC 光學 I/O、heater PAD 與 GND','work/m2_s5/out/interface_results.json',
 '我把採用 core 與十個參考 EC、十條 fan route、十四個訊號 PAD、兩個共地 PAD 及共地走線合併，輸出三份實際接口表。',
 '晶片宣告區域為 3860×1640 µm；金屬是 14 訊號網加 1 共地網。已安裝匯出命名空間未找到可用的 qualified EC，因此我使用實際圖層上的參考 taper 幾何，耦合響應仍待校準。'),
('m2_s6','完整現有規則、幾何接線與修正','work/m2_s6/out/verification_results.json',
 '我完整執行原始 pre-DRC deck，找到兩筆埠文字間距違規；將十個埠標籤由 4 放大成 5 µm，同 deck 重跑，記錄由 2 筆降為 0 筆。',
 '六個實體圖層 XOR 不變。實際材料抽取確認 15 金屬網、14 heater 支路、66 光學端點與 33 組 MMI 外連接；八種錯誤 GDS 都被抓到，其中四種接錯在 DRC=0 時仍被網表比對拒絕。'),
('m2_s7','交付封裝、路徑回註與重播','work/m2_s7/out/replay_results.json',
 '我將 58 段 core 與 10 段 fan 的名義中心線對照到 33 個實際 GDS 連通區，在 M1 core 參考面加入 exp(+iβL)，再重播原相位。',
 '結果由理想 80/80 降為 53/80。我以逐軌相位追蹤解析推導補償，另存模型候選後回到 80/80；沒有用真值重新擬合。50 檔案交付包在中文／空白路徑搬移後，400 筆與幾何／pre-DRC 重播一致。'),
('m3_s1','從零重建與一致性檢查','work/m3_s1/out/rebuild_results.json',
 '我在兩個空目錄各放 33 個來源、設計與工具設定檔，沒有帶入既有 GDS、sidecar 或 out，重新產生 core、接口、標籤修正版、路徑與重播結果。',
 '兩輪各 13 項條件通過，每輪 400 筆與 S7 數值差為 0。原始 GDS SHA 不同；只統一 44 筆日期 payload 後，其他所有位元與 S6 相同，全圖層 XOR／文字及三份接口 CSV 也一致。'),
('m3_s2','獨立幾何量測與交叉驗證','work/m3_s2/out/crosscheck_results.json',
 '我用 gdstk／Shapely 直接讀同一 GDS，再與 KLayout 的六項線寬／間距量測比較，保留見證座標，另寫八個實際 GDS 控制檔。',
 '初版漏掉封閉 notch 的單側極限，把 Si 間距量成 1.579456 µm；修正後為 0.530000 µm。六項量測與 KLayout 的 1 nm 區間一致，54 項判讀、八控制與十二測試通過，原始完整 pre-DRC 仍為 0 筆。')]
MODULES={'m0':('M0｜我先建立工具、物理與共同模型','先學會辨認場、功率與幾何證據，再讓同一套模型支撐後續設計。'),'m1':('M1｜我把光場運算變成可切換邏輯','固定編碼與光路，使用複數矩陣、參考光和差分功率，建立可追溯的五功能基準。'),'m2':('M2｜我把邏輯模型做成 PIC 設計資料','從邊界、PDK 電路與 core，走到接口、規則修正、實際幾何接線和回註交付。'),'m3':('M3｜我重做一次，再換方法檢查','以乾淨來源重建與獨立幾何引擎，確認同一設計、同一問題能得到相同結論。')}
PAGE_PREFIX={('course/'+key+'.html'):key.replace('_','-') for key,*_ in STEPS}
PAGE_PREFIX['analysis/lab01a_7_6.html']='field-analysis'
PAGE_PREFIX['course/m0_s1_foundation.html']='foundation'
PAGE_PREFIX['course/virtuoso_calibre.html']='cad-reproduction'
def local_href(value,source,id_map):
    u=urlsplit(value)
    if u.scheme or u.netloc or value.startswith('data:'):return value
    target=posixpath.normpath(posixpath.join(posixpath.dirname(source),unquote(u.path))) if u.path else source
    if target in PAGE_PREFIX:
        anchor=PAGE_PREFIX[target]+('-'+u.fragment if u.fragment else '')
        return '#'+anchor
    if not u.path:return '#'+id_map.get(u.fragment,u.fragment) if u.fragment else value
    if target=='Lab06b_index.html':return '#report-top'
    if target.startswith('../'):raise ValueError('Link escapes project: '+value)
    return target+('?' +u.query if u.query else '')+('#'+u.fragment if u.fragment else '')
def source_section(source,prefix):
    raw=(ROOT/source).read_text(encoding='utf-8');tree=Tree(raw);main=next(n for n in tree.nodes if n.tag=='main')
    begin=raw.find('>',main.start)+1;end=raw.rfind('</main>',main.start,main.end);body=raw[begin:end];t=Tree(body);spans=[];scripts=[]
    for n in t.nodes:
        if not n.end:continue
        if n.tag=='script':
            if n.attrs.get('src'):raise ValueError('External script needs explicit packaging')
            scripts.append(body[body.find('>',n.start)+1:body.rfind('</script>',n.start,n.end)]);spans.append((n.start,n.end))
        if n.tag=='footer' or (n.tag=='div' and 'hero' in n.attrs.get('class','').split()) or (n.tag=='button' and 'print' in n.attrs.get('class','').split()):spans.append((n.start,n.end))
    merged=[]
    for a,b in sorted(spans):
        if merged and a<=merged[-1][1]:merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
        else:merged.append((a,b))
    for a,b in reversed(merged):body=body[:a]+body[b:]
    ids={n.attrs['id']:prefix+'-'+n.attrs['id'] for n in Tree(body).nodes if n.attrs.get('id')}
    def attr(m):
        key,quote,value=m.group(1),m.group(2),m.group(3)
        if key=='id':value=ids[value]
        elif key in ['for','list','form']:value=ids.get(value,value)
        elif key.startswith('aria-'):value=' '.join(ids.get(v,v) for v in value.split())
        else:value=local_href(value,source,ids)
        return key+'='+quote+value+quote
    body=re.sub(r'\b(id|href|src|for|list|form|aria-labelledby|aria-describedby)\s*=\s*([\'\"])(.*?)\2',attr,body)
    for id_,new in sorted(ids.items(),key=lambda x:-len(x[0])):body=body.replace('url(#'+id_+')','url(#'+new+')')
    body=re.sub(r'<(/?)h([1-6])\b',lambda m:'<'+m[1]+'h'+str(min(int(m[2])+2,6)),body)
    for old,new in [('學員實際執行','我實際執行'),('學員執行與修改範例','我執行與修改的範例'),('學員操作','我的操作'),('學員目標','我的目標'),('學員範例設定','我使用的範例設定'),('學員作答另行提交。',''),('學員作答各自驗收。',''),('學員作答待提交',''),('學員作答需本人完成。','')]:body=body.replace(old,new)
    code='\n'.join(scripts)
    # Review widgets change image src at runtime. Their figure prefixes were
    # relative to course/, so rebase these literal URL prefixes as well as HTML.
    code=re.sub(r'([\'\"])(figures/[^\'\"]*)\1',lambda m:m[1]+posixpath.join(posixpath.dirname(source),m[2])+m[1],code)
    code=code.replace('document.querySelectorAll(', 'REPORT_QUERY_ALL(').replace('document.querySelector(', 'REPORT_QUERY(').replace('document.getElementById(', 'REPORT_GET_ID(')
    boot='''const REPORT_SCOPE=document.getElementById(PREFIX);const REPORT_IDS=IDMAP;
const REPORT_SELECTOR=s=>s.replace(/#([A-Za-z_][\\w-]*)/g,(m,id)=>'#'+(REPORT_IDS[id]||id));
const REPORT_QUERY=s=>REPORT_SCOPE.querySelector(REPORT_SELECTOR(s));const REPORT_QUERY_ALL=s=>REPORT_SCOPE.querySelectorAll(REPORT_SELECTOR(s));const REPORT_GET_ID=id=>document.getElementById(REPORT_IDS[id]||id);
'''.replace('PREFIX',json.dumps(prefix)).replace('IDMAP',json.dumps(ids,separators=(',',':')))
    script='<script>(()=>{'+boot+'\n'+code+'\n})();</script>' if code.strip() else ''
    return body,script,dict(page=source,prefix=prefix,sha256=sha(ROOT/source),id_map=ids,script_count=len(scripts))
def render():
    now=datetime.now(timezone(timedelta(hours=8)));stamp=now.isoformat();date=now.strftime('%Y-%m-%d');records=[];sections=[];script_blocks=[];timeline=[]
    replay=load('work/m2_s7/out/replay_results.json');delivery=load('work/m2_s7/out/delivery_results.json');rebuild=load('work/m3_s1/out/rebuild_results.json');cross=load('work/m3_s2/out/crosscheck_results.json');current=load('config/m2_current_chip.json')
    toc=['<a href="#report-top">報告首頁</a>','<a href="#my-route">我的實作主線</a>','<a href="#my-results">最終結果總表</a>'];last=None
    for key,title,proof,action,learning in STEPS:
        module=key.split('_')[0];prefix=key.replace('_','-');label=key.upper().replace('_',' ');data=load(proof);executed=data.get('timestamp','原始紀錄未提供統一時間欄位')
        if module!=last:
            module_title,intro=MODULES[module];sections.append(f'<h2 id="module-{module}">{module_title}</h2><p class="module-intro">{intro}</p>');toc.append(f'<h2>{module_title.split("｜")[0]}</h2>');last=module
        toc.append(f'<a href="#{prefix}">{label}　{title}</a>')
        content,script,record=source_section('course/'+key+'.html',prefix);record.update(proof=proof,proof_sha256=sha(ROOT/proof),execution_timestamp=executed);records.append(record);script_blocks.append(script)
        sections.append(f'<article class="report-step" id="{prefix}"><div class="step-label">{label} · 我的實作紀錄</div><h3>{title}</h3><div class="experience"><h4>我做了什麼，得到什麼結論</h4><p>{action}</p><p>{learning}</p></div><p class="meta">原始執行紀錄：{escape(str(executed))} · <a href="{proof}">本步原始證據</a> · <a href="course/{key}.html">分頁閱讀</a></p>{content}<p class="source-note">本章由現行 C 版本的 {label} 技術內容整合；原始證據與程式可沿內文連結核對。整合報告不會重新執行該步 EDA／數值求解。</p></article>')
        timeline.append((f'<a href="#{prefix}">{label}</a>',escape(title),escape(str(executed)),f'<a href="{proof}">JSON</a>'))
    extensions=0
    if (ROOT/'course/virtuoso_calibre.html').is_file():
        proof='work/virtuoso_reproduction/out/reproduction_results.json';prefix='cad-reproduction'
        content,script,record=source_section('course/virtuoso_calibre.html',prefix);record.update(proof=proof,proof_sha256=sha(ROOT/proof),execution_timestamp=load(proof)['timestamp']);records.append(record);script_blocks.append(script);extensions=1
        sections.append(f'<article class="report-step" id="{prefix}"><div class="step-label">2026-10-31 · 本日新實測</div><h2>實機重現｜Virtuoso、Calibre Interactive／RVE 與 XStream 修正</h2><div class="experience"><p>我用現行 C 版本重新匯入並顯示七顆 MZI 晶片，執行 GUI 檢查、追查 200 點切割接縫與註記差異，再從空白 OA 重播。以下保存本日新截圖、原始結果、另存的跨工具 GDS 與可重播來源。</p></div>{content}</article>')
        toc+=['<h2>本日實機重現</h2>','<a href="#cad-reproduction">Virtuoso／Calibre 完整重現</a>','<a href="#cad-reproduction-virtuoso">⑥ 匯入並顯示</a>','<a href="#cad-reproduction-interactive">⑦ Interactive／RVE</a>','<a href="#cad-reproduction-fracture">⑧ 200→8191 修正</a>']
    appendices=[]
    for source,prefix,title,lead in [('analysis/lab01a_7_6.html','field-analysis','附錄 A｜我如何讀 Lab01a §7.6 光場圖','我保留既有場圖，回讀原始 NPZ 核對穿透、分光與消光比；以下是圖像、數值與限制的完整分析。'),('course/m0_s1_foundation.html','foundation','附錄 B｜我的理想 MZI 起步實驗','我先以不需 PDK 的理想模型核對五個案例，並保留可操作的相位預習。')]:
        content,script,record=source_section(source,prefix);records.append(record);script_blocks.append(script);appendices.append(f'<article class="report-step" id="{prefix}"><h2>{title}</h2><div class="experience"><p>{lead}</p></div>{content}</article>')
    toc+=['<h2>我的整體整理</h2>','<a href="#my-fixes">問題、原因與修正</a>','<a href="#my-files">最終設計與檔案</a>','<a href="#my-rerun">如何重播我的工作</a>','<a href="#my-boundary">我目前能證明的範圍</a>','<a href="#my-timeline">原始執行紀錄</a>','<a href="#field-analysis">附錄 A｜Lab01a §7.6</a>','<a href="#foundation">附錄 B｜理想 MZI</a>','<a href="course_overview.html">原總覽／課程規劃 ↗</a>']
    summary=f'''<div class="report-cover" id="report-top"><div class="eyebrow">PIC CHIP · MY HANDS-ON REPORT · {date}</div><h1>從光場到 PIC Chip<br>我的完整實作總報告</h1><p class="lead">以我自己作為學員，整理從環境、元件物理與光邏輯，到七顆 MZI 晶片版圖、規則修正、路徑回註、封裝重播及獨立幾何檢查的完整過程。</p><p class="meta">實作者／紀錄者：Codex（以學員身分） · 整理日期 {date}，Asia/Taipei<br>這份單頁報告整合目前 C 版本全部 17 步；各步原始執行時間保留在章內。整理報告沒有再次重跑 EDA／FEM／FDTD。</p><div class="report-tools"><button onclick="window.print()">列印／另存 PDF</button><a href="course_overview.html">原總覽</a><a href="#my-results">先看結果</a><a href="#m0-s1">從我的第一步開始</a></div><span class="tag ok">M0～M3 · 17 步</span><span class="tag">單顆 B7 · 7 MZI · 14 相位</span><span class="tag wait">實體功能／製程資格待建立</span></div>
<div class="report-kpis"><div><b>80 → 53 → 80</b><span>理想 → 原相位線長回註 → 模型補償</span></div><div><b>2 → 0</b><span>原始全套 pre-DRC：標籤修改前後</span></div><div><b>2 × 400</b><span>兩輪乾淨來源重建的模型比較</span></div><div><b>6 / 54</b><span>獨立幾何量測／規則判讀比較</span></div></div>
<div class="callout"><b>我的工作位置：</b>C:\\EDA_Codex\\Lab06b；D 槽唯讀。<b>我的產物：</b>PIC 設計資料、GDS、模型、接口表與可追溯結果。尚未進行流片／實體量測；本文不把理想或教學模型的通過當成實體晶片資格。</div>
<h2 id="my-route">我的實作主線</h2><p>我把問題分成四層：先看懂場與功率，接著讓同一個 B7 在固定光路下切換功能，再把規格落成幾何，最後檢查另一個目錄、另一套幾何引擎能否重現相同結論。每次出現不一致，我保留失敗結果與修正證據。</p><div class="step"><span>M0 工具／物理</span> → <span>M1 光場／邏輯</span> → <span>M2 版圖／交付</span> → <span>M3 重建／交叉檢查</span></div>
<figure><img src="course/figures/m2_s7/final_chip.png" alt="我最終採用的 B7 PIC GDS，由 KLayout 原生繪製，含十個參考 EC、十四訊號 PAD 與共地"><figcaption>我的最終設計｜KLayout 原生 GDS 視圖。這是設計幾何，並非已製造晶片照片；S7、M3 沿用 S6 採用版。</figcaption></figure>
<h2 id="my-results">我的最終結果總表</h2>'''
    if extensions:
        summary=summary.replace('這份單頁報告整合目前 C 版本全部 17 步；各步原始執行時間保留在章內。整理報告沒有再次重跑 EDA／FEM／FDTD。','這份單頁報告整合目前 C 版本全部 17 步，另新增本日 Virtuoso／Calibre 原生實機重現；各步原始時間保留。今日新跑 CAD 匯入、GUI、匯出與規則／接線重播，FEM／FDTD 未重跑。')
    summary+=table('結果與對應證據',['工作','我實際得到的結果','證據'],[
      ('物理與場','FEM fine n_eff=2.353499831254645；Lab01a NPZ 重新分析；Meep FDTD 未重跑','<a href="#m0-s2">M0 S2</a> · <a href="#field-analysis">附錄 A</a>'),
      ('理想與 PDK 電路','五功能 × 十六輸入 = 80/80；本機預設 MMI 為理想 H','<a href="#m1-s4">M1 S4</a> · <a href="#m2-s2">M2 S2</a>'),
      ('晶片幾何','7 MZI／14 MMI；10 參考 EC；14 訊號 PAD＋2 GND；宣告區域 3860×1640 µm','<a href="#m2-s5">M2 S5</a>'),
      ('規則與實際接線','原始 pre-DRC 31 報告類別、2→0；15 金屬網、14 heater 支路、33 光學連接','<a href="#m2-s6">M2 S6</a>'),
      ('線長回註','58 core＋10 fan 路徑綁定；core 模型原相位 53/80，解析候選 80/80','<a href="#m2-s7">M2 S7</a>'),
      ('可攜交付',f'{delivery["files"]} 檔案＋manifest；中文／空白路徑 400 筆與幾何重播一致','<a href="delivery/Lab06b_M2_PIC_delivery.zip">M2 ZIP</a>'),
      ('來源重建','兩輪各 13 條件通過；每輪 400 筆差為 0；GDS 除日期 payload 外位元一致','<a href="#m3-s1">M3 S1</a>'),
      ('獨立幾何','Si 0.350／0.530、HT 0.900／50.000、金屬 8.000／13.500 µm；54 判讀一致','<a href="#m3-s2">M3 S2</a>')]+([('本日原生 CAD 重現','Virtuoso 43 cells／0 error；Calibre GUI／RVE 16 項全 0；XStream 200→8191、原始 pre-DRC 8→0；乾淨 OA 重播通過','<a href="#cad-reproduction">新實測證據與跨工具檔</a>')] if extensions else []))
    ending='<h2 id="my-fixes">我遇到的問題、原因與修正</h2>'
    ending+=table('從失敗到可重現結果',['問題','我怎麼判斷','我留下的修正／範圍'],[
      ('Meep 執行介面未通過','Wsl/E_ACCESSDENIED，不能宣稱已重跑 FDTD','以明示的新 FEM／標量模型與既有 NPZ 分開記錄，保留未重跑範圍。'),
      ('S6 的兩筆文字間距違規','marker 位於 in0／out0 的 GDS 100 字形','十個埠標籤 4→5 µm，同 deck 2→0；六個實體圖層 XOR 不變。'),
      ('原相位加入線長後只剩 53/80','追蹤每軌 βL，相對相位改變相干加權和','解析 φ／θ 偏移另存模型候選，恢復 80/80；未推定電壓或實體資格。'),
      ('GDS 原始 SHA 不同','BGNLIB／BGNSTR 共 44 筆日期 payload 不同','只統一日期後 SHA 一致，再以全圖層 XOR／文字核對，原 SHA 仍保留。'),
      ('獨立間距曾量到 1.579456 µm','封閉 notch 的最短線落在邊界，被 strict disjoint 排除','加上單側空隙極限判讀，得到 0.530000 µm；保留前後值、見證與測試。'),
      ('Windows 原生數值環境','DLL 路徑與 cp950 log 字元影響程序執行','以腳本設定／還原各環境 DLL 路徑；工具 log 使用可用字元，控制案例重新通過。')])
    ending+='<h2 id="my-files">我最後保留的設計與重播資料</h2>'
    if extensions:ending+='<div class="callout good"><b>本日新增的跨工具互通檔：</b><a href="work/virtuoso_reproduction/out/exports_final/B7_crosscad_final.gds">B7_crosscad_final.gds</a> · <a href="delivery/Lab06b_Virtuoso_Calibre_reproduction.zip">Virtuoso／Calibre 重現封裝</a>。只另存 GDS100 註記修正，六個實體圖層與原採用版相同；下表的 S6 原版與 M1／M2 原交接包仍保留。</div>'
    ending+=table('正式採用資料與證據索引',['檔案','用途'],[
      ('<a href="config/m2_current_chip.json">晶片採用索引</a> · <a href="work/m2_s6/out/after/b7_ec_pad.gds">最終 GDS</a>','S6 採用版；後續沒有用重建副本或控制檔取代。'),
      ('<a href="pic_spec.json">原始規格</a> · <a href="phase_settings.json">原始相位</a>','M1 既定意圖，供模型、版圖與重播共同綁定。'),
      ('<a href="work/m2_s7/out/phase_settings_backannotated.json">模型候選相位</a> · <a href="config/m2_backannotation.json">回註模型</a>','與原相位分開；rad，非電壓。'),
      ('<a href="work/m2_s6/out/after/optical_io.csv">光學 I/O</a> · <a href="work/m2_s6/out/after/pad_heater_map.csv">heater PAD</a> · <a href="work/m2_s6/out/after/ground_pads.csv">GND PAD</a>','採用版接口座標與邏輯對照。'),
      ('<a href="delivery/m1_handoff.zip">M1 ZIP</a> · <a href="delivery/Lab06b_M2_PIC_delivery.zip">M2 PIC ZIP</a> · <a href="delivery/m2_pic_delivery/manifest.json">manifest</a>','可攜交接／模型重播與檔案 SHA；工具、PDK、專有 deck 另用本機安裝。'),
      ('<a href="config/m3_acceptance.json">兩輪重建索引</a> · <a href="config/m3_crosscheck_result.json">獨立幾何索引</a>','新產物、比較、見證與資格範圍。'),
      ('<a href="work/m3_s2/out/comparison_54.csv">54 項比較 CSV</a> · <a href="work/m3_s2/out/method_difference.json">方法差異</a>','保留獨立量測與 KLayout 的相同／不同之處。')])
    ending+=f'<p class="meta">採用 GDS SHA-256：<code>{cross["gds_sha256"]}</code><br>M2 ZIP SHA-256：<code>{delivery["zip_sha256"]}</code></p><h2 id="my-rerun">如何重播我的工作</h2>'
    ending+=pre(r'''Set-Location -LiteralPath 'C:\EDA_Codex\Lab06b'
# 重做某一個步驟：使用對應 scripts/run_m*.ps1
& .\scripts\run_m2_s7.ps1   # 路徑回註、封裝與搬移重播
& .\scripts\run_m3_s1.ps1   # 兩個空目錄從來源／設計輸入重建
& .\scripts\run_m3_s2.ps1   # gdstk／Shapely 獨立量測與 KLayout 比對
# 只重建閱讀報告，不重新執行 EDA：
& 'C:\luceda\luceda_2026033\envs\device_sim\python.exe' .\scripts\render_course.py''')
    ending+='<h2 id="my-boundary">我目前能證明的範圍</h2><p>我完成了可追溯的 PIC 設計資料、模型計算、採用 GDS、原始現有 pre-DRC、幾何網表比對、來源重建與選定獨立幾何量測。原相位回註的 53/80 失敗與模型候選的 80/80 都保留在同一份報告中。</p><p>實際 EC／MMI／波導／彎曲響應、heater 偏壓與熱串擾、共地壓降、封裝與量測，以及 foundry 完整 DRC／製程專用 LVS／流片資格，仍需要對應的校準與簽核。這些不能由理想模型、pre-DRC 零筆或幾何一致性直接推定。</p><h2 id="my-timeline">各步原始執行紀錄</h2><p class="muted">以下時間從各步結果 JSON 讀取；報告整理時間與實際求解／建置時間分開保存。</p>'
    ending+=table('17 步來源時間與證據',['步驟','主題','原始紀錄時間','證據'],timeline)
    ending+=''.join(appendices)
    footer=f'<footer class="report-footer">整理者：Codex（以我為學員的實作紀錄） · {escape(stamp)}<br>正式工作區 C:\\EDA_Codex\\Lab06b；D 槽唯讀。此頁沒有學員驗收／交付表單。<br><a href="work/single_report/out/report_sources.json">本總報告來源清單與 SHA</a> · <a href="scripts/render_study.py">總報告產生程式</a> · <a href="course_overview.html">原總覽</a> · <a href="#report-top">回到報告首頁</a></footer>'
    viewer='''<script>(()=>{const nav=document.querySelector('.report-nav'),toggle=document.querySelector('#toc-toggle');toggle.addEventListener('click',()=>{const open=nav.classList.toggle('is-open');toggle.setAttribute('aria-expanded',String(open));});nav.querySelectorAll('a[href^="#"]').forEach(a=>a.addEventListener('click',()=>{if(innerWidth<=820){nav.classList.remove('is-open');toggle.setAttribute('aria-expanded','false');}}));const articles=[...document.querySelectorAll('article.report-step')],links=[...nav.querySelectorAll('a[href^="#"]')],progress=document.querySelector('#reading-position');const observer=new IntersectionObserver(entries=>{const hit=entries.filter(e=>e.isIntersecting).sort((a,b)=>a.boundingClientRect.top-b.boundingClientRect.top)[0];if(!hit)return;links.forEach(a=>{if(a.hash==='#'+hit.target.id)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current');});progress.textContent='目前閱讀：'+hit.target.querySelector('h2,h3').textContent;},{rootMargin:'-5% 0px -70% 0px'});articles.forEach(a=>observer.observe(a));})();</script>'''
    html='<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>從光場到 PIC Chip｜我的完整實作總報告｜Lab06b</title><link rel="stylesheet" href="assets/study.css"></head><body data-report="lab06b-single-page"><div class="report-shell"><nav class="report-nav" aria-label="完整實作總報告目錄"><b>LAB06b · PIC Chip</b><p class="minor">我的實作總報告<br>M0～M3 · 17 步 · '+date+'</p><button class="mobile-toc" id="toc-toggle" aria-expanded="false" aria-controls="toc-links">展開／收合目錄</button><div class="toc-links" id="toc-links">'+''.join(toc)+'</div><div class="read-progress" id="reading-position">從我的第一步開始閱讀</div></nav><main class="report-main">'+summary+''.join(sections)+ending+footer+'</main></div>'+''.join(script_blocks)+viewer+'</body></html>'
    assert '學員姓名' not in html and '學員驗收與交付' not in html
    html=clean_course_html(html)
    old_index=(ROOT/'Lab06b_index.html').read_text(encoding='utf-8')
    if 'data-report="lab06b-single-page"' not in old_index:(ROOT/'course_overview.html').write_text(old_index,encoding='utf-8')
    (ROOT/'Lab06b_index.html').write_text(html,encoding='utf-8')
    (ROOT/'study.html').write_text('<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0;url=Lab06b_index.html"><title>我的 PIC Chip 實作總報告</title></head><body><p><a href="Lab06b_index.html">開啟單頁完整實作總報告</a></p></body></html>',encoding='utf-8')
    record=dict(schema='lab06b.single_report_sources.v1',generated_at=stamp,narrator='Codex as the learner/implementer',canonical_report='Lab06b_index.html',overview='course_overview.html',alias='study.html',course_steps=17,appendices=2,
        source_pages=records,technical_reexecution=bool(extensions),original_steps_reexecuted=False,native_CAD_extensions=extensions,original_D_written=False,report_sha256=sha(ROOT/'Lab06b_index.html'),generator_sha256=sha(Path(__file__)),css_sha256=sha(ROOT/'assets/study.css'),technical_bindings={p:sha(ROOT/p) for p in ['pic_spec.json','phase_settings.json','config/m2_current_chip.json','config/m2_delivery.json','delivery/m1_handoff.zip','delivery/Lab06b_M2_PIC_delivery.zip','work/m2_s6/out/after/b7_ec_pad.gds','work/m2_s7/out/replay_results.json','work/m3_s1/out/rebuild_results.json','work/m3_s2/out/crosscheck_results.json']})
    (OUT/'report_sources.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Single-page report:',len(html.encode('utf-8')),'bytes;',len(STEPS),'steps;',extensions,'native-CAD extension; 2 full appendices; rendering only')
render()
