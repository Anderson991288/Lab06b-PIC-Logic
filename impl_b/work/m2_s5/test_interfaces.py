import unittest,copy
from common import chip_interfaces as c
class InterfaceTests(unittest.TestCase):
    config=None;info=None;core=None;boundary=None
    def test_A_drive_B_return_contract(self):
        bad=copy.deepcopy(self.config);bad['signal_terminal']='B';bad['return_terminal']='A'
        with self.assertRaises(ValueError):c.validate(bad)
    def test_no_unvalidated_EC_loss_claim(self):
        bad=copy.deepcopy(self.config);bad['EC']['coupling_loss_db']=0
        with self.assertRaises(ValueError):c.validate(bad)
    def test_pad_rows_fit_frame(self):
        bad=copy.deepcopy(self.config);bad['chip_top_y']=660
        with self.assertRaises(ValueError):c.validate(bad)
    def test_positive_fiber_pitch(self):
        bad=copy.deepcopy(self.config);bad['fiber_pitch']=-250
        with self.assertRaises(ValueError):c.validate(bad)
    def test_local_metal_min_width(self):
        bad=copy.deepcopy(self.config);bad['wire_width']=1
        with self.assertRaises(ValueError):c.validate(bad)
    def test_fans_keep_order(self):
        a=c.fan(0,600,440,0,self.config);b=c.fan(0,600,190,-30,self.config)
        self.assertTrue(all(p[1]-q[1]>=30-1e-9 for p,q in zip(a,b)))
    def test_driver_interfaces_preserved(self):
        for p in self.info['pads']:
            if p['net']=='GND':continue
            logical=next(x for x in self.boundary['electrical_io'] if x.get('phase_channel')==p['channel'])
            self.assertEqual(p['driver_channel'],logical['driver_channel']);self.assertEqual(p['drive_endpoint'],logical['drive_endpoint'])
    def test_A_B_coordinates_from_accepted_core(self):
        for p in self.info['pads']:
            if p['net']=='GND':continue
            ctl=next(x for x in self.core['phase_regions'] if x['channel']==p['channel'])
            self.assertEqual(p['signal_contact_um'],ctl['local_contacts'][0]['center_um']);self.assertEqual(p['return_contact_um'],ctl['local_contacts'][1]['center_um'])
