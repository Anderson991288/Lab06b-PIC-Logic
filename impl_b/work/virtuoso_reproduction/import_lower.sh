#!/usr/bin/env bash
set -eu
TASK=/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction
mkdir -p "$TASK/work/oa_lower"
cd "$TASK/work/oa_lower"
strmin -library lab06b_current_20261031 -strmFile "$TASK/out/input/B7_source.gds" -topCell LAB06B_B7_EC_PAD_CHIP -case lower -labelCase preserve -view layout -dbuPerUU 1000 -logFile "$TASK/out/import/streamIn_lower.log" -summaryFile "$TASK/out/import/streamIn_lower_summary.txt" > "$TASK/out/import/lower_console.log" 2>&1
printf 'Explicit lower-case OA cell-name import completed; original GDS unchanged\n'
