"""ProcessPanel: apply processing steps and preview the result.

The panel is deliberately thin (Rule 4): it emits signals with the chosen
parameters and lets the window handle computation, dataset management, and
view switching.  No scientific logic lives here.
"""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets


class ProcessPanel(QtWidgets.QWidget):
    """Controls for the plane-level (and future) processing operations.

    Workflow::

        1. User configures channel + order.
        2. User clicks "Preview" → previewRequested is emitted; the window
           runs the step, shows a before/after comparison, and calls
           set_preview_mode(True) to reveal the Apply/Cancel buttons.
        3. User clicks "Apply"  → previewAccepted is emitted; the window
           commits the derivation and calls set_preview_mode(False).
        4. User clicks "Cancel" → previewCancelled is emitted; the window
           discards the preview and calls set_preview_mode(False).
    """

    #: Emitted when the user asks for a before/after comparison. Args: channel, order.
    previewRequested: QtCore.Signal = QtCore.Signal(str, int)
    #: Emitted when the user accepts the current preview (commits the derivation).
    previewAccepted: QtCore.Signal = QtCore.Signal()
    #: Emitted when the user cancels the current preview.
    previewCancelled: QtCore.Signal = QtCore.Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        group = QtWidgets.QGroupBox("Plane Level")
        group_layout = QtWidgets.QFormLayout(group)

        self._channel_combo = QtWidgets.QComboBox()
        group_layout.addRow("Channel:", self._channel_combo)

        self._order_spin = QtWidgets.QSpinBox()
        self._order_spin.setMinimum(1)
        self._order_spin.setMaximum(3)
        self._order_spin.setValue(1)
        self._order_spin.setToolTip("1 = plane, 2 = paraboloid, 3 = higher-order")
        group_layout.addRow("Order:", self._order_spin)

        btn_row = QtWidgets.QHBoxLayout()
        self._preview_btn = QtWidgets.QPushButton("Preview")
        self._preview_btn.setToolTip("Show a before/after comparison without committing")
        self._preview_btn.clicked.connect(self._on_preview_clicked)
        btn_row.addWidget(self._preview_btn)

        self._apply_btn = QtWidgets.QPushButton("Apply")
        self._apply_btn.setToolTip("Commit this derivation as the active measurement")
        self._apply_btn.setVisible(False)
        self._apply_btn.clicked.connect(lambda: self.previewAccepted.emit())
        btn_row.addWidget(self._apply_btn)

        self._cancel_btn = QtWidgets.QPushButton("Cancel")
        self._cancel_btn.setToolTip("Discard the preview and return to the original view")
        self._cancel_btn.setVisible(False)
        self._cancel_btn.clicked.connect(lambda: self.previewCancelled.emit())
        btn_row.addWidget(self._cancel_btn)

        btn_row.addStretch(1)
        group_layout.addRow(btn_row)
        layout.addWidget(group)

        self._status = QtWidgets.QLabel()
        self._status.setWordWrap(True)
        self._status.setStyleSheet("color: #9aa0a6;")
        layout.addWidget(self._status)
        layout.addStretch(1)

    # -- public interface ----------------------------------------------------- #

    def set_channels(self, channels: list[str]) -> None:
        """Populate the channel selector with available real-valued channels."""
        current = self._channel_combo.currentText()
        self._channel_combo.blockSignals(True)
        self._channel_combo.clear()
        self._channel_combo.addItems(channels)
        if current in channels:
            self._channel_combo.setCurrentText(current)
        elif "Z" in channels:
            self._channel_combo.setCurrentText("Z")
        self._channel_combo.blockSignals(False)

    def set_preview_mode(self, active: bool) -> None:
        """Enter or exit preview mode (show Apply/Cancel, disable Preview)."""
        self._preview_btn.setEnabled(not active)
        self._apply_btn.setVisible(active)
        self._cancel_btn.setVisible(active)
        if active:
            ch = self._channel_combo.currentText()
            order = self._order_spin.value()
            self._status.setText(
                f"Previewing plane level on '{ch}' (order {order}).\n"
                "Click Apply to commit or Cancel to discard."
            )
        else:
            self._status.setText("")

    # -- internals ------------------------------------------------------------ #

    def _on_preview_clicked(self) -> None:
        channel = self._channel_combo.currentText()
        if not channel:
            return
        self.previewRequested.emit(channel, self._order_spin.value())


__all__ = ["ProcessPanel"]
