"""Round-trip tests for the project bundle (Project -> .snomproj -> Project).

A project is the whole analysis session: the raw measurement, every derivation, the
active selection, and an opaque session document (view + measurements). Saving and
reopening it must restore all of that without loss - this is what lets a researcher
stop and resume work. Persistence reuses the canonical Zarr store, so each dataset
comes back with its channels, metadata, conventions, provenance DAG, and source
anchor intact (the Zarr round-trip is separately covered by ``test_zarr_roundtrip``).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import snomniman.processing.image  # noqa: F401  (registers image ops)
from snomniman.core import Dataset, serialize_dag
from snomniman.core.exceptions import ReaderError
from snomniman.pipeline import (
    PROJECT_FORMAT,
    Project,
    load_project,
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
def project(synthetic_dataset: Dataset) -> Project:
    raw = synthetic_dataset
    derived = _level(raw)
    session = {
        "titles": ["CdO raw", "CdO raw -> plane level (Z)"],
        "view": {"channel": "O2", "representation": "amplitude", "mode": "single"},
        "measurements": [
            {"kind": "rectangle", "name": "Particle", "visible": True,
             "geometry": {"pos": [50.0, 50.0], "size": [60.0, 40.0]}},
        ],
    }
    return Project(title="CdO session", datasets=(raw, derived), current_index=1, session=session)


# --------------------------------------------------------------------------- #
# Round-trip
# --------------------------------------------------------------------------- #


def test_save_returns_bundle_path(project: Project, tmp_path: Path) -> None:
    bundle = save_project(project, tmp_path / "session.snomproj")
    assert bundle == tmp_path / "session.snomproj"
    assert (bundle / "project.json").is_file()
    assert (bundle / "datasets" / "dataset_00.zarr").is_dir()
    assert (bundle / "datasets" / "dataset_01.zarr").is_dir()


def test_roundtrip_restores_every_dataset(project: Project, tmp_path: Path) -> None:
    bundle = save_project(project, tmp_path / "s.snomproj")
    loaded = load_project(bundle)
    assert len(loaded.datasets) == len(project.datasets)
    for got, want in zip(loaded.datasets, project.datasets, strict=True):
        _assert_dataset_equivalent(got, want)


def test_roundtrip_restores_current_and_session(project: Project, tmp_path: Path) -> None:
    loaded = load_project(save_project(project, tmp_path / "s.snomproj"))
    assert loaded.title == "CdO session"
    assert loaded.current_index == 1
    assert loaded.current.is_raw is False  # the derived dataset is active
    assert loaded.raw.is_raw is True
    assert loaded.session == project.session  # opaque session round-trips verbatim


def test_derived_dataset_keeps_its_provenance(project: Project, tmp_path: Path) -> None:
    loaded = load_project(save_project(project, tmp_path / "s.snomproj"))
    derived = loaded.datasets[1]
    step_ids = [n.record.step_id for n in derived.provenance.iter_nodes()]
    assert step_ids == ["io.read", "image.plane_level"]


def test_project_from_history_defaults_to_newest_active(synthetic_dataset: Dataset) -> None:
    raw = synthetic_dataset
    derived = _level(raw)
    proj = project_from_history([raw, derived], title="t")
    assert proj.current_index == 1 and proj.current is derived


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
    smaller = Project(title="just raw", datasets=(project.datasets[0],), current_index=0)
    save_project(smaller, bundle, overwrite=True)
    loaded = load_project(bundle)
    assert loaded.title == "just raw"
    assert len(loaded.datasets) == 1  # stale dataset_01 is gone


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


def test_project_requires_at_least_one_dataset() -> None:
    with pytest.raises(ValueError, match="at least one dataset"):
        Project(title="empty", datasets=())


def test_project_validates_current_index(synthetic_dataset: Dataset) -> None:
    with pytest.raises(ValueError, match="out of range"):
        Project(title="t", datasets=(synthetic_dataset,), current_index=3)


def test_project_format_constant_is_stable() -> None:
    assert PROJECT_FORMAT == "snomniman.project"
