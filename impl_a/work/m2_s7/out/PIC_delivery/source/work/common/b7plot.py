"""B7 接線圖的共用畫法（M1 s2 起使用）：5 條波導、7 顆 MZI 方塊、層號與輸入輸出名稱。

用法：ys = draw_frame(ax)；之後可在 ax 上疊路線或標註。座標：x 0–10 為光路，層的中心在 COLX；
  rail r 的 y = 4 − r（rail 0 在最上面）。
輸入／輸出：無檔案。
"""
from matplotlib.patches import FancyBboxPatch

from common import b7

COLX = {0: 2.6, 1: 4.2, 2: 5.8, 3: 7.4}
COLORS = ["#1f6feb", "#d9480f", "#2b8a3e", "#ae3ec9", "#b3261e"]


def draw_frame(ax, mzi_label=None):
    """畫 B7 骨架；mzi_label(k) 可回傳方塊下方的小字（例如相位通道名稱）。回傳 {rail: y}。"""
    ys = {r: 4 - r for r in range(b7.N_MODES)}
    for r, y in ys.items():
        ax.plot([0, 10], [y, y], color="#c3ccd8", lw=2, zorder=1)
        ax.text(-0.15, y, b7.IN_SIGNALS[r], ha="right", va="center", fontsize=12, color=COLORS[r], weight="bold")
        ax.text(10.15, y, b7.OUT_SIGNALS[r], va="center", fontsize=12, color="#0b6b2e" if r in b7.READOUT else "#777",
                weight="bold" if r in b7.READOUT else "normal")
    for k, (p, layer) in enumerate(b7.OPS):
        cx = COLX[layer]
        ax.add_patch(FancyBboxPatch((cx - 0.5, ys[p + 1] - 0.22), 1.0, 1.44, boxstyle="round,pad=0.02",
                                    fc="white", ec="#2d5a8c", lw=1.6, alpha=0.9, zorder=2))
        ax.text(cx, ys[p] + 0.32, f"M{k + 1}", ha="center", fontsize=10, color="#2d5a8c", weight="bold", zorder=5)
        if mzi_label:
            ax.text(cx, (ys[p] + ys[p + 1]) / 2, mzi_label(k), ha="center", va="center", fontsize=8, color="#2d5a8c", zorder=5)
    for layer, cx in COLX.items():
        ax.text(cx, -0.65, f"第 {layer + 1} 層", ha="center", fontsize=9.5, color="#666")
    return ys
