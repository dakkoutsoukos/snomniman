"""Drude / Lorentz-oscillator dielectric-model fitting (Phase 8A - the first
:mod:`snomniman.physics` capability, ``docs/phase7-9-master-roadmap.md`` Section
4.3, capabilities 2-3).

This fits a **physically-named** resonance shape directly to a measured complex
near-field spectrum (amplitude and phase, e.g. after ``spectrum.ratio``/``spectrum.
savgol_smooth``): a free-carrier Drude response or a phonon/molecular Lorentz
oscillator response, each of the standard textbook form (Ashcroft & Mermin; Wooten;
see :func:`drude_epsilon`/:func:`lorentz_epsilon`, the full reference forms used by
Phase 8B's forward model).

**A real identifiability finding, not a hedge.** A measured near-field signal
``s(omega)`` is not the sample's bulk dielectric function - the practical way to fit
a resonance shape to it is ``s(omega) = scale * shape(omega) + offset`` for a free
complex ``scale``/``offset`` absorbing the near-field signal's unknown proportionality
and background (the same practical device Phase 6's phenomenological Lorentzian
lineshape fit used). Synthetic round-trip testing (Rule 6) caught something an
initial draft of this module got wrong: in the textbook Drude form, ``omega_p``
appears **only** as the scalar prefactor ``omega_p^2`` - it never affects the curve's
*shape* as a function of frequency, only its overall (complex) scale. It is therefore
**exactly degenerate with the free ``scale``** and cannot be recovered by this fit
under any circumstances, no matter the SNR - not a hard-to-converge case, a
genuinely unidentifiable one. The same is true of the Lorentz oscillator's
``strength``: ``strength * omega_to^2`` is again just a scalar prefactor. What *is*
shape-identifiable, because it changes where and how the curve varies with
frequency (not just its overall scale), is:

- **Drude**: only ``gamma`` (the damping/scattering rate) - the free-carrier plasma
  frequency ``omega_p`` (and hence carrier density) is **not** recoverable from this
  practical fit; it requires the tip-model calibration of Phase 8B.
- **Lorentz**: ``omega_to`` (the resonance/TO-phonon frequency) **and** ``gamma``
  (the linewidth) - the oscillator ``strength`` is **not** recoverable here, for the
  same reason ``omega_p`` is not.

:class:`DielectricFit` therefore never reports ``omega_p``/``strength``/``eps_inf`` -
their absence is a mathematical fact about what this practical fit can defend, not a
missing feature (CLAUDE.md: "a missing capability is preferable to an unjustified
one"). This is also, precisely, *why* Phase 8B (the finite dipole model) is
scientifically necessary rather than merely more accurate: it is the only path to a
calibrated amplitude, and hence to ``omega_p``/carrier density (Phase 8C) at all.

This is the "tool, not judgement" half of Phase 8
(``docs/phase7-9-master-roadmap.md`` Section 4.1): the fit is always available and
previewable, but a low ``r_squared`` means the chosen model does not describe this
spectrum - never a claim about the true bulk material response.

Convention: frequencies are in **wavenumber** (cm^-1), the unit this codebase's
spectral axis already uses (``SpectralInfo.wavenumber_cm1``) and the unit IR
spectroscopy literature itself reports Drude/Lorentz parameters in - not SI angular
frequency. The functional *form* is identical under this substitution; only the
numerical scale of ``gamma``/``omega_to`` changes, exactly as published values
already are.

Scientific validation: a synthetic spectrum generated from known ``(omega_p, gamma)``
/ ``(strength, omega_to, gamma)`` plus a known complex scale/offset recovers
``gamma`` / ``(omega_to, gamma)`` within a documented tolerance **regardless of**
the (unrecoverable) ``omega_p``/``strength``/``eps_inf`` used to generate the data
(the identifiability claim, checked directly); fitting the wrong model family (Drude
to a Lorentz-shaped resonance) is verified to score honestly low - see
``tests/test_physics_dielectric.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt
from scipy.optimize import least_squares

FloatArray = npt.NDArray[np.float64]
ComplexArray = npt.NDArray[np.complex128]

#: The dielectric-model families :func:`fit_dielectric_model` supports.
DRUDE = "drude"
LORENTZ = "lorentz"
MODEL_KINDS: tuple[str, ...] = (DRUDE, LORENTZ)

#: Free parameter count per model kind (shape-identifiable physical params + complex
#: scale + complex offset): Drude = (gamma) + 4 = 5; Lorentz = (omega_to, gamma) + 4
#: = 6. Deliberately excludes omega_p/strength/eps_inf - see the module docstring.
_N_PARAMS = {DRUDE: 5, LORENTZ: 6}


def drude_epsilon(
    wavenumber_cm1: FloatArray, eps_inf: float, omega_p_cm1: float, gamma_cm1: float
) -> ComplexArray:
    """The Drude free-carrier dielectric function, evaluated in wavenumber (cm^-1).

    ``epsilon(w) = eps_inf - omega_p^2 / (w^2 + i*w*gamma)`` (Ashcroft & Mermin). The
    full reference form (used by Phase 8B's forward model, once implemented); NOT
    what :func:`fit_dielectric_model` fits - ``eps_inf``/``omega_p`` are not
    identifiable from a practical near-field fit, see the module docstring.
    """
    w = np.asarray(wavenumber_cm1, dtype=np.float64)
    denom = w**2 + 1j * w * gamma_cm1
    with np.errstate(divide="ignore", invalid="ignore"):
        result = eps_inf - (omega_p_cm1**2) / denom
    return np.asarray(result, dtype=np.complex128)


def lorentz_epsilon(
    wavenumber_cm1: FloatArray,
    eps_inf: float,
    strength: float,
    omega_to_cm1: float,
    gamma_cm1: float,
) -> ComplexArray:
    """A single Lorentz-oscillator dielectric function, in wavenumber (cm^-1).

    ``epsilon(w) = eps_inf + S*w_TO^2 / (w_TO^2 - w^2 - i*w*gamma)`` (Wooten). The
    full reference form; see :func:`drude_epsilon`'s docstring note - ``eps_inf``/
    ``strength`` are not identifiable from a practical near-field fit either.
    """
    w = np.asarray(wavenumber_cm1, dtype=np.float64)
    denom = omega_to_cm1**2 - w**2 - 1j * w * gamma_cm1
    with np.errstate(divide="ignore", invalid="ignore"):
        result = eps_inf + strength * (omega_to_cm1**2) / denom
    return np.asarray(result, dtype=np.complex128)


def _drude_shape(wavenumber_cm1: FloatArray, gamma_cm1: float) -> ComplexArray:
    """The shape-identifiable part of the Drude form (``omega_p`` fixed at 1 - any
    other value is exactly absorbed by the fit's free complex scale)."""
    w = np.asarray(wavenumber_cm1, dtype=np.float64)
    denom = w**2 + 1j * w * gamma_cm1
    with np.errstate(divide="ignore", invalid="ignore"):
        result = -1.0 / denom
    return np.asarray(result, dtype=np.complex128)


def _lorentz_shape(
    wavenumber_cm1: FloatArray, omega_to_cm1: float, gamma_cm1: float
) -> ComplexArray:
    """The shape-identifiable part of the Lorentz form (``strength`` fixed at 1 -
    any other value is exactly absorbed by the fit's free complex scale)."""
    w = np.asarray(wavenumber_cm1, dtype=np.float64)
    denom = omega_to_cm1**2 - w**2 - 1j * w * gamma_cm1
    with np.errstate(divide="ignore", invalid="ignore"):
        result = 1.0 / denom
    return np.asarray(result, dtype=np.complex128)


@dataclass(frozen=True)
class DielectricFit:
    """A Drude or Lorentz-oscillator resonance-shape fit to a measured near-field spectrum.

    A read-only analysis (Rule 4/Section 3.3 of the Phase 6 design doc's own
    precedent): it fits, but never mutates, a spectrum a researcher is already
    looking at, and is not a :class:`~snomniman.processing.ProcessingStep` (it
    reports a fact - a fitted parameter set - not a new dataset to chain from).
    ``gamma_cm1`` is always present (the Drude damping rate or the Lorentz
    linewidth); ``omega_to_cm1`` is Lorentz-only (``None`` for Drude - a pure Drude
    response has no resonance position to report). There is **no** ``omega_p``,
    ``strength``, or ``eps_inf``: none is identifiable from ``scale``/``offset`` in
    this practical fit (see the module docstring) - absent, never a fabricated
    value. ``scale``/``offset`` are the fitted complex affine terms absorbing the
    near-field signal's unknown proportionality and any constant background.
    Uncertainties are one asymptotic standard error from the linearized
    least-squares covariance (the same approximation
    :func:`scipy.optimize.curve_fit` uses internally) - ``NaN`` when the fit is
    singular/ill-conditioned, never a fabricated number.
    """

    kind: str
    omega_to_cm1: float | None
    omega_to_stderr: float | None
    gamma_cm1: float
    gamma_stderr: float
    scale_re: float
    scale_im: float
    offset_re: float
    offset_im: float
    r_squared: float
    rms: float
    n_points: int
    wavenumber_cm1: FloatArray
    fit_curve_re: FloatArray
    fit_curve_im: FloatArray
    residuals_re: FloatArray
    residuals_im: FloatArray

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "omega_to_cm1": self.omega_to_cm1,
            "omega_to_stderr": self.omega_to_stderr,
            "gamma_cm1": self.gamma_cm1,
            "gamma_stderr": self.gamma_stderr,
            "scale_re": self.scale_re,
            "scale_im": self.scale_im,
            "offset_re": self.offset_re,
            "offset_im": self.offset_im,
            "r_squared": self.r_squared,
            "rms": self.rms,
            "n_points": self.n_points,
            "wavenumber_cm1": [float(v) for v in self.wavenumber_cm1],
            "fit_curve_re": [float(v) for v in self.fit_curve_re],
            "fit_curve_im": [float(v) for v in self.fit_curve_im],
            "residuals_re": [float(v) for v in self.residuals_re],
            "residuals_im": [float(v) for v in self.residuals_im],
        }


def _model_signal(wavenumber_cm1: FloatArray, kind: str, params: FloatArray) -> ComplexArray:
    if kind == DRUDE:
        gamma, scale_re, scale_im, offset_re, offset_im = params
        shape = _drude_shape(wavenumber_cm1, gamma)
    else:
        omega_to, gamma, scale_re, scale_im, offset_re, offset_im = params
        shape = _lorentz_shape(wavenumber_cm1, omega_to, gamma)
    scale = complex(scale_re, scale_im)
    offset = complex(offset_re, offset_im)
    return np.asarray(scale * shape + offset, dtype=np.complex128)


def _residuals(
    params: FloatArray, wavenumber_cm1: FloatArray, signal: ComplexArray, kind: str
) -> FloatArray:
    model = _model_signal(wavenumber_cm1, kind, params)
    diff = model - signal
    return np.concatenate([diff.real, diff.imag])


def _initial_guess(
    wavenumber_cm1: FloatArray, signal: ComplexArray, kind: str
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """Data-driven initial parameters + bounds (lower, upper) for the least-squares fit.

    ``shape(w)`` can be many orders of magnitude smaller than the data near a narrow
    resonance (its numerator is fixed at 1, unlike the true, unknown oscillator
    strength) - a naive ``scale0 = 1`` initial guess then leaves the optimizer
    started many decades away from the correct scale, in a badly-conditioned basin.
    Estimating ``scale0`` directly from the data's amplitude relative to
    ``shape(w)`` evaluated at the initial resonance/gamma guess fixes this
    regardless of the true (unrecoverable) oscillator strength.
    """
    w = wavenumber_cm1
    deviation = np.abs(signal - np.mean(signal))
    peak_idx = int(np.argmax(deviation)) if deviation.size else 0
    resonance_guess = float(w[peak_idx]) if w.size else 1.0
    span = float(w.max() - w.min()) if w.size > 1 else 1.0
    gamma_guess = max(span / 10.0, 1e-6)

    offset0 = np.array([float(np.mean(signal.real)), float(np.mean(signal.imag))])
    if kind == DRUDE:
        shape0 = _drude_shape(w, gamma_guess)
    else:
        shape0 = _lorentz_shape(w, resonance_guess, gamma_guess)
    shape_scale = float(np.mean(np.abs(shape0))) if shape0.size else 1.0
    data_scale = float(np.mean(np.abs(signal - (offset0[0] + 1j * offset0[1]))))
    scale_mag = data_scale / shape_scale if shape_scale > 1e-300 else 1.0
    scale0 = np.array([scale_mag, 0.0])

    if kind == DRUDE:
        p0 = np.array([gamma_guess, *scale0, *offset0], dtype=np.float64)
        lower = np.array([1e-9, -np.inf, -np.inf, -np.inf, -np.inf])
        upper = np.array([span * 10.0 + 1.0, np.inf, np.inf, np.inf, np.inf])
    else:
        p0 = np.array([resonance_guess, gamma_guess, *scale0, *offset0], dtype=np.float64)
        lower = np.array([0.0, 1e-9, -np.inf, -np.inf, -np.inf, -np.inf])
        upper = np.array([np.inf, span * 10.0 + 1.0, np.inf, np.inf, np.inf, np.inf])
    return p0, lower, upper


def fit_dielectric_model(
    wavenumber_cm1: FloatArray, signal: ComplexArray, *, kind: str = DRUDE
) -> DielectricFit:
    """Fit a Drude or Lorentz-oscillator resonance shape to a measured near-field spectrum.

    ``wavenumber_cm1``/``signal`` are the full spectrum (monotonically increasing
    wavenumber; ``signal`` the complex near-field value, e.g. ``amplitude *
    exp(1j*phase)`` of an already-processed channel). Every finite sample is used
    (unlike :func:`~snomniman.viz.measure.fit_lineshape`, there is no separate fit
    window - a dielectric response is a property of the whole spectrum, not a single
    peak). Raises :exc:`ValueError` for an unknown ``kind``, mismatched array shapes,
    too few finite samples to constrain the model, or a fit that fails to converge.
    """
    if kind not in MODEL_KINDS:
        raise ValueError(
            f"fit_dielectric_model: kind must be one of {MODEL_KINDS}, got {kind!r}"
        )
    w = np.asarray(wavenumber_cm1, dtype=np.float64)
    s = np.asarray(signal, dtype=np.complex128)
    if w.shape != s.shape:
        raise ValueError(
            "fit_dielectric_model: wavenumber_cm1 and signal must have the same shape, "
            f"got {w.shape} and {s.shape}"
        )
    finite = np.isfinite(w) & np.isfinite(s.real) & np.isfinite(s.imag)
    n_params = _N_PARAMS[kind]
    n_points = int(finite.sum())
    if n_points <= n_params:
        raise ValueError(
            f"fit_dielectric_model: {n_points} finite sample(s); need more than "
            f"{n_params} to fit the {kind} model"
        )
    wf, sf = w[finite], s[finite]

    p0, lower, upper = _initial_guess(wf, sf, kind)
    result = least_squares(
        _residuals,
        p0,
        args=(wf, sf, kind),
        bounds=(lower, upper),
        x_scale="jac",
        max_nfev=20000,
    )
    if not result.success:
        raise ValueError(f"fit_dielectric_model: the fit did not converge - {result.message}")

    params = result.x
    dof = max(2 * n_points - n_params, 1)
    ss_res = float(np.sum(result.fun**2))
    s_sq = ss_res / dof
    jac = result.jac
    try:
        cov = np.linalg.inv(jac.T @ jac) * s_sq
        diag = np.diag(cov)
        stderr = np.sqrt(diag) if np.all(diag >= 0.0) else np.full(n_params, np.nan)
    except np.linalg.LinAlgError:
        stderr = np.full(n_params, np.nan)

    stacked = np.concatenate([sf.real, sf.imag])
    ss_tot = float(np.sum((stacked - np.mean(stacked)) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0.0 else float("nan")
    rms = float(np.sqrt(np.mean(result.fun**2)))

    fit_curve = _model_signal(w, kind, params)
    residuals_full = s - fit_curve

    if kind == DRUDE:
        gamma, scale_re, scale_im, offset_re, offset_im = (float(v) for v in params)
        (gamma_se,) = (float(v) for v in stderr[:1])
        omega_to = omega_to_se = None
    else:
        omega_to, gamma, scale_re, scale_im, offset_re, offset_im = (float(v) for v in params)
        omega_to_se, gamma_se = (float(v) for v in stderr[:2])

    return DielectricFit(
        kind=kind,
        omega_to_cm1=omega_to,
        omega_to_stderr=omega_to_se,
        gamma_cm1=gamma,
        gamma_stderr=gamma_se,
        scale_re=scale_re,
        scale_im=scale_im,
        offset_re=offset_re,
        offset_im=offset_im,
        r_squared=r_squared,
        rms=rms,
        n_points=n_points,
        wavenumber_cm1=w,
        fit_curve_re=np.asarray(fit_curve.real, dtype=np.float64),
        fit_curve_im=np.asarray(fit_curve.imag, dtype=np.float64),
        residuals_re=np.asarray(residuals_full.real, dtype=np.float64),
        residuals_im=np.asarray(residuals_full.imag, dtype=np.float64),
    )


__all__ = [
    "DRUDE",
    "LORENTZ",
    "MODEL_KINDS",
    "DielectricFit",
    "drude_epsilon",
    "fit_dielectric_model",
    "lorentz_epsilon",
]
