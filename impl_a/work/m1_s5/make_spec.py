"""M1 s5：把 B7 的固定光路、介面與讀取規則寫成規格，與功能設定（相位）分開交給 M2。

產生（課程根目錄 spec/）：
  pic_spec.json    固定的部分：光路（OPS）、5 入 5 出光學埠、14 個相位控制通道、讀取規則、驗收條件與容差。
                   不放任何相位數值，只記相位檔的路徑與 SHA-256（相位檔一改，雜湊就對不上）。
  truth_table.json 交接用的理想真值表：5 種功能 × 16 組，每列的目標、ΔP、判定（M2 s2 電路模擬、M3 重建都拿它比）。
  b7_spec.png      規格的圖：接線、埠名與每顆 MZI 的通道名稱。
相位設定仍只存在 sources/b7_phases.json（M1 s4），本程式不複製。
輸入：common/b7.py、sources/b7_phases.json、../m1_s4/out/m1_s4_result.json。
執行：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m1_s5\\make_spec.py
"""
import sys
import json
import hashlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import runtime as rt

rt.setup()
import numpy as np                      # noqa: E402
import matplotlib.pyplot as plt         # noqa: E402
from common import b7                   # noqa: E402
from common.b7plot import draw_frame    # noqa: E402

HERE = Path(__file__).resolve().parent
SPEC = rt.ROOT / "spec"
SPEC.mkdir(exist_ok=True)
GATES = ["AND2", "OR2", "XOR2", "AND4", "OR4"]
S4 = json.loads((HERE.parent / "m1_s4" / "out" / "m1_s4_result.json").read_text(encoding="utf-8"))


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build_spec():
    ph_rel = rt.rel(b7.PHASE_FILE)
    mc = S4["nonideal"]["gates"]
    ok_sigma = max(s for s in S4["nonideal"]["sigmas"] if all(mc[g]["mc_pass"][str(s)] == 1.0 for g in GATES))
    return dict(
        title="B7 光邏輯 PIC 功能與介面規格",
        version=1, date="2026-10-31",
        status="M1 交給 M2 的固定規格；相位數值另存於相位檔",
        core=dict(name="B7", n_modes=b7.N_MODES, n_mzi=len(b7.OPS), n_layers=b7.N_LAYERS,
                  ops=[list(o) for o in b7.OPS],
                  ops_meaning="第 k 項 (p, layer)：MZI k+1 跨 rail p、p+1，位於第 layer+1 層",
                  mzi_model="T(θ, φ) = H·diag(e^{iθ},1)·H·diag(e^{iφ},1)，H = [[1,i],[i,1]]/√2；相位段在上臂（rail p，局部索引 0）"),
        model=dict(loss_db_per_mzi=0, R_amplitude=b7.R_AMP, input_bit_amplitude=[0, 1], coherent_inputs=True,
                   readout_ports=[f"out{j}" for j in b7.READOUT],
                   decision="ΔP = |o2|² − |o4|²；> 0 判 1、< 0 判 0、= 0 為邊界"),
        optical_inputs=[dict(port=f"in{r}", rail=r, signal=s, amplitude="0/1" if r < 4 else b7.R_AMP)
                        for r, s in enumerate(b7.IN_SIGNALS)],
        optical_outputs=[dict(port=f"out{r}", rail=r, signal=s, role="readout" if r in b7.READOUT else "monitor")
                         for r, s in enumerate(b7.OUT_SIGNALS)],
        phase_controls=[dict(channel=f"M{k + 1}_{ph}", mzi=k + 1, phase=ph, phase_index=k, rail=p, layer=layer + 1,
                             electrical="heater 訊號端＋回流端", drive="需校正（相位 → 電壓）")
                        for k, (p, layer) in enumerate(b7.OPS) for ph in ("phi", "theta")],
        functions=GATES,
        phase_settings=dict(file=ph_rel, sha256=sha256(b7.PHASE_FILE),
                            note="功能＝相位檔中的一組 θ1–θ7、φ1–φ7；換功能只換相位，不改光路與讀取"),
        truth_table=dict(file="spec/truth_table.json", rows=16 * len(GATES)),
        acceptance=dict(functional="每種功能 16 組全對，5 種共 80 筆",
                        ideal_margin={g: round(S4["gates"][g]["margin"], 4) for g in GATES},
                        phase_accuracy_rad=ok_sigma,
                        phase_accuracy_note=f"M1 s4 Monte Carlo：14 個相位各自誤差 σ ≤ {ok_sigma} rad 時 5 種功能全對；XOR2 最敏感",
                        layout="模型與佈局共用 OPS、埠名與通道名；佈局後重跑 80 筆"),
        tools=dict(circuit="IPKISS／Caphe（CORNERSTONE SOI220 2×2 MMI）", layout="IPKISS＋Python", review="KLayout",
                   drc="CORNERSTONE 規則檔＋光路連接與電氣連接檢查"),
    )


def build_truth():
    rows = []
    for g in GATES:
        th, ph = b7.load_phases()[g]
        tt = b7.truth_table(b7.unitary(th, ph), g)
        for i, x in enumerate(b7.ALL_BITS):
            rows.append(dict(function=g, bits=b7.bits_str(x), target=int(tt["target"][i]),
                             delta=float(tt["delta"][i]), bit=int(tt["bit"][i])))
    return dict(note="理想模型（無損耗、R=3）的交接真值表；ΔP 依相位檔全精度計算", phase_sha256=sha256(b7.PHASE_FILE), rows=rows)


def fig_spec():
    fig, ax = plt.subplots(figsize=(12.5, 5.2))
    ys = draw_frame(ax, mzi_label=lambda k: f"M{k + 1}_phi\nM{k + 1}_theta")
    for r, y in ys.items():
        ax.text(-0.95, y, f"in{r}", ha="right", va="center", fontsize=9.5, color="#555")
        ax.text(10.75, y, f"out{r}" + ("（PD）" if r in b7.READOUT else ""), va="center", fontsize=9.5, color="#555")
    ax.set_xlim(-1.9, 12.2)
    ax.set_ylim(-0.85, 4.6)
    ax.axis("off")
    ax.set_title("B7 規格：光學埠 in0–in4／out0–out4、14 個相位通道、讀取 out1（o2）與 out3（o4）", fontsize=12.5)
    path = rt.fig_path("m1_s5", "b7_spec.png")
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return path


def main():
    spec = build_spec()
    truth = build_truth()
    (SPEC / "pic_spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    (SPEC / "truth_table.json").write_text(json.dumps(truth, ensure_ascii=False, indent=1), encoding="utf-8")
    fig = fig_spec()
    print("wrote spec/pic_spec.json、spec/truth_table.json、", rt.rel(fig))
    print("phase sha256", spec["phase_settings"]["sha256"][:16], "相位精度", spec["acceptance"]["phase_accuracy_rad"], "rad")
    print("80 筆中判定正確", sum(r["bit"] == r["target"] for r in truth["rows"]))


if __name__ == "__main__":
    main()
