from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,hashlib,csv,shutil
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;OUT=HERE/'out'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
build=load(OUT/'verification_build.json');patch=load(OUT/'label_patch.json');controls=load(OUT/'control_results.json');reg=load(OUT/'regression.json')
connections={v:load(OUT/v/'connectivity.json') for v in ['before','after']}
def csvfile(name,rows,fields=None):
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)
before,after=build['before'],build['after']
csvfile('violations_before.csv',[dict(id=r['id'],category=r['category'],cell=r['cell'],multiplicity=r['multiplicity'],bbox_um=str(r['bbox_um']),marker='; '.join(r['values'])) for r in before['items']])
csvfile('rule_comparison.csv',[dict(category=cat,before=before['counts'].get(cat,0),after=after['counts'].get(cat,0)) for cat in sorted(set(before['categories']+after['categories']))])
csvfile('violations_after.csv',[],['id','category','cell','multiplicity','bbox_um','marker'])
csvfile('negative_controls.csv',[dict(case=r['id'],target=r['target'],detected=r['detected'],pre_DRC_records=r['drc_records'],electrical_passed=r['electrical_passed'],optical_passed=r['optical_passed'],metal_nets=r['metal_net_count'],optical_routes=r['optical_route_count']) for r in controls])
csvfile('optical_connections.csv',[dict(route=k,terminal_A=p[0],terminal_B=p[1],observed_match=p in connections['after']['optical']['observed_groups']) for k,p in enumerate(connections['after']['optical']['expected_pairs'],1)])
csvfile('electrical_connections.csv',[dict(channel=p['channel'],pad=p['pad_id'],pad_component=str(p['pad_component']),A_components=str(p['signal_A_components']),B_components=str(p['return_B_components']),passed=p['passed']) for p in connections['after']['electrical']['connections']])
log=[dict(id='S6-LABEL-01',trigger='Two GDS100 gap markers at in0/out0 in original pre-DRC report',action='Scale all ten port labels 4 to 5 um; keep original anchors and 1 nm output grid',verification='Original deck unchanged; 2 records to 0; six physical layers XOR equal; optical/electrical graph pairs unchanged',status='closed')]
save(OUT/'fix_log.json',log);csvfile('fix_log.csv',log)
checks=[('same_original_deck',before['deck_sha256']==after['deck_sha256']==sha(ROOT/'work/common/drc/cornerstone_Si220_passive.lydrc')),
    ('all_original_categories_executed',before['category_count']==after['category_count'] and before['category_count']>0),
    ('real_initial_violations_recorded',before['total_records']==2 and all('GDS100' in r['category'] for r in before['items'])),
    ('after_pre_DRC_zero',after['total_records']==0),('physical_layers_unchanged',all(r['identical'] for r in patch['physical_mask_comparison'])),
    ('only_port_label_windows_changed',patch['only_port_label_windows_changed']),('both_geometric_connectivity_compared',all(r['passed'] for r in connections.values())),
    ('eight_real_GDS_faults_detected',len(controls)==8 and all(r['detected'] for r in controls)),
    ('DRC_insufficient_demonstrated',any(r['target'] in ['electrical','optical'] and r['drc_records']==0 and r['detected'] for r in controls)),
    ('existing_regression',all(r['successful'] for r in reg['regression'].values())),
    ('M1_immutable_baseline_only',reg['M1_sources_and_zip_unchanged'] and reg['M1_baseline_replay_passed']==80)]
extra=['work/m2_s6/generate_faults.py','work/m2_s6/run_controls.py','work/m2_s6/regression.py','work/m2_s6/summarize.py']
result=dict(step='M2 S6',timestamp=datetime.now(timezone(timedelta(hours=8))).isoformat(),root=str(ROOT),
    before=before,after=after,label_patch=patch,connectivity=connections,negative_controls=controls,fix_log=log,
    regression=reg['regression'],M1_sources_and_zip_unchanged=reg['M1_sources_and_zip_unchanged'],M1_baseline_replay_passed=reg['M1_baseline_replay_passed'],
    checks=[dict(name=n,passed=bool(v)) for n,v in checks],source_hashes={**build['source_hashes'],**{p:sha(ROOT/p) for p in extra}},
    gds_sha256=sha(OUT/'after/b7_ec_pad.gds'),foundry_full_signoff=False,formal_foundry_LVS=False,optical_mode_phase_verified=False,
    scope='All installed original v3.1 pre-DRC categories at declared custom design size; geometric metal/HT and photonic black-box netlist comparison; not foundry full DRC/LVS, EC response, thermal calibration or layout-extracted truth replay.',
    core_passed=all(v for n,v in checks))
save(OUT/'verification_results.json',result)
if result['core_passed']:
    # Same physical interfaces; sidecar and CSVs remain byte-identical to S5.
    source=build['source_chip_index'];files={}
    for rel in source['files']:
        src=ROOT/rel;name=src.name;dest=OUT/'after'/name
        if src.suffix!='.gds':shutil.copy2(src,dest)
        files[dest.relative_to(ROOT).as_posix()]=sha(dest)
    save(ROOT/'config/m2_current_chip.json',dict(schema='lab06b.current_chip.v1',accepted_at_step='M2 S6',qualification='installed_pre_DRC_zero_and_geometric_netlist_compare_only',
        m1_spec_sha256=sha(ROOT/'pic_spec.json'),core_index='config/m2_current_core.json',files=files,
        results='work/m2_s6/out/verification_results.json',label_revision='port labels only; physical masks identical to S5',
        pending=['foundry full signoff and process-qualified LVS','qualified EC/mode/response','thermal/common-ground calibration','layout path backannotation and replay']))
print('M2 S6:',result['core_passed'],'pre-DRC',before['total_records'],'->',after['total_records'],'controls',sum(r['detected'] for r in controls),'/8; geometric optical routes',connections['after']['optical']['route_components'])
raise SystemExit(0 if result['core_passed'] else 1)
