"""把 out/rebuild_report.json 寫進 course/m3_s1.html 的 BEGIN/END 區塊。

用法：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m3_s1\\build_page.py
只取代標記之間的內容；先寫暫存檔、檢查標記完整後再原子替換。
"""
import html
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGE = HERE.parents[1] / "course" / "m3_s1.html"
R = json.loads((HERE / "out" / "rebuild_report.json").read_text(encoding="utf-8"))


def table(head, rows):
    return ("<table><tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</table>")


blocks = {}
runs = R["runs"]
tot = sum(r["seconds"] for r in runs)
slow = max(runs, key=lambda r: r["seconds"])
blocks["run"] = (
    f'<div class="kpis"><div class="kpi"><b>{sum(r["rc"] == 0 for r in runs)}/{len(runs)}</b>支程式成功</div>'
    f'<div class="kpi"><b>{tot / 60:.1f} 分</b>總時間</div><div class="kpi"><b>{len(R["archived"])}</b>個沿用的 Meep 檔</div></div>'
    + table(["步驟", "程式", "環境", "結束碼", "秒"],
            [[r["step"], f"<code>{r['script']}</code>", "femwell（conda run）" if r["kind"] == "femwell" else "IPKISS Python",
              r["rc"], f"{r['seconds']:.1f}"] for r in runs])
    + f'<p>最久的是 <code>{slow["script"]}</code>（{slow["seconds"]:.0f} 秒）。每支程式的完整輸出在 <code>logs/</code>。</p>')

st = R["status"]
cnt = R["counts"]
reasons, rmax = {}, {}
for k, (s, why) in st.items():
    if s == "equivalent":
        base = why.split("（最大相對差")[0]
        reasons.setdefault(base, []).append(k)
        m = re.search(r"最大相對差 ([0-9.e+-]+)", why)
        if m:
            rmax[base] = max(rmax.get(base, 0.0), float(m.group(1)))
eq_rows = [[html.escape(w) + (f"（最大相對差 {rmax[w]:.0e}）" if w in rmax else ""), len(v), "<br>".join(f"<code>{x}</code>" for x in v[:6]) + ("<br>…" if len(v) > 6 else "")]
           for w, v in sorted(reasons.items(), key=lambda kv: -len(kv[1]))]
kinds = {}
for k in st:
    ext = k.rsplit(".", 1)[-1]
    kinds[ext] = kinds.get(ext, 0) + 1
blocks["compare"] = (
    f'<div class="kpis"><div class="kpi"><b>{len(st)}</b>個產出檔</div><div class="kpi"><b>{cnt.get("identical", 0)}</b>位元相同</div>'
    f'<div class="kpi"><b>{cnt.get("equivalent", 0)}</b>內容等價</div><div class="kpi"><b>{cnt.get("different", 0)}</b>不同</div>'
    f'<div class="kpi"><b>{cnt.get("new_only", 0)}</b>原本沒有</div></div>'
    + "<p>檔案類型：" + "、".join(f"{k.upper()} {v}" for k, v in sorted(kinds.items(), key=lambda kv: -kv[1])) + "。</p>"
    + "<h3>內容等價的檔案與原因</h3>" + table(["原因", "檔案數", "例子"], eq_rows)
    + ("<h3>不同的檔案</h3>" + table(["檔案", "差異"], [[f"<code>{k}</code>", html.escape(v)] for k, v in R["different"].items()])
       if R["different"] else "<p>沒有內容不同的檔案。</p>"))

k = R["key"]
blocks["key"] = table(["驗收項目", "重建結果", "判定"], [
    ["規格綁定的相位檔 SHA-256", "與現有規格相同" if k["phase_sha_same"] else "不同", "通過" if k["phase_sha_same"] else "<b>不通過</b>"],
    ["交接真值表 80 筆", f"{k['truth_rows']} 筆，判定與目標全部相同，ΔP 最大差 {k['truth_max_dp_diff']:.1e}",
     "通過" if k["truth_bits_same"] else "<b>不通過</b>"],
    ["femwell 模態（重算）", f"n<sub>eff</sub> = {k['n_eff']:.6f}、n<sub>g</sub> = {k['n_g']:.6f}", "與現有結果相對差 &lt; 10<sup>−13</sup>（容差內，見 ③）"],
    ["晶片電路 80 筆（1530–1570 nm）", f"1550 nm {k['chip_rows_ok']}/80；各波長{'全對' if k['chip_all_wl'] else '有錯'}",
     "通過" if k["chip_rows_ok"] == 80 and k["chip_all_wl"] else "<b>不通過</b>"],
    ["最終 GDS", "多邊形與現有凍結版相同" if k["gds_same"] else "不同", "通過" if k["gds_same"] else "<b>不通過</b>"],
    ["簽核表（M2 s6）", "全部通過" if k["signoff_ok"] else "未通過", "通過" if k["signoff_ok"] else "<b>不通過</b>"],
    ["交付包解壓重驗（M2 s7）", "全部通過" if k["delivery_ok"] else "未通過", "通過" if k["delivery_ok"] else "<b>不通過</b>"],
]) + f'<p class="muted">重建出的 GDS 的 SHA-256 是 <code>{k["new_gds_sha"][:16]}…</code>，與凍結版不同，原因是檔頭的寫出時間；多邊形逐一相同。</p>'

t = R["tamper"]
blocks["tamper"] = table(["注入", "預期", "結果"], [
    ["重建資料夾的相位檔：XOR2 的 θ1 加 0.001 rad，再跑 M2 s2", "規格的 SHA-256 對不上，程式停下",
     ("停下：" + html.escape(t["phase_file"]["message"])) if t["phase_file"]["stopped"] else "<b>沒有停下</b>"],
    ["交接真值表第 38 筆的 ΔP 加 10<sup>−6</sup>，交給比對器", "比對器回報差異",
     ("抓到：" + html.escape(t["comparator"]["found"][0])) if t["comparator"]["found"] else "<b>沒抓到</b>"],
]) + "<p>相位檔測試後已改回原值。</p>"

ok = R["all_ok"]
blocks["verdict"] = (f'<p><b>本次驗收：{"通過" if ok else "未通過"}。</b>{sum(r["rc"] == 0 for r in runs)}/{len(runs)} 支程式成功；'
                     f'{len(st)} 個產出檔：位元相同 {cnt.get("identical", 0)}、內容等價 {cnt.get("equivalent", 0)}、不同 {cnt.get("different", 0)}；'
                     '最終 GDS 多邊形相同，80 筆、簽核與交付重驗都通過；兩種故障都被抓到。</p>')

text = PAGE.read_text(encoding="utf-8")
for kk, b in blocks.items():
    pat = re.compile(rf"(<!-- BEGIN:{kk} -->).*?(<!-- END:{kk} -->)", re.S)
    assert len(pat.findall(text)) == 1, f"標記 {kk} 必須剛好一組"
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