"""Reader registry - format id -> reader callable (ADR-0006; *not* a plugin system).

Adding a vendor/format means implementing one reader and registering it here.
``sniff`` does content-based detection and ``read`` dispatches to the matching
reader. Reader ids encode format + version (e.g. ``neasnom.image.gsf.v1``).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from snomniman.core import Dataset
from snomniman.core.exceptions import ReaderError

from .gsf import MAGIC
from .neasnom import READER_ID as NEASNOM_READER_ID
from .neasnom import read_neasnom_measurement

Reader = Callable[[Path], Dataset]

_READERS: dict[str, Reader] = {}


def register(reader_id: str, reader: Reader) -> None:
    """Register ``reader`` under ``reader_id`` (raises on duplicate ids)."""
    if reader_id in _READERS:
        raise ValueError(f"reader id already registered: {reader_id!r}")
    _READERS[reader_id] = reader


def get_reader(reader_id: str) -> Reader:
    try:
        return _READERS[reader_id]
    except KeyError as exc:
        raise ReaderError(f"no reader registered for {reader_id!r}") from exc


def available_readers() -> list[str]:
    return sorted(_READERS)


def sniff(path: str | Path) -> str | None:
    """Return the reader id that can handle ``path``, or ``None``.

    A neaSNOM GSF measurement is a directory that contains at least one ``.gsf``
    file with the GSF magic and a ``.txt`` parameter file.
    """
    p = Path(path)
    if not p.is_dir():
        return None
    gsf_files = sorted(p.glob("*.gsf"))
    has_txt = any(p.glob("*.txt"))
    if gsf_files and has_txt and _looks_like_gsf(gsf_files[0]):
        return NEASNOM_READER_ID
    return None


def read(path: str | Path) -> Dataset:
    """Sniff ``path`` and dispatch to the matching reader."""
    reader_id = sniff(path)
    if reader_id is None:
        raise ReaderError(f"no reader recognized {path}")
    return get_reader(reader_id)(Path(path))


def _looks_like_gsf(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            return fh.read(len(MAGIC)) == MAGIC
    except OSError:  # pragma: no cover - defensive
        return False


# Built-in readers.
register(NEASNOM_READER_ID, read_neasnom_measurement)


__all__ = [
    "available_readers",
    "get_reader",
    "read",
    "register",
    "sniff",
]
