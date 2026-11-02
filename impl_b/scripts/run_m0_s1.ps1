param([string]$PythonExe)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
$config=Get-Content -LiteralPath (Join-Path $projectRoot 'EDA_paths.json') -Raw | ConvertFrom-Json
if (-not $PythonExe) { $PythonExe=$config.windows.ipkiss_python }
Push-Location -LiteralPath $projectRoot
try {
    & $PythonExe scripts/env_audit.py
    if ($LASTEXITCODE -ne 0) { throw 'Environment baseline failed.' }
    & $PythonExe scripts/smoke_mzi.py
    if ($LASTEXITCODE -ne 0) { throw 'Ideal MZI check failed.' }
    & $PythonExe work/m0_s1/build_mzi_drc.py
    if ($LASTEXITCODE -ne 0) { throw 'MZI GDS/DRC build failed.' }
    & $PythonExe work/m0_s1/check_toolchain.py
    if ($LASTEXITCODE -ne 0) { throw 'Toolchain execution failed.' }
    & $PythonExe scripts/render_course.py
    if ($LASTEXITCODE -ne 0) { throw 'Report render failed.' }
    $result = Get-Content -LiteralPath 'work/m0_s1/out/toolchain_check.json' -Raw | ConvertFrom-Json
    if (-not $result.core_passed) { throw 'M0 S1 core toolchain has unresolved checks; see the rendered report.' }
} finally { Pop-Location }
