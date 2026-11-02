#!/usr/bin/env bash
set -eu
TASK=/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction
cd "$TASK/work/oa"
virtuoso -W > "$TASK/out/virtuoso_version.log" 2>&1
calibre -version > "$TASK/out/calibre_version.log" 2>&1
strmin -help > "$TASK/out/strmin_help.log" 2>&1 || test "$?" -eq 1
strmout -help > "$TASK/out/strmout_help.log" 2>&1 || test "$?" -eq 1
xdpyinfo > "$TASK/out/display_info.log" 2>&1
python3 - <<'PY'
import pathlib,json,os
p=pathlib.Path('/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction/out')
print(json.dumps({'versions':{n:(p/n).read_text(errors='replace')[:700] for n in ['virtuoso_version.log','calibre_version.log']},'display_available':(p/'display_info.log').stat().st_size>0},indent=2))
PY
