"""Tests for the Explorer's Diagnostics panel (presentation of computed facts).

The panel is pure presentation: it must render the model's diagnostic sections and
never mutate the dataset. The scientific correctness of the numbers themselves is
covered by ``tests/test_diagnostics.py``.
"""

from __future__ import annotations

from typing import Any

import pytest

from snomniman.core import Dataset
from snomniman.gui.model import DiagnosticSection, ExplorerModel

pytest.importorskip("PySide6")


def test_model_report_has_expected_sections(synthetic_dataset: Dataset) -> None:
    sections = ExplorerModel(synthetic_dataset).diagnostics_report()
    titles = [s.title for s in sections]
    assert "Topography" in titles
    assert "Optical harmonics" in titles
    assert "Channels" in titles
    assert "Processing applicability" in titles


def test_report_mentions_applicable_operation(synthetic_dataset: Dataset) -> None:
    sections = {s.title: s for s in ExplorerModel(synthetic_dataset).diagnostics_report()}
    ops = sections["Processing applicability"]
    plane = next(r for r in ops.rows if r.label == "image.plane_level")
    assert "available" in plane.value


def test_harmonic_rows_show_signal_noise_classification() -> None:
    # The Optical harmonics section renders the deterministic signal/noise class.
    import numpy as np
    import xarray as xr

    from snomniman.core import ChannelInfo, DataKind, Metadata, ProvenanceNode, StepRecord

    ny, nx = 64, 64
    yy, xx = np.mgrid[0:ny, 0:nx].astype(float)
    smooth = np.exp(-(((xx - 30) ** 2 + (yy - 32) ** 2) / (2 * 15.0**2))) + 5.0
    rng = np.random.default_rng(3)
    noise = np.abs(rng.standard_normal((ny, nx)) + 1j * rng.standard_normal((ny, nx)))
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

    sections = {s.title: s for s in ExplorerModel(ds).diagnostics_report()}
    rows = {r.label: r.value for r in sections["Optical harmonics"].rows}
    assert "signal" in rows["O2 mean amplitude"] and "coherence" in rows["O2 mean amplitude"]
    assert "noise" in rows["O4 mean amplitude"]


def test_panel_renders_report(qapp: Any, synthetic_dataset: Dataset) -> None:
    from snomniman.gui.diagnostics import DiagnosticsPanel

    panel = DiagnosticsPanel()
    sections = ExplorerModel(synthetic_dataset).diagnostics_report()
    panel.set_report(sections)
    # One top-level tree item per section.
    assert panel._tree.topLevelItemCount() == len(sections)
    # Re-rendering replaces rather than appends.
    panel.set_report(sections)
    assert panel._tree.topLevelItemCount() == len(sections)


def test_window_has_diagnostics_tab(qapp: Any, synthetic_dataset: Dataset) -> None:
    from snomniman.gui.window import MeasurementExplorerWindow

    window = MeasurementExplorerWindow(ExplorerModel(synthetic_dataset))
    tab_titles = [
        window._inspect_tabs.tabText(i) for i in range(window._inspect_tabs.count())
    ]
    assert "Diagnostics" in tab_titles


def test_diagnostics_does_not_mutate_dataset(qapp: Any, synthetic_dataset: Dataset) -> None:
    import numpy as np

    model = ExplorerModel(synthetic_dataset)
    before = {
        n: synthetic_dataset.channel(n).values.copy() for n in synthetic_dataset.channel_names
    }
    model.diagnostics_report()
    for name, values in before.items():
        np.testing.assert_array_equal(synthetic_dataset.channel(name).values, values)


def test_sections_are_view_objects(synthetic_dataset: Dataset) -> None:
    sections = ExplorerModel(synthetic_dataset).diagnostics_report()
    assert all(isinstance(s, DiagnosticSection) for s in sections)
