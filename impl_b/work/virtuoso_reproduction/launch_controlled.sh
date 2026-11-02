#!/usr/bin/env bash
set -eu
TASK=/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction
mkdir -p "$TASK/work/commands"
cd "$TASK/work/oa_lower"
exec virtuoso -replay "$TASK/launch_controlled.il" -log "$TASK/out/virtuoso_controlled_CDS.log" < /dev/null > "$TASK/out/virtuoso_controlled_launcher.log" 2>&1
