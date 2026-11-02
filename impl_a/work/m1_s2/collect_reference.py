"""M1 s2：把原版課程的 B7 計算結果（θ 全 π/2、φ 全 0）整理成本課程的參考檔（唯讀讀取，不修改來源）。

輸入：原版課程 evidence/m1_s3_results.json、m1_s3_paths.json（位置由 EDA_paths.json 的 sources_read_only 決定）。
輸出：sources/reference_b7.json（課程根目錄）。學員直接使用這份檔案，不需要原版課程。
執行：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m1_s2\\collect_reference.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CFG = json.loads((ROOT / "EDA_paths.json").read_text(encoding="utf-8"))
SRC = Path(CFG["sources_read_only"]["C01"]["path"]) / "evidence"

res = json.loads((SRC / "m1_s3_results.json").read_text(encoding="utf-8"))
pth = json.loads((SRC / "m1_s3_paths.json").read_text(encoding="utf-8"))
ref = dict(
    note="原版課程 M1 的 B7 理想計算：θ 全 π/2、φ 全 0、R 振幅 3、無損耗；複數以 [實部, 虛部] 表示",
    ops=res["ops"], U=res["U"],
    cases=[dict(bits=c["bits"], powers=c["powers"], delta=c["delta"], bit=c["bit"]) for c in res["cases"]],
    paths={"x4_to_o2": pth["u24"], "x4_to_o4": pth["u44"]},
)
out = ROOT / "sources" / "reference_b7.json"
out.write_text(json.dumps(ref, ensure_ascii=False, indent=1), encoding="utf-8")
print("wrote", out.relative_to(ROOT).as_posix(), "cases", [c["bits"] for c in ref["cases"]])
