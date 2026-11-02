# C:\EDA_Claude — Claude's version of the Lab06b course (written by Claude)

Everything here was written by Claude. Since 2026-10-31 this folder is where all of Claude's course work
happens; the D: drive is read only (Codex builds its own version in D:\LAB\Lab06b at the same time).

```
C:\EDA_Claude
├─ Lab06b_index.html  course index (entry to every readable page)
├─ EDA_paths.json     single source of truth for every tool path and read-only source
├─ env\eda_env.ps1    Windows: . C:\EDA_Claude\env\eda_env.ps1
├─ env\eda_env.sh     WSL Ubuntu (user yangpc): source /mnt/c/EDA_Claude/env/eda_env.sh
├─ course\            one page per step, course.css, figures\
└─ work\              common\ (pdk, drc, gds2png, runtime, DRC deck), m0_s1\, m0_s2\ ...
```

| What | Real location |
|---|---|
| IPKISS 2026.3.3 (ipkiss3 env) | `C:\luceda\luceda_2026033\envs\ipkiss3\python.exe` |
| device_sim (via conda run) | `C:\luceda\luceda_2026033\envs\device_sim` (femwell 0.1.12, numpy 1.26.4) |
| CORNERSTONE PDK | `%USERPROFILE%\luceda\libraries\cornerstone_2.6.luceda1` |
| KLayout | `%APPDATA%\KLayout\klayout_app.exe` (0.30.12 official win64 zip, installed 2026-10-30) |
| DRC deck | `C:\EDA_Claude\work\common\drc\cornerstone_Si220_passive.lydrc` |
| Meep 1.35.0 | WSL Ubuntu user `yangpc` (no user `hans` on this machine), `~/miniforge3`, env `meep` |

WSL: only the Ubuntu distro is used. EDA_Server is never called.
Reader-facing pages show no local paths and no other project names; real paths live only in evidence JSON.

