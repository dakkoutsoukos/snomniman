"""The Measurement Explorer window: where files become an understood measurement.

Composes the read-only experience from the model and the panels: an always-visible
identity header (the scientific frame), the channel browser, the physical image
view, and the metadata/provenance inspectors, with the conventions and a live
cursor readout in the status bar. It is wiring only - it translates user gestures
into model queries and pushes the results into widgets; it computes nothing
scientific and never modifies the measurement (Rule 4; "explore before you
process").

Processing derivations (plane level, future operations) produce new immutable
Datasets via the processing engine.  The window keeps a linear history stack so
the researcher can navigate back to the original measurement after a derivation.
"""

from __future__ import annotations

from typing import Any

from PySide6 import QtCore, QtWidgets

from snomniman import viz
from snomniman.core import Dataset
from snomniman.core.exceptions import ProcessingError
from snomniman.viz import REAL, RenderData

from .comparison import ComparisonView, ContactSheet
from .imageview import ChannelImageView
from .measurement import MeasurementController, MeasurementPanel
from .model import PRESET_LABELS, ExplorerModel, MeasurementIdentity, PaneSpec
from .panels import ChannelBrowser, MetadataInspector, ProvenanceInspector
from .process import ProcessPanel


class MeasurementExplorerWindow(QtWidgets.QMainWindow):
    """The central Explorer surface for one measurement and its derivations."""

    def __init__(self, model: ExplorerModel) -> None:
        super().__init__()
        self._model = model
        self._history: list[ExplorerModel] = []
        self._preview_ds: Dataset | None = None
        self._preview_channel: str = ""
        self._preview_order: int = 1

        self._title = QtWidgets.QLabel()
        self._facts = QtWidgets.QLabel()
        self._active = QtWidgets.QLabel()
        self._back_btn = QtWidgets.QPushButton()
        self._image = ChannelImageView()
        self._comparison = ComparisonView()
        self._contact = ContactSheet()
        self._stack = QtWidgets.QStackedWidget()
        self._browser = ChannelBrowser()
        self._metadata = MetadataInspector()
        self._provenance = ProvenanceInspector()
        self._conventions = QtWidgets.QLabel()
        self._process = ProcessPanel()
        # Measurements are read-only observations placed on the single image; they
        # report across the single view's channels (current + phase + topography).
        self._measure = MeasurementController(model, self._image, model.single_view_specs)
        self._measure_panel = MeasurementPanel(self._measure)

        self._build_layout()
        self._wire()
        self._load()

    # -- construction ---------------------------------------------------------

    def _build_layout(self) -> None:
        central = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout(central)
        outer.setContentsMargins(8, 8, 8, 4)
        outer.setSpacing(4)

        title_font = self._title.font()
        title_font.setPointSize(title_font.pointSize() + 4)
        title_font.setBold(True)
        self._title.setFont(title_font)
        self._facts.setStyleSheet("color: #9aa0a6;")
        self._active.setStyleSheet("color: #c8c8c8;")
        outer.addWidget(self._title)
        outer.addWidget(self._facts)
        outer.addWidget(self._build_view_controls())
        self._stack.addWidget(self._image)  # page 0: single channel
        self._stack.addWidget(self._comparison)  # page 1: side-by-side comparison
        self._stack.addWidget(self._contact)  # page 2: harmonic contact sheet
        outer.addWidget(self._stack, 1)
        outer.addWidget(self._active)
        self.setCentralWidget(central)

        channels = QtWidgets.QDockWidget("Channels")
        channels.setWidget(self._browser)
        channels.setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, channels)

        tabs = QtWidgets.QTabWidget()
        self._inspect_tabs = tabs
        tabs.addTab(self._metadata, "Metadata")
        tabs.addTab(self._provenance, "Provenance")
        tabs.addTab(self._measure_panel, "Measure")
        tabs.addTab(self._process, "Process")
        inspect = QtWidgets.QDockWidget("Inspect")
        inspect.setWidget(tabs)
        inspect.setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, inspect)
        self.resizeDocks([channels, inspect], [260, 380], QtCore.Qt.Orientation.Horizontal)

        self.statusBar().addWidget(self._conventions)

    def _build_view_controls(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout(bar)
        row.setContentsMargins(0, 2, 0, 2)

        self._back_btn.setVisible(False)
        self._back_btn.clicked.connect(self._navigate_back)
        row.addWidget(self._back_btn)
        row.addSpacing(8)

        single = QtWidgets.QPushButton("Single")
        single.setToolTip("Show one channel with full colorbar and contrast controls")
        single.clicked.connect(self._show_single)
        row.addWidget(single)
        row.addSpacing(12)
        row.addWidget(QtWidgets.QLabel("Compare:"))
        for preset, label in PRESET_LABELS.items():
            button = QtWidgets.QPushButton(label)
            button.clicked.connect(lambda _checked=False, p=preset: self._show_comparison(p))
            row.addWidget(button)
        contact = QtWidgets.QPushButton("Contact sheet")
        contact.setToolTip("Thumbnails of every harmonic; click one to inspect it")
        contact.clicked.connect(self._show_contact)
        row.addWidget(contact)
        row.addStretch(1)
        export = QtWidgets.QPushButton("Export figure...")
        export.setToolTip("Save the current view as a publication figure + provenance")
        export.clicked.connect(self._export_figure)
        row.addWidget(export)
        return bar

    def _wire(self) -> None:
        self._browser.channelSelected.connect(self._on_channel_selected)
        self._browser.representationSelected.connect(self._on_representation_selected)
        self._image.cursorMoved.connect(self._on_cursor_moved)
        self._comparison.cursorMoved.connect(self._on_comparison_cursor)
        self._contact.channelSelected.connect(self._on_channel_selected)
        # Measurements live on the single image; adding one focuses that view.
        self._measure.measurementAdded.connect(self._show_single)
        # Processing signals
        self._process.previewRequested.connect(self._on_preview_requested)
        self._process.previewAccepted.connect(self._on_preview_accepted)
        self._process.previewCancelled.connect(self._on_preview_cancelled)

    # -- loading / refreshing -------------------------------------------------

    def _load(self) -> None:
        self.setWindowTitle(f"{self._model.title} - SNOMNIMAN Measurement Explorer")
        self._title.setText(self._model.title)
        self._facts.setText(_facts_line(self._model.identity()))
        self._conventions.setText("Conventions:  " + self._model.conventions_summary())
        self._browser.set_groups(self._model.channel_groups())
        self._metadata.set_sections(self._model.metadata_sections())
        self._provenance.set_provenance(
            self._model.provenance_summary(), self._model.provenance_steps()
        )
        self._process.set_channels(self._real_channels())
        self._browser.select(self._model.current_channel)
        self._show_single()

    def _on_channel_selected(self, canonical: str) -> None:
        # Selecting a channel (from the browser or a contact-sheet thumbnail) opens
        # it in the single, detailed view.
        self._model.set_channel(canonical)
        self._show_single()

    def _on_representation_selected(self, representation: str) -> None:
        self._model.set_representation(representation)
        self._show_single()

    # -- model switching (derivation navigation) ------------------------------

    def _update_model(self, new_model: ExplorerModel, *, push_history: bool = True) -> None:
        """Replace the active model; optionally push the old one to the history stack."""
        if push_history:
            self._history.append(self._model)
        self._model = new_model
        self._measure.set_model(new_model)
        self._refresh_navigation()
        self._load()

    def _navigate_back(self) -> None:
        if not self._history:
            return
        self._preview_ds = None
        self._process.set_preview_mode(False)
        self._update_model(self._history.pop(), push_history=False)

    def _refresh_navigation(self) -> None:
        has_history = bool(self._history)
        self._back_btn.setVisible(has_history)
        if has_history:
            self._back_btn.setText(f"← Back to {self._history[-1].title}")

    def _real_channels(self) -> list[str]:
        """Real-valued (non-complex) channels of the current dataset."""
        return [
            ch for ch in self._model.dataset.channel_names
            if not self._model.dataset.is_complex(ch)
        ]

    # -- view switching -------------------------------------------------------

    def _show_single(self) -> None:
        self._stack.setCurrentWidget(self._image)
        self._refresh_channel()

    def _show_comparison(self, preset: str) -> None:
        specs = self._model.comparison_layout(preset)
        self._comparison.set_panes(specs, self._model.render_spec)
        self._stack.setCurrentWidget(self._comparison)
        self._active.setText("Comparing:   " + "      |      ".join(s.title for s in specs))

    def _show_contact(self) -> None:
        specs = self._model.harmonic_panes()
        self._contact.set_panes(specs, self._model.render_spec)
        self._stack.setCurrentWidget(self._contact)
        self._active.setText(f"Contact sheet  -  {len(specs)} optical harmonics")

    # -- processing (plane level and future operations) -----------------------

    def _on_preview_requested(self, channel: str, order: int) -> None:
        from snomniman.processing.image.plane_level import PlaneLevel

        step = PlaneLevel(channel=channel, order=order)
        try:
            preview_ds = step.apply({"primary": self._model.dataset})
        except ProcessingError as exc:
            QtWidgets.QMessageBox.warning(self, "Preview failed", str(exc))
            return

        self._preview_ds = preview_ds
        self._preview_channel = channel
        self._preview_order = order

        preview_model = ExplorerModel(preview_ds, title="preview")
        orig_spec = PaneSpec(channel, REAL, label=f"{channel} (original)")
        leveled_spec = PaneSpec(channel, REAL, label=f"{channel} (leveled, order {order})")

        orig_rd = self._model.render_spec(PaneSpec(channel, REAL))
        leveled_rd = preview_model.render_spec(PaneSpec(channel, REAL))
        renders: dict[PaneSpec, RenderData] = {orig_spec: orig_rd, leveled_spec: leveled_rd}

        self._comparison.set_panes([orig_spec, leveled_spec], renders.__getitem__)
        self._stack.setCurrentWidget(self._comparison)
        self._active.setText(
            f"Preview: plane level on '{channel}' (order {order})"
            " — Apply to commit, Cancel to discard"
        )
        self._process.set_preview_mode(True)

    def _on_preview_accepted(self) -> None:
        if self._preview_ds is None:
            return
        ch = self._preview_channel
        derived_title = f"{self._model.title} → plane leveled ({ch})"
        new_model = ExplorerModel(self._preview_ds, title=derived_title)
        self._preview_ds = None
        self._preview_channel = ""
        self._process.set_preview_mode(False)
        self._update_model(new_model)

    def _on_preview_cancelled(self) -> None:
        self._preview_ds = None
        self._preview_channel = ""
        self._process.set_preview_mode(False)
        self._show_single()

    # -- publication export ---------------------------------------------------

    def _figure_inputs(self) -> tuple[str, list[tuple[PaneSpec, tuple[float, float]]], list[Any]]:
        """Gather (kind, panels-with-levels, overlays) for the current view."""
        current = self._stack.currentWidget()
        if current is self._comparison and self._comparison.specs:
            panels = [
                (spec, pane.levels)
                for spec, pane in zip(self._comparison.specs, self._comparison.panes, strict=True)
            ]
            return "comparison", panels, []
        if current is self._contact:
            panels = []
            for spec in self._model.harmonic_panes():
                rd = self._model.render_spec(spec)
                panels.append((spec, (rd.vmin, rd.vmax)))
            return "harmonic_series", panels, []
        # single view: the current channel, plus any measurement overlays
        overlays = self._measure.overlay_specs()
        kind = "measurement" if overlays else "single"
        current_spec = PaneSpec(self._model.current_channel, self._model.current_representation)
        return kind, [(current_spec, self._image.levels)], overlays

    def _export_figure(self) -> None:
        kind, panels, overlays = self._figure_inputs()
        spec = self._model.figure_spec(panels, overlays, kind=kind, title=self._model.title)
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export figure",
            f"{self._model.title}.pdf",
            "PDF (*.pdf);;PNG (*.png);;SVG (*.svg)",
        )
        if not path:
            return
        figure_path, provenance_path = viz.export(spec, self._model.dataset, path)
        QtWidgets.QMessageBox.information(
            self,
            "Figure exported",
            f"Saved publication figure:\n{figure_path}\n\n"
            f"with provenance:\n{provenance_path.name}",
        )

    def _refresh_channel(self) -> None:
        self._browser.set_representations(
            self._model.representations(), self._model.current_representation
        )
        self._refresh_image()

    def _refresh_image(self) -> None:
        render = self._model.render()
        self._image.show_render(render)
        # The colorbar now carries the value scale, so the caption stays minimal:
        # what channel/representation is shown and its processing state.
        state = self._channel_state(render.channel)
        self._active.setText(f"Showing   {render.title}      state: {state}")
        # Measurements survive channel changes: recompute them for the new channel.
        self._measure.refresh()

    def _on_cursor_moved(self, x_nm: float, y_nm: float, in_bounds: bool) -> None:
        if not in_bounds:
            self._image.set_readout("")
            return
        readout = self._model.cursor_readout(x_nm, y_nm)
        if not readout.in_bounds:
            self._image.set_readout("")
            return
        values = "      ".join(f"{v.label}: {v.value} {v.unit}" for v in readout.values)
        self._image.set_readout(
            f"x = {readout.x_nm:.0f} nm     y = {readout.y_nm:.0f} nm        {values}"
        )

    def _on_comparison_cursor(self, x_nm: float, y_nm: float, in_bounds: bool) -> None:
        if in_bounds:
            readout = self._model.values_at(self._comparison.specs, x_nm, y_nm)
        else:
            readout = None
        if readout is None or not readout.in_bounds:
            self._comparison.set_readout("")
            self._comparison.set_crosshair(0.0, 0.0, False)
            return
        values = "      ".join(f"{v.label}: {v.value} {v.unit}" for v in readout.values)
        self._comparison.set_readout(
            f"x = {readout.x_nm:.0f} nm     y = {readout.y_nm:.0f} nm        {values}"
        )
        self._comparison.set_crosshair(x_nm, y_nm, True)

    def _channel_state(self, channel: str) -> str:
        try:
            return self._model.dataset.metadata.channel(channel).state
        except KeyError:
            return "raw"


def _facts_line(identity: MeasurementIdentity) -> str:
    parts: list[str] = [f"{identity.kind}", "raw measurement" if identity.is_raw else "derived"]
    if identity.pixels is not None:
        parts.append(f"{identity.pixels[0]} x {identity.pixels[1]} px")
    if identity.field_nm is not None:
        parts.append(f"{identity.field_nm[0] / 1000:g} x {identity.field_nm[1] / 1000:g} µm")
    if identity.wavenumber_cm1 is not None:
        parts.append(f"{identity.wavenumber_cm1:g} cm^-1")
    if identity.detection:
        parts.append(identity.detection)
    if identity.source_type:
        parts.append(identity.source_type)
    if identity.datetime:
        parts.append(identity.datetime)
    if identity.vendor:
        parts.append(identity.vendor)
    return "      ".join(parts)


__all__ = ["MeasurementExplorerWindow"]
