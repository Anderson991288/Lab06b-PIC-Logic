"""把 out/m2_s5_result.json 與 out/chip_info.json 寫進 course/m2_s5.html 的 BEGIN/END 區塊。

用法：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m2_s5\\build_page.py
只取代標記之間的內容；先寫暫存檔、檢查標記完整後再原子替換。
"""
import html
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGE = HERE.parents[1] / "course" / "m2_s5.html"
R = json.loads((HERE / "out" / "m2_s5_result.json").read_text(encoding="utf-8"))
I = json.loads((HERE / "out" / "chip_info.json").read_text(encoding="utf-8"))
E, F, D = R["electrical"], R["fan_in"], R["drc"]


def table(head, rows):
    return ("<table><tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</table>")


def sci(x):
    if x == 0:
        return "0"
    m, e = f"{x:.1e}".split("e")
    return f"{m}×10<sup>{int(e)}</sup>"


def g0(x):
    return f"{x + 0.0:g}"


blocks = {}
ec = I["ec"]
n_sig = sum(1 for p in I["pads"] if p["role"] != "回流")
blocks["plan"] = table(["項目", "本版", "說明"], [
    ["晶片尺寸", f"{g0(I['die_um'][0])} × {g0(I['die_um'][1])} µm", "左右邊是 EC 端面；GDS 99 外框"],
    ["光學介面", f"10 個 EC，左右各 5 個，間距 {g0(ec['fiber_pitch_um'])} µm", "光纖陣列間距；輸入 x1–x4、R，輸出 o1–o5"],
    ["扇入／扇出", "S 彎水平 480 µm（最小曲率半徑約 106 µm）", "250 µm → 30 µm；上下順序不變、無交叉"],
    ["電氣介面", f"{n_sig} 個訊號接墊（上 8、下 6）＋ 2 個 GND 接墊，皆 80 × 80 µm", "金屬線 8 µm、匯流排 20 µm"],
    ["核心", "M2 s3 的 B7 核心，原點 (0, 0)", "7 顆 MZI、14 顆 MMI、14 個 heater"],
])

rows = [[f"fiber_in{k}", ec["inputs"][k]["signal"], f"({g0(ec['inputs'][k]['facet'][0])}, {g0(ec['inputs'][k]['facet'][1])})",
         f"{I['fan_in_length_um'][k]:.4f}", f"{I['fan_in_length_unmatched_um'][k]:.1f}"] for k in range(5)]
blocks["fanin"] = (table(["輸入", "訊號", "端面座標（µm）", "EC＋扇入長度（等長版，µm）", "不加凸起時（µm）"], rows)
                   + f'<p>等長版 5 條的最大差 {sci(F["runs"]["none"]["len_spread_um"])} µm（座標對齊 1 nm 格點的殘差）；'
                     f'不加凸起時最大差 {F["runs"]["unmatched"]["len_spread_um"]:.0f} µm。EC 幾何：尖端 {ec["geometry"]["tip_w"]} µm、'
                     f'研磨窗口 {g0(ec["geometry"]["tip_len"])} µm、薄矽漸寬 {g0(ec["geometry"]["taper_len"])} µm、'
                     f'雙層轉換 {g0(ec["geometry"]["bilevel_len"])} µm，共 {g0(ec["length_um"])} µm。</p>')

rows = [[p["name"], f"({g0(p['xy'][0])}, {g0(p['xy'][1])})", "上" if p["side"] == "top" else "下", p["role"]] for p in I["pads"]]
blocks["pads"] = ("<details><summary>16 個接墊的名稱與座標</summary>" + table(["接墊", "中心（µm）", "側", "角色"], rows)
                  + "</details>")

