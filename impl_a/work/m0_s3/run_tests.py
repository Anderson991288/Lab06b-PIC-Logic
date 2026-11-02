"""M0 s3：共用 MZI 模型的單元測試、故障注入、θ 掃描圖，以及與 M0 s2 FDTD 光場的對照。

步驟：
  1. 對 common/mzi.py 跑全部單元測試。
  2. 故障注入：把模型改壞（7 種常見錯誤），每種都重跑測試，確認至少一項失敗。
  3. 用模型重算 M0 s2 的四種 MZI 狀態，與 FDTD（除以總穿透後）比較；由直通功率反推等效 θ。
  4. 出圖：θ 掃描（直通／交叉功率）與相干合光（輸入相對相位掃描），疊上 FDTD 點。
輸入：../m0_s2/out/m0_s2_result.json、../m0_s2/out/field_*.json。
輸出：out/tests.json、out/m0_s3_result.json、course/figures/m0_s3/theta_sweep.png。
執行：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m0_s3\\run_tests.py
"""
import sys
import json
import math
import importlib.util
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import runtime as rt

rt.setup()
import numpy as np                      # noqa: E402
import matplotlib.pyplot as plt         # noqa: E402
from common import mzi as Z             # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = rt.out_dir(__file__)
S2 = HERE.parent / "m0_s2" / "out"
spec = importlib.util.spec_from_file_location("test_mzi", HERE.parent / "common" / "tests" / "test_mzi.py")
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)


def run_suite():
    """跑一次全部測試，回傳 {測試名: (通過與否, 說明第一行)}。"""
    suite = unittest.TestLoader().loadTestsFromTestCase(T.TestMZI)
    names = [t.id().split(".")[-1] for t in suite]            # suite.run() 跑完會清掉測試物件，先記名字
    result = unittest.TestResult()
    suite.run(result)
    bad = {t.id().split(".")[-1] for t, _ in result.failures + result.errors}
    out = {}
    for name in names:
        doc = (getattr(T.TestMZI, name).__doc__ or "").strip().splitlines()
        out[name] = (name not in bad, doc[0] if doc else "")
    return out


# ---------- 故障注入：每種改壞的模型都要被至少一項測試抓到 ----------
def _t2_wrong_arm(theta, phi=0.0, loss_db=0.0, mmi_err=(0.0, 0.0)):
    t = Z.coupler(mmi_err[1]) @ np.diag([1.0, np.exp(1j * theta)]) @ Z.coupler(mmi_err[0]) @ np.diag([np.exp(1j * phi), 1.0])
    return t * Z.amp(loss_db)


def _t2_phi_after(theta, phi=0.0, loss_db=0.0, mmi_err=(0.0, 0.0)):
    t = np.diag([np.exp(1j * phi), 1.0]) @ Z.coupler(mmi_err[1]) @ np.diag([np.exp(1j * theta), 1.0]) @ Z.coupler(mmi_err[0])
    return t * Z.amp(loss_db)


def _embed_transposed(t, i, j, n):
    m = np.eye(n, dtype=complex)
    m[np.ix_([i, j], [i, j])] = np.asarray(t).T
    return m


MUTANTS = [
    ("F1", "耦合器寫成實數矩陣 [[1,1],[1,−1]]/√2（少了跨接的 90°）", "H", np.array([[1, 1], [1, -1]]) / np.sqrt(2)),
    ("F2", "耦合器忘了除以 √2", "H", np.array([[1, 1j], [1j, 1]])),
    ("F3", "直通功率寫成 sin²θ（少了 /2）", "bar_power", lambda th: np.sin(th) ** 2),
    ("F4", "損耗把 dB 當功率乘在振幅上（10^(−dB/10)）", "amp", lambda d: 10 ** (-d / 10.0) if d else 1.0),
    ("F5", "θ 相位段放到另一條臂", "T2", _t2_wrong_arm),
    ("F6", "φ 相位段放到輸出端（第二個耦合器之後）", "T2", _t2_phi_after),
    ("F7", "嵌入大矩陣時把 2×2 轉置", "embed", _embed_transposed),
]


