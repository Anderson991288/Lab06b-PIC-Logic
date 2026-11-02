"""Portable stdlib manifest and cross-file contract checker. No local EDA paths."""
from pathlib import Path,PurePosixPath
import json,hashlib,csv,math
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def require(ok,msg):
    if not ok:raise ValueError(msg)
def verify(root=ROOT):
    root=Path(root).resolve();m=load(root/'manifest.json');require(m.get('schema')=='lab06b.pic_delivery.v1','manifest schema')
    seen=set()
    for r in m['files']:
        rel=PurePosixPath(r['path']);require(not rel.is_absolute() and '..' not in rel.parts and ':' not in r['path'] and '\\' not in r['path'],'unsafe manifest path')
        require(r['path'] not in seen,'duplicate manifest path');seen.add(r['path']);p=(root/rel).resolve()
        require(p.is_relative_to(root) and p.is_file(),'missing/escaped file '+r['path']);require(sha(p)==r['sha256'],'SHA mismatch '+r['path'])
    required={'layout/B7_final.gds','data/pic_spec.json','data/phase_settings.json','data/model.json','data/paths.json','data/phase_settings_backannotated.json','reports/replay_400.csv','reports/replay_results.json','reports/verification_S6.json','verify_delivery.py','replay_delivery.py','recheck_geometry.py','geometry_engine.py','README.md',*{'models/common/'+n+'.py' for n in ['__init__','mzi','b7','linear_network','encoding','logic_validation','handoff','backannotation']}}
    required|={'data/chip_info.json','data/core_geometry.json','geometry/connectivity.py','geometry/electrical_geometry.py','interfaces/pad_heater_map.csv','interfaces/optical_io.csv','interfaces/ground_pads.csv','reports/pre_drc.lyrdb'}
    require(required<=seen,'incomplete delivery')
    spec=load(root/'data/pic_spec.json');ph=load(root/'data/phase_settings.json');model=load(root/'data/model.json');paths=load(root/'data/paths.json');candidate=load(root/'data/phase_settings_backannotated.json')
    gds=sha(root/'layout/B7_final.gds');specsha=sha(root/'data/pic_spec.json')
    require(gds==m['gds_sha256']==paths['gds_sha256']==candidate['gds_sha256']==load(root/'reports/verification_S6.json')['gds_sha256'],'GDS binding mismatch')
    require(ph['spec_sha256']==specsha==candidate['original_spec_sha256'],'specification binding mismatch')
    require(candidate['original_phases_sha256']==sha(root/'data/phase_settings.json'),'original phase binding mismatch')
    require(candidate['model_sha256']==sha(root/'data/model.json'),'candidate model binding mismatch')
    require(candidate['channel_order']==spec['phase_vector_order'] and candidate['phase_unit']=='rad','phase channel/unit mismatch')
    require(set(candidate['programs'])==set(ph['programs']) and all(len(v)==14 and all(isinstance(x,(int,float)) and math.isfinite(x) for x in v) for v in candidate['programs'].values()),'candidate program coverage')
    require(model['reference_plane']=='M1_core_ports' and model['physical_function_qualified'] is False and candidate['physical_function_qualified'] is False and candidate['voltage_calibration'] is None and m['physical_function_qualified'] is False and m['foundry_full_signoff'] is False,'qualification/reference-plane mismatch')
    with (root/'reports/replay_400.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    reference=load(root/'reports/replay_results.json');keys={(r['case'],r['gate'],r['pattern']) for r in rows}
    expected={(c,g,''.join(str((k>>i)&1) for i in range(4))) for c in reference['cases'] for g in ph['programs'] for k in range(16)}
    require(len(rows)==400 and keys==expected and len(keys)==400,'incomplete 400-case comparison')
    require(len(paths['paths'])==68 and len(paths['routes'])==33,'path coverage mismatch')
    return dict(status='passed',files=len(seen),gds_sha256=gds,physical_function_qualified=False,foundry_full_signoff=False)
if __name__=='__main__':print(json.dumps(verify(),indent=2))
