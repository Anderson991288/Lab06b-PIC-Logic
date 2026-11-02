"""用交付包內的原始碼重建晶片 GDS，與 layout/B7_final.gds 逐多邊形比對（需要 IPKISS 與 CORNERSTONE PDK 授權）。
GDS 檔頭含寫出時間，所以比對多邊形而不是比對 SHA-256。
用法：python rebuild_gds.py [輸出路徑]      結束碼 0 = 幾何完全相同
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
root = Path(__file__).resolve().parent
src = root / "source"
sys.path.insert(0, str(src / "work" / "common"))
import b7_chip as BC  # noqa: E402
import b7_layout as BL  # noqa: E402
import gds2png as G  # noqa: E402

spec = json.loads((src / "spec" / "pic_spec.json").read_text(encoding="utf-8"))
ops = [list(o) for o in spec["core"]["ops"]]
info = json.loads((src / "work" / "m2_s3" / "out" / "layout_info.json").read_text(encoding="utf-8"))
contacts = {k: v for m in info["mzi"] for k, v in m["heater_contacts_um"].items()}
te = json.loads((src / "work" / "m0_s2" / "out" / "m0_s2_result.json").read_text(encoding="utf-8"))["modes"]["te0"]
out = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "rebuilt.gds"
core = BL.B7Core(ops=ops, theta=[0.0] * 7, phi=[0.0] * 7, n_eff=te["n_eff"], n_g=te["n_g"], name="B7_CORE")
BC.Chip(core=core, contacts=contacts, ops=ops, n_eff=te["n_eff"], n_g=te["n_g"], name="B7_CHIP").Layout().write_gdsii(str(out))


def canon(path):
    s, db = G.parse(str(path))
    ref = {r["sname"] for st in s.values() for r in st["srefs"]}
    top = [n for n in s if n not in ref][0]
    pl = []
    G.flatten(s, top, np.eye(2), np.zeros(2), pl)
    return sorted((l, tuple(np.round(p * db / 1e-6, 3).ravel())) for l, p in pl)


a, b = canon(out), canon(root / "layout" / "B7_final.gds")
res = dict(ok=a == b, polygons=len(b), rebuilt=len(a))
print(json.dumps(res, ensure_ascii=False))
sys.exit(0 if res["ok"] else 1)
