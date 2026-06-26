"""Unit tests for the core Dataset abstraction and capability derivation."""

from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

from snomniman.core import (
    Capability,
    ChannelInfo,
    DataKind,
    Dataset,
    DatasetError,
    Metadata,
    ProvenanceNode,
    StepRecord,
)


def _raw_node() -> ProvenanceNode:
    return ProvenanceNode(
        node_id="n0",
        record=StepRecord(step_id="io.read", step_version=1, deterministic=True),
    )


def _synthetic_dataset() -> Dataset:
    ny, nx = 4, 3
    y = np.arange(ny, dtype=float) * 10.0
    x = np.arange(nx, dtype=float) * 10.0
    amp = np.linspace(1.0, 2.0, ny * nx, dtype=np.float32).reshape(ny, nx)
    phase = np.linspace(-1.0, 1.0, ny * nx, dtype=np.float32).reshape(ny, nx)
    o2 = (amp * np.exp(1j * phase)).astype(np.complex64)
    o3 = (amp * np.exp(1j * (phase * 0.5))).astype(np.complex64)
    r_o2 = (amp * np.exp(1j * phase)).astype(np.complex64)
    m1 = (amp * np.exp(1j * phase)).astype(np.complex64)
    z = (amp * 100.0).astype(np.float32)
    data = xr.Dataset(
        {
            "O2": (("y", "x"), o2),
            "O3": (("y", "x"), o3),
            "R_O2": (("y", "x"), r_o2),
            "M1": (("y", "x"), m1),
            "Z": (("y", "x"), z),
        },
        coords={"x": ("x", x), "y": ("y", y)},
    )
    channels = (
        ChannelInfo("O2", "optical", "signal", "complex64", harmonic=2),
        ChannelInfo("O3", "optical", "signal", "complex64", harmonic=3),
        ChannelInfo("R_O2", "optical", "reference", "complex64", harmonic=2),
        ChannelInfo("M1", "mechanical", "signal", "complex64", harmonic=1),
        ChannelInfo("Z", "topography", "signal", "float32", value_unit="nm"),
    )
    md = Metadata(data_kind=DataKind.IMAGE, channels=channels)
    return Dataset(data, kind=DataKind.IMAGE, metadata=md, provenance=_raw_node())


def test_kind_and_is_raw() -> None:
    ds = _synthetic_dataset()
    assert ds.kind is DataKind.IMAGE
    assert ds.is_raw is True


def test_capabilities_derived() -> None:
    ds = _synthetic_dataset()
    caps = ds.capabilities
    assert Capability.SPATIAL_2D in caps
    assert Capability.COMPLEX_OPTICAL in caps
    assert Capability.COMPLEX_MECHANICAL in caps
    assert Capability.TOPOGRAPHY in caps
    assert Capability.REFERENCE in caps
    assert Capability.MULTI_HARMONIC in caps  # O2 and O3
    assert Capability.SPECTRAL not in caps
    assert ds.has_capability(Capability.SPATIAL_2D)


def test_channel_names_and_filtering() -> None:
    ds = _synthetic_dataset()
    assert set(ds.channel_names) == {"O2", "O3", "R_O2", "M1", "Z"}
    assert set(ds.channels(role="reference")) == {"R_O2"}
    assert set(ds.channels(kind="optical")) == {"O2", "O3", "R_O2"}
    assert ds.channels(role="signal", kind="topography") == ["Z"]


def test_amplitude_and_phase_views_are_consistent() -> None:
    ds = _synthetic_dataset()
    o2 = ds.channel("O2").values
    np.testing.assert_allclose(ds.amplitude("O2").values, np.abs(o2), rtol=1e-6)
    np.testing.assert_allclose(ds.phase("O2").values, np.angle(o2), rtol=1e-6)
    assert ds.amplitude("O2").attrs["unit"] == "a.u."
    assert ds.phase("O2").attrs["unit"] == "rad"


def test_amplitude_phase_reject_real_channels() -> None:
    ds = _synthetic_dataset()
    assert ds.is_complex("O2")
    assert not ds.is_complex("Z")
    with pytest.raises(DatasetError, match="not complex"):
        ds.amplitude("Z")
    with pytest.raises(DatasetError, match="not complex"):
        ds.phase("Z")


def test_unknown_channel_raises() -> None:
    ds = _synthetic_dataset()
    with pytest.raises(DatasetError, match="no such channel"):
        ds.channel("nope")


def test_raw_data_is_immutable() -> None:
    ds = _synthetic_dataset()
    with pytest.raises(ValueError, match=r"read-only|assignment"):
        ds.channel("Z").data[0, 0] = 999.0
    with pytest.raises(ValueError, match=r"read-only|assignment"):
        ds.coordinate("x").data[0] = -1.0


def test_amplitude_view_does_not_mutate_source() -> None:
    ds = _synthetic_dataset()
    before = ds.channel("O2").values.copy()
    _ = ds.amplitude("O2") + 5.0  # operating on the view must not touch storage
    np.testing.assert_array_equal(ds.channel("O2").values, before)


def test_rejects_non_xarray() -> None:
    md = Metadata(data_kind=DataKind.IMAGE)
    with pytest.raises(DatasetError, match=r"xarray\.Dataset"):
        Dataset(object(), kind=DataKind.IMAGE, metadata=md, provenance=_raw_node())  # type: ignore[arg-type]
