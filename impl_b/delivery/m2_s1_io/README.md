# M2 S1 boundary and I/O plan

Logical boundary only: 10 proposed optical interfaces, 14 phase drive endpoints
and one logical shared return. These are not fabricated PAD counts or completed
edge couplers. Physical positions, cells, PAD IDs, voltage/current values and
heater calibration remain pending subsequent M2 steps.

boundary_plan.json is bound to m1_pic_spec.json by SHA-256. Original M1 files
and delivery/m1_handoff remain unchanged. All five outputs are preserved:
out1 -> PD_PLUS, out3 -> PD_MINUS; other outputs -> external monitor/load paths.
R amplitude 3 / power 9 refers to the normalized M1 core plane, not laser watts.
Source/receiver path gains and relative phases require calibration.
