#!/usr/bin/env bash
set -u
python3 - <<'PY'
import pathlib,subprocess,socket,json
r={}
try:r['eda.ic_addresses']=socket.gethostbyname_ex('eda.ic')[2]
except OSError as e:r['resolution_error']=str(e)
r['license_processes']=subprocess.run(['ps','-eo','pid,args'],capture_output=True,text=True).stdout.splitlines()
r['license_processes']=[s for s in r['license_processes'] if any(n in s for n in ['lmgrd','cdslmd','mgcld','saltd'])]
r['top_EDA_directories']=[p.name for p in pathlib.Path('/home/EDA').iterdir() if p.is_dir()]
r['candidate_license_directories']=[]
for parent in [pathlib.Path('/home/EDA/cadence'),pathlib.Path('/home/EDA/mentor'),pathlib.Path('/home/edauser')]:
    if not parent.exists():continue
    for p in parent.iterdir():
        if any(w in p.name.lower() for w in ['licen','start','setup','env']):r['candidate_license_directories'].append(str(p))
r['listening_ports']=subprocess.run(['ss','-ltn'],capture_output=True,text=True).stdout
print(json.dumps(r,indent=2))
PY
