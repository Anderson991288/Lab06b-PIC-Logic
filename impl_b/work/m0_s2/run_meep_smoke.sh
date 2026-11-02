#!/bin/bash
# 執行（PowerShell）：wsl -d Ubuntu -e bash /mnt/d/LAB/Lab06b/work/m0_s2/run_meep_smoke.sh
~/miniforge3/bin/conda run -n meep python /mnt/d/LAB/Lab06b/work/m0_s2/meep_smoke.py 2>&1 | grep -E "MEEP_SMOKE_OK|Error" | tail -3
