"""Evidence synthesis capability."""

from research_skills_os.capabilities.evidence_synthesis.gates import (
    evaluate_evidence_synthesis,
)
from research_skills_os.capabilities.evidence_synthesis.models import (
    ContradictionLedger,
    CoverageReport,
    EvidenceRow,
    SynthesisMatrix,
)

__all__ = [
    "ContradictionLedger",
    "CoverageReport",
    "EvidenceRow",
    "SynthesisMatrix",
    "evaluate_evidence_synthesis",
]
