"""Tests for the Qt-free experiment presenter (snomniman.gui.experiment).

ExperimentModel aggregates many measurements into experiment-wide views without a
display and without creating anything (Phase 2B is read-only): a browser overview,
cross-measurement comparison panes + a combined readout, an experiment diagnostics
table, and the same ROI/line evaluated across measurements. These exercise that
aggregation logic headlessly and confirm it only composes existing facts.
"""

from __future__ import annotations

import numpy as np
import pytest

import snomniman.processing.image  # noqa: F401  (registers image ops)
from snomniman.core import Dataset
from snomniman.gui.experiment import ExperimentModel
from snomniman.gui.model import ExplorerModel, MeasurementSession
from snomniman.processing import get_step
from snomniman.viz import AMPLITUDE, REAL


def _session(
    dataset: Dataset, *, mid: str, title: str, history: list[ExplorerModel] | None = None
) -> MeasurementSession:
    return MeasurementSession(
        model=ExplorerModel(dataset, title=title),
        measurement_id=mid,
        title=title,
        history=history or [],
    )


@pytest.fixture
def experiment(synthetic_dataset: Dataset, topography_dataset: Dataset) -> ExperimentModel:
    """A two-measurement experiment: a full optical scan and a topography-only scan."""
    return ExperimentModel(
        [
            _session(synthetic_dataset, mid="measurement-0001", title="CdO full"),
            _session(topography_dataset, mid="measurement-0002", title="Topo only"),
        ]
    )


# -- browser overview (Part 3) ----------------------------------------------- #


def test_browser_rows_summarize_each_measurement(experiment: ExperimentModel) -> None:
    rows = experiment.browser_rows()
    assert [r.title for r in rows] == ["CdO full", "Topo only"]
    assert [r.index for r in rows] == [0, 1]
    # The optical scan reports its harmonics + a reference; the topo scan reports neither.
    assert rows[0].harmonics == "2, 3"
    assert rows[0].has_reference is True
    assert rows[1].harmonics == "-"
    assert rows[1].has_reference is False
    # Both are raw (no derivation history yet).
    assert rows[0].processing == "raw" and rows[1].processing == "raw"


def test_browser_processing_reflects_history(synthetic_dataset: Dataset) -> None:
    raw = synthetic_dataset
    derived = get_step("image.plane_level")(channel="Z", order=1).apply({"primary": raw})
    session = _session(
        derived, mid="measurement-0001", title="CdO", history=[ExplorerModel(raw)]
    )
    rows = ExperimentModel([session]).browser_rows()
    assert rows[0].processing == "1 step"


# -- cross-measurement comparison (Part 1) ----------------------------------- #


def test_shared_channels_is_the_intersection(experiment: ExperimentModel) -> None:
    # Z is in both; the optical channels are only in the first measurement.
    assert experiment.shared_channels([0, 1]) == ["Z"]
    assert "O2" in experiment.shared_channels([0])


def test_comparison_panes_render_each_measurement(experiment: ExperimentModel) -> None:
    panes = experiment.comparison_panes([0, 1], "Z", REAL)
    assert len(panes) == 2
    assert [p.index for p in panes] == [0, 1]
    # Labels disambiguate the panes by measurement (and keep dict-renderer keys unique).
    assert panes[0].spec.label == "CdO full: Z"
    assert panes[1].spec.label == "Topo only: Z"
    assert panes[0].spec != panes[1].spec
    assert np.asarray(panes[0].render.values).ndim == 2  # a real rendered image


def test_comparison_skips_measurements_missing_the_channel(experiment: ExperimentModel) -> None:
    # O2 exists only in the first measurement -> only one pane.
    panes = experiment.comparison_panes([0, 1], "O2", AMPLITUDE)
    assert [p.index for p in panes] == [0]


def test_comparison_readout_reports_each_measurement(experiment: ExperimentModel) -> None:
    readout = experiment.comparison_readout([0, 1], "Z", REAL, 100.0, 75.0)
    assert readout.in_bounds is True
    labels = [v.label for v in readout.values]
    assert any(label.startswith("CdO full:") for label in labels)
    assert any(label.startswith("Topo only:") for label in labels)


# -- experiment diagnostics (Part 4) ----------------------------------------- #


def test_diagnostics_table_shape_and_cells(experiment: ExperimentModel) -> None:
    table = experiment.diagnostics_table()
    assert [c.label for c in table.columns] == [
        "Processing",
        "Roughness Sq",
        "Tilt",
        "Signal harmonics",
        "Reference",
    ]
    assert [r.title for r in table.rows] == ["CdO full", "Topo only"]
    # Both have topography -> a finite roughness sort key; reference differs by scan.
    for row in table.rows:
        assert row.cells[1].value is not None  # roughness Sq computed
    assert table.rows[0].cells[4].text == "yes"  # optical scan has a reference
    assert table.rows[1].cells[4].text == "no"  # topo scan does not


def test_diagnostics_are_cached_per_dataset(experiment: ExperimentModel) -> None:
    experiment.diagnostics_table()
    assert len(experiment._diag_cache) == 2  # one entry per distinct dataset
    # A second call reuses the cache and yields an identical table.
    again = experiment.diagnostics_table()
    assert len(experiment._diag_cache) == 2
    assert [r.cells[1].text for r in again.rows] == [
        r.cells[1].text for r in experiment.diagnostics_table().rows
    ]


# -- cross-measurement statistics (Part 5) ----------------------------------- #


def test_compare_region_tabulates_stats_per_measurement(experiment: ExperimentModel) -> None:
    table = experiment.compare_region([0, 1], "rectangle", (50.0, 50.0, 150.0, 100.0), "Z", REAL)
    assert [c.label for c in table.columns] == ["Mean", "Median", "Min", "Max", "Std"]
    assert len(table.rows) == 2
    assert table.rows[0].cells[0].value is not None  # a finite mean over the region


def test_compare_profile_summarizes_each_line(experiment: ExperimentModel) -> None:
    table = experiment.compare_profile([0, 1], (0.0, 75.0), (200.0, 75.0), "Z", REAL)
    assert [c.label for c in table.columns] == ["Length", "Mean", "Min", "Max"]
    assert len(table.rows) == 2
    length = table.rows[0].cells[0].value
    assert length is not None and length > 0  # a real line length in nm


# -- session management ------------------------------------------------------ #


def test_set_sessions_updates_count(experiment: ExperimentModel) -> None:
    assert experiment.count == 2
    experiment.set_sessions([])
    assert experiment.count == 0
