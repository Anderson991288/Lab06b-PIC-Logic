#!/usr/bin/env bash
set -eu
TASK=/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction
cd "$TASK/work/oa"
exec virtuoso -replay "$TASK/open_current.il" -log "$TASK/out/virtuoso_CDS.log" < /dev/null > "$TASK/out/virtuoso_launcher.log" 2>&1
