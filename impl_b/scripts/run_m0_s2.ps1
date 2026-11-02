param([string]$PhysicsPython)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
$config=Get-Content -LiteralPath (Join-Path $projectRoot 'EDA_paths.json') -Raw | ConvertFrom-Json
if (-not $PhysicsPython) { $PhysicsPython=$config.windows.physics_python }
if (-not (Test-Path -LiteralPath $PhysicsPython -PathType Leaf)) { throw 'Physics Python does not exist. Update EDA_paths.json.' }
$physicsPrefix=Split-Path -Parent $PhysicsPython
$previousPath=$env:PATH
$previousConda=$env:CONDA_PREFIX
$previousDll=$env:CONDA_DLL_SEARCH_MODIFICATION_ENABLE
Push-Location -LiteralPath $projectRoot
try {
    $env:PATH="$physicsPrefix\Library\bin;$physicsPrefix\Scripts;$physicsPrefix;$previousPath"
    $env:CONDA_PREFIX=$physicsPrefix
    $env:CONDA_DLL_SEARCH_MODIFICATION_ENABLE='1'
    & $PhysicsPython work/m0_s2/physics_lab.py
    $physicsExit=$LASTEXITCODE
    & $PhysicsPython scripts/render_course.py
    if ($LASTEXITCODE -ne 0) { throw 'Course render failed.' }
    if ($physicsExit -ne 0) { throw 'Physics checks failed; inspect physics_results.json.' }
} finally {
    Pop-Location
    $env:PATH=$previousPath
    $env:CONDA_PREFIX=$previousConda
    $env:CONDA_DLL_SEARCH_MODIFICATION_ENABLE=$previousDll
}
