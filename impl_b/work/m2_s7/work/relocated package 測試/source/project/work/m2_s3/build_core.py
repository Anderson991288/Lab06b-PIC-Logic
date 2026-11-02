"""Build a new physical B7 core, export/re-read GDS and measured paths."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import os,sys,json,csv,subprocess,hashlib,io,unittest,importlib.util,copy
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;OUT=HERE/'out'
OUT.mkdir(exist_ok=True);os.environ['MPLCONFIGDIR']=str(HERE/'work/matplotlib')
for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:os.environ[k]='1'
sys.path.insert(0,str(ROOT/'work'))
from common import core_layout as geo,handoff,b7,pdk_circuit
import numpy as np
def save(name,v):(OUT/name).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def suite(path,cls,log,prepare=None):
    s=importlib.util.spec_from_file_location(cls,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);t=getattr(m,cls)
    if prepare:prepare(t)
    stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(t))
    (OUT/log).write_text(stream.getvalue(),encoding='utf-8')
    return dict(run=r.testsRun,passed=r.testsRun-len(r.failures)-len(r.errors),successful=r.wasSuccessful())
spec,settings=handoff.load_bundle(ROOT/'delivery/m1_handoff');spec_sha=handoff.digest(ROOT/'pic_spec.json');top=handoff.validate_spec(spec)
c=json.loads((ROOT/'config/m2_core_layout.json').read_text(encoding='utf-8'));geo.validate(c,spec_sha)
core,preview,info=geo.build(top,c)
for cell,name in [(core,'b7_core.gds'),(preview,'mzi_core.gds')]:cell.get_default_view(geo.i3.LayoutView).write_gdsii(str(OUT/name))
save('layout_info.json',info)
cfg=json.loads((ROOT/'EDA_paths.json').read_text(encoding='utf-8'));exe=Path(cfg['windows']['klayout_exe'])
if not exe.is_absolute():exe=ROOT/exe
def readback(gds,output):
    cmd=[str(exe),'-b','-r',str(HERE/'verify_gds.py'),'-rd','input_gds='+str(gds),'-rd','info_json='+str(OUT/'layout_info.json'),'-rd','output_json='+str(output)]
    r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
    (OUT/(output.stem+'.log')).write_text(r.stdout+'\n'+r.stderr,encoding='utf-8')
    if r.returncode:raise RuntimeError('KLayout readback failed: '+r.stderr[-1200:])
    return json.loads(output.read_text(encoding='utf-8'))
gds=readback(OUT/'b7_core.gds',OUT/'gds_readback.json')
# Run the independent checker against deliberately wrong sidecar coordinates.
# These controls test the checker, without modifying final GDS or learner files.
negative=[]
for kind in ['shifted_port','shifted_mzi','shifted_joint']:
    bad=copy.deepcopy(info)
    if kind=='shifted_port':bad['ports'][0]['position_um'][1]+=1
    elif kind=='shifted_mzi':bad['placement'][0]['origin_um'][0]+=1
    else:bad['joints'][0]['position_um'][1]+=1
    folder=HERE/'work'/kind;folder.mkdir(parents=True,exist_ok=True)
    sidecar=folder/'info.json';sidecar.write_text(json.dumps(bad),encoding='utf-8')
    cmd=[str(exe),'-b','-r',str(HERE/'verify_gds.py'),'-rd','input_gds='+str(OUT/'b7_core.gds'),'-rd','info_json='+str(sidecar),'-rd','output_json='+str(folder/'result.json')]
    r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
    (folder/'run.log').write_text(r.stdout+'\n'+r.stderr,encoding='utf-8')
    if r.returncode:raise RuntimeError('Controlled readback execution failed')
    observed=json.loads((folder/'result.json').read_text(encoding='utf-8'))
    negative.append(dict(name=kind,detected=not observed['passed'],failed_checks=[v['name'] for v in observed['checks'] if not v['passed']]))
save('controlled_readback.json',negative)

def setup(t):t.config=c;t.info=info;t.spec_sha=spec_sha
tests=suite(HERE/'test_core_layout.py','CoreLayoutTests','unit_tests.log',setup)
regression={name:suite(ROOT/path,cls,name.lower()+'_regression.log') for name,path,cls in [
    ('M0_S3','work/m0_s3/test_optical_models.py','OpticalModels'),('M1_S1','work/m1_s1/test_encoding_readout.py','EncodingReadout'),
    ('M1_S2','work/m1_s2/test_b7.py','B7Tests'),('M1_S3','work/m1_s3/test_weighted_readout.py','WeightedReadoutTests'),
    ('M1_S4','work/m1_s4/test_logic_validation.py','LogicValidationTests'),('M1_S5','work/m1_s5/test_handoff.py','HandoffTests'),
    ('M2_S1','work/m2_s1/test_boundary.py','BoundaryTests'),('M2_S2','work/m2_s2/test_pdk_circuit.py','PdkCircuitTests')]}
phase_map=sorted(info['phase_regions'],key=lambda p:spec['phase_vector_order'].index(p['channel']))
tables={
    'optical_ports.csv':[dict(port=p['id'],mode=p['mode'],direction=p['direction'],role=p['core_role'],x_um=p['position_um'][0],y_um=p['position_um'][1],angle_deg=p['angle_deg'],EC_cell='pending_M2_S5') for p in info['ports']],
    'phase_regions.csv':[dict(channel=p['channel'],heater_logical_id=p['heater_logical_id'],x_um=p['center_um'][0],y_um=p['center_um'][1],A_x_um=p['local_contacts'][0]['center_um'][0],A_y_um=p['local_contacts'][0]['center_um'][1],B_x_um=p['local_contacts'][1]['center_um'][0],B_y_um=p['local_contacts'][1]['center_um'][1],probe_pad_id='pending_M2_S5',voltage_calibration='pending') for p in phase_map],
    'waveguide_lengths.csv':[dict(path_id=p['id'],kind=p['kind'],length_um=p['length_um'],start_x_um=p['points_um'][0][0],start_y_um=p['points_um'][0][1],end_x_um=p['points_um'][-1][0],end_y_um=p['points_um'][-1][1]) for p in info['paths']]}
csv_ok=[]
for name,rows in tables.items():
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    with (OUT/name).open(encoding='utf-8-sig',newline='') as f:actual=list(csv.DictReader(f))
    csv_ok.append(actual==[{k:str(v) for k,v in row.items()} for row in rows])
old=json.loads((ROOT/'work/m1_s5/out/handoff_results.json').read_text(encoding='utf-8'))
unchanged=all(handoff.digest(ROOT/p)==h for p,h in old['source_hashes'].items()) and handoff.digest(ROOT/old['zip'])==old['zip_sha256']
s2=json.loads((ROOT/'work/m2_s2/out/pdk_results.json').read_text(encoding='utf-8'))
s2_unchanged=all(handoff.digest(ROOT/p)==h for p,h in s2['source_hashes'].items())
replay=handoff.replay(spec,settings);replay_pass=sum(r['summary']['passed'] for r in replay.values())
u=info['unit'];channel_ids={p['channel'] for p in phase_map}
checks=[('independent_GDS_readback',gds['passed']),('phase_channels_match_M1',channel_ids==set(spec['phase_vector_order'])),
    ('MMI_join_error',u['max_join_error_um']<1e-9),('balanced_local_waveguides',abs(u['waveguide_upper_um']-u['waveguide_lower_um'])<1e-9),
    ('continuous_bend_radius',u['continuous_s_bend_min_radius_um']>=5),('measured_path_counts',len(info['paths'])==58),
    ('CSV_round_trip',all(csv_ok)),('three_bad_coordinate_copies_detected',all(r['detected'] for r in negative)),
    ('M1_sources_and_zip_unchanged',unchanged),('M2S2_sources_unchanged',s2_unchanged),('M1_baseline_replay_80',replay_pass==80),
    ('physical_calibration_pending',all(p['pad_id'] is None and p['voltage_calibration'] is None for p in phase_map))]
sources=['config/m2_core_layout.json','work/common/core_layout.py','work/m2_s3/build_core.py','work/m2_s3/verify_gds.py','work/m2_s3/test_core_layout.py']
result=dict(step='M2 S3',timestamp=datetime.now(timezone(timedelta(hours=8))).isoformat(),root=str(ROOT),
    counts=info['counts'],dimensions=dict(optical_span_um=info['core_optical_span_um'],design_frame_um=info['core_frame_size_um'],column_um=info['column_length_um']),
    unit_summary={k:u[k] for k in ['waveguide_upper_um','waveguide_lower_um','inter_mmi_upper_um','inter_mmi_lower_um','max_join_error_um','continuous_s_bend_min_radius_um']},
    gds_readback=gds,unit_tests=tests,regression=regression,checks=[dict(name=n,passed=bool(v)) for n,v in checks],
    controlled_errors=negative,M1_sources_and_zip_unchanged=unchanged,M2S2_sources_unchanged=s2_unchanged,M1_baseline_replay_passed=replay_pass,
    source_hashes={p:handoff.digest(ROOT/p) for p in sources},gds_files={p:handoff.digest(OUT/p) for p in ['b7_core.gds','mzi_core.gds']},
    scope='Initial physical B7 core, actual PDK MMI geometry, custom local heaters and contacts. Scoped independent KLayout readback; no foundry DRC/LVS, EC, probe PADs, return routing, thermal calibration or layout-extracted truth replay. M1 replay is baseline only.',
    core_passed=tests['successful'] and all(r['successful'] for r in regression.values()) and all(v for n,v in checks))
save('layout_results.json',result)
print('M2 S3:',info['counts'],'dimensions',result['dimensions'],flush=True)
print('Readback',gds['passed'],'Tests',tests,'regression',sum(r['passed'] for r in regression.values()),'CORE',result['core_passed'],flush=True)
raise SystemExit(0 if result['core_passed'] else 1)
