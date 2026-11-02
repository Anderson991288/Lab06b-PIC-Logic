"""Versioned M1 logical-core contract, independent of any project root.

Explicit contract validation plus cross-file binding and numerical replay.
No PDK, layout, heater calibration or foundry approval is implied.
"""
from pathlib import Path,PurePosixPath
import json,hashlib,csv,math
from . import b7,logic_validation as logic


def require(ok,path,message):
    if not ok:raise ValueError(path+': '+message)


def finite(x):return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_spec(s):
    def booleans(value,path=''):
        if isinstance(value,bool):require(path=='model.physical_calibration',path,'boolean is not a numeric contract value')
        elif isinstance(value,dict):
            for k,v in value.items():booleans(v,(path+'.' if path else '')+k)
        elif isinstance(value,list):
            for k,v in enumerate(value):booleans(v,path+f'[{k}]')
    booleans(s)
    require(s.get('schema')=='lab06b.pic_spec.v1','schema','unsupported specification version')
    require(s.get('design_id')=='LAB06B_B7','design_id','expected LAB06B_B7')
    require(s.get('units')==dict(phase='rad',length='um',power='normalized'),'units','expected rad / um / normalized')
    require(s.get('phase_settings_file')=='phase_settings.json','phase_settings_file','use local phase_settings.json')
    require(s.get('design_point')==dict(wavelength_um=1.55,polarization='TE'),'design_point','expected 1.55 um TE')
    a=s.get('architecture',{})
    require(a.get('macro')=='B7' and a.get('modes')==5,'architecture','expected B7 with five modes')
    instances=a.get('instances',[])
    require(len(instances)==7,'architecture.instances','expected seven MZIs')
    expected_ops=((0,0),(3,0),(1,1),(0,2),(2,2),(1,3),(3,3))
    for k,(inst,(p,layer)) in enumerate(zip(instances,expected_ops),1):
        require(inst==dict(id=f'M{k}',layer=layer,modes=[p,p+1],theta_channel=f'theta{k}',phi_channel=f'phi{k}'),
                f'architecture.instances[{k-1}]','instance, modes, layer or channel mapping mismatch')
    top=b7.Topology(5,expected_ops,(1,3))
    expected_bypass=[dict(layer=layer,mode=mode) for layer,ports in enumerate(b7.bypass_ports(top)) for mode in ports]
    require(a.get('bypass_segments')==expected_bypass,'architecture.bypass_segments','six identity segments must be explicit')
    require(s.get('input_vector_order')==['x1','x2','x3','x4','R'],'input_vector_order','fixed physical field order required')
    encoding=s.get('encoding',{})
    require(encoding==dict(type='OOK',zero_field=0,one_field=1,data_phase_rad=0,reference_amplitude=3,reference_phase_rad=0),
            'encoding','fixed coherent OOK and reference amplitude 3 required')
    ports=s.get('optical_ports',[])
    require(len(ports)==10,'optical_ports','all five inputs and five outputs are required')
    expected=[]
    for direction in ['in','out']:
        for mode in range(5):
            role=(['x1','x2','x3','x4','R'][mode] if direction=='in' else 'positive_readout' if mode==1 else 'negative_readout' if mode==3 else 'unread_output')
            expected.append(dict(id=f'{direction}{mode}',direction=direction,mode_index=mode,
                alias=(f'i{mode+1}' if direction=='in' else f'o{mode+1}'),role=role,physical_interface=None))
    require(ports==expected,'optical_ports','port names, roles, order or pending physical interfaces differ')
    channels=s.get('phase_channels',[])
    require(len(channels)==14,'phase_channels','fourteen named channels required')
    by_id={c.get('id'):c for c in channels}
    require(len(by_id)==14,'phase_channels','duplicate channel ID')
    for kind,location in [('theta','upper_arm_between_MMI1_MMI2'),('phi','upper_input_before_MMI1')]:
        for k in range(1,8):
            channel=dict(id=f'{kind}{k}',instance=f'M{k}',parameter=kind,location=location,
                         heater_logical_id=f'H_M{k}_{kind}',pad_id=None,calibration=None)
            require(by_id.get(channel['id'])==channel,'phase_channels.'+channel['id'],'logical-to-physical phase mapping differs')
    order=s.get('phase_vector_order',[])
    require(len(order)==14 and len(set(order))==14 and set(order)==set(by_id),'phase_vector_order','must name each channel exactly once')
    readout=s.get('readout',{})
    require(readout==dict(positive_port='out1',negative_port='out3',threshold=0,epsilon=1e-10,boundary_bit=None),
            'readout','fixed port polarity, threshold and boundary rule required')
    functions=s.get('functions',[])
    require(functions==[dict(id=g,active_data_indices=[0,1] if g in logic.GATES[:3] else [0,1,2,3]) for g in logic.GATES],
            'functions','five functions and active inputs must be explicit')
    require(s.get('acceptance')==dict(patterns_per_function=16,total_patterns=80,pattern_index_lsb='x1',rule='signed_margin > epsilon'),
            'acceptance','complete four-bit truth coverage required')
    require(s.get('model')==dict(type='ideal_forward_MZI',mzi_loss_db=0,bypass='identity',physical_calibration=False),
            'model','M1 ideal model must remain explicit')
    require(s.get('m2_pending')==['PDK circuit validation','wire lengths and propagation','chip optical interfaces','heater geometry and calibration','PAD and ground mapping','DRC and connectivity'],
            'm2_pending','M2 work must remain pending')
    return top


