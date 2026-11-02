"""M1 s4：把原版課程已驗證的 5 組邏輯相位整理成本課程的共用相位檔（唯讀讀取，不修改來源）。

輸入：原版課程 evidence/m1_s4_logic.json（位置由 EDA_paths.json 的 sources_read_only 決定）。
輸出：sources/b7_phases.json（課程根目錄）：每個功能的 θ1–θ7、φ1–φ7（全精度），以及原版每列的 ΔP 供核對。
  M1 s4 起所有步驟（含 M2 的電路模擬與佈局）都讀這一份，不在別處重複抄相位。
執行：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m1_s4\\collect_phases.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CFG = json.loads((ROOT / "EDA_paths.json").read_text(encoding="utf-8"))
SRC = Path(CFG["sources_read_only"]["C01"]["path"]) / "evidence" / "m1_s4_logic.json"

src = json.loads(SRC.read_text(encoding="utf-8"))
out = dict(note="原版課程 M1 已驗證的 B7 邏輯相位（理想模型、R 振幅 3、讀 o2−o4）；θ、φ 單位為弧度，順序為 M1–M7",
           model=src["model"], ops=src["ops"],
           gates={g: dict(theta=v["theta"], phi=v["phi"],
                          ref_rows=[dict(bits=r["bits"], target=r["target"], delta=r["delta"]) for r in v["rows"]])
                  for g, v in src["gates"].items()})
dest = ROOT / "sources" / "b7_phases.json"
dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("wrote", dest.relative_to(ROOT).as_posix(), list(out["gates"]))
