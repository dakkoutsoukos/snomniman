"""Tests for Phase 3C region-aware operations (image domain).

Covers ``image.region_phase_reference`` and ``image.region_amplitude_reference``
together with the ``ROI_RECTANGLE`` hint addition to ``ParameterSpec``. Every
operation is tested with a known analytical answer (Rule 6): a carefully constructed
synthetic dataset where the reference-region statistic is exactly computable, so
the result can be verified without running the operation twice.

Coverage per operation:
- Known-answer (the critical scientific invariant)
- Physical quantity preserved (amplitude for phase op; phase for amplitude op)
- Non-mutation of the input dataset
- Provenance recorded
- Metadata state + conventions updated
- Region validation errors (out-of-bounds, inverted bounds)
- Channel validation errors (wrong type, missing)
- Operation-specific edge cases (zero amplitude datum)
"""

from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

import snomniman.processing.image  # noqa: F401  (registers image ops)
from snomniman.core import (
    ChannelInfo,
    Conventions,
    DataKind,
    Dataset,
    Demodulation,
    Excitation,
    Instrument,
    Metadata,
    ProvenanceNode,
    ScanInfo,
    StepRecord,
)
from snomniman.core.exceptions import ProcessingError
from snomniman.processing import ParameterSpec, get_step
from snomniman.processing.step import ROI_RECTANGLE

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _apply(step_id: str, dataset: Dataset, **params: object) -> Dataset:
    return get_step(step_id)(**params).apply({"primary": dataset})


def _make_phase_dataset() -> Dataset:
    """4x4 complex image with a controlled reference region (top-left 2x2).

    Grid: x=[25,75,125,175] nm, y=[25,75,125,175] nm (50 nm pitch).
    Reference region: x in [0,100] nm, y in [0,100] nm -> rows 0-1, cols 0-1 (4 pixels).

    O2 channel:
      - Reference region (rows 0-1, cols 0-1): amplitude=1.0, phase=pi/4
      - Remaining pixels: amplitude=1.0, phase=pi/2

    After ``region_phase_reference`` on this region:
      dphi = circular_mean(reference) = angle(mean(4*exp(i*pi/4))) = pi/4
      All pixels subtract pi/4: reference region -> phase=0; rest -> phase=pi/4.
    """
    ny, nx = 4, 4
    x = (np.arange(nx, dtype=np.float64) + 0.5) * 50.0  # [25, 75, 125, 175]
    y = (np.arange(ny, dtype=np.float64) + 0.5) * 50.0

    phase = np.full((ny, nx), np.pi / 2, dtype=np.float64)
    phase[:2, :2] = np.pi / 4  # reference region

    o2 = np.exp(1j * phase).astype(np.complex64)
    z = np.ones((ny, nx), dtype=np.float64)

    data = xr.Dataset(
        {
            "O2": (("y", "x"), o2),
            "Z": (("y", "x"), z),
        },
        coords={
            "x": ("x", x, {"unit": "nm", "axis": "X"}),
            "y": ("y", y, {"unit": "nm", "axis": "Y"}),
        },
    )
    channels = (
        ChannelInfo("O2", "optical", "signal", "complex64", harmonic=2, amplitude_unit="a.u."),
        ChannelInfo("Z", "topography", "signal", "float64", value_unit="nm"),
    )
    metadata = Metadata(
        data_kind=DataKind.IMAGE,
        conventions=Conventions(),
        instrument=Instrument(vendor="neaspec"),
        excitation=Excitation(),
        demodulation=Demodulation(harmonics=(2,)),
        scan=ScanInfo(pixels=(nx, ny), size_nm=(nx * 50.0, ny * 50.0),
                      pixel_size_nm=(50.0, 50.0)),
        channels=channels,
    )
    node = ProvenanceNode("n0", StepRecord("io.read", 1, True))
    return Dataset(data, kind=DataKind.IMAGE, metadata=metadata, provenance=node)


