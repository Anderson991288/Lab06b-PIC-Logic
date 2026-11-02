"""Add interface geometry to an immutable core. Signal A / return B.

Core is merged unchanged from its accepted GDS by KLayout, not regenerated.
EC is a custom teaching reference on actual PDK process layers, no compact model.
"""
import math
import numpy as np
from cornerstone.technology import select_technology_variant,CornerstoneVariant
select_technology_variant(CornerstoneVariant.SOI220)
from ipkiss3 import all as i3
from ipkiss.process.layer import PPLayer
from . import pdk

def validate(c):
    if c.get('schema')!='lab06b.chip_interfaces.v1' or c.get('units')!='um':raise ValueError('Interface schema/units invalid')
    if c.get('signal_terminal')!='A' or c.get('return_terminal')!='B':raise ValueError('M2 S1 requires A drive and B return')
    for key in ['fan_length','fan_stub','fiber_pitch','pad_size','wire_width','ground_step_before_column','ground_pad_x_margin']:
        v=c.get(key)
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0:raise ValueError('Invalid dimension '+key)
    if c['fan_length']<=2*c['fan_stub'] or c['fan_samples']<101:raise ValueError('Fan route sampling/span invalid')
    if c['pad_bottom_y']>=-120 or c['pad_top_y']<=0 or c['chip_bottom_y']>=c['pad_bottom_y']-c['pad_size']/2 or c['chip_top_y']<=c['pad_top_y']+c['pad_size']/2:raise ValueError('Pad rows must fit declared chip height')
    if c['wire_width']<2 or len(c['ground_column_y'])!=4:raise ValueError('Wire width or column returns invalid')
    ec=c['EC']
    if not 0<ec['tip_width']<=ec['wide_width'] or not ec['tip_straight']<ec['window_length']<ec['length']:raise ValueError('EC taper geometry invalid')
    if ec['coupling_loss_db'] is not None or ec['phase_response'] is not None:raise ValueError('Unvalidated EC cannot claim calibrated response')
    return c

def r3(v):return round(float(v),3)
def rectangle(layer,x0,y0,x1,y1):return i3.Rectangle(layer=layer,center=(r3((x0+x1)/2),r3((y0+y1)/2)),box_size=(r3(abs(x1-x0)),r3(abs(y1-y0))))
def line(elements,points,width):
    for (x0,y0),(x1,y1) in zip(points,points[1:]):
        if x0!=x1 and y0!=y1:raise ValueError('Electrical routes must be Manhattan')
        elements.append(rectangle(pdk.L_PAD,min(x0,x1)-width/2,min(y0,y1)-width/2,max(x0,x1)+width/2,max(y0,y1)+width/2))
def fan(x0,x1,y0,y1,c):
    stub=c['fan_stub'];span=x1-x0-2*stub
    return [(x0,y0)]+[(r3(x0+stub+span*t),r3(y0+(y1-y0)*(1-math.cos(math.pi*t))/2)) for t in np.linspace(0,1,c['fan_samples'])]+[(x1,y1)]
def route_length(p):return sum(math.dist(a,b) for a,b in zip(p,p[1:]))
def ec_cell(c):
    e=c['EC'];T=pdk.pdk.TECH.PPLAYER;tip=e['tip_width'];wide=e['wide_width'];xb=e['window_length'];xe=e['length'];s=e['tip_straight'];wg=pdk.WG_W
    elements=[i3.Boundary(layer=T.SLAB,shape=[(0,-tip/2),(s,-tip/2),(xb,-wide/2),(xe,-wg/2),(xe,wg/2),(xb,wide/2),(s,tip/2),(0,tip/2)]),
        i3.Boundary(layer=T.WG,shape=[(xb,-e['strip_start_width']/2),(xe,-wg/2),(xe,wg/2),(xb,e['strip_start_width']/2)]),
        rectangle(T.WG_HOL,0,-e['window_width']/2,xb,e['window_width']/2)]
    cell=i3.LayoutCell(name='LAB06B_REFERENCE_EC');cell.Layout(elements=elements);return cell

