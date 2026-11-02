"""M2 s1：PIC 上做什麼、外部設備做什麼——功能方塊圖、I/O 表，以及外部設備要做到多準。

步驟：
  1. 由 spec/pic_spec.json 產生 I/O 表（10 個光學埠＋14 個 heater 通道＋共用回流），標明晶片上／晶片外的責任。
  2. 外部設備容忍度（理想 B7、5 種功能、80 筆全對為準）：
     a. 兩顆 PD 響應度不平衡（解析解）      b. R 振幅誤差               c. R 相對資料光的相位誤差
     d. 調變器消光比（0 不是全暗）           e. 4 路資料光各自的相位誤差（Monte Carlo）
     f. 4 路資料光各自的振幅誤差（Monte Carlo）
  3. 出圖：PIC 邊界功能方塊圖、容忍度掃描圖。
輸入：spec/pic_spec.json、sources/b7_phases.json、common/b7.py。
輸出：spec/io_table.json、spec/external_requirements.json、out/m2_s1_result.json；
      course/figures/m2_s1/pic_boundary.png、tolerance.png。
執行：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m2_s1\\pic_boundary.py
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
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402
from common import b7                   # noqa: E402

OUT = rt.out_dir(__file__)
SPEC = json.loads((rt.ROOT / "spec" / "pic_spec.json").read_text(encoding="utf-8"))
GATES = SPEC["functions"]
PH = b7.load_phases()
US = {g: b7.unitary(*PH[g]) for g in GATES}
TGT = {g: b7.target(g) for g in GATES}
N_MC = 500
SIG_PHASE = [0.01, 0.02, 0.05, 0.1, 0.2]
SIG_AMP = [0.01, 0.02, 0.05, 0.1, 0.2]


def io_table():
    rows = []
    for i in SPEC["optical_inputs"]:
        rows.append(dict(kind="光學輸入", port=i["port"], signal=i["signal"], on_chip="邊緣耦合器（EC）",
                         off_chip="雷射分光＋調變器（資料）" if i["signal"] != "R" else "雷射分光＋衰減／相位設定（參考光）"))
    for o in SPEC["optical_outputs"]:
        rows.append(dict(kind="光學輸出", port=o["port"], signal=o["signal"], on_chip="邊緣耦合器（EC）",
                         off_chip="平衡光偵測器＋比較器" if o["role"] == "readout" else "監看光偵測器（除錯、校正）"))
    for c in SPEC["phase_controls"]:
        rows.append(dict(kind="電氣（heater）", port=f'PAD_{c["channel"]}', signal=c["channel"], on_chip="TiN heater＋接墊",
                         off_chip="DAC／電流源（相位 → 驅動值需校正）"))
    rows.append(dict(kind="電氣（回流）", port="PAD_GND", signal="GND", on_chip="共用回流接墊（數量於佈線時決定）",
                     off_chip="驅動器地線"))
    return rows


# ---------- 容忍度 ----------
def outputs(g, x, r_scale=1.0, r_phase=0.0, zero_amp=0.0, data_phase=None, data_amp=None):
    """單一輸入 x 的五路輸出光場；可加入各種外部誤差。"""
    v = np.array([(1.0 if b else zero_amp) for b in x] + [b7.R_AMP * r_scale * np.exp(1j * r_phase)], dtype=complex)
    if data_amp is not None:
        v[:4] *= np.where(np.array(x) > 0, data_amp, 1.0)
    if data_phase is not None:
        v[:4] *= np.exp(1j * data_phase)
    return US[g] @ v


def margin(g, **kw):
    """5 種功能之一的最小有號 ΔP（> 0 表示 16 組全對）。"""
    dp = np.array([b7.delta_p(outputs(g, x, **kw)) for x in b7.ALL_BITS])
    return float((dp * (2 * TGT[g] - 1)).min())


def pd_imbalance():
    """o2 的 PD 響應度為 (1+η) 倍時仍全對的 η 範圍（解析）：目標 1 需 η > P4/P2 − 1，目標 0 需 η < P4/P2 − 1。"""
    res = {}
    for g in GATES:
        y = np.array([outputs(g, x) for x in b7.ALL_BITS])
        P2, P4 = np.abs(y[:, 1]) ** 2, np.abs(y[:, 3]) ** 2
        ratio = P4 / P2 - 1
        res[g] = dict(low=float(ratio[TGT[g] == 1].max()), high=float(ratio[TGT[g] == 0].min()))
    return res


def scan(name, values, key):
    curves = {g: [margin(g, **{key: v}) for v in values] for g in GATES}
    ok = np.all([np.array(c) > 0 for c in curves.values()], axis=0)
    return dict(name=name, values=list(map(float, values)), curves=curves, ok=ok.tolist())


def contiguous(values, ok, center):
    """包含 center 的連續「全對」區間。"""
    v, ok = np.array(values), np.array(ok)
    i0 = int(np.argmin(np.abs(v - center)))
    if not ok[i0]:
        return None
    lo = hi = i0
    while lo > 0 and ok[lo - 1]:
        lo -= 1
    while hi < len(v) - 1 and ok[hi + 1]:
        hi += 1
    return [float(v[lo]), float(v[hi])]


def monte_carlo(kind, sigmas, seed):
    rng = rt.rng(seed)
    out = {}
    for s in sigmas:
        draws = rng.normal(0, s, (N_MC, 4))
        per = {}
        for g in GATES:
            if kind == "phase":
                per[g] = float(np.mean([margin(g, data_phase=d) > 0 for d in draws]))
            else:
                per[g] = float(np.mean([margin(g, data_amp=1 + d) > 0 for d in draws]))
        out[str(s)] = per
    return out


# ---------- 圖 ----------
def box(ax, x, y, w, h, text, fc, ec="#333", fs=10, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02", fc=fc, ec=ec, lw=1.3))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, weight="bold" if bold else "normal")


def arrow(ax, x0, y0, x1, y1, color="#555", lw=1.4):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="-|>", color=color, lw=lw))


def fig_boundary():
    fig, ax = plt.subplots(figsize=(14, 7.2))
    ax.add_patch(Rectangle((5.0, 0.6), 4.6, 6.0, fill=False, ec="#b3261e", lw=2.2, ls="--"))
    ax.text(7.3, 6.75, "PIC（本課程設計的晶片）", ha="center", fontsize=12.5, color="#b3261e", weight="bold")
    box(ax, 0.2, 3.3, 1.4, 0.9, "CW 雷射\n1550 nm", "#fff3bf")
    box(ax, 1.9, 3.3, 1.0, 0.9, "1×5 分光\n1:1:1:1:9", "#fff3bf", fs=8.5)
    labels = ["x1", "x2", "x3", "x4", "R"]
    ys = [5.6, 4.8, 4.0, 3.2, 2.0]
    for lab, y in zip(labels, ys):
        if lab == "R":
            box(ax, 3.2, y - 0.3, 1.5, 0.6, "衰減＋相位\n（振幅 3）", "#ffe8cc", fs=9)
        else:
            box(ax, 3.2, y - 0.3, 1.5, 0.6, f"調變器 {lab}", "#e7f5ff", fs=9.5)
        arrow(ax, 2.9, 3.75, 3.2, y)
        arrow(ax, 4.7, y, 5.25, y, color="#1f6feb")
        ax.text(5.3, y + 0.12, f"EC in{labels.index(lab)}", fontsize=8.5, color="#1f6feb")
    arrow(ax, 1.6, 3.75, 1.9, 3.75)
    box(ax, 6.0, 1.7, 2.2, 4.3, "B7\n7 顆 MZI\n5 條波導、4 層\n14 個 heater", "#f3f0e7", fs=11, bold=True)
    for y in ys:
        arrow(ax, 5.25, y, 6.0, y, color="#1f6feb")
    outs = ["o1", "o2", "o3", "o4", "o5"]
    yo = [5.6, 4.8, 4.0, 3.2, 2.0]
    for k, (lab, y) in enumerate(zip(outs, yo)):
        arrow(ax, 8.2, y, 9.85, y, color="#2b8a3e" if k in b7.READOUT else "#999")
        ax.text(8.35, y + 0.12, f"EC out{k}", fontsize=8.5, color="#2b8a3e" if k in b7.READOUT else "#888")
        if k in b7.READOUT:
            box(ax, 9.85, y - 0.3, 1.0, 0.6, f"PD {lab}", "#d3f9d8", fs=9.5)
        else:
            box(ax, 9.85, y - 0.25, 1.0, 0.5, f"監看 {lab}", "#f1f3f5", fs=8.5)
    box(ax, 11.2, 3.65, 1.3, 1.3, "相減\nTIA\n比較器", "#d3f9d8", fs=9.5)
    arrow(ax, 10.85, 4.8, 11.2, 4.5, color="#2b8a3e")
    arrow(ax, 10.85, 3.2, 11.2, 3.9, color="#2b8a3e")
    box(ax, 12.85, 3.95, 0.9, 0.7, "y\n0／1", "#d3f9d8", fs=10, bold=True)
    arrow(ax, 12.5, 4.3, 12.85, 4.3, color="#2b8a3e")
    box(ax, 6.0, -0.6, 2.2, 0.75, "Heater 驅動\n14 通道 DAC＋GND", "#ffe3e3", fs=9.5)
    for dx in np.linspace(6.2, 8.0, 7):
        ax.plot([dx, dx], [0.15, 1.7], color="#c92a2a", lw=1.0)
    ax.text(8.4, 0.9, "14 個接墊\n＋共用回流", fontsize=8.5, color="#c92a2a")
    box(ax, 0.2, -0.6, 4.5, 0.75, "相位設定檔（功能）→ 校正表 → 驅動值", "#f8f0fc", fs=9.5)
    arrow(ax, 4.7, -0.22, 6.0, -0.22, color="#ae3ec9")
    ax.set_xlim(0, 14)
    ax.set_ylim(-0.8, 7.1)
    ax.axis("off")
    path = rt.fig_path("m2_s1", "pic_boundary.png")
    fig.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return path


def fig_tol(scans, pdb):
    cols = {"AND2": "#1f6feb", "OR2": "#2b8a3e", "XOR2": "#c92a2a", "AND4": "#ae3ec9", "OR4": "#f59f00"}
    fig, axs = plt.subplots(1, 4, figsize=(16, 4.2))
    xs = {"r_scale": ("R 振幅倍率（1 = 振幅 3）", 1), "r_phase": ("R 相對資料光的相位（度）", 180 / math.pi),
          "er": ("調變器消光比（dB）", 1)}
    for ax, sc in zip(axs[:3], scans):
        lab, f = xs[sc["key"]]
        for g in GATES:
            ax.plot(np.array(sc["values"]) * f, sc["curves"][g], color=cols[g], lw=1.8, label=g)
        ax.axhline(0, color="#222", lw=1)
        ax.set(xlabel=lab, ylabel="最小有號 ΔP")
        ax.grid(alpha=0.3)
        ax.set_title(sc["name"], fontsize=11)
    axs[0].legend(fontsize=8.5)
    ax = axs[3]
    cap = 100.0                                        # 上限超過 100% 的畫到 100% 並標「無上限」
    for i, g in enumerate(GATES):
        hi = min(pdb[g]["high"] * 100, cap)
        ax.plot([pdb[g]["low"] * 100, hi], [i, i], color=cols[g], lw=6, solid_capstyle="butt")
        ax.text(pdb[g]["low"] * 100 - 2, i, f'{pdb[g]["low"] * 100:+.0f}%', ha="right", va="center", fontsize=8.5)
        ax.text(hi + 2, i, "無上限" if pdb[g]["high"] * 100 > cap else f'{pdb[g]["high"] * 100:+.0f}%', va="center", fontsize=8.5)
    ax.set_xlim(-75, 125)
    ax.axvline(0, color="#222", lw=1)
    ax.set_yticks(range(len(GATES)), GATES)
    ax.set(xlabel="o2 的 PD 響應度偏差 η（%）", title="(d) PD 不平衡的容許範圍")
    ax.grid(alpha=0.3, axis="x")
    fig.tight_layout()
    path = rt.fig_path("m2_s1", "tolerance.png")
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path


def main():
    io = io_table()
    pdb = pd_imbalance()
    s_r = scan("(a) R 振幅誤差", np.linspace(0.5, 1.5, 201), "r_scale")
    s_r["key"] = "r_scale"
    s_p = scan("(b) R 相位誤差", np.radians(np.linspace(-60, 60, 241)), "r_phase")
    s_p["key"] = "r_phase"
    ers = np.linspace(5, 40, 141)
    s_e = dict(name="(c) 調變器消光比", values=ers.tolist(), key="er",
               curves={g: [min(margin(g, zero_amp=10 ** (-e / 20)), margin(g, zero_amp=-10 ** (-e / 20))) for e in ers]
                       for g in GATES})
    s_e["ok"] = np.all([np.array(c) > 0 for c in s_e["curves"].values()], axis=0).tolist()
    mc_p = monte_carlo("phase", SIG_PHASE, 6)
    mc_a = monte_carlo("amp", SIG_AMP, 7)
    figs = [fig_boundary(), fig_tol([s_r, s_p, s_e], pdb)]

    r_range = contiguous(s_r["values"], s_r["ok"], 1.0)
    p_range = contiguous(s_p["values"], s_p["ok"], 0.0)
    er_ok = [e for e, ok in zip(s_e["values"], s_e["ok"]) if ok]
    er_min = min(er_ok) if er_ok and all(s_e["ok"][s_e["values"].index(er_ok[0]):]) else None
    eta = [max(v["low"] for v in pdb.values()), min(v["high"] for v in pdb.values())]
    sig_p = max([s for s in SIG_PHASE if all(v == 1.0 for v in mc_p[str(s)].values())], default=None)
    sig_a = max([s for s in SIG_AMP if all(v == 1.0 for v in mc_a[str(s)].values())], default=None)
    worst = {k: min(GATES, key=lambda g: fn(g)) for k, fn in (
        ("pd", lambda g: min(-pdb[g]["low"], pdb[g]["high"])),
        ("r_scale", lambda g: min(s_r["curves"][g][0], s_r["curves"][g][-1])),
        ("r_phase", lambda g: min(s_p["curves"][g][0], s_p["curves"][g][-1])),
        ("er", lambda g: -next((e for e, m in zip(ers, s_e["curves"][g]) if m > 0), 99)))}
    req = dict(
        note="理想 B7、5 種功能、80 筆全對為準；每項單獨變化，其餘理想。實際系統多項同時存在，需保留餘量。",
        pd_responsivity_mismatch=dict(range=eta, unit="相對（o2 的 PD 響應度 ÷ o4 的 PD − 1）"),
        r_amplitude_scale=dict(range=r_range, unit="倍率（1 = 振幅 3）"),
        r_phase_rad=dict(range=p_range, unit="rad"),
        modulator_extinction_db_min=er_min,
        data_phase_sigma_rad=sig_p, data_amp_sigma=sig_a, monte_carlo_n=N_MC,
        heater=dict(channels=len(SPEC["phase_controls"]), range_rad=[0, 2 * math.pi],
                    accuracy_rad=SPEC["acceptance"]["phase_accuracy_rad"], drive="需校正；PDK 公開資料未提供 heater 效率"))
    (rt.ROOT / "spec" / "io_table.json").write_text(json.dumps(dict(rows=io), ensure_ascii=False, indent=1), encoding="utf-8")
    (rt.ROOT / "spec" / "external_requirements.json").write_text(json.dumps(req, ensure_ascii=False, indent=1), encoding="utf-8")
    res = dict(io=io, pd=pdb, scans=[s_r, s_p, s_e], mc_phase=mc_p, mc_amp=mc_a, requirements=req, worst=worst,
               figs=[rt.rel(f) for f in figs])
    (OUT / "m2_s1_result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"I/O 表 {len(io)} 列")
    print("PD 不平衡 η 範圍", [f"{v:+.3f}" for v in eta], {g: (round(v['low'], 3), round(v['high'], 3)) for g, v in pdb.items()})
    print("R 振幅倍率範圍", r_range, " R 相位範圍（度）", [round(math.degrees(v), 1) for v in p_range] if p_range else None)
    print("消光比最低", er_min, "dB")
    print("資料相位 σ", sig_p, mc_p)
    print("資料振幅 σ", sig_a, mc_a)
    print("最敏感", worst)


if __name__ == "__main__":
    main()
