from pathlib import Path

import pytest

from research_skills_os.core.errors import DuplicateSpec, SpecLoadError
from research_skills_os.core.registry.loader import RegistryLoader

FIXTURES = Path(__file__).parents[2] / "fixtures" / "registry"


def write_yaml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def test_loads_strict_capability_spec_from_yaml():
    catalog = RegistryLoader(capability_roots=[FIXTURES / "valid-capability.yaml"]).load()

    spec = catalog.capabilities["research-framing"]
    assert spec.id == "research-framing"
    assert spec.input_types == ["idea_memo"]
    assert spec.output_types == ["research_brief"]
    assert spec.network == "none"
    assert catalog.workflows == {}


def test_rejects_workflow_that_embeds_capability_prompt():
    with pytest.raises(SpecLoadError, match="prompt"):
        RegistryLoader(
            capability_roots=[FIXTURES / "valid-capability.yaml"],
            workflow_roots=[FIXTURES / "invalid-workflow-embedded-prompt.yaml"],
        ).load()


def test_rejects_duplicate_capability_ids(tmp_path: Path):
    first = tmp_path / "a" / "capability.yaml"
    second = tmp_path / "b" / "capability.yaml"
    content = (FIXTURES / "valid-capability.yaml").read_text(encoding="utf-8")
    write_yaml(first, content)
    write_yaml(second, content)

    with pytest.raises(DuplicateSpec, match="research-framing"):
        RegistryLoader(capability_roots=[tmp_path]).load()


def test_rejects_workflow_reference_to_unknown_capability(tmp_path: Path):
    workflow = tmp_path / "workflow.yaml"
    write_yaml(
        workflow,
        """spec_version: "1.0"
kind: workflow
id: idea-to-novelty
version: "1.0"
entry_node: missing
terminal_nodes: [missing]
nodes:
  - id: missing
    capability_id: not-registered
edges: []
""",
    )

    with pytest.raises(SpecLoadError, match="not-registered"):
        RegistryLoader(workflow_roots=[workflow]).load()


def test_rejects_cyclic_v1_workflow(tmp_path: Path):
    workflow = tmp_path / "workflow.yaml"
    write_yaml(
        workflow,
        """spec_version: "1.0"
kind: workflow
id: cyclic
version: "1.0"
entry_node: first
terminal_nodes: [second]
nodes:
  - id: first
    capability_id: research-framing
  - id: second
    capability_id: research-framing
edges:
  - from: first
    to: second
  - from: second
    to: first
""",
    )

    with pytest.raises(SpecLoadError, match="cycle"):
        RegistryLoader(
            capability_roots=[FIXTURES / "valid-capability.yaml"],
            workflow_roots=[workflow],
        ).load()


def test_discovers_nested_specs_in_sorted_order(tmp_path: Path):
    template = (FIXTURES / "valid-capability.yaml").read_text(encoding="utf-8")
    write_yaml(tmp_path / "z" / "capability.yaml", template.replace("research-framing", "z-last"))
    write_yaml(tmp_path / "a" / "capability.yaml", template.replace("research-framing", "a-first"))

    catalog = RegistryLoader(capability_roots=[tmp_path]).load()

    assert list(catalog.capabilities) == ["a-first", "z-last"]
