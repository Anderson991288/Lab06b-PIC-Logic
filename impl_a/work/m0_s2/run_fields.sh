#!/bin/bash
# M0 s2 E3：Meep 案例同時跑（各 1 執行緒），各自寫 log。另跑 MMI 的 16、32 px/µm 作解析度收斂對照。
# 執行（PowerShell）：wsl -d Ubuntu -e bash /mnt/c/LAB/Lab06b/impl_a/work/m0_s2/run_fields.sh   （24 px/µm，約 40 分鐘）
cd /mnt/c/LAB/Lab06b/impl_a/work/m0_s2
export OMP_NUM_THREADS=1
PY=~/miniforge3/envs/meep/bin/python
for c in mmi t0 tpi tpi2 comb; do
  $PY mzi_field.py $c > out/field_$c.log 2>&1 &
done
for r in 16 32; do
  MEEP_RES=$r MEEP_TAG=_r$r $PY mzi_field.py mmi > out/field_mmi_r$r.log 2>&1 &
done
wait
grep -h -E "^(mmi|t0|tpi|tpi2|comb):|Error|Traceback" out/field_*.log
echo FIELDS_DONE
