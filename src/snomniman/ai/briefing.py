"""Build a Scientific Briefing from deterministic facts (the AI Scientist, v1).

``build_briefing`` composes the Scientific Description API and the Scientific
Diagnostics Engine into a structured orientation - "tell me about this measurement"
- whose every statement is a deterministic fact with a named source. An optional
:class:`~snomniman.ai.provider.NarrativeProvider` adds a natural-language
interpretation on top; the facts stand on their own when no provider is configured
(AI enhances understanding; it never gates it). Nothing here inspects raw arrays,
mutates the dataset, or touches the provenance DAG.
"""

from __future__ import annotations

from datetime import UTC, datetime

from snomniman.core import Dataset
from snomniman.describe import MeasurementDescription, describe_measurement
from snomniman.diagnostics import (
    HARMONIC_EMPTY,
    HARMONIC_NOISE,
    HARMONIC_SIGNAL,
    MeasurementDiagnostics,
    diagnose,
)

from .provider import NarrativeProvider
from .report import FACT, Briefing, BriefingContext, BriefingSection, BriefingStatement


def _fact(text: str, *sources: str) -> BriefingStatement:
    return BriefingStatement(text=text, kind=FACT, sources=tuple(sources))


def build_briefing(
    dataset: Dataset,
    *,
    title: str | None = None,
    provider: NarrativeProvider | None = None,
) -> Briefing:
    """Build a measurement-orientation briefing for *dataset* (read-only).

    The fact sections are always populated from `describe` + `diagnostics`. If
    *provider* is given, its narrative is attached as the (clearly secondary)
    interpretation, grounded in the same facts.
    """
    desc = describe_measurement(dataset, title=title)
    diag = diagnose(dataset, title=title)

    sections = (
        _summary_section(desc),
        _observations_section(desc, diag),
        _enables_section(desc, diag),
    )

    context = BriefingContext(description=desc.to_dict(), diagnostics=diag.to_dict())
    interpretation: str | None = None
    provider_name: str | None = None
    generated_at: str | None = None
    if provider is not None:
        interpretation = provider.narrate(context)
        provider_name = provider.name
        generated_at = datetime.now(UTC).isoformat()

    return Briefing(
        title=title,
        sections=sections,
        interpretation=interpretation,
        provider=provider_name,
        generated_at=generated_at,
        context=context,
    )


def _summary_section(desc: MeasurementDescription) -> BriefingSection:
    statements: list[BriefingStatement] = []
    state = "raw" if desc.is_raw else "derived"
    line = f"This is a {state} {desc.data_kind} measurement."
    if not desc.is_raw:
        line += f" {desc.provenance.n_steps} processing step(s) recorded."
    statements.append(_fact(line, "description"))

    geo = desc.metadata.geometry
    if geo.size_nm is not None:
        sx, sy = geo.size_nm
        statements.append(_fact(f"Scan area {sx / 1000:.3g} x {sy / 1000:.3g} um.", "description"))
    if geo.pixels is not None:
        px, py = geo.pixels
        statements.append(_fact(f"Sampling {px} x {py} pixels.", "description"))
    if desc.metadata.detection:
        statements.append(_fact(f"Detection method: {desc.metadata.detection}.", "description"))
    if desc.metadata.wavenumber_cm1 is not None:
        statements.append(_fact(
            f"Excitation at {desc.metadata.wavenumber_cm1:.0f} cm^-1.", "description"
        ))
    statements.append(_fact(f"{len(desc.channels)} channels present.", "description"))
    if desc.metadata.harmonics:
        joined = ", ".join(f"O{h}" for h in desc.metadata.harmonics)
        statements.append(_fact(f"Optical harmonics: {joined}.", "description"))
    ref = "reference" in desc.capabilities
    statements.append(_fact(
        "Reference channels are present." if ref else "No reference channels.", "description"
    ))
    return BriefingSection("Measurement Summary", tuple(statements))


def _observations_section(
    desc: MeasurementDescription, diag: MeasurementDiagnostics
) -> BriefingSection:
    statements: list[BriefingStatement] = []
    topo = diag.topography
    if topo is not None:
        unit = topo.unit or ""
        tilt = f"Topography shows a global tilt of {topo.slope_magnitude_per_um:.3g} {unit}/um."
        statements.append(_fact(tilt.strip(), "diagnostics"))
        if topo.rms_roughness is not None:
            statements.append(_fact(
                f"RMS roughness after detilting is {topo.rms_roughness:.3g} {unit}.".strip(),
                "diagnostics",
            ))
    plane = next((a for a in diag.applicability if a.step_id == "image.plane_level"), None)
    if plane is not None and plane.applicable:
        statements.append(_fact(
            "Plane leveling has already been applied."
            if plane.already_applied
            else "Plane leveling is applicable and has not yet been applied.",
            "diagnostics",
        ))
    harm = diag.harmonics
    if harm is not None and harm.amplitudes:
        signal = [a for a in harm.amplitudes if a.classification == HARMONIC_SIGNAL]
        not_signal = [
            a for a in harm.amplitudes if a.classification in (HARMONIC_NOISE, HARMONIC_EMPTY)
        ]
        if signal:
            orders = ", ".join(f"O{a.order}" for a in signal)
            statements.append(_fact(
                f"Optical harmonics carrying spatially-coherent signal: {orders}.", "diagnostics"
            ))
        if not_signal:
            labels = ", ".join(f"O{a.order} ({a.classification})" for a in not_signal)
            statements.append(_fact(
                f"Noise-dominated or unrecorded optical harmonics: {labels}.", "diagnostics"
            ))
        # Strongest among signal-bearing orders (avoids pointing at a background/DC order);
        # falls back to all orders when none could be classified (e.g. a tiny scan).
        pool = signal or list(harm.amplitudes)
        strongest = max(pool, key=lambda a: a.mean_amplitude)
        statements.append(_fact(
            f"Strongest mean optical amplitude among them is at O{strongest.order}.", "diagnostics"
        ))
    for stat in diag.channel_statistics:
        if stat.invalid_count:
            statements.append(_fact(
                f"Channel {stat.channel} contains {stat.invalid_count} invalid (NaN/inf) pixels.",
                "diagnostics",
            ))
    if desc.is_raw:
        statements.append(_fact(
            "This is the raw measurement; no processing has been applied.", "description"
        ))
    return BriefingSection("Scientific Observations", tuple(statements))


def _enables_section(
    desc: MeasurementDescription, diag: MeasurementDiagnostics
) -> BriefingSection:
    statements: list[BriefingStatement] = []
    caps = set(desc.capabilities)
    if "topography" in caps:
        statements.append(_fact(
            "Quantitative topography analysis (height, roughness, profiles).", "description"
        ))
    if "multi_harmonic" in caps:
        statements.append(_fact("Harmonic comparison across optical orders.", "description"))
    if "reference" in caps:
        statements.append(_fact("Reference-based normalization workflows.", "description"))
    for app in diag.applicability:
        if app.applicable:
            note = " (already applied)" if app.already_applied else ""
            statements.append(_fact(
                f"Operation '{app.step_id}' is applicable{note}: {app.description}", "diagnostics"
            ))
        else:
            missing = ", ".join(app.missing_capabilities)
            statements.append(_fact(
                f"Operation '{app.step_id}' is not applicable (needs {missing}).", "diagnostics"
            ))
    return BriefingSection("What This Measurement Enables", tuple(statements))


__all__ = ["build_briefing"]
