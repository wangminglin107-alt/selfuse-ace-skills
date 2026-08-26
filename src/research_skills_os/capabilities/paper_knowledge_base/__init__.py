"""Paper knowledge base capability."""

from research_skills_os.capabilities.paper_knowledge_base.gates import (
    evaluate_paper_knowledge_base,
)
from research_skills_os.capabilities.paper_knowledge_base.models import (
    CorpusStatus,
    DocumentIndex,
    DocumentRecord,
    normalize_bibliographic_text,
)

__all__ = [
    "CorpusStatus",
    "DocumentIndex",
    "DocumentRecord",
    "evaluate_paper_knowledge_base",
    "normalize_bibliographic_text",
]
