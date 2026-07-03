"""Shared pytest configuration and fixtures.

``src`` is on the import path via ``[tool.pytest.ini_options] pythonpath`` in
``pyproject.toml``, so tests can ``import snomniman`` without an editable install.

Synthetic-data fixtures with analytically known answers (Rule 6) live here; the
golden-file fixtures point at the real neaSNOM GSF measurement directory and skip
cleanly when the sample data is absent.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import pytest
import xarray as xr

# GUI tests run headless: select Qt's offscreen platform before any QApplication
# is created. Harmless when PySide6 is not installed (GUI tests skip).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

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
    SpectralInfo,
    StepRecord,
)
from snomniman.io import write_gsf

_REPO_ROOT = Path(__file__).resolve().parents[1]

#: The real measurement directory analysed in docs/measurement-discovery.md.
SAMPLE_MEASUREMENT_DIR = (
    _REPO_ROOT
    / "SNOM Sample Files"
    / "2026-06-16 14928"
    / "2026-06-16 190234 PH CdO Dense ROI 2"
)

#: All four measurement runs present in the sample folder.
SAMPLE_PARENT = _REPO_ROOT / "SNOM Sample Files" / "2026-06-16 14928"


@pytest.fixture
def sample_measurement_dir() -> Path:
    """Path to the real neaSNOM measurement directory, or skip if absent."""
    if not SAMPLE_MEASUREMENT_DIR.is_dir():
        pytest.skip("real neaSNOM sample data not present")
    return SAMPLE_MEASUREMENT_DIR


@pytest.fixture(scope="session")
def qapp() -> Any:
    """A shared QApplication for GUI tests; skips cleanly without the gui extra."""
    pytest.importorskip("PySide6")
    import pyqtgraph as pg
    from PySide6 import QtWidgets

    pg.setConfigOptions(imageAxisOrder="row-major")
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def synthetic_dataset() -> Dataset:
    """A small but complete image Dataset (optical/mechanical/reference/topo).

    Shared by the viz, model, and GUI tests. Coordinates are in canonical nm with
    a known 50 nm pixel pitch over a 200 x 150 nm field, lower-left origin.
    """
    ny, nx = 3, 4
    y = (np.arange(ny, dtype=np.float64) + 0.5) * 50.0
    x = (np.arange(nx, dtype=np.float64) + 0.5) * 50.0
    amp = np.linspace(0.5, 2.0, ny * nx, dtype=np.float64).reshape(ny, nx)
    phase = np.linspace(-np.pi, np.pi, ny * nx, dtype=np.float64).reshape(ny, nx)
    o2 = (amp * np.exp(1j * phase)).astype(np.complex64)
    o3 = (amp * np.exp(1j * (0.5 * phase))).astype(np.complex64)
    r_o2 = (np.ones((ny, nx)) * np.exp(1j * 0.25)).astype(np.complex64)
    m1 = (amp * np.exp(1j * phase)).astype(np.complex64)
    z = (amp * 100.0).astype(np.float64)
    data = xr.Dataset(
        {
            "O2": (("y", "x"), o2),
            "O3": (("y", "x"), o3),
            "R_O2": (("y", "x"), r_o2),
            "M1": (("y", "x"), m1),
            "Z": (("y", "x"), z),
        },
        coords={
            "x": ("x", x, {"unit": "nm", "axis": "X"}),
            "y": ("y", y, {"unit": "nm", "axis": "Y"}),
        },
    )
    channels = (
        ChannelInfo("O2", "optical", "signal", "complex64", harmonic=2, amplitude_unit="a.u."),
        ChannelInfo("O3", "optical", "signal", "complex64", harmonic=3, amplitude_unit="a.u."),
        ChannelInfo("R_O2", "optical", "reference", "complex64", harmonic=2, amplitude_unit="a.u."),
        ChannelInfo("M1", "mechanical", "signal", "complex64", harmonic=1, amplitude_unit="a.u."),
        ChannelInfo("Z", "topography", "signal", "float64", value_unit="nm"),
    )
    metadata = Metadata(
        data_kind=DataKind.IMAGE,
        conventions=Conventions(),
        instrument=Instrument(vendor="neaspec", model="neaSNOM", software_version="2.2.0"),
        excitation=Excitation(source_type="Piano", detector="MIR", wavenumber_cm1=5973.0),
        demodulation=Demodulation(detection="PsHet", harmonics=(1, 2, 3)),
        scan=ScanInfo(
            pixels=(nx, ny),
            size_nm=(nx * 50.0, ny * 50.0),
            pixel_size_nm=(50.0, 50.0),
            offset_nm=(0.0, 0.0),
            rotation_deg=0.0,
        ),
        channels=channels,
        original_units={"x": "m", "y": "m", "Z": "m"},
    )
    node = ProvenanceNode(
        node_id="n0",
        record=StepRecord(step_id="io.read", step_version=1, deterministic=True),
    )
    return Dataset(data, kind=DataKind.IMAGE, metadata=metadata, provenance=node)


@pytest.fixture
def topography_dataset() -> Dataset:
    """A real-only 2-D scan (topography Z) - no complex optical or reference channels.

    Exercises the disabled-operation path of the Processing Workspace: operations
    that require complex/reference capabilities (e.g. reference_normalize) are
    unavailable on this dataset and must explain why.
    """
    ny, nx = 3, 4
    y = (np.arange(ny, dtype=np.float64) + 0.5) * 50.0
    x = (np.arange(nx, dtype=np.float64) + 0.5) * 50.0
    z = np.linspace(700.0, 900.0, ny * nx, dtype=np.float64).reshape(ny, nx)
    data = xr.Dataset(
        {"Z": (("y", "x"), z)},
        coords={
            "x": ("x", x, {"unit": "nm", "axis": "X"}),
            "y": ("y", y, {"unit": "nm", "axis": "Y"}),
        },
    )
    metadata = Metadata(
        data_kind=DataKind.IMAGE,
        conventions=Conventions(),
        instrument=Instrument(vendor="neaspec", model="neaSNOM"),
        excitation=Excitation(),
        demodulation=Demodulation(),
        scan=ScanInfo(
            pixels=(nx, ny), size_nm=(nx * 50.0, ny * 50.0), pixel_size_nm=(50.0, 50.0)
        ),
        channels=(ChannelInfo("Z", "topography", "signal", "float64", value_unit="nm"),),
        original_units={"x": "m", "y": "m", "Z": "m"},
    )
    node = ProvenanceNode(
        node_id="n0", record=StepRecord(step_id="io.read", step_version=1, deterministic=True)
    )
    return Dataset(data, kind=DataKind.IMAGE, metadata=metadata, provenance=node)


@pytest.fixture
def optical_only_dataset() -> Dataset:
    """A 2-D scan with a single complex optical signal channel - no topography, no references.

    Exercises reasoning-rule decline paths: plane leveling has no topography to act on,
    and reference normalization has no references (and the rule has no optical signal to
    normalize when used elsewhere). A degenerate but valid image dataset.
    """
    ny, nx = 3, 4
    y = (np.arange(ny, dtype=np.float64) + 0.5) * 50.0
    x = (np.arange(nx, dtype=np.float64) + 0.5) * 50.0
    o2 = (np.ones((ny, nx)) * np.exp(1j * 0.3)).astype(np.complex64)
    data = xr.Dataset(
        {"O2": (("y", "x"), o2)},
        coords={
            "x": ("x", x, {"unit": "nm", "axis": "X"}),
            "y": ("y", y, {"unit": "nm", "axis": "Y"}),
        },
    )
    metadata = Metadata(
        data_kind=DataKind.IMAGE,
        conventions=Conventions(),
        instrument=Instrument(),
        excitation=Excitation(),
        demodulation=Demodulation(),
        scan=ScanInfo(
            pixels=(nx, ny), size_nm=(nx * 50.0, ny * 50.0), pixel_size_nm=(50.0, 50.0)
        ),
        channels=(ChannelInfo("O2", "optical", "signal", "complex64", harmonic=2),),
    )
    node = ProvenanceNode(
        node_id="n0", record=StepRecord(step_id="io.read", step_version=1, deterministic=True)
    )
    return Dataset(data, kind=DataKind.IMAGE, metadata=metadata, provenance=node)


@pytest.fixture
def spectrum_dataset() -> Dataset:
    """A LINE_SCAN point-spectroscopy Dataset - dims (s, wavenumber), no 2-D grid.

    Shared by the describe/diagnostics/briefing/GUI tests that exercise the point
    spectrum vertical slice without needing the real sample directory. 6 positions
    along a line, each a 30-point spectrum; O2 varies by position + wavenumber so
    a position/channel switch is visibly different (useful for GUI assertions).
    """
    n_pos, n_wn = 6, 30
    s = (np.arange(n_pos, dtype=np.float64) + 0.5) * 20.0
    wn = 5920.0 + np.arange(n_wn, dtype=np.float64)
    amp = 1.0 + 0.1 * np.arange(n_pos, dtype=np.float64)[:, None] + 0.01 * np.arange(n_wn)[None, :]
    phase = np.linspace(-np.pi, np.pi, n_pos * n_wn).reshape(n_pos, n_wn)
    o2 = (amp * np.exp(1j * phase)).astype(np.complex64)
    z = (800.0 + np.arange(n_pos * n_wn, dtype=np.float64).reshape(n_pos, n_wn) * 0.01)
    data = xr.Dataset(
        {"O2": (("s", "wavenumber"), o2), "Z": (("s", "wavenumber"), z)},
        coords={
            "s": ("s", s, {"unit": "nm", "long_name": "scan distance", "axis": "s"}),
            "wavenumber": (
                "wavenumber", wn, {"unit": "cm-1", "long_name": "wavenumber", "axis": "wavenumber"}
            ),
        },
    )
    channels = (
        ChannelInfo("O2", "optical", "signal", "complex64", harmonic=2, amplitude_unit="a.u.",
                    phase_unit="rad"),
        ChannelInfo("Z", "topography", "signal", "float64", value_unit="nm"),
    )
    metadata = Metadata(
        data_kind=DataKind.LINE_SCAN,
        conventions=Conventions(),
        instrument=Instrument(vendor="neaspec", model="neaSNOM"),
        excitation=Excitation(source_type="Piano", detector="MIR"),
        demodulation=Demodulation(detection="PsHet", harmonics=(2,)),
        scan=ScanInfo(pixels=(n_pos, 1), size_nm=(n_pos * 20.0, 0.0), pixel_size_nm=(20.0, 0.0)),
        spectral=SpectralInfo(
            wavenumber_min_cm1=float(wn[0]), wavenumber_max_cm1=float(wn[-1]),
            n_points=n_wn, sampling_cm1=1.0,
        ),
        channels=channels,
        original_units={"wavenumber": "cm-1", "Z": "m"},
    )
    node = ProvenanceNode(
        node_id="n0", record=StepRecord(step_id="io.read", step_version=1, deterministic=True)
    )
    return Dataset(data, kind=DataKind.LINE_SCAN, metadata=metadata, provenance=node)


@pytest.fixture
def hyperspectral_dataset() -> Dataset:
    """A small HYPERSPECTRAL Dataset - dims ``(y, x, wavenumber)`` - with one known
    embedded resonance, for known-answer band-map/pixel-spectrum/ROI-spectrum tests
    (Rule 6). 4x5 spatial pixels (50 nm pitch), 25 wavenumber points (1700-1748
    cm-1, 2 cm-1 sampling). A Lorentzian bump (center 1724 cm-1 = wavenumber index
    12, width 8 cm-1) is embedded in ``O2`` amplitude **only at pixel (y=2, x=3)**;
    every other pixel has a flat baseline amplitude of 0.2 - so a pixel/ROI
    spectrum that includes (2, 3) recovers the bump, one that excludes it does not.
    """
    ny, nx, n_wn = 4, 5, 25
    y = (np.arange(ny, dtype=np.float64) + 0.5) * 50.0
    x = (np.arange(nx, dtype=np.float64) + 0.5) * 50.0
    wn = 1700.0 + np.arange(n_wn, dtype=np.float64) * 2.0

    peak_y, peak_x, peak_wn_index = 2, 3, 12
    center, width, baseline = float(wn[peak_wn_index]), 8.0, 0.2
    lorentzian = 1.0 / (1.0 + ((wn - center) / (width / 2.0)) ** 2)

    amp = np.full((ny, nx, n_wn), baseline, dtype=np.float64)
    amp[peak_y, peak_x, :] += lorentzian
    o2 = amp.astype(np.complex64)  # zero phase everywhere - keeps the fixture simple
    z = np.full((ny, nx), 800.0, dtype=np.float64)

    data = xr.Dataset(
        {
            "O2": (("y", "x", "wavenumber"), o2),
            "Z": (("y", "x"), z),
        },
        coords={
            "x": ("x", x, {"unit": "nm", "axis": "X"}),
            "y": ("y", y, {"unit": "nm", "axis": "Y"}),
            "wavenumber": ("wavenumber", wn, {"unit": "cm-1", "long_name": "wavenumber"}),
        },
    )
    channels = (
        ChannelInfo("O2", "optical", "signal", "complex64", harmonic=2, amplitude_unit="a.u.",
                    phase_unit="rad"),
        ChannelInfo("Z", "topography", "signal", "float64", value_unit="nm"),
    )
    metadata = Metadata(
        data_kind=DataKind.HYPERSPECTRAL,
        conventions=Conventions(),
        instrument=Instrument(vendor="neaspec", model="neaSNOM"),
        excitation=Excitation(source_type="Piano", detector="MIR"),
        demodulation=Demodulation(detection="PsHet", harmonics=(2,)),
        scan=ScanInfo(pixels=(nx, ny), size_nm=(nx * 50.0, ny * 50.0), pixel_size_nm=(50.0, 50.0)),
        spectral=SpectralInfo(
            wavenumber_min_cm1=float(wn[0]), wavenumber_max_cm1=float(wn[-1]),
            n_points=n_wn, sampling_cm1=2.0,
        ),
        channels=channels,
        original_units={"x": "m", "y": "m", "wavenumber": "cm-1", "Z": "m"},
    )
    node = ProvenanceNode(
        node_id="n0", record=StepRecord(step_id="io.read", step_version=1, deterministic=True)
    )
    return Dataset(data, kind=DataKind.HYPERSPECTRAL, metadata=metadata, provenance=node)


@pytest.fixture
def make_gsf(tmp_path: Path) -> Callable[..., Path]:
    """Factory writing a synthetic GSF file and returning its path."""

    def _make(
        data: npt.NDArray[np.float32],
        *,
        name: str = "channel.gsf",
        extra_header: Mapping[str, str] | None = None,
    ) -> Path:
        header = {
            "XReal": "1.000E-05",
            "YReal": "1.000E-05",
            "XOffset": "0.0",
            "YOffset": "0.0",
            "XYUnits": "m",
            "ZUnits": "",
        }
        if extra_header:
            header.update(extra_header)
        path = tmp_path / name
        write_gsf(path, np.asarray(data, dtype=np.float32), header)
        return path

    return _make
