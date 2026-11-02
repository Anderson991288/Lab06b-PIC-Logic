"""產生合併後的課程總目錄 C:\\LAB\\Lab06b\\Lab06b_index.html。
以主線（實作 A）的總目錄為底，加上：兩套實作怎麼合併、主線的設計選擇、進度表的對照欄、關卡表、
還沒有答案的問題、重跑方式與新的資料夾結構。最後嵌入 CSS（單檔）並檢查不含本機路徑與其他計畫字樣。
用法：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\merge\\build_index.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_course import A, LAB, inline, leaks  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

ALT = {
    "m0_s1": "一致：測試件幾何、DRC 0、F1–F8 相同；另有理想 MZI 暖身（5/5）。",
    "m0_s2": "n<sub>eff</sub> 2.353500（差 3×10<sup>−4</sup>）；沒有自己的 FDTD，MZI 光場用舊資料。",
    "m0_s3": "同一個 T(θ,φ) 約定；18/18 測試、5/5 故障被抓到。",
    "m1_s1": "結論一致；裕量用固定門檻定義，數字因此不同。",
    "m1_s2": "U 一致：全交叉走向、結構零、1100 的 ΔP＝2.0。",
    "m1_s3": "改用 AND2 相位手算，各自正確。",
    "m1_s4": "80/80，五個最小裕量一致。",
    "m1_s5": "都通過；SHA-256 綁定方向與 heater 通道順序不同。",
    "m2_s1": "邊界一致；沒有量化外部容許誤差，另有 5 份做壞的邊界被拒絕。",
    "m2_s2": "80/80，五個最小裕量一致。",
    "m2_s3": "<b>佈局分歧：</b>旁路是直線、短 21.13 µm；這一步沒有 DRC。",
    "m2_s4": "審查後把 S 彎拉長到 24 µm（最小半徑 7.67 µm）。",
    "m2_s5": "晶片 3860 × 1640 µm；扇入不等長（差 167.861 µm）；15 個網路。",
    "m2_s6": "初跑 2 筆標籤間隙違規，標籤放大後 0；8 個故障都被抓到。",
    "m2_s7": "線長回註用原相位只有 53/80（原因待確認）；在 Virtuoso 視窗看到同樣的 200 頂點切割現象。",
    "m3_s1": "兩輪重建；GDS 日期統一後逐位元相同。",
    "m3_s2": "第三方讀檔；3 層 6 項量測、54 項判讀一致。",
}

MERGE = """
<h2 id="merge">兩套獨立實作，合併成一份課程</h2>
<p>這份課程由兩套各自獨立完成的實作合併而成。兩套都從同一份原始教材出發，各自寫程式、各自跑結果，不共用數字。合併的方式是：</p>
<ul>
<li><b>主線：</b>每一頁的正文、數字與驗收沿用實作 A（程式與證據在 <code>impl_a/</code>）。</li>
<li><b>對照：</b>每一頁新增一節「對照：另一套獨立實作」，寫出實作 B（程式與證據在 <code>impl_b/</code>）的做法、結果、和主線一致或不同的地方，以及只有它做的檢查與圖。</li>
<li><b>不互相改寫：</b>兩套程式各自保留原樣，各自可以重跑；頁面上兩邊的數字都由各自的證據檔而來。</li>
</ul>
<table><tr><th>範圍</th><th>兩套的關係</th></tr>
<tr><td>M0 s1 – M2 s2</td><td>模型、約定與 80 筆真值表一致，等於多了一次獨立驗證。差異多半是定義或示範方式不同（例如裕量的門檻、手算用的相位）。</td></tr>
<tr><td>M2 s3 – M3 s2</td><td>兩套做出<b>不同的佈局</b>：旁路是否等長、S 彎長度、晶片尺寸、扇入、接地方式都不同。這些步驟的數字不能混用，頁面上分開列。</td></tr></table>

