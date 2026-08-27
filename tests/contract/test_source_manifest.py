import hashlib
import subprocess
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
    "Yuan1z0825/nature-skills": "3817cd194c31010febb1312ab786e53cd8154333",
    "WUBING2023/PaperSpine": "360ae775639a27458d4f24040b65a4cbe935b213",
    "ganzhi-black/humanities-thesis-skill": "9f9c97162e250df8d6c214b828bb973828a2a780",
    "Liuxiangjian-ai/reference-checker-skill": "f30bd18b79f38bb24e57cad6ea0132323e329c94",
    "Light0305/Light-skills": "6b44f57d1274eb38a6c79dc29c2d21e5e0a225a9",
    "Imbad0202/academic-research-skills": "127ff85e4bbfcdd10b95040537b6c6bd7ad17aeb",
}
CHECKOUTS = {
    "jin-s13/ai-research-writing-skill": UPSTREAM / "ai-research-writing-skill",
    "Spark-To-Paper-Skills/spark-to-paper-skills": UPSTREAM / "spark-to-paper-skills",
    "Haojae/SciPilot-Figure-Skill": UPSTREAM / "scipilot-figure-skill",
    "Hsin-Hung/Academic-Skills": UPSTREAM / "academic-skills",
    "LeonChaoX/Qinyan-Academic-Skills": UPSTREAM / "qinyan-academic-skills",
    "Yuan1z0825/nature-skills": UPSTREAM / "nature-skills",
    "WUBING2023/PaperSpine": UPSTREAM / "paperspine",
    "ganzhi-black/humanities-thesis-skill": UPSTREAM / "humanities-thesis-skill",
    "Liuxiangjian-ai/reference-checker-skill": UPSTREAM / "reference-checker-skill",
    "Light0305/Light-skills": UPSTREAM / "light-skills",
    "Imbad0202/academic-research-skills": UPSTREAM / "academic-research-skills",
}
V2A_REPOSITORIES = set(LOCKED_COMMITS) - {
    "jin-s13/ai-research-writing-skill",
    "Spark-To-Paper-Skills/spark-to-paper-skills",
    "Haojae/SciPilot-Figure-Skill",
    "Hsin-Hung/Academic-Skills",
    "LeonChaoX/Qinyan-Academic-Skills",
}
V2A_CAPABILITIES = {
    "paper-knowledge-base",
    "evidence-synthesis",
    "citation-verification",
    "research-os",
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


def test_v2a_reuse_is_traceable_and_excludes_insecure_http_client():
    manifest = load_manifest(MANIFEST)
    v2a = [
        source
        for source in manifest.sources
        if source.upstream_repo in V2A_REPOSITORIES and source.capability in V2A_CAPABILITIES
    ]

    assert {source.upstream_repo for source in v2a} == V2A_REPOSITORIES
    assert all(
        source.local_target and source.tests.local
        for source in v2a
        if source.reuse_mode == "adapted"
    )
    assert all(source.local_target is None for source in v2a if source.reuse_mode == "conceptual")
    assert all(source.source_file != "scripts/lib/http_client.py" for source in manifest.sources)


def test_every_locked_checkout_is_at_the_recorded_commit():
    for repository, commit in LOCKED_COMMITS.items():
        checkout = CHECKOUTS[repository]
        head = subprocess.check_output(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True
        ).strip()
        assert head == commit


def test_v2c_writing_capabilities_record_file_level_source_influence():
    manifest = load_manifest(MANIFEST)
    recorded = {
        (source.capability, source.upstream_repo, source.source_file) for source in manifest.sources
    }

    assert {
        (
            "ssci-argument-architecture",
            "jin-s13/ai-research-writing-skill",
            "references/paper-story.md",
        ),
        (
            "ssci-section-drafting",
            "jin-s13/ai-research-writing-skill",
            "references/section-writing.md",
        ),
        (
            "academic-prose-style-audit",
            "WUBING2023/PaperSpine",
            "src/scripts/style_metrics.py",
        ),
        (
            "academic-prose-style-audit",
            "Yuan1z0825/nature-skills",
            "skills/nature-proposal-writer/references/chinese-review-writing-style.md",
        ),
        (
            "ssci-bilingual-writing",
            "Yuan1z0825/nature-skills",
            "skills/nature-writing/static/fragments/language/zh-to-en.md",
        ),
    } <= recorded
