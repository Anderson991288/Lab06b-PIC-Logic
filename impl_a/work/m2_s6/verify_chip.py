"""M2 s6：凍結版 GDS 的正式檢查。DRC（含逐條規則的故障注入）、只讀 GDS 的光學 LVS 與電氣連接檢查、簽核表。

用法：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m2_s6\\verify_chip.py   （約 1 分鐘）
輸入：M2 s5 的 out/b7_chip.gds（被檢查的版本）、out/chip_info.json、故障版 GDS；spec/pic_spec.json、spec/netlist.json。
輸出：out/b7_chip_checked.gds（通過後才複製）、out/drc_rules_fault.gds、out/lvs_fault_*.gds、*_drc.lyrdb、
      out/drc_result.json、out/connectivity.json、out/signoff.json；course/figures/m2_s6/drc_faults.png、lvs_extract.png。
光學 LVS 只用幾何：GDS 3／5 的多邊形中，高 6 µm 的是 MMI 本體，其餘連成「導線」；每條導線兩端各接一個 MMI 埠或晶片端面。
由導線重建 MMI → MZI → B7 的連接表，再與規格比對；heater 由 GDS 39 壓在哪一條導線決定是哪個通道。
"""
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "work"))
sys.path.insert(0, str(ROOT / "work" / "common"))
sys.stdout.reconfigure(encoding="utf-8")
from common import drc  # noqa: E402
from common import gds2png as G  # noqa: E402

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Polygon as MPoly, Rectangle  # noqa: E402

