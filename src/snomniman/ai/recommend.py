"""Suggested Next Steps - deterministic, grounded workflow recommendations.

The AI Scientist's second capability. After *orienting* the researcher (the
Scientific Briefing), it proposes a ranked list of **next processing steps**. Each
recommendation is produced **deterministically** from the Scientific Description API
(:mod:`snomniman.describe`) and the Scientific Diagnostics Engine
(:mod:`snomniman.diagnostics`): operation applicability, topography tilt, channel
states, and provenance. It never infers from raw arrays, and it is never an LLM that
might hallucinate an unsafe step - which is exactly why it is safe.

This honours the two permanent AI rules (``CLAUDE.md``): reason only over
deterministic facts SNOMNIMAN produced, and always have a useful deterministic
fallback. Here the suggestions *are* deterministic, so they are always available,
grounded, and auditable; an optional :class:`~snomniman.ai.provider.NarrativeProvider`
may later add prose framing, but the structured recommendations never depend on it.

The engine **never executes anything**. A :class:`Recommendation` points at a
registered :class:`~snomniman.processing.ProcessingStep` with pre-filled parameters;
the researcher previews it in the Processing Workspace and decides. By construction
the engine only proposes operations that are *applicable* and *not already applied*,
so it cannot contradict the diagnostics or the provenance.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

import snomniman.processing.image  # noqa: F401  (register the built-in operations to recommend)
from snomniman.core import Dataset
from snomniman.describe import MeasurementDescription, describe_measurement
from snomniman.diagnostics import (
    MeasurementDiagnostics,
    OperationApplicability,
    diagnose,
)

from .report import BriefingContext

#: Source tags (shared vocabulary with the briefing).
_DIAG = "diagnostics"
_DESC = "description"

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
    """One deterministic fact backing a recommendation, with its source layer."""

    text: str
    source: str  # "diagnostics" | "description"

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


@dataclass(frozen=True)
class Recommendation:
    """A grounded, deterministic suggestion for a next processing step.

    It points at a registered operation (``step_id``) with pre-filled ``params``
    ready for the Processing Workspace; it never executes. ``confidence`` is a
    deterministic heuristic priority in [0, 1] derived from the strength of the
    evidence (NOT a probability); ``evidence`` are the deterministic facts that
    justify it; ``expected_outcome`` states what applying it would do.
    """

    step_id: str
    title: str
    params: dict[str, Any]
    confidence: float
    rationale: str
    evidence: tuple[RecommendationEvidence, ...]
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
    ``note`` explains why (e.g. everything applicable is already applied).
    ``context`` is the exact deterministic grounding the suggestions were built
    from - the audit trail, and what a future narrative provider would receive.
    """

    title: str | None
    recommendations: tuple[Recommendation, ...]
    note: str | None
    context: BriefingContext

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


def recommend_workflow(
    dataset: Dataset, *, title: str | None = None
) -> WorkflowSuggestions:
    """Build ranked, grounded next-step suggestions for *dataset* (read-only).

    Composes `describe` + `diagnostics` and applies one deterministic rule per
    operation. Each rule only emits when the operation is applicable, not already
    applied, and supported by a concrete deterministic observation. Nothing is
    executed and the dataset is never modified.
    """
    desc = describe_measurement(dataset, title=title)
    diag = diagnose(dataset, title=title)

    recommendations: list[Recommendation] = []
    recommendations.extend(_recommend_plane_level(desc, diag))
    recommendations.extend(_recommend_reference_normalize(desc, diag))
    recommendations.sort(key=lambda r: r.confidence, reverse=True)

    note = None if recommendations else _empty_note(diag)
    context = BriefingContext(description=desc.to_dict(), diagnostics=diag.to_dict())
    return WorkflowSuggestions(
        title=title,
        recommendations=tuple(recommendations),
        note=note,
        context=context,
    )


# --------------------------------------------------------------------------- #
# One deterministic rule per operation. Each is grounded and self-guarding.
# --------------------------------------------------------------------------- #


