#!/usr/bin/env bash
set -eu
TASK=/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction
xwininfo -root -tree > "$TASK/out/native_windows.txt"
grep -Ei 'Calibre|Virtuoso|Runset|nmDRC|RVE' "$TASK/out/native_windows.txt" | head -45
tail -40 "$TASK/out/virtuoso_controlled_CDS.log"
