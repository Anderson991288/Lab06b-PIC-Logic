"""M0 S2: full-vector FEM strip mode, scalar MMI modal expansion, phase analysis.

The new MMI model is a uniform-body 2D effective-index teaching model, not Meep
FDTD or the tapered PDK device. Inherited FDTD arrays are independently labeled.
"""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import os,sys,json,hashlib,time

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent/'out'
FIG=ROOT/'course/figures/m0_s2'
OUT.mkdir(parents=True,exist_ok=True);FIG.mkdir(parents=True,exist_ok=True)
for key in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS']:
    os.environ[key]='1'
os.environ['MPLCONFIGDIR']=str(ROOT/'work/.matplotlib')
DLL_HANDLE=None
if os.name=='nt' and (Path(sys.prefix)/'Library/bin').is_dir():
    DLL_HANDLE=os.add_dll_directory(str(Path(sys.prefix)/'Library/bin'))
import importlib.metadata as metadata
import numpy as np
import scipy
from scipy.linalg import eigh_tridiagonal
from skfem import MeshTri,Basis,ElementTriP0
from femwell.maxwell.waveguide import compute_modes
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.family':['Microsoft JhengHei','DejaVu Sans'],'axes.unicode_minus':False,'figure.dpi':130})
np.random.seed(7)

CONFIG_PATH=ROOT/'config/m0_s2.json'
CONFIG=json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
LAM=float(CONFIG['wavelength_um']);N_SI=float(CONFIG['n_si']);N_OX=float(CONFIG['n_oxide'])
HEIGHT=float(CONFIG['strip_height_um']);WIDTH=float(CONFIG['strip_width_um'])


def axis(half,corehalf,ncore,nouter):
    return np.unique(np.r_[np.linspace(-half,-corehalf,nouter+1),np.linspace(-corehalf,corehalf,ncore+1),np.linspace(corehalf,half,nouter+1)])


def strip_mode(label,nx,ny,width=WIDTH,domain=(1.5,1.0),save=False):
    started=time.perf_counter()
    x=axis(domain[0],width/2,nx,max(10,round(domain[0]/.12)))
    y=axis(domain[1],HEIGHT/2,ny,max(10,round(domain[1]/.10)))
    mesh=MeshTri.init_tensor(x,y)
    mesh=mesh.with_subdomains({'core':lambda X:(abs(X[0])<width/2)&(abs(X[1])<HEIGHT/2),
                               'oxide':lambda X:(abs(X[0])>width/2)|(abs(X[1])>HEIGHT/2)})
    basis=Basis(mesh,ElementTriP0())
    centers=mesh.p[:,mesh.t].mean(axis=1)
    core=(abs(centers[0])<width/2+1e-10)&(abs(centers[1])<HEIGHT/2+1e-10)
    eps=np.full(basis.N,N_OX**2)
    eps[core]=N_SI**2
    modes=compute_modes(basis,eps,wavelength=LAM,num_modes=4,order=2,metallic_boundaries=True,n_guess=2.4)
    candidates=[m for m in modes if .7<float(np.real(m.te_fraction)) and N_OX<float(np.real(m.n_eff))<N_SI and abs(float(np.imag(m.n_eff)))<1e-7]
    if not candidates:raise RuntimeError('No guided quasi-TE candidate: '+str([(complex(m.n_eff),float(m.te_fraction)) for m in modes]))
    mode=max(candidates,key=lambda m:np.real(m.n_eff))
    (ex,ey),ez=mode.basis.interpolate(mode.E)
    coordinates=mode.basis.global_coordinates().value
    inside=(abs(coordinates[0])<width/2)&(abs(coordinates[1])<HEIGHT/2)
    q=abs(ex)**2+abs(ey)**2+abs(ez)**2
    weights=mode.basis.dx
    material=np.where(inside,N_SI**2,N_OX**2)
    gamma=float(np.sum(material*q*weights*inside)/np.sum(material*q*weights))
    row=dict(label=label,width_um=width,height_um=HEIGHT,domain_half_um=list(domain),core_divisions=[nx,ny],
             triangles=int(mesh.t.shape[1]),field_dofs=int(mode.basis.N),neff=float(np.real(mode.n_eff)),
             neff_imag=float(np.imag(mode.n_eff)),te_fraction=float(mode.te_fraction),
             electric_energy_core_fraction=gamma,runtime_s=round(time.perf_counter()-started,3))
    if save:
        figure,axs=plt.subplots(1,2,figsize=(10.5,4.1),constrained_layout=True)
        mode.plot_intensity(ax=axs[0],normalize=True)
        axs[0].add_patch(plt.Rectangle((-width/2,-HEIGHT/2),width,HEIGHT,fill=False,color='cyan',lw=1.1))
        axs[0].set(xlim=(-.9,.9),ylim=(-.7,.7),xlabel='x [µm]',ylabel='y [µm]',title=f'本輪 FEM 模態｜n_eff={row["neff"]:.6f}')
        axs[1].triplot(mesh.p[0],mesh.p[1],mesh.t.T,color='#477495',lw=.35)
        axs[1].set(xlim=(-.7,.7),ylim=(-.5,.5),xlabel='x [µm]',ylabel='y [µm]',title='三角形網格（核心邊界對齊）',aspect='equal')
        figure.savefig(FIG/'strip_mode.png',bbox_inches='tight');plt.close(figure)
        np.savez_compressed(OUT/'strip_mode_raw.npz',mesh_points=mesh.p,mesh_triangles=mesh.t,epsilon=eps,E=mode.E,H=mode.H,
                            wavelength_um=LAM,width_um=width,height_um=HEIGHT,neff=complex(mode.n_eff))
    print('FEM',label,row['neff'],'TE fraction',row['te_fraction'],flush=True)
    return row


