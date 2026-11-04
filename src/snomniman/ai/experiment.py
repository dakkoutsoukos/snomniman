"""Experiment-level Scientific Assistant: an Experiment Briefing and deterministic
outlier detection across a project's measurements (Phase 9A/9B,
``docs/phase7-9-master-roadmap.md`` Section 5).

Where :mod:`snomniman.ai.briefing` orients a researcher to *one measurement*, this
module orients them to a whole :class:`~snomniman.pipeline.Project`: how many
measurements it holds, what kinds they are, and whether any measurement's
deterministic facts sit statistically apart from its siblings. Every statement is
grounded exactly like a single-measurement :class:`~snomniman.ai.report.Briefing` -
sourced to a specific measurement's ``describe``/``diagnostics`` facts - so this adds
no new safety mechanism, only a new fact producer to reason over (CLAUDE.md's three
permanent AI rules apply unchanged).

This is the one new dependency edge Phase 9 introduces: ``ai -> pipeline`` (`pipeline`
already depends on ``processing``/``core`` and not on ``ai``, so this is non-cyclic).
Deliberately independent of :mod:`snomniman.gui.experiment` (a Qt-free *presenter*
that lives in ``gui`` because its only present consumer is the Explorer window,
Rule 7) - experiment-level *reasoning* is a judgment, not presentation aggregation,
so it belongs in the backend, operating directly on a ``Project``.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

from snomniman.describe import describe_measurement
from snomniman.diagnostics import MeasurementDiagnostics, diagnose
from snomniman.pipeline import Measurement, Project

from .report import (
    FACT,
    BriefingSection,
    BriefingStatement,
    ExperimentBriefing,
    ExperimentBriefingContext,
    OutlierMetric,
    OutlierReport,
)


def _fact(text: str, *sources: str) -> BriefingStatement:
    return BriefingStatement(text=text, kind=FACT, sources=tuple(sources))

#: A metric extractor returns ``(value, unit)`` for a measurement's diagnostics, or
#: ``None`` when that fact is not computable for that measurement - never guessed.
_Extractor = Callable[[MeasurementDiagnostics], tuple[float, str | None] | None]


def _extract_rms_roughness(diag: MeasurementDiagnostics) -> tuple[float, str | None] | None:
    topo = diag.topography
    if topo is None or topo.rms_roughness is None:
        return None
    return topo.rms_roughness, topo.unit


def _extract_tilt_magnitude(diag: MeasurementDiagnostics) -> tuple[float, str | None] | None:
    topo = diag.topography
    if topo is None:
        return None
    unit = f"{topo.unit}/um" if topo.unit else None
    return topo.slope_magnitude_per_um, unit


#: The fixed, small set of already-validated per-measurement diagnostics metrics
#: eligible for cross-measurement outlier detection. Adding a metric here is the
#: only extension point - no other code changes (mirrors the registry pattern used
#: throughout the backend).
_METRICS: tuple[tuple[str, _Extractor], ...] = (
    ("topography.rms_roughness", _extract_rms_roughness),
    ("topography.tilt_magnitude_per_um", _extract_tilt_magnitude),
)

#: A distribution of fewer than this many computable values is not meaningful; the
#: metric is skipped for that project (named in `OutlierReport.note`, not silently
#: dropped).
_MIN_MEASUREMENTS_FOR_STATISTICS = 3


def detect_outliers(project: Project, *, z_threshold: float = 2.0) -> OutlierReport:
    """Deterministic statistical outlier flags across *project*'s measurements.

    For each metric in :data:`_METRICS`, computes that metric's mean/std across every
    measurement where it is computable, and flags any measurement whose value sits at
    least ``z_threshold`` standard deviations from that mean. This is a plain
    descriptive statistic, not a scientific judgement about *why* a measurement
    differs (CLAUDE.md AI rule 1) - it never claims a measurement is instrumentally
    bad, only that it is numerically distant from its siblings in this project. A
    metric with fewer than :data:`_MIN_MEASUREMENTS_FOR_STATISTICS` computable values
    is skipped and named in ``note`` (a distribution needs enough points to be
    meaningful) rather than silently omitted.

    Honest limitation: comparing a metric across measurements assumes they share the
    same unit (each diagnostics fact keeps the unit of its own channel; no
    unit-conversion is attempted). A project mixing e.g. nm- and um-recorded height
    channels would compare mismatched units without warning - a known, documented gap
    (``docs/phase7-9-master-roadmap.md`` Section 5.3.2), not currently guarded against.
    """
    measurements = project.measurements
    diags = {m.measurement_id: diagnose(m.current, title=m.title) for m in measurements}

    all_metrics: list[OutlierMetric] = []
    skipped: list[str] = []
    for metric_name, extractor in _METRICS:
        rows: list[tuple[Measurement, float, str | None]] = []
        for m in measurements:
            extracted = extractor(diags[m.measurement_id])
            if extracted is None:
                continue
            value, unit = extracted
            if not math.isfinite(value):
                continue
            rows.append((m, value, unit))
        if len(rows) < _MIN_MEASUREMENTS_FOR_STATISTICS:
            if rows:
                skipped.append(metric_name)
            continue

        values = [v for _, v, _ in rows]
        mean = float(sum(values) / len(values))
        std = math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))
        for m, value, unit in rows:
            z = 0.0 if std <= 0.0 else (value - mean) / std
            all_metrics.append(
                OutlierMetric(
                    metric=metric_name,
                    unit=unit,
                    measurement_id=m.measurement_id,
                    measurement_title=m.title,
                    value=value,
                    project_mean=mean,
                    project_std=std,
                    z_score=z,
                    flagged=abs(z) >= z_threshold,
                )
            )

    note: str | None = None
    if skipped:
        note = (
            f"Outlier detection skipped for {', '.join(skipped)}: fewer than "
            f"{_MIN_MEASUREMENTS_FOR_STATISTICS} measurements have that metric computed."
        )
    return OutlierReport(
        title=project.title,
        threshold=z_threshold,
        metrics=tuple(all_metrics),
        flagged=tuple(m for m in all_metrics if m.flagged),
        note=note,
    )


def build_experiment_briefing(
    project: Project, *, title: str | None = None, z_threshold: float = 2.0
) -> ExperimentBriefing:
    """Build a whole-project orientation for *project* (read-only).

    Composes every measurement's ``describe``/``diagnostics`` facts (via each
    measurement's *active* dataset, ``Measurement.current``) plus the deterministic
    outlier flags from :func:`detect_outliers`. Always available - no narrative
    provider is wired in for v1 (CLAUDE.md AI rule 2: the deterministic facts are
    the whole point; a future provider seam, if added, would render on top of this
    exact grounding, mirroring :func:`~snomniman.ai.briefing.build_briefing`).
    """
    measurements = project.measurements
    per_measurement: dict[str, dict[str, Any]] = {}
    kinds: dict[str, int] = {}
    topo_count = 0
    for m in measurements:
        desc = describe_measurement(m.current, title=m.title)
        diag = diagnose(m.current, title=m.title)
        per_measurement[m.measurement_id] = {
            "description": desc.to_dict(),
            "diagnostics": diag.to_dict(),
        }
        kinds[desc.data_kind] = kinds.get(desc.data_kind, 0) + 1
        if diag.topography is not None:
            topo_count += 1

    outliers = detect_outliers(project, z_threshold=z_threshold)

    summary: list[BriefingStatement] = []
    summary.append(
        _fact(f"This experiment contains {len(measurements)} measurement(s).", "description")
    )
    if kinds:
        joined = ", ".join(f"{count} {kind}" for kind, count in sorted(kinds.items()))
        summary.append(_fact(f"Composition: {joined}.", "description"))

    observations: list[BriefingStatement] = []
    if measurements:
        observations.append(
            _fact(
                f"{topo_count} of {len(measurements)} measurement(s) have a topography channel.",
                "diagnostics",
            )
        )
    if outliers.flagged:
        for om in outliers.flagged:
            unit = f" {om.unit}" if om.unit else ""
            observations.append(
                _fact(
                    f"Measurement '{om.measurement_title}': {om.metric} = "
                    f"{om.value:.3g}{unit}, {om.z_score:+.2f} standard deviations from "
                    f"this experiment's mean "
                    f"({om.project_mean:.3g} +/- {om.project_std:.3g}{unit}).",
                    "diagnostics",
                )
            )
    elif outliers.metrics:
        observations.append(
            _fact(
                "No measurement's computed metrics are statistical outliers within "
                "this experiment.",
                "diagnostics",
            )
        )
    if outliers.note:
        observations.append(_fact(outliers.note, "diagnostics"))

    sections = (
        BriefingSection("Experiment Summary", tuple(summary)),
        BriefingSection("Cross-Measurement Observations", tuple(observations)),
    )
    context = ExperimentBriefingContext(
        measurement_ids=tuple(m.measurement_id for m in measurements),
        per_measurement=per_measurement,
    )
    return ExperimentBriefing(
        title=title if title is not None else project.title,
        n_measurements=len(measurements),
        sections=sections,
        context=context,
    )


__all__ = ["build_experiment_briefing", "detect_outliers"]
