from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[2]
source=ROOT/'config/m0_s3_reference_phases.json'
saved=json.loads(source.read_text(encoding='utf-8'))
catalog=dict(schema='B7 phase programs v1',phase_unit='rad',phase_order=[f'M{k}' for k in range(1,8)],
    ops_zero_based=saved['ops'],gates={gate:{key:setting[key] for key in ['theta','phi']} for gate,setting in saved['gates'].items()})
target=ROOT/'config/m1_s4_phase_programs.json'
if target.exists():raise SystemExit('Phase catalog already exists; do not overwrite learner work.')
target.write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
provenance=dict(local_snapshot='config/m0_s3_reference_phases.json',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    catalog='config/m1_s4_phase_programs.json',catalog_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
    scope='Extracted full-precision theta/phi only. No new phase synthesis; historical truth rows/U are not the new truth oracle.')
(ROOT/'config/m1_s4_phase_provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')
print('Prepared five phase programs:',target)
