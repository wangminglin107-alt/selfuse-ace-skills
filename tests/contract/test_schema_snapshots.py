import json
from pathlib import Path

from research_skills_os.core.contracts.schema_export import SCHEMA_MODELS, export_schemas


def test_exported_schemas_match_committed_snapshots(tmp_path: Path):
    export_schemas(tmp_path)
    committed = Path(__file__).parents[2] / "src" / "research_skills_os" / "schemas"

    assert sorted(path.name for path in tmp_path.glob("*.schema.json")) == sorted(SCHEMA_MODELS)
    for filename in SCHEMA_MODELS:
        generated_data = json.loads((tmp_path / filename).read_text(encoding="utf-8"))
        committed_data = json.loads((committed / filename).read_text(encoding="utf-8"))
        assert generated_data == committed_data
