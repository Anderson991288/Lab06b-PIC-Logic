"""課程頁面改成單檔自足：把 course.css 與 figures/ 的圖嵌進 HTML，檔案預覽（不載入相對路徑）也能正常顯示。

用法：
  python work/common/inline_page.py              處理 course/*.html 與 Lab06b_index.html
  在各步的 build_page.py 結尾呼叫 inline_page.run(PAGE)，更新表格後自動重新嵌入。
做法（可重複執行）：
  <link rel="stylesheet" href="X">        → <style data-href="X">X 的內容</style>
  <img src="figures/a.png" ...>           → <img data-src="figures/a.png" src="data:image/png;base64,..." ...>
  已嵌入的頁面再執行時，依 data-href／data-src 從原檔重新嵌入，所以重畫圖之後只要再跑一次。
大小：app 的檔案預覽只顯示 512 KB 以下的頁面。圖先以原檔嵌入；整頁超過 BUDGET 時，改用 256 色 PNG 或 JPEG（取較小者）。
原始圖檔不修改。
"""
import base64
import io
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUDGET = 480 * 1024
LINK = re.compile(r'<link rel="stylesheet" href="([^"]+)">')
STYLE = re.compile(r'<style data-href="([^"]+)">.*?</style>', re.S)
IMG = re.compile(r"<img\b[^>]*>")


def _css(page, href):
    p = (page.parent / href.split("?")[0])
    return f'<style data-href="{href}">\n{p.read_text(encoding="utf-8")}\n</style>'


def _encode(path, small):
    raw = path.read_bytes()
    if not small:
        return "image/png", raw
    from PIL import Image
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    b1 = io.BytesIO()
    im.quantize(colors=256, method=Image.Quantize.FASTOCTREE).save(b1, format="PNG", optimize=True)
    b2 = io.BytesIO()
    im.save(b2, format="JPEG", quality=88, optimize=True)
    best = min((("image/png", raw), ("image/png", b1.getvalue()), ("image/jpeg", b2.getvalue())), key=lambda t: len(t[1]))
    return best


def _imgs(page, text, small):
    def rep(m):
        tag = m.group(0)
        src = re.search(r'\bdata-src="([^"]+)"', tag) or re.search(r'\bsrc="([^"]+)"', tag)
        if not src or src.group(1).startswith("data:"):
            return tag
        rel = src.group(1)
        p = page.parent / rel.split("?")[0]
        if not p.exists():
            return tag
        mime, data = _encode(p, small)
        body = re.sub(r'\s*\bdata-src="[^"]*"', "", tag)
        body = re.sub(r'\bsrc="[^"]*"', f'data-src="{rel}" src="data:{mime};base64,{base64.b64encode(data).decode()}"', body, count=1)
        return body
    return IMG.sub(rep, text)


def run(page):
    """嵌入一頁；回傳 (位元組數, 是否壓縮過圖)。"""
    page = Path(page)
    text = page.read_text(encoding="utf-8")
    text = LINK.sub(lambda m: _css(page, m.group(1)), text)
    text = STYLE.sub(lambda m: _css(page, m.group(1)), text)
    out, small = _imgs(page, text, False), False
    if len(out.encode("utf-8")) > BUDGET:
        out, small = _imgs(page, text, True), True
    tmp = page.with_suffix(".tmp")
    tmp.write_text(out, encoding="utf-8")
    assert tmp.read_text(encoding="utf-8").rstrip().endswith("</html>")
    os.replace(tmp, page)
    return len(out.encode("utf-8")), small


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    pages = sorted((ROOT / "course").glob("*.html")) + [ROOT / "Lab06b_index.html"]
    for p in pages:
        n, small = run(p)
        print(f"{p.name:22s} {n / 1024:7.0f} KB{'（圖已壓縮）' if small else ''}")
