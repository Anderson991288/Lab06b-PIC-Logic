"""M0 s2：從 PDK 取出 2×2 MMI 的 GDS 3（Si 核心）多邊形與埠位置，給 Meep 光場模擬用。

用途：Meep 的 MMI 幾何直接來自 PDK 佈局，不手抄尺寸。
輸入：CORNERSTONE PDK（IPKISS 授權）。
輸出：out/mmi_geometry.json（多邊形 µm、埠 (x, y, 角度)、外框、主體寬與長）、out/MMI.gds。
執行：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m0_s2\\export_mmi.py
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import runtime as rt

rt.setup(plot=False)
import numpy as np                      # noqa: E402
from common import pdk                  # noqa: E402
from common import gds2png as G         # noqa: E402


def main():
    od = rt.out_dir(__file__)
    mmi = pdk.mmi2x2()
    lay = mmi.Layout()
    gds = od / "MMI.gds"
    lay.write_gdsii(str(gds))
    structs, db = G.parse(str(gds))
    ref = {s["sname"] for st in structs.values() for s in st["srefs"]}
    top = [n for n in structs if n not in ref][0]
    polys = []
    G.flatten(structs, top, np.eye(2), np.zeros(2), polys)
    core = [(p * (db / 1e-6)).round(4).tolist() for l, p in polys if l == 3]
    ports = {p.name: [round(p.position.x, 4), round(p.position.y, 4), round(p.angle, 1)] for p in lay.ports}
    a = np.vstack([np.asarray(p) for p in core])
    # 主體：x 在兩側埠之間、寬度最大的那個多邊形
    widths = [np.ptp(np.asarray(p)[:, 1]) for p in core]
    body = np.asarray(core[int(np.argmax(widths))])
    res = dict(step="M0 s2", source="CORNERSTONE SOI220nm_1550nm_TE_STRIP_2x2_MMI (PDK layout, GDS 3)",
               layers_found=sorted({l for l, _ in polys}), n_core_polygons=len(core), core_polygons_um=core,
               ports=ports, bbox_um=[float(a[:, 0].min()), float(a[:, 1].min()), float(a[:, 0].max()), float(a[:, 1].max())],
               body_width_um=float(np.ptp(body[:, 1])), body_length_um=float(np.ptp(body[:, 0])),
               port_width_um=pdk.WG_W)
    (od / "mmi_geometry.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("layers", res["layers_found"], "polys", len(core), "ports", ports)
    print("bbox", res["bbox_um"], "body W x L", res["body_width_um"], res["body_length_um"])


if __name__ == "__main__":
    main()
