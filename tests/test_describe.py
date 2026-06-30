"""Tests for the Scientific Description API (snomniman.describe).

The describe layer is a pure, read-only projection of the scientific core + the
processing registry into structured, JSON-serializable descriptors.  These tests
validate the projection on the shared synthetic dataset, on the real golden
measurement, and against the registry (isolated via monkeypatch where needed), and
assert the cardinal invariant that describing never mutates the dataset.
"""

from __future__ import annotations

import json
from collections.abc import Mapping

import numpy as np
import pytest
import xarray as xr

from snomniman.core import DataKind, Dataset, Metadata
from snomniman.core.exceptions import ProcessingError
from snomniman.describe import (
    MeasurementDescription,
    describe_channels,
    describe_measurement,
    describe_operation,
    describe_operations,
    summarize_metadata,
    summarize_provenance,
)
from snomniman.io import read
from snomniman.processing import ParameterSpec, ProcessingStep, register
from snomniman.processing import registry as _reg
from snomniman.processing.image.plane_level import PlaneLevel  # also registers the step

# --------------------------------------------------------------------------- #
# A synthetic operation for registry-isolated tests (never globally registered)
# --------------------------------------------------------------------------- #


class _Synthetic(ProcessingStep):
    step_id = "test.synthetic_describe"
    version = 2
    description = "Synthetic op for description tests."
    deterministic = False

    @classmethod
    def param_specs(cls) -> list[ParameterSpec]:
        return [
            ParameterSpec("amount", "How much.", (int, float), required=False, default=1.0)
        ]

    def _execute(
        self, inputs: Mapping[str, Dataset]
    ) -> tuple[xr.Dataset, DataKind, Metadata]:  # pragma: no cover - never applied
        raise NotImplementedError


# --------------------------------------------------------------------------- #
# Channels
# --------------------------------------------------------------------------- #


def test_describe_channels(synthetic_dataset: Dataset) -> None:
    channels = {c.canonical: c for c in describe_channels(synthetic_dataset)}
    assert set(channels) == {"O2", "O3", "R_O2", "M1", "Z"}

    o2 = channels["O2"]
    assert o2.kind == "optical" and o2.role == "signal" and o2.harmonic == 2
    assert o2.is_complex is True
    assert o2.dtype == "complex64"
    assert o2.available_views == ("amplitude", "phase")
    assert o2.amplitude_unit == "a.u."

    z = channels["Z"]
    assert z.kind == "topography" and z.is_complex is False
    assert z.dtype == "float64"
    assert z.value_unit == "nm"
    assert z.available_views == ("value",)

    assert channels["R_O2"].role == "reference"


# --------------------------------------------------------------------------- #
# Metadata
# --------------------------------------------------------------------------- #


def test_summarize_metadata(synthetic_dataset: Dataset) -> None:
    s = summarize_metadata(synthetic_dataset.metadata)
    assert s.data_kind == "image"
    assert s.vendor == "neaspec" and s.model == "neaSNOM"
    assert s.wavenumber_cm1 == 5973.0
    assert s.detection == "PsHet"
    assert s.harmonics == (1, 2, 3)
    # honest unknowns are None, not "unknown" strings
    assert s.wavelength_nm is None
    assert s.setpoint is None
    # conventions reported explicitly (OHD-6)
    assert s.conventions.spatial_unit == "nm"
    assert s.conventions.origin == "lower-left"
    assert s.conventions.phase_handling == "as imported"
    # geometry in canonical nm
    assert s.geometry.pixels == (4, 3)
    assert s.geometry.size_nm == (200.0, 150.0)
    assert s.original_units == {"x": "m", "y": "m", "Z": "m"}


# --------------------------------------------------------------------------- #
# Provenance
# --------------------------------------------------------------------------- #


def test_summarize_provenance_raw(synthetic_dataset: Dataset) -> None:
    p = summarize_provenance(synthetic_dataset.provenance)
    assert p.is_raw is True
    assert p.n_steps == 1
    assert p.steps[0].step_id == "io.read"
    assert p.steps[0].is_raw is True
    assert p.steps[0].inputs == ()
    assert p.steps[0].sources == ()
    assert p.sources == ()


def test_summarize_provenance_after_apply(synthetic_dataset: Dataset) -> None:
    leveled = PlaneLevel(channel="Z", order=1).apply({"primary": synthetic_dataset})
    p = summarize_provenance(leveled.provenance)
    assert p.is_raw is False
    assert p.n_steps == 2
    # topological order: the raw read precedes the step that consumed it
    assert p.steps[0].step_id == "io.read"
    last = p.steps[-1]
    assert last.step_id == "image.plane_level"
    assert last.inputs == ("primary",)
    assert last.params == {"channel": "Z", "order": 1}
    assert last.deterministic is True
    assert last.is_raw is False


