"""只用交付包內的檔案重做光學 LVS 與電氣連接檢查（不需要 IPKISS；需要 numpy、shapely、matplotlib）。
用法：python verify_gds.py      結束碼 0 = 與規格一致
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
root = Path(__file__).resolve().parent
sys.path.insert(0, str(root / "source" / "work" / "common"))
import gds_verify as GV  # noqa: E402

spec = json.loads((root / "interfaces" / "pic_spec.json").read_text(encoding="utf-8"))
nl = json.loads((root / "interfaces" / "netlist.json").read_text(encoding="utf-8"))
chip = json.loads((root / "interfaces" / "chip_info.json").read_text(encoding="utf-8"))
gds = root / "layout" / "B7_final.gds"
lvs, _ = GV.optical_lvs(gds, spec, nl)
el = GV.electrical(gds, spec, chip["pads"])
res = dict(ok=lvs["ok"] and el["ok"], lvs={k: v for k, v in lvs.items()}, electrical={k: v for k, v in el.items() if k != "rows"})
print(json.dumps(res, ensure_ascii=False))
sys.exit(0 if res["ok"] else 1)
