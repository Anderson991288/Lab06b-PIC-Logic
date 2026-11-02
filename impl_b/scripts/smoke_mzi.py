"""M0 S1: standard-library, lossless MZI check; not a device/PDK simulation."""
from pathlib import Path
import argparse
import cmath
import json
import math


def mmi(v):
    a, b = v
    return [(a + 1j * b) / math.sqrt(2), (1j * a + b) / math.sqrt(2)]


def mzi(v, theta):
    a, b = mmi(v)
    return mmi([a, b * cmath.exp(1j * theta)])


def run():
    # Index 0 = lower port in1/out1, index 1 = upper port in2/out2.
    # theta acts on upper arm, matching the Lab01a field script convention.
    cases = [
        ('cross', [1, 0], 0, [0, 1]),
        ('split', [1, 0], math.pi / 2, [0.5, 0.5]),
        ('bar', [1, 0], math.pi, [1, 0]),
        ('combine_pi', [1 / math.sqrt(2), -1 / math.sqrt(2)], math.pi / 2, [1, 0]),
        ('combine_0', [1 / math.sqrt(2), 1 / math.sqrt(2)], math.pi / 2, [0, 1]),
    ]
    results = []
    for name, v, theta, expected in cases:
        field = mzi(v, theta)
        power = [abs(z) ** 2 for z in field]
        pin = sum(abs(z) ** 2 for z in v)
        error = max(abs(a - b) for a, b in zip(power, expected))
        passed = error < 1e-12 and abs(sum(power) - pin) < 1e-12
        results.append(dict(name=name, theta_rad=theta, input_field=[[complex(z).real, complex(z).imag] for z in v],
                            output_field=[[z.real, z.imag] for z in field],
                            output_power=power, expected_power=expected, input_power=pin,
                            max_error=error, passed=passed))
    return dict(scope='ideal lossless MZI, standard library; no PDK, FDTD, thermal or layout verification',
                port_convention='index 0 lower in1/out1; index 1 upper in2/out2; theta on upper arm',
                passed=all(r['passed'] for r in results), cases=results)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'evidence/m0_s1/smoke_mzi.json')
    args = parser.parse_args()
    report = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    for row in report['cases']:
        print(row['name'], ['%.6f' % p for p in row['output_power']], 'PASS' if row['passed'] else 'FAIL')
    print('5/5 PASS' if report['passed'] else 'FAILED')
    raise SystemExit(0 if report['passed'] else 1)
