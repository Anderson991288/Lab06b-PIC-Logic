#!/bin/bash
# M2 s7 Calibre 段（批次）：用 cornerstone_pre_drc.svrf 對 5 個 GDS 跑 Calibre nmDRC（階層模式）。
# 在課程根目錄以登入殼層執行：wsl -d EDA_Server -- bash -lc "bash work/m2_s7/eda/calibre.sh"
# 需要先跑 virtuoso.sh（讀它的兩個匯出檔）。
# 每個 GDS 產生 <名稱>.drc.summary、<名稱>.drc.results（ASCII）、<名稱>.calibre.log，複製回 out/calibre/。
set -euo pipefail
SRC=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$SRC/../../.." && pwd)
OUT=$SRC/out/calibre
W=$HOME/claude_b7/calibre
rm -rf "$W"; mkdir -p "$W" "$OUT"; cd "$W"
cp "$SRC/cornerstone_pre_drc.svrf" rules.svrf
cp "$ROOT/work/m2_s6/out/b7_chip_checked.gds" signed.gds
cp signed.gds signed_area_wrong.gds
cp "$SRC/out/out_default.gds" virtuoso_default.gds
cp "$SRC/out/out_8191.gds" virtuoso_8191.gds
cp "$ROOT/work/m2_s6/out/drc_rules_fault.gds" rule_faults.gds
cp "$ROOT/work/m3_s2/out/edge_cases.gds" edge_cases.gds

run() {   # $1 = 名稱，$2 = 宣告設計區面積（µm²）
  cat > "$1.runset" <<EOF
LAYOUT SYSTEM GDSII
LAYOUT PATH "$1.gds"
LAYOUT PRIMARY "*"
DRC RESULTS DATABASE "$1.drc.results" ASCII
DRC SUMMARY REPORT "$1.drc.summary"
VARIABLE DESIGN_AREA $2
INCLUDE "rules.svrf"
EOF
  calibre -drc -hier "$1.runset" > "$1.calibre.log" 2>&1
  grep -E "TOTAL (DRC )?Results|TOTAL DRC RuleChecks" "$1.drc.summary" | sed "s/^/$1: /"
}
A=4651200                           # 3876 × 1200 µm
run signed $A
run virtuoso_default $A
run virtuoso_8191 $A
run rule_faults $A
run edge_cases $A
run signed_area_wrong 4531200       # 同一份晶片、宣告少 100 µm 寬：設計區檢查必須觸發
cp *.runset *.drc.summary *.drc.results *.calibre.log rules.svrf "$OUT"/
echo done
