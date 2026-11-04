"""Tests for snomniman.diagnostics feature diagnostics (Phase 7B).

Covers (Rule 6 + the diagnostics invariants: facts, never opinions, honest ``None``):
- feature_diagnostics returns None for an absent/non-label channel or a non-spatial
  dataset (an inapplicable request is a fact, not an error).
- Known-answer morphology on a labeled 4x4 and 5x7 blob pair (pixel_size 50x50 nm):
  exact count, pixel_count, area_nm2, equivalent_diameter_nm, coverage_fraction.
- Aspect ratio is > 1 and larger for the more elongated blob (a relative, not exact,
  check - the closed-form covariance construction is validated by shape, not a single
  hand-derived number).
- A too-small (< 3 pixel) region reports None shape metrics but a real area.
- size_histogram is a HistogramData sized to the feature count.
- all_feature_diagnostics / diagnose() wiring; JSON round-trip via to_dict.
"""

from __future__ import annotations

import math

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
from snomniman.diagnostics import (
    FeatureDiagnostics,
    HistogramData,
    all_feature_diagnostics,
    diagnose,
    feature_diagnostics,
)
from snomniman.processing.image.threshold_segment import ThresholdSegment


def _z_dataset(
    z: npt.NDArray[np.float64], *, pixel_size: tuple[float, float] = (50.0, 50.0)
) -> Dataset:
    ny, nx = z.shape
    dx, dy = pixel_size
    x = (np.arange(nx, dtype=np.float64) + 0.5) * dx
    y = (np.arange(ny, dtype=np.float64) + 0.5) * dy
    data = xr.Dataset(
        {"Z": xr.DataArray(z, dims=["y", "x"])},
        coords={
            "x": ("x", x, {"unit": "nm", "axis": "X"}),
            "y": ("y", y, {"unit": "nm", "axis": "Y"}),
        },
    )
    meta = Metadata(
        data_kind=DataKind.IMAGE,
        scan=ScanInfo(pixels=(nx, ny), size_nm=(nx * dx, ny * dy), pixel_size_nm=pixel_size),
        channels=(ChannelInfo("Z", "topography", "signal", "float64", value_unit="nm"),),
    )
    node = ProvenanceNode(
        node_id="n0",
        record=StepRecord(step_id="io.read", step_version=1, deterministic=True),
    )
    return Dataset(data, kind=DataKind.IMAGE, metadata=meta, provenance=node)


def _two_blobs(ny: int = 20, nx: int = 20) -> npt.NDArray[np.float64]:
    z = np.zeros((ny, nx), dtype=np.float64)
    z[2:6, 2:6] = 1.0  # 4x4 = 16 px, square
    z[12:17, 12:19] = 1.0  # 5x7 = 35 px, elongated
    return z


def _segmented(z: npt.NDArray[np.float64]) -> Dataset:
    ds = _z_dataset(z)
    step = ThresholdSegment(channel="Z", method="fixed", threshold=0.5, min_pixels=1)
    return step.apply({"primary": ds})


# --------------------------------------------------------------------------- #
# Absence / inapplicability
# --------------------------------------------------------------------------- #


def test_feature_diagnostics_none_for_missing_channel() -> None:
    ds = _z_dataset(_two_blobs())
    assert feature_diagnostics(ds, "Z_labels") is None


def test_feature_diagnostics_none_for_non_label_channel() -> None:
    ds = _segmented(_two_blobs())
    assert feature_diagnostics(ds, "Z") is None


def test_all_feature_diagnostics_empty_when_no_label_channel() -> None:
    ds = _z_dataset(_two_blobs())
    assert all_feature_diagnostics(ds) == ()


# --------------------------------------------------------------------------- #
# Known-answer morphology
# --------------------------------------------------------------------------- #


def test_feature_diagnostics_known_count_and_area() -> None:
    ds = _segmented(_two_blobs())
    fd = feature_diagnostics(ds, "Z_labels")
    assert isinstance(fd, FeatureDiagnostics)
    assert fd.label_channel == "Z_labels"
    assert fd.source_channel == "Z"
    assert fd.count == 2

    by_size = sorted(fd.features, key=lambda f: f.pixel_count)
    square, elongated = by_size
    assert square.pixel_count == 16
    assert elongated.pixel_count == 35

    # pixel_size 50x50 nm -> 2500 nm^2 per pixel.
    assert math.isclose(square.area_nm2 or 0.0, 16 * 2500.0)
    assert math.isclose(elongated.area_nm2 or 0.0, 35 * 2500.0)
    expected_diam = 2.0 * math.sqrt((16 * 2500.0) / math.pi)
    assert math.isclose(square.equivalent_diameter_nm or 0.0, expected_diam)

    assert fd.total_area_nm2 is not None
    assert math.isclose(fd.total_area_nm2, (16 + 35) * 2500.0)


