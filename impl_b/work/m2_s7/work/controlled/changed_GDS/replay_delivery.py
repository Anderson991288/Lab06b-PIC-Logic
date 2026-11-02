"""Portable NumPy replay. Writes generated results only to --out."""
from pathlib import Path
import os,sys,json,csv,argparse
ROOT=Path(__file__).resolve().parent
if os.name=='nt' and (Path(sys.prefix)/'Library/bin').is_dir():
    prefix=Path(sys.prefix);os.environ['PATH']=os.pathsep.join([str(prefix/'Library/bin'),str(prefix/'Scripts'),str(prefix),os.environ.get('PATH','')]);os.environ['CONDA_PREFIX']=str(prefix);os.environ['CONDA_DLL_SEARCH_MODIFICATION_ENABLE']='1';DLL_HANDLE=os.add_dll_directory(str(prefix/'Library/bin'))
for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:os.environ[k]='1'
from verify_delivery import verify,sha,load
def replay(out):
    integrity=verify(ROOT);sys.path.insert(0,str(ROOT/'models'))
    import numpy as np
    from common import handoff,backannotation as a
    spec=load(ROOT/'data/pic_spec.json');ph=load(ROOT/'data/phase_settings.json');model=load(ROOT/'data/model.json');paths=load(ROOT/'data/paths.json');ref=load(ROOT/'reports/replay_results.json')
    handoff.validate_phases(spec,ph,sha(ROOT/'data/pic_spec.json'));catalog=handoff.phase_catalog(spec,ph);off=a.compensation(spec,paths,model);candidate=a.candidate(catalog,off)
    stored=load(ROOT/'data/phase_settings_backannotated.json');repacked={g:dict(theta=[p[i] for i in range(7)],phi=[p[i] for i in range(7,14)]) for g,p in stored['programs'].items()}
    for g in catalog:
        for kind in ['theta','phi']:assert np.max(np.abs(np.exp(1j*np.array(candidate[g][kind]))-np.exp(1j*np.array(repacked[g][kind]))))<1e-10
    observed={};max_error=0.
    for name,meta in ref['cases'].items():
        program=candidate if meta['phase_source']=='model_candidate' else catalog
        result=a.evaluate(spec,paths,model,program,meta['loss_db_per_cm'],meta['propagation_enabled']);count=sum(r['passed'] for r in result.values());assert count==meta['passed']
        refs={(r['gate'],r['pattern']):r for r in meta['rows']}
        for gate,r in result.items():
            for row in r['rows']:
                old=refs[(gate,row['pattern'])];assert row['bit']==old['bit'] and row['expected']==old['expected'];max_error=max(max_error,abs(row['delta']-old['delta']))
        observed[name]=dict(passed=count,total=80)
    assert max_error<1e-9
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    report=dict(status='passed',integrity=integrity,scenarios=observed,max_abs_delta_error=max_error,physical_function_qualified=False,
        scope='Verified replay of packaged uniform-neff core-plane teaching model; not calibrated chip acceptance.')
    (out/'portable_replay.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args();print(json.dumps(replay(args.out),indent=2))
