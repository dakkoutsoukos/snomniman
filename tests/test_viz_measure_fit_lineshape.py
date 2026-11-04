"""Tests for viz.measure.fit_lineshape - the Lorentzian + linear-baseline analysis.

Follows Phase 5A's Appendix A validation shape (docs/phase5-spectral-nanoftir.md):
a synthetic spectrum built from a known analytic Lorentzian + linear baseline
recovers its parameters within a documented tolerance (the "known-good" case),
plus a "known-bad-fit" case (a genuinely non-Lorentzian synthetic spectrum) that
must be validated to fail honestly - a low R^2 and a poor fit, not a silently
plausible-looking wrong answer. This is Category-A engineering validation (Rule
6), not a Scientific Validation Phase item - see docs/
phase6-spectral-lineshape-analysis.md sec 3.3/5.
"""

from __future__ import annotations

import numpy as np
import pytest

from snomniman.viz.measure import (
    BASELINE_LINEAR,
    LINESHAPE_LORENTZIAN,
    fit_lineshape,
)

_CENTER = 6095.0
_FWHM = 42.4
_AMPLITUDE = 2.069
_SLOPE = -1.556e-3  # per cm^-1 (the figure's own "-1.556/1000cm^-1")
_INTERCEPT = 1.351


def _lorentzian_linear(x: np.ndarray) -> np.ndarray:
    lorentzian = _AMPLITUDE / (1.0 + ((x - _CENTER) / (_FWHM / 2.0)) ** 2)
    return lorentzian + _SLOPE * x + _INTERCEPT


def _synthetic_spectrum(
    *, noise_scale: float = 0.02, seed: int = 0
) -> tuple[np.ndarray, np.ndarray]:
    x = np.arange(5800.0, 6401.0, 1.0)
    rng = np.random.default_rng(seed)
    y = _lorentzian_linear(x) + rng.normal(scale=noise_scale, size=x.size)
    return x, y


# -- known-good: recovers a known analytic Lorentzian + linear baseline ------- #


def test_recovers_known_parameters() -> None:
    x, y = _synthetic_spectrum()
    result = fit_lineshape(x, y, window=(5800.0, 6400.0), unit="a.u.")
    assert result.shape == LINESHAPE_LORENTZIAN
    assert result.baseline == BASELINE_LINEAR
    assert abs(result.center - _CENTER) < 2.0
    assert abs(result.fwhm - _FWHM) < 5.0
    assert abs(result.amplitude - _AMPLITUDE) < 0.1
    assert abs(result.baseline_slope - _SLOPE) < 5e-4
    assert abs(result.baseline_intercept - _INTERCEPT) < 0.2
    assert result.r_squared > 0.99
    assert result.ssr_per_dof > 0.0
    assert result.rms < 0.1


def test_reports_finite_uncertainties_for_a_well_conditioned_fit() -> None:
    x, y = _synthetic_spectrum()
    result = fit_lineshape(x, y, window=(5800.0, 6400.0))
    assert np.isfinite(result.center_stderr)
    assert np.isfinite(result.fwhm_stderr)
    assert np.isfinite(result.amplitude_stderr)
    assert result.center_stderr < 5.0


def test_fit_curve_and_residuals_span_the_full_input() -> None:
    x, y = _synthetic_spectrum()
    result = fit_lineshape(x, y, window=(5900.0, 6300.0))
    assert result.wavenumber_cm1.shape == x.shape
    assert result.fit_curve.shape == x.shape
    assert result.residuals.shape == x.shape
    np.testing.assert_allclose(result.residuals, y - result.fit_curve)


def test_window_order_independent() -> None:
    x, y = _synthetic_spectrum()
    a = fit_lineshape(x, y, window=(5800.0, 6400.0))
    b = fit_lineshape(x, y, window=(6400.0, 5800.0))
    assert a.center == pytest.approx(b.center)
    assert a.window == b.window == (5800.0, 6400.0)


def test_quality_computed_within_window_only() -> None:
    # A window narrower than the full array must count only its own samples.
    x, y = _synthetic_spectrum()
    result = fit_lineshape(x, y, window=(6000.0, 6200.0))
    assert result.n_window == int(np.sum((x >= 6000.0) & (x <= 6200.0)))


# -- known-bad-fit: a genuinely non-Lorentzian spectrum fails honestly -------- #


def test_double_peak_produces_a_poor_fit() -> None:
    # Two well-separated, narrow peaks: a single Lorentzian + linear baseline
    # cannot represent both, so the fit should be honestly poor, not a
    # plausible-looking wrong answer.
    x = np.arange(5800.0, 6401.0, 1.0)
    peak_a = 1.0 / (1.0 + ((x - 5900.0) / 10.0) ** 2)
    peak_b = 1.0 / (1.0 + ((x - 6300.0) / 10.0) ** 2)
    y = peak_a + peak_b
    result = fit_lineshape(x, y, window=(5800.0, 6400.0))
    # A single Lorentzian genuinely cannot represent two separated peaks; the
    # threshold is well below the >0.99 the known-good case achieves, but not
    # pinned to the exact value (a numerical, not a scientific, tolerance).
    assert result.r_squared < 0.6


# -- parameter / precondition validation -------------------------------------- #


def test_unsupported_shape_is_rejected() -> None:
    x, y = _synthetic_spectrum()
    with pytest.raises(ValueError, match="shape"):
        fit_lineshape(x, y, window=(5800.0, 6400.0), shape="gaussian")


def test_unsupported_baseline_is_rejected() -> None:
    x, y = _synthetic_spectrum()
    with pytest.raises(ValueError, match="baseline"):
        fit_lineshape(x, y, window=(5800.0, 6400.0), baseline="none")


def test_mismatched_array_shapes_are_rejected() -> None:
    x, y = _synthetic_spectrum()
    with pytest.raises(ValueError, match="same shape"):
        fit_lineshape(x, y[:-1], window=(5800.0, 6400.0))


def test_too_few_points_in_window_is_rejected() -> None:
    x, y = _synthetic_spectrum()
    with pytest.raises(ValueError, match="finite sample"):
        fit_lineshape(x, y, window=(5800.0, 5803.0))
