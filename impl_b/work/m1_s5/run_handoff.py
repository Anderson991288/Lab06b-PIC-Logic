"""Build, independently consume and verify the M1-to-M2 logical handoff."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import os,sys,json,hashlib,io,unittest,importlib.util,subprocess,shutil,copy,zipfile
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;OUT=HERE/'out'
OUT.mkdir(exist_ok=True);FIG=ROOT/'course/figures/m1_s5';FIG.mkdir(parents=True,exist_ok=True)
for key in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:os.environ[key]='1'
DLL_HANDLE=None
if os.name=='nt' and (Path(sys.prefix)/'Library/bin').is_dir():DLL_HANDLE=os.add_dll_directory(str(Path(sys.prefix)/'Library/bin'))
sys.path[:0]=[str(ROOT/'work'),str(HERE)]
from common import handoff
from package_tools import build_package


def suite(path,cls,logname):
    spec=importlib.util.spec_from_file_location(cls,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(getattr(module,cls)))
    (OUT/logname).write_text(stream.getvalue(),encoding='utf-8')
    return dict(run=r.testsRun,passed=r.testsRun-len(r.failures)-len(r.errors),failures=len(r.failures),errors=len(r.errors),successful=r.wasSuccessful())


tests=suite(HERE/'test_handoff.py','HandoffTests','unit_tests.log')
regression={name:suite(ROOT/path,cls,name.lower()+'_regression.log') for name,path,cls in [
    ('M0_S3','work/m0_s3/test_optical_models.py','OpticalModels'),('M1_S1','work/m1_s1/test_encoding_readout.py','EncodingReadout'),
    ('M1_S2','work/m1_s2/test_b7.py','B7Tests'),('M1_S3','work/m1_s3/test_weighted_readout.py','WeightedReadoutTests'),
    ('M1_S4','work/m1_s4/test_logic_validation.py','LogicValidationTests')]}
bundle=ROOT/'delivery/m1_handoff';manifest=build_package(ROOT,bundle)
spec,phases=handoff.load_bundle(bundle);results=handoff.replay(spec,phases);csv_error=handoff.verify_truth_csv(bundle,results)
stamp=datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%d_%H%M%S_%f')
isolated=ROOT.parent/'validation'/('m1_s5_'+stamp)
assert isolated.resolve().is_relative_to(ROOT.parent.resolve()) and not isolated.exists()
shutil.copytree(bundle,isolated,ignore=shutil.ignore_patterns('__pycache__','verification'))
environment=dict(os.environ);environment.pop('PYTHONPATH',None);environment['PYTHONIOENCODING']='utf-8'


def child(folder,logname,gate='AND2',bits='1100'):
    r=subprocess.run([sys.executable,'-I',str(folder/'replay_handoff.py'),'--gate',gate,'--bits',bits],cwd=folder,
                     env=environment,text=True,encoding='utf-8',errors='replace',capture_output=True,timeout=45)
    (OUT/logname).write_text(r.stdout+'\n'+r.stderr,encoding='utf-8');return r


direct=child(bundle,'direct_replay.log')
isolated_run=child(isolated,'isolated_replay.log','XOR2','1010')
direct_report=json.loads((bundle/'verification/replay_results.json').read_text(encoding='utf-8')) if direct.returncode==0 else {}
isolated_report=json.loads((isolated/'verification/replay_results.json').read_text(encoding='utf-8')) if isolated_run.returncode==0 else {}

# Controlled copies leave canonical specs, phase programs and exported bundle untouched.
rejections=[]
for name in ['phase_digest_change','semantic_wrong_unit','csv_channel_mismatch','wrong_spec_binding']:
    target=HERE/'controlled_cases'/stamp/name
    shutil.copytree(bundle,target,ignore=shutil.ignore_patterns('__pycache__','verification'))
    if name=='phase_digest_change':
        p=target/'phase_settings.json';p.write_text(p.read_text(encoding='utf-8')+' ',encoding='utf-8')
    elif name=='semantic_wrong_unit':
        p=target/'pic_spec.json';data=json.loads(p.read_text(encoding='utf-8'));data['units']['phase']='degree';p.write_text(json.dumps(data),encoding='utf-8')
        phase_path=target/'phase_settings.json';data=json.loads(phase_path.read_text(encoding='utf-8'));data['spec_sha256']=handoff.digest(p);phase_path.write_text(json.dumps(data),encoding='utf-8')
    elif name=='csv_channel_mismatch':
        p=target/'phase_channels.csv';p.write_text(p.read_text(encoding='utf-8-sig').replace('H_M1_theta','H_M2_theta'),encoding='utf-8')
    else:
        p=target/'phase_settings.json';data=json.loads(p.read_text(encoding='utf-8'));data['spec_sha256']='0'*64;p.write_text(json.dumps(data),encoding='utf-8')
    if name!='phase_digest_change':
        p=target/'manifest.json';data=json.loads(p.read_text(encoding='utf-8'))
        for row in data['files']:row['sha256']=handoff.digest(target/row['path'])
        p.write_text(json.dumps(data),encoding='utf-8')
    try:handoff.load_bundle(target);rejected=False;reason='Not rejected'
    except (ValueError,KeyError) as error:rejected=True;reason=str(error)
    rejections.append(dict(name=name,rejected=rejected,reason=reason))
    (OUT/(name+'.log')).write_text(reason,encoding='utf-8')
zip_path=ROOT/'delivery/m1_handoff.zip'
with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED) as z:
    for name in [*[row['path'] for row in manifest['files']],'manifest.json','verification/replay_results.json']:
        z.write(bundle/name,arcname=name)
with zipfile.ZipFile(zip_path) as z:
    assert z.testzip() is None
    zip_matches=all(hashlib.sha256(z.read(row['path'])).hexdigest()==row['sha256'] for row in manifest['files'])
catalog=json.loads((ROOT/'config/m1_s4_phase_programs.json').read_text(encoding='utf-8'))
roundtrip=handoff.phase_catalog(spec,phases)
checks=[('spec_and_crossrefs_valid',True),('ten_core_ports',len(spec['optical_ports'])==10),('fourteen_named_channels',len(spec['phase_channels'])==14),
    ('six_bypass_segments',len(spec['architecture']['bypass_segments'])==6),('phase_precision_preserved',roundtrip==catalog['gates']),
    ('eighty_replayed_truths',sum(r['summary']['passed'] for r in results.values())==80),('M1S4_csv_matches',csv_error<1e-10),
    ('direct_standalone_replay',direct.returncode==0 and direct_report.get('truth_passed')==80),
    ('isolated_replay',isolated_run.returncode==0 and isolated_report.get('truth_passed')==80),
    ('isolated_uses_bundled_model',bool(isolated_report) and Path(isolated_report['loaded_model']).is_relative_to(isolated/'model')),
    ('physical_assignments_pending',all(c['pad_id'] is None and c['calibration'] is None for c in spec['phase_channels'])),
    ('all_controlled_copies_rejected',all(r['rejected'] for r in rejections)),('zip_payload_matches',zip_matches)]
sources=['pic_spec.json','phase_settings.json','work/common/handoff.py','work/common/b7.py','work/common/logic_validation.py',
         'work/m1_s5/run_handoff.py','work/m1_s5/package_tools.py','work/m1_s5/replay_handoff.py','work/m1_s5/test_handoff.py','config/m1_s4_phase_programs.json']
result=dict(step='M1 S5',timestamp=datetime.now(timezone(timedelta(hours=8))).isoformat(),root=str(ROOT),
    root_matches_plan=ROOT.resolve()==Path('C:/EDA_Codex/Lab06b').resolve(),python=sys.executable,
    unit_tests=tests,regression=regression,checks=[dict(name=name,passed=bool(ok)) for name,ok in checks],
    spec_schema=spec['schema'],phase_schema=phases['schema'],spec_sha256=handoff.digest(ROOT/'pic_spec.json'),
    package_manifest=manifest,bundle='delivery/m1_handoff',zip='delivery/m1_handoff.zip',zip_sha256=handoff.digest(zip_path),
    function_summaries={g:r['summary'] for g,r in results.items()},csv_max_error=csv_error,
    direct_replay=direct_report,isolated_replay=isolated_report,rejection_examples=rejections,
    source_hashes={rel:handoff.digest(ROOT/rel) for rel in sources},
    core_passed=tests['successful'] and all(r['successful'] for r in regression.values()) and all(ok for name,ok in checks),
    scope='M1 logical core specification, named phase mapping and portable ideal replay; M2 PDK, geometry, optical packaging, heater/PAD calibration and physical verification remain pending.')
(OUT/'handoff_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('M1 S5 tests:',tests)
print('Previous regression:',sum(r['passed'] for r in regression.values()),'/',sum(r['run'] for r in regression.values()))
print('Bundle replay:',sum(r['summary']['passed'] for r in results.values()),'/80; isolated:',isolated_report.get('truth_passed'))
print('Controlled copies rejected:',sum(r['rejected'] for r in rejections),'/4')
print('M1 S5 CORE:',result['core_passed'])
raise SystemExit(0 if result['core_passed'] else 1)
