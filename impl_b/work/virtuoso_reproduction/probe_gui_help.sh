#!/usr/bin/env bash
set -u
TASK=/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction
cd "$TASK/work/oa_crosscad"
timeout 15 calibre -gui -drc -help > "$TASK/out/calibre_gui_help.log" 2>&1
printf 'GUI help probe return %s\n' "$?"
