"""列出課程頁的標題、區塊標記與連結（略過內嵌圖），合併時用來找插入點。
用法：python peek_page.py <page.html> [...]
"""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
for arg in sys.argv[1:]:
    t = Path(arg).read_text(encoding="utf-8")
    t = re.sub(r'src="data:[^"]+"', 'src="DATA"', t)
    t = re.sub(r"<style[^>]*>.*?</style>", "<style/>", t, flags=re.S)
    print(f"== {arg}  ({len(t)} chars without data)")
    for m in re.finditer(r"<(h1|h2|h3)[^>]*>(.*?)</\1>|<!-- (BEGIN|END):(\w+) -->|<section[^>]*id=\"([^\"]+)\"", t, re.S):
        if m.group(1):
            print(f"  {m.group(1)} {re.sub('<[^>]+>', '', m.group(2)).strip()[:90]}")
        elif m.group(3):
            print(f"     <!-- {m.group(3)}:{m.group(4)} -->")
        else:
            print(f"  section#{m.group(5)}")
    links = sorted(set(re.findall(r'href="([^"#][^"]*)"', t)))
    print("  links:", links[:30])
