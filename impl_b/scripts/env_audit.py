"""M0 S1 baseline audit. EDA imports are opt-in; audit never installs software."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import argparse
import importlib.metadata
import importlib.util
import json
import platform
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def package(name):
    try:
        spec = importlib.util.find_spec(name)
        if spec is None:
            return {'available': False, 'version': None}
        try:
            version = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            version = 'unknown (module discoverable)'
        return {'available': True, 'version': version, 'module_origin': spec.origin}
    except (ImportError, ValueError) as error:
        return {'available': False, 'error': str(error)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe-eda', action='store_true', help='Import IPKISS and CORNERSTONE in isolated child processes; may contact configured license service.')
    parser.add_argument('--output', type=Path, default=ROOT / 'evidence/m0_s1/environment.json')
    args = parser.parse_args()
    checks = []
    checks.append({'name': 'python_3_10_or_newer', 'passed': sys.version_info >= (3, 10)})
    for path in ['Lab06b_index.html', 'course/plan.html', 'course/m0_s1.html',
                 'analysis/lab01a_7_6.html', 'config/course.json', 'scripts/smoke_mzi.py']:
        checks.append({'name': 'file:' + path, 'passed': (ROOT / path).is_file()})
    out = ROOT / 'evidence/m0_s1'
    try:
        out.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=out) as handle:
            handle.write(b'lab06b-write-check')
            handle.flush()
        checks.append({'name': 'evidence_write', 'passed': True})
    except OSError as error:
        checks.append({'name': 'evidence_write', 'passed': False, 'error': str(error)})
    packages = {name: package(name) for name in ['numpy', 'matplotlib', 'ipkiss3', 'cornerstone', 'meep', 'klayout']}
    configured_tools = {}
    path_config = ROOT / 'EDA_paths.json'
    if path_config.is_file():
        try:
            config = json.loads(path_config.read_text(encoding='utf-8-sig'))
            configured_tools = {name: {'path': value, 'exists': bool(value) and (Path(value) if Path(value).is_absolute() else ROOT / value).exists()}
                                for name, value in config.get('windows', {}).items() if isinstance(value, str)}
        except (OSError, ValueError) as error:
            configured_tools = {'config_error': str(error)}
    probes = {}
    if args.probe_eda:
        for name, code in {'ipkiss3': 'import ipkiss3.all as i3; print(i3.__file__)',
                           'cornerstone': 'import cornerstone.all as cs; print(cs.__file__); print(cs.SOI220nm_1550nm_TE_STRIP_2x2_MMI().Layout().size_info())'}.items():
            try:
                proc = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=45)
                probes[name] = dict(passed=proc.returncode == 0, returncode=proc.returncode,
                                    stdout=proc.stdout[-2500:], stderr=proc.stderr[-2500:])
            except (OSError, subprocess.TimeoutExpired) as error:
                probes[name] = dict(passed=False, error=str(error))
    passed = all(check['passed'] for check in checks)
    report = dict(timestamp=datetime.now(timezone(timedelta(hours=8))).isoformat(),
                  root=str(ROOT), planned_root='C:/EDA_Codex/Lab06b',
                  root_matches_plan=ROOT == Path('C:/EDA_Codex/Lab06b'),
                  python=dict(executable=sys.executable, version=platform.python_version()),
                  system=platform.platform(), baseline_passed=passed, checks=checks,
                  packages=packages, executables={name: shutil.which(name) for name in ['wsl', 'klayout', 'calibre']},
                  path_config=str(path_config), configured_tools=configured_tools,
                  eda_probes=probes, eda_ready=bool(probes) and all(p['passed'] for p in probes.values()),
                  note='Module discovery is not a license check. No EDA simulation, DRC or FDTD has been executed by this audit.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('M0 S1 baseline:', 'PASS' if passed else 'FAIL')
    print('Python:', sys.executable)
    print('Root:', ROOT)
    print('EDA readiness:', 'probe passed; M0 S2 circuit validation still required' if report['eda_ready'] else 'NOT VALIDATED / see packages and eda_probes')
    print('Evidence:', args.output)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
