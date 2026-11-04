"""Threshold segmentation: label connected regions (particles/domains) in a channel.

``ThresholdSegment`` is the first step of Phase 7 - Automated Scientific Feature
Analysis (``docs/phase7-9-master-roadmap.md`` Section 3). It turns "I see particles"
into a reproducible count: threshold a real-valued channel (topography or an optical
amplitude/phase view) into foreground/background, then label each connected foreground
region with :func:`scipy.ndimage.label` - the same settled-engineering category as
``image.line_flatten`` (a decades-old, standard SPM/image-analysis operation, not a
scientific judgement requiring the Scientific Validation Phase).

Chosen approach (accepted, not invented here)
----------------------------------------------
- ``method="otsu"`` (default) - Otsu's (1979) threshold: the cut that maximizes
  between-class variance of the channel's histogram. The standard, parameter-free
  default for bimodal foreground/background separation (used by Gwyddion's own grain
  marking, the SPM-domain precedent).
- ``method="percentile"`` - the cut at a given percentile of the finite values.
  Useful when the foreground fraction is known approximately (e.g. "top 10%").
- ``method="fixed"`` - an explicit threshold value, when the researcher already knows
  the right physical cut (e.g. a known height datum).

``polarity`` selects whether the foreground is values ``>=`` threshold (``"above"``,
the default - e.g. particles taller than the background) or ``<=`` threshold
(``"below"`` - e.g. pits, or an inverted-contrast optical domain).

The output is a **new channel**, ``{channel}_labels``, appended alongside the
untouched original (never mutated) - not a new data type: it is an ordinary
real-valued channel, stored as ``float64`` with integer-valued contents (``0.0`` =
background, ``1.0..N.0`` = one id per surviving region, renumbered contiguously after
the ``min_pixels`` filter). This is a deliberate simplification (Section 3.4 of the
design doc): every other channel in this codebase is float/complex, so an integer
dtype's zarr/xarray round-trip is intentionally left unexercised rather than adding a
new persisted dtype convention for a first milestone - float64 exactly represents small
non-negative integers, so nothing is lost.

Watershed splitting of touching/overlapping particles is deliberately **not**
implemented (it needs ``scikit-image``, a new major dependency requiring its own ADR -
see the design doc Section 3.3); connected-components under-counts touching particles,
a documented, honest limitation.

Scientific validation: a synthetic image with N well-separated, known-size blobs
recovers exactly N labeled regions of the expected pixel count (every method); a
sub-``min_pixels`` speck is correctly dropped (see
``tests/test_processing_image_threshold_segment.py``).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

import numpy as np
import numpy.typing as npt
import xarray as xr
from scipy import ndimage

from snomniman.core import Capability, ChannelInfo, DataKind, Dataset, Metadata
from snomniman.core.exceptions import ProcessingError
from snomniman.processing.registry import register
from snomniman.processing.step import CHANNEL_REAL, ParameterSpec, ProcessingStep

#: Accepted threshold-selection methods.
METHODS: tuple[str, ...] = ("otsu", "percentile", "fixed")
#: Accepted foreground polarities.
POLARITIES: tuple[str, ...] = ("above", "below")


def otsu_threshold(values: npt.NDArray[np.float64], *, bins: int = 256) -> float:
    """Otsu's (1979) threshold: the histogram cut maximizing between-class variance.

    Closed-form, deterministic, parameter-free beyond the bin count. Non-finite values
    are ignored. Raises :exc:`ProcessingError` if there are no finite values; returns
    the (degenerate) single value if the channel is constant.
    """
    finite = np.asarray(values, dtype=np.float64).ravel()
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        raise ProcessingError("threshold_segment: no finite values to threshold")
    vmin, vmax = float(finite.min()), float(finite.max())
    if vmin == vmax:
        return vmin

    hist, edges = np.histogram(finite, bins=bins, range=(vmin, vmax))
    hist = hist.astype(np.float64)
    centers = 0.5 * (edges[:-1] + edges[1:])

    weight1 = np.cumsum(hist)
    total_weight = weight1[-1]
    weight2 = total_weight - weight1

    cum_intensity = np.cumsum(hist * centers)
    total_intensity = cum_intensity[-1]

    mean1 = np.divide(cum_intensity, weight1, out=np.zeros_like(cum_intensity), where=weight1 > 0)
    mean2 = np.divide(
        total_intensity - cum_intensity,
        weight2,
        out=np.zeros_like(cum_intensity),
        where=weight2 > 0,
    )
    between_class_variance = weight1 * weight2 * (mean1 - mean2) ** 2
    # The best cut is the bin *edge* above the chosen bin (values >= this edge are
    # foreground under "above" polarity), not the bin center - Otsu's own convention.
    idx = int(np.argmax(between_class_variance))
    return float(edges[idx + 1])


def segment_labels(
    values: npt.NDArray[np.float64],
    *,
    method: str = "otsu",
    threshold: float | None = None,
    percentile: float = 50.0,
    polarity: str = "above",
    min_pixels: int = 2,
) -> npt.NDArray[np.float64]:
    """Threshold a 2-D array and label its connected foreground regions.

    Returns a same-shape ``float64`` array: ``0.0`` for background, ``1.0..N.0`` for
    each connected region with at least ``min_pixels`` pixels (renumbered
    contiguously - a region dropped by the size filter never leaves a gap in the id
    sequence). Non-finite input pixels are always background. The input array is
    never modified.
    """
    if method not in METHODS:
        raise ProcessingError(
            f"threshold_segment: method must be one of {list(METHODS)}, got {method!r}"
        )
    if polarity not in POLARITIES:
        raise ProcessingError(
            f"threshold_segment: polarity must be one of {list(POLARITIES)}, got {polarity!r}"
        )
    if min_pixels < 1:
        raise ProcessingError("threshold_segment: min_pixels must be >= 1")

    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim != 2:
        raise ProcessingError(f"threshold_segment: expected a 2-D array, got shape {arr.shape}")

    if method == "fixed":
        if threshold is None:
            raise ProcessingError("threshold_segment: method='fixed' requires 'threshold'")
        cut = float(threshold)
    elif method == "percentile":
        finite = arr[np.isfinite(arr)]
        if finite.size == 0:
            raise ProcessingError("threshold_segment: no finite values to threshold")
        if not 0.0 <= percentile <= 100.0:
            raise ProcessingError("threshold_segment: percentile must be in [0, 100]")
        cut = float(np.percentile(finite, percentile))
    else:  # otsu
        cut = otsu_threshold(arr)

    finite_mask = np.isfinite(arr)
    if polarity == "above":
        foreground = finite_mask & (arr >= cut)
    else:
        foreground = finite_mask & (arr <= cut)

    raw_labels, n_regions = ndimage.label(foreground)
    out = np.zeros(arr.shape, dtype=np.float64)
    next_id = 1.0
    for region_id in range(1, n_regions + 1):
        region_mask = raw_labels == region_id
        if int(region_mask.sum()) < min_pixels:
            continue
        out[region_mask] = next_id
        next_id += 1.0
    return out


@register
class ThresholdSegment(ProcessingStep):
    """Threshold a channel and label its connected foreground regions.

    Appends a new ``{channel}_labels`` channel (``0`` = background, ``1..N`` = one id
    per surviving connected region); every other channel, including the input, is
    preserved unchanged and the input Dataset is never modified. See the module
    docstring for the segmentation methods and their rationale.
    """

    step_id = "image.threshold_segment"
    version = 1
    description = "Threshold a channel and label connected foreground regions (particles/domains)."
    deterministic = True
    required_capabilities = (Capability.SPATIAL_2D,)

    @classmethod
    def param_specs(cls) -> list[ParameterSpec]:
        return [
            ParameterSpec(
                "channel",
                "Real-valued channel to threshold (e.g. 'Z' or an amplitude view).",
                (str,),
                required=False,
                default="Z",
                channel_role=CHANNEL_REAL,
            ),
            ParameterSpec(
                "method",
                "Threshold selection: 'otsu' (parameter-free default), 'percentile', or 'fixed'.",
                (str,),
                required=False,
                default="otsu",
                choices=METHODS,
            ),
            ParameterSpec(
                "threshold",
                "Explicit threshold value (used only when method='fixed').",
                (int, float),
                required=False,
                default=0.0,
            ),
            ParameterSpec(
                "percentile",
                "Percentile cut, 0-100 (used only when method='percentile').",
                (int, float),
                required=False,
                default=50.0,
            ),
            ParameterSpec(
                "polarity",
                "'above' keeps values >= threshold as foreground (e.g. particles); "
                "'below' keeps values <= threshold (e.g. pits).",
                (str,),
                required=False,
                default="above",
                choices=POLARITIES,
            ),
            ParameterSpec(
                "min_pixels",
                "Minimum connected-region size (pixels) to keep; smaller specks are dropped.",
                (int,),
                required=False,
                default=2,
            ),
        ]

    def _execute(
        self, inputs: Mapping[str, Dataset]
    ) -> tuple[xr.Dataset, DataKind, Metadata]:
        primary = inputs["primary"]
        channel: str = self._params["channel"]

        if channel not in primary.channel_names:
            raise ProcessingError(
                f"{self.step_id}: channel {channel!r} not found; "
                f"available: {primary.channel_names}"
            )
        if primary.is_complex(channel):
            raise ProcessingError(
                f"{self.step_id}: channel {channel!r} is complex; "
                "threshold segmentation requires a real-valued channel"
            )

        label_name = f"{channel}_labels"
        if label_name in primary.channel_names:
            raise ProcessingError(
                f"{self.step_id}: channel {label_name!r} already exists on this measurement"
            )

        raw = primary.data
        source = raw[channel]
        values = np.asarray(source.values, dtype=np.float64)
        labels = segment_labels(
            values,
            method=self._params["method"],
            threshold=self._params["threshold"],
            percentile=self._params["percentile"],
            polarity=self._params["polarity"],
            min_pixels=self._params["min_pixels"],
        )

        new_vars: dict[str, xr.DataArray] = {
            str(name): xr.DataArray(
                np.array(var.values, copy=True),
                coords=var.coords,
                dims=var.dims,
                attrs=dict(var.attrs),
            )
            for name, var in raw.data_vars.items()
        }
        new_vars[label_name] = xr.DataArray(
            labels,
            coords=source.coords,
            dims=source.dims,
            attrs={"derived_from": channel, "quantity": "region_label"},
        )
        new_data = xr.Dataset(new_vars, coords=raw.coords, attrs=dict(raw.attrs))

        new_info = ChannelInfo(
            canonical=label_name,
            kind="label",
            role="signal",
            dtype="float64",
            state="derived",
            value_unit=None,
        )
        new_metadata = replace(
            primary.metadata, channels=(*primary.metadata.channels, new_info)
        )
        return new_data, primary.kind, new_metadata


__all__ = ["METHODS", "POLARITIES", "ThresholdSegment", "otsu_threshold", "segment_labels"]
