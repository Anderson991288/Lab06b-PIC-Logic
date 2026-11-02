"""Replay using the NEWLY built sidecars and extracted GDS path assignments."""
from pathlib import Path
import os,sys,json,csv,unittest,importlib.util,io
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;OUT=HERE/'out'
HANDLE=os.add_dll_directory(str(Path(sys.prefix)/'Library/bin')) if os.name=='nt' else None
sys.path.insert(0,str(ROOT/'work'))
import numpy as np
from common import handoff,backannotation as a
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
spec,phases=handoff.load_bundle(ROOT/'delivery/m1_handoff');catalog=handoff.phase_catalog(spec,phases);paths=load(ROOT/'work/m2_s7/out/paths.json');model=load(ROOT/'config/m2_backannotation.json');a.validate_model(model)
offset=a.compensation(spec,paths,model);candidate=a.candidate(catalog,offset);cases={};rows=[];matrices={}
for name,setting,loss,prop in [('ideal_baseline',catalog,0.,False),('length_original',catalog,0.,True),('length_compensated',candidate,0.,True),('loss_original',catalog,model['illustrative_loss_db_per_cm'],True),('loss_compensated',candidate,model['illustrative_loss_db_per_cm'],True)]:
    result=a.evaluate(spec,paths,model,setting,loss,prop);rr=[row for v in result.values() for row in v['rows']]
    cases[name]=dict(passed=sum(v['passed'] for v in result.values()),total=80,minimum_signed_margin=min(x['signed_margin'] for x in rr),rows=rr)
    matrices[name]={g:np.stack([v['U'].real,v['U'].imag],axis=-1).tolist() for g,v in result.items()}
    for r in rr:rows.append({k:v for k,v in dict(case=name,**r).items() if k!='powers'}|{f'P{k}':r['powers'][k] for k in range(5)})
with (OUT/'replay_400.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
programs={g:[s['theta'][int(c[5:])-1] if c.startswith('theta') else s['phi'][int(c[3:])-1] for c in spec['phase_vector_order']] for g,s in candidate.items()}
save(OUT/'candidate_programs.json',dict(programs=programs,phase_unit='rad',voltage_calibration=None,physical_function_qualified=False))
s=importlib.util.spec_from_file_location('fresh_model_tests',ROOT/'work/m2_s7/test_backannotation.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);t=m.BackannotationTests;t.spec=spec;t.paths=paths;t.model=model;t.catalog=catalog
stream=io.StringIO();tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(t));(OUT/'model_tests.log').write_text(stream.getvalue(),encoding='utf-8')
save(OUT/'replay.json',dict(cases=cases,matrices=matrices,model_tests=dict(run=tests.testsRun,passed=tests.testsRun-len(tests.failures)-len(tests.errors),successful=tests.wasSuccessful()),gds_sha256=paths['gds_sha256'],physical_function_qualified=False,model_source='Declared M2 S7 model input; no FEM re-solve or new calibration in M3 S1'))
assert tests.wasSuccessful() and [c['passed'] for c in cases.values()]==[80,53,80,53,80]
print('Fresh geometry replay:',{k:v['passed'] for k,v in cases.items()},flush=True)
