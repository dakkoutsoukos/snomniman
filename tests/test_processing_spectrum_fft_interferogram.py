"""Tests for spectrum.fft_interferogram - Phase 5A spectral processing foundations.

Validates the four deliverables of docs/phase5-spectral-nanoftir.md sec 6.1 through
the one registered operation that exercises them (``processing.spectrum._math`` is
private, tested only through this public step, matching how ``processing.image``'s
own private ``_region`` helpers are tested - see ``test_processing_image_region_ops.py``):

- **FFT** (Part 1): a synthetic interferogram built from a known analytic Lorentzian
  spectrum (Rule 6) recovers that spectrum's peak position and width within a
  documented tolerance - the Appendix A worked example of the design doc, made real.
- **Apodization** (Part 2): the four research-supported windows are selectable, the
  window is correctly centered on the zero-path-difference (ZPD) sample (not the
  array's geometric center - the load-bearing bug this suite caught during
  implementation: a symmetric window naively centered on the array zeroes out a
  single-sided interferogram's highest-amplitude sample, its very first point), and
  apodization visibly broadens the recovered peak and suppresses sidelobes relative
  to no apodization (boxcar), exactly as apodization theory predicts.
- **Phase correction** (Part 3): zero-filling is an exact interpolation of the
  unpadded FFT (a documented numerical property, not just "looks right"), and Mertz
  phase correction measurably reduces the residual phase error introduced by a
  ZPD-registration offset plus a smooth instrumental phase error, compared to no
  correction.
- **Framework integration** (Part 5): provenance, immutability, capability
  gating, and the ``DataKind`` change (``INTERFEROGRAM`` -> ``SPECTRUM``) - the
  first operation to exercise that already-supported mechanism.
"""

from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

import snomniman.processing.spectrum  # noqa: F401  (registers spectrum ops, incl. fft_interferogram)
from snomniman.core import (
    Capability,
    ChannelInfo,
    DataKind,
    Dataset,
    Metadata,
    ProvenanceNode,
    StepRecord,
)
from snomniman.core.exceptions import ProcessingError
from snomniman.processing import get_step
from snomniman.viz.measure import Peak, analyze_profile

_N = 4096
_OPD_STEP_CM = 1.0e-4  # 1 micron
_CENTER_CM1 = 1735.0
_WIDTH_CM1 = 12.0
_BIN_SPACING_CM1 = 1.0 / (_N * _OPD_STEP_CM)  # ~2.44 cm^-1


def _lorentzian(wavenumber: np.ndarray, *, center: float = _CENTER_CM1, width: float = _WIDTH_CM1,
                 amplitude: float = 1.0) -> np.ndarray:
    return amplitude / (1.0 + ((wavenumber - center) / (width / 2.0)) ** 2)


def _interferogram_dataset(
    signal: np.ndarray, opd: np.ndarray, *, channel: str = "O2"
) -> Dataset:
    """An INTERFEROGRAM Dataset wrapping a real *signal* along an *opd* axis (cm)."""
    data = xr.Dataset(
        {channel: ("opd", signal.astype(np.float64))},
        coords={"opd": ("opd", opd, {"unit": "cm", "long_name": "optical path difference"})},
    )
    metadata = Metadata(
        data_kind=DataKind.INTERFEROGRAM,
        channels=(ChannelInfo(channel, "optical", "signal", "float64", amplitude_unit="a.u."),),
    )
    node = ProvenanceNode(
        node_id="n0", record=StepRecord(step_id="io.read", step_version=1, deterministic=True)
    )
    return Dataset(data, kind=DataKind.INTERFEROGRAM, metadata=metadata, provenance=node)


def _known_lorentzian_dataset(*, seed: int = 1, noise_scale: float = 1e-5) -> Dataset:
    """A single-sided synthetic interferogram (ZPD at index 0) of a known Lorentzian."""
    wn_true = np.fft.rfftfreq(_N, d=_OPD_STEP_CM)
    spectrum = _lorentzian(wn_true).astype(np.complex128)
    rng = np.random.default_rng(seed)
    signal = np.fft.irfft(spectrum, n=_N) + rng.normal(scale=noise_scale, size=_N)
    opd = np.arange(_N, dtype=np.float64) * _OPD_STEP_CM
    return _interferogram_dataset(signal, opd)


