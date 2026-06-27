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
