# -*- coding: utf-8 -*-
"""
§6.19b 論文風格 MMI 光場傳播圖（時間平均 |E|²，Meep 2D-EIM，CW @1550 nm）。

與 meep_mmi_field.py 的差異（為何舊圖是「斑點狀」）：
  * 舊圖取 CW 某一瞬間的 |Hz|² → 含 cos²(ωt−kx) 的時間振盪條紋；
    論文/BPM 圖是『時間平均強度』。此處用 force_complex_fields=True，複數 CW 場的 |Ex|²+|Ey|² 即時間平均包絡。
  * 端點波導必須延伸穿過 PML，否則截斷端面反射 → λ/2n 駐波條紋（並低估穿透率）。
  * 舊圖用 gdsfactory 預設的小 MMI(2.5×5.5 µm)；此處用論文常見的寬 MMI + taper：
      (a) 1×2 MMI（仿參考圖）：W=6 µm，掃 L 取對稱自成像長度 (≈3Lπ/8)，輸出在 ±W/4
      (b) 本晶片實際的 CORNERSTONE SOI220 2×2 MMI：W=6、L=42.5、taper 20 µm(0.45→1.5)、埠 ±1.015
  * 2D 有效折射率法(EIM)：核心 = 220 nm Si slab TE0 的 n_eff，包覆 = SiO2。

執行(WSL Ubuntu, conda meep 環境)：
  wsl -d Ubuntu -u hans -- ~/miniforge3/bin/conda run --no-capture-output -n meep \
      python /mnt/c/EDA/lab01a/meep_mmi_paper.py
"""
import os
import numpy as np
import meep as mp
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
LAM = 1.55
FCEN = 1.0 / LAM
N_CORE = 2.85          # 220 nm Si slab TE0 @1550 的 n_eff（2D-EIM 核心）
N_CLAD = 1.444         # SiO2
RES = 20               # px/µm
DPML = 1.5
CORE = mp.Medium(index=N_CORE)
EXT = DPML + 2.0        # 端點波導延伸穿過 PML（否則截斷端面反射 → 駐波條紋）


def taper(x0, x1, yc, w0, w1):
    """x0→x1 線性 taper（寬 w0→w1），中心 y=yc。"""
    pts = [mp.Vector3(x0, yc - w0 / 2), mp.Vector3(x1, yc - w1 / 2),
           mp.Vector3(x1, yc + w1 / 2), mp.Vector3(x0, yc + w0 / 2)]
    return mp.Prism(pts, height=mp.inf, material=CORE)


def rect(x0, x1, yc, w):
    return mp.Block(size=mp.Vector3(x1 - x0, w, mp.inf),
                    center=mp.Vector3((x0 + x1) / 2, yc), material=CORE)


# ---------------- 元件定義（x: 元件座標, MMI 本體 0..L） ----------------
def dev_1x2(L, W=6.0, wg=0.5, tw=1.5, tin=5.0, tout=10.0, lin=10.0, lout=5.0):
    """1×2 對稱干涉 MMI；回傳 (geometry, x_min, x_max, source(x,y), outputs[(x,y,w)])。"""
    yo = W / 4
    g = [rect(-tin - lin - EXT, -tin, 0, wg), taper(-tin, 0, 0, wg, tw), rect(0, L, 0, W)]
    for s in (+1, -1):
        g += [taper(L, L + tout, s * yo, tw, wg), rect(L + tout, L + tout + lout + EXT, s * yo, wg)]
    return g, -tin - lin, L + tout + lout, (-tin - lin + 2.0, 0.0), [(L + tout + 2.0, s * yo, wg) for s in (+1, -1)]


