"""Comparative exploration: synchronized side-by-side panes and a contact sheet.

Near-field analysis is fundamentally comparative - does the optical signal track
the topography, which harmonic carries contrast, does phase tell the same story as
amplitude, how does the sample differ from its reference. These widgets make that
comparison effortless and strictly read-only:

* :class:`ComparisonView` tiles several channel views, **shares their zoom, pan and
  cursor** (one crosshair marks the same physical point in every pane), and reports
  every visible channel's value at that point in a single readout - minimizing eye
  movement. It computes nothing; it renders the panes a presenter hands it and asks
  the presenter for the values under the cursor.
* :class:`ContactSheet` shows a compact thumbnail of every harmonic for orientation;
  clicking one selects that channel for a closer look.

Neither modifies the Dataset.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets

from snomniman.viz import RenderData

from .colormap import lookup_table
from .imageview import ChannelImageView
from .model import PaneSpec

#: A presenter callback turning a pane spec into display-ready data.
Renderer = Callable[[PaneSpec], RenderData]


def _grid_shape(n: int) -> tuple[int, int]:
    """Rows, cols for ``n`` panes: a tidy near-square grid (max 3 columns)."""
    if n <= 1:
        return 1, 1
    cols = 2 if n <= 4 else 3
    return (n + cols - 1) // cols, cols


class ComparisonView(QtWidgets.QWidget):
    """A grid of channel panes with synchronized zoom, pan and cursor."""

    #: Forwarded from whichever pane is hovered: (x_nm, y_nm, in_bounds).
    cursorMoved = QtCore.Signal(float, float, bool)

    def __init__(self) -> None:
        super().__init__()
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        grid_host = QtWidgets.QWidget()
        self._grid = QtWidgets.QGridLayout(grid_host)
        self._grid.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(grid_host, 1)
        self._readout = QtWidgets.QLabel("Hover over any panel to compare values")
        self._readout.setStyleSheet("color: #c8c8c8; padding: 2px 6px;")
        outer.addWidget(self._readout)

        self._specs: tuple[PaneSpec, ...] = ()
        self._panes: list[ChannelImageView] = []
        self._last_readout = ""

    def set_panes(self, specs: Sequence[PaneSpec], renderer: Renderer) -> None:
        """Lay out one pane per spec, render each, and synchronize navigation."""
        for pane in self._panes:
            self._grid.removeWidget(pane)
            pane.setParent(None)
            pane.deleteLater()
        self._panes = []
        self._specs = tuple(specs)

        rows, cols = _grid_shape(len(self._specs))
        for index, spec in enumerate(self._specs):
            pane = ChannelImageView(compact=True)
            pane.show_render(renderer(spec))
            pane.set_title(spec.title)
            pane.cursorMoved.connect(self._on_pane_cursor)
            if self._panes:
                pane.link_view(self._panes[0])  # share zoom + pan with the first pane
            self._grid.addWidget(pane, index // cols, index % cols)
            self._panes.append(pane)
        _ = rows  # grid sizing is implicit in addWidget positions

    @property
    def specs(self) -> tuple[PaneSpec, ...]:
        return self._specs

    @property
    def panes(self) -> list[ChannelImageView]:
        return list(self._panes)

    def set_readout(self, text: str) -> None:
        self._last_readout = text
        self._readout.setText(text)

    def set_crosshair(self, x_nm: float, y_nm: float, visible: bool) -> None:
        """Mark the same physical point in every pane (the synchronized cursor)."""
        for pane in self._panes:
            pane.set_crosshair(x_nm, y_nm, visible)

    def _on_pane_cursor(self, x_nm: float, y_nm: float, in_bounds: bool) -> None:
        self.cursorMoved.emit(x_nm, y_nm, in_bounds)


class _Thumbnail(QtWidgets.QWidget):
    """A small, clickable, axis-free image used in the contact sheet."""

    clicked = QtCore.Signal(str)

    def __init__(self, render: RenderData, channel: str, title: str) -> None:
        super().__init__()
        self._channel = channel
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(1)

        glw = pg.GraphicsLayoutWidget()
        glw.setMinimumSize(150, 150)
        plot = glw.addPlot()
        plot.setAspectLocked(True)
        plot.setMouseEnabled(x=False, y=False)
        plot.hideButtons()
        plot.hideAxis("left")
        plot.hideAxis("bottom")
        image = pg.ImageItem(render.values)
        x0, x1, y0, y1 = render.extent_nm
        image.setRect(QtCore.QRectF(x0, y0, x1 - x0, y1 - y0))
        image.setLookupTable(lookup_table(render.colormap))
        image.setLevels((render.vmin, render.vmax))
        plot.addItem(image)
        plot.getViewBox().setRange(xRange=(x0, x1), yRange=(y0, y1), padding=0.0)
        glw.scene().sigMouseClicked.connect(lambda _evt: self.clicked.emit(self._channel))
        layout.addWidget(glw)

        label = QtWidgets.QLabel(title)
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        label.setStyleSheet("color: #c8c8c8;")
        layout.addWidget(label)


class ContactSheet(QtWidgets.QWidget):
    """A thumbnail of every harmonic, for orientation; click to open one closely."""

    channelSelected = QtCore.Signal(str)

    def __init__(self) -> None:
        super().__init__()
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        caption = QtWidgets.QLabel("Harmonic contact sheet - click a panel to inspect it")
        caption.setStyleSheet("color: #9aa0a6;")
        outer.addWidget(caption)
        host = QtWidgets.QWidget()
        self._grid = QtWidgets.QGridLayout(host)
        outer.addWidget(host, 1)
        self._thumbs: list[_Thumbnail] = []

    def set_panes(self, specs: Sequence[PaneSpec], renderer: Renderer) -> None:
        for thumb in self._thumbs:
            self._grid.removeWidget(thumb)
            thumb.setParent(None)
            thumb.deleteLater()
        self._thumbs = []

        _, cols = _grid_shape(len(specs))
        for index, spec in enumerate(specs):
            thumb = _Thumbnail(renderer(spec), spec.channel, spec.title)
            thumb.clicked.connect(self.channelSelected)
            self._grid.addWidget(thumb, index // cols, index % cols)
            self._thumbs.append(thumb)

    @property
    def thumbnails(self) -> list[_Thumbnail]:
        return list(self._thumbs)


__all__ = ["ComparisonView", "ContactSheet"]
