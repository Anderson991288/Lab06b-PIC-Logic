"""產生合併後的課程頁：C:\\LAB\\Lab06b\\course\\*.html。

做法（可重複執行）：
  1. 主線取實作 A 的步驟頁（impl_a/course/），連到程式與證據的相對連結改指 ../impl_a/。
  2. 每頁在「判讀練習」之前插入 merge/fragments/<step>.html（另一套獨立實作 B 的做法、結果與對照），
     導覽列同步加入，之後的節號自動往後順延；修改歷史加一筆。
  3. 圖：實作 A 的圖複製到 course/figures/，實作 B 的圖複製到 course/figures_b/，再全部嵌入（單檔，< 480 KB）。
  4. 檢查：不得出現本機路徑與其他計畫字樣；列出被順延節號在內文的引用，供人工確認。
用法：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\merge\\build_course.py
"""
import base64
import io
import re
import shutil
import sys
from pathlib import Path

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
LAB = Path(__file__).resolve().parents[1]
A, B = LAB / "impl_a", LAB / "impl_b"
OUT = LAB / "course"
FRAG = Path(__file__).resolve().parent / "fragments"
BUDGET = 480 * 1024
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
STEPS = [f"m{m}_s{s}" for m, n in ((0, 3), (1, 5), (2, 7), (3, 2)) for s in range(1, n + 1)]
LEAK = re.compile(r"[A-Za-z]:\\|/mnt/[a-z]/(?!&lt;)|EDA_Claude|EDA_Codex|Codex|Claude|Lab0\d[a-z]?\b(?<!Lab06b)|lab01a|C01|luceda_20")
HISTORY = "<p>2026-11-01：與另一套獨立完成的實作合併為單一課程；新增「對照：另一套獨立實作」一節，主線內容與數字不變。</p>"


def copy_figures():
    for src, dst in ((A / "course" / "figures", OUT / "figures"), (B / "course" / "figures", OUT / "figures_b")):
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    shots = B / "work" / "virtuoso_reproduction" / "out" / "screenshots"
    vdir = OUT / "figures_b" / "virtuoso"
    vdir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(shots / "virtuoso_core.png", vdir / "virtuoso_core.png")
    im = Image.open(shots / "rve_final.png")
    im.crop((0, 0, im.width, 466)).save(vdir / "rve_final_crop.png")  # 下方檔案路徑列不放


def relink(text):
    """主線頁裡的 ../work/、../spec/ 等改指 ../impl_a/；總目錄連結不變。"""
    return re.sub(r'href="\.\./(?!Lab06b_index\.html)(?!impl_[ab]/)', 'href="../impl_a/', text)


def insert_fragment(step, text):
    frag = (FRAG / f"{step}.html").read_text(encoding="utf-8").strip()
    m = re.search(r'<h2 id="read">', text) or re.search(r'<h2 id="(\w+)">[①-⑳]\s*常見失敗', text)
    assert m, step
    text = text[:m.start()] + frag + "\n\n" + text[m.start():]
    before_id = re.match(r'<h2 id="(\w+)">', text[m.start() + len(frag) + 2:]).group(1)
    nav = f'<a href="#{before_id}">'
    assert nav in text, (step, nav)
    text = text.replace(nav, '<a href="#alt">對照：另一套獨立實作</a>' + nav, 1)
    return text


def renumber(step, text):
    """h2 依出現順序重新編號；導覽列跟著改；回報內文裡指向被順延節號的引用。"""
    heads = list(re.finditer(r'<h2 id="(\w+)">([①-⑳]?)\s*(.*?)</h2>', text, re.S))
    numbered = [h for h in heads if h.group(2) or h.group(1) == "alt"]
    new_no, old_to_new = {}, {}
    for i, h in enumerate(numbered):
        new_no[h.group(1)] = CIRCLED[i]
        if h.group(2):
            old_to_new[h.group(2)] = CIRCLED[i]

    def fix_head(m):
        if m.group(1) not in new_no:
            return m.group(0)
        return f'<h2 id="{m.group(1)}">{new_no[m.group(1)]} {m.group(3)}</h2>'
    text = re.sub(r'<h2 id="(\w+)">([①-⑳]?)\s*(.*?)</h2>', fix_head, text, flags=re.S)

    def fix_nav(m):
        i = m.group(1)
        if i not in new_no:
            return m.group(0)
        return f'<a href="#{i}">{new_no[i]} {m.group(3)}</a>'
    text = re.sub(r'<a href="#(\w+)">([①-⑳]?)\s*([^<]*)</a>', fix_nav, text)
    shifted = {o: n for o, n in old_to_new.items() if o != n}
    return text, shifted


