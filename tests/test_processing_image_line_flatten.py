"""Tests for snomniman.processing.image.line_flatten - line-by-line flattening.

Covers (Rule 6 + the processing-engine invariants):
- Known-answer correctness of the ``flatten_lines`` algorithm: pure per-line
  offsets removed exactly (median/mean/polynomial), per-line offset+slope removed
  by polynomial order 1, a feature with a known per-line baseline recovered, and
  NaN-robustness.
- A representative combined synthetic scan (global tilt + line offsets + a genuine
  feature): the striping collapses while the feature's contrast survives.
- LineFlatten.apply: only the target channel changes; input immutability (values
  unchanged, arrays still frozen); the result is a new object.
- Provenance: step_id, version, params, and input node recorded; result not raw.
- Defaults and parameter validation (bad method, bad order, missing/complex channel).
- Registry discovery, and a real-measurement (CdO) comparison of raw / plane-leveled
  / line-flattened topography (skips when the sample data is absent).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import numpy.typing as npt
import pytest
import xarray as xr

from snomniman.core import DataKind, Dataset, Metadata, ProvenanceNode, StepRecord
from snomniman.core.exceptions import ProcessingError
from snomniman.processing import get_step
from snomniman.processing.image.line_flatten import LineFlatten, flatten_lines
from snomniman.processing.image.plane_level import PlaneLevel

# --------------------------------------------------------------------------- #
# Test-local dataset helpers (mirroring tests/test_processing_image.py)
# --------------------------------------------------------------------------- #


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


# --------------------------------------------------------------------------- #
# flatten_lines: known-answer correctness
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("method", ["median", "mean", "polynomial"])
def test_pure_line_offsets_removed_to_zero(method: str) -> None:
    """A scan that is *only* per-line constants flattens to all-zeros (every method)."""
    offsets = np.array([1.0, 5.0, -3.0, 12.0])[:, None]
    z = np.tile(offsets, (1, 6))  # each row a distinct constant, no x-structure
    out = flatten_lines(z, method=method, order=1)
    np.testing.assert_allclose(out, 0.0, atol=1e-9)


def test_polynomial_order1_removes_per_line_offset_and_slope() -> None:
    """Each line an independent a*x + c is removed exactly by polynomial order 1."""
    nx = 8
    x = np.arange(nx, dtype=np.float64)
    rows = [2.0 * x + 10.0, -1.0 * x - 4.0, 0.5 * x + 100.0]
    z = np.vstack(rows)
    out = flatten_lines(z, method="polynomial", order=1)
    np.testing.assert_allclose(out, 0.0, atol=1e-9)


def test_polynomial_order2_removes_per_line_quadratic() -> None:
    """A per-line quadratic baseline is removed by polynomial order 2."""
    nx = 12
    x = np.arange(nx, dtype=np.float64)
    z = np.vstack([0.3 * x**2 - 2.0 * x + 7.0, -0.1 * x**2 + x - 5.0])
    out = flatten_lines(z, method="polynomial", order=2)
    np.testing.assert_allclose(out, 0.0, atol=1e-8)


def test_mean_preserves_feature_shape_and_removes_offset() -> None:
    """A common x-feature plus per-line offsets: mean leaves feature - mean(feature)."""
    x = np.arange(6, dtype=np.float64)
    feature = np.sin(x)  # identical in every line
    offsets = np.array([0.0, 4.0, -2.5])[:, None]
    z = feature[None, :] + offsets
    out = flatten_lines(z, method="mean")
    expected_row = feature - feature.mean()  # offset removed, shape preserved
    for row in out:
        np.testing.assert_allclose(row, expected_row, atol=1e-9)


def test_median_recovers_feature_with_known_baseline() -> None:
    """Median removes the per-line median; with a zero-median feature it is recovered."""
    # An odd-length antisymmetric feature has median exactly 0, so the median method
    # removes only the injected per-line offset and returns the feature unchanged.
    feature = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])  # median 0
    offsets = np.array([10.0, -7.0, 3.0])[:, None]
    z = feature[None, :] + offsets
    out = flatten_lines(z, method="median")
    for row in out:
        np.testing.assert_allclose(row, feature, atol=1e-9)


def test_all_invalid_line_is_left_unchanged() -> None:
    """A line with no finite pixels is passed through (no crash, still NaN)."""
    z = np.array([[np.nan, np.nan, np.nan, np.nan], [1.0, 2.0, 3.0, 4.0]])
    out = flatten_lines(z, method="median")
    assert np.all(np.isnan(out[0]))
    # The finite line is centered on its median (median of 1..4 is 2.5).
    np.testing.assert_allclose(out[1], np.array([1.0, 2.0, 3.0, 4.0]) - 2.5, atol=1e-9)


def test_partial_invalid_line_uses_finite_pixels() -> None:
    """The baseline of a line is estimated from its finite pixels only."""
    z = np.array([[1.0, 3.0, np.nan, 5.0]])  # finite median = 3.0
    out = flatten_lines(z, method="median")
    np.testing.assert_allclose(out[0], np.array([-2.0, 0.0, np.nan, 2.0]), atol=1e-9)


def test_flatten_lines_does_not_mutate_input() -> None:
    z = np.array([[1.0, 1.0, 1.0], [9.0, 9.0, 9.0]])
    original = z.copy()
    flatten_lines(z, method="median")
    np.testing.assert_array_equal(z, original)


def test_flatten_lines_rejects_bad_method() -> None:
    with pytest.raises(ProcessingError, match="method must be one of"):
        flatten_lines(np.zeros((2, 2)), method="bogus")


def test_flatten_lines_rejects_non_2d() -> None:
    with pytest.raises(ProcessingError, match="2-D array"):
        flatten_lines(np.zeros((2, 2, 2)))


# --------------------------------------------------------------------------- #
# A representative combined scan: striping removed, real feature preserved
# --------------------------------------------------------------------------- #


def test_combined_scan_removes_striping_keeps_feature() -> None:
    """Global tilt + per-line offsets + a localized feature.

    Line flattening (median) should collapse the line-to-line offset variation
    while preserving the feature's internal peak-to-background contrast.
    """
    rng = np.random.default_rng(0)
    ny, nx = 40, 40
    x = np.arange(nx, dtype=np.float64)
    y = np.arange(ny, dtype=np.float64)
    xx, yy = np.meshgrid(x, y)

    tilt = 0.05 * xx + 0.02 * yy
    line_offsets = rng.normal(0.0, 3.0, size=ny)[:, None]  # the striping
    feature = np.zeros((ny, nx))
    feature[15:25, 15:25] = 10.0  # a clear raised square
    z = tilt + line_offsets + feature

    flattened = flatten_lines(z, method="median")

    # The striping is characterised by the spread of per-line medians: it must
    # shrink dramatically (median method drives each line's median to ~0).
    raw_line_median_spread = float(np.std(np.median(z, axis=1)))
    flat_line_median_spread = float(np.std(np.median(flattened, axis=1)))
    assert flat_line_median_spread < 0.05 * raw_line_median_spread

    # The feature survives: its raised square is still well above the surround.
    feature_level = float(np.median(flattened[15:25, 15:25]))
    background_level = float(np.median(flattened[:10, :10]))
    assert feature_level - background_level > 8.0  # near the injected 10.0


# --------------------------------------------------------------------------- #
# LineFlatten.apply: correctness, channel isolation, immutability
# --------------------------------------------------------------------------- #


def test_apply_removes_pure_line_offsets() -> None:
    z = np.tile(np.array([2.0, -6.0, 11.0])[:, None], (1, 5))
    result = LineFlatten(channel="Z").apply({"primary": _z_dataset(z)})
    residual = np.asarray(result.channel("Z").values, dtype=np.float64)
    np.testing.assert_allclose(residual, 0.0, atol=1e-9)


def test_non_target_channels_unchanged(synthetic_dataset: Dataset) -> None:
    before = {
        name: synthetic_dataset.channel(name).values.copy()
        for name in synthetic_dataset.channel_names
        if name != "Z"
    }
    result = LineFlatten(channel="Z").apply({"primary": synthetic_dataset})
    for name, arr in before.items():
        np.testing.assert_array_equal(result.channel(name).values, arr, err_msg=name)


def test_input_z_values_unchanged_after_apply(synthetic_dataset: Dataset) -> None:
    original_z = synthetic_dataset.channel("Z").values.copy()
    LineFlatten(channel="Z").apply({"primary": synthetic_dataset})
    np.testing.assert_array_equal(synthetic_dataset.channel("Z").values, original_z)


def test_input_arrays_remain_frozen_after_apply(synthetic_dataset: Dataset) -> None:
    LineFlatten(channel="Z").apply({"primary": synthetic_dataset})
    for name in synthetic_dataset.channel_names:
        arr = synthetic_dataset.channel(name).data
        assert isinstance(arr, np.ndarray)
        assert not arr.flags.writeable, f"{name} is writable after apply"


def test_result_is_a_different_object(synthetic_dataset: Dataset) -> None:
    result = LineFlatten(channel="Z").apply({"primary": synthetic_dataset})
    assert result is not synthetic_dataset


def test_dtype_preserved(synthetic_dataset: Dataset) -> None:
    result = LineFlatten(channel="Z").apply({"primary": synthetic_dataset})
    assert result.channel("Z").dtype == synthetic_dataset.channel("Z").dtype


# --------------------------------------------------------------------------- #
# LineFlatten.apply: provenance
# --------------------------------------------------------------------------- #


def test_provenance_step_id(synthetic_dataset: Dataset) -> None:
    result = LineFlatten(channel="Z").apply({"primary": synthetic_dataset})
    assert result.provenance.record.step_id == "image.line_flatten"


def test_provenance_step_version(synthetic_dataset: Dataset) -> None:
    result = LineFlatten(channel="Z").apply({"primary": synthetic_dataset})
    assert result.provenance.record.step_version == 1


def test_provenance_params_recorded(synthetic_dataset: Dataset) -> None:
    result = LineFlatten(channel="Z", method="polynomial", order=2).apply(
        {"primary": synthetic_dataset}
    )
    assert result.provenance.record.params == {
        "channel": "Z",
        "method": "polynomial",
        "order": 2,
    }


def test_provenance_input_node_referenced(synthetic_dataset: Dataset) -> None:
    result = LineFlatten(channel="Z").apply({"primary": synthetic_dataset})
    assert result.provenance.inputs["primary"] is synthetic_dataset.provenance


def test_result_is_not_raw(synthetic_dataset: Dataset) -> None:
    result = LineFlatten(channel="Z").apply({"primary": synthetic_dataset})
    assert not result.is_raw


def test_source_is_none(synthetic_dataset: Dataset) -> None:
    result = LineFlatten(channel="Z").apply({"primary": synthetic_dataset})
    assert result.source is None


# --------------------------------------------------------------------------- #
# Defaults and parameter validation
# --------------------------------------------------------------------------- #


def test_default_params() -> None:
    step = LineFlatten()
    assert step.params == {"channel": "Z", "method": "median", "order": 1}


def test_bad_method_raises() -> None:
    with pytest.raises(ProcessingError, match=r"one of \['median', 'mean', 'polynomial'\]"):
        LineFlatten(method="bogus")


def test_bad_order_raises() -> None:
    with pytest.raises(ProcessingError, match=r"one of \[1, 2, 3\]"):
        LineFlatten(order=5)


def test_missing_channel_raises(synthetic_dataset: Dataset) -> None:
    with pytest.raises(ProcessingError, match="not found"):
        LineFlatten(channel="NOPE").apply({"primary": synthetic_dataset})


def test_complex_channel_raises(synthetic_dataset: Dataset) -> None:
    with pytest.raises(ProcessingError, match="is complex"):
        LineFlatten(channel="O2").apply({"primary": synthetic_dataset})


def test_unknown_param_raises() -> None:
    with pytest.raises(ProcessingError, match="unknown parameter"):
        LineFlatten(direction="horizontal")


# --------------------------------------------------------------------------- #
# Registry discovery
# --------------------------------------------------------------------------- #


def test_line_flatten_registered() -> None:
    assert get_step("image.line_flatten") is LineFlatten


# --------------------------------------------------------------------------- #
# Real-measurement validation (CdO) - skips when the sample data is absent
# --------------------------------------------------------------------------- #


def test_real_measurement_line_flatten_vs_plane_level(sample_measurement_dir: Path) -> None:
    """On the real CdO topography, line flattening and plane leveling both reduce
    line-to-line baseline spread, never mutate the raw, and are distinct operations."""
    from snomniman.io import read_neasnom_measurement

    ds = read_neasnom_measurement(sample_measurement_dir)
    raw_z = np.asarray(ds.channel("Z").values, dtype=np.float64).copy()

    line_flat = LineFlatten(channel="Z", method="median").apply({"primary": ds})
    plane = PlaneLevel(channel="Z", order=1).apply({"primary": ds})

    lf_z = np.asarray(line_flat.channel("Z").values, dtype=np.float64)
    pl_z = np.asarray(plane.channel("Z").values, dtype=np.float64)

    # Per-line baseline spread (std of per-row medians): line flattening removes it
    # to ~0 by construction; plane leveling only partially (it cannot touch
    # independent per-line offsets) - which is exactly why the two operations differ.
    def line_spread(a: npt.NDArray[np.float64]) -> float:
        return float(np.nanstd(np.nanmedian(a, axis=1)))

    assert line_spread(lf_z) < line_spread(raw_z)
    assert line_spread(lf_z) < 1e-6  # median method zeroes each line's median
    # The two derivations are genuinely different results.
    assert not np.allclose(lf_z, pl_z)
    # The raw measurement is never mutated.
    np.testing.assert_array_equal(ds.channel("Z").values, raw_z)
    assert line_flat.provenance.record.step_id == "image.line_flatten"