def _make_amplitude_dataset() -> Dataset:
    """4x4 complex image with a controlled reference region (top-left 2x2).

    O2 channel:
      - Reference region (rows 0-1, cols 0-1): amplitude=3.0, phase=0
      - Remaining pixels: amplitude=1.0, phase=0

    After ``region_amplitude_reference`` on this region:
      datum = mean_amplitude(reference) = 3.0
      All pixels divided by 3: reference region -> amplitude=1.0; rest -> amplitude~=0.333.
    """
    ny, nx = 4, 4
    x = (np.arange(nx, dtype=np.float64) + 0.5) * 50.0
    y = (np.arange(ny, dtype=np.float64) + 0.5) * 50.0

    amp = np.full((ny, nx), 1.0, dtype=np.float64)
    amp[:2, :2] = 3.0  # reference region

    o2 = amp.astype(np.complex64)  # phase=0, all real positive
    z = np.ones((ny, nx), dtype=np.float64)

    data = xr.Dataset(
        {
            "O2": (("y", "x"), o2),
            "Z": (("y", "x"), z),
        },
        coords={
            "x": ("x", x, {"unit": "nm", "axis": "X"}),
            "y": ("y", y, {"unit": "nm", "axis": "Y"}),
        },
    )
    channels = (
        ChannelInfo("O2", "optical", "signal", "complex64", harmonic=2, amplitude_unit="a.u."),
        ChannelInfo("Z", "topography", "signal", "float64", value_unit="nm"),
    )
    metadata = Metadata(
        data_kind=DataKind.IMAGE,
        conventions=Conventions(),
        instrument=Instrument(vendor="neaspec"),
        excitation=Excitation(),
        demodulation=Demodulation(harmonics=(2,)),
        scan=ScanInfo(pixels=(nx, ny), size_nm=(nx * 50.0, ny * 50.0),
                      pixel_size_nm=(50.0, 50.0)),
        channels=channels,
    )
    node = ProvenanceNode("n0", StepRecord("io.read", 1, True))
    return Dataset(data, kind=DataKind.IMAGE, metadata=metadata, provenance=node)


# --------------------------------------------------------------------------- #
# ParameterSpec.region_role
# --------------------------------------------------------------------------- #


def test_parameter_spec_accepts_roi_rectangle() -> None:
    spec = ParameterSpec("x_min", "Left bound (nm).", (int, float), region_role=ROI_RECTANGLE)
    assert spec.region_role == ROI_RECTANGLE


def test_parameter_spec_accepts_none_region_role() -> None:
    spec = ParameterSpec("value", "A value.", (float,))
    assert spec.region_role is None


def test_parameter_spec_rejects_unknown_region_role() -> None:
    with pytest.raises(ValueError, match="region_role"):
        ParameterSpec("x", "x.", (float,), region_role="bad_role")


# --------------------------------------------------------------------------- #
# image.region_phase_reference
# --------------------------------------------------------------------------- #

# Reference region bounds (top-left 2x2 of the 4x4 grid):
_REF_X_MIN, _REF_X_MAX = 0.0, 100.0
_REF_Y_MIN, _REF_Y_MAX = 0.0, 100.0


def test_region_phase_reference_known_answer() -> None:
    """Subtracting the circular mean of the reference region zeros that region's phase."""
    ds = _make_phase_dataset()
    result = _apply(
        "image.region_phase_reference", ds, channel="O2",
        x_min=_REF_X_MIN, x_max=_REF_X_MAX,
        y_min=_REF_Y_MIN, y_max=_REF_Y_MAX,
    )
    out = np.asarray(result.channel("O2").values)
    # Reference region (top-left 2x2) was at phase pi/4; after subtracting pi/4 -> phase ~= 0.
    ref_phases = np.angle(out[:2, :2])
    np.testing.assert_allclose(ref_phases, 0.0, atol=1e-5)
    # Non-reference pixels were at phase π/2; after subtracting π/4 → phase ≈ π/4.
    other_phases = np.angle(out[2:, :])
    np.testing.assert_allclose(other_phases, np.pi / 4, atol=1e-5)
    other_phases_top = np.angle(out[:2, 2:])
    np.testing.assert_allclose(other_phases_top, np.pi / 4, atol=1e-5)


