"""M1 s1：位元怎麼變成光？輸入（編碼）、混合（干涉）、讀取（功率與判定）。

步驟：
  1. 編碼：16 組 x1–x4 → B7 的 5 路輸入光場 v（R＝3），記錄每組的輸入總功率。
  2. 光場 vs 功率：單顆 MZI、θ＝π/2，兩路資料光同時輸入時，上埠功率隨 φ 在 0–2 之間變化；
     若功率可以直接相加，結果永遠是 1。
  3. 單顆 MZI 能做哪些 2 輸入邏輯：x1、x2 進一顆 MZI，讀上埠功率、單一門檻，掃 θ、φ，
     對 14 種非常數函數找最大判定餘裕。
  4. 加入參考光 R：MZI 上埠再與振幅 ρ、相位 ψ 的參考光在 50:50 耦合器合光，
     掃 θ、φ、ψ，ρ＝0.5、1、2、3，看哪些函數變成可行。
  5. 出圖：B7 輸入／混合／讀取標註圖；光場 vs 功率與函數可行性圖。
輸入：common/b7.py、common/mzi.py（無外部資料）。
輸出：out/m1_s1_result.json；course/figures/m1_s1/b7_io.png、single_mzi_logic.png。
執行：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m1_s1\\encode_logic.py
"""
import sys
import json
import math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import runtime as rt

rt.setup()
import numpy as np                      # noqa: E402
import matplotlib.pyplot as plt         # noqa: E402
from matplotlib.patches import Rectangle, FancyBboxPatch  # noqa: E402
from common import b7, mzi as Z         # noqa: E402

OUT = rt.out_dir(__file__)
X2 = [(0, 0), (1, 0), (0, 1), (1, 1)]                 # (x1, x2) 的列序
FUNCS = {"0001": "AND", "0111": "OR", "0110": "XOR", "0101": "x1", "0011": "x2",
         "0100": "x1·¬x2", "0010": "¬x1·x2",
         "1110": "NAND", "1000": "NOR", "1001": "XNOR", "1010": "¬x1", "1100": "¬x2",
         "1101": "x1+¬x2", "1011": "¬x1+x2"}            # 真值字串依 X2 列序：f(00) f(10) f(01) f(11)
N_GRID = 120                                          # θ、φ、ψ 各 120 點（3° 一格）
RHOS = [0.5, 1.0, 2.0, 3.0]
MARGIN_MIN = 1e-6


def encoding():
    rows = []
    for x in b7.ALL_BITS:
        v = b7.encode(x)
        rows.append(dict(bits=b7.bits_str(x), v=[float(a.real) for a in v], p_in=float(np.sum(np.abs(v) ** 2))))
    return rows


def mzi_upper_fields(th, ph):
    """單顆 MZI 上埠（局部索引 0）對 4 組 (x1, x2) 的輸出光場，th、ph 可為陣列。回傳形狀 (4, ...)。"""
    t00 = 1j * np.exp(1j * (ph + th / 2)) * np.sin(th / 2)
    t01 = 1j * np.exp(1j * th / 2) * np.cos(th / 2)
    return np.stack([x1 * t00 + x2 * t01 for x1, x2 in X2])


def best_margin(P, code):
    """P: (4, N) 各輸入的功率；回傳 (最大餘裕, 最佳索引, 門檻)。餘裕 = min(1 類功率) − max(0 類功率)。"""
    one = np.array([c == "1" for c in code])
    m = P[one].min(axis=0) - P[~one].max(axis=0)
    i = int(np.argmax(m))
    return float(m[i]), i, float((P[one, i].min() + P[~one, i].max()) / 2)


def scan():
    g = np.linspace(0, 2 * np.pi, N_GRID, endpoint=False)
    TH, PH = np.meshgrid(g, g, indexing="ij")
    E = mzi_upper_fields(TH.ravel(), PH.ravel())                  # (4, N²)
    res = {}
    # 單顆 MZI（不加 R）
    P = np.abs(E) ** 2
    for code, name in FUNCS.items():
        m, i, t = best_margin(P, code)
        res.setdefault(code, dict(name=name))["mzi"] = dict(
            margin=m, ok=m > MARGIN_MIN, theta_deg=math.degrees(TH.ravel()[i]), phi_deg=math.degrees(PH.ravel()[i]),
            threshold=t, p=[float(P[k, i]) for k in range(4)])
    # MZI 上埠＋參考光 ρe^{iψ}，50:50 耦合器合光
    for rho in RHOS:
        best = {c: (-np.inf, None) for c in FUNCS}
        for psi in g:
            Pr = np.abs((E + rho * np.exp(1j * psi)) / np.sqrt(2)) ** 2
            for code in FUNCS:
                m, i, t = best_margin(Pr, code)
                if m > best[code][0]:
                    best[code] = (m, dict(margin=m, ok=m > MARGIN_MIN, theta_deg=math.degrees(TH.ravel()[i]),
                                          phi_deg=math.degrees(PH.ravel()[i]), psi_deg=math.degrees(psi),
                                          threshold=t, p=[float(Pr[k, i]) for k in range(4)]))
        for code in FUNCS:
            res[code].setdefault("with_r", {})[str(rho)] = best[code][1]
    return res


