"""M2 S3 physical B7 layout; PDK MMI coordinates are queried at runtime.

Port order matches pdk_circuit (local in0/out0 upper). Heater shapes are
custom geometry adapted from the M0 toolchain test, not calibrated devices.
Waveguide lengths exclude the multimode bodies; no beta*L replay implied.
"""
import math
import numpy as np
from cornerstone.technology import select_technology_variant,CornerstoneVariant
select_technology_variant(CornerstoneVariant.SOI220)
from ipkiss3 import all as i3
from . import pdk

UNIT_NAME='LAB06B_MZI_CORE';CORE_NAME='LAB06B_B7_CORE'

def validate(c,spec_sha):
    if c.get('schema')!='lab06b.m2_core_layout.v1' or c.get('units')!='um' or c.get('m1_spec_sha256')!=spec_sha:
        raise ValueError('Layout schema, units or bound M1 specification invalid')
    keys=['pitch','s_bend_length','s_bend_stub','phase_region_length','heater_length','heater_width','landing_width','metal_overlap','lead_length']
    if any(not isinstance(c.get(k),(int,float)) or isinstance(c[k],bool) or not math.isfinite(c[k]) or c[k]<=0 for k in keys):
        raise ValueError('Layout dimensions must be finite and positive')
    n=c.get('s_bend_samples')
    if not isinstance(n,int) or isinstance(n,bool) or n<21 or n%2==0:raise ValueError('S-bend requires an odd sample count >=21')
    if c['s_bend_length']<=2*c['s_bend_stub']:raise ValueError('S-bend horizontal span must exceed two stubs')
    if not math.isclose(c['phase_region_length'],c['heater_length']+2*(c['landing_width']+c['metal_overlap']),abs_tol=1e-9):
        raise ValueError('Phase straight must reserve heater plus both landing/overlap lengths')
    if c['heater_width']<pdk.RULES['HT_min_width'] or c['pitch']-(c['landing_width']+2*c['metal_overlap'])<pdk.RULES['PAD_min_gap']:
        raise ValueError('Heater width or adjacent local contact spacing below planning limits')
    f=c.get('core_frame')
    if not isinstance(f,list) or len(f)!=4 or not all(isinstance(v,(float,int)) and math.isfinite(v) for v in f) or f[2]<=f[0] or f[3]<=f[1]:
        raise ValueError('Declare core frame as [xmin,ymin,xmax,ymax]')
    return c

def snap(points):return [(round(float(x),3),round(float(y),3)) for x,y in points]
def length(points):return sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(points,points[1:]))
def join(*paths):
    out=[]
    for path in paths:
        for point in path:
            if not out or math.dist(out[-1],point)>1e-9:out.append(point)
    return out
def sbend(x,y0,y1,c):
    stub=c['s_bend_stub'];span=c['s_bend_length']-2*stub
    return snap([(x,y0)]+[(x+stub+span*t,y0+(y1-y0)*(1-math.cos(math.pi*t))/2) for t in np.linspace(0,1,c['s_bend_samples'])]+[(x+c['s_bend_length'],y1)])
def rectangle(layer,x0,y0,x1,y1):
    return i3.Rectangle(layer=layer,center=((x0+x1)/2,(y0+y1)/2),box_size=(abs(x1-x0),abs(y1-y0)))
def waveguide(points,name):
    w=i3.Waveguide(name=name,trace_template=pdk.wg_template());w.Layout(shape=snap(points));return w

