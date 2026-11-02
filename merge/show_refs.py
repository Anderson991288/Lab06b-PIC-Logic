"""列出合併頁內文中某些圈號的前後文（略過標題、導覽與內嵌圖），用來確認順延後的引用是否要改。
用法：python show_refs.py <step> <圈號們>   例：python show_refs.py m2_s7 ⑨⑭
"""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
page = Path(__file__).resolve().parents[1] / "course" / f"{sys.argv[1]}.html"
t = page.read_text(encoding="utf-8")
t = re.sub(r'src="data:[^"]+"', "", t)
t = re.sub(r"<style.*?</style>|<nav>.*?</nav>|<h2 .*?</h2>", "", t, flags=re.S)
t = re.sub(r"<[^>]+>", "", t)
for c in sys.argv[2]:
    for m in re.finditer(c, t):
        print(f"[{c}] …{t[max(0, m.start() - 60):m.end() + 40].replace(chr(10), ' ')}…")
for m in re.finditer(r"/mnt/c/\S*", t):
    print("[mnt]", t[max(0, m.start() - 80):m.end() + 20].replace("\n", " "))
