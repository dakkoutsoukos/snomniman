"""The Diagnostics panel: deterministic facts about the measurement, at a glance.

Pure presentation (Rule 4): it renders the :class:`DiagnosticSection` view objects
produced by :meth:`~snomniman.gui.model.ExplorerModel.diagnostics_report` and holds
no scientific logic. The numbers are computed by the backend Scientific Diagnostics
Engine (``snomniman.diagnostics``); this panel only displays them. Diagnostics are
observations, not recommendations - the panel never suggests an action.

It also shows the **value distribution** (histogram) of the channel currently on
screen - percentile markers and the active contrast range drawn over the
distribution - a read-only quantitative analysis (not a display control).
"""

from __future__ import annotations

from collections.abc import Sequence

import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets

from snomniman.diagnostics import HistogramData

from .model import DiagnosticSection

_MUTED = "color: #9aa0a6;"
_P50_PEN = pg.mkPen("#ffcc33", width=1)  # median marker
_RANGE_PEN = pg.mkPen("#46c2ff", width=1, style=QtCore.Qt.PenStyle.DashLine)  # contrast limits


class DiagnosticsPanel(QtWidgets.QWidget):
    """A read-only tree of diagnostic sections + the current channel's distribution."""

    def __init__(self) -> None:
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        intro = QtWidgets.QLabel(
            "Deterministic observations of this measurement. Facts, not advice."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(_MUTED)
        layout.addWidget(intro)

        self._tree = QtWidgets.QTreeWidget()
        self._tree.setColumnCount(2)
        self._tree.setHeaderLabels(["Diagnostic", "Value"])
        self._tree.setRootIsDecorated(False)
        self._tree.header().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        layout.addWidget(self._tree, 1)

        # Distribution (histogram) of the channel currently displayed.
        layout.addWidget(_bold("Distribution (current channel)"))
        self._hist_plot = pg.PlotWidget()
        self._hist_plot.setMaximumHeight(170)
        self._hist_plot.setMouseEnabled(x=False, y=False)
        self._hist_plot.hideButtons()
        self._hist_plot.setLabel("left", "count")
        layout.addWidget(self._hist_plot)
        self._hist_summary = QtWidgets.QLabel("Select a channel to see its value distribution.")
        self._hist_summary.setWordWrap(True)
        self._hist_summary.setStyleSheet(_MUTED)
        self._hist_summary.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self._hist_summary)

    def set_report(self, sections: Sequence[DiagnosticSection]) -> None:
        self._tree.clear()
        for section in sections:
            header = QtWidgets.QTreeWidgetItem([section.title, ""])
            header.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)  # a label, not selectable
            font = header.font(0)
            font.setBold(True)
            header.setFont(0, font)
            self._tree.addTopLevelItem(header)
            for row in section.rows:
                header.addChild(QtWidgets.QTreeWidgetItem([row.label, row.value]))
            header.setExpanded(True)

    def set_histogram(
        self, hist: HistogramData, vmin: float, vmax: float, title: str
    ) -> None:
        """Draw the distribution with median + contrast-range markers and a stats line."""
        self._hist_plot.clear()
        unit = hist.unit or ""
        self._hist_plot.setLabel("bottom", title, units=unit or None)
        if hist.count == 0 or not hist.counts:
            self._hist_summary.setText(f"{title}: no finite values.")
            return

        edges = hist.bin_edges
        centers = [(edges[i] + edges[i + 1]) / 2 for i in range(len(hist.counts))]
        widths = [(edges[i + 1] - edges[i]) * 0.92 for i in range(len(hist.counts))]
        self._hist_plot.addItem(
            pg.BarGraphItem(x=centers, height=list(hist.counts), width=widths, brush="#46c2ff")
        )
        # Median marker + the active contrast limits (dynamic-range visualization).
        if hist.median is not None:
            self._hist_plot.addItem(pg.InfiniteLine(pos=hist.median, angle=90, pen=_P50_PEN))
        for limit in (vmin, vmax):
            self._hist_plot.addItem(pg.InfiniteLine(pos=limit, angle=90, pen=_RANGE_PEN))

        self._hist_summary.setText(_summary(hist, unit))


def _summary(hist: HistogramData, unit: str) -> str:
    def fmt(value: float | None) -> str:
        return "-" if value is None else f"{value:.4g}"

    suffix = f" {unit}" if unit else ""
    p = hist.percentiles
    pct = ""
    if "p5" in p and "p95" in p:
        pct = f"   p5-p95: {p['p5']:.4g} to {p['p95']:.4g}{suffix}"
    return (
        f"n = {hist.count}     mean {fmt(hist.mean)}     median {fmt(hist.median)}     "
        f"std {fmt(hist.std)}     RMS {fmt(hist.rms)}{suffix}"
        f"\nyellow = median; dashed = current contrast range.{pct}"
    )


def _bold(text: str) -> QtWidgets.QLabel:
    label = QtWidgets.QLabel(text)
    font = label.font()
    font.setBold(True)
    label.setFont(font)
    return label
