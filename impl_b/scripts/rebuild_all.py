"""Rebuild accepted PIC twice from staged source/design inputs, never old outputs.

Installed licensed toolchain is external; this is not an OS/tool installation.
Run scripts/run_m3_s1.ps1. All mutation remains under C:/EDA_Codex/Lab06b.
"""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import os,sys,json,csv,shutil,subprocess,time,hashlib,struct,traceback
ROOT=Path(__file__).resolve().parents[1];HERE=ROOT/'work/m3_s1';OUT=HERE/'out';WORK=HERE/'work'
sys.path.insert(0,str(HERE))
from rebuild_support import sha,normalized_digest,reserve_empty_target,safe_source_path
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def csvrows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def env_for(python,target):
    prefix=Path(python).parent;env=os.environ.copy();env['PATH']=str(prefix/'Library/bin')+';'+str(prefix/'Scripts')+';'+str(prefix)+';'+env.get('PATH','')
    env['CONDA_PREFIX']=str(prefix);env['CONDA_DLL_SEARCH_MODIFICATION_ENABLE']='1';env['PYTHONPATH']='';env['PYTHONNOUSERSITE']='1';env['PYTHONDONTWRITEBYTECODE']='1';env['MPLCONFIGDIR']=str(target/'work/m3_s1/work/.matplotlib')
    for key in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:env[key]='1'
    return env
SOURCE_FILES=['pic_spec.json','phase_settings.json',*['config/'+n+'.json' for n in ['m2_boundary','m2_review_layout','m2_chip_interfaces','m2_verification','m2_backannotation']],
    *['work/common/'+n+'.py' for n in ['__init__','mzi','b7','linear_network','encoding','logic_validation','handoff','pdk','core_layout','chip_interfaces','backannotation']],
    'work/m1_s5/replay_handoff.py','work/m2_s3/verify_gds.py',*['work/m2_s5/'+n+'.py' for n in ['build_chip','merge_verify','electrical_geometry']],
    *['work/m2_s6/'+n+'.py' for n in ['run_verification','prepare_gds','connectivity','check_connectivity']],
    'work/m2_s7/extract_lengths.py','work/m2_s7/test_backannotation.py',*['work/m3_s1/'+n+'.py' for n in ['build_core','replay_rebuilt','compare_gds']]]
