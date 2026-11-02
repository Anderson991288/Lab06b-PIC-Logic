"""M0 s2（E3）：Meep 2D 光場傳播——單顆 2×2 MMI，以及 MZI 的切換、分光、合光。

幾何來源（不手抄尺寸）：
  - 2×2 MMI：out/mmi_geometry.json（export_mmi.py 從 PDK 佈局取出的 GDS 3 多邊形與埠位置）。
  - MZI 臂：M0 s1 測試件的參數（work/m0_s1/out/mzi_drc_result.json）：兩臂間距 RAIL_P、餘弦 S 彎長 SB_L 與端點短段。
  - 核心折射率：out/modes.json 的 220 nm 平板 TE0 n_slab（有效折射率法），包覆 SiO2 1.444。
簡化（頁面上要講清楚）：
  - 2D 有效折射率法，只算 TE（電場在晶片平面內）。
  - θ 段臂長取 ARM_L＝20 µm（實際佈局 122 µm）以縮短模擬；θ 以上臂核心折射率 +Δn 產生。
    Δn 不用經驗校正：Δφ = k0·Γ·Δn·ARM_L，Γ = ∂n_eff/∂n_core 由 0.45 µm 橫向平板的解析式數值微分求得。
案例：mmi（只有一顆 MMI）、t0（in1，θ=0）、tpi（in1，θ=π）、tpi2（in1，θ=π/2）、comb（in1＋in2 相干、θ=π/2）。
輸出：out/field_<case>.npz（時間平均 |E|²、範圍、各輸出埠功率比）、out/field_<case>.json。
執行（WSL Ubuntu 的 meep 環境）：python mzi_field.py <case>；全部案例見 run_fields.sh。
"""
import os
import sys
import json
import math
import time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
ROOT = os.path.dirname(os.path.dirname(HERE))
MMI = json.load(open(os.path.join(OUT, "mmi_geometry.json")))
MODES = json.load(open(os.path.join(OUT, "modes.json")))
P1 = json.load(open(os.path.join(ROOT, "work", "m0_s1", "out", "mzi_drc_result.json")))["params"]

LAM = 1.55
N_CORE = MODES["eim"]["n_slab_TE0_220nm"]
N_CLAD = MODES["materials"]["SiO2"]
WG = MMI["port_width_um"]
RES = int(os.environ.get("MEEP_RES", 24))    # px/µm；MMI 試算：16 → 總穿透 0.893（離散化損耗），24 → 0.975
TAG = os.environ.get("MEEP_TAG", "")         # 收斂測試用的檔名後綴，例如 _r32
DPML, LEAD = 1.5, 8.0
ARM_HALF = P1["RAIL_P"] / 2           # 15 µm
SB_L, SB_STUB = P1["SB_L"], 0.5        # 與 M0 s1 相同的餘弦 S 彎
ARM_L = 20.0                           # θ 段直線長（模擬用縮短值）
PX = {k: v[0] for k, v in MMI["ports"].items()}
PY = MMI["ports"]["in2"][1]            # +1.015
X_IN, X_OUT = PX["in1"], PX["out1"]    # MMI 自身座標：−20、62.5


def slab_neff(n1, n2, d, lam, tm=False):
    k0 = 2 * np.pi / lam
    r = (n1 / n2) ** 2 if tm else 1.0
    f = lambda n: np.tan(k0 * np.sqrt(n1 ** 2 - n ** 2) * d / 2) - r * np.sqrt(n ** 2 - n2 ** 2) / np.sqrt(n1 ** 2 - n ** 2)
    lo = max(n2 + 1e-9, np.sqrt(max(n1 ** 2 - (np.pi / (k0 * d)) ** 2, n2 ** 2)) + 1e-9)
    hi = n1 - 1e-9
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if f(lo) * f(mid) <= 0 else (mid, hi)
    return (lo + hi) / 2


def gamma_lateral():
    """2D 波導 n_eff 對核心折射率的靈敏度 Γ = ∂n_eff/∂n_core（中央差分）。"""
    h = 1e-4
    return (slab_neff(N_CORE + h, N_CLAD, WG, LAM, True) - slab_neff(N_CORE - h, N_CLAD, WG, LAM, True)) / (2 * h)


