$ErrorActionPreference = 'Stop'
# Research UI only. This starts no mesh generator, CFD solver, GPU job or live model API.
$checkout = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$runLogs = Join-Path $PSScriptRoot 'artifacts'
New-Item -ItemType Directory -Path $runLogs -Force | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$env:CFD_DEMO = '1'
$env:CFD_LLM = 'mock'
$env:CFD_PORT = '8815'
$env:CFD_WEB_PORT = '5185'
$env:CFD_ALLOW_REMOTE = '0'
$env:CFD_WORKSPACE = $checkout
$env:CFD_CONFIG_DIR = Join-Path $runLogs 'gallery-config'
function IsListening([int]$Port) {
    return [bool](Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
}
if (!(IsListening 5185) -and !(IsListening 8815)) {
    Start-Process -FilePath (Get-Command npm.cmd).Source -ArgumentList @('run', 'dev') -WorkingDirectory (Join-Path $checkout 'gui') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runLogs "$stamp-studio.out") -RedirectStandardError (Join-Path $runLogs "$stamp-studio.err") | Out-Null
} elseif (!(IsListening 5185) -or !(IsListening 8815)) {
    throw 'Only one Studio port is active. Inspect its owner before starting another server.'
}
if (!(IsListening 8776)) {
    Start-Process -FilePath (Get-Command python).Source -ArgumentList @('-m', 'http.server', '8776', '--bind', '127.0.0.1', '--directory', (Join-Path $checkout 'research')) -WindowStyle Hidden | Out-Null
}
Write-Output 'Studio (demo/mock): http://127.0.0.1:5185/'
Write-Output 'Report: http://127.0.0.1:8776/a321-quality/report.html'
Write-Output 'Existing listeners are not replaced; verify the Studio workspace/health in the browser.'
