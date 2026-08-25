"""Exact routing to a registered capability or workflow specification."""

from research_skills_os.core.contracts.enums import TargetKind
from research_skills_os.core.contracts.models import TargetRef
from research_skills_os.core.errors import UnknownTarget
from research_skills_os.core.registry.models import (
    CapabilitySpec,
    RegistryCatalog,
    WorkflowSpec,
)


class Router:
    def __init__(self, catalog: RegistryCatalog) -> None:
        self.catalog = catalog

    def resolve(self, target: TargetRef) -> CapabilitySpec | WorkflowSpec:
        collection: dict[str, CapabilitySpec] | dict[str, WorkflowSpec]
        if target.kind is TargetKind.CAPABILITY:
            collection = self.catalog.capabilities
        else:
            collection = self.catalog.workflows
        try:
            return collection[target.id]
        except KeyError as exc:
            registered = ", ".join(sorted(collection)) or "<none>"
            raise UnknownTarget(
                f"unknown {target.kind.value} {target.id}; registered ids: {registered}"
            ) from exc
