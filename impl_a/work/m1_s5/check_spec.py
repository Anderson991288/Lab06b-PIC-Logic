"""M1 s5：獨立檢查規格——只讀 spec/ 與相位檔，用 common/mzi.py 從規格本身重建 B7，不呼叫 common/b7.py。

檢查項目（C1–C10）見 CHECKS；接著對 7 種「規格寫錯」的故障版各跑一次，確認至少一項檢查失敗。
輸入：spec/pic_spec.json、spec/truth_table.json、sources/b7_phases.json。
輸出：out/spec_check.json。
執行：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m1_s5\\check_spec.py
"""
import sys
import copy
import json
import hashlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import runtime as rt

rt.setup(plot=False)
import numpy as np                      # noqa: E402
from common import mzi as Z             # noqa: E402

ROOT = rt.ROOT
OUT = rt.out_dir(__file__)
# 功能定義在這裡重寫一次（不引用 b7.TARGETS），兩邊對不上時 C7 會失敗
FUNC = {"AND2": lambda x: x[0] & x[1], "OR2": lambda x: x[0] | x[1], "XOR2": lambda x: x[0] ^ x[1],
        "AND4": lambda x: int(all(x)), "OR4": lambda x: int(any(x))}
CHECKS = {
    "C1": "OPS 合法：相鄰兩條波導、同一層的 MZI 不共用波導、MZI 數與 OPS 一致",
    "C2": "光學埠：輸入、輸出各 n_modes 個，名稱不重複，每條 rail 剛好一個",
    "C3": "讀取埠：剛好 2 個，存在於輸出埠且角色為 readout",
    "C4": "相位通道：每顆 MZI 剛好 θ、φ 各一，名稱唯一，rail、層號、索引與 OPS 一致",
    "C5": "相位檔的 SHA-256 與規格記錄相同",
    "C6": "相位檔：每種功能都有 7 個 θ、7 個 φ，且為有限值",
    "C7": "真值表：每種功能 16 組、不重複，目標與功能定義一致",
    "C8": "從規格重建 B7 重算 80 筆：ΔP 與真值表相同、判定等於目標",
    "C9": "參考光振幅：輸入埠表與模型一致",
    "C10": "驗收餘裕：規格記錄的理想餘裕與重算的最小 |ΔP| 一致",
}


def rebuild_u(ops, n, theta, phi):
    U = np.eye(n, dtype=complex)
    for k, (p, _) in enumerate(ops):
        U = Z.embed(Z.T2(theta[k], phi[k]), p, p + 1, n) @ U
    return U


def check(spec, phase_bytes, truth):
    res = {}
    n, ops = spec["core"]["n_modes"], [tuple(o) for o in spec["core"]["ops"]]
    # C1
    ok = len(ops) == spec["core"]["n_mzi"] and all(0 <= p and p + 1 < n for p, _ in ops)
    for layer in {l for _, l in ops}:
        rails = [r for p, l in ops if l == layer for r in (p, p + 1)]
        ok &= len(rails) == len(set(rails))
    res["C1"] = ok
    # C2
    ins, outs = spec["optical_inputs"], spec["optical_outputs"]
    res["C2"] = all(len(L) == n and len({d["port"] for d in L}) == n and sorted(d["rail"] for d in L) == list(range(n))
                    for L in (ins, outs))
    # C3
    ro = spec["model"]["readout_ports"]
    role = {d["port"]: d["role"] for d in outs}
    res["C3"] = len(ro) == 2 and len(set(ro)) == 2 and all(role.get(p) == "readout" for p in ro) \
        and sum(r == "readout" for r in role.values()) == 2
    # C4
    pc = spec["phase_controls"]
    names = [c["channel"] for c in pc]
    ok = len(pc) == 2 * len(ops) and len(set(names)) == len(names)
    for k, (p, layer) in enumerate(ops):
        mine = [c for c in pc if c["mzi"] == k + 1]
        ok &= sorted(c["phase"] for c in mine) == ["phi", "theta"]
        ok &= all(c["channel"] == f"M{k + 1}_{c['phase']}" and c["phase_index"] == k and c["rail"] == p
                  and c["layer"] == layer + 1 for c in mine)
    res["C4"] = bool(ok)
    # C5
    res["C5"] = hashlib.sha256(phase_bytes).hexdigest() == spec["phase_settings"]["sha256"]
    # C6
    gates = json.loads(phase_bytes.decode("utf-8"))["gates"]
    res["C6"] = all(g in gates and len(gates[g]["theta"]) == len(ops) and len(gates[g]["phi"]) == len(ops)
                    and np.all(np.isfinite(gates[g]["theta"] + gates[g]["phi"])) for g in spec["functions"])
    # C7
    rows = truth["rows"]
    ok = len(rows) == 16 * len(spec["functions"])
    for g in spec["functions"]:
        mine = [r for r in rows if r["function"] == g]
        ok &= len(mine) == 16 and len({r["bits"] for r in mine}) == 16
        ok &= all(r["target"] == FUNC[g]([int(b) for b in r["bits"]]) for r in mine)
    res["C7"] = bool(ok)
    # C8、C10
    R = spec["model"]["R_amplitude"]
    j2, j4 = [int(p.replace("out", "")) for p in ro] if res["C3"] else (1, 3)
    ok8, ok10 = True, True
    for g in spec["functions"]:
        if g not in gates:
            ok8 = ok10 = False
            continue
        U = rebuild_u(ops, n, gates[g]["theta"], gates[g]["phi"])
        dmin = np.inf
        for r in (r for r in rows if r["function"] == g):
            y = U @ np.array([int(b) for b in r["bits"]] + [R], dtype=complex)
            dp = abs(y[j2]) ** 2 - abs(y[j4]) ** 2
            ok8 &= abs(dp - r["delta"]) < 1e-9 and int(dp > 0) == r["target"]
            dmin = min(dmin, abs(dp))
        ok10 &= abs(dmin - spec["acceptance"]["ideal_margin"].get(g, np.nan)) < 1e-3
    res["C8"], res["C10"] = bool(ok8), bool(ok10)
    # C9
    res["C9"] = [d for d in ins if d["signal"] == "R"][0]["amplitude"] == R
    return {k: bool(v) for k, v in res.items()}


