"""Topology, independent scalar replay, paths and optical invariants."""
from pathlib import Path
import sys, unittest, json
import numpy as np
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT/'work'))
from common import b7, mzi, linear_network as net
EXPECTED_OPS = ((0,0),(3,0),(1,1),(0,2),(2,2),(1,3),(3,3))


def scalar_replay(theta, phi, field):
    # Independent closed-form pair update, not embedding/cascade or common T2.
    value = np.array(field, dtype=complex, copy=True)
    for k, (p, layer) in enumerate(EXPECTED_OPS):
        a, b = value[p:p+2].copy(); s = np.sin(theta[k]/2); c = np.cos(theta[k]/2)
        q = 1j*np.exp(.5j*theta[k]); phase = np.exp(1j*phi[k])
        value[p], value[p+1] = q*(phase*s*a+c*b), q*(phase*c*a-s*b)
    return value


class B7Tests(unittest.TestCase):
    def setUp(self):
        self.top = b7.load_topology(); self.rng = np.random.default_rng(612)
        self.theta = self.rng.uniform(-5, 5, 7); self.phi = self.rng.uniform(-5, 5, 7)

    def test_course_contract_and_phase_order(self):
        self.assertEqual(self.top.ops, EXPECTED_OPS)
        self.assertEqual(self.top.readout, (1,3)); self.assertEqual(self.top.modes, 5)

    def test_bypass_ports_and_layer_population(self):
        self.assertEqual(b7.bypass_ports(self.top), [(2,), (0,3,4), (4,), (0,)])
        self.assertEqual(sum(map(len,b7.bypass_ports(self.top))), 6)

    def test_topology_guards(self):
        for modes, ops, read in [(4,EXPECTED_OPS,(1,3)), (True,EXPECTED_OPS,(1,3)),
            (5,EXPECTED_OPS[:-1],(1,3)), (5,((0,0),(1,0))+EXPECTED_OPS[2:],(1,3)),
            (5,EXPECTED_OPS[::-1],(1,3)), (5,EXPECTED_OPS,(1,1)), (5,EXPECTED_OPS,(1,5)),
            (5,((4,0),)+EXPECTED_OPS[1:],(1,3))]:
            with self.subTest(modes=modes,ops=ops,read=read), self.assertRaises(ValueError): b7.Topology(modes,ops,read)

    def test_parameter_and_trace_guards(self):
        for theta, phi, loss in [([0]*6,[0]*7,0), ([0]*7,[np.nan]*7,0), ([0]*7,[0]*7,-1),
                                  ([0]*7,[0]*7,[0]*6), ([np.inf]*7,[0]*7,0)]:
            with self.assertRaises(ValueError): b7.transfer_matrix(self.top, theta, phi, loss)
        for v in [[1,0], [1,0,0,0,np.inf]]:
            with self.assertRaises(ValueError): b7.trace(self.top, self.theta,self.phi,v)

    def test_identity_state_keeps_bypass_phase(self):
        np.testing.assert_allclose(b7.transfer_matrix(self.top,[np.pi]*7,[np.pi]*7),np.eye(5),atol=2e-15)

    def test_all_bar_retains_complex_phase(self):
        np.testing.assert_allclose(b7.transfer_matrix(self.top,[np.pi]*7,[0]*7),np.diag([1,1,-1,1,1]),atol=2e-15)

    def test_all_cross_known_permutation(self):
        expected = np.array([[0,0,-1,0,0],[0,0,0,0,-1j],[0,-1j,0,0,0],[0,0,0,-1,0],[1,0,0,0,0]])
        np.testing.assert_allclose(b7.transfer_matrix(self.top,[0]*7,[0]*7), expected, atol=2e-15)

    def test_random_unitarity_and_power(self):
        for _ in range(40):
            t,p = self.rng.uniform(-2*np.pi,2*np.pi,(2,7)); v=self.rng.normal(size=5)+1j*self.rng.normal(size=5)
            U=b7.transfer_matrix(self.top,t,p)
            np.testing.assert_allclose(U.conj().T@U,np.eye(5),atol=5e-15)
            self.assertAlmostEqual(float(np.vdot(U@v,U@v).real),float(np.vdot(v,v).real),places=11)

    def test_elements_and_layers_agree(self):
        for loss in [0.,.4,np.arange(7)/10]:
            U=b7.transfer_matrix(self.top,self.theta,self.phi,loss)
            np.testing.assert_allclose(U,net.cascade(b7.layers(self.top,self.theta,self.phi,loss),5),atol=1e-15)

    def test_same_layer_commutes_but_cross_layer_not(self):
        e=b7.elements(self.top,self.theta,self.phi)
        for a,b in [(0,1),(3,4),(5,6)]:np.testing.assert_allclose(e[a]@e[b],e[b]@e[a],atol=1e-15)
        self.assertGreater(np.linalg.norm(e[2]@e[0]-e[0]@e[2]),.1)

    def test_independent_pairwise_scalar_replay(self):
        for _ in range(20):
            t,p=self.rng.uniform(-6,6,(2,7));v=self.rng.normal(size=5)+1j*self.rng.normal(size=5)
            np.testing.assert_allclose(b7.transfer_matrix(self.top,t,p)@v,scalar_replay(t,p,v),atol=4e-15)

    def test_basis_probes_are_columns_not_rows(self):
        U=b7.transfer_matrix(self.top,self.theta,self.phi)
        columns=np.column_stack([scalar_replay(self.theta,self.phi,np.eye(5)[:,k]) for k in range(5)])
        np.testing.assert_allclose(U,columns,atol=2e-15)
        self.assertGreater(np.linalg.norm(U-columns.T),.1)

    def test_trace_boundary_and_input_copy(self):
        v=np.array([1,0,1,0,3],complex); saved=v.copy()
        a=b7.trace(self.top,self.theta,self.phi,v); b=b7.trace(self.top,self.theta,self.phi,v,by_layer=True)
        for micro,layer in [(0,0),(2,1),(3,2),(5,3),(7,4)]:np.testing.assert_allclose(a[micro][1],b[layer][1],atol=1e-15)
        np.testing.assert_array_equal(v,saved)
        a[0][1][0]=99; np.testing.assert_array_equal(v,saved)

    def test_structural_zeros_follow_directed_paths(self):
        support=np.ones((5,5),bool);support[0,3:]=False
        np.testing.assert_array_equal(b7.reachability(self.top),support)
        for _ in range(20):
            t,p=self.rng.uniform(-6,6,(2,7));U=b7.transfer_matrix(self.top,t,p)
            np.testing.assert_allclose(U[~support],0,atol=1e-15)

    def test_passive_loss_and_bypass_not_global_attenuation(self):
        loss=1.; counts=np.array([2,4,3,3,2])
        U=b7.transfer_matrix(self.top,[np.pi]*7,[0]*7,loss)
        np.testing.assert_allclose(abs(np.diag(U))**2,10**(-loss*counts/10),atol=1e-15)
        for v in self.rng.normal(size=(20,5)):
            M=b7.transfer_matrix(self.top,self.theta,self.phi,.5)
            self.assertLessEqual(sum(mzi.powers(M@v)),sum(mzi.powers(v))+1e-12)

    def test_change_one_phase_changes_matrix(self):
        U=b7.transfer_matrix(self.top,self.theta,self.phi); changed=self.theta.copy();changed[2]+=.2
        self.assertGreater(np.linalg.norm(U-b7.transfer_matrix(self.top,changed,self.phi)),.1)

    def test_inherited_complex_matrices(self):
        saved=json.loads((ROOT/'config/m0_s3_reference_phases.json').read_text(encoding='utf-8'))
        self.assertEqual(tuple(map(tuple,saved['ops'])),self.top.ops)
        for gate, data in saved['gates'].items():
            with self.subTest(gate=gate):
                expected=np.array([[complex(*z) for z in row] for row in data['U']])
                np.testing.assert_allclose(b7.transfer_matrix(self.top,data['theta'],data['phi']),expected,atol=1e-12)


if __name__=='__main__': unittest.main(verbosity=2)
