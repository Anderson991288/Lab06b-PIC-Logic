"""Five fixed phase programs: truth acceptance and separate sensitivity labs."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import os,sys,json,csv,hashlib,io,unittest,importlib.util,copy
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
OUT=HERE/'out';FIG=ROOT/'course/figures/m1_s4'
OUT.mkdir(parents=True,exist_ok=True);FIG.mkdir(parents=True,exist_ok=True)
for key in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:os.environ[key]='1'
os.environ['MPLCONFIGDIR']=str(ROOT/'work/.matplotlib')
DLL_HANDLE=None
if os.name=='nt' and (Path(sys.prefix)/'Library/bin').is_dir():DLL_HANDLE=os.add_dll_directory(str(Path(sys.prefix)/'Library/bin'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.family':['Microsoft JhengHei','DejaVu Sans'],'axes.unicode_minus':False})
sys.path[:0]=[str(ROOT/'work'),str(HERE)]
from common import b7,logic_validation as logic


def serial(v):
    if isinstance(v,np.ndarray):return serial(v.tolist())
    if isinstance(v,complex):return [float(v.real),float(v.imag)]
    if isinstance(v,dict):return {k:serial(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [serial(x) for x in v]
    if isinstance(v,np.generic):return v.item()
    return v


def suite(path,cls,logname):
    spec=importlib.util.spec_from_file_location(cls,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(getattr(module,cls)))
    (OUT/logname).write_text(stream.getvalue(),encoding='utf-8')
    return dict(run=r.testsRun,passed=r.testsRun-len(r.failures)-len(r.errors),failures=len(r.failures),errors=len(r.errors),successful=r.wasSuccessful())


tests=suite(HERE/'test_logic_validation.py','LogicValidationTests','unit_tests.log')
regression={name:suite(ROOT/path,cls,name.lower()+'_regression.log') for name,path,cls in [
    ('M0_S3','work/m0_s3/test_optical_models.py','OpticalModels'),('M1_S1','work/m1_s1/test_encoding_readout.py','EncodingReadout'),
    ('M1_S2','work/m1_s2/test_b7.py','B7Tests'),('M1_S3','work/m1_s3/test_weighted_readout.py','WeightedReadoutTests')]}
top=b7.load_topology();course=json.loads((ROOT/'config/course.json').read_text(encoding='utf-8'))
catalog=json.loads((ROOT/'config/m1_s4_phase_programs.json').read_text(encoding='utf-8'));logic.validate_programs(catalog,top)
epsilon=float(course['acceptance']['epsilon'])
baseline={gate:logic.evaluate_gate(top,catalog['gates'][gate],gate,epsilon=epsilon) for gate in logic.GATES}
unused={gate:logic.unused_input_groups(baseline[gate]['rows'],gate) for gate in logic.GATES[:3]}
source=ROOT/'config/m0_s3_reference_phases.json';fixture=json.loads(source.read_text(encoding='utf-8'))
provenance=json.loads((ROOT/'config/m1_s4_phase_provenance.json').read_text(encoding='utf-8'))
compatibility=[]
for gate in logic.GATES:
    setting=fixture['gates'][gate];saved=np.array([[complex(*z) for z in row] for row in setting['U']])
    compatibility.append(dict(gate=gate,max_complex_error=float(np.max(abs(baseline[gate]['U']-saved))),
        phases_match=all(catalog['gates'][gate][key]==setting[key] for key in ['theta','phi'])))
contrasts=[]
for name,kwargs,swap in [('swapped_readout',dict(readout=(3,1)),False),('reference_off',dict(reference_amplitude=0.),False),('theta_phi_swapped',{},True)]:
    programs=copy.deepcopy(catalog['gates'])
    if swap:
        for s in programs.values():s['theta'],s['phi']=s['phi'],s['theta']
    results={gate:logic.evaluate_gate(top,programs[gate],gate,epsilon=epsilon,**kwargs) for gate in logic.GATES}
    contrasts.append(dict(name=name,passed=sum(r['summary']['passed'] for r in results.values()),total=80,
        boundaries=sum(r['summary']['boundaries'] for r in results.values()),summaries={g:r['summary'] for g,r in results.items()}))
lab=json.loads((ROOT/'config/m1_s4_lab.json').read_text(encoding='utf-8'))
if not isinstance(lab['theta_error_mzi_index'],int) or isinstance(lab['theta_error_mzi_index'],bool) or not 0<=lab['theta_error_mzi_index']<7:
    raise ValueError('theta_error_mzi_index must be 0..6')
logic.truth(lab['gate'],lab['bits'])
offsets=np.zeros(7);offsets[lab['theta_error_mzi_index']]=float(lab['theta_error_pi'])*np.pi
student=logic.evaluate_gate(top,catalog['gates'][lab['gate']],lab['gate'],epsilon=epsilon,
    reference_amplitude=lab['reference_amplitude'],reference_phase=float(lab['reference_phase_pi'])*np.pi,
    theta_offsets=offsets,loss_db=lab['mzi_loss_db'])
student_index=sum(int(b)<<j for j,b in enumerate(lab['bits']))
student=dict(config=lab,summary=student['summary'],selected_case=student['rows'][student_index],rows=student['rows'])
with (OUT/'truth_80.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.writer(f);writer.writerow(['gate','index_lsb_x1','x1x2x3x4','expected','Pout1','Pout3','delta','signed_margin','clearance_over_epsilon','bit','correct','input_total_power','output_total_power'])
    for gate,r in baseline.items():
        for row in r['rows']:writer.writerow([gate,row['index_lsb_x1'],row['pattern'],row['expected'],row['powers'][1],row['powers'][3],row['delta'],row['signed_margin'],row['signed_margin']-epsilon,row['bit'],row['correct'],row['input_total_power'],row['output_total_power']])
with (OUT/'unused_input_groups.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.writer(f);writer.writerow(['gate','x1x2','four_patterns','four_deltas','four_bits','delta_span','passed'])
    for gate,groups in unused.items():
        for g in groups:writer.writerow([gate,''.join(map(str,g['active_bits'])),json.dumps(g['patterns']),json.dumps(g['deltas']),json.dumps(g['bits']),g['delta_span'],g['passed']])
with (OUT/'phase_programs.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.writer(f);writer.writerow(['gate',*[f'theta{k}_rad' for k in range(1,8)],*[f'phi{k}_rad' for k in range(1,8)]])
    for gate in logic.GATES:writer.writerow([gate,*catalog['gates'][gate]['theta'],*catalog['gates'][gate]['phi']])

# Bounded, one-control illustration. It does not certify process tolerance.
sweep_x=np.linspace(-.1,.1,41);sensitivity={}
for gate in logic.GATES:
    sensitivity[gate]=[]
    for delta_pi in sweep_x:
        offsets=np.zeros(7);offsets[0]=delta_pi*np.pi
        r=logic.evaluate_gate(top,catalog['gates'][gate],gate,epsilon=epsilon,theta_offsets=offsets)
        sensitivity[gate].append(r['summary']['minimum_signed_margin'])
with (OUT/'theta1_sensitivity.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.writer(f);writer.writerow(['theta1_error_pi',*logic.GATES])
    for k,x in enumerate(sweep_x):writer.writerow([x,*[sensitivity[g][k] for g in logic.GATES]])
delta_matrix=np.array([[row['delta'] for row in baseline[g]['rows']] for g in logic.GATES])
fig,(ax,margin)=plt.subplots(1,2,figsize=(14,5.4),constrained_layout=True,gridspec_kw={'width_ratios':[2.6,1]})
limit=float(np.max(abs(delta_matrix)));im=ax.imshow(delta_matrix,cmap='RdBu_r',vmin=-limit,vmax=limit,aspect='auto')
for i,g in enumerate(logic.GATES):
    for j,row in enumerate(baseline[g]['rows']):ax.text(j,i,str(row['bit']),ha='center',va='center',color='white' if abs(row['delta'])>.6*limit else '#17263b',fontsize=9)
ax.set(xticks=range(16),xticklabels=[r['pattern'] for r in baseline['AND2']['rows']],yticks=range(5),yticklabels=logic.GATES,title='固定五種相位設定：80 組 ΔP 與判讀 bit',xlabel='資料 x1x2x3x4（x1 為 index 最低位元）')
ax.tick_params(axis='x',rotation=60);fig.colorbar(im,ax=ax,label='ΔP=P(out1)−P(out3)')
values=[baseline[g]['summary']['minimum_signed_margin'] for g in logic.GATES]
margin.barh(logic.GATES,values,color='#258350');margin.axvline(0,color='black',lw=.8)
margin.set(xlabel='最小有號裕量',title='每個功能取 16 組最小值');margin.invert_yaxis();margin.grid(axis='x',alpha=.2)
for k,v in enumerate(values):margin.text(v,k,f' {v:.4f}',va='center',fontsize=9)
margin.set_xlim(0,max(values)*1.28)
fig.savefig(FIG/'truth_and_margins.png',dpi=155);plt.close(fig)
fig,ax=plt.subplots(figsize=(9,5),constrained_layout=True)
for gate in logic.GATES:ax.plot(sweep_x,sensitivity[gate],label=gate)
ax.axhline(0,color='black',linestyle='--');ax.axvline(0,color='#aaa',lw=.7)
ax.set(xlabel='M1 的 θ 誤差 / π（其餘相位不變）',ylabel='各功能 16 組中的最小有號裕量',title='單一控制的示意掃描：不重新調整其他相位或門檻')
ax.legend(ncol=3,fontsize=9);ax.grid(alpha=.2);fig.savefig(FIG/'theta1_sensitivity.png',dpi=155);plt.close(fig)
checks=[('fixed_contract',course['functions']==list(logic.GATES) and course['reference_amplitude']==3 and top.readout==(1,3) and epsilon==1e-10),
    ('eighty_unique_cases',sum(len(r['rows']) for r in baseline.values())==80 and all(len({row['pattern'] for row in r['rows']})==16 for r in baseline.values())),
    ('all_truths_accepted',all(r['summary']['accepted'] for r in baseline.values())),
    ('no_boundaries',all(r['summary']['boundaries']==0 for r in baseline.values())),
    ('positive_clearance',all(r['summary']['minimum_clearance']>0 for r in baseline.values())),
    ('twelve_unused_groups',sum(len(g) for g in unused.values())==12 and all(g['passed'] for groups in unused.values() for g in groups)),
    ('five_saved_matrices',all(c['phases_match'] and c['max_complex_error']<1e-12 for c in compatibility)),
    ('phase_source_digest',hashlib.sha256(source.read_bytes()).hexdigest()==provenance['source_sha256']),
    ('unitarity',all(np.max(abs(r['U'].conj().T@r['U']-np.eye(5)))<1e-12 for r in baseline.values())),
    ('energy_conservation',all(abs(row['input_total_power']-row['output_total_power'])<1e-11 for r in baseline.values() for row in r['rows']))]
checks.extend((c['name']+'_detected',c['passed']<80) for c in contrasts)
sources=['work/common/logic_validation.py','work/common/b7.py','work/common/mzi.py','work/common/linear_network.py','work/common/encoding.py',
         'work/m1_s4/run_logic.py','work/m1_s4/test_logic_validation.py','config/m1_s4_phase_programs.json','config/m1_s4_phase_provenance.json','config/m1_s4_lab.json']
interactive_perturbations=[]
for gate in logic.GATES:
    for pattern,R,phase,error in [('1100',0.,0.,0.),('1010',3.,.5,.1),('1111',2.,0.,-.1)]:
        offsets=np.zeros(7);offsets[0]=error*np.pi
        result=logic.evaluate_gate(top,catalog['gates'][gate],gate,reference_amplitude=R,reference_phase=phase*np.pi,theta_offsets=offsets)
        index=sum(int(b)<<k for k,b in enumerate(pattern))
        interactive_perturbations.append(dict(gate=gate,pattern=pattern,reference_amplitude=R,reference_phase_pi=phase,theta1_error_pi=error,row=result['rows'][index]))
result=dict(step='M1 S4',timestamp=datetime.now(timezone(timedelta(hours=8))).isoformat(),root=str(ROOT),root_matches_plan=ROOT.resolve()==Path('C:/EDA_Codex/Lab06b').resolve(),
    python=sys.executable,numpy_version=np.__version__,baseline_contract=dict(reference_amplitude=3,reference_phase=0,loss_db=0,threshold=0,epsilon=epsilon,readout=[1,3]),
    topology=course['architecture'],phase_source=provenance,unit_tests=tests,regression=regression,baseline=baseline,unused_inputs=unused,
    compatibility=compatibility,controlled_contrasts=contrasts,student_diagnostic=student,interactive_perturbations=interactive_perturbations,
    sensitivity=dict(parameter='M1 theta only',theta_error_pi=sweep_x,minimum_signed_margin=sensitivity),
    checks=[dict(name=name,passed=bool(ok)) for name,ok in checks],
    source_hashes={rel:hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in sources},
    core_passed=tests['successful'] and all(r['successful'] for r in regression.values()) and all(ok for name,ok in checks),
    scope='New full 80-case acceptance using inherited phase programs and current ideal B7; no new optimization, PDK, dynamic receiver, fabrication or measured chip validation.')
(OUT/'logic_results.json').write_text(json.dumps(serial(result),ensure_ascii=False,indent=2),encoding='utf-8')
print('M1 S4 tests:',tests)
print('Previous regression:',sum(r['passed'] for r in regression.values()),'/',sum(r['run'] for r in regression.values()))
for gate,r in baseline.items():print(gate,r['summary']['passed'],'/16; signed margin=',r['summary']['minimum_signed_margin'])
print('Unused input groups:',sum(g['passed'] for groups in unused.values() for g in groups),'/12')
print('M1 S4 CORE:',result['core_passed'])
raise SystemExit(0 if result['core_passed'] else 1)
