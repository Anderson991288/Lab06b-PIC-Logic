from pathlib import Path
import sys,json,copy,unittest,importlib.util
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'work'))
from common import logic_validation as logic,b7


class LogicValidationTests(unittest.TestCase):
    def setUp(self):
        self.top=b7.load_topology()
        self.catalog=json.loads((ROOT/'config/m1_s4_phase_programs.json').read_text(encoding='utf-8'))
        self.setting=self.catalog['gates']['AND2']

    def test_truth_from_independent_index_sets(self):
        ones={'AND2':{3,7,11,15},'OR2':set(range(16))-{0,4,8,12},'XOR2':{1,2,5,6,9,10,13,14},'AND4':{15},'OR4':set(range(1,16))}
        for gate in logic.GATES:
            for index,bits in enumerate(logic.patterns()):self.assertEqual(logic.truth(gate,bits),int(index in ones[gate]))

    def test_all_patterns_and_display_order(self):
        values=logic.patterns();self.assertEqual(len(set(values)),16)
        self.assertEqual(values[1],(1,0,0,0));self.assertEqual(values[3],(1,1,0,0));self.assertEqual(values[15],(1,1,1,1))

    def test_catalog_full_precision_source(self):
        logic.validate_programs(self.catalog,self.top)
        fixture=json.loads((ROOT/'config/m0_s3_reference_phases.json').read_text(encoding='utf-8'))
        for gate in logic.GATES:
            for key in ['theta','phi']:np.testing.assert_array_equal(self.catalog['gates'][gate][key],fixture['gates'][gate][key])

    def test_catalog_guards(self):
        variants=[]
        for key,value in [('phase_unit','degree'),('phase_order',['M1']*7),('ops_zero_based',[[0,0]]*7)]:
            c=copy.deepcopy(self.catalog);c[key]=value;variants.append(c)
        c=copy.deepcopy(self.catalog);del c['gates']['OR4'];variants.append(c)
        c=copy.deepcopy(self.catalog);c['gates']['AND2']['theta']=[0]*6;variants.append(c)
        c=copy.deepcopy(self.catalog);c['gates']['AND2']['phi'][0]=np.nan;variants.append(c)
        for c in variants:
            with self.assertRaises(ValueError):logic.validate_programs(c,self.top)

    def test_all_80_truths_and_clearance(self):
        results=[logic.evaluate_gate(self.top,self.catalog['gates'][gate],gate) for gate in logic.GATES]
        self.assertEqual(sum(r['summary']['passed'] for r in results),80)
        for r in results:
            self.assertTrue(r['summary']['accepted']);self.assertGreater(r['summary']['minimum_clearance'],0)
            self.assertEqual(r['summary']['boundaries'],0)

    def test_class_counts_are_not_four_case_shortcuts(self):
        for gate,count in zip(logic.GATES,[4,12,8,1,15]):
            r=logic.evaluate_gate(self.top,self.catalog['gates'][gate],gate)
            self.assertEqual(sum(row['expected'] for row in r['rows']),count)
            self.assertEqual(r['summary']['confusion_actual_by_predicted'],[[16-count,0],[0,count]])

    def test_unitarity_and_full_saved_complex_U(self):
        fixture=json.loads((ROOT/'config/m0_s3_reference_phases.json').read_text(encoding='utf-8'))
        for gate in logic.GATES:
            U=logic.evaluate_gate(self.top,self.catalog['gates'][gate],gate)['U']
            saved=np.array([[complex(*z) for z in row] for row in fixture['gates'][gate]['U']])
            np.testing.assert_allclose(U,saved,atol=1e-12)
            np.testing.assert_allclose(U.conj().T@U,np.eye(5),atol=5e-15)

    def test_energy_all_five_outputs(self):
        for gate in logic.GATES:
            for row in logic.evaluate_gate(self.top,self.catalog['gates'][gate],gate)['rows']:
                self.assertAlmostEqual(row['input_total_power'],sum(row['bits'])+9)
                self.assertAlmostEqual(row['input_total_power'],row['output_total_power'],places=11)

    def test_unused_inputs_all_four_variants(self):
        for gate in logic.GATES[:3]:
            rows=logic.evaluate_gate(self.top,self.catalog['gates'][gate],gate)['rows']
            groups=logic.unused_input_groups(rows,gate)
            self.assertEqual(len(groups),4)
            self.assertTrue(all(g['passed'] and g['complete'] for g in groups))

    def test_missing_unused_combinations_cannot_pass(self):
        rows=logic.evaluate_gate(self.top,self.setting,'AND2')['rows'][:4]
        self.assertFalse(any(g['passed'] for g in logic.unused_input_groups(rows,'AND2')))

    def test_swapped_ports_rejected_even_when_unitary(self):
        for gate in logic.GATES:
            r=logic.evaluate_gate(self.top,self.catalog['gates'][gate],gate,readout=(3,1))
            self.assertEqual(r['summary']['passed'],0)
            np.testing.assert_allclose(r['U'].conj().T@r['U'],np.eye(5),atol=5e-15)

    def test_signed_margin_not_absolute_difference(self):
        r=logic.evaluate_gate(self.top,self.setting,'AND2',readout=(3,1))
        self.assertGreater(r['summary']['minimum_abs_delta'],0)
        self.assertLess(r['summary']['minimum_signed_margin'],0)
        self.assertFalse(r['summary']['accepted'])

    def test_boundary_is_not_valid_logic(self):
        identity=dict(theta=[np.pi]*7,phi=[np.pi]*7)
        r=logic.evaluate_gate(self.top,identity,'AND2')
        self.assertGreater(r['summary']['boundaries'],0);self.assertFalse(r['summary']['accepted'])
        for row in r['rows']:
            if row['bit'] is None:self.assertFalse(row['correct'])

    def test_reference_removal_exposes_failed_truths(self):
        total=sum(logic.evaluate_gate(self.top,self.catalog['gates'][gate],gate,reference_amplitude=0)['summary']['passed'] for gate in logic.GATES)
        self.assertLess(total,80)

    def test_phase_offsets_and_passive_loss(self):
        zero=logic.evaluate_gate(self.top,self.setting,'AND2',theta_offsets=[0]*7)
        base=logic.evaluate_gate(self.top,self.setting,'AND2')
        np.testing.assert_array_equal(zero['U'],base['U'])
        changed=logic.evaluate_gate(self.top,self.setting,'AND2',theta_offsets=[.2]+[0]*6,loss_db=.2)
        self.assertGreater(np.linalg.norm(changed['U']-base['U']),.05)
        self.assertTrue(all(r['output_total_power']<=r['input_total_power']+1e-12 for r in changed['rows']))

    def test_no_mutation_and_invalid_parameters(self):
        saved=copy.deepcopy(self.setting);logic.evaluate_gate(self.top,self.setting,'AND2');self.assertEqual(self.setting,saved)
        for kw in [{'epsilon':-1},{'threshold':np.nan},{'theta_offsets':[0]*6},{'reference_amplitude':-1}]:
            with self.assertRaises(ValueError):logic.evaluate_gate(self.top,self.setting,'AND2',**kw)
        with self.assertRaises(ValueError):logic.truth('NAND2',[0]*4)
        with self.assertRaises(ValueError):logic.truth('AND2',[0,1,2,0])

    def test_independent_scalar_replay_all_patterns(self):
        spec=importlib.util.spec_from_file_location('independent_b7_test',ROOT/'work/m1_s2/test_b7.py')
        oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
        for gate in logic.GATES:
            setting=self.catalog['gates'][gate]
            for row in logic.evaluate_gate(self.top,setting,gate)['rows']:
                v=np.array([*row['bits'],3],complex)
                np.testing.assert_allclose(row['field'],oracle.scalar_replay(setting['theta'],setting['phi'],v),atol=1e-12)

    def test_summary_requires_epsilon_and_cases(self):
        with self.assertRaises(ValueError):logic.summarize([],1e-10)
        rows=logic.evaluate_gate(self.top,self.setting,'AND2')['rows']
        with self.assertRaises(ValueError):logic.summarize(rows,np.nan)


if __name__=='__main__':unittest.main(verbosity=2)
