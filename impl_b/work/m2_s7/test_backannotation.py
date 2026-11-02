import unittest,copy
import numpy as np
from common import backannotation as a,b7,handoff
class BackannotationTests(unittest.TestCase):
    spec=None;paths=None;model=None;catalog=None
    def test_zero_propagation_matches_original_complex_matrix(self):
        top=handoff.validate_spec(self.spec)
        for s in self.catalog.values():self.assertLess(np.max(np.abs(a.transfer(self.spec,self.paths,self.model,s,propagate=False)-b7.transfer_matrix(top,s['theta'],s['phi']))),1e-12)
    def test_exact_one_cm_loss_conversion(self):self.assertAlmostEqual(abs(a.factor(10000,self.model,3)),10**(-3/20),places=12)
    def test_phase_sign_one_quarter_cycle(self):
        m=copy.deepcopy(self.model);m['neff']=1;m['wavelength_um']=4
        self.assertLess(abs(a.factor(1,m)-1j),1e-12)
    def test_gauge_compensation_full_complex_law(self):
        offset=a.compensation(self.spec,self.paths,self.model);programs=a.candidate(self.catalog,offset);D=np.diag(np.exp(1j*np.array(offset['output_phase_rad'])))
        for gate in self.catalog:self.assertLess(np.max(np.abs(a.transfer(self.spec,self.paths,self.model,programs[gate])-D@a.transfer(self.spec,self.paths,self.model,self.catalog[gate],propagate=False))),1e-9)
    def test_asymmetric_arm_length_compensation(self):
        paths=copy.deepcopy(self.paths);next(p for p in paths['paths'] if p['id']=='M3:WG2')['length_um']+=.19
        off=a.compensation(self.spec,paths,self.model);self.assertAlmostEqual(off['theta_offsets'][2],-a.beta(self.model)*.19,places=10)
        setting=a.candidate(self.catalog,off)['AND2'];target=np.diag(np.exp(1j*np.array(off['output_phase_rad'])))@a.transfer(self.spec,paths,self.model,self.catalog['AND2'],propagate=False)
        self.assertLess(np.max(np.abs(a.transfer(self.spec,paths,self.model,setting)-target)),1e-9)
    def test_lossless_unitarity_with_lengths(self):
        for s in self.catalog.values():
            U=a.transfer(self.spec,self.paths,self.model,s);self.assertLess(np.max(np.abs(U.conj().T@U-np.eye(5))),1e-10)
    def test_passive_loss_does_not_amplify(self):
        U=a.transfer(self.spec,self.paths,self.model,self.catalog['OR4'],3)
        self.assertLessEqual(np.linalg.svd(U,compute_uv=False).max(),1+1e-12)
    def test_duplicate_path_rejected(self):
        p=copy.deepcopy(self.paths);p['paths'][0]['id']=p['paths'][1]['id']
        with self.assertRaises(ValueError):a.index_paths(p)
    def test_missing_path_rejected(self):
        p=copy.deepcopy(self.paths);p['paths'].pop()
        with self.assertRaises(ValueError):a.index_paths(p)
    def test_nonfinite_path_rejected(self):
        p=copy.deepcopy(self.paths);p['paths'][0]['length_um']=float('nan')
        with self.assertRaises(ValueError):a.index_paths(p)
    def test_wrong_reference_plane_rejected(self):
        m=copy.deepcopy(self.model);m['reference_plane']='fiber'
        with self.assertRaises(ValueError):a.validate_model(m)
    def test_physical_qualification_not_inferred(self):
        m=copy.deepcopy(self.model);m['physical_function_qualified']=True
        with self.assertRaises(ValueError):a.validate_model(m)
