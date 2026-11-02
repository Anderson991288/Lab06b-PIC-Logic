#!/usr/bin/env bash
set -eu
CAL=/home/EDA/mentor/calibre2026/aok_cal_2026.1_17.11
grep -n -E 'layout-server|LAYOUT_SERVER|layout_server|NEED_SEND|runset|execCalibre' "$CAL/lib/calibre.skl" | head -55
head -125 "$CAL/shared/pkgs/icv/systest_data/tclsrc/gui_drc_script.tcl"
python3 - <<'PY'
from pathlib import Path
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  args=(p/'cmdline').read_bytes().decode().replace('\x00',' ')
  if 'calibrerve' not in args or ' -gui' not in args:continue
  print('OWN_GUI',p.name,args)
  env=(p/'environ').read_bytes().decode().split('\x00')
  for e in env:
   if e.startswith(('MGC_CALIBRE_','CALIBRE_')) and not any(k in e.lower() for k in ('lic','token','key')):print(e)
 except (PermissionError,FileNotFoundError):pass
PY
