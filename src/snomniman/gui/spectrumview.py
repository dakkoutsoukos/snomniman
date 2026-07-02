"""The spectrum plot view: the point-spectroscopy analogue of ``ChannelImageView``.

Pure presentation (Rule 4): it renders the :class:`~snomniman.gui.model.SpectrumCurve`
value object the backend already computed - a channel's amplitude/phase/value versus
wavenumber at one spatial position - and holds no scientific logic. Shown instead of
the 2-D image view whenever the active measurement has no spatial grid
(``ExplorerModel.is_spectral``, i.e. a ``SPECTRUM`` or a ``LINE_SCAN`` with a
wavenumber axis). Zoom/pan are pyqtgraph's native ``PlotWidget`` behavior; the
position slider (shown only when the dataset has more than one spatial position) is a
read-only index selection, not computation.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import numpy.typing as npt
import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets

from .model import SpectrumCurve

_MUTED = "color: #9aa0a6;"
_CURVE_PEN = pg.mkPen("#46c2ff", width=1.5)


class SpectrumPlotView(QtWidgets.QWidget):
    """A single spectrum curve, with an optional position selector and a value readout."""

    positionChanged = QtCore.Signal(int)

    def __init__(self) -> None:
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        self._position_row = QtWidgets.QWidget()
        pos_layout = QtWidgets.QHBoxLayout(self._position_row)
        pos_layout.setContentsMargins(0, 0, 0, 0)
        pos_layout.addWidget(QtWidgets.QLabel("Position:"))
        self._position_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self._position_slider.setMinimum(0)
        self._position_spin = QtWidgets.QSpinBox()
        self._position_spin.setMinimum(0)
        pos_layout.addWidget(self._position_slider, 1)
        pos_layout.addWidget(self._position_spin)
        layout.addWidget(self._position_row)
        self._position_row.setVisible(False)

        self._plot = pg.PlotWidget()
        self._plot.setLabel("bottom", "wavenumber", units="cm-1")
        self._plot.showGrid(x=True, y=True, alpha=0.2)
        self._curve_item = self._plot.plot([], [], pen=_CURVE_PEN)
        layout.addWidget(self._plot, 1)

        self._readout = QtWidgets.QLabel("")
        self._readout.setStyleSheet(_MUTED)
        self._readout.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self._readout)

        self._position_slider.valueChanged.connect(self._position_spin.setValue)
        self._position_spin.valueChanged.connect(self._position_slider.setValue)
        self._position_spin.valueChanged.connect(self.positionChanged.emit)

        self._wavenumber: npt.NDArray[np.float64] | None = None
        self._values: npt.NDArray[np.float64] | None = None
        self._proxy = pg.SignalProxy(
            self._plot.scene().sigMouseMoved, rateLimit=30, slot=self._on_mouse_moved
        )

    # -- position selector ------------------------------------------------------

    def set_position_range(self, count: int | None) -> None:
        """Show/hide + size the position selector; ``None``/``<=1`` hides it."""
        if count is None or count <= 1:
            self._position_row.setVisible(False)
            return
        self._position_row.setVisible(True)
        self._position_slider.setMaximum(count - 1)
        self._position_spin.setMaximum(count - 1)

    def position(self) -> int:
        return self._position_spin.value()

    # -- curve --------------------------------------------------------------

    def show_curve(self, curve: SpectrumCurve) -> None:
        self._wavenumber = curve.wavenumber_cm1
        self._values = curve.values
        self._curve_item.setData(curve.wavenumber_cm1, curve.values)
        self._plot.setLabel("left", curve.label, units=curve.unit or None)
        if curve.cyclic:
            self._plot.setYRange(-np.pi - 0.2, np.pi + 0.2)
        else:
            self._plot.enableAutoRange(axis="y")

    def set_readout(self, text: str) -> None:
        self._readout.setText(text)

    # -- cursor readout -------------------------------------------------------

    def _on_mouse_moved(self, evt: Any) -> None:
        if self._wavenumber is None or self._values is None or self._wavenumber.size == 0:
            return
        pos = evt[0]
        plot_item = self._plot.getPlotItem()
        if plot_item is None or not plot_item.vb.sceneBoundingRect().contains(pos):
            return
        point = plot_item.vb.mapSceneToView(pos)
        idx = int(np.argmin(np.abs(self._wavenumber - point.x())))
        wn = float(self._wavenumber[idx])
        val = float(self._values[idx])
        self.set_readout(f"wavenumber = {wn:.1f} cm^-1      value = {val:.4g}")


__all__ = ["SpectrumPlotView"]
