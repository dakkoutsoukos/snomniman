"""Tests for spectrum.savgol_smooth.

The known-answer case exploits Savitzky-Golay's own defining property: with
``mode="interp"`` (scipy's default, used here) the filter reproduces a
polynomial of degree <= ``polyorder`` **exactly**, everywhere including the
edges (the edge polynomial is fit and evaluated there, not padded/reflected).
A noisy version of the same polynomial demonstrates the filter actually
reduces noise relative to the raw signal - the qualitative property the figure
that commissioned this operation relies on ("savgol mean").
"""

from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

import snomniman.processing.spectrum  # noqa: F401  (registers spectrum ops, incl. savgol_smooth)
from snomniman.core import (
    Capability,
    ChannelInfo,
    DataKind,
    Dataset,
    Metadata,
    ProvenanceNode,
    StepRecord,
)
from snomniman.core.exceptions import ProcessingError
from snomniman.processing import get_step

_WN = 5920.0 + np.arange(41, dtype=np.float64)


def _raw_node(node_id: str = "n0") -> ProvenanceNode:
    return ProvenanceNode(
        node_id=node_id, record=StepRecord(step_id="io.read", step_version=1, deterministic=True)
    )


def _spectrum_dataset(values: np.ndarray, *, extra: dict[str, np.ndarray] | None = None) -> Dataset:
    """A single-position SPECTRUM Dataset with a real 'O2_ratio' channel (+ optional extras)."""
    data_vars = {"O2_ratio": ("wavenumber", values)}
    channels = [ChannelInfo("O2_ratio", "optical", "signal", "float64", value_unit="a.u.")]
    for name, extra_values in (extra or {}).items():
        data_vars[name] = ("wavenumber", extra_values)
        channels.append(ChannelInfo(name, "optical", "signal", "float64", value_unit="a.u."))
    data = xr.Dataset(
        data_vars,
        coords={"wavenumber": ("wavenumber", _WN, {"unit": "cm-1", "long_name": "wavenumber"})},
    )
    metadata = Metadata(data_kind=DataKind.SPECTRUM, channels=tuple(channels))
    return Dataset(data, kind=DataKind.SPECTRUM, metadata=metadata, provenance=_raw_node())


def _smooth(ds: Dataset, **params: object) -> Dataset:
    return get_step("spectrum.savgol_smooth")(**params).apply({"primary": ds})


def _quadratic() -> np.ndarray:
    t = np.arange(_WN.size, dtype=np.float64) - _WN.size / 2.0
    return 0.5 * t**2 - 3.0 * t + 7.0


# -- science: known-answer smoothing ------------------------------------------ #


def test_reproduces_polynomial_exactly() -> None:
    poly = _quadratic()
    ds = _spectrum_dataset(poly)
    result = _smooth(ds, channel="O2_ratio", window_length=9, polyorder=2)
    np.testing.assert_allclose(result.channel("O2_ratio").values, poly, atol=1e-9)


def test_reduces_noise_relative_to_raw() -> None:
    poly = _quadratic()
    rng = np.random.default_rng(0)
    noisy = poly + rng.normal(scale=0.5, size=poly.size)
    ds = _spectrum_dataset(noisy)
    result = _smooth(ds, channel="O2_ratio", window_length=11, polyorder=2)
    smoothed = np.asarray(result.channel("O2_ratio").values)
    raw_error = np.sqrt(np.mean((noisy - poly) ** 2))
    smoothed_error = np.sqrt(np.mean((smoothed - poly) ** 2))
    assert smoothed_error < raw_error


def test_other_channels_preserved() -> None:
    poly = _quadratic()
    extra = np.linspace(0.0, 1.0, poly.size)
    ds = _spectrum_dataset(poly, extra={"O3_ratio": extra})
    result = _smooth(ds, channel="O2_ratio", window_length=9, polyorder=2)
    np.testing.assert_array_equal(result.channel("O3_ratio").values, extra)


def test_input_not_mutated() -> None:
    poly = _quadratic()
    ds = _spectrum_dataset(poly)
    before = np.array(ds.channel("O2_ratio").values, copy=True)
    _smooth(ds, channel="O2_ratio", window_length=9, polyorder=2)
    np.testing.assert_array_equal(ds.channel("O2_ratio").values, before)


# -- parameter / precondition validation -------------------------------------- #


def test_missing_channel_is_rejected() -> None:
    ds = _spectrum_dataset(_quadratic())
    with pytest.raises(ProcessingError, match="not found"):
        _smooth(ds, channel="nope", window_length=9)


def test_complex_channel_is_rejected() -> None:
    values = (1.0 + 0j) * np.ones(_WN.size, dtype=np.complex64)
    data = xr.Dataset(
        {"O2": ("wavenumber", values)},
        coords={"wavenumber": ("wavenumber", _WN)},
    )
    metadata = Metadata(
        data_kind=DataKind.SPECTRUM,
        channels=(ChannelInfo("O2", "optical", "signal", "complex64", amplitude_unit="a.u."),),
    )
    ds = Dataset(data, kind=DataKind.SPECTRUM, metadata=metadata, provenance=_raw_node())
    with pytest.raises(ProcessingError, match="complex"):
        _smooth(ds, channel="O2", window_length=9)


def test_even_window_length_is_rejected() -> None:
    ds = _spectrum_dataset(_quadratic())
    with pytest.raises(ProcessingError, match="odd"):
        _smooth(ds, channel="O2_ratio", window_length=10)


def test_polyorder_must_be_less_than_window_length() -> None:
    ds = _spectrum_dataset(_quadratic())
    with pytest.raises(ProcessingError, match="polyorder"):
        _smooth(ds, channel="O2_ratio", window_length=5, polyorder=5)


def test_window_length_exceeding_axis_is_rejected() -> None:
    ds = _spectrum_dataset(_quadratic())
    with pytest.raises(ProcessingError, match="exceeds"):
        _smooth(ds, channel="O2_ratio", window_length=999)


def test_default_polyorder() -> None:
    ds = _spectrum_dataset(_quadratic())
    result = _smooth(ds, channel="O2_ratio", window_length=9)  # polyorder omitted
    assert result.channel("O2_ratio").values.shape == (_WN.size,)


def test_required_capabilities() -> None:
    assert get_step("spectrum.savgol_smooth").required_capabilities == (Capability.SPECTRAL,)
