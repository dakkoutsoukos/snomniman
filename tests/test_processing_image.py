"""Tests for snomniman.processing.image - plane leveling and the fit_surface algorithm.

Covers:
- Known-answer correctness (Rule 6): synthetic planes / paraboloids / cubics
  with analytically-known residuals after subtraction.
- Only the target channel changes; all other channels are bit-identical to input.
- Input Dataset immutability: values unchanged and arrays still frozen after apply.
- Provenance: step_id, version, params, and input node all recorded correctly.
- Parameter validation: order range (1..3 only), missing channel, complex channel.
- Registry: ``get_step("image.plane_level")`` returns PlaneLevel.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt
import pytest
import xarray as xr

from snomniman.core import DataKind, Dataset, Metadata, ProvenanceNode, StepRecord
from snomniman.core.exceptions import ProcessingError
from snomniman.processing import get_step
from snomniman.processing.image.plane_level import PlaneLevel, fit_surface

# --------------------------------------------------------------------------- #
# Test-local dataset helpers
# --------------------------------------------------------------------------- #


def _z_dataset(
    z: npt.NDArray[np.float64],
    x: npt.NDArray[np.float64],
    y: npt.NDArray[np.float64],
) -> Dataset:
    """Minimal Dataset with one real-valued 'Z' channel for algorithm tests."""
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


def _tilted_plane(nx: int, ny: int, ax: float, ay: float, c: float) -> tuple[
    npt.NDArray[np.float64], npt.NDArray[np.float64], npt.NDArray[np.float64]
]:
    x = np.linspace(25.0, 975.0, nx)
    y = np.linspace(25.0, 975.0, ny)
    xx, yy = np.meshgrid(x, y)
    z = ax * xx + ay * yy + c
    return z.astype(np.float64), x, y


# --------------------------------------------------------------------------- #
# fit_surface: known-answer correctness
# --------------------------------------------------------------------------- #


def test_fit_surface_plane_exact() -> None:
    """fit_surface(order=1) recovers a pure tilted plane with residual ≈ 0."""
    z, x, y = _tilted_plane(20, 25, ax=2.5, ay=1.3, c=50.0)
    surface = fit_surface(z, x, y, order=1)
    np.testing.assert_allclose(z - surface, 0.0, atol=1e-8)


def test_fit_surface_paraboloid_exact() -> None:
    """fit_surface(order=2) recovers a pure paraboloid with residual ≈ 0."""
    nx, ny = 20, 20
    x = np.linspace(25.0, 975.0, nx)
    y = np.linspace(25.0, 975.0, ny)
    xx, yy = np.meshgrid(x, y)
    z = (0.001 * xx**2 + 0.002 * yy**2 + 1.5 * xx + 0.5 * yy + 10.0).astype(np.float64)
    surface = fit_surface(z, x, y, order=2)
    np.testing.assert_allclose(z - surface, 0.0, atol=1e-6)


def test_fit_surface_cubic_exact() -> None:
    """fit_surface(order=3) recovers a pure cubic surface with residual ≈ 0."""
    nx, ny = 20, 20
    x = np.linspace(0.0, 100.0, nx)
    y = np.linspace(0.0, 100.0, ny)
    xx, yy = np.meshgrid(x, y)
    z = (0.0001 * xx**3 + 0.0001 * yy**3 + 0.01 * xx**2 + xx + yy + 5.0).astype(np.float64)
    surface = fit_surface(z, x, y, order=3)
    np.testing.assert_allclose(z - surface, 0.0, atol=1e-5)


# --------------------------------------------------------------------------- #
# PlaneLevel.apply: correctness
# --------------------------------------------------------------------------- #


def test_plane_level_removes_tilt_analytically() -> None:
    """PlaneLevel (order=1) subtracts an exact plane; residual ≈ 0 machine precision."""
    z, x, y = _tilted_plane(20, 25, ax=2.5, ay=1.3, c=50.0)
    ds = _z_dataset(z, x, y)
    result = PlaneLevel(channel="Z", order=1).apply({"primary": ds})
    residual = np.asarray(result.channel("Z").values, dtype=np.float64)
    np.testing.assert_allclose(residual, 0.0, atol=1e-8)


def test_plane_level_paraboloid_analytically() -> None:
    """PlaneLevel (order=2) subtracts a paraboloid; residual ≈ 0."""
    nx, ny = 20, 20
    x = np.linspace(25.0, 975.0, nx)
    y = np.linspace(25.0, 975.0, ny)
    xx, yy = np.meshgrid(x, y)
    z = (0.001 * xx**2 + 0.002 * yy**2 + 1.5 * xx + 10.0).astype(np.float64)
    ds = _z_dataset(z, x, y)
    result = PlaneLevel(channel="Z", order=2).apply({"primary": ds})
    residual = np.asarray(result.channel("Z").values, dtype=np.float64)
    np.testing.assert_allclose(residual, 0.0, atol=1e-6)


# --------------------------------------------------------------------------- #
# PlaneLevel.apply: channel isolation + immutability
# --------------------------------------------------------------------------- #


def test_non_target_channels_are_unchanged(synthetic_dataset: Dataset) -> None:
    """Only 'Z' changes; all other channels are bit-identical to the input."""
    before = {
        name: synthetic_dataset.channel(name).values.copy()
        for name in synthetic_dataset.channel_names
        if name != "Z"
    }
    result = PlaneLevel(channel="Z").apply({"primary": synthetic_dataset})
    for name, arr in before.items():
        np.testing.assert_array_equal(result.channel(name).values, arr, err_msg=name)


def test_target_channel_z_values_differ(synthetic_dataset: Dataset) -> None:
    """The leveled Z values are different from the original (tilt was present)."""
    original_z = synthetic_dataset.channel("Z").values.copy()
    result = PlaneLevel(channel="Z").apply({"primary": synthetic_dataset})
    # After leveling a non-flat Z, values are not all identical to the original.
    assert not np.allclose(result.channel("Z").values, original_z)


def test_input_z_values_unchanged_after_apply(synthetic_dataset: Dataset) -> None:
    """apply() never mutates the input Dataset's values."""
    original_z = synthetic_dataset.channel("Z").values.copy()
    PlaneLevel(channel="Z").apply({"primary": synthetic_dataset})
    np.testing.assert_array_equal(synthetic_dataset.channel("Z").values, original_z)


