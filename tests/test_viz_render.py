"""Tests for the Qt-free display-ready render layer (snomniman.viz.render)."""

from __future__ import annotations

import numpy as np
import pytest

from snomniman.core import Dataset
from snomniman.viz import (
    AMPLITUDE,
    PHASE,
    REAL,
    available_representations,
    default_representation,
    level_range,
    pick_scale_bar,
    prepare_channel,
)


def test_representations_complex_vs_real(synthetic_dataset: Dataset) -> None:
    assert available_representations(synthetic_dataset, "O2") == (AMPLITUDE, PHASE)
    assert available_representations(synthetic_dataset, "Z") == (REAL,)
    assert default_representation(synthetic_dataset, "O2") == AMPLITUDE
    assert default_representation(synthetic_dataset, "Z") == REAL


def test_prepare_amplitude(synthetic_dataset: Dataset) -> None:
    rd = prepare_channel(synthetic_dataset, "O2", AMPLITUDE)
    np.testing.assert_allclose(rd.values, np.abs(synthetic_dataset.channel("O2").values))
    assert rd.cyclic is False
    assert rd.colormap == "viridis"
    assert rd.unit == "a.u."
    assert rd.vmax > rd.vmin
    assert rd.title == "O2 amplitude (a.u.)"


def test_prepare_phase_is_cyclic_and_bounded(synthetic_dataset: Dataset) -> None:
    rd = prepare_channel(synthetic_dataset, "O2", PHASE)
    assert rd.cyclic is True
    assert rd.colormap == "twilight"
    assert (rd.vmin, rd.vmax) == (-np.pi, np.pi)
    assert np.all(np.abs(rd.values) <= np.pi + 1e-5)  # float32 angle at the +/-pi wrap
    # Phase is shown exactly as imported (OHD-6D): equals angle of the complex data.
    np.testing.assert_allclose(rd.values, np.angle(synthetic_dataset.channel("O2").values))


def test_prepare_real_topography(synthetic_dataset: Dataset) -> None:
    rd = prepare_channel(synthetic_dataset, "Z")
    assert rd.representation == REAL
    assert rd.unit == "nm"
    assert rd.colormap == "afmhot"  # height-like map for topography
    np.testing.assert_array_equal(rd.values, synthetic_dataset.channel("Z").values)


def test_extent_is_lower_left_pixel_edges(synthetic_dataset: Dataset) -> None:
    rd = prepare_channel(synthetic_dataset, "O2")
    x0, x1, y0, y1 = rd.extent_nm
    # 4 x 3 px at 50 nm pitch, pixel centers start at 25 nm -> edges 0..200, 0..150.
    assert (x0, x1) == pytest.approx((0.0, 200.0))
    assert (y0, y1) == pytest.approx((0.0, 150.0))
    assert x1 > x0 and y1 > y0  # both axes increase (lower-left)


def test_invalid_representation_raises(synthetic_dataset: Dataset) -> None:
    with pytest.raises(ValueError, match="no 'phase' view"):
        prepare_channel(synthetic_dataset, "Z", PHASE)


def test_pick_scale_bar_round_numbers() -> None:
    length, label = pick_scale_bar(10000.0)  # 10 um field -> ~2 um bar
    assert length == 2000.0
    assert label == "2 µm"
    assert pick_scale_bar(500.0) == (100.0, "100 nm")
    assert pick_scale_bar(2000.0)[0] == 500.0
    assert pick_scale_bar(0.0) == (0.0, "")


def test_dead_channel_range_is_non_degenerate(synthetic_dataset: Dataset) -> None:
    # The all-constant reference amplitude must still yield vmin < vmax.
    rd = prepare_channel(synthetic_dataset, "R_O2", AMPLITUDE)
    assert rd.vmax > rd.vmin


def test_level_range_default_vs_full() -> None:
    # An array with strong outliers: percentile default clips them; full keeps them.
    values = np.concatenate([np.linspace(0.0, 1.0, 1000), [1000.0]]).astype(np.float64)
    lo_d, hi_d = level_range(values, "default")
    lo_f, hi_f = level_range(values, "full")
    assert hi_f == pytest.approx(1000.0)  # full keeps the outlier
    assert hi_d < 10.0  # default clips it away
    assert lo_f <= lo_d and hi_f >= hi_d  # full always encloses default


def test_level_range_guards_and_validates() -> None:
    flat = np.full((4, 4), 3.0)
    lo, hi = level_range(flat, "full")
    assert hi > lo  # non-degenerate even for a constant channel
    with pytest.raises(ValueError, match="unknown level mode"):
        level_range(flat, "nonsense")
