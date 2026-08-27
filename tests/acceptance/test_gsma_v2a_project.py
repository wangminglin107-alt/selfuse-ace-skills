import hashlib
import json
import re
from pathlib import Path

import yaml

from research_skills_os.capabilities.citation_verification.gates import (
    evaluate_citation_verification,
)
from research_skills_os.capabilities.evidence_synthesis.gates import (
    evaluate_evidence_synthesis,
)
from research_skills_os.capabilities.paper_knowledge_base.gates import (
    evaluate_paper_knowledge_base,
)
from research_skills_os.capabilities.theory_architecture.gates import (
    evaluate_theory_architecture,
)
from research_skills_os.core.checkpoint.service import CheckpointService
from research_skills_os.core.contracts.enums import GateStatus
from research_skills_os.core.state.models import ProjectLifecycle
from research_skills_os.core.state.repository import StateRepository

ROOT = Path(__file__).parents[2]
PROJECT = ROOT / "projects" / "gsma-sentiment-engagement"
ARTIFACTS = PROJECT / "artifacts"
EXPECTED_SOURCES = {"norc-gsma-method", "brady-2017", "najafizada-2022"}


def load_json(name: str):
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))


def load_jsonl(name: str):
    return [
        json.loads(line)
        for line in (ARTIFACTS / name).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def assert_all_pass(results):
    failures = [result for result in results if result.status is not GateStatus.PASS]
    assert failures == []


def test_real_project_declares_bounded_associational_scope_and_official_sources():
    project = yaml.safe_load((PROJECT / "project.yaml").read_text(encoding="utf-8"))
    registry = yaml.safe_load((ARTIFACTS / "source-registry.yaml").read_text(encoding="utf-8"))
    combined = json.dumps(project, ensure_ascii=False).casefold()

    assert project["claim_boundary"] == "associational"
    assert "causal effect" not in combined
    assert "individual sentiment" not in combined
    assert registry["archive"]["official_url"].startswith("https://gss.norc.org/")
    assert len(registry["archive"]["sha256"]) == 64
    assert {source["source_id"] for source in registry["included_sources"]} == EXPECTED_SOURCES
    assert registry["candidate_sources"][0]["status"] == "metadata_only"


def test_document_index_hashes_and_exact_passages_are_locally_traceable():
    index = load_json("document-index.json")
    corpus = load_json("corpus-status.json")
    rows = load_jsonl("evidence-rows.jsonl")
    documents = {document["source_id"]: document for document in index["documents"]}

    assert set(documents) == EXPECTED_SOURCES
    for source_id, document in documents.items():
        path = PROJECT / document["path"]
        content = path.read_text(encoding="utf-8")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == document["artifact_sha256"]
        assert digest == corpus["artifact_hashes"][source_id]
        for row in (row for row in rows if row["source_id"] == source_id):
            assert row["exact_passage"] in content
            passage_hash = hashlib.sha256(row["exact_passage"].encode()).hexdigest()
            assert passage_hash == row["locator"]["content_sha256"]


def test_all_evidence_spine_gates_pass_without_promoting_causal_claims():
    rows = load_jsonl("evidence-rows.jsonl")
    assert_all_pass(
        evaluate_paper_knowledge_base(
            load_json("document-index.json"), load_json("corpus-status.json")
        )
    )
    assert_all_pass(
        evaluate_evidence_synthesis(
            rows,
            load_json("synthesis-matrix.json"),
            load_json("contradiction-ledger.json"),
            load_json("coverage-report.json"),
        )
    )
    assert_all_pass(
        evaluate_citation_verification(
            load_json("citation-identity-audit.json"),
            load_json("citation-support-audit.json"),
            load_json("citation-blockers.json"),
        )
    )
    assert_all_pass(
        evaluate_theory_architecture(
            load_json("theory-candidates.json"),
            load_json("construct-map.json"),
            load_json("theory-decision-packet.json"),
            (ARTIFACTS / "theory-rationale.md").read_text(encoding="utf-8"),
        )
    )

    assert any(row["evidence_role"] in {"qualifies", "null", "contradicts"} for row in rows)
    support = load_json("citation-support-audit.json")
    assert all(record["claim_strength"] != "causal" for record in support["records"])
    assert load_json("theory-decision-packet.json")["authorization_state"] == "proposed"


def test_project_has_token_efficient_zotero_obsidian_sync_contract():
    spec = yaml.safe_load((PROJECT / "library-sync.yaml").read_text(encoding="utf-8"))

    assert spec["zotero_collection"] == "Pilot\uff5cGSMA情绪与互动"
    assert spec["obsidian_project"] == "Research/GSMA情绪与互动"
    assert {source["source_id"] for source in spec["sources"]} == EXPECTED_SOURCES
    assert all((PROJECT / source["note_source"]).is_file() for source in spec["sources"])
    assert all(len(source["content_sha256"]) == 64 for source in spec["sources"])


def test_real_project_has_verified_kernel_checkpoint_and_primary_data_provenance():
    provenance = json.loads(
        (PROJECT / "provenance" / "gsma-data-source.json").read_text(encoding="utf-8")
    )
    checkpoint_id = (
        PROJECT / ".research-os" / "current-checkpoint"
    ).read_text(encoding="utf-8").strip()
    checkpoint_service = CheckpointService(PROJECT)
    checkpoint = checkpoint_service.load(checkpoint_id)
    verification = checkpoint_service.verify_resume(checkpoint_id)
    state = StateRepository(PROJECT).load()

    assert provenance["official_landing_page"] == "https://gss.norc.org/gsma.html"
    assert provenance["archive_sha256"] == (
        "6732e90eb1d692e4dfa71de947318cd86aef114a3aaad83e95ebdaf2ac9ef8b0"
    )
    assert re.fullmatch(r"[0-9]{8}T[0-9]{6}Z_[0-9a-f]{8}", checkpoint_id)
    assert checkpoint.completed_target == "theory-architecture"
    assert verification.status == "verified"
    assert state.lifecycle is ProjectLifecycle.PAUSED
    assert state.completed_targets[-1] == "theory-architecture"
