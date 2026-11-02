from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'work'))
from common import boundary,handoff
target=ROOT/'config/m2_boundary.json'
if target.exists():raise SystemExit('Existing boundary plan must not be overwritten')
spec=json.loads((ROOT/'pic_spec.json').read_text(encoding='utf-8'))
plan=boundary.make_plan(spec,handoff.digest(ROOT/'pic_spec.json'))
target.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Prepared M2 boundary overlay:',target)
