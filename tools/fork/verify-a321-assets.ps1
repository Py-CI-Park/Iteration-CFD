# meteor-cfd fork operations - Py-CI-Park/Iteration-CFD
# Source-available, not Open Source. See LICENSE at the repository root.
# No GPL-licensed source was consulted.
<#
.SYNOPSIS
  Verify the A321 handoff critical-asset manifest (SHA256 of every listed file).
.DESCRIPTION
  Reads research/a321-quality/evidence/handoff-critical-assets.json and checks each
  relative path exists with the recorded sha256. Exit 0 when all match, 1 otherwise.
  Read-only.
#>
param(
    [string]$Manifest = 'research/a321-quality/evidence/handoff-critical-assets.json'
)
$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $Manifest)) { throw "manifest not found: $Manifest" }
$data = Get-Content -LiteralPath $Manifest -Raw | ConvertFrom-Json
$checked = 0
$failures = @()
foreach ($asset in $data.assets) {
    $checked++
    $path = Join-Path (Get-Location) $asset.path
    if (-not (Test-Path -LiteralPath $path)) { $failures += "MISSING  $($asset.path)"; continue }
    $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($hash -ne $asset.sha256) { $failures += "MISMATCH $($asset.path)" }
}
$failures | ForEach-Object { Write-Output $_ }
Write-Output "checked=$checked failed=$($failures.Count)"
if ($failures.Count -gt 0) { exit 1 }
