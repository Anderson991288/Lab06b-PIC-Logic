"""M1 s4：同一組 B7 光路，換 14 個相位就換功能——80 筆真值表、餘裕、為什麼 XOR 比較脆弱、非理想下還對不對。

步驟：
  1. 讀共用相位檔，對 AND2、OR2、XOR2、AND4、OR4 各跑 16 組（共 80 筆），與原版每列 ΔP 核對；相位取 4 位小數重跑。
  2. 前幾步的單元測試重跑一次（b7.py 本步有新增功能，確認沒有改壞）。
  3. 用 M1 s3 的二次式拆 ΔP：拿掉「資料×資料」交叉項後各功能還對不對；「功率相加」算錯在真正相位下錯幾筆。
  4. 非理想：M0 s3 由 FDTD 擬合的等效誤差（θ 偏移、耦合器分光誤差）、每顆 MZI 0.66 dB 損耗、隨機相位誤差（Monte Carlo）。
  5. 自己找相位：用最佳化為 NAND2（輸入 00 要輸出 1）求 14 個相位。
輸入：sources/b7_phases.json、../m0_s3/out/m0_s3_result.json、common/b7.py。
輸出：out/m1_s4_result.json；course/figures/m1_s4/truth_tables.png、robustness.png。
執行：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m1_s4\\logic_gates.py
"""
import sys
import json
import math
import time
import importlib.util
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import runtime as rt

rt.setup()
import numpy as np                      # noqa: E402
import matplotlib.pyplot as plt         # noqa: E402
from scipy.optimize import minimize     # noqa: E402
from common import b7                   # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = rt.out_dir(__file__)
GATES = ["AND2", "OR2", "XOR2", "AND4", "OR4"]
PH = b7.load_phases()
REFG = json.loads(b7.PHASE_FILE.read_text(encoding="utf-8"))["gates"]
SIGMAS = [0.01, 0.02, 0.05, 0.1, 0.2]   # 隨機相位誤差標準差（rad），14 個相位各自獨立
N_MC = 500
LOSS_DB = 0.66                           # 每顆 MZI＝兩顆 MMI × 約 0.33 dB
N_RESTART = 30


