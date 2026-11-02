param()
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
$config=Get-Content -LiteralPath (Join-Path $projectRoot 'EDA_paths.json') -Raw | ConvertFrom-Json
$python=$config.windows.physics_python
$prefix=Split-Path -Parent $python
$previousPath=$env:PATH
$previousConda=$env:CONDA_PREFIX
$previousDll=$env:CONDA_DLL_SEARCH_MODIFICATION_ENABLE
Push-Location -LiteralPath $projectRoot
try {
    $env:PATH="$prefix\Library\bin;$prefix\Scripts;$prefix;$previousPath"
    $env:CONDA_PREFIX=$prefix
    $env:CONDA_DLL_SEARCH_MODIFICATION_ENABLE='1'
    & $python work/m3_s2/run_crosscheck.py
    if ($LASTEXITCODE -ne 0) { throw 'Independent geometry crosscheck failed.' }
    & $python work/m3_s2/plot_crosscheck.py
    if ($LASTEXITCODE -ne 0) { throw 'Crosscheck figures failed.' }
    & $python scripts/render_course.py
    if ($LASTEXITCODE -ne 0) { throw 'Course render failed.' }
} finally {
    Pop-Location
    $env:PATH=$previousPath
    $env:CONDA_PREFIX=$previousConda
    $env:CONDA_DLL_SEARCH_MODIFICATION_ENABLE=$previousDll
}
