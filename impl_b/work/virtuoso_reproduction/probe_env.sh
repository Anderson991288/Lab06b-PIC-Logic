#!/usr/bin/env bash
set -eu
python3 - <<'PY'
import os,json,pathlib,shutil,subprocess
record={'uid':os.getuid(),'user':os.environ.get('USER'),'cwd':os.getcwd(),'home':os.environ.get('HOME'),'display':os.environ.get('DISPLAY'),'wayland_display':os.environ.get('WAYLAND_DISPLAY'),'tools':{name:shutil.which(name) for name in ['virtuoso','strmin','strmout','calibre','xdpyinfo','wmctrl','xwininfo']}}
record['known_installations']={p:pathlib.Path(p).exists() for p in ['/home/EDA/cadence','/home/EDA/mentor/calibre2026/aok_cal_2026.1_17.11','/mnt/c/EDA_Codex/Lab06b']}
print(json.dumps(record,indent=2))
PY
