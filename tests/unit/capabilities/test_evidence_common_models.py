import pytest
from pydantic import ValidationError

from research_skills_os.capabilities.evidence_common import (
    AccessState,
    ContentLocator,
    EvidenceRole,
    IdentityState,
    PrivacyLabel,
    SupportState,
    VerificationRoute,
)


def test_content_locator_requires_page_or_stable_section():
    with pytest.raises(ValidationError, match="page or section"):
        ContentLocator(block_id="block-1", content_sha256="a" * 64)


def test_content_locator_accepts_page_and_lowercase_sha256():
    locator = ContentLocator(page=7, block_id="p7-b2", content_sha256="a" * 64)

    assert locator.page == 7


@pytest.mark.parametrize("digest", ["A" * 64, "a" * 63, "g" * 64])
def test_content_locator_rejects_invalid_sha256(digest: str):
    with pytest.raises(ValidationError):
        ContentLocator(page=1, block_id="p1-b1", content_sha256=digest)


def test_evidence_states_are_closed_and_stable():
    assert {item.value for item in EvidenceRole} == {
        "supports",
        "qualifies",
        "contradicts",
        "null",
        "background",
    }
    assert {item.value for item in IdentityState} == {
        "verified",
        "mismatch",
        "not_found",
        "suspicious",
        "manual_needed",
    }
    assert {item.value for item in SupportState} == {
        "supports",
        "partial",
        "misaligned",
        "contradicted",
        "unavailable",
        "manual_needed",
    }
    assert {item.value for item in AccessState} == {
        "full_text",
        "abstract_only",
        "metadata_only",
        "unavailable",
    }
    assert {item.value for item in PrivacyLabel} == {
        "public",
        "project_private",
        "restricted",
    }
    assert {item.value for item in VerificationRoute} == {
        "doi",
        "title_author",
        "isbn",
        "official_source",
        "manual",
    }