<h3 id="choice">主線為什麼採用實作 A 的佈局</h3>
<ol>
<li><b>旁路等長：</b>主線從佈局抽出的電路不改相位就是 80/80，1530–1570 nm 都通過。實作 B 的直旁路，正好是主線 M2 s3 的故障案例：1550 nm 仍全對，但重新校正後只剩 ±3 nm 可用。</li>
<li><b>扇入等長：</b>實作 B 的五路輸入長度差 167.861 µm；主線的故障注入顯示，扇入不等長會造成 27/80 錯。</li>
<li><b>每一步都有 DRC 與從佈局抽出的電路：</b>實作 B 在 M2 s3 沒有做 DRC，線長回註要到 M2 s7 才做，並發現原相位只剩 53/80。</li>
<li><b>交付包能重建 GDS：</b>主線的交付包可以只用包內程式重建出相同的 969 個多邊形。</li>
</ol>
<p>實作 B 的長處都放進各頁的對照一節：更大的 S 彎半徑、以竄改後重算雜湊的交叉綁定測試、GDS 日期統一後比對雜湊、Virtuoso 視窗與 Calibre RVE 操作、真實 DRC 違規的修正流程、量測方法本身出錯的案例。</p>
"""

GATES = """
<h3 id="gates">關卡與交接</h3>
<table><tr><th>關卡</th><th>通過條件</th><th>沒通過時</th></tr>
<tr><td>G0 工具鏈</td><td>IPKISS／PDK 實際執行、正常 MZI DRC 0、F1–F8 故障命中、原始 log 留存</td><td>確認實際路徑、授權、規則檔與版本，修正後重跑。</td></tr>
<tr><td>G1 邏輯</td><td>固定 B7 光路、埠序與判讀；AND2／OR2／XOR2／AND4／OR4 各 16 組，共 80 組</td><td>核對輸入編碼、相位與上下埠；ΔP 接近 0 視為邊界。</td></tr>
<tr><td>G2 版圖</td><td>模型和 GDS 共用埠名與相位標籤；EC、接墊、接地與未讀取的輸出都有去向；旁路與扇入等長</td><td>保留問題座標與前後圖，改 Python 參數重出。</td></tr>
<tr><td>G3 幾何與連接</td><td>平台規則全部通過，且用到的規則以故障注入證明會觸發；光路連接、電氣開路短路與接墊命名另外驗證</td><td>DRC 不能代替連接檢查。</td></tr>
<tr><td>G4 交付</td><td>線長回填後功能重跑；GDS、相位、埠／接墊表、工具版本與 manifest 一致；解壓後能重建與重驗</td><td>缺少真實傳播或元件模型時，寫明限制；送件仍依平台簽核。</td></tr></table>
<p class="muted">關卡表取自實作 B 的課程規劃，G2–G4 依主線的做法補上等長、規則觸發與重建三個條件。</p>
"""

OPEN = """
<h2 id="open">還沒有答案的問題</h2>
<ul>
<li><b>S 彎半徑：</b>主線的最小曲率半徑 5.23 µm 通過 PDK DRC，但兩套都沒有彎道損耗的模擬或量測；實作 B 認為應該拉大到 7.5 µm 以上。</li>
<li><b>實作 B 的 53/80：</b>可能來自直旁路的真實長度差，也可能來自回註模型沒有計入 MMI 本體長度，尚未確認。</li>
<li><b>模型：</b>PDK 電路模型是理想元件（MMI 無損 50:50，波導預設 n<sub>eff</sub>＝1、n<sub>g</sub>＝2）；MMI 相位用等長條狀波導等效。</li>
<li><b>沒有實體驗證：</b>沒有下線、封裝與量測；Virtuoso 沒有 CORNERSTONE 的製程套件；沒有 Calibre LVS。</li>
<li><b>學員作答：</b>各步的判讀練習與作答範本（<code>impl_b/learner/</code> 的 17 個 JSON）需要學員本人完成，由講師驗收。</li>
</ul>

