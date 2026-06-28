"""The knowledge article - one structured, queryable unit of scientific teaching.

An :class:`Article` is *not* a documentation page: it is structured data the
application can query, cross-link, and surface in context ("Learn more" on an
operation, a diagnostic, a recommendation). Articles are concise, scientifically
accurate, and interconnected - each one helps a researcher understand a measurement
or an analysis step, not a software feature.

Articles carry **honest** content: every field is optional except the title,
summary, and explanation, so an article states only what it can say accurately
(the project maxim - never pad with unjustified content). Cross-references are by
identifier and are integrity-checked (no dangling links).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

#: The four article categories.
CONCEPT = "concept"  # scientific concepts (harmonics, phase, provenance, ...)
OPERATION = "operation"  # one per registered ProcessingStep
DIAGNOSTIC = "diagnostic"  # one per computed diagnostic quantity
AI = "ai"  # the AI Scientist's philosophy and capabilities

CATEGORIES = (CONCEPT, OPERATION, DIAGNOSTIC, AI)

#: id-prefix conventions, so the application can resolve an object to its article:
#: an operation ``image.plane_level`` -> ``operation.image.plane_level``; a diagnostic
#: key ``rms_roughness`` -> ``diagnostic.rms_roughness``.
OPERATION_PREFIX = "operation."
DIAGNOSTIC_PREFIX = "diagnostic."


class KnowledgeError(KeyError):
    """Raised for an unknown article id or a knowledge-base integrity violation."""


@dataclass(frozen=True)
class Article:
    """One structured knowledge article (frozen, JSON-serializable).

    ``article_id`` is stable and dot-namespaced by category (e.g.
    ``concept.phase``, ``operation.image.plane_level``, ``diagnostic.rms_roughness``,
    ``ai.suggested_next_steps``). Only ``title`` / ``summary`` / ``explanation`` are
    required; an article fills the optional fields only where it has something
    accurate to say. Cross-references: ``related_concepts`` are article ids,
    ``related_operations`` are step_ids, ``related_diagnostics`` are diagnostic keys.
    """

    article_id: str
    category: str
    title: str
    summary: str
    explanation: str
    scientific_background: str | None = None
    mathematical_background: str | None = None
    practical_guidance: str | None = None
    common_mistakes: tuple[str, ...] = ()
    related_concepts: tuple[str, ...] = ()
    related_operations: tuple[str, ...] = ()
    related_diagnostics: tuple[str, ...] = ()
    references: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}

    def search_text(self) -> str:
        """Lower-cased text used for simple substring search."""
        return " ".join([self.title, self.summary, self.explanation]).lower()


def _jsonify(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _jsonify(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonify(v) for v in obj]
    return obj


__all__ = [
    "AI",
    "CATEGORIES",
    "CONCEPT",
    "DIAGNOSTIC",
    "DIAGNOSTIC_PREFIX",
    "OPERATION",
    "OPERATION_PREFIX",
    "Article",
    "KnowledgeError",
]
