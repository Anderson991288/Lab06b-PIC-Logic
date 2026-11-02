"""把 out/m1_s1_result.json 寫進 course/m1_s1.html 的 BEGIN/END 區塊。

用法：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m1_s1\\build_page.py
只取代標記之間的內容；先寫暫存檔、檢查標記完整後再原子替換。
"""
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGE = HERE.parents[1] / "course" / "m1_s1.html"
R = json.loads((HERE / "out" / "m1_s1_result.json").read_text(encoding="utf-8"))
F = R["funcs"]
RHOS = [str(r) for r in R["rhos"]]
MIN = 1e-6


def table(head, rows):
    return ("<table><tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</table>")


def cell(m):
    return f"{m:.2f}" if m > MIN else ('<span class="badge fail">邊界 0</span>' if m > -MIN else '<span class="badge fail">做不到</span>')


blocks = {}
io = R["io"]
mzis = {r: [] for r in range(5)}
for k, (p, layer) in enumerate(io["ops"]):
    mzis[p].append(f"M{k + 1}（第 {layer + 1} 層，上）")
    mzis[p + 1].append(f"M{k + 1}（第 {layer + 1} 層，下）")
blocks["io"] = table(["波導", "輸入", "振幅", "經過的 MZI", "輸出", "角色"],
                     [[str(i["rail"]), i["signal"], str(i["amplitude"]), "、".join(mzis[i["rail"]]),
                       o["signal"], "讀取" if o["role"] == "readout" else "監看"]
                      for i, o in zip(io["inputs"], io["outputs"])]) \
    + f'<p>判定規則：{io["decision"]}。只讀兩路、用差值判定，雷射功率整體飄動時兩路一起變，符號不變。</p>'

enc = R["encoding"]
pick = ["0000", "1000", "1100", "1010", "1111"]
rows = [[e["bits"], "[" + ", ".join(f"{a:g}" for a in e["v"]) + "]", f'{e["p_in"]:g}'] for e in enc if e["bits"] in pick]
blocks["encoding"] = (table(["x1x2x3x4", "光場向量 v", "輸入總功率 Σ|v|²"], rows)
                      + f'<p class="muted">16 組全部在證據 JSON。輸入總功率 {min(e["p_in"] for e in enc):g}–{max(e["p_in"] for e in enc):g}'
                        f'（= 資料位元數 + R² = 位元數 + {io["r_amp"] ** 2:g}），R 佔大部分。位元字串由左到右是 x1、x2、x3、x4。</p>')

a, o, x = F["0001"]["mzi"], F["0111"]["mzi"], F["0110"]["mzi"]
blocks["field"] = (
    f'<p>單一路輸入時上埠功率是 sin²(θ/2) 或 cos²(θ/2)，θ=π/2 時都是 0.5。兩路一起輸入時，上埠光場是兩路光場相加：'
    f'|T₀₀ + T₀₁|² = 1 + sinθ·cosφ，所以同一組輸入「11」可以得到 0 到 2 之間任何值。'
    f'掃描找到的最佳設定也落在這裡：AND 在 θ={a["theta_deg"]:.0f}°、φ={a["phi_deg"]:.0f}°（11 的功率 {a["p"][3]:.2f}，10／01 都是 {a["p"][1]:.2f}）；'
    f'XOR 在 φ={x["phi_deg"]:.0f}°（11 的功率 {x["p"][3]:.2f}，光場互相抵消）。</p>')

codes = list(F)
ok_codes = [c for c in codes if F[c]["mzi"]["ok"]]
bad_codes = [c for c in codes if not F[c]["mzi"]["ok"]]
rows = []
for c in codes:
    m = F[c]["mzi"]
    rows.append([F[c]["name"], c, c[0], cell(m["margin"]),
                 f'θ={m["theta_deg"]:.0f}°、φ={m["phi_deg"]:.0f}°、門檻 {m["threshold"]:.2f}' if m["ok"] else "—"])
