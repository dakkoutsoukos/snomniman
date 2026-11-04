"""Tests for snomniman.physics.dielectric - Drude/Lorentz-oscillator fitting (Phase 8A).

Covers (Rule 6, the same discipline as tests/test_viz_measure_fit_lineshape.py):
- A known-good synthetic round-trip for each model kind: the shape-identifiable
  parameters (gamma for Drude; omega_to/gamma for Lorentz) are recovered within a
  tight tolerance (noiseless) and a looser one (with noise), with high fit quality.
- The identifiability finding itself, checked directly: the SAME gamma/omega_to are
  recovered regardless of the (mathematically unrecoverable) omega_p/strength/
  eps_inf used to generate the synthetic data - proving those really are absorbed by
  scale/offset, not merely "hard to fit."
- A known-bad case: fitting the wrong model family to a spectrum scores honestly low
  (R^2 well below the good-fit case) - never a silently "good enough" wrong answer.
- Parameter validation (bad kind, mismatched shapes, too few finite samples).
- JSON round-trip via to_dict.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from snomniman.physics import (
    DRUDE,
    LORENTZ,
    DielectricFit,
    drude_epsilon,
    fit_dielectric_model,
    lorentz_epsilon,
)


def _wavenumbers(n: int = 200, lo: float = 300.0, hi: float = 1600.0) -> np.ndarray:
    return np.linspace(lo, hi, n)


def _synthetic_drude_signal(
    w: np.ndarray, *, eps_inf: float, omega_p: float, gamma: float, scale: complex, offset: complex
) -> np.ndarray:
    eps = drude_epsilon(w, eps_inf, omega_p, gamma)
    return scale * eps + offset


def _synthetic_lorentz_signal(
    w: np.ndarray,
    *,
    eps_inf: float,
    strength: float,
    omega_to: float,
    gamma: float,
    scale: complex,
    offset: complex,
) -> np.ndarray:
    eps = lorentz_epsilon(w, eps_inf, strength, omega_to, gamma)
    return scale * eps + offset


# --------------------------------------------------------------------------- #
# Known-good synthetic round-trips (shape-identifiable parameters only)
# --------------------------------------------------------------------------- #


def test_drude_fit_recovers_gamma_noiseless() -> None:
    w = _wavenumbers()
    true: dict[str, Any] = {
        "eps_inf": 4.0, "omega_p": 800.0, "gamma": 60.0, "scale": 1.2 + 0.3j, "offset": 0.1 - 0.05j
    }
    signal = _synthetic_drude_signal(w, **true)

    fit = fit_dielectric_model(w, signal, kind=DRUDE)
    assert isinstance(fit, DielectricFit)
    assert fit.kind == DRUDE
    assert fit.gamma_cm1 == pytest.approx(true["gamma"], rel=1e-3)
    assert fit.r_squared > 0.999
    assert fit.omega_to_cm1 is None
    assert not hasattr(fit, "omega_p_cm1")
    assert not hasattr(fit, "strength")
    assert not hasattr(fit, "eps_inf")


def test_drude_fit_recovers_gamma_with_noise() -> None:
    rng = np.random.default_rng(0)
    w = _wavenumbers()
    true: dict[str, Any] = {
        "eps_inf": 3.0, "omega_p": 650.0, "gamma": 80.0, "scale": 1.0 + 0.0j, "offset": 0.0 + 0.0j
    }
    signal = _synthetic_drude_signal(w, **true)
    noise = 0.01 * (rng.standard_normal(w.size) + 1j * rng.standard_normal(w.size))
    noisy = (signal + noise * np.abs(signal).mean()).astype(np.complex128)

    fit = fit_dielectric_model(w, noisy, kind=DRUDE)
    assert fit.gamma_cm1 == pytest.approx(true["gamma"], rel=0.1)
    assert fit.r_squared > 0.95


def test_drude_fit_is_insensitive_to_the_unidentifiable_parameters() -> None:
    # omega_p and eps_inf only ever contribute through a multiplicative/additive
    # constant that the free complex scale/offset exactly absorb - the SAME gamma
    # must be recovered no matter which omega_p/eps_inf generated the data. This is
    # the identifiability claim itself, not just a convergence check.
    w = _wavenumbers()
    fit_a = fit_dielectric_model(
        w,
        _synthetic_drude_signal(
            w, eps_inf=0.0, omega_p=200.0, gamma=60.0, scale=1.2 + 0.3j, offset=0.1 - 0.05j
        ),
        kind=DRUDE,
    )
    fit_b = fit_dielectric_model(
        w,
        _synthetic_drude_signal(
            w, eps_inf=50.0, omega_p=4000.0, gamma=60.0, scale=1.2 + 0.3j, offset=0.1 - 0.05j
        ),
        kind=DRUDE,
    )
    assert fit_a.gamma_cm1 == pytest.approx(fit_b.gamma_cm1, rel=1e-6)
    assert fit_a.gamma_cm1 == pytest.approx(60.0, rel=1e-3)
    assert fit_a.r_squared > 0.999 and fit_b.r_squared > 0.999


def test_lorentz_fit_recovers_omega_to_and_gamma_noiseless() -> None:
    w = _wavenumbers(lo=400.0, hi=800.0)
    true: dict[str, Any] = {
        "eps_inf": 2.0, "strength": 15.0, "omega_to": 590.0, "gamma": 12.0,
        "scale": 1.0 + 0.2j, "offset": 0.05 + 0.0j,
    }
    signal = _synthetic_lorentz_signal(w, **true)

    fit = fit_dielectric_model(w, signal, kind=LORENTZ)
    assert fit.kind == LORENTZ
    assert fit.omega_to_cm1 == pytest.approx(true["omega_to"], rel=1e-3)
    assert fit.gamma_cm1 == pytest.approx(true["gamma"], rel=1e-2)
    assert fit.r_squared > 0.999
    assert not hasattr(fit, "strength")
    assert not hasattr(fit, "omega_p_cm1")


def test_lorentz_fit_is_insensitive_to_the_unidentifiable_strength() -> None:
    w = _wavenumbers(lo=400.0, hi=800.0)
    fit_a = fit_dielectric_model(
        w,
        _synthetic_lorentz_signal(
            w, eps_inf=0.0, strength=1.0, omega_to=590.0, gamma=12.0, scale=1.0 + 0.2j, offset=0.05
        ),
        kind=LORENTZ,
    )
    fit_b = fit_dielectric_model(
        w,
        _synthetic_lorentz_signal(
            w, eps_inf=0.0, strength=200.0, omega_to=590.0, gamma=12.0,
            scale=1.0 + 0.2j, offset=0.05,
        ),
        kind=LORENTZ,
    )
    assert fit_a.omega_to_cm1 == pytest.approx(fit_b.omega_to_cm1, rel=1e-6)
    assert fit_a.gamma_cm1 == pytest.approx(fit_b.gamma_cm1, rel=1e-6)


def test_lorentz_fit_quality_degrades_honestly_on_noise() -> None:
    rng = np.random.default_rng(1)
    w = _wavenumbers(lo=400.0, hi=800.0)
    true: dict[str, Any] = {
        "eps_inf": 2.0, "strength": 15.0, "omega_to": 590.0, "gamma": 12.0,
        "scale": 1.0 + 0.0j, "offset": 0.0 + 0.0j,
    }
    signal = _synthetic_lorentz_signal(w, **true)
    heavy_noise = 0.5 * np.abs(signal).mean() * (
        rng.standard_normal(w.size) + 1j * rng.standard_normal(w.size)
    )
    noisy_signal = (signal + heavy_noise).astype(np.complex128)
    fit = fit_dielectric_model(w, noisy_signal, kind=LORENTZ)
    assert fit.r_squared < 0.9  # honestly degraded, not silently perfect


# --------------------------------------------------------------------------- #
# Known-bad case: the wrong model family
# --------------------------------------------------------------------------- #


def test_drude_model_fits_a_lorentz_resonance_poorly() -> None:
    # A sharp, symmetric resonance is qualitatively different from a Drude roll-off;
    # forcing a Drude fit onto it should score visibly worse than the matching model.
    w = _wavenumbers(lo=400.0, hi=800.0)
    lorentz_true: dict[str, Any] = {
        "eps_inf": 2.0, "strength": 15.0, "omega_to": 590.0, "gamma": 8.0,
        "scale": 1.0 + 0.0j, "offset": 0.0 + 0.0j,
    }
    signal = _synthetic_lorentz_signal(w, **lorentz_true)

    good_fit = fit_dielectric_model(w, signal, kind=LORENTZ)
    bad_fit = fit_dielectric_model(w, signal, kind=DRUDE)
    assert good_fit.r_squared > 0.99
    assert bad_fit.r_squared < good_fit.r_squared - 0.05


# --------------------------------------------------------------------------- #
# Parameter validation
# --------------------------------------------------------------------------- #


def test_rejects_unknown_kind() -> None:
    w = _wavenumbers(n=20)
    signal = np.ones(20, dtype=np.complex128)
    with pytest.raises(ValueError):
        fit_dielectric_model(w, signal, kind="bogus")


def test_rejects_mismatched_shapes() -> None:
    w = _wavenumbers(n=20)
    signal = np.ones(19, dtype=np.complex128)
    with pytest.raises(ValueError):
        fit_dielectric_model(w, signal, kind=DRUDE)


def test_rejects_too_few_finite_samples() -> None:
    w = _wavenumbers(n=4)
    signal = np.ones(4, dtype=np.complex128)
    with pytest.raises(ValueError):
        fit_dielectric_model(w, signal, kind=DRUDE)  # 4 points, 5 params needed


# --------------------------------------------------------------------------- #
# JSON round-trip
# --------------------------------------------------------------------------- #


def test_to_dict_round_trips_through_json() -> None:
    import json

    w = _wavenumbers()
    true: dict[str, Any] = {
        "eps_inf": 4.0, "omega_p": 800.0, "gamma": 60.0, "scale": 1.2 + 0.3j, "offset": 0.1 - 0.05j
    }
    signal = _synthetic_drude_signal(w, **true)
    fit = fit_dielectric_model(w, signal, kind=DRUDE)
    payload = json.loads(json.dumps(fit.to_dict()))
    assert payload["kind"] == "drude"
    assert len(payload["wavenumber_cm1"]) == len(w)
    assert payload["gamma_cm1"] == pytest.approx(true["gamma"], rel=1e-3)
