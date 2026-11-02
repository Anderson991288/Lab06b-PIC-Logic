"""Preserve S3; build a margin-improved candidate; run independent KLayout."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import os,sys,json,shutil,subprocess,io,unittest,importlib.util
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;OUT=HERE/'out'
for folder in [OUT/'before',OUT/'after']:folder.mkdir(parents=True,exist_ok=True)
os.environ['MPLCONFIGDIR']=str(HERE/'work/matplotlib')
for key in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:os.environ[key]='1'
sys.path.insert(0,str(ROOT/'work'))
from common import core_layout as geo,handoff
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
source=ROOT/'work/m2_s3/out';prior=load(source/'layout_results.json')
assert prior['core_passed']
for name,digest in prior['gds_files'].items():assert handoff.digest(source/name)==digest
before_hashes={name:handoff.digest(source/name) for name in ['b7_core.gds','mzi_core.gds','layout_info.json']}
for name in before_hashes:shutil.copy2(source/name,OUT/'before'/name)
spec,phases=handoff.load_bundle(ROOT/'delivery/m1_handoff');top=handoff.validate_spec(spec)
c=load(ROOT/'config/m2_review_layout.json');geo.validate(c,handoff.digest(ROOT/'pic_spec.json'))
core,preview,info=geo.build(top,c)
for cell,name in [(core,'b7_core.gds'),(preview,'mzi_core.gds')]:cell.get_default_view(geo.i3.LayoutView).write_gdsii(str(OUT/'after'/name))
save(OUT/'after/layout_info.json',info)
cfg=load(ROOT/'EDA_paths.json');exe=Path(cfg['windows']['klayout_exe'])
if not exe.is_absolute():exe=ROOT/exe
def klayout(script,args,log,timeout=180):
    cmd=[str(exe),'-b','-r',str(script)]
    for k,v in args.items():cmd.extend(['-rd',str(k)+'='+str(v)])
    r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
    log.write_text(r.stdout+'\n'+r.stderr,encoding='utf-8')
    if r.returncode:raise RuntimeError(script.name+' failed: '+r.stderr[-1200:])
    print(r.stdout.strip(),flush=True)
for version in ['before','after']:
    folder=OUT/version
    klayout(ROOT/'work/m2_s3/verify_gds.py',dict(input_gds=folder/'b7_core.gds',info_json=folder/'layout_info.json',output_json=folder/'gds_readback.json'),folder/'gds_readback.log')
    assert load(folder/'gds_readback.json')['passed']
    klayout(HERE/'klayout_review.py',dict(folder_path=folder,version_name=version,make_faults=int(version=='after'),
        fault_folder=HERE/'work/controlled_gds',render_images=1,image_folder=ROOT/'course/figures/m2_s4'),folder/'review_geometry.log')

def suite(path,cls,prepare=None):
    s=importlib.util.spec_from_file_location(cls,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);t=getattr(m,cls)
    if prepare:prepare(t)
    stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(t))
    (OUT/(cls+'_regression.log')).write_text(stream.getvalue(),encoding='utf-8')
    return dict(run=r.testsRun,passed=r.testsRun-len(r.failures)-len(r.errors),successful=r.wasSuccessful())
def setup(t):t.config=c;t.info=info;t.spec_sha=handoff.digest(ROOT/'pic_spec.json')
regression={name:suite(ROOT/path,cls,setup if name=='M2_S3' else None) for name,path,cls in [
    ('M0_S3','work/m0_s3/test_optical_models.py','OpticalModels'),('M1_S1','work/m1_s1/test_encoding_readout.py','EncodingReadout'),
    ('M1_S2','work/m1_s2/test_b7.py','B7Tests'),('M1_S3','work/m1_s3/test_weighted_readout.py','WeightedReadoutTests'),
    ('M1_S4','work/m1_s4/test_logic_validation.py','LogicValidationTests'),('M1_S5','work/m1_s5/test_handoff.py','HandoffTests'),
    ('M2_S1','work/m2_s1/test_boundary.py','BoundaryTests'),('M2_S2','work/m2_s2/test_pdk_circuit.py','PdkCircuitTests'),
    ('M2_S3','work/m2_s3/test_core_layout.py','CoreLayoutTests')]}
old=load(ROOT/'work/m1_s5/out/handoff_results.json');unchanged=all(handoff.digest(ROOT/p)==h for p,h in old['source_hashes'].items()) and handoff.digest(ROOT/old['zip'])==old['zip_sha256']
baseline=handoff.replay(spec,phases);count=sum(r['summary']['passed'] for r in baseline.values())
source_paths=['config/m2_review_layout.json','work/common/core_layout.py','work/m2_s4/run_review.py','work/m2_s4/klayout_review.py','work/m2_s3/verify_gds.py']
save(OUT/'build_review.json',dict(step='M2 S4',timestamp=datetime.now(timezone(timedelta(hours=8))).isoformat(),root=str(ROOT),regression=regression,
    M1_sources_and_zip_unchanged=unchanged,M1_baseline_replay_passed=count,S3_baseline_hashes=before_hashes,
    S3_baseline_unchanged=all(handoff.digest(source/name)==h for name,h in before_hashes.items()),
    source_hashes={p:handoff.digest(ROOT/p) for p in source_paths}))
assert all(r['successful'] for r in regression.values()) and unchanged and count==80
print('Regression',sum(r['passed'] for r in regression.values()),'; M1 baseline replay',count,'; S3 preserved',flush=True)
