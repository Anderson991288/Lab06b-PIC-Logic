#!/usr/bin/env bash
set -u
printf 'Capture tools\n'
command -v import xwd scrot || true
printf 'Display resolution settings\n'
grep -i -n -E 'resolution|stopLevel' /home/EDA/cadence/IC231_ISR15/tools/dfII/etc/cdsenv 2>/dev/null | head -15 || true
printf 'Calibre entry functions\n'
grep -n -E 'Run.nmDRC|Run DRC|hiCreateMenuItem|calibreDRC|runDRC|RunDRC' /home/EDA/mentor/calibre2026/aok_cal_2026.1_17.11/lib/calibre.skl | head -20 || true
