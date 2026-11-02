from pathlib import Path
import json,hashlib,csv,shutil

README='''# M1 → M2 logical B7 handoff

This is a portable ideal-model handoff, not a fabricated or PDK-verified chip.
Python >= 3.10 and NumPy are required; the optical model is included in model/.

Run with your numerical Python:
    python replay_handoff.py --gate AND2 --bits 1100

The consumer verifies SHA-256, schema and cross-file references, optical/phase
CSV tables, then recomputes all 80 truths and compares acceptance_truth.csv.
It loads model/common from this folder; no parent course/config directory is needed.
verification/replay_results.json is a regenerated output, excluded from the
immutable-file manifest. The manifest checks file consistency; semantic and
numerical checks are additional requirements.

pic_spec.json fixes the core topology, encoding, ten optical ports, fourteen
named phase channels, readout and acceptance. phase_settings.json binds to
the exact spec SHA-256 and declares its channel order. Values are full precision radians.
PAD IDs, physical optical interfaces and heater calibration remain pending M2.
Preserve unread output ports and the six bypass paths in subsequent physical work.
Do not treat phase in rad as heater voltage or the ideal replay as PDK approval.
'''


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists() or p.read_bytes()!=data:p.write_bytes(data)


def build_package(project,dest):
    project=Path(project);dest=Path(dest);dest.mkdir(parents=True,exist_ok=True)
    import sys
    sys.path.insert(0,str(project/'work'))
    from common import handoff
    spec=json.loads((project/'pic_spec.json').read_text(encoding='utf-8'))
    phases=json.loads((project/'phase_settings.json').read_text(encoding='utf-8'))
    handoff.validate_spec(spec);handoff.validate_phases(spec,phases,sha(project/'pic_spec.json'))
    for name in ['pic_spec.json','phase_settings.json']:put(dest/name,(project/name).read_bytes())
    put(dest/'README.md',README.encode('utf-8'))
    put(dest/'replay_handoff.py',(project/'work/m1_s5/replay_handoff.py').read_bytes())
    modules=['__init__','mzi','b7','linear_network','encoding','logic_validation','handoff']
    for name in modules:put(dest/'model/common'/f'{name}.py',(project/'work/common'/f'{name}.py').read_bytes())
    for name,rows in [('optical_ports.csv',handoff.port_rows(spec)),('phase_channels.csv',handoff.channel_rows(spec))]:
        with (dest/name).open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    baseline=json.loads((project/'work/m1_s4/out/logic_results.json').read_text(encoding='utf-8'))
    if not baseline['core_passed']:raise ValueError('M1 S4 acceptance is not complete')
    for rel,digest in baseline['source_hashes'].items():
        if sha(project/rel)!=digest:raise ValueError('M1 S4 source changed: '+rel)
    with (dest/'acceptance_truth.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f);writer.writerow(['gate','pattern','expected','bit','delta','signed_margin'])
        for gate,r in baseline['baseline'].items():
            for row in r['rows']:writer.writerow([gate,row['pattern'],row['expected'],row['bit'],row['delta'],row['signed_margin']])
    names=['pic_spec.json','phase_settings.json','README.md','replay_handoff.py','optical_ports.csv','phase_channels.csv','acceptance_truth.csv',
           *[f'model/common/{name}.py' for name in modules]]
    manifest=dict(schema='lab06b.handoff_manifest.v1',package_kind='M1 logical core handoff to M2',
                  files=[dict(path=name,sha256=sha(dest/name)) for name in sorted(names)])
    put(dest/'manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8'))
    return manifest
