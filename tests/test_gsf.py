"""Unit tests for the pure GSF reader/writer (snomniman.io.gsf)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest

from snomniman.core.exceptions import ReaderError
from snomniman.io.gsf import MAGIC, parse_gsf, read_gsf, write_gsf
from snomniman.io.gsf import _data_offset as data_offset


def test_data_offset_alignment_all_mod4_cases() -> None:
    # 1-4 NUL bytes pad the header to a 4-byte boundary; a length already aligned
    # still advances by 4 (the bug-prone case).
    assert data_offset(332) == 336  # 332 % 4 == 0 -> +4
    assert data_offset(333) == 336  # % 4 == 1 -> +3
    assert data_offset(330) == 332  # % 4 == 2 -> +2
    assert data_offset(331) == 332  # % 4 == 3 -> +1


def test_write_read_roundtrip(tmp_path: Path) -> None:
    data = np.arange(150 * 200, dtype=np.float32).reshape(200, 150)  # (yres, xres)
    path = tmp_path / "rt.gsf"
    write_gsf(path, data, {"XReal": "1.0E-05", "YReal": "1.0E-05", "XYUnits": "m"})
    gf = read_gsf(path)
    assert gf.xres == 150
    assert gf.yres == 200
    assert gf.data.shape == (200, 150)
    assert gf.data.dtype == np.float32
    np.testing.assert_array_equal(gf.data, data)


@pytest.mark.parametrize("extra_key_len", range(0, 4))
def test_roundtrip_independent_of_header_length(
    tmp_path: Path, extra_key_len: int
) -> None:
    # Vary header length so (magic + header) hits every length-mod-4 case.
    data = np.linspace(-1.0, 1.0, 6 * 5, dtype=np.float32).reshape(5, 6)
    header = {"XReal": "1E-05", "YReal": "1E-05", "Pad": "x" * extra_key_len}
    path = tmp_path / "h.gsf"
    write_gsf(path, data, header)
    np.testing.assert_array_equal(read_gsf(path).data, data)


def test_little_endian_float_values(tmp_path: Path) -> None:
    data = np.array([[1.5, -2.25], [3.125, 0.0]], dtype=np.float32)
    path = tmp_path / "le.gsf"
    write_gsf(path, data, {})
    raw = path.read_bytes()
    # Locate the payload and decode explicitly as little-endian float32.
    start = raw.index(b"\x00", len(MAGIC))
    start += 4 - start % 4
    decoded = np.frombuffer(raw[start:], dtype="<f4")
    np.testing.assert_array_equal(decoded, data.ravel())


def test_bad_magic_raises() -> None:
    with pytest.raises(ReaderError, match="bad magic"):
        parse_gsf(b"NOT A GSF FILE\x00\x00\x00\x00")


def test_missing_required_field_raises() -> None:
    body = b"Gwyddion Simple Field 1.0\nXRes=4\n"  # no YRes
    payload = body + b"\x00" * (4 - len(body) % 4) + b"\x00" * (4 * 4)
    with pytest.raises(ReaderError, match="YRes"):
        parse_gsf(payload)


def test_truncated_data_raises(make_gsf: Callable[..., Path]) -> None:
    path = make_gsf(np.zeros((4, 4), dtype=np.float32))
    truncated = path.read_bytes()[:-16]  # drop 4 float32 values
    with pytest.raises(ReaderError, match="truncated"):
        parse_gsf(truncated)


def test_header_whitespace_is_stripped(make_gsf: Callable[..., Path]) -> None:
    # neaSNOM right-justifies values with spaces; parsing must strip them.
    path = make_gsf(np.zeros((2, 2), dtype=np.float32), extra_header={"XReal": "   2.0E-05  "})
    gf = read_gsf(path)
    assert gf.xreal == 2.0e-05
