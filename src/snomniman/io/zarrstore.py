"""Canonical Zarr store for a :class:`~snomniman.core.dataset.Dataset` (OHD-3).

This is SNOMNIMAN's *canonical project store* (data-model.md sec 10): a complete,
loss-less, self-contained on-disk representation of a ``Dataset`` that round-trips
its full scientific state - every channel (including complex optical/mechanical),
the shared coordinates and their units, the typed :class:`Metadata` (with the
explicit conventions, OHD-6), the :class:`RawSource` anchor, the human-facing
:class:`DataKind`, and the dataset's node in the provenance DAG.

Layout. The labeled arrays are written with ``xarray.Dataset.to_zarr``; Zarr
natively stores complex64 channels, per-channel and per-coordinate ``attrs``
(units, ``canonical``/``role``/...), dtypes, and the dimension structure. The
SNOMNIMAN-level semantics that are *not* plain array data - the ``DataKind``, the
typed metadata, the provenance graph, and the raw-source anchor - are serialized
into a single JSON document stored under the reserved Zarr group attribute
``"snomniman"``. Keeping that document one self-contained JSON string (rather than
nested Zarr attributes) makes the round-trip fully deterministic and immune to any
attribute-encoding quirks; the per-array units/attrs that Zarr already handles
well are left to Zarr.

Derived-not-stored. Two facets are deliberately recomputed on load rather than
persisted: the :class:`~snomniman.core.capabilities.Capability` set and the
amplitude/phase views. Both are pure functions of the array data (see
:mod:`snomniman.core.dataset`); deriving them on load means they can never drift
from the data they describe.

Notes for future developers:

* Stores are written ``consolidated=False`` because consolidated metadata is not
  part of the Zarr v3 specification (and emits a warning otherwise).
* The store is loaded eagerly (``.load()``) so the reconstructed dataset holds
  real numpy arrays, which the :class:`Dataset` constructor then freezes - giving
  the same raw-immutability guarantee as a freshly imported measurement. Lazy /
  chunk-streaming loading is a deliberate future optimization, not Phase 1.
* This is the *canonical store*, not a vendor format, so it is intentionally not
  part of the vendor reader registry (which exists to import foreign files).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import xarray as xr

from snomniman.core import (
    DataKind,
    Dataset,
    Metadata,
    RawSource,
    deserialize_dag,
    serialize_dag,
)
from snomniman.core.exceptions import ReaderError

#: Marks a store as a SNOMNIMAN dataset (guards against opening a foreign Zarr).
STORE_FORMAT = "snomniman.dataset"

#: Bumped when the store layout changes (supports forward-compatible migrations).
STORE_SCHEMA_VERSION = 1

#: Reserved Zarr group attribute holding the JSON sidecar document.
_SIDECAR_KEY = "snomniman"


def write_zarr(dataset: Dataset, path: str | Path, *, overwrite: bool = True) -> Path:
    """Write ``dataset`` to a canonical Zarr store at ``path`` (loss-less).

    Persists the full scientific state: every channel (complex preserved),
    coordinates and units, the typed metadata with its explicit conventions, the
    provenance DAG, the raw-source anchor, and the ``DataKind``. With
    ``overwrite=False`` an existing store is left untouched (raises
    ``FileExistsError``). Returns the store path.
    """
    store_path = Path(path)
    if not overwrite and store_path.exists():
        raise FileExistsError(f"store already exists (overwrite=False): {store_path}")
    sidecar: dict[str, Any] = {
        "format": STORE_FORMAT,
        "schema_version": STORE_SCHEMA_VERSION,
        "kind": dataset.kind.value,
        "metadata": dataset.metadata.to_dict(),
        "provenance": serialize_dag(dataset.provenance),
        "source": dataset.source.to_dict() if dataset.source is not None else None,
    }
    # Shallow-copy so we never attach attrs to the immutable backing object; the
    # frozen (read-only) arrays are only read by to_zarr, so sharing them is safe.
    xr_ds = dataset.data.copy()
    xr_ds.attrs = {**dataset.data.attrs, _SIDECAR_KEY: json.dumps(sidecar)}

    xr_ds.to_zarr(store_path, mode="w", consolidated=False)
    return store_path


def read_zarr(path: str | Path) -> Dataset:
    """Load a canonical Zarr store written by :func:`write_zarr` into a ``Dataset``.

    The reconstructed dataset is equivalent to the original: identical channels and
    dtypes, coordinates, units, metadata, conventions, provenance, and source.
    Arrays are materialized and frozen, so raw immutability holds exactly as on
    first import. Raises :class:`ReaderError` if ``path`` is not a SNOMNIMAN store.
    """
    store_path = Path(path)
    try:
        raw = xr.open_zarr(store_path, consolidated=False).load()
    except Exception as exc:  # I/O boundary: translate to the typed error hierarchy
        raise ReaderError(f"not a readable Zarr store: {store_path} ({exc})") from exc

    sidecar = _load_sidecar(raw, store_path)

    # Strip the reserved sidecar key so the reconstructed group attrs match the
    # original; any other user-set group attrs are preserved verbatim.
    raw.attrs = {k: v for k, v in raw.attrs.items() if k != _SIDECAR_KEY}

    source_dict = sidecar.get("source")
    return Dataset(
        raw,
        kind=DataKind(sidecar["kind"]),
        metadata=Metadata.from_dict(sidecar["metadata"]),
        provenance=deserialize_dag(sidecar["provenance"]),
        source=RawSource.from_dict(source_dict) if source_dict is not None else None,
    )


def _load_sidecar(raw: xr.Dataset, store_path: Path) -> dict[str, Any]:
    """Extract and validate the JSON sidecar document from the Zarr group attrs."""
    encoded = raw.attrs.get(_SIDECAR_KEY)
    if not isinstance(encoded, str):
        raise ReaderError(
            f"{store_path} is not a SNOMNIMAN dataset store "
            f"(missing '{_SIDECAR_KEY}' metadata)"
        )
    try:
        sidecar: dict[str, Any] = json.loads(encoded)
    except json.JSONDecodeError as exc:  # pragma: no cover - corrupt store
        raise ReaderError(f"corrupt SNOMNIMAN metadata in {store_path}: {exc}") from exc

    if sidecar.get("format") != STORE_FORMAT:
        raise ReaderError(
            f"unexpected store format {sidecar.get('format')!r} in {store_path}; "
            f"expected {STORE_FORMAT!r}"
        )
    version = sidecar.get("schema_version", 0)
    if not isinstance(version, int) or version > STORE_SCHEMA_VERSION:
        raise ReaderError(
            f"store schema version {version} in {store_path} is newer than this "
            f"build supports (<= {STORE_SCHEMA_VERSION}); upgrade SNOMNIMAN"
        )
    return sidecar


__all__ = [
    "STORE_FORMAT",
    "STORE_SCHEMA_VERSION",
    "read_zarr",
    "write_zarr",
]
