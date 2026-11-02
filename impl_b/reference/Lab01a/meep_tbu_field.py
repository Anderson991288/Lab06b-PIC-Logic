# -*- coding: utf-8 -*-
"""
§6.19 完整 2×2 MZI（TBU）光場傳播圖（Meep 2D-EIM，CW 1550 nm，時間平均 |E|²）。
幾何依晶片實際元件：CORNERSTONE 2×2 MMI（主體 6×42.5 µm、taper 20 µm 0.45→1.5 µm、埠 ±1.015 µm）×2、
臂 S 彎用佈局的 Euler 形狀（out/bend_shapes.json，拉開到 ±15 µm）。
為縮短模擬，臂直段取 20 µm（實際 184 µm），θ 以上臂核心折射率 +Δn 等效（Δn = θ·λ/(2π·L)）。
光由 MMI1 的 in1（y=−1.015）射入；θ=0 與 θ=π 兩狀態對照——光分別從不同輸出埠離開。
用法（WSL Ubuntu, conda meep；勿用 EDA_Server）：
  python meep_tbu_field.py run 0      # θ=0，存 out/tbu_field_0.npz
  python meep_tbu_field.py run 1      # θ=π，存 out/tbu_field_1.npz
  python meep_tbu_field.py plot       # 合成 out/meep_tbu_field.png
"""
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
LAM, N_CORE, N_CLAD = 1.55, 2.85, 1.444
RES, DPML = 16, 1.5
W, WG, TW, TL, L, YP = 6.0, 0.45, 1.5, 20.0, 42.5, 1.015
ARM_L, ARM_HALF = 20.0, 15.0
LEAD = 10.0
GAMMA = 1.07          # 實際相移 / 以核心 Δn 估算的相移：未補償時 θ=π 殘光 1.2%（相差 0.22 rad），θ=π/2 試算得 61:39 → 相移偏多 ~7%
                      # （先前誤判為偏少而用 0.93，(b) 得 0.47/0.30）；除以 GAMMA 使 θ 準確


def _ideal_alpha():
    """理想 MZI（C=[[1,i],[i,1]]/√2、θ 在上臂）θ=π/2 時，讓 in1+in2（等幅）全部合到單一輸出的 in2 相對相位 α。"""
    C = np.array([[1, 1j], [1j, 1]]) / np.sqrt(2)
    M = C @ np.diag([1, np.exp(1j * np.pi / 2)]) @ C          # 索引 0 = 下（in1/out1）、1 = 上（in2/out2）
    al = np.linspace(0, 2 * np.pi, 3601)
    p0 = [abs((M @ np.array([1, np.exp(1j * a)]) / np.sqrt(2))[0]) ** 2 for a in al]
    return float(al[int(np.argmax(p0))])


# 報告用的三種運作狀態（＋θ=π 參考）：(名稱, θ, [(埠 y, 複數振幅)...], 標題)
CASES = [
    ("in1_t0", 0.0, [(-1.015, 1.0)], "(a) in1 only, θ = 0  →  switched to out2 (cross)"),
    ("in1_tpi", np.pi, [(-1.015, 1.0)], "θ = π  →  out1 (bar)"),
    ("in1_tpi2", np.pi / 2, [(-1.015, 1.0)], "(b) in1 only, θ = π/2  →  split to out1 + out2 (50:50)"),
    ("in12_tpi2", np.pi / 2, None, "(c) in1 + in2 (coherent), θ = π/2  →  combined into one output"),
]
X_M1 = 0.0
X_SB1 = X_M1 + L + TL                 # 第一組 S 彎起點（MMI1 輸出 taper 末端）
SB = json.load(open(os.path.join(OUT, "bend_shapes.json")))["shapes"]["euler"]["points"]
SB = np.array(SB)                     # 起點 (0,0) → 終點 (15, 13.985)
SB_DX, SB_DY = SB[-1]
X_ARM0 = X_SB1 + SB_DX
X_ARM1 = X_ARM0 + ARM_L
X_SB2 = X_ARM1 + SB_DX
X_M2 = X_SB2 + TL
X_END = X_M2 + L + TL
XMIN, XMAX = X_M1 - TL - LEAD, X_END + LEAD
YMAX = ARM_HALF + 3.0


