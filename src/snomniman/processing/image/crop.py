"""Spatial cropping - a derived Dataset restricted to a rectangular region.

``Crop`` selects the pixels whose physical coordinates fall within
``[x_min, x_max] x [y_min, y_max]`` (canonical nm) and returns a new Dataset with
every channel cropped, the coordinate system preserved (just sliced), and the scan
geometry updated to match (pixels, size, offset). Conventions and provenance are
preserved; the input Dataset is never modified.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

import numpy as np
import xarray as xr

from snomniman.core import Capability, DataKind, Dataset, Metadata
from snomniman.core.exceptions import ProcessingError
from snomniman.processing.registry import register
from snomniman.processing.step import ParameterSpec, ProcessingStep


@register
class Crop(ProcessingStep):
    """Crop every channel to a rectangular region given in nm.

    Bounds are inclusive and expressed in canonical nm (lower-left origin). The
    coordinate axes are sliced (not re-based), so absolute positions are preserved.
    """

    step_id = "image.crop"
    version = 1
    description = "Crop the measurement to a rectangular region (nm)."
    deterministic = True
    required_capabilities = (Capability.SPATIAL_2D,)

    @classmethod
    def param_specs(cls) -> list[ParameterSpec]:
        return [
            ParameterSpec("x_min", "Left bound (nm).", (int, float), required=True),
            ParameterSpec("x_max", "Right bound (nm).", (int, float), required=True),
            ParameterSpec("y_min", "Bottom bound (nm).", (int, float), required=True),
            ParameterSpec("y_max", "Top bound (nm).", (int, float), required=True),
        ]

    @classmethod
    def validate(cls, params: Mapping[str, object]) -> dict[str, object]:
        out = super().validate(params)
        if out["x_min"] >= out["x_max"]:
            raise ProcessingError(f"{cls.step_id}: x_min must be < x_max")
        if out["y_min"] >= out["y_max"]:
            raise ProcessingError(f"{cls.step_id}: y_min must be < y_max")
        return out

    def _execute(
        self, inputs: Mapping[str, Dataset]
    ) -> tuple[xr.Dataset, DataKind, Metadata]:
        primary = inputs["primary"]
        x = np.asarray(primary.coordinate("x").values, dtype=np.float64)
        y = np.asarray(primary.coordinate("y").values, dtype=np.float64)

        x_min, x_max = float(self._params["x_min"]), float(self._params["x_max"])
        y_min, y_max = float(self._params["y_min"]), float(self._params["y_max"])
        xs = np.flatnonzero((x >= x_min) & (x <= x_max))
        ys = np.flatnonzero((y >= y_min) & (y <= y_max))
        if xs.size == 0 or ys.size == 0:
            raise ProcessingError(
                f"{self.step_id}: crop region selects no pixels; "
                f"x in [{x.min()}, {x.max()}], y in [{y.min()}, {y.max()}]"
            )

        new_data = primary.data.isel(
            x=slice(int(xs[0]), int(xs[-1]) + 1),
            y=slice(int(ys[0]), int(ys[-1]) + 1),
        ).copy(deep=True)

        new_metadata = self._cropped_metadata(primary.metadata, new_data)
        return new_data, primary.kind, new_metadata

    @staticmethod
    def _cropped_metadata(metadata: Metadata, cropped: xr.Dataset) -> Metadata:
        scan = metadata.scan
        nx = int(cropped.sizes["x"])
        ny = int(cropped.sizes["y"])
        px, py = (scan.pixel_size_nm or (0.0, 0.0))
        cx = np.asarray(cropped.coords["x"].values, dtype=np.float64)
        cy = np.asarray(cropped.coords["y"].values, dtype=np.float64)
        new_scan = replace(
            scan,
            pixels=(nx, ny),
            size_nm=(nx * px, ny * py),
            offset_nm=(float(cx[0]) - px / 2, float(cy[0]) - py / 2),
            center_nm=(float(cx.mean()), float(cy.mean())),
        )
        return replace(metadata, scan=new_scan)


__all__ = ["Crop"]
