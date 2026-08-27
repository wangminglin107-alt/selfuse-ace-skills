import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[2]
QUICKSTART = ROOT / "docs" / "operator-guide" / "quickstart.md"
EVIDENCE_GUIDE = ROOT / "docs" / "operator-guide" / "evidence-and-citation-states.md"
THEORY_GUIDE = ROOT / "docs" / "operator-guide" / "contradictions-and-theory-decisions.md"
COMMAND_BLOCK = re.compile(
    r"<!-- doc-test:start quickstart -->\s*```powershell\s*(.*?)\s*```\s*"
    r"<!-- doc-test:end quickstart -->",
    re.DOTALL,
)


def test_marked_quickstart_commands_run_in_windows_path_with_spaces_and_cjk(tmp_path: Path):
    content = QUICKSTART.read_text(encoding="utf-8")
    match = COMMAND_BLOCK.search(content)
    assert match is not None, "quickstart must contain one marked executable PowerShell block"
    project = tmp_path / "documented workflow 研究"
    environment = os.environ.copy()
    environment["RESEARCH_OS_REPO_ROOT"] = str(ROOT)
    environment["RESEARCH_OS_DEMO_ROOT"] = str(project)

    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            match.group(1),
        ],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads((project / "quickstart-result.json").read_text(encoding="utf-8"))
    assert summary["lifecycle"] == "running"
    assert summary["active_target"] == "research-framing"
    assert summary["workflow"] == "idea-to-novelty"
    assert (project / ".research-os" / "events.jsonl").is_file()


def test_v2a_guides_keep_identity_support_contradiction_and_human_decisions_separate():
    evidence = EVIDENCE_GUIDE.read_text(encoding="utf-8")
    theory = THEORY_GUIDE.read_text(encoding="utf-8")

    assert "identity_state" in evidence
    assert "support_state" in evidence
    assert "metadata_only" in evidence
    assert "manual_needed" in evidence
    assert "material contradiction" in theory
    assert "authorization_state" in theory
    assert "proposed" in theory
    assert "selected" in theory