def sbend(x0, y0, y1, L=SB_L, n=81, stub=SB_STUB):
    u = np.linspace(0, 1, n)
    Lc = L - 2 * stub
    return np.array([(x0, y0)] + [(x0 + stub + Lc * t, y0 + (y1 - y0) * (1 - math.cos(math.pi * t)) / 2) for t in u]
                    + [(x0 + L, y1)])


def clean_poly(p):
    """GDS 多邊形最後一點與第一點重複，且方向不一；Meep Prism 遇到時會把整個外框填滿。去掉重複點並改成逆時針。"""
    p = np.asarray(p, float)
    if np.allclose(p[0], p[-1]):
        p = p[:-1]
    area = 0.5 * np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1])
    return p if area > 0 else p[::-1]


def ribbon(pts, w):
    t = np.gradient(pts, axis=0)
    t /= np.linalg.norm(t, axis=1)[:, None]
    nrm = np.stack([-t[:, 1], t[:, 0]], 1)
    return np.vstack([pts + nrm * w / 2, (pts - nrm * w / 2)[::-1]])


def layout(case):
    """回傳 (MMI 原點 x 列表, S 彎與臂的中心線, x 範圍)。MMI 原點使其 in 埠位於指定 x。"""
    if case == "mmi":
        return [0.0], [], (X_IN - LEAD, X_OUT + LEAD)
    x_sb1 = X_OUT
    x_arm0 = x_sb1 + SB_L
    x_arm1 = x_arm0 + ARM_L
    x_m2 = x_arm1 + SB_L - X_IN
    arms = []
    for s in (+1, -1):
        arms.append(("sb", sbend(x_sb1, s * PY, s * ARM_HALF)))
        arms.append(("arm", np.array([(x_arm0, s * ARM_HALF), (x_arm1, s * ARM_HALF)]), s))
        arms.append(("sb", sbend(x_arm1, s * ARM_HALF, s * PY)))
    return [0.0, x_m2], arms, (X_IN - LEAD, x_m2 + X_OUT + LEAD)


CASES = {  # θ, 輸入 [(埠 y, 複數振幅)]（None＝理想合光相位）
    "mmi": (None, [(-PY, 1.0)]),
    "t0": (0.0, [(-PY, 1.0)]),
    "tpi": (math.pi, [(-PY, 1.0)]),
    "tpi2": (math.pi / 2, [(-PY, 1.0)]),
    "comb": (math.pi / 2, None),
}


def ideal_mzi(theta):
    """理想 MZI：C=[[1,i],[i,1]]/√2，θ 在上臂（索引 0＝下 in1/out1，1＝上 in2/out2）。"""
    C = np.array([[1, 1j], [1j, 1]]) / np.sqrt(2)
    return C @ np.diag([1, np.exp(1j * theta)]) @ C


def ideal_alpha(theta=math.pi / 2):
    """in1、in2 等幅輸入時，讓光全部合到 out1 的 in2 相對相位 α。"""
    M = ideal_mzi(theta)
    al = np.linspace(0, 2 * np.pi, 3601)
    p0 = [abs((M @ np.array([1, np.exp(1j * a)]) / np.sqrt(2))[0]) ** 2 for a in al]
    return float(al[int(np.argmax(p0))])