History:
- 2026-10-30 created as `C:\EDA` with junctions; same day renamed to `C:\EDA_Claude`, junctions removed.
- 2026-10-31 course moved here from D:\LAB\Lab06b (my own files copied; D: left untouched).
  M0 s1 rerun here: 15/15 checks pass.
  M0 s2 done: femwell modes + EIM, Meep 2D MMI (16/24/32 px/µm) and MZI four states at 24 px/µm
  (each MZI case ~4.1 h on 1 core); max error vs ideal 0.019, extinction 25–29 dB.
  M0 s3 done: work/common/mzi.py (original T(θ,φ) convention + layout_to_model), 13/13 unit tests,
  7/7 fault injections caught, model vs FDTD max diff 0.019.
  M1 s1 done: work/common/b7.py (OPS, I/O, encode, delta_p, decide); single MZI realizes 7/14 two-input
  functions (exactly those with f(00)=0), with reference light 14/14.
  M1 s2 done: b7.unitary/trace/paths cross-checked; 10/10 tests (golden: all-cross permutation and the
  original course's U via sources/reference_b7.json); 7/7 assembly faults caught.
  M1 s3 done: b7.readout_form (ΔP as quadratic form in bits); hand calc 1000/1100 matches original;
  6/6 readout tests; five common calculation mistakes compared (demo + 200 random settings).
  M1 s4 done: sources/b7_phases.json (shared phases, from the original course); 80/80 truth table rows,
  identical to original; XOR2 margin 0.25 relies on data×data cross terms; NAND2 phases synthesized.
  M1 s5 done: spec/pic_spec.json + spec/truth_table.json (phases referenced by SHA-256, not copied);
  independent checker 10/10 (rebuilds B7 from spec via mzi.py only), 7/7 spec faults caught.
  common/b7plot.py extracted; M1 s2 reran with it, results unchanged.
  M2 s1 done: spec/io_table.json (25 interfaces) + spec/external_requirements.json (PD mismatch, R amplitude/phase,
  extinction ratio, data phase/amplitude tolerances; AND4 most sensitive to R).
  M2 s2 done: work/common/b7_circuit.py (netlist from spec only; PDK MMI + ideal phase cells in Caphe) and
  spec/netlist.json (7 MZI, 9 links, 10 ports); 80/80, U vs NumPy 1.2e-15; 7/7 wiring faults caught by U compare
  (o1/o5 swap invisible to the 80 rows); PDK circuit models are ideal (MMI = H, waveguide default n_eff 1, n_g 2);
  arm-length rule ΔL·|Δλ| ≤ 1.84e-3 µm² (femwell n_g, 0.02 rad residual).
  M2 s3 done: work/common/b7_layout.py (MZI 489 µm column, 30 µm pitch, path-matched bypass 510.133 µm,
  NetlistFromLayout + HierarchicalModel, calibrate()); b7_core.gds DRC 0; extracted netlist == spec/netlist.json;
  layout circuit 80/80 at 1530–1570 nm without recalibration; 5 layout faults (offset, wrong rail, flip,
  straight bypass, arm +2 µm) each caught by DRC / netlist compare / path-match check. MMI phase = strip-equivalent (assumption).
  M2 s4 done: work/m2_s4/review_layout.py reads GDS only (Shapely), 8 checks vs spec: placement, ports, Si gap (min 0.53 µm),
  20 path lengths by area/width (spread 7e-12 µm), heater→channel mapping, contacts, metal spacing, outline; all pass on
  b7_core.gds; all 5 s3 fault GDS caught (no single check catches all). No GDS changes.
  M2 s5 done: work/common/b7_chip.py; b7_chip.gds 3876×1200 µm with the unchanged s3 core (polygon-identical), 10 self-built
  thin-Si edge couplers (GDS 3/4/5, 250 µm pitch), length-matched fan-in (bumps, spread 2e-5 µm), single-metal routing
  (signals to 14 pads, returns to outer buses GND_T/GND_B); DRC 0; chip circuit 80/80 at 1530–1570 nm; GDS read-back
  electrical check (16 nets, no shorts/opens), 24 metal-over-straight-waveguide crossings; 4 interface faults caught.
  M2 s6 done: work/m2_s6/verify_chip.py; DRC 0 on the frozen chip, every used rule (12) + design area proven to fire by
  injected shapes; GDS-only optical LVS (MMI bodies recognised, 33 wires, 7 MZI, links/ports/heaters == spec);
  GDS-only electrical check (14 channels, heater 111.11 squares); 6 fault GDS caught; b7_chip_checked.gds + signoff.json.
  LVS/electrical functions moved to work/common/gds_verify.py (s6 rerun unchanged).
  M2 s7 done: work/m2_s7/package.py -> out/PIC_delivery + B7_PIC_delivery.zip (53 files, sources path-sanitised, no DRC deck);
  unzip re-check using only package files: manifest SHA-256, verify_gds (LVS/electrical), rebuild_gds (969 polygons identical),
  DRC 0, 1-byte tamper detected. Module M2 complete.
  M3 s1 done: work/m3_s1/rebuild_all.py rebuilds M0 s2 -> M2 s7 (20 scripts, ~7 min) in work/m3_s1/out/rebuild from scripts +
  read-only references (Meep field files reused, SHA-256 recorded); 126 outputs: 70 identical, 56 equivalent (GDS timestamp,
  hash cascade, lyrdb marker order, femwell 1e-14 noise, one PNG 1-gray-level), 0 different; tampered phase file stops M2 s2.
  `--compare-only` re-runs just the comparison.
  M3 s2 done: work/m3_s2/independent_drc.py, own edge-pair width/space check (euclidean, facing test, 45° angle limit,
  -0.001 µm margin) vs KLayout: final GDS 0/0; measured minima Si width 0.350, GDS5 0.250 (zero margin, EC), Si gap 0.53;
  s6 rule faults 12/12 and 11 edge cases 11/11 agree; without the angle limit C6/C7/C9/C10 differ. Course complete.
- 2026-10-31 pages made single-file: work/common/inline_page.py embeds course.css and figures/ (data URIs, keeps data-href /
  data-src so it can re-run); every build_page.py calls it at the end. Pages stay < 480 KB (the app's file preview limit is
  512 KB); m0_s2 images are re-encoded as 256-colour PNG for the page only. Run `inline_page.py` alone to refresh all pages
  after redrawing figures without rebuilding tables.
- 2026-11-01 M2 s7 Virtuoso/Calibre part added (batch only, user-approved use of the EDA_Server distro; nothing installed or
  reconfigured there; work dirs ~/claude_b7/ in that distro). work/m2_s7/eda/: virtuoso.sh (strmin -> OA -> SKILL stats ->
  strmout default and -maxVertices 8191), calibre.sh (calibre -drc -hier on 6 inputs), cornerstone_pre_drc.svrf (own SVRF
  translation, 22 checks; GDS6/60 rules not translated, guarded by "layer must be empty"), compare.py (KLayout XOR + pre-DRC,
  Calibre parse, figure). Results: import 0/0; 8191 export XOR 0 on 7 layers, both engines 0; default export chops 15 curves
  (51 -> 80 GDS3 polygons) and the platform deck reports 16 GDS3 width markers at 8 seams because its
  `soi_etch2_light_layer.raw.sized(...)` line switches GDS3 to raw (per-polygon) mode, while Calibre merges first (0).
  Calibre vs KLayout: rule faults 12/12, design-area fault, edge cases 11/11 identical. The distro boots on first call and its
  Cadence license daemon needs ~1 min before Virtuoso can check out a license. Not part of the M3 s1 clean rebuild.
