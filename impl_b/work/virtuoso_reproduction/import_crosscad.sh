#!/usr/bin/env bash
set -eu
TASK=/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction
mkdir -p "$TASK/work/oa_crosscad"
cd "$TASK/work/oa_crosscad"
if ! test -f cds.lib; then
 printf 'SOFTINCLUDE /home/EDA/cadence/IC231_ISR15/share/cdssetup/cds.lib\nDEFINE lab06b_crosscad_20261031 %s/work/oa_crosscad/lab06b_crosscad_20261031\n' "$TASK" > cds.lib
fi
strmin -library lab06b_crosscad_20261031 -strmFile "$TASK/out/input/B7_crosscad_labels.gds" -topCell LAB06B_B7_EC_PAD_CHIP -case lower -labelCase preserve -view layout -dbuPerUU 1000 -logFile "$TASK/out/import/streamIn_crosscad.log" -summaryFile "$TASK/out/import/streamIn_crosscad_summary.txt" > "$TASK/out/import/crosscad_console.log" 2>&1
printf 'Cross-CAD candidate imported to a new C-backed OA library\n'