blocks["logic"] = (f'<div class="kpis"><div class="kpi"><b>{R["n_ok_mzi"]}/{R["n_funcs"]}</b>單顆 MZI 做得到</div>'
                   f'<div class="kpi"><b>{R["grid_deg"]:g}°</b>掃描間距</div></div>'
                   + table(["函數", "真值 f(00) f(10) f(01) f(11)", "f(00)", "最大餘裕", "最佳設定"], rows)
                   + f'<p>做得到的 {len(ok_codes)} 種，輸入 00 時全部輸出 0；做不到的 {len(bad_codes)} 種'
                     f'（{"、".join(F[c]["name"] for c in bad_codes)}），輸入 00 時全部要輸出 1。'
                     '原因很直接：00 時沒有任何光進來，上埠功率一定是 0，門檻不可能低於 0。'
                     '表中「邊界 0」表示最好也只能讓某個 0 類輸入和 1 類輸入功率相同（例如都是 0），一樣分不開。</p>')

rows = []
for c in codes:
    rows.append([F[c]["name"], cell(F[c]["mzi"]["margin"])] + [cell(F[c]["with_r"][r]["margin"]) for r in RHOS])
n_r = R["n_ok_with_r"]
nor = F["1000"]["with_r"][RHOS[0]]
blocks["ref"] = (table(["函數", "單顆 MZI"] + [f"加 R，ρ={float(r):g}" for r in RHOS], rows)
                 + "<ul>"
                 + f'<li><b>R 補上 00 的光：</b>做得到的函數 {R["n_ok_mzi"]} → ' + " → ".join(f'{n_r[r]}（ρ={float(r):g}）' for r in RHOS)
                 + f'。ρ=0.5 時 NOR 四組輸入的功率剛好都是 {nor["p"][0]:.3f}，餘裕 0：MZI 上埠的兩個係數 a、b 滿足 |a|²+|b|²=1，'
                   '所以 |a|+|b| ≥ 1；要讓 10、01、11 都比 00 暗，需要 |a|+|b| &lt; 2ρ，ρ=0.5 時剛好是等號。</li>'
                 + f'<li><b>R 也是放大器：</b>AND 的餘裕 {F["0001"]["with_r"][RHOS[0]]["margin"]:.2f} → {F["0001"]["with_r"][RHOS[-1]]["margin"]:.2f}、'
                   f'x1 的餘裕 {F["0101"]["with_r"][RHOS[0]]["margin"]:.2f} → {F["0101"]["with_r"][RHOS[-1]]["margin"]:.2f}（ρ 由 {float(RHOS[0]):g} 到 {float(RHOS[-1]):g}），隨 ρ 近似線性增加。'
                   '功率 |R + 資料|² 展開後有一項 2·R·資料，R 越強，這一項越大（相干偵測的增益）。</li>'
                 + f'<li><b>XOR 不受益：</b>XOR {F["0110"]["with_r"][RHOS[0]]["margin"]:.2f} → {F["0110"]["with_r"][RHOS[-1]]["margin"]:.2f}、'
                   f'XNOR 停在約 {F["1001"]["with_r"][RHOS[-1]]["margin"]:.2f}。2·R·資料 這一項對位元是線性的（一條直線），'
                   'XOR 不能用一條直線分開，只能靠資料光彼此的交叉項，它不隨 R 變大。B7 用 R=3，預期 M1 s4 中 XOR 的餘裕也會比 AND、OR 小（到 M1 s4 再用數字驗證）。</li>'
                 + "</ul>")

ok = (R["n_ok_mzi"] == len(R["f00_one"]) and all(c[0] == "0" for c in ok_codes)
      and n_r[RHOS[-1]] == R["n_funcs"] and min(e["p_in"] for e in enc) == 9 and max(e["p_in"] for e in enc) == 13)
blocks["verdict"] = (f'<p><b>本次驗收：{"通過" if ok else "未通過"}。</b>編碼 16 組、輸入總功率 9–13；'
                     f'單顆 MZI {R["n_ok_mzi"]}/{R["n_funcs"]}（正好是 f(00)=0 的那些）；加 R（ρ={float(RHOS[-1]):g}）{n_r[RHOS[-1]]}/{R["n_funcs"]}。</p>')

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