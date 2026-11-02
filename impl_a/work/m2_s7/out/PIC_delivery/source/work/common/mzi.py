"""單顆 MZI 的 2×2 傳輸矩陣：全課程共用的光學模型與符號慣例（M0 s3）。

結構（光由左往右）：φ 相位段 → 2×2 耦合器 H → θ 相位段 → 2×2 耦合器 H；兩個相位段都在索引 0 的臂上。
  T(θ, φ) = H · diag(e^{iθ}, 1) · H · diag(e^{iφ}, 1)，H = [[1, i], [i, 1]] / √2（理想 50:50，跨接多 90°）。
  展開：T00 = i e^{i(φ+θ/2)} sin(θ/2)，T01 = i e^{iθ/2} cos(θ/2)，
        T10 = i e^{i(φ+θ/2)} cos(θ/2)，T11 = −i e^{iθ/2} sin(θ/2)。
  ⇒ 任一埠入射：直通（bar）功率 sin²(θ/2)、交叉（cross）功率 cos²(θ/2)；θ＝0 全交叉、θ＝π 全直通。
  φ 只改變兩路輸入的相對相位，單一輸入時不影響功率；B7 用它對齊相干光。
索引約定：索引 0 是放相位段的臂。M0 s2 的 Meep 佈局中相位段在上臂（in2／out2），
  所以佈局埠 (in1, in2) 對應模型索引 (1, 0)，用 layout_to_model() 換算。
非理想：
  loss_db：每顆 MZI 的插入損耗，振幅乘 a = 10^(−loss_db/20)（兩臂相同，不改變分光比）。
  mmi_err：兩個耦合器的分光比誤差 (ε1, ε2)，H(ε) = [[√(1/2+ε), i√(1/2−ε)], [i√(1/2−ε), √(1/2+ε)]]（仍么正）。
輸入／輸出：純函式，無檔案。
"""
import numpy as np

H = np.array([[1, 1j], [1j, 1]]) / np.sqrt(2)
SWAP = np.array([[0, 1], [1, 0]])          # 佈局埠 (1, 2) ↔ 模型索引 (1, 0)


def coupler(eps=0.0):
    """2×2 耦合器；eps＝0 為理想 50:50（等於 H），eps＞0 時直通路徑功率 1/2＋eps。"""
    if eps == 0.0:
        return H
    c, s = np.sqrt(0.5 + eps), np.sqrt(0.5 - eps)
    return np.array([[c, 1j * s], [1j * s, c]])


def amp(loss_db):
    """插入損耗（dB）→ 振幅因子（功率因子的平方根）。"""
    return 10 ** (-loss_db / 20.0) if loss_db else 1.0


def T2(theta, phi=0.0, loss_db=0.0, mmi_err=(0.0, 0.0)):
    """單顆 MZI 的 2×2 矩陣（複數），由元件逐段相乘。"""
    t = coupler(mmi_err[1]) @ np.diag([np.exp(1j * theta), 1.0]) @ coupler(mmi_err[0]) @ np.diag([np.exp(1j * phi), 1.0])
    return t * amp(loss_db)


def T2_closed(theta, phi=0.0):
    """理想 MZI 的解析展開（單元測試用來核對 T2）。"""
    e = np.exp(1j * theta / 2)
    return np.array([[1j * np.exp(1j * phi) * e * np.sin(theta / 2), 1j * e * np.cos(theta / 2)],
                     [1j * np.exp(1j * phi) * e * np.cos(theta / 2), -1j * e * np.sin(theta / 2)]])


def bar_power(theta):
    """單一埠入射時直通埠的功率比 sin²(θ/2)（與 φ 無關）。"""
    return np.sin(theta / 2) ** 2


def theta_for_bar(p_bar):
    """要得到直通功率比 p_bar 所需的 θ ∈ [0, π]。"""
    return 2 * np.arcsin(np.sqrt(np.clip(p_bar, 0.0, 1.0)))


def layout_to_model(v):
    """佈局埠順序 (port1, port2) 的向量或 2×2 矩陣 ↔ 模型索引順序（互逆，同一個函式）。"""
    v = np.asarray(v)
    return SWAP @ v @ SWAP if v.ndim == 2 else SWAP @ v


def embed(t, i, j, n):
    """把 2×2 矩陣 t 放進 n×n 單位矩陣的 (i, j) 模上。"""
    m = np.eye(n, dtype=complex)
    m[np.ix_([i, j], [i, j])] = t
    return m
