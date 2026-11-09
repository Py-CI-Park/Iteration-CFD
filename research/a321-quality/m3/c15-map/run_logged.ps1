# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
param([string]$Label, [string]$Command)
$ErrorActionPreference = 'Continue'
$outputDir = $PSScriptRoot
$logPath = Join-Path $outputDir ($Label + '.log')
if (Test-Path -LiteralPath $logPath) { throw "Log already exists: $logPath" }
$watch = [Diagnostics.Stopwatch]::StartNew()
$global:LASTEXITCODE = 0
"COMMAND: $Command`nSTART_UTC: $([DateTime]::UtcNow.ToString('o'))" | Out-File -LiteralPath $logPath -Encoding utf8
$rawLimit = 45MB
$rawBytes = 0
$truncated = $false
$tailLines = [Collections.Generic.Queue[string]]::new()
$executionErrors=@()
Invoke-Expression ($Command + ' 2>&1') -ErrorVariable +executionErrors | ForEach-Object {
    $line=$_.ToString()
    $rawBytes += [Text.Encoding]::UTF8.GetByteCount($line) + 2
    if ($rawBytes -le $rawLimit) {
        Add-Content -LiteralPath $logPath -Value $line -Encoding utf8
        Write-Output $line
    } else {
        if (!$truncated) {
            Add-Content -LiteralPath $logPath -Value 'OUTPUT CAPPED; retaining bounded tail below' -Encoding utf8
            $truncated=$true
        }
        if ($line.Length -gt 2000) { $line=$line.Substring($line.Length-2000) }
        $tailLines.Enqueue($line)
        if ($tailLines.Count -gt 1000) { $null=$tailLines.Dequeue() }
    }
}
$commandExit = $LASTEXITCODE
if ($executionErrors.Count -gt 0 -and $commandExit -eq 0) { $commandExit=1 }
$watch.Stop()
if ($truncated) { Add-Content -LiteralPath $logPath -Value @($tailLines.ToArray()) -Encoding utf8 }
$footer="EXIT_CODE: $commandExit`nWALL_SECONDS: $($watch.Elapsed.TotalSeconds)"
Add-Content -LiteralPath $logPath -Value $footer -Encoding utf8
Write-Output $footer
$logFile = Get-Item -LiteralPath $logPath
if ($logFile.Length -gt 50MB) {
    $head = Get-Content -LiteralPath $logPath -TotalCount 1000
    $tail = Get-Content -LiteralPath $logPath -Tail 1000
    @($head; "TRUNCATED: original bytes $($logFile.Length)"; $tail) | Set-Content -LiteralPath $logPath -Encoding utf8
}
exit $commandExit
