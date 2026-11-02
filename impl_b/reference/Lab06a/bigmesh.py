"""整顆晶片＝一個大 Macro 的網格與有損合成（M2 s2b）。

用途：N＝K＋1 模（R＋K 路資料）、任意平面排程（只用相鄰波導的 2×2 MZI）、判讀列為任意兩條輸出 (a, b)、
R 接任意輸入埠。提供：排程產生器（Reck 邊緣匯流、中央匯流）、可控性檢查（判讀兩列投影的雅可比秩）、
路徑長度（振幅因子換成單位根＋FFT）、有損合成（解析梯度；輸入多時以切平面法做 epigraph 精修）。
平面幾何的下界：每顆 MZI 最多把光移動一條波導，輸入 j 到判讀輸出 c 至少經過 |j−c| 顆 MZI。
輸入：排程 ops（[(位置 p, 層)]，MZI 作用在模 p、p+1）、判讀輸出、埠指派、真值表符號。
輸出：純函式，回傳 dict（margin、相位、收斂資訊），無檔案。
"""
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from . import mesh as M
from . import mzi as Z
from . import synth as S


@dataclass
class Design:
    """大 Macro 的一個設計：n 模、排程、判讀輸出、R 埠（資料依序接其餘埠，可另給 data_ports）。"""
    name: str
    n: int
    ops: list                 # [(p, layer)]，依層排序
    readout: tuple = (0, 1)
    r_port: int = 0
    data_ports: tuple = None

    @property
    def mesh(self):
        if not hasattr(self, "_mesh"):
            sched = [((p, p + 1), l) for p, l in self.ops]
            self._mesh = M.Mesh(self.n, 2, sched=(sched, 1 + max(l for _, l in self.ops)))
        return self._mesh

    @property
    def n_mzi(self):
        return len(self.ops)

    @property
    def depth(self):
        return 1 + max(l for _, l in self.ops)

    def ports(self):
        dp = self.data_ports or tuple(m for m in range(self.n) if m != self.r_port)
        return self.r_port, dp


def layered(seq, n):
    """位置序列 → (p, 層)：每顆放在最早可放的層。"""
    last = [0] * n
    out = []
    for p in seq:
        l = max(last[p], last[p + 1])
        out.append((p, l))
        last[p] = last[p + 1] = l + 1
    return sorted(out, key=lambda t: (t[1], t[0]))


def reck(n, diags=2):
    """Reck 前 diags 條對角：判讀在 o1、o2（邊緣），由下往上匯流。"""
    return layered([p for d in range(diags) for p in range(n - 2, d - 1, -1)], n)


def center_funnel(n, c):
    """中央匯流：判讀在輸出 c、c+1。第一條：兩側往 c 匯（左側 p＝0…c−1 往右、右側 p＝n−2…c 往左）；
    第二條：同樣往 c+1 匯，但不碰已完成的 c（左側 p＝0…c−1 往右到 c… 由右側經 p＝n−2…c+1 往左）。
    MZI 數＝(n−1)＋(n−2)，與 Reck 前兩條對角相同（自由度下界）。"""
    first = list(range(0, c)) + list(range(n - 2, c - 1, -1))
    second = list(range(0, c)) + list(range(n - 2, c, -1))
    return layered(first + second, n)


def lossy_rows_design(d, theta, phi, loss_db, grad=False):
    """判讀兩列 A（2×n），grad 時另回傳 dA/dθ、dA/dφ。"""
    out = S.lossy_rows(theta, phi, loss_db, grad=grad, nrows=d.n, n_modes=d.n, mesh=d.mesh)
    sel = list(d.readout)
    if not grad:
        return out[sel]
    A, dth, dph = out
    return A[sel], dth[:, sel], dph[:, sel]


def input_matrix(d, X, R=M.R_AMP):
    rp, dp = d.ports()
    V = np.zeros((X.shape[0], d.n))
    V[:, rp] = R
    for j, m in enumerate(dp[:X.shape[1]]):
        V[:, m] = X[:, j]
    return V


def z_fn(d, s, V, loss_db):
    nm = d.n_mzi

    def f(q, grad):
        if not grad:
            A = lossy_rows_design(d, q[:nm], q[nm:], loss_db)
            o = np.abs(V @ A.T) ** 2
            return s * (o[:, 0] - o[:, 1])
        A, dth, dph = lossy_rows_design(d, q[:nm], q[nm:], loss_db, grad=True)
        y = V @ A.T
        o = np.abs(y) ** 2
        dA = np.concatenate([dth, dph])
        dy = np.einsum("nj,qrj->nqr", V, dA)
        do = 2 * np.real(np.conj(y)[:, None, :] * dy)
        return s * (o[:, 0] - o[:, 1]), s[:, None] * (do[:, :, 0] - do[:, :, 1])
    return f


