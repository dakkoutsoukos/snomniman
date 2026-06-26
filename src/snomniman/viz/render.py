"""Display-ready render data for one channel view (architecture.md sec 3, viz).

This is the Qt-free heart of visualization: it turns a :class:`Dataset` channel
into a :class:`RenderData` value object - the 2-D array to show, its physical
extent honoring the lower-left origin convention (OHD-6C), a recommended colormap
and value range, and the unit/label - *without* any toolkit. The GUI consumes
this; it does not re-derive any of it. Keeping these decisions here (not in
widgets) means the scientific-display choices are testable headlessly and can
never drift between viewers.

Honesty about representation is the key job. A complex optical/mechanical channel
is never shown "raw": the researcher chooses **amplitude** (magnitude) or
**phase** (angle), and phase is flagged ``cyclic`` with a cyclic colormap because
it wraps at +/-pi - it must *look* like an angle, not a height. Phase is shown
exactly as imported (OHD-6D): no invert/re-reference/unwrap/normalize happens
here. Colormaps are named with matplotlib names; resolving a name to a lookup
table is the GUI's job, so this module stays free of any rendering toolkit.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from snomniman.core import ChannelInfo, Dataset

#: Representations of a channel a viewer can show.
AMPLITUDE = "amplitude"
PHASE = "phase"
REAL = "real"

#: Robust display-range percentiles (clip extreme outliers, keep the structure).
_LO_PCT, _HI_PCT = 1.0, 99.0

#: Recommended matplotlib colormap names (the GUI resolves these to LUTs).
_CMAP_AMPLITUDE = "viridis"
_CMAP_TOPOGRAPHY = "afmhot"
_CMAP_PHASE = "twilight"  # perceptually-uniform cyclic map, right for wrapped phase


@dataclass(frozen=True)
class RenderData:
    """Everything a viewer needs to draw one channel view honestly."""

    channel: str
    representation: str  # AMPLITUDE | PHASE | REAL
    values: npt.NDArray[np.float64]  # (y, x), lower-left origin (row 0 = bottom)
    extent_nm: tuple[float, float, float, float]  # (x_min, x_max, y_min, y_max), pixel edges
    vmin: float
    vmax: float
    colormap: str  # matplotlib colormap name
    cyclic: bool  # True for phase (wraps at +/-pi)
    unit: str
    label: str  # e.g. "O2 amplitude"
    title: str  # e.g. "O2 amplitude (a.u.)"


def available_representations(dataset: Dataset, channel: str) -> tuple[str, ...]:
    """Representations the viewer may offer for ``channel``.

    Complex channels are shown as amplitude *or* phase (two views of one quantity);
    real channels have a single representation.
    """
    return (AMPLITUDE, PHASE) if dataset.is_complex(channel) else (REAL,)


def default_representation(dataset: Dataset, channel: str) -> str:
    """The representation a viewer should show first (amplitude carries contrast)."""
    return AMPLITUDE if dataset.is_complex(channel) else REAL


def prepare_channel(
    dataset: Dataset, channel: str, representation: str | None = None
) -> RenderData:
    """Build display-ready :class:`RenderData` for ``channel`` (default rep if unset)."""
    rep = representation or default_representation(dataset, channel)
    allowed = available_representations(dataset, channel)
    if rep not in allowed:
        raise ValueError(f"channel {channel!r} has no {rep!r} view; choose from {allowed}")

    if rep == AMPLITUDE:
        values = np.asarray(dataset.amplitude(channel).values, dtype=np.float64)
        unit = _amplitude_unit(dataset, channel)
        vmin, vmax = _robust_range(values)
        colormap, cyclic = _CMAP_AMPLITUDE, False
    elif rep == PHASE:
        values = np.asarray(dataset.phase(channel).values, dtype=np.float64)
        unit = "rad"
        vmin, vmax = -np.pi, np.pi  # phase is angular; fixed honest range
        colormap, cyclic = _CMAP_PHASE, True
    else:  # REAL
        values = np.asarray(dataset.channel(channel).values, dtype=np.float64)
        unit = _real_unit(dataset, channel)
        vmin, vmax = _robust_range(values)
        colormap = _CMAP_TOPOGRAPHY if _is_topography(dataset, channel) else _CMAP_AMPLITUDE
        cyclic = False

    label = f"{channel} {rep}" if rep != REAL else channel
    title = f"{label} ({unit})" if unit else label
    return RenderData(
        channel=channel,
        representation=rep,
        values=values,
        extent_nm=_extent_nm(dataset),
        vmin=vmin,
        vmax=vmax,
        colormap=colormap,
        cyclic=cyclic,
        unit=unit,
        label=label,
        title=title,
    )


def pick_scale_bar(span_nm: float, *, fraction: float = 0.2) -> tuple[float, str]:
    """Choose a tidy scale-bar length (~``fraction`` of ``span_nm``) and its label.

    Snaps to a 1/2/5 x 10^k length so the bar reads as a round physical distance,
    and labels it in nm or um. Returns ``(length_nm, label)``.
    """
    if not span_nm > 0:
        return 0.0, ""
    target = span_nm * fraction
    power = np.floor(np.log10(target))
    base = target / (10.0**power)
    nice = 1.0 if base < 1.5 else 2.0 if base < 3.5 else 5.0 if base < 7.5 else 10.0
    length = float(nice * 10.0**power)
    return length, _length_label(length)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _robust_range(values: npt.NDArray[np.float64]) -> tuple[float, float]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return 0.0, 1.0
    lo, hi = (float(v) for v in np.percentile(finite, [_LO_PCT, _HI_PCT]))
    if not hi > lo:  # flat/dead channel - give a non-degenerate range
        hi = lo + 1.0
    return lo, hi


def _extent_nm(dataset: Dataset) -> tuple[float, float, float, float]:
    """Physical pixel-edge extent (x_min, x_max, y_min, y_max) in nm, lower-left."""
    x = np.asarray(dataset.coordinate("x").values, dtype=np.float64)
    y = np.asarray(dataset.coordinate("y").values, dtype=np.float64)
    dx = float(x[1] - x[0]) if x.size > 1 else 1.0
    dy = float(y[1] - y[0]) if y.size > 1 else 1.0
    return (
        float(x[0] - dx / 2),
        float(x[-1] + dx / 2),
        float(y[0] - dy / 2),
        float(y[-1] + dy / 2),
    )


def _length_label(length_nm: float) -> str:
    if length_nm >= 1000.0:
        return f"{length_nm / 1000.0:g} µm"
    return f"{length_nm:g} nm"


def _is_topography(dataset: Dataset, channel: str) -> bool:
    info = _channel_info(dataset, channel)
    return info is not None and info.kind == "topography"


def _amplitude_unit(dataset: Dataset, channel: str) -> str:
    info = _channel_info(dataset, channel)
    return (info.amplitude_unit if info and info.amplitude_unit else "a.u.")


def _real_unit(dataset: Dataset, channel: str) -> str:
    info = _channel_info(dataset, channel)
    if info and info.value_unit:
        return info.value_unit
    attr_unit = dataset.channel(channel).attrs.get("value_unit")
    return str(attr_unit) if attr_unit else ""


def _channel_info(dataset: Dataset, channel: str) -> ChannelInfo | None:
    try:
        return dataset.metadata.channel(channel)
    except KeyError:
        return None


__all__ = [
    "AMPLITUDE",
    "PHASE",
    "REAL",
    "RenderData",
    "available_representations",
    "default_representation",
    "pick_scale_bar",
    "prepare_channel",
]
