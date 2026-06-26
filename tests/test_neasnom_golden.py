"""Golden-file tests: the real neaSNOM GSF measurement directory -> Dataset.

These lock the reader against known values from the real CdO measurement analysed
in docs/measurement-discovery.md. They skip cleanly when the sample data is absent
(e.g. on CI without the large sample folder).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import numpy.typing as npt
import pytest

from snomniman.core import Capability, DataKind, ReaderError, deserialize_dag, serialize_dag
from snomniman.io import read, read_gsf, read_neasnom_measurement
from snomniman.io.neasnom import READER_ID

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SAMPLE_PARENT = _REPO_ROOT / "SNOM Sample Files" / "2026-06-16 14928"
_GOLDEN_DIR = _SAMPLE_PARENT / "2026-06-16 190234 PH CdO Dense ROI 2"

_EXPECTED_CHANNELS = {
    *(f"O{n}" for n in range(6)),
    *(f"M{n}" for n in range(6)),
    *(f"R_O{n}" for n in range(6)),
    *(f"R_M{n}" for n in range(6)),
    "Z", "Z_C", "Z_H", "Z_CH",
    "R_Z", "R_Z_C", "R_Z_H", "R_Z_CH",
}


@pytest.fixture(scope="module")
def golden():  # type: ignore[no-untyped-def]
    if not _GOLDEN_DIR.is_dir():
        pytest.skip("real neaSNOM sample data not present")
    return read_neasnom_measurement(_GOLDEN_DIR)


def _raw_oriented(token: str) -> npt.NDArray[np.float32]:
    """Read a raw channel GSF and flip it into canonical lower-left/y-up order."""
    gf = read_gsf(_GOLDEN_DIR / f"{_GOLDEN_DIR.name} {token}.gsf")
    return np.flipud(gf.data)


# -- structure --------------------------------------------------------------- #


def test_channel_count_and_names(golden) -> None:  # type: ignore[no-untyped-def]
    assert len(golden.channel_names) == 32
    assert set(golden.channel_names) == _EXPECTED_CHANNELS


def test_dimensions(golden) -> None:  # type: ignore[no-untyped-def]
    assert dict(golden.data.sizes) == {"y": 150, "x": 150}
    assert golden.channel("O2").shape == (150, 150)


def test_kind_and_capabilities(golden) -> None:  # type: ignore[no-untyped-def]
    assert golden.kind is DataKind.IMAGE
    assert golden.capabilities == frozenset(
        {
            Capability.SPATIAL_2D,
            Capability.COMPLEX_OPTICAL,
            Capability.COMPLEX_MECHANICAL,
            Capability.TOPOGRAPHY,
            Capability.REFERENCE,
            Capability.MULTI_HARMONIC,
        }
    )
    assert golden.is_raw is True


def test_sniff_and_dispatch_match_direct_read(golden) -> None:  # type: ignore[no-untyped-def]
    via_registry = read(_GOLDEN_DIR)
    assert set(via_registry.channel_names) == set(golden.channel_names)


# -- coordinates (canonical nm, lower-left, increasing) ---------------------- #


def test_coordinates_nm_and_increasing(golden) -> None:  # type: ignore[no-untyped-def]
    x = golden.coordinate("x").values
    y = golden.coordinate("y").values
    assert golden.coordinate("x").attrs["unit"] == "nm"
    assert golden.coordinate("y").attrs["unit"] == "nm"
    assert x.shape == (150,) and y.shape == (150,)
    assert np.all(np.diff(x) > 0) and np.all(np.diff(y) > 0)  # increasing
    # Pixel size 10 um / 150 = 66.667 nm; full extent 10000 nm.
    np.testing.assert_allclose(np.diff(x), 10000.0 / 150.0, rtol=1e-6)
    np.testing.assert_allclose(x[-1] - x[0], (150 - 1) * 10000.0 / 150.0, rtol=1e-6)
    # Lower-left corner near the GSF offset (pixel-center -> + half a pixel).
    np.testing.assert_allclose(x[0], 55811.8154659 + 0.5 * 10000.0 / 150.0, rtol=1e-6)


# -- channel values (faithful to the raw files) ------------------------------ #


def test_optical_amplitude_matches_raw(golden) -> None:  # type: ignore[no-untyped-def]
    amp = golden.amplitude("O2").values
    raw_a = _raw_oriented("O2A raw")
    np.testing.assert_allclose(amp, raw_a, rtol=1e-5, atol=1e-3)


def test_optical_phase_preserved_as_imported(golden) -> None:  # type: ignore[no-untyped-def]
    phase = golden.phase("O2").values
    raw_p = _raw_oriented("O2P raw")
    # Circular difference is robust to the +/-pi wrap boundary.
    circ = np.angle(np.exp(1j * (phase - raw_p)))
    assert float(np.max(np.abs(circ))) < 1e-3


def test_orientation_is_lower_left(golden) -> None:  # type: ignore[no-untyped-def]
    # Canonical row 0 is the physical BOTTOM, i.e. the last GSF row (top-to-bottom).
    raw = read_gsf(_GOLDEN_DIR / f"{_GOLDEN_DIR.name} O2A raw.gsf").data
    amp00 = float(golden.amplitude("O2").values[0, 0])
    assert amp00 == pytest.approx(float(raw[-1, 0]), rel=1e-5)
    assert amp00 != pytest.approx(float(raw[0, 0]), rel=1e-5)  # flip is observable


def test_topography_converted_to_nm(golden) -> None:  # type: ignore[no-untyped-def]
    z = golden.channel("Z")
    assert z.attrs["value_unit"] == "nm"
    expected = _raw_oriented("Z raw").astype(np.float64) * 1e9
    np.testing.assert_allclose(z.values, expected, rtol=1e-6)
    assert 600.0 < float(z.min()) < 1000.0  # heights in nm, not metres


# -- metadata ---------------------------------------------------------------- #


def test_metadata_instrument_and_excitation(golden) -> None:  # type: ignore[no-untyped-def]
    m = golden.metadata
    assert m.instrument.vendor == "neaspec"
    assert m.instrument.software_version == "2.2.14109.0"
    assert m.excitation.source_type == "Piano"
    assert m.excitation.detector == "MIR"
    assert m.excitation.wavenumber_cm1 == pytest.approx(5973.0)
    assert m.demodulation.detection == "PsHet"
    assert m.demodulation.harmonics == (0, 1, 2, 3, 4, 5)


def test_metadata_scan_geometry(golden) -> None:  # type: ignore[no-untyped-def]
    s = golden.metadata.scan
    assert s.pixels == (150, 150)
    assert s.size_nm == pytest.approx((10000.0, 10000.0))
    assert s.center_nm == pytest.approx((60810.0, 14160.0))
    assert s.offset_nm[0] == pytest.approx(55811.8154659)
    assert s.pixel_size_nm == pytest.approx((66.6667, 66.6667), rel=1e-4)
    assert s.rotation_deg == 0.0
    # Self-consistency: offset + half-extent == scan centre (txt vs GSF agree).
    assert s.offset_nm[0] + s.size_nm[0] / 2 == pytest.approx(s.center_nm[0], abs=10.0)


def test_metadata_acquisition(golden) -> None:  # type: ignore[no-untyped-def]
    a = golden.metadata.acquisition
    assert a.datetime == "2026-06-16T19:02:34"
    assert a.integration_time_s == pytest.approx(0.121)
    assert a.tapping_amplitude_nm == pytest.approx(53.079)
    assert a.setpoint == pytest.approx(80.48)
    assert a.averaging == 1


def test_metadata_channels_and_raw_header(golden) -> None:  # type: ignore[no-untyped-def]
    m = golden.metadata
    assert len(m.channels) == 32
    o2 = m.channel("O2")
    assert o2.dtype == "complex64" and o2.harmonic == 2 and o2.role == "signal"
    # source_files keep the exact on-disk filenames (auditable mapping).
    assert o2.source_files == (
        f"{_GOLDEN_DIR.name} O2A raw.gsf",
        f"{_GOLDEN_DIR.name} O2P raw.gsf",
    )
    assert m.channel("R_O2").role == "reference"
    assert m.channel("Z").value_unit == "nm"
    assert m.original_units["x"] == "m"
    # Verbatim vendor header preserved.
    assert any("neaspec" in line for line in m.raw_header["parameter_file"]["lines"])
    assert m.raw_header["gsf_header_sample"]["XRes"] == "150"


# -- provenance + source ----------------------------------------------------- #


def test_raw_source_anchor(golden) -> None:  # type: ignore[no-untyped-def]
    src = golden.source
    assert src is not None
    assert src.reader == READER_ID
    assert src.is_directory is True
    assert len(src.sha256) == 64
    assert len(src.manifest) == 57  # 56 .gsf + 1 .txt
    assert src.bytes > 5_000_000


def test_provenance_read_node(golden) -> None:  # type: ignore[no-untyped-def]
    node = golden.provenance
    assert node.node_id == "n0"
    assert node.record.step_id == "io.read"
    assert node.record.deterministic is True
    assert set(node.sources) == {"source"}
    assert node.record.input_fingerprint == f"sha256:{golden.source.sha256}"
    assert "numpy" in node.record.software


def test_provenance_serialization_roundtrip(golden) -> None:  # type: ignore[no-untyped-def]
    encoded = json.dumps(serialize_dag(golden.provenance))
    rebuilt = deserialize_dag(json.loads(encoded))
    assert serialize_dag(rebuilt) == serialize_dag(golden.provenance)


def test_raw_dataset_is_immutable(golden) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError):
        golden.channel("Z").data[0, 0] = 0.0


# -- generalisation across all four runs ------------------------------------- #


def test_imaging_runs_load_and_other_modalities_fail_cleanly() -> None:
    if not _SAMPLE_PARENT.is_dir():
        pytest.skip("real neaSNOM sample data not present")
    runs = sorted(p for p in _SAMPLE_PARENT.iterdir() if p.is_dir())
    imaging_loaded = 0
    for run in runs:
        try:
            ds = read_neasnom_measurement(run)
        except ReaderError:
            # A non-imaging modality (the "PSP ... Spectra" point-spectra run) is
            # rejected cleanly rather than mis-read. Phase 1 targets imaging only.
            continue
        # Runs differ in scan size (one is 400x300, not 150x150); the reader must
        # not hardcode dimensions - just require a valid 2-D grid.
        sizes = dict(ds.data.sizes)
        assert set(sizes) == {"y", "x"}
        assert sizes["x"] > 0 and sizes["y"] > 0
        assert any(name.startswith("O") for name in ds.channel_names)
        assert ds.kind is DataKind.IMAGE
        imaging_loaded += 1
    assert imaging_loaded >= 3  # the three imaging runs in the sample folder