<h2 id="replay">重跑方式</h2>
<table><tr><th>實作</th><th>怎麼跑</th><th>搬到這個資料夾後的確認（2026-11-01）</th></tr>
<tr><td>主線（A）</td><td>在 <code>impl_a</code> 資料夾，依各步「學員操作」執行；或用 <code>work\\m3_s1\\rebuild_all.py</code> 一次重建。</td><td>從零重建：126 個輸出中 122 個相同或內容等價，4 個只差在檔案裡記錄的執行日期。</td></tr>
<tr><td>實作 B</td><td>在 <code>impl_b</code> 資料夾執行 <code>scripts\\run_m*_s*.ps1</code>（每步一支）。</td><td>重跑 M1 s4、M2 s2、M3 s2 都通過。它的程式會核對自己記錄的來源 SHA-256，所以程式內容保持原樣；其中 M3 s1 的重建程式限定在原資料夾執行，在這裡不能直接重跑。</td></tr></table>
"""

LAYOUT = """<pre>Lab06b
├─ Lab06b_index.html   本頁：規劃、進度、所有步驟入口
├─ course\\             17 步合併頁（單檔，圖已嵌入）；course.css；figures\\（主線）、figures_b\\（實作 B）
├─ impl_a\\             主線的程式與證據：EDA_paths.json、env\\、sources\\、spec\\、work\\&lt;step&gt;\\out\\
├─ impl_b\\             實作 B 的程式與證據：scripts\\、work\\、config\\、evidence\\、learner\\、tools\\KLayout\\
└─ merge\\              合併用工具：relocate.py（改路徑）、build_course.py、build_index.py、fragments\\（各頁對照段落）</pre>"""


def main():
    t = (A / "Lab06b_index.html").read_text(encoding="utf-8")
    t = t.replace('<a href="#status">進度總覽</a>',
                  '<a href="#merge">兩套實作與合併</a><a href="#status">進度總覽</a>', 1)
    t = t.replace('<a href="#layout">資料夾結構</a>',
                  '<a href="#open">還沒有答案的問題</a><a href="#replay">重跑方式</a><a href="#layout">資料夾結構</a>', 1)
    t = re.sub(r"總目錄｜2026-10-31", "總目錄｜2026-11-01", t)
    t = t.replace('<h2 id="status">', MERGE.strip() + '\n\n<h2 id="status">', 1)
    t = t.replace("<th>說明</th></tr>", "<th>說明（主線）</th><th>對照：實作 B</th></tr>", 1)

    def add_col(m):
        return m.group(0).replace("</tr>", f"<td>{ALT[m.group(1)]}</td></tr>")
    t, n = re.subn(r'<tr><td><a href="course/(m\d_s\d)\.html">M\d s\d</a></td>.*?</tr>', add_col, t, flags=re.S)
    assert n == 17, n
    t = t.replace('<h2 id="field">', GATES.strip() + '\n\n<h2 id="field">', 1)
    t = t.replace('<h2 id="improve">', OPEN.strip() + '\n\n<h2 id="improve">', 1)
    t = re.sub(r'(<h2 id="layout">資料夾結構</h2>\s*)<pre>.*?</pre>', lambda m: m.group(1) + LAYOUT, t, flags=re.S)
    t = t.replace("<footer>課程總目錄｜版本 2｜2026-10-31</footer>",
                  "<footer>課程總目錄｜版本 3（兩套實作合併）｜2026-11-01</footer>")
    assert "版本 3" in t and 'id="merge"' in t and 'id="gates"' in t and 'id="open"' in t
    page = LAB / "Lab06b_index.html"
    out, _ = inline(page, t)
    page.write_text(out, encoding="utf-8")
    bad = leaks(out)
    print(f"Lab06b_index.html: {len(out.encode('utf-8')) / 1024:.0f} KB", "LEAK " + str(bad) if bad else "")
    for href in sorted(set(re.findall(r'href="(course/[^"#]+)', out))):
        assert (LAB / href.split("?")[0]).exists(), href
    return not bad


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
