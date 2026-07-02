"""Projection functions - the entry points of the Scientific Description API.

Each function is a **pure, read-only projection**: it never mutates its inputs and
never performs scientific computation.  It reports what the scientific core and the
processing registry already know, in a structured, JSON-serializable shape.

Dependencies: :mod:`snomniman.core` (Dataset / Metadata / provenance / RawSource)
and :mod:`snomniman.processing` (the step registry, for the operation catalogue).
Qt-free, like the rest of the backend (Rule 4).  See ``docs/description-api.md``.
"""

from __future__ import annotations

from pathlib import Path

from snomniman.core import Dataset, Metadata, ProvenanceNode, RawSource
from snomniman.processing import get_step, list_steps
from snomniman.processing.step import InputSpec, ParameterSpec, ProcessingStep

from .descriptors import (
    ChannelDescription,
    ConventionsDescription,
    GeometryDescription,
    LineageStep,
    MeasurementDescription,
    MetadataSummary,
    OperationDescription,
    OperationInputSlot,
    OperationParameter,
    ProvenanceSummary,
    SourceDescription,
    SpectralGeometryDescription,
)


def describe_channels(dataset: Dataset) -> tuple[ChannelDescription, ...]:
    """Describe every channel actually present in *dataset* (in data order)."""
    by_name = {c.canonical: c for c in dataset.metadata.channels}
    out: list[ChannelDescription] = []
    for name in dataset.channel_names:
        info = by_name.get(name)
        is_complex = dataset.is_complex(name)
        views = ("amplitude", "phase") if is_complex else ("value",)
        out.append(
            ChannelDescription(
                canonical=name,
                kind=info.kind if info else None,
                role=info.role if info else None,
                harmonic=info.harmonic if info else None,
                is_complex=is_complex,
                dtype=str(dataset.channel(name).dtype),
                state=info.state if info else "raw",
                value_unit=info.value_unit if info else None,
                amplitude_unit=info.amplitude_unit if info else None,
                phase_unit=info.phase_unit if info else None,
                available_views=views,
            )
        )
    return tuple(out)


def summarize_metadata(metadata: Metadata) -> MetadataSummary:
    """Project typed :class:`~snomniman.core.Metadata` into a glanceable summary."""
    m = metadata
    return MetadataSummary(
        data_kind=m.data_kind.value,
        vendor=m.instrument.vendor,
        model=m.instrument.model,
        software_version=m.instrument.software_version,
        source_type=m.excitation.source_type,
        detector=m.excitation.detector,
        wavenumber_cm1=m.excitation.wavenumber_cm1,
        wavelength_nm=m.excitation.wavelength_nm,
        detection=m.demodulation.detection,
        harmonics=tuple(m.demodulation.harmonics),
        datetime=m.acquisition.datetime,
        integration_time_s=m.acquisition.integration_time_s,
        tapping_amplitude_nm=m.acquisition.tapping_amplitude_nm,
        setpoint=m.acquisition.setpoint,
        averaging=m.acquisition.averaging,
        geometry=GeometryDescription(
            pixels=m.scan.pixels,
            size_nm=m.scan.size_nm,
            pixel_size_nm=m.scan.pixel_size_nm,
            offset_nm=m.scan.offset_nm,
            center_nm=m.scan.center_nm,
            rotation_deg=m.scan.rotation_deg,
        ),
        spectral=(
            None
            if m.spectral is None
            else SpectralGeometryDescription(
                wavenumber_min_cm1=m.spectral.wavenumber_min_cm1,
                wavenumber_max_cm1=m.spectral.wavenumber_max_cm1,
                n_points=m.spectral.n_points,
                sampling_cm1=m.spectral.sampling_cm1,
            )
        ),
        conventions=ConventionsDescription(
            spatial_unit=m.conventions.spatial_unit,
            origin=m.conventions.origin,
            x_dir=m.conventions.x_dir,
            y_dir=m.conventions.y_dir,
            phase_unit=m.conventions.phase_unit,
            phase_reference=m.conventions.phase_reference,
            phase_sign=m.conventions.phase_sign,
        ),
        original_units=dict(m.original_units),
    )


