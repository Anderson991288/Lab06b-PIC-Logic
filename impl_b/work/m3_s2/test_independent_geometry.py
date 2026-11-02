from pathlib import Path
import math,uuid,unittest
import shapely,gdstk
from shapely.geometry import box,Polygon
from shapely.affinity import rotate
from independent_geometry import read_material,measure_facing
HERE=Path(__file__).resolve().parent
class IndependentGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder=HERE/'work'/('tests_'+uuid.uuid4().hex);assert cls.folder.resolve().is_relative_to((HERE/'work').resolve());cls.folder.mkdir(parents=True)
    def measure(self,g,w=12,s=12,limits=True):return measure_facing(g,w,s,include_boundary_limits=limits)
    def test_exact_rectangle_width(self):self.assertAlmostEqual(self.measure(box(0,0,10,.45))['width']['minimum']['value_um'],.45,places=10)
    def test_rotated_rectangle_width(self):self.assertAlmostEqual(self.measure(rotate(box(0,0,10,.45),37))['width']['minimum']['value_um'],.45,places=9)
    def test_two_component_gap(self):self.assertAlmostEqual(self.measure(shapely.union_all([box(0,0,10,1),box(0,1.2,10,2.2)]))['space']['minimum']['value_um'],.2,places=10)
    def test_merged_seam_is_not_gap(self):
        r=self.measure(shapely.union_all([box(0,0,5,1),box(5,0,10,1)]));self.assertAlmostEqual(r['width']['minimum']['value_um'],1);self.assertIsNone(r['space']['minimum'])
    def notch(self):return box(0,0,10,10).difference(Polygon([(2,4.735),(10,4),(10,6),(2,5.265)]))
    def test_closed_notch_one_sided_minimum(self):
        m=self.measure(self.notch())['space']['minimum'];self.assertAlmostEqual(m['value_um'],.53,places=10);self.assertEqual(m['visibility'],'one_sided_boundary_limit')
    def test_strict_connector_misses_notch_limit(self):
        old=self.measure(self.notch(),limits=False)['space']['minimum'];self.assertTrue(old is None or old['value_um']>.53+1e-6)
    def test_hole_kept_as_empty_space(self):
        r=self.measure(box(0,0,10,10).difference(box(1,1,9,9)));self.assertAlmostEqual(r['width']['minimum']['value_um'],1);self.assertAlmostEqual(r['space']['minimum']['value_um'],8)
    def test_shielding_retains_nearest_real_gap(self):
        r=self.measure(shapely.union_all([box(0,0,10,1),box(0,1.3,10,2.3),box(0,2.9,10,3.9)]));self.assertAlmostEqual(r['space']['minimum']['value_um'],.3,places=10)
    def test_library_units_convert_to_um(self):
        lib=gdstk.Library(unit=1e-9,precision=1e-12);c=lib.new_cell('NANOMETER');c.add(gdstk.rectangle((0,0),(10000,450),layer=3));p=self.folder/'units.gds';lib.write_gds(str(p));m,meta=read_material(p,3);self.assertAlmostEqual(self.measure(m)['width']['minimum']['value_um'],.45,places=10);self.assertAlmostEqual(meta['precision_um'],.000001)
    def test_hierarchy_rotation_and_reflection(self):
        lib=gdstk.Library();u=lib.new_cell('UNIT');u.add(gdstk.rectangle((0,0),(10,1),layer=3));top=lib.new_cell('TOP');top.add(gdstk.Reference(u,origin=(20,20),rotation=math.pi/2,x_reflection=True,magnification=2));p=self.folder/'hierarchy.gds';lib.write_gds(str(p));m,_=read_material(p,3);self.assertAlmostEqual(self.measure(m,24,24)['width']['minimum']['value_um'],2,places=9)
    def test_invalid_polygon_is_rejected(self):
        lib=gdstk.Library();c=lib.new_cell('INVALID');c.add(gdstk.Polygon([(0,0),(2,2),(0,2),(2,0)],layer=3));p=self.folder/'invalid.gds';lib.write_gds(str(p))
        with self.assertRaises(ValueError):read_material(p,3)
    def test_missing_layer_is_rejected(self):
        lib=gdstk.Library();c=lib.new_cell('MISSING');c.add(gdstk.rectangle((0,0),(1,1),layer=39));p=self.folder/'missing.gds';lib.write_gds(str(p))
        with self.assertRaises(ValueError):read_material(p,3)
