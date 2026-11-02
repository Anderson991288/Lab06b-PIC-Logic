"""common/b7.py 的單元測試（M1 s2）。

三種獨立算法互相核對（矩陣相乘、逐層追蹤、路徑展開），再用兩組不依賴程式的「黃金值」把關：
手動追蹤的全交叉排列，以及原版課程的 U（sources/reference_b7.json）。
執行：work/m1_s2/build_b7.py（寫出 out/tests.json，並對故障版重跑）。
"""
import json
import unittest
from pathlib import Path

import numpy as np

from common import b7

TOL = 1e-12
ROOT = Path(__file__).resolve().parents[3]
REF = json.loads((ROOT / "sources" / "reference_b7.json").read_text(encoding="utf-8"))
CROSS_PERM = [4, 2, 0, 3, 1]       # 手動追蹤：θ 全 0 時 x1→o5、x2→o3、x3→o1、x4→o4、R→o2


def cplx(a):
    return np.array(a)[..., 0] + 1j * np.array(a)[..., 1]


class TestB7(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(7)
        self.settings = [(rng.uniform(0, 2 * np.pi, 7), rng.uniform(0, 2 * np.pi, 7)) for _ in range(30)]

    def test_unitary(self):
        """任意 14 個相位，U 都么正：U†U = I（無損耗時總功率守恆）。"""
        for th, ph in self.settings:
            U = b7.unitary(th, ph)
            self.assertLess(np.abs(U.conj().T @ U - np.eye(5)).max(), TOL)

    def test_trace_matches_matrix(self):
        """逐層追蹤的最後一層 = U·v（兩種獨立算法）。"""
        rng = np.random.default_rng(1)
        for th, ph in self.settings:
            v = rng.normal(size=5) + 1j * rng.normal(size=5)
            self.assertLess(np.abs(b7.trace(v, th, ph)[-1] - b7.unitary(th, ph) @ v).max(), 1e-11)

    def test_trace_energy_each_layer(self):
        """每一層之後的總功率都等於輸入總功率。"""
        th, ph = self.settings[0]
        for x in b7.ALL_BITS:
            v = b7.encode(x)
            for f in b7.trace(v, th, ph):
                self.assertAlmostEqual(np.sum(np.abs(f) ** 2), np.sum(np.abs(v) ** 2), places=11)

    def test_path_sum(self):
        """每個 U[j, i] = 輸入 i 到輸出 j 所有路徑係數乘積的總和（第三種獨立算法）。"""
        for th, ph in self.settings[:5]:
            U = b7.unitary(th, ph)
            for i in range(5):
                for j in range(5):
                    s = sum(p["weight"] for p in b7.paths(i, j, th, ph))
                    self.assertLess(abs(s - U[j, i]), TOL)

    def test_reachability(self):
        """沒有路徑的 (i, j) 在任何相位下 U[j, i] 都是 0；有路徑的一般不為 0。"""
        th, ph = self.settings[3]
        U = b7.unitary(th, ph)
        for i in range(5):
            for j in range(5):
                n = len(b7.paths(i, j, th, ph))
                self.assertEqual(n == 0, abs(U[j, i]) < 1e-12, (i, j, n))

    def test_all_cross_permutation(self):
        """黃金值：θ 全 0（每顆全交叉）時，|U|² 是手動追蹤得到的排列。"""
        P = np.abs(b7.unitary(0.0, 0.3)) ** 2
        G = np.zeros((5, 5))
        for i, j in enumerate(CROSS_PERM):
            G[j, i] = 1
        self.assertLess(np.abs(P - G).max(), TOL)

    def test_all_bar_identity(self):
        """θ 全 π（每顆全直通）時，|U| = I：光留在原波導。"""
        self.assertLess(np.abs(np.abs(b7.unitary(np.pi, 1.1)) - np.eye(5)).max(), TOL)

    def test_reference_matrix(self):
        """黃金值：θ 全 π/2、φ 全 0 的 U 與原版課程逐項相同；1000、1100 的五路功率與 ΔP 也相同。"""
        U = b7.unitary(np.pi / 2, 0.0)
        self.assertLess(np.abs(U - cplx(REF["U"])).max(), 1e-12)
        for c in REF["cases"]:
            x = [int(b) for b in c["bits"]]
            y = U @ b7.encode(x)
            self.assertLess(np.abs(np.abs(y) ** 2 - c["powers"]).max(), 1e-12)
            self.assertAlmostEqual(b7.delta_p(y), c["delta"], places=12)

    def test_reference_paths(self):
        """黃金值：x4→o2 只有 1 條路徑、x4→o4 有 2 條，經過的 MZI 與係數和原版相同。"""
        for (i, j), key in (((3, 1), "x4_to_o2"), ((3, 3), "x4_to_o4")):
            mine = sorted(b7.paths(i, j, np.pi / 2, 0.0), key=lambda p: p["steps"])
            ref = sorted(REF["paths"][key], key=lambda p: p["steps"])
            self.assertEqual(len(mine), len(ref))
            for m, r in zip(mine, ref):
                self.assertEqual([list(s) for s in m["steps"]], r["steps"])
                self.assertLess(abs(m["weight"] - cplx(r["weight"])), 1e-12)

    def test_same_layer_commute(self):
        """同一層的 MZI 作用在不重疊的波導上，先後順序不影響結果；相鄰層共用波導則一般會影響。"""
        from common import mzi as Z
        th, ph = self.settings[2]
        E = [Z.embed(Z.T2(th[k], ph[k]), p, p + 1, 5) for k, (p, _) in enumerate(b7.OPS)]
        for k in range(7):
            for l in range(7):
                if k < l and b7.OPS[k][1] == b7.OPS[l][1]:
                    self.assertLess(np.abs(E[k] @ E[l] - E[l] @ E[k]).max(), TOL)
        self.assertGreater(np.abs(E[0] @ E[2] - E[2] @ E[0]).max(), 1e-3)     # M1、M3 共用 rail 1


if __name__ == "__main__":
    unittest.main()
