"""The AI Scientist panel: an expert orientation plus grounded next-step suggestions.

Pure presentation (Rule 4): it renders the :class:`~snomniman.ai.report.Briefing` and
the :class:`~snomniman.ai.recommend.WorkflowSuggestions` the model produces, and holds
no scientific logic. Both are **deterministic** and always shown; an optional AI
*interpretation* appears only when a provider is configured (none is, in this build).

"Suggested next steps" are grounded recommendations: each points at a registered
operation that is applicable now and not yet applied. The panel never executes them -
its Preview button hands the operation off to the generic Processing Workspace (the
researcher previews and decides). This is a briefing, not a chat: no input box, no
agent behaviour.
"""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from snomniman.ai import (
    STRENGTH_MODERATE,
    STRENGTH_STRONG,
    Briefing,
    Recommendation,
    WorkflowSuggestions,
)

_MUTED = "color: #9aa0a6;"
_STRENGTH_STYLE = {
    STRENGTH_STRONG: "color: #1e1f22; background: #5bd66f; padding: 1px 6px; border-radius: 6px;",
    STRENGTH_MODERATE: "color: #1e1f22; background: #e6c44d; padding: 1px 6px; border-radius: 6px;",
}
_STRENGTH_TENTATIVE_STYLE = (
    "color: #c8c8c8; background: #44474d; padding: 1px 6px; border-radius: 6px;"
)


class BriefingPanel(QtWidgets.QWidget):
    """A read-only AI Scientist panel: facts, suggested next steps, optional narrative."""

    #: Emitted when a recommendation's Preview is clicked. Args: step_id, params dict.
    recommendationPreviewRequested: QtCore.Signal = QtCore.Signal(str, object)

    def __init__(self) -> None:
        super().__init__()
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)

        intro = QtWidgets.QLabel(
            "An orientation to this measurement and a few grounded next steps, derived "
            "entirely from the Description API and the Diagnostics Engine. Facts and "
            "applicable suggestions - never advice that the data does not support."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(_MUTED)
        outer.addWidget(intro)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        body = QtWidgets.QWidget()
        self._body = QtWidgets.QVBoxLayout(body)
        self._body.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        self._tree = QtWidgets.QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(True)
        self._tree.setWordWrap(True)
        self._tree.setMinimumHeight(220)
        self._body.addWidget(self._tree)

        self._suggest_box = QtWidgets.QGroupBox("Suggested next steps")
        self._suggest_layout = QtWidgets.QVBoxLayout(self._suggest_box)
        self._suggest_layout.setSpacing(6)
        self._body.addWidget(self._suggest_box)

        self._interpretation = QtWidgets.QLabel()
        self._interpretation.setWordWrap(True)
        self._interpretation.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        box = QtWidgets.QGroupBox("Interpretation (AI)")
        box_layout = QtWidgets.QVBoxLayout(box)
        box_layout.addWidget(self._interpretation)
        self._body.addWidget(box)
        self._body.addStretch(1)

        self._copy = QtWidgets.QPushButton("Copy briefing")
        self._copy.setToolTip("Copy the full briefing (facts + suggestions) as text")
        self._copy.clicked.connect(self._copy_to_clipboard)
        outer.addWidget(self._copy, 0, QtCore.Qt.AlignmentFlag.AlignRight)

        self._briefing: Briefing | None = None
        self._suggestions: WorkflowSuggestions | None = None

    # -- briefing (facts) -----------------------------------------------------

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

    # -- suggested next steps -------------------------------------------------

    def set_suggestions(self, suggestions: WorkflowSuggestions) -> None:
        """Render the ranked recommendations as cards (or a note when there are none)."""
        self._suggestions = suggestions
        _clear_layout(self._suggest_layout)
        if not suggestions.recommendations:
            note = suggestions.note or "No next steps are suggested for this measurement."
            label = QtWidgets.QLabel(note)
            label.setWordWrap(True)
            label.setStyleSheet(_MUTED)
            self._suggest_layout.addWidget(label)
            return
        caption = QtWidgets.QLabel(
            "Each step is applicable now and not yet applied. Preview opens it in the "
            "Processing Workspace - the AI proposes, you decide."
        )
        caption.setWordWrap(True)
        caption.setStyleSheet(_MUTED)
        self._suggest_layout.addWidget(caption)
        for rec in suggestions.recommendations:
            self._suggest_layout.addWidget(self._make_card(rec))

    def _make_card(self, rec: Recommendation) -> QtWidgets.QWidget:
        card = QtWidgets.QFrame()
        card.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        layout = QtWidgets.QVBoxLayout(card)
        layout.setSpacing(3)

        head = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel(rec.title)
        title_font = title.font()
        title_font.setBold(True)
        title.setFont(title_font)
        head.addWidget(title)
        badge = QtWidgets.QLabel(rec.strength)
        badge.setStyleSheet(_STRENGTH_STYLE.get(rec.strength, _STRENGTH_TENTATIVE_STYLE))
        head.addWidget(badge)
        head.addStretch(1)
        layout.addLayout(head)

        rationale = QtWidgets.QLabel(rec.rationale)
        rationale.setWordWrap(True)
        layout.addWidget(rationale)

        if rec.evidence:
            why = QtWidgets.QLabel(
                "Why:\n" + "\n".join(f"  • {e.text}" for e in rec.evidence)
            )
            why.setWordWrap(True)
            why.setStyleSheet(_MUTED)
            layout.addWidget(why)

        outcome = QtWidgets.QLabel(f"Expected outcome: {rec.expected_outcome}")
        outcome.setWordWrap(True)
        outcome.setStyleSheet(_MUTED)
        layout.addWidget(outcome)

        if rec.considerations:
            caveats = QtWidgets.QLabel(
                "Consider:\n" + "\n".join(f"  • {c}" for c in rec.considerations)
            )
            caveats.setWordWrap(True)
            caveats.setStyleSheet(_MUTED)
            layout.addWidget(caveats)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch(1)
        preview = QtWidgets.QPushButton("Preview")
        preview.setToolTip("Open this operation in the Processing Workspace, pre-configured")
        preview.clicked.connect(
            lambda _=False, sid=rec.step_id, params=dict(rec.params): (
                self.recommendationPreviewRequested.emit(sid, params)
            )
        )
        btn_row.addWidget(preview)
        layout.addLayout(btn_row)
        return card

    # -- copy / export --------------------------------------------------------

    def as_text(self) -> str:
        """Plain-text rendering of the briefing + suggestions (for copy/export)."""
        lines: list[str] = []
        if self._briefing is not None:
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
                lines.append("")
        if self._suggestions is not None:
            lines.append("Suggested next steps")
            if self._suggestions.recommendations:
                for rec in self._suggestions.recommendations:
                    lines.append(f"  - {rec.title} [{rec.strength}]: {rec.rationale}")
            else:
                lines.append(f"  {self._suggestions.note or '(none)'}")
        return "\n".join(lines).rstrip() + "\n"

    def _copy_to_clipboard(self) -> None:
        clipboard = QtWidgets.QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self.as_text())


def _clear_layout(layout: QtWidgets.QLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item is None:
            continue
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()
        else:
            child = item.layout()
            if child is not None:
                _clear_layout(child)


__all__ = ["BriefingPanel"]
