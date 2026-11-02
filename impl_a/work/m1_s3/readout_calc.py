"""M1 s3：v → y = U·v → 功率 → ΔP → 0／1，一步一步算，並把 ΔP 拆成三種來源。

步驟：
  1. 單元測試（common/tests/test_readout.py）。
  2. 手算表：示範設定（θ 全 π/2、φ 全 0）下，輸入 1000、1100 的 o2、o4 逐項加權和、功率、ΔP、判定。
  3. 16 組輸入：ΔP 拆成「只有 R」「R×資料」「資料自己」「資料×資料」四部分，加總核對。
  4. 常見算錯：功率相加、R 放功率 9、取模長不平方、讀錯埠、忘了 R——各自的 ΔP 與判定錯幾組。
  5. 出圖：1100 的光場箭頭圖（複數平面上的加權和）、16 組 ΔP 分解圖。
輸入：common/b7.py、sources/reference_b7.json。
輸出：out/tests.json、out/m1_s3_result.json；course/figures/m1_s3/phasor_1100.png、dp_terms.png。
執行：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m1_s3\\readout_calc.py
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
from common import b7                   # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = rt.out_dir(__file__)
spec = importlib.util.spec_from_file_location("test_readout", HERE.parent / "common" / "tests" / "test_readout.py")
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)
U = b7.unitary(np.pi / 2, 0.0)
J2, J4 = b7.READOUT
IN = b7.IN_SIGNALS


def c2(z):
    return [float(np.real(z)), float(np.imag(z))]


def run_suite():
    suite = unittest.TestLoader().loadTestsFromTestCase(T.TestReadout)
    names = [t.id().split(".")[-1] for t in suite]
    result = unittest.TestResult()
    suite.run(result)
    bad = {t.id().split(".")[-1] for t, _ in result.failures + result.errors}
    return {n: (n not in bad, ((getattr(T.TestReadout, n).__doc__ or "").strip().splitlines() or [""])[0]) for n in names}


def hand_calc(bits):
    x = [int(b) for b in bits]
    v = b7.encode(x)
    out = dict(bits=bits, v=[float(a.real) for a in v])
    for name, j in (("o2", J2), ("o4", J4)):
        terms = [dict(src=IN[k], u=c2(U[j, k]), v=float(v[k].real), prod=c2(U[j, k] * v[k])) for k in range(5)]
        y = sum(U[j, k] * v[k] for k in range(5))
        out[name] = dict(terms=terms, field=c2(y), power=float(abs(y) ** 2))
    out["delta"] = out["o2"]["power"] - out["o4"]["power"]
    out["bit"] = b7.decide(out["delta"])
    return out


def decompose():
    f = b7.readout_form(U)
    rows = []
    for x in b7.ALL_BITS:
        lin = float(f["a"] @ x)
        diag = float(np.diag(f["Q"]) @ x)
        cross = float(x @ f["Q"] @ x - diag)
        dp = float(b7.delta_p(U @ b7.encode(x)))
        rows.append(dict(bits=b7.bits_str(x), r_only=f["c0"], r_x_data=lin, data_self=diag, data_x_data=cross,
                         total=dp, check=abs(f["c0"] + lin + diag + cross - dp), bit=b7.decide(dp)))
    off = f["Q"][~np.eye(4, dtype=bool)]
    return dict(c0=f["c0"], a=f["a"].tolist(), Q=f["Q"].tolist(), rows=rows,
                max_abs_a=float(np.abs(f["a"]).max()), max_abs_Q_off=float(np.abs(off).max()))


N_RANDOM = 200                           # 隨機相位設定數（看算錯方式在一般相位下錯多少）


def mistakes():
    """學員常見的算錯方式：示範設定下 16 組的 ΔP 與判定，以及 200 組隨機相位下平均判錯幾組。"""
    def correct(x, U):
        return b7.delta_p(U @ b7.encode(x))

    def power_sum(x, U):
        v = b7.encode(x)
        P = (np.abs(U) ** 2) @ (np.abs(v) ** 2)
        return P[J2] - P[J4]

    def r_as_power(x, U):
        return b7.delta_p(U @ b7.encode(x, r=b7.R_AMP ** 2))

    def modulus(x, U):
        y = np.abs(U @ b7.encode(x))
        return y[J2] - y[J4]

    def wrong_ports(x, U):
        y = np.abs(U @ b7.encode(x)) ** 2
        return y[2] - y[4]                       # 把 o2、o4 的編號直接當成從 0 起算的索引，讀到 o3、o5

    def no_r(x, U):
        return b7.delta_p(U @ b7.encode(x, r=0.0))

    cases = [("correct", "正確：先加光場、再取平方", correct),
             ("power_sum", "把功率相加（各項先取平方再加）", power_sum),
             ("r_as_power", "R 放成功率 9（應為振幅 3）", r_as_power),
             ("modulus", "取模長 |o| 不平方", modulus),
             ("wrong_ports", "讀錯埠：程式寫 y[2]、y[4]（讀到 o3、o5）", wrong_ports),
             ("no_r", "忘了加 R", no_r)]
    rng = rt.rng(3)
    Us = [b7.unitary(rng.uniform(0, 2 * np.pi, 7), rng.uniform(0, 2 * np.pi, 7)) for _ in range(N_RANDOM)]
    refs = [np.array([correct(x, Ur) for x in b7.ALL_BITS]) for Ur in Us]
    ref = np.array([correct(x, U) for x in b7.ALL_BITS])
    rows = []
    for key, desc, fn in cases:
        d = np.array([fn(x, U) for x in b7.ALL_BITS])
        flips = int(np.sum(np.sign(d) != np.sign(ref)))
        rand = [np.sum(np.sign([fn(x, Ur) for x in b7.ALL_BITS]) != np.sign(rf)) for Ur, rf in zip(Us, refs)]
        rows.append(dict(key=key, desc=desc, d1000=float(d[1]), d1100=float(d[3]), flips=flips,
                         ones=int(np.sum(d > 0)), rand_mean_flips=float(np.mean(rand)),
                         rand_any=float(np.mean(np.array(rand) > 0))))
    return rows


# ---------- 圖 ----------
COL = ["#1f6feb", "#d9480f", "#2b8a3e", "#ae3ec9", "#b3261e"]


def fig_phasor(hc):
    fig, axs = plt.subplots(1, 2, figsize=(12, 5.6))
    for ax, name in zip(axs, ("o2", "o4")):
        z0 = 0j
        for k, t in enumerate(hc[name]["terms"]):
            p = complex(*t["prod"])
            if abs(p) < 1e-12:
                continue
            ax.annotate("", xy=((z0 + p).real, (z0 + p).imag), xytext=(z0.real, z0.imag),
                        arrowprops=dict(arrowstyle="-|>", color=COL[k], lw=3, mutation_scale=18))
            ax.plot([], [], color=COL[k], lw=3, label=f"{t['src']}：u = {t['u'][0]:+.3f}{t['u'][1]:+.3f}i，× {t['v']:g} = {p.real:+.3f}{p.imag:+.3f}i")
            z0 += p
        ax.annotate("", xy=(z0.real, z0.imag), xytext=(0, 0),
                    arrowprops=dict(arrowstyle="-|>", color="#222", lw=1.5, ls="--", mutation_scale=14))
        ax.plot([], [], color="#222", lw=1.5, ls="--", label=f"總和 {name} = {z0.real:+.3f}{z0.imag:+.3f}i，|{name}|² = {abs(z0) ** 2:.3f}")
        ax.plot(0, 0, "ko", ms=4)
        ax.axhline(0, color="#999", lw=0.8)
        ax.axvline(0, color="#999", lw=0.8)
        ax.set_aspect("equal")
        ax.grid(alpha=0.3)
        ax.set(xlim=(-1.6, 1.6), ylim=(-1.5, 1.6), xlabel="實部", ylabel="虛部",
               title=f"{name}：各輸入的光場貢獻首尾相接（輸入 {hc['bits']}）")
        ax.legend(fontsize=8.5, loc="lower center")
    fig.suptitle(f"先加光場、再取平方：ΔP = {hc['o2']['power']:.3f} − {hc['o4']['power']:.3f} = {hc['delta']:.3f} → 判 {hc['bit']}",
                 fontsize=13, y=1.0)
    fig.tight_layout()
    path = rt.fig_path("m1_s3", "phasor_1100.png")
    fig.savefig(path, dpi=115, bbox_inches="tight")
    plt.close(fig)
    return path


def fig_terms(dec):
    rows = dec["rows"]
    x = np.arange(len(rows))
    parts = [("r_only", "只有 R（R²）", "#b3261e"), ("r_x_data", "R × 資料（∝ R）", "#f59f00"),
             ("data_self", "資料自己的功率", "#74c0fc"), ("data_x_data", "資料 × 資料（交叉項）", "#2b8a3e")]
    fig, ax = plt.subplots(figsize=(13, 5))
    pos, neg = np.zeros(len(rows)), np.zeros(len(rows))
    for key, lab, col in parts:
        val = np.array([r[key] for r in rows])
        base = np.where(val >= 0, pos, neg)
        ax.bar(x, val, bottom=base, color=col, label=lab, width=0.7)
        pos += np.where(val >= 0, val, 0)
        neg += np.where(val < 0, val, 0)
    tot = np.array([r["total"] for r in rows])
    ax.plot(x, tot, "kD", ms=7, label="ΔP 總和")
    for i, t in enumerate(tot):
        ax.text(i, max(pos[i], t) + 0.12, f"{t:+.2f}\n→{'邊界' if rows[i]['bit'] is None else rows[i]['bit']}", ha="center", fontsize=8.5)
    ax.axhline(0, color="#222", lw=1)
    ax.set_xticks(x, [r["bits"] for r in rows], rotation=0, fontsize=9)
    ax.set_xlabel("輸入 x1x2x3x4")
    ax.set_ylabel("對 ΔP 的貢獻")
    ax.set_title("示範設定（θ 全 π/2、φ 全 0）：16 組輸入的 ΔP 拆成四種來源", fontsize=12.5)
    ax.legend(fontsize=9, ncol=5, loc="lower center", bbox_to_anchor=(0.5, -0.32))
    ax.set_ylim(min(neg.min(), tot.min()) - 0.4, max(pos.max(), tot.max()) + 0.8)
    fig.tight_layout()
    path = rt.fig_path("m1_s3", "dp_terms.png")
    fig.savefig(path, dpi=115)
    plt.close(fig)
    return path


def main():
    tests = run_suite()
    hcs = [hand_calc("1000"), hand_calc("1100")]
    dec = decompose()
    mis = mistakes()
    figs = [fig_phasor(hcs[1]), fig_terms(dec)]
    tj = dict(tests=[dict(name=k, passed=ok, doc=d) for k, (ok, d) in tests.items()],
              n_pass=sum(ok for ok, _ in tests.values()), n_total=len(tests))
    (OUT / "tests.json").write_text(json.dumps(tj, ensure_ascii=False, indent=1), encoding="utf-8")
    res = dict(tests=dict(n_pass=tj["n_pass"], n_total=tj["n_total"]), setting="θ 全 π/2、φ 全 0、R＝3",
               hand=hcs, decomposition=dec, mistakes=mis,
               max_check=max(r["check"] for r in dec["rows"]), figs=[rt.rel(f) for f in figs])
    (OUT / "m1_s3_result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"單元測試 {tj['n_pass']}/{tj['n_total']}")
    for h in hcs:
        print(f"  {h['bits']}: o2 {h['o2']['field']} P {h['o2']['power']:.4f} | o4 {h['o4']['field']} P {h['o4']['power']:.4f} | ΔP {h['delta']:.4f} → {h['bit']}")
    print(f"分解：c0 {dec['c0']:.4f}  a {np.round(dec['a'], 4).tolist()}  max|Q 非對角| {dec['max_abs_Q_off']:.4f}  核對 {res['max_check']:.1e}")
    for r in dec["rows"]:
        print(f"  {r['bits']} R {r['r_only']:+.3f} R×d {r['r_x_data']:+.3f} self {r['data_self']:+.3f} d×d {r['data_x_data']:+.3f} = {r['total']:+.3f} → {r['bit']}")
    for m in mis:
        print(f"  {m['key']:12s} 1000 {m['d1000']:+.3f} 1100 {m['d1100']:+.3f} 判定錯 {m['flips']}/16  判 1 的數目 {m['ones']}"
              f"  隨機相位平均錯 {m['rand_mean_flips']:.2f}/16，至少錯 1 組的比例 {m['rand_any']:.0%}")


if __name__ == "__main__":
    main()
