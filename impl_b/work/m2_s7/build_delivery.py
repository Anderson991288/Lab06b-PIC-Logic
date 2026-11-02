from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,hashlib,shutil,zipfile,subprocess,os,sys
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;OUT=HERE/'out';WORK=HERE/'work'
DELIVERY=ROOT/'delivery/m2_pic_delivery';DELIVERY.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
replay=load(OUT/'replay_results.json');reg=load(OUT/'regression.json');current=load(ROOT/'config/m2_current_chip.json')
assert replay['core_passed'] and current['accepted_at_step']=='M2 S6' and sum(r['passed'] for r in reg['regression'].values())==144
for p,h in current['files'].items():assert sha(ROOT/p)==h
managed=[]
def put(src,rel):
    dst=DELIVERY/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);managed.append(rel)
def write(rel,text):
    p=DELIVERY/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8');managed.append(rel)
gds=next(ROOT/p for p in current['files'] if p.endswith('.gds'));chip=next(ROOT/p for p in current['files'] if p.endswith('chip_info.json'))
put(gds,'layout/B7_final.gds');put(chip,'data/chip_info.json')
for name in ['pad_heater_map.csv','optical_io.csv','ground_pads.csv']:
    put(next(ROOT/p for p in current['files'] if p.endswith(name)),'interfaces/'+name)
for src,rel in [(ROOT/'pic_spec.json','data/pic_spec.json'),(ROOT/'phase_settings.json','data/phase_settings.json'),(ROOT/'config/m2_backannotation.json','data/model.json'),
    (ROOT/'work/m2_s4/out/after/layout_info.json','data/core_geometry.json'),(OUT/'paths.json','data/paths.json'),(OUT/'phase_settings_backannotated.json','data/phase_settings_backannotated.json'),
    (OUT/'replay_results.json','reports/replay_results.json'),(OUT/'replay_400.csv','reports/replay_400.csv'),(OUT/'path_lengths.csv','interfaces/path_lengths.csv'),(OUT/'route_lengths.csv','interfaces/route_lengths.csv'),
    (OUT/'neff_sensitivity.json','reports/neff_sensitivity.json'),(ROOT/'work/m2_s6/out/verification_results.json','reports/verification_S6.json'),
    (ROOT/'work/m2_s6/out/after/pre_drc.lyrdb','reports/pre_drc.lyrdb'),(ROOT/'work/m2_s6/out/after/connectivity.json','reports/connectivity_S6.json'),
    (ROOT/'work/m2_s6/out/fix_log.csv','reports/fix_log.csv'),(OUT/'unit_tests.log','reports/backannotation_tests.log'),(OUT/'regression.json','reports/regression.json')]:put(src,rel)
for name in ['verify_delivery.py','replay_delivery.py','recheck_geometry.py','geometry_engine.py']:put(HERE/name,name)
for name in ['__init__','mzi','b7','linear_network','encoding','logic_validation','handoff','backannotation']:put(ROOT/'work/common'/(name+'.py'),'models/common/'+name+'.py')
put(ROOT/'work/m2_s6/connectivity.py','geometry/connectivity.py');put(ROOT/'work/m2_s5/electrical_geometry.py','geometry/electrical_geometry.py')
for rel in ['work/common/core_layout.py','work/common/chip_interfaces.py','work/m2_s3/build_core.py','work/m2_s5/build_chip.py','work/m2_s5/merge_verify.py','work/m2_s6/prepare_gds.py','work/m2_s7/extract_lengths.py','work/m2_s7/run_replay.py','config/m2_review_layout.json','config/m2_chip_interfaces.json','config/m2_verification.json']:
    put(ROOT/rel,'source/project/'+rel)
