import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC
from pathlib import Path

import pytest

from research_skills_os.core.errors import EventLogCorruption
from research_skills_os.core.state.event_log import EventLog
from research_skills_os.core.state.models import EventType, ProjectEvent


def make_event(event_id: str, event_type: EventType = EventType.RUN_STARTED) -> ProjectEvent:
    return ProjectEvent(event_id=event_id, type=event_type, payload={"run_id": event_id})


def test_appends_events_with_monotonic_sequence_and_utc_timestamp(tmp_path: Path):
    log = EventLog(tmp_path / ".research-os" / "events.jsonl")

    first = log.append(make_event("event-1"))
    second = log.append(make_event("event-2"))

    assert [first.sequence, second.sequence] == [1, 2]
    assert first.timestamp.tzinfo is UTC
    assert log.read_all() == [first, second]


def test_serializes_one_complete_json_object_per_line(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    log = EventLog(path)

    log.append(make_event("event-1"))
    log.append(make_event("event-2"))

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert [json.loads(line)["event_id"] for line in lines] == ["event-1", "event-2"]


def test_rejects_malformed_event_line(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    path.write_text('{"event_id":"broken"}\nnot-json\n', encoding="utf-8")
    log = EventLog(path)

    with pytest.raises(EventLogCorruption, match="line 1"):
        log.read_all()


def test_serializes_concurrent_appends_without_duplicate_sequences(tmp_path: Path):
    log = EventLog(tmp_path / ".research-os" / "events.jsonl")

    with ThreadPoolExecutor(max_workers=8) as executor:
        appended = list(
            executor.map(lambda index: log.append(make_event(f"event-{index}")), range(20))
        )

    stored = log.read_all()
    assert sorted(event.sequence for event in appended) == list(range(1, 21))
    assert [event.sequence for event in stored] == list(range(1, 21))
    assert {event.event_id for event in stored} == {f"event-{index}" for index in range(20)}
