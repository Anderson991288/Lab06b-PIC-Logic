# Lab06b EDA environment (Windows PowerShell). Usage:  . C:\LAB\Lab06b\impl_a\env\eda_env.ps1
# All values come from C:\LAB\Lab06b\impl_a\EDA_paths.json so there is one place to change.
$cfg = Get-Content C:\LAB\Lab06b\impl_a\EDA_paths.json -Raw -Encoding UTF8 | ConvertFrom-Json
$x = { param($v) [Environment]::ExpandEnvironmentVariables($v) }
$env:EDA_ROOT      = $cfg.root
$env:LUCEDA_PY     = & $x $cfg.windows.ipkiss_python
$env:KLAYOUT_EXE   = & $x $cfg.windows.klayout_exe
$env:EDA_PDK       = & $x $cfg.windows.pdk_cornerstone
$env:EDA_DRC_DECK  = & $x $cfg.windows.drc_deck
$env:COURSE        = $cfg.course.path
$env:PYTHONIOENCODING = 'utf-8'
$env:OMP_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:NUMEXPR_NUM_THREADS = '1'
function ipkiss { & $env:LUCEDA_PY @args }
# device_sim must go through conda run (direct python.exe crashes silently in scipy LAPACK)
function devsim { & (& $x $cfg.windows.conda) run --no-capture-output -p (& $x $cfg.windows.device_sim_env) python @args }
Write-Host "EDA env loaded: EDA_ROOT=$env:EDA_ROOT  COURSE=$env:COURSE"
