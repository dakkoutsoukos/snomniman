"""snomniman.diagnostics - the Scientific Diagnostics Engine (depends on processing, core).

A Qt-free, read-only backend package that computes objective, reproducible,
scientifically defensible *facts* about a measurement: per-channel statistics,
topography geometry (plane slope, roughness, height range), optical harmonic
content (amplitude decay), and which registered operations structurally apply.

The processing engine performs deterministic scientific *operations*; the
diagnostics engine performs deterministic scientific *observations*. A future AI
Scientist reasons over these observations - it must never re-derive a fact from
raw arrays when a deterministic algorithm can establish it. The engine produces
facts, not opinions: no recommendations, no LLM calls, no provider APIs.

It is a sibling of :mod:`snomniman.describe` (which *projects* structure without
computing): consumers compose the two. Outputs are frozen, typed, and
JSON-serializable via each descriptor's ``to_dict``. See
``docs/diagnostics-engine.md`` (ADR-0019).
"""

from __future__ import annotations

from .descriptors import (
    HARMONIC_EMPTY,
    HARMONIC_NOISE,
    HARMONIC_SIGNAL,
    HARMONIC_UNKNOWN,
    HARMONIC_WEAK,
    ChannelStatistics,
    FeatureDiagnostics,
    HarmonicAmplitude,
    HarmonicDiagnostics,
    HistogramData,
    MeasurementDiagnostics,
    OperationApplicability,
    ParticleFeature,
    TopographyDiagnostics,
)
from .diagnose import (
    all_feature_diagnostics,
    channel_statistics,
    diagnose,
    feature_diagnostics,
    harmonic_diagnostics,
    histogram,
    operation_applicability,
    topography_diagnostics,
)

__all__ = [
    "HARMONIC_EMPTY",
    "HARMONIC_NOISE",
    "HARMONIC_SIGNAL",
    "HARMONIC_UNKNOWN",
    "HARMONIC_WEAK",
    "ChannelStatistics",
    "FeatureDiagnostics",
    "HarmonicAmplitude",
    "HarmonicDiagnostics",
    "HistogramData",
    "MeasurementDiagnostics",
    "OperationApplicability",
    "ParticleFeature",
    "TopographyDiagnostics",
    "all_feature_diagnostics",
    "channel_statistics",
    "diagnose",
    "feature_diagnostics",
    "harmonic_diagnostics",
    "histogram",
    "operation_applicability",
    "topography_diagnostics",
]
