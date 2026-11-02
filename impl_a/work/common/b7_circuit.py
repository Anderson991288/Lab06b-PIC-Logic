"""B7 的 IPKISS／Caphe 電路模型（M2 s2 起使用；佈局後重跑 80 筆也用這裡）。

用途：只從規格（spec/pic_spec.json 的 OPS 與光學埠）產生連接表，再用 CORNERSTONE 2×2 MMI＋理想相位區
      組成 7 顆 MZI、串成五入五出的 B7，交給 Caphe 求 S 矩陣。不 import b7.py，與 NumPy 模型互相獨立。
輸入：spec dict、θ[7]、φ[7]；可選每顆 MZI 上臂的額外波導（arm 模板與長度）。
輸出：無檔案；netlist(spec) 回傳連接表 dict，make_b7(...) 回傳 IPKISS 電路 cell，forward_u(...) 回傳 U[λ, 5, 5]。

MZI 局部埠：in0／out0 = 局部索引 0（上臂，rail p，相位段所在）；in1／out1 = 局部索引 1（rail p+1）。
PDK MMI 的上埠是 in2／out2（y = +1.015 µm），所以局部索引 0 ↔ MMI 的 in2／out2，這個對應在 make_mzi 裡轉接。
"""
import ipkiss3.all as i3
import numpy as np

import pdk


class PhaseModel(i3.CompactModel):
    """理想相位區：t = exp(i·phase)，無損耗、無反射、不隨波長變化。"""
    parameters = ["phase"]
    terms = [i3.OpticalTerm(name="in"), i3.OpticalTerm(name="out")]

    def calculate_smatrix(parameters, env, S):
        t = np.exp(1j * parameters.phase)
        S["in", "out"] = t
        S["out", "in"] = t


class IdealPhase(i3.PCell):
    """熱光相位區的電路替身；heater 的電壓／溫度模型留到量測校正。"""
    phase = i3.NumberProperty(default=0.0)

    class Netlist(i3.NetlistView):
        def _generate_terms(self, terms):
            terms += i3.OpticalTerm(name="in")
            terms += i3.OpticalTerm(name="out")
            return terms

    class CircuitModel(i3.CircuitModelView):
        def _generate_model(self):
            return PhaseModel(phase=self.cell.phase)


def make_mzi(theta, phi, arm=None, fault=None):
    """一顆 MZI：φ → MMI1 → θ（＋上臂額外波導）→ MMI2，相位段在上臂。
    arm：None 或已設定長度的波導 cell（加在 θ 之後）。fault：故障注入代號（只供 M2 s2 驗證用）。"""
    sign = -1.0 if fault == "neg_phase" else 1.0
    up_in, up_out = ("in1", "out1") if fault == "lower_arm" else ("in2", "out2")      # 相位段接在哪一臂
    lo_in, lo_out = ("in2", "out2") if fault == "lower_arm" else ("in1", "out1")
    a, b = (phi, theta) if fault != "swap_theta_phi" else (theta, phi)
    children = {"mmi1": pdk.mmi2x2(), "mmi2": pdk.mmi2x2(),
                "phi": IdealPhase(phase=sign * float(a)), "theta": IdealPhase(phase=sign * float(b))}
    links = [("phi:out", f"mmi1:{up_in}"), (f"mmi1:{up_out}", "theta:in"), (f"mmi1:{lo_out}", f"mmi2:{lo_in}")]
    if arm is None:
        links.append(("theta:out", f"mmi2:{up_in}"))
    else:
        children["arm"] = arm
        links += [("theta:out", "arm:in"), ("arm:out", f"mmi2:{up_in}")]
    o0, o1 = ("mmi2:out1", "mmi2:out2") if fault == "out_swap" else ("mmi2:out2", "mmi2:out1")
    ext = {"phi:in": "in0", f"mmi1:{lo_in}": "in1", o0: "out0", o1: "out1"}
    return i3.ConnectComponents(child_cells=children, links=links, external_port_names=ext)


def netlist(spec):
    """由規格的 OPS 與光學埠產生 B7 連接表：依層序追蹤每條 rail 目前的來源埠。"""
    n = spec["core"]["n_modes"]
    ops = [tuple(o) for o in spec["core"]["ops"]]
    in_port = {d["rail"]: d["port"] for d in spec["optical_inputs"]}
    out_port = {d["rail"]: d["port"] for d in spec["optical_outputs"]}
    src = {r: None for r in range(n)}               # None = 還在晶片輸入端
    links, ext = [], {}
    order = sorted(range(len(ops)), key=lambda k: ops[k][1])
    for k in order:
        p, _ = ops[k]
        for j in (0, 1):
            r, dst = p + j, f"M{k + 1}:in{j}"
            if src[r] is None:
                ext[dst] = in_port[r]
            else:
                links.append([src[r], dst])
            src[r] = f"M{k + 1}:out{j}"
    assert all(s is not None for s in src.values()), "每條 rail 都必須經過至少一顆 MZI"
    for r in range(n):
        ext[src[r]] = out_port[r]
    return {"instances": [{"name": f"M{k + 1}", "cell": "MZI", "rails": [ops[k][0], ops[k][0] + 1],
                           "layer": ops[k][1] + 1} for k in range(len(ops))],
            "links": links, "external": ext}


def make_b7(spec, theta, phi, arms=None, fault=None, nl=None):
    """B7 電路 cell。arms：None 或 7 個（波導 cell 或 None）；fault 見 make_mzi 與下方 B7 層級代號。"""
    nl = nl or netlist(spec)
    mzi_fault = fault if fault in ("lower_arm", "swap_theta_phi", "neg_phase") else None
    children = {}
    for k in range(len(nl["instances"])):
        f = "out_swap" if (fault == "out_swap_M3" and k == 2) else mzi_fault
        children[f"M{k + 1}"] = make_mzi(theta[k], phi[k], arm=None if arms is None else arms[k], fault=f)
    links = [list(l) for l in nl["links"]]
    ext = dict(nl["external"])
    swaps = {"swap_x1_x4": ("in0", "in3"), "swap_o1_o5": ("out0", "out4")}
    if fault in swaps:
        inv = {v: k for k, v in ext.items()}
        pa, pb = swaps[fault]
        ext[inv[pa]], ext[inv[pb]] = pb, pa
    if fault == "swap_links":                          # 第 2 層到第 3 層之間兩條線接反
        links[2][1], links[3][1] = links[3][1], links[2][1]
    return i3.ConnectComponents(child_cells=children, links=[tuple(x.replace(".", ":") for x in l) for l in links],
                                external_port_names=ext)


def forward_u(cell, wavelengths, n=5):
    """Caphe 求 S，抽出前向 U[λ, out, in]（列＝輸出埠 out0–out4，欄＝輸入埠 in0–in4）。"""
    wl = np.atleast_1d(np.asarray(wavelengths, dtype=float))
    S = cell.CircuitModel().get_smatrix(wavelengths=wl, validate_netlist=True)
    U = np.empty((len(wl), n, n), dtype=complex)
    for o in range(n):
        for i in range(n):
            U[:, o, i] = S[f"out{o}", f"in{i}"]
    back = max(abs(S[f"in{o}", f"in{i}"]).max() for o in range(n) for i in range(n))
    return U, float(back)


def arm_waveguide(template, length):
    """上臂的額外直波導（長度 µm）；長度 0 回傳 None。"""
    if length <= 0:
        return None
    wg = i3.Waveguide(trace_template=template)
    wg.Layout(shape=[(0.0, 0.0), (float(length), 0.0)])
    return wg
