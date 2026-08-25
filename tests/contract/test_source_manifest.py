import hashlib
from pathlib import Path

import pytest

from research_skills_os.core.provenance.manifest import ManifestValidationError, load_manifest

ROOT = Path(__file__).parents[2]
MANIFEST = ROOT / "SOURCE_MANIFEST.yaml"
FIXTURES = ROOT / "tests" / "fixtures" / "manifest"
UPSTREAM = ROOT.parent / "upstream"
LOCKED_COMMITS = {
    "jin-s13/ai-research-writing-skill": "5d6e4244e532189099ca5a9c5585b23febcae955",
    "Spark-To-Paper-Skills/spark-to-paper-skills": ("c17149def034bc777462de612926c8e3b6d01b8c"),
    "Haojae/SciPilot-Figure-Skill": "43098ddb9e6a6d142218540c114f9ed38922fc42",
    "Hsin-Hung/Academic-Skills": "71e9c42c60636602e87985f4306d134a3b63809e",
    "LeonChaoX/Qinyan-Academic-Skills": "646429a4eeb765360f6ce13b5936334225d52af8",
}
CHECKOUTS = {
    "jin-s13/ai-research-writing-skill": UPSTREAM / "ai-research-writing-skill",
    "Spark-To-Paper-Skills/spark-to-paper-skills": UPSTREAM / "spark-to-paper-skills",
    "Haojae/SciPilot-Figure-Skill": UPSTREAM / "scipilot-figure-skill",
    "Hsin-Hung/Academic-Skills": UPSTREAM / "academic-skills",
    "LeonChaoX/Qinyan-Academic-Skills": UPSTREAM / "qinyan-academic-skills",
}
LOCAL_SKILLS = {
    "ssci-argument-architecture",
    "ssci-bilingual-writing",
    "ssci-paper-writer",
    "ssci-peer-review",
    "ssci-research-framing",
    "ssci-revision-audit",
    "ssci-section-drafting",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_manifest_loads_and_pins_every_required_upstream_commit():
    manifest = load_manifest(MANIFEST)
    recorded = {
        source.upstream_repo: source.upstream_commit
        for source in manifest.sources
        if source.source_kind == "git"
    }

    assert LOCKED_COMMITS.items() <= recorded.items()
    assert all(source.license.status == "confirmed" for source in manifest.sources)
    assert all(source.security.review_status == "approved" for source in manifest.sources)


def test_manifest_records_all_seven_local_ssci_skills_by_content_hash():
    manifest = load_manifest(MANIFEST)
    local = {
        source.upstream_repo.removeprefix("local/codex-skill-"): source
        for source in manifest.sources
        if source.upstream_repo.startswith("local/codex-skill-")
    }

    assert set(local) == LOCAL_SKILLS
    for skill_name, source in local.items():
        path = Path(source.source_file)
        assert path == Path.home() / ".codex" / "skills" / skill_name / "SKILL.md"
        assert source.source_sha256 == sha256(path)


def test_recorded_source_files_and_local_targets_exist_and_match_hashes():
    manifest = load_manifest(MANIFEST)

    for source in manifest.sources:
        if source.source_kind == "git":
            source_path = CHECKOUTS[source.upstream_repo] / source.source_file
        else:
            source_path = Path(source.source_file)
        assert source_path.is_file(), source_path
        assert source.source_sha256 == sha256(source_path)
        if source.local_target is not None:
            assert (ROOT / source.local_target).is_file(), source.local_target


def test_networked_sources_declare_endpoints_and_security_notes():
    manifest = load_manifest(MANIFEST)

    for source in manifest.sources:
        if source.security.network != "none":
            assert source.security.endpoints
            assert source.security.network_notes


@pytest.mark.parametrize(
    ("fixture", "message"),
    [
        ("invalid-missing-license.yaml", "license"),
        ("invalid-adapted-without-tests.yaml", "adapted"),
    ],
)
def test_invalid_or_unauditable_manifests_block_acceptance(fixture: str, message: str):
    with pytest.raises(ManifestValidationError, match=message):
        load_manifest(FIXTURES / fixture)


def test_reference_only_sources_include_scipilot_and_qinyan_without_runtime_reuse():
    manifest = load_manifest(MANIFEST)
    reference_only = {
        source.upstream_repo: source
        for source in manifest.sources
        if source.reuse_mode == "reference_only"
    }

    assert "Haojae/SciPilot-Figure-Skill" in reference_only
    assert "LeonChaoX/Qinyan-Academic-Skills" in reference_only
    assert reference_only["Haojae/SciPilot-Figure-Skill"].local_target is None
    assert reference_only["LeonChaoX/Qinyan-Academic-Skills"].local_target is None
