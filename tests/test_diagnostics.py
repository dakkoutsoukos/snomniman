"""Tests for snomniman.diagnostics - the Scientific Diagnostics Engine.

Every diagnostic is validated against a known answer (Rule 6): synthetic tilted
planes with exact slopes, constant fields with zero roughness, injected NaNs with
exact invalid counts, and analytically-equal harmonic amplitudes. Applicability is
checked structurally against declared capabilities. No heuristic assertions.
"""

from __future__ import annotations

import json

import numpy as np
import numpy.typing as npt
import pytest
import xarray as xr

# Importing the image sub-package registers image.plane_level (needed for the
# applicability diagnostics, mirroring how the GUI ensures registration).
import snomniman.processing.image  # noqa: F401
from snomniman.core import (
    ChannelInfo,
    DataKind,
    Dataset,
    Metadata,
    ProvenanceNode,
    StepRecord,
)
from snomniman.diagnostics import (
    channel_statistics,
    diagnose,
    operation_applicability,
    topography_diagnostics,
)
from snomniman.processing.image.plane_level import PlaneLevel

# --------------------------------------------------------------------------- #
# Local dataset builders
# --------------------------------------------------------------------------- #


def _topo_dataset(
    z: npt.NDArray[np.float64],
    x: npt.NDArray[np.float64],
    y: npt.NDArray[np.float64],
) -> Dataset:
    """A Dataset with a single real topography channel 'Z' (height in nm)."""
    data = xr.Dataset(
        {"Z": (("y", "x"), z)},
        coords={
            "x": ("x", x, {"unit": "nm", "axis": "X"}),
            "y": ("y", y, {"unit": "nm", "axis": "Y"}),
        },
    )
    meta = Metadata(
        data_kind=DataKind.IMAGE,
        channels=(ChannelInfo("Z", "topography", "signal", "float64", value_unit="nm"),),
    )
    node = ProvenanceNode(
        node_id="n0",
        record=StepRecord(step_id="io.read", step_version=1, deterministic=True),
    )
    return Dataset(data, kind=DataKind.IMAGE, metadata=meta, provenance=node)


def _line_dataset() -> Dataset:
    """A 1-D (line) Dataset - has SPATIAL_1D but not SPATIAL_2D."""
    x = np.linspace(0.0, 100.0, 8)
    data = xr.Dataset(
        {"O2": (("x",), np.ones(8, dtype=np.float64))},
        coords={"x": ("x", x, {"unit": "nm", "axis": "X"})},
    )
    node = ProvenanceNode(
        node_id="n0",
        record=StepRecord(step_id="io.read", step_version=1, deterministic=True),
    )
    return Dataset(
        data, kind=DataKind.IMAGE, metadata=Metadata(data_kind=DataKind.IMAGE), provenance=node
    )


