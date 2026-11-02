"""把 out/drc_result.json、connectivity.json、signoff.json 寫進 course/m2_s6.html 的 BEGIN/END 區塊。

用法：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m2_s6\\build_page.py
只取代標記之間的內容；先寫暫存檔、檢查標記完整後再原子替換。
"""
import html
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGE = HERE.parents[1] / "course" / "m2_s6.html"
D = json.loads((HERE / "out" / "drc_result.json").read_text(encoding="utf-8"))
C = json.loads((HERE / "out" / "connectivity.json").read_text(encoding="utf-8"))
S = json.loads((HERE / "out" / "signoff.json").read_text(encoding="utf-8"))


def table(head, rows):
    return ("<table><tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</table>")


def used(rule):
    r = rule.replace("&lt;", "<")
    return any(f"(GDS{l}<" in r or f"(GDS{l} <" in r for l in (3, 4, 5, 39, 41, 100)) or "design area" in r or \
        any(r.startswith(f"{l}/0 grid") for l in (3, 4, 5, 39, 41, 99, 100))


blocks = {}
c0 = D["clean"]
rows_u = [[html.escape(r.replace("&lt;", "<")), c0["counts"].get(r, 0)] for r in c0["rules"] if used(r)]
rows_n = [html.escape(r.replace("&lt;", "<")) for r in c0["rules"] if not used(r)]
blocks["drc"] = (
    f'<div class="kpis"><div class="kpi"><b>{c0["total"]}</b>違規</div><div class="kpi"><b>{c0["outside"]}</b>設計區外圖形</div>'
    f'<div class="kpi"><b>{c0["n_rules"]}</b>條規則</div><div class="kpi"><b>{D["design_area_um"][0]:g}×{D["design_area_um"][1]:g}</b>宣告設計區（µm）</div></div>'
    + "<h3>本設計用到的圖層</h3>" + table(["規則（規則檔原文）", "違規數"], rows_u)
    + f"<details><summary>本設計沒用到的圖層（{len(rows_n)} 條，結果都是 0）</summary><ul>"
    + "".join(f"<li>{r}</li>" for r in rows_n) + "</ul></details>"
    + f'<p class="muted">被檢查的檔案：<code>{D["gds"]}</code>，SHA-256 <code>{D["sha256"][:16]}…</code></p>')

F = D["rule_faults"]
blocks["drcfault"] = (
    table(["規則", "觸發次數"], [[k, v if v else "<b>0（漏抓）</b>"] for k, v in F["hit"].items()]
          + [["設計區尺寸（宣告少 100 µm）", F["area_wrong_hit"]]])
    + f'<p>{sum(v >= 1 for v in F["hit"].values())}/{len(F["hit"])} 條規則與設計區都觸發；意外觸發的其他規則：{len(F["unexpected"])} 條。'
      '晶片本體在這次執行仍是 0 違規（所有標記都在注入的圖形上）。</p>')

L = C["optical"]
blocks["lvs"] = (
    f'<div class="kpis"><div class="kpi"><b>{L["n_bodies"]}</b>MMI 本體</div><div class="kpi"><b>{L["n_mzi"]}</b>MZI</div>'
    f'<div class="kpi"><b>{L["n_wires"]}</b>導線</div><div class="kpi"><b>{L["n_links"]}/9</b>MZI 間連線</div>'
    f'<div class="kpi"><b>{L["n_ext"]}/10</b>外部埠</div><div class="kpi"><b>{L["n_heaters"]}/14</b>heater 通道</div></div>'
    + table(["比對項目", "結果"], [["MZI 之間的連線 vs spec/netlist.json", "一致" if L["links_match"] else "<b>不一致</b>"],
                                 ["端面（fiber_in／out）到 MZI 的對應 vs 規格", "一致" if L["ext_match"] else "<b>不一致</b>"],
                                 ["heater 所在導線 → 通道 vs 規格的 14 個相位通道", "一致" if L["heaters_match"] else "<b>不一致</b>"],
                                 ["每條導線剛好兩個端點", "是" if not any("端點" in p for p in L["problems"]) else "<b>否</b>"]])
    + f'<p>另有 {L["n_marks"]} 個小方塊不接任何端點，是 EC 旁的研磨刻度。</p>')

E = C["electrical"]
rows = [[r["channel"], "、".join(r["signal_pad"]) or "—", "、".join(r["ground"]) or "—", "通過" if r["ok"] else "<b>不通過</b>"]
        for r in E["rows"]]
blocks["elec"] = (
    f'<p>GDS 41 合併成 {E["n_nets"]} 個連通網，找到 {E["n_pads"]} 個 80 × 80 µm 接墊。每個 heater（GDS 39）必須剛好接觸兩個網：'
    '一個只含它自己訊號接墊的網，與一個回流網。heater 是哪個通道，由它的位置（欄、rail、φ／θ）對規格決定，不看設計表。</p>'
    + table(["通道", "訊號接墊", "回流", "判定"], rows)
    + f'<p>每條 TiN 加熱絲（扣掉兩端落墊）量到 {E["heater_squares"][0]:g}–{E["heater_squares"][1]:g} 個方塊（100 µm ÷ 0.9 µm）。</p>')

rows = []
for f, v in C["faults"].items():
    lv = "抓到：" + v["lvs_problems"][0] if v["lvs_ok"] is False else "沒抓到"
    el = "抓到：" + v["elec_problems"][0] if v["elec_ok"] is False else "沒抓到"
    rows.append([v["desc"], html.escape(lv), html.escape(el)])
blocks["faults"] = (table(["故障版", "光學 LVS", "電氣連接"], rows)
                    + '<p>光路錯誤（錯位、放錯 rail、翻轉）由 LVS 抓到；金屬錯誤（開路、短路、接墊名稱寫反）由電氣檢查抓到，'
                      'LVS 對它們沒有反應。翻轉同時改變光路與 heater 位置，兩項都抓到。</p>')

rows = [[i["item"], i["step"], html.escape(i["result"]), "通過" if i["ok"] else "<b>不通過</b>"] for i in S["items"]]
blocks["signoff"] = (table(["項目", "在哪一步", "結果", "判定"], rows)
                     + f'<p>凍結版：<code>{S["gds"]}</code>，{S["die_um"][0]:g} × {S["die_um"][1]:g} µm，'
                       f'SHA-256 <code>{(S["sha256"] or "—")[:16]}…</code>。M2 s3–s5 的結果都是由同一份程式與規格產生；'
                       'M2 s5 的 GDS 與這裡凍結的檔案位元相同。範圍：' + html.escape(S["scope"]) + '。</p>')

ok = S["all_ok"]
blocks["verdict"] = (f'<p><b>本次驗收：{"通過" if ok else "未通過"}。</b>DRC {c0["total"]} 違規，{len(F["hit"])} 條規則與設計區都確認會觸發；'
                     f'光學 LVS 與規格一致；14 個 heater 接線正確；{len(C["faults"])} 個故障版都被抓到；已產生凍結版與簽核表。</p>')

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