def _fft(ds: Dataset, **params: object) -> Dataset:
    return get_step("spectrum.fft_interferogram")(**params).apply({"primary": ds})


def _main_peak(wavenumber: np.ndarray, magnitude: np.ndarray) -> Peak:
    features = analyze_profile(wavenumber, magnitude, unit="cm-1")
    return max(features.peaks, key=lambda p: p.value)


# -- Part 1: FFT - known-answer recovery (Appendix A) ------------------------ #


def test_recovers_known_lorentzian_peak_position() -> None:
    ds = _known_lorentzian_dataset()
    result = _fft(ds, channel="O2", apodization="boxcar", zero_fill=1, phase_correction="none")
    assert result.kind is DataKind.SPECTRUM
    wn = result.coordinate("wavenumber").values
    mag = np.abs(result.channel("O2").values)
    peak = _main_peak(wn, mag)
    assert abs(peak.position_nm - _CENTER_CM1) < 1.5 * _BIN_SPACING_CM1


def test_recovers_known_lorentzian_width_without_apodization() -> None:
    # Boxcar (no apodization) at zero_fill=1 is the cleanest case: the FFT is a
    # near-exact inverse of the synthetic construction (rfft(irfft(X)) == X).
    ds = _known_lorentzian_dataset(noise_scale=0.0)
    result = _fft(ds, channel="O2", apodization="boxcar", zero_fill=1, phase_correction="none")
    wn = result.coordinate("wavenumber").values
    mag = np.abs(result.channel("O2").values)
    np.testing.assert_allclose(
        mag, _lorentzian(wn), atol=1e-6, err_msg="unwindowed round trip should reproduce the input"
    )
    peak = _main_peak(wn, mag)
    assert peak.fwhm_nm is not None
    assert abs(peak.fwhm_nm - _WIDTH_CM1) / _WIDTH_CM1 < 0.1


def test_output_channel_is_complex_with_expected_metadata() -> None:
    ds = _known_lorentzian_dataset()
    result = _fft(ds, channel="O2")
    assert result.is_complex("O2")
    info = result.metadata.channel("O2")
    assert info.state == "spectrum"
    assert info.phase_unit == "rad"
    assert result.metadata.spectral is not None
    assert result.metadata.spectral.n_points == result.coordinate("wavenumber").size
    assert result.metadata.interferometer is not None
    assert result.metadata.interferometer.apodization == "blackman_harris_3"  # the default


# -- Part 2: apodization -------------------------------------------------- #


def test_apodization_window_centers_on_zpd_not_array_center() -> None:
    # The bug this test pins: a Hann window naively centered on the array is zero
    # at index 0, annihilating a single-sided interferogram's ZPD (its highest-
    # amplitude sample) - the recovered spectrum would collapse to near-zero.
    ds = _known_lorentzian_dataset(noise_scale=0.0)
    result = _fft(ds, channel="O2", apodization="hann", zero_fill=1, phase_correction="none")
    mag = np.abs(result.channel("O2").values)
    assert mag.max() > 0.5  # coherent-gain normalized: a real peak, not near-zero


@pytest.mark.parametrize("apodization", ["hann", "hamming", "blackman_harris_3"])
def test_apodization_recovers_peak_position(apodization: str) -> None:
    ds = _known_lorentzian_dataset(noise_scale=0.0)
    result = _fft(ds, channel="O2", apodization=apodization, zero_fill=4, phase_correction="none")
    wn = result.coordinate("wavenumber").values
    mag = np.abs(result.channel("O2").values)
    peak = _main_peak(wn, mag)
    assert abs(peak.position_nm - _CENTER_CM1) < 2.0 * _BIN_SPACING_CM1


