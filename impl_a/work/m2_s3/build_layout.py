"""M2 s3：IPKISS＋Python 佈局。單顆 MZI 與 B7 核心寫成 GDS，從佈局抽出連接表與電路，重跑 80 筆。

用法：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m2_s3\\build_layout.py   （約 1 分鐘）
輸入：spec/pic_spec.json、spec/netlist.json、sources/b7_phases.json（SHA-256 核對）、M0 s2 的 femwell n_eff、n_g。
輸出：out/mzi_core.gds、out/b7_core.gds、out/b7_core_offset.gds（故障注入，供 DRC）、*_drc.lyrdb、
      out/layout_info.json（放置座標、10 個光學埠、14 個相位段與接觸墊位置）、out/m2_s3_result.json；
      course/figures/m2_s3/mzi_core.png、b7_core.png、path_match.png。
步驟：① 幾何與 GDS ② DRC ③ 佈局抽連接表 vs 規格 ④ 佈局電路 80 筆 × 波長 ⑤ 故障注入（連接、長度）。
"""
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "work"))
sys.path.insert(0, str(ROOT / "work" / "common"))
sys.stdout.reconfigure(encoding="utf-8")

import ipkiss3.all as i3  # noqa: E402

import b7_layout as BL  # noqa: E402
import pdk  # noqa: E402
from common import b7, drc  # noqa: E402
from common import gds2png as G  # noqa: E402

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import PatchCollection  # noqa: E402
from matplotlib.patches import Polygon  # noqa: E402

