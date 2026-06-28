"""The diagnostics functions - deterministic scientific observations of a dataset.

Each function computes objective, reproducible facts and returns a frozen
descriptor. They never mutate the dataset, never call an LLM, and never make
recommendations: the diagnostics engine produces facts, not opinions
(``docs/diagnostics-engine.md``). Computation is the line that separates this
package from :mod:`snomniman.describe`, which only projects what the core
already knows.

Dependencies: :mod:`snomniman.core` (Dataset/Metadata/Capability) and
:mod:`snomniman.processing` (the step registry, for applicability). Qt-free, like
the rest of the backend (Rule 4).
"""

from __future__ import annotations

import math

import numpy as np
import numpy.typing as npt

from snomniman.core import Capability, Dataset
from snomniman.processing import get_step, list_steps

from .descriptors import (
    ChannelStatistics,
    HarmonicAmplitude,
    HarmonicDiagnostics,
    MeasurementDiagnostics,
    OperationApplicability,
    TopographyDiagnostics,
)

#: nanometres per micrometre (slopes are reported per micrometre).
_NM_PER_UM = 1000.0


def channel_statistics(dataset: Dataset, name: str) -> ChannelStatistics:
    """Finite-value statistics for one channel (amplitude view if complex)."""
    info = {c.canonical: c for c in dataset.metadata.channels}.get(name)
    if dataset.is_complex(name):
        values = np.asarray(dataset.amplitude(name).values, dtype=np.float64)
        view = "amplitude"
        unit = info.amplitude_unit if info else "a.u."
    else:
        values = np.asarray(dataset.channel(name).values, dtype=np.float64)
        view = "value"
        unit = info.value_unit if info else None

    flat = values.ravel()
    count = int(flat.size)
    finite_mask = np.isfinite(flat)
    finite_count = int(finite_mask.sum())
    invalid_count = count - finite_count
    if finite_count == 0:
        return ChannelStatistics(
            channel=name, view=view, unit=unit, count=count,
            finite_count=0, invalid_count=invalid_count,
            minimum=None, maximum=None, mean=None, std=None, dynamic_range=None,
        )
    fv = flat[finite_mask]
    minimum = float(fv.min())
    maximum = float(fv.max())
    return ChannelStatistics(
        channel=name, view=view, unit=unit, count=count,
        finite_count=finite_count, invalid_count=invalid_count,
        minimum=minimum, maximum=maximum,
        mean=float(fv.mean()), std=float(fv.std()),
        dynamic_range=maximum - minimum,
    )


def topography_diagnostics(dataset: Dataset) -> TopographyDiagnostics | None:
    """Plane slope, height range, and post-tilt roughness of the topography channel.

    Returns ``None`` when the dataset has no real topography channel or is not a
    2-D scan (slope is undefined without both spatial axes).
    """
    topo = [c for c in dataset.channels(kind="topography") if not dataset.is_complex(c)]
    if not topo or Capability.SPATIAL_2D not in dataset.capabilities:
        return None
    # Report the *signal* topography (the measured height), never a reference height
    # channel (R_Z*); prefer the canonical "Z" when present.
    signal_topo = [
        c for c in dataset.channels(role="signal", kind="topography")
        if not dataset.is_complex(c)
    ]
    candidates = signal_topo or topo
    name = "Z" if "Z" in candidates else candidates[0]
    info = {c.canonical: c for c in dataset.metadata.channels}.get(name)
    unit = info.value_unit if info else None

    values = np.asarray(dataset.channel(name).values, dtype=np.float64)
    x = np.asarray(dataset.coordinate("x").values, dtype=np.float64)
    y = np.asarray(dataset.coordinate("y").values, dtype=np.float64)

    a, b, plane = _fit_plane(values, x, y)
    if a is None or b is None or plane is None:
        return None

    residual = values - plane
    finite = np.isfinite(values)
    height_range = (
        float(np.nanmax(values) - np.nanmin(values)) if finite.any() else None
    )
    rms_roughness = float(np.nanstd(residual)) if finite.any() else None
    slope_x = a * _NM_PER_UM
    slope_y = b * _NM_PER_UM
    return TopographyDiagnostics(
        channel=name,
        unit=unit,
        slope_x_per_um=slope_x,
        slope_y_per_um=slope_y,
        slope_magnitude_per_um=math.hypot(slope_x, slope_y),
        height_range=height_range,
        rms_roughness=rms_roughness,
        minimum=float(np.nanmin(values)) if finite.any() else None,
        maximum=float(np.nanmax(values)) if finite.any() else None,
    )


