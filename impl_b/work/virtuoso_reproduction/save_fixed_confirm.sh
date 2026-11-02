#!/usr/bin/env bash
set -eu
TASK=/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction
wish "$TASK/send_native.tcl" "$TASK/save_fixed_confirm.tcl"
export LC_ALL=C.utf8
xwininfo -root -tree | grep -E 'RVE|Calibre -|Summary Report' | head -10
python3 "$TASK/capture_native.py" 'RVE.*drc.results' rve_final
