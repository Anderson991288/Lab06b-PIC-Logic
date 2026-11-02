param([string]$ModelPython)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
$config=Get-Content -LiteralPath (Join-Path $projectRoot 'EDA_paths.json') -Raw | ConvertFrom-Json
if (-not $ModelPython) { $ModelPython=$config.windows.ipkiss_python }
$modelPrefix=Split-Path -Parent $ModelPython
$previousPath=$env:PATH
$previousConda=$env:CONDA_PREFIX
$previousDll=$env:CONDA_DLL_SEARCH_MODIFICATION_ENABLE
Push-Location -LiteralPath $projectRoot
try {
    $env:PATH="$modelPrefix\Library\bin;$modelPrefix\Scripts;$modelPrefix;$previousPath"
    $env:CONDA_PREFIX=$modelPrefix
    $env:CONDA_DLL_SEARCH_MODIFICATION_ENABLE='1'
    & $ModelPython work/m2_s4/run_review.py
    if ($LASTEXITCODE -ne 0) { throw 'KLayout review build failed; inspect work/m2_s4/out/.' }
    $plotPython=$config.windows.physics_python
    $plotPrefix=Split-Path -Parent $plotPython
    $env:PATH="$plotPrefix\Library\bin;$plotPrefix\Scripts;$plotPrefix;$previousPath"
    $env:CONDA_PREFIX=$plotPrefix
    & $plotPython work/m2_s4/analyze_paths.py
    if ($LASTEXITCODE -ne 0) { throw 'Centerline crossing review failed.' }
    & $plotPython work/m2_s4/summarize_review.py
    if ($LASTEXITCODE -ne 0) { throw 'Review acceptance failed.' }
    & $plotPython work/m2_s4/plot_review.py
    if ($LASTEXITCODE -ne 0) { throw 'Review plots failed.' }
    & $plotPython scripts/render_course.py
    if ($LASTEXITCODE -ne 0) { throw 'Course render failed.' }
} finally {
    Pop-Location
    $env:PATH=$previousPath
    $env:CONDA_PREFIX=$previousConda
    $env:CONDA_DLL_SEARCH_MODIFICATION_ENABLE=$previousDll
}
