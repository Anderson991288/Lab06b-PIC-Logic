"""把 out/review_checks.json 寫進 course/m2_s4.html 的 BEGIN/END 區塊。

用法：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m2_s4\\build_page.py
只取代標記之間的內容；先寫暫存檔、檢查標記完整後再原子替換。
"""
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGE = HERE.parents[1] / "course" / "m2_s4.html"
D = json.loads((HERE / "out" / "review_checks.json").read_text(encoding="utf-8"))
RES, FAULTS, RULE = D["results"], D["faults"], D["rules"]
R0 = RES["b7_core"]
NAMES = {"C1": "放置", "C2": "光學埠", "C3": "Si 間隙", "C4": "路徑等長", "C5": "heater 對規格通道",
         "C6": "接觸墊", "C7": "金屬間距", "C8": "設計區"}


def table(head, rows):
    return ("<table><tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</table>")


def mark(ok):
    return "通過" if ok else "<b>不通過</b>"


c = R0
c4 = c["C4"]
c7 = c["C7"]
rows = [
    ["C1 " + NAMES["C1"], "GDS 裡 MZI 參照的座標 vs 規格 OPS（欄 × 489 µm、−30 × rail），且沒有鏡像或旋轉",
     f"{c['C1']['n']} 顆，全部一致", mark(c["C1"]["ok"])],
    ["C2 " + NAMES["C2"], "10 個埠的中心在 Si 上、上下緣在 Si 邊界上、往外 10 nm 已不是 Si（端面）",
     f"{sum(p['ok'] for p in c['C2']['ports'])}/10", mark(c["C2"]["ok"])],
    ["C3 " + NAMES["C3"], f"互不相碰的 Si 多邊形之間最小間隙 ≥ {RULE['si_gap']} µm",
     f"最小 {c['C3']['min_gap_um']:.2f} µm（({c['C3']['at'][0]:g}, {c['C3']['at'][1]:g}) 附近，PDK MMI 的兩個錐形端之間）；Si 連通區 {c['C3']['n_regions']} 個",
     mark(c["C3"]["ok"])],
    ["C4 " + NAMES["C4"], "每欄每條 rail（MZI 上下臂、旁路）共 20 段，長度 = 面積 ÷ 0.45 µm；20 段之間的差 &lt; 0.01 µm",
     f"{c4['n']} 段，皆 {c4['median_um']:.3f} µm，最大差 {c4['spread_um']:.1e} µm（中心線值 {c4['centerline_um']:.3f} µm）",
     mark(c4["ok"])],
    ["C5 " + NAMES["C5"], "每個 TiN 區 → (欄, rail, φ／θ) → 規格的相位通道；rail 必須是規格的上臂，且下面有 Si",
     f"{c['C5']['n']} 個 TiN 區，對到 14 個不同通道", mark(c["C5"]["ok"])],
    ["C6 " + NAMES["C6"], "每個 Ti/AL 區壓在一個 TiN 區上，每個 TiN 區兩個", f"{c['C6']['n']} 個，未壓在 TiN 上 {c['C6']['orphan']} 個",
     mark(c["C6"]["ok"])],
    ["C7 " + NAMES["C7"], f"TiN 間距 ≥ {RULE['ht_gap']:g} µm、Ti/AL 間距 ≥ {RULE['pad_gap']:g} µm；另量 TiN 到別段波導（資訊）",
     f"TiN {c7['ht_gap_um']:.0f} µm、Ti/AL {c7['pad_gap_um']:.0f} µm；TiN 到別段波導最近 {c7['ht_to_other_wg_um']:.1f} µm"
     f"（({c7['ht_to_other_wg_at']['heater'][0]:g}, {c7['ht_to_other_wg_at']['heater'][1]:g}) 的 M5 φ 段落墊，"
     "到同一顆 MZI 下臂往 MMI 收的 S 彎）", mark(c7["ok"])],
    ["C8 " + NAMES["C8"], "所有圖形在 GDS 99 內，框的尺寸等於宣告值", f"{c['C8']['size_um'][0]:g} × {c['C8']['size_um'][1]:g} µm",
     mark(c["C8"]["ok"])],
]
blocks = {"checks": table(["項目", "檢查方法", "結果", "判定"], rows)
          + f'<p class="muted">被審查的檔案：<code>{R0["gds"]}</code>，SHA-256 <code>{R0["sha256"][:16]}…</code>（完整值在 JSON）。</p>'}

cs = [f"C{i}" for i in range(1, 9)]
rows = []
for f, desc in FAULTS.items():
    r = RES[f]
    hit = [k for k in cs if not r[k]["ok"]]
    rows.append([desc] + ["<b>抓到</b>" if not r[k]["ok"] else "—" for k in cs] + [f"{len(hit)} 項"])
per = {k: sum(not RES[f][k]["ok"] for f in FAULTS) for k in cs}
rows.append(["抓到幾種錯誤"] + [f"{per[k]}/{len(FAULTS)}" for k in cs] + [""])
det = []
for f, desc in FAULTS.items():
    r = RES[f]
    if not r["C1"]["ok"]:
        m = r["C1"]["mismatch"]
        det.append(f"{desc}：C1 " + "、".join(f"{k} 預期 ({v['expect'][0]:g}, {v['expect'][1]:g})，實際 "
                                              f"({v['got'][0]:g}, {v['got'][1]:g}{'，鏡像' if v['got'][2] else ''})" for k, v in m.items()))
    if not r["C4"]["ok"]:
        det.append(f"{desc}：C4 最大差 {r['C4']['spread_um']:.3f} µm（{r['C4']['worst']}）")
    if not r["C5"]["ok"]:
        det.append(f"{desc}：C5 " + "、".join(f"{p.get('channel', '')} 在 rail {p.get('rail')}，規格 rail {p.get('spec_rail')}"
                                              for p in r["C5"]["problems"]))
    if not r["C3"]["ok"]:
        det.append(f"{desc}：C3 最小間隙 {r['C3']['min_gap_um']:.2f} µm")
blocks["faults"] = (table(["故障版", *[f"{k} {NAMES[k]}" for k in cs], "合計"], rows)
                    + "<ul>" + "".join(f"<li>{d}</li>" for d in det) + "</ul>"
                    + '<p>C4 的「c<i>欄</i>r<i>rail</i>」是第幾欄、第幾條 rail。放錯 rail 時 C4 也不通過：C4 依規格的 rail 歸類 M3 的兩臂，M3 實際下移一條 rail，兩臂的長度被算到錯的 rail 上；'
                      '這是放置錯誤的連帶結果，主要由 C1、C5 指出。'
                      'C2、C6、C7、C8 對這 5 種錯誤都沒有反應：它們檢查的是埠、金屬與邊界，這 5 種錯誤都沒動到這些地方。</p>')

ok = R0["all_ok"] and all(not RES[f]["all_ok"] for f in FAULTS)
blocks["verdict"] = (f'<p><b>本次驗收：{"通過" if ok else "未通過"}。</b>b7_core.gds 8 項審查全部通過；'
                     f'{sum(not RES[f]["all_ok"] for f in FAULTS)}/{len(FAULTS)} 個故障版被抓到；待補項目已列入 ⑤。</p>')

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