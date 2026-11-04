"""Data types for the Scientific Briefing - the first AI Scientist capability.

A *briefing* is a measurement orientation: "tell me about this measurement." Its
**facts** are produced deterministically from :mod:`snomniman.describe` and
:mod:`snomniman.diagnostics`; an optional **interpretation** is a natural-language
narrative produced by a :class:`~snomniman.ai.provider.NarrativeProvider` *renderer*
when one is configured. The facts are always present and authoritative; the AI never
gates access to understanding and never invents facts (see ``CLAUDE.md``).

Every type here is frozen and JSON-serializable via ``to_dict`` (mirroring the
``describe``/``diagnostics`` descriptor pattern). The :class:`Briefing` carries the
exact :class:`BriefingContext` it was built from, so every statement - and any AI
narrative - can be audited against the deterministic facts that grounded it.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

#: The deterministic layers a statement may be grounded in.
FACT = "fact"
INTERPRETATION = "interpretation"


@dataclass(frozen=True)
class BriefingStatement:
    """One statement in the briefing, with its kind and grounding.

    ``kind`` is :data:`FACT` (established deterministically) or
    :data:`INTERPRETATION` (a labelled, non-authoritative reading). ``sources``
    names the deterministic layers backing a fact (e.g. ``("diagnostics",)``);
    interpretations cite the same facts they were derived from.
    """

    text: str
    kind: str  # FACT | INTERPRETATION
    sources: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


@dataclass(frozen=True)
class BriefingSection:
    """A titled group of statements (Summary, Observations, Enables, ...)."""

    title: str
    statements: tuple[BriefingStatement, ...]

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


@dataclass(frozen=True)
class BriefingContext:
    """The exact deterministic facts a briefing (and any AI narrative) may use.

    This *is* the grounding: it is the projection a provider receives, and the
    audit trail a user inspects. It contains nothing but the JSON projections of
    the Scientific Description API and the Scientific Diagnostics Engine - no raw
    arrays, no hidden context.
    """

    description: dict[str, Any]  # MeasurementDescription.to_dict()
    diagnostics: dict[str, Any]  # MeasurementDiagnostics.to_dict()

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


@dataclass(frozen=True)
class Briefing:
    """A measurement orientation: deterministic fact sections + optional narrative.

    ``sections`` are always populated (deterministic facts). ``interpretation`` is
    the optional AI narrative, present only when a provider rendered one;
    ``provider`` and ``generated_at`` record what produced it, for auditability.
    ``context`` is the grounding the whole briefing was built from.
    """

    title: str | None
    sections: tuple[BriefingSection, ...]
    interpretation: str | None
    provider: str | None
    generated_at: str | None
    context: BriefingContext

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


# --------------------------------------------------------------------------- #
# Suggested Next Steps - data types (produced by the Scientific Reasoning Rule
# Engine in ``reasoning.py``, orchestrated by ``recommend.py``)
# --------------------------------------------------------------------------- #

#: Display strength tiers for a recommendation's heuristic confidence.
STRENGTH_STRONG = "strong"
STRENGTH_MODERATE = "moderate"
STRENGTH_TENTATIVE = "tentative"


def strength_label(confidence: float) -> str:
    """Map a heuristic confidence in [0, 1] to a qualitative strength tier.

    The numeric ``confidence`` is a deterministic *priority* derived from the
    strength of the supporting evidence - not a statistical probability - so the
    UI shows this honest tier rather than implying false precision.
    """
    if confidence >= 0.66:
        return STRENGTH_STRONG
    if confidence >= 0.4:
        return STRENGTH_MODERATE
    return STRENGTH_TENTATIVE


@dataclass(frozen=True)
class RecommendationEvidence:
    """One deterministic fact backing a recommendation, with its source layer.

    ``source`` names where the trigger came from: ``diagnostics`` (a computed fact),
    ``description`` (a projected structural fact), ``provenance`` (the derivation
    history), or ``metadata`` (a recorded convention/parameter).
    """

    text: str
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


@dataclass(frozen=True)
class Recommendation:
    """A grounded, deterministic suggestion for a next processing step.

    It points at a registered operation (``step_id``) with pre-filled ``params``
    ready for the Processing Workspace; it never executes. ``rule_id`` names the
    Scientific Reasoning Rule that produced it (full traceability). ``confidence``
    is a deterministic heuristic priority in [0, 1] from the strength of the
    evidence (NOT a probability); ``evidence`` are the deterministic triggers;
    ``considerations`` are deterministic caveats the researcher should weigh;
    ``expected_outcome`` states what applying it would do.
    """

    rule_id: str
    step_id: str
    title: str
    params: dict[str, Any]
    confidence: float
    rationale: str
    evidence: tuple[RecommendationEvidence, ...]
    considerations: tuple[str, ...]
    expected_outcome: str

    @property
    def strength(self) -> str:
        return strength_label(self.confidence)

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


@dataclass(frozen=True)
class WorkflowSuggestions:
    """The ranked suggestions for a measurement (deterministic; always available).

    ``recommendations`` is ordered by ``confidence`` (descending). When empty,
    ``note`` explains why. ``context`` is the exact deterministic grounding the
    suggestions were built from - the audit trail, and what a future narrative
    provider would receive.
    """

    title: str | None
    recommendations: tuple[Recommendation, ...]
    note: str | None
    context: BriefingContext

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


# --------------------------------------------------------------------------- #
# Experiment-level Scientific Assistant - data types (Phase 9A/9B). Produced by
# ``ai.experiment``; parallel to the single-measurement types above, composing
# many measurements' facts rather than one.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ExperimentBriefingContext:
    """The exact per-measurement facts an :class:`ExperimentBriefing` was built from.

    ``per_measurement`` holds each measurement's own already-serialized
    :class:`BriefingContext` (``.to_dict()``), keyed by ``measurement_id`` - the
    same grounding a single-measurement :class:`Briefing` carries, just one per
    measurement, so any experiment-level statement can be traced back to the exact
    measurement and deterministic layer that produced it.
    """

    measurement_ids: tuple[str, ...]
    per_measurement: Mapping[str, dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


@dataclass(frozen=True)
class ExperimentBriefing:
    """A whole-project orientation: deterministic fact sections over every measurement.

    Structurally parallel to :class:`Briefing` (same ``sections``/``BriefingStatement``
    contract - every statement is source-tagged) but composed from every measurement
    in a :class:`~snomniman.pipeline.Project` instead of one dataset's facts.
    """

    title: str | None
    n_measurements: int
    sections: tuple[BriefingSection, ...]
    context: ExperimentBriefingContext

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


@dataclass(frozen=True)
class OutlierMetric:
    """One measurement's value for one metric, relative to its project's own distribution.

    A plain descriptive statistic (a z-score against the project's own mean/std for
    this metric) - never a claim about *why* a measurement differs or whether it is
    instrumentally bad (CLAUDE.md AI rule 1). ``flagged`` is ``True`` iff
    ``abs(z_score)`` is at least the report's ``threshold``.
    """

    metric: str
    unit: str | None
    measurement_id: str
    measurement_title: str
    value: float
    project_mean: float
    project_std: float
    z_score: float
    flagged: bool

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


@dataclass(frozen=True)
class OutlierReport:
    """Deterministic outlier flags across a project, for every metric that could be compared.

    ``metrics`` carries every (measurement, metric) pair that had enough data to be
    compared; ``flagged`` is the subset that crossed ``threshold``. ``note`` explains
    a metric skipped for having too few computable measurements to form a meaningful
    distribution, when that happened.
    """

    title: str | None
    threshold: float
    metrics: tuple[OutlierMetric, ...]
    flagged: tuple[OutlierMetric, ...]
    note: str | None

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


def _jsonify(obj: Any) -> Any:
    """Recursively convert tuples to lists so the result is JSON-round-trippable."""
    if isinstance(obj, dict):
        return {k: _jsonify(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonify(v) for v in obj]
    return obj


__all__ = [
    "FACT",
    "INTERPRETATION",
    "STRENGTH_MODERATE",
    "STRENGTH_STRONG",
    "STRENGTH_TENTATIVE",
    "Briefing",
    "BriefingContext",
    "BriefingSection",
    "BriefingStatement",
    "ExperimentBriefing",
    "ExperimentBriefingContext",
    "OutlierMetric",
    "OutlierReport",
    "Recommendation",
    "RecommendationEvidence",
    "WorkflowSuggestions",
    "strength_label",
]
