#!/usr/bin/env bash
set -eu
TASK=/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction
mkdir -p "$TASK/out/cli_crosscad"
cd "$TASK/out/cli_crosscad"
calibre -drc -hier -64 "$TASK/out/rules/crosscad.svrf" > run.log 2>&1
printf 'Cross-CAD annotation candidate checked by unchanged Calibre draft\n'
