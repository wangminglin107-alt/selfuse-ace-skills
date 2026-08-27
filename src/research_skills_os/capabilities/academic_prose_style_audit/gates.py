"""High-precision, explainable prose diagnostics without detector claims."""

from __future__ import annotations

import re
from collections import Counter
from statistics import pstdev

from research_skills_os.capabilities.academic_prose_style_audit.models import (
    ProseStyleFinding,
    ProseStyleMetrics,
    ProseStyleReport,
)

FILLERS = (
    "值得注意的是",
    "综上所述",
    "上述分析表明",
    "具有重要意义",
    "为后续研究提供参考",
    "毫无疑问",
    "众所周知",
)
CONNECTORS = ("此外", "同时", "首先", "其次", "再次", "最后", "另一方面", "进一步而言")


def _sentences(text: str) -> list[str]:
    pattern = r"[\u3002\uff01\uff1f!?\uff1b;]+"
    return [part.strip() for part in re.split(pattern, text) if part.strip()]


def _paragraphs(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]


def _repeated_ngrams(text: str, size: int = 6) -> list[str]:
    punctuation = (
        r"[\s\u3001\u3002\u300a\u300b\uff01\uff08\uff09"
        r"\uff0c\uff1a\uff1b\uff1f,.!?;:'\"()]"
    )
    compact = re.sub(punctuation, "", text)
    if len(compact) < size:
        return []
    counts = Counter(compact[index : index + size] for index in range(len(compact) - size + 1))
    return sorted(gram for gram, count in counts.items() if count >= 3)


def audit_prose(text: str, protected_anchors: tuple[str, ...] = ()) -> ProseStyleReport:
    """Return deterministic diagnostics; only missing protected anchors block."""

    paragraphs = _paragraphs(text)
    sentences = _sentences(text)
    characters = len(re.sub(r"\s", "", text))
    findings: list[ProseStyleFinding] = []

    filler_hits = [(phrase, text.count(phrase)) for phrase in FILLERS if phrase in text]
    filler_count = sum(count for _, count in filler_hits)
    for phrase, count in filler_hits:
        findings.append(
            ProseStyleFinding(
                code="formulaic_filler",
                severity="warning",
                unit="document",
                excerpt=phrase,
                message=(
                    f"Formulaic phrase occurs {count} time(s); keep only if it adds "
                    "evidence or logic."
                ),
            )
        )

    openings = Counter(paragraph[:4] for paragraph in paragraphs if len(paragraph) >= 4)
    repeated_openings = sorted(opening for opening, count in openings.items() if count >= 3)
    for opening in repeated_openings:
        findings.append(
            ProseStyleFinding(
                code="repeated_paragraph_opening",
                severity="warning",
                unit="paragraphs",
                excerpt=opening,
                message="Three or more paragraphs share this opening; inspect for template rhythm.",
            )
        )

    connector_count = sum(text.count(connector) for connector in CONNECTORS)
    connector_density = round(connector_count * 1000 / max(characters, 1), 2)
    if connector_count >= 3 and connector_density > 20:
        findings.append(
            ProseStyleFinding(
                code="connector_density",
                severity="advisory",
                unit="document",
                excerpt=str(connector_count),
                message=(
                    "Connector density is high; verify that relations are carried by claims, "
                    "not scaffolding."
                ),
            )
        )

    sentence_lengths = [len(re.sub(r"\s", "", sentence)) for sentence in sentences]
    length_stddev = round(pstdev(sentence_lengths), 2) if len(sentence_lengths) > 1 else 0.0
    if len(sentence_lengths) >= 5 and length_stddev < 4:
        findings.append(
            ProseStyleFinding(
                code="uniform_sentence_rhythm",
                severity="advisory",
                unit="document",
                excerpt=str(length_stddev),
                message=(
                    "Sentence lengths are unusually uniform; inspect for repeated syntactic "
                    "templates."
                ),
            )
        )

    repeated_ngrams = _repeated_ngrams(text)
    if repeated_ngrams:
        findings.append(
            ProseStyleFinding(
                code="repeated_ngram",
                severity="advisory",
                unit="document",
                excerpt=repeated_ngrams[0],
                message=(
                    "A six-character sequence repeats at least three times; inspect before "
                    "revising."
                ),
            )
        )

    missing = tuple(anchor for anchor in protected_anchors if anchor not in text)
    for anchor in missing:
        findings.append(
            ProseStyleFinding(
                code="protected_anchor_missing",
                severity="blocking",
                unit="document",
                excerpt=anchor,
                message="A protected meaning anchor is missing; reject the style revision.",
            )
        )

    return ProseStyleReport(
        findings=tuple(findings),
        metrics=ProseStyleMetrics(
            character_count=characters,
            paragraph_count=len(paragraphs),
            sentence_count=len(sentences),
            formulaic_filler_count=filler_count,
            connector_count=connector_count,
            connectors_per_1000_characters=connector_density,
            sentence_length_stddev=length_stddev,
            repeated_opening_count=len(repeated_openings),
            repeated_ngram_count=len(repeated_ngrams),
        ),
        protected_anchors=protected_anchors,
        missing_anchors=missing,
        ok=not missing,
    )
