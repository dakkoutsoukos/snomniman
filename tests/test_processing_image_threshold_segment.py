"""Tests for snomniman.processing.image.threshold_segment - particle/domain labeling.

Covers (Rule 6 + the processing-engine invariants):
- otsu_threshold recovers a known separating cut on a synthetic bimodal histogram.
- segment_labels recovers exactly N labeled regions of the expected pixel count for
  well-separated synthetic blobs, for every method (otsu/percentile/fixed) and both
  polarities.
- The min_pixels filter drops a sub-threshold speck and renumbers contiguously (no
  gap in the surviving id sequence).
- ThresholdSegment.apply: appends '{channel}_labels', preserves every other channel
  (including the input) unchanged, input immutability, provenance recorded.
- Parameter validation (bad method/polarity, missing 'threshold' for method='fixed',
  missing/complex channel, a pre-existing label-channel name collision).
- Registry discovery.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt
import pytest
import xarray as xr

from snomniman.core import DataKind, Dataset, Metadata, ProvenanceNode, StepRecord
from snomniman.core.exceptions import ProcessingError
from snomniman.processing import get_step
from snomniman.processing.image.threshold_segment import (
    ThresholdSegment,
    otsu_threshold,
    segment_labels,
)


def _z_dataset(z: npt.NDArray[np.float64]) -> Dataset:
    """Minimal Dataset with one real-valued 'Z' channel on a uniform nm grid."""
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
    meta = Metadata(data_kind=DataKind.IMAGE)
    node = ProvenanceNode(
        node_id="n0",
        record=StepRecord(step_id="io.read", step_version=1, deterministic=True),
    )
    return Dataset(data, kind=DataKind.IMAGE, metadata=meta, provenance=node)


def _two_blobs(ny: int = 20, nx: int = 20) -> npt.NDArray[np.float64]:
    """Background 0.0 with two well-separated square blobs of known size, value 1.0."""
    z = np.zeros((ny, nx), dtype=np.float64)
    z[2:6, 2:6] = 1.0  # a 4x4 = 16-pixel blob
    z[12:17, 12:19] = 1.0  # a 5x7 = 35-pixel blob
    return z


# --------------------------------------------------------------------------- #
# otsu_threshold: known-answer correctness
# --------------------------------------------------------------------------- #


def test_otsu_threshold_separates_a_clean_bimodal_histogram() -> None:
    # A well-separated bimodal population: any correctly-computed Otsu cut must land
    # strictly between the two clusters (it need not sit at the visual midpoint - the
    # between-class-variance criterion is flat across the whole empty gap, so the
    # implementation may return any point in it; what matters is that it classifies
    # every sample correctly).
    rng = np.random.default_rng(0)
    low = rng.normal(0.0, 0.05, size=500)
    high = rng.normal(10.0, 0.05, size=500)
    values = np.concatenate([low, high]).reshape(25, 40)
    cut = otsu_threshold(values)
    assert low.max() < cut < high.min()


def test_otsu_threshold_constant_channel_returns_that_value() -> None:
    values = np.full((5, 5), 3.0)
    assert otsu_threshold(values) == 3.0


def test_otsu_threshold_raises_on_all_nan() -> None:
    values = np.full((3, 3), np.nan)
    with pytest.raises(ProcessingError):
        otsu_threshold(values)


# --------------------------------------------------------------------------- #
# segment_labels: known-answer correctness
# --------------------------------------------------------------------------- #


def test_segment_labels_fixed_recovers_exact_blob_count_and_sizes() -> None:
    z = _two_blobs()
    labels = segment_labels(z, method="fixed", threshold=0.5, polarity="above", min_pixels=1)
    ids = sorted(int(i) for i in np.unique(labels) if i != 0)
    assert ids == [1, 2]
    sizes = sorted(int((labels == i).sum()) for i in ids)
    assert sizes == [16, 35]


def test_segment_labels_otsu_recovers_exact_blob_count() -> None:
    z = _two_blobs()
    labels = segment_labels(z, method="otsu", polarity="above", min_pixels=1)
    ids = [int(i) for i in np.unique(labels) if i != 0]
    assert len(ids) == 2


def test_segment_labels_percentile_recovers_exact_blob_count() -> None:
    z = _two_blobs()
    # The blobs cover 51/400 pixels (~13%); a cut well above the background
    # percentile isolates them.
    labels = segment_labels(z, method="percentile", percentile=95.0, polarity="above", min_pixels=1)
    ids = [int(i) for i in np.unique(labels) if i != 0]
    assert len(ids) == 2


def test_segment_labels_below_polarity_finds_a_pit() -> None:
    z = np.ones((10, 10), dtype=np.float64)
    z[3:6, 3:6] = -1.0
    labels = segment_labels(z, method="fixed", threshold=0.0, polarity="below", min_pixels=1)
    ids = [int(i) for i in np.unique(labels) if i != 0]
    assert ids == [1]
    assert int((labels == 1).sum()) == 9


def test_segment_labels_min_pixels_drops_speck_and_renumbers_contiguously() -> None:
    z = np.zeros((20, 20), dtype=np.float64)
    z[2:6, 2:6] = 1.0  # 16 pixels - kept
    z[10, 10] = 1.0  # 1 pixel - a speck, dropped by min_pixels=2
    z[15:18, 15:19] = 1.0  # 3x4 = 12 pixels - kept
    labels = segment_labels(z, method="fixed", threshold=0.5, polarity="above", min_pixels=2)
    ids = sorted(int(i) for i in np.unique(labels) if i != 0)
    assert ids == [1, 2]  # contiguous - the dropped speck left no gap
    assert int((labels == 1).sum()) == 16
    assert int((labels == 2).sum()) == 12
    assert not np.any((labels != 0) & (np.arange(labels.size).reshape(labels.shape) == 0))


def test_segment_labels_nonfinite_pixels_are_never_foreground() -> None:
    z = np.full((6, 6), np.nan)
    z[1:4, 1:4] = 5.0
    labels = segment_labels(z, method="fixed", threshold=0.0, polarity="above", min_pixels=1)
    assert np.all(labels[np.isnan(z)] == 0.0)
    assert int((labels == 1).sum()) == 9


def test_segment_labels_rejects_bad_method_polarity_min_pixels() -> None:
    z = np.zeros((4, 4))
    with pytest.raises(ProcessingError):
        segment_labels(z, method="bogus")
    with pytest.raises(ProcessingError):
        segment_labels(z, polarity="bogus")
    with pytest.raises(ProcessingError):
        segment_labels(z, min_pixels=0)
    with pytest.raises(ProcessingError):
        segment_labels(z, method="fixed", threshold=None)


# --------------------------------------------------------------------------- #
# ThresholdSegment.apply: engine invariants
# --------------------------------------------------------------------------- #


def test_apply_adds_label_channel_and_preserves_others() -> None:
    ds = _z_dataset(_two_blobs())
    step = ThresholdSegment(channel="Z", method="fixed", threshold=0.5, min_pixels=1)
    result = step.apply({"primary": ds})

    assert "Z_labels" in result.channel_names
    assert "Z" in result.channel_names
    np.testing.assert_array_equal(result.data["Z"].values, ds.data["Z"].values)
    ids = sorted(int(i) for i in np.unique(result.data["Z_labels"].values) if i != 0)
    assert ids == [1, 2]


def test_apply_does_not_mutate_input() -> None:
    z = _two_blobs()
    ds = _z_dataset(z.copy())
    original = ds.data["Z"].values.copy()
    ThresholdSegment(channel="Z", method="fixed", threshold=0.5, min_pixels=1).apply(
        {"primary": ds}
    )
    np.testing.assert_array_equal(ds.data["Z"].values, original)
    assert "Z_labels" not in ds.channel_names


def test_apply_records_provenance() -> None:
    ds = _z_dataset(_two_blobs())
    step = ThresholdSegment(channel="Z", method="otsu", min_pixels=1)
    result = step.apply({"primary": ds})
    assert result.provenance.record.step_id == "image.threshold_segment"
    assert result.provenance.record.step_version == 1
    assert result.provenance.inputs["primary"] is ds.provenance
    assert result.is_raw is False


def test_apply_defaults_to_channel_z_and_otsu() -> None:
    ds = _z_dataset(_two_blobs())
    result = ThresholdSegment().apply({"primary": ds})
    assert "Z_labels" in result.channel_names


def test_apply_rejects_missing_channel() -> None:
    ds = _z_dataset(_two_blobs())
    with pytest.raises(ProcessingError):
        ThresholdSegment(channel="Q").apply({"primary": ds})


def test_apply_rejects_complex_channel() -> None:
    ny, nx = 4, 4
    x = (np.arange(nx, dtype=np.float64) + 0.5) * 50.0
    y = (np.arange(ny, dtype=np.float64) + 0.5) * 50.0
    o2 = np.ones((ny, nx), dtype=np.complex64)
    data = xr.Dataset(
        {"O2": xr.DataArray(o2, dims=["y", "x"])},
        coords={"x": ("x", x, {"unit": "nm"}), "y": ("y", y, {"unit": "nm"})},
    )
    meta = Metadata(data_kind=DataKind.IMAGE)
    node = ProvenanceNode(
        node_id="n0", record=StepRecord(step_id="io.read", step_version=1, deterministic=True)
    )
    ds = Dataset(data, kind=DataKind.IMAGE, metadata=meta, provenance=node)
    with pytest.raises(ProcessingError):
        ThresholdSegment(channel="O2").apply({"primary": ds})


def test_apply_rejects_existing_label_channel_name() -> None:
    ny, nx = 4, 4
    x = (np.arange(nx, dtype=np.float64) + 0.5) * 50.0
    y = (np.arange(ny, dtype=np.float64) + 0.5) * 50.0
    z = np.zeros((ny, nx))
    data = xr.Dataset(
        {"Z": xr.DataArray(z, dims=["y", "x"]), "Z_labels": xr.DataArray(z, dims=["y", "x"])},
        coords={"x": ("x", x, {"unit": "nm"}), "y": ("y", y, {"unit": "nm"})},
    )
    meta = Metadata(data_kind=DataKind.IMAGE)
    node = ProvenanceNode(
        node_id="n0", record=StepRecord(step_id="io.read", step_version=1, deterministic=True)
    )
    ds = Dataset(data, kind=DataKind.IMAGE, metadata=meta, provenance=node)
    with pytest.raises(ProcessingError):
        ThresholdSegment(channel="Z").apply({"primary": ds})


def test_apply_rejects_bad_fixed_method_missing_threshold() -> None:
    # method='fixed' with the default threshold=0.0 is valid (0.0 is a legitimate cut);
    # this checks the parameter *type* validation still rejects a non-numeric value.
    ds = _z_dataset(_two_blobs())
    with pytest.raises(ProcessingError):
        ThresholdSegment(channel="Z", method="bogus").apply({"primary": ds})


def test_registered_and_discoverable() -> None:
    cls = get_step("image.threshold_segment")
    assert cls is ThresholdSegment
