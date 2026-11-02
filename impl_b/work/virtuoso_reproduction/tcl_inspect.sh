#!/usr/bin/env bash
set -eu
CAL=/home/EDA/mentor/calibre2026/aok_cal_2026.1_17.11
"$CAL/bin/wish" <<'TCL'
wm withdraw .
puts "TCL_APPS [winfo interps]"
foreach app [winfo interps] {
 if {[string match "calibre-drc:*" $app]} {
  puts "GUI_TITLE [send $app {wm title .}]"
  puts "ROOT_CHILDREN [send $app {winfo children .}]"
  puts "RUN_COMMANDS [send $app {info commands *run*}]"
 }
}
exit
TCL