def test_region_phase_reference_amplitude_preserved() -> None:
    """Phase re-referencing must not change amplitude."""
    ds = _make_phase_dataset()
    original_amp = np.abs(np.asarray(ds.channel("O2").values))
    result = _apply(
        "image.region_phase_reference", ds, channel="O2",
        x_min=_REF_X_MIN, x_max=_REF_X_MAX,
        y_min=_REF_Y_MIN, y_max=_REF_Y_MAX,
    )
    result_amp = np.abs(np.asarray(result.channel("O2").values))
    np.testing.assert_allclose(result_amp, original_amp, rtol=1e-5)


def test_region_phase_reference_does_not_mutate_input() -> None:
    ds = _make_phase_dataset()
    before = np.array(ds.channel("O2").values, copy=True)
    _apply(
        "image.region_phase_reference", ds, channel="O2",
        x_min=_REF_X_MIN, x_max=_REF_X_MAX,
        y_min=_REF_Y_MIN, y_max=_REF_Y_MAX,
    )
    np.testing.assert_array_equal(ds.channel("O2").values, before)


def test_region_phase_reference_records_provenance() -> None:
    ds = _make_phase_dataset()
    result = _apply(
        "image.region_phase_reference", ds, channel="O2",
        x_min=_REF_X_MIN, x_max=_REF_X_MAX,
        y_min=_REF_Y_MIN, y_max=_REF_Y_MAX,
    )
    assert result.provenance.record.step_id == "image.region_phase_reference"
    params = result.provenance.record.params
    assert params["channel"] == "O2"
    assert params["x_min"] == _REF_X_MIN
    assert params["x_max"] == _REF_X_MAX


def test_region_phase_reference_updates_metadata() -> None:
    ds = _make_phase_dataset()
    result = _apply(
        "image.region_phase_reference", ds, channel="O2",
        x_min=_REF_X_MIN, x_max=_REF_X_MAX,
        y_min=_REF_Y_MIN, y_max=_REF_Y_MAX,
    )
    assert result.metadata.channel("O2").state == "referenced"
    assert "image.region_phase_reference" in (result.metadata.conventions.phase_reference or "")


def test_region_phase_reference_other_channels_unchanged() -> None:
    """Channels other than the target are unchanged."""
    ds = _make_phase_dataset()
    before_z = np.array(ds.channel("Z").values, copy=True)
    result = _apply(
        "image.region_phase_reference", ds, channel="O2",
        x_min=_REF_X_MIN, x_max=_REF_X_MAX,
        y_min=_REF_Y_MIN, y_max=_REF_Y_MAX,
    )
    np.testing.assert_array_equal(result.channel("Z").values, before_z)


def test_region_phase_reference_rejects_out_of_bounds_region() -> None:
    ds = _make_phase_dataset()
    with pytest.raises(ProcessingError, match="selects no pixels"):
        _apply(
            "image.region_phase_reference", ds, channel="O2",
            x_min=5000.0, x_max=6000.0,   # far outside the 200-nm dataset
            y_min=0.0, y_max=100.0,
        )


def test_region_phase_reference_rejects_inverted_x_bounds() -> None:
    ds = _make_phase_dataset()
    with pytest.raises(ProcessingError, match="x_min"):
        _apply(
            "image.region_phase_reference", ds, channel="O2",
            x_min=100.0, x_max=50.0,  # inverted
            y_min=0.0, y_max=100.0,
        )


def test_region_phase_reference_rejects_inverted_y_bounds() -> None:
    ds = _make_phase_dataset()
    with pytest.raises(ProcessingError, match="y_min"):
        _apply(
            "image.region_phase_reference", ds, channel="O2",
            x_min=0.0, x_max=100.0,
            y_min=100.0, y_max=50.0,  # inverted
        )


