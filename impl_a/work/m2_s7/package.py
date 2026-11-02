"""M2 s7：完成交付。把 M2 s6 凍結的晶片 GDS、檢查報告、介面表、模擬結果與原始碼打成交付包，再解壓重驗。

用法：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m2_s7\\package.py   （約 1 分鐘）
輸入：M2 s6 的 out/b7_chip_checked.gds 與 signoff.json，以及 M2 s1–s6 的報告、spec/、sources/、work/common/ 原始碼。
輸出：out/PIC_delivery/（交付資料夾）、out/B7_PIC_delivery.zip、out/delivery_check.json。
重驗：解壓到暫存資料夾，只用包內檔案執行 check_delivery.py（SHA-256）、verify_gds.py（只讀 GDS 的 LVS 與電氣）、
      rebuild_gds.py（用包內原始碼重建 GDS，逐多邊形比對）；另以本機規則檔對包內 GDS 跑 DRC；最後竄改一個位元組確認會被抓到。
"""
import csv
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "work"))
sys.stdout.reconfigure(encoding="utf-8")
from common import drc  # noqa: E402

OUT = HERE / "out"
PKG = OUT / "PIC_delivery"
ZIP = OUT / "B7_PIC_delivery.zip"
VER = OUT / "_verify"
W = ROOT / "work"
t0 = time.time()
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()  # noqa: E731

S6 = json.loads((W / "m2_s6" / "out" / "signoff.json").read_text(encoding="utf-8"))
assert S6["all_ok"], "M2 s6 簽核未通過，不能交付"
GDS = W / "m2_s6" / "out" / "b7_chip_checked.gds"
assert sha(GDS) == S6["sha256"], "凍結版 GDS 與簽核表的 SHA-256 不符"
spec = json.loads((ROOT / "spec" / "pic_spec.json").read_text(encoding="utf-8"))
assert sha(ROOT / spec["phase_settings"]["file"]) == spec["phase_settings"]["sha256"], "相位檔與規格不符"
CHIP = json.loads((W / "m2_s5" / "out" / "chip_info.json").read_text(encoding="utf-8"))
INFO3 = json.loads((W / "m2_s3" / "out" / "layout_info.json").read_text(encoding="utf-8"))

if PKG.exists():
    shutil.rmtree(PKG)
for d in ("layout", "reports", "interfaces", "simulation", "figures", "source"):
    (PKG / d).mkdir(parents=True)


def put(src, dst):
    dst = PKG / dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


# ---------------- 版圖、報告、介面、模擬、圖 ----------------
put(GDS, "layout/B7_final.gds")
put(W / "m2_s3" / "out" / "b7_core.gds", "layout/B7_core_reviewed.gds")
for f in ("drc_result.json", "connectivity.json", "signoff.json"):
    put(W / "m2_s6" / "out" / f, f"reports/{f}")
put(W / "m2_s5" / "out" / "b7_chip_drc.lyrdb", "reports/B7_final_drc.lyrdb")
put(W / "m2_s4" / "out" / "review_checks.json", "reports/core_review.json")
put(W / "m2_s5" / "out" / "m2_s5_result.json", "reports/chip_simulation.json")
for f in ("pic_spec.json", "netlist.json", "io_table.json", "external_requirements.json", "truth_table.json"):
    put(ROOT / "spec" / f, f"interfaces/{f}")
put(W / "m2_s5" / "out" / "chip_info.json", "interfaces/chip_info.json")
put(W / "m2_s3" / "out" / "layout_info.json", "interfaces/core_layout_info.json")
put(ROOT / spec["phase_settings"]["file"], "simulation/phase_settings.json")
put(W / "m2_s2" / "out" / "matrices.json", "simulation/pdk_matrices.json")
put(W / "m2_s2" / "out" / "truth_tables.csv", "simulation/pdk_truth_tables.csv")
for src, dst in (("m2_s5/chip_overview.png", "B7_final.png"), ("m2_s5/electrical.png", "B7_pads_nets.png"),
                 ("m2_s3/b7_core.png", "B7_core.png"), ("m2_s6/lvs_extract.png", "B7_lvs_extract.png")):
    put(ROOT / "course" / "figures" / src, f"figures/{dst}")

# 光學埠表
sig = {r: s for r, s in enumerate(["x1", "x2", "x3", "x4", "R"])}
buf = io.StringIO()
w = csv.writer(buf)
w.writerow(["port", "signal", "side", "facet_x_um", "facet_y_um", "core_port", "role"])
for d in CHIP["ec"]["inputs"]:
    w.writerow([d["port"], d["signal"], "left", d["facet"][0], d["facet"][1], d["core"], "input"])