@pytest.mark.parametrize("apodization", ["hann", "hamming", "blackman_harris_3"])
def test_apodization_broadens_peak_relative_to_boxcar(apodization: str) -> None:
    # Apodization trades resolution for sidelobe suppression - every window here is
    # expected to broaden the main lobe relative to no apodization (textbook
    # behaviour, e.g. Harris 1978's mainlobe-width table).
    ds = _known_lorentzian_dataset(noise_scale=0.0)
    boxcar = _fft(ds, channel="O2", apodization="boxcar", zero_fill=4, phase_correction="none")
    windowed = _fft(
        ds, channel="O2", apodization=apodization, zero_fill=4, phase_correction="none"
    )
    boxcar_peak = _main_peak(
        boxcar.coordinate("wavenumber").values, np.abs(boxcar.channel("O2").values)
    )
    windowed_peak = _main_peak(
        windowed.coordinate("wavenumber").values, np.abs(windowed.channel("O2").values)
    )
    assert boxcar_peak.fwhm_nm is not None and windowed_peak.fwhm_nm is not None
    assert windowed_peak.fwhm_nm > 1.3 * boxcar_peak.fwhm_nm


def test_boxcar_apodization_exposes_more_sidelobes_than_blackman_harris() -> None:
    # A quantitative illustration of *why* apodization matters: an unwindowed
    # interferogram's sinc-shaped instrument line function rings broadly; the
    # 3-term Blackman-Harris window (~-67 dB sidelobes, Harris 1978) suppresses it.
    ds = _known_lorentzian_dataset(noise_scale=0.0)
    boxcar = _fft(ds, channel="O2", apodization="boxcar", zero_fill=4, phase_correction="none")
    bh3 = _fft(
        ds, channel="O2", apodization="blackman_harris_3", zero_fill=4, phase_correction="none"
    )
    boxcar_peaks = analyze_profile(
        boxcar.coordinate("wavenumber").values, np.abs(boxcar.channel("O2").values), unit="cm-1"
    ).peaks
    bh3_peaks = analyze_profile(
        bh3.coordinate("wavenumber").values, np.abs(bh3.channel("O2").values), unit="cm-1"
    ).peaks
    assert len(boxcar_peaks) > len(bh3_peaks)


def test_default_apodization_is_blackman_harris_3() -> None:
    step = get_step("spectrum.fft_interferogram")(channel="O2")
    assert step.params["apodization"] == "blackman_harris_3"


def test_unknown_apodization_is_rejected() -> None:
    with pytest.raises(ProcessingError):
        get_step("spectrum.fft_interferogram")(channel="O2", apodization="rectangular_typo")


# -- Part 4: spectral utilities - zero-fill is exact interpolation ----------- #


def test_zero_fill_is_exact_interpolation_at_original_bins() -> None:
    # A documented, verifiable DSP property: zero-padding before an FFT exactly
    # interpolates the underlying DTFT - the padded FFT's values at the original
    # (unpadded) bin frequencies exactly match the unpadded FFT.
    ds = _known_lorentzian_dataset(noise_scale=0.0)
    zf1 = _fft(ds, channel="O2", apodization="boxcar", zero_fill=1, phase_correction="none")
    zf4 = _fft(ds, channel="O2", apodization="boxcar", zero_fill=4, phase_correction="none")
    wn1 = zf1.coordinate("wavenumber").values
    wn4 = zf4.coordinate("wavenumber").values
    mag1 = np.abs(zf1.channel("O2").values)
    mag4 = np.abs(zf4.channel("O2").values)
    matching = mag4[:: 4][: mag1.size]
    matching_wn = wn4[:: 4][: wn1.size]
    np.testing.assert_allclose(matching_wn, wn1, atol=1e-9)
    np.testing.assert_allclose(matching, mag1, atol=1e-10)


def test_zero_fill_increases_point_count_without_new_resolution() -> None:
    ds = _known_lorentzian_dataset(noise_scale=0.0)
    zf1 = _fft(ds, channel="O2", zero_fill=1)
    zf4 = _fft(ds, channel="O2", zero_fill=4)
    n1, n4 = zf1.coordinate("wavenumber").size, zf4.coordinate("wavenumber").size
    # A real-FFT of length n has n // 2 + 1 points; zero-filling to 4x the length
    # gives (4n) // 2 + 1, not exactly 4x due to that "+1" (Nyquist bin) offset.
    assert n4 == (4 * _N) // 2 + 1
    assert n1 == _N // 2 + 1


def test_zero_fill_below_one_is_rejected() -> None:
    ds = _known_lorentzian_dataset()
    with pytest.raises(ProcessingError, match="zero_fill"):
        _fft(ds, channel="O2", zero_fill=0)


