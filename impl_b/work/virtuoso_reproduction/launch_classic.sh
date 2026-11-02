#!/usr/bin/env bash
set -eu
TASK=/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction
export MGC_CALIBRE_NEED_SEND=:lab06b_classic
export CALIBRE_ENABLE_CLASSIC_CI_DRC=1
export MGC_CALIBRE_LAYOUT_SERVER=localhost:9189
export MGC_CALIBRE_LAYOUT_SERVER_NAME=Cadence:Virtuoso
cd "$TASK/work/oa_lower"
exec calibre -gui -drc "$TASK/out/Lab06b_auto.runset" > "$TASK/out/interactive_classic.log" 2>&1
