from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,csv,hashlib
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/m2_s4/out'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
B=load(OUT/'build_review.json');infos={v:load(OUT/v/'layout_info.json') for v in ['before','after']}
reviews={v:load(OUT/v/'review_geometry.json') for v in infos};cross=load(OUT/'route_crossings.json')
old,new=infos.values();settings=load(ROOT/'config/m2_review_layout.json');target=settings['review']['continuous_radius_target_um']
def csv_table(name,rows):
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    with (OUT/name).open(encoding='utf-8-sig',newline='') as f:actual=list(csv.DictReader(f))
    assert actual==[{k:str(v) for k,v in r.items()} for r in rows]
metrics=[]
for key,before,after,unit in [
    ('S_bend_horizontal',20.,settings['s_bend_length'],'um'),
    ('continuous_min_radius',old['unit']['continuous_s_bend_min_radius_um'],new['unit']['continuous_s_bend_min_radius_um'],'um'),
    ('column_length',old['column_length_um'],new['column_length_um'],'um'),
    ('core_optical_span_x',old['core_optical_span_um'][0],new['core_optical_span_um'][0],'um'),
    ('upper_singlemode_waveguide_per_MZI',old['unit']['waveguide_upper_um'],new['unit']['waveguide_upper_um'],'um'),
    ('inter_MMI_upper',old['unit']['inter_mmi_upper_um'],new['unit']['inter_mmi_upper_um'],'um'),
    ('design_frame_x',old['core_frame_size_um'][0],new['core_frame_size_um'][0],'um')]:
    metrics.append(dict(metric=key,before=before,after=after,delta=after-before,unit=unit))
csv_table('change_metrics.csv',metrics)
paths=[];old_paths={p['id']:p for p in old['paths']}
for p in new['paths']:
    q=old_paths[p['id']];paths.append(dict(path_id=p['id'],kind=p['kind'],before_um=q['length_um'],after_um=p['length_um'],delta_um=p['length_um']-q['length_um']))
csv_table('length_changes.csv',paths)
port_changes=[]
for a,b in zip(old['ports'],new['ports']):
    assert a['id']==b['id'] and a['mode']==b['mode'] and a['core_role']==b['core_role'] and a['angle_deg']==b['angle_deg']
    port_changes.append(dict(port=a['id'],role=a['core_role'],before_x_um=a['position_um'][0],before_y_um=a['position_um'][1],after_x_um=b['position_um'][0],after_y_um=b['position_um'][1],dx_um=b['position_um'][0]-a['position_um'][0],dy_um=b['position_um'][1]-a['position_um'][1]))
csv_table('port_changes.csv',port_changes)
phase_changes=[];old_phase={p['channel']:p for p in old['phase_regions']}
for p in new['phase_regions']:
    q=old_phase[p['channel']]
    phase_changes.append(dict(channel=p['channel'],heater=p['heater_logical_id'],before_x_um=q['center_um'][0],after_x_um=p['center_um'][0],y_um=p['center_um'][1],dx_um=p['center_um'][0]-q['center_um'][0],A_x_um=p['local_contacts'][0]['center_um'][0],B_x_um=p['local_contacts'][1]['center_um'][0],external_pad='pending_M2_S5'))
csv_table('phase_region_changes.csv',phase_changes)
native=[r for v in reviews.values() for r in v['images']]
source_paths=['work/m2_s4/analyze_paths.py','work/m2_s4/summarize_review.py']
checks=[('both_GDS_readbacks',all(load(OUT/v/'gds_readback.json')['passed'] for v in infos)),
    ('both_scoped_rule_screens',all(r['all_scoped_rules_passed'] for r in reviews.values())),
    ('both_route_coverage_samples',all(r['route_samples_covered'] for r in reviews.values())),
    ('both_centerline_crossing_reviews',all(r['passed'] for r in cross.values())),
    ('three_actual_fault_GDS_detected',len(reviews['after']['controlled_faults'])==3 and all(r['detected'] for r in reviews['after']['controlled_faults'])),
    ('radius_course_target_achieved',new['unit']['continuous_s_bend_min_radius_um']>=target),
    ('channel_names_and_counts_unchanged',old['counts']==new['counts'] and set(old_phase)=={p['channel'] for p in new['phase_regions']}),
    ('all_regression',all(r['successful'] for r in B['regression'].values())),
    ('S3_baseline_unchanged',B['S3_baseline_unchanged']),('M1_immutable_and_baseline_replay',B['M1_sources_and_zip_unchanged'] and B['M1_baseline_replay_passed']==80),
    ('twentyfour_native_images',len(native)==24 and all((ROOT/'course/figures/m2_s4'/p['file']).is_file() for p in native))]