def regression():
    out = {}
    for name, cls in (("test_b7", "TestB7"), ("test_readout", "TestReadout")):
        spec = importlib.util.spec_from_file_location(name, HERE.parent / "common" / "tests" / f"{name}.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        r = unittest.TestResult()
        suite = unittest.TestLoader().loadTestsFromTestCase(getattr(m, cls))
        n = suite.countTestCases()
        suite.run(r)
        out[name] = dict(n=n, failed=len(r.failures) + len(r.errors))
    return out


def replay():
    res = {}
    for g in GATES:
        th, ph = PH[g]
        tt = b7.truth_table(b7.unitary(th, ph), g)
        ref = np.array([r["delta"] for r in REFG[g]["ref_rows"]])
        rnd = b7.truth_table(b7.unitary(np.round(th, 4), np.round(ph, 4)), g)
        res[g] = dict(theta=th.tolist(), phi=ph.tolist(), delta=tt["delta"].tolist(), bit=tt["bit"].tolist(),
                      target=tt["target"].tolist(), ok=tt["ok"], n_ok=int(np.sum(tt["bit"] == tt["target"])),
                      margin=tt["margin"], max_diff_ref=float(np.abs(tt["delta"] - ref).max()),
                      round4_ok=rnd["ok"], round4_margin=rnd["margin"])
    return res


def anatomy():
    """拆 ΔP：拿掉資料×資料交叉項（只留 c0＋線性＋資料自己）還對不對；功率相加算錯錯幾筆。"""
    res = {}
    for g in GATES:
        U = b7.unitary(*PH[g])
        f = b7.readout_form(U)
        tgt = b7.target(g)
        Qd = np.diag(np.diag(f["Q"]))
        lin = np.array([f["c0"] + f["a"] @ x + x @ Qd @ x for x in b7.ALL_BITS])
        full = np.array([f["c0"] + f["a"] @ x + x @ f["Q"] @ x for x in b7.ALL_BITS])
        cross = full - lin
        s = 2 * tgt - 1
        P = np.abs(U) ** 2
        ps = np.array([(P @ np.abs(b7.encode(x)) ** 2)[1] - (P @ np.abs(b7.encode(x)) ** 2)[3] for x in b7.ALL_BITS])
        res[g] = dict(c0=f["c0"], max_abs_a=float(np.abs(f["a"]).max()),
                      max_abs_cross=float(np.abs(cross).max()), no_cross_ok=bool(np.all(lin * s > 0)),
                      no_cross_margin=float((lin * s).min()), no_cross_wrong=int(np.sum(lin * s <= 0)),
                      power_sum_wrong=int(np.sum(ps * s <= 0)))
    return res


def nonideal():
    fit = json.loads((HERE.parent / "m0_s3" / "out" / "m0_s3_result.json").read_text(encoding="utf-8"))["fit"]
    delta, eps = math.radians(fit["delta_deg"]), fit["eps"]
    res = {}
    rng = rt.rng(4)
    noise = {s: rng.normal(0, s, (N_MC, 14)) for s in SIGMAS}
    for g in GATES:
        th, ph = PH[g]
        r = {}
        for key, kw in (("fdtd_equiv", dict(theta_offset=delta, mmi_err=(eps[0], eps[1]))),
                        ("fdtd_equiv_swapped", dict(theta_offset=delta, mmi_err=(eps[1], eps[0]))),
                        ("loss", dict(loss_db=LOSS_DB))):
            tt = b7.truth_table(b7.unitary(th, ph, **kw), g)
            r[key] = dict(ok=tt["ok"], margin=tt["margin"], n_ok=int(np.sum(tt["bit"] == tt["target"])))
        mc = {}
        for s in SIGMAS:
            n = noise[s]
            oks = [b7.truth_table(b7.unitary(th + n[i, :7], ph + n[i, 7:]), g)["ok"] for i in range(N_MC)]
            mc[str(s)] = float(np.mean(oks))
        r["mc_pass"] = mc
        res[g] = r
    return dict(fit=dict(delta_deg=fit["delta_deg"], eps=eps), loss_db=LOSS_DB, sigmas=SIGMAS, n_mc=N_MC, gates=res)


def synth(gate="NAND2"):
    """最大化最小有號 ΔP：以 soft-min（log-sum-exp）近似，L-BFGS 多起點。"""
    tgt = b7.target(gate)
    s = 2 * tgt - 1
    V = np.column_stack([b7.ALL_BITS, np.full(16, b7.R_AMP)]).astype(complex)
    beta = 8.0

    def obj(p):
        dp = b7.delta_p(V @ b7.unitary(p[:7], p[7:]).T) * s
        return float(np.log(np.sum(np.exp(-beta * dp))) / beta)          # ≈ −min(dp)

    rng = rt.rng(5)
    t0 = time.time()
    best, tries = None, []
    for k in range(N_RESTART):
        r = minimize(obj, rng.uniform(0, 2 * np.pi, 14), method="L-BFGS-B")
        m = b7.truth_table(b7.unitary(r.x[:7], r.x[7:]), gate)["margin"]
        tries.append(m)
        if best is None or m > best[0]:
            best = (m, np.mod(r.x, 2 * np.pi))
    th, ph = best[1][:7], best[1][7:]
    tt = b7.truth_table(b7.unitary(th, ph), gate)
    f = b7.readout_form(b7.unitary(th, ph))
    return dict(gate=gate, theta=th.tolist(), phi=ph.tolist(), margin=tt["margin"], ok=tt["ok"],
                delta=tt["delta"].tolist(), c0=f["c0"], n_restart=N_RESTART,
                n_success=int(np.sum(np.array(tries) > 0)), restart_margins=[float(m) for m in tries],
                runtime_s=round(time.time() - t0, 1))


# ---------- 圖 ----------
def fig_tables(rep, syn):
    names = GATES + [syn["gate"]]
    fig, axs = plt.subplots(len(names), 1, figsize=(12.5, 2.0 * len(names)), sharex=True)
    labels = [b7.bits_str(x) for x in b7.ALL_BITS]
    for ax, g in zip(axs, names):
        d = np.array(rep[g]["delta"] if g in rep else syn["delta"])
        tgt = b7.target(g)
        m = rep[g]["margin"] if g in rep else syn["margin"]
        ax.bar(range(16), d, color=np.where(tgt == 1, "#2b8a3e", "#c92a2a"), width=0.7)
        ax.axhline(0, color="#222", lw=1)
        for y in (m, -m):
            ax.axhline(y, color="#666", lw=0.8, ls=":")
        tag = "（本頁自己求的相位）" if g not in rep else ""
        ax.set_ylabel("ΔP", fontsize=9)
        ax.set_title(f"{g}{tag}：16/16 正確，最小 |ΔP| = {m:.3f}" if (rep.get(g, syn)["ok"]) else f"{g}：有錯", fontsize=10.5, loc="left")
        ax.grid(axis="y", alpha=0.3)
    axs[-1].set_xticks(range(16), labels, fontsize=9)
    axs[-1].set_xlabel("輸入 x1x2x3x4（綠＝目標 1，紅＝目標 0；虛線＝±最小 |ΔP|）")
    fig.tight_layout()
    path = rt.fig_path("m1_s4", "truth_tables.png")
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path


def fig_robust(rep, ni):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.6))
    cols = {"AND2": "#1f6feb", "OR2": "#2b8a3e", "XOR2": "#c92a2a", "AND4": "#ae3ec9", "OR4": "#f59f00"}
    x = np.arange(len(GATES))
    w = 0.25
    a1.bar(x - w, [rep[g]["margin"] for g in GATES], w, color="#495057", label="理想")
    a1.bar(x, [ni["gates"][g]["fdtd_equiv"]["margin"] for g in GATES], w, color="#74c0fc", label="M0 s3 FDTD 等效誤差")
    a1.bar(x + w, [ni["gates"][g]["loss"]["margin"] for g in GATES], w, color="#f59f00", label=f"每顆 MZI {ni['loss_db']} dB 損耗")
    a1.axhline(0, color="#222", lw=1)
    a1.set_xticks(x, GATES)
    a1.set_ylabel("最小有號 ΔP（< 0 表示有判錯）")
    a1.set_title("(a) 判定餘裕：理想 vs 非理想", fontsize=11.5)
    a1.legend(fontsize=9)
    a1.grid(axis="y", alpha=0.3)
    for g in GATES:
        a2.plot(ni["sigmas"], [ni["gates"][g]["mc_pass"][str(s)] * 100 for s in ni["sigmas"]], "o-", color=cols[g], lw=2, label=g)
    a2.set_xscale("log")
    a2.set_xticks(ni["sigmas"], [f"{s:g}" for s in ni["sigmas"]])     # 自訂刻度，避免 mathtext 負號缺字
    a2.minorticks_off()
    a2.set(xlabel="14 個相位各自的隨機誤差 σ（rad）", ylabel="16 組全對的比例（%）", ylim=(-3, 103),
           title=f"(b) 相位誤差容忍度（每點 {ni['n_mc']} 次 Monte Carlo）")
    a2.grid(alpha=0.3, which="both")
    a2.legend(fontsize=9)
    fig.tight_layout()
    path = rt.fig_path("m1_s4", "robustness.png")
    fig.savefig(path, dpi=115)
    plt.close(fig)
    return path