plt.rcParams["font.family"] = ["Microsoft JhengHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT = HERE / "out"
FIG = ROOT / "course" / "figures" / "m2_s3"
OUT.mkdir(exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
WL0 = 1.55
MARGIN = 10.0
BLOCK_B7 = (2100.0, 200.0)       # 配給 B7 核心的設計區（宣告值）
BLOCK_MZI = (520.0, 80.0)
t0 = time.time()

spec = json.loads((ROOT / "spec" / "pic_spec.json").read_text(encoding="utf-8"))
ph_path = ROOT / spec["phase_settings"]["file"]
assert hashlib.sha256(ph_path.read_bytes()).hexdigest() == spec["phase_settings"]["sha256"]
NL = json.loads((ROOT / "spec" / "netlist.json").read_text(encoding="utf-8"))
assert NL["spec_sha256"] == hashlib.sha256((ROOT / "spec" / "pic_spec.json").read_bytes()).hexdigest(), "連接表不是由目前的規格產生"
PH = b7.load_phases(ph_path)
GATES = spec["functions"]
OPS = [list(o) for o in spec["core"]["ops"]]
R_AMP = spec["model"]["R_amplitude"]
m0 = json.loads((ROOT / "work" / "m0_s2" / "out" / "m0_s2_result.json").read_text(encoding="utf-8"))["modes"]["te0"]
NEFF, NG = m0["n_eff"], m0["n_g"]
SPEC_MARGIN = spec["acceptance"]["ideal_margin"]


def outlined(name, child, block):
    """把 cell 放進宣告尺寸的 GDS 99 設計區（置中，圖形離外框至少 MARGIN）。"""
    bb = child.Layout().size_info()
    w, h = bb.east - bb.west, bb.north - bb.south
    assert w + 2 * MARGIN <= block[0] and h + 2 * MARGIN <= block[1], f"{name} {w:.1f}×{h:.1f} 放不進 {block}"
    cx, cy = round((bb.west + bb.east) / 2), round((bb.south + bb.north) / 2)
    box = (cx - block[0] / 2, cy - block[1] / 2, cx + block[0] / 2, cy + block[1] / 2)
    top = i3.LayoutCell(name=name).Layout(elements=[i3.SRef(child, name="core"), BL.rect(pdk.L_OUTLINE, *box)],
                                         ports=list(child.Layout().ports))
    return top, box, (round(w, 3), round(h, 3))


def b7cell(gate=None, fault="none", theta=None, phi=None, name=None):
    th, ph = (PH[gate] if gate else (np.zeros(7), np.zeros(7)))
    th = th if theta is None else theta
    ph = ph if phi is None else phi
    return BL.B7Core(ops=OPS, theta=[float(v) for v in th], phi=[float(v) for v in ph], n_eff=NEFF, n_g=NG,
                     fault=fault, name=name or f"B7_{gate}_{fault}_{hashlib.md5(np.r_[th, ph].tobytes()).hexdigest()[:8]}")


def u_of(cell, wl):
    S = cell.CircuitModel().get_smatrix(wavelengths=np.atleast_1d(wl))
    return np.array([[[S[f"out{o}", f"in{i}"][k] for i in range(5)] for o in range(5)] for k in range(len(np.atleast_1d(wl)))])


def same_up_to_output_phase(U, Ui):
    """U 是否等於 diag(輸出相位)·Ui：大小逐元素相同，且每一列（輸出埠）的相位差一致。回傳 (大小最大差, 列內相位最大散佈)。"""
    mag = float(abs(abs(U) - abs(Ui)).max())
    spread = 0.0
    for o in range(5):
        nz = abs(Ui[o]) > 1e-6
        r = np.angle(U[o, nz] / Ui[o, nz])
        r = np.angle(np.exp(1j * (r - r[0])))
        spread = max(spread, float(abs(r).max()))
    return mag, spread


# ① 幾何與 GDS（相位 0 的版本；相位值不改變幾何）
geo = BL.geometry()
mzi0 = BL.MZI(k=1, n_eff=NEFF, n_g=NG, name="MZI_M1")
mzi_top, mzi_box, mzi_wh = outlined("MZI_CORE", mzi0, BLOCK_MZI)
mzi_top.write_gdsii(str(OUT / "mzi_core.gds"))
core0 = b7cell(name="B7_CORE")
b7_top, b7_box, b7_wh = outlined("B7_CORE_TOP", core0, BLOCK_B7)
b7_top.write_gdsii(str(OUT / "b7_core.gds"))
core_off = b7cell(fault="offset", name="B7_CORE_OFFSET")
off_top, _, _ = outlined("B7_CORE_OFFSET_TOP", core_off, BLOCK_B7)
off_top.write_gdsii(str(OUT / "b7_core_offset.gds"))
print("GDS written", mzi_wh, b7_wh, round(time.time() - t0, 1), "s")

# 佈局資訊：放置座標、埠、相位段與接觸墊
place = []
for k, (p, layer) in enumerate(OPS):
    x0, y0 = layer * BL.L_COL, -BL.PITCH * p
    pads = {}
    for sec, xs in (("phi", 0.0), ("theta", BL.PS_LEN + 2 * BL.SB_L + BL.M_LEN)):
        c = (BL.LAND_W + BL.LAND_M) / 2
        pads[f"M{k + 1}_{sec}"] = [[BL.r3(x0 + xs + c), BL.r3(y0)], [BL.r3(x0 + xs + BL.PS_LEN - c), BL.r3(y0)]]
    place.append(dict(name=f"M{k + 1}", column=layer + 1, rails=[p, p + 1], origin_um=[BL.r3(x0), BL.r3(y0)],
                      heater_contacts_um=pads))
ports = [dict(name=pt.name, xy=[BL.r3(pt.position.x), BL.r3(pt.position.y)], angle=float(pt.angle))
         for pt in core0.Layout().ports]
info = dict(note="B7 核心佈局資訊；座標 µm，rail r 的 y = −30·r；接觸墊座標為 Ti/AL 接觸墊中心（兩端各一）",
            geometry=geo, block_um=BLOCK_B7, outline_um=b7_box, extent_um=b7_wh, mzi=place, ports=ports,
            heater=dict(width_um=BL.HT_W, length_um=BL.HT_L, land_um=BL.LAND_W, contact_um=BL.LAND_W + 2 * BL.LAND_M),
            channels=[f"{m['name']}_{s}" for m in place for s in ("phi", "theta")])
(OUT / "layout_info.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")

# ② DRC（正式 DRC 在 M2 s6；這裡先確認核心本身乾淨，並看 0.1 µm 錯位 DRC 抓不抓得到）
drc_res = {}
for nm, gds, block in (("mzi_core", OUT / "mzi_core.gds", BLOCK_MZI), ("b7_core", OUT / "b7_core.gds", BLOCK_B7),
                       ("b7_core_offset", OUT / "b7_core_offset.gds", BLOCK_B7)):
    r = drc.run(gds, design_area=block)
    drc_res[nm] = dict(total=r["total"], counts=r["counts"], outside=r["outside"], n_rules=len(r["rules"]))
    print("DRC", nm, r["total"], r["counts"], "outside", r["outside"])

# ③ 從佈局抽連接表，與規格的連接表比對
links, ext, dang = BL.contract(core0.Netlist())
key = lambda L: sorted(map(tuple, L))  # noqa: E731
lvs = dict(links_match=key(links) == key(NL["links"]), external_match=ext == NL["external"], dangling=dang,
           n_links=len(links), n_external=len(ext), n_nets=len(core0.Netlist().nets))
print("LVS", lvs)

# ④ 佈局電路：5 種功能 × 16 筆 × 波長（不重新校正）
wl = np.round(np.linspace(1.53, 1.57, 17), 4)
gates = {}
for g in GATES:
    th, ph = PH[g]
    cell = b7cell(g)
    l2, e2, d2 = BL.contract(cell.Netlist())
    U = u_of(cell, wl)
    Ui = b7.unitary(th, ph)
    i0 = int(np.argmin(abs(wl - WL0)))
    mag, spread = zip(*(same_up_to_output_phase(U[k], Ui) for k in range(len(wl))))
    tts = [b7.truth_table(U[k], g, r=R_AMP) for k in range(len(wl))]
    gates[g] = dict(lvs=key(l2) == key(NL["links"]) and e2 == NL["external"] and not d2,
                    wrong_1550=int((tts[i0]["bit"] != tts[i0]["target"]).sum()), margin_1550=tts[i0]["margin"],
                    worst_norm=float(min(t["margin"] for t in tts) / SPEC_MARGIN[g]),
                    all_ok=all(t["ok"] for t in tts), mag_diff=max(mag), phase_spread=max(spread))
    print(g, gates[g])

# ⑤ 故障注入
FAULTS = {
    "offset": "M5 往右錯位 0.1 µm",
    "wrong_rail": "M3 放到 rail 2–3（應為 1–2）",
    "flip": "M6 上下翻轉（heater 跑到下臂）",
    "straight": "旁路改成直線（不等長）",
    "arm": "M7 下臂 θ 段多 2 µm",
}
geo_s = BL.geometry(matched=False)
mut = {}
for f, desc in FAULTS.items():
    cell = b7cell("XOR2", fault=f)
    try:
        l2, e2, d2 = BL.contract(cell.Netlist())
        lv = dict(links_match=key(l2) == key(NL["links"]), external_match=e2 == NL["external"], dangling=d2)
    except Exception as e:  # noqa: BLE001
        lv = dict(error=f"{type(e).__name__}: {str(e)[:160]}")
    res = dict(desc=desc, lvs=lv)
    gds_f = OUT / f"b7_core_{f}.gds"                     # 相位 0 的故障版幾何，跑同一份 DRC
    if f != "offset":
        ftop, _, _ = outlined(f"B7_CORE_{f.upper()}_TOP", b7cell(fault=f, name=f"B7_CORE_{f.upper()}"), BLOCK_B7)
        ftop.write_gdsii(str(gds_f))
    rd = drc.run(gds_f, design_area=BLOCK_B7)
    res["drc"] = dict(total=rd["total"], counts=rd["counts"])
    try:
        wrong, spreads = 0, []
        for g in GATES:
            U = u_of(b7cell(g, fault=f), WL0)[0]
            tt = b7.truth_table(U, g, r=R_AMP)
            wrong += int((tt["bit"] != tt["target"]).sum())
            spreads.append(same_up_to_output_phase(U, b7.unitary(*PH[g])))
        res.update(circuit="ok", wrong_1550=wrong, mag_diff=max(s[0] for s in spreads),
                   phase_spread=max(s[1] for s in spreads))
    except Exception as e:  # noqa: BLE001
        res.update(circuit=f"{type(e).__name__}: {str(e).splitlines()[0][:160]}")
    res["lvs_caught"] = ("error" in lv) or not (lv.get("links_match") and lv.get("external_match") and not lv.get("dangling"))
    res["path_caught"] = res.get("circuit") != "ok" or res.get("mag_diff", 0) > 1e-9 or res.get("phase_spread", 0) > 1e-6
    mut[f] = res
    print(f, res)

# 長度類故障：在 1550 nm 依實際幾何重新校正 heater，再掃雷射波長
wl_d = np.round(np.linspace(1.53, 1.57, 161), 5)
cal = {}
for f, kw in (("none", {}), ("straight", dict(matched=False)), ("arm", dict(extra={6: BL.bump(0, 0, BL.PS_LEN, 2.0)[1]}))):
    worst = np.full(len(wl_d), np.inf)
    chk = 0.0
    for g in GATES:
        th, ph = PH[g]
        th2, ph2 = BL.calibrate(OPS, th, ph, WL0, NEFF, NG, **kw)
        U = u_of(b7cell(g, fault=f, theta=th2, phi=ph2), wl_d)
        i0 = int(np.argmin(abs(wl_d - WL0)))
        chk = max(chk, same_up_to_output_phase(U[i0], b7.unitary(th, ph))[1])
        m = np.array([b7.truth_table(U[k], g, r=R_AMP)["margin"] / SPEC_MARGIN[g] for k in range(len(wl_d))])
        worst = np.minimum(worst, m)
    i0 = int(np.argmin(abs(wl_d - WL0)))
    lo = hi = i0
    while lo > 0 and worst[lo - 1] > 0:
        lo -= 1
    while hi < len(wl_d) - 1 and worst[hi + 1] > 0:
        hi += 1
    cal[f] = dict(worst=worst.tolist(), cal_check=chk, pass_nm=[round((wl_d[lo] - WL0) * 1e3, 2), round((wl_d[hi] - WL0) * 1e3, 2)],
                  full=bool(lo == 0 and hi == len(wl_d) - 1))
    print("calibrated", f, cal[f]["cal_check"], cal[f]["pass_nm"], cal[f]["full"])


# 圖：回讀 GDS
def polys_of(gds):
    structs, db = G.parse(str(gds))
    ref = {s["sname"] for st in structs.values() for s in st["srefs"]}
    top = [n for n in structs if n not in ref][0]
    pl = []
    G.flatten(structs, top, np.eye(2), np.zeros(2), pl)
    return [(l, p * (db / 1e-6)) for l, p in pl]


def draw(ax, pl, xlim=None, ylim=None):
    names = {3: "GDS 3 矽波導", 39: "GDS 39 TiN heater", 41: "GDS 41 Ti/AL 接觸墊", 99: "GDS 99 設計區", 100: "GDS 100 文字"}
    fill, cols = [], []
    for l, p in pl:
        if l == 99:
            ax.add_patch(Polygon(p, closed=True, fill=False, edgecolor=G.LAYER_COLOR[99], lw=1.2))
        else:
            fill.append(Polygon(p, closed=True))
            cols.append(G.LAYER_COLOR.get(l, "#999"))
    ax.add_collection(PatchCollection(fill, facecolor=cols, edgecolor="black", linewidth=0.1, alpha=0.8))
    ax.set_aspect("equal")
    ax.autoscale()
    if xlim:
        ax.set_xlim(*xlim)
    if ylim:
        ax.set_ylim(*ylim)
    ax.set_xlabel("x（µm）")
    ax.set_ylabel("y（µm）")
    import matplotlib.patches as mp
    ls = sorted({l for l, _ in pl})
    return [mp.Patch(color=G.LAYER_COLOR.get(l, "#999")) for l in ls], [names.get(l, f"GDS {l}") for l in ls]


pm = polys_of(OUT / "mzi_core.gds")
fig, ax = plt.subplots(figsize=(13, 3.6))
h, lab = draw(ax, pm)
xs = [0, BL.PS_LEN, BL.PS_LEN + 2 * BL.SB_L + BL.M_LEN, 2 * BL.PS_LEN + 2 * BL.SB_L + BL.M_LEN, BL.L_COL]
for x0, x1, t in ((0, BL.PS_LEN, "φ 段（heater）"), (BL.PS_LEN, xs[2], "S 彎＋MMI1＋S 彎"),
                  (xs[2], xs[3], "θ 段（heater）"), (xs[3], BL.L_COL, "S 彎＋MMI2＋S 彎")):
    ax.annotate("", xy=(x0, 14), xytext=(x1, 14), arrowprops=dict(arrowstyle="<->", color="#555", lw=0.8))
    ax.text((x0 + x1) / 2, 17, t, ha="center", fontsize=9.5, color="#333")
ax.text(-22, 0, "in0（rail p）", ha="right", va="center", fontsize=9)
ax.text(-22, -BL.PITCH, "in1（rail p+1）", ha="right", va="center", fontsize=9)
ax.set_xlim(-110, BL.L_COL + 25)
ax.set_ylim(-48, 26)
ax.legend(h, lab, loc="upper center", bbox_to_anchor=(0.5, -0.28), ncol=len(lab), fontsize=9, frameon=False)
ax.set_title(f"單顆 MZI（回讀 mzi_core.gds）：一欄長 {BL.L_COL:g} µm，兩臂幾何長度 {geo['mzi_upper_um']:.3f}／{geo['mzi_lower_um']:.3f} µm", fontsize=11)
fig.tight_layout()
fig.savefig(FIG / "mzi_core.png", dpi=140, bbox_inches="tight")
plt.close(fig)

pb = polys_of(OUT / "b7_core.gds")
fig, (a1, a2) = plt.subplots(2, 1, figsize=(14, 7.6), gridspec_kw=dict(height_ratios=[1, 1.25]))
h, lab = draw(a1, pb)
for m in place:
    a1.text(m["origin_um"][0] + BL.L_COL / 2, m["origin_um"][1] + 8, m["name"], ha="center", fontsize=9, color="#2d5a8c",
            weight="bold")
for r in range(5):
    a1.text(-70, -BL.PITCH * r, b7.IN_SIGNALS[r], ha="right", va="center", fontsize=9)
    a1.text(4 * BL.L_COL + 70, -BL.PITCH * r, b7.OUT_SIGNALS[r], va="center", fontsize=9)
a1.set_title(f"B7 核心（回讀 b7_core.gds）：四欄 × 五條 rail，設計區 {BLOCK_B7[0]:g}×{BLOCK_B7[1]:g} µm", fontsize=11)
x0z = BL.L_COL - 20
draw(a2, pb, xlim=(x0z, x0z + 560), ylim=(-150, 15))
a1.add_patch(plt.Rectangle((x0z, -150), 560, 165, fill=False, ec="#b3261e", lw=1.4, ls="--"))
a2.set_title("放大第 2 欄：M3 在 rail 1–2；rail 0、3、4 走等長旁路（同樣的 S 彎往下橫移 14 µm）", fontsize=11)
a2.legend(h, lab, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=len(lab), fontsize=9, frameon=False)
fig.tight_layout()
fig.savefig(FIG / "b7_core.png", dpi=140, bbox_inches="tight")
plt.close(fig)

fig, ax = plt.subplots(figsize=(9.5, 4.4))
lbl = {"none": "等長旁路（本設計）", "straight": "直線旁路（每欄短 %.1f µm）" % (geo["bypass_um"] - geo_s["bypass_um"]),
       "arm": "M7 下臂多 2 µm"}
for f, c in (("none", "#2b8a3e"), ("straight", "#b3261e"), ("arm", "#d9480f")):
    ax.plot((wl_d - WL0) * 1000, cal[f]["worst"], color=c, lw=2.2, label=lbl[f])
ax.axhline(0, color="#555", lw=0.8)
ax.set_xlabel("雷射波長偏離 1550 nm（nm）")
ax.set_ylabel("5 種功能中最小的 餘量 ÷ 理想餘量")
ax.set_title("三種佈局都在 1550 nm 校正 heater 後，雷射波長偏移的影響", fontsize=11)
ax.set_ylim(-1.05, 1.1)
ax.grid(alpha=0.3)
ax.legend(fontsize=9.5, loc="lower center")
fig.tight_layout()
fig.savefig(FIG / "path_match.png", dpi=140, bbox_inches="tight")
plt.close(fig)

result = dict(step="M2 s3", date="2026-10-31", n_eff=NEFF, n_g=NG, geometry=geo, geometry_straight=geo_s,
              block_b7=BLOCK_B7, extent_b7=b7_wh, block_mzi=BLOCK_MZI, extent_mzi=mzi_wh,
              drc=drc_res, lvs=lvs, gates=gates, wl_um=wl.tolist(), mutants=mut,
              calibrated=dict(wl_um=wl_d.tolist(), runs=cal), runtime_s=round(time.time() - t0, 1))
(OUT / "m2_s3_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
print("done", result["runtime_s"], "s")
