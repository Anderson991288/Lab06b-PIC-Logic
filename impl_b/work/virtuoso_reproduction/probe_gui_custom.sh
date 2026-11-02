#!/usr/bin/env bash
set -eu
CAL=/home/EDA/mentor/calibre2026/aok_cal_2026.1_17.11
ls "$CAL/shared/pkgs/icv.aok/tools/custom"
find "$CAL/shared/pkgs/icv.aok/tools/custom" -type f | head -30
ls "$CAL/shared/pkgs/icv/systest_data/tclsrc" | head -35
grep -R -n -E 'runDRC|runDrc|RunDRC|runVerification|run_drc|runCalibre|nmDRC' "$CAL/shared/pkgs/icv.aok/tools/custom" | head -45
find "$CAL" -maxdepth 4 -iname '*.pdf' | head -25
