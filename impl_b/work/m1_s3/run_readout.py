"""M1 S3 weighted complex sums, interference expansion and fixed readout."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import sys,os,json,hashlib,csv,unittest,io,importlib.util
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
OUT=HERE/'out';FIG=ROOT/'course/figures/m1_s3'
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
from common import b7,encoding,weighted_readout as w,linear_network as net


def serial(value):
    if isinstance(value,np.ndarray):return serial(value.tolist())
    if isinstance(value,complex):return [float(value.real),float(value.imag)]
    if isinstance(value,dict):return {k:serial(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [serial(v) for v in value]
    if isinstance(value,np.generic):return value.item()
    return value


def suite(path,classname,filename):
    spec=importlib.util.spec_from_file_location(classname,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(getattr(module,classname)))
    (OUT/filename).write_text(stream.getvalue(),encoding='utf-8')
    return dict(run=result.testsRun,passed=result.testsRun-len(result.failures)-len(result.errors),failures=len(result.failures),errors=len(result.errors),successful=result.wasSuccessful())


tests=suite(HERE/'test_weighted_readout.py','WeightedReadoutTests','unit_tests.log')
regression={name:suite(ROOT/path,cls,name.lower()+'_regression.log') for name,path,cls in [
    ('M0_S3','work/m0_s3/test_optical_models.py','OpticalModels'),
    ('M1_S1','work/m1_s1/test_encoding_readout.py','EncodingReadout'),
    ('M1_S2','work/m1_s2/test_b7.py','B7Tests')]}
top=b7.load_topology();fixture=json.loads((ROOT/'config/m0_s3_reference_phases.json').read_text(encoding='utf-8'))
setting=fixture['gates']['AND2'];U=b7.transfer_matrix(top,setting['theta'],setting['phi'])
saved=np.array([[complex(*z) for z in row] for row in setting['U']])
worked=[]
for pattern,expected in [('1000',0),('1100',1)]:
    v=encoding.with_reference(list(map(int,pattern)));result=w.evaluate(U,v,*top.readout)
    worked.append(dict(pattern=pattern,expected=expected,input=v,result=result))
cfg=json.loads((ROOT/'config/m1_s3_example.json').read_text(encoding='utf-8'))
if cfg['phase_setting']!='AND2':raise ValueError('M1 S3 keeps the inherited AND2 setting fixed')
if len(cfg['bits'])!=4 or len(cfg['data_phases_pi'])!=4:raise ValueError('Provide four bits and four phases')
student_v=encoding.with_reference(cfg['bits'],cfg['reference_amplitude'],cfg['reference_phase_pi']*np.pi,
                                  phases=np.asarray(cfg['data_phases_pi'])*np.pi)
student=w.evaluate(U,student_v,*top.readout,cfg['threshold'],cfg['epsilon'])
boundary=[]
for target in [0.,1e-12,1e-8,-1e-8]:
    read=w.evaluate(np.eye(2),[np.sqrt(1+target),1],0,1)
    boundary.append(dict(intended_delta=target,actual_delta=read['readout']['delta'],bit=read['readout']['bit']))
v=worked[1]['input'];correct=worked[1]['result']
incoherent_delta=correct['self_delta']
amplitude_delta=float(abs(correct['positive']['field'])-abs(correct['negative']['field']))
phase_v=encoding.with_reference([1,1,0,0],reference_phase=.25*np.pi,phases=[0,.4*np.pi,0,0])
phase_correct=w.evaluate(U,phase_v)
bad=np.conj(U)@phase_v;bad_read=net.power_difference_readout(bad)
wrong=[dict(name='sum_powers_before_fields',value=incoherent_delta,correct_delta=correct['readout']['delta'],
            error=abs(incoherent_delta-correct['readout']['delta'])),
       dict(name='amplitude_difference_as_power_difference',value=amplitude_delta,correct_delta=correct['readout']['delta'],
            error=abs(amplitude_delta-correct['readout']['delta'])),
       dict(name='conjugating_matrix_row',field_max_error=float(np.max(abs(bad-phase_correct['output_field']))),
            delta_error=abs(bad_read['delta']-phase_correct['readout']['delta']))]
checks=[('two_worked_truth_cases',all(c['result']['readout']['bit']==c['expected'] for c in worked)),
        ('saved_U_compatibility',np.max(abs(U-saved))<1e-12),
        ('unitarity',np.max(abs(U.conj().T@U-np.eye(5)))<1e-12),
        ('all_output_energy',all(abs(sum(abs(c['input'])**2)-sum(c['result']['output_powers']))<1e-11 for c in worked)),
        ('row_sums_match_matrix',all(abs(c['result'][key]['field']-c['result']['output_field'][idx])<1e-12 for c in worked for key,idx in [('positive',1),('negative',3)])),
        ('power_self_plus_interference',all(abs(c['result'][key]['power']-c['result'][key]['self_power']-c['result'][key]['interference_power'])<1e-12 for c in worked for key in ['positive','negative'])),
        ('quadratic_form_matches_readout',all(abs(c['result']['quadratic_delta']-c['result']['readout']['delta'])<1e-12 for c in worked)),
        ('boundary_not_valid_one',boundary[0]['bit'] is None and boundary[1]['bit'] is None),
        ('wrong_power_sum_exposed',wrong[0]['error']>1e-6),
        ('wrong_amplitude_difference_exposed',wrong[1]['error']>1e-6),
        ('wrong_conjugation_exposed',wrong[2]['field_max_error']>1e-6)]
with (OUT/'weighted_terms.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.writer(f);writer.writerow(['pattern','output_index','input_index','coefficient_real','coefficient_imag','input_real','input_imag','term_real','term_imag','cumulative_real','cumulative_imag','self_power'])
    for c in worked:
        for key in ['positive','negative']:
            r=c['result'][key]
            for j in range(5):writer.writerow([c['pattern'],r['output'],j,r['coefficients'][j].real,r['coefficients'][j].imag,c['input'][j].real,c['input'][j].imag,r['terms'][j].real,r['terms'][j].imag,r['cumulative'][j].real,r['cumulative'][j].imag,r['self_powers'][j]])
with (OUT/'interference_pairs.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.writer(f);writer.writerow(['pattern','output_index','j','k','pair_power'])
    for c in worked:
        for key in ['positive','negative']:
            for p in c['result'][key]['pairs']:writer.writerow([c['pattern'],c['result'][key]['output'],p['j'],p['k'],p['power']])
with (OUT/'readout_summary.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.writer(f);writer.writerow(['pattern','Pout1','Pout3','self_delta','interference_delta','delta','threshold','bit','expected'])
    for c in worked:
        a=c['result'];writer.writerow([c['pattern'],a['positive']['power'],a['negative']['power'],a['self_delta'],a['interference_delta'],a['readout']['delta'],0,a['readout']['bit'],c['expected']])

colors=['#155bd0','#d17c16','#258350','#9a51a0','#a64532'];names=['x1','x2','x3','x4','R']
fig,axes=plt.subplots(2,2,figsize=(11.5,8.3),constrained_layout=True)
for i,c in enumerate(worked):
    for j,key in enumerate(['positive','negative']):
        ax=axes[i,j];r=c['result'][key];points=np.r_[0j,r['cumulative']]
        for k,term in enumerate(r['terms']):
            if abs(term)<1e-7:continue
            a,b=points[k:k+2];ax.annotate('',xy=(b.real,b.imag),xytext=(a.real,a.imag),arrowprops=dict(arrowstyle='->',color=colors[k],lw=2.4))
            midpoint=(a+b)/2;ax.annotate(names[k],(midpoint.real,midpoint.imag),xytext=(5,7),textcoords='offset points',color=colors[k],fontsize=11)
        ax.plot([0,r['field'].real],[0,r['field'].imag],'--',color='#17263b',alpha=.65,label='總場 y')
        ax.scatter([r['field'].real],[r['field'].imag],color='#17263b',s=25)
        center=(max(points.real)+min(points.real))/2+1j*(max(points.imag)+min(points.imag))/2
        extent=max(float(np.ptp(points.real)),float(np.ptp(points.imag)),.4)*.72
        ax.set(xlim=(center.real-extent,center.real+extent),ylim=(center.imag-extent,center.imag+extent),
               xlabel='場的實部',ylabel='場的虛部',title=f"{c['pattern']} → out{r['output']}：P={r['power']:.6f}",aspect='equal')
        ax.axhline(0,color='#aaa',lw=.5);ax.axvline(0,color='#aaa',lw=.5);ax.grid(alpha=.2);ax.legend(fontsize=9)
fig.savefig(FIG/'phasor_sums.png',dpi=150);plt.close(fig)
angles=np.linspace(0,2*np.pi,241);phase_sweep={}
fig,axes=plt.subplots(1,2,figsize=(12,4.7),constrained_layout=True)
groups=[(c['pattern'],c['result'][key]) for c in worked for key in ['positive','negative']]
x=np.arange(4)
for offset,(name,label) in zip([-.25,0,.25],[('self_power','自項功率'),('interference_power','干涉項'),('power','實際功率')]):
    axes[0].bar(x+offset,[r[name] for p,r in groups],.24,label=label)
axes[0].set(xticks=x,xticklabels=[f"{p}\nout{r['output']}" for p,r in groups],ylabel='歸一化功率',title='每個讀取埠：P = 自項 + 干涉項')
axes[0].axhline(0,color='black',lw=.7);axes[0].legend(fontsize=9)
for pattern in ['1000','1100']:
    deltas=[w.evaluate(U,encoding.with_reference(list(map(int,pattern)),reference_phase=angle))['readout']['delta'] for angle in angles]
    phase_sweep[pattern]=deltas;axes[1].plot(angles/np.pi,deltas,label=pattern)
axes[1].axhline(0,color='black',linestyle='--',label='固定門檻 0')
axes[1].set(xlabel='參考光相位 / π',ylabel='ΔP = P(out1)−P(out3)',title='只改參考光相位：原判讀可能改變')
axes[1].grid(alpha=.2);axes[1].legend(fontsize=9)
fig.savefig(FIG/'power_readout.png',dpi=150);plt.close(fig)
samples=[]
for pattern in ['0000','1000','1100','1111']:
    for R,ref_phase,data_phase,threshold in [(3,0,0,0),(3,.5,0,0),(3,1,0,0),(0,0,0,0),(2,0,.5,0),(3,0,1,.5)]:
        field=encoding.with_reference(list(map(int,pattern)),R,ref_phase*np.pi,phases=[0,data_phase*np.pi,0,0])
        samples.append(dict(pattern=pattern,reference_amplitude=R,reference_phase_pi=ref_phase,x2_phase_pi=data_phase,threshold=threshold,result=w.evaluate(U,field,threshold=threshold)))
source_files=['work/common/weighted_readout.py','work/common/b7.py','work/common/mzi.py','work/common/linear_network.py','work/common/encoding.py',
              'work/m1_s3/run_readout.py','work/m1_s3/test_weighted_readout.py','config/m1_s3_example.json','config/m0_s3_reference_phases.json']
architecture=json.loads((ROOT/'config/course.json').read_text(encoding='utf-8'))['architecture']
result=dict(step='M1 S3',timestamp=datetime.now(timezone(timedelta(hours=8))).isoformat(),root=str(ROOT),
    root_matches_plan=ROOT.resolve()==Path('C:/EDA_Codex/Lab06b').resolve(),python=sys.executable,numpy_version=np.__version__,
    topology=architecture,architecture_sha256=hashlib.sha256(json.dumps(architecture,sort_keys=True).encode()).hexdigest(),
    phase_source=json.loads((ROOT/'config/m0_s3_reference_provenance.json').read_text(encoding='utf-8')),
    phase_setting='AND2',U=U,theta=setting['theta'],phi=setting['phi'],unit_tests=tests,regression=regression,
    worked_cases=worked,student_example=dict(config=cfg,input=student_v,result=student),
    checks=[dict(name=name,passed=bool(ok)) for name,ok in checks],controlled_calculation_errors=wrong,boundary_examples=boundary,
    reference_phase_sweep=dict(phase_pi=angles/np.pi,delta=phase_sweep),interactive_samples=samples,
    source_hashes={rel:hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in source_files},
    core_passed=tests['successful'] and all(r['successful'] for r in regression.values()) and all(ok for _,ok in checks),
    scope='New weighted-field/power/readout explanations for two cases using inherited AND2 phases and current B7; no new synthesis, full five-function acceptance, PDK, dynamic receiver or chip validation.')
(OUT/'readout_results.json').write_text(json.dumps(serial(result),ensure_ascii=False,indent=2),encoding='utf-8')
print('M1 S3 tests:',tests)
print('Previous regressions:',sum(r['passed'] for r in regression.values()),'/',sum(r['run'] for r in regression.values()))
print('Readout checks:',sum(ok for _,ok in checks),'/',len(checks))
for c in worked:print(c['pattern'], 'Pout1=',c['result']['positive']['power'],'Pout3=',c['result']['negative']['power'],'delta=',c['result']['readout']['delta'],'bit=',c['result']['readout']['bit'])
print('M1 S3 CORE:',result['core_passed'])
raise SystemExit(0 if result['core_passed'] else 1)
