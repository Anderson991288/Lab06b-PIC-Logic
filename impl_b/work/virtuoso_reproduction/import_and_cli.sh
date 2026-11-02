#!/usr/bin/env bash
set -eu
TASK=/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction
cd "$TASK/work/oa"
strmin -library LAB06B_REPRO_20261031 -strmFile "$TASK/out/input/B7_source.gds" -topCell LAB06B_B7_EC_PAD_CHIP -view layout -dbuPerUU 1000 -logFile "$TASK/out/import/streamIn.log" -summaryFile "$TASK/out/import/streamIn_summary.txt" > "$TASK/out/import/console.log" 2>&1
printf 'Current GDS Stream In process completed\n'
for name in accepted negative; do
  cd "$TASK/out/cli_$name"
  calibre -drc -hier -64 "$TASK/out/rules/$name.svrf" > run.log 2>&1
  printf 'Calibre CLI %s completed\n' "$name"
done
