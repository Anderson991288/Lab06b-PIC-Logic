# Lab06b M2 PIC teaching delivery

This is a review/replay package, not a fabrication release or calibrated chip.
The GDS is byte-identical to the accepted S6 revision. Original M1 specification
and phases are preserved. SHA-256 checks detect changes; they are not a digital
signature or proof of provenance from a trusted signer.

## Portable commands

Tested with Python 3.12.13 / NumPy 1.26.4, Windows native runtime:

    python verify_delivery.py
    python replay_delivery.py --out ../replay_output

The first command uses only the Python standard library. The second recomputes
five scenarios / 400 truth cases and compares all deltas with the archived data.
Windows conda DLL setup is handled inside the replay script, without editing
the user's environment configuration. No project drive paths are required.

Optional geometric/pre-DRC recheck requires external KLayout 0.30.12 and the
recorded original CORNERSTONE v3.1 pre-DRC deck, supplied separately:

    python recheck_geometry.py --klayout <klayout_app.exe> --deck <original.lydrc> --out ../geometry_output

The proprietary vendor deck, installed PDK, EDA binaries and licenses are not
redistributed. The external deck SHA is pinned in manifest.json. Area is checked
against this course's declared 3860 x 1640 um region, not foundry MPW allocation.
Source/project archives selected authored layout scripts and parameters; full
course/EDA rebuild uses the original C project and licensed installed tools.

## Reference plane and models

All numerical truth replay is at the M1 core ports (including the core leads).
68 centerline polylines (58 core, 10 fanout) are mapped to the actual GDS's 33
outside-MMI connections. Lengths are nominal grid-snapped polyline lengths,
not calibrated optical PEX. MMI body spans and EC tapers are not assigned the
single-mode propagation index.

Propagation is exp(+i 2 pi neff L/lambda), lambda=1.55 um, neff=2.353499831254645
from M0's uniform-oxide FEM example. Installed ideal H matrices are retained;
no calibrated absolute MMI phase is available. The 3 dB/cm loss scenario and
neff perturbations are teaching assumptions, not measured foundry data.

Original ideal phases pass 80/80 in the ideal baseline, then 53/80 after length
phase is included. Analytic per-rail phase tracking gives a separate model-only
candidate passing 80/80 in that model; it is not fitted to Boolean truth labels.
The residual output diagonal phases preserve powers. No heater voltage, Vpi,
EC loss/phase or physical-chip performance is inferred from this calculation.

## Contents

- layout: accepted GDS, top LAB06B_B7_EC_PAD_CHIP; 10 reference ECs,
  14 signal PADs, 2 GND PADs (one shared return).
- interfaces/data: optical/PAD/GND tables, geometry, paths and named phases.
- reports: unchanged pre-DRC zero-marker result, geometric connectivity,
  model replay, tests and sensitivity evidence.
- models/geometry: authored portable numerical and geometric checkers.
- source/project: selected layout sources, with external dependencies noted.

## Qualification still pending

Foundry full signoff/process LVS; qualified EC and fiber/packaging response;
absolute MMI phase/bend-specific model; thermal/common-ground/bias calibration;
and physical measured 80-case acceptance remain open. The course model's
80/80 is not experimental acceptance. Use phase_settings_backannotated.json
only as a model candidate; retain data/phase_settings.json as the M1 original.
