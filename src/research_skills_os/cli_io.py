"""Stable JSON output helpers for skills and operators."""

import json
import sys
from typing import Any


def emit_json(value: Any) -> None:
    sys.stdout.write(
        f"{json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=True)}\n"
    )


def emit_error(message: str) -> None:
    sys.stderr.write(f"{message}\n")
