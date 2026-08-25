"""Project-scoped access to event history and current replayed state."""

from __future__ import annotations

from pathlib import Path

from research_skills_os.core.state.event_log import EventLog
from research_skills_os.core.state.models import ProjectEvent, ProjectState
from research_skills_os.core.state.reducer import reduce_events


class StateRepository:
    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root).resolve(strict=True)
        self.event_log = EventLog(self.project_root / ".research-os" / "events.jsonl")

    def append(self, event: ProjectEvent) -> ProjectEvent:
        return self.event_log.append(event)

    def load(self) -> ProjectState:
        return reduce_events(self.event_log.read_all())