def test_input_arrays_remain_frozen_after_apply(synthetic_dataset: Dataset) -> None:
    """apply() leaves the input arrays read-only."""
    PlaneLevel(channel="Z").apply({"primary": synthetic_dataset})
    for name in synthetic_dataset.channel_names:
        arr = synthetic_dataset.channel(name).data
        assert isinstance(arr, np.ndarray)
        assert not arr.flags.writeable, f"{name} is writable after apply"


def test_result_is_a_different_object(synthetic_dataset: Dataset) -> None:
    result = PlaneLevel(channel="Z").apply({"primary": synthetic_dataset})
    assert result is not synthetic_dataset


# --------------------------------------------------------------------------- #
# PlaneLevel.apply: provenance
# --------------------------------------------------------------------------- #


def test_provenance_step_id(synthetic_dataset: Dataset) -> None:
    result = PlaneLevel(channel="Z").apply({"primary": synthetic_dataset})
    assert result.provenance.record.step_id == "image.plane_level"


def test_provenance_step_version(synthetic_dataset: Dataset) -> None:
    result = PlaneLevel(channel="Z").apply({"primary": synthetic_dataset})
    assert result.provenance.record.step_version == 1


def test_provenance_params_recorded(synthetic_dataset: Dataset) -> None:
    result = PlaneLevel(channel="Z", order=2).apply({"primary": synthetic_dataset})
    assert result.provenance.record.params == {"channel": "Z", "order": 2}


def test_provenance_input_node_referenced(synthetic_dataset: Dataset) -> None:
    result = PlaneLevel(channel="Z").apply({"primary": synthetic_dataset})
    assert "primary" in result.provenance.inputs
    assert result.provenance.inputs["primary"] is synthetic_dataset.provenance


def test_result_is_not_raw(synthetic_dataset: Dataset) -> None:
    result = PlaneLevel(channel="Z").apply({"primary": synthetic_dataset})
    assert not result.is_raw


def test_source_is_none(synthetic_dataset: Dataset) -> None:
    result = PlaneLevel(channel="Z").apply({"primary": synthetic_dataset})
    assert result.source is None


# --------------------------------------------------------------------------- #
# PlaneLevel: default parameters
# --------------------------------------------------------------------------- #


def test_default_channel_is_z() -> None:
    step = PlaneLevel()
    assert step.params["channel"] == "Z"


def test_default_order_is_1() -> None:
    step = PlaneLevel()
    assert step.params["order"] == 1


# --------------------------------------------------------------------------- #
# PlaneLevel: parameter validation
# --------------------------------------------------------------------------- #


def test_order_0_raises() -> None:
    with pytest.raises(ProcessingError, match="order must be 1, 2, or 3"):
        PlaneLevel(order=0)


def test_order_4_raises() -> None:
    with pytest.raises(ProcessingError, match="order must be 1, 2, or 3"):
        PlaneLevel(order=4)


def test_missing_channel_raises(synthetic_dataset: Dataset) -> None:
    step = PlaneLevel(channel="DOES_NOT_EXIST")
    with pytest.raises(ProcessingError, match="not found"):
        step.apply({"primary": synthetic_dataset})


def test_complex_channel_raises(synthetic_dataset: Dataset) -> None:
    step = PlaneLevel(channel="O2")  # O2 is complex in the synthetic dataset
    with pytest.raises(ProcessingError, match="is complex"):
        step.apply({"primary": synthetic_dataset})


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #


def test_plane_level_registered() -> None:
    """get_step("image.plane_level") must return PlaneLevel after package import."""
    assert get_step("image.plane_level") is PlaneLevel
