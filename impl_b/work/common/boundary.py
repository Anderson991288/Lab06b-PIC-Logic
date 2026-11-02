"""M2 S1 logical system boundary overlay; M1 contract remains immutable."""
from . import handoff
BLOCKS=[('B7_CORE','PIC','seven_MZI_core'),('OPTICAL_INTERFACES','PIC','ten_planned_edge_couplers'),
        ('HEATERS','PIC','fourteen_phase_actuators'),('ELECTRICAL_ROUTING','PIC','drive_and_return_routing'),
        ('LASER_0','external','shared_coherent_source'),('DATA_MODULATORS','external','four_channel_optical_OOK'),
        ('REFERENCE_CONDITIONER','external','reference_amplitude_and_phase'),('PHASE_ALIGNMENT','external','relative_phase_control'),
        ('HEATER_DRIVERS','external','fourteen_calibrated_bias_channels'),('PD_PAIR','external','two_readout_photodiodes'),
        ('TIA_COMPARATOR','external','calibrated_differential_readout'),('OUTPUT_LOADS','external','unread_output_monitor_or_load')]


def make_plan(spec,spec_sha256):
    handoff.validate_spec(spec)
    optical=[]
    for p in spec['optical_ports']:
        index=p['mode_index'];direction=p['direction']
        endpoint=(f'EXT_DATA_X{index+1}' if index<4 else 'EXT_REFERENCE') if direction=='in' else 'PD_PLUS' if index==1 else 'PD_MINUS' if index==3 else f'EXT_LOAD{index}'
        optical.append(dict(interface_id=f'OPT_{direction.upper()}{index}',core_port=p['id'],mode_index=index,direction=direction,
            role=p['role'],proposed_side='left' if direction=='in' else 'right',proposed_coupler_id=f'EC_{direction.upper()}{index}',
            physical_cell=None,physical_position_um=None,external_endpoint=endpoint,source_laser='LASER_0' if direction=='in' else None))
    electrical=[];returns=[]
    by_id={c['id']:c for c in spec['phase_channels']}
    for index,name in enumerate(spec['phase_vector_order']):
        c=by_id[name]
        electrical.append(dict(interface_id='CTRL_'+name,kind='phase_drive',phase_channel=name,instance=c['instance'],
            heater_logical_id=c['heater_logical_id'],driver_channel=f'DRV{index:02d}',drive_endpoint=c['heater_logical_id']+'.A',
            return_net='GND',pad_id=None,drive_value=None,drive_unit=None,calibration=None))
        returns.append(dict(heater_logical_id=c['heater_logical_id'],terminal='B',net='GND'))
    electrical.append(dict(interface_id='GND',kind='common_return',phase_channel=None,instance=None,heater_logical_id=None,
        driver_channel='DRV_RETURN',drive_endpoint='GND',return_net='GND',pad_id=None,drive_value=None,drive_unit=None,calibration=None))
    return dict(schema='lab06b.m2_boundary.v1',m1_spec_sha256=spec_sha256,stage='logical_boundary_only',
        system_blocks=[dict(id=i,domain=d,function=f,implementation_status='pending_physical_implementation' if d=='PIC' else 'external_requirement') for i,d,f in BLOCKS],
        optical_io=optical,electrical_io=electrical,return_connections=returns,
        core_field_targets=dict(data_one_amplitude=1,reference_amplitude=3,reference_power=9,data_phase_rad=0,reference_phase_rad=0,power_unit_w=None),
        data_encoding_location='external_optical_modulators',heater_role='fixed_function_phase_programming',
        reference_plane='M1_core_ports_after_input_coupling_before_output_coupling',
        receiver=dict(location='external',positive_interface='OPT_OUT1',negative_interface='OPT_OUT3',
            comparison='equivalent_core_power_difference',threshold=0,epsilon=1e-10,optical_path_calibration='pending',
            gain_and_offset_calibration='pending',physical_receiver_spec=None),
        grounding=dict(logical_return_net='GND',strategy='shared_return_logical_plan',physical_pad_count=None,common_impedance_validation='pending'),
        physical_validation=dict(PDK_circuit='pending',layout='pending',PAD_mapping='pending',heater_calibration='pending',DRC_connectivity='pending'))


def validate_plan(plan,spec,spec_sha256):
    def reject_bools(value):
        if isinstance(value,bool):raise ValueError('boundary: boolean cannot replace a contract number')
        if isinstance(value,dict):
            for v in value.values():reject_bools(v)
        if isinstance(value,list):
            for v in value:reject_bools(v)
    reject_bools(plan)
    handoff.validate_spec(spec)
    handoff.require(plan.get('schema')=='lab06b.m2_boundary.v1','boundary.schema','unsupported version')
    handoff.require(plan.get('m1_spec_sha256')==spec_sha256,'boundary.m1_spec_sha256','M1 specification binding mismatch')
    expected=make_plan(spec,spec_sha256)
    for key in ['stage','system_blocks','optical_io','electrical_io','return_connections','core_field_targets',
                'data_encoding_location','heater_role','reference_plane','receiver','grounding','physical_validation']:
        handoff.require(plan.get(key)==expected[key],'boundary.'+key,'boundary, role, mapping or pending physical assignment mismatch')
    return dict(optical_interfaces=len(plan['optical_io']),phase_drive_interfaces=sum(r['kind']=='phase_drive' for r in plan['electrical_io']),
        logical_return_nets=1,electrical_interface_roles=len(plan['electrical_io']),physical_pad_count=None,
        on_chip_blocks=sum(r['domain']=='PIC' for r in plan['system_blocks']),external_blocks=sum(r['domain']=='external' for r in plan['system_blocks']))


def optical_rows(plan):
    return [{k:('not_applicable' if k=='source_laser' else 'pending_M2') if v is None else v for k,v in row.items()} for row in plan['optical_io']]
def electrical_rows(plan):
    return [{k:('pending_M2' if k=='pad_id' or (row['kind']=='phase_drive' and k in ('drive_value','drive_unit','calibration')) else 'not_applicable') if v is None else v for k,v in row.items()} for row in plan['electrical_io']]


def trace_interface(plan,interface_id):
    for row in plan['optical_io']:
        if row['interface_id']==interface_id:
            return [row['external_endpoint'],row['interface_id'],row['proposed_coupler_id'],row['core_port']] if row['direction']=='in' else [row['core_port'],row['proposed_coupler_id'],row['interface_id'],row['external_endpoint']]
    for row in plan['electrical_io']:
        if row['interface_id']==interface_id:
            return ['GND','DRV_RETURN'] if row['kind']=='common_return' else [row['driver_channel'],row['interface_id'],row['drive_endpoint'],row['heater_logical_id']+'.B',row['return_net'],'DRV_RETURN']
    raise ValueError('Unknown boundary interface')
