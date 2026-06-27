"""Tests for provenance-bearing publication figures (snomniman.viz.figure).

Qt-free: renders with a standalone matplotlib Figure (Agg), so these run headless.
"""

from __future__ import annotations

import json
from pathlib import Path

from matplotlib.figure import Figure

from snomniman.core import Dataset
from snomniman.viz import (
    AMPLITUDE,
    PHASE,
    REAL,
    FigureSpec,
    OverlaySpec,
    PanelSpec,
    export,
    provenance_caption,
    provenance_record,
    render_figure,
    render_from_record,
)


def _spec(kind: str = "single", panels: tuple[PanelSpec, ...] = (), overlays=()) -> FigureSpec:  # type: ignore[no-untyped-def]
    if not panels:
        panels = (PanelSpec("O2", AMPLITUDE, "O2 amplitude", "a.u.", "viridis", False, 0.5, 2.0),)
    return FigureSpec(
        title="Test figure",
        kind=kind,
        measurement="CdO test",
        source_path="data/cdo",
        source_sha256="abc123def456",
        panels=panels,
        extent_nm=(0.0, 200.0, 0.0, 150.0),
        scale_bar_nm=50.0,
        scale_bar_label="50 nm",
        overlays=tuple(overlays),
        conventions={"spatial_unit": "nm", "origin": "lower-left", "phase": "as imported"},
        created_at="2026-06-26T12:00:00+00:00",
        snomniman_version="0.1.0",
        software={"snomniman": "0.1.0", "numpy": "2.x"},
    )


def test_figure_spec_roundtrips() -> None:
    overlay = OverlaySpec("line", "Particle width", ((10.0, 20.0), (180.0, 120.0)))
    spec = _spec(overlays=(overlay,))
    rebuilt = FigureSpec.from_dict(json.loads(json.dumps(spec.to_dict())))
    assert rebuilt == spec  # frozen dataclasses compare by value, JSON-stable


def test_render_single_panel(synthetic_dataset: Dataset) -> None:
    fig = render_figure(_spec("single"), synthetic_dataset)
    assert isinstance(fig, Figure)
    # One image panel -> one image axes plus its colorbar axes.
    assert len(fig.axes) >= 2


def test_render_comparison_two_panels(synthetic_dataset: Dataset) -> None:
    panels = (
        PanelSpec("O2", AMPLITUDE, "O2 amplitude", "a.u.", "viridis", False, 0.5, 2.0),
        PanelSpec("O2", PHASE, "O2 phase", "rad", "twilight", True, -3.14, 3.14),
    )
    fig = render_figure(_spec("comparison", panels), synthetic_dataset)
    # Two image panels (each with a colorbar).
    assert len(fig.axes) >= 4


def test_measurement_figure_adds_profile_axis(synthetic_dataset: Dataset) -> None:
    overlay = OverlaySpec("line", "Profile", ((10.0, 75.0), (190.0, 75.0)))
    panels = (PanelSpec("Z", REAL, "Z", "nm", "afmhot", False, 50.0, 200.0),)
    no_profile = len(render_figure(_spec("single", panels), synthetic_dataset).axes)
    measurement_fig = render_figure(_spec("measurement", panels, (overlay,)), synthetic_dataset)
    assert len(measurement_fig.axes) > no_profile  # gains a profile subplot


def test_provenance_record_and_caption() -> None:
    spec = _spec(overlays=(OverlaySpec("rectangle", "ROI 1", ((0.0, 0.0), (10.0, 10.0))),))
    record = provenance_record(spec)
    assert record["figure_spec"]["measurement"] == "CdO test"
    caption = provenance_caption(spec)
    assert "CdO test" in caption
    assert "O2 amplitude" in caption  # panels + their colormap/range
    assert "ROI 1" in caption  # measurement overlays
    assert "SNOMNIMAN 0.1.0" in caption
    assert "lower-left" in caption  # conventions


def test_export_writes_figure_and_provenance(synthetic_dataset: Dataset, tmp_path: Path) -> None:
    out = tmp_path / "figure.png"
    figure_path, provenance_path = export(_spec("single"), synthetic_dataset, out)
    assert figure_path.exists() and figure_path.stat().st_size > 0
    assert provenance_path.exists()
    record = json.loads(provenance_path.read_text(encoding="utf-8"))
    assert record["figure_spec"]["title"] == "Test figure"
    assert "caption" in record


def test_figure_is_reproducible_from_record(synthetic_dataset: Dataset, tmp_path: Path) -> None:
    # The saved provenance regenerates the same figure from the original measurement.
    _, provenance_path = export(_spec("single"), synthetic_dataset, tmp_path / "f.pdf")
    record = json.loads(provenance_path.read_text(encoding="utf-8"))
    fig = render_from_record(record, synthetic_dataset)
    assert isinstance(fig, Figure)


def test_export_does_not_modify_dataset(synthetic_dataset: Dataset, tmp_path: Path) -> None:
    import numpy as np

    ds = synthetic_dataset
    before = {n: ds.channel(n).values.copy() for n in ds.channel_names}
    export(_spec("single"), ds, tmp_path / "f.svg")
    for name, arr in before.items():
        np.testing.assert_array_equal(ds.channel(name).values, arr)
        assert ds.channel(name).data.flags.writeable is False
