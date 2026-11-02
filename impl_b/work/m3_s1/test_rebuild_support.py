from pathlib import Path
import unittest,struct,hashlib,uuid
from rebuild_support import normalized_gds_bytes,safe_source_path,reserve_empty_target
HERE=Path(__file__).resolve().parent
def record(kind,payload=b''):return struct.pack('>HH',4+len(payload),kind)+payload
def gds(year=2026,xy=3,name=b'CELL'):
    date=struct.pack('>12h',*(year,1,1,0,0,0)*2)
    return record(0x0002,struct.pack('>h',600))+record(0x0102,date)+record(0x0502,date)+record(0x0606,name)+record(0x1003,struct.pack('>2i',xy,4))+record(0x0700)+record(0x0400)
class RebuildSupportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=HERE/'work'/('unit_'+uuid.uuid4().hex);assert cls.base.resolve().is_relative_to((HERE/'work').resolve());cls.base.mkdir(parents=True)
    def test_only_dates_normalize(self):self.assertEqual(normalized_gds_bytes(gds(2026)),normalized_gds_bytes(gds(2050)))
    def test_coordinate_change_remains_visible(self):self.assertNotEqual(normalized_gds_bytes(gds(xy=3))[0],normalized_gds_bytes(gds(xy=4))[0])
    def test_cell_name_change_remains_visible(self):self.assertNotEqual(normalized_gds_bytes(gds(name=b'CELL'))[0],normalized_gds_bytes(gds(name=b'FAIL'))[0])
    def test_truncated_record_rejected(self):
        with self.assertRaises(ValueError):normalized_gds_bytes(gds()[:-1])
    def test_invalid_record_length_rejected(self):
        with self.assertRaises(ValueError):normalized_gds_bytes(b'\x00\x02\x00\x02')
    def test_malformed_date_record_rejected(self):
        with self.assertRaises(ValueError):normalized_gds_bytes(record(0x0102,b'xx')+record(0x0400))
    def test_trailing_bytes_rejected(self):
        with self.assertRaises(ValueError):normalized_gds_bytes(gds()+b'\x00\x00')
    def test_generated_seed_and_traversal_rejected(self):
        for value in ['work/m2_s4/out/layout_info.json','layout/file.gds','delivery/file.zip','../escape.py','C:/absolute.py']:
            with self.subTest(value=value),self.assertRaises(ValueError):safe_source_path(value)
        self.assertEqual(str(safe_source_path('config/m2_review_layout.json')),'config/m2_review_layout.json')
    def test_existing_target_refused(self):
        target=self.base/'existing';reserve_empty_target(target,self.base)
        with self.assertRaises(ValueError):reserve_empty_target(target,self.base)
    def test_target_escape_refused(self):
        with self.assertRaises(ValueError):reserve_empty_target(self.base.parent/'escape',self.base)