def ribbon(pts, w):
    pts = np.asarray(pts, float)
    keep = np.r_[True, np.hypot(*np.diff(pts, axis=0).T) > 1e-6]      # 去除重複點（IPKISS 形狀可能含重複頂點 → 切線 0/0）
    pts = pts[keep]
    t = np.gradient(pts, axis=0)
    t /= np.linalg.norm(t, axis=1)[:, None]
    nrm = np.stack([-t[:, 1], t[:, 0]], 1)
    return np.vstack([pts + nrm * w / 2, (pts - nrm * w / 2)[::-1]])


def geometry(theta):
    import meep as mp
    core = mp.Medium(index=N_CORE)
    dn = theta * LAM / (2 * np.pi * ARM_L) / GAMMA                      # 模場只有 Γ 在核心內 → Δn_core 放大 1/Γ
    hot = mp.Medium(index=N_CORE + dn)
    V = lambda a: [mp.Vector3(*p) for p in a]

    def taper(x0, x1, yc, w0, w1):
        return mp.Prism(V([(x0, yc - w0 / 2), (x1, yc - w1 / 2), (x1, yc + w1 / 2), (x0, yc + w0 / 2)]), height=mp.inf, material=core)

    def rect(x0, x1, yc, w, mat=core):
        return mp.Block(size=mp.Vector3(x1 - x0, w, mp.inf), center=mp.Vector3((x0 + x1) / 2, yc), material=mat)

    ext = DPML + 1.0
    g = []
    for xm in (X_M1, X_M2):
        g.append(rect(xm, xm + L, 0, W))
        for s in (+1, -1):
            g += [taper(xm - TL, xm, s * YP, WG, TW), taper(xm + L, xm + L + TL, s * YP, TW, WG)]
    for s in (+1, -1):
        g.append(rect(XMIN - ext, X_M1 - TL, s * YP, WG))                    # 輸入導引（兩埠，in2 不打光）
        g.append(rect(X_END, XMAX + ext, s * YP, WG))                        # 輸出導引
        up = SB * [1, s] + [X_SB1, s * YP]                                    # S 彎拉開
        dn_ = (SB[::-1] * [-1, 1] + [SB_DX, 0]) * [1, s] + [X_ARM1, s * YP]   # S 彎收回（鏡像）
        g += [mp.Prism(V(ribbon(up, WG)), height=mp.inf, material=core),
              mp.Prism(V(ribbon(dn_, WG)), height=mp.inf, material=core)]
        g.append(rect(X_ARM0 - 0.05, X_ARM1 + 0.05, s * ARM_HALF, WG, hot if s > 0 else core))
    return g


