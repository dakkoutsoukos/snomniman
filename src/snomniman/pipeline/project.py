"""The :class:`Project` bundle and its on-disk persistence (OHD-5 reproducibility).

A *project* is a whole analysis session: the immutable raw measurement, every
derived dataset produced from it, which one is currently active, and the
application's session state (the active view and the read-only measurements placed
on the image). Saving a project and reopening it later is what lets a researcher
stop work and resume exactly where they left off.

Persistence reuses the **canonical Zarr store** (``snomniman.io.write_zarr`` /
``read_zarr``) rather than inventing a second serialization of a ``Dataset``: a
project is a directory bundle holding one Zarr store per dataset plus a small JSON
manifest. Because every dataset already carries its complete provenance DAG, the
processing history is preserved for free - reopening a project restores the same
derivation graph the session built, with raw data still immutable and every result
still reconstructable from its sources (Rule 5).

Layout of a saved project (a ``<name>.snomproj`` directory)::

    <name>.snomproj/
        project.json                     # the manifest (format, order, session)
        datasets/
            dataset_00.zarr/             # canonical Zarr store (io.write_zarr)
            dataset_01.zarr/
            ...

The manifest records the dataset order, the ``current_index``, and an opaque
``session`` document. ``pipeline`` treats ``session`` as pass-through data: it
serializes and restores it but assigns it no meaning, so GUI-level session state
(titles, the active view, measurement overlays) round-trips without coupling this
backend layer to any view semantics.
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
PROJECT_SCHEMA_VERSION = 1

#: The manifest file name inside a project bundle.
MANIFEST_NAME = "project.json"

#: Subdirectory holding the per-dataset Zarr stores.
_DATASETS_DIR = "datasets"


@dataclass(frozen=True)
class Project:
    """An analysis session: the datasets, which is active, and session state.

    ``datasets`` is ordered oldest-to-newest (``datasets[0]`` is conventionally the
    raw measurement; later entries are derivations). ``current_index`` selects the
    active dataset. ``session`` is an opaque, JSON-serializable mapping the caller
    (the GUI) uses to persist view/layout and measurement state; this layer stores
    and returns it verbatim.
    """

    title: str
    datasets: tuple[Dataset, ...]
    current_index: int = 0
    session: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.datasets:
            raise ValueError("a Project must contain at least one dataset")
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
        """The first (conventionally the raw) dataset in the session."""
        return self.datasets[0]


def save_project(project: Project, path: str | Path, *, overwrite: bool = False) -> Path:
    """Write ``project`` to a ``.snomproj`` bundle at ``path``; return the path.

    Each dataset is persisted with :func:`snomniman.io.write_zarr` (loss-less,
    provenance intact) under ``datasets/``, alongside a ``project.json`` manifest.
    With ``overwrite=False`` an existing ``path`` raises ``FileExistsError``. With
    ``overwrite=True`` an existing path is replaced **only** if it is empty or an
    existing SNOMNIMAN project bundle; any other existing directory is refused
    (this never clobbers unrelated data).
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

    datasets_dir = bundle / _DATASETS_DIR
    datasets_dir.mkdir(parents=True)

    rel_paths: list[str] = []
    for index, dataset in enumerate(project.datasets):
        rel = f"{_DATASETS_DIR}/dataset_{index:02d}.zarr"
        write_zarr(dataset, bundle / rel, overwrite=True)
        rel_paths.append(rel)

    manifest: dict[str, Any] = {
        "format": PROJECT_FORMAT,
        "schema_version": PROJECT_SCHEMA_VERSION,
        "title": project.title,
        "current_index": project.current_index,
        "datasets": rel_paths,
        "session": dict(project.session),
        "created_at": datetime.now(UTC).isoformat(),
        "software": current_software(),
    }
    (bundle / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return bundle


def load_project(path: str | Path) -> Project:
    """Load a ``.snomproj`` bundle written by :func:`save_project` into a ``Project``.

    Every dataset is restored with :func:`snomniman.io.read_zarr`, so each comes
    back with its channels, metadata, conventions, provenance DAG, and raw-source
    anchor intact and immutable. Raises :class:`ReaderError` if ``path`` is not a
    readable SNOMNIMAN project bundle.
    """
    bundle = Path(path)
    manifest = _load_manifest(bundle)

    rel_paths = manifest.get("datasets")
    if not isinstance(rel_paths, list) or not rel_paths:
        raise ReaderError(f"project manifest in {bundle} lists no datasets")
    datasets = tuple(read_zarr(bundle / rel) for rel in rel_paths)

    session = manifest.get("session", {})
    if not isinstance(session, dict):  # pragma: no cover - corrupt manifest
        session = {}
    return Project(
        title=str(manifest.get("title", bundle.stem)),
        datasets=datasets,
        current_index=int(manifest.get("current_index", 0)),
        session=session,
    )


def project_from_history(
    datasets: Sequence[Dataset],
    *,
    title: str,
    current_index: int | None = None,
    session: Mapping[str, Any] | None = None,
) -> Project:
    """Build a :class:`Project` from a derivation history (newest dataset active).

    A convenience for the common case where ``datasets`` is the linear history of a
    session (raw first, then each derivation) and the last one is active.
    """
    if current_index is None:
        current_index = len(datasets) - 1
    return Project(
        title=title,
        datasets=tuple(datasets),
        current_index=current_index,
        session=dict(session) if session is not None else {},
    )


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


__all__ = [
    "MANIFEST_NAME",
    "PROJECT_FORMAT",
    "PROJECT_SCHEMA_VERSION",
    "Project",
    "load_project",
    "project_from_history",
    "save_project",
]
