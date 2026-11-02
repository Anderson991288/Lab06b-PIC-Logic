#!/usr/bin/env bash
set -eu
python3 - <<'PY'
from pathlib import Path
import json
root=Path('/home/EDA/mentor/calibre2026/aok_cal_2026.1_17.11')
out={'documentation_paths':[]}
for p in root.iterdir():
    if any(s in p.name.lower() for s in ['doc','help','pdf']):
        out['documentation_paths'].append(str(p))
        if p.is_dir():out[str(p)]=[str(x) for x in p.iterdir()][:60]
print(json.dumps(out,indent=2))
PY
