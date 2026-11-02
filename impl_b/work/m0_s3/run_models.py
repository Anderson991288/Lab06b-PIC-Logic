"""M0 S3 reproducible model tests, controlled mutations and teaching evidence."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import os,sys,io,json,csv,hashlib,importlib.util,unittest

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent;OUT=HERE/'out';FIG=ROOT/'course/figures/m0_s3'
OUT.mkdir(parents=True,exist_ok=True);FIG.mkdir(parents=True,exist_ok=True)
for key in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[key]='1'
os.environ['MPLCONFIGDIR']=str(ROOT/'work/.matplotlib')
DLL_HANDLE=None
if os.name=='nt' and (Path(sys.prefix)/'Library/bin').is_dir():DLL_HANDLE=os.add_dll_directory(str(Path(sys.prefix)/'Library/bin'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.family':['Microsoft JhengHei','DejaVu Sans'],'axes.unicode_minus':False})
sys.path.insert(0,str(ROOT/'work'))
from common import mzi
from common import linear_network as network

spec=importlib.util.spec_from_file_location('optical_test_module',HERE/'test_optical_models.py')
tests=importlib.util.module_from_spec(spec);spec.loader.exec_module(tests)


class RecordedResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.cases=[]
    def addSuccess(self,test):super().addSuccess(test);self.cases.append({'name':test._testMethodName,'status':'pass'})
    def addFailure(self,test,err):super().addFailure(test,err);self.cases.append({'name':str(test),'status':'failure'})
    def addError(self,test,err):super().addError(test,err);self.cases.append({'name':str(test),'status':'error'})


def run_suite(logfile,methods=None):
    suite=unittest.TestLoader().loadTestsFromTestCase(tests.OpticalModels) if methods is None else unittest.TestSuite([tests.OpticalModels(name) for name in methods])
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=RecordedResult).run(suite)
    (OUT/logfile).write_text(stream.getvalue(),encoding='utf-8')
    return result


baseline=run_suite('unit_tests.log')
print('Baseline unit tests:',baseline.testsRun,'passed=',baseline.wasSuccessful(),flush=True)
faults=[]


def mutant(name,owner,attribute,replacement,method,reason):
    original=getattr(owner,attribute)
    try:
        setattr(owner,attribute,replacement)
        result=run_suite('mutation_'+name+'.log',[method])
        faults.append({'name':name,'test':method,'detected':not result.wasSuccessful(),
                       'failures':len(result.failures),'errors':len(result.errors),'reason':reason,
                       'scope':'Controlled temporary function replacement; restored in finally block'})
    finally:setattr(owner,attribute,original)


mutant('real_coupler',mzi,'coupler',lambda eps=0:np.array([[1,1],[1,-1]],complex)/np.sqrt(2),
       'test_exact_switch_and_split_matrices','Wrong real coupler remains unitary but changes the optical phase convention.')
original_mzi=mzi.T2
mutant('theta_phi_swapped',mzi,'T2',lambda theta,phi=0,loss_db=0,mmi_errors=(0,0):original_mzi(phi,theta,loss_db,mmi_errors),
       'test_closed_form_complex_regression','Interchanging physical phase locations changes the complex transfer matrix.')
mutant('power_factor_as_amplitude',mzi,'amplitude_factor',lambda loss_db:10.**(-loss_db/10),
       'test_insertion_loss_is_power_db','Using the power attenuation factor on the field doubles the dB loss.')


def reversed_cascade(stages,n_modes):
    total=np.eye(n_modes,dtype=complex)
    for stage in stages:total=total@stage
    return total


mutant('reversed_cascade',network,'cascade',reversed_cascade,'test_nonadjacent_embedding_and_order',
       'Matrix multiplication must follow physical propagation order.')
original_readout=network.power_difference_readout


def bad_tie(*args,**kwargs):
    result=original_readout(*args,**kwargs)
    if result['bit'] is None:result.update(bit=1,boundary=False)
    return result


mutant('tie_counted_as_one',network,'power_difference_readout',bad_tie,'test_readout_boundary_has_no_valid_bit',
       'A zero-margin result must remain a boundary rather than a valid bit.')
restored=run_suite('unit_tests_after_restoration.log')
print('Restored unit tests:',restored.testsRun,'passed=',restored.wasSuccessful(),flush=True)

fixture_path=ROOT/'config/m0_s3_reference_phases.json'
fixture=json.loads(fixture_path.read_text(encoding='utf-8'))
functions={'AND2':lambda b:b[0]&b[1],'OR2':lambda b:b[0]|b[1],'XOR2':lambda b:b[0]^b[1],
           'AND4':lambda b:int(all(b)),'OR4':lambda b:int(any(b))}
gate_rows=[];gate_summary=[]
for name,setting in fixture['gates'].items():
    stages=[network.embed_2x2(mzi.T2(setting['theta'][k],setting['phi'][k]),p,p+1,5) for k,(p,_) in enumerate(fixture['ops'])]
    u=network.cascade(stages,5)
    saved=np.array([[complex(*z) for z in row] for row in setting['U']])
    local=[]
    for number in range(16):
        bits=[(number>>j)&1 for j in range(4)];v=np.array([*bits,3],complex);field=u@v
        read=network.power_difference_readout(field)
        row={'gate':name,'bits_x1_to_x4':''.join(map(str,bits)),'expected':functions[name](bits),
             **read,'passed':read['bit']==functions[name](bits),'power_sum_error':float(abs(mzi.powers(field).sum()-mzi.powers(v).sum()))}
        gate_rows.append(row);local.append(row)
    gate_summary.append({'gate':name,'passed':sum(r['passed'] for r in local),'total':len(local),
                         'minimum_signed_margin':min((2*r['expected']-1)*r['margin'] for r in local),
                         'max_complex_U_error':float(np.max(abs(u-saved)))})
with (OUT/'b7_compatibility.csv').open('w',encoding='utf-8-sig',newline='') as stream:
    writer=csv.DictWriter(stream,fieldnames=list(gate_rows[0]));writer.writeheader();writer.writerows(gate_rows)

theta=np.linspace(0,2*np.pi,241);phi=np.linspace(0,2*np.pi,161)
power_single=np.array([mzi.powers(mzi.T2(t)@[1,0]) for t in theta])
power_equal=np.array([[mzi.powers(mzi.T2(t,p)@(np.ones(2)/np.sqrt(2)))[0] for p in phi] for t in theta])
fig,axs=plt.subplots(1,2,figsize=(10.5,4),constrained_layout=True)
axs[0].plot(theta/np.pi,power_single[:,0],label='out0 / upper（bar）')
axs[0].plot(theta/np.pi,power_single[:,1],label='out1 / lower（cross）')
axs[0].set(xlabel='θ / π',ylabel='歸一化功率',title='單路上埠輸入：φ 不改變功率');axs[0].legend(fontsize=8);axs[0].grid(alpha=.2)
im=axs[1].pcolormesh(phi/np.pi,theta/np.pi,power_equal,shading='auto',vmin=0,vmax=1,cmap='viridis')
axs[1].set(xlabel='φ / π（上方輸入相位）',ylabel='θ / π（內臂相位）',title='雙路等功率：P(out0 / upper)')
fig.colorbar(im,ax=axs[1],label='歸一化功率');fig.savefig(FIG/'mzi_response.png',dpi=150,bbox_inches='tight');plt.close(fig)

example_path=ROOT/'config/m0_s3_example.json'
example=json.loads(example_path.read_text(encoding='utf-8'))
if example.get('order')!=list(mzi.PORT_ORDER):raise ValueError('Example order must remain [upper, lower]; use the explicit lower-first adapter when needed')
v=np.array([complex(*z) for z in example['input_field']]);theta_demo=float(example['theta_pi'])*np.pi;phi_demo=float(example['phi_pi'])*np.pi
trace=[{'stage':name,'field':[[float(z.real),float(z.imag)] for z in field],
        'power':mzi.powers(field).tolist(),'total_power':float(mzi.powers(field).sum())}
       for name,field in mzi.trace(theta_demo,phi_demo,v,loss_db=example['loss_db'],mmi_errors=example['mmi_errors'])]
s2=json.loads((ROOT/'work/m0_s2/out/physics_results.json').read_text(encoding='utf-8'))
neff=s2['fem']['convergence'][-1]['neff'];wavelength=s2['parameters']['wavelength_um']
core=baseline.wasSuccessful() and restored.wasSuccessful() and all(r['detected'] for r in faults) and all(r['passed'] for r in gate_rows)
hashes={rel:hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in ['work/common/mzi.py','work/common/linear_network.py','work/m0_s3/test_optical_models.py','work/m0_s3/run_models.py','config/m0_s3_reference_phases.json','config/m0_s3_example.json']}
failed_methods={getattr(getattr(test,'test_case',test),'_testMethodName',str(test)) for test,_ in restored.failures+restored.errors}
case_records=[{'name':name,'status':'fail' if name in failed_methods else 'pass'} for name in unittest.TestLoader().getTestCaseNames(tests.OpticalModels)]
interactive=[]
for mode,t,p in [('single',0,0),('single',.5,.7),('single',1,.3),('equal',.5,0),('equal',.5,1),('equal',.25,.5),('equal',1.5,0)]:
    vector=np.array([1,0]) if mode=='single' else np.ones(2)/np.sqrt(2)
    interactive.append({'input':mode,'theta_pi':t,'phi_pi':p,'power':mzi.powers(mzi.T2(t*np.pi,p*np.pi)@vector).tolist()})
report={'step':'M0 S3','timestamp':datetime.now(timezone(timedelta(hours=8))).isoformat(),'root':str(ROOT),
        'root_matches_plan':ROOT==Path('C:/EDA_Codex/Lab06b'),'python':sys.executable,'numpy_version':np.__version__,
        'convention':{'vector_order':['upper','lower'],'layout_ports':['in0/out0 = upper','in1/out1 = lower'],
                      'formula':'T=a*C2*P_upper(theta)*C1*P_upper(phi)','phase_unit':'radian','field_is_complex':True,
                      'bar_power_single_upper':'sin(theta/2)^2','lower_first_adapter':'P*T*P, P swaps both inputs and outputs'},
        'unit_tests':{'run':restored.testsRun,'passed':restored.testsRun-len(failed_methods),
                      'failures':len(failed_methods),'assertion_failures':len(restored.failures),'errors':len(restored.errors),'cases':case_records,
                      'baseline_passed':baseline.wasSuccessful(),'after_mutation_restoration_passed':restored.wasSuccessful()},
        'controlled_mutations':faults,'b7_compatibility':{'scope':'Replay of inherited ideal phase settings; no new phase synthesis, PDK simulation or chip validation',
             'total':len(gate_rows),'passed':sum(r['passed'] for r in gate_rows),'functions':gate_summary},
        'trace_example':{'theta':theta_demo,'phi':phi_demo,'input_field':example['input_field'],'loss_db':example['loss_db'],'mmi_errors':example['mmi_errors'],'rows':trace},
        'interactive_samples':interactive,
        's2_connection':{'neff':neff,'wavelength_um':wavelength,'geometrical_length_for_pi_um':wavelength/(2*neff),
                         'scope':'Uniform segment geometric phase at the assumed effective index; not heater tuning voltage'},
        'source_hashes':hashes,'core_passed':core,
        'scope':'Forward lumped ideal MZI with optional uniform loss and unitary coupler errors. No reflection, dispersion, layout extraction, heater calibration or new FDTD.'}
(OUT/'model_results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('Controlled mutations detected:',sum(r['detected'] for r in faults),'/',len(faults),flush=True)
print('B7 inherited phase replay:',report['b7_compatibility']['passed'],'/',len(gate_rows),flush=True)
print('M0 S3 CORE:',core,flush=True)
raise SystemExit(0 if core else 2)
