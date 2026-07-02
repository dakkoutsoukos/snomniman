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

from ._neasnom_header import parse_param_file, str_value, txt_index
from .gsf import MAGIC
from .neasnom import READER_ID as NEASNOM_READER_ID
from .neasnom import read_neasnom_measurement
from .neasnom_spectrum import READER_ID as NEASNOM_SPECTRUM_READER_ID
from .neasnom_spectrum import read_neasnom_spectrum_measurement

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

    Content-based, in order: a **point-spectroscopy** directory has a
    ``*Spectra.txt`` file whose vendor header ``Scan:`` line names "Point
    Spectroscopy" - checked *before* the imaging check, since such a directory
    also carries ordinary-looking per-position ``.gsf`` channel maps that would
    otherwise wrongly match the imaging sniff below. An **imaging** neaSNOM
    measurement is a directory that contains at least one ``.gsf`` file with the
    GSF magic and a ``.txt`` parameter file.
    """
    p = Path(path)
    if not p.is_dir():
        return None
    if _looks_like_point_spectroscopy(p):
        return NEASNOM_SPECTRUM_READER_ID
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


def _looks_like_point_spectroscopy(root: Path) -> bool:
    candidates = sorted(root.glob("*Spectra.txt"))
    if not candidates:
        return False
    try:
        txt = parse_param_file(candidates[0])
    except OSError:  # pragma: no cover - defensive
        return False
    scan = str_value(txt_index(txt).get("Scan")) or ""
    return "point spectroscopy" in scan.lower()


# Built-in readers.
register(NEASNOM_READER_ID, read_neasnom_measurement)
register(NEASNOM_SPECTRUM_READER_ID, read_neasnom_spectrum_measurement)


__all__ = [
    "available_readers",
    "get_reader",
    "read",
    "register",
    "sniff",
]
