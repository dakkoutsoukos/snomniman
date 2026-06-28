"""Tests for the Scientific Reasoning Rule Engine (deterministic; no provider).

Each shipped rule is tested individually (its ``evaluate`` over a ReasoningContext).
The engine's interaction semantics - the applicability / already-applied guards,
prerequisite sequencing, mutual exclusion, and priority ordering - are tested with
*synthetic* rules registered in an isolated registry, so the mechanism is verified
even though the current shipped rules declare no prerequisites or exclusions.
"""

from __future__ import annotations

from typing import Any

import pytest

from snomniman.ai import (
    ReasoningContext,
    ReasoningRule,
    RuleOutcome,
    recommend_workflow,
)
from snomniman.ai import reasoning as _reasoning
from snomniman.ai.reasoning import (
    DIAGNOSTICS,
    PlaneLevelRule,
    ReferenceNormalizeRule,
    iter_rules,
    list_rules,
    register_rule,
)
from snomniman.ai.report import RecommendationEvidence
from snomniman.core import Dataset
from snomniman.processing.image.crop import Crop
from snomniman.processing.image.plane_level import PlaneLevel

_CROP_PARAMS = {"x_min": 0.0, "x_max": 120.0, "y_min": 0.0, "y_max": 120.0}


# --------------------------------------------------------------------------- #
# Individual rules (the unit of scientific judgment)
# --------------------------------------------------------------------------- #


def test_plane_level_rule_fires_on_measured_tilt(synthetic_dataset: Dataset) -> None:
    outcome = PlaneLevelRule().evaluate(ReasoningContext.build(synthetic_dataset))
    assert outcome is not None
    assert outcome.params == {"channel": "Z", "order": 1}
    assert 0.0 <= outcome.confidence <= 1.0
    assert outcome.evidence and outcome.considerations


def test_plane_level_rule_declines_without_topography(optical_only_dataset: Dataset) -> None:
    assert PlaneLevelRule().evaluate(ReasoningContext.build(optical_only_dataset)) is None


def test_reference_normalize_rule_fires_on_raw_signals(synthetic_dataset: Dataset) -> None:
    outcome = ReferenceNormalizeRule().evaluate(ReasoningContext.build(synthetic_dataset))
    assert outcome is not None
    assert outcome.params == {}
    # The deterministic downside (noise amplification near a weak reference) is surfaced.
    assert any("noise" in c.lower() for c in outcome.considerations)


def test_reference_normalize_rule_declines_without_optical_signal(
    topography_dataset: Dataset,
) -> None:
    ctx = ReasoningContext.build(topography_dataset)
    assert ReferenceNormalizeRule().evaluate(ctx) is None


def test_reference_normalize_rule_notes_completed_leveling(synthetic_dataset: Dataset) -> None:
    leveled = PlaneLevel(channel="Z", order=1).apply({"primary": synthetic_dataset})
    outcome = ReferenceNormalizeRule().evaluate(ReasoningContext.build(leveled))
    assert outcome is not None
    # Interaction-aware, provenance-sourced evidence: it knows leveling is done.
    assert any("leveling has already been applied" in e.text.lower() for e in outcome.evidence)
    assert any(e.source == "provenance" for e in outcome.evidence)


# --------------------------------------------------------------------------- #
# Registry + context
# --------------------------------------------------------------------------- #


def test_shipped_rules_are_registered() -> None:
    rules = list_rules()
    assert "reasoning.level_dominant_tilt" in rules
    assert "reasoning.normalize_with_reference" in rules


def test_iter_rules_returns_instances_in_deterministic_order() -> None:
    rules = iter_rules()
    assert all(isinstance(r, ReasoningRule) for r in rules)
    ids = [r.rule_id for r in rules]
    assert ids == sorted(ids)


def test_context_applied_steps_reads_provenance(synthetic_dataset: Dataset) -> None:
    leveled = PlaneLevel(channel="Z", order=1).apply({"primary": synthetic_dataset})
    ctx = ReasoningContext.build(leveled)
    assert "image.plane_level" in ctx.applied_steps
    assert "io.read" in ctx.applied_steps


def test_context_applicability(synthetic_dataset: Dataset) -> None:
    app = ReasoningContext.build(synthetic_dataset).applicability("image.plane_level")
    assert app is not None and app.applicable


# --------------------------------------------------------------------------- #
# Engine interaction mechanism (synthetic rules in an isolated registry)
# --------------------------------------------------------------------------- #


def _outcome(confidence: float, params: dict[str, Any]) -> RuleOutcome:
    return RuleOutcome(
        confidence=confidence,
        rationale="synthetic",
        evidence=(RecommendationEvidence("synthetic trigger", DIAGNOSTICS),),
        considerations=(),
        params=params,
        expected_outcome="synthetic outcome",
    )