def _tilted_plane(
    nx: int, ny: int, ax: float, ay: float, c: float
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    x = np.linspace(25.0, 975.0, nx)
    y = np.linspace(25.0, 975.0, ny)
    xx, yy = np.meshgrid(x, y)
    z = ax * xx + ay * yy + c
    return z.astype(np.float64), x, y


# --------------------------------------------------------------------------- #
# Channel statistics
# --------------------------------------------------------------------------- #


def test_real_channel_statistics(synthetic_dataset: Dataset) -> None:
    report = diagnose(synthetic_dataset)
    z = next(s for s in report.channel_statistics if s.channel == "Z")
    assert z.view == "value" and z.unit == "nm"
    # Z = amp * 100 with amp in [0.5, 2.0] -> [50, 200].
    assert z.minimum == pytest.approx(50.0)
    assert z.maximum == pytest.approx(200.0)
    assert z.dynamic_range == pytest.approx(150.0)
    assert z.invalid_count == 0 and z.finite_count == z.count


def test_complex_channel_statistics_use_amplitude(synthetic_dataset: Dataset) -> None:
    report = diagnose(synthetic_dataset)
    o2 = next(s for s in report.channel_statistics if s.channel == "O2")
    assert o2.view == "amplitude" and o2.unit == "a.u."
    assert o2.minimum == pytest.approx(0.5) and o2.maximum == pytest.approx(2.0)


def test_invalid_values_are_counted() -> None:
    z, x, y = _tilted_plane(4, 3, ax=0.0, ay=0.0, c=10.0)
    z = z.copy()
    z[0, 0] = np.nan
    z[1, 2] = np.inf
    stats = channel_statistics(_topo_dataset(z, x, y), "Z")
    assert stats.count == 12 and stats.invalid_count == 2 and stats.finite_count == 10
    # The constant remainder is all 10.0.
    assert stats.minimum == pytest.approx(10.0) and stats.maximum == pytest.approx(10.0)


# --------------------------------------------------------------------------- #
# Topography
# --------------------------------------------------------------------------- #


def test_topography_slope_recovers_known_tilt() -> None:
    # ax,ay are gradients per nm; per-micrometre is x1000.
    z, x, y = _tilted_plane(20, 25, ax=0.002, ay=0.001, c=50.0)
    topo = topography_diagnostics(_topo_dataset(z, x, y))
    assert topo is not None
    assert topo.channel == "Z" and topo.unit == "nm"
    assert topo.slope_x_per_um == pytest.approx(2.0)
    assert topo.slope_y_per_um == pytest.approx(1.0)
    assert topo.slope_magnitude_per_um == pytest.approx(np.hypot(2.0, 1.0))
    # A pure plane has no roughness once the plane is removed.
    assert topo.rms_roughness == pytest.approx(0.0, abs=1e-9)


def test_topography_height_range() -> None:
    z, x, y = _tilted_plane(10, 10, ax=0.002, ay=0.001, c=50.0)
    topo = topography_diagnostics(_topo_dataset(z, x, y))
    assert topo is not None
    assert topo.height_range == pytest.approx(float(z.max() - z.min()))


def test_topography_absent_returns_none() -> None:
    assert topography_diagnostics(_line_dataset()) is None


# --------------------------------------------------------------------------- #
# Harmonics
# --------------------------------------------------------------------------- #


def test_harmonic_amplitudes_and_decay(synthetic_dataset: Dataset) -> None:
    report = diagnose(synthetic_dataset)
    assert report.harmonics is not None
    # Only optical *signal* harmonics: O2, O3 (R_O2 is a reference, M1 mechanical).
    assert report.harmonics.harmonics == (2, 3)
    by_order = {a.order: a for a in report.harmonics.amplitudes}
    assert by_order[2].decay_ratio is None  # lowest present order
    # O2 and O3 share the same amplitude field in the fixture -> ratio 1.0.
    assert by_order[3].decay_ratio == pytest.approx(1.0)


# --------------------------------------------------------------------------- #
# Harmonic signal-vs-noise classification (docs/harmonic-ranking-analysis.md)
# --------------------------------------------------------------------------- #


def _optical_dataset(amplitudes: dict[int, npt.NDArray[np.float64]]) -> Dataset:
    """A 2-D Dataset whose complex optical channel O{n} has amplitude ``amplitudes[n]``.

    Each channel is stored as ``amplitude + 0j`` so the amplitude view is exactly the
    supplied (non-negative) image - giving the classifier an analytically known input.
    """
    ny, nx = next(iter(amplitudes.values())).shape
    y = (np.arange(ny, dtype=np.float64) + 0.5) * 50.0
    x = (np.arange(nx, dtype=np.float64) + 0.5) * 50.0
    data = xr.Dataset(
        {f"O{n}": (("y", "x"), img.astype(np.complex128)) for n, img in amplitudes.items()},
        coords={
            "x": ("x", x, {"unit": "nm", "axis": "X"}),
            "y": ("y", y, {"unit": "nm", "axis": "Y"}),
        },
    )
    channels = tuple(
        ChannelInfo(f"O{n}", "optical", "signal", "complex128", harmonic=n) for n in amplitudes
    )
    meta = Metadata(data_kind=DataKind.IMAGE, channels=channels)
    node = ProvenanceNode(
        node_id="n0", record=StepRecord(step_id="io.read", step_version=1, deterministic=True)
    )
    return Dataset(data, kind=DataKind.IMAGE, metadata=meta, provenance=node)


def _smooth_field(ny: int = 64, nx: int = 64) -> npt.NDArray[np.float64]:
    """A smooth, band-limited near-field-like image (broad Gaussian blobs), all positive."""
    yy, xx = np.mgrid[0:ny, 0:nx].astype(np.float64)
    f = np.zeros((ny, nx))
    for cy, cx, s in [(20, 24, 12.0), (44, 40, 16.0)]:
        f += np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * s * s))
    return f + 5.0


def test_pure_smooth_signal_classifies_as_signal() -> None:
    # Analytical anchor: a smooth field has spatial coherence ~1 -> "signal".
    ds = _optical_dataset({2: _smooth_field()})
    harm = diagnose(ds).harmonics
    assert harm is not None
    a = harm.amplitudes[0]
    assert a.spatial_coherence is not None and a.spatial_coherence > 0.95
    assert a.classification == "signal"


def test_pure_white_noise_classifies_as_noise() -> None:
    # Analytical anchor: white-noise amplitude has coherence ~0 -> "noise".
    rng = np.random.default_rng(20260628)
    amp = np.abs(rng.standard_normal((96, 96)) + 1j * rng.standard_normal((96, 96)))
    a = diagnose(_optical_dataset({3: amp})).harmonics.amplitudes[0]  # type: ignore[union-attr]
    assert a.spatial_coherence is not None and abs(a.spatial_coherence) < 0.1
    assert a.snr_estimate is not None and a.snr_estimate < 0.5
    assert a.classification == "noise"


