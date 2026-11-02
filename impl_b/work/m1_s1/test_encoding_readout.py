"""Independent predictions, energy conservation and receiver unit checks."""
import sys, unittest
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'work'), str(Path(__file__).resolve().parent)]
from common import encoding, mzi, photodetection as pd, linear_network as net
from experiments import and2, nand2, nand_matrix


class EncodingReadout(unittest.TestCase):
    def test_ook_field_is_sqrt_power(self):
        field = encoding.ook_fields([0, 1, 1], on_power=4., phases=[0, 0, np.pi])
        np.testing.assert_allclose(field, [0, 2, -2], atol=1e-12)
        np.testing.assert_allclose(mzi.powers(field), [0, 4, 4])

    def test_b7_port_order_and_reference_power(self):
        np.testing.assert_array_equal(encoding.with_reference([1, 0, 1, 0]), [1, 0, 1, 0, 3])
        for value in range(16):
            bits = [(value >> i) & 1 for i in range(4)]
            self.assertAlmostEqual(sum(mzi.powers(encoding.with_reference(bits))), sum(bits)+9)

    def test_encoding_rejects_invalid_data(self):
        for bits in [[], [2], [-1], [.5], [[0, 1]], [np.nan]]:
            with self.subTest(bits=bits), self.assertRaises(ValueError): encoding.ook_fields(bits)
        for kwargs in [{'on_power': 0}, {'on_power': np.inf}, {'phases': [0]}, {'phases': [0, np.nan]}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError): encoding.ook_fields([0, 1], **kwargs)
        for amplitude, phase in [(-1, 0), (np.inf, 0), (2, np.nan)]:
            with self.assertRaises(ValueError): encoding.with_reference([0], amplitude, phase)

    def test_and_truth_and_scalar_fields(self):
        k = (-1+1j)/2
        for a, b in [(0, 0), (0, 1), (1, 0), (1, 1)]:
            _, out, read = and2([a, b])
            np.testing.assert_allclose(out, [k*(a+b), k*(a-b)], atol=1e-12)
            self.assertEqual(read['bit'], a & b)
            self.assertAlmostEqual(read['delta'], 2*a*b)

    def test_and_relative_phase_formula(self):
        for phase in np.linspace(-np.pi, np.pi, 37):
            _, out, read = and2([1, 1], phase)
            self.assertAlmostEqual(read['delta'], 2*np.cos(phase))
            self.assertAlmostEqual(sum(mzi.powers(out)), 2.)
        self.assertEqual(and2([1, 1], np.pi)[2]['bit'], 0)

    def test_loss_keeps_fixed_threshold(self):
        self.assertEqual(and2([1, 1], loss_db=4)[2]['bit'], 0)
        self.assertAlmostEqual(and2([1, 1], loss_db=3)[2]['delta'], 2*10**(-.3))

    def test_common_phase_does_not_change_readout(self):
        matrix = mzi.T2(np.pi/2)
        base = encoding.ook_fields([1, 1])
        for angle in [0., .2, 2.8]:
            np.testing.assert_allclose(mzi.powers(matrix@(base*np.exp(1j*angle))), [2, 0], atol=1e-12)

    def test_incoherent_average_loses_cross_term(self):
        # Deterministic equally spaced phase ensemble, not a stochastic coherence model.
        average = np.mean([mzi.powers(and2([1, 1], t)[1]) for t in 2*np.pi*np.arange(64)/64], axis=0)
        np.testing.assert_allclose(average, [1, 1], atol=1e-12)

    def test_nand_network_unitarity_and_target_row(self):
        U = nand_matrix()
        np.testing.assert_allclose(U.conj().T@U, np.eye(3), atol=1e-12)
        q = U[0, 2]*np.sqrt(3)
        self.assertAlmostEqual(abs(q), 1.)
        np.testing.assert_allclose(U[0], q*np.array([-1, -1, 1])/np.sqrt(3), atol=1e-12)

    def test_nand_truth_and_all_output_energy(self):
        for a, b in [(0, 0), (0, 1), (1, 0), (1, 1)]:
            inp, out, read = nand2([a, b])
            self.assertAlmostEqual(read['power'], (2-a-b)**2/3)
            self.assertEqual(read['bit'], 1-(a & b))
            self.assertAlmostEqual(sum(mzi.powers(out)), sum(mzi.powers(inp)))

    def test_reference_removed_cannot_light_zero_data(self):
        inp, out, read = nand2([0, 0], 0.)
        np.testing.assert_array_equal(inp, [0, 0, 0])
        np.testing.assert_array_equal(out, [0, 0, 0])
        self.assertEqual(read['bit'], 0)

    def test_reference_phase_changes_interference(self):
        self.assertAlmostEqual(nand2([1, 1], 2., np.pi)[2]['power'], 16/3)
        self.assertEqual(nand2([1, 1], 2., np.pi)[2]['bit'], 1)

    def test_reference_amplitude_is_not_power(self):
        self.assertAlmostEqual(sum(mzi.powers(encoding.with_reference([0, 0], 3))), 9.)
        self.assertAlmostEqual(nand2([0, 0], 2)[2]['power'], 4/3)

    def test_no_per_pattern_normalization(self):
        self.assertAlmostEqual(sum(mzi.powers(encoding.with_reference([0, 0], 2))), 4.)
        self.assertAlmostEqual(sum(mzi.powers(encoding.with_reference([1, 1], 2))), 6.)
        # Normalizing each input would erase the intended fixed power scale.
        self.assertNotAlmostEqual(nand2([0, 0])[2]['power'], nand2([1, 1])[2]['power'])

    def test_receiver_units_and_boundary(self):
        result = pd.differential_receiver([np.sqrt(2), 0], 0, 1, threshold=1.)
        self.assertAlmostEqual(result['differential_current_a'], 1.6e-6)
        self.assertAlmostEqual(result['differential_voltage_v'], .016)
        self.assertAlmostEqual(result['threshold_voltage_v'], .008)
        self.assertEqual(result['bit'], 1)
        self.assertIsNone(pd.differential_receiver([1, 0], 0, 1, threshold=1.)['bit'])
        self.assertIsNone(net.power_difference_readout([0, 0], 0, 1)['bit'])
        self.assertIsNone(nand2([0, 0], np.sqrt(.5))[2]['bit'])

    def test_receiver_rejects_nonphysical_scales(self):
        for kw in [{'power_unit_w': 0}, {'responsivity_a_per_w': -1}, {'transimpedance_v_per_a': np.nan}]:
            with self.subTest(kw=kw), self.assertRaises(ValueError): pd.differential_receiver([1, 0], 0, 1, **kw)
        with self.assertRaises(ValueError): nand2([0, 0], threshold=np.nan)


if __name__ == '__main__': unittest.main(verbosity=2)
