"""Privacy-first adapters for local and explicitly authorized evidence sources."""

from research_skills_os.providers.local_manual import LocalManualProvider
from research_skills_os.providers.protocol import (
    ProviderAdapter,
    ProviderDeclaration,
    ProviderRequest,
    ProviderResult,
    ProviderSource,
)
from research_skills_os.providers.registry import ProviderRegistry

__all__ = [
    "LocalManualProvider",
    "ProviderAdapter",
    "ProviderDeclaration",
    "ProviderRegistry",
    "ProviderRequest",
    "ProviderResult",
    "ProviderSource",
]
