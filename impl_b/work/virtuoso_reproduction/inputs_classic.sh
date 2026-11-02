#!/usr/bin/env bash
set -eu
TASK=/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction
wish "$TASK/send_native.tcl" "$TASK/inputs_classic.tcl"
tail -18 "$TASK/out/interactive_classic.log"
python3 "$TASK/capture_native.py" '^Calibre Interactive - nmDRC v2026.1_17.11$' calibre_auto_inputs
python3 "$TASK/capture_native.py" 'Layout Suite XL Reading: lab06b_crosscad_20261031' virtuoso_final