def summarize_provenance(node: ProvenanceNode) -> ProvenanceSummary:
    """Walk the provenance DAG from *node* and report its derivation history."""
    steps: list[LineageStep] = []
    distinct: dict[tuple[str, str], SourceDescription] = {}
    for n in node.iter_nodes():
        rec = n.record
        sources: list[SourceDescription] = []
        for edge, src in n.sources.items():
            desc = _describe_source(edge, src)
            sources.append(desc)
            distinct.setdefault((src.path, src.sha256), desc)
        steps.append(
            LineageStep(
                node_id=n.node_id,
                step_id=rec.step_id,
                step_version=rec.step_version,
                deterministic=rec.deterministic,
                params=dict(rec.params),
                software=dict(rec.software),
                applied_at=rec.applied_at,
                inputs=tuple(n.inputs.keys()),
                sources=tuple(sources),
                is_raw=n.is_raw,
            )
        )
    return ProvenanceSummary(
        is_raw=node.is_raw,
        n_steps=len(steps),
        steps=tuple(steps),
        sources=tuple(distinct.values()),
    )


def describe_operations() -> tuple[OperationDescription, ...]:
    """Describe every registered processing operation (the catalogue).

    Reflects whatever is currently registered: the caller is responsible for
    importing the operation sub-packages it cares about (e.g.
    ``import snomniman.processing.image``) before calling, exactly as the GUI and
    the future pipeline replay engine do.  This is the registry-wide catalogue;
    per-dataset *applicability* (does this operation apply to this measurement?)
    is computed by :mod:`snomniman.diagnostics`, which reads each step's declared
    ``required_capabilities`` - ``describe`` stays a pure projection.
    """
    return tuple(_describe_step_class(get_step(step_id)) for step_id in list_steps())


def describe_operation(step_id: str) -> OperationDescription:
    """Describe one registered operation; raises ``ProcessingError`` if unknown."""
    return _describe_step_class(get_step(step_id))


def describe_measurement(
    dataset: Dataset, *, title: str | None = None
) -> MeasurementDescription:
    """The top-level aggregate description of *dataset* (read-only)."""
    return MeasurementDescription(
        title=title,
        data_kind=dataset.kind.value,
        is_raw=dataset.is_raw,
        dims={str(k): int(v) for k, v in dataset.data.sizes.items()},
        capabilities=tuple(sorted(c.value for c in dataset.capabilities)),
        channels=describe_channels(dataset),
        metadata=summarize_metadata(dataset.metadata),
        provenance=summarize_provenance(dataset.provenance),
    )


def _describe_source(name: str, src: RawSource) -> SourceDescription:
    return SourceDescription(
        name=name,
        path=src.path,
        filename=Path(src.path).name,
        sha256=src.sha256,
        reader=src.reader,
        is_directory=src.is_directory,
        bytes=src.bytes,
    )


def _describe_step_class(cls: type[ProcessingStep]) -> OperationDescription:
    return OperationDescription(
        step_id=cls.step_id,
        version=cls.version,
        description=cls.description,
        deterministic=cls.deterministic,
        parameters=tuple(_describe_parameter(s) for s in cls.param_specs()),
        inputs=tuple(_describe_input(s) for s in cls.input_specs()),
    )


def _describe_input(spec: InputSpec) -> OperationInputSlot:
    return OperationInputSlot(name=spec.name, description=spec.description)


def _describe_parameter(spec: ParameterSpec) -> OperationParameter:
    return OperationParameter(
        name=spec.name,
        description=spec.description,
        types=tuple(t.__name__ for t in spec.py_type),
        required=spec.required,
        default=spec.default,
        choices=spec.choices,
        channel_role=spec.channel_role,
    )


__all__ = [
    "describe_channels",
    "describe_measurement",
    "describe_operation",
    "describe_operations",
    "summarize_metadata",
    "summarize_provenance",
]
