"""M1 s2：7 顆 MZI 組成 B7 的 5×5 矩陣 U——單元測試、故障注入、路徑數、逐層功率與出圖。

步驟：
  1. 對 common/b7.py 跑單元測試（三種獨立算法互相核對＋兩組黃金值）。
  2. 故障注入：7 種常見組裝錯誤，每種都重跑測試，確認至少一項失敗。
  3. 結構：每個輸入到每個輸出有幾條路徑（與相位無關）；哪些組合永遠沒有光。
  4. 示範設定 θ 全 π/2、φ 全 0：|U|²、輸入 1100 的逐層功率分佈、ΔP。
  5. 出圖：全交叉追蹤圖（學員手動追蹤的答案）、|U|² 與逐層功率圖。
輸入：common/b7.py、common/mzi.py、sources/reference_b7.json。
輸出：out/tests.json、out/m1_s2_result.json；course/figures/m1_s2/b7_cross_trace.png、b7_u_layers.png。
執行：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m1_s2\\build_b7.py
"""
import sys
import json
import importlib.util
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import runtime as rt

rt.setup()
import numpy as np                      # noqa: E402
import matplotlib.pyplot as plt         # noqa: E402
from common import b7, mzi as Z         # noqa: E402
from common.b7plot import COLX, COLORS, draw_frame  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = rt.out_dir(__file__)
spec = importlib.util.spec_from_file_location("test_b7", HERE.parent / "common" / "tests" / "test_b7.py")
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)
NAMES = b7.IN_SIGNALS


def run_suite():
    suite = unittest.TestLoader().loadTestsFromTestCase(T.TestB7)
    names = [t.id().split(".")[-1] for t in suite]            # suite.run() 跑完會清掉測試物件，先記名字
    result = unittest.TestResult()
    suite.run(result)
    bad = {t.id().split(".")[-1] for t, _ in result.failures + result.errors}
    return {n: (n not in bad, ((getattr(T.TestB7, n).__doc__ or "").strip().splitlines() or [""])[0]) for n in names}


# ---------- 故障注入 ----------
def _u_reversed(theta, phi=0.0):
    theta, phi = b7._phases(theta, phi)
    U = np.eye(5, dtype=complex)
    for k, (p, _) in enumerate(b7.OPS):
        U = U @ Z.embed(Z.T2(theta[k], phi[k]), p, p + 1, 5)
    return U


def _u_flipped(theta, phi=0.0):
    theta, phi = b7._phases(theta, phi)
    U = np.eye(5, dtype=complex)
    for k, (p, _) in enumerate(b7.OPS):
        U = Z.embed(Z.T2(theta[k], phi[k])[::-1, ::-1], p, p + 1, 5) @ U
    return U


def _u_no_phi(theta, phi=0.0):
    return _ORIG["unitary"](theta, 0.0)


def _trace_reversed(v, theta, phi=0.0):
    theta, phi = b7._phases(theta, phi)
    field = np.array(v, dtype=complex)
    stages = [field.copy()]
    for layer in reversed(range(b7.N_LAYERS)):
        for k, (p, lay) in enumerate(b7.OPS):
            if lay == layer:
                field[[p, p + 1]] = Z.T2(theta[k], phi[k]) @ field[[p, p + 1]]
        stages.append(field.copy())
    return stages


def _paths_transposed(i, j, theta, phi=0.0):
    theta, phi = b7._phases(theta, phi)
    out = _ORIG["paths"](i, j, theta, phi)
    for p in out:                                              # 用 T[入, 出] 取代 T[出, 入]
        w = 1.0 + 0j
        for k, b, a in p["steps"]:
            w *= Z.T2(theta[k - 1], phi[k - 1])[a - 1, b - 1]
        p["weight"] = w
    return out


_ORIG = {"unitary": b7.unitary, "paths": b7.paths}
OPS_M5 = [(0, 0), (3, 0), (1, 1), (0, 2), (1, 2), (1, 3), (3, 3)]
OPS_LAYER = [(0, 0), (3, 0), (1, 0), (0, 2), (2, 2), (1, 3), (3, 3)]
MUTANTS = [
    ("F1", "矩陣相乘順序反了（U = U·Ek，等於光由右往左走）", "unitary", _u_reversed),
    ("F2", "MZI 嵌入時上下顛倒（局部索引 0、1 對調）", "unitary", _u_flipped),
    ("F3", "組 U 時漏了 φ（只用 θ）", "unitary", _u_no_phi),
    ("F4", "OPS 抄錯：M5 寫成跨 rail 1–2（應為 2–3）", "OPS", OPS_M5),
    ("F5", "OPS 層號標錯：M3 寫成第 1 層（應為第 2 層）", "OPS", OPS_LAYER),
    ("F6", "逐層追蹤時層的順序倒過來", "trace", _trace_reversed),
    ("F7", "路徑係數取成 T[入, 出]（行列對調）", "paths", _paths_transposed),
]


def run_mutants():
    rows = []
    for mid, desc, attr, value in MUTANTS:
        orig = getattr(b7, attr)
        setattr(b7, attr, value)
        try:
            res = run_suite()
        finally:
            setattr(b7, attr, orig)
        caught = sorted(k for k, (ok, _) in res.items() if not ok)
        rows.append(dict(id=mid, fault=desc, caught_by=caught, detected=bool(caught)))
    return rows


# ---------- 結構與示範設定 ----------
def structure():
    th = np.full(7, 0.7)                                       # 任意非特殊相位；路徑數與相位無關
    counts = [[len(b7.paths(i, j, th)) for i in range(5)] for j in range(5)]   # counts[j][i]：輸入 i → 輸出 j
    return counts


