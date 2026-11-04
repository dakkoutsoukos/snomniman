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
from snomniman.core import (
    ChannelInfo,
    DataKind,
    Dataset,
    Metadata,
    ProvenanceNode,
    SpectralInfo,
    StepRecord,
)
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
    for step_id in (
        "image.line_flatten",
        "image.reference_normalize",
        "image.phase_unwrap",
        "image.crop",
        "image.threshold_segment",  # Phase 7 - no AI-specific change was needed either
    ):
        assert step_id in text, f"AI briefing did not gain vocabulary for {step_id}"


def test_observations_narrate_detected_features(synthetic_dataset: Dataset) -> None:
    # Phase 7 (docs/phase7-9-master-roadmap.md Section 5.3.4): once a measurement has
    # been segmented, the Briefing narrates the detected features - the same
    # "AI's vocabulary is exactly the deterministic engine's vocabulary" claim,
    # extended from operations/harmonics to Phase 7 facts.
    from snomniman.processing.image.threshold_segment import ThresholdSegment

    segmented = ThresholdSegment(channel="Z", method="otsu", min_pixels=1).apply(
        {"primary": synthetic_dataset}
    )
    obs = next(
        s for s in build_briefing(segmented).sections if s.title == "Scientific Observations"
    )
    text = " ".join(st.text for st in obs.statements)
    assert "feature(s) detected in 'Z_labels'" in text
    assert "from 'Z'" in text


def test_observations_omit_feature_statement_when_zero_features(synthetic_dataset: Dataset) -> None:
    # An empty segmentation (nothing crossed the threshold) is honestly silent, not a
    # spurious "0 features detected" statement.
    from snomniman.processing.image.threshold_segment import ThresholdSegment

    segmented = ThresholdSegment(
        channel="Z", method="fixed", threshold=1e9, polarity="above", min_pixels=1
    ).apply({"primary": synthetic_dataset})
    obs = next(
        s for s in build_briefing(segmented).sections if s.title == "Scientific Observations"
    )
    text = " ".join(st.text for st in obs.statements)
    assert "feature(s) detected" not in text


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


def test_observations_surface_harmonic_signal_noise() -> None:
    # A briefing surfaces the deterministic signal-vs-noise classification of harmonics.
    import numpy as np
    import xarray as xr

    from snomniman.core import ChannelInfo, DataKind, Metadata, ProvenanceNode, StepRecord

    ny, nx = 64, 64
    yy, xx = np.mgrid[0:ny, 0:nx].astype(float)
    smooth = np.exp(-(((xx - 30) ** 2 + (yy - 32) ** 2) / (2 * 15.0**2))) + 5.0  # coherent
    rng = np.random.default_rng(1)
    noise = np.abs(rng.standard_normal((ny, nx)) + 1j * rng.standard_normal((ny, nx)))  # noise
    x = (np.arange(nx) + 0.5) * 50.0
    y = (np.arange(ny) + 0.5) * 50.0
    data = xr.Dataset(
        {
            "O2": (("y", "x"), smooth.astype(np.complex128)),
            "O4": (("y", "x"), noise.astype(np.complex128)),
        },
        coords={
            "x": ("x", x, {"unit": "nm", "axis": "X"}),
            "y": ("y", y, {"unit": "nm", "axis": "Y"}),
        },
    )
    meta = Metadata(
        data_kind=DataKind.IMAGE,
        channels=(
            ChannelInfo("O2", "optical", "signal", "complex128", harmonic=2),
            ChannelInfo("O4", "optical", "signal", "complex128", harmonic=4),
        ),
    )
    node = ProvenanceNode(
        node_id="n0", record=StepRecord(step_id="io.read", step_version=1, deterministic=True)
    )
    ds = Dataset(data, kind=DataKind.IMAGE, metadata=meta, provenance=node)

    obs = next(s for s in build_briefing(ds).sections if s.title == "Scientific Observations")
    text = " ".join(st.text for st in obs.statements)
    assert "coherent signal: O2" in text
    assert "O4 (noise)" in text


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


# --------------------------------------------------------------------------- #
# Point spectroscopy (a LINE_SCAN with a wavenumber axis, no 2-D spatial grid)
# --------------------------------------------------------------------------- #


def _line_scan_spectrum_dataset() -> Dataset:
    import numpy as np
    import xarray as xr

    n_pos, n_wn = 12, 40
    s = (np.arange(n_pos, dtype=np.float64) + 0.5) * 20.0
    wn = 5920.0 + np.arange(n_wn, dtype=np.float64)
    o2 = np.ones((n_pos, n_wn), dtype=np.complex128) * (2.0 + 1j)
    z = np.full((n_pos, n_wn), 800.0, dtype=np.float64)
    data = xr.Dataset(
        {"O2": (("s", "wavenumber"), o2), "Z": (("s", "wavenumber"), z)},
        coords={
            "s": ("s", s, {"unit": "nm", "axis": "s"}),
            "wavenumber": ("wavenumber", wn, {"unit": "cm-1", "axis": "wavenumber"}),
        },
    )
    channels = (
        ChannelInfo("O2", "optical", "signal", "complex128", harmonic=2),
        ChannelInfo("Z", "topography", "signal", "float64", value_unit="nm"),
    )
    meta = Metadata(
        data_kind=DataKind.LINE_SCAN,
        channels=channels,
        spectral=SpectralInfo(
            wavenumber_min_cm1=5920.0, wavenumber_max_cm1=5959.0, n_points=40, sampling_cm1=1.0
        ),
    )
    node = ProvenanceNode(
        node_id="n0", record=StepRecord(step_id="io.read", step_version=1, deterministic=True)
    )
    return Dataset(data, kind=DataKind.LINE_SCAN, metadata=meta, provenance=node)


def test_summary_reports_spectral_range_not_single_excitation() -> None:
    briefing = build_briefing(_line_scan_spectrum_dataset())
    summary = " ".join(s.text for s in briefing.sections[0].statements)
    assert "Spectral range 5920-5959 cm^-1, 40 points (1 cm^-1 sampling)." in summary
    assert "Excitation at" not in summary  # superseded by the fuller spectral-range fact


def test_enables_reports_height_recorded_not_full_topography_toolset() -> None:
    briefing = build_briefing(_line_scan_spectrum_dataset())
    enables = " ".join(s.text for s in briefing.sections[2].statements)
    assert "Height (topography) values are recorded alongside the optical channels." in enables
    assert "roughness, profiles" not in enables  # those need a 2-D spatial grid


def test_briefing_does_not_crash_without_spatial_2d(synthetic_dataset: Dataset) -> None:
    # A regression guard for the vertical-slice generalization: every section must
    # build without raising for a dataset that has no (y, x) grid at all.
    briefing = build_briefing(_line_scan_spectrum_dataset())
    assert len(briefing.sections) == 3
    for section in briefing.sections:
        assert section.statements  # never an empty, silently-broken section
