import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[2]
LOCK = ROOT / "requirements.lock"
PIN = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s]+) --hash=sha256:([0-9a-f]{64})$")


def normalized(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).casefold()


def declared_direct_dependencies() -> set[str]:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    requirements = [
        *project["build-system"]["requires"],
        *project["project"]["dependencies"],
        *project["project"]["optional-dependencies"]["dev"],
    ]
    return {normalized(re.split(r"[<>=!~]", item, maxsplit=1)[0]) for item in requirements}


def test_dependency_lock_pins_and_hashes_every_entry_and_direct_dependency():
    lines = [
        line.strip()
        for line in LOCK.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    matches = [PIN.fullmatch(line) for line in lines]

    assert lines
    assert all(matches)
    locked_names = {normalized(match.group(1)) for match in matches if match is not None}
    assert declared_direct_dependencies() <= locked_names
    assert len(locked_names) == len(lines)
