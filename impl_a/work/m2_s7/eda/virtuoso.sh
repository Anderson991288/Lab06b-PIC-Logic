#!/bin/bash
# M2 s7 Virtuoso 段（批次）：簽核版 GDS → XStream In → OA → 統計 → XStream Out（預設 200 點與 8191 點）。
# 在課程根目錄以登入殼層執行：wsl -d EDA_Server -- bash -lc "bash work/m2_s7/eda/virtuoso.sh"
# 工作目錄在 Linux 原生目錄（OA library 不放在 Windows 掛載目錄）；結果複製回 out/。
set -euo pipefail
SRC=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$SRC/../../.." && pwd)
OUT=$SRC/out
GDS=$ROOT/work/m2_s6/out/b7_chip_checked.gds
W=$HOME/claude_b7/virtuoso
rm -rf "$W"; mkdir -p "$W" "$OUT"; cd "$W"
cp "$GDS" in.gds
touch cds.lib
export CDS_SKIP_OS_CHECK_ON_STARTUP=1

strmin -library B7_CHIP -strmFile in.gds -logFile strmIn.log -summaryFile strmIn.sum

export OA_REPORT=$W/oa_report.txt
virtuoso -nograph -replay "$SRC/inspect_oa.il" -log virtuoso_inspect.log > /dev/null
TOP=$(awk '/^top /{print $2; exit}' oa_report.txt)
echo "top cell: $TOP"

strmout -library B7_CHIP -topCell "$TOP" -view layout -strmFile out_default.gds -logFile strmOut_default.log
strmout -library B7_CHIP -topCell "$TOP" -view layout -strmFile out_8191.gds -logFile strmOut_8191.log \
        -maxVertices 8191 -dbuPerUU 1000

cp strmIn.log strmIn.sum oa_report.txt virtuoso_inspect.log strmOut_default.log strmOut_8191.log \
   out_default.gds out_8191.gds "$OUT"/
cat cds.lib > "$OUT"/cds.lib.txt
echo done
