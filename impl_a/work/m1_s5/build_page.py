"""把 spec/pic_spec.json、spec/truth_table.json、out/spec_check.json 寫進 course/m1_s5.html 的 BEGIN/END 區塊。

用法：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m1_s5\\build_page.py
只取代標記之間的內容；先寫暫存檔、檢查標記完整後再原子替換。
"""
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PAGE = ROOT / "course" / "m1_s5.html"
SP = json.loads((ROOT / "spec" / "pic_spec.json").read_text(encoding="utf-8"))
TT = json.loads((ROOT / "spec" / "truth_table.json").read_text(encoding="utf-8"))
CK = json.loads((HERE / "out" / "spec_check.json").read_text(encoding="utf-8"))


def table(head, rows):
    return ("<table><tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</table>")


def badge(ok, yes="通過", no="失敗"):
    return f'<span class="badge {"pass" if ok else "fail"}">{yes if ok else no}</span>'


blocks = {}
ins, outs = SP["optical_inputs"], SP["optical_outputs"]
blocks["io"] = (table(["線路（rail）", "輸入埠", "訊號", "振幅", "輸出埠", "訊號", "用途"],
                      [[str(i["rail"]), i["port"], i["signal"], str(i["amplitude"]), o["port"], o["signal"],
                        "讀取（PD）" if o["role"] == "readout" else "監看"] for i, o in zip(ins, outs)])
                + f'<p>讀取規則：{SP["model"]["decision"]}。輸入為相干光，資料位元以振幅 0／1 表示，R 振幅 {SP["model"]["R_amplitude"]:g}'
                  '（模型尺度，不是電壓或 mW）。</p>')

pc = SP["phase_controls"]
rows = []
for k, (p, layer) in enumerate(SP["core"]["ops"]):
    ch = {c["phase"]: c["channel"] for c in pc if c["mzi"] == k + 1}
    rows.append([f"M{k + 1}", f"rail {p}–{p + 1}", f"第 {layer + 1} 層", f"rail {p}（上臂）", ch["phi"], ch["theta"], str(k)])
blocks["ctrl"] = (table(["MZI", "跨接", "層", "相位段位置", "φ 通道", "θ 通道", "相位陣列索引"], rows)
                  + f'<p>共 {len(pc)} 個通道，每個 heater 有訊號端與回流端；驅動值需要「相位 → 電壓」校正。'
                    '通道名稱同時用在電路模型、佈局的 heater 標籤與接墊表，M2 s6 會檢查三者一致。</p>')

acc = SP["acceptance"]
rows = []
for g in SP["functions"]:
    mine = [r for r in TT["rows"] if r["function"] == g]
    ones = "、".join(r["bits"] for r in mine if r["target"] == 1)
    rows.append([g, f'{sum(r["bit"] == r["target"] for r in mine)}/16', f'{acc["ideal_margin"][g]:.3f}', ones])
blocks["truth"] = (table(["功能", "理想模型正確", "理想餘裕", "目標為 1 的輸入（x1x2x3x4）"], rows)
                   + "<ul>"
                   + f'<li><b>功能驗收：</b>{acc["functional"]}。</li>'
                   + f'<li><b>相位精度：</b>{acc["phase_accuracy_rad"]} rad（{acc["phase_accuracy_note"]}）。</li>'
                   + f'<li><b>佈局：</b>{acc["layout"]}。</li>'
                   + f'<li><b>相位檔：</b><code>{SP["phase_settings"]["file"]}</code>，SHA-256 前 16 碼 <code>{SP["phase_settings"]["sha256"][:16]}</code>。</li>'
                   + "</ul>")

blocks["check"] = (f'<div class="kpis"><div class="kpi"><b>{CK["n_pass"]}/{CK["n_checks"]}</b>檢查通過</div></div>'
                   + table(["代號", "檢查", "結果"], [[c["id"], c["desc"], badge(c["ok"])] for c in CK["checks"]]))
blocks["faults"] = (f'<div class="kpis"><div class="kpi"><b>{CK["n_detected"]}/{CK["n_mutants"]}</b>故障被抓到</div></div>'
                    + table(["代號", "規格寫錯的方式", "失敗的檢查", "結果"],
                            [[m["id"], m["fault"], "、".join(m["failed_checks"]) or "—", badge(m["detected"], "抓到", "漏掉")]
                             for m in CK["mutants"]]))

no_phase = not any(k in json.dumps(SP) for k in ('"theta": [', '"phi": ['))
ok = CK["n_pass"] == CK["n_checks"] and CK["n_detected"] == CK["n_mutants"] and no_phase
blocks["verdict"] = (f'<p><b>本次驗收：{"通過" if ok else "未通過"}。</b>規格不含相位數值；獨立檢查 {CK["n_pass"]}/{CK["n_checks"]}；'
                     f'故障注入 {CK["n_detected"]}/{CK["n_mutants"]} 被抓到。</p>')

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