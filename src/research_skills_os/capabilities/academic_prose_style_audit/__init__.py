"""Deterministic advisory checks for academic prose."""

from research_skills_os.capabilities.academic_prose_style_audit.gates import audit_prose
from research_skills_os.capabilities.academic_prose_style_audit.models import ProseStyleReport

__all__ = ["ProseStyleReport", "audit_prose"]