# -- Part 3: phase correction (Mertz) ---------------------------------------- #


def _peak_phase(ds: Dataset, phase_correction: str, *, apodization: str = "boxcar") -> float:
    result = _fft(
        ds, channel="O2", apodization=apodization, zero_fill=1, phase_correction=phase_correction
    )
    spectrum = result.channel("O2").values
    magnitude = np.abs(spectrum)
    mask = magnitude > 0.5 * magnitude.max()
    return float(np.mean(np.angle(spectrum[mask])))


def test_mertz_phase_correction_reduces_zpd_offset_phase_error() -> None:
    """A ZPD-registration offset plus a smooth instrumental phase corrupts the
    recovered phase; Mertz correction should recover it closer to the phase a
    correctly-registered, uncorrupted measurement would show (~0, by construction)."""
    wn_true = np.fft.rfftfreq(_N, d=_OPD_STEP_CM)
    spectrum_true = _lorentzian(wn_true).astype(np.complex128)

    ground_truth = _interferogram_dataset(
        np.fft.irfft(spectrum_true, n=_N), np.arange(_N, dtype=np.float64) * _OPD_STEP_CM
    )
    ground_truth_phase = _peak_phase(ground_truth, "none")

    zpd_offset = 8  # samples
    a, b, c = 0.15, 0.005, -0.0002
    instrumental_phase = a + b * (wn_true - _CENTER_CM1) + c * (wn_true - _CENTER_CM1) ** 2
    corrupted_spectrum = (spectrum_true * np.exp(1j * instrumental_phase)).astype(np.complex128)
    corrupted_signal = np.roll(np.fft.irfft(corrupted_spectrum, n=_N), zpd_offset)
    corrupted_opd = (np.arange(_N, dtype=np.float64) - zpd_offset) * _OPD_STEP_CM
    corrupted = _interferogram_dataset(corrupted_signal, corrupted_opd)

    uncorrected_phase = _peak_phase(corrupted, "none")
    corrected_phase = _peak_phase(corrupted, "mertz")

    uncorrected_error = abs(uncorrected_phase - ground_truth_phase)
    corrected_error = abs(corrected_phase - ground_truth_phase)
    assert uncorrected_error > 1.0  # the corruption is substantial, uncorrected
    assert corrected_error < 0.5  # Mertz recovers most of it
    assert corrected_error < 0.5 * uncorrected_error


def test_phase_correction_none_is_the_identity_on_a_clean_interferogram() -> None:
    ds = _known_lorentzian_dataset(noise_scale=0.0)
    corrected = _fft(ds, channel="O2", apodization="boxcar", zero_fill=1, phase_correction="mertz")
    uncorrected = _fft(ds, channel="O2", apodization="boxcar", zero_fill=1, phase_correction="none")
    # A clean, correctly-registered interferogram has ~zero instrumental phase, so
    # Mertz correction should change very little.
    np.testing.assert_allclose(
        np.abs(corrected.channel("O2").values), np.abs(uncorrected.channel("O2").values), atol=1e-3
    )


def test_default_phase_correction_is_mertz() -> None:
    step = get_step("spectrum.fft_interferogram")(channel="O2")
    assert step.params["phase_correction"] == "mertz"


# -- framework integration: capabilities, provenance, DataKind, refusals ----- #


def test_required_capabilities() -> None:
    assert get_step("spectrum.fft_interferogram").required_capabilities == (
        Capability.INTERFEROMETRIC,
    )


def test_interferogram_dataset_has_interferometric_capability() -> None:
    ds = _known_lorentzian_dataset()
    assert ds.has_capability(Capability.INTERFEROMETRIC)
    assert not ds.has_capability(Capability.SPECTRAL)


def test_output_has_spectral_not_interferometric_capability() -> None:
    ds = _known_lorentzian_dataset()
    result = _fft(ds, channel="O2")
    assert result.has_capability(Capability.SPECTRAL)
    assert not result.has_capability(Capability.INTERFEROMETRIC)


def test_data_kind_changes_from_interferogram_to_spectrum() -> None:
    ds = _known_lorentzian_dataset()
    assert ds.kind is DataKind.INTERFEROGRAM
    result = _fft(ds, channel="O2")
    assert result.kind is DataKind.SPECTRUM


