"""Quantitative measurements: read-only observations derived from a grid.

A *measurement* extracts information from the data without changing it - a line
profile, a distance, the statistics of a region. This is the opposite of
processing (which derives new data): nothing here returns or mutates a Dataset.
The functions are pure NumPy over an array plus its physical pixel-center
coordinates, so they are validated against synthetic inputs with known answers
(Rule 6); the GUI overlays consume them.

Coordinates are the canonical pixel-center axes (monotonically increasing nm,
lower-left origin). Physical points map to fractional pixel indices by
interpolation against those axes, so non-square or offset grids are handled
correctly.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
from scipy.signal import find_peaks, peak_widths

FloatArray = npt.NDArray[np.float64]


@dataclass(frozen=True)
class RegionStats:
    """Summary statistics of a region (all read-only observations).

    Carries the descriptive variability set (``count``, ``mean``, ``median``,
    ``std``, ``rms``) plus the inter-quartile markers (``p25``, ``p75``); the newer
    fields default to NaN so older positional construction stays valid.
    """

    count: int
    area_nm2: float
    mean: float
    median: float
    minimum: float
    maximum: float
    std: float
    rms: float = float("nan")
    p25: float = float("nan")
    p75: float = float("nan")


def distance(p0: tuple[float, float], p1: tuple[float, float]) -> tuple[float, float, float]:
    """Return ``(length, dx, dy)`` between two physical points (same units)."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    return float(math.hypot(dx, dy)), float(dx), float(dy)


def pixel_area(x_coords: FloatArray, y_coords: FloatArray) -> float:
    """Physical area of one pixel from the coordinate spacing (nm^2)."""
    dx = float(x_coords[1] - x_coords[0]) if x_coords.size > 1 else 1.0
    dy = float(y_coords[1] - y_coords[0]) if y_coords.size > 1 else 1.0
    return abs(dx * dy)


def sample_line(
    values: FloatArray,
    x_coords: FloatArray,
    y_coords: FloatArray,
    p0: tuple[float, float],
    p1: tuple[float, float],
    n: int | None = None,
) -> tuple[FloatArray, FloatArray]:
    """Bilinear-sample ``values`` along the segment ``p0`` -> ``p1`` (physical nm).

    Returns ``(positions_nm, samples)``: the distance along the line at each sample
    and the interpolated value there. ``n`` defaults to about one sample per pixel.
    """
    ny, nx = values.shape
    length = float(math.hypot(p1[0] - p0[0], p1[1] - p0[1]))
    if n is None:
        dx = abs(x_coords[1] - x_coords[0]) if x_coords.size > 1 else 1.0
        dy = abs(y_coords[1] - y_coords[0]) if y_coords.size > 1 else 1.0
        pix = max(abs(p1[0] - p0[0]) / dx, abs(p1[1] - p0[1]) / dy)
        n = max(math.ceil(pix) + 1, 2)
    t = np.linspace(0.0, 1.0, n)
    xs = p0[0] + t * (p1[0] - p0[0])
    ys = p0[1] + t * (p1[1] - p0[1])
    fx = np.interp(xs, x_coords, np.arange(nx, dtype=np.float64))
    fy = np.interp(ys, y_coords, np.arange(ny, dtype=np.float64))
    return t * length, _bilinear(values, fx, fy)


def rect_mask(
    x_coords: FloatArray,
    y_coords: FloatArray,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
) -> npt.NDArray[np.bool_]:
    """Boolean mask of pixels whose centers fall in the rectangle (physical coords)."""
    lo_x, hi_x = sorted((x0, x1))
    lo_y, hi_y = sorted((y0, y1))
    mx = (x_coords >= lo_x) & (x_coords <= hi_x)
    my = (y_coords >= lo_y) & (y_coords <= hi_y)
    return my[:, None] & mx[None, :]