def field_vs_power():
    ph = np.linspace(0, 2 * np.pi, 361)
    E = mzi_upper_fields(np.full_like(ph, np.pi / 2), ph)
    P = np.abs(E) ** 2
    return ph, P


# ---------- 圖 ----------
def fig_b7():
    fig, ax = plt.subplots(figsize=(13, 5.6))
    ys = {r: 4 - r for r in range(5)}                              # rail 0 在最上面
    x0, x1 = 0.0, 10.0
    colx = {0: 2.6, 1: 4.2, 2: 5.8, 3: 7.4}
    ax.add_patch(Rectangle((-1.6, -0.75), 2.9, 5.5, color="#e7f0fb", zorder=0))
    ax.add_patch(Rectangle((1.6, -0.75), 6.7, 5.5, color="#f3f0e7", zorder=0))
    ax.add_patch(Rectangle((8.6, -0.75), 4.6, 5.5, color="#eaf6ec", zorder=0))
    for x, t in ((-0.15, "① 輸入（編碼）"), (4.95, "② 混合（7 顆 MZI 干涉）"), (10.9, "③ 讀取（功率差＋判定）")):
        ax.text(x, 4.5, t, ha="center", fontsize=12.5, weight="bold", color="#333")
    for r, y in ys.items():
        ax.plot([x0, x1], [y, y], color="#5a6b80", lw=2, zorder=1)
        sig = b7.IN_SIGNALS[r]
        lab = f"{sig}  振幅 0／1" if r < 4 else f"R  振幅 {b7.R_AMP:g}"
        ax.text(x0 - 0.15, y, lab, ha="right", va="center", fontsize=11, color="#b3261e" if r == 4 else "#1f3b63")
        out = b7.OUT_SIGNALS[r]
        hot = r in b7.READOUT
        ax.text(x1 + 0.15, y, out + ("（讀取）" if hot else "（監看）"), va="center", fontsize=11,
                color="#0b6b2e" if hot else "#777", weight="bold" if hot else "normal")
    for k, (p, layer) in enumerate(b7.OPS):
        cx, ytop, ybot = colx[layer], ys[p], ys[p + 1]
        ax.add_patch(FancyBboxPatch((cx - 0.5, ybot - 0.22), 1.0, ytop - ybot + 0.44, boxstyle="round,pad=0.02",
                                    fc="white", ec="#2d5a8c", lw=1.8, zorder=3))
        ax.text(cx, (ytop + ybot) / 2 + 0.12, f"M{k + 1}", ha="center", va="center", fontsize=11.5, weight="bold", zorder=4)
        ax.text(cx, (ytop + ybot) / 2 - 0.2, f"θ{k + 1} φ{k + 1}", ha="center", va="center", fontsize=8.5, color="#2d5a8c", zorder=4)
    for layer, cx in colx.items():
        ax.text(cx, -0.55, f"第 {layer + 1} 層", ha="center", fontsize=9.5, color="#666")
    # 讀取：兩顆 PD、相減、比較器
    for r in b7.READOUT:
        y = ys[r]
        ax.plot([x1 + 1.35, x1 + 1.75], [y, y], color="#0b6b2e", lw=1.5)
        ax.add_patch(Rectangle((x1 + 1.75, y - 0.2), 0.45, 0.4, fc="#0b6b2e", ec="none"))
        ax.text(x1 + 1.97, y + 0.32, "PD", ha="center", fontsize=8.5, color="#0b6b2e")
    ya, yb = ys[b7.READOUT[0]], ys[b7.READOUT[1]]
    ax.plot([x1 + 2.2, x1 + 2.5, x1 + 2.5], [ya, ya, (ya + yb) / 2 + 0.25], color="#0b6b2e", lw=1.3)
    ax.plot([x1 + 2.2, x1 + 2.5, x1 + 2.5], [yb, yb, (ya + yb) / 2 - 0.25], color="#0b6b2e", lw=1.3)
    ax.text(x1 + 2.5, (ya + yb) / 2, "ΔP = P(o2) − P(o4)\nΔP > 0 → 1\nΔP < 0 → 0", ha="center", va="center",
            fontsize=10, bbox=dict(fc="white", ec="#0b6b2e"))
    ax.set_xlim(-2.0, 13.4)
    ax.set_ylim(-0.85, 4.95)
    ax.axis("off")
    ax.set_title("B7：四路資料光 x1–x4 與參考光 R 進入 7 顆 MZI，讀 o2、o4 的功率差", fontsize=13)
    path = rt.fig_path("m1_s1", "b7_io.png")
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return path