fem=load(ROOT/'work/m0_s2/out/physics_results.json');write('data/FEM_reference.json',json.dumps(dict(source='M0 S2 uniform-oxide fine-mesh FEM',original_sha256=sha(ROOT/'work/m0_s2/out/physics_results.json'),parameters=fem['parameters'],fine=next(r for r in fem['fem']['convergence'] if r['label']=='fine'),physical_chip_calibration=False),ensure_ascii=False,indent=2)+'\n')
write('requirements.txt','numpy==1.26.4\n')
write('README.md','''# Lab06b M2 PIC teaching delivery

This is a review/replay package, not a fabrication release or calibrated chip.
The GDS is byte-identical to the accepted S6 revision. Original M1 specification
and phases are preserved. SHA-256 checks detect changes; they are not a digital
signature or proof of provenance from a trusted signer.

## Portable commands

Tested with Python 3.12.13 / NumPy 1.26.4, Windows native runtime:

    python verify_delivery.py
    python replay_delivery.py --out ../replay_output

The first command uses only the Python standard library. The second recomputes
five scenarios / 400 truth cases and compares all deltas with the archived data.
Windows conda DLL setup is handled inside the replay script, without editing
the user's environment configuration. No project drive paths are required.

Optional geometric/pre-DRC recheck requires external KLayout 0.30.12 and the
recorded original CORNERSTONE v3.1 pre-DRC deck, supplied separately:

    python recheck_geometry.py --klayout <klayout_app.exe> --deck <original.lydrc> --out ../geometry_output

The proprietary vendor deck, installed PDK, EDA binaries and licenses are not
redistributed. The external deck SHA is pinned in manifest.json. Area is checked
against this course's declared 3860 x 1640 um region, not foundry MPW allocation.
Source/project archives selected authored layout scripts and parameters; full
course/EDA rebuild uses the original C project and licensed installed tools.

## Reference plane and models

All numerical truth replay is at the M1 core ports (including the core leads).
68 centerline polylines (58 core, 10 fanout) are mapped to the actual GDS's 33
outside-MMI connections. Lengths are nominal grid-snapped polyline lengths,
not calibrated optical PEX. MMI body spans and EC tapers are not assigned the
single-mode propagation index.

Propagation is exp(+i 2 pi neff L/lambda), lambda=1.55 um, neff=2.353499831254645
from M0's uniform-oxide FEM example. Installed ideal H matrices are retained;
no calibrated absolute MMI phase is available. The 3 dB/cm loss scenario and
neff perturbations are teaching assumptions, not measured foundry data.

Original ideal phases pass 80/80 in the ideal baseline, then 53/80 after length
phase is included. Analytic per-rail phase tracking gives a separate model-only
candidate passing 80/80 in that model; it is not fitted to Boolean truth labels.
The residual output diagonal phases preserve powers. No heater voltage, Vpi,
EC loss/phase or physical-chip performance is inferred from this calculation.

## Contents

- layout: accepted GDS, top LAB06B_B7_EC_PAD_CHIP; 10 reference ECs,
  14 signal PADs, 2 GND PADs (one shared return).
- interfaces/data: optical/PAD/GND tables, geometry, paths and named phases.
- reports: unchanged pre-DRC zero-marker result, geometric connectivity,
  model replay, tests and sensitivity evidence.
- models/geometry: authored portable numerical and geometric checkers.
- source/project: selected layout sources, with external dependencies noted.

## Qualification still pending

Foundry full signoff/process LVS; qualified EC and fiber/packaging response;
absolute MMI phase/bend-specific model; thermal/common-ground/bias calibration;
and physical measured 80-case acceptance remain open. The course model's
80/80 is not experimental acceptance. Use phase_settings_backannotated.json
only as a model candidate; retain data/phase_settings.json as the M1 original.
''')
manifest=dict(schema='lab06b.pic_delivery.v1',created_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),kind='teaching_review_package',gds_sha256=sha(gds),
    physical_function_qualified=False,foundry_full_signoff=False,external_deck_sha256=sha(ROOT/'work/common/drc/cornerstone_Si220_passive.lydrc'),
    files=[dict(path=p,bytes=(DELIVERY/p).stat().st_size,sha256=sha(DELIVERY/p)) for p in sorted(managed)])
save(DELIVERY/'manifest.json',manifest)
relocated=WORK/'relocated package 測試';relocated.mkdir(parents=True,exist_ok=True)
for name in managed+['manifest.json']:
    dst=relocated/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(DELIVERY/name,dst)
