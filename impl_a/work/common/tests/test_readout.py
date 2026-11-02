"""B7 讀取（v → y=Uv → 功率 → ΔP → 0／1）的單元測試（M1 s3）。

執行：work/m1_s3/readout_calc.py（寫出 out/tests.json）。
"""
import json
import unittest
from pathlib import Path

import numpy as np

from common import b7

TOL = 1e-11
ROOT = Path(__file__).resolve().parents[3]
REF = json.loads((ROOT / "sources" / "reference_b7.json").read_text(encoding="utf-8"))


class TestReadout(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(11)
        self.Us = [b7.unitary(rng.uniform(0, 2 * np.pi, 7), rng.uniform(0, 2 * np.pi, 7)) for _ in range(20)]

    def test_reference_cases(self):
        """黃金值：θ 全 π/2、φ 全 0 時，1000、1100 的 ΔP 與判定和原版相同。"""
        U = b7.unitary(np.pi / 2, 0.0)
        for c in REF["cases"]:
            y = U @ b7.encode([int(b) for b in c["bits"]])
            self.assertAlmostEqual(b7.delta_p(y), c["delta"], places=12)
            self.assertEqual(b7.decide(b7.delta_p(y)), c["bit"])

    def test_weighted_sum(self):
        """o2、o4 = U 第 2、4 列與 v 的加權和（逐項相加）＝矩陣乘法的結果。"""
        for U in self.Us[:5]:
            for x in b7.ALL_BITS:
                v = b7.encode(x)
                y = U @ v
                for j in b7.READOUT:
                    self.assertLess(abs(sum(U[j, k] * v[k] for k in range(5)) - y[j]), TOL)

    def test_quadratic_form(self):
        """ΔP = c0 + a·x + xᵀQx 對 16 組輸入與任意相位都精確成立。"""
        for U in self.Us:
            f = b7.readout_form(U)
            for x in b7.ALL_BITS:
                dp = b7.delta_p(U @ b7.encode(x))
                self.assertLess(abs(f["c0"] + f["a"] @ x + x @ f["Q"] @ x - dp), TOL)

    def test_r_scaling(self):
        """R 加倍：只有 R 的項 ×4、R×資料 的交叉項 ×2、資料彼此的交叉項不變。"""
        for U in self.Us[:5]:
            f1, f2 = b7.readout_form(U, 3.0), b7.readout_form(U, 6.0)
            self.assertAlmostEqual(f2["c0"], 4 * f1["c0"], places=11)
            self.assertLess(np.abs(f2["a"] - 2 * f1["a"]).max(), TOL)
            self.assertLess(np.abs(f2["Q"] - f1["Q"]).max(), TOL)

    def test_power_sum_conserved(self):
        """五路輸出功率總和 = 輸入總功率（資料位元數 + R²）；只看 o2＋o4 不會守恆。"""
        for U in self.Us[:5]:
            for x in b7.ALL_BITS:
                y = U @ b7.encode(x)
                self.assertAlmostEqual(np.sum(np.abs(y) ** 2), x.sum() + b7.R_AMP ** 2, places=10)

    def test_dark_input(self):
        """輸入 0000 時只剩 R：ΔP = R²(|u25|² − |u45|²) = c0。"""
        for U in self.Us[:5]:
            self.assertAlmostEqual(b7.delta_p(U @ b7.encode([0, 0, 0, 0])), b7.readout_form(U)["c0"], places=11)


if __name__ == "__main__":
    unittest.main()
