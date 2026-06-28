"""snomniman.ai - the AI Scientist (depends on describe, diagnostics, core).

A Qt-free backend package whose first capability is **measurement orientation**: a
Scientific Briefing that answers "tell me about this measurement." Its facts are
produced deterministically from :mod:`snomniman.describe` (structure) and
:mod:`snomniman.diagnostics` (computed facts); an optional natural-language
*interpretation* is rendered by a :class:`NarrativeProvider` when one is configured.

Foundational principles (see ``CLAUDE.md``):

- The AI may only reason over deterministic facts produced by SNOMNIMAN; it must
  never become the primary interpreter of raw scientific data when deterministic
  algorithms can establish those facts.
- Every AI-powered feature has a useful deterministic fallback. AI *enhances*
  understanding; it never *gates* access to understanding.

This v1 adds **no model dependency**: only the provider seam (protocol + prompt
builder + a network-free mock). A concrete provider (e.g. Anthropic) arrives later as
an optional extra, lazy-imported, never required for the backend or CI. The briefing
is read-only text, not a Dataset derivation: it never mutates data and adds nothing to
the provenance DAG. See ``docs/ai-scientist-v1.md`` (ADR-0020).
"""

from __future__ import annotations

from .briefing import build_briefing
from .provider import (
    ORIENTATION_SYSTEM,
    MockNarrativeProvider,
    NarrativeProvider,
    build_orientation_prompt,
)
from .recommend import (
    STRENGTH_MODERATE,
    STRENGTH_STRONG,
    STRENGTH_TENTATIVE,
    Recommendation,
    RecommendationEvidence,
    WorkflowSuggestions,
    recommend_workflow,
    strength_label,
)
from .report import (
    FACT,
    INTERPRETATION,
    Briefing,
    BriefingContext,
    BriefingSection,
    BriefingStatement,
)

__all__ = [
    "FACT",
    "INTERPRETATION",
    "ORIENTATION_SYSTEM",
    "STRENGTH_MODERATE",
    "STRENGTH_STRONG",
    "STRENGTH_TENTATIVE",
    "Briefing",
    "BriefingContext",
    "BriefingSection",
    "BriefingStatement",
    "MockNarrativeProvider",
    "NarrativeProvider",
    "Recommendation",
    "RecommendationEvidence",
    "WorkflowSuggestions",
    "build_briefing",
    "build_orientation_prompt",
    "recommend_workflow",
    "strength_label",
]