def main():
    assert ROOT.resolve()==Path('C:/EDA_Codex/Lab06b').resolve()
    paths=load(ROOT/'EDA_paths.json');tools=paths['windows'];ipkiss=Path(tools['ipkiss_python']);physics=Path(tools['physics_python']);exe=Path(tools['klayout_exe']);exe=exe if exe.is_absolute() else ROOT/exe
    deck=ROOT/tools['drc_deck'];assert sha(deck)==load(ROOT/'config/m2_verification.json')['deck_sha256']
    for tool in [ipkiss,physics,exe,deck]:assert tool.is_file(),str(tool)
    for rel in SOURCE_FILES:safe_source_path(rel)
    source_hashes={p:sha(ROOT/p) for p in SOURCE_FILES};external=dict(klayout=str(exe),klayout_sha256=sha(exe),deck=str(deck),deck_sha256=sha(deck),ipkiss_python=str(ipkiss),physics_python=str(physics))
    current=load(ROOT/'config/m2_current_chip.json');assert current['accepted_at_step']=='M2 S6'
    for rel,h in current['files'].items():assert sha(ROOT/rel)==h
    reference_gds=next(ROOT/p for p in current['files'] if p.endswith('.gds'));reference_csv=ROOT/'work/m2_s7/out/replay_400.csv';reference_paths=load(ROOT/'work/m2_s7/out/paths.json');reference_candidate=load(ROOT/'work/m2_s7/out/phase_settings_backannotated.json')
    reference_hashes={p:sha(ROOT/p) for p in ['config/m2_current_chip.json','config/m2_current_core.json','config/m2_delivery.json','work/m2_s6/out/after/b7_ec_pad.gds','work/m2_s7/out/replay_400.csv','work/m2_s7/out/paths.json','work/m2_s7/out/phase_settings_backannotated.json','delivery/Lab06b_M2_PIC_delivery.zip','delivery/m1_handoff.zip']}
    stamp=datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%d_%H%M%S_%f');runroot=WORK/'clean build 測試'/stamp;builds=[];all_commands=[]
    for label in ['A','B']:
        target=reserve_empty_target(runroot/label,WORK);seed=[]
        for rel in SOURCE_FILES:
            dest=target/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,dest);assert sha(dest)==source_hashes[rel];seed.append(dict(path=rel,sha256=sha(dest)))
        configured=json.loads(json.dumps(paths));configured['root']=str(target);configured['windows']['klayout_exe']=str(exe);configured['windows']['drc_deck']=str(deck);save(target/'EDA_paths.json',configured)
        v=load(target/'config/m2_verification.json');v['deck']=str(deck);save(target/'config/m2_verification.json',v)
        # Tool-location adaptation is explicit; no design parameter or rule change.
        for row in seed:row['sha256']=sha(target/row['path'])
        seed.append(dict(path='EDA_paths.json',sha256=sha(target/'EDA_paths.json')))
        assert not list(target.rglob('*.gds')) and not list(target.rglob('out')) and not list(target.rglob('*.zip'))
        save(target/'seed_manifest.json',dict(kind='authored_sources_and_design_inputs_only',files=seed,generated_outputs_seeded=0,adaptation='External tool and unchanged-deck locations only; design inputs unchanged'))
        for rel in ['work/m3_s1/out','work/m2_s5/out','work/m2_s6/out/before','work/m2_s6/out/after','work/m2_s7/out']:(target/rel).mkdir(parents=True,exist_ok=True)
        def command(name,args,python=None,timeout=300):
            start=time.monotonic();result=subprocess.run([str(a) for a in args],cwd=target,capture_output=True,text=True,encoding='utf-8',errors='replace',env=env_for(python or physics,target),timeout=timeout)
            log=OUT/('build_'+label)/(name+'.log');log.parent.mkdir(parents=True,exist_ok=True);log.write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
            row=dict(build=label,stage=name,seconds=round(time.monotonic()-start,3),returncode=result.returncode,command=[str(a) for a in args],log=log.relative_to(ROOT).as_posix());all_commands.append(row);save(OUT/'commands.json',all_commands)
            if result.returncode:raise RuntimeError(label+' '+name+' failed: '+result.stderr[-1400:]+'; log '+str(log))
            print(label,name,'passed',row['seconds'],'s',flush=True)
        command('01_core',[ipkiss,'work/m3_s1/build_core.py'],ipkiss)
        core=target/'work/m2_s4/out/after'
        command('02_core_readback',[exe,'-b','-r',target/'work/m2_s3/verify_gds.py','-rd','input_gds='+str(core/'b7_core.gds'),'-rd','info_json='+str(core/'layout_info.json'),'-rd','output_json='+str(core/'gds_readback.json')])
        command('03_interfaces',[ipkiss,'work/m2_s5/build_chip.py'],ipkiss)
        files=['work/m2_s5/out/'+n for n in ['b7_ec_pad.gds','chip_info.json','pad_heater_map.csv','optical_io.csv','ground_pads.csv']]
        pointer=dict(schema='lab06b.current_chip.v1',accepted_at_step='M2 S5',m1_spec_sha256=sha(target/'pic_spec.json'),files={p:sha(target/p) for p in files});save(target/'config/m2_current_chip.json',pointer)
        command('04_pre_DRC_and_graph',[physics,'work/m2_s6/run_verification.py'])
        pointer['accepted_at_step']='M2 S6';pointer['files'].pop('work/m2_s5/out/b7_ec_pad.gds');pointer['files']['work/m2_s6/out/after/b7_ec_pad.gds']=sha(target/'work/m2_s6/out/after/b7_ec_pad.gds');save(target/'config/m2_current_chip.json',pointer)
        command('05_lengths',[exe,'-b','-r',target/'work/m2_s7/extract_lengths.py'])
        command('06_replay',[physics,'work/m3_s1/replay_rebuilt.py'])
        gds=target/'work/m2_s6/out/after/b7_ec_pad.gds';report=OUT/('build_'+label)/'gds_comparison.json'
        command('07_reference_XOR',[exe,'-b','-r',target/'work/m3_s1/compare_gds.py','-rd','reference_gds='+str(reference_gds),'-rd','rebuilt_gds='+str(gds),'-rd','output_json='+str(report)])
        geometry=load(report);before=load(target/'work/m2_s6/out/before/drc_result.json');after=load(target/'work/m2_s6/out/after/drc_result.json');graph=load(target/'work/m2_s6/out/after/connectivity.json');replay=load(target/'work/m3_s1/out/replay.json');paths_new=load(target/'work/m2_s7/out/paths.json');core_new=load(core/'layout_info.json')
        raw_sha=sha(gds);normalized=normalized_digest(gds);ref_normalized=normalized_digest(reference_gds)
        tables=[dict(file=Path(p).name,sha256=sha(target/p),identical=sha(target/p)==sha(ROOT/next(q for q in current['files'] if q.endswith(Path(p).name)))) for p in files if p.endswith('.csv')]
        fresh_rows=csvrows(target/'work/m3_s1/out/replay_400.csv');old_rows=csvrows(reference_csv);assert len(fresh_rows)==len(old_rows)==400
        max_error=0.;discrete=True
        for a,b in zip(fresh_rows,old_rows):
            discrete &= all(a[k]==b[k] for k in ['case','gate','pattern','expected','bit','passed','index_lsb_x1'])
            max_error=max(max_error,max(abs(float(a[k])-float(b[k])) for k in ['delta','signed_margin','input_power','output_power','P0','P1','P2','P3','P4']))
        fresh_candidate=load(target/'work/m3_s1/out/candidate_programs.json');candidate_error=max(abs(x-y) for g,v in fresh_candidate['programs'].items() for x,y in zip(v,reference_candidate['programs'][g]))
        checks=[('zero_generated_seed',True),('independent_staged_common',Path(load(target/'work/m3_s1/out/runtime.json')['common_module']).is_relative_to(target)),
            ('core_readback',load(core/'gds_readback.json')['passed']),('core_geometry_sidecar_exact',core_new==load(ROOT/'work/m2_s4/out/after/layout_info.json')),
            ('all_layer_XOR_and_text',geometry['passed']),('timestamp_only_normalized_sha_exact',normalized['sha256']==ref_normalized['sha256']),('three_interface_csv_exact',all(x['identical'] for x in tables)),
            ('original_pre_DRC_2_to_0',before['total_records']==2 and after['total_records']==0 and after['category_count']==31),('geometric_netlist',graph['passed'] and graph['electrical']['metal_nets']==15 and graph['optical']['route_components']==33),
            ('68_paths_and_33_assignments_exact',paths_new['paths']==reference_paths['paths'] and paths_new['routes']==reference_paths['routes']),('400_case_comparison',discrete and max_error<1e-9),('candidate_radians_exact',candidate_error<1e-10),('12_model_tests',replay['model_tests']['run']==replay['model_tests']['passed']==12)]
        row=dict(build=label,target=str(target),raw_sha256=raw_sha,raw_sha_identical=raw_sha==sha(reference_gds),normalized=normalized,reference_normalized=ref_normalized,geometry=geometry,tables=tables,
            pre_DRC_before=before['total_records'],pre_DRC_after=after['total_records'],pre_DRC_categories=after['category_count'],metal_nets=graph['electrical']['metal_nets'],optical_connections=graph['optical']['route_components'],
            replay_counts={k:v['passed'] for k,v in replay['cases'].items()},max_abs_numeric_error=max_error,candidate_max_abs_rad_error=candidate_error,model_tests=replay['model_tests'],checks=[dict(name=k,passed=bool(v)) for k,v in checks],passed=all(v for k,v in checks),seconds=sum(c['seconds'] for c in all_commands if c['build']==label),runtime=load(target/'work/m3_s1/out/runtime.json'))
        builds.append(row);save(OUT/'build_progress.json',builds)
        # Retain new outputs as reviewable evidence; these are NEVER build inputs.
        copies={'b7_rebuilt.gds':gds,'b7_core.gds':core/'b7_core.gds','layout_info.json':core/'layout_info.json','chip_info.json':target/'work/m2_s5/out/chip_info.json','paths.json':target/'work/m2_s7/out/paths.json','pre_drc.lyrdb':target/'work/m2_s6/out/after/pre_drc.lyrdb','connectivity.json':target/'work/m2_s6/out/after/connectivity.json','replay.json':target/'work/m3_s1/out/replay.json','replay_400.csv':target/'work/m3_s1/out/replay_400.csv','candidate_programs.json':target/'work/m3_s1/out/candidate_programs.json','model_tests.log':target/'work/m3_s1/out/model_tests.log','seed_manifest.json':target/'seed_manifest.json','runtime.json':target/'work/m3_s1/out/runtime.json',**{Path(p).name:target/p for p in files if p.endswith('.csv')}}
        for name,src in copies.items():shutil.copy2(src,OUT/('build_'+label)/name)
        if not row['passed']:raise RuntimeError('Rebuild '+label+' acceptance failed: '+str([x['name'] for x in row['checks'] if not x['passed']]))
    assert builds[0]['normalized']['sha256']==builds[1]['normalized']['sha256']
    assert all(sha(ROOT/p)==h for p,h in source_hashes.items()) and all(sha(ROOT/p)==h for p,h in reference_hashes.items())
    result=dict(step='M3 S1',timestamp=datetime.now(timezone(timedelta(hours=8))).isoformat(),status='passed',builds=builds,source_hashes=source_hashes,reference_hashes=reference_hashes,external_dependencies=external,
        two_clean_builds_equivalent=True,generated_outputs_seeded=0,commands=all_commands,physical_function_qualified=False,foundry_full_signoff=False,D_writes=False,
        scope='Two independent empty build trees, authored source and M1 design/phase/config inputs; licensed tools preinstalled. Regenerate core, interfaces, S6 label correction, full installed pre-DRC/graph, nominal paths and teaching replay. Timestamp-only digest plus all-layer XOR/text; raw byte hashes retained. No FEM/FDTD re-solve, environment installation, measured EC/MMI/heater calibration or foundry signoff.',next_step='M3 S2')
    save(OUT/'rebuild_results.json',result);print('M3 S1: TWO CLEAN BUILDS ACCEPTED',flush=True)
if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    try:main()
    except Exception as error:
        save(OUT/'last_failure.json',dict(status='failed',error=str(error),traceback=traceback.format_exc()));raise