def fig_logic(res):
    ph, P = field_vs_power()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 5.2), gridspec_kw=dict(width_ratios=[1, 1.15]))
    a1.plot(np.degrees(ph), P[1], color="#1f6feb", lw=5, alpha=0.6, label="只有 x1（10）")
    a1.plot(np.degrees(ph), P[2], color="#d9480f", lw=2, ls="--", label="只有 x2（01）")
    a1.plot(np.degrees(ph), P[3], color="#2b8a3e", lw=2.5, label="x1、x2 同時（11）：光場相加")
    a1.axhline(P[1, 0] + P[2, 0], color="#555", ls=":", lw=2, label="若功率直接相加：0.5＋0.5＝1")
    for x, t in ((0, "OR／AND"), (180, "XOR")):
        a1.annotate(t, (x, P[3, int(x / 360 * 360)]), (x + 18, 1.75 if x == 0 else 0.25), fontsize=10,
                    arrowprops=dict(arrowstyle="->", color="#333"))
    a1.set(xlabel="φ（度）", ylabel="MZI 上埠功率（每路資料光功率＝1）", xlim=(0, 360), ylim=(-0.05, 2.1),
           xticks=range(0, 361, 45), title="(a) 單顆 MZI、θ = π/2：光場相加，不是功率相加")
    a1.grid(alpha=0.3)
    a1.legend(fontsize=9, loc="upper center")

    codes = list(FUNCS)
    cols = ["MZI"] + [f"+R ρ={r:g}" for r in RHOS]
    M = np.array([[res[c]["mzi"]["margin"]] + [res[c]["with_r"][str(r)]["margin"] for r in RHOS] for c in codes])
    show = np.where(M > MARGIN_MIN, M, np.nan)
    im = a2.imshow(show, cmap="YlGn", aspect="auto", vmin=0, vmax=np.nanmax(show))
    for i in range(len(codes)):
        for j in range(len(cols)):
            ok = M[i, j] > MARGIN_MIN
            a2.text(j, i, f"{M[i, j]:.2f}" if ok else "✕", ha="center", va="center", fontsize=9,
                    color=("white" if M[i, j] > 0.6 * np.nanmax(show) else "#222") if ok else "#c92a2a")
    a2.set_xticks(range(len(cols)), cols, fontsize=9.5)
    a2.set_yticks(range(len(codes)), [f"{FUNCS[c]}  ({c})" for c in codes], fontsize=9.5)
    a2.axhline(6.5, color="#333", lw=1.2)
    a2.set_title("(b) 2 輸入邏輯能不能做：最大判定餘裕（✕＝做不到）", fontsize=11.5)
    fig.colorbar(im, ax=a2, shrink=0.8, label="餘裕 min P(1 類) − max P(0 類)")
    fig.tight_layout()
    path = rt.fig_path("m1_s1", "single_mzi_logic.png")
    fig.savefig(path, dpi=115)
    plt.close(fig)
    return path


def main():
    enc = encoding()
    res = scan()
    figs = [fig_b7(), fig_logic(res)]
    n_mzi = sum(r["mzi"]["ok"] for r in res.values())
    n_r = {str(rho): sum(r["with_r"][str(rho)]["ok"] for r in res.values()) for rho in RHOS}
    f00_one = [c for c in FUNCS if c[0] == "1"]
    out = dict(io=dict(inputs=[dict(rail=i, signal=s, amplitude="0/1" if i < 4 else b7.R_AMP) for i, s in enumerate(b7.IN_SIGNALS)],
                       outputs=[dict(rail=i, signal=s, role="readout" if i in b7.READOUT else "monitor")
                                for i, s in enumerate(b7.OUT_SIGNALS)],
                       ops=b7.OPS, r_amp=b7.R_AMP, decision="ΔP = |o2|² − |o4|²；> 0 判 1"),
               encoding=enc, funcs=res, n_funcs=len(FUNCS), n_ok_mzi=n_mzi, n_ok_with_r=n_r,
               f00_one=f00_one, grid_deg=360 / N_GRID, rhos=RHOS, figs=[rt.rel(f) for f in figs])
    (OUT / "m1_s1_result.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"編碼 16 組；輸入總功率 {min(e['p_in'] for e in enc):g}–{max(e['p_in'] for e in enc):g}")
    print(f"單顆 MZI 可做 {n_mzi}/{len(FUNCS)}；加 R：{n_r}")
    for c, r in res.items():
        print(f"  {r['name']:7s} {c}  MZI {r['mzi']['margin']:+.3f}  " +
              "  ".join(f"ρ{rho:g} {r['with_r'][str(rho)]['margin']:+.3f}" for rho in RHOS))


if __name__ == "__main__":
    main()
