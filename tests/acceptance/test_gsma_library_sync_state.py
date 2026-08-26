import json
from pathlib import Path, PurePosixPath

import yaml

ROOT = Path(__file__).parents[2]
PROJECT = ROOT / "projects" / "gsma-sentiment-engagement"


def test_live_state_maps_every_source_once_with_matching_hashes():
    spec = yaml.safe_load((PROJECT / "library-sync.yaml").read_text(encoding="utf-8"))
    state = json.loads(
        (PROJECT / "artifacts" / "library-sync-state.json").read_text(encoding="utf-8")
    )
    configured = {source["source_id"]: source for source in spec["sources"]}

    assert set(state["records"]) == set(configured)
    assert len({record["identity"] for record in state["records"].values()}) == len(configured)
    for source_id, record in state["records"].items():
        path = PurePosixPath(record["obsidian_note"])
        assert record["content_sha256"] == configured[source_id]["content_sha256"]
        assert len(record["zotero_item_key"]) == 8
        assert path.parts[:2] == ("Research", "GSMA情绪与互动")
        assert ".." not in path.parts


def test_pilot_records_discovered_gaps_and_concrete_improvements():
    audit = (PROJECT / "artifacts" / "library-sync-audit.md").read_text(encoding="utf-8")

    assert "## 已发现问题" in audit
    assert "## 改进计划" in audit
    assert "[已修复]" in audit
    assert "[后续]" in audit


def test_project_overview_links_all_three_source_notes():
    overview = (PROJECT / "notes" / "项目总览.md").read_text(encoding="utf-8")

    assert "[[Sources/Papers/norc-gsma-method" in overview
    assert "[[Sources/Papers/brady-2017" in overview
    assert "[[Sources/Papers/najafizada-2022" in overview
    assert "不支持因果解释" in overview
