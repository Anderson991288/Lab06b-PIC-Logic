"""M0 s2：整理 E2（模態）與 E3（光場）結果，與理論及參考數值比較，並畫光場圖。

用途：
  1. 每個 Meep 案例：兩輸出埠功率比、總穿透（超額損耗 dB）、消光比 dB，與理想 MZI（sin²／cos²）比較。
  2. MMI 解析度收斂（16、24、32 px/µm）。
  3. 與參考研究數值並列（sources/reference_fields.json）。
  4. 出圖：單顆 2×2 MMI 光場、MZI 四種狀態光場。
輸入：out/modes.json、out/field_*.json、out/field_*.npz、../../sources/reference_fields.json。
輸出：out/m0_s2_result.json；course/figures/m0_s2/mmi_field.png、mzi_fields.png。
執行：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m0_s2\\analyze_fields.py
"""
import sys
import json
import math
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import runtime as rt

rt.setup()
import numpy as np                      # noqa: E402
import matplotlib.pyplot as plt         # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
REF = json.loads((rt.ROOT / "sources" / "reference_fields.json").read_text(encoding="utf-8"))
MODES = json.loads((OUT / "modes.json").read_text(encoding="utf-8"))
MMI = json.loads((OUT / "mmi_geometry.json").read_text(encoding="utf-8"))
CASES = ["mmi", "t0", "tpi", "tpi2", "comb"]
LABEL = {"mmi": "單顆 2×2 MMI，光從 in1 進", "t0": "(a) 切換：in1，θ = 0", "tpi": "(b) 切換：in1，θ = π",
         "tpi2": "(c) 分光：in1，θ = π/2", "comb": "(d) 合光：in1＋in2 相干，θ = π/2"}


def db(x):
    return 10 * math.log10(x) if x > 0 else float("-inf")


def load(case, tag=""):
    p = OUT / f"field_{case}{tag}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def summarize(f):
    p = f["p_out"]
    tot = sum(p)
    s = dict(p_out=p, total=tot, excess_loss_db=-db(tot), p_norm=[x / tot for x in p],
             extinction_db=db(max(p) / min(p)) if min(p) > 0 else None, runtime_s=f["runtime_s"], res=f["res"])
    if f.get("ideal_p_out"):
        s["ideal"] = f["ideal_p_out"]
        s["max_abs_err_norm"] = max(abs(a - b) for a, b in zip(s["p_norm"], f["ideal_p_out"]))
    return s


def draw(ax, case, f):
    d = np.load(OUT / f"field_{case}.npz")
    I, ext = d["I"], d["ext"]
    x0, x1 = f["x_range"]
    ix = int((x0 + 3.0 - ext[0]) / (ext[1] - ext[0]) * (I.shape[0] - 1))      # 輸入波導處的峰值做歸一
    norm = I[ix].max() * len(f["sources"])
    im = ax.imshow(I.T / norm, origin="lower", extent=ext, cmap="jet", vmin=0, vmax=0.5, aspect="auto",
                   interpolation="bilinear")
    ax.set_xlim(x0, x1)
    ax.set_ylim(-f["y_half"], f["y_half"])
    py = MMI["ports"]["in2"][1]
    for t, x, y, ha in (("in1", x0 + 1, -py - 2.4, "left"), ("in2", x0 + 1, py + 1.2, "left"),
                        ("out1", x1 - 1, -py - 2.4, "right"), ("out2", x1 - 1, py + 1.2, "right")):
        ax.text(x, y, t, color="w", fontsize=9, ha=ha)
    for xm in f["mmi_origins"]:
        ax.text(xm + MMI["body_length_um"] / 2, -MMI["body_width_um"] / 2 - 0.6, "2×2 MMI", color="w", ha="center",
                va="top", fontsize=8.5)
    if case != "mmi":
        xa = f["mmi_origins"][0] + MMI["ports"]["out1"][0] + 20.0
        ax.text(xa + f["arm_L"] / 2, f["y_half"] - 7.0, "θ 段（上臂）", color="w", ha="center", fontsize=8.5)
    p = f["p_out"]
    ax.set_title(f"{LABEL[case]}　→　out1 {p[0]:.3f}／out2 {p[1]:.3f}（總穿透 {sum(p):.3f}）", fontsize=11)
    ax.set_ylabel("y (µm)")
    return im


