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

FloatArray = npt.NDArray[np.float64]


@dataclass(frozen=True)
class RegionStats:
    """Summary statistics of a region (all read-only observations)."""

    count: int
    area_nm2: float
    mean: float
    median: float
    minimum: float
    maximum: float
    std: float


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
    )


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
    "RegionStats",
    "distance",
    "pixel_area",
    "polygon_mask",
    "rect_mask",
    "region_stats",
    "sample_line",
]