def run_mutants():
    rows = []
    for mid, desc, attr, value in MUTANTS:
        orig = getattr(Z, attr)
        setattr(Z, attr, value)
        try:
            res = run_suite()
        finally:
            setattr(Z, attr, orig)
        caught = sorted(k for k, (ok, _) in res.items() if not ok)
        rows.append(dict(id=mid, fault=desc, caught_by=caught, detected=bool(caught)))
    return rows


# ---------- 與 M0 s2 FDTD 對照 ----------
CASE_NAME = {"t0": "切換 θ=0", "tpi": "直通 θ=π", "tpi2": "分光 θ=π/2", "comb": "合光 θ=π/2"}


def model_layout_out(info):
    """用共用模型算 M0 s2 某個案例的輸出功率（佈局埠順序 out1, out2）。"""
    v_layout = np.array([a[0] + 1j * a[1] for _, a in sorted(info["sources"], key=lambda s: s[0])])  # y 由小到大＝in1, in2
    if len(v_layout) == 1:
        v_layout = np.array([v_layout[0], 0])
    y = Z.layout_to_model(Z.T2(info["theta"], 0.0) @ Z.layout_to_model(v_layout))
    return np.abs(y) ** 2


def compare():
    s2 = json.loads((S2 / "m0_s2_result.json").read_text(encoding="utf-8"))["cases"]
    rows = []
    for c in ("t0", "tpi", "tpi2", "comb"):
        info = json.loads((S2 / f"field_{c}.json").read_text(encoding="utf-8"))
        m = model_layout_out(info)
        f = np.array(s2[c]["p_norm"])
        row = dict(case=c, name=CASE_NAME[c], theta=info["theta"], model=m.tolist(), fdtd_norm=f.tolist(),
                   fdtd_total=s2[c]["total"], max_abs_diff=float(np.abs(m - f).max()),
                   model_vs_s2_ideal=float(np.abs(m - np.array(s2[c]["ideal"])).max()))
        if len(info["sources"]) == 1:                     # 單一輸入：out1 是直通埠
            th_eff = float(Z.theta_for_bar(f[0]))
            row["theta_eff_deg"] = math.degrees(th_eff)
            row["theta_err_deg"] = math.degrees(th_eff) - math.degrees(info["theta"])
        else:
            row["alpha"] = info["alpha"]
        rows.append(row)
    return rows


def fit_nonideal(rows):
    """用三個參數（θ 偏移 δ、兩顆耦合器的分光誤差 ε1、ε2）擬合三個單一輸入案例的直通功率。
    三個參數對三個數據點，是「等效」重現，不代表找到物理原因；並列單顆 MMI 的 FDTD 分光誤差供比較。"""
    from scipy.optimize import least_squares
    single = [r for r in rows if "theta_eff_deg" in r]

    def resid(p):
        return [abs(Z.T2(r["theta"] + p[0], 0.0, mmi_err=(p[1], p[2]))[1, 1]) ** 2 - r["fdtd_norm"][0] for r in single]

    fit = least_squares(resid, [0.03, 0.02, -0.02], bounds=([-0.5, -0.2, -0.2], [0.5, 0.2, 0.2]))
    mmi = json.loads((S2 / "m0_s2_result.json").read_text(encoding="utf-8"))["cases"]["mmi"]
    return dict(delta_deg=math.degrees(fit.x[0]), eps=sorted(fit.x[1:].tolist(), key=abs, reverse=True),
                max_resid=float(np.abs(fit.fun).max()), n_points=len(single),
                single_mmi_eps=mmi["p_out"][0] / sum(mmi["p_out"]) - 0.5)


