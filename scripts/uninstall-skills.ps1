[CmdletBinding()]
param(
    [string]$SkillHome = (Join-Path $env:USERPROFILE '.codex\skills'),
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$SkillHomePath = [IO.Path]::GetFullPath($SkillHome)
$RecordPath = Join-Path $SkillHomePath '.research-skills-os-install.json'
$BackupRoot = [IO.Path]::GetFullPath((Join-Path $SkillHomePath '.research-skills-os-backups'))

function Assert-DirectChild {
    param([string]$Root, [string]$Candidate, [string]$Name)
    $expected = [IO.Path]::GetFullPath((Join-Path $Root $Name))
    $actual = [IO.Path]::GetFullPath($Candidate)
    if (-not $actual.Equals($expected, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Install record contains unsafe target path for $Name"
    }
}

function Assert-BackupPath {
    param([string]$Candidate)
    $actual = [IO.Path]::GetFullPath($Candidate)
    $prefix = $BackupRoot.TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar
    if (-not $actual.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Install record contains an unsafe backup path.'
    }
}

function Assert-NoReparsePoint {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }
    $items = @((Get-Item -LiteralPath $Path -Force))
    if ((Get-Item -LiteralPath $Path -Force).PSIsContainer) {
        $items += @(Get-ChildItem -LiteralPath $Path -Force -Recurse)
    }
    foreach ($item in $items) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Reparse points are not allowed in uninstall trees: $($item.FullName)"
        }
    }
}

function Get-DirectoryDigest {
    param([string]$Path)
    $root = [IO.Path]::GetFullPath($Path)
    $entries = @()
    foreach ($file in @(Get-ChildItem -LiteralPath $root -File -Recurse | Sort-Object FullName)) {
        $relative = $file.FullName.Substring($root.TrimEnd('\', '/').Length + 1).Replace('\', '/')
        $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        $entries += "${relative}:$hash"
    }
    $canonical = [string]::Join("`n", $entries)
    $bytes = [Text.Encoding]::UTF8.GetBytes($canonical)
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try {
        $digest = $algorithm.ComputeHash($bytes)
    }
    finally {
        $algorithm.Dispose()
    }
    return -join @($digest | ForEach-Object { $_.ToString('x2') })
}

if (-not (Test-Path -LiteralPath $RecordPath -PathType Leaf)) {
    [pscustomobject]@{
        mode = if ($WhatIf) { 'what_if' } else { 'uninstall' }
        status = 'not_installed'
        skill_home = $SkillHomePath
        skills = @()
    } | ConvertTo-Json -Depth 10
    exit 0
}

$Record = Get-Content -LiteralPath $RecordPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($Record.record_version -ne '1.0') {
    throw 'Unsupported install record version.'
}
if (-not ([IO.Path]::GetFullPath($Record.skill_home)).Equals(
        $SkillHomePath,
        [StringComparison]::OrdinalIgnoreCase
    )) {
    throw 'Install record belongs to a different skill home.'
}

$Plan = @()
foreach ($entry in $Record.skills) {
    $destination = [IO.Path]::GetFullPath($entry.destination)
    Assert-DirectChild -Root $SkillHomePath -Candidate $destination -Name $entry.name
    if (Test-Path -LiteralPath $destination) {
        Assert-NoReparsePoint -Path $destination
        $actual = Get-DirectoryDigest -Path $destination
        if ($actual -ne $entry.installed_sha256) {
            throw "Installed skill was modified; refusing uninstall: $($entry.name)"
        }
    }
    $backupPath = $entry.backup_path
    if ($null -ne $backupPath) {
        Assert-BackupPath -Candidate $backupPath
        if (-not (Test-Path -LiteralPath $backupPath -PathType Container)) {
            throw "Recorded backup is missing: $($entry.name)"
        }
        Assert-NoReparsePoint -Path $backupPath
    }
    $Plan += [pscustomobject]@{
        name = $entry.name
        destination = $destination
        backup_path = $backupPath
        action = if ($null -ne $backupPath) { 'restore_backup' } else { 'remove' }
    }
}

if ($WhatIf) {
    [pscustomobject]@{
        mode = 'what_if'
        status = 'planned'
        skill_home = $SkillHomePath
        skills = $Plan
    } | ConvertTo-Json -Depth 10
    exit 0
}

foreach ($item in $Plan) {
    Assert-DirectChild -Root $SkillHomePath -Candidate $item.destination -Name $item.name
    if (Test-Path -LiteralPath $item.destination) {
        Remove-Item -LiteralPath $item.destination -Recurse -Force
    }
    if ($null -ne $item.backup_path) {
        Move-Item -LiteralPath $item.backup_path -Destination $item.destination
    }
}
Remove-Item -LiteralPath $RecordPath -Force

[pscustomobject]@{
    mode = 'uninstall'
    status = 'removed'
    skill_home = $SkillHomePath
    skills = $Plan
} | ConvertTo-Json -Depth 10
