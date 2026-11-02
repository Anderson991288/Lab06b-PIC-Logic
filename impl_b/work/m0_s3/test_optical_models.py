"""Physical invariants and independent regressions for the common optical models."""
from pathlib import Path
import json,math,sys,unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'work'))
from common import mzi
from common import linear_network as network


def closed_form(theta,phi):
    # Independent scalar expressions, preserving global complex phase.
    a=1j*np.exp(.5j*theta);s=np.sin(theta/2);c=np.cos(theta/2)
    return np.array([[a*np.exp(1j*phi)*s,a*c],[a*np.exp(1j*phi)*c,-a*s]])


class OpticalModels(unittest.TestCase):
    def assertClose(self,a,b,tol=1e-12):
        self.assertTrue(np.allclose(a,b,rtol=0,atol=tol),f'{a!r} != {b!r}')

    def test_mmi_quadrature_and_unitarity(self):
        self.assertClose(mzi.H.conj().T@mzi.H,np.eye(2))
        self.assertAlmostEqual(float(np.angle(mzi.H[0,1]/mzi.H[0,0])),np.pi/2)
        self.assertClose(abs(mzi.H)**2,np.full((2,2),.5))

    def test_exact_switch_and_split_matrices(self):
        self.assertClose(mzi.T2(0,0),[[0,1j],[1j,0]])
        self.assertClose(mzi.T2(np.pi,0),[[-1,0],[0,1]])
        self.assertClose(mzi.T2(np.pi/2,0),np.array([[-1+1j,-1+1j],[-1+1j,1-1j]])/2)

    def test_closed_form_complex_regression(self):
        rng=np.random.default_rng(603)
        for theta,phi in rng.uniform(-4*np.pi,4*np.pi,(100,2)):
            with self.subTest(theta=theta,phi=phi):self.assertClose(mzi.T2(theta,phi),closed_form(theta,phi))

    def test_unitarity_with_coupler_imbalance(self):
        rng=np.random.default_rng(604)
        for _ in range(80):
            theta,phi=rng.uniform(-8,8,2);errors=rng.uniform(-.3,.3,2)
            u=mzi.T2(theta,phi,mmi_errors=errors)
            self.assertClose(u.conj().T@u,np.eye(2))

    def test_scalar_path_replay_matches_matrix(self):
        v=np.array([.3+.8j,-.2+.5j]);theta=.73;phi=-.41;errors=(-.07,.13);loss=1.4
        upper,lower=v;upper*=np.exp(1j*phi)
        c,s=np.sqrt(.5+errors[0]),np.sqrt(.5-errors[0])
        upper,lower=c*upper+1j*s*lower,1j*s*upper+c*lower
        upper*=np.exp(1j*theta)
        c,s=np.sqrt(.5+errors[1]),np.sqrt(.5-errors[1])
        expected=np.array([c*upper+1j*s*lower,1j*s*upper+c*lower])*10**(-loss/20)
        self.assertClose(mzi.T2(theta,phi,loss,errors)@v,expected)

    def test_insertion_loss_is_power_db(self):
        v=np.array([1+.2j,.5-.3j]);pin=float(mzi.powers(v).sum())
        for loss in [0,3,6,20,60]:
            u=mzi.T2(.7,.2,loss)
            self.assertAlmostEqual(float(mzi.powers(u@v).sum())/pin,10**(-loss/10),places=12)
            self.assertClose(u.conj().T@u,10**(-loss/10)*np.eye(2))
        self.assertAlmostEqual(mzi.amplitude_factor(20),.1)

    def test_phi_single_input_power_and_two_input_interference(self):
        for phi in [0,.3,np.pi,4.7]:self.assertClose(mzi.powers(mzi.T2(.8,phi)@[1,0]),mzi.powers(mzi.T2(.8,0)@[1,0]))
        v=np.ones(2)/np.sqrt(2)
        self.assertClose(mzi.powers(mzi.T2(np.pi/2,0)@v),[1,0])
        self.assertClose(mzi.powers(mzi.T2(np.pi/2,np.pi)@v),[0,1])

    def test_global_phase_invariance(self):
        v=np.array([.8+.1j,-.2+.5j]);g=np.exp(.87j);u=mzi.T2(1.2,.4)
        self.assertClose(u@(g*v),g*(u@v));self.assertClose(mzi.powers(u@v),mzi.powers(u@(g*v)))

    def test_complex_phase_periodicity(self):
        u=mzi.T2(.3,-.8)
        self.assertClose(u,mzi.T2(.3+2*np.pi,-.8));self.assertClose(u,mzi.T2(.3,-.8+2*np.pi))

    def test_lower_first_adapter_matches_s2_convention(self):
        for theta,phi in [(0,0),(.9,-.5),(np.pi/2,np.pi)]:
            lower=mzi.H@np.diag([1,np.exp(1j*theta)])@mzi.H@np.diag([1,np.exp(1j*phi)])
            self.assertClose(mzi.to_lower_first(mzi.T2(theta,phi)),lower)
        s2=json.loads((ROOT/'work/m0_s2/out/physics_results.json').read_text(encoding='utf-8'))
        vectors={'cross':[1,0],'split':[1,0],'bar':[1,0],
                 'combine_pi':np.array([1,-1])/np.sqrt(2),'combine_0':np.ones(2)/np.sqrt(2)}
        for case in s2['ideal_mzi']:
            power=mzi.powers(mzi.to_lower_first(mzi.T2(case['theta_rad']))@vectors[case['case']])
            self.assertClose(power,case['power'])

    def test_inverse_bar_fraction(self):
        for target in [0,.1,.25,.5,.9,1]:
            theta=mzi.theta_for_bar(target)
            self.assertTrue(0<=theta<=np.pi)
            self.assertAlmostEqual(float(mzi.powers(mzi.T2(theta)@[1,0])[0]),target,places=12)

    def test_parameter_guards(self):
        invalid=[lambda:mzi.T2(np.nan),lambda:mzi.T2(0,np.inf),lambda:mzi.T2(0,loss_db=-1),
                 lambda:mzi.coupler(.51),lambda:mzi.theta_for_bar(-.1),lambda:mzi.phase_shift(0,'middle'),
                 lambda:mzi.apply_matrix(np.eye(2),[1]),lambda:network.embed_2x2(np.eye(2),0,0,5),
                 lambda:network.embed_2x2(np.eye(2),0,5,5),lambda:network.cascade([np.eye(2)],5),
                 lambda:network.power_difference_readout([1,0],0,0),lambda:network.power_difference_readout([1,0],0,1,epsilon=-1)]
        for index,call in enumerate(invalid):
            with self.subTest(index=index),self.assertRaises(ValueError):call()

    def test_no_input_or_constant_mutation(self):
        v=np.array([1,.3j]);original=v.copy();u=mzi.T2(.2,.3);copy=u.copy()
        mzi.apply_matrix(u,v);mzi.to_lower_first(u);mzi.trace(.2,.3,v)
        self.assertClose(v,original);self.assertClose(u,copy)
        c=mzi.coupler();c[0,0]=99;self.assertNotEqual(mzi.H[0,0],99)

    def test_nonadjacent_embedding_and_order(self):
        v=np.array([1,2,3,4,5],complex);t=mzi.T2(.4,.7)
        expected=v.copy();expected[[0,4]]=t@v[[0,4]]
        self.assertClose(network.embed_2x2(t,0,4,5)@v,expected)
        a=network.embed_2x2(mzi.T2(.9,.5),0,1,3)
        b=network.embed_2x2(mzi.T2(.2,-.4),1,2,3)
        self.assertClose(network.cascade([a,b],3),b@a)
        self.assertFalse(np.allclose(a@b,b@a))
        self.assertClose(network.cascade([],3),np.eye(3))

    def test_readout_boundary_has_no_valid_bit(self):
        self.assertIsNone(network.power_difference_readout([0,1,0,1])['bit'])
        self.assertIsNone(network.power_difference_readout([0,1,0,1],threshold=1e-12)['bit'])
        self.assertEqual(network.power_difference_readout([0,2,0,1])['bit'],1)
        self.assertEqual(network.power_difference_readout([0,1,0,2])['bit'],0)

    def test_trace_and_propagation_agree(self):
        v=np.array([.8+.4j,-.1+.7j]);rows=mzi.trace(.6,-.3,v,loss_db=2)
        self.assertClose(rows[-1][1],mzi.T2(.6,-.3,loss_db=2)@v)
        stages=[network.embed_2x2(mzi.T2(.8),0,1,3),network.embed_2x2(mzi.T2(.4,.3),1,2,3)]
        field=np.array([1,2j,.4]);trace=network.propagate_stages(stages,field)
        self.assertClose(trace[-1],network.cascade(stages,3)@field)
        for row in trace:self.assertAlmostEqual(float(mzi.powers(row).sum()),float(mzi.powers(field).sum()),places=12)

    def test_effective_index_phase_and_units(self):
        report=json.loads((ROOT/'work/m0_s2/out/physics_results.json').read_text(encoding='utf-8'))
        n=report['fem']['convergence'][-1]['neff'];wavelength=report['parameters']['wavelength_um']
        self.assertClose(mzi.propagation_factor(n,wavelength/n,wavelength),1)
        self.assertClose(mzi.propagation_factor(n,wavelength/(2*n),wavelength),-1)
        self.assertClose(mzi.propagation_factor(n,0,wavelength),1)
        with self.assertRaises(ValueError):mzi.propagation_factor(n,1,0)

    def test_b7_80_cases_against_boolean_truth_and_saved_complex_U(self):
        fixture=json.loads((ROOT/'config/m0_s3_reference_phases.json').read_text(encoding='utf-8'))
        functions={'AND2':lambda b:b[0]&b[1],'OR2':lambda b:b[0]|b[1],
                   'XOR2':lambda b:b[0]^b[1],'AND4':lambda b:int(all(b)),'OR4':lambda b:int(any(b))}
        for name,setting in fixture['gates'].items():
            stages=[network.embed_2x2(mzi.T2(setting['theta'][k],setting['phi'][k]),p,p+1,5) for k,(p,_) in enumerate(fixture['ops'])]
            u=network.cascade(stages,5)
            saved=np.array([[complex(*z) for z in row] for row in setting['U']])
            self.assertClose(u,saved)
            for integer in range(16):
                bits=[(integer>>j)&1 for j in range(4)];v=np.array([*bits,3],complex)
                result=network.power_difference_readout(u@v)
                with self.subTest(gate=name,bits=bits):
                    self.assertEqual(result['bit'],functions[name](bits))
                    self.assertAlmostEqual(float(mzi.powers(u@v).sum()),float(mzi.powers(v).sum()),places=11)


if __name__=='__main__':unittest.main(verbosity=2)
