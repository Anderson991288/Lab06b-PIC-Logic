#!/usr/bin/env bash
set -eu
TASK=/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction
wish "$TASK/send_native.tcl" "$TASK/remote_inspect.tcl" > "$TASK/out/native_gui_widgets.txt"
cat "$TASK/out/native_gui_widgets.txt"