def test_region_phase_reference_rejects_real_channel() -> None:
    ds = _make_phase_dataset()
    with pytest.raises(ProcessingError, match="requires a complex channel"):
        _apply(
            "image.region_phase_reference", ds, channel="Z",
            x_min=_REF_X_MIN, x_max=_REF_X_MAX,
            y_min=_REF_Y_MIN, y_max=_REF_Y_MAX,
        )


def test_region_phase_reference_rejects_missing_channel() -> None:
    ds = _make_phase_dataset()
    with pytest.raises(ProcessingError, match="not found"):
        _apply(
            "image.region_phase_reference", ds, channel="NOPE",
            x_min=_REF_X_MIN, x_max=_REF_X_MAX,
            y_min=_REF_Y_MIN, y_max=_REF_Y_MAX,
        )


# --------------------------------------------------------------------------- #
# image.region_amplitude_reference
# --------------------------------------------------------------------------- #


def test_region_amplitude_reference_known_answer() -> None:
    """Dividing by the reference region mean amplitude maps that region's mean to 1.0."""
    ds = _make_amplitude_dataset()
    result = _apply(
        "image.region_amplitude_reference", ds, channel="O2",
        x_min=_REF_X_MIN, x_max=_REF_X_MAX,
        y_min=_REF_Y_MIN, y_max=_REF_Y_MAX,
    )
    out = np.asarray(result.channel("O2").values)
    # Reference region was amplitude=3.0; divided by mean(3.0)=3.0 → 1.0.
    ref_amps = np.abs(out[:2, :2])
    np.testing.assert_allclose(ref_amps, 1.0, rtol=1e-5)
    # Non-reference pixels had amplitude=1.0; divided by 3.0 → ≈0.333.
    other_amps = np.abs(out[2:, :])
    np.testing.assert_allclose(other_amps, 1.0 / 3.0, rtol=1e-4)


def test_region_amplitude_reference_phase_preserved() -> None:
    """Amplitude normalization must not change phase."""
    ds = _make_amplitude_dataset()
    # Add non-zero phase to verify preservation
    raw_o2 = np.asarray(ds.channel("O2").values, dtype=np.complex128)
    raw_o2 = raw_o2 * np.exp(1j * 0.7)  # rotate all pixels by 0.7 rad
    # Rebuild dataset with modified O2
    data = ds.data.assign({"O2": (("y", "x"), raw_o2.astype(np.complex64))})
    ds2 = Dataset(data, kind=ds.kind, metadata=ds.metadata, provenance=ds.provenance)

    original_phase = np.angle(np.asarray(ds2.channel("O2").values))
    result = _apply(
        "image.region_amplitude_reference", ds2, channel="O2",
        x_min=_REF_X_MIN, x_max=_REF_X_MAX,
        y_min=_REF_Y_MIN, y_max=_REF_Y_MAX,
    )
    result_phase = np.angle(np.asarray(result.channel("O2").values))
    np.testing.assert_allclose(result_phase, original_phase, atol=1e-5)


def test_region_amplitude_reference_does_not_mutate_input() -> None:
    ds = _make_amplitude_dataset()
    before = np.array(ds.channel("O2").values, copy=True)
    _apply(
        "image.region_amplitude_reference", ds, channel="O2",
        x_min=_REF_X_MIN, x_max=_REF_X_MAX,
        y_min=_REF_Y_MIN, y_max=_REF_Y_MAX,
    )
    np.testing.assert_array_equal(ds.channel("O2").values, before)


def test_region_amplitude_reference_records_provenance() -> None:
    ds = _make_amplitude_dataset()
    result = _apply(
        "image.region_amplitude_reference", ds, channel="O2",
        x_min=_REF_X_MIN, x_max=_REF_X_MAX,
        y_min=_REF_Y_MIN, y_max=_REF_Y_MAX,
    )
    assert result.provenance.record.step_id == "image.region_amplitude_reference"
    params = result.provenance.record.params
    assert params["channel"] == "O2"
    assert params["x_min"] == _REF_X_MIN
    assert params["y_max"] == _REF_Y_MAX


