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


@dataclass(frozen=True)
class HarmonicAmplitude:
    """Mean amplitude of one optical harmonic, and its decay vs the previous order."""

    order: int
    mean_amplitude: float
    #: ``mean_amplitude`` divided by that of the next-lower present order; ``None``
    #: for the lowest order present. In s-SNOM a value well below 1 indicates the
    #: expected background suppression at higher harmonics.
    decay_ratio: float | None

    def to_dict(self) -> dict[str, Any]:
        return {k: _jsonify(v) for k, v in asdict(self).items()}


@dataclass(frozen=True)
class HarmonicDiagnostics:
    """Optical harmonic content, by amplitude (a deterministic confidence proxy).

    No "SNR" is reported: a true SNR needs a noise model or a signal-free region,
    neither of which is available deterministically here. The amplitude-decay
    ratio is reported instead - a measurable, convention-free quantity.
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
    "ChannelStatistics",
    "HarmonicAmplitude",
    "HarmonicDiagnostics",
    "MeasurementDiagnostics",
    "OperationApplicability",
    "TopographyDiagnostics",
]
