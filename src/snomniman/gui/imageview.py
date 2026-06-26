"""The channel image view: an honest, physical-units PyQtGraph display.

Consumes a :class:`~snomniman.viz.RenderData` and draws it with the correct
lower-left orientation, physical nm axes (tick labels shown in um), the
recommended colormap and value range, and a physical scale bar. It computes
nothing scientific - every display decision was already made (and tested) in
:mod:`snomniman.viz`. It reports the cursor's physical position so the window can
show what exists under the pointer.

It wraps a PyQtGraph ``PlotWidget`` by composition (rather than subclassing it) so
the typed Qt surface stays clean.
"""

from __future__ import annotations

import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets

from snomniman.viz import RenderData, pick_scale_bar

from .colormap import lookup_table


class ChannelImageView(QtWidgets.QWidget):
    """A physical-units image display for one channel view; emits cursor moves."""

    #: Emitted on hover: (x_nm, y_nm, in_bounds).
    cursorMoved = QtCore.Signal(float, float, bool)

    def __init__(self) -> None:
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._plot = pg.PlotWidget()
        layout.addWidget(self._plot)

        self._plot.setAspectLocked(True)
        # Data, coords and hover are all in canonical nm (matching the model). Show
        # the *ticks* in um for readability by scaling tick text only; the scale bar
        # and cursor readout remain the authoritative physical references.
        for axis_name in ("bottom", "left"):
            axis = self._plot.getPlotItem().getAxis(axis_name)
            axis.setScale(1e-3)
            axis.enableAutoSIPrefix(False)
        self._plot.setLabel("bottom", "x", units="µm")
        self._plot.setLabel("left", "y", units="µm")

        self._image = pg.ImageItem()
        self._plot.addItem(self._image)
        self._scalebar: object | None = None
        self._extent: tuple[float, float, float, float] | None = None
        self._plot.scene().sigMouseMoved.connect(self._on_mouse_moved)

    def show_render(self, render: RenderData) -> None:
        """Display ``render``; preserves zoom/pan when the field extent is unchanged."""
        x0, x1, y0, y1 = render.extent_nm
        self._image.setImage(render.values, levels=(render.vmin, render.vmax), autoLevels=False)
        self._image.setRect(QtCore.QRectF(x0, y0, x1 - x0, y1 - y0))
        self._image.setLookupTable(lookup_table(render.colormap))

        if self._extent != render.extent_nm:  # new measurement/field -> frame it
            self._extent = render.extent_nm
            self._plot.getPlotItem().getViewBox().setRange(
                xRange=(x0, x1), yRange=(y0, y1), padding=0.02
            )
            self._install_scale_bar(x1 - x0)

    def _install_scale_bar(self, span_nm: float) -> None:
        if self._scalebar is not None:
            return
        length, label = pick_scale_bar(span_nm)
        if length <= 0:
            return
        bar = pg.ScaleBar(size=length, suffix="m")
        bar.setParentItem(self._plot.getPlotItem().getViewBox())
        bar.anchor((1, 1), (1, 1), offset=(-25, -25))
        if hasattr(bar, "text"):
            bar.text.setText(label)
        self._scalebar = bar

    def _on_mouse_moved(self, scene_pos: QtCore.QPointF) -> None:
        vb = self._plot.getPlotItem().getViewBox()
        point = vb.mapSceneToView(scene_pos)
        in_bounds = self._extent is not None and (
            self._extent[0] <= point.x() <= self._extent[1]
            and self._extent[2] <= point.y() <= self._extent[3]
        )
        self.cursorMoved.emit(float(point.x()), float(point.y()), bool(in_bounds))


__all__ = ["ChannelImageView"]
