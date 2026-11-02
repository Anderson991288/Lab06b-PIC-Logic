#!/bin/bash
# M0 s2 前置：查 WSL Ubuntu 的使用者、下載工具與網路（只讀）
echo "user: $(whoami) uid=$(id -u)"
echo "users(uid>=1000): $(getent passwd | awk -F: '$3>=1000 && $3<65000 {print $1}' | tr '\n' ' ')"
for t in curl wget bzip2; do printf '%-6s %s\n' "$t" "$(command -v $t || echo -)"; done
echo "home free: $(df -h ~ | awk 'NR==2{print $4}')"
for u in https://github.com https://conda.anaconda.org/conda-forge/noarch/repodata.json; do
  code=$(timeout 30 curl -s -o /dev/null -w '%{http_code}' -I "$u" 2>/dev/null || echo fail)
  echo "net $u -> $code"
done
ls -d ~/miniforge3 2>/dev/null && echo "miniforge exists"
exit 0
