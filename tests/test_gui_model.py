"""Tests for the Qt-free Explorer presenter (snomniman.gui.model).

These exercise the full read-only experience logic without a display: channel
grouping, identity, metadata sections, provenance, cursor readout, channel
switching, and - critically - that exploring never modifies the Dataset.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from snomniman.core import Dataset
from snomniman.gui.model import (
    PRESET_AMP_PHASE,
    PRESET_HARMONIC_SERIES,
    PRESET_OPTICAL_TOPO,
    PRESET_SAMPLE_REF,
    ExplorerModel,
    PaneSpec,
)
from snomniman.viz import AMPLITUDE, PHASE, REAL, prepare_band, prepare_channel

_REPO_ROOT = Path(__file__).resolve().parents[1]
_GOLDEN_DIR = (
    _REPO_ROOT / "SNOM Sample Files" / "2026-06-16 14928" / "2026-06-16 190234 PH CdO Dense ROI 2"
)


@pytest.fixture
def golden_model() -> ExplorerModel:
    if not _GOLDEN_DIR.is_dir():
        pytest.skip("real neaSNOM sample data not present")
    return ExplorerModel.open_measurement(_GOLDEN_DIR)


# -- defaults + channel switching ------------------------------------------- #


def test_default_channel_is_o2_amplitude(synthetic_dataset: Dataset) -> None:
    model = ExplorerModel(synthetic_dataset)
    assert model.current_channel == "O2"
    assert model.current_representation == AMPLITUDE


def test_set_channel_and_representation(synthetic_dataset: Dataset) -> None:
    model = ExplorerModel(synthetic_dataset)
    model.set_representation(PHASE)
    assert model.current_representation == PHASE
    # Switching channel resets to the new channel's natural representation.
    model.set_channel("Z")
    assert model.current_channel == "Z"
    assert model.current_representation == "real"
    with pytest.raises(KeyError):
        model.set_channel("nope")
    with pytest.raises(ValueError, match="not available"):
        model.set_channel("Z")  # real channel
        model.set_representation(PHASE)


def test_render_follows_current_state(synthetic_dataset: Dataset) -> None:
    model = ExplorerModel(synthetic_dataset)
    model.set_representation(PHASE)
    rd = model.render()
    assert rd.channel == "O2" and rd.representation == PHASE and rd.cyclic is True


# -- channel grouping mirrors physics --------------------------------------- #


def test_channel_groups(synthetic_dataset: Dataset) -> None:
    groups = {g.title: g for g in ExplorerModel(synthetic_dataset).channel_groups()}
    assert set(groups) == {
        "Optical (near-field)", "Mechanical (cantilever)", "Topography", "References"
    }
    optical = [e.canonical for e in groups["Optical (near-field)"].entries]
    assert optical == ["O2", "O3"]  # sorted by harmonic
    assert groups["References"].entries[0].canonical == "R_O2"
    assert groups["Topography"].entries[0].descriptor == "height"


def test_golden_channel_groups_complete(golden_model: ExplorerModel) -> None:
    groups = {g.title: g for g in golden_model.channel_groups()}
    optical = [e.canonical for e in groups["Optical (near-field)"].entries]
    assert optical == [f"O{n}" for n in range(6)]  # O0..O5 in order
    total = sum(len(g.entries) for g in groups.values())
    assert total == 32  # every channel is browsable, none orphaned


# -- identity + metadata reflect the Dataset -------------------------------- #


def test_identity_reflects_metadata(golden_model: ExplorerModel) -> None:
    ident = golden_model.identity()
    assert ident.is_raw is True
    assert ident.kind == "image"
    assert ident.pixels == (150, 150)
    assert ident.wavenumber_cm1 == pytest.approx(5973.0)
    assert ident.detection == "PsHet"
    assert ident.vendor == "neaspec"


def test_metadata_sections_reflect_dataset(golden_model: ExplorerModel) -> None:
    sections = {s.title: s for s in golden_model.metadata_sections()}
    assert "Conventions" in sections and "Excitation" in sections
    conv = {i.label: i for i in sections["Conventions"].items}
    assert conv["Spatial unit"].value == "nm"
    assert "lower-left" in conv["Origin"].value
    exc = {i.label: i for i in sections["Excitation"].items}
    assert exc["Wavenumber"].value == "5973" and exc["Wavenumber"].unit == "cm^-1"
    # Every value carries a source (the provenance of the metadata).
    for s in sections.values():
        for item in s.items:
            assert item.source


def test_unknown_metadata_shown_as_unknown(synthetic_dataset: Dataset) -> None:
    # synthetic_dataset has no acquisition date -> shown as "unknown", never guessed.
    sections = {s.title: s for s in ExplorerModel(synthetic_dataset).metadata_sections()}
    date = {i.label: i for i in sections["Acquisition"].items}["Date"]
    assert date.value == "unknown"


# -- provenance ------------------------------------------------------------- #


def test_provenance_visible(golden_model: ExplorerModel) -> None:
    assert "raw measurement" in golden_model.provenance_summary()
    steps = golden_model.provenance_steps()
    assert len(steps) == 1
    step = steps[0]
    assert step.step_id == "io.read"
    assert "Imported" in step.description
    assert step.sources and "reader neasnom.image.gsf.v1" in step.sources[0]
    assert "numpy" in step.software


# -- cursor readout --------------------------------------------------------- #


def test_cursor_readout_in_and_out_of_bounds(golden_model: ExplorerModel) -> None:
    rd = golden_model.render()
    x0, x1, y0, y1 = rd.extent_nm
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    readout = golden_model.cursor_readout(cx, cy)
    assert readout.in_bounds is True
    labels = [v.label for v in readout.values]
    assert "O2 amplitude" in labels and "O2 phase" in labels
    assert "Z height" in labels  # topography context at the same pixel
    # Outside the field -> no values, flagged out of bounds.
    assert golden_model.cursor_readout(x1 + 1000.0, cy).in_bounds is False


# -- the cardinal invariant: exploration never mutates ---------------------- #


def test_exploring_does_not_modify_dataset(golden_model: ExplorerModel) -> None:
    ds = golden_model.dataset
    before = {name: ds.channel(name).values.copy() for name in ds.channel_names}
    # Drive a full exploration session.
    for group in golden_model.channel_groups():
        for entry in group.entries:
            golden_model.set_channel(entry.canonical)
            for rep in golden_model.representations():
                golden_model.set_representation(rep)
                golden_model.render()
                golden_model.cursor_readout(0.0, 0.0)
    for name, arr in before.items():
        np.testing.assert_array_equal(ds.channel(name).values, arr, err_msg=name)
        # The raw arrays are still frozen (immutable) after all that exploring.
        assert ds.channel(name).data.flags.writeable is False


def test_open_measurement_classmethod(golden_model: ExplorerModel) -> None:
    assert golden_model.title.startswith("2026-06-16")
    assert golden_model.dataset.is_raw is True


# -- comparison layouts ------------------------------------------------------ #


def test_preset_amplitude_phase(synthetic_dataset: Dataset) -> None:
    model = ExplorerModel(synthetic_dataset)  # default channel O2 (complex)
    assert model.comparison_layout(PRESET_AMP_PHASE) == [
        PaneSpec("O2", AMPLITUDE),
        PaneSpec("O2", PHASE),
    ]
    # A real channel has only one representation -> a single pane.
    model.set_channel("Z")
    assert model.comparison_layout(PRESET_AMP_PHASE) == [PaneSpec("Z", REAL)]


def test_preset_optical_topography(synthetic_dataset: Dataset) -> None:
    panes = ExplorerModel(synthetic_dataset).comparison_layout(PRESET_OPTICAL_TOPO)
    assert panes == [PaneSpec("O2", AMPLITUDE), PaneSpec("Z", REAL)]


def test_preset_sample_reference(synthetic_dataset: Dataset) -> None:
    model = ExplorerModel(synthetic_dataset)
    assert model.comparison_layout(PRESET_SAMPLE_REF) == [
        PaneSpec("O2", AMPLITUDE),
        PaneSpec("R_O2", AMPLITUDE),
    ]
    # Anchoring on the reference resolves back to the same sample/reference pair.
    model.set_channel("R_O2")
    assert model.comparison_layout(PRESET_SAMPLE_REF) == [
        PaneSpec("O2", AMPLITUDE),
        PaneSpec("R_O2", AMPLITUDE),
    ]


def test_preset_harmonic_series_and_contact_sheet(golden_model: ExplorerModel) -> None:
    series = golden_model.comparison_layout(PRESET_HARMONIC_SERIES)
    assert series == [PaneSpec(f"O{n}", AMPLITUDE) for n in range(6)]
    assert golden_model.harmonic_panes() == series  # contact sheet uses the same set


def test_unknown_preset_raises(synthetic_dataset: Dataset) -> None:
    with pytest.raises(ValueError, match="unknown comparison preset"):
        ExplorerModel(synthetic_dataset).comparison_layout("nonsense")


def test_pane_spec_title() -> None:
    assert PaneSpec("O2", AMPLITUDE).title == "O2 amplitude"
    assert PaneSpec("Z", REAL).title == "Z"


def test_render_spec(synthetic_dataset: Dataset) -> None:
    rd = ExplorerModel(synthetic_dataset).render_spec(PaneSpec("O2", PHASE))
    assert rd.channel == "O2" and rd.representation == PHASE and rd.cyclic is True


# -- synchronized comparison cursor ------------------------------------------ #


def test_values_at_reports_every_pane(golden_model: ExplorerModel) -> None:
    specs = golden_model.comparison_layout(PRESET_OPTICAL_TOPO)  # [O2 amplitude, Z]
    rd = golden_model.render_spec(specs[0])
    x0, x1, y0, y1 = rd.extent_nm
    readout = golden_model.values_at(specs, (x0 + x1) / 2, (y0 + y1) / 2)
    assert readout.in_bounds is True
    labels = [v.label for v in readout.values]
    assert labels == ["O2 amplitude", "Z"]  # one value per visible pane, in order
    # Out of the field -> flagged, no values.
    assert golden_model.values_at(specs, x1 + 1e6, (y0 + y1) / 2).in_bounds is False


# -- publication figure spec ------------------------------------------------- #


def test_figure_spec_captures_display_and_provenance(synthetic_dataset: Dataset) -> None:
    model = ExplorerModel(synthetic_dataset)
    panels = [(PaneSpec("O2", AMPLITUDE), (0.5, 2.0))]
    spec = model.figure_spec(panels, [], kind="single", title="My figure")
    assert spec.kind == "single" and spec.title == "My figure"
    assert len(spec.panels) == 1
    panel = spec.panels[0]
    assert panel.channel == "O2" and panel.colormap == "viridis" and panel.unit == "a.u."
    assert (panel.vmin, panel.vmax) == (0.5, 2.0)
    # Provenance is baked in so the figure can explain and regenerate itself.
    assert spec.conventions["spatial_unit"] == "nm"
    assert spec.conventions["origin"] == "lower-left"
    assert spec.snomniman_version and "numpy" in spec.software
    assert spec.scale_bar_nm > 0 and spec.created_at


# -- measurements ------------------------------------------------------------ #


def test_line_profile_across_visible_channels(synthetic_dataset: Dataset) -> None:
    model = ExplorerModel(synthetic_dataset)
    specs = model.comparison_layout(PRESET_AMP_PHASE)  # [O2 amplitude, O2 phase]
    rd = model.render_spec(specs[0])
    x0, x1, y0, y1 = rd.extent_nm
    profile = model.line_profile(specs, (x0 + 5, (y0 + y1) / 2), (x1 - 5, (y0 + y1) / 2))
    assert profile.distance_nm == pytest.approx(x1 - 5 - (x0 + 5))
    assert len(profile.curves) == 2  # one curve per visible channel
    assert [c.label for c in profile.curves] == ["O2 amplitude", "O2 phase"]
    assert profile.curves[0].unit == "a.u." and profile.curves[1].unit == "rad"
    # Every curve has the same number of samples as the shared position axis.
    for curve in profile.curves:
        assert curve.samples.shape == profile.positions_nm.shape


def test_line_profile_values_match_channel(synthetic_dataset: Dataset) -> None:
    # A profile along a pixel-center row reproduces that row of the amplitude image.
    model = ExplorerModel(synthetic_dataset)
    amp = prepare_channel(synthetic_dataset, "O2", AMPLITUDE).values
    x = synthetic_dataset.coordinate("x").values
    y = synthetic_dataset.coordinate("y").values
    profile = model.line_profile([PaneSpec("O2", AMPLITUDE)], (x[0], y[1]), (x[-1], y[1]))
    samples = profile.curves[0].samples
    np.testing.assert_allclose(samples[0], amp[1, 0], atol=1e-5)
    np.testing.assert_allclose(samples[-1], amp[1, -1], atol=1e-5)


def test_rect_statistics(synthetic_dataset: Dataset) -> None:
    model = ExplorerModel(synthetic_dataset)
    specs = [PaneSpec("Z", REAL)]
    report = model.rect_statistics(specs, 0.0, 0.0, 1e9, 1e9)  # whole field
    row = report.rows[0]
    z = synthetic_dataset.channel("Z").values
    assert report.kind == "rectangle"
    assert report.count == z.size
    assert row.unit == "nm"
    assert row.stats.mean == pytest.approx(float(np.mean(z)))
    assert row.stats.maximum == pytest.approx(float(np.max(z)))
    # Area equals pixel count times pixel area.
    assert report.area_nm2 == pytest.approx(z.size * model.pixel_area_nm2())


def test_polygon_statistics_runs_for_every_channel(golden_model: ExplorerModel) -> None:
    specs = golden_model.comparison_layout(PRESET_OPTICAL_TOPO)  # [O2 amplitude, Z]
    report = golden_model.polygon_statistics(
        specs, [(57000.0, 11000.0), (63000.0, 11000.0), (60000.0, 17000.0)]
    )
    assert report.kind == "polygon"
    assert report.count > 0
    assert [r.label for r in report.rows] == ["O2 amplitude", "Z"]


def test_measurements_do_not_mutate_dataset(golden_model: ExplorerModel) -> None:
    ds = golden_model.dataset
    before = {name: ds.channel(name).values.copy() for name in ds.channel_names}
    specs = golden_model.comparison_layout(PRESET_AMP_PHASE)
    golden_model.line_profile(specs, (56000.0, 10000.0), (65000.0, 19000.0))
    golden_model.rect_statistics(specs, 57000.0, 11000.0, 63000.0, 17000.0)
    for name, arr in before.items():
        np.testing.assert_array_equal(ds.channel(name).values, arr, err_msg=name)
        assert ds.channel(name).data.flags.writeable is False


def test_comparison_does_not_mutate_dataset(golden_model: ExplorerModel) -> None:
    ds = golden_model.dataset
    before = {name: ds.channel(name).values.copy() for name in ds.channel_names}
    presets = (PRESET_AMP_PHASE, PRESET_OPTICAL_TOPO, PRESET_SAMPLE_REF, PRESET_HARMONIC_SERIES)
    for preset in presets:
        specs = golden_model.comparison_layout(preset)
        for spec in specs:
            golden_model.render_spec(spec)
        golden_model.values_at(specs, 0.0, 0.0)
    for name, arr in before.items():
        np.testing.assert_array_equal(ds.channel(name).values, arr, err_msg=name)
        assert ds.channel(name).data.flags.writeable is False


# --------------------------------------------------------------------------- #
# Hyperspectral dispatch state + band/pixel/ROI spectrum extraction (Phase 5B)
# --------------------------------------------------------------------------- #


def test_is_hyperspectral_never_overlaps_is_spectral(
    synthetic_dataset: Dataset, spectrum_dataset: Dataset, hyperspectral_dataset: Dataset
) -> None:
    image = ExplorerModel(synthetic_dataset)
    point_spectrum = ExplorerModel(spectrum_dataset)
    cube = ExplorerModel(hyperspectral_dataset)

    assert image.is_hyperspectral is False and image.is_spectral is False
    assert point_spectrum.is_hyperspectral is False and point_spectrum.is_spectral is True
    # The load-bearing regression: is_spectral must NOT be True for a hyperspectral
    # dataset (it has both SPATIAL_2D and SPECTRAL) - is_hyperspectral is a genuine
    # third state, never an overload.
    assert cube.is_hyperspectral is True and cube.is_spectral is False


def test_wavenumber_axis(hyperspectral_dataset: Dataset) -> None:
    model = ExplorerModel(hyperspectral_dataset)
    wn = model.wavenumber_axis()
    assert wn.shape == (25,)
    assert wn[0] == pytest.approx(1700.0)
    assert wn[12] == pytest.approx(1724.0)


def test_band_map_matches_viz_prepare_band(hyperspectral_dataset: Dataset) -> None:
    model = ExplorerModel(hyperspectral_dataset)
    rd = model.band_map(12)
    expected = prepare_band(hyperspectral_dataset, "O2", 12, AMPLITUDE)
    np.testing.assert_allclose(rd.values, expected.values)


def test_pixel_spectrum_recovers_the_known_resonance(hyperspectral_dataset: Dataset) -> None:
    model = ExplorerModel(hyperspectral_dataset)
    curve = model.pixel_spectrum(x_index=3, y_index=2)  # the fixture's known peak pixel
    peak_idx = int(np.argmax(curve.values))
    assert peak_idx == 12
    assert curve.wavenumber_cm1[peak_idx] == pytest.approx(1724.0)


def test_pixel_spectrum_off_peak_is_flat(hyperspectral_dataset: Dataset) -> None:
    model = ExplorerModel(hyperspectral_dataset)
    curve = model.pixel_spectrum(x_index=0, y_index=0)
    np.testing.assert_allclose(curve.values, 0.2, atol=1e-6)


def test_rect_spectrum_including_peak_recovers_it(hyperspectral_dataset: Dataset) -> None:
    model = ExplorerModel(hyperspectral_dataset)
    # The known peak pixel is (y=2, x=3); an ROI covering it recovers the bump
    # even after averaging with three flat neighbours.
    curve = model.rect_spectrum(x0=100.0, y0=75.0, x1=250.0, y1=175.0, label="ROI A")
    assert int(np.argmax(curve.values)) == 12
    assert curve.values.max() > 0.3  # diluted by neighbours, but still a clear bump


def test_rect_spectrum_excluding_peak_is_flat(hyperspectral_dataset: Dataset) -> None:
    model = ExplorerModel(hyperspectral_dataset)
    curve = model.rect_spectrum(x0=0.0, y0=0.0, x1=50.0, y1=50.0)
    np.testing.assert_allclose(curve.values, 0.2, atol=0.03)


def test_rect_spectrum_full_frame_matches_independent_mean(hyperspectral_dataset: Dataset) -> None:
    model = ExplorerModel(hyperspectral_dataset)
    curve = model.rect_spectrum(x0=0.0, y0=0.0, x1=250.0, y1=200.0)
    expected = np.mean(np.abs(hyperspectral_dataset.channel("O2").values), axis=(0, 1))
    np.testing.assert_allclose(curve.values, expected, rtol=1e-6)


def test_polygon_spectrum_recovers_the_known_resonance(hyperspectral_dataset: Dataset) -> None:
    # A generously-sized polygon covering the known peak pixel (y=2, x=3). Exact
    # numeric equality with rect_spectrum isn't assumed - rect_mask/polygon_mask
    # can differ at pixel-center boundary inclusion (an existing, validated
    # property of those primitives, not something this test should pin).
    model = ExplorerModel(hyperspectral_dataset)
    polygon = model.polygon_spectrum(
        [(50.0, 50.0), (300.0, 50.0), (300.0, 200.0), (50.0, 200.0)]
    )
    assert int(np.argmax(polygon.values)) == 12


def test_nearest_pixel_reuses_extent_lookup(hyperspectral_dataset: Dataset) -> None:
    model = ExplorerModel(hyperspectral_dataset)
    iy, ix, in_bounds = model.nearest_pixel(175.0, 125.0)  # near pixel (y=2, x=3)
    assert in_bounds is True
    assert (iy, ix) == (2, 3)
    assert model.nearest_pixel(-1000.0, -1000.0)[2] is False


def test_band_map_histogram_is_per_band_not_whole_cube(hyperspectral_dataset: Dataset) -> None:
    model = ExplorerModel(hyperspectral_dataset)
    peak_band = model.band_map_histogram(12)
    off_band = model.band_map_histogram(0)
    # A per-band histogram must differ between the peak band and a flat band -
    # a whole-cube statistic would give the same (wrong) answer for both.
    assert peak_band.maximum != pytest.approx(off_band.maximum)


def test_band_dataset_is_a_plain_2d_image(hyperspectral_dataset: Dataset) -> None:
    from snomniman.core import DataKind

    model = ExplorerModel(hyperspectral_dataset)
    band = model.band_dataset(12)
    assert band.kind is DataKind.IMAGE
    assert "wavenumber" not in band.coord_names
    np.testing.assert_allclose(
        band.channel("O2").values,
        hyperspectral_dataset.channel("O2").isel(wavenumber=12).values,
    )
    assert band.provenance.inputs["primary"] is hyperspectral_dataset.provenance


def test_band_dataset_rejects_a_channel_with_no_wavenumber(hyperspectral_dataset: Dataset) -> None:
    from snomniman.core.exceptions import ProcessingError

    model = ExplorerModel(hyperspectral_dataset)
    model.set_channel("Z")
    with pytest.raises(ProcessingError, match="wavenumber"):
        model.band_dataset(0)
