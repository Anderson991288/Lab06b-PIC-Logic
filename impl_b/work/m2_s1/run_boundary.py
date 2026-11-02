"""M2 S1 boundary tables and cross-reference verification; no PDK solve."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import os,sys,json,hashlib,csv,io,unittest,importlib.util,copy,shutil
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;OUT=HERE/'out'
OUT.mkdir(exist_ok=True);DELIVERY=ROOT/'delivery/m2_s1_io';DELIVERY.mkdir(parents=True,exist_ok=True)
for key in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:os.environ[key]='1'
DLL_HANDLE=None
if os.name=='nt' and (Path(sys.prefix)/'Library/bin').is_dir():DLL_HANDLE=os.add_dll_directory(str(Path(sys.prefix)/'Library/bin'))
sys.path[:0]=[str(ROOT/'work'),str(HERE)]
from common import boundary,handoff


def suite(path,cls,log):
    spec=importlib.util.spec_from_file_location(cls,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(getattr(module,cls)))
    (OUT/log).write_text(stream.getvalue(),encoding='utf-8')
    return dict(run=r.testsRun,passed=r.testsRun-len(r.failures)-len(r.errors),failures=len(r.failures),errors=len(r.errors),successful=r.wasSuccessful())


spec=json.loads((ROOT/'pic_spec.json').read_text(encoding='utf-8'));spec_sha=handoff.digest(ROOT/'pic_spec.json')
plan=json.loads((ROOT/'config/m2_boundary.json').read_text(encoding='utf-8'))
summary=boundary.validate_plan(plan,spec,spec_sha)
tests=suite(HERE/'test_boundary.py','BoundaryTests','unit_tests.log')
regression={name:suite(ROOT/path,cls,name.lower()+'_regression.log') for name,path,cls in [
    ('M0_S3','work/m0_s3/test_optical_models.py','OpticalModels'),('M1_S1','work/m1_s1/test_encoding_readout.py','EncodingReadout'),
    ('M1_S2','work/m1_s2/test_b7.py','B7Tests'),('M1_S3','work/m1_s3/test_weighted_readout.py','WeightedReadoutTests'),
    ('M1_S4','work/m1_s4/test_logic_validation.py','LogicValidationTests'),('M1_S5','work/m1_s5/test_handoff.py','HandoffTests')]}
source_spec,phase_settings=handoff.load_bundle(ROOT/'delivery/m1_handoff')
replay=handoff.replay(source_spec,phase_settings)
csv_error=handoff.verify_truth_csv(ROOT/'delivery/m1_handoff',replay)
previous=json.loads((ROOT/'work/m1_s5/out/handoff_results.json').read_text(encoding='utf-8'))
unchanged=all(handoff.digest(ROOT/p)==digest for p,digest in previous['source_hashes'].items())
tables={'optical_io.csv':boundary.optical_rows(plan),'electrical_io.csv':boundary.electrical_rows(plan),
        'system_blocks.csv':plan['system_blocks'],'heater_returns.csv':plan['return_connections']}
csv_verified=[]
for name,rows in tables.items():
    with (DELIVERY/name).open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    with (DELIVERY/name).open(encoding='utf-8-sig',newline='') as stream:observed=list(csv.DictReader(stream))
    csv_verified.append(observed==[{k:str(v) for k,v in row.items()} for row in rows])
for source,dest in [(ROOT/'config/m2_boundary.json',DELIVERY/'boundary_plan.json'),(ROOT/'pic_spec.json',DELIVERY/'m1_pic_spec.json')]:shutil.copy2(source,dest)
(DELIVERY/'README.md').write_text('''# M2 S1 boundary and I/O plan

Logical boundary only: 10 proposed optical interfaces, 14 phase drive endpoints
and one logical shared return. These are not fabricated PAD counts or completed
edge couplers. Physical positions, cells, PAD IDs, voltage/current values and
heater calibration remain pending subsequent M2 steps.

boundary_plan.json is bound to m1_pic_spec.json by SHA-256. Original M1 files
and delivery/m1_handoff remain unchanged. All five outputs are preserved:
out1 -> PD_PLUS, out3 -> PD_MINUS; other outputs -> external monitor/load paths.
R amplitude 3 / power 9 refers to the normalized M1 core plane, not laser watts.
Source/receiver path gains and relative phases require calibration.
''',encoding='utf-8')
files=['boundary_plan.json','m1_pic_spec.json',*tables.keys(),'README.md']
manifest=dict(schema='lab06b.m2_s1_io_manifest.v1',files=[dict(path=p,sha256=handoff.digest(DELIVERY/p)) for p in files])
(DELIVERY/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
controlled=[]
for name in ['missing_unread_output','PD_inside_PIC','receiver_polarity_swapped','driver_channel_duplicated','R_power_confused_with_amplitude']:
    p=copy.deepcopy(plan)
    if name=='missing_unread_output':p['optical_io']=[r for r in p['optical_io'] if r['core_port']!='out0']
    if name=='PD_inside_PIC':next(r for r in p['system_blocks'] if r['id']=='PD_PAIR')['domain']='PIC'
    if name=='receiver_polarity_swapped':p['receiver']['positive_interface'],p['receiver']['negative_interface']=p['receiver']['negative_interface'],p['receiver']['positive_interface']
    if name=='driver_channel_duplicated':p['electrical_io'][1]['driver_channel']=p['electrical_io'][0]['driver_channel']
    if name=='R_power_confused_with_amplitude':p['core_field_targets']['reference_power']=3
    try:boundary.validate_plan(p,spec,spec_sha);rejected=False;reason='Not rejected'
    except ValueError as error:rejected=True;reason=str(error)
    controlled.append(dict(name=name,rejected=rejected,reason=reason))
    (OUT/(name+'.log')).write_text(reason,encoding='utf-8')
traces={r['interface_id']:boundary.trace_interface(plan,r['interface_id']) for r in plan['optical_io']+plan['electrical_io']}
checks=[('M1_spec_bound',plan['m1_spec_sha256']==spec_sha),('M1_sources_unchanged',unchanged),
    ('ten_core_optical_ports',summary['optical_interfaces']==10),('fourteen_drives_one_return',summary['phase_drive_interfaces']==14 and summary['logical_return_nets']==1),
    ('all_heater_returns_mapped',len(plan['return_connections'])==14),('external_readout_polarity',plan['receiver']['positive_interface']=='OPT_OUT1' and plan['receiver']['negative_interface']=='OPT_OUT3'),
    ('physical_pad_count_pending',summary['physical_pad_count'] is None),('CSV_tables_match',all(csv_verified)),
    ('M1_truth_replay',sum(r['summary']['passed'] for r in replay.values())==80 and csv_error<1e-10),
    ('five_controlled_errors_rejected',all(r['rejected'] for r in controlled)),
    ('delivery_hashes',all(handoff.digest(DELIVERY/r['path'])==r['sha256'] for r in manifest['files']))]
sources=['pic_spec.json','phase_settings.json','config/m2_boundary.json','work/common/boundary.py','work/common/handoff.py',
         'work/m2_s1/test_boundary.py','work/m2_s1/run_boundary.py']
result=dict(step='M2 S1',timestamp=datetime.now(timezone(timedelta(hours=8))).isoformat(),root=str(ROOT),root_matches_plan=ROOT.resolve()==Path('C:/EDA_Codex/Lab06b').resolve(),
    python=sys.executable,boundary_summary=summary,unit_tests=tests,regression=regression,plan=plan,
    traces=traces,M1_replay={g:r['summary'] for g,r in replay.items()},M1_source_hashes_unchanged=unchanged,
    controlled_errors=controlled,delivery_manifest=manifest,checks=[dict(name=name,passed=bool(ok)) for name,ok in checks],
    source_hashes={p:handoff.digest(ROOT/p) for p in sources},
    core_passed=tests['successful'] and all(r['successful'] for r in regression.values()) and all(ok for name,ok in checks),
    scope='Logical PIC/external-system boundary and proposed optical/electrical interfaces; no new PDK circuit, GDS, physical PAD count, heater voltage calibration or fabrication verification.')
(OUT/'boundary_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('M2 S1 tests:',tests)
print('Previous regression:',sum(r['passed'] for r in regression.values()),'/',sum(r['run'] for r in regression.values()))
print('Boundary:',summary)
print('M1 replay:',sum(r['summary']['passed'] for r in replay.values()),'/80; source hashes unchanged:',unchanged)
print('M2 S1 CORE:',result['core_passed'])
raise SystemExit(0 if result['core_passed'] else 1)
