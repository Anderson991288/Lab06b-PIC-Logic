"""把 out/m0_s2_result.json 寫進 course/m0_s2.html 的 BEGIN/END 區塊（modes、eim、mmi、mzi）。

用法：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m0_s2\\build_page.py
只取代標記之間的內容；先寫暫存檔、檢查標記完整後再原子替換。
"""
import json
import math
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGE = HERE.parents[1] / "course" / "m0_s2.html"
R = json.loads((HERE / "out" / "m0_s2_result.json").read_text(encoding="utf-8"))
M, C, REF = R["modes"], R["cases"], R["reference"]


def f(x, n=3):
    return "—" if x is None else f"{x:.{n}f}"


def table(head, rows):
    return ("<table><tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</table>")


blocks = {}
te0 = M["te0"]
conv = M["mesh_convergence"]
blocks["modes"] = table(
    ["項目", "結果", "說明"],
    [["TE0 有效折射率 n_eff", f(te0["n_eff"], 4), f"網格由粗到細 {f(conv[0]['n_eff'], 5)} → {f(conv[-1]['n_eff'], 5)}，差 "
      f"{abs(conv[0]['n_eff'] - conv[-1]['n_eff']):.1e}，已收斂"],
     ["TE0 群折射率 n_g", f(te0["n_g"], 3), f"由 {te0['wl_um'][0]}–{te0['wl_um'][-1]} µm 的 n_eff 擬合：n_g = n_eff − λ·dn_eff/dλ"],
     ["TE 偏振比例", f(te0["te_fraction"], 3), "接近 1：主電場沿波導寬度方向（晶片平面內）"],
     ["0.45 µm 的 TE1", f(M["te1_at_W"], 4) if M["te1_at_W"] else "不導光",
      f"只比 SiO2 1.444 高 {M['te1_at_W'] - 1.444:.3f}：剛越過截止、模場大半在包覆層，遇彎道即散失" if M["te1_at_W"] else ""],
     ["單模寬度上限", f"{M['single_mode_max_width_um']:.2f} µm",
      f"以 n_eff 高出 SiO2 {M['guide_margin']} 以上算「明確導光」；{M['first_multimode_width_um']:.2f} µm 起 TE1 明確導光"]])

e = M["eim"]
blocks["eim"] = table(
    ["步驟", "做法", "結果"],
    [["1. 垂直方向", "220 nm Si 平板（上下 SiO2）的 TE0，解析解", f"n_slab = {f(e['n_slab_TE0_220nm'], 4)}"],
     ["2. 水平方向", "把 n_slab 當核心、寬 0.45 µm 的平板（電場垂直側壁，用 TM 式）", f"n_EIM = {f(e['n_eim_strip'], 4)}"],
     ["3. 對照 3D", "femwell 直接算 0.45×0.22 µm 截面", f"n_eff = {f(e['n_femwell_strip'], 4)}；EIM 偏高 {e['rel_error'] * 100:.1f}%"],
     ["Meep 2D 用的材料", "核心 n_slab、包覆 SiO2", f"{f(R['sim']['n_core'], 4)}／{f(R['sim']['n_clad'], 3)}"]])

cv = R["mmi_convergence"]
mm = C["mmi"]
blocks["mmi"] = table(
    ["解析度 (px/µm)", "out1（bar）", "out2（cross）", "總穿透", "超額損耗 (dB)", "計算時間 (s)"],
    [[str(c["res"]), f(c["p_out"][0]), f(c["p_out"][1]), f(c["total"]), f(-10 * math.log10(c["total"]), 2),
      f(c["runtime_s"], 0)] for c in cv]
    + [["參考研究（16）", f(REF["mmi"]["p_out"][0]), f(REF["mmi"]["p_out"][1]), f(REF["mmi"]["total"]),
        f(-10 * math.log10(REF["mmi"]["total"]), 2), "—"]])

rows = []
for k, name in (("t0", "切換 θ=0"), ("tpi", "切換 θ=π"), ("tpi2", "分光 θ=π/2"), ("comb", "合光 θ=π/2")):
    s, r = C[k], REF.get(k)
    rows.append([name, f"{f(s['ideal'][0], 2)}／{f(s['ideal'][1], 2)}",
                 f"{f(s['p_out'][0])}／{f(s['p_out'][1])}", f(s["total"]),
                 f"{f(s['p_norm'][0])}／{f(s['p_norm'][1])}", f(s["max_abs_err_norm"], 3),
                 f(s["extinction_db"], 1) if k != "tpi2" else "—",
                 f"{f(r['p_out'][0])}／{f(r['p_out'][1])}" if r else "—"])
blocks["mzi"] = table(["狀態", "理想 out1／out2", "本課程 out1／out2", "總穿透", "除以總穿透後", "與理想最大差",
                       "消光比 (dB)", "參考研究 out1／out2"], rows)

text = PAGE.read_text(encoding="utf-8")
for k, b in blocks.items():
    pat = re.compile(rf"(<!-- BEGIN:{k} -->).*?(<!-- END:{k} -->)", re.S)
    assert len(pat.findall(text)) == 1, f"標記 {k} 必須剛好一組"
    text = pat.sub(lambda m: m.group(1) + "\n" + b + "\n" + m.group(2), text)
tmp = PAGE.with_suffix(".tmp")
tmp.write_text(text, encoding="utf-8")
assert tmp.read_text(encoding="utf-8").rstrip().endswith("</html>")
os.replace(tmp, PAGE)
print("updated", PAGE.name, list(blocks))

# 單檔自足：把 CSS 與圖嵌進頁面（app 的檔案預覽不載入相對路徑）
import sys as _sys  # noqa: E402
_sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import inline_page  # noqa: E402
print("inlined", PAGE.name, "%.0f KB" % (inline_page.run(PAGE)[0] / 1024))