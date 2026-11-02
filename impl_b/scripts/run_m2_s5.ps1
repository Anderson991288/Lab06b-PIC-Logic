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
    & $ModelPython work/m2_s5/build_chip.py
    if ($LASTEXITCODE -ne 0) { throw 'Chip interface build/readback failed.' }
    $klayout=$config.windows.klayout_exe
    if (-not [System.IO.Path]::IsPathRooted($klayout)) { $klayout=Join-Path $projectRoot $klayout }
    $faultProcess=Start-Process -FilePath $klayout -ArgumentList @('-b','-r',(Join-Path $projectRoot 'work/m2_s5/connectivity_faults.py')) -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput (Join-Path $projectRoot 'work/m2_s5/out/connectivity_faults.log') -RedirectStandardError (Join-Path $projectRoot 'work/m2_s5/out/connectivity_faults_errors.log')
    if ($faultProcess.ExitCode -ne 0) { throw 'Connectivity negative controls failed.' }
    & $ModelPython work/m2_s5/validate_interfaces.py
    if ($LASTEXITCODE -ne 0) { throw 'Interface acceptance failed.' }
    $plotPython=$config.windows.physics_python
    $plotPrefix=Split-Path -Parent $plotPython
    $env:PATH="$plotPrefix\Library\bin;$plotPrefix\Scripts;$plotPrefix;$previousPath"
    $env:CONDA_PREFIX=$plotPrefix
    & $plotPython work/m2_s5/plot_chip.py
    if ($LASTEXITCODE -ne 0) { throw 'Chip report plot failed.' }
    & $plotPython scripts/render_course.py
    if ($LASTEXITCODE -ne 0) { throw 'Course render failed.' }
} finally {
    Pop-Location
    $env:PATH=$previousPath
    $env:CONDA_PREFIX=$previousConda
    $env:CONDA_DLL_SEARCH_MODIFICATION_ENABLE=$previousDll
}
