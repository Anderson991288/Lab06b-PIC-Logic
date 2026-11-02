from pathlib import Path
import sys,json,unittest,copy
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'work'))
from common import boundary,handoff


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.spec=json.loads((ROOT/'pic_spec.json').read_text(encoding='utf-8'))
        self.sha=handoff.digest(ROOT/'pic_spec.json')
        self.plan=json.loads((ROOT/'config/m2_boundary.json').read_text(encoding='utf-8'))

    def test_port_coverage_and_counts(self):
        summary=boundary.validate_plan(self.plan,self.spec,self.sha)
        self.assertEqual(summary['optical_interfaces'],10);self.assertEqual(summary['phase_drive_interfaces'],14)
        self.assertEqual(summary['electrical_interface_roles'],15);self.assertIsNone(summary['physical_pad_count'])
        self.assertEqual({r['core_port'] for r in self.plan['optical_io']},{p['id'] for p in self.spec['optical_ports']})

    def test_block_boundary(self):
        domains={r['id']:r['domain'] for r in self.plan['system_blocks']}
        self.assertEqual({i for i,d in domains.items() if d=='PIC'},{'B7_CORE','OPTICAL_INTERFACES','HEATERS','ELECTRICAL_ROUTING'})
        for block in ['LASER_0','DATA_MODULATORS','PD_PAIR','TIA_COMPARATOR','HEATER_DRIVERS']:self.assertEqual(domains[block],'external')

    def test_shared_source_and_reference_plane(self):
        inputs=[r for r in self.plan['optical_io'] if r['direction']=='in']
        self.assertEqual({r['source_laser'] for r in inputs},{'LASER_0'})
        self.assertEqual(self.plan['core_field_targets']['reference_power'],9)
        self.assertIsNone(self.plan['core_field_targets']['power_unit_w'])
        self.assertIn('after_input_coupling',self.plan['reference_plane'])

    def test_output_polarity_and_unread_destinations(self):
        ports={r['core_port']:r for r in self.plan['optical_io']}
        self.assertEqual(ports['out1']['external_endpoint'],'PD_PLUS');self.assertEqual(ports['out3']['external_endpoint'],'PD_MINUS')
        self.assertEqual([ports[f'out{k}']['external_endpoint'] for k in [0,2,4]],['EXT_LOAD0','EXT_LOAD2','EXT_LOAD4'])

    def test_phase_to_driver_mapping(self):
        rows=[r for r in self.plan['electrical_io'] if r['kind']=='phase_drive']
        self.assertEqual([r['phase_channel'] for r in rows],self.spec['phase_vector_order'])
        self.assertEqual(len({r['driver_channel'] for r in rows}),14)
        self.assertEqual(len({r['drive_endpoint'] for r in rows}),14)
        for r in rows:self.assertEqual(r['drive_endpoint'],r['heater_logical_id']+'.A')

    def test_common_return_is_not_one_fabricated_pad(self):
        self.assertEqual(len(self.plan['return_connections']),14)
        self.assertEqual({r['net'] for r in self.plan['return_connections']},{'GND'})
        self.assertEqual({r['terminal'] for r in self.plan['return_connections']},{'B'})
        self.assertIsNone(self.plan['grounding']['physical_pad_count'])

    def test_optical_and_electrical_traces(self):
        self.assertEqual(boundary.trace_interface(self.plan,'OPT_IN4'),['EXT_REFERENCE','OPT_IN4','EC_IN4','in4'])
        self.assertEqual(boundary.trace_interface(self.plan,'OPT_OUT3')[-1],'PD_MINUS')
        self.assertEqual(boundary.trace_interface(self.plan,'CTRL_phi7'),['DRV13','CTRL_phi7','H_M7_phi.A','H_M7_phi.B','GND','DRV_RETURN'])
        with self.assertRaises(ValueError):boundary.trace_interface(self.plan,'unknown')

    def test_binding_and_version_guards(self):
        with self.assertRaises(ValueError):boundary.validate_plan(self.plan,self.spec,'0'*64)
        p=copy.deepcopy(self.plan);p['schema']='v99'
        with self.assertRaises(ValueError):boundary.validate_plan(p,self.spec,self.sha)

    def test_missing_unread_output_rejected(self):
        p=copy.deepcopy(self.plan);p['optical_io']=[r for r in p['optical_io'] if r['core_port']!='out0']
        with self.assertRaisesRegex(ValueError,'optical_io'):boundary.validate_plan(p,self.spec,self.sha)

    def test_detector_inside_chip_rejected(self):
        p=copy.deepcopy(self.plan);next(r for r in p['system_blocks'] if r['id']=='PD_PAIR')['domain']='PIC'
        with self.assertRaisesRegex(ValueError,'system_blocks'):boundary.validate_plan(p,self.spec,self.sha)

    def test_driver_alias_and_return_omission_rejected(self):
        for kind in ['driver','return']:
            p=copy.deepcopy(self.plan)
            if kind=='driver':p['electrical_io'][1]['driver_channel']=p['electrical_io'][0]['driver_channel']
            else:p['return_connections'].pop()
            with self.assertRaises(ValueError):boundary.validate_plan(p,self.spec,self.sha)

    def test_pending_physical_assignments(self):
        for kind in ['pad','position','drive','ground_count']:
            p=copy.deepcopy(self.plan)
            if kind=='pad':p['electrical_io'][0]['pad_id']='PAD1'
            if kind=='position':p['optical_io'][0]['physical_position_um']=[0,0]
            if kind=='drive':p['electrical_io'][0]['drive_value']=3.14
            if kind=='ground_count':p['grounding']['physical_pad_count']=1
            with self.assertRaises(ValueError):boundary.validate_plan(p,self.spec,self.sha)

    def test_reference_power_and_heater_data_role(self):
        p=copy.deepcopy(self.plan);p['core_field_targets']['reference_power']=3
        with self.assertRaises(ValueError):boundary.validate_plan(p,self.spec,self.sha)
        p=copy.deepcopy(self.plan);p['heater_role']='bit_rate_data_modulation'
        with self.assertRaises(ValueError):boundary.validate_plan(p,self.spec,self.sha)

    def test_csv_rows_and_no_mutation(self):
        before=copy.deepcopy(self.plan)
        self.assertEqual(len(boundary.optical_rows(self.plan)),10);self.assertEqual(len(boundary.electrical_rows(self.plan)),15)
        self.assertTrue(all(r['pad_id']=='pending_M2' for r in boundary.electrical_rows(self.plan)))
        self.assertEqual(self.plan,before)

    def test_M1_handoff_still_replays_80(self):
        s,p=handoff.load_bundle(ROOT/'delivery/m1_handoff')
        self.assertEqual(sum(v['summary']['passed'] for v in handoff.replay(s,p).values()),80)


if __name__=='__main__':unittest.main(verbosity=2)
