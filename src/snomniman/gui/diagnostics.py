"""The Diagnostics panel: deterministic facts about the measurement, at a glance.

Pure presentation (Rule 4): it renders the :class:`DiagnosticSection` view objects
produced by :meth:`~snomniman.gui.model.ExplorerModel.diagnostics_report` and holds
no scientific logic. The numbers are computed by the backend Scientific Diagnostics
Engine (``snomniman.diagnostics``); this panel only displays them. Diagnostics are
observations, not recommendations - the panel never suggests an action.
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6 import QtCore, QtWidgets

from .model import DiagnosticSection


class DiagnosticsPanel(QtWidgets.QWidget):
    """A read-only tree of diagnostic sections (topography, channels, ...)."""

    def __init__(self) -> None:
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        intro = QtWidgets.QLabel(
            "Deterministic observations of this measurement. Facts, not advice."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #9aa0a6;")
        layout.addWidget(intro)

        self._tree = QtWidgets.QTreeWidget()
        self._tree.setColumnCount(2)
        self._tree.setHeaderLabels(["Diagnostic", "Value"])
        self._tree.setRootIsDecorated(False)
        self._tree.header().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        layout.addWidget(self._tree, 1)

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