checklist=[
    dict(id='R1',topic='埠序與接收極性',status='passed',evidence='port_changes.csv：10 個角色與朝向不變，out1 正／out3 負。'),
    dict(id='R2',topic='七顆放置與六段直通',status='passed',evidence='兩版 GDS readback 皆核對 7 個 MZI 引用、14 MMI、6 段直通。'),
    dict(id='R3',topic='接縫與路徑覆蓋',status='passed',evidence='兩版皆核對十埠、81 個接點；另取樣全部波導中心線頂點與線段中點。'),
    dict(id='R4',topic='彎道裕量',status='improved',evidence=f'連續解析半徑 {old["unit"]["continuous_s_bend_min_radius_um"]:.6f} → {new["unit"]["continuous_s_bend_min_radius_um"]:.6f} µm；課程目標 {target:g}，既有規劃值 5。'),
    dict(id='R5',topic='Si／HT／局部金屬線寬與間距',status='passed',evidence='KLayout 六項局部篩查皆零警示；不是完整 foundry deck。'),
    dict(id='R6',topic='交叉與非預期接觸',status='passed_with_scope',evidence='58 段中心線的 1653 對組合沒有非預期交集；僅檢查 sidecar，不是從 GDS 抽取完整拓樸。'),
    dict(id='R7',topic='heater／局部落墊',status='passed',evidence='14 個 HT 與 28 個局部金屬區保留；A/B 座標按名稱更新。'),
    dict(id='R8',topic='EC／外部 PAD／共地',status='pending_M2_S5',evidence='尚未配置；28 個局部接觸不是最終外部 PAD 數。'),
    dict(id='R9',topic='完整 DRC／LVS／製程驗證',status='pending_M2_S6',evidence='本步局部篩查不替代完整驗證。'),
    dict(id='R10',topic='光學損耗與相位回註',status='pending_M2_S7',evidence='長度改變，尚未計算實體傳播相位或重新調整相位；M1 80/80 仍只作基準。')]
csv_table('review_checklist.csv',checklist)
passed=all(ok for name,ok in checks)
result=dict(step='M2 S4',timestamp=datetime.now(timezone(timedelta(hours=8))).isoformat(),root=str(ROOT),
    review_decision='accept_margin_improved_core' if passed else 'unresolved',course_radius_target_um=target,
    target_authority=settings['review']['target_authority'],metrics=metrics,review_checklist=checklist,
    regression=B['regression'],versions={v:dict(radius_um=infos[v]['unit']['continuous_s_bend_min_radius_um'],optical_span_um=infos[v]['core_optical_span_um'],
        scoped_rules=reviews[v]['rules'],route_coverage=reviews[v]['route_coverage'],gap_bounds=reviews[v]['isolated_gap_bounds'],
        readback=load(OUT/v/'gds_readback.json'),crossings=cross[v]) for v in infos},
    changed_ports=sum(r['dx_um']!=0 or r['dy_um']!=0 for r in port_changes),changed_phase_centers=sum(r['dx_um']!=0 for r in phase_changes),
    controlled_faults=reviews['after']['controlled_faults'],native_images=native,
    checks=[dict(name=n,passed=bool(v)) for n,v in checks],
    source_hashes={**B['source_hashes'],**{p:sha(ROOT/p) for p in source_paths}},
    S3_baseline_hashes=B['S3_baseline_hashes'],S3_baseline_unchanged=B['S3_baseline_unchanged'],
    M1_sources_and_zip_unchanged=B['M1_sources_and_zip_unchanged'],M1_baseline_replay_passed=B['M1_baseline_replay_passed'],
    core_passed=passed,scope='Scoped KLayout visual/geometry review, design-margin improvement and revision evidence. No full foundry DRC/LVS, EC/PAD/GND fanout, thermal calibration, measured bend loss or layout-extracted truth acceptance.')
save(OUT/'review_results.json',result)
if passed:
    prefix='work/m2_s4/out/after/'
    save(ROOT/'config/m2_current_core.json',dict(schema='lab06b.current_core.v1',accepted_at_step='M2 S4',
        m1_spec_sha256=sha(ROOT/'pic_spec.json'),layout_config='config/m2_review_layout.json',layout_config_sha256=sha(ROOT/'config/m2_review_layout.json'),
        files={prefix+p:sha(OUT/'after'/p) for p in ['b7_core.gds','mzi_core.gds','layout_info.json']},
        review_result='work/m2_s4/out/review_results.json',pending=['EC/PAD/GND','full DRC and connectivity','thermal calibration','layout phase backannotation and replay']))
print('M2 S4:',result['review_decision'],'regression',sum(r['passed'] for r in B['regression'].values()),'native images',len(native))
print('radius',old['unit']['continuous_s_bend_min_radius_um'],'->',new['unit']['continuous_s_bend_min_radius_um'],'; changed ports',result['changed_ports'],'phase centers',result['changed_phase_centers'])
raise SystemExit(0 if passed else 1)
