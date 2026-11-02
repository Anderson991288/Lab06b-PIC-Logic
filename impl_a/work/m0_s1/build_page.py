"""把 out/toolchain_check.json 寫進 course/m0_s1.html 的 BEGIN/END:toolchain 區塊。

用法：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m0_s1\\build_page.py
只取代標記之間的內容；先寫暫存檔、檢查標記完整後再原子替換。
"""
import html
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PAGE = ROOT / "course" / "m0_s1.html"
DATA = json.loads((HERE / "out" / "toolchain_check.json").read_text(encoding="utf-8"))
LABEL = {"pass": "通過", "fail": "失敗", "missing": "未安裝", "blocked": "等待"}

s = DATA["summary"]
rows = "".join(
    f'<tr><td>{html.escape(i["id"])}</td><td>{html.escape(i["name"])}</td>'
    f'<td><span class="badge {i["status"]}">{LABEL[i["status"]]}</span></td>'
    f'<td><code>{html.escape(i["detail"])}</code></td><td>{html.escape(i["fix"])}</td></tr>'
    for i in DATA["items"])
block = (
    f'<p class="muted">執行時間 {DATA["time"]}｜Python {DATA["python"]}｜共 {len(DATA["items"])} 項</p>'
    '<div class="kpis">' + "".join(
        f'<div class="kpi"><span class="badge {k}">{LABEL[k]}</span><b>{s[k]}</b></div>' for k in LABEL) +
    '</div><table><tr><th>編號</th><th>項目</th><th>狀態</th><th>實際輸出</th><th>下一步</th></tr>'
    + rows + '</table>')

text = PAGE.read_text(encoding="utf-8")
pat = re.compile(r"(<!-- BEGIN:toolchain -->).*?(<!-- END:toolchain -->)", re.S)
assert len(pat.findall(text)) == 1, "標記必須剛好一組"
new = pat.sub(lambda m: m.group(1) + "\n" + block + "\n" + m.group(2), text)
tmp = PAGE.with_suffix(".tmp")
tmp.write_text(new, encoding="utf-8")
assert tmp.read_text(encoding="utf-8").rstrip().endswith("</html>")
os.replace(tmp, PAGE)
print("updated", PAGE.name, s)

# 單檔自足：把 CSS 與圖嵌進頁面（app 的檔案預覽不載入相對路徑）
import sys as _sys  # noqa: E402
_sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import inline_page  # noqa: E402
print("inlined", PAGE.name, "%.0f KB" % (inline_page.run(PAGE)[0] / 1024))