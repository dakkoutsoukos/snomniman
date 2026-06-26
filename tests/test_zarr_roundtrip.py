"""Round-trip tests for the canonical Zarr store (Dataset -> Zarr -> Dataset).

Closes the final Phase-1 Definition-of-Done item and enforces the data-model.md
sec 11 invariant: a ``Dataset -> Zarr -> Dataset`` round-trip preserves data,
coordinates, units, conventions, metadata, provenance, and source without loss.

Two complementary fixtures are exercised:

* a hand-built **synthetic** dataset with analytically known content (complex
  optical/mechanical channels, a multi-harmonic set, a reference channel, float64
  and float32 topography), non-default conventions, fully populated typed
  metadata, a real ``RawSource``, and a **multi-node** provenance DAG; and
* the real **golden** neaSNOM measurement (skipped when the sample data is absent).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from snomniman.core import (
    Acquisition,
    ChannelInfo,
    Conventions,
    DataKind,
    Dataset,
    Demodulation,
    Excitation,
    Instrument,
    Metadata,
    ProvenanceNode,
    RawSource,
    ReaderError,
    ScanInfo,
    StepRecord,
    serialize_dag,
)
from snomniman.io import STORE_FORMAT, read_neasnom_measurement, read_zarr, write_zarr

_REPO_ROOT = Path(__file__).resolve().parents[1]
_GOLDEN_DIR = (
    _REPO_ROOT / "SNOM Sample Files" / "2026-06-16 14928" / "2026-06-16 190234 PH CdO Dense ROI 2"
)


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


def _synthetic_dataset() -> Dataset:
    """A content-rich synthetic dataset with a known answer and a 2-node DAG."""
    ny, nx = 5, 4
    y = (np.arange(ny, dtype=np.float64) + 0.5) * 12.5
    x = (np.arange(nx, dtype=np.float64) + 0.5) * 12.5
    amp = np.linspace(0.5, 3.0, ny * nx, dtype=np.float64).reshape(ny, nx)
    phase = np.linspace(-np.pi, np.pi, ny * nx, dtype=np.float64).reshape(ny, nx)
    o2 = (amp * np.exp(1j * phase)).astype(np.complex64)
    o3 = (amp * np.exp(1j * (0.5 * phase))).astype(np.complex64)
    r_o2 = (np.ones((ny, nx)) * np.exp(1j * 0.25)).astype(np.complex64)
    m1 = (amp * np.exp(1j * (phase - 0.1))).astype(np.complex64)
    z = (amp * 100.0).astype(np.float64)  # topography in nm (float64)
    z_c = (amp * 0.5).astype(np.float32)  # a real variant (float32)

    data = xr.Dataset(
        {
            "O2": (("y", "x"), o2),
            "O3": (("y", "x"), o3),
            "R_O2": (("y", "x"), r_o2),
            "M1": (("y", "x"), m1),
            "Z": (("y", "x"), z),
            "Z_C": (("y", "x"), z_c),
        },
        coords={
            "x": ("x", x, {"unit": "nm", "long_name": "x (fast scan axis)", "axis": "X"}),
            "y": ("y", y, {"unit": "nm", "long_name": "y (slow scan axis)", "axis": "Y"}),
        },
    )

    channels = (
        ChannelInfo("O2", "optical", "signal", "complex64", harmonic=2,
                    amplitude_unit="a.u.", phase_unit="rad", vendor_token="O2 raw",
                    source_files=("m O2A raw.gsf", "m O2P raw.gsf")),
        ChannelInfo("O3", "optical", "signal", "complex64", harmonic=3,
                    amplitude_unit="a.u.", phase_unit="rad"),
        ChannelInfo("R_O2", "optical", "reference", "complex64", harmonic=2,
                    amplitude_unit="a.u.", phase_unit="rad"),
        ChannelInfo("M1", "mechanical", "signal", "complex64", harmonic=1,
                    amplitude_unit="a.u.", phase_unit="rad"),
        ChannelInfo("Z", "topography", "signal", "float64", value_unit="nm"),
        ChannelInfo("Z_C", "topography", "signal", "float32", value_unit="a.u."),
    )
    metadata = Metadata(
        data_kind=DataKind.IMAGE,
        # Non-default conventions to prove they persist verbatim (OHD-6).
        conventions=Conventions(phase_reference="referenced-to-R_O2", phase_sign="+"),
        instrument=Instrument(vendor="neaspec", model="neaSNOM", software_version="2.2.14109.0"),
        excitation=Excitation(source_type="Piano", detector="MIR", wavenumber_cm1=5973.0),
        demodulation=Demodulation(detection="PsHet", harmonics=(0, 1, 2, 3)),
        scan=ScanInfo(
            pixels=(nx, ny),
            size_nm=(nx * 12.5, ny * 12.5),
            center_nm=(25.0, 31.25),
            offset_nm=(0.0, 0.0),
            pixel_size_nm=(12.5, 12.5),
            rotation_deg=0.0,
        ),
        acquisition=Acquisition(
            datetime="2026-06-16T19:02:34",
            integration_time_s=0.121,
            tapping_amplitude_nm=53.079,
            setpoint=80.48,
            averaging=1,
        ),
        channels=channels,
        original_units={"x": "m", "y": "m", "Z": "m", "wavenumber": "cm-1"},
        # Nested verbatim header (JSON-native types only, as real readers produce).
        raw_header={
            "parameter_file": {
                "lines": ["# neaspec", "# Version:\t2.2.14109.0"],
                "records": [{"label": "Version", "unit": None, "values": ["2.2.14109.0"]}],
            },
            "gsf_header_sample": {"XRes": "4", "YRes": "5", "XYUnits": "m"},
        },
    )

    source = RawSource(
        path="data/synthetic measurement",
        sha256="0" * 64,
        reader="neasnom.image.gsf.v1",
        reader_params={"channel_map": "default"},
        bytes=123456,
        is_directory=True,
        manifest=(("m O2A raw.gsf", "a" * 64), ("m O2P raw.gsf", "b" * 64)),
        imported_at="2026-06-16T19:05:00+00:00",
    )
    # A 2-node DAG: io.read (n0) -> a recorded processing step (n1, the root). This
    # exercises multi-node + source persistence and the non-raw (derived) path.
    read_node = ProvenanceNode(
        node_id="n0",
        record=StepRecord(
            step_id="io.read", step_version=1, deterministic=True,
            params={"reader": source.reader}, applied_at="2026-06-16T19:05:01+00:00",
            input_fingerprint=f"sha256:{source.sha256}",
        ),
        sources={"source": source},
    )
    root = ProvenanceNode(
        node_id="n1",
        record=StepRecord(
            step_id="image.demo_step", step_version=2, deterministic=True,
            params={"channel": "O2", "order": 1}, applied_at="2026-06-16T19:05:02+00:00",
            notes="synthetic derived node",
        ),
        inputs={"primary": read_node},
    )

    return Dataset(data, kind=DataKind.IMAGE, metadata=metadata, provenance=root, source=source)


@pytest.fixture
def synthetic() -> Dataset:
    return _synthetic_dataset()


@pytest.fixture
def golden() -> Dataset:
    if not _GOLDEN_DIR.is_dir():
        pytest.skip("real neaSNOM sample data not present")
    return read_neasnom_measurement(_GOLDEN_DIR)


def _roundtrip(dataset: Dataset, tmp_path: Path) -> Dataset:
    store = write_zarr(dataset, tmp_path / "store.zarr")
    return read_zarr(store)


def _assert_equivalent(original: Dataset, loaded: Dataset) -> None:
    """Assert a loaded dataset reconstructs the complete scientific state."""
    # Kind + derived capabilities + raw/derived flag.
    assert loaded.kind is original.kind
    assert loaded.capabilities == original.capabilities
    assert loaded.is_raw == original.is_raw

    # Channels: same set, dtypes preserved (complex stays complex), exact values,
    # coordinates, units and per-array attrs (xr identical = names+dims+values+attrs).
    assert set(loaded.channel_names) == set(original.channel_names)
    for name in original.channel_names:
        assert loaded.channel(name).dtype == original.channel(name).dtype, name
    xr.testing.assert_identical(loaded.data, original.data)

    # Typed metadata incl. the explicit conventions (full value equality).
    assert loaded.metadata == original.metadata
    assert loaded.metadata.to_dict() == original.metadata.to_dict()
    assert loaded.metadata.conventions == original.metadata.conventions

    # Provenance DAG (serialized-form equality is the established idiom).
    assert serialize_dag(loaded.provenance) == serialize_dag(original.provenance)

    # Raw-source anchor.
    if original.source is None:
        assert loaded.source is None
    else:
        assert loaded.source is not None
        assert loaded.source == original.source
        assert loaded.source.to_dict() == original.source.to_dict()


# --------------------------------------------------------------------------- #
# Synthetic round-trip
# --------------------------------------------------------------------------- #


def test_synthetic_roundtrip_is_equivalent(synthetic: Dataset, tmp_path: Path) -> None:
    _assert_equivalent(synthetic, _roundtrip(synthetic, tmp_path))


def test_write_returns_store_path(synthetic: Dataset, tmp_path: Path) -> None:
    store = write_zarr(synthetic, tmp_path / "s.zarr")
    assert store == tmp_path / "s.zarr"
    assert store.is_dir()  # a Zarr store is a directory tree


def test_channel_equality_preserves_complex_dtype(synthetic: Dataset, tmp_path: Path) -> None:
    loaded = _roundtrip(synthetic, tmp_path)
    assert loaded.channel("O2").dtype == np.complex64
    assert loaded.channel("Z").dtype == np.float64
    assert loaded.channel("Z_C").dtype == np.float32
    # Bit-identical channel values, including the complex ones.
    for name in synthetic.channel_names:
        np.testing.assert_array_equal(loaded.channel(name).values, synthetic.channel(name).values)


def test_coordinate_equality(synthetic: Dataset, tmp_path: Path) -> None:
    loaded = _roundtrip(synthetic, tmp_path)
    for axis in ("x", "y"):
        np.testing.assert_array_equal(
            loaded.coordinate(axis).values, synthetic.coordinate(axis).values
        )
        assert loaded.coordinate(axis).attrs["unit"] == "nm"
        assert loaded.coordinate(axis).dtype == synthetic.coordinate(axis).dtype


def test_metadata_equality(synthetic: Dataset, tmp_path: Path) -> None:
    loaded = _roundtrip(synthetic, tmp_path)
    assert loaded.metadata == synthetic.metadata
    # Nested verbatim header and per-channel descriptors survive intact.
    assert loaded.metadata.raw_header == synthetic.metadata.raw_header
    assert loaded.metadata.channel("O2").source_files == ("m O2A raw.gsf", "m O2P raw.gsf")
    assert loaded.metadata.original_units == synthetic.metadata.original_units


def test_convention_equality(synthetic: Dataset, tmp_path: Path) -> None:
    loaded = _roundtrip(synthetic, tmp_path)
    conv = loaded.metadata.conventions
    assert conv == synthetic.metadata.conventions
    assert conv.spatial_unit == "nm"
    assert conv.origin == "lower-left"
    assert conv.x_dir == "right" and conv.y_dir == "up"
    assert conv.phase_reference == "referenced-to-R_O2"
    assert conv.phase_sign == "+"


def test_provenance_equality_multinode(synthetic: Dataset, tmp_path: Path) -> None:
    loaded = _roundtrip(synthetic, tmp_path)
    assert serialize_dag(loaded.provenance) == serialize_dag(synthetic.provenance)
    # The full two-node DAG and its leaf source survived.
    assert len(list(loaded.provenance.iter_nodes())) == 2
    assert loaded.provenance.node_id == "n1"
    assert loaded.is_raw is False
    sources = list(loaded.provenance.iter_sources())
    assert len(sources) == 1 and sources[0].reader == "neasnom.image.gsf.v1"


def test_source_equality(synthetic: Dataset, tmp_path: Path) -> None:
    loaded = _roundtrip(synthetic, tmp_path)
    assert loaded.source is not None
    assert loaded.source == synthetic.source
    assert loaded.source.is_directory is True
    assert loaded.source.manifest == (("m O2A raw.gsf", "a" * 64), ("m O2P raw.gsf", "b" * 64))


def test_capabilities_recomputed_match(synthetic: Dataset, tmp_path: Path) -> None:
    loaded = _roundtrip(synthetic, tmp_path)
    # Capabilities are derived from the data on load, so they cannot drift.
    assert loaded.capabilities == synthetic.capabilities


def test_loaded_dataset_is_immutable(synthetic: Dataset, tmp_path: Path) -> None:
    loaded = _roundtrip(synthetic, tmp_path)
    with pytest.raises(ValueError, match=r"read-only|assignment"):
        loaded.channel("Z").data[0, 0] = 0.0
    with pytest.raises(ValueError, match=r"read-only|assignment"):
        loaded.coordinate("x").data[0] = -1.0


def test_amplitude_phase_views_after_roundtrip(synthetic: Dataset, tmp_path: Path) -> None:
    loaded = _roundtrip(synthetic, tmp_path)
    o2 = loaded.channel("O2").values
    np.testing.assert_allclose(loaded.amplitude("O2").values, np.abs(o2), rtol=1e-6)
    np.testing.assert_allclose(loaded.phase("O2").values, np.angle(o2), rtol=1e-6)


def test_source_none_roundtrips(tmp_path: Path) -> None:
    base = _synthetic_dataset()
    raw_node = ProvenanceNode(
        node_id="n0",
        record=StepRecord(step_id="io.read", step_version=1, deterministic=True),
    )
    no_source = Dataset(
        base.data.copy(), kind=base.kind, metadata=base.metadata, provenance=raw_node, source=None
    )
    loaded = _roundtrip(no_source, tmp_path)
    assert loaded.source is None
    assert loaded.is_raw is True


# --------------------------------------------------------------------------- #
# Guards
# --------------------------------------------------------------------------- #


def test_overwrite_false_refuses_existing(synthetic: Dataset, tmp_path: Path) -> None:
    store = tmp_path / "store.zarr"
    write_zarr(synthetic, store)
    with pytest.raises(FileExistsError):
        write_zarr(synthetic, store, overwrite=False)
    # The original store is intact and still loads.
    assert read_zarr(store).kind is DataKind.IMAGE


def test_read_rejects_non_store(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ReaderError, match="not a readable Zarr store"):
        read_zarr(empty)


def test_read_rejects_foreign_zarr(tmp_path: Path) -> None:
    foreign = tmp_path / "foreign.zarr"
    xr.Dataset({"a": ("x", np.arange(3.0))}).to_zarr(foreign, mode="w", consolidated=False)
    with pytest.raises(ReaderError, match="not a SNOMNIMAN dataset store"):
        read_zarr(foreign)


# --------------------------------------------------------------------------- #
# Golden (real-measurement) round-trip
# --------------------------------------------------------------------------- #


def test_golden_roundtrip_is_equivalent(golden: Dataset, tmp_path: Path) -> None:
    _assert_equivalent(golden, _roundtrip(golden, tmp_path))


def test_golden_roundtrip_is_raw_and_self_consistent(golden: Dataset, tmp_path: Path) -> None:
    loaded = _roundtrip(golden, tmp_path)
    assert loaded.is_raw is True
    assert len(loaded.channel_names) == 32
    assert dict(loaded.data.sizes) == {"y": 150, "x": 150}
    # Store carries the SNOMNIMAN format marker in its provenance/metadata pathway.
    assert loaded.source is not None and loaded.source.reader == "neasnom.image.gsf.v1"


def test_golden_channel_values_bit_identical(golden: Dataset, tmp_path: Path) -> None:
    loaded = _roundtrip(golden, tmp_path)
    for name in golden.channel_names:
        np.testing.assert_array_equal(
            loaded.channel(name).values, golden.channel(name).values, err_msg=name
        )
    # The complex optical channel keeps its exact complex64 representation.
    assert loaded.channel("O2").dtype == np.complex64
    np.testing.assert_array_equal(loaded.amplitude("O2").values, golden.amplitude("O2").values)


def test_store_format_constant_is_stable() -> None:
    # A guard so the on-disk format marker is not changed casually.
    assert STORE_FORMAT == "snomniman.dataset"
