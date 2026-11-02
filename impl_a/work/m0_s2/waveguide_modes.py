"""M0 s2（E2）：femwell 算 220 nm SOI strip 波導的模態，並求 Meep 2D 光場模擬要用的有效折射率。

用途：
  1. 0.45×0.22 µm strip（本課程 MZI 與 PDK MMI 埠的寬度）在 1550 nm 的 TE0：n_eff、網格收斂、群折射率 n_g。
  2. 寬度掃描 0.30–0.80 µm：TE0、TE1 的 n_eff，找單模上限（TE1 n_eff 超過包覆層 1.444 的寬度）。
  3. 有效折射率法（EIM）：220 nm 平板 TE0 的 n_slab（解析解）＝ Meep 2D 的核心折射率；
     再用 n_slab 解 0.45 µm 橫向平板，與 femwell 3D 結果比較，量化 2D 近似的誤差。
輸入：無（材料用固定折射率 Si 3.476、SiO2 1.444，與 Meep 相同）。
輸出：out/modes.json；course/figures/m0_s2/wg_modes.png。
執行（device_sim 必須經 conda run）：
  conda run --no-capture-output -p <device_sim> python C:\\LAB\\Lab06b\\impl_a\\work\\m0_s2\\waveguide_modes.py   （約 2 分鐘）
"""
import os
import sys
import json
import time
from collections import OrderedDict
from pathlib import Path

