"""Durable JSONL event log with cross-process append serialization."""

from __future__ import annotations

import json
import os
from pathlib import Path

from filelock import FileLock
from pydantic import ValidationError

from research_skills_os.core.errors import EventLogCorruption
from research_skills_os.core.state.models import ProjectEvent


class EventLog:
    def __init__(self, path: str | Path, *, lock_timeout: float = 10.0) -> None:
        self.path = Path(path)
        self.lock = FileLock(f"{self.path}.lock", timeout=lock_timeout)

    def append(self, event: ProjectEvent) -> ProjectEvent:
        """Assign the next sequence and durably append one complete JSON line."""

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock:
            existing = self._read_unlocked()
            stored = event.model_copy(update={"sequence": len(existing) + 1})
            line = json.dumps(
                stored.model_dump(mode="json"),
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(f"{line}\n")
                handle.flush()
                os.fsync(handle.fileno())
            return stored

    def read_all(self) -> list[ProjectEvent]:
        with self.lock:
            return self._read_unlocked()

    def _read_unlocked(self) -> list[ProjectEvent]:
        if not self.path.exists():
            return []

        events: list[ProjectEvent] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                try:
                    raw = json.loads(line)
                    event = ProjectEvent.model_validate(raw)
                except (json.JSONDecodeError, ValidationError) as exc:
                    raise EventLogCorruption(
                        f"invalid event log entry at line {line_number}"
                    ) from exc
                if event.sequence != line_number:
                    raise EventLogCorruption(
                        f"event sequence mismatch at line {line_number}: {event.sequence}"
                    )
                events.append(event)
        return events
