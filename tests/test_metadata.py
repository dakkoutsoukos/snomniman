"""Unit tests for typed Metadata: defaults, lookup, and JSON round-trip."""

from __future__ import annotations

import json

from snomniman.core import (
    Acquisition,
    ChannelInfo,
    Conventions,
    DataKind,
    Demodulation,
    Excitation,
    Instrument,
    Metadata,
    ScanInfo,
    SpectralInfo,
)


def _full_metadata() -> Metadata:
    return Metadata(
        data_kind=DataKind.IMAGE,
        conventions=Conventions(),
        instrument=Instrument(vendor="neaspec", software_version="2.2.14109.0"),
        excitation=Excitation(source_type="Piano", detector="MIR", wavenumber_cm1=5973.0),
        demodulation=Demodulation(detection="PsHet", harmonics=(0, 1, 2, 3, 4, 5)),
        scan=ScanInfo(
            pixels=(150, 150),
            size_nm=(10000.0, 10000.0),
            center_nm=(60810.0, 14160.0),
            offset_nm=(55811.8, 9163.7),
            pixel_size_nm=(66.667, 66.667),
            rotation_deg=0.0,
        ),
        acquisition=Acquisition(
            datetime="2026-06-16T19:02:34",
            integration_time_s=0.121,
            tapping_amplitude_nm=53.079,
            setpoint=80.48,
            averaging=1,
        ),
        channels=(
            ChannelInfo("O2", "optical", "signal", "complex64", harmonic=2,
                        amplitude_unit="a.u.", phase_unit="rad",
                        vendor_token="O2 raw", source_files=("O2A raw.gsf", "O2P raw.gsf")),
            ChannelInfo("Z", "topography", "signal", "float64", value_unit="nm",
                        vendor_token="Z raw", source_files=("Z raw.gsf",)),
        ),
        original_units={"x": "m", "y": "m", "Z": "m", "wavenumber": "cm-1"},
        raw_header={"parameter_file": {"lines": ["# www.neaspec.com"]}, "gsf": {"XRes": "150"}},
    )


def test_default_conventions_are_canonical() -> None:
    c = Conventions()
    assert c.spatial_unit == "nm"
    assert c.origin == "lower-left"
    assert c.x_dir == "right"
    assert c.y_dir == "up"
    assert c.phase_unit == "rad"
    # Phase reference/sign unknown until measured -> explicit None, never guessed.
    assert c.phase_reference is None
    assert c.phase_sign is None


def test_channel_lookup() -> None:
    md = _full_metadata()
    assert md.channel("O2").harmonic == 2
    assert md.channel("Z").value_unit == "nm"
    try:
        md.channel("missing")
    except KeyError:
        pass
    else:  # pragma: no cover
        raise AssertionError("expected KeyError")


def test_to_dict_is_json_serializable_and_round_trips() -> None:
    md = _full_metadata()
    as_dict = md.to_dict()
    # Survives an actual JSON encode/decode (Zarr attrs / project JSON path).
    restored = Metadata.from_dict(json.loads(json.dumps(as_dict)))
    assert restored.to_dict() == as_dict
    assert restored.data_kind is DataKind.IMAGE
    assert restored.excitation.wavenumber_cm1 == 5973.0
    assert restored.demodulation.harmonics == (0, 1, 2, 3, 4, 5)
    assert restored.scan.pixels == (150, 150)
    assert restored.channel("O2").source_files == ("O2A raw.gsf", "O2P raw.gsf")


def test_raw_header_preserved_verbatim() -> None:
    md = _full_metadata()
    assert md.raw_header["parameter_file"]["lines"] == ["# www.neaspec.com"]
    # Round-trip keeps it byte-for-byte (treated strictly as data).
    restored = Metadata.from_dict(md.to_dict())
    assert restored.raw_header == md.raw_header


def test_spectral_defaults_to_none() -> None:
    # Imaging metadata never sets it - additive field, existing readers unaffected.
    md = _full_metadata()
    assert md.spectral is None
    restored = Metadata.from_dict(md.to_dict())
    assert restored.spectral is None


def test_spectral_info_round_trips() -> None:
    md = Metadata(
        data_kind=DataKind.LINE_SCAN,
        spectral=SpectralInfo(
            wavenumber_min_cm1=5920.0, wavenumber_max_cm1=6120.0, n_points=201, sampling_cm1=1.0
        ),
    )
    as_dict = md.to_dict()
    restored = Metadata.from_dict(json.loads(json.dumps(as_dict)))
    assert restored.spectral == SpectralInfo(
        wavenumber_min_cm1=5920.0, wavenumber_max_cm1=6120.0, n_points=201, sampling_cm1=1.0
    )
    assert restored.data_kind is DataKind.LINE_SCAN
