# Lab06b EDA environment (WSL Ubuntu, user yangpc). Usage:  source /mnt/c/LAB/Lab06b/impl_a/env/eda_env.sh
# Never call the EDA_Server distro from these scripts.
export EDA_ROOT=/mnt/c/LAB/Lab06b/impl_a
export COURSE=/mnt/c/LAB/Lab06b/impl_a
export OMP_NUM_THREADS=1
# Meep: conda env "meep" under ~/miniforge3
meep_py() { ~/miniforge3/bin/conda run --no-capture-output -n meep python "$@"; }
