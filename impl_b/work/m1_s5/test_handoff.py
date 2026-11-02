from pathlib import Path
import sys,json,copy,unittest,tempfile
import numpy as np
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'work'),str(HERE)]
from common import handoff
from package_tools import build_package


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.spec=json.loads((ROOT/'pic_spec.json').read_text(encoding='utf-8'))
        self.phases=json.loads((ROOT/'phase_settings.json').read_text(encoding='utf-8'))
        self.sha=handoff.digest(ROOT/'pic_spec.json')

    def test_contract_counts_and_pending_assignments(self):
        top=handoff.validate_spec(self.spec)
        self.assertEqual(len(top.ops),7);self.assertEqual(len(self.spec['optical_ports']),10)
        self.assertEqual(len(self.spec['phase_channels']),14);self.assertEqual(len(self.spec['architecture']['bypass_segments']),6)
        self.assertTrue(all(c['pad_id'] is None and c['calibration'] is None for c in self.spec['phase_channels']))

    def test_spec_phase_binding(self):
        handoff.validate_phases(self.spec,self.phases,self.sha)
        with self.assertRaisesRegex(ValueError,'spec_sha256'):handoff.validate_phases(self.spec,self.phases,'0'*64)

    def test_phase_vectors_replay_all_80(self):
        result=handoff.replay(self.spec,self.phases)
        self.assertEqual(sum(r['summary']['passed'] for r in result.values()),80)
        baseline=json.loads((ROOT/'work/m1_s4/out/logic_results.json').read_text(encoding='utf-8'))
        for gate,r in result.items():
            U=np.array([[complex(*z) for z in row] for row in baseline['baseline'][gate]['U']])
            np.testing.assert_allclose(r['U'],U,atol=1e-12)

    def test_named_channels_support_consistent_reordering(self):
        s=copy.deepcopy(self.spec);p=copy.deepcopy(self.phases)
        order=list(reversed(range(14)))
        s['phase_vector_order']=[self.spec['phase_vector_order'][k] for k in order]
        p['channel_order']=s['phase_vector_order']
        p['programs']={g:[v[k] for k in order] for g,v in p['programs'].items()}
        p['spec_sha256']='test-reordered-spec'
        handoff.validate_phases(s,p,'test-reordered-spec')
        for gate,r in handoff.replay(s,p).items():np.testing.assert_allclose(r['U'],handoff.replay(self.spec,self.phases)[gate]['U'],atol=1e-12)

    def test_unsupported_version_and_units_rejected(self):
        for key,value in [('schema','v99'),('units',dict(phase='degree',length='nm',power='normalized'))]:
            s=copy.deepcopy(self.spec);s[key]=value
            with self.assertRaises(ValueError):handoff.validate_spec(s)

    def test_ops_bypass_and_instance_crossrefs(self):
        for variant in ['mode','bypass','channel']:
            s=copy.deepcopy(self.spec)
            if variant=='mode':s['architecture']['instances'][0]['modes']=[1,2]
            if variant=='bypass':s['architecture']['bypass_segments'].pop()
            if variant=='channel':s['architecture']['instances'][0]['theta_channel']='theta2'
            with self.assertRaises(ValueError):handoff.validate_spec(s)

    def test_duplicate_and_wrong_phase_mapping(self):
        for variant in ['duplicate','location','order']:
            s=copy.deepcopy(self.spec)
            if variant=='duplicate':s['phase_channels'][0]['id']='theta2'
            if variant=='location':s['phase_channels'][0]['location']='upper_input_before_MMI1'
            if variant=='order':s['phase_vector_order'][0]='theta2'
            with self.assertRaises(ValueError):handoff.validate_spec(s)

    def test_phase_vectors_and_gate_coverage(self):
        for variant in ['count','nan','bool','order','unit','gate']:
            p=copy.deepcopy(self.phases)
            if variant=='count':p['programs']['AND2'].pop()
            if variant=='nan':p['programs']['AND2'][0]=np.nan
            if variant=='bool':p['programs']['AND2'][0]=True
            if variant=='order':p['channel_order']=p['channel_order'][::-1]
            if variant=='unit':p['phase_unit']='degree'
            if variant=='gate':del p['programs']['OR4']
            with self.assertRaises(ValueError):handoff.validate_phases(self.spec,p,self.sha)

    def test_port_polarity_encoding_and_coverage_guards(self):
        for variant in ['port','readout','reference','patterns']:
            s=copy.deepcopy(self.spec)
            if variant=='port':s['optical_ports'][8]['role']='unread_output'
            if variant=='readout':s['readout']['positive_port']='out3'
            if variant=='reference':s['encoding']['reference_amplitude']=9
            if variant=='patterns':s['acceptance']['patterns_per_function']=4
            with self.assertRaises(ValueError):handoff.validate_spec(s)

    def test_boolean_numeric_and_unjustified_physical_values(self):
        for variant in ['bool','pad','calibration','model']:
            s=copy.deepcopy(self.spec)
            if variant=='bool':s['readout']['threshold']=False
            if variant=='pad':s['phase_channels'][0]['pad_id']='PAD1'
            if variant=='calibration':s['phase_channels'][0]['calibration']={'Vpi':1.0}
            if variant=='model':s['model']['physical_calibration']=True
            with self.assertRaises(ValueError):handoff.validate_spec(s)

    def bundle(self):
        root=HERE/'test_temp';root.mkdir(exist_ok=True)
        tmp=tempfile.TemporaryDirectory(dir=root)
        self.assertTrue(Path(tmp.name).resolve().is_relative_to(root.resolve()))
        build_package(ROOT,Path(tmp.name));return tmp

    def test_self_contained_bundle_and_csv(self):
        with self.bundle() as directory:
            s,p=handoff.load_bundle(directory)
            self.assertLess(handoff.verify_truth_csv(directory,handoff.replay(s,p)),1e-10)

    def test_digest_tampering_detected(self):
        with self.bundle() as directory:
            path=Path(directory)/'phase_settings.json';path.write_text(path.read_text(encoding='utf-8')+' ',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'digest'):handoff.load_bundle(directory)

    def test_relative_manifest_paths_and_duplicates(self):
        with self.bundle() as directory:
            p=Path(directory)/'manifest.json';m=json.loads(p.read_text(encoding='utf-8'));saved=copy.deepcopy(m)
            m['files'][0]['path']='../outside';p.write_text(json.dumps(m),encoding='utf-8')
            with self.assertRaises(ValueError):handoff.verify_manifest(directory)
            saved['files'].append(saved['files'][0]);p.write_text(json.dumps(saved),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'duplicate'):handoff.verify_manifest(directory)

    def test_csv_mapping_has_semantic_validation(self):
        with self.bundle() as directory:
            p=Path(directory)/'phase_channels.csv';text=p.read_text(encoding='utf-8-sig');p.write_text(text.replace('H_M1_theta','H_M2_theta'),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'CSV'):handoff.verify_tables(directory,self.spec)

    def test_truth_csv_requires_exact_coverage(self):
        with self.bundle() as directory:
            p=Path(directory)/'acceptance_truth.csv';text=p.read_text(encoding='utf-8-sig');p.write_text('\n'.join(text.splitlines()[:-1]),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'80'):handoff.verify_truth_csv(directory,handoff.replay(self.spec,self.phases))


if __name__=='__main__':unittest.main(verbosity=2)
