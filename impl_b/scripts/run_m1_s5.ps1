param([string]$ModelPython)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
$config=Get-Content -LiteralPath (Join-Path $projectRoot 'EDA_paths.json') -Raw | ConvertFrom-Json
if (-not $ModelPython) { $ModelPython=$config.windows.physics_python }
if (-not (Test-Path -LiteralPath $ModelPython -PathType Leaf)) { throw 'Model Python does not exist. Update EDA_paths.json.' }
$modelPrefix=Split-Path -Parent $ModelPython
$previousPath=$env:PATH
$previousConda=$env:CONDA_PREFIX
$previousDll=$env:CONDA_DLL_SEARCH_MODIFICATION_ENABLE
Push-Location -LiteralPath $projectRoot
try {
    $env:PATH="$modelPrefix\Library\bin;$modelPrefix\Scripts;$modelPrefix;$previousPath"
    $env:CONDA_PREFIX=$modelPrefix
    $env:CONDA_DLL_SEARCH_MODIFICATION_ENABLE='1'
    & $ModelPython work/m1_s5/run_handoff.py
    $modelExit=$LASTEXITCODE
    & $ModelPython scripts/render_course.py
    if ($LASTEXITCODE -ne 0) { throw 'Course render failed.' }
    if ($modelExit -ne 0) { throw 'Handoff failed; inspect work/m1_s5/out/handoff_results.json and unit_tests.log.' }
} finally {
    Pop-Location
    $env:PATH=$previousPath
    $env:CONDA_PREFIX=$previousConda
    $env:CONDA_DLL_SEARCH_MODIFICATION_ENABLE=$previousDll
}
