"""Structural interface tests independent of the ideal transfer oracle."""
import unittest
from collections import Counter
from common import pdk_circuit as c,b7

class PdkCircuitTests(unittest.TestCase):
    def setUp(self):self.top=b7.load_topology();self.net=c.wiring(self.top)
    def test_all_external_names(self):
        self.assertEqual(set(self.net['external_port_names'].values()),{f'{side}{k}' for side in ['in','out'] for k in range(5)})
    def test_every_internal_port_once(self):
        counts=Counter(x for e in self.net['edges'] for x in [e['source'],e['destination']] if not x.startswith('B7:'))
        self.assertEqual(set(counts.values()),{1});self.assertEqual(len(counts),28)
    def test_external_endpoints_once(self):
        ends=[x for e in self.net['edges'] for x in [e['source'],e['destination']] if x.startswith('B7:')]
        self.assertEqual(len(ends),len(set(ends)));self.assertEqual(len(ends),10)
    def test_nine_inter_mzi_links(self):self.assertEqual(len(self.net['links']),9)
    def test_bypass_roles(self):self.assertEqual(self.net['bypass_by_layer'],[[2],[0,3,4],[4],[0]])
    def test_layer_direction(self):
        layers={f'M{k+1}':l for k,(p,l) in enumerate(self.top.ops)}
        for a,b in self.net['links']:self.assertLess(layers[a.split(':')[0]],layers[b.split(':')[0]])
    def test_first_input_is_upper_m1(self):self.assertEqual(self.net['external_port_names']['M1:in0'],'in0')
    def test_reference_path_starts_lower_m2(self):self.assertEqual(self.net['external_port_names']['M2:in1'],'in4')
    def test_readout_ends(self):
        self.assertEqual(self.net['external_port_names']['M6:out0'],'out1')
        self.assertEqual(self.net['external_port_names']['M7:out0'],'out3')
    def test_phase_input_rejection(self):
        for a,b in [([0]*6,[0]*7),([0]*7,[float('nan')]*7)]:
            with self.assertRaises(ValueError):c.circuit(self.top,a,b)