def dev_cs2x2(W=6.0, L=42.5, wg=0.45, tw=1.5, tl=20.0, yp=1.015, lin=4.0, lout=4.0):
    """CORNERSTONE SOI220 2×2 MMI（尺寸取自 Luceda PDK cell）；光從 in1(y=-yp) 射入。"""
    g = [rect(0, L, 0, W)]
    for s in (+1, -1):
        g += [rect(-tl - lin - EXT, -tl, s * yp, wg), taper(-tl, 0, s * yp, wg, tw),
              taper(L, L + tl, s * yp, tw, wg), rect(L + tl, L + tl + lout + EXT, s * yp, wg)]
    return g, -tl - lin, L + tl + lout, (-tl - lin + 1.5, -yp), [(L + tl + 2.0, s * yp, wg) for s in (-1, +1)]


# ---------------- CW 模擬 → 時間平均 |E|²（複數場包絡）+ flux 功率 ----------------
def run_cw(geom, xmin, xmax, src, outs, half_h=4.5, settle=None):
    """force_complex_fields: CW 場為 E·e^{-iωt}，任一時刻 |E|² 即時間平均包絡（無 cos² 條紋）。
       穩態後才加 flux 監測（DFT 只累積穩態），回傳 (I, eps, ext, P_in, [P_out...])。"""
    sx = (xmax - xmin) + 2 * DPML
    sy = 2 * half_h + 2 * DPML
    xc = (xmin + xmax) / 2
    sxs, sys_ = src
    source = mp.EigenModeSource(
        mp.ContinuousSource(FCEN, width=20),
        center=mp.Vector3(sxs, sys_), size=mp.Vector3(0, 3.0),
        eig_band=1, eig_parity=mp.EVEN_Z, direction=mp.X)   # 2D: EVEN_Z = TE (Ex,Ey,Hz)
    sim = mp.Simulation(cell_size=mp.Vector3(sx, sy), geometry_center=mp.Vector3(xc, 0),
                        geometry=geom, sources=[source],
                        boundary_layers=[mp.PML(DPML)], resolution=RES,
                        default_material=mp.Medium(index=N_CLAD),
                        force_complex_fields=True)
    t_settle = settle or (sx * N_CORE * 1.6 + 60)      # 光走完全長並達穩態
    sim.run(until=t_settle)
    fr = lambda x, y: mp.FluxRegion(center=mp.Vector3(x, y), size=mp.Vector3(0, 2.0))
    f_in = sim.add_flux(FCEN, 0, 1, fr(sxs + 2.0, sys_))
    f_out = [sim.add_flux(FCEN, 0, 1, fr(x, y)) for (x, y, w) in outs]
    sim.run(until=20 / FCEN)                            # 穩態下累積 20 個週期
    p_in = mp.get_fluxes(f_in)[0]
    p_out = [mp.get_fluxes(f)[0] for f in f_out]
    ex = np.asarray(sim.get_array(component=mp.Ex))
    ey = np.asarray(sim.get_array(component=mp.Ey))
    I = np.abs(ex) ** 2 + np.abs(ey) ** 2
    eps = np.real(np.asarray(sim.get_array(component=mp.Dielectric)))
    ext = [xmin - DPML, xmax + DPML, -sy / 2, sy / 2]
    return I, eps, ext, p_in, p_out


def plot(ax, I, ext, title, xlim=None, ylim=(-4, 4), norm=1.0):
    Z = I / norm
    im = ax.imshow(Z.T, origin="lower", extent=ext, cmap="jet", vmin=0, vmax=0.5,
                   aspect="auto", interpolation="bilinear")
    ax.set_xlim(*(xlim or ext[:2])); ax.set_ylim(*ylim)
    ax.set_xlabel("x (microns)"); ax.set_ylabel("y (microns)")
    ax.set_title(title, fontsize=12)
    return im


