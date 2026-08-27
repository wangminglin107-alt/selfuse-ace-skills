from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).parents[2]
SKILLS = ROOT / "skills"


def load_skill(name: str) -> tuple[dict[str, object], str]:
    text = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
    _, frontmatter, body = text.split("---", 2)
    return yaml.safe_load(frontmatter), body.strip()


def test_paper_writer_is_a_thin_compatibility_route_to_research_os() -> None:
    frontmatter, body = load_skill("ssci-paper-writer")

    assert frontmatter["metadata"] == {
        "role": "compatibility",
        "delegates_to": "research-os",
    }
    assert len(body) < 900
    assert "## Procedure" not in body
    assert "## Shared operating rules" not in body


def test_legacy_framing_name_delegates_without_duplicating_method() -> None:
    frontmatter, body = load_skill("ssci-research-framing")

    assert frontmatter["metadata"] == {
        "role": "compatibility",
        "delegates_to": "research-framing",
    }
    assert len(body) < 700
    assert "## Procedure" not in body


def test_research_os_is_the_only_lifecycle_owner() -> None:
    _, os_body = load_skill("research-os")
    assert "evidence-to-chinese-note" in os_body

    for name in ("ssci-paper-writer", "ssci-research-framing"):
        _, body = load_skill(name)
        assert "start, begin, complete, checkpoint, verify, and resume" not in body
