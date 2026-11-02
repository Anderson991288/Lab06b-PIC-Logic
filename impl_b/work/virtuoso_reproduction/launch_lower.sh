#!/usr/bin/env bash
set -eu
TASK=/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction
cd "$TASK/work/oa_lower"
exec virtuoso -replay "$TASK/open_lower.il" -log "$TASK/out/virtuoso_lower_CDS.log" < /dev/null > "$TASK/out/virtuoso_lower_launcher.log" 2>&1
