"""把 out/delivery_check.json、交付包的 signoff.json、介面表與 eda/out/virtuoso_calibre.json 寫進 course/m2_s7.html 的 BEGIN/END 區塊。

用法：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m2_s7\\build_page.py
只取代標記之間的內容；先寫暫存檔、檢查標記完整後再原子替換。
"""
import csv
import html
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGE = HERE.parents[1] / "course" / "m2_s7.html"
PKG = HERE / "out" / "PIC_delivery"
R = json.loads((HERE / "out" / "delivery_check.json").read_text(encoding="utf-8"))
S = json.loads((PKG / "reports" / "signoff.json").read_text(encoding="utf-8"))
M = json.loads((PKG / "manifest.json").read_text(encoding="utf-8"))
V = json.loads((HERE / "eda" / "out" / "virtuoso_calibre.json").read_text(encoding="utf-8"))


def table(head, rows):
    return ("<table><tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</table>")


def rows_of(name):
    with open(PKG / "interfaces" / name, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


blocks = {}
rows = [[i["item"], i["step"], html.escape(i["result"]), "通過" if i["ok"] else "<b>不通過</b>"] for i in S["items"]]
rows.append(["交付包解壓重驗", "M2 s7", "清單、LVS／電氣、重建比對、DRC、竄改測試", "通過" if R["all_ok"] else "<b>不通過</b>"])
VI, GEO, KLR, CAL = V["virtuoso"], V["geometry"], V["klayout"], V["calibre"]
v_ok = (VI["stream_in"]["errors"] == VI["stream_in"]["warnings"] == 0 and all(r["xor_area"] == 0 for r in GEO["8191"].values())
        and KLR["virtuoso_8191"]["total"] == 0)
rows.append(["Virtuoso 匯入／匯出", "M2 s7 ⑥", f"匯入 {VI['stream_in']['errors']} 錯誤 {VI['stream_in']['warnings']} 警告；"
             f"8191 點匯出與簽核版七層 XOR 0、KLayout {KLR['virtuoso_8191']['total']} 違規", "通過" if v_ok else "<b>不通過</b>"])
c_ok = V["all_ok"] and all(c["klayout"] == c["calibre"] for c in V["cases"])
rows.append(["Calibre DRC 對照", "M2 s7 ⑦", f"簽核版 {CAL['signed']['total']} 違規；規則故障檔、{len(V['cases'])} 個邊界案例都與 KLayout 一致",
             "通過" if c_ok else "<b>不通過</b>"])
blocks["summary"] = (table(["項目", "在哪一步", "結果", "判定"], rows)
                     + f'<p>全部針對同一個檔案：<code>layout/B7_final.gds</code>，SHA-256 <code>{R["final_sha256"]}</code>。'
                       f'範圍：{html.escape(S["scope"])}。</p>')

op = rows_of("optical_ports.csv")
pm = rows_of("pad_map.csv")
blocks["iface"] = (
    "<h3>光學端面（optical_ports.csv）</h3>"
    + table(["端面", "訊號", "側", "座標（µm）", "核心埠", "用途"],
            [[r["port"], r["signal"], "左" if r["side"] == "left" else "右", f"({float(r['facet_x_um']):g}, {float(r['facet_y_um']):g})",
              r["core_port"], {"input": "輸入", "readout": "<b>讀取</b>", "monitor": "監看"}[r["role"]]] for r in op])
    + "<h3>接墊（pad_map.csv）</h3>"
    + table(["接墊", "中心（µm）", "側", "接到", "heater 中心（µm）"],
            [[r["pad"], f"({float(r['center_x_um']):g}, {float(r['center_y_um']):g})", "上" if r["side"] == "top" else "下",
              (f"{r['mzi']} 的 {'φ' if r['phase'] == 'phi' else 'θ'}（rail {r['rail']}）" if r["role"] == "heater_signal" else "回流匯流排"),
              (f"({float(r['heater_center_x_um']):g}, {float(r['heater_center_y_um']):g})" if r["heater_center_x_um"] else "—")]
             for r in pm]))

desc = {"layout": "晶片版圖、已審查的核心", "reports": "DRC 摘要與原始報告、連接檢查、簽核表、核心審查、晶片電路模擬",
        "interfaces": "規格、連接表、I/O 表、外部需求、真值表、光學埠表、接墊表、佈局資訊",
        "simulation": "相位設定、PDK 電路的 U 矩陣與 80 筆", "figures": "全圖、接墊與金屬網、核心、LVS 抽出圖",
        "source": "產生與檢查版圖的程式（保留資料夾結構）、它讀的規格與輸入"}
blocks["package"] = (
    f'<div class="kpis"><div class="kpi"><b>{R["n_files"]}</b>個檔案</div><div class="kpi"><b>{R["zip_kb"]} KB</b>zip</div>'
    f'<div class="kpi"><b>{len(R["leaks"])}</b>個檔案含本機路徑</div></div>'
    + table(["資料夾", "檔案數", "內容"], [[f"<code>{k}/</code>", v, desc[k]] for k, v in R["folders"].items()]
            + [["根目錄", 5, "README.md、manifest.json、check_delivery.py、verify_gds.py、rebuild_gds.py"]])
    + '<p>下載：<a href="../work/m2_s7/out/B7_PIC_delivery.zip">B7_PIC_delivery.zip</a>　／　'
      '<a href="../work/m2_s7/out/PIC_delivery/README.md">README</a>　／　'
      '<a href="../work/m2_s7/out/PIC_delivery/manifest.json">SHA-256 清單</a></p>')

c, v, b, d, t = R["check_delivery"], R["verify_gds"], R["rebuild_gds"], R["drc"], R["tamper"]
lv, el = v["result"]["lvs"], v["result"]["electrical"]
blocks["verify"] = table(["檢查", "需要什麼", "結果"], [
    ["zip 的 CRC", "Python", "通過" if R["zip_crc_ok"] else "<b>失敗</b>"],
    ["check_delivery.py：逐檔 SHA-256", "Python", f"{c['result']['checked']} 個檔案相符、清單外的檔案 {len(c['result']['extra'])} 個"],
    ["verify_gds.py：只讀 GDS 的 LVS 與電氣", "numpy、shapely、matplotlib",
     f"{lv['n_mzi']} MZI、{lv['n_links']} 連線、{lv['n_ext']} 外部埠、{lv['n_heaters']} heater 與規格一致；"
     f"{el['n_nets']} 個金屬網、問題 {len(el['problems'])} 項"],
    ["rebuild_gds.py：用包內程式重建", "IPKISS、CORNERSTONE PDK", f"重建 {b['result']['rebuilt']} 個多邊形，與交付版 {b['result']['polygons']} 個"
     + ("完全相同" if b["result"]["ok"] else "<b>不同</b>")],
    ["DRC（本機規則檔）", "KLayout、CORNERSTONE 規則檔", f"{d['total']} 違規、外框外 {d['outside']}（{d['n_rules']} 條規則）"],
    ["竄改測試：GDS 改 1 個位元組", "Python", ("抓到：" + "、".join(t["problems"] or [])) if t["detected"] else "<b>沒抓到</b>"],
    ["改回原值", "Python", "通過" if t["restored_ok"] else "<b>失敗</b>"],
])

# ⑥ Virtuoso
GS = VI["gds"]
oa_n, oa_max = {}, {}
for k, s in VI["oa"]["shapes"].items():
    lay = k.split("/")[0].lstrip("L")
    oa_n[lay] = oa_n.get(lay, 0) + s["n"]
    oa_max[lay] = max(oa_max.get(lay, 0), s["max_points"])
LAYERS = ["3", "4", "5", "39", "41", "99", "100"]
LNAME = {"3": "GDS 3 Si", "4": "GDS 4", "5": "GDS 5 薄矽", "39": "GDS 39 TiN", "41": "GDS 41 Ti/AL", "99": "GDS 99 外框", "100": "GDS 100 標記"}


def xor_txt(v, lay):
    r = GEO[v][lay]
    return "0" if r["xor_area"] == 0 else f"<b>{r['xor_area']:.4f} µm²（{r['xor_count']} 塊）</b>"


sig, dfl, m81 = GS["signed"], GS["out_default"], GS["out_8191"]
assert KLR["signed"]["sha256"] == R["final_sha256"], "Virtuoso 的輸入必須是交付版 GDS"
vrows = [
    ["cell", sig["cells"], VI["oa"]["cells"], dfl["cells"], m81["cells"]],
    ["instance", sig["elements"]["sref"], VI["oa"]["instances"], dfl["elements"]["sref"], m81["elements"]["sref"]],
    ["GDS 3 多邊形", sig["polygons_per_layer"]["3"], oa_n["3"], f"<b>{dfl['polygons_per_layer']['3']}</b>", m81["polygons_per_layer"]["3"]],
    ["GDS 3 單一多邊形最多點數", sig["max_points_per_layer"]["3"], f"{oa_max['3']}（頂點，不含閉合點）",
     dfl["max_points_per_layer"]["3"], m81["max_points_per_layer"]["3"]],
    ["其他 6 層多邊形", " ／ ".join(str(sig["polygons_per_layer"][l]) for l in LAYERS[1:]),
     " ／ ".join(str(oa_n[l]) for l in LAYERS[1:]), " ／ ".join(str(dfl["polygons_per_layer"][l]) for l in LAYERS[1:]),
     " ／ ".join(str(m81["polygons_per_layer"][l]) for l in LAYERS[1:])],
    ["GDS 3 與簽核版 XOR", "—", "—", xor_txt("default", "3"), xor_txt("8191", "3")],
    ["其他 6 層與簽核版 XOR", "—", "—", "0" if all(GEO["default"][l]["xor_area"] == 0 for l in LAYERS[1:]) else "<b>有差異</b>",
     "0" if all(GEO["8191"][l]["xor_area"] == 0 for l in LAYERS[1:]) else "<b>有差異</b>"],
    ["KLayout pre-DRC", KLR["signed"]["total"], "—", f"<b>{KLR['virtuoso_default']['total']}</b>", KLR["virtuoso_8191"]["total"]],
    ["Calibre DRC（⑦）", CAL["signed"]["total"], "—", CAL["virtuoso_default"]["total"], CAL["virtuoso_8191"]["total"]],
]
lg = lambda d: f"{d['errors']} 錯誤、{d['warnings']} 警告"  # noqa: E731
blocks["virtuoso"] = (
    f'<div class="kpis"><div class="kpi"><b>{VI["stream_in"]["errors"]}／{VI["stream_in"]["warnings"]}</b>匯入錯誤／警告</div>'
    f'<div class="kpi"><b>{VI["oa"]["cells"]}</b>OA cell</div><div class="kpi"><b>{len(VI["out_default"]["chopped"])}</b>預設匯出被切開的多邊形</div>'
    f'<div class="kpi"><b>0</b>8191 點匯出與簽核版 XOR（7 層）</div></div>'
    + table(["項目", "簽核版 GDS", "OA（Virtuoso 內）", "預設匯出", "8191 點匯出"], vrows)
    + f'<p class="muted">版本 Virtuoso {VI["version"]}。XStream In：{lg(VI["stream_in"])}；XStream Out 預設：{lg(VI["out_default"])}；'
      f'8191 點：{lg(VI["out_8191"])}。其他 6 層依序為 GDS 4、5、39、41、99、100。OA 的頂層 cell 為 <code>{VI["oa"]["top"]}</code>，'
      f'外框 {html.escape(VI["oa"]["bbox"])} µm。</p>'
    + f'<p>OA 裡最長的曲線是 {oa_max["3"]} 個頂點，GDS 寫成 {oa_max["3"] + 1} 個點（多一個閉合點）；簽核版是 {sig["max_points_per_layer"]["3"]} 個點，'
      '匯入時去掉一個多餘的頂點（共線或重複），8191 點匯出與簽核版 XOR 為 0，代表形狀沒變。'
      '三個 log 都是 0 錯誤 0 警告，但預設匯出的 log 有 '
      f'{len(VI["out_default"]["chopped"])} 則 XSTRM-275 訊息：多邊形超過 200 點，會被切成小塊。<b>log 沒有警告不等於幾何沒變</b>。</p>')

SE = V["seam"]
md = SE["modes"]["deep"]
n_seam = dfl["polygons_per_layer"]["3"] - sig["polygons_per_layer"]["3"]
cf = V["chop_figure"]
sites = "、".join(f"({x:g}, {y:g})" for x, y in SE["sites"])
blocks["seam"] = (
    f'<p>預設匯出用垂直線把 {len(VI["out_default"]["chopped"])} 條超過 200 點的曲線切開，GDS 3 從 {sig["polygons_per_layer"]["3"]} 塊變成 '
    f'{dfl["polygons_per_layer"]["3"]} 塊，多出 {n_seam} 條接縫。接縫上的新頂點取整到 1 nm 格點，所以和原形狀有極小差異'
    f'（XOR 共 {GEO["default"]["3"]["xor_area"]:.4f} µm²，分散在 {GEO["default"]["3"]["xor_count"]} 塊）。'
    f'KLayout pre-DRC 在其中 {len(SE["sites"])} 條接縫上各報 2 個 GDS 3 線寬違規，共 {SE["markers"]} 個；Calibre 對同一個檔案報 0。</p>'
    + '<figure><img src="figures/m2_s7_chop.png" alt="預設匯出把一條彎曲波導切成多塊；接縫處的線寬標記"><figcaption>'
      f'圖 1｜同一條彎曲波導（{cf["points"]} 點）。上：預設匯出切成 {cf["pieces_default"]} 塊（顏色區分），灰色虛線是接縫，'
      f'紅圈是 KLayout 標記（這條波導上 {cf["markers_in_cell"]} 個）。下：8191 點匯出維持 1 塊。右：放大一條接縫，'
      '紅線是標記的兩條邊：垂直的切線和波導邊，在每一塊的角上都形成尖角。</figcaption></figure>'
    + '<p>標記的兩條邊一條是切線、一條是波導邊，表示 KLayout 是<b>一塊一塊</b>量的，沒有先把同層的多邊形合併。用同一份檔案做對照實驗：</p>'
    + table(["KLayout 的寫法（GDS 3 線寬 &lt; 0.349 µm、夾角限制 45°）", "標記數"], [
        ["先合併再量（<code>.merged.width</code>）", md["merged"]],
        ["剛讀進來的圖層直接量（預設會合併）", md["fresh_before_raw_call"]],
        ["逐塊量（<code>.raw.width</code>）", md["raw"]],
        ["照平台規則檔的順序：先對同一層呼叫 <code>.raw.sized(0.2.um)</code>，再量線寬", f"<b>{md['after_raw_sized_call']}</b>"]])
    + '<p>原因在平台規則檔：檢查 GDS 60 與 GDS 3 重疊的那一行寫了 <code>soi_etch2_light_layer.raw.sized(0.2.um)</code>。'
      '<code>.raw</code> 會直接把這個圖層物件改成「不合併」模式，所以後面 GDS 3 的線寬與間距檢查都是逐塊量。'
      'Calibre 讀圖層時一律先合併，接縫消失，只剩不到 1 nm 的折角，所以是 0。'
      '平面模式與階層模式結果相同（表中為階層模式）。</p>'
    + f'<p>標記的邊長 {SE["lengths_um"][0]:.2f}–{SE["lengths_um"][-1]:.2f} µm，位置（µm）：{sites}。'
      '這些接縫都落在波導坡度大於 45° 的地方：切線與波導邊的夾角小於 45°，才在夾角限制的檢查範圍內；緩坡上的接縫夾角大，不被檢查。'
      '<b>修正：</b>匯出時加 <code>-maxVertices 8191</code>，每條曲線維持一塊，幾何與簽核版完全相同，兩個引擎都是 0。'
      '送件或交給別人時，要用 log 確認實際用了哪個 maxVertices。</p>')

# ⑦ Calibre
INP = [("signed", "簽核版"), ("rule_faults", "規則故障檔"), ("signed_area_wrong", "設計區少 100 µm"),
       ("virtuoso_default", "預設匯出"), ("virtuoso_8191", "8191 點匯出")]


def pair(k, c):
    return f"{k} ／ {c}" if k == c else f"<b>{k} ／ {c}</b>"


crow = [[html.escape(r["category"]), f"<code>{r['check']}</code>"] + [pair(r[f"kl_{n}"], r[f"cal_{n}"]) for n, _ in INP]
        for r in V["rules"] if not r["check"].startswith("USED_")]
crow += [[f"GDS {r['check'].split('_')[1]} 不可出現（{html.escape(r['category'])}）", f"<code>{r['check']}</code>"]
         + [f"— ／ {r[f'cal_{n}']}" for n, _ in INP] for r in V["rules"] if r["check"].startswith("USED_")]
crow.append(["<b>合計</b>", ""] + [pair(KLR[n]["total"], CAL[n]["total"]) for n, _ in INP])
n_rule = sum(1 for r in V["rules"] if not r["check"].startswith(("USED_", "GRID_", "AREA_")))
fault_same = sum(1 for r in V["rules"] if not r["check"].startswith(("USED_", "GRID_", "AREA_"))
                 and r["cal_rule_faults"] == r["kl_rule_faults"] >= 1)
case_rows = [[c["id"], c["desc"], LNAME[str(c["layer"])], "線寬" if c["kind"] == "width" else "間距",
              c["klayout"], c["calibre"], c["independent"],
              "一致" if c["klayout"] == c["calibre"] == c["independent"] else "<b>不一致</b>"] for c in V["cases"]]
n_case = sum(1 for c in V["cases"] if c["klayout"] == c["calibre"])
blocks["calibre"] = (
    f'<div class="kpis"><div class="kpi"><b>{len(V["rules"])}</b>條 Calibre 檢查</div>'
    f'<div class="kpi"><b>{CAL["signed"]["total"]}</b>簽核版違規</div>'
    f'<div class="kpi"><b>{fault_same}/{n_rule}</b>線寬／間距規則故障一致</div>'
    f'<div class="kpi"><b>{n_case}/{len(V["cases"])}</b>邊界案例一致</div></div>'
    + "<h3>逐條規則（KLayout ／ Calibre 違規數）</h3>"
    + table(["規則（平台規則檔原文）", "Calibre 檢查", *[t for _, t in INP]], crow)
    + f'<p>Calibre 版本 {V["calibre_version"]}，階層模式。簽核版、8191 點匯出兩個引擎都是 0；規則故障檔 {n_rule} 條線寬／間距規則各觸發 1 次，'
      '次數與 KLayout 相同；設計區宣告少 100 µm 時兩邊都報 1 個。唯一不同的是預設匯出（見 ⑥）。'
      f'格點檢查在兩邊都是 0：GDS 的資料單位就是 1 nm，座標不可能落在格點外，這 7 條只是照抄。</p>'
    + f'<details><summary>沒有改寫的 {len(V["not_translated"])} 條規則（GDS 6、60）</summary><ul>'
    + "".join(f"<li>{html.escape(r)}</li>" for r in V["not_translated"]) + "</ul></details>"
    + "<h3>邊界案例（M3 s2 的 11 個，三種方法的標記數）</h3>"
    + table(["案例", "內容", "圖層", "規則", "KLayout", "Calibre", "獨立方法（M3 s2）", "判定"], case_rows)
    + '<p>夾角限制、楔形尖端、同一圖形內的窄縫、角對角與短平行段，三種方法的標記數都相同；'
      '剛好等於門檻的 C2、C4 都不報。這表示 <code>ABUT &lt; 45</code> 在這些情況與 KLayout 的 <code>angle_limit(45)</code> 等價。'
      '但合併語意不在這 11 個案例裡：每個案例都是互不重疊的完整多邊形，測不出 ⑥ 的差異。</p>')

ok = R["all_ok"] and S["all_ok"] and v_ok and c_ok
blocks["verdict"] = (f'<p><b>本次驗收：{"通過" if ok else "未通過"}。</b>交付版 SHA-256 與 M2 s6 簽核一致；{R["n_files"]} 個檔案；'
                     '解壓後清單核對、LVS／電氣、重建比對、DRC 都通過，竄改會被抓到；送件與量測待補項目已列出。'
                     f'Virtuoso 匯入 0 錯誤 0 警告，8191 點匯出與簽核版幾何相同；Calibre 簽核版 {CAL["signed"]["total"]} 違規，'
                     f'規則故障 {fault_same}/{n_rule}、邊界案例 {n_case}/{len(V["cases"])} 與 KLayout 一致；預設匯出的 '
                     f'{KLR["virtuoso_default"]["total"]} 個標記已找出原因。</p>')

text = PAGE.read_text(encoding="utf-8")
for k, blk in blocks.items():
    pat = re.compile(rf"(<!-- BEGIN:{k} -->).*?(<!-- END:{k} -->)", re.S)
    assert len(pat.findall(text)) == 1, f"標記 {k} 必須剛好一組"
    text = pat.sub(lambda m: m.group(1) + "\n" + blk + "\n" + m.group(2), text)
tmp = PAGE.with_suffix(".tmp")
tmp.write_text(text, encoding="utf-8")
assert tmp.read_text(encoding="utf-8").rstrip().endswith("</html>")
os.replace(tmp, PAGE)
print("updated", PAGE.name, list(blocks), "verdict", ok)

# 單檔自足：把 CSS 與圖嵌進頁面（app 的檔案預覽不載入相對路徑）
import sys as _sys  # noqa: E402
_sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import inline_page  # noqa: E402
print("inlined", PAGE.name, "%.0f KB" % (inline_page.run(PAGE)[0] / 1024))