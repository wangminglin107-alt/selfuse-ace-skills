[CmdletBinding()]
param(
    [string]$RuntimeRoot = (Join-Path $env:USERPROFILE '.codex\research-skills-os-runtime'),
    [string]$LauncherDirectory = (Join-Path $env:USERPROFILE 'bin'),
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RuntimeRootPath = [IO.Path]::GetFullPath($RuntimeRoot)
$LauncherDirectoryPath = [IO.Path]::GetFullPath($LauncherDirectory)
$LauncherPath = [IO.Path]::GetFullPath((Join-Path $LauncherDirectoryPath 'research-os.cmd'))
$RecordPath = Join-Path $RuntimeRootPath '.research-skills-os-runtime-install.json'
$ExpectedBackupRoot = [IO.Path]::GetFullPath((Join-Path (
            [IO.Path]::GetDirectoryName($RuntimeRootPath)
        ) '.research-skills-os-runtime-backups'))

function Assert-SafeRuntimeRoot {
    param([string]$Path)
    $full = [IO.Path]::GetFullPath($Path).TrimEnd('\', '/')
    $parent = [IO.Path]::GetDirectoryName($full)
    $UserProfilePath = [IO.Path]::GetFullPath($env:USERPROFILE).TrimEnd('\', '/')
    if ([string]::IsNullOrWhiteSpace($parent) -or
        $full.Equals($UserProfilePath, [StringComparison]::OrdinalIgnoreCase) -or
        $full.Equals([IO.Path]::GetPathRoot($full).TrimEnd('\', '/'), [StringComparison]::OrdinalIgnoreCase)) {
        throw "Unsafe runtime root: $full"
    }
}

function Assert-PathEquals {
    param([string]$Expected, [string]$Actual, [string]$Label)
    if (-not ([IO.Path]::GetFullPath($Expected)).Equals(
            [IO.Path]::GetFullPath($Actual), [StringComparison]::OrdinalIgnoreCase)) {
        throw "Install record contains an unsafe $Label path."
    }
}

function Assert-NoReparsePoint {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return }
    $items = @((Get-Item -LiteralPath $Path -Force))
    if ($items[0].PSIsContainer) {
        $items += @(Get-ChildItem -LiteralPath $Path -Force -Recurse)
    }
    foreach ($item in $items) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Reparse points are not allowed in runtime uninstall trees: $($item.FullName)"
        }
    }
}

function Assert-BackupSession {
    param([string]$Candidate)
    $actual = [IO.Path]::GetFullPath($Candidate).TrimEnd('\', '/')
    $parent = [IO.Path]::GetDirectoryName($actual)
    if (-not $parent.Equals($ExpectedBackupRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Install record contains an unsafe backup root.'
    }
    if (-not (Test-Path -LiteralPath $actual -PathType Container)) {
        throw 'Recorded backup root is missing.'
    }
    Assert-NoReparsePoint -Path $actual
    return $actual
}

function Assert-BackupChild {
    param([string]$SessionRoot, [string]$Candidate, [string]$ExpectedName)
    $expected = [IO.Path]::GetFullPath((Join-Path $SessionRoot $ExpectedName))
    $actual = [IO.Path]::GetFullPath($Candidate)
    if (-not $actual.Equals($expected, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Install record contains an unsafe backup path.'
    }
}

Assert-SafeRuntimeRoot -Path $RuntimeRootPath
Assert-NoReparsePoint -Path $RuntimeRootPath
if (-not (Test-Path -LiteralPath $RecordPath -PathType Leaf)) {
    if (Test-Path -LiteralPath $RuntimeRootPath) {
        throw 'Runtime exists without a managed install record; refusing uninstall.'
    }
    [pscustomobject]@{
        mode = if ($WhatIf) { 'what_if' } else { 'uninstall' }
        status = 'not_installed'
        runtime_root = $RuntimeRootPath
        launcher = $LauncherPath
    } | ConvertTo-Json -Depth 5
    exit 0
}

$Record = Get-Content -LiteralPath $RecordPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($Record.record_version -ne '1.0') { throw 'Unsupported runtime install record version.' }
Assert-PathEquals -Expected $RuntimeRootPath -Actual $Record.runtime_root -Label 'runtime'
Assert-PathEquals -Expected $LauncherPath -Actual $Record.launcher -Label 'launcher'
if (-not (Test-Path -LiteralPath $LauncherPath -PathType Leaf)) {
    throw 'Recorded launcher is missing; refusing partial uninstall.'
}
Assert-NoReparsePoint -Path $LauncherPath
$LauncherDigest = (Get-FileHash -LiteralPath $LauncherPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($LauncherDigest -ne $Record.launcher_sha256) {
    throw 'Installed launcher was modified; refusing uninstall.'
}

$RuntimeBackup = $Record.runtime_backup
$LauncherBackup = $Record.launcher_backup
if ($null -ne $RuntimeBackup -or $null -ne $LauncherBackup) {
    if ($null -eq $Record.backup_root) { throw 'Install record is missing its backup root.' }
    $BackupSession = Assert-BackupSession -Candidate $Record.backup_root
    if ($null -ne $RuntimeBackup) {
        Assert-BackupChild -SessionRoot $BackupSession -Candidate $RuntimeBackup -ExpectedName 'runtime'
        if (-not (Test-Path -LiteralPath $RuntimeBackup -PathType Container)) {
            throw 'Recorded runtime backup is missing.'
        }
        Assert-NoReparsePoint -Path $RuntimeBackup
    }
    if ($null -ne $LauncherBackup) {
        Assert-BackupChild -SessionRoot $BackupSession -Candidate $LauncherBackup -ExpectedName 'research-os.cmd'
        if (-not (Test-Path -LiteralPath $LauncherBackup -PathType Leaf)) {
            throw 'Recorded launcher backup is missing.'
        }
        Assert-NoReparsePoint -Path $LauncherBackup
    }
}

if ($WhatIf) {
    [pscustomobject]@{
        mode = 'what_if'
        status = 'planned'
        runtime_root = $RuntimeRootPath
        launcher = $LauncherPath
        restore_runtime_backup = $RuntimeBackup
        restore_launcher_backup = $LauncherBackup
    } | ConvertTo-Json -Depth 5
    exit 0
}

Assert-NoReparsePoint -Path $LauncherPath
Assert-NoReparsePoint -Path $RuntimeRootPath
if ($null -ne $Record.backup_root) {
    Assert-NoReparsePoint -Path $Record.backup_root
}
Remove-Item -LiteralPath $LauncherPath -Force
Assert-SafeRuntimeRoot -Path $RuntimeRootPath
Remove-Item -LiteralPath $RuntimeRootPath -Recurse -Force
if ($null -ne $RuntimeBackup) {
    Move-Item -LiteralPath $RuntimeBackup -Destination $RuntimeRootPath
}
if ($null -ne $LauncherBackup) {
    Move-Item -LiteralPath $LauncherBackup -Destination $LauncherPath
}

[pscustomobject]@{
    mode = 'uninstall'
    status = 'removed'
    runtime_root = $RuntimeRootPath
    launcher = $LauncherPath
    restored_runtime_backup = $RuntimeBackup
    restored_launcher_backup = $LauncherBackup
} | ConvertTo-Json -Depth 5