def test_region_amplitude_reference_updates_metadata() -> None:
    ds = _make_amplitude_dataset()
    result = _apply(
        "image.region_amplitude_reference", ds, channel="O2",
        x_min=_REF_X_MIN, x_max=_REF_X_MAX,
        y_min=_REF_Y_MIN, y_max=_REF_Y_MAX,
    )
    assert result.metadata.channel("O2").state == "normalized"
    assert result.metadata.channel("O2").amplitude_unit == ""


def test_region_amplitude_reference_other_channels_unchanged() -> None:
    ds = _make_amplitude_dataset()
    before_z = np.array(ds.channel("Z").values, copy=True)
    result = _apply(
        "image.region_amplitude_reference", ds, channel="O2",
        x_min=_REF_X_MIN, x_max=_REF_X_MAX,
        y_min=_REF_Y_MIN, y_max=_REF_Y_MAX,
    )
    np.testing.assert_array_equal(result.channel("Z").values, before_z)


def test_region_amplitude_reference_rejects_out_of_bounds_region() -> None:
    ds = _make_amplitude_dataset()
    with pytest.raises(ProcessingError, match="selects no pixels"):
        _apply(
            "image.region_amplitude_reference", ds, channel="O2",
            x_min=5000.0, x_max=6000.0,
            y_min=0.0, y_max=100.0,
        )


def test_region_amplitude_reference_rejects_inverted_x_bounds() -> None:
    ds = _make_amplitude_dataset()
    with pytest.raises(ProcessingError, match="x_min"):
        _apply(
            "image.region_amplitude_reference", ds, channel="O2",
            x_min=100.0, x_max=50.0,
            y_min=0.0, y_max=100.0,
        )


def test_region_amplitude_reference_rejects_inverted_y_bounds() -> None:
    ds = _make_amplitude_dataset()
    with pytest.raises(ProcessingError, match="y_min"):
        _apply(
            "image.region_amplitude_reference", ds, channel="O2",
            x_min=0.0, x_max=100.0,
            y_min=100.0, y_max=50.0,
        )


def test_region_amplitude_reference_rejects_zero_amplitude_region() -> None:
    """A reference region with zero mean amplitude cannot normalize."""
    ds = _make_amplitude_dataset()
    # Override O2 to all-zero in the reference region
    raw_o2 = np.asarray(ds.channel("O2").values, dtype=np.complex64).copy()
    raw_o2[:2, :2] = 0.0 + 0.0j
    data = ds.data.assign({"O2": (("y", "x"), raw_o2)})
    ds_zero = Dataset(data, kind=ds.kind, metadata=ds.metadata, provenance=ds.provenance)
    with pytest.raises(ProcessingError, match="mean amplitude"):
        _apply(
            "image.region_amplitude_reference", ds_zero, channel="O2",
            x_min=_REF_X_MIN, x_max=_REF_X_MAX,
            y_min=_REF_Y_MIN, y_max=_REF_Y_MAX,
        )


def test_region_amplitude_reference_rejects_real_channel() -> None:
    ds = _make_amplitude_dataset()
    with pytest.raises(ProcessingError, match="requires a complex channel"):
        _apply(
            "image.region_amplitude_reference", ds, channel="Z",
            x_min=_REF_X_MIN, x_max=_REF_X_MAX,
            y_min=_REF_Y_MIN, y_max=_REF_Y_MAX,
        )


def test_region_amplitude_reference_rejects_missing_channel() -> None:
    ds = _make_amplitude_dataset()
    with pytest.raises(ProcessingError, match="not found"):
        _apply(
            "image.region_amplitude_reference", ds, channel="NOPE",
            x_min=_REF_X_MIN, x_max=_REF_X_MAX,
            y_min=_REF_Y_MIN, y_max=_REF_Y_MAX,
        )
