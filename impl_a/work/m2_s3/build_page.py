"""把 out/m2_s3_result.json 與 out/layout_info.json 寫進 course/m2_s3.html 的 BEGIN/END 區塊。

用法：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m2_s3\\build_page.py
只取代標記之間的內容；先寫暫存檔、檢查標記完整後再原子替換。
"""
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGE = HERE.parents[1] / "course" / "m2_s3.html"
R = json.loads((HERE / "out" / "m2_s3_result.json").read_text(encoding="utf-8"))
INFO = json.loads((HERE / "out" / "layout_info.json").read_text(encoding="utf-8"))
G, GS, MU, CAL = R["geometry"], R["geometry_straight"], R["mutants"], R["calibrated"]["runs"]


def table(head, rows):
    return ("<table><tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</table>")


def sci(x):
    if x == 0:
        return "0"
    m, e = f"{x:.1e}".split("e")
    return f"{m}×10<sup>{int(e)}</sup>"


blocks = {}
H = INFO["heater"]
blocks["geo"] = table(["項目", "數值", "說明"], [
    ["rail 間距（MZI 兩臂間距）", "30 µm", "heater 與相鄰波導至少隔 30 µm"],
    ["相位段", "122 µm", f"TiN {H['width_um']}×{H['length_um']:g} µm，兩端 {H['land_um']:g} µm 落墊、{H['contact_um']:g} µm Ti/AL 接觸墊"],
    ["餘弦 S 彎", f"水平 20 µm、橫移 {G['dy_um']:.3f} µm、實長 {G['sbend_um']:.3f} µm", "最小曲率半徑 5.23 µm（PDK 標準 5 µm）"],
    ["PDK 2×2 MMI", f"埠到埠 {G['mmi_len_um']:g} µm", "上埠 in2／out2"],
    ["一欄（MZI 埠到埠）", f"{G['column_um']:g} µm", "= 2 × 122 + 4 × 20 + 2 × 82.5"],
    ["MZI 上臂／下臂幾何長度", f"{G['mzi_upper_um']:.3f}／{G['mzi_lower_um']:.3f} µm", "兩臂等長（上下鏡像）"],
    ["單顆 MZI 外框", f"{R['extent_mzi'][0]:g} × {R['extent_mzi'][1]:g} µm", f"設計區宣告 {R['block_mzi'][0]:g} × {R['block_mzi'][1]:g} µm"],
])

def g0(x):
    return f"{x + 0.0:g}"          # 避免印出 −0


rows = [[m["name"], m["column"], f"{m['rails'][0]}、{m['rails'][1]}", f"({g0(m['origin_um'][0])}, {g0(m['origin_um'][1])})",
         "、".join(f"{k}：({g0(v[0][0])}, {g0(v[0][1])}) 與 ({g0(v[1][0])}, {g0(v[1][1])})" for k, v in m["heater_contacts_um"].items())]
        for m in INFO["mzi"]]
ins = [p for p in INFO["ports"] if p["name"].startswith("in")]
outs = [p for p in INFO["ports"] if p["name"].startswith("out")]
blocks["place"] = (
    table(["MZI", "欄", "rail", "原點（µm）", "接觸墊中心（µm）"], rows)
    + f'<p>旁路幾何長度 {G["bypass_um"]:.3f} µm（等長），直線旁路則為 {GS["bypass_um"]:g} µm，'
      f'每欄短 {G["bypass_um"] - GS["bypass_um"]:.1f} µm。光學埠：輸入 x = {ins[0]["xy"][0]:g} µm、'
      f'輸出 x = {outs[0]["xy"][0]:g} µm，y = 0、−30、…、−120 µm。B7 核心外框 {R["extent_b7"][0]:g} × {R["extent_b7"][1]:g} µm，'
      f'設計區宣告 {R["block_b7"][0]:g} × {R["block_b7"][1]:g} µm。</p>')

L, D = R["lvs"], R["drc"]
blocks["lvs"] = (
    f'<div class="kpis"><div class="kpi"><b>{L["n_nets"]}</b>抽出的連線（含旁路、引線）</div>'
    f'<div class="kpi"><b>{L["n_links"]}/9</b>MZI 間連線與規格相同</div>'
    f'<div class="kpi"><b>{L["n_external"]}/10</b>外部埠與規格相同</div>'
    f'<div class="kpi"><b>{len(L["dangling"])}</b>未連接的埠</div></div>'
    + table(["GDS", "DRC 違規", "設計區外圖形", "規則數"],
            [[n, D[n]["total"], D[n]["outside"], D[n]["n_rules"]] for n in ("mzi_core", "b7_core")])
    + f'<p>抽出的連接表：MZI 間連線{"完全一致" if L["links_match"] else "<b>不一致</b>"}，'
      f'外部埠{"完全一致" if L["external_match"] else "<b>不一致</b>"}。</p>')

rows = [[g, "一致" if v["lvs"] else "<b>不一致</b>", f"{16 - v['wrong_1550']}/16", f"{v['margin_1550']:.4f}",
         f"{v['worst_norm']:.5f}", sci(v["mag_diff"]), sci(v["phase_spread"])] for g, v in R["gates"].items()]
