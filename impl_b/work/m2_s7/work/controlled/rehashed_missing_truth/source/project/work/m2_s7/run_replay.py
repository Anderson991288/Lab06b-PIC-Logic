from pathlib import Path
from datetime import datetime,timezone,timedelta
import os,sys,json,copy,csv,io,unittest,importlib.util
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;OUT=HERE/'out'
for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:os.environ[k]='1'
HANDLE=os.add_dll_directory(str(Path(sys.prefix)/'Library/bin')) if os.name=='nt' else None
sys.path.insert(0,str(ROOT/'work'))
import numpy as np
from common import backannotation as a,handoff
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def pairs(U):return np.stack([U.real,U.imag],axis=-1).tolist()
spec,phases=handoff.load_bundle(ROOT/'delivery/m1_handoff');catalog=handoff.phase_catalog(spec,phases);paths=load(OUT/'paths.json');model=load(ROOT/'config/m2_backannotation.json')
a.validate_model(model);fem=load(ROOT/'work/m0_s2/out/physics_results.json');fine=next(r for r in fem['fem']['convergence'] if r['label']=='fine')
assert model['neff']==fine['neff'] and model['wavelength_um']==spec['design_point']['wavelength_um']
offset=a.compensation(spec,paths,model);candidate=a.candidate(catalog,offset)
settings=dict(schema='lab06b.model_phase_programs.v1',original_spec_sha256=handoff.digest(ROOT/'pic_spec.json'),original_phases_sha256=handoff.digest(ROOT/'phase_settings.json'),
    gds_sha256=paths['gds_sha256'],model_sha256=handoff.digest(ROOT/'config/m2_backannotation.json'),channel_order=spec['phase_vector_order'],phase_unit='rad',
    programs={g:[s['theta'][int(c[5:])-1] if c.startswith('theta') else s['phi'][int(c[3:])-1] for c in spec['phase_vector_order']] for g,s in candidate.items()},
    offsets=offset,voltage_calibration=None,physical_function_qualified=False,
    scope='Analytic phase-only candidate for this uniform-neff core-plane model; no truth fitting or heater-voltage instructions.')
save(OUT/'phase_settings_backannotated.json',settings)
cases={};raw={};csvrows=[]
for name,program,loss,prop in [('ideal_baseline',catalog,0.,False),('length_original',catalog,0.,True),('length_compensated',candidate,0.,True),('loss_original',catalog,model['illustrative_loss_db_per_cm'],True),('loss_compensated',candidate,model['illustrative_loss_db_per_cm'],True)]:
    result=a.evaluate(spec,paths,model,program,loss,prop);raw[name]=result
    functions={g:dict(passed=r['passed'],total=16,minimum_signed_margin=r['minimum_signed_margin'],max_unitarity_error=float(np.max(np.abs(r['U'].conj().T@r['U']-np.eye(5))))) for g,r in result.items()}
    cases[name]=dict(passed=sum(r['passed'] for r in result.values()),total=80,loss_db_per_cm=loss,propagation_enabled=prop,phase_source='model_candidate' if program is candidate else 'original_M1',functions=functions,matrices={g:pairs(r['U']) for g,r in result.items()},rows=[row for r in result.values() for row in r['rows']])
    for r in cases[name]['rows']:csvrows.append({k:v for k,v in dict(case=name,**r).items() if k!='powers'}|{f'P{k}':r['powers'][k] for k in range(5)})
    print(name,cases[name]['passed'],'/80; min margin',min(r['minimum_signed_margin'] for r in result.values()),flush=True)
with (OUT/'replay_400.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(csvrows[0]));w.writeheader();w.writerows(csvrows)
for filename,rows in [('path_lengths.csv',[{k:p.get(k,'') for k in ['id','kind','source_class','length_um','gds_route_component']} for p in paths['paths']]),('route_lengths.csv',[dict(component=r['component'],terminal_A=r['terminals'][0],terminal_B=r['terminals'][1],WG_length_um=r['centerline_length_um'],core_length_um=r['core_length_um'],fan_length_um=r['fan_length_um'],EC_response_unknown=r['EC_response_unknown']) for r in paths['routes']])]:
    with (OUT/filename).open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
sweep=[]
for delta in model['neff_sweep_offsets']:
    changed=copy.deepcopy(model);changed['neff']+=delta;row=dict(neff_offset=delta,neff=changed['neff'])
    for name,program in [('original',catalog),('frozen_candidate',candidate)]:
        result=a.evaluate(spec,paths,changed,program);row[name+'_passed']=sum(r['passed'] for r in result.values());row[name+'_minimum_margin']=min(r['minimum_signed_margin'] for r in result.values())
    sweep.append(row)
save(OUT/'neff_sensitivity.json',sweep)
D=np.diag(np.exp(1j*np.asarray(offset['output_phase_rad'])));gauge_error=max(float(np.max(np.abs(raw['length_compensated'][g]['U']-D@raw['ideal_baseline'][g]['U']))) for g in catalog)
power_error=max(abs(r['output_power']-r['input_power']) for name in ['ideal_baseline','length_original','length_compensated'] for r in cases[name]['rows'])
s=importlib.util.spec_from_file_location('back_tests',HERE/'test_backannotation.py');module=importlib.util.module_from_spec(s);s.loader.exec_module(module);t=module.BackannotationTests
t.spec=spec;t.paths=paths;t.model=model;t.catalog=catalog
stream=io.StringIO();tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(t));(OUT/'unit_tests.log').write_text(stream.getvalue(),encoding='utf-8')
checks=[('ideal_80',cases['ideal_baseline']['passed']==80),('modeled_phase_candidate_80',cases['length_compensated']['passed']==80),('complex_gauge_identity',gauge_error<1e-9),('lossless_energy_conservation',power_error<1e-9),('loss_is_passive',all(r['output_power']<=r['input_power']+1e-9 for name in ['loss_original','loss_compensated'] for r in cases[name]['rows'])),('400_complete_patterns',len(csvrows)==400 and len({(r['case'],r['gate'],r['pattern']) for r in csvrows})==400),('unit_tests',tests.wasSuccessful())]
source=['config/m2_backannotation.json','work/common/backannotation.py','work/m2_s7/extract_lengths.py','work/m2_s7/run_replay.py','work/m2_s7/test_backannotation.py']
record=dict(step='M2 S7',timestamp=datetime.now(timezone(timedelta(hours=8))).isoformat(),root=str(ROOT),model=model,cases=cases,complex_gauge_error=gauge_error,lossless_power_error=power_error,sensitivity=sweep,unit_tests=dict(run=tests.testsRun,passed=tests.testsRun-len(tests.failures)-len(tests.errors),successful=tests.wasSuccessful()),checks=[dict(name=n,passed=bool(v)) for n,v in checks],source_hashes={p:handoff.digest(ROOT/p) for p in source},gds_sha256=paths['gds_sha256'],model_candidate=settings,physical_function_qualified=False,core_passed=all(v for n,v in checks),scope='Core-plane uniform-neff teaching replay using bound centerline polyline lengths; model-only analytic compensation. No EC/fanout response, calibrated absolute MMI phase, bend loss/index, process or heater calibration.')
save(OUT/'replay_results.json',record)
print('Gauge error',gauge_error,'tests',record['unit_tests'],'CORE',record['core_passed'])
raise SystemExit(0 if record['core_passed'] else 1)