def main():
    reg = regression()
    rep = replay()
    ana = anatomy()
    ni = nonideal()
    syn = synth()
    figs = [fig_tables(rep, syn), fig_robust(rep, ni)]
    n80 = sum(rep[g]["n_ok"] for g in GATES)
    res = dict(regression=reg, gates=rep, n_rows=16 * len(GATES), n_correct=n80, anatomy=ana, nonideal=ni, synth=syn,
               figs=[rt.rel(f) for f in figs])
    (OUT / "m1_s4_result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("回歸測試", reg)
    print(f"80 筆：{n80}/80 正確")
    for g in GATES:
        r, a, n = rep[g], ana[g], ni["gates"][g]
        print(f"  {g:5s} 餘裕 {r['margin']:.4f} 與原版差 {r['max_diff_ref']:.1e} 4 位小數 {r['round4_ok']} | c0 {a['c0']:+.3f} "
              f"max|a| {a['max_abs_a']:.3f} max|交叉| {a['max_abs_cross']:.3f} 無交叉項 {a['no_cross_ok']}({a['no_cross_wrong']} 錯) 功率相加錯 {a['power_sum_wrong']} | "
              f"FDTD 等效 {n['fdtd_equiv']['ok']} {n['fdtd_equiv']['margin']:+.3f} / 對調 {n['fdtd_equiv_swapped']['margin']:+.3f} 損耗 {n['loss']['margin']:+.3f} | MC {n['mc_pass']}")
    print(f"NAND2：餘裕 {syn['margin']:.4f} ok {syn['ok']} c0 {syn['c0']:+.3f} 成功起點 {syn['n_success']}/{syn['n_restart']} 用時 {syn['runtime_s']} s")


if __name__ == "__main__":
    main()
