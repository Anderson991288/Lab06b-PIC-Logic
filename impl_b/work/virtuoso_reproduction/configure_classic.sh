#!/usr/bin/env bash
set -eu
TASK=/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction
wish "$TASK/send_native.tcl" "$TASK/configure_classic.tcl"
tail -65 "$TASK/out/interactive_classic.log"
