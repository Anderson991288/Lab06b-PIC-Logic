param([string]$ModelPython)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
$config=Get-Content -LiteralPath (Join-Path $projectRoot 'EDA_paths.json') -Raw | ConvertFrom-Json
if (-not $ModelPython) { $ModelPython=$config.windows.ipkiss_python }
$physicsPython=$config.windows.physics_python
$physicsPrefix=Split-Path -Parent $physicsPython
$modelPrefix=Split-Path -Parent $ModelPython
$previousPath=$env:PATH
$previousConda=$env:CONDA_PREFIX
$previousDll=$env:CONDA_DLL_SEARCH_MODIFICATION_ENABLE
Push-Location -LiteralPath $projectRoot
try {
    $env:PATH="$physicsPrefix\Library\bin;$physicsPrefix\Scripts;$physicsPrefix;$previousPath"
    $env:CONDA_PREFIX=$physicsPrefix
    $env:CONDA_DLL_SEARCH_MODIFICATION_ENABLE='1'
    & $physicsPython work/m2_s6/run_verification.py
    if ($LASTEXITCODE -ne 0) { throw 'Pre-DRC or graph preparation failed.' }
    & $physicsPython work/m2_s6/run_controls.py
    if ($LASTEXITCODE -ne 0) { throw 'Negative GDS controls failed.' }
    $env:PATH="$modelPrefix\Library\bin;$modelPrefix\Scripts;$modelPrefix;$previousPath"
    $env:CONDA_PREFIX=$modelPrefix
    & $ModelPython work/m2_s6/regression.py
    if ($LASTEXITCODE -ne 0) { throw 'Existing regression failed.' }
    $env:PATH="$physicsPrefix\Library\bin;$physicsPrefix\Scripts;$physicsPrefix;$previousPath"
    $env:CONDA_PREFIX=$physicsPrefix
    & $physicsPython work/m2_s6/summarize.py
    if ($LASTEXITCODE -ne 0) { throw 'S6 acceptance failed.' }
    $klayout=$config.windows.klayout_exe
    if (-not [System.IO.Path]::IsPathRooted($klayout)) { $klayout=Join-Path $projectRoot $klayout }
    $render=Start-Process -FilePath $klayout -ArgumentList @('-b','-r',(Join-Path $projectRoot 'work/m2_s6/render_evidence.py')) -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput (Join-Path $projectRoot 'work/m2_s6/out/render_evidence.log') -RedirectStandardError (Join-Path $projectRoot 'work/m2_s6/out/render_evidence_errors.log')
    if ($render.ExitCode -ne 0) { throw 'Native KLayout evidence render failed.' }
    & $physicsPython work/m2_s6/plot_verification.py
    if ($LASTEXITCODE -ne 0) { throw 'Verification plots failed.' }
    & $physicsPython scripts/render_course.py
    if ($LASTEXITCODE -ne 0) { throw 'Course render failed.' }
} finally {
    Pop-Location
    $env:PATH=$previousPath
    $env:CONDA_PREFIX=$previousConda
    $env:CONDA_DLL_SEARCH_MODIFICATION_ENABLE=$previousDll
}
