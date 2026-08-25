"""Stable JSON output helpers for skills and operators."""

import json
import sys
from enum import IntEnum
from typing import Any


class ExitCode(IntEnum):
    SUCCESS = 0
    VALIDATION = 2
    BLOCKED_GATE = 3
    INTEGRITY_SECURITY = 4
    EXECUTION_FAILURE = 5


def emit_json(value: Any) -> None:
    sys.stdout.write(
        f"{json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=True)}\n"
    )


def emit_error(message: str) -> None:
    sys.stderr.write(f"{message}\n")


def emit_diagnostic(category: str, message: str) -> None:
    emit_error(f"{category}: {message}")
