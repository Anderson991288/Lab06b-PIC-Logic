#!/usr/bin/env bash
# New OA from original S6 source; all generated data stays in the pinned C stage.
set -eu
TASK=$(cd -- "$(dirname -- "$0")" && pwd)
STAGE=$(python3 - "$TASK/out/clean_replay_stage.json" <<'PY'
import json,sys
print(json.load(open(sys.argv[1]))['wsl'])
PY
)
case "$STAGE" in "$TASK"/work/clean_replay_*) ;; *) echo 'Unsafe replay stage' >&2; exit 2;; esac
cd "$STAGE"
test ! -d lab06b_replay_source
printf 'SOFTINCLUDE /home/EDA/cadence/IC231_ISR15/share/cdssetup/cds.lib\nDEFINE lab06b_replay_source %s/lab06b_replay_source\nDEFINE lab06b_replay_final %s/lab06b_replay_final\n' "$STAGE" "$STAGE" > cds.lib
for variant in source final; do
  input=source.gds; test "$variant" != final || input=candidate.gds
  strmin -library "lab06b_replay_$variant" -strmFile "$STAGE/$input" -topCell LAB06B_B7_EC_PAD_CHIP -case lower -labelCase preserve -view layout -dbuPerUU 1000 -logFile "$STAGE/import_$variant.log" > "import_$variant.console" 2>&1
done
for limit in 200 8191; do
  strmout -library lab06b_replay_source -topCell lab06b_b7_ec_pad_chip -view layout -strmFile "$STAGE/source_$limit.gds" -layerMap "$STAGE/layer.map" -cellMap "$STAGE/lab06b_replay_source.map" -maxVertices "$limit" -dbuPerUU 1000 -labelCase preserve -logFile "$STAGE/export_$limit.log" > "export_$limit.console" 2>&1
done
strmout -library lab06b_replay_final -topCell lab06b_b7_ec_pad_chip -view layout -strmFile "$STAGE/final.gds" -layerMap "$STAGE/layer.map" -cellMap "$STAGE/lab06b_replay_final.map" -maxVertices 8191 -dbuPerUU 1000 -labelCase preserve -logFile "$STAGE/export_final.log" > export_final.console 2>&1
for name in source final negative; do
 mkdir "drc_$name"
 top=LAB06B_B7_EC_PAD_CHIP
 test "$name" != negative || top=LAB06B_NEGATIVE_16
 cat > "drc_$name/run.svrf" <<EOF
LAYOUT SYSTEM GDSII
LAYOUT PATH "$STAGE/$name.gds"
LAYOUT PRIMARY "$top"
DRC RESULTS DATABASE "$STAGE/drc_$name/results.db" ASCII
DRC SUMMARY REPORT "$STAGE/drc_$name/summary.txt"
INCLUDE "$STAGE/cornerstone_basic_draft.svrf"
EOF
 (cd "drc_$name"; calibre -drc -hier -64 run.svrf > run.log 2>&1)
done
printf 'Native clean replay completed in %s\n' "$STAGE"