def figure(rows):
    th = np.linspace(0, 2 * np.pi, 361)
    bar = np.array([abs(Z.T2(t)[0, 0]) ** 2 for t in th])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.3))
    a1.plot(np.degrees(th), bar, color="#1f6feb", lw=2, label="直通 sin²(θ/2)（in1→out1）")
    a1.plot(np.degrees(th), 1 - bar, color="#d9480f", lw=2, label="交叉 cos²(θ/2)（in1→out2）")
    for r in rows:
        if "theta_eff_deg" in r:
            x = math.degrees(r["theta"])
            a1.plot(x, r["fdtd_norm"][0], "o", ms=9, mfc="none", mec="#1f6feb", mew=2)
            a1.plot(x, r["fdtd_norm"][1], "s", ms=9, mfc="none", mec="#d9480f", mew=2)
    a1.plot([], [], "ko", mfc="none", label="M0 s2 FDTD（除以總穿透後）")
    a1.set(xlabel="θ（度）", ylabel="輸出功率比", xlim=(-8, 368), ylim=(-0.03, 1.03), xticks=range(0, 361, 45),
           title="(a) 單一輸入：θ 決定直通／交叉")
    a1.grid(alpha=0.3)
    a1.legend(fontsize=9, loc="center right")

    al = np.linspace(0, 2 * np.pi, 361)
    p = np.array([np.abs(Z.layout_to_model(Z.T2(np.pi / 2) @ Z.layout_to_model(np.array([1, np.exp(1j * a)]) / np.sqrt(2)))) ** 2
                  for a in al])
    a2.plot(np.degrees(al), p[:, 0], color="#1f6feb", lw=2, label="out1")
    a2.plot(np.degrees(al), p[:, 1], color="#d9480f", lw=2, label="out2")
    for r in rows:
        if "alpha" in r:
            x = math.degrees(r["alpha"])
            a2.plot(x, r["fdtd_norm"][0], "o", ms=9, mfc="none", mec="#1f6feb", mew=2)
            a2.plot(x, r["fdtd_norm"][1], "s", ms=9, mfc="none", mec="#d9480f", mew=2, label="M0 s2 FDTD 合光")
    a2.set(xlabel="in2 相對 in1 的相位 α（度）", ylabel="輸出功率比", xlim=(0, 360), ylim=(-0.03, 1.03),
           xticks=range(0, 361, 45), title="(b) 兩路等幅輸入、θ = π/2：相對相位決定合到哪一路")
    a2.grid(alpha=0.3)
    a2.legend(fontsize=9, loc="center right")
    fig.tight_layout()
    path = rt.fig_path("m0_s3", "theta_sweep.png")
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def main():
    tests = run_suite()
    mutants = run_mutants()
    rows = compare()
    fit = fit_nonideal(rows)
    fig = figure(rows)
    tests_json = dict(tests=[dict(name=k, passed=ok, doc=d) for k, (ok, d) in tests.items()],
                      n_pass=sum(ok for ok, _ in tests.values()), n_total=len(tests),
                      mutants=mutants, n_detected=sum(m["detected"] for m in mutants), n_mutants=len(mutants),
                      numpy=np.__version__, python=sys.version.split()[0])
    (OUT / "tests.json").write_text(json.dumps(tests_json, ensure_ascii=False, indent=1), encoding="utf-8")
    res = dict(tests=dict(n_pass=tests_json["n_pass"], n_total=tests_json["n_total"],
                          n_detected=tests_json["n_detected"], n_mutants=tests_json["n_mutants"]),
               compare=rows, fit=fit, max_abs_diff=max(r["max_abs_diff"] for r in rows),
               model_vs_s2_ideal=max(r["model_vs_s2_ideal"] for r in rows), figs=[rt.rel(fig)])
    (OUT / "m0_s3_result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"單元測試 {tests_json['n_pass']}/{tests_json['n_total']} 通過")
    for k, (ok, _) in tests.items():
        print(f"  {'PASS' if ok else 'FAIL'} {k}")
    print(f"故障注入 {tests_json['n_detected']}/{tests_json['n_mutants']} 被抓到")
    for m in mutants:
        print(f"  {m['id']} {'抓到' if m['detected'] else '漏掉'} {m['caught_by']}")
    for r in rows:
        extra = f" θ_eff {r['theta_eff_deg']:.2f}°（差 {r['theta_err_deg']:+.2f}°）" if "theta_eff_deg" in r else ""
        print(f"  {r['case']:5s} 模型 {r['model'][0]:.4f}/{r['model'][1]:.4f}  FDTD {r['fdtd_norm'][0]:.4f}/{r['fdtd_norm'][1]:.4f}"
              f"  差 {r['max_abs_diff']:.4f}  模型對 s2 理想 {r['model_vs_s2_ideal']:.1e}{extra}")
    print(f"等效擬合 δ {fit['delta_deg']:+.2f}°  ε {fit['eps'][0]:+.4f}/{fit['eps'][1]:+.4f}  殘差 {fit['max_resid']:.1e}"
          f"  單顆 MMI ε {fit['single_mmi_eps']:+.5f}")


if __name__ == "__main__":
    main()
