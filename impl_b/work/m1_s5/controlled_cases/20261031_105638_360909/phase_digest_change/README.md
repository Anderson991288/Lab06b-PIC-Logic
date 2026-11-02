# M1 → M2 logical B7 handoff

This is a portable ideal-model handoff, not a fabricated or PDK-verified chip.
Python >= 3.10 and NumPy are required; the optical model is included in model/.

Run with your numerical Python:
    python replay_handoff.py --gate AND2 --bits 1100

The consumer verifies SHA-256, schema and cross-file references, optical/phase
CSV tables, then recomputes all 80 truths and compares acceptance_truth.csv.
It loads model/common from this folder; no parent course/config directory is needed.
verification/replay_results.json is a regenerated output, excluded from the
immutable-file manifest. The manifest checks file consistency; semantic and
numerical checks are additional requirements.

pic_spec.json fixes the core topology, encoding, ten optical ports, fourteen
named phase channels, readout and acceptance. phase_settings.json binds to
the exact spec SHA-256 and declares its channel order. Values are full precision radians.
PAD IDs, physical optical interfaces and heater calibration remain pending M2.
Preserve unread output ports and the six bypass paths in subsequent physical work.
Do not treat phase in rad as heater voltage or the ideal replay as PDK approval.
