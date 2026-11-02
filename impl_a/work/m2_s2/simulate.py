"""M2 s2：用 CORNERSTONE MMI＋理想相位區組成 B7，Caphe 求 S，重跑 80 筆並與 NumPy 模型逐元素比對。

用法：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m2_s2\\simulate.py
輸入：spec/pic_spec.json、spec/truth_table.json、sources/b7_phases.json（以 SHA-256 核對）、
      M0 s2 的 femwell 結果（n_eff、n_g，用於臂長差分析）。
輸出：spec/netlist.json（交給佈局）、out/matrices.json、out/truth_tables.csv、out/m2_s2_result.json、
      figures/m2_s2/netlist.png、figures/m2_s2/arm_mismatch.png。
步驟：① 連接表 ② PDK MMI 檢查 ③ 5 種功能 × 16 筆 ④ 波長掃描 ⑤ 連接錯誤注入 ⑥ 上臂長度差與雷射波長。
"""
import csv
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

import b7_circuit as BC  # noqa: E402
import pdk  # noqa: E402
from common import b7  # noqa: E402

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from common import b7plot  # noqa: E402

plt.rcParams["font.family"] = ["Microsoft JhengHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT = HERE / "out"
FIG = ROOT / "course" / "figures" / "m2_s2"
OUT.mkdir(exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
WL0 = 1.55
t0 = time.time()

spec_path = ROOT / "spec" / "pic_spec.json"
spec = json.loads(spec_path.read_text(encoding="utf-8"))
ph_path = ROOT / spec["phase_settings"]["file"]
sha = hashlib.sha256(ph_path.read_bytes()).hexdigest()
assert sha == spec["phase_settings"]["sha256"], "相位檔與規格的 SHA-256 不符"
PH = b7.load_phases(ph_path)
GATES = spec["functions"]
TT = json.loads((ROOT / spec["truth_table"]["file"]).read_text(encoding="utf-8"))["rows"]
REF = {(r["function"], r["bits"]): r for r in TT}
R_AMP = spec["model"]["R_amplitude"]

# ① 連接表：只由規格產生，存到 spec/ 交給佈局
nl = BC.netlist(spec)
nl_doc = {"note": "由 pic_spec.json 的 OPS 與光學埠自動產生；MZI 局部埠 in0/out0 為上臂（rail p，相位段所在）",
          "spec_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
          "mzi_ports": {"in0": "PDK MMI1 in2（上）經 φ", "in1": "PDK MMI1 in1（下）",
                        "out0": "PDK MMI2 out2（上）", "out1": "PDK MMI2 out1（下）"},
          **nl}
(ROOT / "spec" / "netlist.json").write_text(json.dumps(nl_doc, ensure_ascii=False, indent=1), encoding="utf-8")
print("netlist:", len(nl["instances"]), "MZI,", len(nl["links"]), "links,", len(nl["external"]), "external")

# ② PDK MMI：S 矩陣與理想 H 的差
mmi = pdk.mmi2x2()
wl_scan = np.round(np.linspace(1.50, 1.60, 21), 4)
Sm = mmi.CircuitModel().get_smatrix(wavelengths=wl_scan)
Hpdk = np.array([[[Sm[o, i][k] for i in ("in2", "in1")] for o in ("out2", "out1")] for k in range(len(wl_scan))])
H = np.array([[1, 1j], [1j, 1]]) / np.sqrt(2)
mmi_check = dict(max_diff_vs_H=float(abs(Hpdk - H).max()), wl_range=[float(wl_scan[0]), float(wl_scan[-1])],
                 back_reflection=float(max(abs(Sm[a, b]).max() for a in ("in1", "in2") for b in ("in1", "in2"))),
                 ports={p.name: [round(p.position.x, 3), round(p.position.y, 3)] for p in mmi.Layout().ports})
print("MMI vs H:", mmi_check["max_diff_vs_H"])


def rows_wrong(U, gate):
    tt = b7.truth_table(U, gate, r=R_AMP)
    return int((tt["bit"] != tt["target"]).sum()), tt


# ③ 5 種功能 × 16 筆
gates, rows, U_c = {}, [], {}
for g in GATES:
    th, ph = PH[g]
    cell = BC.make_b7(spec, th, ph, nl=nl)
    U, back = BC.forward_u(cell, [WL0])
    U = U[0]
    U_np = b7.unitary(th, ph)
    nwrong, tt = rows_wrong(U, g)
    U_c[g] = U
    gates[g] = dict(diff_vs_numpy=float(abs(U - U_np).max()), unitarity=float(abs(U.conj().T @ U - np.eye(5)).max()),
                    back_reflection=back, wrong=nwrong, margin=tt["margin"],
                    spec_margin=spec["acceptance"]["ideal_margin"][g])
    P = np.abs(np.column_stack([b7.ALL_BITS, np.full(16, R_AMP)]) @ U.T) ** 2
    for i, x in enumerate(b7.ALL_BITS):
        bs = b7.bits_str(x)
        ref = REF[(g, bs)]
        rows.append(dict(function=g, bits=bs, target=int(tt["target"][i]), p_o2=float(P[i, 1]), p_o4=float(P[i, 3]),
                         delta=float(tt["delta"][i]), bit=int(tt["bit"][i]), ok=bool(tt["bit"][i] == tt["target"][i]),
                         delta_spec=ref["delta"], diff_vs_spec=float(abs(tt["delta"][i] - ref["delta"]))))
    print(g, gates[g])
n_ok = sum(r["ok"] for r in rows)
print("80 rows:", n_ok, "/", len(rows))

(OUT / "matrices.json").write_text(json.dumps(
    {"wavelength_um": WL0, "order": "U[out][in]，埠 out0–out4 × in0–in4；元素為 [實部, 虛部]",
     "gates": {g: [[[float(z.real), float(z.imag)] for z in row] for row in U] for g, U in U_c.items()}},
    indent=1), encoding="utf-8")
with open(OUT / "truth_tables.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)

# ④ 波長掃描（無額外波導）：PDK 模型是否隨波長變化
cell = BC.make_b7(spec, *PH["XOR2"], nl=nl)
Uw, _ = BC.forward_u(cell, wl_scan)
wl_flat = float(abs(Uw - Uw[len(wl_scan) // 2]).max())
print("wavelength flatness:", wl_flat)

# ⑤ 連接錯誤注入：U 逐元素比對 vs 只看 80 筆
FAULTS = {
    "lower_arm": "相位段接到下臂（PDK MMI 上下埠 in1／in2 搞反）",
    "swap_theta_phi": "θ 與 φ 兩段相位區對調",
    "neg_phase": "相位區正負號相反 e^(−iφ)",
    "out_swap_M3": "M3 的兩個輸出埠名稱對調",
    "swap_x1_x4": "晶片輸入 x1 與 x4 對調",
    "swap_links": "第 2、3 層之間兩條連線接反",
    "swap_o1_o5": "監看輸出 o1 與 o5 對調（讀取埠 o2、o4 不變）",
}
mutants = {}
for key, desc in FAULTS.items():
    per = {}
    for g in GATES:
        th, ph = PH[g]
        U, _ = BC.forward_u(BC.make_b7(spec, th, ph, fault=key, nl=nl), [WL0])
        nw, tt = rows_wrong(U[0], g)
        per[g] = dict(diff=float(abs(U[0] - U_c[g]).max()), wrong=nw)
    mutants[key] = dict(desc=desc, per_gate=per, rows_wrong=sum(v["wrong"] for v in per.values()),
                        u_caught=any(v["diff"] > 1e-9 for v in per.values()))
    print(key, mutants[key]["rows_wrong"], mutants[key]["u_caught"])

# ⑥ 上臂長度差 ΔL：femwell 的 n_eff、n_g 放進 PDK 波導模型；在 1.55 µm 以 θ 校正，再掃雷射波長
m0 = json.loads((ROOT / "work" / "m0_s2" / "out" / "m0_s2_result.json").read_text(encoding="utf-8"))["modes"]["te0"]
NEFF, NG = m0["n_eff"], m0["n_g"]
tmpl = pdk.pdk.StripWaveguideTemplate()                # 另建模板，不改共用的 pdk.wg_template()
tmpl.Layout(core_width=pdk.WG_W)
tmpl.CircuitModel(n_eff=NEFF, n_g=NG, center_wavelength=WL0, loss_dB_m=0.0)
wl_d = np.round(np.linspace(1.53, 1.57, 161), 5)        # 0.25 nm 步距

# 波導模型的相位斜率是否等於 2π·n_g·L/λ²（確認 Caphe 確實用了這組 n_g）
probe = BC.arm_waveguide(tmpl, 10.0)
Sp = probe.CircuitModel().get_smatrix(wavelengths=wl_d)
psi = np.unwrap(np.angle(Sp["out", "in"]))
slope = float(np.polyfit(wl_d, psi, 1)[0])
slope_th = -2 * np.pi * NG * 10.0 / WL0 ** 2          # ψ = 2π·n_eff·L/λ ⇒ dψ/dλ = −2π·n_g·L/λ²
print("phase slope", slope, "theory", slope_th)
i0 = int(np.argmin(abs(wl_d - WL0)))

DL = [0.0, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0]
disp = {}
for dl in DL:
    arm = BC.arm_waveguide(tmpl, dl)
    if arm is not None:
        Sa = arm.CircuitModel().get_smatrix(wavelengths=wl_d)
        psi = np.unwrap(np.angle(Sa["out", "in"]))
        delta = psi - psi[i0]                          # Caphe 波導模型的殘留相位（精確值）
        psi0 = float(psi[i0])
    else:
        delta, psi0 = np.zeros_like(wl_d), 0.0
    delta_lin = -2 * np.pi * NG * dl * (wl_d - WL0) / WL0 ** 2          # 一階近似
    per = {}
    cross = 0.0
    for g in GATES:
        th, ph = PH[g]
        U, _ = BC.forward_u(BC.make_b7(spec, th - psi0, ph, arms=[arm] * 7, nl=nl), wl_d)
        m = []
        for k in range(len(wl_d)):
            m.append(b7.truth_table(U[k], g, r=R_AMP)["margin"] / gates[g]["spec_margin"])
            cross = max(cross, float(abs(U[k] - b7.unitary(th, ph, theta_offset=delta[k])).max()))
        per[g] = m
    worst = np.min(np.array(list(per.values())), axis=0)
    lo = hi = i0
    while lo > 0 and worst[lo - 1] > 0:
        lo -= 1
    while hi < len(wl_d) - 1 and worst[hi + 1] > 0:
        hi += 1
    disp[str(dl)] = dict(norm_margin=per, worst=worst.tolist(), cross_vs_numpy=cross,
                         lin_err=float(abs(delta - delta_lin).max()),
                         pass_nm=[round((wl_d[lo] - WL0) * 1000, 2), round((wl_d[hi] - WL0) * 1000, 2)],
                         pass_full=bool(lo == 0 and hi == len(wl_d) - 1))
    print("ΔL", dl, "worst min", float(worst.min()), "cross", cross, "pass", disp[str(dl)]["pass_nm"])

# 系統性 θ 偏移的 80 筆極限（NumPy，細掃）：全部 7 顆同向，以及只有單顆
dgrid = np.linspace(-0.6, 0.6, 2401)


def limit(fn):
    ok = np.array([all(b7.truth_table(fn(d, g), g, r=R_AMP)["ok"] for g in GATES) for d in dgrid])
    i0 = len(dgrid) // 2
    lo = i0
    while lo > 0 and ok[lo - 1]:
        lo -= 1
    hi = i0
    while hi < len(dgrid) - 1 and ok[hi + 1]:
        hi += 1
    return float(dgrid[lo]), float(dgrid[hi])


lim_all = limit(lambda d, g: b7.unitary(*PH[g], theta_offset=d))
lim_single = {}
for k in range(7):
    def fn(d, g, k=k):
        th = PH[g][0].copy()
        th[k] += d
        return b7.unitary(th, PH[g][1])
    lim_single[f"M{k + 1}"] = limit(fn)
delta_max = min(abs(lim_all[0]), lim_all[1])
target_rad = spec["acceptance"]["phase_accuracy_rad"]
coef = WL0 ** 2 / (2 * np.pi * NG)                     # ΔL·|Δλ| = δ·λ²/(2π n_g)，單位 µm²
print("limit all", lim_all, "single", lim_single)

# 圖 1：連接表（左：單顆 MZI 內部；右：B7 的 9 條內部連線與 10 個外部埠）
fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 4.6), gridspec_kw=dict(width_ratios=[1, 1.9]))
a1.set_xlim(-0.5, 10.5)
a1.set_ylim(-1.6, 2.6)
a1.axis("off")
for y in (1.0, 0.0):
    a1.plot([0, 10], [y, y], color="#c3ccd8", lw=2, zorder=1)
boxes = [(1.6, "φ", 1.0, "#e8590c"), (3.6, "MMI1", 0.5, "#2d5a8c"), (5.6, "θ", 1.0, "#e8590c"), (7.6, "MMI2", 0.5, "#2d5a8c")]
for x, lab, y, c in boxes:
    h = 1.6 if lab.startswith("MMI") else 0.5
    w_ = 1.4 if lab.startswith("MMI") else 1.1
    a1.add_patch(plt.Rectangle((x - w_ / 2, y - h / 2), w_, h, fc="white", ec=c, lw=1.8, zorder=2))
    a1.text(x, y, lab, ha="center", va="center", fontsize=11 if lab.startswith("MMI") else 13, color=c, weight="bold", zorder=3)
for x in (3.6, 7.6):
    a1.text(x - 0.75, 1.12, "in2", ha="right", fontsize=8, color="#555")
    a1.text(x - 0.75, -0.28, "in1", ha="right", fontsize=8, color="#555")
    a1.text(x + 0.75, 1.12, "out2", fontsize=8, color="#555")
    a1.text(x + 0.75, -0.28, "out1", fontsize=8, color="#555")
a1.text(-0.1, 1.0, "in0\n(rail p)", ha="right", va="center", fontsize=10)
a1.text(-0.1, 0.0, "in1\n(rail p+1)", ha="right", va="center", fontsize=10)
a1.text(10.1, 1.0, "out0", va="center", fontsize=10)
a1.text(10.1, 0.0, "out1", va="center", fontsize=10)
a1.text(5.0, 2.3, "單顆 MZI：PDK MMI 的上埠是 in2／out2", ha="center", fontsize=11.5, weight="bold")
a1.text(5.0, -1.25, "相位段在上臂；局部埠 0 = 上臂 = PDK 的 in2／out2", ha="center", fontsize=9.5, color="#555")
a2.set_xlim(-1.2, 11.4)
a2.set_ylim(-1.0, 4.9)
a2.axis("off")
ys = b7plot.draw_frame(a2)
pos = {}
for k, (p, layer) in enumerate(b7.OPS):
    pos[f"M{k + 1}"] = (b7plot.COLX[layer], p)
for n_, (s, d) in enumerate(nl["links"], 1):
    ms, js = s.split(":")
    md, jd = d.split(":")
    r = pos[ms][1] + int(js[-1])
    x = (pos[ms][0] + 0.5 + pos[md][0] - 0.5) / 2
    a2.text(x, ys[r] + 0.1, f"L{n_}", ha="center", fontsize=9, color="#b3261e", weight="bold",
            bbox=dict(fc="white", ec="none", pad=0.5), zorder=6)
for port, name in nl["external"].items():
    m, j = port.split(":")
    r = pos[m][1] + int(j[-1])
    x = 0.55 if j.startswith("in") else 9.45
    a2.text(x, ys[r] + 0.12, name, ha="center", fontsize=8.5, color="#555", zorder=6)
a2.text(5.0, 4.6, f"B7 連接表：{len(nl['links'])} 條內部連線（紅）＋ {len(nl['external'])} 個外部埠（灰）",
        ha="center", fontsize=11.5, weight="bold")
fig.tight_layout()
fig.savefig(FIG / "netlist.png", dpi=130, bbox_inches="tight")
plt.close(fig)

# 圖 2：上臂長度差（a）最差功能的相對餘量 vs 雷射波長（b）允許的 ΔL vs 雷射波長偏移
fig, (b1, b2) = plt.subplots(1, 2, figsize=(13, 4.6))
cmap = plt.get_cmap("viridis")
for n_, dl in enumerate(DL):
    b1.plot((wl_d - WL0) * 1000, disp[str(dl)]["worst"], color=cmap(n_ / (len(DL) - 1)), lw=2,
            label=f"ΔL = {dl:g} µm")
b1.axhline(0, color="#b3261e", lw=1)
b1.set_xlabel("雷射波長偏離 1550 nm（nm）")
b1.set_ylabel("5 種功能中最小的 餘量 ÷ 理想餘量")
b1.set_title("(a) 7 顆 MZI 上臂都多 ΔL，在 1550 nm 校正", fontsize=11)
b1.set_ylim(-1.05, 1.55)
b1.grid(alpha=0.3)
b1.legend(fontsize=8.5, loc="upper center", ncol=4)
dlam = np.logspace(-2, 1.3, 50)
b2.loglog(dlam, delta_max * coef / (dlam * 1e-3), color="#b3261e", lw=2,
          label=f"80 筆全對的極限（θ 同向偏 {delta_max:.3f} rad）")
b2.loglog(dlam, target_rad * coef / (dlam * 1e-3), color="#1f6feb", lw=2,
          label=f"設計目標：殘留相位 ≤ {target_rad} rad")
b2.set_xlabel("雷射波長偏移 |Δλ|（nm）")
b2.set_ylabel("允許的上臂長度差 ΔL（µm）")
b2.set_title("(b) 雷射波長偏移越大，兩臂越要等長", fontsize=11)
b2.grid(alpha=0.3, which="both")
b2.minorticks_off()
b2.set_xticks([0.01, 0.1, 1, 10], ["0.01", "0.1", "1", "10"])
b2.set_yticks([0.01, 0.1, 1, 10, 100, 1000], ["0.01", "0.1", "1", "10", "100", "1000"])
b2.legend(fontsize=9)
fig.tight_layout()
fig.savefig(FIG / "arm_mismatch.png", dpi=130, bbox_inches="tight")
plt.close(fig)

result = dict(
    step="M2 s2", date="2026-10-31",
    model_scope="CORNERSTONE SOI220 2×2 MMI 電路模型＋理想相位區＋零長度連線；⑥ 另加 femwell 參數的直波導",
    netlist=dict(n_mzi=len(nl["instances"]), n_links=len(nl["links"]), n_external=len(nl["external"]),
                 links=nl["links"], external=nl["external"]),
    mmi=mmi_check, wg_default={k: float(getattr(pdk.wg_template().CircuitModel(), k))
                               for k in ("n_eff", "n_g", "loss_dB_m", "center_wavelength")},
    gates=gates, rows_ok=n_ok, rows_total=len(rows),
    max_diff_vs_numpy=max(v["diff_vs_numpy"] for v in gates.values()),
    max_diff_vs_spec=max(r["diff_vs_spec"] for r in rows),
    wl_flatness=wl_flat, mutants=mutants,
    arm=dict(n_eff=NEFF, n_g=NG, slope_caphe=slope, slope_theory=slope_th, wl_um=wl_d.tolist(), dl_um=DL,
             disp=disp, limit_all=lim_all, limit_single=lim_single, delta_max=delta_max, target_rad=target_rad,
             coef_um2_per_rad=coef),
    runtime_s=round(time.time() - t0, 1),
)
(OUT / "m2_s2_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
print("done", result["runtime_s"], "s")