def demo():
    U = b7.unitary(np.pi / 2, 0.0)
    x = [1, 1, 0, 0]
    v = b7.encode(x)
    stages = b7.trace(v, np.pi / 2, 0.0)
    P = [np.abs(s) ** 2 for s in stages]
    y = U @ v
    return dict(U2=(np.abs(U) ** 2).tolist(), bits=b7.bits_str(x), stage_power=[p.tolist() for p in P],
                out_power=(np.abs(y) ** 2).tolist(), delta=float(b7.delta_p(y)), bit=b7.decide(b7.delta_p(y)))


# ---------- 圖 ----------
def fig_cross():
    fig, ax = plt.subplots(figsize=(12, 5))
    ys = draw_frame(ax)
    for i, j in enumerate(T.CROSS_PERM):
        pth = max(b7.paths(i, j, 0.0), key=lambda p: abs(p["weight"]))   # 全交叉時只有一條路徑係數不為 0
        xs, yy, r = [0], [ys[i]], i
        for layer, r2 in enumerate(pth["rails"]):
            cx = COLX[layer]
            xs += [cx - 0.5, cx + 0.5]
            yy += [ys[r], ys[r2]]
            r = r2
        xs.append(10)
        yy.append(ys[r])
        off = (i - 2) * 0.035
        ax.plot(xs, np.array(yy) + off, color=COLORS[i], lw=3, zorder=4, solid_capstyle="round")
    ax.set_xlim(-1.2, 11)
    ax.set_ylim(-0.85, 4.6)
    ax.axis("off")
    ax.set_title("θ 全 0（每顆 MZI 全交叉）：逐層追蹤每一路光走到哪個出口", fontsize=13)
    path = rt.fig_path("m1_s2", "b7_cross_trace.png")
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return path


def fig_u(d, counts):
    U2 = np.array(d["U2"])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13.5, 5.2), gridspec_kw=dict(width_ratios=[1, 1.1]))
    im = a1.imshow(U2, cmap="Blues", vmin=0, vmax=U2.max())
    for j in range(5):
        for i in range(5):
            txt = f"{U2[j, i]:.3f}\n{counts[j][i]} 條" if counts[j][i] else "0\n無路徑"
            a1.text(i, j, txt, ha="center", va="center", fontsize=9,
                    color="white" if U2[j, i] > 0.6 * U2.max() else ("#c92a2a" if not counts[j][i] else "#222"))
    a1.set_xticks(range(5), NAMES)
    a1.set_yticks(range(5), [s + ("（讀取）" if r in b7.READOUT else "") for r, s in enumerate(b7.OUT_SIGNALS)])
    a1.set_xlabel("輸入")
    a1.set_title("(a) |U|²（θ 全 π/2、φ 全 0）與路徑數", fontsize=11.5)
    fig.colorbar(im, ax=a1, shrink=0.8)

    P = np.array(d["stage_power"])
    bottom = np.zeros(len(P))
    for r in range(5):
        a2.bar(range(len(P)), P[:, r], bottom=bottom, color=COLORS[r], label=f"rail {r}（{NAMES[r]}→{b7.OUT_SIGNALS[r]}）")
        for s in range(len(P)):
            if P[s, r] > 0.35:
                a2.text(s, bottom[s] + P[s, r] / 2, f"{P[s, r]:.2f}", ha="center", va="center", fontsize=8.5, color="white")
        bottom += P[:, r]
    a2.set_xticks(range(len(P)), ["輸入"] + [f"第 {k} 層後" for k in range(1, len(P))])
    a2.set_ylabel("功率")
    a2.set_title(f"(b) 輸入 {d['bits']}：每一層之後各波導的功率（總和固定 {bottom[0]:.0f}）", fontsize=11.5)
    a2.legend(fontsize=8.5, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    fig.tight_layout()
    path = rt.fig_path("m1_s2", "b7_u_layers.png")
    fig.savefig(path, dpi=115)
    plt.close(fig)
    return path


def main():
    tests = run_suite()
    mutants = run_mutants()
    counts = structure()
    d = demo()
    figs = [fig_cross(), fig_u(d, counts)]
    tj = dict(tests=[dict(name=k, passed=ok, doc=doc) for k, (ok, doc) in tests.items()],
              n_pass=sum(ok for ok, _ in tests.values()), n_total=len(tests),
              mutants=mutants, n_detected=sum(m["detected"] for m in mutants), n_mutants=len(mutants))
    (OUT / "tests.json").write_text(json.dumps(tj, ensure_ascii=False, indent=1), encoding="utf-8")
    zero = [[NAMES[i], b7.OUT_SIGNALS[j]] for j in range(5) for i in range(5) if counts[j][i] == 0]
    res = dict(tests=dict(n_pass=tj["n_pass"], n_total=tj["n_total"], n_detected=tj["n_detected"], n_mutants=tj["n_mutants"]),
               path_counts=counts, zero_pairs=zero, cross_perm=T.CROSS_PERM, demo=d, figs=[rt.rel(f) for f in figs])
    (OUT / "m1_s2_result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"單元測試 {tj['n_pass']}/{tj['n_total']}")
    for k, (ok, _) in tests.items():
        print(f"  {'PASS' if ok else 'FAIL'} {k}")
    print(f"故障注入 {tj['n_detected']}/{tj['n_mutants']}")
    for m in mutants:
        print(f"  {m['id']} {'抓到' if m['detected'] else '漏掉'} {m['caught_by']}")
    print("路徑數（列＝輸出 o1..o5，行＝輸入 x1..R）")
    for j, row in enumerate(counts):
        print("  ", b7.OUT_SIGNALS[j], row)
    print("永遠沒有光：", zero)
    print(f"示範 {d['bits']}: 輸出功率 {np.round(d['out_power'], 4).tolist()} ΔP {d['delta']:.4f} → {d['bit']}")


if __name__ == "__main__":
    main()
