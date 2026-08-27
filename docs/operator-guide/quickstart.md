# Quickstart

This offline example initializes a project, installs only declarative registry specifications into
that project, validates an interactive workflow request, starts the run, and begins the first
capability. It deliberately stops before scholarly work because capability results must contain
real artifacts and deterministic gate results.

Set `RESEARCH_OS_REPO_ROOT` and optionally `RESEARCH_OS_DEMO_ROOT`, or run the block from this
repository. Paths may contain spaces and CJK characters.

<!-- doc-test:start quickstart -->
```powershell
$RepoRoot = if ($env:RESEARCH_OS_REPO_ROOT) { $env:RESEARCH_OS_REPO_ROOT } else { (Resolve-Path '.').Path }
$ProjectRoot = if ($env:RESEARCH_OS_DEMO_ROOT) { $env:RESEARCH_OS_DEMO_ROOT } else { Join-Path $PWD 'research demo 研究' }
$Python = Join-Path $RepoRoot '.venv\Scripts\python.exe'
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

& $Python -m research_skills_os.cli project init --root $ProjectRoot --project-id demo-project
if ($LASTEXITCODE -ne 0) { throw "project init failed: $LASTEXITCODE" }

$RegistryRoot = Join-Path $ProjectRoot '.research-os\registry'
$CapabilityRegistry = Join-Path $RegistryRoot 'capabilities'
$WorkflowRegistry = Join-Path $RegistryRoot 'workflows'
New-Item -ItemType Directory -Force -Path $CapabilityRegistry, $WorkflowRegistry | Out-Null
Copy-Item -Recurse -Force (Join-Path $RepoRoot 'src\research_skills_os\capabilities\*') $CapabilityRegistry
Copy-Item -Recurse -Force (Join-Path $RepoRoot 'src\research_skills_os\workflows\*') $WorkflowRegistry

$RequestPath = Join-Path $ProjectRoot 'interactive-request.json'
$Request = @{
  request_id = 'demo-interactive-1'
  project_id = 'demo-project'
  target = @{ kind = 'workflow'; id = 'idea-to-novelty' }
  mode = 'interactive'
  goal = 'Develop the supplied creator-exit idea through a bounded novelty audit.'
  constraints = @{ language = 'bilingual'; domain = 'communication'; network = 'deny' }
} | ConvertTo-Json -Depth 8
[System.IO.File]::WriteAllText($RequestPath, $Request, $Utf8NoBom)

& $Python -m research_skills_os.cli validate request $RequestPath
if ($LASTEXITCODE -ne 0) { throw "request validation failed: $LASTEXITCODE" }
$RunOutput = & $Python -m research_skills_os.cli run start --project $ProjectRoot --request $RequestPath
if ($LASTEXITCODE -ne 0) { throw "run start failed: $LASTEXITCODE" }
$RunId = ($RunOutput | ConvertFrom-Json).run_id
& $Python -m research_skills_os.cli target begin --project $ProjectRoot --run $RunId --target research-framing
if ($LASTEXITCODE -ne 0) { throw "target begin failed: $LASTEXITCODE" }
$State = & $Python -m research_skills_os.cli run status --project $ProjectRoot --json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw "run status failed: $LASTEXITCODE" }

$Summary = @{ lifecycle = $State.lifecycle; active_target = $State.active_target; workflow = 'idea-to-novelty' } | ConvertTo-Json
[System.IO.File]::WriteAllText((Join-Path $ProjectRoot 'quickstart-result.json'), $Summary, $Utf8NoBom)
```
<!-- doc-test:end quickstart -->

Continue by invoking the active `research-framing` Skill. It produces and validates two artifacts,
registers them, and calls `target complete`. Interactive mode then returns a kernel checkpoint and
stops before `literature-intelligence`.