def test_checkerboard_is_incoherent_noise() -> None:
    # A perfect checkerboard is maximally anti-correlated (coherence ~ -1): not signal.
    yy, xx = np.mgrid[0:32, 0:32]
    amp = (((xx + yy) % 2) + 1.0).astype(np.float64)  # alternating 1.0 / 2.0
    a = diagnose(_optical_dataset({2: amp})).harmonics.amplitudes[0]  # type: ignore[union-attr]
    assert a.spatial_coherence is not None and a.spatial_coherence < 0.0
    assert a.classification == "noise"


def test_empty_channel_classifies_as_empty() -> None:
    # A not-recorded harmonic (identically zero) is flagged, never fed to the classifier.
    a = diagnose(_optical_dataset({5: np.zeros((40, 40))})).harmonics.amplitudes[0]  # type: ignore[union-attr]
    assert a.classification == "empty"
    assert a.spatial_coherence is None and a.snr_estimate is None


def test_snr_crossover_known_answer() -> None:
    # Synthetic SNR sweep: high SNR -> signal, low SNR -> noise; SNR estimate ~ true SNR.
    rng = np.random.default_rng(7)
    base = _smooth_field(80, 80)
    base = (base - base.mean()) / base.std()  # unit-variance signal shape
    noise = rng.standard_normal((80, 80))
    strong = np.abs(4.0 * base + 6.0 + noise)  # true amplitude SNR ~ 4
    weak = np.abs(0.3 * base + 6.0 + noise)  # true amplitude SNR ~ 0.3
    ds = _optical_dataset({2: strong, 4: weak})
    by_order = {a.order: a for a in diagnose(ds).harmonics.amplitudes}  # type: ignore[union-attr]
    assert by_order[2].classification == "signal"
    assert by_order[2].snr_estimate == pytest.approx(4.0, rel=0.25)
    assert by_order[4].classification == "noise"


def test_small_image_classification_is_unknown(synthetic_dataset: Dataset) -> None:
    # The 3x4 fixture is too small for a meaningful estimate -> honest "unknown".
    harm = diagnose(synthetic_dataset).harmonics
    assert harm is not None
    for a in harm.amplitudes:
        assert a.classification == "unknown"
        assert a.spatial_coherence is None and a.snr_estimate is None


# --------------------------------------------------------------------------- #
# Applicability
# --------------------------------------------------------------------------- #


def test_plane_level_applicable_to_image(synthetic_dataset: Dataset) -> None:
    apps = {a.step_id: a for a in operation_applicability(synthetic_dataset)}
    pl = apps["image.plane_level"]
    assert pl.applicable is True
    assert pl.required_capabilities == ("spatial_2d",)
    assert pl.missing_capabilities == ()
    assert pl.already_applied is False


def test_plane_level_inapplicable_to_line() -> None:
    apps = {a.step_id: a for a in operation_applicability(_line_dataset())}
    pl = apps["image.plane_level"]
    assert pl.applicable is False
    assert pl.missing_capabilities == ("spatial_2d",)


def test_already_applied_tracks_provenance(synthetic_dataset: Dataset) -> None:
    leveled = PlaneLevel(channel="Z", order=1).apply({"primary": synthetic_dataset})
    apps = {a.step_id: a for a in operation_applicability(leveled)}
    assert apps["image.plane_level"].already_applied is True


def test_applicability_grows_with_the_vocabulary(synthetic_dataset: Dataset) -> None:
    # Newly-registered operations appear in applicability with NO diagnostics changes.
    apps = {a.step_id: a for a in operation_applicability(synthetic_dataset)}
    for step_id in (
        "image.plane_level",
        "image.line_flatten",
        "image.reference_normalize",
        "image.phase_unwrap",
        "image.crop",
    ):
        assert step_id in apps, f"{step_id} not surfaced in applicability"
        assert apps[step_id].applicable is True  # synthetic has 2D + complex optical + reference


# --------------------------------------------------------------------------- #
# Serialization and immutability
# --------------------------------------------------------------------------- #


def test_report_is_json_serializable(synthetic_dataset: Dataset) -> None:
    payload = diagnose(synthetic_dataset, title="demo").to_dict()
    text = json.dumps(payload)  # raises if any value is not JSON-ready
    assert json.loads(text)["title"] == "demo"


def test_diagnose_does_not_mutate_dataset(synthetic_dataset: Dataset) -> None:
    before = {
        n: synthetic_dataset.channel(n).values.copy() for n in synthetic_dataset.channel_names
    }
    diagnose(synthetic_dataset)
    for name, values in before.items():
        np.testing.assert_array_equal(synthetic_dataset.channel(name).values, values)
