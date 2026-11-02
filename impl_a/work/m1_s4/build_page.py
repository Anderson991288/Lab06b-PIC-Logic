"""把 out/m1_s4_result.json 寫進 course/m1_s4.html 的 BEGIN/END 區塊。

用法：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m1_s4\\build_page.py
只取代標記之間的內容；先寫暫存檔、檢查標記完整後再原子替換。
"""
import json
import os
import re
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PAGE = HERE.parents[1] / "course" / "m1_s4.html"
R = json.loads((HERE / "out" / "m1_s4_result.json").read_text(encoding="utf-8"))
G = R["gates"]
GATES = list(G)
A, NI, S = R["anatomy"], R["nonideal"], R["synth"]


def table(head, rows):
    return ("<table><tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</table>")


def badge(ok, yes="通過", no="失敗"):
    return f'<span class="badge {"pass" if ok else "fail"}">{yes if ok else no}</span>'


def yn(ok):
    return badge(ok, "仍全對", "有判錯")


blocks = {}
rows = []
for g in GATES:
    rows.append([g, "θ"] + [f"{v:.4f}" for v in G[g]["theta"]])
    rows.append(["", "φ"] + [f"{v:.4f}" for v in G[g]["phi"]])
blocks["phases"] = table(["功能", ""] + [f"M{k}" for k in range(1, 8)], rows)

# 2 輸入功能的 ΔP 是否與 x3、x4 無關
indep = {}
for g in ("AND2", "OR2", "XOR2"):
    d = np.array(G[g]["delta"]).reshape(4, 4)        # 列序：x1 最低位 → reshape 後每列是同一組 (x3,x4)
    indep[g] = float(np.abs(d - d[0]).max())
blocks["truth"] = (
    f'<div class="kpis"><div class="kpi"><b>{R["n_correct"]}/{R["n_rows"]}</b>筆正確</div>'
    f'<div class="kpi"><b>{max(G[g]["max_diff_ref"] for g in GATES):.0e}</b>與原版最大差</div></div>'
    + table(["功能", "16 組正確", "餘裕（最小 |ΔP|）", "c₀（0000 的 ΔP）", "相位取 4 位小數", "與原版每列 ΔP 最大差"],
            [[g, f'{G[g]["n_ok"]}/16', f'{G[g]["margin"]:.3f}', f'{A[g]["c0"]:+.3f}',
              badge(G[g]["round4_ok"], "仍全對", "有判錯") + f'（{G[g]["round4_margin"]:.3f}）', f'{G[g]["max_diff_ref"]:.0e}']
             for g in GATES])
    + f'<p>2 輸入功能的 ΔP 隨 x3、x4 改變的最大差：' + "、".join(f"{g} {v:.0e}" for g, v in indep.items())
    + '——幾乎為 0（最佳化的數值精度），相位把 x3、x4 的光對讀取差值的影響壓到可忽略。'
    + f'回歸測試：M1 s2 {R["regression"]["test_b7"]["n"] - R["regression"]["test_b7"]["failed"]}/{R["regression"]["test_b7"]["n"]}、'
      f'M1 s3 {R["regression"]["test_readout"]["n"] - R["regression"]["test_readout"]["failed"]}/{R["regression"]["test_readout"]["n"]} 仍通過。</p>')

xor_min = min(GATES, key=lambda g: G[g]["margin"])
blocks["why"] = (
    table(["功能", "餘裕", "max |R×資料 票數 a|", "max |資料×資料 交叉項|", "拿掉交叉項後", "M1 s3 的「功率相加」算錯"],
          [[g, f'{G[g]["margin"]:.3f}', f'{A[g]["max_abs_a"]:.3f}', f'{A[g]["max_abs_cross"]:.3f}',
            (badge(True, "仍全對") if A[g]["no_cross_ok"] else f'<span class="badge fail">錯 {A[g]["no_cross_wrong"]} 組</span>'),
            f'錯 {A[g]["power_sum_wrong"]}/16'] for g in GATES])
    + "<ul>"
    + f'<li><b>預測 1 成立：</b>餘裕最小的是 {xor_min}（{G[xor_min]["margin"]:.3f}），約為 AND2、OR2 的 1/8。'
      f'它的交叉項（最大 {A["XOR2"]["max_abs_cross"]:.2f}）與 R 的票數（最大 {A["XOR2"]["max_abs_a"]:.2f}）同量級，判定靠的是交叉項。</li>'
    + f'<li><b>預測 2 成立：</b>拿掉資料×資料交叉項，XOR2 錯 {A["XOR2"]["no_cross_wrong"]} 組；AND2、OR2、OR4 仍全對。'
      f'AND4 也錯 {A["AND4"]["no_cross_wrong"]} 組：AND4 本身可以用一條直線分開，但這組相位剛好也用到交叉項（最大 {A["AND4"]["max_abs_cross"]:.2f}）。</li>'
    + f'<li><b>功率相加的後果：</b>在真正的邏輯相位下，「先平方再相加」的錯誤算法 OR4 錯 {A["OR4"]["power_sum_wrong"]} 組、OR2 錯 {A["OR2"]["power_sum_wrong"]} 組，'
      'M1 s3 隨機相位下看到的「平均只錯 1.8 組」低估了這個錯。</li>'
    + "</ul>")

