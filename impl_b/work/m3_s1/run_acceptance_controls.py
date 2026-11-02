"""Timestamp, geometry, stale-directory and missing-source acceptance controls."""
from pathlib import Path
import json,sys,struct,subprocess,io,unittest,importlib.util,uuid,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'out';WORK=HERE/'work'
sys.path.insert(0,str(HERE))
from rebuild_support import sha,normalized_digest,reserve_empty_target
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
r=load(OUT/'rebuild_results.json');assert r['status']=='passed';controls=[]
control=WORK/('controls_'+uuid.uuid4().hex);control.mkdir(parents=True)
source=OUT/'build_A/b7_rebuilt.gds';changed=control/'dates_only.gds';data=bytearray(source.read_bytes());i=0
while i<len(data):
    n,k=struct.unpack_from('>HH',data,i)
    if k in [0x0102,0x0502]:data[i+4:i+28]=struct.pack('>12h',*(2050,1,1,0,0,0)*2)
    i+=n
changed.write_bytes(data);controls.append(dict(id='timestamp_only',raw_sha_different=sha(changed)!=sha(source),normalized_sha_equal=normalized_digest(changed)['sha256']==normalized_digest(source)['sha256'],passed=sha(changed)!=sha(source) and normalized_digest(changed)['sha256']==normalized_digest(source)['sha256']))
tools=load(ROOT/'EDA_paths.json')['windows'];exe=Path(tools['klayout_exe']);exe=exe if exe.is_absolute() else ROOT/exe
def klayout(script,args,name):
    cmd=[str(exe),'-b','-r',str(script)]
    for k,v in args.items():cmd+=['-rd',k+'='+str(v)]
    result=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180);(OUT/(name+'.log')).write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
    if result.returncode:raise RuntimeError(name+' execution failed')
fault=control/'Si_added.gds';comparison=OUT/'geometry_fault_comparison.json'
klayout(HERE/'make_geometry_fault.py',dict(input_gds=source,output_gds=fault),'make_geometry_fault')
klayout(HERE/'compare_gds.py',dict(reference_gds=source,rebuilt_gds=fault,output_json=comparison),'geometry_fault_compare')
comp=load(comparison);controls.append(dict(id='actual_Si_geometry_change',XOR_polygons=sum(x['XOR_polygons'] for x in comp['layers']),normalized_sha_different=normalized_digest(source)['sha256']!=normalized_digest(fault)['sha256'],passed=not comp['passed'] and any(x['XOR_polygons'] for x in comp['layers']) and normalized_digest(source)['sha256']!=normalized_digest(fault)['sha256']))
stale=False
try:reserve_empty_target(Path(r['builds'][0]['target']),WORK)
except ValueError as error:stale=True;reason=str(error)
controls.append(dict(id='reuse_nonempty_target',rejected=stale,reason=reason,passed=stale))
# Check recorded seed files after all generation; no source output may replace them.
seed_checks=[]
for build in r['builds']:
    target=Path(build['target']);seed=load(target/'seed_manifest.json');ok=all((target/x['path']).is_file() and sha(target/x['path'])==x['sha256'] for x in seed['files']);seed_checks.append(dict(build=build['build'],files=len(seed['files']),unchanged=ok));assert ok
missing=control/'missing_source';missing.mkdir();manifest=dict(files=[dict(path='pic_spec.json',sha256=r['source_hashes']['pic_spec.json'])]);save(missing/'seed_manifest.json',manifest)
missing_detected=not all((missing/x['path']).is_file() and sha(missing/x['path'])==x['sha256'] for x in manifest['files'])
controls.append(dict(id='missing_source_inventory',rejected=missing_detected,passed=missing_detected,scope='Seed inventory audit; no licensed build launched'))
s=importlib.util.spec_from_file_location('support_tests',HERE/'test_rebuild_support.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);stream=io.StringIO();t=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(m.RebuildSupportTests));(OUT/'support_tests.log').write_text(stream.getvalue(),encoding='utf-8')
record=dict(status='passed' if all(x['passed'] for x in controls) and t.wasSuccessful() else 'failed',controls=controls,seed_files_after_build=seed_checks,tests=dict(run=t.testsRun,passed=t.testsRun-len(t.failures)-len(t.errors),successful=t.wasSuccessful()),source_hashes={p.relative_to(ROOT).as_posix():sha(p) for p in [HERE/'rebuild_support.py',HERE/'test_rebuild_support.py',HERE/'run_acceptance_controls.py',HERE/'make_geometry_fault.py']})
save(OUT/'acceptance_controls.json',record);assert record['status']=='passed';print('Acceptance controls 4/4; support tests',t.testsRun,'passed')
