"""把 out/tests.json、out/m1_s3_result.json 寫進 course/m1_s3.html 的 BEGIN/END 區塊。

用法：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m1_s3\\build_page.py
只取代標記之間的內容；先寫暫存檔、檢查標記完整後再原子替換。
"""
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGE = HERE.parents[1] / "course" / "m1_s3.html"
TJ = json.loads((HERE / "out" / "tests.json").read_text(encoding="utf-8"))
R = json.loads((HERE / "out" / "m1_s3_result.json").read_text(encoding="utf-8"))
REF = json.loads((HERE.parents[1] / "sources" / "reference_b7.json").read_text(encoding="utf-8"))

NAME = {"test_reference_cases": "黃金值：原版 1000、1100", "test_weighted_sum": "加權和 = 矩陣乘法",
        "test_quadratic_form": "ΔP 二次式精確成立", "test_r_scaling": "R 加倍的比例",
        "test_power_sum_conserved": "五路功率守恆", "test_dark_input": "全暗輸入只剩 R"}


def z(c):
    re_, im = c
    re_ = 0.0 if abs(re_) < 5e-13 else re_
    im = 0.0 if abs(im) < 5e-13 else im
    return f"{re_:+.3f}{im:+.3f}i"


def table(head, rows):
    return ("<table><tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</table>")


def badge(ok, yes="通過", no="失敗"):
    return f'<span class="badge {"pass" if ok else "fail"}">{yes if ok else no}</span>'


blocks = {}
ref = {c["bits"]: c for c in REF["cases"]}
parts = []
for h in R["hand"]:
    rows = []
    for k in range(5):
        t2, t4 = h["o2"]["terms"][k], h["o4"]["terms"][k]
        rows.append([t2["src"], f'{t2["v"]:g}', z(t2["u"]), z(t2["prod"]), z(t4["u"]), z(t4["prod"])])
    rows.append(["<b>加總（光場）</b>", "", "", f'<b>o2 = {z(h["o2"]["field"])}</b>', "", f'<b>o4 = {z(h["o4"]["field"])}</b>'])
    rows.append(["<b>功率 |·|²</b>", "", "", f'<b>{h["o2"]["power"]:.4f}</b>', "", f'<b>{h["o4"]["power"]:.4f}</b>'])
    rc = ref[h["bits"]]
    parts.append(f'<h3>輸入 {h["bits"]}：v = [{", ".join(f"{a:g}" for a in h["v"])}]</h3>'
                 + table(["輸入", "振幅 vk", "u₂k", "u₂k·vk", "u₄k", "u₄k·vk"], rows)
                 + f'<p>ΔP = {h["o2"]["power"]:.4f} − {h["o4"]["power"]:.4f} = <b>{h["delta"]:.4f}</b>，判 <b>{h["bit"]}</b>。'
                   f'原版課程：ΔP = {rc["delta"]:.4f}、判 {rc["bit"]}；五路功率 '
                   + "、".join(f"{p:.4f}" for p in rc["powers"]) + "。</p>")
blocks["hand"] = "".join(parts)

d = R["decomposition"]
rows = d["rows"]
low = min((r for r in rows if r["bit"] is not None), key=lambda r: abs(r["total"]))
cross_big = max(rows, key=lambda r: abs(r["data_x_data"]))
blocks["terms"] = (
    "<ul>"
    + f'<li><b>只有 R：</b>c₀ = {d["c0"]:.3f}。示範設定下 R 到 o2、o4 的功率相同，所以 0000 落在邊界。</li>'
    + f'<li><b>R × 資料：</b>a = [{", ".join(f"{v:+.3f}" for v in d["a"])}]（x1–x4 各自的票數）。x3 的票是負的，所以 x3=1 時傾向判 0。</li>'
    + f'<li><b>資料 × 資料：</b>非對角 Q 最大 {d["max_abs_Q_off"]:.3f}；影響最大的是 {cross_big["bits"]}（{cross_big["data_x_data"]:+.3f}）。'
      f'餘裕最小的是 {low["bits"]}：ΔP = {low["total"]:+.3f}，R×資料 {low["r_x_data"]:+.3f} 幾乎被資料×資料 {low["data_x_data"]:+.3f} 抵銷。</li>'
    + f'<li><b>核對：</b>四部分加總與直接計算的最大差 {R["max_check"]:.0e}。</li>'
    + "</ul>")

mrows = []
for m in R["mistakes"]:
    mrows.append([m["desc"], f'{m["d1000"]:+.3f}', f'{m["d1100"]:+.3f}', f'{m["flips"]}/16',
                  f'{m["rand_mean_flips"]:.2f}/16', f'{m["rand_any"]:.0%}'])
mm = {m["key"]: m for m in R["mistakes"]}
blocks["mistakes"] = (
    table(["算法", "ΔP（1000）", "ΔP（1100）", "示範設定判錯", "隨機相位平均判錯", "隨機相位中至少錯 1 組的比例"], mrows)
    + "<ul>"
    + f'<li><b>功率相加</b>（錯在步驟 2、3 的順序）：丟掉 R×資料 與 資料×資料 兩項，示範設定下判錯 {mm["power_sum"]["flips"]}/16。'
      f'隨機相位下平均只錯 {mm["power_sum"]["rand_mean_flips"]:.1f} 組，是因為隨機相位的 c₀（∝ R²＝9）通常很大，兩種算法共用它；'
      '邏輯相位的判定靠的正是被丟掉的兩項，M1 s4 會用真正的相位再檢查一次這個錯的後果。</li>'
    + f'<li><b>取模長不平方</b>（錯在步驟 3）：|o2| − |o4| 與 |o2|² − |o4|² 永遠同號，所以判定一組都不會錯（隨機相位 {mm["modulus"]["rand_mean_flips"]:.0f} 組），'
      '但 ΔP 的大小錯了：用它估餘裕會低估雜訊容忍度。<b>判定正確不代表計算正確。</b></li>'
    + f'<li><b>R 放成 9</b>（錯在步驟 1）：示範設定下剛好沒判錯，隨機相位下平均錯 {mm["r_as_power"]["rand_mean_flips"]:.1f} 組：R 的比重被放大，改變 R 與資料之間的平衡。</li>'
    + f'<li><b>讀錯埠、忘了 R</b>：隨機相位下平均判錯 {mm["wrong_ports"]["rand_mean_flips"]:.1f}、{mm["no_r"]["rand_mean_flips"]:.1f} 組。'
      '忘了 R 時 0000 永遠是 0，回到 M1 s1「沒有光就讀不到 1」的限制。</li>'
    + "</ul>")

blocks["tests"] = (f'<div class="kpis"><div class="kpi"><b>{TJ["n_pass"]}/{TJ["n_total"]}</b>通過</div></div>'
                   + table(["測試", "檢查的性質", "結果"],
                           [[f'{NAME.get(t["name"], t["name"])}<br><code>{t["name"]}</code>', t["doc"], badge(t["passed"])]
                            for t in TJ["tests"]]))

hand_ok = all(abs(h["delta"] - ref[h["bits"]]["delta"]) < 1e-12 and h["bit"] == ref[h["bits"]]["bit"] for h in R["hand"])
ok = TJ["n_pass"] == TJ["n_total"] and hand_ok and R["max_check"] < 1e-12
blocks["verdict"] = (f'<p><b>本次驗收：{"通過" if ok else "未通過"}。</b>1000、1100 與原版課程一致；'
                     f'ΔP 四部分加總最大差 {R["max_check"]:.0e}；單元測試 {TJ["n_pass"]}/{TJ["n_total"]}。</p>')

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