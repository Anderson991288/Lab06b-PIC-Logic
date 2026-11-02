from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[2]
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if (ROOT/'pic_spec.json').exists() or (ROOT/'phase_settings.json').exists():raise SystemExit('Existing handoff sources must not be overwritten')
course=json.loads((ROOT/'config/course.json').read_text(encoding='utf-8'))
catalog=json.loads((ROOT/'config/m1_s4_phase_programs.json').read_text(encoding='utf-8'))
ops=course['architecture']['ops_zero_based']
ports=[]
for direction in ['in','out']:
    for k in range(5):
        role=course['architecture']['inputs'][k] if direction=='in' else 'positive_readout' if k==1 else 'negative_readout' if k==3 else 'unread_output'
        ports.append(dict(id=f'{direction}{k}',direction=direction,mode_index=k,alias=f'{"i" if direction=="in" else "o"}{k+1}',role=role,physical_interface=None))
channels=[dict(id=f'{kind}{k}',instance=f'M{k}',parameter=kind,location=location,heater_logical_id=f'H_M{k}_{kind}',pad_id=None,calibration=None)
    for kind,location in [('theta','upper_arm_between_MMI1_MMI2'),('phi','upper_input_before_MMI1')] for k in range(1,8)]
spec=dict(schema='lab06b.pic_spec.v1',design_id='LAB06B_B7',units=dict(phase='rad',length='um',power='normalized'),
    design_point=dict(wavelength_um=1.55,polarization='TE'),phase_settings_file='phase_settings.json',
    architecture=dict(macro='B7',modes=5,instances=[dict(id=f'M{k+1}',layer=layer,modes=[p,p+1],theta_channel=f'theta{k+1}',phi_channel=f'phi{k+1}') for k,(p,layer) in enumerate(ops)],
        bypass_segments=[dict(layer=layer,mode=m) for layer in range(4) for m in range(5) if m not in [q for p,l in ops if l==layer for q in (p,p+1)]]),
    input_vector_order=['x1','x2','x3','x4','R'],encoding=dict(type='OOK',zero_field=0,one_field=1,data_phase_rad=0,reference_amplitude=3,reference_phase_rad=0),
    optical_ports=ports,phase_channels=channels,phase_vector_order=[c['id'] for c in channels],
    readout=dict(positive_port='out1',negative_port='out3',threshold=0,epsilon=1e-10,boundary_bit=None),
    functions=[dict(id=g,active_data_indices=[0,1] if g in ['AND2','OR2','XOR2'] else [0,1,2,3]) for g in course['functions']],
    acceptance=dict(patterns_per_function=16,total_patterns=80,pattern_index_lsb='x1',rule='signed_margin > epsilon'),
    model=dict(type='ideal_forward_MZI',mzi_loss_db=0,bypass='identity',physical_calibration=False),
    m2_pending=['PDK circuit validation','wire lengths and propagation','chip optical interfaces','heater geometry and calibration','PAD and ground mapping','DRC and connectivity'])
save(ROOT/'pic_spec.json',spec)
phases=dict(schema='lab06b.phase_settings.v1',phase_unit='rad',spec_sha256=hashlib.sha256((ROOT/'pic_spec.json').read_bytes()).hexdigest(),
    channel_order=spec['phase_vector_order'],programs={g:catalog['gates'][g]['theta']+catalog['gates'][g]['phi'] for g in course['functions']},
    provenance=dict(source='config/m1_s4_phase_programs.json',source_sha256=hashlib.sha256((ROOT/'config/m1_s4_phase_programs.json').read_bytes()).hexdigest(),synthesis='inherited phase settings; no new optimization'))
save(ROOT/'phase_settings.json',phases)
print('Created M1 logical core specification and bound phase settings')