def polish_cutting_plane(p0, f, best, n_active=64, rounds=12, maxiter=400):
    """epigraph 精修的切平面版：只放目前最差的 n_active 個輸入當限制；解完後檢查全部輸入，
    把新的最差者加入，直到全部輸入的最小值不再進步。輸入少（≤ n_active）時等於一般 epigraph。"""
    p, v = p0, float(best)
    z = f(p, False)
    act = set(np.argsort(z)[:n_active].tolist())
    info = dict(rounds=0, nit=0, converged=False, n_active=0)
    for _ in range(rounds):
        idx = np.array(sorted(act))
        cons = {"type": "ineq", "fun": lambda x: f(x[:-1], False)[idx] - x[-1],
                "jac": lambda x: np.hstack([f(x[:-1], True)[1][idx], -np.ones((len(idx), 1))])}
        jac0 = np.zeros(len(p) + 1)
        jac0[-1] = -1.0
        r = minimize(lambda x: -x[-1], np.concatenate([p, [v]]), jac=lambda x: jac0, method="SLSQP", constraints=[cons],
                     options=dict(maxiter=maxiter, ftol=1e-12))
        info["rounds"] += 1
        info["nit"] += int(r.nit)
        z = f(r.x[:-1], False)
        vv = float(z.min())
        gain = vv - v
        if vv >= v - 1e-12:
            p, v = r.x[:-1], max(v, vv)
        new = set(np.argsort(z)[:n_active // 4].tolist()) - act
        act |= new
        if r.success and not new and gain < 1e-7:
            info["converged"] = True
            break
        if gain < 1e-7 and not new:
            break
    info["n_active"] = len(act)
    return p, v, info


def synthesize(d, s, X, R=M.R_AMP, loss_db=0.9, restarts=6, betas=(4.0, 20.0, 100.0), seed=700, n_active=64):
    V = input_matrix(d, X, R)
    f = z_fn(d, s, V, loss_db)
    rng = np.random.default_rng(seed)
    best, bp = -np.inf, None
    for _ in range(restarts):
        q = S._soft_stage(rng.uniform(0, 2 * np.pi, 2 * d.n_mzi), f, betas)
        v = float(f(q, False).min())
        if v > best:
            best, bp = v, q
    soft = best
    bp, best, info = polish_cutting_plane(bp, f, best, n_active=n_active)
    return dict(margin=float(best), margin_softstage=float(soft), p=bp, polish=info)


def controllable(d, rng=None, h=1e-6):
    """判讀兩列投影 P_a、P_b 對全部相位的雅可比秩是否等於 2·n_mzi（且 n_mzi 不少於下界 2n−3）。"""
    rng = rng or np.random.default_rng(31)
    nm = d.n_mzi
    th, ph = rng.uniform(0, 2 * np.pi, (2, nm))
    p = np.concatenate([th, ph])

    def proj(q):
        A = lossy_rows_design(d, q[:nm], q[nm:], 0.0)
        return np.concatenate([np.concatenate([np.outer(np.conj(a), a).real.ravel(), np.outer(np.conj(a), a).imag.ravel()]) for a in A])
    J = np.array([(proj(p + h * e) - proj(p - h * e)) / (2 * h) for e in np.eye(2 * nm)]).T
    rank = int(np.linalg.matrix_rank(J, tol=1e-6))
    return rank, 2 * (2 * d.n - 3)


def path_lengths(d, n_mc=8, N=None):
    """判讀兩列每個輸入的路徑長度集合（a 的多項式係數不為 0 的次數）。"""
    N = N or (1 << int(np.ceil(np.log2(d.n_mzi + 2))))
    rng = np.random.default_rng(32)
    Zs = np.exp(2j * np.pi * np.arange(N) / N)
    m = d.mesh
    L = [[set() for _ in range(d.n)] for _ in range(2)]
    for _ in range(n_mc):
        th, ph = rng.uniform(0, 2 * np.pi, (2, d.n_mzi))
        Us = []
        for zz in Zs:
            U = np.eye(d.n, dtype=complex)
            for q in m.order:
                (i, j), _ = m.sched[q]
                t = zz * Z.T2(th[q], ph[q])
                Ui, Uj = U[i].copy(), U[j].copy()
                U[i] = t[0, 0] * Ui + t[0, 1] * Uj
                U[j] = t[1, 0] * Ui + t[1, 1] * Uj
            Us.append(U[list(d.readout)])
        c = np.fft.fft(np.array(Us), axis=0) / N
        for i in range(2):
            for j in range(d.n):
                L[i][j] |= {int(l) for l in np.nonzero(np.abs(c[:, i, j]) > 1e-9)[0]}
    return [[sorted(x) for x in row] for row in L]


def path_lengths_dp(n, ops, outputs):
    """路徑長度的組合計算（不需相位）：依層序逐顆 MZI，模 p、p+1 的長度集合合併後加 1 送到兩個輸出。
    以位元遮罩表示長度集合（第 ℓ 位＝長度 ℓ）。回傳 L[r][j]＝輸出 outputs[r] 從輸入 j 的長度集合（list）。
    一般相位下各路徑係數不會恰好抵消，所以與 path_lengths（單位根＋FFT）相同（單元測試確認）。"""
    S = [[0] * n for _ in range(n)]
    for j in range(n):
        S[j][j] = 1
    for p, _ in sorted(ops, key=lambda t: (t[1], t[0])):
        for j in range(n):
            u = (S[j][p] | S[j][p + 1]) << 1
            S[j][p] = S[j][p + 1] = u
    out = []
    for c in outputs:
        out.append([[l for l in range(S[j][c].bit_length()) if S[j][c] >> l & 1] for j in range(n)])
    return out


def path_score(n, ops, readout, r_ports, data_ports):
    """有損下的路徑指標（越小越好）：
    s_R：兩條判讀列上，每路資料與「最近的 R 埠」干涉路徑長度和的最大值 max_j min_k (ℓ_R_k＋ℓ_j)（門檻類函數）；
    s_dd：兩路資料之間的最大路徑長度和 max_{j≠k}(ℓ_j＋ℓ_k)（二次型函數）；以各集合的最大長度計。"""
    L = path_lengths_dp(n, ops, readout)
    s_r = max(min(max(L[r][k]) + max(L[r][j]) for k in r_ports) for r in range(len(readout)) for j in data_ports)
    lens = [[max(L[r][j]) for j in data_ports] for r in range(len(readout))]
    s_dd = max(sorted(row)[-1] + sorted(row)[-2] for row in lens)
    return s_r, s_dd


def brick(n, depth, start=0):
    """深度 depth 的磚牆（矩形）排列：第 l 層放在位置 p≡(start＋l) mod 2 的所有 MZI（Clements 類，截斷）。"""
    return [(p, l) for l in range(depth) for p in range((start + l) % 2, n - 1, 2)]


def prune(n, ops, readout):
    """去掉不影響判讀輸出的 MZI：由判讀輸出往回追，只保留其後仍能把光送到判讀輸出的 MZI。"""
    ops = sorted(ops, key=lambda t: (t[1], t[0]))
    live = set(readout)
    keep = []
    for p, l in reversed(ops):
        if p in live or p + 1 in live:
            keep.append((p, l))
            live |= {p, p + 1}
    return sorted(keep, key=lambda t: (t[1], t[0]))


def sample_ptf2(K, n_funcs, seed=0, w_quad=1.0):
    """隨機 PTF2：在 ±1 基底 s_j＝2x_j−1 上取 f＝sign(a0＋Σa_j s_j＋w_quad·Σa_jk s_j s_k)，係數為標準常態。
    排除常數函數與重複；回傳真值表符號陣列（2^K × n_funcs）與係數。抽樣分布由係數的常態分布決定（報告須寫明）。"""
    rng = np.random.default_rng(seed)
    X = np.array([[(x >> b) & 1 for b in range(K)] for x in range(1 << K)], float)
    Sg = 2 * X - 1
    iu = np.triu_indices(K, 1)
    quad = Sg[:, iu[0]] * Sg[:, iu[1]]
    out, seen = [], set()
    while len(out) < n_funcs:
        a0, a1, a2 = rng.normal(), rng.normal(size=K), rng.normal(size=len(iu[0]))
        v = a0 + Sg @ a1 + w_quad * quad @ a2
        s = np.where(v > 0, 1.0, -1.0)
        key = s.tobytes()
        if abs(s.sum()) == len(s) or key in seen:
            continue
        seen.add(key)
        out.append(s)
    return np.array(out).T


def sample_macro(K, n_funcs, R=M.R_AMP, seed=0, min_margin=1e-3):
    """隨機「Macro 函數」：在 K＋1 個有光模上取兩條 Haar 隨機正交單位列 (u, w)（7×2 複數常態矩陣的 QR 推廣），
    f＝sign(|u·v|²−|w·v|²)，v＝[R, x]。以此產生的函數在無損下一定可實現（生成時的 margin 為下界），
    代表 Macro 能做的函數空間；排除常數、重複與生成 margin＜min_margin 者。回傳 (符號陣列 2^K×n, 生成 margin)。"""
    rng = np.random.default_rng(seed)
    X = np.array([[(x >> b) & 1 for b in range(K)] for x in range(1 << K)], float)
    V = np.hstack([np.full((len(X), 1), R), X])
    out, gm, seen = [], [], set()
    while len(out) < n_funcs:
        A = rng.normal(size=(K + 1, 2)) + 1j * rng.normal(size=(K + 1, 2))
        Q, _ = np.linalg.qr(A)
        D = np.abs(V @ Q[:, 0].conj()) ** 2 - np.abs(V @ Q[:, 1].conj()) ** 2
        s = np.where(D > 0, 1.0, -1.0)
        m = float((s * D).min())
        key = s.tobytes()
        if abs(s.sum()) == len(s) or key in seen or m < min_margin:
            continue
        seen.add(key)
        out.append(s)
        gm.append(m)
    return np.array(out).T, np.array(gm)
