"""Deterministic YAML discovery and cross-specification validation."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import ValidationError

from research_skills_os.core.errors import DuplicateSpec, SpecLoadError
from research_skills_os.core.registry.models import (
    CapabilitySpec,
    RegistryCatalog,
    WorkflowSpec,
)

SpecT = TypeVar("SpecT", CapabilitySpec, WorkflowSpec)


class RegistryLoader:
    def __init__(
        self,
        *,
        capability_roots: Iterable[str | Path] = (),
        workflow_roots: Iterable[str | Path] = (),
    ) -> None:
        self.capability_roots = [Path(root) for root in capability_roots]
        self.workflow_roots = [Path(root) for root in workflow_roots]

    def load(self) -> RegistryCatalog:
        capabilities: dict[str, CapabilitySpec] = {}
        for path in self._discover(self.capability_roots):
            capability_spec = self._parse(path, CapabilitySpec)
            if capability_spec.id in capabilities:
                raise DuplicateSpec(f"duplicate capability id: {capability_spec.id}")
            capabilities[capability_spec.id] = capability_spec

        workflows: dict[str, WorkflowSpec] = {}
        for path in self._discover(self.workflow_roots):
            workflow_spec = self._parse(path, WorkflowSpec)
            if workflow_spec.id in workflows:
                raise DuplicateSpec(f"duplicate workflow id: {workflow_spec.id}")
            workflows[workflow_spec.id] = workflow_spec

        for workflow in workflows.values():
            nodes = {node.id: node for node in workflow.nodes}
            for node in workflow.nodes:
                if node.capability_id not in capabilities:
                    raise SpecLoadError(
                        f"workflow {workflow.id} references unknown capability {node.capability_id}"
                    )
            for mapping in workflow.artifact_mappings:
                source = capabilities[nodes[mapping.from_node].capability_id]
                unknown_types = sorted(set(mapping.artifact_types) - set(source.output_types))
                if unknown_types:
                    raise SpecLoadError(
                        f"workflow {workflow.id} maps undeclared outputs from "
                        f"{source.id}: {', '.join(unknown_types)}"
                    )
        return RegistryCatalog(
            capabilities={key: capabilities[key] for key in sorted(capabilities)},
            workflows={key: workflows[key] for key in sorted(workflows)},
        )

    @staticmethod
    def _discover(roots: list[Path]) -> list[Path]:
        discovered: set[Path] = set()
        for root in roots:
            if root.is_file():
                discovered.add(root.resolve())
            elif root.is_dir():
                discovered.update(path.resolve() for path in root.rglob("*.yaml"))
                discovered.update(path.resolve() for path in root.rglob("*.yml"))
            else:
                raise SpecLoadError(f"specification path does not exist: {root}")
        return sorted(discovered, key=lambda path: path.as_posix().casefold())

    @staticmethod
    def _parse(path: Path, model: type[SpecT]) -> SpecT:
        try:
            raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
            return model.model_validate(raw)
        except (OSError, yaml.YAMLError, ValidationError) as exc:
            raise SpecLoadError(f"invalid specification {path}: {exc}") from exc