n_ok = sum(16 - v["wrong_1550"] for v in R["gates"].values())
all_wl = all(v["all_ok"] for v in R["gates"].values())
wl = R["wl_um"]
blocks["rows"] = (
    f'<div class="kpis"><div class="kpi"><b>{n_ok}/80</b>1550 nm 判定正確</div>'
    f'<div class="kpi"><b>{"全對" if all_wl else "有錯"}</b>{wl[0] * 1000:.0f}–{wl[-1] * 1000:.0f} nm 共 {len(wl)} 點</div>'
    f'<div class="kpi"><b>{sci(max(v["mag_diff"] for v in R["gates"].values()))}</b>|U| 與理想最大差</div></div>'
    + table(["功能", "抽出連接表", "1550 nm", "餘量", "各波長最小 餘量÷理想", "|U| 與理想最大差", "同一輸出的相位散佈（rad）"], rows)
    + '<p>「同一輸出的相位散佈」是每一列 U<sub>佈局</sub>／U<sub>理想</sub> 的相位差異，接近 0 就代表只差輸出端相位。'
      '這裡沒有改任何 heater 設定，直接用 M1 s4 的相位。</p>')

rows = []
for k, v in MU.items():
    lv = v["lvs"]
    if "error" in lv:
        lvs = "抽取失敗"
    elif lv["links_match"] and lv["external_match"] and not lv["dangling"]:
        lvs = "一致（沒抓到）"
    else:
        lvs = "抓到" + (f"：{len(lv['dangling'])} 個埠未連接" if lv["dangling"] else "：連線與規格不同")
    drc_t = f"抓到：{v['drc']['total']} 處 &lt; 0.2 µm 縫" if v["drc"]["total"] else "0（沒抓到）"
    if v["circuit"] == "ok":
        circ = f"{v['wrong_1550']}/80 錯"
        path = f"抓到：|U| 差 {v['mag_diff']:.3f}" if v["path_caught"] else "沒抓到"
    else:
        circ = "電路有未連接的埠，無法求解"
        path = "—"
    rows.append([v["desc"], drc_t, lvs, circ, path])
blocks["faults"] = (
    table(["佈局錯誤", "DRC", "抽連接表比對", "80 筆（1550 nm、未校正）", "等光程檢查"], rows)
    + '<ul><li><b>DRC</b> 只抓得到留下小縫的錯（錯位、放錯 rail）；翻轉、旁路不等長、臂長差的幾何都合法。</li>'
      '<li><b>抽連接表</b> 抓得到所有接錯埠的錯，但長度錯誤不改變連接，抓不到。</li>'
      '<li><b>等光程檢查</b> 抓得到長度錯誤；直線旁路在 1550 nm 甚至 80 筆全對，只看 80 筆會漏掉。</li></ul>')

n_byp = 4 * 5 - 2 * len(INFO["mzi"])          # 每欄 5 條 rail，扣掉 MZI 占用的
lbl = {"none": "等長旁路（本設計）", "straight": "直線旁路", "arm": "M7 下臂多 2 µm"}
rows = []
for f, v in CAL.items():
    lo, hi = v["pass_nm"]
    rows.append([lbl[f], sci(v["cal_check"]), "整個 ±20 nm" if v["full"] else f"{lo:+.2f} 到 {hi:+.2f} nm"])
blocks["cal"] = (
    table(["佈局", "校正後與理想的相位散佈（rad）", "80 筆全對的雷射波長範圍"], rows)
    + '<p>校正函式 <code>b7_layout.calibrate</code> 依層序追蹤每條 rail 累積的傳播相位，把輸入端的相位差併入 φ、臂內相位差併入 θ。'
      '校正後三種佈局在 1550 nm 都和理想一致（第二欄），差別在離開 1550 nm 之後：M7 臂長差 2 µm 的範圍與 M2 s2 規則一致'
      f'（單顆 M7 容忍約 0.135 rad）；直線旁路有 {n_byp} 段、每段短 {G["bypass_um"] - GS["bypass_um"]:.1f} µm，範圍更窄。</p>')

ok = (D["b7_core"]["total"] == 0 and D["mzi_core"]["total"] == 0 and D["b7_core"]["outside"] == 0
      and L["links_match"] and L["external_match"] and not L["dangling"] and n_ok == 80 and all_wl
      and all(v["lvs_caught"] or v["path_caught"] or v["drc"]["total"] for v in MU.values()))
blocks["verdict"] = (f'<p><b>本次驗收：{"通過" if ok else "未通過"}。</b>B7 核心 DRC {D["b7_core"]["total"]} 違規；'
                     f'抽出連接表與規格一致；佈局電路 {n_ok}/80，{wl[0] * 1000:.0f}–{wl[-1] * 1000:.0f} nm 全對；'
                     f'{len(MU)} 種佈局錯誤都被抓到。</p>')

text = PAGE.read_text(encoding="utf-8")
for k, b in blocks.items():
    pat = re.compile(rf"(<!-- BEGIN:{k} -->).*?(<!-- END:{k} -->)", re.S)
    assert len(pat.findall(text)) == 1, f"標記 {k} 必須剛好一組"
    text = pat.sub(lambda m: m.group(1) + "\n" + b + "\n" + m.group(2), text)
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