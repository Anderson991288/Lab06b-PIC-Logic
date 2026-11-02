#!/usr/bin/env bash
set -eu
python3 - <<'PY'
from pathlib import Path
import os,signal,json
task=Path('/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction')
old_logs=[str(task/'out'/f) for f in ['virtuoso_CDS.log','virtuoso_lower_CDS.log','virtuoso_review_CDS.log']]
stopped=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  args=(p/'cmdline').read_bytes().decode().split('\0');exe=Path(os.readlink(p/'exe')).name
  own_virt=exe=='virtuoso' and any(x in args for x in old_logs)
  own_qt=False
  if exe=='calibrerve' and '-gui' in args and '-drc' in args:
   env=(p/'environ').read_bytes().decode().split('\0')
   own_qt=('MGC_CALIBRE_DRC_RUNSET_FILE='+str(task/'out/Lab06b_auto.runset') in env and 'CALIBRE_ENABLE_CLASSIC_CI_DRC=1' not in env)
  if own_virt or own_qt:
   os.kill(int(p.name),signal.SIGTERM);stopped.append({'pid':int(p.name),'app':exe,'scope':'Own obsolete launch / completed review smoke only'})
 except (PermissionError,FileNotFoundError,ProcessLookupError):pass
(task/'out/own_trial_cleanup.json').write_text(json.dumps({'stopped':stopped,'preserved':'Controlled current-design Virtuoso, classic Interactive and final RVE; no user apps or services targeted'},indent=2))
print('Closed',len(stopped),'own obsolete launch processes; current evidence apps retained')
PY
