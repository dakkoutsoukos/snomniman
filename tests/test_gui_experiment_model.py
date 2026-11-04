"""Qt-free tests for snomniman.gui.experiment.ExperimentModel.feature_table (Phase 7C).

ExperimentModel is a Qt-free presenter (its own docstring: "aggregating a project's
measurements as one experiment"), so this exercises it directly - no QApplication, no
pytest.importorskip("PySide6") - mirroring how test_gui_report.py already tests
ReportModel without a display.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt
import xarray as xr

from snomniman.core import (
    ChannelInfo,
    DataKind,
    Dataset,
    Metadata,
    ProvenanceNode,
    ScanInfo,
    StepRecord,
)
from snomniman.gui.experiment import ExperimentModel
from snomniman.gui.model import ExplorerModel, MeasurementSession
from snomniman.processing.image.threshold_segment import ThresholdSegment


def _z_dataset(z: npt.NDArray[np.float64]) -> Dataset:
    ny, nx = z.shape
    x = (np.arange(nx, dtype=np.float64) + 0.5) * 50.0
    y = (np.arange(ny, dtype=np.float64) + 0.5) * 50.0
    data = xr.Dataset(
        {"Z": xr.DataArray(z, dims=["y", "x"])},
        coords={
            "x": ("x", x, {"unit": "nm", "axis": "X"}),
            "y": ("y", y, {"unit": "nm", "axis": "Y"}),
        },
    )
    meta = Metadata(
        data_kind=DataKind.IMAGE,
        scan=ScanInfo(pixels=(nx, ny), size_nm=(nx * 50.0, ny * 50.0), pixel_size_nm=(50.0, 50.0)),
        channels=(ChannelInfo("Z", "topography", "signal", "float64", value_unit="nm"),),
    )
    node = ProvenanceNode(
        node_id="n0",
        record=StepRecord(step_id="io.read", step_version=1, deterministic=True),
    )
    return Dataset(data, kind=DataKind.IMAGE, metadata=meta, provenance=node)


def _two_blobs(ny: int = 20, nx: int = 20) -> npt.NDArray[np.float64]:
    z = np.zeros((ny, nx), dtype=np.float64)
    z[2:6, 2:6] = 1.0  # 16 px
    z[12:17, 12:19] = 1.0  # 35 px
    return z


def _session(dataset: Dataset, *, mid: str, title: str) -> MeasurementSession:
    return MeasurementSession(
        model=ExplorerModel(dataset, title=title), measurement_id=mid, title=title
    )


def test_feature_table_reports_dash_for_unsegmented_measurement() -> None:
    session = _session(_z_dataset(_two_blobs()), mid="measurement-0001", title="Raw")
    table = ExperimentModel([session]).feature_table()
    assert table.title == "Feature analysis"
    assert len(table.rows) == 1
    assert all(c.text == "-" for c in table.rows[0].cells)


def test_feature_table_reports_segmented_measurement() -> None:
    raw = _z_dataset(_two_blobs())
    segmented = ThresholdSegment(channel="Z", method="fixed", threshold=0.5, min_pixels=1).apply(
        {"primary": raw}
    )
    session = _session(segmented, mid="measurement-0001", title="Segmented")
    table = ExperimentModel([session]).feature_table()
    row = table.rows[0]
    label_channels, count, total_area, coverage, mean_diameter = row.cells

    assert label_channels.text == "Z_labels"
    assert count.text == "2"
    assert count.value == 2.0
    assert total_area.value is not None
    assert coverage.value is not None
    assert mean_diameter.value is not None


def test_feature_table_mixed_project_one_row_per_measurement() -> None:
    raw = _z_dataset(_two_blobs())
    segmented = ThresholdSegment(channel="Z", method="fixed", threshold=0.5, min_pixels=1).apply(
        {"primary": raw}
    )
    sessions = [
        _session(raw, mid="measurement-0001", title="Unsegmented"),
        _session(segmented, mid="measurement-0002", title="Segmented"),
    ]
    table = ExperimentModel(sessions).feature_table()
    assert len(table.rows) == 2
    assert table.rows[0].cells[1].text == "-"
    assert table.rows[1].cells[1].text == "2"