def validate_phases(spec,p,spec_sha256):
    validate_spec(spec)
    require(p.get('schema')=='lab06b.phase_settings.v1','phase.schema','unsupported phase version')
    require(p.get('spec_sha256')==spec_sha256,'phase.spec_sha256','phase settings belong to a different specification')
    require(p.get('phase_unit')=='rad','phase.phase_unit','radian required')
    require(p.get('channel_order')==spec['phase_vector_order'],'phase.channel_order','phase vector names do not match specification')
    programs=p.get('programs',{})
    require(set(programs)==set(logic.GATES),'phase.programs','exactly five functions required')
    for name,values in programs.items():
        require(isinstance(values,list) and len(values)==14 and all(finite(v) for v in values),
                'phase.programs.'+name,'fourteen finite radian values required')
    return p


def phase_catalog(spec,p):
    programs={}
    for gate,values in p['programs'].items():
        by_channel=dict(zip(p['channel_order'],values))
        programs[gate]=dict(theta=[by_channel[f'theta{k}'] for k in range(1,8)],phi=[by_channel[f'phi{k}'] for k in range(1,8)])
    return programs


def replay(spec,p):
    top=validate_spec(spec);catalog=phase_catalog(spec,p)
    return {gate:logic.evaluate_gate(top,catalog[gate],gate,reference_amplitude=spec['encoding']['reference_amplitude'],
        reference_phase=spec['encoding']['reference_phase_rad'],threshold=spec['readout']['threshold'],epsilon=spec['readout']['epsilon']) for gate in logic.GATES}


def port_rows(spec):return [{**{k:p[k] for k in ['id','direction','mode_index','alias','role']},'physical_interface':'pending_M2'} for p in spec['optical_ports']]
def channel_rows(spec):
    by_id={c['id']:c for c in spec['phase_channels']}
    return [dict(vector_index=k,**{key:by_id[c][key] for key in ['id','instance','parameter','location','heater_logical_id']},pad_id='pending_M2',calibration='pending_M2') for k,c in enumerate(spec['phase_vector_order'])]


def verify_tables(root,spec):
    for filename,expected in [('optical_ports.csv',port_rows(spec)),('phase_channels.csv',channel_rows(spec))]:
        with (Path(root)/filename).open(encoding='utf-8-sig',newline='') as stream:observed=list(csv.DictReader(stream))
        require(observed==[{k:str(v) for k,v in row.items()} for row in expected],filename,'CSV does not match specification')


def verify_manifest(root):
    root=Path(root).resolve();manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    require(manifest.get('schema')=='lab06b.handoff_manifest.v1','manifest.schema','unsupported manifest')
    entries=manifest.get('files',[]);seen=set()
    for entry in entries:
        rel=PurePosixPath(entry['path'])
        require(not rel.is_absolute() and '..' not in rel.parts and '\\' not in entry['path'] and ':' not in entry['path'],'manifest.path','local relative path required')
        require(entry['path'] not in seen,'manifest.path','duplicate file entry');seen.add(entry['path'])
        path=(root/rel).resolve()
        require(path.is_relative_to(root) and path.is_file(),'manifest.file','missing or escaped file')
        require(digest(path)==entry['sha256'],'manifest.sha256','file digest mismatch: '+str(rel))
    required={'pic_spec.json','phase_settings.json','phase_channels.csv','optical_ports.csv','acceptance_truth.csv','replay_handoff.py','README.md',
              *{f'model/common/{name}.py' for name in ['__init__','mzi','b7','linear_network','encoding','logic_validation','handoff']}}
    require(required.issubset(seen),'manifest.files','incomplete standalone package')
    return manifest


def load_bundle(root):
    root=Path(root);verify_manifest(root)
    spec=json.loads((root/'pic_spec.json').read_text(encoding='utf-8'))
    phases=json.loads((root/'phase_settings.json').read_text(encoding='utf-8'))
    validate_spec(spec);validate_phases(spec,phases,digest(root/'pic_spec.json'));verify_tables(root,spec)
    return spec,phases


def verify_truth_csv(root,results):
    with (Path(root)/'acceptance_truth.csv').open(encoding='utf-8-sig',newline='') as stream:rows=list(csv.DictReader(stream))
    require(len(rows)==80,'acceptance_truth.csv','expected 80 cases')
    expected={(g,row['pattern']):row for g,r in results.items() for row in r['rows']};seen=set();max_error=0.
    for row in rows:
        key=(row['gate'],row['pattern'])
        require(key in expected and key not in seen,'acceptance_truth.csv','unknown or duplicate case');seen.add(key)
        ref=expected[key]
        require(int(row['expected'])==ref['expected'] and int(row['bit'])==ref['bit'],'acceptance_truth.csv','truth or bit mismatch')
        for key in ['delta','signed_margin']:
            value=float(row[key]);require(math.isfinite(value),'acceptance_truth.csv','nonfinite result')
            max_error=max(max_error,abs(value-ref[key]))
    require(max_error<1e-10,'acceptance_truth.csv','numerical result mismatch')
    return max_error