def mzi(c):
    mmi=pdk.mmi2x2();mp={p.name:[float(p.position.x),float(p.position.y)] for p in mmi.Layout().ports}
    if not (mp['in2'][1]>mp['in1'][1] and mp['out2'][1]>mp['out1'][1]):raise ValueError('PDK upper/lower order changed')
    upper,lower,middle=0.,-c['pitch'],-c['pitch']/2
    phase=c['phase_region_length'];x=phase
    up=[(0.,upper),(x,upper)];lo=[(0.,lower),(x,lower)]
    segments=[];refs=[];positions=[];joints=[];phase_starts=[0.]
    for k in range(2):
        up=join(up,sbend(x,upper,middle+mp['in2'][1],c));lo=join(lo,sbend(x,lower,middle+mp['in1'][1],c))
        segments.extend([up,lo]);x+=c['s_bend_length'];origin=round(x-mp['in2'][0],3)
        positions.append([origin,middle]);refs.append(i3.SRef(reference=mmi,position=(origin,middle),name=f'MMI{k+1}'))
        x=round(origin+mp['out2'][0],3)
        up=sbend(x,middle+mp['out2'][1],upper,c);lo=sbend(x,middle+mp['out1'][1],lower,c)
        x+=c['s_bend_length']
        if k==0:
            phase_starts.append(x);up=join(up,[(x,upper),(x+phase,upper)]);lo=join(lo,[(x,lower),(x+phase,lower)]);x+=phase
    segments.extend([up,lo]);x=round(x,3)
    for k,points in enumerate(segments):refs.append(i3.SRef(reference=waveguide(points,f'MZI_WG{k}'),name=f'WG{k}'))
    error=0.
    for k,(mx,my) in enumerate(positions):
        for offset,ip,op in [(0,'in2','out2'),(1,'in1','out1')]:
            for actual,target,tag in [(segments[2*k+offset][-1],[mx+mp[ip][0],my+mp[ip][1]],ip),
                                      (segments[2*(k+1)+offset][0],[mx+mp[op][0],my+mp[op][1]],op)]:
                error=max(error,math.dist(actual,target));joints.append(dict(id=f'MMI{k+1}:{tag}',position_um=list(actual)))
    elements=[];controls=[]
    for phase_name,start in zip(['phi','theta'],phase_starts):
        land=c['landing_width'];overlap=c['metal_overlap'];h0=start+land+overlap;h1=h0+c['heater_length'];w=c['heater_width']
        elements.append(rectangle(pdk.L_HT,h0-land,-w/2,h1+land,w/2));terminals=[]
        for xe,sign,terminal in [(h0,-1,'A'),(h1,1,'B')]:
            elements.append(rectangle(pdk.L_HT,xe,-land/2,xe+sign*land,land/2))
            elements.append(rectangle(pdk.L_PAD,xe,-land/2-overlap,xe+sign*(land+overlap),land/2+overlap))
            terminals.append(dict(terminal=terminal,center_um=[xe+sign*(land+overlap)/2,0.]))
        controls.append(dict(parameter=phase_name,straight_start_um=start,straight_end_um=start+phase,
            heated_start_um=h0,heated_end_um=h1,center_um=[(h0+h1)/2,0.],local_contacts=terminals))
        elements.append(i3.PolygonText(layer=pdk.L_LABEL,text=phase_name,coordinate=(start+35,8),height=4.))
    ports=[i3.OpticalPort(name=n,position=(px,py),angle=a,trace_template=pdk.wg_template()) for n,px,py,a in [
        ('in0',0,upper,180),('in1',0,lower,180),('out0',x,upper,0),('out1',x,lower,0)]]
    cell=i3.LayoutCell(name=UNIT_NAME);cell.Layout(elements=elements+refs,ports=ports)
    dy=abs(upper-(middle+mp['in2'][1]));radius=2*(c['s_bend_length']-2*c['s_bend_stub'])**2/(math.pi**2*dy)
    if radius<pdk.RULES['bend_min_radius']:raise ValueError('Continuous S-bend radius below planning limit')
    return cell,dict(length_um=x,pitch_um=c['pitch'],mmi_ports=mp,mmi_positions_um=positions,
        mmi_longitudinal_span_um=mp['out2'][0]-mp['in2'][0],segments=[dict(id=f'WG{k}',arm='upper' if k%2==0 else 'lower',
            stage=['input_phi','inter_mmi_theta','output'][k//2],points_um=p,length_um=length(p)) for k,p in enumerate(segments)],
        waveguide_upper_um=sum(length(p) for p in segments[::2]),waveguide_lower_um=sum(length(p) for p in segments[1::2]),
        inter_mmi_upper_um=length(segments[2]),inter_mmi_lower_um=length(segments[3]),
        continuous_s_bend_min_radius_um=radius,max_join_error_um=error,joints=joints,controls=controls)

def build(top,c):
    unit,u=mzi(c);L=u['length_um'];pitch=c['pitch'];lead=c['lead_length'];end=4*L
    refs=[];placement=[];controls=[];paths=[];joints=[];elements=[]
    for k,(p,layer) in enumerate(top.ops,1):
        ox,oy=layer*L,-p*pitch
        refs.append(i3.SRef(reference=unit,position=(ox,oy),name=f'M{k}'))
        placement.append(dict(id=f'M{k}',layer=layer,modes=[p,p+1],origin_um=[ox,oy],bbox_um=[ox,oy-pitch,ox+L,oy]))
        for j in u['joints']:joints.append(dict(id=f'M{k}:'+j['id'],position_um=[j['position_um'][0]+ox,j['position_um'][1]+oy]))
        for ctl in u['controls']:
            channel=ctl['parameter']+str(k);heater=f'H_M{k}_{ctl["parameter"]}'
            controls.append(dict(channel=channel,instance=f'M{k}',parameter=ctl['parameter'],heater_logical_id=heater,
                center_um=[ctl['center_um'][0]+ox,oy],heated_start_um=[ctl['heated_start_um']+ox,oy],
                heated_end_um=[ctl['heated_end_um']+ox,oy],local_contacts=[dict(endpoint=heater+'.'+t['terminal'],
                    center_um=[t['center_um'][0]+ox,oy]) for t in ctl['local_contacts']],pad_id=None,voltage_calibration=None))
        for seg in u['segments']:paths.append(dict(id=f'M{k}:'+seg['id'],kind='MZI_waveguide',instance=f'M{k}',stage=seg['stage'],arm=seg['arm'],
            points_um=[[x+ox,y+oy] for x,y in seg['points_um']],length_um=seg['length_um']))
        elements.append(i3.PolygonText(layer=pdk.L_LABEL,text=f'M{k}',coordinate=(ox+L/2,oy-17),height=5.))
    for layer in range(4):
        busy={q for p,l in top.ops if l==layer for q in (p,p+1)}
        for rail in sorted(set(range(5))-busy):
            name=f'WG_BYP_L{layer}_R{rail}';points=[(layer*L,-rail*pitch),((layer+1)*L,-rail*pitch)]
            refs.append(i3.SRef(reference=waveguide(points,name),name=name))
            paths.append(dict(id=name,kind='bypass',layer=layer,mode=rail,points_um=points,length_um=L))
    ports=[]
    for rail in range(5):
        y=-rail*pitch
        for direction,a,b,px,angle in [('in',-lead,0.,-lead,180),('out',end,end+lead,end+lead,0)]:
            name=f'WG_{direction}{rail}';points=[(a,y),(b,y)]
            refs.append(i3.SRef(reference=waveguide(points,name),name=name))
            paths.append(dict(id=name,kind='lead',mode=rail,points_um=points,length_um=lead))
            ports.append(dict(id=f'{direction}{rail}',mode=rail,direction=direction,position_um=[px,y],angle_deg=angle,
                core_role=['x1','x2','x3','x4','R'][rail] if direction=='in' else {1:'PD_PLUS',3:'PD_MINUS'}.get(rail,'external_load'),
                physical_coupler=None))
            joints.append(dict(id=f'lead_{direction}{rail}',position_um=[b if direction=='in' else a,y]))
    for boundary in range(1,4):
        for rail in range(5):joints.append(dict(id=f'column{boundary}_rail{rail}',position_um=[boundary*L,-rail*pitch]))
    for p in ports:elements.append(i3.PolygonText(layer=pdk.L_LABEL,text=p['id'],coordinate=(p['position_um'][0]+(3 if p['direction']=='in' else -20),p['position_um'][1]+3),height=4.))
    elements.append(rectangle(pdk.L_OUTLINE,*c['core_frame']))
    core=i3.LayoutCell(name=CORE_NAME)
    core.Layout(elements=refs+elements,ports=[i3.OpticalPort(name=p['id'],position=tuple(p['position_um']),angle=p['angle_deg'],trace_template=pdk.wg_template()) for p in ports])
    preview=i3.LayoutCell(name='LAB06B_MZI_PREVIEW');preview.Layout(elements=[i3.SRef(reference=unit),rectangle(pdk.L_OUTLINE,-10,-45,L+10,20)],ports=unit.get_default_view(i3.LayoutView).ports)
    return core,preview,dict(unit=u,placement=placement,phase_regions=controls,paths=paths,joints=joints,
        ports=sorted(ports,key=lambda p:(p['direction']!='in',p['mode'])),core_optical_span_um=[end+2*lead,4*pitch],
        core_frame_um=c['core_frame'],core_frame_size_um=[c['core_frame'][2]-c['core_frame'][0],c['core_frame'][3]-c['core_frame'][1]],
        core_end_x_um=end,column_length_um=L,counts=dict(mzi=7,pdk_mmi=14,heater=14,local_metal_contacts=28,bypass=6,leads=10,optical_ports=10))
