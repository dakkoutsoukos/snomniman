"""Tests for the Phase 3B analysis backend (Qt-free, known-answer).

Covers the reusable analysis primitives: line-profile feature detection +
descriptive stats (`viz.measure.analyze_profile`), region comparison
(`viz.measure.compare_regions`) and the richer `RegionStats`, and the value
histogram (`diagnostics.histogram`). These are pure functions over arrays, so they
run without a display and are validated against analytically known answers (Rule 6).
"""

from __future__ import annotations

import numpy as np
import pytest

from snomniman.diagnostics import histogram
from snomniman.viz import RegionStats, analyze_profile, compare_regions
from snomniman.viz.measure import region_stats

# -- histogram --------------------------------------------------------------- #


def test_histogram_known_distribution() -> None:
    values = np.arange(100, dtype=np.float64)  # 0..99, uniform
    h = histogram(values, unit="nm", bins=10)
    assert h.count == 100
    assert sum(h.counts) == 100  # every finite sample is binned
    assert len(h.bin_edges) == len(h.counts) + 1 == 11
    assert h.unit == "nm"
    assert h.minimum == 0.0 and h.maximum == 99.0
    assert h.mean == pytest.approx(49.5)
    assert h.percentiles["p50"] == pytest.approx(49.5)
    assert h.percentiles["p25"] == pytest.approx(24.75)
    assert h.rms == pytest.approx(float(np.sqrt(np.mean(values**2))))


def test_histogram_fd_default_bins_all_samples() -> None:
    rng = np.random.default_rng(0)
    values = rng.normal(size=500)
    h = histogram(values)  # Freedman-Diaconis default
    assert h.count == 500
    assert sum(h.counts) == 500
    assert 1 <= len(h.counts) <= 256


def test_histogram_ignores_non_finite() -> None:
    values = np.array([1.0, 2.0, np.nan, 3.0, np.inf])
    h = histogram(values, bins=3)
    assert h.count == 3  # nan + inf dropped
    assert sum(h.counts) == 3


def test_histogram_empty_is_honest() -> None:
    h = histogram(np.array([np.nan, np.nan]), unit="a.u.")
    assert h.count == 0
    assert h.counts == () and h.bin_edges == ()
    assert h.mean is None and h.median is None and h.percentiles == {}


# -- line-profile feature analysis ------------------------------------------- #


def test_analyze_profile_two_gaussian_peaks() -> None:
    positions = np.linspace(0.0, 100.0, 101)
    sigma = 5.0
    values = np.exp(-((positions - 25) ** 2) / (2 * sigma**2)) + np.exp(
        -((positions - 75) ** 2) / (2 * sigma**2)
    )
    feat = analyze_profile(positions, values, unit="nm")
    assert len(feat.peaks) == 2
    centers = sorted(p.position_nm for p in feat.peaks)
    assert centers[0] == pytest.approx(25.0, abs=2.0)
    assert centers[1] == pytest.approx(75.0, abs=2.0)
    # Peak spacing is the feature period (e.g. polariton-fringe spacing).
    assert feat.mean_spacing_nm == pytest.approx(50.0, abs=2.0)
    # Gaussian FWHM = 2.355*sigma ~ 11.8 nm.
    for peak in feat.peaks:
        assert peak.fwhm_nm is not None and 9.0 <= peak.fwhm_nm <= 14.0
    assert feat.count == 101 and feat.unit == "nm"
    assert feat.maximum == pytest.approx(1.0, abs=0.02)
    assert feat.length_nm == pytest.approx(100.0)


def test_analyze_profile_flat_has_no_peaks() -> None:
    positions = np.linspace(0.0, 10.0, 20)
    feat = analyze_profile(positions, np.ones(20), unit="nm")
    assert feat.peaks == ()
    assert feat.mean_spacing_nm is None
    assert feat.mean == pytest.approx(1.0) and feat.std == pytest.approx(0.0)
    assert feat.rms == pytest.approx(1.0)


def test_analyze_profile_handles_non_finite() -> None:
    positions = np.linspace(0.0, 10.0, 11)
    values = np.array([0, 1, 2, np.nan, 4, 5, 4, 3, 2, 1, 0], dtype=np.float64)
    feat = analyze_profile(positions, values)
    assert feat.count == 10  # the NaN is excluded from the descriptive stats
    assert feat.maximum == pytest.approx(5.0)


# -- region statistics + comparison ------------------------------------------ #


def test_region_stats_includes_rms_and_quartiles() -> None:
    values = np.arange(100, dtype=np.float64).reshape(10, 10)
    mask = np.ones((10, 10), dtype=bool)
    stats = region_stats(values, mask, pixel_area_nm2=4.0)
    assert stats.count == 100
    assert stats.area_nm2 == pytest.approx(400.0)
    assert stats.mean == pytest.approx(49.5)
    assert stats.rms == pytest.approx(float(np.sqrt(np.mean(np.arange(100.0) ** 2))))
    assert stats.p25 == pytest.approx(24.75)
    assert stats.p75 == pytest.approx(74.25)


def _stats(mean: float) -> RegionStats:
    return RegionStats(
        count=4, area_nm2=4.0, mean=mean, median=mean, minimum=mean, maximum=mean, std=0.0
    )


def test_compare_regions_difference_ratio_and_underlying_stats() -> None:
    a, b = _stats(2.0), _stats(1.0)
    comp = compare_regions(a, b, label_a="A", label_b="B", unit="a.u.")
    assert comp.difference == pytest.approx(1.0)
    assert comp.ratio == pytest.approx(2.0)
    # The underlying descriptive statistics are exposed alongside the comparison.
    assert comp.stats_a is a and comp.stats_b is b
    assert comp.label_a == "A" and comp.label_b == "B" and comp.unit == "a.u."


def test_compare_regions_ratio_is_none_when_denominator_zero() -> None:
    comp = compare_regions(_stats(2.0), _stats(0.0), label_a="A", label_b="B")
    assert comp.difference == pytest.approx(2.0)
    assert comp.ratio is None
