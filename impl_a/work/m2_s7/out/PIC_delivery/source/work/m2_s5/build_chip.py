"""M2 s5：B7 晶片佈局。M2 s3 的核心原樣放入，加上 EC、扇入／扇出、heater 接墊與回流；寫 GDS 後回讀檢查。

用法：python work\\m2_s5\\build_chip.py   （約 1 分鐘）
輸入：spec/pic_spec.json、spec/netlist.json、sources/b7_phases.json（SHA-256）、M2 s3 的 out/layout_info.json 與
      out/b7_core.gds（核心比對基準）、M0 s2 的 femwell n_eff、n_g。
輸出：out/b7_chip.gds、out/b7_chip_<故障>.gds、*_drc.lyrdb、out/chip_info.json、out/m2_s5_result.json；
      course/figures/m2_s5/chip_overview.png、ec_detail.png、electrical.png。
檢查：① 核心與 M2 s3 相同 ② DRC ③ 光路：從佈局抽出 fiber_in → 核心 → fiber_out ④ 晶片電路 80 筆 × 波長
      ⑤ 電氣：回讀 GDS 的金屬連通網、接墊 → heater → 規格通道、短路／開路 ⑥ 金屬跨波導 ⑦ 故障注入。
"""
import hashlib
import json
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

import ipkiss3.all as i3  # noqa: E402,F401

import b7_chip as BC  # noqa: E402
import b7_layout as BL  # noqa: E402
from common import b7, drc  # noqa: E402
from common import gds2png as G  # noqa: E402

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import PatchCollection  # noqa: E402
from matplotlib.patches import Polygon as MPoly, Rectangle  # noqa: E402