plt.rcParams["font.family"] = ["Microsoft JhengHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT = HERE / "out"
FIG = ROOT / "course" / "figures" / "m2_s6"
OUT.mkdir(exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
S5 = ROOT / "work" / "m2_s5" / "out"
GDS = S5 / "b7_chip.gds"
t0 = time.time()

spec = json.loads((ROOT / "spec" / "pic_spec.json").read_text(encoding="utf-8"))
NL = json.loads((ROOT / "spec" / "netlist.json").read_text(encoding="utf-8"))
CHIP = json.loads((S5 / "chip_info.json").read_text(encoding="utf-8"))
OPS = [tuple(o) for o in spec["core"]["ops"]]
CTRL = {(c["mzi"], c["phase"]): c["channel"] for c in spec["phase_controls"]}
L_COL, PITCH = 489.0, 30.0
DIE = tuple(CHIP["die_um"])
TOL = 2e-3
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()  # noqa: E731
assert sha(GDS) == CHIP["gds_sha256"], "M2 s5 的 GDS 與 chip_info.json 記錄的版本不同"


import gds_verify as GV  # noqa: E402  只讀 GDS 的 LVS 與電氣檢查（M2 s7 交付包共用同一份程式）

polys, parts = GV.polys, GV.parts


def optical_lvs(gds):
    return GV.optical_lvs(gds, spec, NL)


def electrical(gds, pads):
    return GV.electrical(gds, spec, pads)


# ① 光學 LVS、電氣：正常版
lvs0, ex0 = optical_lvs(GDS)
el0 = electrical(GDS, CHIP["pads"])
print("LVS", {k: v for k, v in lvs0.items() if k != "problems"}, lvs0["problems"][:3])
print("ELEC", el0["ok"], el0["n_nets"], el0["n_pads"], el0["heater_squares"], el0["problems"][:3])

# ② DRC：正式規則檔、宣告晶片尺寸
r = drc.run(GDS, design_area=DIE)
drc0 = dict(total=r["total"], counts=r["counts"], rules=r["rules"], outside=r["outside"], n_rules=len(r["rules"]))
print("DRC", r["total"], len(r["rules"]))

# ③ DRC 規則的故障注入：晶片空白處（右下）每條規則各放一個違規
import ipkiss3.all as i3  # noqa: E402
import pdk  # noqa: E402
T = pdk.pdk.TECH
LAY = {3: pdk.L_WG, 4: T.PPLAYER.WG_HOL, 5: T.PPLAYER.SLAB, 39: pdk.L_HT, 41: pdk.L_PAD, 100: pdk.L_LABEL}
RULE = {3: (0.35, 0.20), 4: (0.20, 0.35), 5: (0.25, 0.25), 39: (0.6, 10.0), 41: (2.0, 10.0), 100: (0.25, 0.25)}
PAT = {(l, k): ("feature size" if k == "w" else "gap", f"(GDS{l}<") for l in RULE for k in ("w", "s")}   # 規則名稱 = 種類＋圖層
shapes, where = [], {}
x, y = 1240.0, -620.0
for layer, (wmin, smin) in RULE.items():
    L = LAY[layer]
    shapes.append(i3.Rectangle(layer=L, center=(x + 10, y), box_size=(20.0, round(wmin - 0.05, 3))))      # 太窄
    where[(layer, "w")] = (x + 10, y)
    x += 30 if layer not in (39, 41) else 40
    g = round(smin * 0.6, 3)
    shapes += [i3.Rectangle(layer=L, center=(x + 5, y), box_size=(10.0, 3.0)),
               i3.Rectangle(layer=L, center=(x + 15 + g, y), box_size=(10.0, 3.0))]                       # 太近
    where[(layer, "s")] = (x + 10 + g / 2, y)
    x += 30 + g + (20 if layer in (39, 41) else 0)
    if x > 1960:
        x, y = 1240.0, -575.0
structs, db = G.parse(str(GDS))
ref = {s["sname"] for st in structs.values() for s in st["srefs"]}
top_name = [n for n in structs if n not in ref][0]


class Frozen(i3.PCell):
    """把凍結版 GDS 原樣讀進來，再疊上違規圖形。"""
    class Layout(i3.LayoutView):
        def _generate_instances(self, insts):
            insts += i3.SRef(i3.GDSCell(filename=str(GDS), name=top_name), name="chip")
            return insts

        def _generate_elements(self, elems):
            for s in shapes:
                elems += s
            return elems


fault_gds = OUT / "drc_rules_fault.gds"
Frozen(name="DRC_RULE_FAULTS").Layout().write_gdsii(str(fault_gds))
rf = drc.run(fault_gds, design_area=DIE)
match = lambda c, p: p[0] in c and p[1] in c.replace("&lt;", "<")  # noqa: E731
hit = {f"GDS{l} {'線寬' if k == 'w' else '間距'}": sum(n for c, n in rf["counts"].items() if match(c, PAT[(l, k)]))
       for (l, k) in PAT}
unexpected = sorted(c for c in rf["counts"] if not any(match(c, p) for p in PAT.values()))
r_area = drc.run(GDS, design_area=(DIE[0] - 100.0, DIE[1]))
area_hit = sum(n for c, n in r_area["counts"].items() if "design area" in c)
drc_fault = dict(hit=hit, unexpected=unexpected, total=rf["total"], area_wrong_hit=area_hit,
                 all_caught=all(v >= 1 for v in hit.values()) and area_hit >= 1 and not unexpected)
print("DRC faults", drc_fault)

# ④ LVS／電氣的故障注入：晶片版的核心故障（重新產生）與 M2 s5 的電氣故障版
import b7_chip as BC  # noqa: E402
import b7_layout as BL  # noqa: E402
INFO3 = json.loads((ROOT / "work" / "m2_s3" / "out" / "layout_info.json").read_text(encoding="utf-8"))
CONTACTS = {k: v for m in INFO3["mzi"] for k, v in m["heater_contacts_um"].items()}
m0 = json.loads((ROOT / "work" / "m0_s2" / "out" / "m0_s2_result.json").read_text(encoding="utf-8"))["modes"]["te0"]
LFAULT = {"flip": "M6 上下翻轉（heater 在下臂）", "wrong_rail": "M3 放到 rail 2–3", "offset": "M5 錯位 0.1 µm"}
EFAULT = {"open": "M4_theta 訊號線開路", "short": "M3_phi 訊號線碰到回流匯流排", "pad_swap": "接墊對照表 M1 兩個名稱寫反"}
faults = {}
for f, desc in LFAULT.items():
    core = BL.B7Core(ops=[list(o) for o in OPS], theta=[0.0] * 7, phi=[0.0] * 7, n_eff=m0["n_eff"], n_g=m0["n_g"],
                     fault=f, name=f"B7_CORE_{f.upper()}")
    g = OUT / f"lvs_fault_{f}.gds"
    BC.Chip(core=core, contacts=CONTACTS, ops=[list(o) for o in OPS], n_eff=m0["n_eff"], n_g=m0["n_g"],
            name=f"B7_CHIP_{f.upper()}").Layout().write_gdsii(str(g))
    lv, _ = optical_lvs(g)
    el = electrical(g, CHIP["pads"])
    faults[f] = dict(desc=desc, lvs_ok=lv["ok"], lvs_problems=lv["problems"][:3],
                     elec_ok=el["ok"], elec_problems=el["problems"][:2])
for f, desc in EFAULT.items():
    g = S5 / f"b7_chip_{f}.gds"
    pads = BC.plan([list(o) for o in OPS], CONTACTS, f)["pads"]
    pad_tab = [dict(name=n, xy=[x, y]) for n, x, y, _ in pads]
    lv, _ = optical_lvs(g)
    el = electrical(g, pad_tab)
    faults[f] = dict(desc=desc, lvs_ok=lv["ok"], lvs_problems=lv["problems"][:2], elec_ok=el["ok"], elec_problems=el["problems"][:2])
for f, v in faults.items():
    print("fault", f, "LVS", v["lvs_ok"], v["lvs_problems"][:1], "ELEC", v["elec_ok"], v["elec_problems"][:1])

# ⑤ 凍結：全部通過才複製；簽核表把各步的結果綁在同一個 SHA-256
passed = (drc0["total"] == 0 and not drc0["outside"] and lvs0["ok"] and el0["ok"] and drc_fault["all_caught"]
          and all(v["lvs_ok"] is False or v["elec_ok"] is False for v in faults.values()))
checked = OUT / "b7_chip_checked.gds"
if passed:
    shutil.copyfile(GDS, checked)
R5 = json.loads((S5 / "m2_s5_result.json").read_text(encoding="utf-8"))
R4 = json.loads((ROOT / "work" / "m2_s4" / "out" / "review_checks.json").read_text(encoding="utf-8"))
R3 = json.loads((ROOT / "work" / "m2_s3" / "out" / "m2_s3_result.json").read_text(encoding="utf-8"))
signoff = dict(
    gds=checked.name, sha256=sha(checked) if passed else None, die_um=DIE,
    items=[
        dict(item="DRC（CORNERSTONE pre-DRC 規則檔）", step="M2 s6", result=f"{drc0['total']} 違規、外框外 {drc0['outside']}", ok=drc0["total"] == 0),
        dict(item="DRC 規則本身會觸發", step="M2 s6", result=f"{sum(v >= 1 for v in hit.values())}/{len(hit)} 條＋設計區", ok=drc_fault["all_caught"]),
        dict(item="光學 LVS（只讀 GDS）", step="M2 s6", result=f"{lvs0['n_mzi']} MZI、{lvs0['n_links']} 連線、{lvs0['n_ext']} 外部埠、{lvs0['n_heaters']} heater 與規格一致", ok=lvs0["ok"]),
        dict(item="電氣連接（只讀 GDS）", step="M2 s6", result=f"14 通道各接 1 訊號接墊＋回流；{el0['n_nets']} 個金屬網", ok=el0["ok"]),
        dict(item="核心與已審查版本相同", step="M2 s5", result="逐多邊形相同", ok=R5["core_identical"]),
        dict(item="核心審查 8 項", step="M2 s4", result="全部通過", ok=R4["results"]["b7_core"]["all_ok"]),
        dict(item="晶片電路 80 筆（1530–1570 nm）", step="M2 s5", result="80/80，不需重新校正",
             ok=all(v["all_ok"] for v in R5["gates"].values())),
        dict(item="核心佈局抽連接表", step="M2 s3", result="與規格一致", ok=R3["lvs"]["links_match"] and R3["lvs"]["external_match"]),
    ],
    scope="pre-DRC：規則檔註明完整 DRC 由 CORNERSTONE 執行；LVS 只比對拓樸與 heater 位置，不含 EC 模態與損耗")
signoff["all_ok"] = passed and all(i["ok"] for i in signoff["items"])
(OUT / "signoff.json").write_text(json.dumps(signoff, ensure_ascii=False, indent=1), encoding="utf-8")
(OUT / "drc_result.json").write_text(json.dumps(dict(gds=GDS.name, sha256=sha(GDS), design_area_um=DIE, clean=drc0,
                                                     rule_faults=drc_fault, fault_gds=fault_gds.name), ensure_ascii=False,
                                                indent=1, default=float), encoding="utf-8")
(OUT / "connectivity.json").write_text(json.dumps(dict(gds=GDS.name, sha256=sha(GDS), optical=lvs0, electrical=el0,
                                                       faults=faults), ensure_ascii=False, indent=1, default=float),
                                       encoding="utf-8")
print("signoff", signoff["all_ok"])

# 圖 1：DRC 規則的故障注入（回讀 fault GDS 的右下角）
pf = polys(fault_gds)
fig, ax = plt.subplots(figsize=(14, 2.8))
colr = {3: G.LAYER_COLOR[3], 4: G.LAYER_COLOR[4], 5: G.LAYER_COLOR[5], 39: G.LAYER_COLOR[39], 41: G.LAYER_COLOR[41], 100: "#555"}
for l, p in pf:
    if l in colr and p[:, 0].min() > 1200 and p[:, 1].max() < -540:
        ax.add_patch(MPoly(p, closed=True, fc=colr[l], ec="black", lw=0.2))
for (l, k), (xx, yy) in where.items():
    ax.text(xx, yy + 4, f"GDS{l}\n{'線寬' if k == 'w' else '間距'}", ha="center", fontsize=7.5)
ax.set_xlim(1230, 1680)
ax.set_ylim(-626, -606)
ax.set_aspect("auto")
ax.set_xlabel("x（µm）")
ax.set_ylabel("y（µm）")
ax.set_title("DRC 規則的故障注入：晶片右下角空白處，每條規則放一個「太窄」與一個「太近」（回讀 drc_rules_fault.gds）", fontsize=10.5)
fig.tight_layout()
fig.savefig(FIG / "drc_faults.png", dpi=140, bbox_inches="tight")
plt.close(fig)

# 圖 2：LVS 抽出的元件與導線（核心區）
fig, ax = plt.subplots(figsize=(15, 4.2))
cm = plt.get_cmap("tab20")
for n, (w, t) in enumerate(ex0["term"]):
    for q in parts(w.intersection(box(-80, -150, 2040, 20))):
        if q.geom_type == "Polygon":
            ax.add_patch(MPoly(np.array(q.exterior.coords), closed=True, fc=cm(n % 20), ec=cm(n % 20), lw=1.2))
for i, b in enumerate(ex0["bodies"]):
    ax.add_patch(MPoly(np.array(b.exterior.coords), closed=True, fc="#222", ec="#222"))
    if i in ex0["name"]:
        nm, ab = ex0["name"][i]
        ax.text(b.centroid.x, b.centroid.y - 6, f"{nm}{'·1' if ab == 'A' else '·2'}", ha="center", va="top", fontsize=7.5)
ax.set_xlim(-80, 2040)
ax.set_ylim(-150, 20)
ax.set_aspect("auto")
ax.set_xlabel("x（µm）")
ax.set_ylabel("y（µm）")
ax.set_title(f"光學 LVS 從 GDS 抽出的元件：黑色是 {lvs0['n_bodies']} 個 MMI 本體，其餘每條導線一種顏色（共 {lvs0['n_wires']} 條，兩端各接一個端點）",
             fontsize=10.5)
fig.tight_layout()
fig.savefig(FIG / "lvs_extract.png", dpi=140, bbox_inches="tight")
plt.close(fig)
print("done", round(time.time() - t0, 1), "s")
