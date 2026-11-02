"""M0 s2：把參考研究的光場模擬數值抄成課程內的參考檔（來源唯讀，只讀不改）。

用途：課程頁面把重跑結果與參考數值並列；參考數值集中在一個檔，頁面不連到外部報告。
輸入：參考研究的 Meep 結果檔 tbu_field_*.npz（p_out 欄位）；MMI 的穿透與分光比取自該研究報告的圖說。
輸出：C:\\LAB\\Lab06b\\impl_a\\sources\\reference_fields.json。
執行：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m0_s2\\collect_reference.py
"""
import json
import hashlib
from pathlib import Path
import numpy as np

SRC = Path(r"D:\LAB\lab01a\out")                     # 唯讀
DST = Path(__file__).resolve().parents[2] / "sources" / "reference_fields.json"
CASES = {"t0": "tbu_field_in1_t0.npz", "tpi": "tbu_field_1.npz", "tpi2": "tbu_field_in1_tpi2.npz",
         "comb": "tbu_field_in12_tpi2.npz"}

ref = {"method": "Meep 2D effective index, CW 1550 nm, 16 px/um, arm 20 um, theta via core dn / 1.07 empirical",
       "cases": {}}
for k, f in CASES.items():
    p = SRC / f
    d = np.load(p)
    ref["cases"][k] = dict(p_out=[round(float(x), 4) for x in d["p_out"]], theta=float(d["theta"]),
                           sha256=hashlib.sha256(p.read_bytes()).hexdigest()[:16])
ref["mmi2x2"] = dict(W_um=6.0, L_um=42.5, T=0.966, bar=0.500, cross=0.500, source="report figure caption")
ref["mmi1x2"] = dict(W_um=6.0, L_um=31.0, T=0.988, split=[0.500, 0.500], source="report figure caption")
DST.parent.mkdir(exist_ok=True)
DST.write_text(json.dumps(ref, indent=1), encoding="utf-8")
print(json.dumps(ref["cases"]))
