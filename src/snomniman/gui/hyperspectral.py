"""The hyperspectral workspace: a band-map image linked to a per-pixel/ROI spectrum.

Composes two existing, unmodified widgets - :class:`~snomniman.gui.imageview.
ChannelImageView` (the band map) and :class:`~snomniman.gui.spectrumview.
SpectrumPlotView` (the linked spectrum) - side by side in a splitter, plus a
wavenumber slider. Pure presentation (Rule 4): it holds no scientific logic and
no :class:`~snomniman.gui.model.ExplorerModel` reference - the window wires its
signals to model calls and pushes results back in, exactly like every other
stack page (``ChannelImageView``, ``SpectrumPlotView`` themselves).

This is the one genuinely new GUI surface Phase 5B needs (docs/
phase5-spectral-nanoftir.md sec 3.3): no existing widget shows an image and a
curve side by side, linked by pixel selection.
"""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from .imageview import ChannelImageView
from .spectrumview import SpectrumPlotView


class HyperspectralView(QtWidgets.QWidget):
    """A band-map image (left) linked to a spectrum plot (right)."""

    #: Emitted when the wavenumber slider/spinbox changes (the new band index).
    wavenumberChanged = QtCore.Signal(int)
    #: Emitted on a click on the band map, in physical (x_nm, y_nm) - mirrors
    #: ChannelImageView.cursorMoved's contract; the window resolves this to a
    #: pixel index via ExplorerModel.nearest_pixel (no indexing logic here).
    pixelClicked = QtCore.Signal(float, float)

    def __init__(self) -> None:
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        wn_row = QtWidgets.QWidget()
        wn_layout = QtWidgets.QHBoxLayout(wn_row)
        wn_layout.setContentsMargins(0, 0, 0, 0)
        wn_layout.addWidget(QtWidgets.QLabel("Wavenumber:"))
        self._wavenumber_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self._wavenumber_slider.setMinimum(0)
        self._wavenumber_spin = QtWidgets.QSpinBox()
        self._wavenumber_spin.setMinimum(0)
        wn_layout.addWidget(self._wavenumber_slider, 1)
        wn_layout.addWidget(self._wavenumber_spin)
        self._wavenumber_readout = QtWidgets.QLabel("")
        wn_layout.addWidget(self._wavenumber_readout)
        layout.addWidget(wn_row)

        self._wavenumber_slider.valueChanged.connect(self._wavenumber_spin.setValue)
        self._wavenumber_spin.valueChanged.connect(self._wavenumber_slider.setValue)
        self._wavenumber_spin.valueChanged.connect(self.wavenumberChanged.emit)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.band_view = ChannelImageView()
        self.spectrum_view = SpectrumPlotView()
        splitter.addWidget(self.band_view)
        splitter.addWidget(self.spectrum_view)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

        self.band_view.view_box.scene().sigMouseClicked.connect(self._on_band_clicked)

    # -- wavenumber control -----------------------------------------------------

    def set_wavenumber_range(self, count: int) -> None:
        """Size the wavenumber slider/spinbox to ``count`` bands (>= 1)."""
        maximum = max(0, count - 1)
        self._wavenumber_slider.setMaximum(maximum)
        self._wavenumber_spin.setMaximum(maximum)

    def wavenumber_index(self) -> int:
        return self._wavenumber_spin.value()

    def set_wavenumber_index(self, index: int) -> None:
        """Set the slider/spinbox without re-emitting (for restoring saved state)."""
        self._wavenumber_spin.blockSignals(True)
        self._wavenumber_slider.blockSignals(True)
        self._wavenumber_spin.setValue(index)
        self._wavenumber_slider.setValue(index)
        self._wavenumber_spin.blockSignals(False)
        self._wavenumber_slider.blockSignals(False)

    def set_wavenumber_readout(self, text: str) -> None:
        self._wavenumber_readout.setText(text)

    # -- click-to-pin -------------------------------------------------------

    def _on_band_clicked(self, event: object) -> None:
        pos = getattr(event, "scenePos", None)
        if pos is None:
            return
        point = self.band_view.view_box.mapSceneToView(pos())
        self.pixelClicked.emit(float(point.x()), float(point.y()))


__all__ = ["HyperspectralView"]
