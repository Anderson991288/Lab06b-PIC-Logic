from pathlib import Path
from datetime import datetime,timezone,timedelta
import os,sys,json,hashlib,subprocess,csv
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;OUT=HERE/'out'
os.environ['MPLCONFIGDIR']=str(HERE/'work/matplotlib')
for key in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:os.environ[key]='1'
sys.path.insert(0,str(ROOT/'work'))
from common import chip_interfaces as chip,handoff
import cornerstone
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
c=load(ROOT/'config/m2_chip_interfaces.json');current=load(ROOT/c['current_core_index'])
assert current['accepted_at_step']=='M2 S4' and current['m1_spec_sha256']==handoff.digest(ROOT/'pic_spec.json')
assert handoff.digest(ROOT/current['layout_config'])==current['layout_config_sha256']
for rel,digest in current['files'].items():assert (ROOT/rel).resolve().is_relative_to(ROOT) and handoff.digest(ROOT/rel)==digest
core_path=next(ROOT/p for p in current['files'] if p.endswith('/b7_core.gds'));core_info=load(next(ROOT/p for p in current['files'] if p.endswith('/layout_info.json')))
spec,phases=handoff.load_bundle(ROOT/'delivery/m1_handoff');boundary=load(ROOT/'config/m2_boundary.json')
cell,info=chip.build(core_info,c,boundary,spec);cell.get_default_view(chip.i3.LayoutView).write_gdsii(str(OUT/'chip_interfaces.gds'))
info['accepted_core_index']=current;info['core_source']=str(core_path.relative_to(ROOT));save(OUT/'chip_info.json',info)
tools=load(ROOT/'EDA_paths.json');exe=Path(tools['windows']['klayout_exe']);exe=exe if exe.is_absolute() else ROOT/exe
args=dict(out_folder=OUT,core_gds=core_path,figure_folder=ROOT/'course/figures/m2_s5')
cmd=[str(exe),'-b','-r',str(HERE/'merge_verify.py')]
for k,v in args.items():cmd+=['-rd',str(k)+'='+str(v)]
r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
(OUT/'chip_readback.log').write_text(r.stdout+'\n'+r.stderr,encoding='utf-8');print(r.stdout,flush=True)
if r.returncode:raise RuntimeError(r.stderr[-1800:])
readback=load(OUT/'chip_readback.json')
audit=dict(pdk_version=cornerstone.__version__,EC_exported_names=[n for n in dir(chip.pdk.pdk) if 'edgecoupl' in n.lower().replace('_','') or 'spot_size' in n.lower()],
    EC_kind='custom_reference_geometry; no qualified EC found in installed exported PDK namespace',layer_map={3:'WG DRAWING',4:'WG HOLE partial etch window',5:'SLAB DRAWING',39:'HT DRAWING',41:'PAD DRAWING'},
    reference='reference/C01/m2_chip_layout.py EC recipe; PDK mapping audited locally',optical_calibration=None)
save(OUT/'EC_audit.json',audit)
tables={
    'pad_heater_map.csv':[dict(pad_id=p['pad_id'],driver_channel=p['driver_channel'],interface_id=p['interface_id'],phase_channel=p['channel'],heater=p['heater_logical_id'],drive_endpoint=p['drive_endpoint'],return_endpoint=p['return_endpoint'],pad_x_um=p['center_um'][0],pad_y_um=p['center_um'][1],A_x_um=p['signal_contact_um'][0],A_y_um=p['signal_contact_um'][1],B_x_um=p['return_contact_um'][0],B_y_um=p['return_contact_um'][1],heater_x_um=p['heater_center_um'][0],heater_y_um=p['heater_center_um'][1],return_net='GND',voltage_calibration='pending') for p in info['pads'] if p['net']!='GND'],
    'optical_io.csv':[dict(interface=p['interface_id'],EC=p['EC_id'],core_port=p['core_port'],external_endpoint=p['external_endpoint'],facet_x_um=p['facet_um'][0],facet_y_um=p['facet_um'][1],core_x_um=p['core_um'][0],core_y_um=p['core_um'][1],coupling_loss_db='pending',path_phase_rad='pending') for p in info['optical_io']],
    'ground_pads.csv':[dict(pad_id=p['pad_id'],net='GND',driver_return=p['driver_channel'],x_um=p['center_um'][0],y_um=p['center_um'][1],common_impedance='pending') for p in info['pads'] if p['net']=='GND'],
    'fan_lengths.csv':[dict(route=p['id'],direction=p['direction'],mode=p['mode'],length_um=p['length_um'],continuous_min_radius_um=p['continuous_min_radius_um']) for p in info['optical_routes']]}
for name,rows in tables.items():
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    with (OUT/name).open(encoding='utf-8-sig',newline='') as f:assert list(csv.DictReader(f))==[{k:'' if v is None else str(v) for k,v in row.items()} for row in rows]
sources=['config/m2_chip_interfaces.json','config/m2_current_core.json','work/common/chip_interfaces.py','work/m2_s5/build_chip.py','work/m2_s5/merge_verify.py','work/m2_s5/electrical_geometry.py']
save(OUT/'chip_build.json',dict(timestamp=datetime.now(timezone(timedelta(hours=8))).isoformat(),root=str(ROOT),counts=info['counts'],chip_size_um=info['chip_size_um'],
    readback=readback,EC_audit=audit,source_hashes={p:handoff.digest(ROOT/p) for p in sources},current_core_hashes=current['files']))
print('Chip size',info['chip_size_um'],'counts',info['counts'],flush=True)
raise SystemExit(0 if readback['passed'] else 1)