def main():
    log = open(os.path.join(OUT, "meep_mmi_paper.log"), "w")

    def P(*a):
        s = " ".join(str(x) for x in a); print(s); log.write(s + "\n"); log.flush()

    P("=== §6.19b 論文風格 MMI 光場傳播圖 (Meep 2D-EIM, CW 1550 nm, 時間平均 |E|² = 複數 CW 場包絡) ===")
    P(f"n_core(EIM)={N_CORE}, n_clad={N_CLAD}, res={RES}/µm")

    # ---- (a) 1×2：掃 L 找對稱自成像長度 ----
    W = 6.0
    Lpi = 4 * N_CORE * (W + 0.3) ** 2 / (3 * LAM)
    P(f"(a) 1x2 MMI W={W}: Lπ≈{Lpi:.1f} µm → 理論 L=3Lπ/8≈{3 * Lpi / 8:.1f} µm")
    def input_peak(I, ext, src):
        ix = int((src[0] + 3 - ext[0]) / (ext[1] - ext[0]) * (I.shape[0] - 1))
        return I[ix].max()

    best = None
    for L in np.arange(29.0, 33.01, 1.0):     # 先前 29–37 寬掃峰值在 ~31
        g, xmin, xmax, src, outs = dev_1x2(L)
        _, _, _, pin, po = run_cw(g, xmin, xmax, src, outs)
        T = sum(po) / pin
        P(f"   L={L:5.1f}  T={T:.3f} ({10 * np.log10(T):+.2f} dB)  split(下)={po[1] / sum(po):.3f}")
        if best is None or T > best[1]:
            best = (L, T)
    for L in (best[0] - 0.5, best[0] - 0.25, best[0] + 0.25, best[0] + 0.5):
        g, xmin, xmax, src, outs = dev_1x2(L)
        _, _, _, pin, po = run_cw(g, xmin, xmax, src, outs)
        T = sum(po) / pin
        P(f"   L={L:5.2f}  T={T:.3f}")
        if T > best[1]:
            best = (L, T)
    Lb = best[0]
    g, xmin, xmax, src, outs = dev_1x2(Lb)
    Ia, epsa, exta, pin, po = run_cw(g, xmin, xmax, src, outs)
    na = input_peak(Ia, exta, src)
    T = sum(po) / pin
    P(f"(a) 最佳 L={Lb:.2f} µm: T={T:.3f} (超額損耗 {-10 * np.log10(T):.2f} dB), 分光={po[0] / sum(po):.3f}/{po[1] / sum(po):.3f}")

    # ---- (b) CORNERSTONE 2×2 ----
    g, xmin, xmax, src, outs = dev_cs2x2()
    Ib, epsb, extb, pin, po = run_cw(g, xmin, xmax, src, outs)
    nb = input_peak(Ib, extb, src)
    T = sum(po) / pin
    P(f"(b) CORNERSTONE 2x2 (W=6, L=42.5), in1 入射: T={T:.3f} (超額損耗 {-10 * np.log10(T):.2f} dB), "
      f"bar(out1)={po[0] / sum(po):.3f}, cross(out2)={po[1] / sum(po):.3f}")
    P("    註: 2D-EIM 近似; 自成像長度與 3D 實際元件略有差異（PDK 依 3D 設計 L=42.5）。")

    # ---- 圖 ----
    for tag, I, ext, nrm, ttl, xl in [
        ("a", Ia, exta, na, f"E intensity — 1x2 MMI (W=6 µm, L={Lb:.1f} µm)", (-10, Lb + 12)),
        ("b", Ib, extb, nb, "E intensity — CORNERSTONE 2x2 MMI (W=6 µm, L=42.5 µm)", (-24, 66.5)),
    ]:
        fig, ax = plt.subplots(figsize=(7.6 if tag == "a" else 11, 5.2))
        im = plot(ax, I, ext, ttl, xlim=xl, norm=nrm)
        cb = fig.colorbar(im, ax=ax, ticks=np.linspace(0, 0.5, 7))
        cb.ax.set_yticklabels([f"{v:.3g}" for v in np.linspace(0, 0.5, 7)])
        fn = os.path.join(OUT, f"meep_mmi_paper_{tag}.png")
        fig.savefig(fn, dpi=140, bbox_inches="tight"); plt.close(fig)
        P("圖已存:", os.path.relpath(fn, os.path.dirname(OUT)))
    log.close()


if __name__ == "__main__":
    main()
