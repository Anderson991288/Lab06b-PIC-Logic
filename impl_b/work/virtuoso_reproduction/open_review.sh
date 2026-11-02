#!/usr/bin/env bash
set -eu
TASK=$(cd -- "$(dirname -- "$0")" && pwd)
export CALIBRE_ENABLE_CLASSIC_CI_DRC=1
export MGC_CALIBRE_DRC_RUNSET_FILE="$TASK/out/GUI_fixed_saved.runset"
cd "$TASK/work/oa_crosscad"
test -f cds.lib
exec virtuoso -replay "$TASK/open_review.il" -log "$TASK/out/virtuoso_review_CDS.log" < /dev/null > "$TASK/out/virtuoso_review_launcher.log" 2>&1