for d in CHIP["ec"]["outputs"]:
    role = "readout" if d["core"] in ("out1", "out3") else "monitor"
    w.writerow([d["port"], d["signal"], "right", d["facet"][0], d["facet"][1], d["core"], role])
(PKG / "interfaces" / "optical_ports.csv").write_text(buf.getvalue(), encoding="utf-8-sig")

# 接墊表：接墊 → heater（通道、MZI、φ／θ、rail、heater 中心）
ctrl = {c["channel"]: c for c in spec["phase_controls"]}
contacts = {k: v for m in INFO3["mzi"] for k, v in m["heater_contacts_um"].items()}
buf = io.StringIO()
w = csv.writer(buf)
w.writerow(["pad", "center_x_um", "center_y_um", "side", "role", "mzi", "phase", "rail", "heater_center_x_um",
            "heater_center_y_um", "tin_squares"])
sq = json.loads((W / "m2_s6" / "out" / "connectivity.json").read_text(encoding="utf-8"))["electrical"]["heater_squares"][0]
for p in CHIP["pads"]:
    if p["name"] in ctrl:
        c = ctrl[p["name"]]
        (x0, y0), (x1, y1) = contacts[p["name"]]
        w.writerow([p["name"], p["xy"][0], p["xy"][1], p["side"], "heater_signal", f"M{c['mzi']}", c["phase"], c["rail"],
                    round((x0 + x1) / 2, 3), round((y0 + y1) / 2, 3), sq])
    else:
        w.writerow([p["name"], p["xy"][0], p["xy"][1], p["side"], "return", "", "", "", "", "", ""])
(PKG / "interfaces" / "pad_map.csv").write_text(buf.getvalue(), encoding="utf-8-sig")

# ---------------- 原始碼（保留課程資料夾結構；絕對路徑改成相對說明） ----------------
SRC = {
    "work/common": ["b7.py", "mzi.py", "pdk.py", "b7_circuit.py", "b7_layout.py", "b7_chip.py", "gds_verify.py",
                    "gds2png.py", "drc.py", "runtime.py", "b7plot.py"],
    "work/m2_s2": ["simulate.py"], "work/m2_s3": ["build_layout.py"], "work/m2_s4": ["review_layout.py"],
    "work/m2_s5": ["build_chip.py"], "work/m2_s6": ["verify_chip.py"],
}
PATH_RE = [(re.compile(r"C:\\\\luceda\\\\[^\s]*?python\.exe"), "python"),
           (re.compile(r"C:\\\\LAB\\\\Lab06b\\\\impl_a\\\\"), ""), (re.compile(r"C:\\LAB\\Lab06b\\impl_a\\?"), "")]
for d, files in SRC.items():
    for f in files:
        txt = (ROOT / d / f).read_text(encoding="utf-8")
        for pat, rep in PATH_RE:
            txt = pat.sub(rep, txt)
        dst = PKG / "source" / d / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(txt, encoding="utf-8")
for src, dst in ((ROOT / "spec", "source/spec"), ):
    for f in ("pic_spec.json", "netlist.json", "truth_table.json", "io_table.json", "external_requirements.json"):
        put(src / f, f"{dst}/{f}")
put(ROOT / spec["phase_settings"]["file"], f"source/{spec['phase_settings']['file']}")
put(W / "m0_s2" / "out" / "m0_s2_result.json", "source/work/m0_s2/out/m0_s2_result.json")
put(W / "m2_s3" / "out" / "layout_info.json", "source/work/m2_s3/out/layout_info.json")

# ---------------- 交付包內的三支檢查程式 ----------------
(PKG / "check_delivery.py").write_text('''"""檢查交付包是否完整：逐檔比對 manifest.json 的 SHA-256 與大小，並列出清單以外的檔案。只用 Python 標準函式庫。
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
extra = [str(p.relative_to(root)).replace("\\\\", "/") for p in root.rglob("*") if p.is_file()]
extra = [p for p in extra if p not in seen and p != "manifest.json" and "__pycache__" not in p]
res = dict(ok=not bad and not extra, checked=len(man["files"]), problems=bad, extra=extra)
print(json.dumps(res, ensure_ascii=False))
sys.exit(0 if res["ok"] else 1)
''', encoding="utf-8")
(PKG / "verify_gds.py").write_text('''"""只用交付包內的檔案重做光學 LVS 與電氣連接檢查（不需要 IPKISS；需要 numpy、shapely、matplotlib）。
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
''', encoding="utf-8")
(PKG / "rebuild_gds.py").write_text('''"""用交付包內的原始碼重建晶片 GDS，與 layout/B7_final.gds 逐多邊形比對（需要 IPKISS 與 CORNERSTONE PDK 授權）。
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
''', encoding="utf-8")