def _recommend_plane_level(
    desc: MeasurementDescription, diag: MeasurementDiagnostics
) -> list[Recommendation]:
    """Suggest plane leveling when a measured global tilt dominates the topography."""
    step_id = "image.plane_level"
    app = _applicability(diag, step_id)
    if app is None or not app.applicable or app.already_applied:
        return []
    topo = diag.topography
    field_um = _field_um(desc)
    if topo is None or field_um is None:
        return []
    tilt_swing = abs(topo.slope_magnitude_per_um) * field_um  # height change across the field
    if tilt_swing <= 0.0:
        return []

    unit = topo.unit or "nm"
    rough = topo.rms_roughness
    if rough is not None and rough > 0.0:
        # Fraction of the topography's RMS variation attributable to the global tilt
        # (a linear ramp of peak-to-peak P has RMS P/sqrt(12)).
        tilt_rms = tilt_swing / math.sqrt(12.0)
        confidence = tilt_rms / (tilt_rms + rough)
    else:
        confidence = 0.5
    if confidence < 0.15:
        return []

    evidence = [
        RecommendationEvidence(
            f"Topography '{topo.channel}' has a global tilt of "
            f"{topo.slope_magnitude_per_um:.3g} {unit}/um "
            f"(~{tilt_swing:.3g} {unit} across the {field_um:.3g} um field).",
            _DIAG,
        )
    ]
    if rough is not None and rough > 0.0:
        evidence.append(
            RecommendationEvidence(
                f"RMS roughness after detilting is {rough:.3g} {unit}; the tilt accounts "
                f"for about {confidence * 100:.0f}% of the height variation.",
                _DIAG,
            )
        )
    return [
        Recommendation(
            step_id=step_id,
            title=_op_title(step_id),
            params={"channel": topo.channel, "order": 1},
            confidence=round(confidence, 2),
            rationale=(
                "A global tilt dominates the topography; leveling removes it so the real "
                "height features and roughness stand out."
            ),
            evidence=tuple(evidence),
            expected_outcome=(
                f"Subtracts a fitted plane from '{topo.channel}'; coordinates, conventions, "
                "and every other channel are unchanged."
            ),
        )
    ]


def _recommend_reference_normalize(
    desc: MeasurementDescription, diag: MeasurementDiagnostics
) -> list[Recommendation]:
    """Suggest reference normalization when references exist and signals are still raw."""
    step_id = "image.reference_normalize"
    app = _applicability(diag, step_id)
    if app is None or not app.applicable or app.already_applied:
        return []
    raw_signals = [
        c.canonical
        for c in desc.channels
        if c.kind == "optical" and c.role == "signal" and c.is_complex and c.state != "normalized"
    ]
    if not raw_signals:
        return []

    joined = ", ".join(raw_signals)
    evidence = (
        RecommendationEvidence(
            "Reference channels (R_O*) are present in this measurement.", _DESC
        ),
        RecommendationEvidence(
            f"{len(raw_signals)} optical signal channel(s) are still raw "
            f"(not yet normalized): {joined}.",
            _DESC,
        ),
    )
    return [
        Recommendation(
            step_id=step_id,
            title=_op_title(step_id),
            params={},
            # A standard, well-supported early step when references are present.
            confidence=0.85,
            rationale=(
                "Reference channels are available; normalizing divides each optical channel "
                "by its matching reference to remove the common system response."
            ),
            evidence=evidence,
            expected_outcome=(
                "Each complex optical channel is divided by its reference: amplitude becomes a "
                "dimensionless ratio and phase is referenced to the reference (an explicit, "
                "recorded re-reference)."
            ),
        )
    ]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _applicability(
    diag: MeasurementDiagnostics, step_id: str
) -> OperationApplicability | None:
    return next((a for a in diag.applicability if a.step_id == step_id), None)


def _field_um(desc: MeasurementDescription) -> float | None:
    """A representative field length in micrometres (mean of the x/y extents)."""
    size = desc.metadata.geometry.size_nm
    if size is None:
        return None
    sx, sy = size
    if sx <= 0.0 or sy <= 0.0:
        return None
    return (sx + sy) / 2.0 / 1000.0


def _op_title(step_id: str) -> str:
    """Human title from a step_id: ``image.plane_level`` -> ``Plane Level``."""
    return step_id.split(".")[-1].replace("_", " ").title()


def _empty_note(diag: MeasurementDiagnostics) -> str:
    if any(a.already_applied for a in diag.applicability):
        return (
            "No further steps are suggested right now: the operations this measurement "
            "supports have already been applied, or there is no deterministic evidence "
            "that another step is needed."
        )
    return (
        "No next steps are suggested: there is no deterministic evidence that a processing "
        "step is currently needed."
    )


def _jsonify(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _jsonify(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonify(v) for v in obj]
    return obj


__all__ = [
    "STRENGTH_MODERATE",
    "STRENGTH_STRONG",
    "STRENGTH_TENTATIVE",
    "Recommendation",
    "RecommendationEvidence",
    "WorkflowSuggestions",
    "recommend_workflow",
    "strength_label",
]
