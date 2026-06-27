"""Tests for the second-generation image operations: reference_normalize, phase_unwrap, crop.

Each is validated against a known answer (Rule 6): analytical identities for
normalization, an analytical wrapped ramp for unwrapping, and exact sub-region
equality for cropping. Immutability and provenance are checked for every op.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt
import pytest
import xarray as xr

# Importing the sub-package registers every image operation.
import snomniman.processing.image  # noqa: F401
from snomniman.core import (
    Capability,
    ChannelInfo,
    Conventions,
    DataKind,
    Dataset,
    Metadata,
    ProvenanceNode,
    ScanInfo,
    StepRecord,
)
from snomniman.core.exceptions import ProcessingError
from snomniman.processing import get_step
from snomniman.processing.image.crop import Crop
from snomniman.processing.image.phase_unwrap import PhaseUnwrap, unwrap_2d
from snomniman.processing.image.reference_normalize import ReferenceNormalize


def _node() -> ProvenanceNode:
    return ProvenanceNode(
        node_id="n0",
        record=StepRecord(step_id="io.read", step_version=1, deterministic=True),
    )


# --------------------------------------------------------------------------- #
# image.reference_normalize
# --------------------------------------------------------------------------- #


def test_reference_normalize_is_registered() -> None:
    assert get_step("image.reference_normalize") is ReferenceNormalize
    assert ReferenceNormalize.required_capabilities == (
        Capability.COMPLEX_OPTICAL,
        Capability.REFERENCE,
    )


def test_reference_normalize_divides_by_reference(synthetic_dataset: Dataset) -> None:
    result = ReferenceNormalize().apply({"primary": synthetic_dataset})
    o2 = np.asarray(synthetic_dataset.channel("O2").values)
    r = np.asarray(synthetic_dataset.channel("R_O2").values)
    norm = np.asarray(result.channel("O2").values)
    # (O / R) * R == O to (complex64) precision.
    np.testing.assert_allclose(norm * r, o2, rtol=1e-5, atol=1e-5)
    # Normalized phase is the difference of the input phases.
    expected_phase = np.angle(o2) - np.angle(r)
    got_phase = np.angle(norm)
    np.testing.assert_allclose(
        np.angle(np.exp(1j * (got_phase - expected_phase))), 0.0, atol=1e-5
    )


def test_reference_normalize_marks_state_and_phase_reference(synthetic_dataset: Dataset) -> None:
    result = ReferenceNormalize().apply({"primary": synthetic_dataset})
    info = {c.canonical: c for c in result.metadata.channels}
    assert info["O2"].state == "normalized"
    assert info["R_O2"].state == "raw"  # reference preserved
    assert result.metadata.conventions.phase_reference is not None


def test_reference_normalize_provenance_and_immutability(synthetic_dataset: Dataset) -> None:
    before = np.asarray(synthetic_dataset.channel("O2").values).copy()
    result = ReferenceNormalize().apply({"primary": synthetic_dataset})
    assert result.provenance.record.step_id == "image.reference_normalize"
    assert result is not synthetic_dataset
    np.testing.assert_array_equal(synthetic_dataset.channel("O2").values, before)


def test_reference_normalize_requires_a_pair() -> None:
    # An optical signal channel with no matching reference -> error.
    data = xr.Dataset(
        {"O2": (("y", "x"), np.ones((2, 2), dtype=np.complex64))},
        coords={"x": ("x", [0.0, 1.0]), "y": ("y", [0.0, 1.0])},
    )
    meta = Metadata(
        data_kind=DataKind.IMAGE,
        channels=(ChannelInfo("O2", "optical", "signal", "complex64", harmonic=2),),
    )
    ds = Dataset(data, kind=DataKind.IMAGE, metadata=meta, provenance=_node())
    with pytest.raises(ProcessingError, match="no optical signal/reference pairs"):
        ReferenceNormalize().apply({"primary": ds})


# --------------------------------------------------------------------------- #
# image.phase_unwrap
# --------------------------------------------------------------------------- #


def test_unwrap_2d_recovers_a_known_ramp() -> None:
    # A phase ramp that wraps several times; unwrap must recover it up to a constant.
    y, x = np.mgrid[0:30, 0:40].astype(np.float64)
    true = 0.6 * x + 0.4 * y  # radians, exceeds 2*pi many times
    wrapped = np.angle(np.exp(1j * true))
    out = unwrap_2d(wrapped)
    np.testing.assert_allclose(out - out[0, 0], true - true[0, 0], atol=1e-9)


def test_phase_unwrap_adds_channel_and_keeps_raw(synthetic_dataset: Dataset) -> None:
    result = PhaseUnwrap(channel="O2").apply({"primary": synthetic_dataset})
    assert "O2_phase_unwrapped" in result.channel_names
    assert "O2" in result.channel_names  # raw retained
    info = {c.canonical: c for c in result.metadata.channels}["O2_phase_unwrapped"]
    assert info.state == "unwrapped" and info.value_unit == "rad"
    # Raw O2 is untouched.
    np.testing.assert_array_equal(
        result.channel("O2").values, synthetic_dataset.channel("O2").values
    )


def test_phase_unwrap_rejects_real_channel(synthetic_dataset: Dataset) -> None:
    with pytest.raises(ProcessingError, match="not complex"):
        PhaseUnwrap(channel="Z").apply({"primary": synthetic_dataset})


def test_phase_unwrap_provenance(synthetic_dataset: Dataset) -> None:
    result = PhaseUnwrap(channel="O2").apply({"primary": synthetic_dataset})
    assert result.provenance.record.step_id == "image.phase_unwrap"
    assert result.provenance.record.params["channel"] == "O2"


# --------------------------------------------------------------------------- #
# image.crop
# --------------------------------------------------------------------------- #


def _grid_dataset() -> tuple[Dataset, npt.NDArray[np.float64]]:
    nx, ny = 6, 5
    x = (np.arange(nx, dtype=np.float64) + 0.5) * 100.0  # 50..550 nm
    y = (np.arange(ny, dtype=np.float64) + 0.5) * 100.0
    z = np.arange(nx * ny, dtype=np.float64).reshape(ny, nx)
    data = xr.Dataset(
        {"Z": (("y", "x"), z)},
        coords={
            "x": ("x", x, {"unit": "nm", "axis": "X"}),
            "y": ("y", y, {"unit": "nm", "axis": "Y"}),
        },
    )
    meta = Metadata(
        data_kind=DataKind.IMAGE,
        conventions=Conventions(),
        scan=ScanInfo(
            pixels=(nx, ny),
            size_nm=(nx * 100.0, ny * 100.0),
            pixel_size_nm=(100.0, 100.0),
        ),
        channels=(ChannelInfo("Z", "topography", "signal", "float64", value_unit="nm"),),
    )
    return Dataset(data, kind=DataKind.IMAGE, metadata=meta, provenance=_node()), z


def test_crop_selects_the_region_exactly() -> None:
    ds, z = _grid_dataset()
    # Keep x in [150, 350] -> pixel centers 150,250,350 (indices 1..3);
    # y in [150, 250] -> centers 150,250 (indices 1..2).
    result = Crop(x_min=120.0, x_max=360.0, y_min=120.0, y_max=260.0).apply({"primary": ds})
    assert result.data.sizes == {"x": 3, "y": 2}
    np.testing.assert_array_equal(result.channel("Z").values, z[1:3, 1:4])
    np.testing.assert_array_equal(result.coordinate("x").values, ds.coordinate("x").values[1:4])


def test_crop_updates_scan_geometry() -> None:
    ds, _ = _grid_dataset()
    result = Crop(x_min=120.0, x_max=360.0, y_min=120.0, y_max=260.0).apply({"primary": ds})
    scan = result.metadata.scan
    assert scan.pixels == (3, 2)
    assert scan.size_nm == (300.0, 200.0)
    # Lower-left corner: first kept center (150) minus half a pixel (50) -> 100.
    assert scan.offset_nm == (100.0, 100.0)


def test_crop_empty_region_errors() -> None:
    ds, _ = _grid_dataset()
    with pytest.raises(ProcessingError, match="selects no pixels"):
        Crop(x_min=10_000.0, x_max=20_000.0, y_min=0.0, y_max=1.0).apply({"primary": ds})


def test_crop_validates_bounds() -> None:
    with pytest.raises(ProcessingError, match="x_min must be"):
        Crop(x_min=5.0, x_max=1.0, y_min=0.0, y_max=1.0)


def test_crop_immutability_and_provenance() -> None:
    ds, z = _grid_dataset()
    result = Crop(x_min=120.0, x_max=360.0, y_min=120.0, y_max=260.0).apply({"primary": ds})
    assert result.provenance.record.step_id == "image.crop"
    np.testing.assert_array_equal(ds.channel("Z").values, z)  # input untouched