def polygon_mask(
    x_coords: FloatArray,
    y_coords: FloatArray,
    vertices: list[tuple[float, float]],
) -> npt.NDArray[np.bool_]:
    """Boolean mask of pixel centers inside the polygon (even-odd ray casting)."""
    gx, gy = np.meshgrid(x_coords, y_coords)
    verts = np.asarray(vertices, dtype=np.float64)
    inside = np.zeros(gx.shape, dtype=bool)
    count = len(verts)
    j = count - 1
    for i in range(count):
        xi, yi = verts[i]
        xj, yj = verts[j]
        denom = yj - yi if yj != yi else 1e-30
        crosses = ((yi > gy) != (yj > gy)) & (gx < (xj - xi) * (gy - yi) / denom + xi)
        inside ^= crosses
        j = i
    return inside


def region_stats(
    values: FloatArray, mask: npt.NDArray[np.bool_], *, pixel_area_nm2: float
) -> RegionStats:
    """Statistics of ``values`` where ``mask`` is true (finite samples only)."""
    sel = values[mask & np.isfinite(values)]
    count = int(sel.size)
    if count == 0:
        nan = float("nan")
        return RegionStats(0, 0.0, nan, nan, nan, nan, nan)
    return RegionStats(
        count=count,
        area_nm2=count * pixel_area_nm2,
        mean=float(np.mean(sel)),
        median=float(np.median(sel)),
        minimum=float(np.min(sel)),
        maximum=float(np.max(sel)),
        std=float(np.std(sel)),
        rms=float(np.sqrt(np.mean(np.square(sel)))),
        p25=float(np.percentile(sel, 25)),
        p75=float(np.percentile(sel, 75)),
    )


@dataclass(frozen=True)
class Peak:
    """One detected peak in a line profile (a read-only observation)."""

    position_nm: float  # distance along the profile at the peak
    value: float  # the profile value at the peak (channel unit)
    prominence: float
    fwhm_nm: float | None  # full width at half-prominence, or None if unresolved


@dataclass(frozen=True)
class ProfileFeatures:
    """Quantitative features of a 1-D line profile (peaks + descriptive stats).

    A reusable, GUI-free analysis value object: the descriptive variability set
    (``count`` / ``mean`` / ``median`` / ``std`` / ``rms``), the profile geometry
    (``length_nm``), and the detected ``peaks`` with their mean spacing (the
    feature period - e.g. polariton-fringe spacing). Experiment-level workflows can
    consume this directly.
    """

    count: int
    mean: float
    median: float
    std: float
    rms: float
    minimum: float
    maximum: float
    length_nm: float
    peaks: tuple[Peak, ...]
    mean_spacing_nm: float | None  # mean peak-to-peak spacing, or None if < 2 peaks
    unit: str


@dataclass(frozen=True)
class RegionComparison:
    """A comparison of two regions: the difference/ratio plus the underlying stats.

    Exposes both the quantitative comparison (``difference`` = mean A - mean B,
    ``ratio`` = mean A / mean B) and the descriptive statistics that produced it
    (``stats_a`` / ``stats_b``), so the contrast number is always auditable.
    """

    label_a: str
    label_b: str
    stats_a: RegionStats
    stats_b: RegionStats
    difference: float
    ratio: float | None  # None when B's mean is zero / non-finite
    unit: str


def analyze_profile(
    positions_nm: FloatArray,
    values: FloatArray,
    *,
    unit: str = "",
    prominence: float | None = None,
) -> ProfileFeatures:
    """Detect peaks and summarize a sampled line profile (read-only).

    ``positions_nm`` is the monotonically increasing distance along the profile and
    ``values`` the sampled values (same length). Peaks are found with a prominence
    threshold (default 5% of the value range, so noise is ignored); each peak's full
    width at half-prominence is reported in nm. The descriptive statistics are taken
    over the finite samples. Non-finite samples are linearly interpolated for peak
    detection only (they do not bias the statistics).
    """
    positions = np.asarray(positions_nm, dtype=np.float64)
    raw = np.asarray(values, dtype=np.float64)
    finite_mask = np.isfinite(raw)
    finite = raw[finite_mask]
    length = float(positions[-1] - positions[0]) if positions.size > 1 else 0.0
    if finite.size == 0:
        nan = float("nan")
        return ProfileFeatures(0, nan, nan, nan, nan, nan, nan, length, (), None, unit)

    stats = (
        int(finite.size),
        float(np.mean(finite)),
        float(np.median(finite)),
        float(np.std(finite)),
        float(np.sqrt(np.mean(np.square(finite)))),
        float(np.min(finite)),
        float(np.max(finite)),
    )

    peaks = _detect_peaks(positions, raw, finite_mask, prominence)
    spacing = None
    if len(peaks) >= 2:
        centers = [p.position_nm for p in peaks]
        spacing = float(np.mean(np.diff(centers)))
    return ProfileFeatures(*stats, length, tuple(peaks), spacing, unit)


