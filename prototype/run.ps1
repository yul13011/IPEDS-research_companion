param([int]$Port = 8516)
$ErrorActionPreference = 'Stop'
$prototypeRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $prototypeRoot
$localPython = Join-Path $prototypeRoot '.venv/Scripts/python.exe'
$bundledPython = 'C:/Users/liyuj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
if (Test-Path -LiteralPath $localPython) { $prototypePython = $localPython }
elseif (Test-Path -LiteralPath $bundledPython) { $prototypePython = $bundledPython }
else { $prototypePython = (Get-Command python).Source }
if (Test-Path -LiteralPath (Join-Path $prototypeRoot '.packages')) {
    $env:PYTHONPATH = (Join-Path $prototypeRoot '.packages') + [IO.Path]::PathSeparator + $env:PYTHONPATH
}
# Local/dev launcher: route question logging to the internal tab so our own test
# questions never mix with real users' questions in the main sheet tab.
$env:IPEDS_INTERNAL_LOG = '1'
& $prototypePython prototype/launch.py --global.developmentMode false --server.address 127.0.0.1 --server.port $Port --server.headless true --browser.gatherUsageStats false --server.fileWatcherType none --logger.level warning
