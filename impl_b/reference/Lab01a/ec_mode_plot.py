# -*- coding: utf-8 -*-
"""
邊緣耦合器尖端截面的模場圖（femwell，1550 nm、TE）：
  (a) 220 nm strip 0.40 µm（晶片內波導）  (b) 220 nm 尖端 0.35 µm（GDS 3 最小線寬）  (c) 100 nm 薄矽尖端 0.25 µm（本設計）
每張圖疊上 UHNA7（MFD 3.2 µm）與 SMF-28（MFD 10.4 µm）的 1/e² 強度輪廓（光纖中心放在最佳垂直位置）。
輸出：figures/ec_tip_modes.png、out/ec_mode_plot.log
執行：conda run -p <device_sim> python ec_mode_plot.py
"""
import os
import numpy as np
from shapely.geometry import box
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import ec_fau_eval as E

E.MESH = os.path.join(E.OUT, "_ecf_plot.msh")
FIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "DejaVu Sans"]; plt.rcParams["axes.unicode_minus"] = False
CASES = [("(a) 220 nm × 0.40 µm（晶片內 strip）", 0.40, E.H), ("(b) 220 nm × 0.35 µm（GDS 3 最小線寬）", 0.35, E.H),
         ("(c) 100 nm × 0.25 µm（本設計薄矽尖端）", 0.25, E.H_THIN)]


def main():
    log = open(os.path.join(E.OUT, "ec_mode_plot.log"), "w", encoding="utf-8")
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.6))
    xs, ys = np.linspace(-5, 5, 301), np.linspace(-3.0, 2.5, 166)
    XX, YY = np.meshgrid(xs, ys)
    for ax, (title, w, t) in zip(axs, CASES):
        be, eps = E.build([box(-w / 2, 0, w / 2, t)])
        m, frac, Ex, X, dA = E.pick(be, eps, 1.46 + (2.2 if t > 0.15 else 0.5) * w)
        b2, I2 = m.calculate_intensity()
        I = (b2.probes(np.vstack([XX.ravel(), YY.ravel()])) @ I2).reshape(XX.shape)
        I = np.sqrt(np.clip(I / I.max(), 0, None))        # 顯示 |E|（振幅）：較能看出模場擴散範圍
        fx, fy, yc = E.mode_size(Ex, X, dA)
        u = E.overlap(Ex, X, dA, 3.2); s = E.overlap(Ex, X, dA, 10.4)
        ax.imshow(I, extent=[xs[0], xs[-1], ys[0], ys[-1]], origin="lower", cmap="inferno", aspect="equal", vmin=0, vmax=1)
        ax.add_patch(plt.Rectangle((-w / 2, 0), w, t, fill=False, ec="c", lw=1))
        for yy, c in ((0.0, "w"), (-E.T_BOX, "0.6"), (E.T_TOX, "w")):
            ax.axhline(yy, color=c, lw=0.6, ls=":")
        th = np.linspace(0, 2 * np.pi, 200)
        for mfd, (eta, y0), col, lab in ((3.2, u, "lime", "UHNA7"), (10.4, s, "deepskyblue", "SMF-28")):
            ax.plot(mfd / 2 * np.cos(th), y0 + mfd / 2 * np.sin(th), color=col, lw=1.2, ls="--",
                    label="%s 1/e²（%.2f dB）" % (lab, E.db(eta)))
        ax.set_xlim(xs[0], xs[-1]); ax.set_ylim(ys[0], ys[-1])
        ax.set_title(title + "\n模場 %.2f × %.2f µm" % (fx, fy), fontsize=10)
        ax.set_xlabel("x [µm]"); ax.set_ylabel("y [µm]（0 = Si 底面）")
        ax.legend(fontsize=7.5, loc="lower right")
        ax.text(-4.8, E.T_TOX + 0.15, "空氣", color="w", fontsize=8); ax.text(-4.8, 0.3, "上包覆 SiO2", color="w", fontsize=8)
        ax.text(-4.8, -1.0, "BOX 2 µm", color="w", fontsize=8)
        t_ = "%s：模場 %.2f×%.2f µm、UHNA7 %.2f dB、SMF-28 %.2f dB" % (title, fx, fy, E.db(u[0]), E.db(s[0]))
        print(t_); log.write(t_ + "\n")
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "ec_tip_modes.png"), dpi=130); plt.close(fig)
    print("圖已存: figures/ec_tip_modes.png")


if __name__ == "__main__":
    main()