def mutants(spec, phase_bytes, truth):
    out = []

    def m1(s, p, t):
        i = next(i for i, c in enumerate(s["phase_controls"]) if c["channel"] == "M3_phi")
        s["phase_controls"][i]["channel"] = "M3_theta"            # 把 M3_phi 寫成 M3_theta（重複）
        return s, p, t

    def m2(s, p, t):
        s["model"]["readout_ports"] = ["out1", "out2"]
        return s, p, t

    def m3(s, p, t):
        g = json.loads(p.decode("utf-8"))
        g["gates"]["XOR2"]["phi"][2] += 0.001                      # 有人手改了相位檔
        return s, json.dumps(g, ensure_ascii=False, indent=1).encode("utf-8"), t

    def m4(s, p, t):
        s["core"]["ops"][2] = [1, 0]                               # M3 寫成第 1 層，與 M1 共用 rail 1
        return s, p, t

    def m5(s, p, t):
        s["optical_inputs"][4]["amplitude"] = 9                    # R 寫成功率
        return s, p, t

    def m6(s, p, t):
        t["rows"][3]["target"] ^= 1                                # 真值表抄錯一列
        return s, p, t

    def m7(s, p, t):
        s["optical_outputs"][2]["port"] = "out1"                   # 輸出埠名重複
        return s, p, t

    cases = [("S1", "通道名稱重複：M3_phi 寫成 M3_theta", m1), ("S2", "讀取埠寫成 out1、out2", m2),
             ("S3", "相位檔被手改（XOR2 的 φ3 +0.001 rad），規格未更新", m3),
             ("S4", "OPS 抄錯：M3 放到第 1 層，與 M1 共用波導", m4), ("S5", "R 的振幅寫成 9（功率）", m5),
             ("S6", "真值表抄錯一列的目標", m6), ("S7", "輸出埠名重複（兩個 out1）", m7)]
    for sid, desc, fn in cases:
        s, p, t = fn(copy.deepcopy(spec), phase_bytes, copy.deepcopy(truth))
        r = check(s, p, t)
        failed = [k for k, ok in r.items() if not ok]
        out.append(dict(id=sid, fault=desc, failed_checks=failed, detected=bool(failed)))
    return out


def main():
    spec = json.loads((ROOT / "spec" / "pic_spec.json").read_text(encoding="utf-8"))
    truth = json.loads((ROOT / "spec" / "truth_table.json").read_text(encoding="utf-8"))
    phase_bytes = (ROOT / spec["phase_settings"]["file"]).read_bytes()
    res = check(spec, phase_bytes, truth)
    mut = mutants(spec, phase_bytes, truth)
    out = dict(checks=[dict(id=k, desc=CHECKS[k], ok=res[k]) for k in CHECKS], n_pass=sum(res.values()), n_checks=len(CHECKS),
               mutants=mut, n_detected=sum(m["detected"] for m in mut), n_mutants=len(mut))
    (OUT / "spec_check.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"規格檢查 {out['n_pass']}/{out['n_checks']}")
    for c in out["checks"]:
        print(f"  {'PASS' if c['ok'] else 'FAIL'} {c['id']} {c['desc']}")
    print(f"故障注入 {out['n_detected']}/{out['n_mutants']}")
    for m in mut:
        print(f"  {m['id']} {'抓到' if m['detected'] else '漏掉'} {m['failed_checks']}  {m['fault']}")


if __name__ == "__main__":
    main()
