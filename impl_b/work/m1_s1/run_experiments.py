"""Rebuild M1 S1 experiments, tests, CSV and scientific figures."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import os, sys, json, hashlib, io, unittest, importlib.util, csv
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = HERE/'out'; FIG = ROOT/'course/figures/m1_s1'
OUT.mkdir(parents=True, exist_ok=True); FIG.mkdir(parents=True, exist_ok=True)
for key in ['OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS']: os.environ[key] = '1'
os.environ['MPLCONFIGDIR'] = str(ROOT/'work/.matplotlib')
DLL_HANDLE = None
if os.name == 'nt' and (Path(sys.prefix)/'Library/bin').is_dir():
    DLL_HANDLE = os.add_dll_directory(str(Path(sys.prefix)/'Library/bin'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.family': ['Microsoft JhengHei', 'DejaVu Sans'], 'axes.unicode_minus': False})
sys.path[:0] = [str(ROOT/'work'), str(HERE)]
from common import encoding, mzi, photodetection as pd
from experiments import and2, nand2, nand_matrix


def suite(path, classname, logfile):
    spec = importlib.util.spec_from_file_location(classname, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(getattr(module, classname)))
    (OUT/logfile).write_text(stream.getvalue(), encoding='utf-8')
    return {'run': result.testsRun, 'passed': result.testsRun-len(result.failures)-len(result.errors),
            'failures': len(result.failures), 'errors': len(result.errors), 'successful': result.wasSuccessful()}


def pairs(field): return [[float(z.real), float(z.imag)] for z in field]


def row(a, b, kind, **kwargs):
    inp, out, read = (and2 if kind == 'AND2' else nand2)([a, b], **kwargs)
    expected = a & b if kind == 'AND2' else 1-(a & b)
    return dict(bits=[a, b], expected=expected, input_field=pairs(inp), output_field=pairs(out),
                input_power=float(sum(mzi.powers(inp))), output_powers=mzi.powers(out).tolist(),
                output_total_power=float(sum(mzi.powers(out))), readout=read,
                signed_margin=float((2*expected-1)*read['margin']), correct=read['bit'] == expected)


tests = suite(HERE/'test_encoding_readout.py', 'EncodingReadout', 'unit_tests.log')
regression = suite(ROOT/'work/m0_s3/test_optical_models.py', 'OpticalModels', 'm0_s3_regression.log')
patterns = [(0, 0), (0, 1), (1, 0), (1, 1)]
and_table = [row(a, b, 'AND2') for a, b in patterns]
nand_table = [row(a, b, 'NAND2') for a, b in patterns]
fault_tables = {
    'AND2_relative_phase_pi': [row(a, b, 'AND2', relative_phase=np.pi) for a, b in patterns],
    'NAND2_reference_off': [row(a, b, 'NAND2', reference_amplitude=0) for a, b in patterns],
    'NAND2_reference_phase_pi': [row(a, b, 'NAND2', reference_phase=np.pi) for a, b in patterns],
    'NAND2_reference_amplitude_3': [row(a, b, 'NAND2', reference_amplitude=3) for a, b in patterns]}
config = json.loads((ROOT/'config/m1_s1_example.json').read_text(encoding='utf-8'))
student_and = row(*config['bits'], 'AND2', relative_phase=config['and_relative_phase_pi']*np.pi,
                  threshold=config['and_threshold'], loss_db=config['and_loss_db'])
student_nand = row(*config['bits'], 'NAND2', reference_amplitude=config['nand_reference_amplitude'],
                   reference_phase=config['nand_reference_phase_pi']*np.pi, threshold=config['nand_threshold'])
student_out = np.array([complex(*z) for z in student_and['output_field']])
receiver = pd.differential_receiver(student_out, 0, 1, config['power_unit_w'],
    config['responsivity_a_per_w'], config['transimpedance_v_per_a'], config['and_threshold'])
encoded = []
for value in range(16):
    bits = [(value >> i) & 1 for i in range(4)]
    field = encoding.with_reference(bits)
    encoded.append({'pattern_index_lsb_x1': value, 'bits': bits, 'field': pairs(field),
                    'total_power': float(sum(mzi.powers(field)))})
with (OUT/'truth_tables.csv').open('w', newline='', encoding='utf-8-sig') as f:
    writer = csv.writer(f); writer.writerow(['experiment', 'x1', 'x2', 'Pout0', 'Pout1', 'Pout2',
        'input_total', 'output_total', 'margin', 'bit', 'expected', 'correct'])
    for name, rows in [('AND2_baseline', and_table), ('NAND2_baseline', nand_table), *fault_tables.items()]:
        for r in rows:
            powers = r['output_powers']+[None]*(3-len(r['output_powers']))
            writer.writerow([name, *r['bits'], *powers, r['input_power'], r['output_total_power'],
                r['readout']['margin'], r['readout']['bit'], r['expected'], r['correct']])
with (OUT/'b7_input_encoding.csv').open('w', newline='', encoding='utf-8-sig') as f:
    writer = csv.writer(f); writer.writerow(['index_lsb_x1', 'x1', 'x2', 'x3', 'x4', 'R_field', 'R_power', 'total_power'])
    for r in encoded: writer.writerow([r['pattern_index_lsb_x1'], *r['bits'], 3, 9, r['total_power']])

# Each plotted sample is calculated through the shared complex matrices.
angles = np.linspace(-np.pi, np.pi, 361)
delta = [and2([1, 1], phase)[2]['delta'] for phase in angles]
phase_average = np.mean([mzi.powers(and2([1, 1], phase)[1]) for phase in 2*np.pi*np.arange(64)/64], axis=0)
fig, axes = plt.subplots(1, 3, figsize=(15, 4.7), constrained_layout=True)
axes[0].plot(angles/np.pi, delta, label='11：ΔP')
axes[0].axhline(1., color='#a65c16', linestyle='--', label='固定門檻 T=1')
axes[0].set(xlabel='資料相對相位 / π', ylabel='歸一化功率差', title='AND2：同樣位元，相位不同')
axes[0].legend(fontsize=9)
for a, b in patterns:
    powers = [nand2([a, b], reference_phase=phase)[2]['power'] for phase in angles]
    axes[1].plot(angles/np.pi, powers, label=f'{a}{b}')
axes[1].axhline(1/6, color='black', linestyle='--', label='T=1/6')
axes[1].set(xlabel='參考光相位 / π', ylabel='P(out0)', title='NAND2：R=2，三路無損網路')
axes[1].legend(fontsize=9)
amplitudes = np.linspace(0., 3.2, 321)
minimum_margin = [min(row(a, b, 'NAND2', reference_amplitude=amp)['signed_margin'] for a, b in patterns) for amp in amplitudes]
axes[2].plot(amplitudes, minimum_margin)
axes[2].axhline(0, color='black', linestyle='--')
axes[2].axvline(2, color='#a65c16', linestyle=':')
axes[2].set(xlabel='參考光振幅 R（功率為 R²）', ylabel='四組輸入最小有號裕量', title='固定相位／門檻：R 並非越大越好')
for ax in axes: ax.grid(alpha=.22)
fig.savefig(FIG/'encoding_readout.png', dpi=155); plt.close(fig)

checks = [
    ('AND2_fixed_truth', all(r['correct'] for r in and_table)),
    ('NAND2_fixed_truth', all(r['correct'] for r in nand_table)),
    ('all_outputs_conserve_power', all(abs(r['input_power']-r['output_total_power']) < 1e-12
        for rows in [and_table, nand_table, *fault_tables.values()] for r in rows)),
    ('B7_16_input_encodings', all(abs(r['total_power']-(sum(r['bits'])+9)) < 1e-12 for r in encoded)),
    ('incoherent_phase_average', bool(np.allclose(phase_average, [1, 1], atol=1e-12))),
    ('reference_off_exposes_zero_input_limit', fault_tables['NAND2_reference_off'][0]['readout']['bit'] == 0),
    ('relative_phase_error_exposed', not fault_tables['AND2_relative_phase_pi'][-1]['correct']),
    ('reference_phase_error_exposed', not fault_tables['NAND2_reference_phase_pi'][-1]['correct'])]
samples = []
for kind, a, b, amp, phase in [('AND2', 0, 0, 2., 0.), ('AND2', 1, 1, 2., 0.),
    ('AND2', 1, 1, 2., .5), ('AND2', 1, 1, 2., 1.), ('NAND2', 0, 0, 2., 0.),
    ('NAND2', 0, 1, 2., 0.), ('NAND2', 1, 1, 2., 0.), ('NAND2', 1, 1, 0., 0.),
    ('NAND2', 1, 1, 2., 1.), ('NAND2', 1, 1, 3., 0.)]:
    sample = row(a, b, kind, **({'relative_phase': phase*np.pi} if kind == 'AND2'
        else {'reference_amplitude': amp, 'reference_phase': phase*np.pi}))
    samples.append(dict(kind=kind, bits=[a, b], amplitude=amp, phase_pi=phase,
                        output_powers=sample['output_powers'], readout=sample['readout']))
sources = ['work/common/encoding.py', 'work/common/photodetection.py', 'work/common/mzi.py',
    'work/common/linear_network.py', 'work/m1_s1/experiments.py', 'work/m1_s1/test_encoding_readout.py',
    'work/m1_s1/run_experiments.py', 'config/m1_s1_example.json']
result = dict(step='M1 S1', timestamp=datetime.now(timezone(timedelta(hours=8))).isoformat(),
    root=str(ROOT), root_matches_plan=ROOT.resolve() == Path('C:/EDA_Codex/Lab06b').resolve(),
    python=sys.executable, numpy_version=np.__version__, unit_tests=tests, m0_s3_regression=regression,
    baseline={'AND2': and_table, 'NAND2': nand_table}, perturbations=fault_tables,
    b7_input_encodings=encoded, incoherent_phase_average_powers=phase_average.tolist(),
    student_example=dict(config=config, AND2=student_and, NAND2=student_nand, receiver=receiver),
    checks=[{'name': name, 'passed': bool(ok)} for name, ok in checks],
    interactive_samples=samples,
    source_hashes={rel: hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in sources},
    core_passed=tests['successful'] and regression['successful'] and all(ok for _, ok in checks),
    scope='New ideal optical encoding and two/three-mode experiments; no B7 phase synthesis, PDK, dynamic receiver or chip validation.')
(OUT/'encoding_results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print('M1 S1 tests:', tests)
print('M0 S3 regression:', regression)
print('Fixed AND2/NAND2 truth:', sum(r['correct'] for r in and_table+nand_table), '/ 8')
print('Experiment checks:', sum(ok for _, ok in checks), '/', len(checks))
print('M1 S1 CORE:', result['core_passed'])
raise SystemExit(0 if result['core_passed'] else 1)
