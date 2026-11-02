#!/bin/bash
# M0 s2 前置：在 WSL Ubuntu 安裝 Miniforge 與 Meep（conda 環境 meep，套件來自 conda-forge）。
# 執行（PowerShell）：wsl -d Ubuntu -e bash /mnt/d/LAB/Lab06b/work/m0_s2/setup_meep.sh
# 只裝在目前使用者的 ~/miniforge3，不需要 sudo；已裝過的步驟會跳過。
set -euo pipefail
MF=~/miniforge3
VER=26.9.4-1                     # 固定版本：安裝檔與官方 .sha256 用同一個帶版本號的檔名
URL=https://github.com/conda-forge/miniforge/releases/download/$VER/Miniforge3-$VER-Linux-x86_64.sh
TMP=$(mktemp -d)

if [ ! -x "$MF/bin/conda" ]; then
  echo "[1/3] 下載 Miniforge"
  curl -fsSL -o "$TMP/mf.sh" "$URL"
  curl -fsSL -o "$TMP/mf.sh.sha256" "$URL.sha256"
  want=$(awk '{print $1}' "$TMP/mf.sh.sha256")
  got=$(sha256sum "$TMP/mf.sh" | awk '{print $1}')
  echo "sha256 want $want"
  echo "sha256 got  $got"
  [ "$want" = "$got" ] || { echo "SHA-256 不符，停止"; exit 2; }
  echo "[2/3] 安裝 Miniforge 到 $MF"
  bash "$TMP/mf.sh" -b -p "$MF"
else
  echo "[1-2/3] Miniforge 已存在，跳過"
fi
rm -rf "$TMP"

if [ ! -d "$MF/envs/meep" ]; then
  echo "[3/3] 建立 conda 環境 meep（pymeep、matplotlib、h5py）"
  "$MF/bin/conda" create -y -n meep -c conda-forge pymeep matplotlib h5py
else
  echo "[3/3] 環境 meep 已存在，跳過"
fi

"$MF/bin/conda" run -n meep python -c "import meep as mp; print('MEEP_OK', mp.__version__)"
