#!/usr/bin/env bash
set -eu
CAL=/home/EDA/mentor/calibre2026/aok_cal_2026.1_17.11
for t in xdotool gdbus python3 wish; do command -v "$t" || true; done
sed -n '1265,1290p' "$CAL/shared/systest/test.CalibreinteractiveDRC"
file "$CAL/shared/pkgs/icv/systest_data/tclsrc/wait_for_runset"
head -65 "$CAL/shared/pkgs/icv/systest_data/tclsrc/wait_for_runset"
find "$CAL/shared" -maxdepth 4 \( -iname '*custom*' -o -iname '*interact*' \) | head -35
python3 - <<'PY'
for m in ['pyatspi','gi']:
 try: __import__(m);print('MODULE',m,'OK')
 except ImportError:print('MODULE',m,'absent')
PY
