"""common/mzi.py 的單元測試（M0 s3）。

執行：work/m0_s3/run_tests.py（寫出 out/tests.json，並對故障模型重跑一次確認測試抓得到錯）。
也可單獨跑：python -m unittest work/common/tests/test_mzi.py（需先把 work/ 加進 sys.path）。
"""
import unittest

import numpy as np

from common import mzi as Z

TOL = 1e-12


class TestMZI(unittest.TestCase):
    def setUp(self):
        self.angles = np.random.default_rng(1).uniform(0, 2 * np.pi, (50, 2))

    def test_unitary(self):
        """理想 MZI 么正：T†T = I（能量守恆）。"""
        for th, ph in self.angles:
            t = Z.T2(th, ph)
            self.assertLess(np.abs(t.conj().T @ t - np.eye(2)).max(), TOL)

    def test_closed_form(self):
        """逐段相乘與解析展開一致。"""
        for th, ph in self.angles:
            self.assertLess(np.abs(Z.T2(th, ph) - Z.T2_closed(th, ph)).max(), TOL)

    def test_switch_states(self):
        """θ＝0 全交叉、θ＝π 全直通（兩個入射埠都成立，φ 任意）。"""
        for ph in (0.0, 0.7, 2.9):
            p0, ppi = np.abs(Z.T2(0.0, ph)) ** 2, np.abs(Z.T2(np.pi, ph)) ** 2
            self.assertLess(np.abs(p0 - [[0, 1], [1, 0]]).max(), TOL)
            self.assertLess(np.abs(ppi - [[1, 0], [0, 1]]).max(), TOL)

    def test_split_state(self):
        """θ＝π/2：單一埠入射時兩個輸出各一半。"""
        self.assertLess(np.abs(np.abs(Z.T2(np.pi / 2, 1.3)) ** 2 - 0.5).max(), TOL)

    def test_bar_cross_power(self):
        """任意 θ、φ：直通功率 sin²(θ/2)、交叉功率 cos²(θ/2)。"""
        for th, ph in self.angles:
            p = np.abs(Z.T2(th, ph)) ** 2
            self.assertLess(abs(p[0, 0] - Z.bar_power(th)), TOL)
            self.assertLess(abs(p[1, 1] - Z.bar_power(th)), TOL)
            self.assertLess(abs(p[1, 0] - (1 - Z.bar_power(th))), TOL)

    def test_phi_only_phase(self):
        """φ 只改變輸入相對相位：|T| 與 φ 無關。"""
        ref = np.abs(Z.T2(1.1, 0.0))
        for ph in np.linspace(0, 2 * np.pi, 9):
            self.assertLess(np.abs(np.abs(Z.T2(1.1, ph)) - ref).max(), TOL)

    def test_coherent_combine(self):
        """兩路等幅同相輸入、θ＝π/2：φ＝0 時全部合到索引 0，φ＝π 時全部到索引 1（相干性）。"""
        v = np.array([1, 1]) / np.sqrt(2)
        self.assertAlmostEqual(abs((Z.T2(np.pi / 2, 0.0) @ v)[0]) ** 2, 1.0, places=12)
        self.assertAlmostEqual(abs((Z.T2(np.pi / 2, np.pi) @ v)[1]) ** 2, 1.0, places=12)

    def test_theta_for_bar_inverse(self):
        for p in np.linspace(0, 1, 11):
            self.assertAlmostEqual(Z.bar_power(Z.theta_for_bar(p)), p, places=12)

    def test_layout_mapping(self):
        """M0 s2 的佈局約定（相位段在埠 2 的臂）換算後等於本模型 T(θ, 0)。"""
        C = np.array([[1, 1j], [1j, 1]]) / np.sqrt(2)
        for th in np.linspace(0, 2 * np.pi, 13):
            layout = C @ np.diag([1, np.exp(1j * th)]) @ C
            self.assertLess(np.abs(Z.layout_to_model(layout) - Z.T2(th, 0.0)).max(), TOL)

    def test_loss(self):
        """每顆 0.9 dB：T†T = a²·I，總功率乘 10^(−0.09)。"""
        t = Z.T2(0.7, 1.9, loss_db=0.9)
        self.assertLess(np.abs(t.conj().T @ t - 10 ** (-0.09) * np.eye(2)).max(), TOL)

    def test_mmi_error(self):
        """分光比誤差 ε：耦合器仍么正、直通功率 1/2＋ε。
        兩個耦合器誤差相同：θ＝π 的直通態仍完美，θ＝0 的交叉態漏光 4ε²；誤差不同時直通態也漏光。"""
        eps = 0.03
        c = Z.coupler(eps)
        self.assertLess(np.abs(c.conj().T @ c - np.eye(2)).max(), TOL)
        self.assertAlmostEqual(abs(c[0, 0]) ** 2, 0.5 + eps, places=12)
        self.assertLess(abs(Z.T2(np.pi, 0.0, mmi_err=(eps, eps))[1, 0]) ** 2, TOL)
        self.assertAlmostEqual(abs(Z.T2(0.0, 0.0, mmi_err=(eps, eps))[0, 0]) ** 2, 4 * eps ** 2, places=12)
        self.assertGreater(abs(Z.T2(np.pi, 0.0, mmi_err=(eps, -eps))[1, 0]) ** 2, 1e-4)

    def test_embed(self):
        t = Z.T2(0.4, 0.2)
        m = Z.embed(t, 2, 3, 7)
        self.assertLess(np.abs(m[2:4, 2:4] - t).max(), TOL)
        rest = np.delete(np.delete(m, [2, 3], 0), [2, 3], 1)
        self.assertLess(np.abs(rest - np.eye(5)).max(), TOL)

    def test_cascade_unitary(self):
        """多顆 MZI 嵌入 5 條波導後相乘仍么正（M1 的 B7 就是這樣組成）。"""
        U = np.eye(5, dtype=complex)
        for k, (th, ph) in enumerate(self.angles[:7]):
            p = k % 4
            U = Z.embed(Z.T2(th, ph), p, p + 1, 5) @ U
        self.assertLess(np.abs(U.conj().T @ U - np.eye(5)).max(), 1e-11)


if __name__ == "__main__":
    unittest.main()
