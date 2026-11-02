#!/usr/bin/env bash
set -eu
TASK=/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction
wish "$TASK/send_native.tcl" "$TASK/save_auto_configure_fixed.tcl"
python3 "$TASK/capture_native.py" '^Calibre Interactive - nmDRC' calibre_fixed_inputs
export LC_ALL=C.utf8
xwininfo -root -tree | grep -E 'Calibre|RVE|DRC Summary' | head -15
