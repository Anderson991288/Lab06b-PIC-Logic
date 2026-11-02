#!/usr/bin/env bash
set -eu
python3 - <<'PY'
import subprocess
r=subprocess.run(['xwininfo','-root','-tree'],capture_output=True,text=True)
for line in r.stdout.splitlines():
    if any(s in line.lower() for s in ['virtuoso','lab06b','calibre','layout xl']):print(line)
PY
