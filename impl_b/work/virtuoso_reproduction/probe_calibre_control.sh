#!/usr/bin/env bash
set -eu
export LC_ALL=C.utf8
TASK=/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction
xwininfo -root -tree > "$TASK/out/native_windows.txt"
head -40 "$TASK/out/native_windows.txt"
find /home/EDA/mentor/calibre2026/aok_cal_2026.1_17.11 -maxdepth 3 \( -iname '*interact*' -o -iname '*custom*' -o -iname '*tcl*' \) | head -55