def test_input_is_not_mutated() -> None:
    ds = _known_lorentzian_dataset()
    before = np.array(ds.channel("O2").values, copy=True)
    _fft(ds, channel="O2")
    np.testing.assert_array_equal(ds.channel("O2").values, before)


def test_provenance_records_the_step() -> None:
    ds = _known_lorentzian_dataset()
    result = _fft(ds, channel="O2", apodization="hann", zero_fill=2, phase_correction="none")
    node = result.provenance
    assert node.record.step_id == "spectrum.fft_interferogram"
    assert node.record.params["apodization"] == "hann"
    assert node.record.params["zero_fill"] == 2
    assert node.inputs["primary"] is ds.provenance


def test_deterministic_reruns_are_bit_identical() -> None:
    ds = _known_lorentzian_dataset()
    a = _fft(ds, channel="O2")
    b = _fft(ds, channel="O2")
    np.testing.assert_array_equal(a.channel("O2").values, b.channel("O2").values)


# -- refusals: refuse, never silently reconcile ------------------------------ #


def test_rejects_complex_channel() -> None:
    wn_true = np.fft.rfftfreq(_N, d=_OPD_STEP_CM)
    spectrum = _lorentzian(wn_true).astype(np.complex128)
    signal = np.fft.irfft(spectrum, n=_N)
    complex_signal = (signal + 1j * signal).astype(np.complex128)
    data = xr.Dataset(
        {"O2": ("opd", complex_signal)},
        coords={"opd": ("opd", np.arange(_N, dtype=np.float64) * _OPD_STEP_CM, {"unit": "cm"})},
    )
    metadata = Metadata(
        data_kind=DataKind.INTERFEROGRAM,
        channels=(ChannelInfo("O2", "optical", "signal", "complex128", amplitude_unit="a.u."),),
    )
    node = ProvenanceNode(
        node_id="n0", record=StepRecord(step_id="io.read", step_version=1, deterministic=True)
    )
    ds = Dataset(data, kind=DataKind.INTERFEROGRAM, metadata=metadata, provenance=node)
    with pytest.raises(ProcessingError, match="complex"):
        _fft(ds, channel="O2")


def test_rejects_wrong_data_kind() -> None:
    ds = _known_lorentzian_dataset()
    wrong = Dataset(ds.data, kind=DataKind.SPECTRUM, metadata=ds.metadata, provenance=ds.provenance)
    with pytest.raises(ProcessingError, match="INTERFEROGRAM"):
        _fft(wrong, channel="O2")


def test_rejects_non_uniform_opd_sampling() -> None:
    opd = np.concatenate([np.arange(100) * 1e-4, np.arange(100, 200) * 2e-4])
    signal = np.sin(opd * 1e3)
    ds = _interferogram_dataset(signal, opd)
    with pytest.raises(ProcessingError, match="uniformly sampled"):
        _fft(ds, channel="O2")


def test_rejects_missing_channel() -> None:
    ds = _known_lorentzian_dataset()
    with pytest.raises(ProcessingError, match="not found"):
        _fft(ds, channel="does_not_exist")


def test_rejects_wrong_dims() -> None:
    opd = np.arange(8, dtype=np.float64) * 1e-4
    s = np.arange(3, dtype=np.float64)
    signal = np.outer(s, np.linspace(1.0, 0.0, 8))
    data = xr.Dataset(
        {"O2": (("s", "opd"), signal)},
        coords={
            "s": ("s", s, {"unit": "nm"}),
            "opd": ("opd", opd, {"unit": "cm"}),
        },
    )
    metadata = Metadata(
        data_kind=DataKind.INTERFEROGRAM,
        channels=(ChannelInfo("O2", "optical", "signal", "float64", amplitude_unit="a.u."),),
    )
    node = ProvenanceNode(
        node_id="n0", record=StepRecord(step_id="io.read", step_version=1, deterministic=True)
    )
    ds = Dataset(data, kind=DataKind.INTERFEROGRAM, metadata=metadata, provenance=node)
    with pytest.raises(ProcessingError, match="opd"):
        _fft(ds, channel="O2")
