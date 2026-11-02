#!/usr/bin/env bash
set -eu
CAL=/home/EDA/mentor/calibre2026/aok_cal_2026.1_17.11
head -155 "$CAL/shared/pkgs/icv/systest_data/tclsrc/test_gui.tcl"
"$CAL/bin/wish" <<'TCL'
wm withdraw .
puts "TCL_APPS [winfo interps]"
exit
TCL
