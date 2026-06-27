"""The Scientific Briefing panel: an expert orientation to the loaded measurement.

Pure presentation (Rule 4): it renders the :class:`~snomniman.ai.report.Briefing`
produced by :meth:`~snomniman.gui.model.ExplorerModel.scientific_briefing` and holds
no scientific logic. The briefing's **facts** are deterministic and always shown; an
optional AI **interpretation** appears only when a provider is configured (none is, in
this build) - the facts are complete and authoritative on their own. This is a
read-only briefing, not a chat: no input box, no history, no agent behaviour.
"""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from snomniman.ai import Briefing


class BriefingPanel(QtWidgets.QWidget):
    """A read-only briefing: collapsible fact sections + an optional AI narrative."""

    def __init__(self) -> None:
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        intro = QtWidgets.QLabel(
            "An orientation to this measurement, grounded entirely in the Description "
            "API and the Diagnostics Engine. Facts, not advice."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #9aa0a6;")
        layout.addWidget(intro)

        self._tree = QtWidgets.QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(True)
        self._tree.setWordWrap(True)
        layout.addWidget(self._tree, 1)

        self._interpretation = QtWidgets.QLabel()
        self._interpretation.setWordWrap(True)
        self._interpretation.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        box = QtWidgets.QGroupBox("Interpretation (AI)")
        box_layout = QtWidgets.QVBoxLayout(box)
        box_layout.addWidget(self._interpretation)
        layout.addWidget(box)

        self._copy = QtWidgets.QPushButton("Copy briefing")
        self._copy.setToolTip("Copy the full briefing (facts + interpretation) as text")
        self._copy.clicked.connect(self._copy_to_clipboard)
        layout.addWidget(self._copy, 0, QtCore.Qt.AlignmentFlag.AlignRight)

        self._briefing: Briefing | None = None

    def set_briefing(self, briefing: Briefing) -> None:
        self._briefing = briefing
        self._tree.clear()
        for section in briefing.sections:
            header = QtWidgets.QTreeWidgetItem([section.title])
            header.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
            font = header.font(0)
            font.setBold(True)
            header.setFont(0, font)
            self._tree.addTopLevelItem(header)
            for st in section.statements:
                header.addChild(QtWidgets.QTreeWidgetItem([st.text]))
            header.setExpanded(True)

        if briefing.interpretation is not None:
            self._interpretation.setText(briefing.interpretation)
            self._interpretation.setStyleSheet("")
        else:
            self._interpretation.setText(
                "No AI interpretation provider is configured. "
                "The facts above are complete and authoritative."
            )
            self._interpretation.setStyleSheet("color: #9aa0a6; font-style: italic;")

    def as_text(self) -> str:
        """Plain-text rendering of the current briefing (for copy/export)."""
        if self._briefing is None:
            return ""
        lines: list[str] = []
        if self._briefing.title:
            lines.append(f"Scientific Briefing - {self._briefing.title}")
            lines.append("")
        for section in self._briefing.sections:
            lines.append(section.title)
            lines.extend(f"  - {st.text}" for st in section.statements)
            lines.append("")
        if self._briefing.interpretation is not None:
            lines.append(f"Interpretation (AI, {self._briefing.provider}):")
            lines.append(f"  {self._briefing.interpretation}")
        return "\n".join(lines).rstrip() + "\n"

    def _copy_to_clipboard(self) -> None:
        clipboard = QtWidgets.QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self.as_text())
