"""Executed ONLY in a newly staged source tree; generate core and logical bundle."""
from pathlib import Path
import sys,os,json,shutil,csv,inspect,platform
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;OUT=HERE/'out'
sys.path.insert(0,str(ROOT/'work'))
for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:os.environ[k]='1'
from common import handoff,core_layout as geo
import cornerstone,ipkiss,numpy as np
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def csvsave(p,rows):
    with p.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
spec=load(ROOT/'pic_spec.json');phases=load(ROOT/'phase_settings.json');top=handoff.validate_spec(spec);handoff.validate_phases(spec,phases,handoff.digest(ROOT/'pic_spec.json'))
bundle=ROOT/'delivery/m1_handoff';bundle.mkdir(parents=True)
for name in ['pic_spec.json','phase_settings.json']:shutil.copy2(ROOT/name,bundle/name)
csvsave(bundle/'optical_ports.csv',handoff.port_rows(spec));csvsave(bundle/'phase_channels.csv',handoff.channel_rows(spec))
baseline=handoff.replay(spec,phases);truth=[dict(gate=g,**{k:r[k] for k in ['pattern','expected','bit','delta','signed_margin']}) for g,result in baseline.items() for r in result['rows']]
csvsave(bundle/'acceptance_truth.csv',truth)
shutil.copy2(ROOT/'work/m1_s5/replay_handoff.py',bundle/'replay_handoff.py');(bundle/'README.md').write_text('Logical bundle regenerated from author design inputs in M3 S1.\n',encoding='utf-8')
for name in ['__init__','mzi','b7','linear_network','encoding','logic_validation','handoff']:
    dest=bundle/'model/common'/(name+'.py');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'work/common'/(name+'.py'),dest)
save(bundle/'manifest.json',dict(schema='lab06b.handoff_manifest.v1',files=[dict(path=p.relative_to(bundle).as_posix(),sha256=handoff.digest(p)) for p in sorted(bundle.rglob('*')) if p.is_file() and p.name!='manifest.json']))
handoff.load_bundle(bundle)
c=load(ROOT/'config/m2_review_layout.json');geo.validate(c,handoff.digest(ROOT/'pic_spec.json'));core,preview,info=geo.build(top,c)
folder=ROOT/'work/m2_s4/out/after';folder.mkdir(parents=True,exist_ok=True)
for cell,name in [(core,'b7_core.gds'),(preview,'mzi_core.gds')]:cell.get_default_view(geo.i3.LayoutView).write_gdsii(str(folder/name))
save(folder/'layout_info.json',info)
save(ROOT/'config/m2_current_core.json',dict(schema='lab06b.current_core.v1',accepted_at_step='M2 S4',m1_spec_sha256=handoff.digest(ROOT/'pic_spec.json'),layout_config='config/m2_review_layout.json',layout_config_sha256=handoff.digest(ROOT/'config/m2_review_layout.json'),files={str((folder/name).relative_to(ROOT).as_posix()):handoff.digest(folder/name) for name in ['b7_core.gds','mzi_core.gds','layout_info.json']}))
runtime=dict(python=sys.version,executable=sys.executable,numpy=np.__version__,cornerstone_version=cornerstone.__version__,ipkiss_version=getattr(ipkiss,'__version__',None),common_module=str(Path(geo.__file__).resolve()),build_root=str(ROOT),baseline_passed=sum(r['summary']['passed'] for r in baseline.values()))
runtime['external_module_sources']={str(p):handoff.digest(p) for p in {Path(cornerstone.__file__),Path(inspect.getfile(geo.pdk.mmi2x2().__class__)),Path(inspect.getfile(geo.pdk.wg_template().__class__))}}
assert Path(geo.__file__).resolve().is_relative_to(ROOT) and runtime['baseline_passed']==80
save(OUT/'runtime.json',runtime);print('Fresh core and M1 bundle generated; baseline 80/80',flush=True)
