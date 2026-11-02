#!/usr/bin/env bash
set -eu
TASK=/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction
wish "$TASK/send_native.tcl" "$TASK/run_gui_fixed.tcl"
python3 "$TASK/capture_native.py" '^Calibre - RVE' rve_auto
