"""Round-trip tests for the project bundle (Project -> .snomproj -> Project).

A project is a whole analysis session that may hold many measurements. Each
measurement is an independent scientific object: a raw dataset, every derivation,
the active selection, and an opaque session document (view + overlays). Saving and
reopening a project must restore all of that for every measurement without loss -
this is what lets a researcher stop and resume work. Persistence reuses the
canonical Zarr store, so each dataset comes back with its channels, metadata,
conventions, provenance DAG, and source anchor intact (the Zarr round-trip is
separately covered by ``test_zarr_roundtrip``).

A single-measurement project (the common case) must keep behaving exactly like the
original single-measurement model, and schema-version-1 bundles must still load.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import snomniman.processing.image  # noqa: F401  (registers image ops)
from snomniman.core import Dataset, serialize_dag
from snomniman.core.exceptions import ReaderError
from snomniman.io import write_zarr
from snomniman.pipeline import (
    PROJECT_FORMAT,
    Measurement,
    Project,
    load_project,
    measurement_from_history,
    project_from_history,
    save_project,
)
from snomniman.processing import get_step


def _level(dataset: Dataset) -> Dataset:
    """A derived dataset: plane-level the topography (gives a 2-node provenance DAG)."""
    return get_step("image.plane_level")(channel="Z", order=1).apply({"primary": dataset})


def _assert_dataset_equivalent(loaded: Dataset, original: Dataset) -> None:
    assert loaded.kind is original.kind
    assert loaded.capabilities == original.capabilities
    assert loaded.is_raw == original.is_raw
    assert set(loaded.channel_names) == set(original.channel_names)
    for name in original.channel_names:
        np.testing.assert_array_equal(
            loaded.channel(name).values, original.channel(name).values, err_msg=name
        )
        assert loaded.channel(name).dtype == original.channel(name).dtype
    assert loaded.metadata == original.metadata
    assert serialize_dag(loaded.provenance) == serialize_dag(original.provenance)


@pytest.fixture
def measurement(synthetic_dataset: Dataset) -> Measurement:
    """A measurement with a 2-dataset history (raw + leveled), the derived one active."""
    raw = synthetic_dataset
    return Measurement(
        measurement_id="measurement-0001",
        title="CdO Dense ROI",
        datasets=(raw, _level(raw)),
        current_index=1,
        session={
            "titles": ["CdO raw", "CdO raw -> plane level (Z)"],
            "view": {"channel": "O2", "representation": "amplitude", "mode": "single"},
            "measurements": [
                {"kind": "rectangle", "name": "Particle", "visible": True,
                 "geometry": {"pos": [50.0, 50.0], "size": [60.0, 40.0]}},
            ],
        },
    )


@pytest.fixture
def project(measurement: Measurement, synthetic_dataset: Dataset) -> Project:
    """A two-measurement project: one with a history, one raw-only; the second active."""
    second = Measurement(
        measurement_id="measurement-0002",
        title="CdO Sparse ROI",
        datasets=(synthetic_dataset,),
        current_index=0,
    )
    return Project(
        title="CdO session",
        measurements=(measurement, second),
        current_index=1,
        session={"next_measurement_seq": 3},
    )


# --------------------------------------------------------------------------- #
# Round-trip (multi-measurement)
# --------------------------------------------------------------------------- #


def test_save_returns_bundle_path_with_measurement_layout(
    project: Project, tmp_path: Path
) -> None:
    bundle = save_project(project, tmp_path / "session.snomproj")
    assert bundle == tmp_path / "session.snomproj"
    assert (bundle / "project.json").is_file()
    # measurement 0 has a 2-dataset history, measurement 1 has one dataset.
    assert (bundle / "measurements" / "measurement_00" / "datasets" / "dataset_00.zarr").is_dir()
    assert (bundle / "measurements" / "measurement_00" / "datasets" / "dataset_01.zarr").is_dir()
    assert (bundle / "measurements" / "measurement_01" / "datasets" / "dataset_00.zarr").is_dir()


def test_roundtrip_restores_every_measurement_and_dataset(
    project: Project, tmp_path: Path
) -> None:
    loaded = load_project(save_project(project, tmp_path / "s.snomproj"))
    assert len(loaded.measurements) == len(project.measurements)
    for got_m, want_m in zip(loaded.measurements, project.measurements, strict=True):
        assert got_m.measurement_id == want_m.measurement_id
        assert got_m.title == want_m.title
        assert got_m.current_index == want_m.current_index
        assert got_m.session == want_m.session
        assert len(got_m.datasets) == len(want_m.datasets)
        for got, want in zip(got_m.datasets, want_m.datasets, strict=True):
            _assert_dataset_equivalent(got, want)


def test_roundtrip_restores_active_measurement_and_project_session(
    project: Project, tmp_path: Path
) -> None:
    loaded = load_project(save_project(project, tmp_path / "s.snomproj"))
    assert loaded.title == "CdO session"
    assert loaded.current_index == 1
    assert loaded.current_measurement.measurement_id == "measurement-0002"
    # The active measurement's active dataset is the working dataset.
    assert loaded.current_dataset.is_raw is True  # measurement-0002 has only its raw
    assert loaded.measurements[0].current.is_raw is False  # measurement-0001 active = derived
    assert loaded.session == {"next_measurement_seq": 3}  # project-level session round-trips


def test_derived_dataset_keeps_its_provenance(project: Project, tmp_path: Path) -> None:
    loaded = load_project(save_project(project, tmp_path / "s.snomproj"))
    derived = loaded.measurements[0].datasets[1]
    step_ids = [n.record.step_id for n in derived.provenance.iter_nodes()]
    assert step_ids == ["io.read", "image.plane_level"]


# --------------------------------------------------------------------------- #
# Single-measurement equivalence (a one-measurement project == the old model)
# --------------------------------------------------------------------------- #


def test_single_measurement_project_roundtrips(
    synthetic_dataset: Dataset, tmp_path: Path
) -> None:
    raw = synthetic_dataset
    proj = project_from_history([raw, _level(raw)], title="solo")
    loaded = load_project(save_project(proj, tmp_path / "solo.snomproj"))
    assert len(loaded.measurements) == 1
    only = loaded.current_measurement
    assert only.current_index == 1  # newest active
    assert only.current.is_raw is False
    assert only.raw.is_raw is True


def test_measurement_from_history_defaults_to_newest_active(
    synthetic_dataset: Dataset,
) -> None:
    raw = synthetic_dataset
    derived = _level(raw)
    m = measurement_from_history([raw, derived], title="t")
    assert m.current_index == 1 and m.current is derived


def test_project_from_history_builds_one_measurement(synthetic_dataset: Dataset) -> None:
    raw = synthetic_dataset
    proj = project_from_history([raw, _level(raw)], title="t")
    assert len(proj.measurements) == 1
    assert proj.current_index == 0
    assert proj.current_measurement.current_index == 1
    assert proj.current_dataset.is_raw is False


# --------------------------------------------------------------------------- #
# Schema-version-1 migration (old single-measurement bundles still load)
# --------------------------------------------------------------------------- #


def test_loads_and_migrates_a_v1_bundle(synthetic_dataset: Dataset, tmp_path: Path) -> None:
    """A v1 bundle (top-level ``datasets`` + ``session``) migrates to one measurement."""
    bundle = tmp_path / "legacy.snomproj"
    raw = synthetic_dataset
    derived = _level(raw)
    write_zarr(raw, bundle / "datasets" / "dataset_00.zarr", overwrite=True)
    write_zarr(derived, bundle / "datasets" / "dataset_01.zarr", overwrite=True)
    v1_manifest = {
        "format": PROJECT_FORMAT,
        "schema_version": 1,
        "title": "legacy session",
        "current_index": 1,
        "datasets": ["datasets/dataset_00.zarr", "datasets/dataset_01.zarr"],
        "session": {"view": {"channel": "O3", "representation": "amplitude"}},
    }
    (bundle / "project.json").write_text(json.dumps(v1_manifest), encoding="utf-8")

    loaded = load_project(bundle)
    assert loaded.title == "legacy session"
    assert len(loaded.measurements) == 1
    migrated = loaded.current_measurement
    assert migrated.measurement_id == "measurement-0001"
    assert migrated.title == "legacy session"
    assert migrated.current_index == 1
    assert migrated.current.is_raw is False
    # The v1 session (per-measurement view) is re-homed onto the measurement.
    assert migrated.session == {"view": {"channel": "O3", "representation": "amplitude"}}
    assert loaded.session == {}  # project-level session starts empty after migration


# --------------------------------------------------------------------------- #
# Guards
# --------------------------------------------------------------------------- #


def test_overwrite_false_refuses_existing(project: Project, tmp_path: Path) -> None:
    bundle = save_project(project, tmp_path / "s.snomproj")
    with pytest.raises(FileExistsError):
        save_project(project, bundle, overwrite=False)
    # The original bundle is intact and still loads.
    assert load_project(bundle).title == "CdO session"


def test_overwrite_true_replaces_existing_project(project: Project, tmp_path: Path) -> None:
    bundle = save_project(project, tmp_path / "s.snomproj")
    smaller = project_from_history([project.measurements[0].raw], title="just raw")
    save_project(smaller, bundle, overwrite=True)
    loaded = load_project(bundle)
    assert loaded.title == "just raw"
    assert len(loaded.measurements) == 1  # stale measurement_01 is gone
    assert len(loaded.measurements[0].datasets) == 1  # stale dataset_01 is gone


def test_overwrite_refuses_non_project_directory(project: Project, tmp_path: Path) -> None:
    foreign = tmp_path / "not_a_project"
    foreign.mkdir()
    (foreign / "important.txt").write_text("keep me", encoding="utf-8")
    with pytest.raises(FileExistsError, match="not a SNOMNIMAN project"):
        save_project(project, foreign, overwrite=True)
    assert (foreign / "important.txt").read_text(encoding="utf-8") == "keep me"


def test_load_rejects_missing_manifest(tmp_path: Path) -> None:
    empty = tmp_path / "empty.snomproj"
    empty.mkdir()
    with pytest.raises(ReaderError, match="not a SNOMNIMAN project"):
        load_project(empty)


def test_load_rejects_foreign_format(tmp_path: Path) -> None:
    bundle = tmp_path / "foreign.snomproj"
    bundle.mkdir()
    (bundle / "project.json").write_text('{"format": "something.else"}', encoding="utf-8")
    with pytest.raises(ReaderError, match="unexpected project format"):
        load_project(bundle)


def test_load_rejects_newer_schema(tmp_path: Path) -> None:
    bundle = tmp_path / "future.snomproj"
    bundle.mkdir()
    (bundle / "project.json").write_text(
        json.dumps({"format": PROJECT_FORMAT, "schema_version": 999}), encoding="utf-8"
    )
    with pytest.raises(ReaderError, match="newer than this build"):
        load_project(bundle)


def test_project_requires_at_least_one_measurement() -> None:
    with pytest.raises(ValueError, match="at least one measurement"):
        Project(title="empty", measurements=())


def test_project_validates_current_index(measurement: Measurement) -> None:
    with pytest.raises(ValueError, match="out of range"):
        Project(title="t", measurements=(measurement,), current_index=3)


def test_measurement_requires_at_least_one_dataset() -> None:
    with pytest.raises(ValueError, match="at least one dataset"):
        Measurement(measurement_id="measurement-0001", title="t", datasets=())


def test_measurement_validates_current_index(synthetic_dataset: Dataset) -> None:
    with pytest.raises(ValueError, match="out of range"):
        Measurement(
            measurement_id="measurement-0001",
            title="t",
            datasets=(synthetic_dataset,),
            current_index=3,
        )


def test_project_format_constant_is_stable() -> None:
    assert PROJECT_FORMAT == "snomniman.project"
