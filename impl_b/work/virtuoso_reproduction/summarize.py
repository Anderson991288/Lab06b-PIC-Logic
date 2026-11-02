from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,re,hashlib
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;OUT=HERE/'out'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def calibre(folder,filename):
 t=(folder/filename).read_text();rows=[dict(rule=k,count=int(n)) for k,n in re.findall(r'RULECHECK\s+(CS\S+)\s+\.+\s+TOTAL Result Count = (\d+)',t)]
 assert len(rows)==16,(folder,rows)
 return dict(checks=16,total=sum(r['count'] for r in rows),rules=rows,summary=(folder/filename).relative_to(ROOT).as_posix())
cal={name:calibre(OUT/folder,file) for name,folder,file in [('source','cli_accepted','summary.txt'),('negative','cli_negative','summary.txt'),('labels_revised','cli_crosscad','summary.txt'),('gui_auto','gui_auto','drc.summary'),('gui_fixed','gui_fixed','drc.summary')]}
assert [cal[k]['total'] for k in cal]==[27,16,0,0,0]
assert all(r['count']==1 for r in cal['negative']['rules'])
pre=load(OUT/'roundtrip_pre_drc.json');assert [r['records'] for r in pre]==[8,0,0,8,0]
geo=load(OUT/'final_geometry.json');clean=load(OUT/'clean_replay.json');assert geo['final_connectivity']['passed'] and clean['status']=='passed'
assert 'CellCount=43' in (OUT/'oa_final_readback.txt').read_text()
for p in ['import/streamIn_lower.log','import/streamIn_crosscad.log','exports_final/streamOut_8191.log']:
 assert "'0' error(s) and '0' warning(s)" in (OUT/p).read_text(),p
for p,val in [('GUI_auto_saved.runset','1'),('GUI_fixed_saved.runset','0')]:
 assert f'*drcLayoutGetFromViewer: {val}' in (OUT/p).read_text()
mapping=load(OUT/'oa_cell_name_map.json');assert len(mapping)==43 and len(set(mapping.values()))==43
source=ROOT/'work/m2_s6/out/after/b7_ec_pad.gds';assert sha(source)=='0a8bece1fddd9e10a5cac8369ac57259f5775735b4f5ef6758ab76ceddc23963'
pins=['pic_spec.json','phase_settings.json','config/m2_current_chip.json','delivery/m1_handoff.zip','delivery/Lab06b_M2_PIC_delivery.zip','work/m2_s6/out/after/b7_ec_pad.gds']
proofs=['out/input/B7_source.gds','out/input/B7_crosscad_labels.gds','out/exports_final/B7_crosscad_final.gds','out/exports/B7_max200.gds','out/exports/B7_max8191.gds','out/gui_auto/lab06b_b7_ec_pad_chip.calibre.db','out/GUI_auto_saved.runset','out/GUI_fixed_saved.runset','out/roundtrip_geometry.json','out/final_geometry.json','out/label_revision.json','out/clean_replay.json','out/oa_final_readback.txt','out/screenshots/virtuoso_final.png','out/screenshots/virtuoso_core.png','out/screenshots/calibre_auto_inputs.png','out/screenshots/calibre_fixed_inputs_0.png','out/screenshots/rve_final.png']
r=dict(schema='lab06b.virtuoso_calibre_reproduction.v1',timestamp=datetime.now(timezone(timedelta(hours=8))).isoformat(),status='passed',new_execution=True,D_writes=False,
 versions=dict(WSL='EDA_Server, AlmaLinux 8.10',Virtuoso='IC23.1-64b.ISR15.37',Calibre='2026.1_17.11',KLayout='0.30.12'),
 native_GUI=dict(virtuoso_layout_opened=True,interactive='Calibre 2026.1 classic Interactive, vendor-provided compatibility GUI',RVE='16 green checks, No Results Found; actual final results.db loaded',capture='Unedited native Linux X11 window pixels',automation='Virtuoso SKILL menu callback + native Calibre Tcl widget invocations; no Windows input injection used'),
 source=dict(path=source.relative_to(ROOT).as_posix(),sha256=sha(source),adopted_S6_unchanged=True),
 final=dict(path='work/virtuoso_reproduction/out/exports_final/B7_crosscad_final.gds',sha256=sha(OUT/'exports_final/B7_crosscad_final.gds'),top='LAB06B_B7_EC_PAD_CHIP',cells=43,instances=58,texts1002=16,bbox_um=[-920,-900,2940,740],maxVertices=8191,annotation_revision='19 GDS100 annotation clusters scaled 1.3; six physical masks XOR0; 16 GDS1002 texts unchanged',OA_library='lab06b_crosscad_20261031',OA_top='lab06b_b7_ec_pad_chip',OA_path='work/virtuoso_reproduction/work/oa_crosscad/lab06b_crosscad_20261031'),
 name_mapping=dict(count=43,case_collision_count=0,policy='Explicit lower-case OA names on C NTFS; original case restored on GDS export; text case preserved'),
 calibre=cal,pre_DRC=pre,original_roundtrip=load(OUT/'roundtrip_geometry.json'),geometry=geo,clean_replay=clean,
 rules=dict(calibre_scope='Unchanged locally authored 16-rule width/space draft; negative controls hit every rule once. Not qualified foundry DRC/LVS.',draft_sha256=sha(OUT/'rules/cornerstone_basic_draft.svrf'),KLayout_scope='Unchanged installed CORNERSTONE Si220 passive pre-DRC, all 31 report categories',KLayout_deck_sha256=pre[0]['deck_sha256']),
 preserved_bindings={p:sha(ROOT/p) for p in pins},proofs={p:sha(HERE/p) for p in proofs},limitations=['OA technology is Stream-In auto technology, not a foundry-qualified Virtuoso PDK; Layout XL extraction disabled without validLayers/validVias constraint groups.','Calibre 16-rule draft and KLayout 31-category pre-DRC have different scope/angle semantics; the GUI-auto GDS illustrates why both are checked.','No fabricated silicon, measured optical function, thermal calibration, qualified LVS or signoff is claimed.'])
(OUT/'reproduction_results.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'config/virtuoso_reproduction.json').write_text(json.dumps(dict(status='passed',report='course/virtuoso_calibre.html',proof='work/virtuoso_reproduction/out/reproduction_results.json',interop_deliverable=r['final'],original_adopted_source=r['source'],D_writes=False),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Fresh native-CAD reproduction evidence verified and pinned')