def harmonic_diagnostics(dataset: Dataset) -> HarmonicDiagnostics | None:
    """Mean amplitude and decay ratio per optical signal harmonic (ascending order).

    Returns ``None`` when no optical signal channel carries a harmonic order.
    """
    by_name = {c.canonical: c for c in dataset.metadata.channels}
    pairs: list[tuple[int, str]] = []
    for name in dataset.channel_names:
        info = by_name.get(name)
        if info is None or info.kind != "optical" or info.role != "signal":
            continue
        if info.harmonic is None:
            continue
        pairs.append((info.harmonic, name))
    if not pairs:
        return None
    pairs.sort()

    amplitudes: list[HarmonicAmplitude] = []
    prev_mean: float | None = None
    for order, name in pairs:
        if dataset.is_complex(name):
            vals = np.asarray(dataset.amplitude(name).values, dtype=np.float64)
        else:
            vals = np.abs(np.asarray(dataset.channel(name).values, dtype=np.float64))
        mean = float(np.nanmean(vals))
        ratio = (mean / prev_mean) if (prev_mean is not None and prev_mean != 0.0) else None
        amplitudes.append(HarmonicAmplitude(order=order, mean_amplitude=mean, decay_ratio=ratio))
        prev_mean = mean
    return HarmonicDiagnostics(
        harmonics=tuple(order for order, _ in pairs),
        amplitudes=tuple(amplitudes),
    )


def operation_applicability(dataset: Dataset) -> tuple[OperationApplicability, ...]:
    """Structural applicability of every *registered* operation to this dataset.

    Reflects whatever steps are currently registered: the caller imports the
    operation sub-packages it cares about (e.g. ``import snomniman.processing.image``)
    before calling, exactly as the GUI does. Facts only - never a recommendation.
    """
    caps = dataset.capabilities
    applied = {n.record.step_id for n in dataset.provenance.iter_nodes()}
    out: list[OperationApplicability] = []
    for step_id in list_steps():
        cls = get_step(step_id)
        required = tuple(cls.required_capabilities)
        missing = tuple(c for c in required if c not in caps)
        out.append(
            OperationApplicability(
                step_id=step_id,
                description=cls.description,
                applicable=not missing,
                required_capabilities=tuple(c.value for c in required),
                missing_capabilities=tuple(c.value for c in missing),
                already_applied=step_id in applied,
            )
        )
    return tuple(out)


def diagnose(dataset: Dataset, *, title: str | None = None) -> MeasurementDiagnostics:
    """Compute the full diagnostics report for *dataset* (read-only)."""
    return MeasurementDiagnostics(
        title=title,
        is_raw=dataset.is_raw,
        channel_statistics=tuple(
            channel_statistics(dataset, name) for name in dataset.channel_names
        ),
        topography=topography_diagnostics(dataset),
        harmonics=harmonic_diagnostics(dataset),
        applicability=operation_applicability(dataset),
    )


def _fit_plane(
    values: npt.NDArray[np.float64],
    x: npt.NDArray[np.float64],
    y: npt.NDArray[np.float64],
) -> tuple[float | None, float | None, npt.NDArray[np.float64] | None]:
    """Least-squares plane ``z = a*x + b*y + c`` over finite pixels.

    Returns ``(a, b, plane)`` where ``a``/``b`` are gradients per nm and ``plane``
    is the fitted surface over the full grid; ``(None, None, None)`` if fewer than
    three finite pixels make the fit ill-posed. Distinct from
    ``processing.image.fit_surface``: this masks non-finite pixels and returns the
    coefficients (the slope), which the leveling operation does not need.
    """
    xx, yy = np.meshgrid(x, y)
    design = np.column_stack([xx.ravel(), yy.ravel(), np.ones(xx.size)])
    z = values.ravel()
    finite = np.isfinite(z)
    if int(finite.sum()) < 3:
        return None, None, None
    coeffs, *_ = np.linalg.lstsq(design[finite], z[finite], rcond=None)
    plane: npt.NDArray[np.float64] = (design @ coeffs).reshape(values.shape)
    return float(coeffs[0]), float(coeffs[1]), plane


__all__ = [
    "channel_statistics",
    "diagnose",
    "harmonic_diagnostics",
    "operation_applicability",
    "topography_diagnostics",
]