def compare_regions(
    a: RegionStats,
    b: RegionStats,
    *,
    label_a: str,
    label_b: str,
    unit: str = "",
) -> RegionComparison:
    """Compare two regions' means: the difference, the ratio, and both stat sets."""
    difference = float(a.mean - b.mean)
    ratio = float(a.mean / b.mean) if (b.mean != 0.0 and math.isfinite(b.mean)) else None
    return RegionComparison(label_a, label_b, a, b, difference, ratio, unit)


def _detect_peaks(
    positions: FloatArray,
    raw: FloatArray,
    finite_mask: npt.NDArray[np.bool_],
    prominence: float | None,
) -> list[Peak]:
    """Find prominent peaks; report each peak's value, prominence, and FWHM in nm."""
    if raw.size < 3:
        return []
    # Interpolate any non-finite samples (so a gap does not create a spurious edge).
    series = raw.copy()
    if not finite_mask.all():
        idx_all = np.arange(raw.size)
        series = np.interp(idx_all, idx_all[finite_mask], raw[finite_mask])
    finite = series[np.isfinite(series)]
    value_range = float(np.max(finite) - np.min(finite))
    prom = prominence
    if prom is None:
        prom = 0.05 * value_range if value_range > 0 else None
    if prom is None or prom <= 0:
        return []
    indices, props = find_peaks(series, prominence=prom)
    if indices.size == 0:
        return []
    spacing_nm = (
        float(positions[-1] - positions[0]) / (positions.size - 1) if positions.size > 1 else 1.0
    )
    widths_samples, _, _, _ = peak_widths(series, indices, rel_height=0.5)
    proms = props["prominences"]
    peaks: list[Peak] = []
    for k, sample in enumerate(indices):
        width_nm = float(widths_samples[k]) * spacing_nm
        peaks.append(
            Peak(
                position_nm=float(positions[sample]),
                value=float(series[sample]),
                prominence=float(proms[k]),
                fwhm_nm=width_nm if width_nm > 0 else None,
            )
        )
    return peaks


def _bilinear(values: FloatArray, fx: FloatArray, fy: FloatArray) -> FloatArray:
    """Bilinear interpolation of ``values`` at fractional indices (fx col, fy row)."""
    ny, nx = values.shape
    x0 = np.clip(np.floor(fx).astype(int), 0, nx - 1)
    y0 = np.clip(np.floor(fy).astype(int), 0, ny - 1)
    x1 = np.clip(x0 + 1, 0, nx - 1)
    y1 = np.clip(y0 + 1, 0, ny - 1)
    wx = np.clip(fx - x0, 0.0, 1.0)
    wy = np.clip(fy - y0, 0.0, 1.0)
    top = values[y0, x0] * (1 - wx) + values[y0, x1] * wx
    bottom = values[y1, x0] * (1 - wx) + values[y1, x1] * wx
    return np.asarray(top * (1 - wy) + bottom * wy, dtype=np.float64)


__all__ = [
    "Peak",
    "ProfileFeatures",
    "RegionComparison",
    "RegionStats",
    "analyze_profile",
    "compare_regions",
    "distance",
    "pixel_area",
    "polygon_mask",
    "rect_mask",
    "region_stats",
    "sample_line",
]
