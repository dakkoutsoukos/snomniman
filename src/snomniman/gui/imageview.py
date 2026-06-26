"""The channel image view: a quantitatively honest, physical-units display.

Consumes a :class:`~snomniman.viz.RenderData` and draws it so the researcher can
*trust the numbers*, not just see a picture: the image in physical nm coordinates
(ticks in um), lower-left origin, channel-aware colormap and scale bar.

In the default (full) mode it adds a **colorbar + histogram** (a PyQtGraph
``HistogramLUTItem``) with the channel unit, the value distribution and visible
clipping; **contrast controls** (default / full-range buttons + exact min/max
entry) that change only the *display*; and a **cursor readout** beneath the image.

In **compact** mode (used for the panes of a comparison) it drops the histogram,
contrast bar and readout strip and instead shows a pane title and a crosshair, so
several panes tile cleanly with a single shared readout. Either way it computes
nothing scientific (the colormap, ranges, units and extent come from
:mod:`snomniman.viz`) and never modifies the Dataset - contrast and crosshairs are
display-only.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import numpy.typing as npt
import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets

from snomniman.viz import RenderData, level_range, pick_scale_bar

from .colormap import lookup_table

_CROSSHAIR_PEN = pg.mkPen("#46c2ff", width=1, style=QtCore.Qt.PenStyle.DashLine)


class ChannelImageView(QtWidgets.QWidget):
    """A physical-units image; full mode adds colorbar/histogram/contrast/readout."""

    #: Emitted on hover: (x_nm, y_nm, in_bounds).
    cursorMoved = QtCore.Signal(float, float, bool)

    def __init__(self, *, compact: bool = False) -> None:
        super().__init__()
        self._compact = compact
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._layout_widget = pg.GraphicsLayoutWidget()
        layout.addWidget(self._layout_widget, 1)

        self._plot = self._layout_widget.addPlot(row=0, col=0)
        self._plot.setAspectLocked(True)
        for axis_name in ("bottom", "left"):  # data is nm; show ticks in um
            axis = self._plot.getAxis(axis_name)
            axis.setScale(1e-3)
            axis.enableAutoSIPrefix(False)
        self._plot.setLabel("bottom", "x", units="µm")
        self._plot.setLabel("left", "y", units="µm")

        self._image_item = pg.ImageItem()
        self._plot.addItem(self._image_item)

        self._vline = pg.InfiniteLine(angle=90, movable=False, pen=_CROSSHAIR_PEN)
        self._hline = pg.InfiniteLine(angle=0, movable=False, pen=_CROSSHAIR_PEN)
        for line in (self._vline, self._hline):
            line.setVisible(False)
            self._plot.addItem(line, ignoreBounds=True)

        self._hist: pg.HistogramLUTItem | None = None
        self._readout: pg.LabelItem | None = None
        if not compact:
            self._hist = pg.HistogramLUTItem(image=self._image_item)
            self._hist.axis.enableAutoSIPrefix(False)
            self._layout_widget.addItem(self._hist, row=0, col=1)
            self._readout = self._layout_widget.addLabel(
                "Hover over the image to read values", row=1, col=0, colspan=2, justify="left"
            )
            layout.addWidget(self._build_contrast_bar())
            self._hist.sigLevelsChanged.connect(self._on_hist_changed)

        self._scalebar: object | None = None
        self._extent: tuple[float, float, float, float] | None = None
        self._values: npt.NDArray[np.float64] = np.zeros((1, 1))
        self._default_levels: tuple[float, float] = (0.0, 1.0)
        self._last_readout = ""
        self._syncing = False

        self._plot.scene().sigMouseMoved.connect(self._on_mouse_moved)

    # -- public API -----------------------------------------------------------

    def show_render(self, render: RenderData) -> None:
        """Display ``render``; resets contrast to the channel-aware default."""
        x0, x1, y0, y1 = render.extent_nm
        self._image_item.setImage(render.values, autoLevels=False)
        self._image_item.setRect(QtCore.QRectF(x0, y0, x1 - x0, y1 - y0))
        lut = lookup_table(render.colormap)
        self._values = np.asarray(render.values, dtype=np.float64)
        self._default_levels = (render.vmin, render.vmax)

        if self._hist is not None:
            self._hist.gradient.setColorMap(pg.ColorMap(np.linspace(0.0, 1.0, len(lut)), lut))
            self._hist.axis.setLabel(render.unit or None)
            self._configure_spinboxes(render.vmin, render.vmax)
            self._apply_levels(render.vmin, render.vmax)
            self.set_readout("Hover over the image to read values")
        else:  # compact pane: apply colormap + levels directly to the image
            self._image_item.setLookupTable(lut)
            self._image_item.setLevels((render.vmin, render.vmax))

        if self._extent != render.extent_nm:  # new field of view -> frame it
            self._extent = render.extent_nm
            self._plot.getViewBox().setRange(xRange=(x0, x1), yRange=(y0, y1), padding=0.02)
            self._install_scale_bar(x1 - x0)

    def set_title(self, text: str) -> None:
        self._plot.setTitle(text)

    def set_readout(self, text: str) -> None:
        """Show ``text`` in the readout strip beneath the image (full mode only)."""
        self._last_readout = text
        if self._readout is not None:
            self._readout.setText(text)

    def set_crosshair(self, x_nm: float, y_nm: float, visible: bool) -> None:
        """Mark the physical point (x, y) - used to sync the cursor across panes."""
        self._vline.setPos(x_nm)
        self._hline.setPos(y_nm)
        self._vline.setVisible(visible)
        self._hline.setVisible(visible)

    def link_view(self, other: ChannelImageView) -> None:
        """Share zoom and pan with ``other`` (synchronized navigation)."""
        self._plot.setXLink(other._plot)
        self._plot.setYLink(other._plot)

    @property
    def view_box(self) -> Any:
        """The plot's ViewBox (physical nm coordinates) - for measurement overlays."""
        return self._plot.getViewBox()

    def add_overlay(self, item: object) -> None:
        """Add a measurement overlay item to the plot (does not touch the data)."""
        self._plot.addItem(item)

    def remove_overlay(self, item: object) -> None:
        self._plot.removeItem(item)

    @property
    def levels(self) -> tuple[float, float]:
        """Current display levels (min, max). Display only - never the data."""
        lv = self._image_item.levels
        return (float(lv[0]), float(lv[1])) if lv is not None else (0.0, 1.0)

    # -- contrast bar (full mode only) ----------------------------------------

    def _build_contrast_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout(bar)
        row.setContentsMargins(6, 2, 6, 2)
        row.addWidget(QtWidgets.QLabel("Contrast:"))

        default_btn = QtWidgets.QPushButton("Default")
        default_btn.setToolTip("Robust percentile range (the channel default)")
        default_btn.clicked.connect(self._reset_default)
        row.addWidget(default_btn)

        full_btn = QtWidgets.QPushButton("Full range")
        full_btn.setToolTip("Show the true min..max, including outliers")
        full_btn.clicked.connect(self._reset_full)
        row.addWidget(full_btn)

        row.addSpacing(12)
        row.addWidget(QtWidgets.QLabel("min"))
        self._min_spin = self._make_spinbox()
        self._min_spin.valueChanged.connect(self._on_spin_changed)
        row.addWidget(self._min_spin)
        row.addWidget(QtWidgets.QLabel("max"))
        self._max_spin = self._make_spinbox()
        self._max_spin.valueChanged.connect(self._on_spin_changed)
        row.addWidget(self._max_spin)
        row.addStretch(1)
        return bar

    @staticmethod
    def _make_spinbox() -> QtWidgets.QDoubleSpinBox:
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(-1e12, 1e12)
        spin.setKeyboardTracking(False)  # emit only when entry is committed
        spin.setMaximumWidth(110)
        return spin

    def _configure_spinboxes(self, lo: float, hi: float) -> None:
        span = hi - lo
        decimals = 4 if span < 10 else 3 if span < 100 else 2 if span < 1e4 else 0
        step = max(span / 100.0, 10.0**-decimals)
        self._syncing = True
        for spin in (self._min_spin, self._max_spin):
            spin.setDecimals(decimals)
            spin.setSingleStep(step)
        self._syncing = False

    def _apply_levels(self, lo: float, hi: float) -> None:
        assert self._hist is not None
        self._syncing = True
        self._hist.setLevels(lo, hi)
        self._min_spin.setValue(lo)
        self._max_spin.setValue(hi)
        self._syncing = False

    def _reset_default(self) -> None:
        self._apply_levels(*self._default_levels)

    def _reset_full(self) -> None:
        self._apply_levels(*level_range(self._values, "full"))

    def _on_spin_changed(self, _value: float) -> None:
        if self._syncing or self._hist is None:
            return
        lo, hi = self._min_spin.value(), self._max_spin.value()
        if hi > lo:
            self._syncing = True
            self._hist.setLevels(lo, hi)
            self._syncing = False

    def _on_hist_changed(self) -> None:
        if self._syncing or self._hist is None:
            return
        lo, hi = self._hist.getLevels()
        self._syncing = True
        self._min_spin.setValue(lo)
        self._max_spin.setValue(hi)
        self._syncing = False

    # -- scale bar + cursor ---------------------------------------------------

    def _install_scale_bar(self, span_nm: float) -> None:
        if self._scalebar is not None:
            return
        length, label = pick_scale_bar(span_nm)
        if length <= 0:
            return
        bar = pg.ScaleBar(size=length, suffix="m")
        bar.setParentItem(self._plot.getViewBox())
        bar.anchor((1, 1), (1, 1), offset=(-25, -25))
        if hasattr(bar, "text"):
            bar.text.setText(label)
        self._scalebar = bar

    def _on_mouse_moved(self, scene_pos: QtCore.QPointF) -> None:
        point = self._plot.getViewBox().mapSceneToView(scene_pos)
        in_bounds = self._extent is not None and (
            self._extent[0] <= point.x() <= self._extent[1]
            and self._extent[2] <= point.y() <= self._extent[3]
        )
        self.cursorMoved.emit(float(point.x()), float(point.y()), bool(in_bounds))


__all__ = ["ChannelImageView"]
