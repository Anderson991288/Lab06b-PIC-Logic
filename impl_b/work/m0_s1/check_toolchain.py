"""M0 S1 core toolchain: native Python, licensed PDK, KLayout and rebuilt MZI."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONFIG = ROOT / 'EDA_paths.json'
cfg = json.loads(CONFIG.read_text(encoding='utf-8-sig'))


def resolved(value):
    path = Path(os.path.expandvars(value))
    return path if path.is_absolute() else ROOT / path


tools = {key: resolved(value) for key, value in cfg['windows'].items() if value}
out = HERE / 'out'
out.mkdir(exist_ok=True)
items = []


def add(key, label, passed, detail, required=True):
    items.append(dict(id=key, name=label, status='pass' if passed else 'blocked', detail=detail, required=required))
    print(key, 'PASS' if passed else 'BLOCKED', label, detail, flush=True)


def probe(key, name, command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=45,
                                env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
        log = result.stdout + '\n' + result.stderr
        (out / (key.lower() + '.log')).write_text(log, encoding='utf-8')
        add(key, name, result.returncode == 0, (log.strip().splitlines() or ['no output'])[-1][:500])
    except (OSError, subprocess.TimeoutExpired) as error:
        add(key, name, False, str(error))


for key in ['ipkiss_python', 'pdk_cornerstone', 'drc_deck', 'klayout_exe']:
    add('P_' + key, key, key in tools and tools[key].is_file() if key != 'pdk_cornerstone' else tools[key].is_dir(), str(tools.get(key)))
probe('T1', 'IPKISS licensed import', [str(tools['ipkiss_python']), '-c', "import ipkiss3.all as i3, ipkiss; print('IPKISS',ipkiss.__version__)"])
probe('T2', 'CORNERSTONE MMI ports', [str(tools['ipkiss_python']), '-c', "import cornerstone, cornerstone.all as pdk; print('CORNERSTONE',getattr(cornerstone,'__version__','unknown')); c=pdk.SOI220nm_1550nm_TE_STRIP_2x2_MMI(); print('MMI ports:',[p.name for p in c.Layout().ports])"])
if tools['klayout_exe'].is_file():
    probe('T5', 'KLayout batch version', [str(tools['klayout_exe']), '-b', '-v'])
else:
    add('T5', 'KLayout batch version', False, 'Project-local KLayout binary has not been supplied.')
layout = out / 'mzi_drc_result.json'
if layout.exists():
    data = json.loads(layout.read_text(encoding='utf-8'))
    clean, fault = data['drc_clean'], data['drc_fault']
    add('E1a', 'Clean GDS outline', clean['outside'] == 0, f"outside={clean['outside']}")
    add('E1b', 'Injected outside shape', fault['outside'] == 1, f"outside={fault['outside']}; expected=1")
    ran = clean['status'] == 'ran'
    add('E1c', 'Clean GDS DRC', ran and clean.get('total') == 0, json.dumps({'status':clean['status'],'total':clean.get('total')}))
    add('E1d', 'F1-F8 injection detected', ran and fault.get('all_caught', False) and not fault.get('unexpected'), json.dumps(fault.get('hit', {})))
else:
    add('E1', 'Rebuild MZI and run DRC', False, 'Run build_mzi_drc.py first.')
report = dict(step='M0 S1', timestamp=datetime.now(timezone(timedelta(hours=8))).isoformat(),
              root=str(ROOT), planned_root='C:\\EDA_Codex\\Lab06b', root_matches_plan=ROOT==Path('C:/EDA_Codex/Lab06b'),
              config=str(CONFIG), python=sys.executable, items=items,
              core_passed=all(item['status']=='pass' for item in items if item['required']),
              summary={state:sum(i['status']==state for i in items) for state in ['pass','blocked']},
              drc_deck_sha256=hashlib.sha256(tools['drc_deck'].read_bytes()).hexdigest(),
              deferred_to_m0_s2=['femwell modal analysis', 'Meep field rerun'],
              scope='This run imports IPKISS/PDK and checks rebuilt GDS/DRC. It does not claim chip-level B7 completion or field simulation.')
(out / 'toolchain_check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('Core toolchain:', 'PASS' if report['core_passed'] else 'BLOCKED', flush=True)
