"""Structured, JSON-serializable descriptors for the Scientific Diagnostics Engine.

These frozen value objects carry *computed* facts about a measurement - statistics,
topography geometry, harmonic content, and per-operation applicability. They are the
diagnostics counterpart of :mod:`snomniman.describe`'s descriptors: where ``describe``
*projects* what the core already knows, ``diagnostics`` *measures* the measurement and
reports the numbers. Like the description descriptors they hold **honest values**
(``None`` where a quantity cannot be computed, never a placeholder) and serialize
losslessly to JSON-ready ``dict`` via :meth:`to_dict`.

Produced by :mod:`snomniman.diagnostics.diagnose`. See ``docs/diagnostics-engine.md``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ChannelStatistics:
    """Deterministic statistics for one channel, over its finite values.

    For complex channels the statistics describe the amplitude view ``abs(O)``
    (``view == "amplitude"``); phase is cyclic and is deliberately not summarized
    this way (OHD-6D). For real channels they describe the values directly
    (``view == "value"``). ``invalid_count`` is the number of non-finite pixels
    (NaN/inf); statistics are computed over the finite remainder only.
    """

    channel: str
    view: str  # "value" | "amplitude"
    unit: str | None
    count: int
    finite_count: int
    invalid_count: int
    minimum: float | None
    maximum: float | None
    mean: float | None
    std: float | None
    dynamic_range: float | None  # maximum - minimum

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


@dataclass(frozen=True)
class TopographyDiagnostics:
    """Deterministic facts about the topography (height) channel.

    The plane is an ordinary least-squares fit ``z = a*x + b*y + c`` over the
    finite pixels; ``slope_*`` are the fitted gradients. Slopes are reported per
    micrometre (the natural scale for SNOM tilt) in the channel's height unit.
    ``rms_roughness`` is the standard deviation of the residual after plane
    removal (an Sq-like roughness with global tilt removed).
    """

    channel: str
    unit: str | None  # height unit (e.g. "nm")
    slope_x_per_um: float  # height-unit per micrometre, x direction
    slope_y_per_um: float
    slope_magnitude_per_um: float
    height_range: float | None
    rms_roughness: float | None
    minimum: float | None
    maximum: float | None

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


#: Harmonic signal-vs-noise classification labels (docs/harmonic-ranking-analysis.md).
HARMONIC_SIGNAL = "signal"  # spatially-coherent content above the noise floor
HARMONIC_WEAK = "weak"  # signal comparable to or below noise (the transition band)
HARMONIC_NOISE = "noise"  # noise-dominated / incoherent
HARMONIC_EMPTY = "empty"  # not meaningfully recorded (~zero variance)
HARMONIC_UNKNOWN = "unknown"  # cannot be computed (no 2-D amplitude image)


@dataclass(frozen=True)
class HarmonicAmplitude:
    """One optical harmonic's magnitude, decay, and signal-vs-noise classification.

    Beyond magnitude this carries a deterministic, validated answer to "is this
    harmonic signal or noise?" (docs/harmonic-ranking-analysis.md, Outcome 1):

    - ``spatial_coherence`` - mean lag-1 autocorrelation of the amplitude image (over
      x and y), a structure-vs-noise measure with an analytical white-noise null
      ``~N(0, 1/N)``; ``~1`` for smooth signal, ``~0`` for white noise. ``None`` when
      there is no 2-D amplitude image or the channel is degenerate.
    - ``snr_estimate`` - a single-image signal-to-noise estimate using an Immerkaer
      (1996) noise-floor estimate (``signal_std / noise_std``); ``None`` likewise. This
      discharges ADR-0019's SNR deferral *for a validated single-image estimate*.
    - ``classification`` - the conservative summary, one of :data:`HARMONIC_SIGNAL` /
      :data:`HARMONIC_WEAK` / :data:`HARMONIC_NOISE` / :data:`HARMONIC_EMPTY` /
      :data:`HARMONIC_UNKNOWN`.

    This is a **noise-floor / coherence** classification, NOT a near-field-vs-background
    or "best-harmonic" judgement: a low order dominated by far-field background is
    legitimately "signal" here (it carries coherent content). Choosing the working
    harmonic remains an expert judgement (see the knowledge base), not a computed fact.
    """

    order: int
    mean_amplitude: float
    #: ``mean_amplitude`` divided by that of the next-lower present order; ``None``
    #: for the lowest order present. In s-SNOM a value well below 1 indicates the
    #: expected background suppression at higher harmonics.
    decay_ratio: float | None
    spatial_coherence: float | None = None
    snr_estimate: float | None = None
    classification: str = HARMONIC_UNKNOWN

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


@dataclass(frozen=True)
class HarmonicDiagnostics:
    """Optical harmonic content: magnitude, decay, and signal-vs-noise classification.

    Reports mean amplitude and the convention-free decay ratio per order, plus a
    deterministic per-harmonic signal/noise classification (spatial coherence +
    single-image SNR; docs/harmonic-ranking-analysis.md). The classification answers
    the M4 "which orders are signal vs. noise" question; it does not rank harmonics by
    "informativeness" (rejected as not deterministically defensible - see the study).
    """

    harmonics: tuple[int, ...]  # optical signal orders present, ascending
    amplitudes: tuple[HarmonicAmplitude, ...]

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


@dataclass(frozen=True)
class OperationApplicability:
    """Whether a registered operation structurally applies to this dataset.

    Purely factual: ``applicable`` is true iff the dataset has every
    :class:`~snomniman.core.Capability` the step declares. It is *not* a
    recommendation - whether the operation is scientifically advisable is a
    separate (future, AI) judgement, never made here.
    """

    step_id: str
    description: str
    applicable: bool
    required_capabilities: tuple[str, ...]
    missing_capabilities: tuple[str, ...]
    already_applied: bool  # this step_id already appears in the provenance DAG

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


@dataclass(frozen=True)
class MeasurementDiagnostics:
    """The aggregate of all computed diagnostics for one dataset.

    Deliberately lean: it carries only *computed* facts plus a minimal identity
    (``title``/``is_raw``). The structural summary (dims, kind, channels,
    metadata, provenance) is the job of :mod:`snomniman.describe`; consumers
    (the Explorer, a future AI) compose the two rather than this duplicating it.
    """

    title: str | None
    is_raw: bool
    channel_statistics: tuple[ChannelStatistics, ...]
    topography: TopographyDiagnostics | None
    harmonics: HarmonicDiagnostics | None
    applicability: tuple[OperationApplicability, ...]

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


def _jsonify(obj: Any) -> Any:
    """Recursively convert tuples to lists so the result is JSON-round-trippable."""
    if isinstance(obj, dict):
        return {k: _jsonify(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonify(v) for v in obj]
    return obj


__all__ = [
    "HARMONIC_EMPTY",
    "HARMONIC_NOISE",
    "HARMONIC_SIGNAL",
    "HARMONIC_UNKNOWN",
    "HARMONIC_WEAK",
    "ChannelStatistics",
    "HarmonicAmplitude",
    "HarmonicDiagnostics",
    "MeasurementDiagnostics",
    "OperationApplicability",
    "TopographyDiagnostics",
]
