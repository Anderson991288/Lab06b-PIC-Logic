#!/usr/bin/env bash
set -eu
TASK=/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction
cd "$TASK/work/oa_crosscad"
strmout -library lab06b_crosscad_20261031 -topCell lab06b_b7_ec_pad_chip -view layout -strmFile "$TASK/out/exports_final/B7_crosscad_final.gds" -layerMap "$TASK/out/exports/layer.map" -cellMap "$TASK/out/exports_final/cell.map" -maxVertices 8191 -dbuPerUU 1000 -labelCase preserve -logFile "$TASK/out/exports_final/streamOut_8191.log" > "$TASK/out/exports_final/console.log" 2>&1
printf 'Final cross-CAD GDS exported from OA with explicit 8191 vertices\n'