e0 = E["none"]
gates = R["gates"]
n_ok = sum(16 - v["wrong_1550"] for v in gates.values())
all_wl = all(v["all_ok"] for v in gates.values())
loss = R["ec_loss"]
rows = [
    ["核心與 M2 s3 相同", "晶片 GDS 裡的 B7_CORE 與 M2 s3 的 b7_core.gds 逐多邊形比對", "完全相同" if R["core_identical"] else "<b>不同</b>"],
    ["DRC", "CORNERSTONE 規則檔，設計區 = 宣告的晶片尺寸",
     f"{D['none']['total']} 違規、外框外 {D['none']['outside']}（{D['none']['n_rules']} 條規則，含 GDS 4、5）"],
    ["光路連接", "從佈局抽出的連接，由每個 fiber_in 走到核心、由核心走到 fiber_out",
     "5 入 5 出順序一致" if R["optical"]["ok"] else "<b>不一致</b>"],
    ["晶片電路 80 筆", f"fiber_in → fiber_out 的 S 矩陣，{R['wl_um'][0] * 1000:.0f}–{R['wl_um'][-1] * 1000:.0f} nm 共 {len(R['wl_um'])} 點，heater 不重新校正",
     f"1550 nm {n_ok}/80；各波長{'全對' if all_wl else '有錯'}；|U| 與理想最大差 {sci(max(v['mag_diff'] for v in gates.values()))}，"
     f"同一輸出的相位散佈 {sci(max(v['phase_spread'] for v in gates.values()))} rad（扇入格點殘差）"],
    ["EC 損耗", f"每個端面 3 dB（t = {loss['t']:.3f}）時的餘量 ÷ 無損耗餘量",
     f"{min(v['ratio'] for v in loss['gates'].values()):.4f}（= 0.501²），5 種功能都{'全對' if all(v['ok'] for v in loss['gates'].values()) else '有錯'}"],
    ["電氣連通（回讀 GDS）", "GDS 41 連通網 → 接墊；TiN 位置 → 規格通道；每個訊號網只接一個接墊與一個指定 heater",
     f"{e0['n_nets']} 個金屬網：訊號 {e0['n_signal_nets']}、回流 2（GND_T 接 {e0['gnd_heaters']['GND_T']} 個 heater、"
     f"GND_B 接 {e0['gnd_heaters']['GND_B']} 個）；問題 {len(e0['problems'])} 項"],
    ["金屬跨波導", "金屬 ∩ Si，扣掉 heater 接觸墊", f"{e0['crossings']} 處，全部在直波導上（寬度 0.45 µm）" if e0["crossings_straight"]
     else f"{e0['crossings']} 處，<b>有跨到非直波導</b>"],
]
blocks["checks"] = table(["檢查", "方法", "結果"], rows) + (
    "<p>下臂被金屬跨過的 MZI：" + "、".join(f"{k} {v} 處" for k, v in e0["lower_arm_crossings"].items())
    + "。這些都是往下拉的 heater 線經過同一顆 MZI 的下臂；上臂本來就有 4 個 Ti/AL 接觸墊在波導上方。</p>")

rows = []
for f, desc in R["faults"].items():
    drc_t = (f"抓到：{D[f]['total']} 處（" + "、".join(html.escape(k) for k in D[f]["counts"]) + "）") if D[f]["total"] else "0（沒抓到）"
    if f in E:
        el = "抓到：" + E[f]["problems"][0] if E[f]["problems"] else "沒抓到"
        op = "—"
    else:
        el = "—"
        u = F["runs"]["unmatched"]
        lo, hi = u["pass_nm"]
        op = f"抓到：未校正 {u['wrong_uncal']}/80 錯；在 1550 nm 校正後只剩 {lo:+.2f} 到 {hi:+.2f} nm 可用（等長版：整個 ±20 nm）"
    rows.append([desc, drc_t, el, op])
blocks["faults"] = (table(["介面錯誤", "DRC", "電氣連通（回讀 GDS）", "光路與晶片電路"], rows)
                    + '<p>接墊名稱寫反時 GDS 與正常版完全一樣，DRC 不可能抓到；只有把「回讀出的接線」與「對照表」比對才看得出來。'
                      '扇入不等長也是合法幾何，要靠晶片電路的波長掃描。</p>')

ok = (R["core_identical"] and D["none"]["total"] == 0 and D["none"]["outside"] == 0 and R["optical"]["ok"]
      and n_ok == 80 and all_wl and e0["ok"] and e0["crossings_straight"]
      and all(D[f]["total"] or (f in E and E[f]["problems"]) or f == "unmatched" for f in R["faults"])
      and F["runs"]["unmatched"]["wrong_uncal"] > 0)
blocks["verdict"] = (f'<p><b>本次驗收：{"通過" if ok else "未通過"}。</b>核心未修改；晶片 DRC {D["none"]["total"]} 違規；'
                     f'光路 5 入 5 出順序一致；晶片電路 {n_ok}/80，1530–1570 nm 全對；14 個訊號網與 2 個回流網無短路、開路；'
                     f'{len(R["faults"])} 種介面錯誤都被抓到。</p>')

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