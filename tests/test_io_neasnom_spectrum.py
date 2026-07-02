"""Tests for the neaSNOM point-spectroscopy reader (docs/point-spectrum-discovery.md).

Golden tests lock the reader against the real "PSP" (Point Spectroscopy) measurement
directory and skip cleanly when the sample data is absent. Synthetic tests cover the
single-position ``SPECTRUM`` path (not present in the real sample) and the reader's
validation guards, with a known answer for every assertion (Rule 6).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from snomniman.core import Capability, DataKind, ReaderError
from snomniman.io import read, sniff
from snomniman.io.neasnom import READER_ID as IMAGE_READER_ID
from snomniman.io.neasnom_spectrum import READER_ID, read_neasnom_spectrum_measurement

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SAMPLE_PARENT = _REPO_ROOT / "SNOM Sample Files" / "2026-06-16 14928"
_GOLDEN_DIR = _SAMPLE_PARENT / "2026-06-16 212518 PH PSP CdO Dense ROI 2"


@pytest.fixture(scope="module")
def golden():  # type: ignore[no-untyped-def]
    if not _GOLDEN_DIR.is_dir():
        pytest.skip("real neaSNOM point-spectroscopy sample data not present")
    return read_neasnom_spectrum_measurement(_GOLDEN_DIR)


# -- structure (real data) ---------------------------------------------------- #


def test_channel_count_and_names(golden) -> None:  # type: ignore[no-untyped-def]
    assert set(golden.channel_names) == {f"O{n}" for n in range(6)} | {"Z"}


def test_dimensions_and_kind(golden) -> None:  # type: ignore[no-untyped-def]
    assert dict(golden.data.sizes) == {"s": 100, "wavenumber": 201}
    assert golden.kind is DataKind.LINE_SCAN
    assert golden.is_raw is True


def test_capabilities(golden) -> None:  # type: ignore[no-untyped-def]
    assert golden.capabilities == frozenset(
        {
            Capability.SPATIAL_1D,
            Capability.SPECTRAL,
            Capability.COMPLEX_OPTICAL,
            Capability.MULTI_HARMONIC,
            Capability.TOPOGRAPHY,
        }
    )


def test_sniff_and_dispatch_match_direct_read(golden) -> None:  # type: ignore[no-untyped-def]
    assert sniff(_GOLDEN_DIR) == READER_ID
    via_registry = read(_GOLDEN_DIR)
    assert set(via_registry.channel_names) == set(golden.channel_names)
    assert dict(via_registry.data.sizes) == dict(golden.data.sizes)


def test_neighboring_imaging_directory_still_routes_to_the_image_reader() -> None:
    # The routing fix must not regress the (far more common) imaging case.
    image_dir = _SAMPLE_PARENT / "2026-06-16 190234 PH CdO Dense ROI 2"
    if not image_dir.is_dir():
        pytest.skip("real neaSNOM imaging sample data not present")
    assert sniff(image_dir) == IMAGE_READER_ID


# -- coordinates (canonical, validated against the raw text) ----------------- #


def test_wavenumber_coordinate(golden) -> None:  # type: ignore[no-untyped-def]
    wn = golden.coordinate("wavenumber").values
    assert wn.shape == (201,)
    assert wn[0] == 5920.0
    assert wn[-1] == 6120.0
    np.testing.assert_allclose(np.diff(wn), 1.0)
    assert golden.coordinate("wavenumber").attrs["unit"] == "cm-1"


def test_s_coordinate_is_canonical_nm(golden) -> None:  # type: ignore[no-untyped-def]
    s = golden.coordinate("s").values
    assert s.shape == (100,)
    assert golden.coordinate("s").attrs["unit"] == "nm"
    np.testing.assert_allclose(np.diff(s), 20.0)  # 2000 nm line / 100 positions
    assert np.all(np.diff(s) > 0)


# -- channel values (spot-checked against the raw Spectra.txt) --------------- #


def test_o0_value_matches_raw_text(golden) -> None:  # type: ignore[no-untyped-def]
    # Row 0 (position 0, Omega 0): O0A=64.53029, O0P=0 -> complex 64.53029+0j.
    value = golden.channel("O0").values[0, 0]
    np.testing.assert_allclose(value, complex(64.53029, 0.0), rtol=1e-5)


def test_z_value_matches_raw_text_converted_to_nm(golden) -> None:  # type: ignore[no-untyped-def]
    # Raw Z at position 0, Omega 0 is 8.0220553E-07 m -> 802.20553 nm.
    value = golden.channel("Z").values[0, 0]
    np.testing.assert_allclose(value, 802.20553, rtol=1e-6)


def test_z_varies_across_wavenumber_within_one_position(golden) -> None:  # type: ignore[no-untyped-def]
    # AFM feedback stays active through the sweep - Z must not be reduced to one
    # value per position; verified against the real file's own (non-constant) values.
    z_row0 = golden.channel("Z").values[0, :]
    assert not np.allclose(z_row0, z_row0[0])


# -- metadata ------------------------------------------------------------------ #


def test_spectral_metadata(golden) -> None:  # type: ignore[no-untyped-def]
    spec = golden.metadata.spectral
    assert spec is not None
    assert spec.wavenumber_min_cm1 == 5920.0
    assert spec.wavenumber_max_cm1 == 6120.0
    assert spec.n_points == 201
    assert spec.sampling_cm1 == pytest.approx(1.0)


def test_scan_geometry_mirrors_vendor_gsf_convention(golden) -> None:  # type: ignore[no-untyped-def]
    # The vendor's own companion GSF side-export uses XRes=100, YRes=1, XReal=2E-6 m;
    # this reader derives the same geometry independently from the Spectra.txt header.
    scan = golden.metadata.scan
    assert scan.pixels == (100, 1)
    assert scan.size_nm == (2000.0, 0.0)


def test_no_reference_channels_in_this_measurement(golden) -> None:  # type: ignore[no-untyped-def]
    assert Capability.REFERENCE not in golden.capabilities


def test_provenance_is_a_single_raw_read_node(golden) -> None:  # type: ignore[no-untyped-def]
    assert golden.provenance.is_raw is True
    assert golden.source is not None
    assert golden.source.reader == READER_ID
    assert golden.source.is_directory is True
    # Only the parsed file is anchored - the companion per-position GSF channel maps
    # are a vendor side-export this reader deliberately does not ingest.
    assert len(golden.source.manifest) == 1
    assert golden.source.manifest[0][0].endswith("Spectra.txt")


# --------------------------------------------------------------------------- #
# Synthetic: single-position SPECTRUM path (not present in the real sample)
# --------------------------------------------------------------------------- #

_SINGLE_POINT_HEADER = """# www.neaspec.com
# Scan:\t \tPoint Spectroscopy (PsHet)
# Project:\t \ttest
# Description:\t \tsingle point
# Date:\t \t06/16/2026 21:25:18
# Scanner Center Position (X, Y):\t[µm]\t10.0\t5.0\t
# Scan Area (X, Y, Z):\t[µm]\t0.000\t0.000\t0.000
# Pixel Area (X, Y, Z):\t[px]\t1\t1\t3
# Laser Source:\t \tPiano\t
# Detector:\t \tMIR
# Target Wavelength:\t[cm⁻¹]\t5920.000\t \t
# Demodulation Mode:\t \tPsHet
# Version:\t \t2.2.14109.0
Row\tColumn\tOmega\tWavenumber\tZ\tO0A\tO0P\tO2A\tO2P\t
0\t0\t0\t5920 \t8.0E-07\t64.5\t0\t4.16\t1.5\t
0\t0\t1\t5921 \t8.1E-07\t63.1\t0\t3.95\t1.4\t
0\t0\t2\t5922 \t8.2E-07\t78.1\t0\t3.67\t1.3\t
"""


def _write_spectra_dir(tmp_path: Path, name: str, content: str) -> Path:
    d = tmp_path / name
    d.mkdir()
    (d / f"{name} Spectra.txt").write_text(content, encoding="utf-8")
    return d


def test_single_position_produces_spectrum_datakind(tmp_path: Path) -> None:
    d = _write_spectra_dir(tmp_path, "single", _SINGLE_POINT_HEADER)
    ds = read_neasnom_spectrum_measurement(d)
    assert ds.kind is DataKind.SPECTRUM
    assert dict(ds.data.sizes) == {"wavenumber": 3}
    assert "s" not in ds.coord_names
    assert Capability.SPATIAL_1D not in ds.capabilities
    assert Capability.SPECTRAL in ds.capabilities
    np.testing.assert_allclose(ds.channel("O0").values, [64.5, 63.1, 78.1])
    np.testing.assert_allclose(ds.channel("Z").values, [800.0, 810.0, 820.0])


def test_single_position_sniffs_and_dispatches(tmp_path: Path) -> None:
    d = _write_spectra_dir(tmp_path, "single", _SINGLE_POINT_HEADER)
    assert sniff(d) == READER_ID
    ds = read(d)
    assert ds.kind is DataKind.SPECTRUM


def test_non_point_spectroscopy_txt_directory_is_not_sniffed_as_spectrum(
    tmp_path: Path,
) -> None:
    d = tmp_path / "not_psp"
    d.mkdir()
    (d / "not_psp.txt").write_text("# Scan:\t \tSomething Else\n", encoding="utf-8")
    assert sniff(d) is None


# -- validation guards (Rule 6: never assume, validate against the file) ----- #


def test_inconsistent_wavenumber_sweep_across_positions_raises(tmp_path: Path) -> None:
    bad = _SINGLE_POINT_HEADER.replace(
        '# Pixel Area (X, Y, Z):\t[px]\t1\t1\t3\n',
        '# Pixel Area (X, Y, Z):\t[px]\t2\t1\t3\n',
    )
    # Add a second position whose wavenumber vector differs at the last sample.
    bad += "0\t1\t0\t5920 \t8.0E-07\t64.5\t0\t4.16\t1.5\t\n"
    bad += "0\t1\t1\t5921 \t8.1E-07\t63.1\t0\t3.95\t1.4\t\n"
    bad += "0\t1\t2\t9999 \t8.2E-07\t78.1\t0\t3.67\t1.3\t\n"  # wrong wavenumber
    d = _write_spectra_dir(tmp_path, "bad", bad)
    with pytest.raises(ReaderError, match="inconsistent wavenumber sweep"):
        read_neasnom_spectrum_measurement(d)


def test_pixel_area_header_mismatch_raises(tmp_path: Path) -> None:
    # Header claims 201 spectral points but the table only has 3 - must not be silent.
    bad = _SINGLE_POINT_HEADER.replace(
        '# Pixel Area (X, Y, Z):\t[px]\t1\t1\t3\n',
        '# Pixel Area (X, Y, Z):\t[px]\t1\t1\t201\n',
    )
    d = _write_spectra_dir(tmp_path, "mismatch", bad)
    with pytest.raises(ReaderError, match="Pixel Area"):
        read_neasnom_spectrum_measurement(d)


def test_missing_required_column_raises(tmp_path: Path) -> None:
    bad = _SINGLE_POINT_HEADER.replace("Wavenumber\t", "")
    d = _write_spectra_dir(tmp_path, "missing_col", bad)
    with pytest.raises(ReaderError, match="missing required column"):
        read_neasnom_spectrum_measurement(d)


def test_no_spectra_file_raises(tmp_path: Path) -> None:
    d = tmp_path / "empty"
    d.mkdir()
    with pytest.raises(ReaderError, match=r"no \*Spectra\.txt"):
        read_neasnom_spectrum_measurement(d)
