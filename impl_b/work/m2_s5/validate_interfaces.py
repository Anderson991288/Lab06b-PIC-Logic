from pathlib import Path
import os,sys,json,io,unittest,importlib.util
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;OUT=HERE/'out'
for key in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:os.environ[key]='1'
sys.path.insert(0,str(ROOT/'work'))
from common import handoff,chip_interfaces
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def suite(path,cls,prepare=None):
    s=importlib.util.spec_from_file_location(cls,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);t=getattr(m,cls)
    if prepare:prepare(t)
    stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(t))
    (OUT/(cls+'_tests.log')).write_text(stream.getvalue(),encoding='utf-8')
    return dict(run=r.testsRun,passed=r.testsRun-len(r.failures)-len(r.errors),successful=r.wasSuccessful())
B=load(OUT/'chip_build.json');I=load(OUT/'chip_info.json');C=load(ROOT/'config/m2_chip_interfaces.json');boundary=load(ROOT/'config/m2_boundary.json')
core=load(next(ROOT/p for p in B['current_core_hashes'] if p.endswith('/layout_info.json')))
def setup(t):t.config=C;t.info=I;t.core=core;t.boundary=boundary
def setupcore(t):t.config=load(ROOT/'config/m2_review_layout.json');t.info=core;t.spec_sha=handoff.digest(ROOT/'pic_spec.json')
tests=suite(HERE/'test_interfaces.py','InterfaceTests',setup)
regression={name:suite(ROOT/path,cls,setupcore if name=='M2_S3' else None) for name,path,cls in [
    ('M0_S3','work/m0_s3/test_optical_models.py','OpticalModels'),('M1_S1','work/m1_s1/test_encoding_readout.py','EncodingReadout'),
    ('M1_S2','work/m1_s2/test_b7.py','B7Tests'),('M1_S3','work/m1_s3/test_weighted_readout.py','WeightedReadoutTests'),
    ('M1_S4','work/m1_s4/test_logic_validation.py','LogicValidationTests'),('M1_S5','work/m1_s5/test_handoff.py','HandoffTests'),
    ('M2_S1','work/m2_s1/test_boundary.py','BoundaryTests'),('M2_S2','work/m2_s2/test_pdk_circuit.py','PdkCircuitTests'),
    ('M2_S3','work/m2_s3/test_core_layout.py','CoreLayoutTests')]}
old=load(ROOT/'work/m1_s5/out/handoff_results.json');unchanged=all(handoff.digest(ROOT/p)==h for p,h in old['source_hashes'].items()) and handoff.digest(ROOT/old['zip'])==old['zip_sha256']
spec,phases=handoff.load_bundle(ROOT/'delivery/m1_handoff');replay=handoff.replay(spec,phases);passed=sum(r['summary']['passed'] for r in replay.values())
faults=load(OUT/'connectivity_faults.json');core_unchanged=all(handoff.digest(ROOT/p)==h for p,h in B['current_core_hashes'].items())
checks=[('actual_GDS_selected_connectivity',B['readback']['passed']),('six_scoped_rule_screens',all(r['width_warnings']==r['space_warnings']==0 for r in B['readback']['scoped_rules'])),
    ('16_physical_pads_15_logical_roles',I['counts']['physical_pads']==16 and I['counts']['signal_pads']==14 and I['counts']['ground_pads']==2 and I['counts']['logical_return_nets']==1),
    ('core_original_files_unchanged',core_unchanged),('three_negative_controls_detected',all(r['detected'] for r in faults)),
    ('M1_immutable_and_baseline',unchanged and passed==80),('new_interface_tests',tests['successful']),('existing_regression',all(r['successful'] for r in regression.values())),
    ('optical_and_voltage_calibration_pending',all(p['coupling_loss_db'] is None and p['path_phase_rad'] is None for p in I['optical_io']) and all(p['voltage_calibration'] is None for p in I['pads'] if p['net']!='GND'))]
paths=['work/m2_s5/test_interfaces.py','work/m2_s5/validate_interfaces.py','work/m2_s5/connectivity_faults.py']
result=dict(step='M2 S5',root=str(ROOT),counts=B['counts'],chip_size_um=B['chip_size_um'],unit_tests=tests,regression=regression,
    readback=B['readback'],EC_audit=B['EC_audit'],controlled_faults=faults,M1_sources_and_zip_unchanged=unchanged,M1_baseline_replay_passed=passed,
    accepted_core_files_unchanged=core_unchanged,checks=[dict(name=n,passed=bool(v)) for n,v in checks],
    source_hashes={**B['source_hashes'],**{p:handoff.digest(ROOT/p) for p in paths}},
    gds_sha256=handoff.digest(OUT/'b7_ec_pad.gds'),
    scope='Initial reference EC/fanout and PAD/GND geometry around exact accepted core. Selected GDS connectivity and local rule screens passed; no qualified EC, full process DRC/LVS, packaging, heater/common-ground calibration or layout-extracted truth replay.',
    core_passed=all(v for n,v in checks))
(OUT/'interface_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
if result['core_passed']:
    pointer=dict(schema='lab06b.current_chip.v1',accepted_at_step='M2 S5',qualification='interface_geometry_and_selected_connectivity_only',
        m1_spec_sha256=handoff.digest(ROOT/'pic_spec.json'),core_index='config/m2_current_core.json',
        files={str((OUT/name).relative_to(ROOT)).replace('\\','/'):handoff.digest(OUT/name) for name in ['b7_ec_pad.gds','chip_info.json','pad_heater_map.csv','optical_io.csv','ground_pads.csv']},
        results='work/m2_s5/out/interface_results.json',pending=['qualified EC and optical mode/response','full DRC and connectivity','thermal/common-ground calibration','layout path backannotation and replay'])
    (ROOT/'config/m2_current_chip.json').write_text(json.dumps(pointer,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('M2 S5 tests',tests,'regressions',sum(r['passed'] for r in regression.values()),'CORE',result['core_passed'])
raise SystemExit(0 if result['core_passed'] else 1)
