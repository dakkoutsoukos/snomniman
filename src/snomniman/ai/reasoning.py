"""The Scientific Reasoning Rule Engine - scientific best practice, as deterministic data.

Where :mod:`snomniman.diagnostics` *computes facts* and :mod:`snomniman.processing`
*performs operations*, the reasoning engine encodes **scientific judgment**: given the
deterministic facts about a measurement, which registered operation should a researcher
consider next, why, under what conditions, and with what caveats. Each unit of judgment
is a :class:`ReasoningRule` - first-class, declarative, individually testable, and
*registered* the way an operation is. A rule reasons only over a :class:`ReasoningContext`
(the Description API + Diagnostics Engine projections); it never executes anything, never
calls a model, and never touches raw arrays.

This module is the **scientific authority** for "what next" (CLAUDE.md AI rule 3:
deterministic systems choose; AI explains). A future LLM may *phrase* a recommendation,
never *choose* it. The orchestration (evaluate every rule, enforce applicability /
not-already-applied, honour prerequisites + exclusions, order by priority) lives in
:mod:`snomniman.ai.recommend`. See ``docs/scientific-reasoning.md`` (ADR-0023).

Scope note (Rule 7): the prerequisite/exclusion *mechanism* exists and is tested, but the
current operation vocabulary has no hard prerequisites or exclusions, so the shipped rules
declare none. Relationships are modelled when they are real, not speculatively.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar

import snomniman.processing.image  # noqa: F401  (register operations so applicability resolves)
from snomniman.core import Dataset
from snomniman.describe import (
    ChannelDescription,
    MeasurementDescription,
    describe_measurement,
)
from snomniman.diagnostics import (
    MeasurementDiagnostics,
    OperationApplicability,
    diagnose,
)

from .report import RecommendationEvidence as Evidence

#: Source tags for evidence (the deterministic layer a trigger came from).
DIAGNOSTICS = "diagnostics"
DESCRIPTION = "description"
PROVENANCE = "provenance"
METADATA = "metadata"


@dataclass(frozen=True)
class ReasoningContext:
    """The deterministic facts a rule may reason over (read-only).

    Nothing here is a raw array: only the JSON-shaped projections of the Description
    API and the Diagnostics Engine, plus a few convenience accessors. This *is* the
    grounding a rule is allowed to use.
    """

    description: MeasurementDescription
    diagnostics: MeasurementDiagnostics

    @classmethod
    def build(cls, dataset: Dataset, *, title: str | None = None) -> ReasoningContext:
        return cls(
            description=describe_measurement(dataset, title=title),
            diagnostics=diagnose(dataset, title=title),
        )

    def applicability(self, step_id: str) -> OperationApplicability | None:
        return next(
            (a for a in self.diagnostics.applicability if a.step_id == step_id), None
        )

    @property
    def applied_steps(self) -> frozenset[str]:
        """The step_ids already in the provenance DAG (the derivation history)."""
        return frozenset(s.step_id for s in self.description.provenance.steps)

    def channels(
        self, *, kind: str | None = None, role: str | None = None
    ) -> tuple[ChannelDescription, ...]:
        return tuple(
            c
            for c in self.description.channels
            if (kind is None or c.kind == kind) and (role is None or c.role == role)
        )

    def field_um(self) -> float | None:
        """A representative field length in micrometres (mean of the x/y extents)."""
        size = self.description.metadata.geometry.size_nm
        if size is None:
            return None
        sx, sy = size
        if sx <= 0.0 or sy <= 0.0:
            return None
        return (sx + sy) / 2.0 / 1000.0


@dataclass(frozen=True)
class RuleOutcome:
    """A rule's deterministic verdict that an operation is worth considering.

    Produced by :meth:`ReasoningRule.evaluate` when (and only when) the deterministic
    facts support the recommendation. The orchestrator turns it into a
    :class:`~snomniman.ai.report.Recommendation`, adding the rule/step identity.
    """

    confidence: float  # heuristic priority in [0, 1] from the evidence strength
    rationale: str
    evidence: tuple[Evidence, ...]
    considerations: tuple[str, ...]
    params: dict[str, Any]
    expected_outcome: str


class ReasoningRule(ABC):
    """One unit of deterministic scientific judgment about a registered operation.

    A rule declares which operation it recommends (``step_id``) and any
    ``prerequisite_steps`` / ``excluded_steps`` (operation relationships), and
    implements :meth:`evaluate` to either propose a grounded :class:`RuleOutcome` or
    decline (``None``). It does **not** re-check applicability or already-applied state
    - the orchestrator enforces those uniformly from the operation's declared
    capabilities and the provenance, so a rule contains only the *scientific* trigger.
    """

    #: Stable, dot-namespaced rule identifier (e.g. ``"reasoning.level_dominant_tilt"``).
    rule_id: ClassVar[str]
    #: The registered operation this rule recommends (e.g. ``"image.plane_level"``).
    step_id: ClassVar[str]
    #: One sentence: the best practice this rule encodes (for docs + explainability).
    summary: ClassVar[str]
    #: Operations that should be applied before this one is recommended (ordering).
    prerequisite_steps: ClassVar[tuple[str, ...]] = ()
    #: Operations this recommendation must not co-occur with (mutual exclusion).
    excluded_steps: ClassVar[tuple[str, ...]] = ()

    @abstractmethod
    def evaluate(self, ctx: ReasoningContext) -> RuleOutcome | None:
        """Return a grounded outcome iff the deterministic facts support this step."""


# --------------------------------------------------------------------------- #
# Rule registry (mirrors the processing step registry; not a plugin system)
# --------------------------------------------------------------------------- #

_RULES: dict[str, ReasoningRule] = {}


def register_rule(cls: type[ReasoningRule]) -> type[ReasoningRule]:
    """Register a :class:`ReasoningRule` subclass (decorator). Instantiates a singleton."""
    if not getattr(cls, "rule_id", ""):
        raise ValueError(f"Cannot register {cls.__name__!r}: rule_id is missing")
    if cls.rule_id in _RULES:
        raise ValueError(f"rule_id {cls.rule_id!r} is already registered")
    _RULES[cls.rule_id] = cls()
    return cls


def iter_rules() -> tuple[ReasoningRule, ...]:
    """All registered rules, ordered by rule_id (deterministic iteration)."""
    return tuple(_RULES[rid] for rid in sorted(_RULES))


def list_rules() -> list[str]:
    return sorted(_RULES)


# --------------------------------------------------------------------------- #
# The shipped rule set (one deterministic rule per grounded best practice)
# --------------------------------------------------------------------------- #


@register_rule
class PlaneLevelRule(ReasoningRule):
    """Level the topography when a measured global tilt dominates its height variation."""

    rule_id = "reasoning.level_dominant_tilt"
    step_id = "image.plane_level"
    summary = (
        "Recommend plane leveling when the topography carries a measurable global tilt "
        "that accounts for a meaningful share of its height variation."
    )

    def evaluate(self, ctx: ReasoningContext) -> RuleOutcome | None:
        topo = ctx.diagnostics.topography
        field_um = ctx.field_um()
        if topo is None or field_um is None:
            return None
        tilt_swing = abs(topo.slope_magnitude_per_um) * field_um  # height change across field
        if tilt_swing <= 0.0:
            return None
        unit = topo.unit or "nm"
        rough = topo.rms_roughness
        if rough is not None and rough > 0.0:
            tilt_rms = tilt_swing / math.sqrt(12.0)  # RMS of a peak-to-peak linear ramp
            confidence = tilt_rms / (tilt_rms + rough)
        else:
            confidence = 0.5
        if confidence < 0.15:
            return None

        evidence = [
            Evidence(
                f"Topography '{topo.channel}' has a global tilt of "
                f"{topo.slope_magnitude_per_um:.3g} {unit}/um "
                f"(~{tilt_swing:.3g} {unit} across the {field_um:.3g} um field).",
                DIAGNOSTICS,
            )
        ]
        if rough is not None and rough > 0.0:
            evidence.append(
                Evidence(
                    f"RMS roughness after detilting is {rough:.3g} {unit}; the tilt "
                    f"accounts for about {confidence * 100:.0f}% of the height variation.",
                    DIAGNOSTICS,
                )
            )
        evidence.append(
            Evidence("Plane leveling does not yet appear in the derivation history.", PROVENANCE)
        )
        return RuleOutcome(
            confidence=confidence,
            rationale=(
                "A global tilt dominates the topography; leveling removes it so the real "
                "height features and roughness stand out."
            ),
            evidence=tuple(evidence),
            considerations=(
                "Order 1 (a plane) is the safe default; higher polynomial orders can "
                "subtract genuine sample curvature, not just instrument tilt.",
            ),
            params={"channel": topo.channel, "order": 1},
            expected_outcome=(
                f"Subtracts a fitted plane from '{topo.channel}'; coordinates, conventions, "
                "and every other channel are unchanged."
            ),
        )


@register_rule
class ReferenceNormalizeRule(ReasoningRule):
    """Normalize optical channels when references exist and the signals are still raw."""

    rule_id = "reasoning.normalize_with_reference"
    step_id = "image.reference_normalize"
    summary = (
        "Recommend reference normalization when reference channels are present and the "
        "complex optical signals have not yet been normalized."
    )

    def evaluate(self, ctx: ReasoningContext) -> RuleOutcome | None:
        raw_signals = [
            c.canonical
            for c in ctx.channels(kind="optical", role="signal")
            if c.is_complex and c.state != "normalized"
        ]
        if not raw_signals:
            return None

        joined = ", ".join(raw_signals)
        evidence = [
            Evidence("Reference channels (R_O*) are present in this measurement.", DESCRIPTION),
            Evidence(
                f"{len(raw_signals)} optical signal channel(s) are still raw "
                f"(not yet normalized): {joined}.",
                DESCRIPTION,
            ),
        ]
        # Interaction-aware (deterministic, from provenance): note a completed prerequisite.
        if "image.plane_level" in ctx.applied_steps:
            evidence.append(
                Evidence(
                    "Plane leveling has already been applied; normalization is a natural "
                    "next step toward quantitative analysis.",
                    PROVENANCE,
                )
            )
        return RuleOutcome(
            confidence=0.85,
            rationale=(
                "Reference channels are available; normalizing divides each optical channel "
                "by its matching reference to remove the common system response, enabling "
                "quantitative comparison across harmonics."
            ),
            evidence=tuple(evidence),
            considerations=(
                "Normalization divides by the reference; where the reference amplitude is "
                "near zero, division amplifies noise.",
                "Phase becomes referenced to the reference channel (an explicit, recorded "
                "re-reference), not absolute phase.",
            ),
            params={},
            expected_outcome=(
                "Each complex optical channel is divided by its reference: amplitude becomes "
                "a dimensionless ratio and phase is referenced to the reference."
            ),
        )


__all__ = [
    "DESCRIPTION",
    "DIAGNOSTICS",
    "METADATA",
    "PROVENANCE",
    "PlaneLevelRule",
    "ReasoningContext",
    "ReasoningRule",
    "ReferenceNormalizeRule",
    "RuleOutcome",
    "iter_rules",
    "list_rules",
    "register_rule",
]
