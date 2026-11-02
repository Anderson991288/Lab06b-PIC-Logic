"""B7 光邏輯核心的共用定義（M1 s1 建立；M1 s2 加上矩陣、逐層追蹤與路徑展開）。

結構：5 條波導（rail 0–4，佈局圖由上到下）、7 顆 MZI、4 層。
  OPS[k] = (p, layer)：第 k+1 顆 MZI（M1–M7）跨 rail p、p+1，位於第 layer 層；
  rail p 是這顆 MZI 的局部索引 0（上），rail p+1 是局部索引 1（下）。
輸入（編碼）：rail 0–3 = 資料 x1–x4，振幅 0 或 1（同相、相干）；rail 4 = 參考光 R，振幅 3。
讀取：o2（rail 1）與 o4（rail 3）的功率差 ΔP = |o2|² − |o4|²；ΔP > 0 判 1，ΔP < 0 判 0，ΔP = 0 為邊界。
  o1、o3、o5 只監看，不參與判定。
位元順序：字串 "x1x2x3x4"；ALL_BITS 第 i 列的 xj = (i >> (j−1)) & 1（x1 是最低位），與原版真值表列序相同。
矩陣（M1 s2）：三種彼此獨立的算法，單元測試互相核對。
  unitary(θ, φ)：U = E7 ⋯ E2 E1，Ek = 把第 k 顆的 T(θk, φk) 嵌進 5×5 單位矩陣；y = U v。
  trace(v, θ, φ)：逐層只更新兩條相鄰波導的光場，回傳每一層之後的 5 路光場。
  paths(i, j, θ, φ)：列出輸入 rail i 到輸出 rail j 的每一條路徑與其係數乘積，加總等於 U[j, i]。
讀取的展開（M1 s3）：readout_form(U, r) 把 ΔP 寫成位元的二次式
  ΔP(x) = c0 + Σk ak·xk + Σk Σl Qkl·xk·xl，
  c0 = r²(|u25|² − |u45|²)（只有 R）、ak = 2r·Re(u25*·u2k − u45*·u4k)（R 與資料的交叉項）、
  Qkl = Re(u2k*·u2l − u4k*·u4l)（資料彼此的交叉項，對角線是資料自己的功率）。k、l 為 x1–x4。
邏輯功能（M1 s4）：TARGETS 為目標真值函數；load_phases() 讀 sources/b7_phases.json 的 θ、φ；
  truth_table(θ, φ, gate) 對 16 組輸入算 ΔP 與判定；unitary 可加 loss_db、mmi_err、theta_offset 模擬非理想。
輸入／輸出：純函式，無檔案。
"""
import json
from itertools import product
from pathlib import Path

import numpy as np

from common import mzi as Z

PHASE_FILE = Path(__file__).resolve().parents[2] / "sources" / "b7_phases.json"

N_MODES = 5
OPS = [(0, 0), (3, 0), (1, 1), (0, 2), (2, 2), (1, 3), (3, 3)]
N_LAYERS = 4
R_AMP = 3.0
IN_SIGNALS = ["x1", "x2", "x3", "x4", "R"]          # 依 rail 0–4
OUT_SIGNALS = ["o1", "o2", "o3", "o4", "o5"]
READOUT = (1, 3)                                    # (o2, o4) 的 rail
ALL_BITS = np.array([[(i >> j) & 1 for j in range(4)] for i in range(16)], dtype=float)
TARGETS = {"AND2": lambda x: x[0] and x[1], "OR2": lambda x: x[0] or x[1],
           "XOR2": lambda x: bool(x[0]) != bool(x[1]), "AND4": lambda x: all(x), "OR4": lambda x: any(x),
           "NAND2": lambda x: not (x[0] and x[1])}   # 2 輸入功能只看 x1、x2，但 16 組輸入（含 x3、x4）都要對


def bits_str(x):
    """[x1, x2, x3, x4] → "x1x2x3x4" 字串，例如 [1, 1, 0, 0] → "1100"。"""
    return "".join(str(int(b)) for b in x)


def encode(x, r=R_AMP):
    """位元 → 5 條波導的輸入光場向量 v = [x1, x2, x3, x4, R]（複數，全部同相）。"""
    return np.array([*x, r], dtype=complex)


def delta_p(y):
    """輸出光場 y → 讀取功率差 ΔP = |o2|² − |o4|²（可傳 1 維向量或每列一筆的 2 維陣列）。"""
    p = np.abs(np.asarray(y)) ** 2
    return p[..., READOUT[0]] - p[..., READOUT[1]]


def decide(dp, tol=0.0):
    """ΔP → 邏輯值：> tol 判 1，< −tol 判 0，其餘回傳 None（邊界）。"""
    return 1 if dp > tol else (0 if dp < -tol else None)


