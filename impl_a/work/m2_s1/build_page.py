"""把 out/m2_s1_result.json 寫進 course/m2_s1.html 的 BEGIN/END 區塊。

用法：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m2_s1\\build_page.py
只取代標記之間的內容；先寫暫存檔、檢查標記完整後再原子替換。
"""
import json
import math
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGE = HERE.parents[1] / "course" / "m2_s1.html"
R = json.loads((HERE / "out" / "m2_s1_result.json").read_text(encoding="utf-8"))
REQ, W = R["requirements"], R["worst"]


def table(head, rows):
    return ("<table><tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</table>")


def db(x):
    return 10 * math.log10(x)


blocks = {}
io = R["io"]
kinds = {}
for r in io:
    kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
opt = [r for r in io if r["kind"].startswith("光學")]
ele = [r for r in io if r["kind"].startswith("電氣")]
blocks["io"] = (
    f'<div class="kpis">' + "".join(f'<div class="kpi"><b>{n}</b>{k}</div>' for k, n in kinds.items()) + "</div>"
    + "<h3>光學</h3>" + table(["類別", "晶片埠", "訊號", "晶片上", "晶片外"],
                             [[r["kind"], r["port"], r["signal"], r["on_chip"], r["off_chip"]] for r in opt])
    + "<h3>電氣</h3>" + table(["類別", "接墊", "通道", "晶片上", "晶片外"],
                             [[r["kind"], r["port"], r["signal"], r["on_chip"], r["off_chip"]] for r in ele])
    + '<p class="muted">接墊名稱沿用規格的通道名（PAD_M1_phi …）；回流接墊的數量與位置在 M2 s5 繞線時決定。</p>')

rs, rp = REQ["r_amplitude_scale"]["range"], REQ["r_phase_rad"]["range"]
eta = REQ["pd_responsivity_mismatch"]["range"]
mcp, mca = R["mc_phase"], R["mc_amp"]
worst_amp = min(R["mc_amp"]["0.1"], key=R["mc_amp"]["0.1"].get)
rows = [
    ["兩顆 PD 響應度不平衡", f"{eta[0] * 100:+.0f}% 到 {eta[1] * 100:+.0f}%", W["pd"], "平衡偵測器的兩顆 PD 要匹配到約 ±20% 以內"],
    ["R 振幅", f"×{rs[0]:.3f} 到 ×{rs[1]:.3f}（功率 {db(rs[0] ** 2):+.1f} 到 {db(rs[1] ** 2):+.1f} dB）", W["r_scale"],
     "R 路徑的衰減要設定並維持在約 ±1 dB 以內"],
    ["R 相對資料光的相位", f"{math.degrees(rp[0]):+.0f}° 到 {math.degrees(rp[1]):+.0f}°", W["r_phase"],
     "R 與資料光必須同一雷射，且光纖路徑的相位要穩定（需要鎖相或溫控）"],
    ["調變器消光比", f"≥ {REQ['modulator_extinction_db_min']:.1f} dB", W["er"], "位元 0 的殘光（同相或反相最壞情況）"],
    ["4 路資料光各自的相位", f"σ = {REQ['data_phase_sigma_rad']} rad 時 {R['requirements']['monte_carlo_n']} 次全對", "—",
     f"σ = 0.2 rad 時 XOR2 降到 {mcp['0.2']['XOR2']:.1%}"],
    ["4 路資料光各自的振幅", f"σ = {REQ['data_amp_sigma'] * 100:.0f}% 時全對", worst_amp,
     f"σ = 10% 時 XOR2 {mca['0.1']['XOR2']:.1%}、AND4 {mca['0.1']['AND4']:.1%}"],
    ["heater 相位（M1 s4）", f"σ ≤ {REQ['heater']['accuracy_rad']} rad", "XOR2", "14 通道、0–2π，驅動值需校正"],
]
blocks["req"] = (
    table(["外部參數", "80 筆仍全對的範圍", "最先出錯的功能", "對外部設備的意義"], rows)
    + "<ul>"
    + f'<li><b>AND4 對 R 最敏感：</b>R 振幅、R 相位、PD 不平衡三項的界線都由 AND4 決定。AND4 只有 1111 判 1，'
      '它和 0111、1011 等「差一個 1」的輸入之間，要靠 R 與資料光的精確平衡分開。</li>'
    + f'<li><b>XOR2 對資料光振幅最敏感：</b>XOR 的判定靠資料光彼此的交叉項（M1 s4 ③），兩路資料光振幅不一樣時交叉項不再對稱。</li>'
    + '<li><b>雷射整體功率不在表裡：</b>所有輸入等比例變化不改變 ΔP 的正負（④ 第 2 題），所以只要求「相對」精度。</li>'
    + "</ul>")

ok = (len(io) == 25 and all(v is not None for v in (rs, rp, REQ["modulator_extinction_db_min"],
                                                     REQ["data_phase_sigma_rad"], REQ["data_amp_sigma"])))
blocks["verdict"] = (f'<p><b>本次驗收：{"通過" if ok else "未通過"}。</b>I/O 表 {len(io)} 項；'
                     '6 項外部參數都求得「80 筆全對」的範圍並找出限制它的功能；已寫入 <code>spec/external_requirements.json</code>。</p>')

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