#!/usr/bin/env bash
set -eu
CAL=/home/EDA/mentor/calibre2026/aok_cal_2026.1_17.11
find "$CAL" -maxdepth 4 \( -iname '*gui*' -o -iname '*user*.pdf' -o -iname '*custom*.pdf' \) | head -45
ls "$CAL/shared/systest/test.CalibreinteractiveDRC"
grep -R -n -E 'RunDRC|runDRC|runDrc|runVerification|customize|runset|autostart' "$CAL/shared/systest/test.CalibreinteractiveDRC" | head -45