def run(k):
    import meep as mp
    name, theta, srcs, _ = CASES[k]
    if srcs is None:
        a = _ideal_alpha()
        srcs = [(-YP, 1 / np.sqrt(2)), (+YP, np.exp(1j * a) / np.sqrt(2))]
    sx, sy = (XMAX - XMIN) + 2 * DPML, 2 * YMAX + 2 * DPML
    sources = [mp.EigenModeSource(mp.ContinuousSource(1 / LAM, width=20), center=mp.Vector3(XMIN + 1.0, y),
                                  size=mp.Vector3(0, 1.8), eig_band=1, eig_parity=mp.EVEN_Z, direction=mp.X,
                                  amplitude=complex(amp)) for y, amp in srcs]
    sim = mp.Simulation(cell_size=mp.Vector3(sx, sy), geometry_center=mp.Vector3((XMIN + XMAX) / 2, 0),
                        geometry=geometry(theta), sources=sources, boundary_layers=[mp.PML(DPML)],
                        resolution=RES, default_material=mp.Medium(index=N_CLAD), force_complex_fields=True)
    sim.run(until=(XMAX - XMIN) * N_CORE * 1.4 + 120)
    fr = lambda x, y: mp.FluxRegion(center=mp.Vector3(x, y), size=mp.Vector3(0, 1.8))
    f_in = [sim.add_flux(1 / LAM, 0, 1, fr(XMIN + 3.0, s * YP)) for s in (-1, +1)]
    f_o = [sim.add_flux(1 / LAM, 0, 1, fr(XMAX - 3.0, s * YP)) for s in (-1, +1)]
    sim.run(until=20 * LAM)
    pin = sum(mp.get_fluxes(f)[0] for f in f_in)
    po = [mp.get_fluxes(f)[0] / pin for f in f_o]
    I = np.abs(np.asarray(sim.get_array(component=mp.Ex))) ** 2 + np.abs(np.asarray(sim.get_array(component=mp.Ey))) ** 2
    if not mp.am_master():                       # MPI 平行時只由主程序存檔
        return
    np.savez_compressed(os.path.join(OUT, "tbu_field_%s.npz" % name), I=I.astype(np.float32),
                        ext=np.array([XMIN - DPML, XMAX + DPML, -sy / 2, sy / 2]), theta=theta, p_out=np.array(po),
                        n_src=len(srcs))
    print("%s: out1(y=-%.3f)=%.3f  out2(y=+%.3f)=%.3f" % (name, YP, po[0], YP, po[1]), flush=True)


def plot():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    show = [0, 2, 3]
    fig, axs = plt.subplots(len(show), 1, figsize=(13, 10.8), sharex=True)
    for ax, k in zip(axs, show):
        name, theta, srcs, title = CASES[k]
        d = np.load(os.path.join(OUT, "tbu_field_%s.npz" % name))
        I, ext, po = d["I"], d["ext"], d["p_out"]
        # 以「單一輸入埠、全功率」的波導峰值歸一（兩埠同時輸入時每埠為 1/2 功率）
        ix = int((XMIN + 3.0 - ext[0]) / (ext[1] - ext[0]) * (I.shape[0] - 1))
        norm = I[ix].max() * int(d["n_src"])
        im = ax.imshow(I.T / norm, origin="lower", extent=ext, cmap="jet", vmin=0, vmax=0.5, aspect="auto", interpolation="bilinear")
        ax.set_xlim(XMIN, XMAX); ax.set_ylim(-YMAX, YMAX); ax.set_ylabel("y (microns)")
        ax.set_title("E intensity — %s:   out1 %.2f / out2 %.2f" % (title, po[0], po[1]), fontsize=11.5)
        ax.text(XMIN + 1, -YP - 2.6, "in1", color="w", fontsize=9)
        ax.text(XMIN + 1, YP + 1.4, "in2", color="w", fontsize=9)
        ax.text(XMAX - 9, -YP - 2.6, "out1", color="w", fontsize=9)
        ax.text(XMAX - 9, YP + 1.4, "out2", color="w", fontsize=9)
        ax.text((X_ARM0 + X_ARM1) / 2, ARM_HALF + 1.2, "θ arm", color="w", ha="center", fontsize=8)
        for xm in (X_M1, X_M2):
            ax.text(xm + L / 2, -W / 2 - 1.8, "2×2 MMI", color="w", ha="center", va="top", fontsize=8)
    axs[-1].set_xlabel("x (microns)")
    fig.colorbar(im, ax=axs, shrink=0.85)
    fig.suptitle("2×2 MZI operating states — switching, 50:50 splitting, two-input combining (CORNERSTONE MMI ×2)", fontsize=12)
    fig.savefig(os.path.join(OUT, "meep_tbu_field.png"), dpi=130, bbox_inches="tight")
    print("saved out/meep_tbu_field.png")


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]))
    else:
        plot()
