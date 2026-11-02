"""Extract route components outside actual MMI geometries and compare B7 pairs.

Geometric photonic graph only. Union of GDS3/5 does not prove mode continuity.
No foundry-qualified LVS device/extraction deck or parasitics are implied.
"""
import pya

def analyze(layout,info,spec,core_info,electrical_evaluate):
    top=layout.top_cell();db=layout.dbu
    def region(layer):return pya.Region(top.begin_shapes_rec(layout.layer(layer,0))).merged()
    electrical=electrical_evaluate(region(41),region(39),info,db)
    core=layout.cell('LAB06B_B7_CORE');unit=layout.cell('LAB06B_MZI_CORE')
    mzis=[i for i in core.each_inst() if layout.cell(i.cell_index).name=='LAB06B_MZI_CORE']
    placements={tuple(round(v/db) for v in p['origin_um']):p['id'] for p in core_info['placement']}
    mmi_positions={tuple(round(v/db) for v in xy):'MMI'+str(k+1) for k,xy in enumerate(core_info['unit']['mmi_positions_um'])}
    remove=pya.Region();terminals=[];devices=[];joint_issues=[];si=region(3);material=(si+region(5)).merged()
    template_region=None
    for mz in mzis:
        disp=(mz.trans.disp.x,mz.trans.disp.y);mid=placements.get(disp)
        if mid is None:raise RuntimeError('Unrecognized actual MZI placement')
        for inst in unit.each_inst():
            device=layout.cell(inst.cell_index)
            if 'MMI' not in device.name.upper():continue
            key=(inst.trans.disp.x,inst.trans.disp.y);local_name=mmi_positions.get(key)
            if local_name is None:raise RuntimeError('Unrecognized actual MMI placement')
            total=mz.trans*inst.trans;dr=pya.Region(device.begin_shapes_rec(layout.layer(3,0))).merged();remove+=dr.transformed(total)
            if template_region is None:template_region=dr
            devices.append(dict(id=mid+':'+local_name,cell=device.name,template_identical=(dr^template_region).is_empty()))
            for port,xy in core_info['unit']['mmi_ports'].items():
                outside=-.01 if port.startswith('in') else .01
                local=pya.Point(round((xy[0]+outside)/db),round(xy[1]/db));point=total*local
                center=total*pya.Point(round(xy[0]/db),round(xy[1]/db))
                dx,dy=round(.01/db),round(.05/db)
                probe=pya.Region(pya.Box(center.x-dx,center.y-dy,center.x+dx,center.y+dy))
                if not (probe-si).is_empty():joint_issues.append(mid+':'+local_name+':'+port)
                terminals.append(dict(id=mid+':'+local_name+':'+port,point=point))
    for p in info['optical_io']:
        x,y=p['facet_um'];x+=.1 if p['direction']=='in' else -.1
        terminals.append(dict(id=p['EC_id']+':facet',point=pya.Point(round(x/db),round(y/db))))
    wires=(material-remove).merged();components=list(wires.each());groups={k:[] for k in range(len(components))};missing=[]
    for t in terminals:
        found=[k for k,p in enumerate(components) if p.inside(t['point'])]
        if len(found)!=1:missing.append(dict(terminal=t['id'],components=found))
        else:groups[found[0]].append(t['id'])
    expected=[];fronts=[f'EC_IN{k}:facet' for k in range(5)]
    for instance in spec['architecture']['instances']:
        name=instance['id'];upper,lower=instance['modes']
        for rail,port in [(upper,'in2'),(lower,'in1')]:expected.append(sorted([fronts[rail],name+':MMI1:'+port]))
        expected.extend([sorted([name+':MMI1:out2',name+':MMI2:in2']),sorted([name+':MMI1:out1',name+':MMI2:in1'])])
        fronts[upper]=name+':MMI2:out2';fronts[lower]=name+':MMI2:out1'
    expected.extend(sorted([fronts[k],f'EC_OUT{k}:facet']) for k in range(5))
    observed=[sorted(v) for v in groups.values()];expected_set={tuple(v) for v in expected};observed_set={tuple(v) for v in observed}
    optic=dict(MZI_instances=len(mzis),MMI_occurrences=len(devices),terminal_count=len(terminals),route_components=len(components),
        devices=devices,expected_pairs=sorted(expected),observed_groups=sorted(observed),missing_terminals=missing,
        joint_issues=joint_issues,missing_pairs=[list(v) for v in sorted(expected_set-observed_set)],unexpected_groups=[list(v) for v in sorted(observed_set-expected_set)],
        passed=len(devices)==14 and len(terminals)==66 and len(components)==33 and not missing and not joint_issues and expected_set==observed_set and all(d['template_identical'] for d in devices),
        scope='Actual GDS material graph with 14 MMI black boxes removed; 33 outside-device connections vs declared B7. Not optical field, phase/loss, EC mode validation or foundry-certified LVS.')
    return dict(electrical=electrical,optical=optic,passed=electrical['passed'] and optic['passed'])
