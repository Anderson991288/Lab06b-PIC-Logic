#!/usr/bin/env bash
set -u
TASK=/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction
cd "$TASK/work/oa_crosscad"
timeout 10 calibre -interactive -drc -help > "$TASK/out/calibre_interactive_help.log" 2>&1
printf 'Interactive help return %s\n' "$?"
python3 - <<'PY'
from pathlib import Path
r=Path('/home/EDA/mentor/calibre2026/aok_cal_2026.1_17.11/bin')
print('Related executables:',[p.name for p in r.iterdir() if any(x in p.name.lower() for x in ['gui','inter','runset','calibre','drc'])][:50])
PY