def readout_form(U, r=R_AMP):
    """ΔP 的二次式係數：回傳 dict(c0, a[4], Q[4×4])，ΔP(x) = c0 + a·x + xᵀQx（x 為實數位元向量）。"""
    U = np.asarray(U)
    a2, a4 = U[READOUT[0]], U[READOUT[1]]
    w2, w4 = a2[:4], a4[:4]
    c0 = r ** 2 * (abs(a2[4]) ** 2 - abs(a4[4]) ** 2)
    a = 2 * r * np.real(np.conj(a2[4]) * w2 - np.conj(a4[4]) * w4)
    Q = np.real(np.outer(np.conj(w2), w2) - np.outer(np.conj(w4), w4))
    return dict(c0=float(c0), a=a, Q=Q)


def _phases(theta, phi):
    theta = np.broadcast_to(np.asarray(theta, float), (len(OPS),))
    phi = np.broadcast_to(np.asarray(phi, float), (len(OPS),))
    return theta, phi


def unitary(theta, phi=0.0, loss_db=0.0, mmi_err=(0.0, 0.0), theta_offset=0.0):
    """B7 的 5×5 傳輸矩陣 U；theta、phi 為 7 個值（或單一值套用到全部）。光由左往右，矩陣由右往左乘。
    非理想（每顆 MZI 相同）：loss_db 插入損耗、mmi_err 兩顆耦合器的分光誤差 (ε1, ε2)、theta_offset 每顆 θ 的固定偏移。"""
    theta, phi = _phases(theta, phi)
    U = np.eye(N_MODES, dtype=complex)
    for k, (p, _) in enumerate(OPS):
        t = Z.T2(theta[k] + theta_offset, phi[k], loss_db=loss_db, mmi_err=tuple(mmi_err))
        U = Z.embed(t, p, p + 1, N_MODES) @ U
    return U


def load_phases(path=PHASE_FILE):
    """讀共用相位檔：回傳 {功能: (θ[7], φ[7])}。"""
    g = json.loads(Path(path).read_text(encoding="utf-8"))["gates"]
    return {k: (np.array(v["theta"]), np.array(v["phi"])) for k, v in g.items()}


def target(gate):
    """功能的目標真值（16 組，依 ALL_BITS 列序）。"""
    return np.array([int(bool(TARGETS[gate](x))) for x in ALL_BITS])


def truth_table(U, gate, r=R_AMP):
    """對 16 組輸入算 ΔP、判定與是否正確；回傳 dict(delta[16], bit[16], target[16], ok, margin)。
    margin = 最小的 有號 ΔP·(2·target−1)：> 0 表示全部判對，數值是離邊界最近的一組還差多少。"""
    tgt = target(gate)
    V = np.column_stack([ALL_BITS, np.full(16, r)]).astype(complex)
    dp = delta_p(V @ U.T)
    signed = dp * (2 * tgt - 1)
    return dict(delta=dp, bit=(dp > 0).astype(int), target=tgt, ok=bool(np.all(signed > 0)), margin=float(signed.min()))


def trace(v, theta, phi=0.0):
    """逐層傳播：回傳 N_LAYERS+1 個 5 維光場（輸入、第 1 層後、…、第 4 層後）。"""
    theta, phi = _phases(theta, phi)
    field = np.array(v, dtype=complex)
    stages = [field.copy()]
    for layer in range(N_LAYERS):
        for k, (p, lay) in enumerate(OPS):
            if lay == layer:
                field[[p, p + 1]] = Z.T2(theta[k], phi[k]) @ field[[p, p + 1]]
        stages.append(field.copy())
    return stages


def _layer_map():
    """每一層：rail → (MZI 編號 k, 局部索引)；沒有 MZI 的 rail 不在字典裡（直通，係數 1）。"""
    maps = [dict() for _ in range(N_LAYERS)]
    for k, (p, layer) in enumerate(OPS):
        maps[layer][p] = (k, 0)
        maps[layer][p + 1] = (k, 1)
    return maps


def paths(i, j, theta, phi=0.0):
    """輸入 rail i → 輸出 rail j 的所有路徑。每條路徑回傳 dict(rails, steps, weight)：
    rails 是各層之後所在的 rail，steps 是 (MZI 編號 1–7, 局部輸出 1/2, 局部輸入 1/2)，weight 是係數乘積。"""
    theta, phi = _phases(theta, phi)
    T = [Z.T2(theta[k], phi[k]) for k in range(len(OPS))]
    maps = _layer_map()
    out = []
    for choice in product((0, 1), repeat=N_LAYERS):     # 每層在 MZI 裡選上或下輸出；沒有 MZI 時只有一種
        r, w, rails, steps, ok = i, 1.0 + 0j, [], [], True
        for layer in range(N_LAYERS):
            if r in maps[layer]:
                k, a = maps[layer][r]
                b = choice[layer]
                w *= T[k][b, a]
                steps.append((k + 1, b + 1, a + 1))
                r = OPS[k][0] + b
            elif choice[layer] == 1:                     # 直通的層只算一次
                ok = False
                break
            rails.append(r)
        if ok and r == j:
            out.append(dict(rails=rails, steps=steps, weight=w))
    return out
