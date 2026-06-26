"""Pure Gwyddion Simple Field (GSF) reader/writer - format level, no SNOM semantics.

GSF layout (Gwyddion spec; confirmed by binary inspection in
measurement-discovery.md):

* ASCII magic line ``Gwyddion Simple Field 1.0\\n``;
* a text header of ``key = value`` lines (leading/trailing whitespace stripped);
* 1-4 NUL bytes padding the (magic + header) length up to a 4-byte boundary
  (when the length is already a multiple of 4 there are **4** NUL bytes);
* ``XRes * YRes`` IEEE float32 values, little-endian, stored **row by row from
  top to bottom, left to right**.

This module is deliberately faithful to the file: it returns the data in the
native top-to-bottom order and applies no unit or orientation conversion. Mapping
to SNOMNIMAN's canonical lower-left / y-up convention happens one layer up, in the
neaSNOM reader, where it is recorded in provenance.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt

from snomniman.core.exceptions import ReaderError

MAGIC = b"Gwyddion Simple Field 1.0\n"


@dataclass(frozen=True)
class GsfFile:
    """A parsed GSF file: its text header plus the float32 grid (native order)."""

    header: dict[str, str]
    data: npt.NDArray[np.float32]  # shape (yres, xres), top-to-bottom row order
    path: str | None = None

    @property
    def xres(self) -> int:
        return int(self.header["XRes"])

    @property
    def yres(self) -> int:
        return int(self.header["YRes"])

    def _float(self, key: str, default: float | None = None) -> float | None:
        value = self.header.get(key)
        if value is None or value == "":
            return default
        return float(value)

    @property
    def xreal(self) -> float | None:
        return self._float("XReal")

    @property
    def yreal(self) -> float | None:
        return self._float("YReal")

    @property
    def xoffset(self) -> float | None:
        return self._float("XOffset", 0.0)

    @property
    def yoffset(self) -> float | None:
        return self._float("YOffset", 0.0)

    @property
    def xyunits(self) -> str:
        return self.header.get("XYUnits", "")

    @property
    def zunits(self) -> str:
        return self.header.get("ZUnits", "")


def _data_offset(header_end: int) -> int:
    """Start of the binary block: round ``header_end`` up to the next 4 boundary.

    Per the GSF spec the padding is 1-4 NUL bytes, so a length already aligned to
    4 still advances by 4 (``4 - 0`` -> 4).
    """
    return header_end + (4 - header_end % 4)


def parse_gsf(raw: bytes, *, path: str | None = None) -> GsfFile:
    """Parse GSF bytes into a :class:`GsfFile`. Raises :class:`ReaderError`."""
    if not raw.startswith(MAGIC):
        raise ReaderError(f"not a GSF file (bad magic): {path or '<bytes>'}")
    nul = raw.find(b"\x00", len(MAGIC))
    if nul == -1:
        raise ReaderError(f"GSF header has no NUL terminator: {path or '<bytes>'}")
    header_text = raw[len(MAGIC) : nul].decode("utf-8")
    header: dict[str, str] = {}
    for line in header_text.splitlines():
        if not line.strip():
            continue
        key, sep, value = line.partition("=")
        if not sep:
            raise ReaderError(f"malformed GSF header line {line!r} in {path or '<bytes>'}")
        header[key.strip()] = value.strip()

    for required in ("XRes", "YRes"):
        if required not in header:
            raise ReaderError(f"GSF header missing {required} in {path or '<bytes>'}")
    xres = int(header["XRes"])
    yres = int(header["YRes"])
    if xres <= 0 or yres <= 0:
        raise ReaderError(f"GSF has non-positive dimensions {xres}x{yres}")

    start = _data_offset(nul)
    count = xres * yres
    payload = raw[start : start + count * 4]
    if len(payload) != count * 4:
        raise ReaderError(
            f"GSF truncated: expected {count * 4} data bytes, found {len(payload)} "
            f"in {path or '<bytes>'}"
        )
    data = np.frombuffer(payload, dtype="<f4", count=count).reshape(yres, xres).copy()
    return GsfFile(header=header, data=data, path=path)


def read_gsf(path: str | Path) -> GsfFile:
    """Read and parse a GSF file from disk."""
    p = Path(path)
    return parse_gsf(p.read_bytes(), path=str(p))


def write_gsf(
    path: str | Path,
    data: npt.NDArray[np.float32],
    header: dict[str, str],
) -> None:
    """Write a GSF file (top-to-bottom row order). Used for tests and round-trips.

    ``header`` must contain consistent ``XRes``/``YRes``; ``data`` is written in
    its given (row-major, top-to-bottom) order as little-endian float32.
    """
    if data.ndim != 2:
        raise ReaderError("GSF data must be 2-D (yres, xres)")
    yres, xres = data.shape
    full = {"XRes": str(xres), "YRes": str(yres), **header}
    text = "".join(f"{k}={v}\n" for k, v in full.items()).encode("utf-8")
    body = MAGIC + text
    pad = 4 - len(body) % 4  # 1..4 NUL bytes
    payload = np.ascontiguousarray(data, dtype="<f4").tobytes()
    Path(path).write_bytes(body + b"\x00" * pad + payload)


__all__ = ["MAGIC", "GsfFile", "parse_gsf", "read_gsf", "write_gsf"]
