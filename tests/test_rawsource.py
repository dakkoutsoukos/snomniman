"""Unit tests for the RawSource reproducibility anchor (incl. directory hashing)."""

from __future__ import annotations

from pathlib import Path

from snomniman.core import RawSource


def _write(path: Path, content: bytes) -> Path:
    path.write_bytes(content)
    return path


def test_from_file_hashes_content(tmp_path: Path) -> None:
    f = _write(tmp_path / "a.bin", b"hello world")
    src = RawSource.from_file(f, reader="r.v1")
    assert src.bytes == 11
    assert src.is_directory is False
    assert len(src.sha256) == 64
    # Same content -> same hash; changed content -> different hash.
    assert RawSource.from_file(f, reader="r.v1").sha256 == src.sha256
    _write(f, b"hello world!")
    assert RawSource.from_file(f, reader="r.v1").sha256 != src.sha256


def test_directory_manifest_is_order_independent(tmp_path: Path) -> None:
    a = _write(tmp_path / "a.gsf", b"AAAA")
    b = _write(tmp_path / "b.gsf", b"BBBB")
    c = _write(tmp_path / "c.txt", b"CCCC")
    src1 = RawSource.from_directory(tmp_path, reader="r.v1", files=[a, b, c])
    src2 = RawSource.from_directory(tmp_path, reader="r.v1", files=[c, b, a])
    assert src1.sha256 == src2.sha256
    assert src1.is_directory is True
    assert src1.bytes == 12
    assert len(src1.manifest) == 3
    # Manifest is sorted by relative name.
    assert [name for name, _ in src1.manifest] == ["a.gsf", "b.gsf", "c.txt"]


def test_directory_hash_changes_when_a_file_changes(tmp_path: Path) -> None:
    a = _write(tmp_path / "a.gsf", b"AAAA")
    b = _write(tmp_path / "b.gsf", b"BBBB")
    before = RawSource.from_directory(tmp_path, reader="r.v1", files=[a, b]).sha256
    _write(b, b"BBBX")
    after = RawSource.from_directory(tmp_path, reader="r.v1", files=[a, b]).sha256
    assert before != after


def test_to_dict_from_dict_roundtrip(tmp_path: Path) -> None:
    a = _write(tmp_path / "a.gsf", b"AAAA")
    src = RawSource.from_directory(
        tmp_path, reader="neasnom.image.gsf.v1", files=[a], reader_params={"k": "v"}
    )
    restored = RawSource.from_dict(src.to_dict())
    assert restored.sha256 == src.sha256
    assert restored.reader == src.reader
    assert restored.reader_params == {"k": "v"}
    assert restored.is_directory is True
    assert restored.manifest == src.manifest
