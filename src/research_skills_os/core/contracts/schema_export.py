"""Export stable JSON Schema snapshots from the canonical Pydantic models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

from pydantic import BaseModel

from research_skills_os.core.contracts.models import (
    ArtifactEnvelope,
    Checkpoint,
    ExecutionRequest,
    ExecutionResult,
    GateResult,
)

SCHEMA_MODELS: Final[dict[str, type[BaseModel]]] = {
    "artifact-envelope.schema.json": ArtifactEnvelope,
    "checkpoint.schema.json": Checkpoint,
    "execution-request.schema.json": ExecutionRequest,
    "execution-result.schema.json": ExecutionResult,
    "gate-result.schema.json": GateResult,
}


def export_schemas(destination: Path | None = None) -> Path:
    """Write normalized schemas and return their destination directory."""

    target = destination or Path(__file__).resolve().parents[2] / "schemas"
    target.mkdir(parents=True, exist_ok=True)
    for filename, model in SCHEMA_MODELS.items():
        content = json.dumps(
            model.model_json_schema(), ensure_ascii=False, indent=2, sort_keys=True
        )
        (target / filename).write_text(f"{content}\n", encoding="utf-8", newline="\n")
    return target


def main() -> None:
    export_schemas()


if __name__ == "__main__":
    main()
