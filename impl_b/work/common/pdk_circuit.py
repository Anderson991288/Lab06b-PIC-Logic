"""M2 S2 logical Caphe circuit: actual PDK MMIs, ideal phase cells/links.

No layout, propagation lengths, heater calibration, EC or process corners.
Local port 0 is upper (PDK in2/out2), local port 1 is lower (in1/out1).
"""
from cornerstone.technology import select_technology_variant, CornerstoneVariant
select_technology_variant(CornerstoneVariant.SOI220)
import cornerstone.all as cs
from ipkiss3 import all as i3
import numpy as np

MMI_CELL='SOI220nm_1550nm_TE_STRIP_2x2_MMI'

class PhaseModel(i3.CompactModel):
    parameters=['phase']
    terms=[i3.OpticalTerm(name='in'),i3.OpticalTerm(name='out')]
    def calculate_smatrix(parameters,env,S):
        value=np.exp(1j*parameters.phase)
        S['out','in']=value
        S['in','out']=value

class IdealPhase(i3.PCell):
    phase=i3.NumberProperty(default=0.)
    class Netlist(i3.NetlistView):
        def _generate_terms(self,terms):
            terms+=i3.OpticalTerm(name='in')
            terms+=i3.OpticalTerm(name='out')
            return terms
    class CircuitModel(i3.CircuitModelView):
        def _generate_model(self):return PhaseModel(phase=self.cell.phase)

def mzi(theta,phi,wrong_phi=False):
    """phi precedes MMI1 on upper input; theta between MMIs on upper arm."""
    upper,lower=('in1','in2') if wrong_phi else ('in2','in1')
    return i3.ConnectComponents(child_cells={
        'mmi1':getattr(cs,MMI_CELL)(),'mmi2':getattr(cs,MMI_CELL)(),
        'theta':IdealPhase(phase=float(theta)),'phi':IdealPhase(phase=float(phi))},
        links=[('phi:out','mmi1:'+upper),('mmi1:out2','theta:in'),
               ('theta:out','mmi2:in2'),('mmi1:out1','mmi2:in1')],
        external_port_names={'phi:in':'in0','mmi1:'+lower:'in1',
                             'mmi2:out2':'out0','mmi2:out1':'out1'})

def wiring(topology):
    fronts=[f'B7:in{k}' for k in range(5)];edges=[]
    for k,(p,layer) in enumerate(topology.ops,1):
        for local,q in enumerate((p,p+1)):
            edges.append(dict(source=fronts[q],destination=f'M{k}:in{local}',mode=q))
            fronts[q]=f'M{k}:out{local}'
    edges.extend(dict(source=s,destination=f'B7:out{q}',mode=q) for q,s in enumerate(fronts))
    links=[];external={}
    for e in edges:
        a,b=e['source'],e['destination']
        if a.startswith('B7:'):external[b]=a.split(':')[1]
        elif b.startswith('B7:'):external[a]=b.split(':')[1]
        else:links.append((a,b))
    return dict(edges=edges,links=links,external_port_names=external,
                mzi_count=7,pdk_mmi_instances=14,ideal_phase_instances=14,
                bypass_by_layer=[sorted(set(range(5))-{q for p,l in topology.ops if l==layer for q in (p,p+1)}) for layer in range(4)])

def circuit(topology,theta,phi,wrong_phi=False):
    theta=np.asarray(theta,dtype=float);phi=np.asarray(phi,dtype=float)
    if theta.shape!=(7,) or phi.shape!=(7,) or not np.isfinite([theta,phi]).all():
        raise ValueError('Fourteen finite radian values required')
    net=wiring(topology)
    return i3.ConnectComponents(child_cells={f'M{k+1}':mzi(theta[k],phi[k],wrong_phi) for k in range(7)},
        links=net['links'],external_port_names=net['external_port_names'])

def smatrix(cell,inputs,outputs,wavelength_um=1.55):
    S=cell.CircuitModel().get_smatrix(wavelengths=np.array([wavelength_um]),validate_netlist=True)
    return np.array([[S[o,i][0] for i in inputs] for o in outputs],dtype=complex)

def b7_smatrix(topology,theta,phi,wrong_phi=False):
    ports=[f'in{k}' for k in range(5)]+[f'out{k}' for k in range(5)]
    return smatrix(circuit(topology,theta,phi,wrong_phi),ports,ports)