fit = NI["fit"]
scale = 10 ** (-4 * NI["loss_db"] / 10)           # 經過 4 顆 MZI 的功率比例（多數路線）
rows = []
for g in GATES:
    n = NI["gates"][g]
    rows.append([g, f'{G[g]["margin"]:.3f}',
                 f'{yn(n["fdtd_equiv"]["ok"])} {n["fdtd_equiv"]["margin"]:.3f}（ε 對調 {n["fdtd_equiv_swapped"]["margin"]:.3f}）',
                 f'{yn(n["loss"]["ok"])} {n["loss"]["margin"]:.3f}（{n["loss"]["margin"] / G[g]["margin"]:.0%}）']
                + [f'{n["mc_pass"][str(s)]:.0%}' for s in NI["sigmas"]])
worst_loss = min(GATES, key=lambda g: NI["gates"][g]["loss"]["margin"] / G[g]["margin"])
blocks["robust"] = (
    table(["功能", "理想餘裕", f'FDTD 等效誤差（δ={fit["delta_deg"]:+.1f}°、ε={fit["eps"][0]:+.3f}／{fit["eps"][1]:+.3f}）',
           f'每顆 MZI {NI["loss_db"]} dB（餘裕剩下）'] + [f'σ={s:g} rad' for s in NI["sigmas"]], rows)
    + "<ul>"
    + '<li><b>FDTD 等效誤差：</b>把 M0 s3 從 2D FDTD 擬合出的 θ 偏移與耦合器誤差套到全部 7 顆 MZI，五種功能仍全對；'
      f'XOR2 餘裕從 {G["XOR2"]["margin"]:.3f} 降到 {NI["gates"]["XOR2"]["fdtd_equiv"]["margin"]:.3f}，相對降幅最大。</li>'
    + f'<li><b>損耗：</b>經過 4 顆 MZI 的路線功率剩 {scale:.0%}；若所有路線都這樣等比例變小，餘裕也該剩約 {scale:.0%}。'
      f'實際 {worst_loss} 只剩 {NI["gates"][worst_loss]["loss"]["margin"] / G[worst_loss]["margin"]:.0%}：'
      '第 1 層的 rail 2、第 2 層的 rail 0、3、4、第 3 層的 rail 4、第 4 層的 rail 0 沒有 MZI，'
      '不同路線經過 2 到 4 顆 MZI，損耗不均勻，改變了 o2、o4 之間的平衡。'
      'M2 s2 用 PDK 元件模型時會再看到這個效應。</li>'
    + f'<li><b>相位誤差：</b>σ ≤ 0.02 rad 時五種功能 {NI["n_mc"]} 次全部正確；σ = 0.05 rad 時 XOR2 降到 {NI["gates"]["XOR2"]["mc_pass"]["0.05"]:.0%}，'
      f'σ = 0.1 rad 時 XOR2 只剩 {NI["gates"]["XOR2"]["mc_pass"]["0.1"]:.0%}。相位精度的規格要以 XOR2 為準。</li>'
    + "</ul>")

succ = S["n_success"]
blocks["synth"] = (
    table(["項目", "結果"],
          [["16 組", badge(S["ok"], "全對", "有錯")], ["餘裕", f'{S["margin"]:.3f}（與 AND2、OR2 同量級）'],
           ["c₀（0000 的 ΔP）", f'{S["c0"]:+.3f}：R 被導向 o2 較多，所以全暗時判 1'],
           ["成功的起點", f'{succ}/{S["n_restart"]}（各起點的餘裕 {min(S["restart_margins"]):.3f}–{max(S["restart_margins"]):.3f}）'],
           ["計算時間", f'{S["runtime_s"]} 秒'],
           ["θ（M1–M7）", "、".join(f"{v:.3f}" for v in S["theta"])], ["φ（M1–M7）", "、".join(f"{v:.3f}" for v in S["phi"])]])
    + '<p class="muted">這組相位只存在本步的證據檔，不寫進共用相位檔：M2 只實作已選定的 5 種功能。不同起點會收斂到不同相位，但餘裕接近，表示 NAND2 對 B7 來說是「容易」的功能。</p>')

ok = (R["n_correct"] == R["n_rows"] and all(G[g]["max_diff_ref"] < 1e-12 and G[g]["round4_ok"] for g in GATES)
      and all(v["failed"] == 0 for v in R["regression"].values()) and xor_min == "XOR2" and not A["XOR2"]["no_cross_ok"]
      and S["ok"] and S["c0"] > 0)
blocks["verdict"] = (f'<p><b>本次驗收：{"通過" if ok else "未通過"}。</b>80/80 正確、與原版逐列一致、4 位小數仍全對；回歸測試全過；'
                     f'XOR2 餘裕最小且依賴交叉項；NAND2 自行求得（餘裕 {S["margin"]:.3f}、c₀ {S["c0"]:+.3f}）。</p>')

text = PAGE.read_text(encoding="utf-8")
for k, b in blocks.items():
    pat = re.compile(rf"(<!-- BEGIN:{k} -->).*?(<!-- END:{k} -->)", re.S)
    assert len(pat.findall(text)) == 1, f"標記 {k} 必須剛好一組"
    text = pat.sub(lambda m: m.group(1) + "\n" + b + "\n" + m.group(2), text)
tmp = PAGE.with_suffix(".tmp")
tmp.write_text(text, encoding="utf-8")
assert tmp.read_text(encoding="utf-8").rstrip().endswith("</html>")
os.replace(tmp, PAGE)
print("updated", PAGE.name, list(blocks), "verdict", ok, "indep", indep)

# 單檔自足：把 CSS 與圖嵌進頁面（app 的檔案預覽不載入相對路徑）
import sys as _sys  # noqa: E402
_sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import inline_page  # noqa: E402
print("inlined", PAGE.name, "%.0f KB" % (inline_page.run(PAGE)[0] / 1024))