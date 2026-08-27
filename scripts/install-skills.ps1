[CmdletBinding()]
param(
    [string]$SkillHome = (Join-Path $env:USERPROFILE '.codex\skills'),
    [string]$SourceManifest = (Join-Path $PSScriptRoot '..\SOURCE_MANIFEST.yaml'),
    [switch]$Replace,
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$SkillNames = @(
    'citation-verification',
    'evidence-synthesis',
    'research-os',
    'research-framing',
    'literature-intelligence',
    'literature-to-theory',
    'novelty-audit',
    'idea-to-novelty',
    'paper-knowledge-base',
    'theory-architecture'
)
$ManifestCapabilities = @(
    'research-os',
    'research-framing',
    'literature-intelligence',
    'novelty-audit',
    'paper-knowledge-base',
    'evidence-synthesis',
    'citation-verification',
    'theory-architecture'
)
$SourceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\skills')).Path
$SourceManifestPath = [IO.Path]::GetFullPath($SourceManifest)
if (-not (Test-Path -LiteralPath $SourceManifestPath -PathType Leaf)) {
    throw "Source manifest is missing: $SourceManifestPath"
}
$ManifestText = Get-Content -LiteralPath $SourceManifestPath -Raw -Encoding UTF8
if ($ManifestText -notmatch '(?m)^manifest_version:\s*["'']?1\.0["'']?\s*$') {
    throw 'Source manifest has no supported manifest_version.'
}
foreach ($capability in $ManifestCapabilities) {
    $escaped = [Regex]::Escape($capability)
    if ($ManifestText -notmatch "(?m)^\s*(?:-\s*)?capability:\s*$escaped\s*$") {
        throw "Source manifest is incomplete: missing capability $capability"
    }
}
$SkillHomePath = [IO.Path]::GetFullPath($SkillHome)
$RecordPath = Join-Path $SkillHomePath '.research-skills-os-install.json'
$BackupRoot = Join-Path $SkillHomePath '.research-skills-os-backups'

function Assert-DirectChild {
    param([string]$Root, [string]$Candidate, [string]$Name)
    $expected = [IO.Path]::GetFullPath((Join-Path $Root $Name))
    $actual = [IO.Path]::GetFullPath($Candidate)
    if (-not $actual.Equals($expected, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Unsafe target path for $Name"
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
            throw "Reparse points are not allowed in install trees: $($item.FullName)"
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

function Write-JsonAtomic {
    param([string]$Path, [object]$Value)
    $temporary = "$Path.$([guid]::NewGuid().ToString('N')).tmp"
    try {
        $json = $Value | ConvertTo-Json -Depth 10
        [IO.File]::WriteAllText($temporary, "$json`n", [Text.UTF8Encoding]::new($false))
        if (Test-Path -LiteralPath $Path -PathType Leaf) {
            $replacedBackup = "$Path.$([guid]::NewGuid().ToString('N')).bak"
            try {
                [IO.File]::Replace($temporary, $Path, $replacedBackup)
            }
            finally {
                if (Test-Path -LiteralPath $replacedBackup) {
                    Remove-Item -LiteralPath $replacedBackup -Force
                }
            }
        }
        else {
            [IO.File]::Move($temporary, $Path)
        }
    }
    finally {
        if (Test-Path -LiteralPath $temporary) {
            Remove-Item -LiteralPath $temporary -Force
        }
    }
}

$ExistingRecord = $null
if (Test-Path -LiteralPath $RecordPath -PathType Leaf) {
    $ExistingRecord = Get-Content -LiteralPath $RecordPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($ExistingRecord.record_version -ne '1.0') {
        throw 'Unsupported install record version.'
    }
}
$ExistingByName = @{}
if ($null -ne $ExistingRecord) {
    foreach ($entry in $ExistingRecord.skills) {
        $ExistingByName[$entry.name] = $entry
    }
}

$Plan = @()
foreach ($name in $SkillNames) {
    $source = [IO.Path]::GetFullPath((Join-Path $SourceRoot $name))
    $destination = [IO.Path]::GetFullPath((Join-Path $SkillHomePath $name))
    Assert-DirectChild -Root $SkillHomePath -Candidate $destination -Name $name
    if (-not (Test-Path -LiteralPath (Join-Path $source 'SKILL.md') -PathType Leaf)) {
        throw "Skill source is incomplete: $name"
    }
    Assert-NoReparsePoint -Path $source
    $sourceDigest = Get-DirectoryDigest -Path $source
    $action = 'install'
    if (Test-Path -LiteralPath $destination) {
        Assert-NoReparsePoint -Path $destination
        $installedDigest = Get-DirectoryDigest -Path $destination
        $managed = $ExistingByName.ContainsKey($name)
        if ($managed -and $installedDigest -eq $sourceDigest) {
            $action = 'unchanged'
        }
        elseif ($Replace) {
            $action = 'replace'
        }
        else {
            $action = 'collision'
        }
    }
    $Plan += [pscustomobject]@{
        name = $name
        source = $source
        destination = $destination
        source_sha256 = $sourceDigest
        action = $action
    }
}

if ($WhatIf) {
    [pscustomobject]@{
        mode = 'what_if'
        skill_home = $SkillHomePath
        record_path = $RecordPath
        skills = $Plan
    } | ConvertTo-Json -Depth 10
    exit 0
}

$Collisions = @($Plan | Where-Object action -eq 'collision')
if ($Collisions.Count -gt 0) {
    $names = [string]::Join(', ', @($Collisions.name))
    throw "Skill collision detected: $names. Re-run with -Replace to create backups."
}

if (-not (Test-Path -LiteralPath $SkillHomePath)) {
    New-Item -ItemType Directory -Path $SkillHomePath | Out-Null
}
$SkillHomeItem = Get-Item -LiteralPath $SkillHomePath -Force
if (($SkillHomeItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
    throw "The skill home cannot be a reparse point: $SkillHomePath"
}

$BackupSession = Join-Path $BackupRoot "$([DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ'))-$([guid]::NewGuid().ToString('N'))"
$Completed = @()
function Undo-CompletedInstall {
    foreach ($completedItem in @($Completed | Sort-Object { $_.plan.name } -Descending)) {
        $destination = $completedItem.plan.destination
        Assert-DirectChild -Root $SkillHomePath -Candidate $destination -Name $completedItem.plan.name
        if ($completedItem.plan.action -ne 'unchanged' -and (Test-Path -LiteralPath $destination)) {
            Remove-Item -LiteralPath $destination -Recurse -Force
        }
        if ($null -ne $completedItem.backup_path -and (Test-Path -LiteralPath $completedItem.backup_path)) {
            Move-Item -LiteralPath $completedItem.backup_path -Destination $destination
        }
    }
}

try {
    foreach ($item in $Plan) {
        $backupPath = $null
        if ($item.action -eq 'unchanged') {
            if ($ExistingByName.ContainsKey($item.name)) {
                $backupPath = $ExistingByName[$item.name].backup_path
            }
            $Completed += [pscustomobject]@{
                plan = $item
                backup_path = $backupPath
            }
        }
        else {
            if ($item.action -eq 'replace') {
                if (-not (Test-Path -LiteralPath $BackupSession)) {
                    New-Item -ItemType Directory -Path $BackupSession | Out-Null
                }
                $backupPath = Join-Path $BackupSession $item.name
                Assert-DirectChild -Root $BackupSession -Candidate $backupPath -Name $item.name
                Move-Item -LiteralPath $item.destination -Destination $backupPath
            }
            $Completed += [pscustomobject]@{
                plan = $item
                backup_path = $backupPath
            }
            Copy-Item -LiteralPath $item.source -Destination $item.destination -Recurse
        }
    }
}
catch {
    Undo-CompletedInstall
    throw
}

try {
    $Commit = 'unknown'
    try {
        $Commit = (& git -C ([IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))) rev-parse HEAD).Trim()
    }
    catch {
        $Commit = 'unknown'
    }
    $Entries = @()
    foreach ($completedItem in $Completed) {
        $item = $completedItem.plan
        $installedDigest = Get-DirectoryDigest -Path $item.destination
        if ($installedDigest -ne $item.source_sha256) {
            throw "Installed hash mismatch: $($item.name)"
        }
        $Entries += [pscustomobject]@{
            name = $item.name
            source = $item.source
            destination = $item.destination
            source_sha256 = $item.source_sha256
            installed_sha256 = $installedDigest
            backup_path = $completedItem.backup_path
        }
    }
    $Status = if (@($Plan | Where-Object action -ne 'unchanged').Count -eq 0) {
        'unchanged'
    }
    else {
        'installed'
    }
    $Record = [pscustomobject]@{
        record_version = '1.0'
        project_commit = $Commit
        installed_at_utc = [DateTime]::UtcNow.ToString('o')
        skill_home = $SkillHomePath
        status = $Status
        skills = $Entries
        rollback_command = "& '$([IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'uninstall-skills.ps1')))' -SkillHome '$SkillHomePath'"
    }
    Write-JsonAtomic -Path $RecordPath -Value $Record
}
catch {
    Undo-CompletedInstall
    throw
}
$Record | ConvertTo-Json -Depth 10
