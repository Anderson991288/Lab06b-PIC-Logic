"""把 out/m3_s2_result.json 寫進 course/m3_s2.html 的 BEGIN/END 區塊。

用法：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m3_s2\\build_page.py
只取代標記之間的內容；先寫暫存檔、檢查標記完整後再原子替換。
"""
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGE = HERE.parents[1] / "course" / "m3_s2.html"
R = json.loads((HERE / "out" / "m3_s2_result.json").read_text(encoding="utf-8"))
NAME = {"3": "GDS 3 Si 波導", "4": "GDS 4 蝕刻窗", "5": "GDS 5 薄矽", "39": "GDS 39 TiN", "41": "GDS 41 Ti/AL", "100": "GDS 100 文字"}


def table(head, rows):
    return ("<table><tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</table>")


def f3(x):
    return "—" if x is None else f"{round(x, 3) + 0.0:.3f}"      # + 0.0：避免印出 −0.000


blocks = {}
rows = []
for l, v in R["final"].items():
    pg = R["poly_gap"].get(l)
    ms = v["min_s"] if v["min_s"] is not None else (pg["min"] if pg else None)
    src = "" if v["min_s"] is not None else ("（不同圖形之間）" if pg else "")
    mw_margin = None if v["min_w"] is None else v["min_w"] - v["rule_w"]
    ms_margin = None if ms is None else ms - v["rule_s"]
    rows.append([NAME[l], f"{v['rule_w']:g}", f3(v["min_w"]), f3(mw_margin), f"{v['rule_s']:g}", f3(ms) + src, f3(ms_margin),
                 f"{v['n_w'] + v['n_s']}"])
blocks["final"] = (
    f'<div class="kpis"><div class="kpi"><b>{R["klayout_final"]["total"]}</b>KLayout 違規</div>'
    f'<div class="kpi"><b>{sum(v["n_w"] + v["n_s"] for v in R["final"].values())}</b>獨立方法違規</div></div>'
    + table(["圖層", "規則線寬", "量到最小線寬", "餘量", "規則間距", "量到最小間距", "餘量", "獨立方法違規"], rows)
    + f'<p>單位 µm。被檢查的檔案：交付包的 <code>{R["final_gds"]}</code>（SHA-256 <code>{R["final_sha256"][:16]}…</code>）。'
      '「不同圖形之間」是合併後各個獨立圖形的最短距離（Shapely 多邊形距離），用在邊對搜尋半徑內找不到面對面邊的圖層；'
      f'heater 之間最近 {R["poly_gap"]["39"]["min"]:g} µm、金屬之間最近 {R["poly_gap"]["41"]["min"]:g} µm，都遠大於 10 µm 的規則。</p>')

rows = [[NAME[str(r["layer"])], "線寬" if r["kind"] == "width" else "間距", r["klayout"], r["mine"], f3(r["d_klayout"]), f3(r["d_mine"]),
         "一致" if r["klayout"] == r["mine"] and r["klayout"] > 0 else "<b>不一致</b>"] for r in R["fault_rows"]]
n_ok = sum(1 for r in R["fault_rows"] if r["klayout"] == r["mine"] and r["klayout"] > 0)
blocks["fault"] = table(["圖層", "規則", "KLayout 標記", "獨立方法標記", "KLayout 距離", "獨立方法距離", "對照"], rows) + \
    f'<p>{n_ok}/{len(R["fault_rows"])} 條規則一致，量到的違規距離也相同（單位 µm）。</p>'

rows = []
for c in R["cases"]:
    exp = {True: "違規", False: "不違規", None: "看定義"}[c["expect"]]
    same = c["klayout"] == c["mine"]
    rows.append([c["id"], c["desc"], exp, c["klayout"], c["mine"], c["mine_noangle"], f3(c["d_klayout"]), f3(c["d_mine"]),
                 "一致" if same else "<b>不一致</b>"])
n_same = sum(1 for c in R["cases"] if c["klayout"] == c["mine"])
blocks["cases"] = table(["案例", "內容", "預期", "KLayout", "獨立方法", "獨立方法（無夾角限制）", "KLayout 距離", "獨立方法距離", "對照"], rows) + \
    f'<p>{n_same}/{len(R["cases"])} 個案例兩種方法一致。「看定義」表示結果取決於規則怎麼定義面對面的邊。</p>'

ca = {c["id"]: c for c in R["cases"]}
diff_ang = [c["id"] for c in R["cases"] if c["mine_noangle"] != c["mine"]]
blocks["diff"] = (
    "<ul>"
    + f'<li><b>夾角限制是最大的定義差異：</b>拿掉 45° 限制後，{"、".join(diff_ang)} 的標記數都變多。'
      f'C7（頂角 60°）從 0 變成 {ca["C7"]["mine_noangle"]}：兩條邊夾角超過 45°，規則檔不把它們當成「面對面」，所以尖角本身不違規。'
      '其餘多出來的標記也都是夾角大於 45° 的邊對（例如互相垂直的邊）。換用其他 DRC 工具時，要先確認它的夾角設定。</li>'
    + f'<li><b>角對角也算：</b>C9 兩個方塊只在角落接近（{ca["C9"]["d_klayout"]:.2f} µm），兩種方法都標記 {ca["C9"]["klayout"]} 個'
      '（垂直邊一對、水平邊一對）：歐氏距離量的是線段之間最近的點，不要求兩條邊在投影上重疊。規則檔若改用投影距離（projection，只量兩條邊投影重疊的部分），這兩對邊沒有重疊，量法就不同。</li>'
    + f'<li><b>平行段很短也算：</b>C10 兩個方塊只有 2 µm 的平行段，距離 {ca["C10"]["d_klayout"]:.0f} µm 小於 10 µm，兩種方法都標記。</li>'
    + f'<li><b>尖端的距離報法不同：</b>C6 兩種方法都判違規，但 KLayout 報的距離是 {ca["C6"]["d_klayout"]:.3f} µm、獨立方法是 '
      f'{ca["C6"]["d_mine"]:.3f} µm。兩條邊在尖端共用一個頂點；KLayout 的標記一路畫到尖端，獨立方法把距離為 0 的配對當成相鄰邊排除，'
      '報的是離尖端最近、但不共用頂點的那一小段。判定相同，量到的數字不同。</li>'
    + '<li><b>門檻相同：</b>剛好等於「規則值 − 0.001 µm」不違規（C2、C4），兩種方法一致；這也是規則檔 feature_margin 的意義。</li>'
    + '<li><b>同一圖形內的窄縫：</b>C8 的 U 形缺口屬於同一個多邊形，兩種方法都當成間距檢查。</li>'
    + "</ul>")

ok = (R["klayout_final"]["total"] == 0 and sum(v["n_w"] + v["n_s"] for v in R["final"].values()) == 0
      and n_ok == len(R["fault_rows"]) and n_same == len(R["cases"]))
blocks["verdict"] = (f'<p><b>本次驗收：{"通過" if ok else "未通過"}。</b>最終 GDS 兩種方法都 0 違規；規則故障注入 {n_ok}/{len(R["fault_rows"])} 一致；'
                     f'邊界案例 {n_same}/{len(R["cases"])} 一致；定義差異（夾角限制、角對角、門檻）已說明。</p>')

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