plt.rcParams["font.family"] = ["Microsoft JhengHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT = HERE / "out"
FIG = ROOT / "course" / "figures" / "m2_s5"
OUT.mkdir(exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
S3 = ROOT / "work" / "m2_s3" / "out"
WL0 = 1.55
t0 = time.time()

spec = json.loads((ROOT / "spec" / "pic_spec.json").read_text(encoding="utf-8"))
ph_path = ROOT / spec["phase_settings"]["file"]
assert hashlib.sha256(ph_path.read_bytes()).hexdigest() == spec["phase_settings"]["sha256"]
PH = b7.load_phases(ph_path)
GATES = spec["functions"]
OPS = [list(o) for o in spec["core"]["ops"]]
R_AMP = spec["model"]["R_amplitude"]
SPEC_MARGIN = spec["acceptance"]["ideal_margin"]
CTRL = {(c["mzi"], c["phase"]): c for c in spec["phase_controls"]}
INFO = json.loads((S3 / "layout_info.json").read_text(encoding="utf-8"))
CONTACTS = {k: v for m in INFO["mzi"] for k, v in m["heater_contacts_um"].items()}
m0 = json.loads((ROOT / "work" / "m0_s2" / "out" / "m0_s2_result.json").read_text(encoding="utf-8"))["modes"]["te0"]
NEFF, NG = m0["n_eff"], m0["n_g"]
L_COL, PITCH = BL.L_COL, BL.PITCH


def core_cell(gate=None, name=None):
    th, ph = PH[gate] if gate else (np.zeros(7), np.zeros(7))
    return BL.B7Core(ops=OPS, theta=[float(v) for v in th], phi=[float(v) for v in ph], n_eff=NEFF, n_g=NG,
                     name=name or f"B7_{gate}_none_{hashlib.md5(np.r_[th, ph].tobytes()).hexdigest()[:8]}")


def chip_cell(core, fault="none", ec_t=1.0, name=None):
    return BC.Chip(core=core, contacts=CONTACTS, ops=OPS, n_eff=NEFF, n_g=NG, ec_t=ec_t, fault=fault,
                   name=name or f"CHIP_{core.name}_{fault}_{ec_t:.4f}")


def u_of(cell, wl):
    wl = np.atleast_1d(wl)
    S = cell.CircuitModel().get_smatrix(wavelengths=wl)
    return np.array([[[S[f"fiber_out{o}", f"fiber_in{i}"][k] for i in range(5)] for o in range(5)] for k in range(len(wl))])


def same_up_to_output_phase(U, Ui):
    mag = float(abs(abs(U) - abs(Ui)).max())
    spread = 0.0
    for o in range(5):
        nz = abs(Ui[o]) > 1e-6
        r = np.angle(U[o, nz] / Ui[o, nz])
        spread = max(spread, float(abs(np.angle(np.exp(1j * (r - r[0])))).max()))
    return mag, spread


def polys_of(gds, struct=None):
    structs, db = G.parse(str(gds))
    ref = {s["sname"] for st in structs.values() for s in st["srefs"]}
    top = struct or [n for n in structs if n not in ref][0]
    pl = []
    G.flatten(structs, top, np.eye(2), np.zeros(2), pl)
    return [(l, p * (db / 1e-6)) for l, p in pl]


# ① GDS：核心（相位 0）＋晶片；核心與 M2 s3 的 b7_core.gds 逐多邊形比對
core0 = core_cell(name="B7_CORE")
chip0 = chip_cell(core0, name="B7_CHIP")
chip0.Layout().write_gdsii(str(OUT / "b7_chip.gds"))


def canon(pl):
    return sorted((l, tuple(np.round(p, 3).ravel())) for l, p in pl)


same_core = canon(polys_of(OUT / "b7_chip.gds", "B7_CORE")) == canon(polys_of(S3 / "b7_core.gds", "B7_CORE"))
print("core identical to M2 s3:", same_core)

# ② DRC（宣告晶片尺寸）
FAULTS = {"open": "M4_theta 訊號線停在接觸墊外 2 µm（開路）", "short": "M3_phi 訊號線畫到回流匯流排（短路）",
          "pad_swap": "對照表把 M1_phi、M1_theta 兩個接墊名稱寫反", "unmatched": "扇入不加等長凸起"}
drc_res = {}
for f in ["none"] + list(FAULTS):
    gds = OUT / ("b7_chip.gds" if f == "none" else f"b7_chip_{f}.gds")
    if f != "none":
        chip_cell(core0, fault=f, name=f"B7_CHIP_{f.upper()}").Layout().write_gdsii(str(gds))
    r = drc.run(gds, design_area=BC.DIE)
    drc_res[f] = dict(total=r["total"], counts=r["counts"], outside=r["outside"], n_rules=len(r["rules"]))
    print("DRC", f, r["total"], r["counts"], "outside", r["outside"])


# ③ 光路：沿抽出的連接，從每個 fiber_in 走到核心、從核心走到 fiber_out
def chains(nv):
    adj, terms = {}, {}
    for key in nv.nets.keys():
        a, b = key.split("-")
        for x, y in ((a, b), (b, a)):
            adj.setdefault(x, []).append(y)
        for t in (a, b):
            if ":" in t:
                i, n = t.split(":")
                terms.setdefault(i, set()).add(n)

    def walk(t):
        path = [t]
        for _ in range(20):
            nxt = adj.get(path[-1], [])
            if not nxt:
                return path, None
            n = nxt[0]
            path.append(n)
            if ":" not in n or n.startswith("core:"):
                return path, n
            i, nm = n.split(":")
            other = [x for x in terms[i] if x != nm]
            path.append(f"{i}:{other[0]}")
        return path, None
    res = {}
    for k in range(5):
        res[f"fiber_in{k}"] = walk(f"fiber_in{k}")[1]
        res[f"core:out{k}"] = walk(f"core:out{k}")[1]
    return res


ch = chains(chip0.Netlist())
optical_ok = all(ch[f"fiber_in{k}"] == f"core:in{k}" and ch[f"core:out{k}"] == f"fiber_out{k}" for k in range(5))
print("optical chains", optical_ok, ch)

# ④ 晶片電路：fiber_in → fiber_out，80 筆 × 1530–1570 nm（不重新校正）
wl = np.round(np.linspace(1.53, 1.57, 17), 4)
L_in = BC.input_lengths(True)
gates = {}
for g in GATES:
    th, ph = PH[g]
    U = u_of(chip_cell(core_cell(g)), wl)
    Ui = b7.unitary(th, ph)
    mag, spread = zip(*(same_up_to_output_phase(U[k], Ui) for k in range(len(wl))))
    tts = [b7.truth_table(U[k], g, r=R_AMP) for k in range(len(wl))]
    i0 = int(np.argmin(abs(wl - WL0)))
    gates[g] = dict(wrong_1550=int((tts[i0]["bit"] != tts[i0]["target"]).sum()), margin_1550=tts[i0]["margin"],
                    worst_norm=float(min(t["margin"] for t in tts) / SPEC_MARGIN[g]), all_ok=all(t["ok"] for t in tts),
                    mag_diff=max(mag), phase_spread=max(spread))
    print(g, gates[g])

# EC 損耗：所有通道相同時，ΔP 只是等比例縮小
t_ec = 10 ** (-3.0 / 20)
loss = {}
for g in GATES:
    U = u_of(chip_cell(core_cell(g), ec_t=t_ec), [WL0])[0]
    tt = b7.truth_table(U, g, r=R_AMP)
    loss[g] = dict(ok=tt["ok"], ratio=tt["margin"] / gates[g]["margin_1550"])
print("EC loss", loss)

# 扇入不等長：未校正的 80 筆，以及在 1550 nm 校正後的可用波長
L_un = BC.input_lengths(False)
wl_d = np.round(np.linspace(1.53, 1.57, 161), 5)
cal = {}
for f, lens in (("none", L_in), ("unmatched", L_un)):
    worst, wrong0 = np.full(len(wl_d), np.inf), 0
    for g in GATES:
        th, ph = PH[g]
        U0 = u_of(chip_cell(core_cell(g), fault=f), [WL0])[0]
        tt0 = b7.truth_table(U0, g, r=R_AMP)
        wrong0 += int((tt0["bit"] != tt0["target"]).sum())
        th2, ph2 = BL.calibrate(OPS, th, ph, WL0, NEFF, NG, input_um=lens - lens.min())
        core = BL.B7Core(ops=OPS, theta=[float(v) for v in th2], phi=[float(v) for v in ph2], n_eff=NEFF, n_g=NG,
                         name=f"B7_cal_{f}_{g}")
        U = u_of(chip_cell(core, fault=f), wl_d)
        m = np.array([b7.truth_table(U[k], g, r=R_AMP)["margin"] / SPEC_MARGIN[g] for k in range(len(wl_d))])
        worst = np.minimum(worst, m)
    i0 = int(np.argmin(abs(wl_d - WL0)))
    lo = hi = i0
    while lo > 0 and worst[lo - 1] > 0:
        lo -= 1
    while hi < len(wl_d) - 1 and worst[hi + 1] > 0:
        hi += 1
    cal[f] = dict(wrong_uncal=wrong0, worst=worst.tolist(), full=bool(lo == 0 and hi == len(wl_d) - 1),
                  pass_nm=[round((wl_d[lo] - WL0) * 1e3, 2), round((wl_d[hi] - WL0) * 1e3, 2)],
                  len_spread_um=float(lens.max() - lens.min()))
    print("fan-in", f, cal[f]["wrong_uncal"], cal[f]["pass_nm"], cal[f]["len_spread_um"])


# ⑤ 電氣：只讀 GDS。金屬連通網 → 接墊、heater；heater 位置 → 規格通道
def electrical(gds, pad_table):
    pl = polys_of(gds)
    metal = [Polygon(p) for l, p in pl if l == 41]
    tin = unary_union([Polygon(p) for l, p in pl if l == 39])
    si = unary_union([Polygon(p) for l, p in pl if l == 3])
    pads = [q for q in metal if abs(q.area - BC.PAD ** 2) < 1 and abs((q.bounds[2] - q.bounds[0]) - BC.PAD) < 1e-3]
    mu = unary_union(metal)
    nets = list(mu.geoms) if mu.geom_type == "MultiPolygon" else [mu]
    hts = list(tin.geoms) if tin.geom_type == "MultiPolygon" else [tin]
    net_of = lambda g: next(i for i, n in enumerate(nets) if n.intersects(g))  # noqa: E731
    name_at = {(round(x, 1), round(y, 1)): n for n, x, y, _ in pad_table}
    pad_net = {}
    for q in pads:
        c = q.centroid
        pad_net[name_at.get((round(c.x, 1), round(c.y, 1)), "?")] = net_of(q)
    problems, heaters = [], {}
    for h in hts:
        cx, cy = h.centroid.coords[0]
        lay, rail = int(cx // L_COL), int(round(-cy / PITCH))
        sec = "phi" if (cx - lay * L_COL) < L_COL / 2 else "theta"
        k = next(i for i, (p, l) in enumerate(OPS) if l == lay and rail in (p, p + 1))
        chn = CTRL[(k + 1, sec)]["channel"]
        touch = sorted({i for i, n in enumerate(nets) if n.intersects(h)})
        heaters[chn] = touch
        if len(touch) != 2:
            problems.append(f"{chn} 兩端接到 {len(touch)} 個金屬網（應為 2：訊號、回流）")
    gnd = {pad_net.get("GND_T"), pad_net.get("GND_B")}
    for n, i in pad_net.items():
        if n.startswith("GND"):
            continue
        hs = [c for c, t in heaters.items() if i in t]
        others = [m for m, j in pad_net.items() if j == i and m != n]
        if hs != [n]:
            problems.append(f"接墊 {n} 的金屬網接到 heater {hs}（應為 [{n}]）")
        if others:
            problems.append(f"接墊 {n} 與 {others} 短路")
        if i in gnd:
            problems.append(f"接墊 {n} 與回流短路")
    for c, t in heaters.items():
        if len(t) == 2 and not (set(t) & gnd):
            problems.append(f"{c} 沒有接到回流")
    sig_nets = {i for n, i in pad_net.items() if not n.startswith("GND")}
    # 金屬跨波導：金屬 ∩ Si，扣掉 heater 接觸墊（TiN 落墊上方，本來就在波導上）
    over = mu.intersection(si).difference(tin.buffer(1.5))
    parts = [g for g in (over.geoms if hasattr(over, "geoms") else [over]) if g.area > 1e-6]
    straight = all(g.bounds[3] - g.bounds[1] < pdk_w + 1e-3 for g in parts)
    lower_arm = {}
    for g in parts:
        cx, cy = g.centroid.coords[0]
        lay, rail = int(cx // L_COL), int(round(-cy / PITCH))
        k = next((i for i, (p, l) in enumerate(OPS) if l == lay and rail == p + 1), None)
        if k is not None:
            lower_arm[f"M{k + 1}"] = lower_arm.get(f"M{k + 1}", 0) + 1
    return dict(n_nets=len(nets), n_signal_nets=len(sig_nets), n_heaters=len(hts), n_pads=len(pads),
                gnd_heaters={n: sum(1 for t in heaters.values() if pad_net.get(n) in t) for n in ("GND_T", "GND_B")},
                problems=problems, ok=not problems and len(sig_nets) == 14 and len(pads) == 16,
                crossings=len(parts), crossings_straight=bool(straight), lower_arm_crossings=lower_arm)


pdk_w = 0.45
plan0 = BC.plan(OPS, CONTACTS)
elec = {"none": electrical(OUT / "b7_chip.gds", plan0["pads"])}
for f in ("open", "short", "pad_swap"):
    elec[f] = electrical(OUT / f"b7_chip_{f}.gds", BC.plan(OPS, CONTACTS, f)["pads"])
for f, v in elec.items():
    print("elec", f, v["ok"], v["n_nets"], v["n_signal_nets"], v["gnd_heaters"], v["crossings"], v["problems"][:3])

# 晶片資訊
info = dict(note="B7 晶片佈局資訊；座標 µm，與核心同一座標系（核心原點 (0, 0)）",
            die_um=BC.DIE, die_box_um=[BC.X_LEFT, BC.Y_DIE[0], BC.X_RIGHT, BC.Y_DIE[1]],
            ec=dict(geometry=BC.EC, length_um=BC.EC_LEN, fiber_pitch_um=BC.FIBER_PITCH,
                    inputs=[dict(port=f"fiber_in{k}", signal=b7.IN_SIGNALS[k], core=f"in{k}", facet=[BC.X_LEFT, BC.ec_y(k)])
                            for k in range(5)],
                    outputs=[dict(port=f"fiber_out{k}", signal=b7.OUT_SIGNALS[k], core=f"out{k}",
                                  facet=[BC.X_RIGHT, BC.ec_y(k)]) for k in range(5)]),
            fan_in_length_um=L_in.tolist(), fan_in_length_unmatched_um=L_un.tolist(),
            pads=[dict(name=n, xy=[x, y], size_um=BC.PAD, side="top" if y > 0 else "bottom",
                       role="回流" if n.startswith("GND") else "heater 訊號") for n, x, y, _ in plan0["pads"]],
            metal=dict(line_width_um=BC.W_LINE, bus_width_um=BC.BUS_W, buses=plan0["buses"]),
            gds_sha256=hashlib.sha256((OUT / "b7_chip.gds").read_bytes()).hexdigest())
(OUT / "chip_info.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")

# 圖
COL = {3: G.LAYER_COLOR[3], 4: G.LAYER_COLOR[4], 5: G.LAYER_COLOR[5], 39: G.LAYER_COLOR[39], 41: G.LAYER_COLOR[41],
       100: G.LAYER_COLOR[100]}
NAMES = {3: "GDS 3 矽波導", 4: "GDS 4 蝕刻窗", 5: "GDS 5 薄矽保護", 39: "GDS 39 TiN", 41: "GDS 41 Ti/AL", 100: "GDS 100 文字",
         99: "GDS 99 晶片外框"}
pl = polys_of(OUT / "b7_chip.gds")


def draw(ax, pl, layers=(4, 5, 3, 39, 41, 100), colors=None, lw=0.1):
    import matplotlib.patches as mp
    for l in layers:
        ps = [MPoly(p, closed=True) for ll, p in pl if ll == l]
        if ps:
            ax.add_collection(PatchCollection(ps, facecolor=(colors or COL).get(l, "#999"), edgecolor="black",
                                              linewidth=lw, alpha=0.85))
    ob = [p for ll, p in pl if ll == 99][0]
    ax.add_patch(Rectangle((ob[:, 0].min(), ob[:, 1].min()), np.ptp(ob[:, 0]), np.ptp(ob[:, 1]), fill=False,
                           ec=G.LAYER_COLOR[99], lw=1.2))
    ax.set_aspect("equal")
    ax.set_xlabel("x（µm）")
    ax.set_ylabel("y（µm）")
    return [mp.Patch(color=(colors or COL).get(l, "#999")) for l in layers], [NAMES[l] for l in layers]


fig, ax = plt.subplots(figsize=(15, 5.6))
h, lab = draw(ax, pl)
ax.set_xlim(BC.X_LEFT - 60, BC.X_RIGHT + 60)
ax.set_ylim(BC.Y_DIE[0] - 30, BC.Y_DIE[1] + 30)
for k in range(5):
    ax.text(BC.X_LEFT - 12, BC.ec_y(k), b7.IN_SIGNALS[k], ha="right", va="center", fontsize=10, color="#1f6feb", weight="bold")
    ax.text(BC.X_RIGHT + 12, BC.ec_y(k), b7.OUT_SIGNALS[k], va="center", fontsize=10,
            color="#0b6b2e" if k in b7.READOUT else "#777", weight="bold")
ax.add_patch(Rectangle((-60, -150), BC.CORE_OUT + 60, 160, fill=False, ec="#2d5a8c", ls="--", lw=1))
ax.text(978, -215, "B7 核心（M2 s3，未修改）", ha="center", fontsize=10, color="#2d5a8c", bbox=dict(fc="white", ec="none", pad=1), zorder=8)
ax.text((BC.X_LEFT + BC.CORE_IN) / 2, 500, "EC ＋ 等長扇入（250 → 30 µm）", ha="center", fontsize=10)
ax.text((BC.CORE_OUT + BC.X_RIGHT) / 2, 500, "扇出 ＋ EC", ha="center", fontsize=10)
ax.text(978, 420, "上排：8 個訊號接墊（rail 0、1 的 heater）＋ 回流匯流排與 GND_T", ha="center", fontsize=9.5)
ax.text(978, -560, "下排：6 個訊號接墊（rail 2、3 的 heater）＋ 回流匯流排與 GND_B", ha="center", fontsize=9.5)
ax.legend(h, lab, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=len(lab), fontsize=9, frameon=False)
ax.set_title(f"B7 晶片全圖（回讀 b7_chip.gds）：{BC.DIE[0]:g} × {BC.DIE[1]:g} µm", fontsize=11)
fig.tight_layout()
fig.savefig(FIG / "chip_overview.png", dpi=140, bbox_inches="tight")
plt.close(fig)

fig, axs = plt.subplots(1, 2, figsize=(14, 4.2), gridspec_kw=dict(width_ratios=[1, 1.3]))
y4 = BC.ec_y(2)
h, lab = draw(axs[0], pl, layers=(4, 5, 3))
axs[0].set_xlim(BC.X_LEFT - 5, BC.X_LEFT + 60)
axs[0].set_ylim(y4 - 30, y4 + 30)
axs[0].set_title("(a) 端面附近：GDS 5 尖端 0.25 µm、GDS 4 開窗、GDS 3 研磨刻度", fontsize=10)
draw(axs[1], pl, layers=(4, 5, 3))
axs[1].set_xlim(BC.X_LEFT + 215, BC.X_LEFT + 275)
axs[1].set_ylim(y4 - 3, y4 + 3)
axs[1].set_aspect("auto")
axs[1].set_title("(b) 雙層轉換（縱向放大）：0.35 µm 核心起點 → 0.45 µm strip", fontsize=10)
axs[0].legend(h, lab, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3, fontsize=9, frameon=False)
fig.tight_layout()
fig.savefig(FIG / "ec_detail.png", dpi=140, bbox_inches="tight")
plt.close(fig)

# 電氣：金屬依連通網著色（回讀 GDS）
metal = unary_union([Polygon(p) for l, p in pl if l == 41])
nets = list(metal.geoms)
gnd_ids = {i for i, n in enumerate(nets) if n.area > 30000}
fig, ax = plt.subplots(figsize=(15, 5.2))
draw(ax, pl, layers=(3, 39))
cm = plt.get_cmap("tab20")
for i, n in enumerate(nets):
    c = "#b3261e" if i in gnd_ids else cm(i % 20)
    ax.add_patch(MPoly(np.array(n.exterior.coords), closed=True, fc=c, ec="black", lw=0.2, alpha=0.9, zorder=5))
for n, x, y, _ in plan0["pads"]:
    ax.text(x, y, n, ha="center", va="center", fontsize=6.5, color="white", weight="bold", zorder=6)
ax.set_xlim(-80, 1900)
ax.set_ylim(-540, 420)
ax.set_title("金屬依連通網著色（回讀 b7_chip.gds）：每個訊號網一種顏色，紅色為兩個回流網", fontsize=11)
fig.tight_layout()
fig.savefig(FIG / "electrical.png", dpi=140, bbox_inches="tight")
plt.close(fig)

result = dict(step="M2 s5", date="2026-10-31", n_eff=NEFF, n_g=NG, die_um=BC.DIE, core_identical=same_core,
              drc=drc_res, optical=dict(ok=optical_ok, chains=ch), gates=gates, wl_um=wl.tolist(), ec_loss=dict(t=t_ec, gates=loss),
              fan_in=dict(matched=L_in.tolist(), unmatched=L_un.tolist(), wl_um=wl_d.tolist(), runs=cal),
              electrical=elec, faults=FAULTS, runtime_s=round(time.time() - t0, 1))
(OUT / "m2_s5_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
print("done", result["runtime_s"], "s")
