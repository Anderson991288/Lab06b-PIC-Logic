"""把 out/m2_s2_result.json 寫進 course/m2_s2.html 的 BEGIN/END 區塊。

用法：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m2_s2\\build_page.py
只取代標記之間的內容；先寫暫存檔、檢查標記完整後再原子替換。
"""
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGE = HERE.parents[1] / "course" / "m2_s2.html"
R = json.loads((HERE / "out" / "m2_s2_result.json").read_text(encoding="utf-8"))
NL, G, MU, A = R["netlist"], R["gates"], R["mutants"], R["arm"]


def table(head, rows):
    return ("<table><tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</table>")


def sci(x):
    if x == 0:
        return "0"
    m, e = f"{x:.1e}".split("e")
    return f"{m}×10<sup>{int(e)}</sup>"


blocks = {}

# ① 連接表
rail_of = {}
for port, name in NL["external"].items():
    rail_of[name] = port
rows = []
for n, (s, d) in enumerate(NL["links"], 1):
    rows.append([f"L{n}", s, d])
ins = "、".join(f"{v}→{k}" for k, v in NL["external"].items() if v.startswith("in"))
outs = "、".join(f"{k}→{v}" for k, v in NL["external"].items() if v.startswith("out"))
blocks["netlist"] = (
    f'<div class="kpis"><div class="kpi"><b>{NL["n_mzi"]}</b>MZI</div><div class="kpi"><b>{NL["n_links"]}</b>內部連線</div>'
    f'<div class="kpi"><b>{NL["n_external"]}</b>外部埠</div></div>'
    + table(["連線", "從", "到"], rows)
    + f'<p class="muted">外部輸入：{ins}。外部輸出：{outs}。</p>')

# ② PDK 模型
M, W = R["mmi"], R["wg_default"]
blocks["pdk"] = (
    table(["元件", "在 Caphe 裡的模型", "檢查結果", "代表什麼"], [
        ["2×2 MMI（SOI220nm_1550nm_TE_STRIP_2x2_MMI）", "picazzo 的 2×2 耦合器模型",
         f"{M['wl_range'][0]:.2f}–{M['wl_range'][1]:.2f} µm 內與理想 H 的最大差 {sci(M['max_diff_vs_H'])}；反射 {sci(M['back_reflection'])}",
         "無損 50:50、不隨波長變化，就是 M0 s3 的 H"],
        ["strip 波導（預設參數）", "固定 n<sub>eff</sub>、n<sub>g</sub> 的色散模型",
         f"n<sub>eff</sub> = {W['n_eff']:g}、n<sub>g</sub> = {W['n_g']:g}、損耗 {W['loss_dB_m']:g} dB/m",
         "佔位數值，不是 220 nm 矽波導（femwell：n<sub>eff</sub> ≈ "
         f"{A['n_eff']:.2f}、n<sub>g</sub> ≈ {A['n_g']:.2f}）；⑤ 改填 femwell 值"],
        ["θ、φ 相位區", "本課程自訂 CompactModel", "t = e<sup>iφ</sup>", "heater 的電壓—溫度關係不在電路模型裡"],
    ])
    + f'<p>波長掃描：B7（無額外波導）在 {M["wl_range"][0]:.2f}–{M["wl_range"][1]:.2f} µm 的 U 最大變化 {sci(R["wl_flatness"])}，'
      '也就是完全不隨波長變化。所以這一步的「PDK 電路模擬」驗證的是<b>接線與埠序</b>，不是製程誤差；'
      'MMI 的實際分光誤差與損耗已在 M0 s2（FDTD）量到，並在 M1 s4 確認 5 種功能仍全對。</p>'
    + f'<p class="muted">MMI 埠位置（µm）：' + "、".join(f"{k} ({v[0]:g}, {v[1]:g})" for k, v in M["ports"].items())
    + "；y > 0 的 in2／out2 是上埠。</p>")

# ③ 80 筆
rows = [[g, f"{16 - v['wrong']}/16", f"{v['margin']:.4f}", f"{v['spec_margin']:.4f}", sci(v["diff_vs_numpy"]),
         sci(v["unitarity"])] for g, v in G.items()]
blocks["rows"] = (
    f'<div class="kpis"><div class="kpi"><b>{R["rows_ok"]}/{R["rows_total"]}</b>判定正確</div>'
    f'<div class="kpi"><b>{sci(R["max_diff_vs_numpy"])}</b>U 與 NumPy 最大差</div>'
    f'<div class="kpi"><b>{sci(R["max_diff_vs_spec"])}</b>ΔP 與交接真值表最大差</div></div>'
    + table(["功能", "通過", "餘量（Caphe）", "規格餘量", "U 與 NumPy 最大差", "|U†U − I|"], rows)
    + '<p>餘量與 M1 s5 規格的理想餘量一致（規格四捨五入到 4 位）。|U†U − I| 在數值誤差內為 0，表示 PDK 模型無損，'
      '總功率守恆。80 筆的功率與 ΔP 存在 <code>truth_tables.csv</code>。</p>')

# ④ 故障注入
rows = []
for k, v in MU.items():
    pg = v["per_gate"]
    worst = max(pg, key=lambda g: pg[g]["wrong"])
    hit = "、".join(f"{g} {pg[g]['wrong']}" for g in pg if pg[g]["wrong"])
    rows.append([v["desc"], f"{v['rows_wrong']}/80" + (f"（{hit}）" if hit else ""),
                 "抓到" if v["rows_wrong"] else "<b>沒抓到</b>", "抓到" if v["u_caught"] else "<b>沒抓到</b>"])
