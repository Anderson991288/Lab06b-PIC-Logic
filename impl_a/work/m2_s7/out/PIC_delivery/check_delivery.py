"""檢查交付包是否完整：逐檔比對 manifest.json 的 SHA-256 與大小，並列出清單以外的檔案。只用 Python 標準函式庫。
用法：python check_delivery.py      結束碼 0 = 全部相符
"""
import hashlib
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
root = Path(__file__).resolve().parent
man = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
bad, seen = [], set()
for f in man["files"]:
    p = root / f["path"]
    seen.add(f["path"])
    if not p.exists():
        bad.append(f"缺少 {f['path']}")
    elif p.stat().st_size != f["size"] or hashlib.sha256(p.read_bytes()).hexdigest() != f["sha256"]:
        bad.append(f"內容不符 {f['path']}")
extra = [str(p.relative_to(root)).replace("\\", "/") for p in root.rglob("*") if p.is_file()]
extra = [p for p in extra if p not in seen and p != "manifest.json" and "__pycache__" not in p]
res = dict(ok=not bad and not extra, checked=len(man["files"]), problems=bad, extra=extra)
print(json.dumps(res, ensure_ascii=False))
sys.exit(0 if res["ok"] else 1)
