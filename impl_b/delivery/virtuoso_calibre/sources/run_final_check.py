from pathlib import Path
import subprocess,json
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
exe=ROOT/json.loads((ROOT/'EDA_paths.json').read_text(encoding='utf-8-sig'))['windows']['klayout_exe']
r=subprocess.run([str(exe),'-b','-r',str(HERE/'final_geometry.py')],capture_output=True,text=True,timeout=180)
(HERE/'out/final_geometry.log').write_text(r.stdout+'\n'+r.stderr)
print(r.stdout,r.stderr);assert r.returncode==0
