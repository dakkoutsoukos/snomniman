"""Known-answer tests for the quantitative measurement math (snomniman.viz.measure).

Pure scientific validation (Rule 6): synthetic grids with answers computed by hand.
"""

from __future__ import annotations

import numpy as np
import pytest

from snomniman.viz import (
    distance,
    pixel_area,
    polygon_mask,
    rect_mask,
    region_stats,
    sample_line,
)

# A 5 x 4 grid (ny=5, nx=4) on a 50 nm pitch, lower-left origin, pixel centers.
_NY, _NX, _PITCH = 5, 4, 50.0
_X = (np.arange(_NX, dtype=np.float64) + 0.5) * _PITCH  # 25, 75, 125, 175
_Y = (np.arange(_NY, dtype=np.float64) + 0.5) * _PITCH  # 25 .. 225


def test_distance_3_4_5() -> None:
    assert distance((0.0, 0.0), (30.0, 40.0)) == pytest.approx((50.0, 30.0, 40.0))
    assert distance((100.0, 200.0), (100.0, 200.0)) == (0.0, 0.0, 0.0)


def test_pixel_area() -> None:
    assert pixel_area(_X, _Y) == pytest.approx(2500.0)  # 50 nm x 50 nm


def test_sample_line_on_a_known_ramp() -> None:
    # values equal the physical x at each pixel -> a horizontal profile reads back
    # the physical x it passes through, and its length is the x-span.
    values = np.tile(_X, (_NY, 1))
    positions, samples = sample_line(values, _X, _Y, (25.0, 125.0), (175.0, 125.0))
    assert positions[0] == pytest.approx(0.0)
    assert positions[-1] == pytest.approx(150.0)  # 175 - 25
    np.testing.assert_allclose(samples[0], 25.0, atol=1e-6)
    np.testing.assert_allclose(samples[-1], 175.0, atol=1e-6)
    # Monotonic increasing along the ramp.
    assert np.all(np.diff(samples) > 0)


def test_sample_line_midpoint_interpolates() -> None:
    values = np.tile(_X, (_NY, 1))
    _, samples = sample_line(values, _X, _Y, (25.0, 125.0), (125.0, 125.0), n=3)
    np.testing.assert_allclose(samples, [25.0, 75.0, 125.0], atol=1e-6)


def test_rect_mask_counts_expected_pixels() -> None:
    # Covers x in [0,100] -> columns 0,1 (centers 25,75); y in [0,100] -> rows 0,1.
    mask = rect_mask(_X, _Y, 0.0, 0.0, 100.0, 100.0)
    assert mask.shape == (_NY, _NX)
    assert mask.sum() == 4  # 2 cols x 2 rows
    assert mask[0, 0] and mask[1, 1] and not mask[2, 0]


def test_region_stats_on_uniform_region() -> None:
    values = np.full((_NY, _NX), 7.0)
    mask = rect_mask(_X, _Y, 0.0, 0.0, 100.0, 100.0)  # 4 pixels
    stats = region_stats(values, mask, pixel_area_nm2=pixel_area(_X, _Y))
    assert stats.count == 4
    assert stats.area_nm2 == pytest.approx(4 * 2500.0)
    assert stats.mean == stats.median == stats.minimum == stats.maximum == 7.0
    assert stats.std == 0.0


def test_region_stats_known_values() -> None:
    values = np.zeros((_NY, _NX))
    values[0, 0], values[0, 1], values[1, 0], values[1, 1] = 1.0, 2.0, 3.0, 4.0
    mask = rect_mask(_X, _Y, 0.0, 0.0, 100.0, 100.0)
    stats = region_stats(values, mask, pixel_area_nm2=1.0)
    assert stats.mean == pytest.approx(2.5)
    assert stats.median == pytest.approx(2.5)
    assert stats.minimum == 1.0 and stats.maximum == 4.0
    assert stats.std == pytest.approx(np.std([1.0, 2.0, 3.0, 4.0]))


def test_region_stats_empty_is_nan() -> None:
    values = np.zeros((_NY, _NX))
    mask = rect_mask(_X, _Y, 5000.0, 5000.0, 6000.0, 6000.0)  # off-grid -> empty
    stats = region_stats(values, mask, pixel_area_nm2=1.0)
    assert stats.count == 0
    assert np.isnan(stats.mean)


def test_polygon_mask_matches_rectangle() -> None:
    # A square polygon must select the same pixels as the equivalent rectangle.
    poly = polygon_mask(_X, _Y, [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)])
    rect = rect_mask(_X, _Y, 0.0, 0.0, 100.0, 100.0)
    np.testing.assert_array_equal(poly, rect)


def test_polygon_mask_triangle() -> None:
    # Big triangle covering the lower-left corner; at least the (0,0) pixel is in.
    mask = polygon_mask(_X, _Y, [(0.0, 0.0), (300.0, 0.0), (0.0, 300.0)])
    assert mask[0, 0]
    assert not mask[_NY - 1, _NX - 1]  # far corner is outside
