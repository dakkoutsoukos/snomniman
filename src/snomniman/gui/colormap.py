"""Resolve a matplotlib colormap name to a PyQtGraph lookup table (GUI helper).

:mod:`snomniman.viz` names a colormap (e.g. ``"viridis"``, cyclic ``"twilight"``
for phase) but stays free of any rendering toolkit. Turning that name into a
concrete LUT is a presentation concern, so it lives here. The result is a plain
numpy array, so this helper carries no Qt dependency and is unit-testable.
"""

from __future__ import annotations

import matplotlib as mpl
import numpy as np
import numpy.typing as npt


def lookup_table(name: str, n: int = 256) -> npt.NDArray[np.uint8]:
    """Return an ``(n, 4)`` RGBA uint8 LUT for the matplotlib colormap ``name``."""
    cmap = mpl.colormaps[name]
    samples = np.asarray(cmap(np.linspace(0.0, 1.0, n)), dtype=np.float64)
    return (samples * 255.0).astype(np.uint8)


__all__ = ["lookup_table"]