def run(case):
    import meep as mp
    t0 = time.time()
    theta, srcs = CASES[case]
    alpha = None
    if srcs is None:
        alpha = ideal_alpha(theta)
        srcs = [(-PY, 1 / np.sqrt(2)), (+PY, np.exp(1j * alpha) / np.sqrt(2))]
    xm, arms, (XMIN, XMAX) = layout(case)
    YMAX = (ARM_HALF if arms else MMI["body_width_um"] / 2) + 3.0
    core = mp.Medium(index=N_CORE)
    G = gamma_lateral()
    dn = (theta or 0.0) / (2 * np.pi / LAM * G * ARM_L)
    hot = mp.Medium(index=N_CORE + dn)
    V = lambda a: [mp.Vector3(float(x), float(y)) for x, y in a]
    ext = DPML + 1.0
    geo = []
    for x0 in xm:
        geo += [mp.Prism(V(clean_poly(p) + [x0, 0]), height=mp.inf, material=core) for p in MMI["core_polygons_um"]]
    for s in (+1, -1):
        geo.append(mp.Block(size=mp.Vector3(X_IN - XMIN + ext, WG, mp.inf),
                            center=mp.Vector3((XMIN - ext + X_IN) / 2, s * PY), material=core))
        xo = xm[-1] + X_OUT
        geo.append(mp.Block(size=mp.Vector3(XMAX + ext - xo, WG, mp.inf),
                            center=mp.Vector3((xo + XMAX + ext) / 2, s * PY), material=core))
    for a in arms:
        if a[0] == "sb":
            geo.append(mp.Prism(V(clean_poly(ribbon(a[1], WG))), height=mp.inf, material=core))
    for a in arms:          # 臂最後放，上臂的 hot 覆蓋重疊處
        if a[0] == "arm":
            (xa, ya), (xb, _) = a[1]
            geo.append(mp.Block(size=mp.Vector3(xb - xa, WG, mp.inf), center=mp.Vector3((xa + xb) / 2, ya),
                                material=hot if a[2] > 0 else core))
    sx, sy = (XMAX - XMIN) + 2 * DPML, 2 * YMAX + 2 * DPML
    sources = [mp.EigenModeSource(mp.ContinuousSource(1 / LAM, width=20), center=mp.Vector3(XMIN + 1.0, y),
                                  size=mp.Vector3(0, 1.8), eig_band=1, eig_parity=mp.EVEN_Z, direction=mp.X,
                                  amplitude=complex(amp)) for y, amp in srcs]
    sim = mp.Simulation(cell_size=mp.Vector3(sx, sy), geometry_center=mp.Vector3((XMIN + XMAX) / 2, 0),
                        geometry=geo, sources=sources, boundary_layers=[mp.PML(DPML)], resolution=RES,
                        default_material=mp.Medium(index=N_CLAD), force_complex_fields=True)
    sim.run(until=(XMAX - XMIN) * N_CORE * 1.4 + 120)
    fr = lambda x, y: mp.FluxRegion(center=mp.Vector3(x, y), size=mp.Vector3(0, 1.8))
    f_in = [sim.add_flux(1 / LAM, 0, 1, fr(XMIN + 3.0, s * PY)) for s in (-1, +1)]
    f_o = [sim.add_flux(1 / LAM, 0, 1, fr(XMAX - 3.0, s * PY)) for s in (-1, +1)]
    sim.run(until=20 * LAM)
    pin = sum(mp.get_fluxes(f)[0] for f in f_in)
    po = [mp.get_fluxes(f)[0] / pin for f in f_o]
    I = np.abs(np.asarray(sim.get_array(component=mp.Ex))) ** 2 + np.abs(np.asarray(sim.get_array(component=mp.Ey))) ** 2
    if not mp.am_master():
        return
    ideal = None
    if theta is not None:
        vin = np.array([0, 0], complex)
        for y, amp in srcs:
            vin[0 if y < 0 else 1] = amp
        ideal = (np.abs(ideal_mzi(theta) @ vin) ** 2).tolist()
    info = dict(case=case, theta=theta, alpha=alpha, sources=[[y, [complex(a).real, complex(a).imag]] for y, a in srcs],
                p_out=[float(p) for p in po], p_total=float(sum(po)), ideal_p_out=ideal,
                n_core=N_CORE, n_clad=N_CLAD, gamma=G, dn=dn, arm_L=ARM_L, res=RES,
                mmi_origins=xm, x_range=[XMIN, XMAX], y_half=YMAX, ext=[XMIN - DPML, XMAX + DPML, -sy / 2, sy / 2],
                meep=mp.__version__, runtime_s=round(time.time() - t0, 1))
    if not TAG:
        np.savez_compressed(os.path.join(OUT, f"field_{case}.npz"), I=I.astype(np.float32), ext=np.array(info["ext"]))
    json.dump(info, open(os.path.join(OUT, f"field_{case}{TAG}.json"), "w"), indent=1)
    print(f"{case}: out1 {po[0]:.4f} out2 {po[1]:.4f} total {sum(po):.4f} ideal {ideal} ({info['runtime_s']} s)", flush=True)


if __name__ == "__main__":
    run(sys.argv[1])
