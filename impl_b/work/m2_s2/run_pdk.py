"""Execute CORNERSTONE/IPKISS Caphe; export all 80 comparisons, no fitting."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import os,sys,json,csv,hashlib,inspect,unittest,io,importlib.util
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;OUT=HERE/'out'
OUT.mkdir(exist_ok=True)
for key in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:os.environ[key]='1'
sys.path.insert(0,str(ROOT/'work'))
from common import pdk_circuit as pc,handoff,b7,mzi,logic_validation as logic,encoding,linear_network as ln
import cornerstone,ipkiss,numpy as np

def save(name,v):(OUT/name).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def pairs(a):return np.stack([a.real,a.imag],axis=-1).tolist()
def maximum(a):return float(np.max(np.abs(a)))
def suite(path,cls,log):
    s=importlib.util.spec_from_file_location(cls,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
    stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(getattr(m,cls)))
    (OUT/log).write_text(stream.getvalue(),encoding='utf-8')
    return dict(run=r.testsRun,passed=r.testsRun-len(r.failures)-len(r.errors),successful=r.wasSuccessful())

spec,settings=handoff.load_bundle(ROOT/'delivery/m1_handoff')
assert handoff.digest(ROOT/'pic_spec.json')==handoff.digest(ROOT/'delivery/m1_handoff/pic_spec.json')
assert handoff.digest(ROOT/'phase_settings.json')==handoff.digest(ROOT/'delivery/m1_handoff/phase_settings.json')
top=handoff.validate_spec(spec);catalog=handoff.phase_catalog(spec,settings);baseline=handoff.replay(spec,settings)
wave=spec['design_point']['wavelength_um'];eps=spec['readout']['epsilon'];threshold=spec['readout']['threshold']
mmi=getattr(pc.cs,pc.MMI_CELL)();cm=mmi.CircuitModel();model=cm._generate_model()
H=pc.smatrix(mmi,['in2','in1'],['out2','out1'],wave)
model_file=Path(inspect.getfile(type(model)));cell_file=Path(inspect.getfile(type(mmi)))
parameters={k:pairs(np.asarray(getattr(model,k),dtype=complex)) for k in model.parameters}
audit=dict(pdk_version=cornerstone.__version__,ipkiss_version=ipkiss.__version__,python=sys.executable,
    pdk_module=str(Path(cornerstone.__file__).resolve()),cell=pc.MMI_CELL,
    compact_model=type(model).__module__+'.'+type(model).__name__,parameters=parameters,
    source_files=[dict(path=str(p),sha256=handoff.digest(p)) for p in [cell_file,model_file]],
    ports=[dict(name=p.name,x_um=float(p.position[0]),y_um=float(p.position[1])) for p in mmi.Layout().ports],
    forward_upper_lower=pairs(H),max_abs_H_error=maximum(H-np.array([[1,1j],[1j,1]])/np.sqrt(2)),
    interpretation='Installed PDK inherits default ideal Coupler2x2Model. Agreement validates circuit semantics, not measured loss, fabrication tolerance, bandwidth or thermal calibration.')
save('pdk_model_audit.json',audit);save('netlist.json',pc.wiring(top))
single=[]
for theta,phi in [(0.,0.),(np.pi,0.),(.73,1.21),(2.4,-.61)]:
    T=pc.smatrix(pc.mzi(theta,phi),['in0','in1'],['out0','out1'],wave)
    single.append(dict(theta=float(theta),phi=float(phi),max_abs_error=maximum(T-mzi.T2(theta,phi)),matrix=pairs(T)))
save('single_mzi_checks.json',single)
rows=[];functions=[];matrices={};details={};smatrices={}
for gate in logic.GATES:
    setting=catalog[gate];S=pc.b7_smatrix(top,setting['theta'],setting['phi']);U=S[5:,:5];ideal=baseline[gate]['U']
    stats=dict(gate=gate,max_abs_U_error=maximum(U-ideal),
        max_reflection_block=maximum(S[:5,:5]),max_output_reflection_block=maximum(S[5:,5:]),
        max_reciprocity_error=maximum(S-S.T),max_unitarity_error=maximum(S.conj().T@S-np.eye(10)))
    local=[];detail=[]
    for old in baseline[gate]['rows']:
        bits=old['bits'];field=encoding.with_reference(bits,spec['encoding']['reference_amplitude'],spec['encoding']['reference_phase_rad'])
        out=U@field;power=np.abs(out)**2;read=ln.power_difference_readout(out,1,3,threshold,eps)
        truth=logic.truth(gate,bits);signed=(2*truth-1)*read['margin']
        row=dict(gate=gate,index_lsb_x1=old['index_lsb_x1'],pattern=old['pattern'],expected=truth,
            ideal_bit=old['bit'],pdk_bit=read['bit'],ideal_delta=old['delta'],pdk_delta=read['delta'],
            delta_error=read['delta']-old['delta'],signed_margin=float(signed),
            passed=bool(read['bit']==truth and signed>eps),max_abs_field_error=maximum(out-old['field']),
            max_abs_power_error=maximum(power-old['powers']),
            input_total_power=float(np.vdot(field,field).real),pdk_total_power=float(power.sum()))
        for k in range(5):row[f'ideal_P{k}']=float(old['powers'][k]);row[f'pdk_P{k}']=float(power[k])
        rows.append(row);local.append(row);detail.append(dict(**row,input_field=pairs(field),ideal_field=pairs(old['field']),pdk_field=pairs(out)))
    stats.update(passed=sum(r['passed'] for r in local),total=16,minimum_signed_margin=min(r['signed_margin'] for r in local),
        worst_pattern=min(local,key=lambda r:r['signed_margin'])['pattern'],max_abs_delta_error=max(abs(r['delta_error']) for r in local))
    functions.append(stats);matrices[gate]=dict(ideal=pairs(ideal),pdk=pairs(U));details[gate]=detail;smatrices[gate]=pairs(S)
    print(gate,stats['passed'],'/16; max |U_PDK-U_ideal| =',stats['max_abs_U_error'],flush=True)
save('comparison.json',details);save('matrices.json',matrices);save('smatrices.json',dict(port_order=[f'in{k}' for k in range(5)]+[f'out{k}' for k in range(5)],data=smatrices))
with (OUT/'comparison_80.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
with (OUT/'comparison_80.csv').open(encoding='utf-8-sig',newline='') as f:csv_rows=list(csv.DictReader(f))
csv_ok=len(csv_rows)==80 and all(float(a['pdk_delta'])==b['pdk_delta'] and a['pattern']==b['pattern'] for a,b in zip(csv_rows,rows))

# Controlled variants never touch the canonical phase files.
g='XOR2';s=catalog[g];U=baseline[g]['U'];bad=[]
for name,actual in [('phi_on_wrong_input',pc.b7_smatrix(top,s['theta'],s['phi'],wrong_phi=True)[5:,:5]),
                    ('theta_phi_vector_swapped',pc.b7_smatrix(top,s['phi'],s['theta'])[5:,:5]),
                    ('theta_sign_reversed',pc.b7_smatrix(top,[-x for x in s['theta']],s['phi'])[5:,:5])]:
    error=maximum(actual-U);bad.append(dict(name=name,gate=g,max_abs_U_error=error,detected=error>1e-8,engine='Caphe'))
without_global=np.eye(5,dtype=complex)
for k,(p,l) in enumerate(top.ops):
    local=mzi.T2(s['theta'][k],s['phi'][k])/(1j*np.exp(.5j*s['theta'][k]))
    block=np.eye(5,dtype=complex);block[p:p+2,p:p+2]=local;without_global=block@without_global
bad.append(dict(name='discard_each_MZI_global_phase',gate=g,max_abs_U_error=maximum(without_global-U),detected=maximum(without_global-U)>1e-8,engine='NumPy controlled variant'))
flipped=sum((-r['pdk_delta']>0)==r['expected'] for r in rows)
bad.append(dict(name='receiver_polarity_reversed',failed=80-flipped,detected=flipped<80,engine='CSV receiver variant'))
save('controlled_errors.json',bad)
tests=suite(HERE/'test_pdk_circuit.py','PdkCircuitTests','unit_tests.log')
regression={name:suite(ROOT/path,cls,name.lower()+'_regression.log') for name,path,cls in [
    ('M0_S3','work/m0_s3/test_optical_models.py','OpticalModels'),('M1_S1','work/m1_s1/test_encoding_readout.py','EncodingReadout'),
    ('M1_S2','work/m1_s2/test_b7.py','B7Tests'),('M1_S3','work/m1_s3/test_weighted_readout.py','WeightedReadoutTests'),
    ('M1_S4','work/m1_s4/test_logic_validation.py','LogicValidationTests'),('M1_S5','work/m1_s5/test_handoff.py','HandoffTests'),
    ('M2_S1','work/m2_s1/test_boundary.py','BoundaryTests')]}
previous=json.loads((ROOT/'work/m1_s5/out/handoff_results.json').read_text(encoding='utf-8'))
unchanged=all(handoff.digest(ROOT/p)==h for p,h in previous['source_hashes'].items()) and handoff.digest(ROOT/previous['zip'])==previous['zip_sha256']
max_u=max(s['max_abs_U_error'] for s in functions);max_delta=max(abs(r['delta_error']) for r in rows)
checks=[('PDK_cell_and_upper_port',next(p['y_um'] for p in audit['ports'] if p['name']=='in2')>next(p['y_um'] for p in audit['ports'] if p['name']=='in1')),
    ('MMI_default_H',audit['max_abs_H_error']<1e-10),('four_single_MZIs',max(s['max_abs_error'] for s in single)<1e-10),
    ('five_complex_matrices',max_u<1e-10),('eighty_truths',sum(r['passed'] for r in rows)==80),
    ('power_differences',max_delta<1e-10),('power_conservation',max(abs(r['pdk_total_power']-r['input_total_power']) for r in rows)<1e-10),
    ('full_reflection_blocks',max(max(s['max_reflection_block'],s['max_output_reflection_block']) for s in functions)<1e-10),
    ('reciprocal_and_unitary',max(max(s['max_reciprocity_error'],s['max_unitarity_error']) for s in functions)<1e-10),
    ('all_eighty_unique',len({(r['gate'],r['pattern']) for r in rows})==80),('CSV_round_trip',csv_ok),
    ('five_controlled_errors_detected',all(r['detected'] for r in bad)),('M1_sources_and_zip_unchanged',unchanged)]
source_paths=['pic_spec.json','phase_settings.json','work/common/pdk_circuit.py','work/m2_s2/run_pdk.py','work/m2_s2/test_pdk_circuit.py']
result=dict(step='M2 S2',timestamp=datetime.now(timezone(timedelta(hours=8))).isoformat(),root=str(ROOT),
    engine='IPKISS CircuitModel / Caphe get_smatrix(validate_netlist=True)',wavelength_um=wave,
    passed=sum(r['passed'] for r in rows),total=80,functions=functions,max_abs_U_error=max_u,max_abs_delta_error=max_delta,
    unit_tests=tests,regression=regression,checks=[dict(name=n,passed=bool(v)) for n,v in checks],
    pdk_audit=audit,controlled_errors=bad,M1_sources_and_zip_unchanged=unchanged,
    source_hashes={p:handoff.digest(ROOT/p) for p in source_paths},
    scope='14 actual CORNERSTONE MMI instances, 14 custom ideal phase cells, zero-length ideal links; default ideal MMI model. No layout propagation, EC, electrical heater calibration, fabrication tolerances, bandwidth or DRC verification.',
    core_passed=tests['successful'] and all(r['successful'] for r in regression.values()) and all(v for n,v in checks))
save('pdk_results.json',result)
print('M2 S2:',result['passed'],'/80; tests',tests,'; regressions',sum(r['passed'] for r in regression.values()),flush=True)
print('CORE',result['core_passed'],flush=True)
raise SystemExit(0 if result['core_passed'] else 1)