def build(core,c,boundary,spec):
    validate(c);L=core['column_length_um'];end=core['core_end_x_um'];lead_in=next(p for p in core['ports'] if p['id']=='in0')['position_um'][0]
    lead_out=next(p for p in core['ports'] if p['id']=='out0')['position_um'][0]
    west=lead_in-c['fan_length']-c['EC']['length'];east=lead_out+c['fan_length']+c['EC']['length'];center=-2*core['unit']['pitch_um']
    refs=[];elements=[];routes=[];optical=[];pads=[];signals=[];returns=[]
    ec=ec_cell(c)
    for mode in range(5):
        y=center+(2-mode)*c['fiber_pitch'];rail=-mode*core['unit']['pitch_um']
        refs.append(i3.SRef(reference=ec,position=(west,y),name=f'EC_IN{mode}'))
        refs.append(i3.SRef(reference=ec,position=(east,y),transformation=i3.Rotation(rotation=180.),name=f'EC_OUT{mode}'))
        for direction,points,facet,strip in [('in',fan(west+c['EC']['length'],lead_in,y,rail,c),[west,y],[west+c['EC']['length'],y]),
                                            ('out',fan(lead_out,east-c['EC']['length'],rail,y,c),[east,y],[east-c['EC']['length'],y])]:
            name=f'FAN_{direction}{mode}';wg=i3.Waveguide(name=name,trace_template=pdk.wg_template());wg.Layout(shape=points);refs.append(i3.SRef(reference=wg,name=name))
            dy=abs(y-rail);radius=None if dy==0 else 2*(c['fan_length']-2*c['fan_stub'])**2/(math.pi**2*dy)
            routes.append(dict(id=name,mode=mode,direction=direction,points_um=points,length_um=route_length(points),continuous_min_radius_um=radius))
            core_port=f'{direction}{mode}';b=next(p for p in boundary['optical_io'] if p['core_port']==core_port)
            optical.append(dict(interface_id=b['interface_id'],EC_id=f'EC_{direction.upper()}{mode}',core_port=core_port,mode=mode,
                direction=direction,external_endpoint=b['external_endpoint'],facet_um=facet,strip_um=strip,
                core_um=[lead_in if direction=='in' else lead_out,rail],facet_angle_deg=180 if direction=='in' else 0,
                coupling_loss_db=None,path_phase_rad=None,reference_plane='M1_core_ports',kind='reference_geometry_not_qualified_EC'))
    placements={p['id']:p for p in core['placement']};phase_regions={p['channel']:p for p in core['phase_regions']}
    first_origin=core['unit']['mmi_positions_um'][0][0];second_origin=core['unit']['mmi_positions_um'][1][0]
    for index,channel in enumerate(spec['phase_vector_order']):
        region=phase_regions[channel];ox,oy=placements[region['instance']]['origin_um'];upper=oy>=-30
        sy=c['pad_top_y'] if upper else c['pad_bottom_y'];sx=ox+(c['phi_signal_x_offset'] if region['parameter']=='phi' else first_origin+c['theta_signal_after_mmi1_origin'])
        a=next(p['center_um'] for p in region['local_contacts'] if p['endpoint'].endswith('.A'))
        b=next(p['center_um'] for p in region['local_contacts'] if p['endpoint'].endswith('.B'))
        gx=ox+(first_origin if region['parameter']=='phi' else second_origin);layer=placements[region['instance']]['layer'];gy=c['ground_column_y'][layer]
        spath=[a,[sx,oy],[sx,sy]];gpath=[b,[gx,oy],[gx,gy]]
        line(elements,spath,c['wire_width']);line(elements,gpath,c['wire_width'])
        pad=f'PAD_DRV{index:02d}';elements.append(rectangle(pdk.L_PAD,sx-c['pad_size']/2,sy-c['pad_size']/2,sx+c['pad_size']/2,sy+c['pad_size']/2))
        logical=next(p for p in boundary['electrical_io'] if p.get('phase_channel')==channel)
        pads.append(dict(pad_id=pad,net=channel,channel=channel,driver_channel=logical['driver_channel'],interface_id=logical['interface_id'],
            heater_logical_id=region['heater_logical_id'],drive_endpoint=region['heater_logical_id']+'.A',return_endpoint=region['heater_logical_id']+'.B',
            center_um=[sx,sy],size_um=c['pad_size'],side='top' if upper else 'bottom',signal_contact_um=a,return_contact_um=b,
            heater_center_um=region['center_um'],return_net='GND',phase_unit='rad',voltage_calibration=None))
        signals.append(dict(channel=channel,pad_id=pad,points_um=spath));returns.append(dict(channel=channel,net='GND',points_um=gpath))
    left=-c['ground_pad_x_margin'];right=end+c['ground_pad_x_margin'];levels=c['ground_column_y']
    bus=[[left,levels[0]]]
    for layer in range(1,4):
        x=layer*L-c['ground_step_before_column'];bus.extend([[x,levels[layer-1]],[x,levels[layer]]])
    bus.append([right,levels[-1]]);line(elements,bus,c['wire_width'])
    for tag,x,y in [('W',left,levels[0]),('E',right,levels[-1])]:
        line(elements,[[x,y],[x,c['pad_top_y']]],c['wire_width']);s=c['pad_size'];elements.append(rectangle(pdk.L_PAD,x-s/2,c['pad_top_y']-s/2,x+s/2,c['pad_top_y']+s/2))
        pads.append(dict(pad_id='PAD_GND_'+tag,net='GND',center_um=[x,c['pad_top_y']],size_um=s,side='top',driver_channel='DRV_RETURN'))
    label=PPLayer(pdk.pdk.TECH.PROCESS.NONE,pdk.pdk.TECH.PURPOSE.LABEL)
    for p in pads:
        x,y=p['center_um'];elements.append(i3.Label(layer=label,text=p['pad_id']+' '+p['net'],coordinate=(x,y+(60 if y>0 else -60)),height=15.,alignment=(i3.TEXT.ALIGN.CENTER,i3.TEXT.ALIGN.MIDDLE)))
    bounds=[west,c['chip_bottom_y'],east,c['chip_top_y']];elements.append(rectangle(pdk.L_OUTLINE,*bounds))
    cell=i3.LayoutCell(name='LAB06B_CHIP_INTERFACES');cell.Layout(elements=refs+elements)
    return cell,dict(chip_bounds_um=bounds,chip_size_um=[east-west,c['chip_top_y']-c['chip_bottom_y']],
        core_bounds_reference='unchanged accepted M2 S4 core',pads=pads,optical_io=sorted(optical,key=lambda p:(p['direction']!='in',p['mode'])),
        optical_routes=routes,signal_routes=signals,return_routes=returns,ground_bus=bus,ground_column_y=levels,
        counts=dict(EC=10,signal_pads=14,ground_pads=2,physical_pads=16,logical_return_nets=1),
        EC=c['EC'],fiber_pitch_um=c['fiber_pitch'],wire_width_um=c['wire_width'],core_phase_regions=core['phase_regions'])