for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[v] = "1"
import numpy as np                                    # noqa: E402
import matplotlib                                     # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                       # noqa: E402
from shapely.geometry import box                      # noqa: E402
from skfem import Basis, ElementTriP0                 # noqa: E402
from skfem.io.meshio import from_meshio               # noqa: E402
from skfem.visuals.matplotlib import plot as skplot   # noqa: E402
from femwell.mesh import mesh_from_OrderedDict        # noqa: E402
from femwell.maxwell.waveguide import compute_modes   # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass
plt.rcParams["font.family"] = ["Microsoft JhengHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
FIG = ROOT / "course" / "figures" / "m0_s2"
FIG.mkdir(parents=True, exist_ok=True)

W, T, LAM = 0.45, 0.22, 1.55
N_SI, N_OX = 3.476, 1.444
X_CLAD, Y_CLAD = 2.5, 2.0
MESHES = [(0.03, 0.3), (0.02, 0.2), (0.01, 0.1)]
MESH_USE = (0.02, 0.2)
WLS = np.round(np.linspace(1.53, 1.57, 5), 4)
WIDTHS = np.round(np.arange(0.30, 0.801, 0.05), 3)
GUIDE_MARGIN = 0.01        # n_eff 至少高出 SiO2 這麼多才算「明確導光」


def basis(w, mesh):
    polys = OrderedDict(core=box(-w / 2, 0, w / 2, T), clad=box(-X_CLAD - w / 2, -Y_CLAD, X_CLAD + w / 2, T + Y_CLAD))
    m = from_meshio(mesh_from_OrderedDict(polys, {"core": {"resolution": mesh[0], "distance": 1.0}},
                                          default_resolution_max=mesh[1], filename=str(OUT / "_wg.msh")))
    return Basis(m, ElementTriP0())


def solve(w, lam=LAM, mesh=MESH_USE, num=2, b0=None):
    b0 = b0 or basis(w, mesh)
    eps = b0.zeros(dtype=complex)
    eps[b0.get_dofs(elements="core")] = N_SI ** 2
    eps[b0.get_dofs(elements="clad")] = N_OX ** 2
    modes = compute_modes(b0, eps, wavelength=lam, num_modes=num, order=2, n_guess=N_SI)
    te = sorted([m for m in modes if m.te_fraction > 0.5], key=lambda m: -np.real(m.n_eff))
    return te, b0


def slab_neff(n1, n2, d, lam, tm=False):
    """對稱平板的基模 n_eff（偶模）。TE：tan(κd/2)=γ/κ；TM：tan(κd/2)=(n1/n2)²γ/κ。二分法求根。"""
    k0 = 2 * np.pi / lam
    r = (n1 / n2) ** 2 if tm else 1.0

    def f(n):
        kap, gam = k0 * np.sqrt(n1 ** 2 - n ** 2), k0 * np.sqrt(n ** 2 - n2 ** 2)
        return np.tan(kap * d / 2) - r * gam / kap

    lo = max(n2 + 1e-9, np.sqrt(max(n1 ** 2 - (np.pi / (k0 * d)) ** 2, n2 ** 2)) + 1e-9)   # 偶模基模在第一個 tan 分支內
    hi = n1 - 1e-9
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def main():
    t0 = time.perf_counter()
    res = {"step": "M0 s2 E2", "tool": "femwell", "date": time.strftime("%Y-%m-%d"),
           "geometry_um": dict(W=W, T=T, x_clad=X_CLAD, y_clad=Y_CLAD), "materials": dict(Si=N_SI, SiO2=N_OX),
           "wavelength_um": LAM}

    conv = []
    for mesh in MESHES:
        te, b0 = solve(W, mesh=mesh)
        conv.append(dict(res_core=mesh[0], res_max=mesh[1], ndof=int(b0.N), n_eff=float(np.real(te[0].n_eff))))
        print(f"網格 {mesh}: ndof {b0.N:6d}  TE0 n_eff {conv[-1]['n_eff']:.5f}")
    res["mesh_convergence"] = conv

    b0 = basis(W, MESH_USE)
    neff_l = []
    for lam in WLS:
        te, _ = solve(W, lam=lam, b0=b0)
        neff_l.append(float(np.real(te[0].n_eff)))
    p = np.polyfit(WLS, neff_l, 2)
    ng = float(np.polyval(p, LAM) - LAM * np.polyval(np.polyder(p), LAM))
    te0, _ = solve(W, b0=b0)
    m0 = te0[0]
    res["te0"] = dict(n_eff=float(np.real(m0.n_eff)), te_fraction=float(m0.te_fraction), n_g=ng,
                      wl_um=WLS.tolist(), n_eff_vs_wl=neff_l)
    print(f"TE0 (W={W}): n_eff {res['te0']['n_eff']:.4f}  n_g {ng:.3f}  TE 比例 {m0.te_fraction:.3f}")

    sweep = []
    for w in WIDTHS:
        te, _ = solve(float(w), num=4)
        n = [float(np.real(m.n_eff)) for m in te if np.real(m.n_eff) > N_OX]
        sweep.append(dict(width_um=float(w), te_n_eff=n))
        print(f"寬 {w:.2f} µm：TE 模 n_eff {['%.4f' % x for x in n]}")
    res["width_sweep"] = sweep
    # TE1 剛越過截止時（n_eff 只比 SiO2 高一點）模場大半在包覆層，彎道一下就漏掉；以 GUIDE_MARGIN 區分「明確導光」
    strong = lambda s: [n for n in s["te_n_eff"] if n > N_OX + GUIDE_MARGIN]
    res["guide_margin"] = GUIDE_MARGIN
    res["single_mode_max_width_um"] = max([s["width_um"] for s in sweep if len(strong(s)) < 2], default=None)
    res["first_multimode_width_um"] = min([s["width_um"] for s in sweep if len(strong(s)) >= 2], default=None)
    res["te1_at_W"] = next((s["te_n_eff"][1] for s in sweep if abs(s["width_um"] - W) < 1e-6 and len(s["te_n_eff"]) > 1), None)

    n_slab = slab_neff(N_SI, N_OX, T, LAM)
    n_eim = slab_neff(n_slab, N_OX, W, LAM, tm=True)       # 橫向：TE 模的主電場垂直於側壁 → 用 TM 平板式
    res["eim"] = dict(n_slab_TE0_220nm=n_slab, n_eim_strip=n_eim, n_femwell_strip=res["te0"]["n_eff"],
                      rel_error=(n_eim - res["te0"]["n_eff"]) / res["te0"]["n_eff"],
                      note="Meep 2D uses n_slab as core index and SiO2 1.444 as cladding")
    print(f"EIM：220 nm 平板 n_slab {n_slab:.4f}；0.45 µm 橫向 n_eim {n_eim:.4f} vs femwell {res['te0']['n_eff']:.4f}")

    fig, ax = plt.subplots(1, 2, figsize=(12, 4.4), gridspec_kw=dict(width_ratios=[1.15, 1]))
    ib, I = m0.calculate_intensity()
    skplot(ib, I / I.max(), ax=ax[0], shading="gouraud", cmap="inferno")
    ax[0].add_patch(plt.Rectangle((-W / 2, 0), W, T, fill=False, ec="w", lw=1))
    ax[0].set_xlim(-1.0, 1.0); ax[0].set_ylim(-0.5, 0.75); ax[0].set_aspect("equal")
    ax[0].set_xlabel("x (µm)"); ax[0].set_ylabel("y (µm)")
    ax[0].set_title(f"(a) TE0 光強 |E|²，0.45×0.22 µm，n_eff = {res['te0']['n_eff']:.3f}")
    for k in range(2):
        xs = [s["width_um"] for s in sweep if len(s["te_n_eff"]) > k]
        ys = [s["te_n_eff"][k] for s in sweep if len(s["te_n_eff"]) > k]
        ax[1].plot(xs, ys, "o-", label=f"TE{k}")
    ax[1].axhline(N_OX, color="gray", ls="--", lw=1); ax[1].text(0.31, N_OX + 0.02, "SiO2 1.444（低於此值不導光）", fontsize=9)
    ax[1].axvline(W, color="C3", ls=":", lw=1); ax[1].text(W + 0.01, 1.95, "本課程 0.45 µm", color="C3", fontsize=9)
    ax[1].set_xlabel("波導寬 (µm)"); ax[1].set_ylabel("n_eff"); ax[1].legend(loc="lower right")
    ax[1].set_title("(b) 寬度掃描：TE0／TE1 有效折射率"); ax[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG / "wg_modes.png", dpi=130)
    res["figs"] = ["course/figures/m0_s2/wg_modes.png"]
    res["runtime_s"] = round(time.perf_counter() - t0, 1)
    (OUT / "modes.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("寫出 out/modes.json", f"（{res['runtime_s']} s）")


if __name__ == "__main__":
    main()
