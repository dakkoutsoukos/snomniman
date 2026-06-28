"""Tests for the AI Scientist's deterministic workflow recommendations.

Suggested Next Steps must be grounded in deterministic facts and obey hard safety
rules: only applicable operations, never already-applied ones, never contradicting
the diagnostics or provenance, no invented data. These tests pin those guarantees
(no provider, no network) plus ranking, evidence grounding, and immutability.
"""

from __future__ import annotations

import json

import numpy as np

from snomniman.ai import (
    STRENGTH_MODERATE,
    STRENGTH_STRONG,
    STRENGTH_TENTATIVE,
    Recommendation,
    WorkflowSuggestions,
    recommend_workflow,
    strength_label,
)
from snomniman.core import Dataset
from snomniman.diagnostics import diagnose
from snomniman.processing.image.plane_level import PlaneLevel
from snomniman.processing.image.reference_normalize import ReferenceNormalize


def _by_step(ws: WorkflowSuggestions) -> dict[str, Recommendation]:
    return {r.step_id: r for r in ws.recommendations}


# --------------------------------------------------------------------------- #
# Content: what gets recommended, with grounded fields
# --------------------------------------------------------------------------- #


def test_raw_measurement_recommends_level_and_normalize(synthetic_dataset: Dataset) -> None:
    ws = recommend_workflow(synthetic_dataset, title="synthetic")
    steps = _by_step(ws)
    assert "image.plane_level" in steps
    assert "image.reference_normalize" in steps
    assert ws.note is None


def test_plane_level_targets_signal_topography_with_params(synthetic_dataset: Dataset) -> None:
    rec = _by_step(recommend_workflow(synthetic_dataset))["image.plane_level"]
    assert rec.params == {"channel": "Z", "order": 1}
    assert rec.evidence  # grounded
    assert rec.expected_outcome
    assert 0.0 <= rec.confidence <= 1.0


def test_reference_normalize_has_no_params(synthetic_dataset: Dataset) -> None:
    rec = _by_step(recommend_workflow(synthetic_dataset))["image.reference_normalize"]
    assert rec.params == {}
    assert 0.0 <= rec.confidence <= 1.0


def test_recommendations_ranked_by_confidence(synthetic_dataset: Dataset) -> None:
    recs = recommend_workflow(synthetic_dataset).recommendations
    confidences = [r.confidence for r in recs]
    assert confidences == sorted(confidences, reverse=True)


def test_every_recommendation_is_grounded(synthetic_dataset: Dataset) -> None:
    for rec in recommend_workflow(synthetic_dataset).recommendations:
        assert rec.rationale
        assert rec.evidence
        assert rec.rule_id  # traceable to the reasoning rule that produced it
        for ev in rec.evidence:
            assert ev.source in {"diagnostics", "description", "provenance", "metadata"}
            assert ev.text


# --------------------------------------------------------------------------- #
# Hard safety rules
# --------------------------------------------------------------------------- #


def test_only_applicable_operations_are_recommended(synthetic_dataset: Dataset) -> None:
    ws = recommend_workflow(synthetic_dataset)
    applicable = {a.step_id for a in diagnose(synthetic_dataset).applicability if a.applicable}
    for rec in ws.recommendations:
        assert rec.step_id in applicable


def test_unavailable_operation_is_never_recommended(topography_dataset: Dataset) -> None:
    # No references/optical -> reference_normalize is not applicable, so never suggested.
    steps = _by_step(recommend_workflow(topography_dataset))
    assert "image.reference_normalize" not in steps
    # ...but plane leveling of the real topography still is.
    assert "image.plane_level" in steps


def test_already_applied_operation_drops_out(synthetic_dataset: Dataset) -> None:
    leveled = PlaneLevel(channel="Z", order=1).apply({"primary": synthetic_dataset})
    steps = _by_step(recommend_workflow(leveled))
    assert "image.plane_level" not in steps  # already in provenance
    assert "image.reference_normalize" in steps  # still pending


def test_empty_when_everything_applicable_is_applied(synthetic_dataset: Dataset) -> None:
    leveled = PlaneLevel(channel="Z", order=1).apply({"primary": synthetic_dataset})
    both = ReferenceNormalize().apply({"primary": leveled})
    ws = recommend_workflow(both)
    assert ws.recommendations == ()
    assert ws.note is not None  # explains why there is nothing to do


def test_recommendation_does_not_contradict_provenance(synthetic_dataset: Dataset) -> None:
    leveled = PlaneLevel(channel="Z", order=1).apply({"primary": synthetic_dataset})
    applied = {n.record.step_id for n in leveled.provenance.iter_nodes()}
    for rec in recommend_workflow(leveled).recommendations:
        assert rec.step_id not in applied


# --------------------------------------------------------------------------- #
# Strength tiers, serialization, immutability
# --------------------------------------------------------------------------- #


def test_strength_label_tiers() -> None:
    assert strength_label(0.9) == STRENGTH_STRONG
    assert strength_label(0.5) == STRENGTH_MODERATE
    assert strength_label(0.2) == STRENGTH_TENTATIVE


def test_suggestions_json_serializable(synthetic_dataset: Dataset) -> None:
    ws = recommend_workflow(synthetic_dataset, title="synthetic")
    # Round-trips through JSON (structured, inspectable output).
    text = json.dumps(ws.to_dict())
    back = json.loads(text)
    assert back["title"] == "synthetic"
    assert {r["step_id"] for r in back["recommendations"]} == {
        "image.plane_level",
        "image.reference_normalize",
    }
    # The grounding context travels with the suggestions for audit.
    assert "description" in back["context"] and "diagnostics" in back["context"]


def test_recommend_does_not_mutate_dataset(synthetic_dataset: Dataset) -> None:
    before = {
        n: synthetic_dataset.channel(n).values.copy() for n in synthetic_dataset.channel_names
    }
    recommend_workflow(synthetic_dataset)
    for name, values in before.items():
        np.testing.assert_array_equal(synthetic_dataset.channel(name).values, values)
        assert synthetic_dataset.channel(name).data.flags.writeable is False


def test_unknown_dataset_without_topography_or_refs_is_quiet(
    optical_only_dataset: Dataset,
) -> None:
    # No topography to level and no references to normalize against: nothing grounded
    # to suggest -> empty with a note (never invents a step).
    ws = recommend_workflow(optical_only_dataset)
    assert ws.recommendations == ()
    assert ws.note is not None
