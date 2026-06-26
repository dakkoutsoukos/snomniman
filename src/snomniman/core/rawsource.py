"""``RawSource`` - the immutable reproducibility anchor (data-model.md sec 7).

A ``RawSource`` records *where data came from* and a content hash so replay can
verify the raw input is unchanged before reconstructing a result. Raw files are
**referenced, never copied or modified** (ADR-0009).

A neaSNOM measurement is a *directory* of per-channel ``.gsf`` files plus a
``.txt`` parameter file, not a single file (measurement-discovery.md). The
deferred Phase-1 implementation detail - how to anchor a directory - is resolved
here: the sha256 is computed over a **sorted manifest of (relative-name, per-file
sha256)** for the files the reader consumes. This is order-independent, changes if
any consumed file changes, and ignores vendor-generated previews.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_CHUNK = 1 << 20  # 1 MiB streaming read


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def _hash_file(path: Path) -> tuple[str, int]:
    """Return ``(sha256_hex, n_bytes)`` for a single file, read in chunks."""
    h = hashlib.sha256()
    n = 0
    with path.open("rb") as fh:
        while chunk := fh.read(_CHUNK):
            h.update(chunk)
            n += len(chunk)
    return h.hexdigest(), n


@dataclass(frozen=True)
class RawSource:
    """An immutable reference to an origin file or measurement directory."""

    path: str
    sha256: str
    reader: str
    reader_params: dict[str, Any] = field(default_factory=dict)
    bytes: int = 0
    is_directory: bool = False
    manifest: tuple[tuple[str, str], ...] = ()  # (relative-name, file-sha256), sorted
    imported_at: str = field(default_factory=_utcnow_iso)

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        *,
        reader: str,
        reader_params: dict[str, Any] | None = None,
    ) -> RawSource:
        """Anchor a single file by its sha256."""
        p = Path(path)
        digest, nbytes = _hash_file(p)
        return cls(
            path=str(p),
            sha256=digest,
            reader=reader,
            reader_params=dict(reader_params or {}),
            bytes=nbytes,
            is_directory=False,
            manifest=((p.name, digest),),
        )

    @classmethod
    def from_directory(
        cls,
        path: str | Path,
        *,
        reader: str,
        files: Iterable[str | Path],
        reader_params: dict[str, Any] | None = None,
    ) -> RawSource:
        """Anchor a measurement *directory* by a sorted per-file hash manifest.

        ``files`` are the consumed files (e.g. the ``.gsf`` channels + ``.txt``);
        vendor-generated previews (``Images/``, ``.gwy``, ``.html``) are excluded
        by the caller so the anchor reflects only the scientific inputs.
        """
        root = Path(path)
        entries: list[tuple[str, str]] = []
        total = 0
        for f in files:
            fp = Path(f)
            digest, nbytes = _hash_file(fp)
            rel = fp.relative_to(root).as_posix() if fp.is_absolute() else fp.name
            entries.append((rel, digest))
            total += nbytes
        entries.sort()
        return cls(
            path=str(root),
            sha256=_manifest_digest(entries),
            reader=reader,
            reader_params=dict(reader_params or {}),
            bytes=total,
            is_directory=True,
            manifest=tuple(entries),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "sha256": self.sha256,
            "reader": self.reader,
            "reader_params": dict(self.reader_params),
            "bytes": self.bytes,
            "is_directory": self.is_directory,
            "manifest": [list(e) for e in self.manifest],
            "imported_at": self.imported_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RawSource:
        return cls(
            path=data["path"],
            sha256=data["sha256"],
            reader=data["reader"],
            reader_params=dict(data.get("reader_params", {})),
            bytes=data.get("bytes", 0),
            is_directory=data.get("is_directory", False),
            manifest=tuple((e[0], e[1]) for e in data.get("manifest", ())),
            imported_at=data.get("imported_at", _utcnow_iso()),
        )


def _manifest_digest(entries: Sequence[tuple[str, str]]) -> str:
    """Hash a sorted manifest into one stable, order-independent sha256."""
    h = hashlib.sha256()
    for name, digest in entries:
        h.update(name.encode("utf-8"))
        h.update(b"\0")
        h.update(digest.encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()


__all__ = ["RawSource"]
