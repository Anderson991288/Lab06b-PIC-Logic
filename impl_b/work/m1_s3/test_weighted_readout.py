"""Independent scalar sums, interference expansion and readout boundaries."""
from pathlib import Path
import sys,unittest,json,itertools
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'work'))
from common import weighted_readout as w,b7,encoding


class WeightedReadoutTests(unittest.TestCase):
    def setUp(self):
        self.rng=np.random.default_rng(613)
        self.U=b7.transfer_matrix(b7.load_topology(),[np.pi/2]*7,[0]*7)

    def test_complex_terms_without_conjugating_row(self):
        row=np.array([[1+2j,3-1j]])
        value=w.row_contributions(row,[2j,1-1j],0)
        np.testing.assert_allclose(value['terms'],[-4+2j,2-4j])
        self.assertAlmostEqual(value['field'],-2-2j)
        self.assertAlmostEqual(value['power'],8.)

    def test_interference_expansion_and_signed_terms(self):
        value=w.row_contributions([[1,1]],[1,-1],0)
        self.assertEqual(value['self_power'],2.)
        self.assertEqual(value['interference_power'],-2.)
        self.assertEqual(value['power'],0.)
        self.assertEqual(value['pairs'],[{'j':0,'k':1,'power':-2.}])

    def test_scalar_sum_matches_matrix(self):
        for _ in range(25):
            v=self.rng.normal(size=5)+1j*self.rng.normal(size=5)
            a=w.evaluate(self.U,v)
            for key,index in [('positive',1),('negative',3)]:
                expected=complex(sum(self.U[index,j]*v[j] for j in range(5)))
                self.assertAlmostEqual(a[key]['field'],expected)
            np.testing.assert_allclose(a['output_field'],self.U@v,atol=1e-14)

    def test_ten_pair_terms_complete_power(self):
        v=np.array([1,1j,2,3j,.5]);a=w.evaluate(self.U,v)
        for key in ['positive','negative']:
            r=a[key];self.assertEqual(len(r['pairs']),10)
            self.assertAlmostEqual(r['self_power']+r['interference_power'],r['power'])

    def test_difference_operator_is_hermitian(self):
        Q=w.difference_operator(self.U)
        np.testing.assert_allclose(Q,Q.conj().T,atol=1e-15)
        for _ in range(20):
            v=self.rng.normal(size=5)+1j*self.rng.normal(size=5);a=w.evaluate(self.U,v)
            self.assertAlmostEqual(a['quadratic_delta'],a['readout']['delta'])
            self.assertAlmostEqual(a['self_delta']+a['interference_delta'],a['readout']['delta'])

    def test_readout_port_swap_changes_sign(self):
        v=[1,0,0,0,3];a=w.evaluate(self.U,v);b=w.evaluate(self.U,v,3,1)
        self.assertAlmostEqual(a['readout']['delta'],-b['readout']['delta'])
        self.assertAlmostEqual(a['positive']['power'],b['negative']['power'])

    def test_boundary_and_nonzero_threshold(self):
        self.assertIsNone(w.evaluate(np.eye(2),[1,1],0,1)['readout']['bit'])
        self.assertEqual(w.evaluate(np.eye(2),[1,1],0,1,threshold=.1)['readout']['bit'],0)
        self.assertIsNone(w.evaluate(np.eye(2),[1,0],0,1,threshold=1.)['readout']['bit'])
        self.assertIsNone(w.evaluate(np.eye(2),[0,0],0,1)['readout']['bit'])
        self.assertIsNone(w.evaluate(np.eye(2),[1e-6,0],0,1)['readout']['bit'])

    def test_input_scale_squares_power_and_absolute_epsilon(self):
        a=w.evaluate(np.eye(2),[2,1],0,1);b=w.evaluate(np.eye(2),[6,3],0,1)
        self.assertAlmostEqual(b['readout']['delta'],9*a['readout']['delta'])
        self.assertEqual(a['readout']['bit'],b['readout']['bit'])
        self.assertEqual(w.evaluate(np.eye(2),[2,1],0,1,threshold=4)['readout']['bit'],0)
        self.assertEqual(w.evaluate(np.eye(2),[6,3],0,1,threshold=4)['readout']['bit'],1)

    def test_global_phase_invariance(self):
        v=np.array([1,1,0,0,3],complex);a=w.evaluate(self.U,v)
        for phase in [.3,1.4,np.pi]:
            b=w.evaluate(self.U,v*np.exp(1j*phase))
            np.testing.assert_allclose(a['output_powers'],b['output_powers'],atol=1e-14)

    def test_relative_phase_cannot_be_discarded(self):
        row=[[1,1]]
        self.assertAlmostEqual(w.row_contributions(row,[1,1],0)['power'],4.)
        self.assertAlmostEqual(w.row_contributions(row,[1,1j],0)['power'],2.)
        self.assertAlmostEqual(w.row_contributions(row,[1,-1],0)['power'],0.)

    def test_independent_phase_average_removes_all_cross_terms(self):
        row=np.array([[1,1j,2]])/np.sqrt(6)
        powers=[w.row_contributions(row,[1,np.exp(1j*a),np.exp(1j*b)],0)['power']
                for a,b in itertools.product(2*np.pi*np.arange(8)/8,repeat=2)]
        self.assertAlmostEqual(float(np.mean(powers)),1.)

    def test_reference_phase_average_keeps_data_interference(self):
        row=np.ones((1,3))/np.sqrt(3)
        mean=np.mean([w.row_contributions(row,[1,1,np.exp(1j*a)],0)['power'] for a in 2*np.pi*np.arange(16)/16])
        self.assertAlmostEqual(float(mean),5/3)
        self.assertAlmostEqual(w.row_contributions(row,[1,1,1],0)['self_power'],1.)

    def test_inherited_and2_two_worked_cases(self):
        s=json.loads((ROOT/'config/m0_s3_reference_phases.json').read_text(encoding='utf-8'))['gates']['AND2']
        U=b7.transfer_matrix(b7.load_topology(),s['theta'],s['phi'])
        for bits,expected in [([1,0,0,0],0),([1,1,0,0],1)]:
            v=encoding.with_reference(bits);a=w.evaluate(U,v)
            self.assertEqual(a['readout']['bit'],expected)
            self.assertAlmostEqual(sum(a['output_powers']),sum(abs(v)**2))

    def test_cumulative_sum_and_no_input_mutation(self):
        v=np.array([1,2j,0,0,3],complex);saved=v.copy();U=self.U.copy();a=w.row_contributions(self.U,v,1)
        for k,z in enumerate(a['cumulative']):self.assertAlmostEqual(z,sum(a['terms'][:k+1]))
        a['input_field'][0]=99;a['coefficients'][0]=99
        np.testing.assert_array_equal(v,saved);np.testing.assert_array_equal(self.U,U)

    def test_validation(self):
        for matrix,v,out in [([],[],0),([[1,np.nan]],[1,1],0),([[1,2]],[1],0),
            ([[1]],[np.inf],0),([[1]],[1],True),([[1]],[1],1)]:
            with self.assertRaises(ValueError):w.row_contributions(matrix,v,out)
        with self.assertRaises(ValueError):w.difference_operator(np.eye(2),0,0)
        with self.assertRaises(ValueError):w.evaluate(np.eye(2),[1,0],0,1,epsilon=-1)
        with self.assertRaises(ValueError):w.evaluate(np.eye(2),[1,0],0,1,threshold=np.nan)


if __name__=='__main__':unittest.main(verbosity=2)
