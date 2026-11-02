#!/usr/bin/env bash
set -u
TASK=/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction
chattr +F "$TASK/work/oa" > "$TASK/out/case_attribute.log" 2>&1
rc=$?
python3 - "$rc" <<'PY'
import sys,os,pathlib,json
p=pathlib.Path('/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction/work/oa')
results={'chattr_returncode':int(sys.argv[1])}
for name in ['CaseProbe','caseprobe']:
    try:
        fd=os.open(str(p/name),os.O_WRONLY|os.O_CREAT|os.O_EXCL);os.close(fd);results[name]='created'
    except FileExistsError:results[name]='already_exists'
results['case_sensitive']=results['caseprobe']=='created'
dest=pathlib.Path('/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction/out/case_probe.json')
dest.write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
PY
