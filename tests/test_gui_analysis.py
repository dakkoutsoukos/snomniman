"""End-to-end window tests for the Phase 3B analysis surfaces (read-only).

Verify, through the window, that the three analysis capabilities are wired into the
existing surfaces: line-profile feature analysis + a richer region table and
region-vs-region comparison (Measurements), and the value-distribution histogram
(Diagnostics). Each is read-only - no derived dataset is created. Skipped without
the gui extra; headless (offscreen) otherwise.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from snomniman.core import Dataset
from snomniman.gui.model import ExplorerModel

pytest.importorskip("PySide6")

from snomniman.gui.window import MeasurementExplorerWindow


@pytest.fixture
def window(qapp: Any, synthetic_dataset: Dataset) -> Iterator[MeasurementExplorerWindow]:
    win = MeasurementExplorerWindow(ExplorerModel(synthetic_dataset, title="CdO"))
    win.resize(1100, 720)
    win.show()  # realize the scene so overlay geometry maps to physical coords
    qapp.processEvents()
    yield win
    win.close()
    win.deleteLater()
    qapp.processEvents()


# -- histogram (Diagnostics) ------------------------------------------------- #


def test_diagnostics_histogram_reflects_active_channel(window: MeasurementExplorerWindow) -> None:
    hist = window._model.channel_histogram()
    assert hist.count > 0
    assert hist.mean is not None
    # The Diagnostics panel's distribution summary was populated on load.
    assert "n =" in window._diagnostics._hist_summary.text()


def test_diagnostics_histogram_updates_on_channel_change(
    window: MeasurementExplorerWindow, qapp: Any
) -> None:
    window._browser.channelSelected.emit("Z")
    qapp.processEvents()
    # Z is real with unit nm: the distribution's x-axis label follows the channel.
    assert window._model.channel_histogram().unit == "nm"


# -- line-profile feature analysis (Measurements) ---------------------------- #


def test_line_profile_reports_features(window: MeasurementExplorerWindow, qapp: Any) -> None:
    window._measure.add_line()
    qapp.processEvents()
    features = window._measure.profile_features()
    assert features is not None
    assert features.count > 0
    # The Measure panel shows a profile feature summary.
    assert "Profile" in window._measure_panel._analysis.text()


# -- region statistics + comparison (Measurements) --------------------------- #


def test_region_table_has_variability_columns(
    window: MeasurementExplorerWindow, qapp: Any
) -> None:
    window._measure.add_rectangle()
    qapp.processEvents()
    table = window._measure_panel._table
    headers: set[str] = set()
    for c in range(table.columnCount()):
        item = table.horizontalHeaderItem(c)
        if item is not None:
            headers.add(item.text())
    assert {"Std", "RMS", "P25", "P75"} <= headers


def test_region_comparison_exposes_difference_ratio_and_stats(
    window: MeasurementExplorerWindow, qapp: Any
) -> None:
    window._measure.add_rectangle()
    window._measure.add_rectangle()
    qapp.processEvents()
    window._measure_panel._compare_regions()
    comparison = window._measure_panel._comparison
    assert comparison is not None
    # Both the comparison and the underlying descriptive stats are available.
    assert comparison.difference is not None
    assert comparison.stats_a.count > 0 and comparison.stats_b.count > 0
    assert "vs" in window._measure_panel._analysis.text()


def test_compare_regions_without_two_regions_is_a_noop(
    window: MeasurementExplorerWindow, qapp: Any
) -> None:
    window._measure.add_rectangle()  # only one region
    qapp.processEvents()
    window._measure_panel._compare_regions()
    assert window._measure_panel._comparison is None
    assert "two regions" in window._measure_panel._analysis.text()