def mmi_expansion(dy,plot=False):
    # Scalar Helmholtz eigenmodes in a uniform 6-µm body, with oxide outside.
    y=np.arange(-7,7+dy/2,dy);step=float(y[1]-y[0]);yi=y[1:-1]
    k0=2*np.pi/LAM
    n=np.where(abs(yi)<3,N_SI*0+2.85,N_OX)
    diagonal=-2/step**2+k0**2*n**2
    beta2,phi=eigh_tridiagonal(diagonal,np.full(len(yi)-1,1/step**2),select='v',
                              select_range=((k0*N_OX)**2+1e-9,(k0*2.85)**2))
    beta=np.sqrt(beta2);phi=phi/np.sqrt(step)
    source=np.exp(-((yi+1.015)/.35)**2).astype(complex)
    source/=np.sqrt(np.sum(abs(source)**2)*step)
    a=phi.conj().T@source*step
    z=np.linspace(0,60,601)
    field=phi@(a[:,None]*np.exp(1j*beta[:,None]*z[None,:]))
    power=np.sum(abs(field)**2,axis=0)*step
    intensity=abs(field)**2
    pdklength=42.5;index=int(np.argmin(abs(z-pdklength)))
    upper=float(np.sum(intensity[yi>0,index])*step/power[index])
    row=dict(dy_um=step,guided_modes=len(beta),projected_input_norm=float(np.sum(abs(a)**2)),
             longitudinal_norm_max_error=float(np.max(abs(power-power[0]))),
             at_z_um=float(z[index]),upper_half_fraction=upper,lower_half_fraction=1-upper,
             metric_scope='Transverse half-plane integral, not output waveguide port coupling or PDK split ratio')
    if plot:
        norm=float(np.max(abs(source)**2))
        figure,ax=plt.subplots(figsize=(10.5,4.0),constrained_layout=True)
        im=ax.pcolormesh(z,yi,intensity/norm,shading='auto',cmap='turbo',vmin=0,vmax=.5)
        ax.axhline(3,color='white',ls='--',lw=.7);ax.axhline(-3,color='white',ls='--',lw=.7)
        ax.axvline(pdklength,color='white',ls=':',lw=1.2,label='42.5 µm 僅作長度對照')
        ax.set(xlabel='傳播方向 z [µm]',ylabel='橫向 y [µm]',ylim=(-4,4),title='本輪標量模態展開｜均勻 MMI 主體，非 FDTD／非完整 PDK 元件')
        ax.legend(loc='upper right',fontsize=8);figure.colorbar(im,ax=ax,label='|ψ|² / 輸入峰值（上限 0.5）')
        figure.savefig(FIG/'mmi_modal_field.png',bbox_inches='tight');plt.close(figure)
        np.savez_compressed(OUT/'mmi_modal_field.npz',y_um=yi,z_um=z,field=field,beta_um_inv=beta,coefficients=a,input_field=source)
    print('MMI scalar expansion',dy,'guided modes',len(beta),'upper half',upper,flush=True)
    return row


