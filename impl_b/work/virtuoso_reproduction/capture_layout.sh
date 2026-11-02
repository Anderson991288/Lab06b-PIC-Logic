#!/usr/bin/env bash
set -eu
python3 - <<'PY'
import subprocess,re,json,pathlib
out=pathlib.Path('/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction/out')
text=subprocess.run(['xwininfo','-root','-tree'],capture_output=True,text=True,check=True).stdout
pattern=r'^\s+(0x[0-9a-f]+) "(Virtuoso[^\n"]*Layout Suite XL Reading: lab06b_current_20261031 lab06b_b7_ec_pad_chip layout)"'
matches=re.findall(pattern,text,re.M)
if len(matches)!=1:raise RuntimeError('Expected exactly one current layout X11 window: '+repr(matches))
window,title=matches[0];path=out/'screenshots/virtuoso_current.png'
subprocess.run(['import','-window',window,str(path)],check=True)
(out/'screenshots/virtuoso_capture.json').write_text(json.dumps({'method':'ImageMagick native Linux X11 window capture; unedited pixels','window_id':window,'title':title,'file':str(path)},indent=2))
print('Captured native current-design Virtuoso window',window)
PY