miss = {g: [MU[k]["desc"] for k in MU if MU[k]["rows_wrong"] and MU[k]["per_gate"][g]["wrong"] == 0]
        for g in next(iter(MU.values()))["per_gate"]}
miss_txt = "".join(f"只測 {g} 會漏掉「{'」「'.join(v)}」；" for g, v in miss.items() if v)
n_u = sum(v["u_caught"] for v in MU.values())
n_r = sum(v["rows_wrong"] > 0 for v in MU.values())
blocks["faults"] = (
    table(["注入的錯誤", "80 筆中判錯", "只看 80 筆", "逐元素比對 U"], rows)
    + f'<p>逐元素比對 U 抓到 {n_u}/{len(MU)} 種，只看 80 筆抓到 {n_r}/{len(MU)} 種。'
      '漏掉的是監看埠對調：讀取埠 o2、o4 沒變，判定就不會錯，但量測校正要讀 o1、o3、o5，接錯一樣會出問題。'
      + miss_txt + '所以 5 種功能都要跑。</p>')

# ⑤ 臂長差
rows = []
for dl in A["dl_um"]:
    d = A["disp"][str(dl)]
    lo, hi = d["pass_nm"]
    rng = "整個 ±20 nm" if d["pass_full"] else (f"{lo:+.2f} 到 {hi:+.2f} nm" if hi > lo else "小於 0.25 nm 步距")
    rows.append([f"{dl:g}", rng, sci(d["cross_vs_numpy"])])
la, ls = A["limit_all"], A["limit_single"]
sens = sorted(ls, key=lambda k: min(abs(ls[k][0]), ls[k][1]))
free = [k for k in ls if abs(ls[k][0]) >= 0.6 and ls[k][1] >= 0.6]
coef = A["coef_um2_per_rad"]
tgt = A["target_rad"]
rule = tgt * coef
blocks["arm"] = (
    f'<p>先確認 Caphe 真的用了填入的 n<sub>g</sub>：10 µm 波導的相位對波長斜率 dψ/dλ，Caphe 為 {A["slope_caphe"]:.2f} rad/µm，'
    f'公式 −2π n<sub>g</sub> L／λ² 為 {A["slope_theory"]:.2f} rad/µm，差 '
    f'{abs(A["slope_caphe"] / A["slope_theory"] - 1) * 100:.2f}%（線性擬合 1530–1570 nm）。'
    '再把每個波長的 Caphe U 與「NumPy 模型＋相同 θ 偏移」比對（表中最後一欄），兩者一致，代表加了波導的電路仍然接對。</p>'
    + table(["上臂多出 ΔL（µm）", "80 筆全對的雷射波長範圍", "Caphe 與 NumPy 最大差"], rows)
    + table(["θ 偏移情況", "80 筆全對的範圍（rad）"],
            [["7 顆同向等量", f"{la[0]:+.3f} 到 {la[1]:+.3f}"]]
            + [[f"只有 {k}", ("±0.6 內都不出錯" if k in free else
                              ("−0.6 以下" if abs(ls[k][0]) >= 0.6 else f"{ls[k][0]:+.3f}") + f" 到 {ls[k][1]:+.3f}")]
               for k in sens])
    + '<p class="muted">θ 偏移掃描範圍 ±0.6 rad、步距 0.0005 rad。</p>'
    + '<ul>'
    + f'<li><b>最敏感的 MZI：</b>{sens[0]}、{sens[1]}、{sens[2]}；{"、".join(free)} 單獨偏移 ±0.6 rad 內都不影響判定。佈局時先讓前三顆的兩臂等長。</li>'
    + f'<li><b>佈局規則：</b>7 顆同向偏移超過 {A["delta_max"]:.3f} rad 就會判錯；但 heater 本身也有誤差（M1 s4 要求 {tgt} rad），'
      f'所以殘留相位以 {tgt} rad 為目標：<b>ΔL × |Δλ| ≤ {tgt} × λ²／(2π n<sub>g</sub>) = {rule * 1e3:.2f}×10<sup>−3</sup> µm²</b>。'
      f'雷射偏移 ±1 nm 時 ΔL ≤ {rule / 1e-3:.1f} µm；±0.1 nm 時 ΔL ≤ {rule / 1e-4:.0f} µm。</li>'
    + '<li><b>對稱設計最安全：</b>兩臂用同樣的彎道與長度（ΔL ≈ 0），heater 放在其中一臂但不改變長度，就不受雷射波長影響。</li>'
    + '</ul>')

ok = (R["rows_ok"] == R["rows_total"] == 80 and R["max_diff_vs_numpy"] < 1e-12 and NL["n_links"] == 9
      and NL["n_external"] == 10 and all(v["u_caught"] for v in MU.values()))
blocks["verdict"] = (f'<p><b>本次驗收：{"通過" if ok else "未通過"}。</b>連接表 {NL["n_mzi"]} 顆 MZI、{NL["n_links"]} 條連線、'
                     f'{NL["n_external"]} 個外部埠；Caphe {R["rows_ok"]}/{R["rows_total"]}，U 與 NumPy 最大差 {sci(R["max_diff_vs_numpy"])}；'
                     f'{n_u}/{len(MU)} 種接線錯誤被抓到；臂長規則 ΔL × |Δλ| ≤ {rule * 1e3:.2f}×10<sup>−3</sup> µm²。</p>')

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