def main():
    fields = {c: load(c) for c in CASES}
    missing = [c for c, f in fields.items() if f is None]
    if missing:
        raise SystemExit(f"缺少 Meep 結果：{missing}（先跑 run_fields.sh）")
    res = {"step": "M0 s2", "date": time.strftime("%Y-%m-%d"),
           "modes": {k: MODES[k] for k in ("te0", "eim", "single_mode_max_width_um", "first_multimode_width_um",
                                           "te1_at_W", "guide_margin", "mesh_convergence", "width_sweep")},
           "sim": {k: fields["t0"][k] for k in ("n_core", "n_clad", "gamma", "arm_L", "res", "meep")},
           "dn_theta_pi": fields["tpi"]["dn"], "alpha_comb": fields["comb"]["alpha"],
           "cases": {c: summarize(f) for c, f in fields.items()},
           "mmi_geometry": {k: MMI[k] for k in ("body_width_um", "body_length_um", "ports", "source")}}
    conv = []
    for tag, r in (("_r16", 16), ("", None), ("_r32", 32)):
        f = load("mmi", tag)
        if f:
            conv.append(dict(res=f["res"], p_out=f["p_out"], total=sum(f["p_out"]), runtime_s=f["runtime_s"]))
    res["mmi_convergence"] = sorted(conv, key=lambda c: c["res"])
    rc = REF["cases"]
    res["reference"] = {c: dict(p_out=rc[c]["p_out"], total=sum(rc[c]["p_out"]),
                                extinction_db=db(max(rc[c]["p_out"]) / min(rc[c]["p_out"]))) for c in rc}
    res["reference"]["mmi"] = dict(p_out=[REF["mmi2x2"]["bar"] * REF["mmi2x2"]["T"], REF["mmi2x2"]["cross"] * REF["mmi2x2"]["T"]],
                                   total=REF["mmi2x2"]["T"])
    res["reference_method"] = REF["method"]

    fig, ax = plt.subplots(figsize=(11, 3.4))
    im = draw(ax, "mmi", fields["mmi"])
    ax.set_xlabel("x (µm)")
    fig.colorbar(im, ax=ax, shrink=0.9, label="|E|²（相對輸入）")
    fig.savefig(rt.fig_path("m0_s2", "mmi_field.png"), dpi=130, bbox_inches="tight")
    plt.close(fig)

    order = ["t0", "tpi", "tpi2", "comb"]
    fig, axs = plt.subplots(len(order), 1, figsize=(13, 13), sharex=True)
    for a, c in zip(axs, order):
        im = draw(a, c, fields[c])
    axs[-1].set_xlabel("x (µm)")
    fig.colorbar(im, ax=axs, shrink=0.6, label="|E|²（相對單一輸入）")
    fig.suptitle("MZI 四種狀態的光場（Meep 2D，CW 1550 nm，時間平均 |E|²）", fontsize=13, y=0.93)
    fig.savefig(rt.fig_path("m0_s2", "mzi_fields.png"), dpi=110, bbox_inches="tight")
    plt.close(fig)
    res["figs"] = [rt.rel(rt.fig_path("m0_s2", n)) for n in ("wg_modes.png", "mmi_field.png", "mzi_fields.png")]
    (OUT / "m0_s2_result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for c, s in res["cases"].items():
        print(f"{c:5s} out {s['p_out'][0]:.4f}/{s['p_out'][1]:.4f} total {s['total']:.4f} "
              f"ER {s['extinction_db'] if s['extinction_db'] is None else round(s['extinction_db'], 1)} dB "
              f"err {s.get('max_abs_err_norm')}")
    print("conv", [(c["res"], round(c["total"], 4)) for c in res["mmi_convergence"]])


if __name__ == "__main__":
    main()