def phase_and_inherited():
    rows=[]
    for name,theta,expected in [('cross',0,[0,1]),('split',np.pi/2,[.5,.5]),('bar',np.pi,[1,0])]:
        power=[float(np.sin(theta/2)**2),float(np.cos(theta/2)**2)]
        rows.append(dict(case=name,theta_rad=theta,power=power,passed=bool(np.allclose(power,expected))))
    for label,sign,expected in [('combine_pi',-1,[1,0]),('combine_0',1,[0,1])]:
        H=np.array([[1,1j],[1j,1]])/np.sqrt(2)
        output=H@np.diag([1,np.exp(1j*np.pi/2)])@H@np.array([1,sign])/np.sqrt(2)
        power=(abs(output)**2).tolist()
        rows.append(dict(case=label,theta_rad=np.pi/2,power=power,passed=bool(np.allclose(power,expected))))
    inherited=[]
    for case in ['in1_t0','in1_tpi2','in12_tpi2']:
        path=ROOT/f'sources/Lab01a/out/tbu_field_{case}.npz'
        with np.load(path) as source:
            power=source['p_out'].astype(float)
            inherited.append(dict(case=case,power=power.tolist(),T=float(power.sum()),
                                  out1_fraction=float(power[0]/power.sum()),ER_dB=float(10*np.log10(max(power)/min(power))),
                                  source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),scope='Inherited Lab01a FDTD; arithmetic recomputed, no FDTD rerun'))
    theta=np.linspace(0,2*np.pi,401)
    fig,axs=plt.subplots(1,2,figsize=(10.5,3.8),constrained_layout=True)
    axs[0].plot(theta/np.pi,np.sin(theta/2)**2,label='out1（下）');axs[0].plot(theta/np.pi,np.cos(theta/2)**2,label='out2（上）')
    axs[0].set(xlabel='θ / π',ylabel='歸一化功率',title='單路輸入：理想 MZI');axs[0].legend();axs[0].grid(alpha=.2)
    axs[1].plot(theta/np.pi,(1+np.sin(theta))/2,label='相對相位 π → out1');axs[1].plot(theta/np.pi,(1-np.sin(theta))/2,label='相對相位 0 → out1')
    axs[1].set(xlabel='θ / π',ylabel='歸一化功率',title='雙路等功率：總入射功率固定為 1');axs[1].legend();axs[1].grid(alpha=.2)
    fig.savefig(FIG/'phase_power.png',bbox_inches='tight');plt.close(fig)
    return rows,inherited


started=time.perf_counter()
convergence=[strip_mode('coarse',6,4),strip_mode('medium',10,7),strip_mode('fine',16,10,save=True)]
expanded=strip_mode('expanded_domain',16,10,domain=(2.,1.5))
width_sweep=[convergence[-1] if abs(w-WIDTH)<1e-10 else strip_mode('width_'+str(w),16,10,width=w) for w in CONFIG['width_sweep_um']]
delta=abs(convergence[-1]['neff']-convergence[-2]['neff'])
domain_delta=abs(expanded['neff']-convergence[-1]['neff'])
scalar=[mmi_expansion(.04),mmi_expansion(.03),mmi_expansion(.02,plot=True)]
ideal,inherited=phase_and_inherited()
checks={'guided_quasi_TE':all(r['te_fraction']>.7 and N_OX<r['neff']<N_SI for r in convergence+width_sweep+[expanded]),
        'neff_mesh_delta_below_1e_3':delta<1e-3,'neff_domain_delta_below_1e_3':domain_delta<1e-3,
        'width_neff_monotonic':bool(np.all(np.diff([r['neff'] for r in width_sweep])>0)),
        'scalar_norm_error_below_1e_10':max(r['longitudinal_norm_max_error'] for r in scalar)<1e-10,
        'scalar_halfplane_grid_delta_below_2e_3':abs(scalar[-1]['upper_half_fraction']-scalar[-2]['upper_half_fraction'])<2e-3,
        'ideal_cases_5_of_5':all(r['passed'] for r in ideal),
        'inherited_data_finite':all(np.isfinite(r['T']) and r['T']>0 for r in inherited)}
report={'timestamp':datetime.now(timezone(timedelta(hours=8))).isoformat(),'step':'M0 S2','root':str(ROOT),
        'root_matches_plan':ROOT==Path('C:/EDA_Codex/Lab06b'),
        'versions':{name:metadata.version(name) for name in ['numpy','scipy','femwell','scikit-fem','matplotlib']},
        'python':sys.executable,'parameters':{'wavelength_um':LAM,'n_si':N_SI,'n_oxide':N_OX,'strip_width_um':WIDTH,'strip_height_um':HEIGHT,
        'cladding':'homogeneous SiO2, finite PEC calculation boundary; no substrate, air, heater, dispersion or leakage model'},
        'fem':{'convergence':convergence,'expanded_domain':expanded,'width_sweep':width_sweep,'mesh_neff_delta':delta,'domain_neff_delta':domain_delta},
        'new_scalar_propagation':{'scope':'Lossless scalar Helmholtz guided-mode expansion in uniform 6um MMI body, n_core_EIM=2.85; no taper, ports or reflection model; not FDTD', 'grids':scalar},
        'ideal_mzi':ideal,'inherited_fdtd':inherited,'checks':checks,'core_passed':all(checks.values()),
        'fdtd_rerun':{'status':'not_run','reason':'WSL inventory returned Wsl/E_ACCESSDENIED through this execution interface; Meep installation state is unverified'},
        'config_sha256':hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest(),
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'runtime_s':round(time.perf_counter()-started,2)}
(OUT/'physics_results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('M0 S2 CHECKS',checks,flush=True)
print('M0 S2 CORE',report['core_passed'],'runtime',report['runtime_s'],flush=True)
raise SystemExit(0 if report['core_passed'] else 2)
