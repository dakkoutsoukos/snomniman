"""The :class:`Project` bundle, its :class:`Measurement`s, and on-disk persistence.

A *project* is a whole analysis session that may hold **many measurements**. Each
:class:`Measurement` is an independent scientific object: an immutable raw dataset,
every dataset derived from it (its derivation history), which one is currently
active, and an opaque per-measurement session document (the GUI's view + overlay
state). A :class:`Project` owns an ordered collection of measurements, remembers
which one is active, and carries its own small project-level session document.

This is a deliberate *promotion* of the original single-measurement project model:
what used to be a ``Project`` (a tuple of datasets = one measurement's history) is
now a :class:`Measurement`, and ``Project`` is the new level above it (a tuple of
measurements). The dataset-history semantics are unchanged - ``datasets[0]`` is
conventionally the raw measurement and later entries are derivations.

Persistence reuses the **canonical Zarr store** (``snomniman.io.write_zarr`` /
``read_zarr``) rather than inventing a second serialization of a ``Dataset``: a
project is a directory bundle holding one Zarr store per dataset (grouped by
measurement) plus a small JSON manifest. Because every dataset already carries its
complete provenance DAG, the processing history is preserved for free - reopening a
project restores the same derivation graphs the session built, with raw data still
immutable and every result still reconstructable from its sources (Rule 5).

Layout of a saved project (a ``<name>.snomproj`` directory)::

    <name>.snomproj/
        project.json                                 # the manifest
        measurements/
            measurement_00/
                datasets/
                    dataset_00.zarr/                 # canonical Zarr store (io.write_zarr)
                    dataset_01.zarr/
            measurement_01/
                datasets/
                    dataset_00.zarr/
            ...

On-disk directory names are **ordinal** (``measurement_00`` reflects display order
at save time); a measurement's stable, human-readable identity (``measurement-0001``)
lives in the manifest, so reordering or removing measurements never churns paths.

The manifest records the project title, the active ``current_index``, an opaque
project-level ``session`` document, and one entry per measurement (its id, title,
active ``current_index``, opaque per-measurement ``session``, and dataset paths).
``pipeline`` treats every ``session`` as pass-through data: it serializes and
restores it but assigns it no meaning, so GUI-level state (titles, the active view,
measurement overlays, the measurement-id counter) round-trips without coupling this
backend layer to any view semantics.

Schema version 1 bundles (a single-measurement project) are still readable: they
are migrated on load into a project with exactly one measurement, with the v1
session re-homed onto that measurement.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from snomniman.core import Dataset, current_software
from snomniman.core.exceptions import ReaderError
from snomniman.io import read_zarr, write_zarr

#: Marks a directory as a SNOMNIMAN project bundle (guards against opening junk).
PROJECT_FORMAT = "snomniman.project"

#: Bumped when the manifest layout changes (supports forward-compatible loads).
#: v1 = single-measurement (top-level ``datasets``); v2 = multi-measurement.
PROJECT_SCHEMA_VERSION = 2

#: The manifest file name inside a project bundle.
MANIFEST_NAME = "project.json"

#: Subdirectory holding the per-measurement subtrees.
_MEASUREMENTS_DIR = "measurements"

#: Fallback id for the single measurement migrated from a v1 bundle.
_FIRST_MEASUREMENT_ID = "measurement-0001"


@dataclass(frozen=True)
class Measurement:
    """One scientific object: a dataset history, which is active, and session state.

    ``datasets`` is ordered oldest-to-newest (``datasets[0]`` is conventionally the
    raw measurement; later entries are derivations). ``current_index`` selects the
    active dataset. ``measurement_id`` is a stable, project-local, human-readable
    handle (e.g. ``measurement-0001``); ``title`` is the editable display name.
    ``session`` is an opaque, JSON-serializable mapping the caller (the GUI) uses to
    persist this measurement's view/layout and overlay state; this layer stores and
    returns it verbatim.
    """

    measurement_id: str
    title: str
    datasets: tuple[Dataset, ...]
    current_index: int = 0
    session: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.datasets:
            raise ValueError("a Measurement must contain at least one dataset")
        if not 0 <= self.current_index < len(self.datasets):
            raise ValueError(
                f"current_index {self.current_index} out of range for "
                f"{len(self.datasets)} dataset(s)"
            )

    @property
    def current(self) -> Dataset:
        """The active dataset (the one the session is currently working on)."""
        return self.datasets[self.current_index]

    @property
    def raw(self) -> Dataset:
        """The first (conventionally the raw) dataset in this measurement."""
        return self.datasets[0]


@dataclass(frozen=True)
class Project:
    """An analysis session: an ordered set of measurements and which is active.

    ``measurements`` is ordered (its order is the display order). ``current_index``
    selects the active measurement. ``session`` is an opaque, JSON-serializable
    mapping for project-level state (e.g. the measurement-id counter); this layer
    stores and returns it verbatim. A project with a single measurement is the
    common case and behaves like the original single-measurement project.
    """

    title: str
    measurements: tuple[Measurement, ...]
    current_index: int = 0
    session: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.measurements:
            raise ValueError("a Project must contain at least one measurement")
        if not 0 <= self.current_index < len(self.measurements):
            raise ValueError(
                f"current_index {self.current_index} out of range for "
                f"{len(self.measurements)} measurement(s)"
            )

    @property
    def current_measurement(self) -> Measurement:
        """The active measurement."""
        return self.measurements[self.current_index]

    @property
    def current_dataset(self) -> Dataset:
        """The active dataset of the active measurement (the working dataset)."""
        return self.current_measurement.current


def save_project(project: Project, path: str | Path, *, overwrite: bool = False) -> Path:
    """Write ``project`` to a ``.snomproj`` bundle at ``path``; return the path.

    Each measurement's datasets are persisted with :func:`snomniman.io.write_zarr`
    (loss-less, provenance intact) under ``measurements/measurement_NN/datasets/``,
    alongside a ``project.json`` manifest. With ``overwrite=False`` an existing
    ``path`` raises ``FileExistsError``. With ``overwrite=True`` an existing path is
    replaced **only** if it is empty or an existing SNOMNIMAN project bundle; any
    other existing directory is refused (this never clobbers unrelated data).
    """
    bundle = Path(path)
    if bundle.exists():
        if not overwrite:
            raise FileExistsError(f"project already exists (overwrite=False): {bundle}")
        if not _is_project_bundle(bundle) and any(bundle.iterdir()):
            raise FileExistsError(
                f"{bundle} exists and is not a SNOMNIMAN project; refusing to overwrite"
            )
        shutil.rmtree(bundle)

    (bundle / _MEASUREMENTS_DIR).mkdir(parents=True)

    entries: list[dict[str, Any]] = []
    for m_index, measurement in enumerate(project.measurements):
        m_dir = f"{_MEASUREMENTS_DIR}/measurement_{m_index:02d}"
        rel_paths: list[str] = []
        for d_index, dataset in enumerate(measurement.datasets):
            rel = f"{m_dir}/datasets/dataset_{d_index:02d}.zarr"
            write_zarr(dataset, bundle / rel, overwrite=True)
            rel_paths.append(rel)
        entries.append(
            {
                "id": measurement.measurement_id,
                "title": measurement.title,
                "current_index": measurement.current_index,
                "session": dict(measurement.session),
                "datasets": rel_paths,
            }
        )

    manifest: dict[str, Any] = {
        "format": PROJECT_FORMAT,
        "schema_version": PROJECT_SCHEMA_VERSION,
        "title": project.title,
        "current_index": project.current_index,
        "session": dict(project.session),
        "measurements": entries,
        "created_at": datetime.now(UTC).isoformat(),
        "software": current_software(),
    }
    (bundle / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return bundle


def load_project(path: str | Path) -> Project:
    """Load a ``.snomproj`` bundle written by :func:`save_project` into a ``Project``.

    Every dataset is restored with :func:`snomniman.io.read_zarr`, so each comes
    back with its channels, metadata, conventions, provenance DAG, and raw-source
    anchor intact and immutable. Schema-version-1 (single-measurement) bundles are
    migrated into a one-measurement project. Raises :class:`ReaderError` if ``path``
    is not a readable SNOMNIMAN project bundle.
    """
    bundle = Path(path)
    manifest = _load_manifest(bundle)
    if int(manifest.get("schema_version", 0)) <= 1:
        return _load_v1(bundle, manifest)

    entries = manifest.get("measurements")
    if not isinstance(entries, list) or not entries:
        raise ReaderError(f"project manifest in {bundle} lists no measurements")
    measurements = tuple(_load_measurement(bundle, entry) for entry in entries)
    return Project(
        title=str(manifest.get("title", bundle.stem)),
        measurements=measurements,
        current_index=int(manifest.get("current_index", 0)),
        session=_as_mapping(manifest.get("session")),
    )


def measurement_from_history(
    datasets: Sequence[Dataset],
    *,
    title: str,
    measurement_id: str = _FIRST_MEASUREMENT_ID,
    current_index: int | None = None,
    session: Mapping[str, Any] | None = None,
) -> Measurement:
    """Build a :class:`Measurement` from a derivation history (newest active).

    A convenience for the common case where ``datasets`` is the linear history of a
    measurement (raw first, then each derivation) and the last one is active.
    """
    if current_index is None:
        current_index = len(datasets) - 1
    return Measurement(
        measurement_id=measurement_id,
        title=title,
        datasets=tuple(datasets),
        current_index=current_index,
        session=dict(session) if session is not None else {},
    )


def project_from_history(
    datasets: Sequence[Dataset],
    *,
    title: str,
    current_index: int | None = None,
    session: Mapping[str, Any] | None = None,
) -> Project:
    """Build a single-measurement :class:`Project` from a derivation history.

    A convenience wrapper around :func:`measurement_from_history` for the common
    single-measurement case (the session document is attached to that measurement).
    """
    measurement = measurement_from_history(
        datasets, title=title, current_index=current_index, session=session
    )
    return Project(title=title, measurements=(measurement,))


def _load_measurement(bundle: Path, entry: Mapping[str, Any]) -> Measurement:
    """Restore one measurement from its manifest entry."""
    rel_paths = entry.get("datasets")
    if not isinstance(rel_paths, list) or not rel_paths:
        raise ReaderError(f"a measurement in {bundle} lists no datasets")
    datasets = tuple(read_zarr(bundle / rel) for rel in rel_paths)
    return Measurement(
        measurement_id=str(entry.get("id", _FIRST_MEASUREMENT_ID)),
        title=str(entry.get("title", "measurement")),
        datasets=datasets,
        current_index=int(entry.get("current_index", 0)),
        session=_as_mapping(entry.get("session")),
    )


def _load_v1(bundle: Path, manifest: Mapping[str, Any]) -> Project:
    """Migrate a schema-version-1 (single-measurement) bundle into a Project.

    A v1 bundle stored one measurement's history at the top level (``datasets``)
    with the per-measurement view/overlay state in ``session``. That maps exactly
    onto a project with a single measurement: the datasets and session move onto
    the measurement, and the project-level session starts empty.
    """
    rel_paths = manifest.get("datasets")
    if not isinstance(rel_paths, list) or not rel_paths:
        raise ReaderError(f"project manifest in {bundle} lists no datasets")
    datasets = tuple(read_zarr(bundle / rel) for rel in rel_paths)
    title = str(manifest.get("title", bundle.stem))
    measurement = Measurement(
        measurement_id=_FIRST_MEASUREMENT_ID,
        title=title,
        datasets=datasets,
        current_index=int(manifest.get("current_index", 0)),
        session=_as_mapping(manifest.get("session")),
    )
    return Project(title=title, measurements=(measurement,))


def _is_project_bundle(path: Path) -> bool:
    """True iff ``path`` looks like a SNOMNIMAN project bundle (safe to replace)."""
    manifest = path / MANIFEST_NAME
    if not manifest.is_file():
        return False
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):  # pragma: no cover - corrupt/locked
        return False
    return isinstance(data, dict) and data.get("format") == PROJECT_FORMAT


def _load_manifest(bundle: Path) -> dict[str, Any]:
    """Read and validate the project manifest, or raise :class:`ReaderError`."""
    manifest_path = bundle / MANIFEST_NAME
    if not manifest_path.is_file():
        raise ReaderError(
            f"{bundle} is not a SNOMNIMAN project (missing {MANIFEST_NAME})"
        )
    try:
        manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - corrupt manifest
        raise ReaderError(f"corrupt project manifest in {bundle}: {exc}") from exc

    if manifest.get("format") != PROJECT_FORMAT:
        raise ReaderError(
            f"unexpected project format {manifest.get('format')!r} in {bundle}; "
            f"expected {PROJECT_FORMAT!r}"
        )
    version = manifest.get("schema_version", 0)
    if not isinstance(version, int) or version > PROJECT_SCHEMA_VERSION:
        raise ReaderError(
            f"project schema version {version} in {bundle} is newer than this build "
            f"supports (<= {PROJECT_SCHEMA_VERSION}); upgrade SNOMNIMAN"
        )
    return manifest


def _as_mapping(value: Any) -> dict[str, Any]:
    """Coerce a manifest ``session`` field to a dict (tolerate corrupt/missing)."""
    return dict(value) if isinstance(value, dict) else {}


__all__ = [
    "MANIFEST_NAME",
    "PROJECT_FORMAT",
    "PROJECT_SCHEMA_VERSION",
    "Measurement",
    "Project",
    "load_project",
    "measurement_from_history",
    "project_from_history",
    "save_project",
]
