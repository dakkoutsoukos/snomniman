"""Tests for snomniman.ai - the Scientific Briefing (AI Scientist v1).

The briefing's facts are deterministic, so they are tested exactly. Grounding is
verified structurally: every fact statement cites only `description`/`diagnostics`,
and the provider seam is exercised with a network-free mock. No external API is
touched (none is bundled).
"""

from __future__ import annotations

import json

# Importing the image sub-package registers image.plane_level (for applicability).
import snomniman.processing.image  # noqa: F401
from snomniman.ai import (
    FACT,
    Briefing,
    BriefingContext,
    MockNarrativeProvider,
    build_briefing,
    build_orientation_prompt,
)
from snomniman.core import Dataset
from snomniman.processing.image.plane_level import PlaneLevel

_FACT_SECTIONS = {
    "Measurement Summary",
    "Scientific Observations",
    "What This Measurement Enables",
}
_ALLOWED_SOURCES = {"description", "diagnostics"}


def test_briefing_has_the_three_fact_sections(synthetic_dataset: Dataset) -> None:
    briefing = build_briefing(synthetic_dataset)
    assert isinstance(briefing, Briefing)
    assert {s.title for s in briefing.sections} == _FACT_SECTIONS
    assert all(s.statements for s in briefing.sections)  # none empty for an image


def test_every_statement_is_a_grounded_fact(synthetic_dataset: Dataset) -> None:
    briefing = build_briefing(synthetic_dataset)
    for section in briefing.sections:
        for st in section.statements:
            assert st.kind == FACT
            assert st.sources, f"statement not grounded: {st.text!r}"
            assert set(st.sources) <= _ALLOWED_SOURCES


def test_summary_reports_raw_and_harmonics(synthetic_dataset: Dataset) -> None:
    briefing = build_briefing(synthetic_dataset)
    summary = next(s for s in briefing.sections if s.title == "Measurement Summary")
    text = " ".join(st.text for st in summary.statements)
    assert "raw" in text.lower()
    assert "O2" in text and "O3" in text
    assert "Reference channels are present" in text  # R_O2 in the fixture


def test_enables_lists_applicable_plane_level(synthetic_dataset: Dataset) -> None:
    briefing = build_briefing(synthetic_dataset)
    enables = next(s for s in briefing.sections if s.title == "What This Measurement Enables")
    text = " ".join(st.text for st in enables.statements)
    assert "image.plane_level" in text and "applicable" in text


def test_ai_vocabulary_grows_with_new_operations(synthetic_dataset: Dataset) -> None:
    # Every registered operation enriches the AI briefing with NO AI-specific change.
    briefing = build_briefing(synthetic_dataset)
    enables = next(s for s in briefing.sections if s.title == "What This Measurement Enables")
    text = " ".join(st.text for st in enables.statements)
    for step_id in ("image.reference_normalize", "image.phase_unwrap", "image.crop"):
        assert step_id in text, f"AI briefing did not gain vocabulary for {step_id}"


def test_observations_note_plane_level_not_yet_applied(synthetic_dataset: Dataset) -> None:
    briefing = build_briefing(synthetic_dataset)
    obs = next(s for s in briefing.sections if s.title == "Scientific Observations")
    text = " ".join(st.text for st in obs.statements)
    assert "not yet been applied" in text
    # After leveling, the observation flips.
    leveled = PlaneLevel(channel="Z", order=1).apply({"primary": synthetic_dataset})
    obs2 = next(
        s for s in build_briefing(leveled).sections if s.title == "Scientific Observations"
    )
    assert "already been applied" in " ".join(st.text for st in obs2.statements)


# -- grounding context ------------------------------------------------------- #


def test_context_carries_description_and_diagnostics(synthetic_dataset: Dataset) -> None:
    briefing = build_briefing(synthetic_dataset, title="demo")
    ctx = briefing.context
    assert isinstance(ctx, BriefingContext)
    assert ctx.description["title"] == "demo"
    assert "channel_statistics" in ctx.diagnostics
    # The whole briefing round-trips through JSON (auditable, serializable).
    text = json.dumps(briefing.to_dict())
    assert json.loads(text)["context"]["description"]["is_raw"] is True


# -- provider seam ----------------------------------------------------------- #


def test_no_provider_means_no_interpretation(synthetic_dataset: Dataset) -> None:
    briefing = build_briefing(synthetic_dataset)
    assert briefing.interpretation is None
    assert briefing.provider is None and briefing.generated_at is None


def test_provider_adds_interpretation_grounded_in_context(synthetic_dataset: Dataset) -> None:
    briefing = build_briefing(synthetic_dataset, provider=MockNarrativeProvider())
    assert briefing.provider == "mock"
    assert briefing.generated_at is not None
    assert briefing.interpretation is not None
    # The mock derives its text from the context (channel count), proving grounding.
    assert f"{len(synthetic_dataset.channel_names)} channel(s)" in briefing.interpretation


def test_prompt_embeds_only_the_facts(synthetic_dataset: Dataset) -> None:
    briefing = build_briefing(synthetic_dataset)
    prompt = build_orientation_prompt(briefing.context)
    assert "only the facts" in prompt.lower()
    assert "do not invent" in prompt.lower()
    # The facts payload is embedded verbatim.
    assert json.dumps(briefing.context.to_dict(), indent=2, sort_keys=True) in prompt


def test_briefing_does_not_mutate_dataset(synthetic_dataset: Dataset) -> None:
    import numpy as np

    before = {
        n: synthetic_dataset.channel(n).values.copy() for n in synthetic_dataset.channel_names
    }
    build_briefing(synthetic_dataset, provider=MockNarrativeProvider())
    for name, values in before.items():
        np.testing.assert_array_equal(synthetic_dataset.channel(name).values, values)
