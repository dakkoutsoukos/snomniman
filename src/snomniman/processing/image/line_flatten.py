"""Line-by-line flattening (row alignment) for real-valued image channels.

``LineFlatten`` removes the per-scan-line baseline that real raster topography
carries: each scan line is acquired sequentially, so thermal drift, feedback
settling, and tip changes give successive lines slightly different offsets (and
sometimes a per-line slope/bow). The result is the familiar horizontal
"striping" that a single global surface fit (``image.plane_level``) cannot
remove, because the offsets are independent between lines rather than a smooth
function of position.

Chosen approach (accepted SPM/AFM methodology, not invented here)
----------------------------------------------------------------
For each scan line (a row of constant ``y``, varying along the fast axis ``x``)
the operation estimates a baseline and subtracts it:

- ``method="median"`` (default) - subtract the line's **median**. This is the
  standard, robust row-alignment method: the median is insensitive to a few
  bright/dark feature pixels, so genuine features in a line do not drag its
  correction. This is the default "Align Rows" method in Gwyddion.
- ``method="mean"`` - subtract the line's **mean** (a degree-0 fit). Simpler but
  not robust: a strong feature shifts the whole line's correction.
- ``method="polynomial"`` - subtract a least-squares **polynomial of order
  ``order``** fitted along the line, removing a per-line offset *and* slope (and,
  at higher orders, gentle per-line bow).

Why this and not alternatives. Median/mean/low-order-polynomial row leveling is
the established, deterministic SPM baseline-removal family (Necas & Klapetek,
Gwyddion; Horcas et al., WSxM). Median is chosen as the default because it is the
most robust to real features and is the de-facto standard; the mean and
polynomial variants cover the remaining accepted cases. We deliberately do *not*
invent a feature-masking or "median of differences" matcher (Rule 2/Rule 7): the
robust median already handles the dominant case, and a more elaborate matcher is
added only if a real workflow needs it.

Relationship to ``image.plane_level``. Plane leveling fits **one global surface**
(a plane/paraboloid/cubic) to the whole channel - it removes sample tilt and
broad bow but cannot touch line-to-line offsets. Line flattening removes
**independent per-line** baselines but cannot represent a smooth 2-D background.
They are complementary, distinct verbs (this is why ``line_flatten`` is its own
operation, not a parameterisation of ``plane_level``); a common workflow is to
line-flatten first, then plane-level (or vice versa).

Assumptions / limitations. The fast scan axis is taken to be ``x`` (horizontal
scan lines); this matches the neaSNOM raster. Non-finite (NaN/inf) pixels are
ignored when estimating a line's baseline; an all-invalid line is left unchanged.
Aggressive use can introduce faint vertical banding where a real feature spans
many lines (the classic row-flattening trade-off) - hence the robust median
default and an explicit, previewed, recorded derivation.

Scientific validation: tested against analytically-known synthetic surfaces -
pure per-line offsets are removed to machine precision (every method), per-line
offset+slope is removed exactly (polynomial order 1), and a feature with a known
per-line baseline is recovered (see ``tests/test_processing_image_line_flatten.py``).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import numpy.typing as npt
import xarray as xr

from snomniman.core import Capability, DataKind, Dataset, Metadata
from snomniman.core.exceptions import ProcessingError
from snomniman.processing.registry import register
from snomniman.processing.step import CHANNEL_REAL, ParameterSpec, ProcessingStep

#: Accepted baseline-estimation methods (declared as ``choices`` for the UI too).
METHODS: tuple[str, ...] = ("median", "mean", "polynomial")


def flatten_lines(
    values: npt.NDArray[np.float64],
    method: str = "median",
    order: int = 1,
) -> npt.NDArray[np.float64]:
    """Subtract a per-scan-line baseline from a 2-D array; return the flattened copy.

    Lines are the rows of ``values`` (shape ``(ny, nx)``); the baseline is
    estimated along the last axis (the fast scan axis ``x``). ``method`` selects
    ``"median"`` / ``"mean"`` (a per-line constant) or ``"polynomial"`` (a
    per-line least-squares polynomial of degree ``order``). Non-finite pixels are
    ignored when estimating each line's baseline; a line with no finite pixels is
    left unchanged. The input array is never modified.
    """
    if method not in METHODS:
        raise ProcessingError(
            f"line_flatten: method must be one of {list(METHODS)}, got {method!r}"
        )
    out = np.array(values, dtype=np.float64, copy=True)
    if out.ndim != 2:
        raise ProcessingError(
            f"line_flatten: expected a 2-D array, got shape {out.shape}"
        )
    nx = out.shape[1]
    # Centred column index for a well-conditioned polynomial basis. For uniform
    # pixel spacing (the raster case) the subtracted fit is invariant to this
    # affine reparameterisation, so using the pixel index is exact and stable.
    t = np.arange(nx, dtype=np.float64)
    t -= t.mean()

    for i, row in enumerate(out):
        finite = np.isfinite(row)
        n = int(finite.sum())
        if n == 0:
            continue  # all-invalid line: nothing to estimate, leave unchanged
        if method == "median":
            out[i] = row - float(np.median(row[finite]))
        elif method == "mean":
            out[i] = row - float(np.mean(row[finite]))
        else:  # polynomial
            deg = min(order, n - 1)
            if deg < 1:
                # too few finite points for a slope -> fall back to a constant
                out[i] = row - float(np.mean(row[finite]))
                continue
            coeffs = np.polyfit(t[finite], row[finite], deg)
            out[i] = row - np.polyval(coeffs, t)
    return out


@register
class LineFlatten(ProcessingStep):
    """Subtract a per-scan-line baseline from a real-valued channel.

    For each horizontal scan line the operation removes a baseline estimated by
    ``method`` (``"median"`` default, ``"mean"``, or ``"polynomial"`` of
    ``order``), removing line-to-line offsets (and, for the polynomial method,
    per-line slope/bow). All other channels are preserved unchanged and the input
    Dataset is never modified.

    Distinct from ``image.plane_level`` (which fits one global surface): use line
    flattening to remove scan-line striping, plane leveling to remove global tilt.
    """

    step_id = "image.line_flatten"
    version = 1
    description = "Subtract a per-scan-line baseline (median/mean/polynomial) from a channel."
    deterministic = True
    required_capabilities = (Capability.SPATIAL_2D,)

    @classmethod
    def param_specs(cls) -> list[ParameterSpec]:
        return [
            ParameterSpec(
                "channel",
                "Real-valued channel to flatten (e.g. 'Z').",
                (str,),
                required=False,
                default="Z",
                channel_role=CHANNEL_REAL,
            ),
            ParameterSpec(
                "method",
                "Per-line baseline: 'median' (robust default), 'mean', or 'polynomial'.",
                (str,),
                required=False,
                default="median",
                choices=METHODS,
            ),
            ParameterSpec(
                "order",
                "Polynomial order (used only when method='polynomial').",
                (int,),
                required=False,
                default=1,
                choices=(1, 2, 3),
            ),
        ]

    def _execute(
        self, inputs: Mapping[str, Dataset]
    ) -> tuple[xr.Dataset, DataKind, Metadata]:
        primary = inputs["primary"]
        channel: str = self._params["channel"]
        method: str = self._params["method"]
        order: int = self._params["order"]

        if channel not in primary.channel_names:
            raise ProcessingError(
                f"{self.step_id}: channel {channel!r} not found; "
                f"available: {primary.channel_names}"
            )
        if primary.is_complex(channel):
            raise ProcessingError(
                f"{self.step_id}: channel {channel!r} is complex; "
                "line flattening requires a real-valued channel"
            )

        raw = primary.data
        values = np.asarray(raw[channel].values, dtype=np.float64)
        flattened = flatten_lines(values, method=method, order=order)

        new_vars: dict[str, xr.DataArray] = {}
        for raw_name, var in raw.data_vars.items():
            name = str(raw_name)
            if name == channel:
                arr: npt.NDArray[Any] = flattened.astype(var.dtype)
            else:
                arr = np.array(var.values, copy=True)
            new_vars[name] = xr.DataArray(
                arr, coords=var.coords, dims=var.dims, attrs=dict(var.attrs)
            )
        new_data = xr.Dataset(new_vars, coords=raw.coords, attrs=dict(raw.attrs))
        return new_data, primary.kind, primary.metadata


__all__ = ["LineFlatten", "flatten_lines"]
