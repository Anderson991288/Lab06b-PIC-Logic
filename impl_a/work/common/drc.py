"""KLayout 批次 DRC（CORNERSTONE Si220 被動 deck）（M0 s2）。

用途：對 GDS 跑 DRC，回傳各規則違規數；另外檢查「所有圖形都在 GDS 99 外框內」（平台 deck 不檢查這項）。
  設計區 dw×dh 應由呼叫端以「配給的區塊尺寸」傳入；若不傳，才量 GDS 99 外框代入，
  此時設計區檢查等於自己驗證自己，結果中 design_area_source 會標為 "measured"。
輸入：GDS 檔；KLayout 執行檔（環境變數 KLAYOUT_EXE，未設時用使用者應用程式資料夾下的 KLayout/klayout_app.exe）；
      deck design/common/drc/cornerstone_Si220_passive.lydrc（平台專有，不隨原始碼散布）。
輸出：與 GDS 同名的 *_drc.lyrdb；回傳 dict(total, counts, rules, report, design_area_um, design_area_source, outside)。
用法：python design/common/drc.py <gds> [dw dh]
"""
import os
import sys
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gds2png as G   # noqa: E402

KLAYOUT = Path(os.environ.get("KLAYOUT_EXE") or Path(os.environ.get("APPDATA", "")) / "KLayout" / "klayout_app.exe")
DECK = HERE / "drc" / "cornerstone_Si220_passive.lydrc"


def _polys(gds):
    structs, db = G.parse(str(gds))
    ref = {s["sname"] for st in structs.values() for s in st["srefs"]}
    top = [n for n in structs if n not in ref][0]
    polys = []
    G.flatten(structs, top, np.eye(2), np.zeros(2), polys)
    return [(l, p * (db / 1e-6)) for l, p in polys]


def layer_bbox(gds, layer):
    """頂層 cell 攤平後，某一層所有多邊形的外框 (xmin, ymin, xmax, ymax)，µm；沒有該層回傳 None。"""
    pts = [p for l, p in _polys(gds) if l == layer]
    if not pts:
        return None
    a = np.vstack(pts)
    return float(a[:, 0].min()), float(a[:, 1].min()), float(a[:, 0].max()), float(a[:, 1].max())


def outside_outline(gds, tol=1e-6):
    """GDS 99 以外各層的多邊形中，有頂點落在 GDS 99 外框之外的個數。"""
    polys = _polys(gds)
    out = [p for l, p in polys if l == 99]
    if not out:
        return None
    a = np.vstack(out)
    x0, y0, x1, y1 = a[:, 0].min(), a[:, 1].min(), a[:, 0].max(), a[:, 1].max()
    return int(sum(1 for l, p in polys if l != 99 and
                   (p[:, 0].min() < x0 - tol or p[:, 0].max() > x1 + tol or p[:, 1].min() < y0 - tol or p[:, 1].max() > y1 + tol)))


def run(gds, design_area=None, deck=DECK, quiet=True):
    """design_area：(dw, dh) µm，配給的區塊尺寸。"""
    gds = Path(gds).resolve()                       # KLayout 只吃絕對路徑
    report = gds.with_name(gds.stem + "_drc.lyrdb")
    cmd = [str(KLAYOUT), "-b", "-r", str(deck), "-rd", f"input={gds}", "-rd", f"report={report}"]
    source = "declared"
    if design_area is None:
        bb = layer_bbox(gds, 99)
        design_area = (round(bb[2] - bb[0], 3), round(bb[3] - bb[1], 3)) if bb else None
        source = "measured"
    if design_area:
        cmd += ["-rd", f"dw={design_area[0]:g}", "-rd", f"dh={design_area[1]:g}"]
    subprocess.run(cmd, check=True, capture_output=quiet)
    counts, rules = Counter(), []
    for _, el in ET.iterparse(report, events=("end",)):
        tag = el.tag.split("}")[-1]
        if tag == "category" and el.findtext("name"):
            rules.append(el.findtext("name").strip("'"))
        elif tag == "item":
            c = el.findtext("category")
            if c is not None:
                counts[c.strip("'")] += 1
            el.clear()
    return dict(total=sum(counts.values()), counts=dict(counts), rules=rules, report=report,
                design_area_um=design_area, design_area_source=source, outside=outside_outline(gds))


if __name__ == "__main__":
    area = (float(sys.argv[2]), float(sys.argv[3])) if len(sys.argv) > 3 else None
    r = run(sys.argv[1], area)
    print(f"規則 {len(r['rules'])} 條，違規 {r['total']}；設計區 {r['design_area_um']}（{r['design_area_source']}）；"
          f"外框外圖形 {r['outside']}")
    for k, v in sorted(r["counts"].items(), key=lambda kv: -kv[1]):
        print(f"  {v:5d}  {k}")
    ok = r["total"] == 0 and not r["outside"]
    print("DRC-CLEAN" if ok else f"有違規，見 {r['report']}")
    sys.exit(0 if ok else 1)