def test_feature_diagnostics_coverage_fraction() -> None:
    ds = _segmented(_two_blobs(ny=20, nx=20))
    fd = feature_diagnostics(ds, "Z_labels")
    assert fd is not None
    field_area = (20 * 50.0) * (20 * 50.0)
    expected = ((16 + 35) * 2500.0) / field_area
    assert fd.coverage_fraction is not None
    assert math.isclose(fd.coverage_fraction, expected)


def test_feature_diagnostics_elongated_blob_has_larger_aspect_ratio() -> None:
    ds = _segmented(_two_blobs())
    fd = feature_diagnostics(ds, "Z_labels")
    assert fd is not None
    by_size = sorted(fd.features, key=lambda f: f.pixel_count)
    square, elongated = by_size
    assert square.aspect_ratio is not None
    assert elongated.aspect_ratio is not None
    assert square.aspect_ratio >= 1.0
    assert elongated.aspect_ratio > square.aspect_ratio  # 5x7 is visibly more elongated than 4x4


def test_feature_diagnostics_source_channel_statistics() -> None:
    z = _two_blobs()
    z[2:6, 2:6] = 3.0  # give the square blob a distinct source value
    ds = _segmented(z)
    fd = feature_diagnostics(ds, "Z_labels")
    assert fd is not None
    square = next(f for f in fd.features if f.pixel_count == 16)
    assert square.mean_value == 3.0
    assert square.minimum_value == 3.0
    assert square.maximum_value == 3.0
    assert square.source_channel == "Z"
    assert square.source_unit == "nm"


def test_feature_diagnostics_small_region_has_no_shape_metrics_but_has_area() -> None:
    z = np.zeros((10, 10), dtype=np.float64)
    z[3, 3] = 1.0
    z[3, 4] = 1.0  # a 2-pixel region: below the shape-metric minimum
    ds = _segmented(z)
    fd = feature_diagnostics(ds, "Z_labels")
    assert fd is not None
    assert fd.count == 1
    feat = fd.features[0]
    assert feat.pixel_count == 2
    assert feat.aspect_ratio is None
    assert feat.orientation_deg is None
    assert feat.area_nm2 is not None  # area/diameter still computable from pixel count alone


def test_feature_diagnostics_size_histogram_matches_count() -> None:
    ds = _segmented(_two_blobs())
    fd = feature_diagnostics(ds, "Z_labels")
    assert fd is not None
    assert isinstance(fd.size_histogram, HistogramData)
    assert fd.size_histogram.count == fd.count == 2


def test_feature_diagnostics_no_features_when_all_background() -> None:
    ds = _segmented(np.zeros((10, 10)))
    fd = feature_diagnostics(ds, "Z_labels")
    assert fd is not None
    assert fd.count == 0
    assert fd.features == ()
    assert fd.total_area_nm2 is None
    assert fd.coverage_fraction is None
    assert fd.size_histogram is None


# --------------------------------------------------------------------------- #
# Wiring: all_feature_diagnostics / diagnose()
# --------------------------------------------------------------------------- #


def test_all_feature_diagnostics_finds_the_one_label_channel() -> None:
    ds = _segmented(_two_blobs())
    all_fd = all_feature_diagnostics(ds)
    assert len(all_fd) == 1
    assert all_fd[0].label_channel == "Z_labels"


def test_diagnose_includes_features() -> None:
    ds = _segmented(_two_blobs())
    diag = diagnose(ds)
    assert len(diag.features) == 1
    assert diag.features[0].count == 2


def test_diagnose_features_empty_without_segmentation() -> None:
    ds = _z_dataset(_two_blobs())
    diag = diagnose(ds)
    assert diag.features == ()


# --------------------------------------------------------------------------- #
# JSON round-trip
# --------------------------------------------------------------------------- #


def test_feature_diagnostics_to_dict_round_trips_through_json() -> None:
    import json

    ds = _segmented(_two_blobs())
    fd = feature_diagnostics(ds, "Z_labels")
    assert fd is not None
    payload = json.loads(json.dumps(fd.to_dict()))
    assert payload["count"] == 2
    assert len(payload["features"]) == 2
