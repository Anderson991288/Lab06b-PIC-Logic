#!/usr/bin/env bash
set -eu
TASK=/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction
cd "$TASK/work/oa_lower"
for limit in 200 8191; do
  strmout -library lab06b_current_20261031 -topCell lab06b_b7_ec_pad_chip -view layout -strmFile "$TASK/out/exports/B7_max${limit}.gds" -layerMap "$TASK/out/exports/layer.map" -cellMap "$TASK/out/exports/cell.map" -maxVertices "$limit" -dbuPerUU 1000 -labelCase preserve -logFile "$TASK/out/exports/streamOut_${limit}.log" > "$TASK/out/exports/console_${limit}.log" 2>&1
  printf 'OA Stream Out maxVertices=%s completed\n' "$limit"
done