@pytest.fixture
def isolated_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the rule registry with an empty one for the duration of a test."""
    monkeypatch.setattr(_reasoning, "_RULES", {})


def test_engine_skips_already_applied_operations(
    isolated_rules: None, synthetic_dataset: Dataset
) -> None:
    @register_rule
    class _CropRule(ReasoningRule):
        rule_id = "test.crop"
        step_id = "image.crop"
        summary = "synthetic"

        def evaluate(self, ctx: ReasoningContext) -> RuleOutcome | None:
            return _outcome(0.9, dict(_CROP_PARAMS))

    # Applicable + not applied -> recommended.
    steps = {r.step_id for r in recommend_workflow(synthetic_dataset).recommendations}
    assert steps == {"image.crop"}
    # After applying crop, the engine's guard drops it even though the rule would fire.
    cropped = Crop(**_CROP_PARAMS).apply({"primary": synthetic_dataset})
    assert recommend_workflow(cropped).recommendations == ()


def test_mutual_exclusion_keeps_higher_confidence(
    isolated_rules: None, synthetic_dataset: Dataset
) -> None:
    @register_rule
    class _Strong(ReasoningRule):
        rule_id = "test.strong"
        step_id = "image.crop"
        summary = "synthetic"
        excluded_steps = ("image.phase_unwrap",)

        def evaluate(self, ctx: ReasoningContext) -> RuleOutcome | None:
            return _outcome(0.9, dict(_CROP_PARAMS))

    @register_rule
    class _Weak(ReasoningRule):
        rule_id = "test.weak"
        step_id = "image.phase_unwrap"
        summary = "synthetic"

        def evaluate(self, ctx: ReasoningContext) -> RuleOutcome | None:
            return _outcome(0.5, {"channel": "O2"})

    steps = {r.step_id for r in recommend_workflow(synthetic_dataset).recommendations}
    assert "image.crop" in steps
    assert "image.phase_unwrap" not in steps  # excluded by the stronger crop rule


def test_prerequisite_suppresses_until_applied(
    isolated_rules: None, synthetic_dataset: Dataset
) -> None:
    @register_rule
    class _NeedsLevel(ReasoningRule):
        rule_id = "test.needs_level"
        step_id = "image.phase_unwrap"
        summary = "synthetic"
        prerequisite_steps = ("image.plane_level",)

        def evaluate(self, ctx: ReasoningContext) -> RuleOutcome | None:
            return _outcome(0.7, {"channel": "O2"})

    # Prerequisite not yet applied -> suppressed (engine yields nothing).
    suggestions = recommend_workflow(synthetic_dataset)
    assert suggestions.recommendations == ()
    assert suggestions.note is not None
    # Apply the prerequisite -> the recommendation surfaces (natural sequencing).
    leveled = PlaneLevel(channel="Z", order=1).apply({"primary": synthetic_dataset})
    after = recommend_workflow(leveled)
    assert {r.step_id for r in after.recommendations} == {"image.phase_unwrap"}


def test_recommendations_ordered_by_confidence(
    isolated_rules: None, synthetic_dataset: Dataset
) -> None:
    @register_rule
    class _Low(ReasoningRule):
        rule_id = "test.low"
        step_id = "image.crop"
        summary = "synthetic"

        def evaluate(self, ctx: ReasoningContext) -> RuleOutcome | None:
            return _outcome(0.4, dict(_CROP_PARAMS))

    @register_rule
    class _High(ReasoningRule):
        rule_id = "test.high"
        step_id = "image.phase_unwrap"
        summary = "synthetic"

        def evaluate(self, ctx: ReasoningContext) -> RuleOutcome | None:
            return _outcome(0.8, {"channel": "O2"})

    recs = recommend_workflow(synthetic_dataset).recommendations
    assert [r.confidence for r in recs] == sorted((r.confidence for r in recs), reverse=True)
    assert recs[0].step_id == "image.phase_unwrap"


def test_register_rule_rejects_duplicate_id(isolated_rules: None) -> None:
    @register_rule
    class _One(ReasoningRule):
        rule_id = "test.dup"
        step_id = "image.crop"
        summary = "synthetic"

        def evaluate(self, ctx: ReasoningContext) -> RuleOutcome | None:
            return None

    with pytest.raises(ValueError, match="already registered"):

        @register_rule
        class _Two(ReasoningRule):
            rule_id = "test.dup"
            step_id = "image.plane_level"
            summary = "synthetic"

            def evaluate(self, ctx: ReasoningContext) -> RuleOutcome | None:
                return None