# --------------------------------------------------------------------------- #
# Operations (registry catalogue)
# --------------------------------------------------------------------------- #


def test_describe_operations_lists_registered(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_reg, "_REGISTRY", {})
    register(_Synthetic)
    ops = describe_operations()
    assert [o.step_id for o in ops] == ["test.synthetic_describe"]
    op = ops[0]
    assert op.version == 2
    assert op.deterministic is False
    assert len(op.parameters) == 1
    param = op.parameters[0]
    assert param.name == "amount"
    assert param.required is False
    assert param.default == 1.0
    assert set(param.types) == {"int", "float"}


def test_describe_operation_unknown_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_reg, "_REGISTRY", {})
    with pytest.raises(ProcessingError):
        describe_operation("does.not.exist")


def test_describe_operation_real_plane_level() -> None:
    # PlaneLevel is registered in the real registry (imported at module top).
    op = describe_operation("image.plane_level")
    assert op.deterministic is True
    by_name = {p.name: p for p in op.parameters}
    assert set(by_name) == {"channel", "order"}
    assert by_name["channel"].default == "Z"
    assert by_name["order"].default == 1


def test_describe_projects_single_input_slot_by_default() -> None:
    # A single-input operation projects exactly one "primary" slot (the default).
    op = describe_operation("image.plane_level")
    assert [s.name for s in op.inputs] == ["primary"]


def test_describe_projects_multi_input_slots() -> None:
    # The two-input arithmetic operation projects both its declared input slots.
    op = describe_operation("image.arithmetic")
    assert [s.name for s in op.inputs] == ["primary", "secondary"]
    assert all(slot.description for slot in op.inputs)  # each slot is labelled


# --------------------------------------------------------------------------- #
# Aggregate + JSON + invariants
# --------------------------------------------------------------------------- #


def test_describe_measurement_aggregate(synthetic_dataset: Dataset) -> None:
    d = describe_measurement(synthetic_dataset, title="synthetic")
    assert isinstance(d, MeasurementDescription)
    assert d.title == "synthetic"
    assert d.data_kind == "image"
    assert d.is_raw is True
    assert d.dims == {"y": 3, "x": 4}
    assert set(d.capabilities) == {
        "spatial_2d",
        "complex_optical",
        "complex_mechanical",
        "topography",
        "reference",
        "multi_harmonic",
    }
    assert len(d.channels) == 5
    assert d.metadata.data_kind == "image"
    assert d.provenance.is_raw is True


def test_describe_measurement_json_round_trip(synthetic_dataset: Dataset) -> None:
    d = describe_measurement(synthetic_dataset)
    blob = json.dumps(d.to_dict())
    reloaded = json.loads(blob)
    assert reloaded == d.to_dict()
    assert reloaded["metadata"]["conventions"]["origin"] == "lower-left"
    assert isinstance(reloaded["channels"], list)


def test_describe_does_not_mutate_dataset(synthetic_dataset: Dataset) -> None:
    before = np.array(synthetic_dataset.channel("O2").values, copy=True)
    describe_measurement(synthetic_dataset)
    after = synthetic_dataset.channel("O2").values
    np.testing.assert_array_equal(after, before)
    # arrays remain frozen (raw immutability preserved)
    assert after.flags.writeable is False


# --------------------------------------------------------------------------- #
# Golden (real CdO measurement)
# --------------------------------------------------------------------------- #


def test_describe_measurement_golden(sample_measurement_dir: object) -> None:
    ds = read(sample_measurement_dir)  # type: ignore[arg-type]
    d = describe_measurement(ds, title="CdO")
    assert d.data_kind == "image"
    assert d.is_raw is True
    assert "spatial_2d" in d.capabilities
    assert "topography" in d.capabilities
    assert len(d.channels) == len(ds.channel_names)
    assert d.metadata.wavenumber_cm1 is not None

    prov = d.provenance
    assert prov.is_raw is True
    assert prov.n_steps == 1
    assert prov.sources, "raw import must record at least one source"
    src = prov.sources[0]
    assert src.is_directory is True
    assert len(src.sha256) == 64
    assert src.reader

    # the whole description is JSON-serializable (no verbatim header bloat leaks in)
    json.dumps(d.to_dict())
