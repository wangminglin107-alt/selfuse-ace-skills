from __future__ import annotations

from pathlib import Path

import pytest

from research_skills_os.core.errors import SpecLoadError
from research_skills_os.core.registry.loader import RegistryLoader


def write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def capabilities(tmp_path: Path) -> Path:
    root = tmp_path / "capabilities"
    write(
        root / "producer.yaml",
        """spec_version: "1.0"
kind: capability
id: producer
version: "1.0"
input_types: []
output_types: [evidence]
""",
    )
    write(
        root / "consumer.yaml",
        """spec_version: "1.0"
kind: capability
id: consumer
version: "1.0"
input_types: [accepted_evidence]
output_types: [manuscript]
""",
    )
    return root


def workflow(tmp_path: Path, body: str) -> Path:
    return write(
        tmp_path / "workflow.yaml",
        f"""spec_version: "1.0"
kind: workflow
id: semantic-test
version: "1.0"
entry_node: produce
terminal_nodes: [consume]
{body}
""",
    )


def test_rejects_artifact_not_accepted_by_target_capability(tmp_path: Path) -> None:
    path = workflow(
        tmp_path,
        """nodes:
  - id: produce
    capability_id: producer
  - id: consume
    capability_id: consumer
edges:
  - from: produce
    to: consume
artifact_mappings:
  - from_node: produce
    artifact_types: [evidence]
    to_node: consume
""",
    )

    with pytest.raises(SpecLoadError, match=r"does not accept.*evidence"):
        RegistryLoader(capability_roots=[capabilities(tmp_path)], workflow_roots=[path]).load()


def test_rejects_unreachable_non_entry_node(tmp_path: Path) -> None:
    path = workflow(
        tmp_path,
        """nodes:
  - id: produce
    capability_id: producer
  - id: orphan
    capability_id: producer
  - id: consume
    capability_id: consumer
edges:
  - from: produce
    to: consume
""",
    )

    with pytest.raises(SpecLoadError, match=r"unreachable.*orphan"):
        RegistryLoader(capability_roots=[capabilities(tmp_path)], workflow_roots=[path]).load()


def test_rejects_terminal_with_outgoing_edge(tmp_path: Path) -> None:
    path = workflow(
        tmp_path,
        """nodes:
  - id: produce
    capability_id: producer
  - id: consume
    capability_id: consumer
  - id: after
    capability_id: consumer
edges:
  - from: produce
    to: consume
  - from: consume
    to: after
""",
    )

    with pytest.raises(SpecLoadError, match=r"terminal.*outgoing"):
        RegistryLoader(capability_roots=[capabilities(tmp_path)], workflow_roots=[path]).load()


def test_autonomous_review_must_also_be_human_review(tmp_path: Path) -> None:
    path = workflow(
        tmp_path,
        """nodes:
  - id: produce
    capability_id: producer
  - id: consume
    capability_id: consumer
    human_review: false
    autonomous_review: true
edges:
  - from: produce
    to: consume
""",
    )

    with pytest.raises(SpecLoadError, match=r"autonomous_review.*human_review"):
        RegistryLoader(capability_roots=[capabilities(tmp_path)], workflow_roots=[path]).load()


def test_current_project_registries_pass_deep_validation() -> None:
    root = Path(__file__).parents[3]
    catalog = RegistryLoader(
        capability_roots=[root / "src" / "research_skills_os" / "capabilities"],
        workflow_roots=[root / "src" / "research_skills_os" / "workflows"],
    ).load()

    assert {"idea-to-novelty", "literature-to-theory"} <= set(catalog.workflows)
