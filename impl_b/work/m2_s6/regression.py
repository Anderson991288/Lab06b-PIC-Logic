from pathlib import Path
import os,sys,json,io,unittest,importlib.util
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;OUT=HERE/'out'
for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:os.environ[k]='1'
sys.path.insert(0,str(ROOT/'work'))
from common import handoff,chip_interfaces
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def suite(path,cls,setup=None):
    s=importlib.util.spec_from_file_location(cls,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);t=getattr(m,cls)
    if setup:setup(t)
    stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(t))
    (OUT/(cls+'_regression.log')).write_text(stream.getvalue(),encoding='utf-8')
    return dict(run=r.testsRun,passed=r.testsRun-len(r.failures)-len(r.errors),successful=r.wasSuccessful())
core=load(ROOT/'work/m2_s4/out/after/layout_info.json')
def setupcore(t):t.config=load(ROOT/'config/m2_review_layout.json');t.info=core;t.spec_sha=handoff.digest(ROOT/'pic_spec.json')
def setupinterfaces(t):t.config=load(ROOT/'config/m2_chip_interfaces.json');t.info=load(ROOT/'work/m2_s5/out/chip_info.json');t.core=core;t.boundary=load(ROOT/'config/m2_boundary.json')
reg={name:suite(ROOT/path,cls,setupcore if name=='M2_S3' else setupinterfaces if name=='M2_S5' else None) for name,path,cls in [
    ('M0_S3','work/m0_s3/test_optical_models.py','OpticalModels'),('M1_S1','work/m1_s1/test_encoding_readout.py','EncodingReadout'),
    ('M1_S2','work/m1_s2/test_b7.py','B7Tests'),('M1_S3','work/m1_s3/test_weighted_readout.py','WeightedReadoutTests'),
    ('M1_S4','work/m1_s4/test_logic_validation.py','LogicValidationTests'),('M1_S5','work/m1_s5/test_handoff.py','HandoffTests'),
    ('M2_S1','work/m2_s1/test_boundary.py','BoundaryTests'),('M2_S2','work/m2_s2/test_pdk_circuit.py','PdkCircuitTests'),
    ('M2_S3','work/m2_s3/test_core_layout.py','CoreLayoutTests'),('M2_S5','work/m2_s5/test_interfaces.py','InterfaceTests')]}
old=load(ROOT/'work/m1_s5/out/handoff_results.json');unchanged=all(handoff.digest(ROOT/p)==h for p,h in old['source_hashes'].items()) and handoff.digest(ROOT/old['zip'])==old['zip_sha256']
spec,settings=handoff.load_bundle(ROOT/'delivery/m1_handoff');results=handoff.replay(spec,settings);passed=sum(r['summary']['passed'] for r in results.values())
(OUT/'regression.json').write_text(json.dumps(dict(regression=reg,M1_sources_and_zip_unchanged=unchanged,M1_baseline_replay_passed=passed),ensure_ascii=False,indent=2),encoding='utf-8')
print('Existing regression',sum(r['passed'] for r in reg.values()),'; M1 baseline',passed,'/80; immutable',unchanged)
assert all(r['successful'] for r in reg.values()) and unchanged and passed==80
