"""Prepare a new, isolated full native-CAD replay without pre-existing OA."""
from pathlib import Path
from datetime import datetime
import json,shutil,subprocess,hashlib
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;OUT=HERE/'out'
stage=HERE/'work'/('clean_replay_'+datetime.now().strftime('%Y%m%d_%H%M%S'));stage.mkdir(parents=True,exist_ok=False)
exe=ROOT/json.loads((ROOT/'EDA_paths.json').read_text(encoding='utf-8-sig'))['windows']['klayout_exe']
shutil.copy2(ROOT/'work/m2_s6/out/after/b7_ec_pad.gds',stage/'source.gds')
shutil.copy2(OUT/'input/negative_controls.gds',stage/'negative.gds')
shutil.copy2(OUT/'rules/cornerstone_basic_draft.svrf',stage/'cornerstone_basic_draft.svrf')
shutil.copy2(OUT/'exports/layer.map',stage/'layer.map')
mapping=json.loads((OUT/'oa_cell_name_map.json').read_text())
for lib in ['lab06b_replay_source','lab06b_replay_final']:
 (stage/(lib+'.map')).write_text(''.join(f'{lib} {lower} layout {name}\n' for lower,name in mapping.items()),newline='\n')
r=subprocess.run([str(exe),'-b','-r',str(HERE/'patch_labels.py'),'-rd','source_path='+str(stage/'source.gds'),'-rd','dest_path='+str(stage/'candidate.gds'),'-rd','record_path='+str(stage/'label_revision.json')],capture_output=True,text=True,timeout=120)
(stage/'patch.log').write_text(r.stdout+'\n'+r.stderr);assert r.returncode==0,r.stderr
assert hashlib.sha256((stage/'source.gds').read_bytes()).hexdigest()=='0a8bece1fddd9e10a5cac8369ac57259f5775735b4f5ef6758ab76ceddc23963'
(OUT/'clean_replay_stage.json').write_text(json.dumps({'windows':str(stage),'wsl':'/mnt/c/'+stage.as_posix()[3:]},indent=2))
print('Fresh replay prepared:',stage)