# ---------------- README ----------------
L = S6["items"]
readme = f"""# B7 光邏輯 PIC：設計交付包

一顆 4 位元可程式光邏輯晶片：7 顆 MZI 組成 5 入 5 出的 B7，換 14 個 heater 相位就換邏輯功能（AND2、OR2、XOR2、AND4、OR4），
讀取 o2 與 o4 的功率差判定 0／1。製程：CORNERSTONE 220 nm SOI 被動平台（含 TiN heater）。

## 先看這三個
| 檔案 | 內容 |
|---|---|
| `layout/B7_final.gds` | 晶片版圖，{S6['die_um'][0]:g} × {S6['die_um'][1]:g} µm；頂層 cell `B7_CHIP`。SHA-256 `{S6['sha256']}` |
| `interfaces/optical_ports.csv` | 10 個邊緣耦合器端面座標；輸入 x1–x4、R，輸出 o1–o5（o2、o4 讀取） |
| `interfaces/pad_map.csv` | 16 個 80 × 80 µm 接墊：14 路 heater 訊號（通道名 M1_phi … M7_theta）與 GND_T、GND_B |

## 檢查結果（都針對上面的 SHA-256）
""" + "\n".join(f"- {i['item']}：{i['result']}（{'通過' if i['ok'] else '未通過'}）" for i in L) + f"""

範圍：{S6['scope']}。

## 自己驗證
1. `python check_delivery.py`：逐檔比對 SHA-256（只需 Python）。
2. `python verify_gds.py`：只讀 GDS 重做光學 LVS 與電氣連接（需 numpy、shapely、matplotlib）。
3. `python rebuild_gds.py`：用 `source/` 的程式重建 GDS，逐多邊形比對（需 IPKISS 2026.3.3 與 CORNERSTONE 2.6.luceda1 授權）。
4. DRC：規則檔是 CORNERSTONE 的平台檔案，不隨本包散布；取得後用 KLayout（本包以 0.30.12 檢查）載入
   `layout/B7_final.gds`，設計區 {S6['die_um'][0]:g} × {S6['die_um'][1]:g} µm，可對照 `reports/B7_final_drc.lyrdb`。

## 資料夾
| 資料夾 | 內容 |
|---|---|
| `layout/` | 晶片版圖；`B7_core_reviewed.gds` 是已審查的核心（晶片內的核心與它逐多邊形相同） |
| `reports/` | DRC 摘要與原始報告、連接檢查、簽核表、核心審查、晶片電路模擬 |
| `interfaces/` | 功能規格、連接表、I/O 表、外部設備需求、真值表、光學埠表、接墊表、佈局資訊 |
| `simulation/` | 相位設定（θ、φ，單位 rad）、PDK 電路的 U 矩陣與 80 筆結果 |
| `figures/` | 晶片全圖、接墊與金屬網、核心、LVS 抽出圖 |
| `source/` | 產生與檢查本版圖的程式（保留原資料夾結構） |

## 交接時要知道的事
- 相位設定是理想模型的數值；實體晶片要先量 heater 的「電壓 → 相位」再換算。加熱絲為 {sq:g} 個方塊，電阻 = {sq:g} × TiN 片電阻。
- 兩個 GND 接墊量測時接同一個地。
- 輸入的資料光與參考光必須同一雷射、相位穩定；外部設備的精度要求見 `interfaces/external_requirements.json`。
- 晶片內 5 條輸入光路等長；雷射波長在 1530–1570 nm 內不需重新校正 heater（模擬）。
- 邊緣耦合器是以 PDK 圖層自建的薄矽尖端，耦合效率未模擬；0.25 µm 尖端需向 CORNERSTONE 確認可製作。
- 金屬跨過直波導 24 處、熱串擾、EC 與傳播損耗均未建模，需量測。
- DRC 為 pre-DRC，完整 DRC 由 CORNERSTONE 執行。

## 工具版本
Python 3.14.3、IPKISS 2026.3.3、CORNERSTONE 2.6.luceda1、numpy 2.3.5、shapely 2.1.2、matplotlib 3.10.8、KLayout 0.30.12。
"""
(PKG / "README.md").write_text(readme, encoding="utf-8-sig")      # 加 BOM：瀏覽器直接開也能正確顯示中文

