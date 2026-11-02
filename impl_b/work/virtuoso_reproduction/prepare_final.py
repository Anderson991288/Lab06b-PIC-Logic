from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;OUT=HERE/'out';BASE='/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction'
(OUT/'exports_final').mkdir(exist_ok=True)
mapping=json.loads((OUT/'oa_cell_name_map.json').read_text())
(OUT/'exports_final/cell.map').write_text(''.join('lab06b_crosscad_20261031 '+lower+' layout '+original+'\n' for lower,original in mapping.items()),encoding='utf-8',newline='\n')
current=HERE/'work/oa_lower/cds.lib';line='DEFINE lab06b_crosscad_20261031 '+BASE+'/work/oa_crosscad/lab06b_crosscad_20261031\n';s=current.read_text();current.write_text(s+line if line not in s else s,encoding='utf-8',newline='\n')
for name,limit in [('crosscad','8191')]:
    pass
print('Prepared final cell-name restoration map and OA library registration')
