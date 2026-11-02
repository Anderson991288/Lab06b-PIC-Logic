"""Core-plane length replay and analytic phase-gauge compensation.

Uses exp(+i beta L), real scalar neff and uniform illustrative loss.
Retains H's full complex phase. No MMI-length propagation, EC or bias model.
"""
import math
import numpy as np
from . import handoff,mzi,logic_validation as logic,encoding,linear_network as network

def validate_model(c):
    if c.get('schema')!='lab06b.backannotation.v1' or c.get('reference_plane')!='M1_core_ports':raise ValueError('Unsupported model/reference plane')
    for key in ['neff','wavelength_um']:
        if isinstance(c.get(key),bool) or not isinstance(c.get(key),(int,float)) or not math.isfinite(c[key]) or c[key]<=0:raise ValueError('Positive finite '+key+' required')
    if c.get('physical_function_qualified') is not False:raise ValueError('Unqualified teaching model must remain explicit')
    return c

def index_paths(data):
    rows=data['paths'];by={p['id']:p for p in rows}
    if len(by)!=len(rows) or len(rows)!=68:raise ValueError('68 unique paths required')
    expected={f'M{k}:WG{j}' for k in range(1,8) for j in range(6)}|{f'WG_{d}{k}' for d in ['in','out'] for k in range(5)}|{f'FAN_{d}{k}' for d in ['in','out'] for k in range(5)}|{f'WG_BYP_L{l}_R{r}' for l,rs in enumerate([[2],[0,3,4],[4],[0]]) for r in rs}
    if set(by)!=expected:raise ValueError('Path names/topology incomplete')
    if any(not math.isfinite(p['length_um']) or p['length_um']<=0 for p in rows):raise ValueError('Positive finite lengths required')
    return by

def beta(model):validate_model(model);return 2*np.pi*model['neff']/model['wavelength_um']
def factor(length,model,loss_db_per_cm=0.):
    if not math.isfinite(loss_db_per_cm) or loss_db_per_cm<0:raise ValueError('Passive loss must be finite/nonnegative')
    loss_db=loss_db_per_cm*length/10000.
    return 10**(-loss_db/20)*np.exp(1j*beta(model)*length)

def transfer(spec,paths,model,setting,loss_db_per_cm=0.,propagate=True):
    top=handoff.validate_spec(spec);by=index_paths(paths)
    def g(name):return factor(by[name]['length_um'],model,loss_db_per_cm) if propagate else 1.+0j
    U=np.diag([g('WG_in'+str(k)) for k in range(5)])
    for layer in range(4):
        A=np.eye(5,dtype=complex);busy=set()
        for k,(p,l) in enumerate(top.ops):
            if l!=layer:continue
            name=f'M{k+1}:';pre=np.diag([g(name+'WG0'),g(name+'WG1')]);inter=np.diag([g(name+'WG2'),g(name+'WG3')]);post=np.diag([g(name+'WG4'),g(name+'WG5')])
            T=post@mzi.H@inter@mzi.phase_shift(setting['theta'][k])@mzi.H@pre@mzi.phase_shift(setting['phi'][k])
            A[p:p+2,p:p+2]=T;busy.update([p,p+1])
        for rail in set(range(5))-busy:A[rail,rail]=g(f'WG_BYP_L{layer}_R{rail}')
        U=A@U
    return np.diag([g('WG_out'+str(k)) for k in range(5)])@U

def compensation(spec,paths,model):
    top=handoff.validate_spec(spec);by=index_paths(paths);b=beta(model)
    phase=np.array([b*by['WG_in'+str(k)]['length_um'] for k in range(5)])
    theta=[0.]*7;phi=[0.]*7;trace=[]
    for layer in range(4):
        incoming=phase.copy();busy=set()
        for k,(p,l) in enumerate(top.ops):
            if l!=layer:continue
            lengths=[by[f'M{k+1}:WG{j}']['length_um'] for j in range(6)]
            phi[k]=-(incoming[p]-incoming[p+1])-b*(lengths[0]-lengths[1])
            theta[k]=-b*(lengths[2]-lengths[3])
            common=incoming[p+1]+b*(lengths[1]+lengths[3])
            phase[p]=common+b*lengths[4];phase[p+1]=common+b*lengths[5];busy.update([p,p+1])
            trace.append(dict(instance=f'M{k+1}',layer=layer,input_phase_rad=incoming[p:p+2].tolist(),theta_offset_rad=theta[k],phi_offset_rad=phi[k],output_phase_rad=phase[p:p+2].tolist()))
        for rail in set(range(5))-busy:phase[rail]=incoming[rail]+b*by[f'WG_BYP_L{layer}_R{rail}']['length_um']
    phase+=np.array([b*by['WG_out'+str(k)]['length_um'] for k in range(5)])
    return dict(theta_offsets=theta,phi_offsets=phi,output_phase_rad=phase.tolist(),trace=trace,
        rule='phi cancels input relative phase; theta cancels inter-arm relative phase; residual output diagonal phases retain powers',drive_voltage_calibrated=False)

def candidate(catalog,offsets):
    return {gate:{'theta':[(x+y)%(2*np.pi) for x,y in zip(s['theta'],offsets['theta_offsets'])],
                  'phi':[(x+y)%(2*np.pi) for x,y in zip(s['phi'],offsets['phi_offsets'])]} for gate,s in catalog.items()}

def evaluate(spec,paths,model,catalog,loss_db_per_cm=0.,propagate=True):
    result={};eps=spec['readout']['epsilon'];threshold=spec['readout']['threshold']
    for gate in logic.GATES:
        U=transfer(spec,paths,model,catalog[gate],loss_db_per_cm,propagate);rows=[]
        for idx,bits in enumerate(logic.patterns()):
            v=encoding.with_reference(bits,spec['encoding']['reference_amplitude'],spec['encoding']['reference_phase_rad']);out=U@v
            read=network.power_difference_readout(out,1,3,threshold,eps);truth=logic.truth(gate,bits);signed=(2*truth-1)*read['margin']
            rows.append(dict(gate=gate,index_lsb_x1=idx,pattern=''.join(map(str,bits)),expected=truth,bit=read['bit'],delta=read['delta'],signed_margin=float(signed),
                passed=bool(read['bit']==truth and signed>eps),powers=(np.abs(out)**2).tolist(),input_power=float(np.vdot(v,v).real),output_power=float(np.vdot(out,out).real)))
        result[gate]=dict(U=U,rows=rows,passed=sum(r['passed'] for r in rows),minimum_signed_margin=min(r['signed_margin'] for r in rows))
    return result