def fix_refs(step, text, maps):
    """內文的節號引用跟著順延：「M2 s3 ⑦」用 M2 s3 的對照，其餘用本頁的；修改歷史保留原文。"""
    start = text.index("</nav>")
    end = text.find('<h2 id="history">')
    end = len(text) if end < 0 else end
    body = text[start:end]
    changed = []

    def rep(m):
        if m.group(0).startswith("<"):
            return m.group(0)  # 標題與內嵌圖不動
        page = f"m{m.group(2)}_s{m.group(3)}" if m.group(1) else step
        new = maps.get(page, {}).get(m.group(4), m.group(4))
        if new != m.group(4):
            changed.append(f"{m.group(1) or ''}{m.group(4)}→{new}")
        return (m.group(1) or "") + new
    body = re.sub(r'<h2 .*?</h2>|<img\b[^>]*>|(M(\d) s(\d)\s*)?([①-⑳])', rep, body, flags=re.S)
    return text[:start] + body + text[end:], changed


def shift_map(step):
    text = insert_fragment(step, relink((A / "course" / f"{step}.html").read_text(encoding="utf-8")))
    return renumber(step, text)[1]


def encode(path, small):
    raw = path.read_bytes()
    if path.suffix.lower() == ".svg":
        return "image/svg+xml", raw
    if not small:
        return "image/png", raw
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    b1, b2 = io.BytesIO(), io.BytesIO()
    im.quantize(colors=256, method=Image.Quantize.FASTOCTREE).save(b1, format="PNG", optimize=True)
    im.save(b2, format="JPEG", quality=85, optimize=True)
    return min((("image/png", raw), ("image/png", b1.getvalue()), ("image/jpeg", b2.getvalue())), key=lambda t: len(t[1]))


def inline(page, text):
    text = re.sub(r'<style data-href="([^"]+)">.*?</style>',
                  lambda m: f'<style data-href="{m.group(1)}">\n{(page.parent / m.group(1).split("?")[0]).read_text(encoding="utf-8")}\n</style>',
                  text, flags=re.S)
    text = re.sub(r'<link rel="stylesheet" href="([^"]+)">',
                  lambda m: f'<style data-href="{m.group(1)}">\n{(page.parent / m.group(1).split("?")[0]).read_text(encoding="utf-8")}\n</style>', text)

    def imgs(small):
        def rep(m):
            tag = m.group(0)
            src = re.search(r'\bdata-src="([^"]+)"', tag) or re.search(r'\bsrc="([^"]+)"', tag)
            if not src or src.group(1).startswith("data:"):
                return tag
            rel = src.group(1)
            p = page.parent / rel.split("?")[0]
            assert p.exists(), (page.name, rel)
            mime, data = encode(p, small)
            body = re.sub(r'\s*\bdata-src="[^"]*"', "", tag)
            return re.sub(r'\bsrc="[^"]*"', f'data-src="{rel}" src="data:{mime};base64,{base64.b64encode(data).decode()}"', body, count=1)
        return re.sub(r"<img\b[^>]*>", rep, text)
    out = imgs(False)
    small = len(out.encode("utf-8")) > BUDGET
    if small:
        out = imgs(True)
    return out, small


def leaks(text):
    plain = re.sub(r'(src|data-src)="[^"]*"', "", text)
    plain = re.sub(r"<style.*?</style>", "", plain, flags=re.S)
    return sorted({m.group(0) for m in LEAK.finditer(plain)})


def build(step, maps):
    text = (A / "course" / f"{step}.html").read_text(encoding="utf-8")
    text = relink(text)
    text = insert_fragment(step, text)
    text, shifted = renumber(step, text)
    text, refs = fix_refs(step, text, maps)
    text = text.replace("<footer>", HISTORY + "\n<footer>", 1) if HISTORY not in text else text
    page = OUT / f"{step}.html"
    out, small = inline(page, text)
    assert out.rstrip().endswith("</html>")
    page.write_text(out, encoding="utf-8")
    n = len(out.encode("utf-8"))
    bad = leaks(out)
    print(f"{step}: {n / 1024:5.0f} KB{'（圖已壓縮）' if small else ''}"
          f"{'  引用順延 ' + ' '.join(refs) if refs else ''}{'  LEAK ' + str(bad) if bad else ''}")
    assert n <= 512 * 1024, step
    return not bad


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    shutil.copy2(A / "course" / "course.css", OUT / "course.css")
    copy_figures()
    todo = sys.argv[1:] or STEPS
    maps = {s: shift_map(s) for s in STEPS if (FRAG / f"{s}.html").exists()}
    ok = all([build(s, maps) for s in todo if (FRAG / f"{s}.html").exists()])
    missing = [s for s in todo if not (FRAG / f"{s}.html").exists()]
    if missing:
        print("尚未寫對照段落：", " ".join(missing))
    sys.exit(0 if ok else 1)
