"""Rebuild B7 topology/matrix evidence without changing earlier course models."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import os,sys,json,csv,hashlib,io,unittest,importlib.util
ROOT=Path(__file__).resolve().parents[2]; HERE=Path(__file__).resolve().parent
OUT=HERE/'out';FIG=ROOT/'course/figures/m1_s2'
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
from common import b7,mzi,encoding,linear_network as net


def suite(path,classname,logname):
    spec=importlib.util.spec_from_file_location(classname,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    stream=io.StringIO();tests=unittest.defaultTestLoader.loadTestsFromTestCase(getattr(module,classname))
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(tests)
    (OUT/logname).write_text(stream.getvalue(),encoding='utf-8')
    return dict(run=result.testsRun,passed=result.testsRun-len(result.failures)-len(result.errors),
                failures=len(result.failures),errors=len(result.errors),successful=result.wasSuccessful()),module


def pairs(a):return np.stack((np.asarray(a).real,np.asarray(a).imag),axis=-1).tolist()
def error(a,b):return float(np.max(np.abs(np.asarray(a)-np.asarray(b))))
def trace_rows(trace):return [dict(stage=name,field=pairs(field),powers=mzi.powers(field).tolist(),total_power=float(sum(mzi.powers(field)))) for name,field in trace]


tests,oracle=suite(HERE/'test_b7.py','B7Tests','unit_tests.log')
m0,_=suite(ROOT/'work/m0_s3/test_optical_models.py','OpticalModels','m0_s3_regression.log')
m1,_=suite(ROOT/'work/m1_s1/test_encoding_readout.py','EncodingReadout','m1_s1_regression.log')
top=b7.load_topology();example=json.loads((ROOT/'config/m1_s2_example.json').read_text(encoding='utf-8'))
if example['phase_order']!=[f'M{k}' for k in range(1,8)]:raise ValueError('phase_order must be M1 through M7')
if len(example['bits'])!=4:raise ValueError('Provide four data bits')
theta=np.array(example['theta_pi'],dtype=float)*np.pi;phi=np.array(example['phi_pi'],dtype=float)*np.pi
U=b7.transfer_matrix(top,theta,phi,example['mzi_loss_db'])
v=encoding.with_reference(example['bits'],example['reference_amplitude'],example['reference_phase_pi']*np.pi)
rows=trace_rows(b7.trace(top,theta,phi,v,example['mzi_loss_db']))
layer_rows=trace_rows(b7.trace(top,theta,phi,v,example['mzi_loss_db'],by_layer=True))
layer_matrices=b7.layers(top,theta,phi,example['mzi_loss_db'])
probe_U=np.column_stack([oracle.scalar_replay(theta,phi,np.eye(5)[:,k]) for k in range(5)])

# Fixed acceptance baseline is separate from editable student settings.
base_t=np.full(7,np.pi/2);base_p=np.zeros(7);base_U=b7.transfer_matrix(top,base_t,base_p)
base_v=encoding.with_reference([1,0,0,0]);base_rows=trace_rows(b7.trace(top,base_t,base_p,base_v,by_layer=True))
elements=b7.elements(top,base_t,base_p)
fault_matrices={
    'reverse_order':net.cascade(elements[::-1],5),
    'omit_M3':net.cascade(elements[:2]+elements[3:],5),
    'erase_bypass':net.cascade([e*np.isin(np.arange(5)[:,None],[p,p+1]) for e,(p,layer) in zip(elements,top.ops)],5)}
faults=[dict(name=name,unitarity_error=error(bad.conj().T@bad,np.eye(5)),
             reference_matrix_error=error(bad,base_U),rejected=error(bad,base_U)>1e-6) for name,bad in fault_matrices.items()]
fixture=json.loads((ROOT/'config/m0_s3_reference_phases.json').read_text(encoding='utf-8'))
compat=[]
for gate,s in fixture['gates'].items():
    saved=np.array([[complex(*z) for z in row] for row in s['U']])
    actual=b7.transfer_matrix(top,s['theta'],s['phi'])
    compat.append(dict(gate=gate,max_complex_error=error(actual,saved),passed=error(actual,saved)<1e-12))
support=b7.reachability(top)
checks=[('unitarity',error(base_U.conj().T@base_U,np.eye(5))<1e-12),
    ('layer_product',error(base_U,net.cascade(b7.layers(top,base_t,base_p),5))<1e-12),
    ('independent_scalar_replay',error(base_U@base_v,oracle.scalar_replay(base_t,base_p,base_v))<1e-12),
    ('five_basis_columns',error(base_U,np.column_stack([oracle.scalar_replay(base_t,base_p,np.eye(5)[:,k]) for k in range(5)]))<1e-12),
    ('all_layer_powers',all(abs(r['total_power']-10)<1e-12 for r in base_rows)),
    ('directed_structural_zeros',error(base_U[~support],np.zeros(2))<1e-12),
    ('six_bypass_segments',sum(map(len,b7.bypass_ports(top)))==6),
    ('five_saved_complex_matrices',all(r['passed'] for r in compat)),
    ('loss_is_passive',np.linalg.svd(b7.transfer_matrix(top,base_t,base_p,.5),compute_uv=False)[0]<=1+1e-12)]
checks.extend((f['name']+'_rejected',f['rejected']) for f in faults)
profiles={}
for name,t,p in [('split_all',[.5]*7,[0.]*7),('cross_all',[0.]*7,[0.]*7),
                 ('bar_all',[1.]*7,[0.]*7),('identity_all',[1.]*7,[1.]*7),
                 ('student',example['theta_pi'],example['phi_pi'])]:
    loss=example['mzi_loss_db'] if name=='student' else 0.
    profiles[name]=dict(theta_pi=t,phi_pi=p,loss_db=loss,U=pairs(b7.transfer_matrix(top,np.array(t)*np.pi,np.array(p)*np.pi,loss)),
        layers=pairs(b7.layers(top,np.array(t)*np.pi,np.array(p)*np.pi,loss)))
samples=[]
for profile in profiles:
    for source in ['basis0','basis1','basis2','basis3','basis4','1000','1100']:
        field=np.eye(5)[:,int(source[-1])].astype(complex) if source.startswith('basis') else encoding.with_reference(list(map(int,source)))
        p=profiles[profile];tr=b7.trace(top,np.array(p['theta_pi'])*np.pi,np.array(p['phi_pi'])*np.pi,field,p['loss_db'],by_layer=True)
        for step in [0,2,4]:
            samples.append(dict(profile=profile,source=source,reference_amplitude=3.,step=step,field=pairs(tr[step][1]),powers=mzi.powers(tr[step][1]).tolist()))
with (OUT/'layer_trace.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.writer(f);writer.writerow(['stage','mode','field_real','field_imag','power','total_power'])
    for r in layer_rows:
        for k,z in enumerate(r['field']):writer.writerow([r['stage'],k,*z,r['powers'][k],r['total_power']])
with (OUT/'basis_probe.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.writer(f);writer.writerow(['input_column','output_row','real','imag','power'])
    for col in range(5):
        for row in range(5):writer.writerow([col,row,U[row,col].real,U[row,col].imag,abs(U[row,col])**2])
with (OUT/'wiring.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.writer(f);writer.writerow(['MZI','layer','upper_mode','lower_mode','theta_index','phi_index'])
    for k,(p,layer) in enumerate(top.ops):writer.writerow([f'M{k+1}',layer,p,p+1,k,k])

fig,ax=plt.subplots(figsize=(7.4,5.8),constrained_layout=True)
im=ax.imshow(abs(U)**2,cmap='Blues',vmin=0,vmax=max(1.,float(np.max(abs(U)**2))))
for row in range(5):
    for col in range(5):ax.text(col,row,f'{abs(U[row,col])**2:.3f}',ha='center',va='center',color='white' if abs(U[row,col])**2>.55 else '#17263b')
ax.set(xticks=range(5),yticks=range(5),xlabel='輸入欄 index j',ylabel='輸出列 index i',title='目前學員設定：|Uᵢⱼ|²（單位功率單埠探測）')
fig.colorbar(im,ax=ax,label='輸出功率 / 單埠輸入功率');fig.savefig(FIG/'b7_matrix_power.png',dpi=145);plt.close(fig)
fig,(ax,energy)=plt.subplots(1,2,figsize=(11.5,4.7),constrained_layout=True)
im=ax.imshow(np.array([r['powers'] for r in layer_rows]).T,cmap='YlGnBu',aspect='auto')
ax.set(xticks=range(5),xticklabels=['Input','L0','L1','L2','L3'],yticks=range(5),ylabel='光路 index',title='目前輸入：逐層各埠功率')
fig.colorbar(im,ax=ax,label='歸一化功率')
energy.plot(range(5),[r['total_power'] for r in layer_rows],'-o',label='全部五路總功率')
energy.plot(range(5),[r['powers'][1]+r['powers'][3] for r in layer_rows],'-s',label='只加兩個讀取埠')
energy.set(xticks=range(5),xticklabels=['Input','L0','L1','L2','L3'],ylabel='歸一化功率',title='功率檢查要包含未讀取的輸出')
energy.grid(alpha=.25);energy.legend(fontsize=9)
fig.savefig(FIG/'b7_layer_power.png',dpi=145);plt.close(fig)
source_files=['work/common/b7.py','work/common/mzi.py','work/common/linear_network.py','work/common/encoding.py',
              'work/m1_s2/run_b7.py','work/m1_s2/test_b7.py','config/m1_s2_example.json','config/m0_s3_reference_phases.json']
architecture=json.loads((ROOT/'config/course.json').read_text(encoding='utf-8'))['architecture']
result=dict(step='M1 S2',timestamp=datetime.now(timezone(timedelta(hours=8))).isoformat(),root=str(ROOT),
    root_matches_plan=ROOT.resolve()==Path('C:/EDA_Codex/Lab06b').resolve(),python=sys.executable,numpy_version=np.__version__,
    topology=architecture,architecture_sha256=hashlib.sha256(json.dumps(architecture,sort_keys=True).encode('utf-8')).hexdigest(),
    unit_tests=tests,regression={'M0_S3':m0,'M1_S1':m1},checks=[dict(name=name,passed=bool(ok)) for name,ok in checks],
    example=example,input_field=pairs(v),U=pairs(U),element_matrices=pairs(b7.elements(top,theta,phi,example['mzi_loss_db'])),
    layer_matrices=pairs(layer_matrices),element_trace=rows,layer_trace=layer_rows,
    diagnostics=dict(unitarity_error=error(U.conj().T@U,np.eye(5)),layer_product_error=error(U,net.cascade(layer_matrices,5)),
        independent_scalar_error=None if np.any(np.asarray(example['mzi_loss_db'])!=0) else error(U,probe_U),
        maximum_singular_value=float(np.linalg.svd(U,compute_uv=False)[0]),structural_possible=support.tolist(),
        bypass_ports=b7.bypass_ports(top)),
    controlled_wiring_errors=faults,inherited_matrix_compatibility=compat,
    profiles=profiles,interactive_samples=samples,source_hashes={rel:hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in source_files},
    core_passed=tests['successful'] and m0['successful'] and m1['successful'] and all(ok for _,ok in checks),
    scope='New shared ideal B7 topology and 5x5 U; saved complex matrices replayed for compatibility only. No new phase synthesis, PDK, waveguide geometry, heater or chip validation.')
(OUT/'b7_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('M1 S2 unit tests:',tests)
print('Earlier regressions:',m0['passed']+m1['passed'],'/',m0['run']+m1['run'])
print('B7 matrix checks:',sum(ok for _,ok in checks),'/',len(checks))
print('Student U unitarity max error:',result['diagnostics']['unitarity_error'])
print('M1 S2 CORE:',result['core_passed'])
raise SystemExit(0 if result['core_passed'] else 1)
