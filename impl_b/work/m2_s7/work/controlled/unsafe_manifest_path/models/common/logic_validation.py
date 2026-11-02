"""Fixed-encoding B7 truth acceptance; no phase optimization or file I/O.

Five functions each see ALL 16 four-bit patterns, x1 is the low index bit.
Signed margin=(2*truth-1)*(delta-threshold); epsilon boundaries never pass.
Unused x3/x4 remain physical illuminated inputs for two-input functions.
"""
import numpy as np
from . import b7,encoding,linear_network as net
GATES=('AND2','OR2','XOR2','AND4','OR4')


def patterns():return [tuple((index>>j)&1 for j in range(4)) for index in range(16)]


def truth(gate,bits):
    a=np.asarray(bits)
    if a.shape!=(4,) or not np.isin(a,[0,1]).all():raise ValueError('Provide four binary data bits')
    a,b,c,d=map(int,a)
    if gate=='AND2':return a & b
    if gate=='OR2':return a | b
    if gate=='XOR2':return a ^ b
    if gate=='AND4':return a & b & c & d
    if gate=='OR4':return a | b | c | d
    raise ValueError('Unknown logic function')


def validate_programs(catalog,topology):
    if catalog.get('phase_unit')!='rad' or catalog.get('phase_order')!=[f'M{k}' for k in range(1,8)]:
        raise ValueError('Phase unit/order must be rad and M1..M7')
    if tuple(map(tuple,catalog.get('ops_zero_based',[])))!=topology.ops:raise ValueError('Catalog OPS do not match B7')
    if set(catalog.get('gates',{}))!=set(GATES):raise ValueError('Exactly five phase programs are required')
    for name in GATES:
        setting=catalog['gates'][name]
        for key in ['theta','phi']:
            a=np.asarray(setting[key],dtype=float)
            if a.shape!=(7,) or not np.isfinite(a).all():raise ValueError('Each phase array requires seven finite values')
    return catalog


def summarize(rows,epsilon):
    if not rows:raise ValueError('No rows to summarize')
    epsilon=float(epsilon)
    if not np.isfinite(epsilon) or epsilon<0:raise ValueError('Invalid epsilon')
    margins=[r['signed_margin'] for r in rows]
    confusion=[[0,0],[0,0]];boundaries=0
    for r in rows:
        if r['bit'] is None:boundaries+=1
        else:confusion[r['expected']][r['bit']]+=1
    worst=min(rows,key=lambda r:r['signed_margin'])
    return dict(total=len(rows),passed=sum(r['correct'] for r in rows),boundaries=boundaries,
        minimum_signed_margin=float(min(margins)),minimum_clearance=float(min(margins)-epsilon),
        minimum_abs_delta=float(min(abs(r['delta']) for r in rows)),
        worst_pattern=worst['pattern'],confusion_actual_by_predicted=confusion,
        accepted=all(r['correct'] and r['signed_margin']>epsilon for r in rows))


def evaluate_gate(topology,setting,gate,reference_amplitude=3.,reference_phase=0.,threshold=0.,epsilon=1e-10,
                  readout=None,theta_offsets=None,loss_db=0.):
    if gate not in GATES:raise ValueError('Unknown gate')
    theta=np.asarray(setting['theta'],dtype=float)
    if theta_offsets is not None:
        offsets=np.asarray(theta_offsets,dtype=float)
        if offsets.shape!=(7,) or not np.isfinite(offsets).all():raise ValueError('theta_offsets requires seven finite values')
        theta=theta+offsets
    U=b7.transfer_matrix(topology,theta,setting['phi'],loss_db)
    ports=topology.readout if readout is None else readout
    if len(ports)!=2:raise ValueError('Provide positive and negative readout indices')
    rows=[]
    for index,bits in enumerate(patterns()):
        field=encoding.with_reference(bits,reference_amplitude,reference_phase)
        output=U@field;read=net.power_difference_readout(output,*ports,threshold,epsilon)
        expected=truth(gate,bits);signed=(2*expected-1)*read['margin']
        rows.append(dict(index_lsb_x1=index,bits=list(bits),pattern=''.join(map(str,bits)),expected=expected,
            field=output,powers=np.abs(output)**2,delta=read['delta'],margin=read['margin'],bit=read['bit'],
            signed_margin=float(signed),correct=read['bit']==expected,
            input_total_power=float(np.vdot(field,field).real),output_total_power=float(np.vdot(output,output).real)))
    return dict(U=U,rows=rows,summary=summarize(rows,epsilon))


def unused_input_groups(rows,gate):
    if gate not in GATES[:3]:return []
    groups=[]
    for active in [(0,0),(0,1),(1,0),(1,1)]:
        group=[r for r in rows if tuple(r['bits'][:2])==active]
        combinations={tuple(r['bits'][2:]) for r in group}
        complete=len(group)==4 and combinations=={(0,0),(0,1),(1,0),(1,1)}
        correct=complete and all(r['correct'] and r['bit']==truth(gate,[*active,0,0]) for r in group)
        groups.append(dict(active_bits=list(active),patterns=[r['pattern'] for r in group],
            deltas=[r['delta'] for r in group],bits=[r['bit'] for r in group],
            delta_span=float(max(r['delta'] for r in group)-min(r['delta'] for r in group)) if group else None,
            complete=complete,passed=bool(correct)))
    return groups
