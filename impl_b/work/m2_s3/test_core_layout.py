import unittest,copy,math
from common import core_layout as c

class CoreLayoutTests(unittest.TestCase):
    config=None;info=None;spec_sha=None
    def test_bound_spec(self):
        x=copy.deepcopy(self.config);x['m1_spec_sha256']='0'*64
        with self.assertRaises(ValueError):c.validate(x,self.spec_sha)
    def test_phase_straight_reserves_contacts(self):
        x=copy.deepcopy(self.config);x['phase_region_length']=100
        with self.assertRaises(ValueError):c.validate(x,self.spec_sha)
    def test_finite_dimensions(self):
        x=copy.deepcopy(self.config);x['pitch']=float('nan')
        with self.assertRaises(ValueError):c.validate(x,self.spec_sha)
    def test_sample_count(self):
        x=copy.deepcopy(self.config);x['s_bend_samples']=10
        with self.assertRaises(ValueError):c.validate(x,self.spec_sha)
    def test_empty_curved_span(self):
        x=copy.deepcopy(self.config);x['s_bend_length']=.5
        with self.assertRaises(ValueError):c.validate(x,self.spec_sha)
    def test_adjacent_contact_gap(self):
        x=copy.deepcopy(self.config);x['pitch']=18
        with self.assertRaises(ValueError):c.validate(x,self.spec_sha)
    def test_local_port_alignment(self):self.assertLess(self.info['unit']['max_join_error_um'],1e-9)
    def test_local_arm_balance(self):self.assertLess(abs(self.info['unit']['inter_mmi_upper_um']-self.info['unit']['inter_mmi_lower_um']),1e-9)
    def test_grid_all_centerlines(self):
        for p in self.info['paths']:
            for xy in p['points_um']:
                for v in xy:self.assertAlmostEqual(v*1000,round(v*1000),places=6)
    def test_unique_phase_endpoints(self):
        ends=[e['endpoint'] for c in self.info['phase_regions'] for e in c['local_contacts']]
        self.assertEqual(len(ends),28);self.assertEqual(len(set(ends)),28)
    def test_upper_theta_region_inside_inter_mmi(self):
        u=self.info['unit'];theta=next(v for v in u['controls'] if v['parameter']=='theta')
        self.assertGreater(theta['heated_start_um'],u['mmi_positions_um'][0][0]+u['mmi_ports']['out2'][0])
        self.assertLess(theta['heated_end_um'],u['mmi_positions_um'][1][0]+u['mmi_ports']['in2'][0])
    def test_lower_rails_and_direction(self):
        for p in self.info['ports']:
            self.assertEqual(p['position_um'][1],-p['mode']*self.config['pitch'])
            self.assertEqual(p['angle_deg'],180 if p['direction']=='in' else 0)
