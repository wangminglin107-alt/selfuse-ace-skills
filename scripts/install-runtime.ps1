[CmdletBinding()]
param(
    [string]$RuntimeRoot = (Join-Path $env:USERPROFILE '.codex\research-skills-os-runtime'),
    [string]$LauncherDirectory = (Join-Path $env:USERPROFILE 'bin'),
    [string]$PythonExecutable = '',
    [string]$BuildPython = '',
    [string]$Wheelhouse = '',
    [switch]$Replace,
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ProjectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$RuntimeRootPath = [IO.Path]::GetFullPath($RuntimeRoot)
$LauncherDirectoryPath = [IO.Path]::GetFullPath($LauncherDirectory)
$LauncherPath = [IO.Path]::GetFullPath((Join-Path $LauncherDirectoryPath 'research-os.cmd'))
$RecordPath = Join-Path $RuntimeRootPath '.research-skills-os-runtime-install.json'
$LockPath = Join-Path $ProjectRoot 'requirements-runtime.lock'
$BackupRoot = Join-Path ([IO.Path]::GetDirectoryName($RuntimeRootPath)) '.research-skills-os-runtime-backups'

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

function Assert-DirectChild {
    param([string]$Root, [string]$Candidate, [string]$Name)
    $expected = [IO.Path]::GetFullPath((Join-Path $Root $Name))
    $actual = [IO.Path]::GetFullPath($Candidate)
    if (-not $actual.Equals($expected, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Unsafe launcher path: $actual"
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
            throw "Reparse points are not allowed in runtime install trees: $($item.FullName)"
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
    $bytes = [Text.Encoding]::UTF8.GetBytes([string]::Join("`n", $entries))
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try { $digest = $algorithm.ComputeHash($bytes) }
    finally { $algorithm.Dispose() }
    return -join @($digest | ForEach-Object { $_.ToString('x2') })
}

function Write-JsonUtf8 {
    param([string]$Path, [object]$Value)
    $json = $Value | ConvertTo-Json -Depth 10
    [IO.File]::WriteAllText($Path, "$json`n", [Text.UTF8Encoding]::new($false))
}

function Invoke-Checked {
    param([string]$Executable, [string[]]$Arguments)
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $Executable"
    }
}

Assert-SafeRuntimeRoot -Path $RuntimeRootPath
Assert-DirectChild -Root $LauncherDirectoryPath -Candidate $LauncherPath -Name 'research-os.cmd'
if (-not (Test-Path -LiteralPath $LockPath -PathType Leaf)) {
    throw "Runtime lock is missing: $LockPath"
}

$ExistingRecord = $null
if (Test-Path -LiteralPath $RecordPath -PathType Leaf) {
    $ExistingRecord = Get-Content -LiteralPath $RecordPath -Raw -Encoding UTF8 | ConvertFrom-Json
}
$SourceDigest = Get-DirectoryDigest -Path (Join-Path $ProjectRoot 'src\research_skills_os')
$LockDigest = (Get-FileHash -LiteralPath $LockPath -Algorithm SHA256).Hash.ToLowerInvariant()
$ManagedUnchanged = $false
if ($null -ne $ExistingRecord -and
    $ExistingRecord.record_version -eq '1.0' -and
    $ExistingRecord.source_sha256 -eq $SourceDigest -and
    $ExistingRecord.lock_sha256 -eq $LockDigest -and
    (Test-Path -LiteralPath $LauncherPath -PathType Leaf)) {
    $launcherDigest = (Get-FileHash -LiteralPath $LauncherPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $ManagedUnchanged = $launcherDigest -eq $ExistingRecord.launcher_sha256
}

$RuntimeExists = Test-Path -LiteralPath $RuntimeRootPath
$LauncherExists = Test-Path -LiteralPath $LauncherPath
if ($ManagedUnchanged) {
    $Actions = @('unchanged')
}
else {
    $Actions = @('create_runtime', 'create_launcher')
    if (($RuntimeExists -or $LauncherExists) -and -not $Replace) {
        if ($WhatIf) { $Actions = @('collision') }
        else { throw 'Runtime or launcher collision detected. Re-run with -Replace to create backups.' }
    }
}

if ($WhatIf) {
    [pscustomobject]@{
        mode = 'what_if'
        runtime_root = $RuntimeRootPath
        launcher = $LauncherPath
        actions = $Actions
    } | ConvertTo-Json -Depth 5
    exit 0
}

if ($ManagedUnchanged) {
    $RuntimePython = Join-Path $RuntimeRootPath 'Scripts\python.exe'
    Invoke-Checked -Executable $RuntimePython -Arguments @('-m', 'research_skills_os.cli', '--help')
    [pscustomobject]@{
        mode = 'install'
        status = 'unchanged'
        runtime_root = $RuntimeRootPath
        launcher = $LauncherPath
    } | ConvertTo-Json -Depth 5
    exit 0
}

if ([string]::IsNullOrWhiteSpace($PythonExecutable)) {
    $PythonExecutable = (& py -3.12 -c 'import sys; print(sys.executable)').Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($PythonExecutable)) {
        throw 'Python 3.12 is required.'
    }
}
$PythonExecutable = (Resolve-Path -LiteralPath $PythonExecutable).Path
if ([string]::IsNullOrWhiteSpace($BuildPython)) {
    $BuildPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
}
$BuildPython = (Resolve-Path -LiteralPath $BuildPython).Path
if (-not [string]::IsNullOrWhiteSpace($Wheelhouse)) {
    $Wheelhouse = (Resolve-Path -LiteralPath $Wheelhouse).Path
}

$BackupSession = Join-Path $BackupRoot "$([DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ'))-$([guid]::NewGuid().ToString('N'))"
$RuntimeBackup = $null
$LauncherBackup = $null
$TemporaryWheelDirectory = Join-Path ([IO.Path]::GetTempPath()) "research-os-wheel-$([guid]::NewGuid().ToString('N'))"
$InstalledRuntime = $false
$InstalledLauncher = $false
try {
    if ($RuntimeExists) {
        Assert-NoReparsePoint -Path $RuntimeRootPath
        Assert-NoReparsePoint -Path $BackupRoot
        New-Item -ItemType Directory -Path $BackupSession -Force | Out-Null
        $RuntimeBackup = Join-Path $BackupSession 'runtime'
        Move-Item -LiteralPath $RuntimeRootPath -Destination $RuntimeBackup
    }
    if ($LauncherExists) {
        Assert-NoReparsePoint -Path $LauncherPath
        if (-not (Test-Path -LiteralPath $BackupSession)) {
            New-Item -ItemType Directory -Path $BackupSession -Force | Out-Null
        }
        $LauncherBackup = Join-Path $BackupSession 'research-os.cmd'
        Move-Item -LiteralPath $LauncherPath -Destination $LauncherBackup
    }
    New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($RuntimeRootPath)) -Force | Out-Null
    Invoke-Checked -Executable $PythonExecutable -Arguments @('-m', 'venv', $RuntimeRootPath)
    $InstalledRuntime = $true
    $RuntimePython = Join-Path $RuntimeRootPath 'Scripts\python.exe'
    $dependencyArguments = @('-m', 'pip', 'install', '--disable-pip-version-check', '--require-hashes')
    if (-not [string]::IsNullOrWhiteSpace($Wheelhouse)) {
        $dependencyArguments += @('--no-index', '--find-links', $Wheelhouse)
    }
    $dependencyArguments += @('-r', $LockPath)
    Invoke-Checked -Executable $RuntimePython -Arguments $dependencyArguments

    New-Item -ItemType Directory -Path $TemporaryWheelDirectory | Out-Null
    Invoke-Checked -Executable $BuildPython -Arguments @(
        '-m', 'pip', 'wheel', '--disable-pip-version-check', '--no-deps',
        '--no-build-isolation', '--wheel-dir', $TemporaryWheelDirectory, $ProjectRoot
    )
    $Wheels = @(Get-ChildItem -LiteralPath $TemporaryWheelDirectory -Filter '*.whl' -File)
    if ($Wheels.Count -ne 1) { throw 'Expected exactly one Research Skills OS wheel.' }
    Invoke-Checked -Executable $RuntimePython -Arguments @(
        '-m', 'pip', 'install', '--disable-pip-version-check', '--no-deps', $Wheels[0].FullName
    )

    New-Item -ItemType Directory -Path $LauncherDirectoryPath -Force | Out-Null
    $launcherContent = "@echo off`r`n`"$RuntimePython`" -m research_skills_os.cli %*`r`n"
    [IO.File]::WriteAllText($LauncherPath, $launcherContent, [Text.ASCIIEncoding]::new())
    $InstalledLauncher = $true
    Invoke-Checked -Executable $LauncherPath -Arguments @('--help')
    $LauncherDigest = (Get-FileHash -LiteralPath $LauncherPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $Record = [pscustomobject]@{
        record_version = '1.0'
        installation_id = [guid]::NewGuid().ToString('N')
        installed_at_utc = [DateTime]::UtcNow.ToString('o')
        runtime_root = $RuntimeRootPath
        launcher = $LauncherPath
        launcher_sha256 = $LauncherDigest
        source_sha256 = $SourceDigest
        lock_sha256 = $LockDigest
        python_executable = $PythonExecutable
        backup_root = if ($null -ne $RuntimeBackup -or $null -ne $LauncherBackup) { $BackupSession } else { $null }
        runtime_backup = $RuntimeBackup
        launcher_backup = $LauncherBackup
        rollback_command = "& '$([IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'uninstall-runtime.ps1')))' -RuntimeRoot '$RuntimeRootPath' -LauncherDirectory '$LauncherDirectoryPath'"
    }
    Write-JsonUtf8 -Path $RecordPath -Value $Record
}
catch {
    if ($InstalledLauncher -and (Test-Path -LiteralPath $LauncherPath)) {
        Remove-Item -LiteralPath $LauncherPath -Force
    }
    if ($InstalledRuntime -and (Test-Path -LiteralPath $RuntimeRootPath)) {
        Assert-SafeRuntimeRoot -Path $RuntimeRootPath
        Remove-Item -LiteralPath $RuntimeRootPath -Recurse -Force
    }
    if ($null -ne $RuntimeBackup -and (Test-Path -LiteralPath $RuntimeBackup)) {
        Move-Item -LiteralPath $RuntimeBackup -Destination $RuntimeRootPath
    }
    if ($null -ne $LauncherBackup -and (Test-Path -LiteralPath $LauncherBackup)) {
        Move-Item -LiteralPath $LauncherBackup -Destination $LauncherPath
    }
    throw
}
finally {
    if (Test-Path -LiteralPath $TemporaryWheelDirectory) {
        Remove-Item -LiteralPath $TemporaryWheelDirectory -Recurse -Force
    }
}

$Record | ConvertTo-Json -Depth 10
