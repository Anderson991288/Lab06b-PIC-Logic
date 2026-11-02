"""把 out/tests.json、out/m1_s2_result.json 寫進 course/m1_s2.html 的 BEGIN/END 區塊。

用法：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m1_s2\\build_page.py
只取代標記之間的內容；先寫暫存檔、檢查標記完整後再原子替換。
"""
import sys
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import b7                   # noqa: E402

PAGE = HERE.parents[1] / "course" / "m1_s2.html"
TJ = json.loads((HERE / "out" / "tests.json").read_text(encoding="utf-8"))
R = json.loads((HERE / "out" / "m1_s2_result.json").read_text(encoding="utf-8"))
IN, OUTS = b7.IN_SIGNALS, b7.OUT_SIGNALS

NAME = {"test_unitary": "么正性", "test_trace_matches_matrix": "逐層追蹤 = 矩陣", "test_trace_energy_each_layer": "每層功率守恆",
        "test_path_sum": "路徑展開 = 矩陣", "test_reachability": "沒有路徑就沒有光", "test_all_cross_permutation": "黃金值：全交叉排列",
        "test_all_bar_identity": "全直通", "test_reference_matrix": "黃金值：原版 U", "test_reference_paths": "黃金值：原版路徑",
        "test_same_layer_commute": "同層可交換"}
ORDER = list(NAME)


def badge(ok, yes="通過", no="失敗"):
    return f'<span class="badge {"pass" if ok else "fail"}">{yes if ok else no}</span>'


def table(head, rows):
    return ("<table><tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</table>")


blocks = {}
blocks["ops"] = table(["MZI", "OPS", "上臂（局部 0）", "下臂（局部 1）", "層", "相位"],
                      [[f"M{k + 1}", f"({p}, {layer})", f"rail {p}（{IN[p]} 那一列）", f"rail {p + 1}（{IN[p + 1]} 那一列）",
                        f"第 {layer + 1} 層", f"θ{k + 1}、φ{k + 1}"] for k, (p, layer) in enumerate(b7.OPS)])

tests = sorted(TJ["tests"], key=lambda t: ORDER.index(t["name"]))
blocks["tests"] = (f'<div class="kpis"><div class="kpi"><b>{TJ["n_pass"]}/{TJ["n_total"]}</b>通過</div></div>'
                   + table(["測試", "檢查的性質", "結果"],
                           [[f'{NAME[t["name"]]}<br><code>{t["name"]}</code>', t["doc"], badge(t["passed"])] for t in tests]))
blocks["faults"] = (f'<div class="kpis"><div class="kpi"><b>{TJ["n_detected"]}/{TJ["n_mutants"]}</b>故障被抓到</div></div>'
                    + table(["代號", "故障", "抓到它的測試", "結果"],
                            [[m["id"], m["fault"], "、".join(NAME[c] for c in sorted(m["caught_by"], key=ORDER.index)) or "—",
                              badge(m["detected"], "抓到", "漏掉")] for m in TJ["mutants"]]))

C = R["path_counts"]
d = R["demo"]
U2 = d["U2"]
rows = [[OUTS[j] + ("（讀取）" if j in b7.READOUT else "")] + [str(C[j][i]) if C[j][i] else '<b>0</b>' for i in range(5)] for j in range(5)]
cancel = [(IN[i], OUTS[j], C[j][i]) for j in range(5) for i in range(5) if C[j][i] and U2[j][i] < 1e-12]
blocks["paths"] = (
    "<p><b>路徑數</b>（與相位無關，只由接線決定；列＝出口，欄＝入口）：</p>"
    + table(["出口＼入口"] + IN, rows)
    + "<ul>"
    + f'<li><b>永遠沒有光：</b>{"、".join(f"{a}→{b}" for a, b in R["zero_pairs"])}。x4、R 從 rail 3、4 進來；'
      '第 1 層 M2 最多把光往上帶到 rail 3，第 2 層只有 M3（rail 1–2）碰不到它，第 3 層 M5 到 rail 2，第 4 層 M6 到 rail 1——'
      '最高只到 o2，到不了 o1（rail 0）。</li>'
    + f'<li><b>參考光 R 到兩個讀取埠：</b>R→o2 {C[1][4]} 條、R→o4 {C[3][4]} 條；x1、x2 到 o2 各 {C[1][0]} 條，到 o4 各 {C[3][0]} 條。'
      '路徑越多，相位能調整的自由度越多。</li>'
    + "".join(f'<li><b>兩條路抵消：</b>{a}→{b} 有 {n} 條路徑，但在這組相位下 |U|² = 0。</li>' for a, b, n in cancel)
    + f'<li><b>示範輸入 {d["bits"]}：</b>五路輸出功率 ' + "、".join(f'{OUTS[j]} {p:.3f}' for j, p in enumerate(d["out_power"]))
    + f'；ΔP = {d["out_power"][1]:.3f} − {d["out_power"][3]:.3f} = {d["delta"]:.3f}，判 {d["bit"]}。總和 {sum(d["out_power"]):.3f} = 輸入 11。</li>'
    + "</ul>")

ok = (TJ["n_pass"] == TJ["n_total"] and TJ["n_detected"] == TJ["n_mutants"])
blocks["verdict"] = (f'<p><b>本次驗收：{"通過" if ok else "未通過"}。</b>單元測試 {TJ["n_pass"]}/{TJ["n_total"]}（含兩組黃金值）；'
                     f'故障注入 {TJ["n_detected"]}/{TJ["n_mutants"]} 被抓到；永遠沒有光的組合 {len(R["zero_pairs"])} 個。</p>')

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