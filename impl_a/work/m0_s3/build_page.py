"""把 out/tests.json、out/m0_s3_result.json 寫進 course/m0_s3.html 的 BEGIN/END 區塊。

用法：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m0_s3\\build_page.py
只取代標記之間的內容；先寫暫存檔、檢查標記完整後再原子替換。
"""
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGE = HERE.parents[1] / "course" / "m0_s3.html"
TJ = json.loads((HERE / "out" / "tests.json").read_text(encoding="utf-8"))
R = json.loads((HERE / "out" / "m0_s3_result.json").read_text(encoding="utf-8"))

NAME = {"test_unitary": "么正性", "test_closed_form": "解析式", "test_switch_states": "切換態",
        "test_split_state": "分光態", "test_bar_cross_power": "直通／交叉功率", "test_phi_only_phase": "φ 只是相位",
        "test_coherent_combine": "相干合光", "test_theta_for_bar_inverse": "θ 反算", "test_layout_mapping": "佈局換算",
        "test_loss": "損耗", "test_mmi_error": "分光比誤差", "test_embed": "嵌入大矩陣", "test_cascade_unitary": "串接么正性"}
ORDER = list(NAME)


def badge(ok, yes="通過", no="失敗"):
    return f'<span class="badge {"pass" if ok else "fail"}">{yes if ok else no}</span>'


def table(head, rows):
    return ("<table><tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</table>")


blocks = {}
tests = sorted(TJ["tests"], key=lambda t: ORDER.index(t["name"]))
blocks["tests"] = (f'<div class="kpis"><div class="kpi"><b>{TJ["n_pass"]}/{TJ["n_total"]}</b>通過</div>'
                   f'<div class="kpi"><b>1e-12</b>容差</div></div>'
                   + table(["測試", "檢查的性質", "結果"],
                           [[f'{NAME[t["name"]]}<br><code>{t["name"]}</code>', t["doc"], badge(t["passed"])] for t in tests]))

blocks["faults"] = (f'<div class="kpis"><div class="kpi"><b>{TJ["n_detected"]}/{TJ["n_mutants"]}</b>故障被抓到</div></div>'
                    + table(["代號", "故障（模型改壞的方式）", "抓到它的測試", "結果"],
                            [[m["id"], m["fault"], "、".join(NAME[c] for c in sorted(m["caught_by"], key=ORDER.index)) or "—",
                              badge(m["detected"], "抓到", "漏掉")] for m in TJ["mutants"]]))

rows = []
for r in R["compare"]:
    th = f'{r["theta_eff_deg"]:.1f}°（{r["theta_err_deg"]:+.1f}°）' if "theta_eff_deg" in r else "—"
    rows.append([r["name"], f'{r["model"][0]:.3f}／{r["model"][1]:.3f}', f'{r["fdtd_norm"][0]:.4f}／{r["fdtd_norm"][1]:.4f}',
                 f'{r["max_abs_diff"]:.4f}', th, f'{r["model_vs_s2_ideal"]:.0e}'])
blocks["fdtd"] = (table(["狀態", "模型 out1／out2", "FDTD（除以總穿透）", "最大差", "由直通功率反推的 θ", "模型對 M0 s2 理想值"], rows)
                  + f'<p>模型與 FDTD 的最大差 {R["max_abs_diff"]:.3f}，出現在分光狀態；三個單一出口狀態都在 0.004 以內。'
                    f'模型與 M0 s2 頁面上的「理想值」差 {R["model_vs_s2_ideal"]:.0e}（浮點誤差），表示兩邊的符號慣例與埠換算一致。</p>')

f = R["fit"]
c = {r["case"]: r for r in R["compare"]}
blocks["nonideal"] = (
    f'<p>如果差異只是 θ 多了一個固定偏移，θ=0 與 θ=π 反推出的偏移應該大小相同、方向相反；實際是 '
    f'{c["t0"]["theta_err_deg"]:+.1f}° 與 {c["tpi"]["theta_err_deg"]:+.1f}°，而 θ=π/2 是 {c["tpi2"]["theta_err_deg"]:+.1f}°。'
    f'所以 θ=0／π 的漏光（{c["t0"]["fdtd_norm"][0] * 100:.2f}%、{c["tpi"]["fdtd_norm"][1] * 100:.2f}%）不是單純相位誤差：理想耦合器的 MZI 消光比是無限大，有限消光比需要非理想項。</p>'
    + table(["等效參數", "擬合值", "說明"],
            [["θ 偏移 δ", f'{f["delta_deg"]:+.2f}°', "所有 θ 都多這麼多"],
             ["耦合器分光誤差 ε1、ε2", f'{f["eps"][0]:+.4f}、{f["eps"][1]:+.4f}', "兩顆耦合器的等效直通功率 1/2＋ε（順序無法分辨）"],
             ["擬合殘差", f'{f["max_resid"]:.0e}', f'{f["n_points"]} 個參數對 {f["n_points"]} 個數據點，必然完全重現'],
             ["對照：單顆 MMI 的 FDTD", f'ε = {f["single_mmi_eps"]:+.5f}', "M0 s2 ③ 單獨模擬的 PDK MMI，分光幾乎完美"]])
    + '<div class="notice"><b>判讀：</b>等效 ε 比單顆 MMI 的實際分光誤差大兩個數量級，所以它不是 MMI 的分光比誤差，而是把其他效應一起吸收的「等效值」。'
      '可能的來源包括 MMI 跨接相位不剛好 90°（<code>coupler(ε)</code> 只描述功率不平衡，不描述相位）、'
      'θ 段折射率台階的反射與模態失配（θ=π 的 Δn 最大，漏光也最大）。要分開這些來源需要 FDTD 輸出相位，本課程沒有做。'
      '這些差異都在 0.02 以內，M1 用理想模型的結論不受影響。</div>')

ok = (TJ["n_pass"] == TJ["n_total"] and TJ["n_detected"] == TJ["n_mutants"]
      and R["model_vs_s2_ideal"] < 1e-12 and R["max_abs_diff"] < 0.05)
blocks["verdict"] = (f'<p><b>本次驗收：{"通過" if ok else "未通過"}。</b>單元測試 {TJ["n_pass"]}/{TJ["n_total"]}；'
                     f'故障注入 {TJ["n_detected"]}/{TJ["n_mutants"]} 被抓到；模型對 M0 s2 理想值差 {R["model_vs_s2_ideal"]:.0e}；'
                     f'模型對 FDTD 最大差 {R["max_abs_diff"]:.3f}。</p>')

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