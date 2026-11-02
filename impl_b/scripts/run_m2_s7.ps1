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
    $klayout=$config.windows.klayout_exe
    if (-not [System.IO.Path]::IsPathRooted($klayout)) { $klayout=Join-Path $projectRoot $klayout }
    foreach ($task in @('extract_lengths','render_final_gds')) {
        $process=Start-Process -FilePath $klayout -ArgumentList @('-b','-r',(Join-Path $projectRoot "work/m2_s7/$task.py")) -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput (Join-Path $projectRoot "work/m2_s7/out/$task.log") -RedirectStandardError (Join-Path $projectRoot "work/m2_s7/out/${task}_errors.log")
        if ($process.ExitCode -ne 0) { throw "KLayout $task failed." }
    }
    $env:PATH="$physicsPrefix\Library\bin;$physicsPrefix\Scripts;$physicsPrefix;$previousPath"
    $env:CONDA_PREFIX=$physicsPrefix
    $env:CONDA_DLL_SEARCH_MODIFICATION_ENABLE='1'
    & $physicsPython work/m2_s7/run_replay.py
    if ($LASTEXITCODE -ne 0) { throw 'Backannotation replay failed.' }
    $env:PATH="$modelPrefix\Library\bin;$modelPrefix\Scripts;$modelPrefix;$previousPath"
    $env:CONDA_PREFIX=$modelPrefix
    & $ModelPython work/m2_s7/regression.py
    if ($LASTEXITCODE -ne 0) { throw 'Existing regression failed.' }
    $env:PATH="$physicsPrefix\Library\bin;$physicsPrefix\Scripts;$physicsPrefix;$previousPath"
    $env:CONDA_PREFIX=$physicsPrefix
    foreach ($task in @('build_delivery','plot_delivery')) {
        & $physicsPython "work/m2_s7/$task.py"
        if ($LASTEXITCODE -ne 0) { throw "$task failed." }
    }
    & $physicsPython scripts/render_course.py
    if ($LASTEXITCODE -ne 0) { throw 'Report render failed.' }
} finally {
    Pop-Location
    $env:PATH=$previousPath
    $env:CONDA_PREFIX=$previousConda
    $env:CONDA_DLL_SEARCH_MODIFICATION_ENABLE=$previousDll
}