# ---------------- manifest 與 zip ----------------
files = sorted(p for p in PKG.rglob("*") if p.is_file() and p.name != "manifest.json")
man = dict(package="B7_PIC_delivery", date="2026-10-31", final_gds="layout/B7_final.gds", final_sha256=S6["sha256"],
           files=[dict(path=str(p.relative_to(PKG)).replace("\\", "/"), size=p.stat().st_size, sha256=sha(p)) for p in files])
(PKG / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
if ZIP.exists():
    ZIP.unlink()
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(PKG.rglob("*")):
        if p.is_file():
            z.write(p, "PIC_delivery/" + str(p.relative_to(PKG)).replace("\\", "/"))
print("package", len(man["files"]) + 1, "files;", ZIP.stat().st_size // 1024, "KB")

# 讀者會看到的文字不可有本機路徑或其他計畫名稱
LEAK = re.compile(r"[A-Za-z]:\\|EDA_Claude|Lab0\d|lab01a|Codex|C01|luceda_20")
leaks = [str(p.relative_to(PKG)) for p in PKG.rglob("*") if p.suffix in (".md", ".csv", ".json", ".py")
         and LEAK.search(p.read_text(encoding="utf-8-sig", errors="ignore"))]
print("leaks", leaks)

# ---------------- 解壓重驗 ----------------
if VER.exists():
    shutil.rmtree(VER)
with zipfile.ZipFile(ZIP) as z:
    bad_crc = z.testzip()
    z.extractall(VER)
root = VER / "PIC_delivery"
py = sys.executable
env = dict(os.environ, PYTHONIOENCODING="utf-8")


def run(script, *args):
    r = subprocess.run([py, "-I", script, *args], cwd=root, capture_output=True, text=True, encoding="utf-8", env=env)
    last = [l for l in r.stdout.splitlines() if l.startswith("{")]
    return dict(code=r.returncode, result=json.loads(last[-1]) if last else None, stderr=r.stderr[-300:] if r.returncode else "")


chk = run("check_delivery.py")
ver = run("verify_gds.py")
reb = run("rebuild_gds.py", str(VER / "rebuilt.gds"))
(VER / "rebuilt.gds").unlink(missing_ok=True)
d = drc.run(root / "layout" / "B7_final.gds", design_area=tuple(S6["die_um"]))
drc_ok = d["total"] == 0 and not d["outside"]
for p in root.rglob("*_drc.lyrdb"):
    if p.parent.name == "layout":
        p.unlink()
for p in root.rglob("__pycache__"):
    shutil.rmtree(p)
# 竄改測試：改 GDS 一個位元組，check_delivery 必須失敗；改回後必須通過
g = root / "layout" / "B7_final.gds"
raw = bytearray(g.read_bytes())
i = len(raw) // 2
raw[i] ^= 0x01
g.write_bytes(bytes(raw))
tam = run("check_delivery.py")
raw[i] ^= 0x01
g.write_bytes(bytes(raw))
back = run("check_delivery.py")
shutil.rmtree(VER)

res = dict(step="M2 s7", date="2026-10-31", zip=ZIP.name, zip_kb=ZIP.stat().st_size // 1024, zip_crc_ok=bad_crc is None,
           n_files=len(man["files"]) + 1, final_sha256=S6["sha256"], leaks=leaks,
           check_delivery=chk, verify_gds=ver, rebuild_gds=reb,
           drc=dict(total=d["total"], outside=d["outside"], n_rules=len(d["rules"])),
           tamper=dict(detected=tam["code"] != 0, problems=(tam["result"] or {}).get("problems"), restored_ok=back["code"] == 0),
           folders={k: sum(1 for f in man["files"] if f["path"].startswith(k + "/")) for k in
                    ("layout", "reports", "interfaces", "simulation", "figures", "source")},
           runtime_s=round(time.time() - t0, 1))
res["all_ok"] = (res["zip_crc_ok"] and not leaks and chk["code"] == 0 and ver["code"] == 0 and reb["code"] == 0 and drc_ok
                 and res["tamper"]["detected"] and res["tamper"]["restored_ok"])
(OUT / "delivery_check.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in res.items() if k not in ("verify_gds",)}, ensure_ascii=False)[:1500])
print("done", res["runtime_s"], "s")
