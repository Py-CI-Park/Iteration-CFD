# meteor-cfd fork operations - Py-CI-Park/Iteration-CFD
# Source-available, not Open Source. See LICENSE at the repository root.
# No GPL-licensed source was consulted.
<#
.SYNOPSIS
  Check (default) or stage (-Apply) an upstream merge for this fork.
.DESCRIPTION
  Default mode is read-only: fetches upstream, prints how far fork main / the dev
  line are behind upstream/main and which known conflict hotspots upstream touched.
  -Apply creates sync/upstream-YYYYMMDD from the dev line and merges upstream/main
  with --no-ff. It never pushes. See docs/fork/UPSTREAM_SYNC_KO.md.
#>
param(
    [switch]$Apply,
    [string]$DevBranch = 'v2.1.0-dev',
    [string]$UpstreamUrl = 'https://github.com/using76/Iteration-CFD.git'
)
$ErrorActionPreference = 'Stop'

$Hotspots = @(
    'rust/PROVENANCE.md', 'NOTICE', 'gui/package-lock.json', 'gui/package.json',
    'docs/schema', '.gitignore', '.gitattributes'
)

function Invoke-Git {
    param([string[]]$GitArgs)
    $out = & git @GitArgs
    if ($LASTEXITCODE -ne 0) { throw "git $($GitArgs -join ' ') failed (exit $LASTEXITCODE)" }
    return $out
}

function Confirm-UpstreamRemote {
    $remotes = Invoke-Git @('remote')
    if ($remotes -notcontains 'upstream') {
        Write-Output "adding remote upstream -> $UpstreamUrl"
        Invoke-Git @('remote', 'add', 'upstream', $UpstreamUrl) | Out-Null
    }
    Invoke-Git @('fetch', 'upstream', '--tags', '--prune') | Out-Null
}

function Show-Report {
    $behindMain = [int](Invoke-Git @('rev-list', '--count', 'main..upstream/main'))
    $behindDev = [int](Invoke-Git @('rev-list', '--count', "$DevBranch..upstream/main"))
    $upHead = Invoke-Git @('log', '-1', '--format=%h %ad', '--date=short', 'upstream/main')
    Write-Host "upstream/main      : $upHead"
    Write-Host "main behind        : $behindMain"
    Write-Host "$DevBranch behind : $behindDev"
    if ($behindDev -eq 0) { Write-Host 'RESULT: up to date - nothing to merge'; return $false }
    Write-Host '--- new upstream commits (max 30) ---'
    Invoke-Git @('log', '--oneline', '-30', "$DevBranch..upstream/main") | ForEach-Object { Write-Host $_.Substring(0, [Math]::Min(140, $_.Length)) }
    $base = Invoke-Git @('merge-base', $DevBranch, 'upstream/main')
    $changed = Invoke-Git @('diff', '--name-only', $base, 'upstream/main')
    $hits = $changed | Where-Object { $f = $_; $Hotspots | Where-Object { $f -eq $_ -or $f.StartsWith("$_/") } }
    Write-Host "--- upstream files changed: $(@($changed).Count); hotspots touched: $(@($hits).Count) ---"
    $hits | ForEach-Object { Write-Host "  HOTSPOT $_" }
    return $true
}

function Invoke-Apply {
    $dirty = Invoke-Git @('status', '--porcelain', '--untracked-files=no')
    if ($dirty) { throw 'working tree has tracked changes - commit or stash first' }
    $name = 'sync/upstream-' + (Get-Date -Format 'yyyyMMdd')
    Invoke-Git @('switch', '-c', $name, $DevBranch) | Out-Null
    & git merge --no-ff --no-edit upstream/main
    if ($LASTEXITCODE -ne 0) {
        Write-Output "CONFLICT on $name - resolve these, then run the gates in UPSTREAM_SYNC_KO.md:"
        Invoke-Git @('diff', '--name-only', '--diff-filter=U')
        exit 2
    }
    Write-Output "merged upstream/main into $name (not pushed). Run the gates next."
}

Confirm-UpstreamRemote
$needed = Show-Report
if ($Apply -and $needed) { Invoke-Apply }
