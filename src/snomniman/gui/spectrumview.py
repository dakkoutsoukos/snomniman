"""The spectrum plot view: the point-spectroscopy analogue of ``ChannelImageView``.

Pure presentation (Rule 4): it renders the :class:`~snomniman.gui.model.SpectrumCurve`
value object the backend already computed - a channel's amplitude/phase/value versus
wavenumber at one spatial position - and holds no scientific logic. Shown instead of
the 2-D image view whenever the active measurement has no spatial grid
(``ExplorerModel.is_spectral``, i.e. a ``SPECTRUM`` or a ``LINE_SCAN`` with a
wavenumber axis). Zoom/pan are pyqtgraph's native ``PlotWidget`` behavior; the
position slider (shown only when the dataset has more than one spatial position) is a
read-only index selection, not computation.

Also renders the Phase 6 lineshape-fitting interaction
(docs/phase6-spectral-lineshape-analysis.md sec 3.3-3.4): a draggable fit-window
region on the curve and the resulting :class:`~snomniman.viz.LineshapeFit` overlay
(fit curve + residual + a text summary). The widget only draws what it is given -
``fitRequested`` asks the window (which owns the model) to compute the fit via
``ExplorerModel.fit_spectrum_lineshape``; nothing here calls ``viz`` or fits
anything itself, the same "widget renders, window computes" split every other
measurement in this GUI already follows.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import numpy.typing as npt
import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets

from snomniman.viz import LineshapeFit

from .model import SpectrumCurve

_MUTED = "color: #9aa0a6;"
_CURVE_PEN = pg.mkPen("#46c2ff", width=1.5)
_FIT_PEN = pg.mkPen("#ff5c5c", width=2)
_FIT_REGION_BRUSH = pg.mkBrush(255, 92, 92, 40)

#: Overlay colors for show_curves - matches gui/measurement.py's _CURVE_COLORS
#: convention exactly, so a curve keeps the same color whether it is measured or
#: previewed/overlaid here.
_OVERLAY_COLORS = ("#46c2ff", "#ffb454", "#7ee787", "#ff7b72", "#d2a8ff", "#79c0ff")


class _WavelengthAxis(pg.AxisItem):  # type: ignore[misc]  # pyqtgraph is untyped
    """The wavenumber axis's tick positions, re-labeled as their wavelength equivalent.

    Wavelength [um] = 1e4 / wavenumber [cm^-1] is monotonic but not linear, so a
    plain linked twin axis (which assumes an affine relationship) cannot show it;
    this axis instead shares the wavenumber axis's ViewBox (so its ticks land at
    the *same pixel positions*) and only overrides the tick *label text* - the
    same dual-axis technique the source figure this feature was built from uses.
    """

    def tickStrings(
        self, values: Sequence[float], scale: float, spacing: float
    ) -> list[str]:
        return [f"{1e4 / v:.2f}" if v > 0 else "" for v in values]


class SpectrumPlotView(QtWidgets.QWidget):
    """A single spectrum curve, with an optional position selector and a value readout."""

    positionChanged = QtCore.Signal(int)
    fitRequested = QtCore.Signal(float, float)  # (window_low_cm1, window_high_cm1)

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

        self._plot = pg.PlotWidget(axisItems={"top": _WavelengthAxis(orientation="top")})
        self._plot.setLabel("bottom", "wavenumber", units="cm-1")
        self._plot.showAxis("top")
        self._plot.getAxis("top").setLabel("wavelength", units="µm")
        self._plot.showGrid(x=True, y=True, alpha=0.2)
        self._curve_item = self._plot.plot([], [], pen=_CURVE_PEN)
        layout.addWidget(self._plot, 1)

        self._readout = QtWidgets.QLabel("")
        self._readout.setStyleSheet(_MUTED)
        self._readout.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self._readout)

        fit_row = QtWidgets.QHBoxLayout()
        self._fit_checkbox = QtWidgets.QCheckBox("Fit window")
        self._fit_checkbox.setToolTip(
            "Show a draggable wavenumber window, then Fit Lorentzian to fit a "
            "Lorentzian + linear baseline within it"
        )
        self._fit_checkbox.toggled.connect(self._on_fit_toggled)
        self._fit_btn = QtWidgets.QPushButton("Fit Lorentzian")
        self._fit_btn.setToolTip(
            "Fit a Lorentzian + linear baseline to the current curve within the window"
        )
        self._fit_btn.clicked.connect(self._on_fit_clicked)
        self._fit_btn.setVisible(False)
        fit_row.addWidget(self._fit_checkbox)
        fit_row.addWidget(self._fit_btn)
        fit_row.addStretch(1)
        layout.addLayout(fit_row)

        self._fit_readout = QtWidgets.QLabel("")
        self._fit_readout.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self._fit_readout.setWordWrap(True)
        self._fit_readout.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self._fit_readout)

        self._residual_plot = pg.PlotWidget()
        self._residual_plot.setLabel("bottom", "wavenumber", units="cm-1")
        self._residual_plot.setLabel("left", "residual")
        self._residual_plot.showGrid(x=True, y=True, alpha=0.2)
        self._residual_plot.setMaximumHeight(140)
        self._residual_curve = self._residual_plot.plot([], [], pen=_FIT_PEN)
        self._residual_plot.setVisible(False)
        layout.addWidget(self._residual_plot)

        self._position_slider.valueChanged.connect(self._position_spin.setValue)
        self._position_spin.valueChanged.connect(self._position_slider.setValue)
        self._position_spin.valueChanged.connect(self.positionChanged.emit)

        self._wavenumber: npt.NDArray[np.float64] | None = None
        self._values: npt.NDArray[np.float64] | None = None
        self._overlay_items: list[Any] = []
        self._legend: Any = None
        self._fit_region: Any = None
        self._fit_curve_item: Any = None
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
        self._clear_overlays()
        self._wavenumber = curve.wavenumber_cm1
        self._values = curve.values
        self._curve_item.setData(curve.wavenumber_cm1, curve.values)
        self._plot.setLabel("left", curve.label, units=curve.unit or None)
        self._set_y_range(curve.cyclic)

    def show_curves(self, curves: Mapping[str, SpectrumCurve]) -> None:
        """Overlay multiple labelled curves (ROI/spectral-preview comparison).

        Additive to :meth:`show_curve` (unchanged, still used by the single-curve
        point-spectroscopy path): replaces whatever was shown before, one colored,
        legended curve per entry. The cursor readout continues reporting the first
        (primary) curve only - no per-curve tooltip, nothing in the task asks for
        one.
        """
        self._clear_overlays()
        self._curve_item.setData([], [])
        if not curves:
            return
        if self._legend is None:
            self._legend = self._plot.addLegend()
        first: SpectrumCurve | None = None
        for i, (label, curve) in enumerate(curves.items()):
            if first is None:
                first = curve
            pen = pg.mkPen(_OVERLAY_COLORS[i % len(_OVERLAY_COLORS)], width=1.5)
            item = self._plot.plot(curve.wavenumber_cm1, curve.values, pen=pen, name=label)
            self._overlay_items.append(item)
        assert first is not None
        self._wavenumber = first.wavenumber_cm1
        self._values = first.values
        self._plot.setLabel("left", first.label, units=first.unit or None)
        self._set_y_range(first.cyclic)

    def _set_y_range(self, cyclic: bool) -> None:
        if cyclic:
            self._plot.setYRange(-np.pi - 0.2, np.pi + 0.2)
        else:
            self._plot.enableAutoRange(axis="y")

    def _clear_overlays(self) -> None:
        for item in self._overlay_items:
            self._plot.removeItem(item)
        self._overlay_items = []
        if self._legend is not None:
            self._legend.clear()
        # A fit *result* no longer corresponds to a new curve; the fit *window*
        # (region item) deliberately survives a curve change, exactly like every
        # other measurement's geometry "survives channel changes" - re-fit it
        # explicitly (Fit Lorentzian) rather than silently recomputing.
        self._clear_fit_result()

    def set_readout(self, text: str) -> None:
        self._readout.setText(text)

    # -- lineshape fitting (docs/phase6-spectral-lineshape-analysis.md 3.3-3.4) -

    def _on_fit_toggled(self, checked: bool) -> None:
        self._fit_btn.setVisible(checked)
        if checked:
            self._show_fit_region()
        else:
            self._remove_fit_region()
            self._clear_fit_result()

    def _show_fit_region(self) -> None:
        if self._fit_region is not None or self._wavenumber is None or self._wavenumber.size == 0:
            return
        lo, hi = float(self._wavenumber.min()), float(self._wavenumber.max())
        span = hi - lo
        region = pg.LinearRegionItem(
            values=(lo + 0.25 * span, lo + 0.75 * span), brush=_FIT_REGION_BRUSH
        )
        region.setZValue(10)
        self._plot.addItem(region)
        self._fit_region = region

    def _remove_fit_region(self) -> None:
        if self._fit_region is not None:
            self._plot.removeItem(self._fit_region)
            self._fit_region = None

    def fit_window_bounds(self) -> tuple[float, float] | None:
        """The current draggable fit-window bounds, or ``None`` if not shown."""
        if self._fit_region is None:
            return None
        lo, hi = self._fit_region.getRegion()
        return float(lo), float(hi)

    def _on_fit_clicked(self) -> None:
        bounds = self.fit_window_bounds()
        if bounds is not None:
            self.fitRequested.emit(*bounds)

    def show_fit(self, result: LineshapeFit) -> None:
        """Overlay a computed :class:`~snomniman.viz.LineshapeFit`: the fit curve
        on the main plot, the residual below it, and a text summary."""
        if self._fit_curve_item is not None:
            self._plot.removeItem(self._fit_curve_item)
        self._fit_curve_item = self._plot.plot(
            result.wavenumber_cm1, result.fit_curve, pen=_FIT_PEN
        )
        self._residual_curve.setData(result.wavenumber_cm1, result.residuals)
        self._residual_plot.setVisible(True)
        self._fit_readout.setText(_format_fit_summary(result))

    def _clear_fit_result(self) -> None:
        if self._fit_curve_item is not None:
            self._plot.removeItem(self._fit_curve_item)
            self._fit_curve_item = None
        self._residual_curve.setData([], [])
        self._residual_plot.setVisible(False)
        self._fit_readout.setText("")

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


def _format_fit_summary(result: LineshapeFit) -> str:
    lo, hi = result.window
    wavelength_um = 1e4 / result.center
    return (
        f"<b>Lorentzian fit</b> (window {lo:.0f}-{hi:.0f} cm^-1, n={result.n_window}):   "
        f"center = {result.center:.1f} &plusmn; {result.center_stderr:.2f} cm^-1 "
        f"({wavelength_um:.3f} &micro;m)   "
        f"FWHM = {result.fwhm:.1f} &plusmn; {result.fwhm_stderr:.2f} cm^-1   "
        f"amplitude = {result.amplitude:.3g} &plusmn; {result.amplitude_stderr:.2g}<br>"
        f"baseline: {result.baseline_slope:.3g}&middot;x + {result.baseline_intercept:.3g}"
        f"   R&sup2; = {result.r_squared:.4f}   SSR/dof = {result.ssr_per_dof:.3g}"
        f"   RMS = {result.rms:.3g}"
    )


__all__ = ["SpectrumPlotView"]
