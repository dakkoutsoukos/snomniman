"""Tests for GSF channel export (Dataset channel -> .gsf + provenance sidecar).

GSF holds one real grid, so a SNOM channel is exported one representation at a time.
The export must be faithful: the right values, the canonical lower-left orientation
flipped back to GSF's top-to-bottom order, a physically meaningful header, and a
provenance sidecar so the exported grid is never an orphan.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from snomniman.core import Dataset
from snomniman.core.exceptions import DatasetError
from snomniman.io import GSF_EXPORT_FORMAT, export_channel_gsf, read_gsf


def test_export_amplitude_roundtrips_values(synthetic_dataset: Dataset, tmp_path: Path) -> None:
    gsf_path, _ = export_channel_gsf(synthetic_dataset, "O2", tmp_path / "o2.gsf")
    gsf = read_gsf(gsf_path)
    # GSF rows are top-to-bottom; un-flip to compare against the canonical array.
    exported = np.flipud(gsf.data)
    expected = np.abs(synthetic_dataset.channel("O2").values).astype(np.float32)
    np.testing.assert_allclose(exported, expected, rtol=1e-6)


def test_export_header_describes_the_grid(synthetic_dataset: Dataset, tmp_path: Path) -> None:
    gsf_path, _ = export_channel_gsf(synthetic_dataset, "O2", tmp_path / "o2.gsf")
    gsf = read_gsf(gsf_path)
    assert gsf.xres == 4 and gsf.yres == 3  # synthetic is 4x3
    assert gsf.xyunits == "nm"  # canonical spatial unit
    # 50 nm pixel pitch over 4 x 3 pixels -> 200 x 150 nm field.
    assert gsf.xreal == pytest.approx(200.0)
    assert gsf.yreal == pytest.approx(150.0)
    assert gsf.zunits == ""  # amplitude is a.u. -> no GSF unit


def test_export_phase_sets_radian_unit(synthetic_dataset: Dataset, tmp_path: Path) -> None:
    gsf_path, _ = export_channel_gsf(
        synthetic_dataset, "O2", tmp_path / "o2_phase.gsf", representation="phase"
    )
    gsf = read_gsf(gsf_path)
    assert gsf.zunits == "rad"
    exported = np.flipud(gsf.data)
    expected = np.angle(synthetic_dataset.channel("O2").values).astype(np.float32)
    np.testing.assert_allclose(exported, expected, rtol=1e-5, atol=1e-6)


def test_export_real_topography_carries_its_unit(
    synthetic_dataset: Dataset, tmp_path: Path
) -> None:
    gsf_path, _ = export_channel_gsf(synthetic_dataset, "Z", tmp_path / "z.gsf")
    gsf = read_gsf(gsf_path)
    assert gsf.zunits == "nm"
    exported = np.flipud(gsf.data)
    expected = synthetic_dataset.channel("Z").values.astype(np.float32)
    np.testing.assert_allclose(exported, expected, rtol=1e-6)


def test_export_writes_provenance_sidecar(synthetic_dataset: Dataset, tmp_path: Path) -> None:
    _, prov_path = export_channel_gsf(synthetic_dataset, "O2", tmp_path / "o2.gsf")
    assert prov_path == tmp_path / "o2.gsf.provenance.json"
    record = json.loads(prov_path.read_text(encoding="utf-8"))
    assert record["format"] == GSF_EXPORT_FORMAT
    assert record["channel"] == "O2" and record["representation"] == "amplitude"
    # The full provenance DAG travels with the exported grid.
    assert record["provenance"]["nodes"][0]["step_id"] == "io.read"
    assert record["conventions"]["origin"] == "lower-left"


def test_invalid_representation_on_complex_channel(
    synthetic_dataset: Dataset, tmp_path: Path
) -> None:
    with pytest.raises(DatasetError, match="invalid representation"):
        export_channel_gsf(synthetic_dataset, "O2", tmp_path / "o2.gsf", representation="height")


def test_representation_on_real_channel_rejected(
    synthetic_dataset: Dataset, tmp_path: Path
) -> None:
    with pytest.raises(DatasetError, match="is real"):
        export_channel_gsf(synthetic_dataset, "Z", tmp_path / "z.gsf", representation="phase")


def test_unknown_channel_raises(synthetic_dataset: Dataset, tmp_path: Path) -> None:
    with pytest.raises(DatasetError, match="no such channel"):
        export_channel_gsf(synthetic_dataset, "O9", tmp_path / "x.gsf")


def test_export_does_not_mutate_dataset(synthetic_dataset: Dataset, tmp_path: Path) -> None:
    ds = synthetic_dataset
    before = {n: ds.channel(n).values.copy() for n in ds.channel_names}
    export_channel_gsf(synthetic_dataset, "O2", tmp_path / "o2.gsf")
    for name, arr in before.items():
        np.testing.assert_array_equal(synthetic_dataset.channel(name).values, arr, err_msg=name)