env=dict(os.environ);env['PYTHONIOENCODING']='utf-8'
for k in ['CONDA_PREFIX','CONDA_DLL_SEARCH_MODIFICATION_ENABLE']:env.pop(k,None)
prefix=str(Path(sys.executable).parent).casefold();env['PATH']=os.pathsep.join(p for p in env.get('PATH','').split(os.pathsep) if not p.casefold().startswith(prefix))
def command(args,log):
    r=subprocess.run(args,cwd=relocated,capture_output=True,text=True,encoding='utf-8',errors='replace',env=env,timeout=180)
    (OUT/log).write_text(r.stdout+'\n'+r.stderr,encoding='utf-8')
    if r.returncode:raise RuntimeError(log+' failed: '+r.stderr[-1600:])
    return r.stdout
command([sys.executable,str(relocated/'verify_delivery.py')],'portable_integrity.log')
command([sys.executable,str(relocated/'replay_delivery.py'),'--out',str(WORK/'portable_replay')],'portable_replay.log')
tools=load(ROOT/'EDA_paths.json');exe=ROOT/tools['windows']['klayout_exe'];deck=ROOT/tools['windows']['drc_deck']
command([sys.executable,str(relocated/'recheck_geometry.py'),'--klayout',str(exe),'--deck',str(deck),'--out',str(WORK/'portable_geometry')],'portable_geometry.log')
rejections=[]
for case in ['changed_GDS','rehashed_wrong_model','rehashed_missing_truth','unsafe_manifest_path']:
    target=WORK/'controlled'/case;target.mkdir(parents=True,exist_ok=True)
    for name in managed+['manifest.json']:
        dst=target/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(DELIVERY/name,dst)
    tampered=load(target/'manifest.json')
    if case=='changed_GDS':
        with (target/'layout/B7_final.gds').open('ab') as f:f.write(b'FAULT')
    elif case=='rehashed_wrong_model':
        path=target/'data/model.json';data=load(path);data['neff']+=.01;save(path,data)
        next(r for r in tampered['files'] if r['path']=='data/model.json')['sha256']=sha(path)
    elif case=='rehashed_missing_truth':
        path=target/'reports/replay_400.csv';lines=path.read_text(encoding='utf-8-sig').splitlines();path.write_text('\n'.join(lines[:-1])+'\n',encoding='utf-8')
        next(r for r in tampered['files'] if r['path']=='reports/replay_400.csv')['sha256']=sha(path)
    else:tampered['files'][0]['path']='../escape.json'
    save(target/'manifest.json',tampered)
    r=subprocess.run([sys.executable,str(target/'verify_delivery.py')],cwd=target,capture_output=True,text=True,encoding='utf-8',errors='replace',env=env,timeout=30)
    reason=(r.stderr.strip().splitlines() or ['no error'])[-1];rejections.append(dict(case=case,rejected=r.returncode!=0,reason=reason))
assert all(r['rejected'] for r in rejections)
zip_path=ROOT/'delivery/Lab06b_M2_PIC_delivery.zip'
with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED) as z:
    for name in sorted(managed+['manifest.json']):z.write(DELIVERY/name,'m2_pic_delivery/'+name)
with zipfile.ZipFile(zip_path) as z:assert z.testzip() is None
result=dict(status='passed',delivery=str(DELIVERY.relative_to(ROOT)),zip=str(zip_path.relative_to(ROOT)),zip_sha256=sha(zip_path),files=len(managed),
    gds_sha256=sha(gds),manifest_sha256=sha(DELIVERY/'manifest.json'),portable_replay=load(WORK/'portable_replay/portable_replay.json'),portable_geometry=load(WORK/'portable_geometry/portable_geometry.json'),
    relocated_path=str(relocated),tamper_controls=rejections,source_hashes={p:sha(ROOT/p) for p in ['work/m2_s7/build_delivery.py','work/m2_s7/verify_delivery.py','work/m2_s7/replay_delivery.py','work/m2_s7/recheck_geometry.py','work/m2_s7/geometry_engine.py']},physical_function_qualified=False)
save(OUT/'delivery_results.json',result)
print('Delivery:',len(managed),'files; fresh replay and geometric recheck passed; tamper controls',sum(r['rejected'] for r in rejections),'/4')
