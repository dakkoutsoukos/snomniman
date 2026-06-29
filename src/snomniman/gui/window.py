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

from pathlib import Path
from typing import Any

from PySide6 import QtCore, QtGui, QtWidgets

from snomniman import viz
from snomniman.core.exceptions import DatasetError, ProcessingError, ReaderError
from snomniman.io import export_channel_gsf, write_zarr
from snomniman.knowledge import article_for_operation
from snomniman.pipeline import (
    Measurement,
    Project,
    load_project,
    measurement_from_history,
    save_project,
)
from snomniman.viz import RenderData

from .briefing import BriefingPanel
from .comparison import ComparisonView, ContactSheet
from .diagnostics import DiagnosticsPanel
from .imageview import ChannelImageView
from .knowledge import KnowledgePanel
from .measurement import MeasurementController, MeasurementPanel
from .model import (
    PRESET_LABELS,
    ExplorerModel,
    MeasurementIdentity,
    MeasurementSession,
    OperationPreview,
    PaneSpec,
)
from .panels import (
    ChannelBrowser,
    MeasurementManager,
    MetadataInspector,
    ProvenanceInspector,
)
from .process import ProcessingWorkspace


class MeasurementExplorerWindow(QtWidgets.QMainWindow):
    """The central Explorer surface for one measurement and its derivations."""

    def __init__(self, model: ExplorerModel) -> None:
        super().__init__()
        # The session list is established first: the _model/_history properties read
        # the active session, so it must exist before any other state is touched.
        self._next_seq = 1
        self._sessions: list[MeasurementSession] = [
            MeasurementSession(
                model=model, measurement_id=self._new_measurement_id(), title=model.title
            )
        ]
        self._active_index = 0
        self._project_title = model.title
        self._preview: OperationPreview | None = None
        # The saved project this session is bound to (Save vs Save As), and the
        # active comparison preset (persisted with the active session's view state).
        self._project_path: Path | None = None
        self._comparison_preset: str | None = None

        self._title = QtWidgets.QLabel()
        self._facts = QtWidgets.QLabel()
        self._active = QtWidgets.QLabel()
        self._back_btn = QtWidgets.QPushButton()
        self._image = ChannelImageView()
        self._comparison = ComparisonView()
        self._contact = ContactSheet()
        self._stack = QtWidgets.QStackedWidget()
        self._manager = MeasurementManager()
        self._browser = ChannelBrowser()
        self._metadata = MetadataInspector()
        self._provenance = ProvenanceInspector()
        self._conventions = QtWidgets.QLabel()
        self._diagnostics = DiagnosticsPanel()
        self._briefing = BriefingPanel()
        self._process = ProcessingWorkspace()
        self._knowledge = KnowledgePanel()
        # Measurements are read-only observations placed on the single image; they
        # report across the single view's channels (current + phase + topography).
        self._measure = MeasurementController(model, self._image, model.single_view_specs)
        self._measure_panel = MeasurementPanel(self._measure)

        self._build_menu()
        self._build_layout()
        self._wire()
        self._load()
        self._refresh_manager()

    # -- active session (the model/history the single set of widgets is bound to) --

    @property
    def _active_session(self) -> MeasurementSession:
        return self._sessions[self._active_index]

    @property
    def _model(self) -> ExplorerModel:
        return self._active_session.model

    @_model.setter
    def _model(self, value: ExplorerModel) -> None:
        self._active_session.model = value

    @property
    def _history(self) -> list[ExplorerModel]:
        return self._active_session.history

    @_history.setter
    def _history(self, value: list[ExplorerModel]) -> None:
        self._active_session.history = value

    def _new_measurement_id(self) -> str:
        """Mint the next stable, project-local measurement id (never reused)."""
        mid = f"measurement-{self._next_seq:04d}"
        self._next_seq += 1
        return mid

    # -- construction ---------------------------------------------------------

    def _build_menu(self) -> None:
        """The File menu: open/save a project, open a measurement, and the exports.

        Every action delegates to a handler; the menu holds no logic itself. Project
        save/open reuse the pipeline persistence (a bundle of Zarr stores); the
        exports reuse the existing io/viz writers.
        """
        file_menu = self.menuBar().addMenu("&File")
        export_menu = QtWidgets.QMenu("&Export", self)
        # Hold Python references so the QMenu wrappers stay valid (and testable).
        self._file_menu = file_menu
        self._export_menu = export_menu
        self._menu_action(file_menu, "&New Project", self._new_project, "Ctrl+N")
        self._menu_action(file_menu, "Open &Project...", self._open_project, "Ctrl+Shift+O")
        file_menu.addSeparator()
        self._menu_action(file_menu, "Open &Measurement...", self._open_measurement, "Ctrl+O")
        self._menu_action(file_menu, "&Add Measurement...", self._add_measurement, "Ctrl+Shift+A")
        self._menu_action(file_menu, "&Close Measurement", self._close_active_measurement)
        file_menu.addSeparator()
        self._menu_action(file_menu, "&Save Project", self._save_project, "Ctrl+S")
        self._menu_action(file_menu, "Save Project &As...", self._save_project_as, "Ctrl+Shift+S")
        file_menu.addSeparator()
        file_menu.addMenu(export_menu)
        self._menu_action(export_menu, "Processed &Data (Zarr)...", self._export_data_zarr)
        self._menu_action(export_menu, "&Channel (GSF)...", self._export_channel_gsf)
        self._menu_action(export_menu, "&Measurement (CSV)...", self._export_measurement_csv)
        self._menu_action(export_menu, "&Figure...", self._export_figure)
        file_menu.addSeparator()
        self._menu_action(file_menu, "Close &Project", self._close_project)
        self._menu_action(file_menu, "E&xit", self.close, "Ctrl+Q")

    def _menu_action(
        self, menu: QtWidgets.QMenu, text: str, slot: Any, shortcut: str | None = None
    ) -> QtGui.QAction:
        action = menu.addAction(text)
        action.triggered.connect(slot)
        if shortcut is not None:
            action.setShortcut(shortcut)
        return action

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

        measurements = QtWidgets.QDockWidget("Measurements")
        measurements.setWidget(self._manager)
        measurements.setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, measurements)

        channels = QtWidgets.QDockWidget("Channels")
        channels.setWidget(self._browser)
        channels.setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, channels)
        # Measurements on top, the channel browser below it (one left column).
        self.splitDockWidget(measurements, channels, QtCore.Qt.Orientation.Vertical)
        self.resizeDocks([measurements, channels], [150, 460], QtCore.Qt.Orientation.Vertical)

        tabs = QtWidgets.QTabWidget()
        self._inspect_tabs = tabs
        tabs.addTab(self._metadata, "Metadata")
        tabs.addTab(self._provenance, "Provenance")
        tabs.addTab(self._diagnostics, "Diagnostics")
        tabs.addTab(self._briefing, "Briefing")
        tabs.addTab(self._measure_panel, "Measure")
        tabs.addTab(self._process, "Process")
        tabs.addTab(self._knowledge, "Knowledge")
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
        # Measurement Manager: switch / add / close / rename across the project.
        self._manager.measurementActivated.connect(self.switch_to)
        self._manager.addRequested.connect(self._add_measurement)
        self._manager.removeRequested.connect(self.close_measurement)
        self._manager.renameRequested.connect(self._rename_measurement)
        self._browser.channelSelected.connect(self._on_channel_selected)
        self._browser.representationSelected.connect(self._on_representation_selected)
        self._image.cursorMoved.connect(self._on_cursor_moved)
        self._comparison.cursorMoved.connect(self._on_comparison_cursor)
        self._contact.channelSelected.connect(self._on_channel_selected)
        # Measurements live on the single image; adding one focuses that view.
        self._measure.measurementAdded.connect(self._show_single)
        # Processing signals (generic, registry-driven workspace)
        self._process.operationSelected.connect(self._on_operation_selected)
        self._process.previewRequested.connect(self._on_preview_requested)
        self._process.previewAccepted.connect(self._on_preview_accepted)
        self._process.previewCancelled.connect(self._on_preview_cancelled)
        # AI Scientist: a suggested next step hands off to the Processing Workspace.
        self._briefing.recommendationPreviewRequested.connect(self._on_recommendation_preview)
        # Knowledge Center: "Learn more" from the Workspace or a recommendation opens the article.
        self._process.learnMoreRequested.connect(self._on_operation_learn_more)
        self._briefing.learnMoreRequested.connect(self._on_operation_learn_more)

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
        self._diagnostics.set_report(self._model.diagnostics_report())
        self._briefing.set_briefing(self._model.scientific_briefing())
        self._briefing.set_suggestions(self._model.workflow_suggestions())
        self._process.set_catalog(self._model.operation_catalog())
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
        self._refresh_manager()

    def _navigate_back(self) -> None:
        if not self._history:
            return
        self._preview = None
        self._process.set_preview_mode(False)
        self._update_model(self._history.pop(), push_history=False)

    def _refresh_navigation(self) -> None:
        has_history = bool(self._history)
        self._back_btn.setVisible(has_history)
        if has_history:
            self._back_btn.setText(f"← Back to {self._history[-1].title}")

    # -- view switching -------------------------------------------------------

    def _show_single(self) -> None:
        self._stack.setCurrentWidget(self._image)
        self._refresh_channel()

    def _show_comparison(self, preset: str) -> None:
        self._comparison_preset = preset
        specs = self._model.comparison_layout(preset)
        self._comparison.set_panes(specs, self._model.render_spec)
        self._stack.setCurrentWidget(self._comparison)
        self._active.setText("Comparing:   " + "      |      ".join(s.title for s in specs))

    def _show_contact(self) -> None:
        specs = self._model.harmonic_panes()
        self._contact.set_panes(specs, self._model.render_spec)
        self._stack.setCurrentWidget(self._contact)
        self._active.setText(f"Contact sheet  -  {len(specs)} optical harmonics")

    # -- processing (generic: any registered operation, no per-op wiring) ------

    def _on_operation_selected(self, step_id: str) -> None:
        """Show the selected operation's description + parameter form."""
        self._process.show_operation(self._model.operation_option(step_id))

    def _on_recommendation_preview(self, step_id: str, params: dict[str, Any]) -> None:
        """A suggested next step (from the AI Scientist) opens, pre-configured, in the Workspace.

        This is the whole point of building the Workspace first: an AI recommendation
        needs no special execution path - it selects a registered operation, fills its
        parameters, and runs the same generic preview every operation uses.
        """
        self._inspect_tabs.setCurrentWidget(self._process)
        self._process.highlight_operation(step_id)
        self._process.show_operation(self._model.operation_option(step_id))
        self._process.apply_params(params)
        self._on_preview_requested(step_id, params)

    def _on_operation_learn_more(self, step_id: str) -> None:
        """Open the Knowledge Center article for an operation (from Workspace or AI)."""
        article = article_for_operation(step_id)
        if article is None:
            return
        self._inspect_tabs.setCurrentWidget(self._knowledge)
        self._knowledge.show_article(article.article_id)

    def _on_preview_requested(self, step_id: str, params: dict[str, Any]) -> None:
        """Run the operation on a copy and show a before/after preview.

        The model does the science (build the step, apply it, diff the result); the
        window only lays the panes out and reveals the summary. Nothing is
        committed - the derived dataset rides on the preview until Accept.
        """
        try:
            preview = self._model.preview_operation(step_id, params)
        except ProcessingError as exc:
            QtWidgets.QMessageBox.warning(self, "Preview failed", str(exc))
            return

        self._preview = preview
        specs = [pane.spec for pane in preview.panes]
        renders: dict[PaneSpec, RenderData] = {pane.spec: pane.render for pane in preview.panes}
        self._comparison.set_panes(specs, renders.__getitem__)
        self._stack.setCurrentWidget(self._comparison)
        self._active.setText(
            f"Preview: {self._operation_title(step_id)} — Accept to commit, Cancel to discard"
        )
        self._process.show_preview(preview)
        self._process.set_preview_mode(True)

    def _on_preview_accepted(self) -> None:
        if self._preview is None:
            return
        new_model = ExplorerModel(self._preview.dataset, title=self._preview.title)
        self._preview = None
        self._process.set_preview_mode(False)
        self._update_model(new_model)

    def _on_preview_cancelled(self) -> None:
        self._preview = None
        self._process.set_preview_mode(False)
        self._show_single()

    def _operation_title(self, step_id: str) -> str:
        return self._model.operation_option(step_id).title

    # -- project session: new / open / save -----------------------------------

    def _new_project(self) -> None:
        """Start a fresh project from a newly chosen measurement (replaces the current)."""
        self._open_measurement()

    def _close_project(self) -> None:
        """Close the whole project and start fresh from a newly chosen measurement.

        A project always holds at least one measurement, so (like New Project) this
        prompts for one; cancelling keeps the current project untouched.
        """
        self._open_measurement()

    def _open_measurement(self) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Open neaSNOM measurement directory"
        )
        if not path:
            return
        try:
            model = ExplorerModel.open_measurement(path)
        except ReaderError as exc:
            QtWidgets.QMessageBox.critical(self, "Could not open measurement", str(exc))
            return
        self._project_path = None
        self.load_explorer_model(model)

    def _add_measurement(self) -> None:
        """Open a measurement and append it to the current project (does not replace)."""
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Add neaSNOM measurement directory"
        )
        if not path:
            return
        try:
            model = ExplorerModel.open_measurement(path)
        except ReaderError as exc:
            QtWidgets.QMessageBox.critical(self, "Could not open measurement", str(exc))
            return
        self.add_measurement_model(model)

    def _rename_measurement(self, index: int) -> None:
        """Prompt for and apply a new display name for the measurement at ``index``."""
        if not 0 <= index < len(self._sessions):
            return
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Rename measurement", "Name:", text=self._sessions[index].title
        )
        if ok and name:
            self.rename_measurement(index, name)

    def _close_active_measurement(self) -> None:
        """File-menu handler: close the currently active measurement."""
        self.close_measurement(self._active_index)

    def _open_project(self) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Open SNOMNIMAN project")
        if not path:
            return
        try:
            project = load_project(path)
        except ReaderError as exc:
            QtWidgets.QMessageBox.critical(self, "Could not open project", str(exc))
            return
        self.load_project_object(project)
        self._project_path = Path(path)

    def _save_project(self) -> None:
        if self._project_path is None:
            self._save_project_as()
        else:
            self._write_project(self._project_path)

    def _save_project_as(self) -> None:
        default = f"{self._project_title}.snomproj"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save project as", default, "SNOMNIMAN project (*.snomproj)"
        )
        if not path:
            return
        bundle = Path(path)
        if bundle.suffix != ".snomproj":
            bundle = bundle.with_suffix(".snomproj")
        self._write_project(bundle)

    def _write_project(self, path: Path) -> None:
        try:
            save_project(self.current_project(), path, overwrite=True)
        except (OSError, FileExistsError) as exc:
            QtWidgets.QMessageBox.warning(self, "Save failed", str(exc))
            return
        self._project_path = path
        QtWidgets.QMessageBox.information(self, "Project saved", f"Saved project:\n{path}")

    def current_project(self) -> Project:
        """Bundle every measurement (each with its history + view + overlays) for saving."""
        self._capture_active_session()
        measurements = tuple(self._measurement_of(s) for s in self._sessions)
        return Project(
            title=self._project_title,
            measurements=measurements,
            current_index=self._active_index,
            session={"next_measurement_seq": self._next_seq},
        )

    def _measurement_of(self, session: MeasurementSession) -> Measurement:
        """Build the immutable :class:`Measurement` snapshot of one working session."""
        models = [*session.history, session.model]
        doc: dict[str, Any] = {
            "titles": [m.title for m in models],
            "view": session.view_state,
            "measurements": session.measure_records,
        }
        return measurement_from_history(
            [m.dataset for m in models],
            title=session.title,
            measurement_id=session.measurement_id,
            current_index=len(session.history),
            session=doc,
        )

    def _capture_active_session(self) -> None:
        """Snapshot the live widget state (view + overlays) into the active session.

        The active session's view/overlays live in the widgets until captured; the
        inactive sessions already hold the state captured when they were last left.
        """
        s = self._active_session
        s.view_state = self._view_state()
        s.measure_records = self._measure.to_records()

    # -- multi-measurement management (switch / add / rename / close) ----------

    def switch_to(self, index: int) -> None:
        """Make measurement ``index`` active, preserving both sessions (no disk reload).

        The outgoing session's live view + overlays are captured first; the incoming
        session's captured state is restored into the single set of widgets.
        """
        if not 0 <= index < len(self._sessions) or index == self._active_index:
            return
        self._capture_active_session()
        self._active_index = index
        self._bind_active_session()

    def add_measurement_model(self, model: ExplorerModel) -> None:
        """Append a measurement to the project and switch to it (the dialog seam).

        Public so tests can add a measurement without a file dialog or disk access.
        """
        self._capture_active_session()
        self._sessions.append(
            MeasurementSession(
                model=model, measurement_id=self._new_measurement_id(), title=model.title
            )
        )
        self._active_index = len(self._sessions) - 1
        self._bind_active_session()

    def rename_measurement(self, index: int, name: str) -> None:
        """Set a measurement's display name (the seam ``_rename_measurement`` calls)."""
        if not 0 <= index < len(self._sessions) or not name:
            return
        self._sessions[index].title = name
        # For a single-measurement project, the project name follows the measurement.
        if len(self._sessions) == 1:
            self._project_title = name
        self._refresh_manager()

    def close_measurement(self, index: int) -> None:
        """Close the measurement at ``index``.

        Closing the active measurement binds a neighbour into the widgets; closing
        an inactive one leaves the active view untouched. A project keeps at least
        one measurement, so closing the last one starts a fresh project instead.
        """
        if not 0 <= index < len(self._sessions):
            return
        if len(self._sessions) == 1:
            self._close_project()
            return
        closing_active = index == self._active_index
        del self._sessions[index]
        if index < self._active_index:
            self._active_index -= 1
        elif closing_active:
            self._active_index = min(self._active_index, len(self._sessions) - 1)
        if closing_active:
            self._bind_active_session()
        else:
            self._refresh_manager()

    def _refresh_manager(self) -> None:
        """Update the Manager list + the window title to reflect the open measurements.

        With a single measurement the window title is left exactly as the single-
        measurement Explorer sets it, so the app feels unchanged; the "m/n" hint
        appears only once a project holds more than one measurement.
        """
        labels = [self._manager_label(s) for s in self._sessions]
        self._manager.set_measurements(labels, self._active_index)
        n = len(self._sessions)
        if n > 1:
            self.setWindowTitle(
                f"{self._active_session.title} - Measurement {self._active_index + 1}/{n}"
                " - SNOMNIMAN Measurement Explorer"
            )

    @staticmethod
    def _manager_label(session: MeasurementSession) -> str:
        steps = len(session.history)
        if steps:
            return f"{session.title}   ({steps} step{'s' if steps != 1 else ''})"
        return session.title

    def load_explorer_model(self, model: ExplorerModel) -> None:
        """Reset the window to a single fresh measurement (New / Open Measurement)."""
        self._next_seq = 1
        self._sessions = [
            MeasurementSession(
                model=model, measurement_id=self._new_measurement_id(), title=model.title
            )
        ]
        self._active_index = 0
        self._project_title = model.title
        self._preview = None
        self._comparison_preset = None
        self._process.set_preview_mode(False)
        self._bind_active_session()

    def load_project_object(self, project: Project) -> None:
        """Rebuild the window from a saved :class:`Project` (every measurement + session)."""
        self._sessions = [self._session_of(m) for m in project.measurements]
        self._active_index = project.current_index
        self._project_title = project.title
        self._next_seq = _safe_int(
            project.session.get("next_measurement_seq"), len(self._sessions) + 1
        )
        self._preview = None
        self._comparison_preset = None
        self._process.set_preview_mode(False)
        self._bind_active_session()

    def _session_of(self, measurement: Measurement) -> MeasurementSession:
        """Rebuild a working session from an immutable :class:`Measurement` snapshot."""
        doc = dict(measurement.session)
        titles = doc.get("titles")
        models: list[ExplorerModel] = []
        for index, dataset in enumerate(measurement.datasets):
            title = titles[index] if isinstance(titles, list) and index < len(titles) else None
            models.append(ExplorerModel(dataset, title=title if isinstance(title, str) else None))
        view = doc.get("view")
        records = doc.get("measurements")
        return MeasurementSession(
            model=models[measurement.current_index],
            measurement_id=measurement.measurement_id,
            title=measurement.title,
            history=models[: measurement.current_index],
            measure_records=list(records) if isinstance(records, list) else [],
            view_state=dict(view) if isinstance(view, dict) else {},
        )

    def _bind_active_session(self) -> None:
        """Bind the single set of widgets to the active session and restore its view.

        Used after the active measurement changes (load, switch): the widgets are
        repainted from the active session's model and its captured view + overlays
        are restored, all without re-reading anything from disk.
        """
        s = self._active_session
        self._comparison_preset = None
        self._preview = None
        self._process.set_preview_mode(False)
        self._measure.set_model(s.model)
        self._refresh_navigation()
        self._load()
        self._restore_view_and_measurements(s)
        self._refresh_manager()

    def _view_state(self) -> dict[str, Any]:
        current = self._stack.currentWidget()
        mode = "single"
        if current is self._comparison:
            mode = "comparison"
        elif current is self._contact:
            mode = "contact"
        return {
            "channel": self._model.current_channel,
            "representation": self._model.current_representation,
            "mode": mode,
            "preset": self._comparison_preset,
        }

    def _restore_view_and_measurements(self, s: MeasurementSession) -> None:
        """Restore the active view (channel / representation / mode) and overlays."""
        view = s.view_state or {}
        channel = view.get("channel")
        if isinstance(channel, str) and channel in self._model.dataset.channel_names:
            self._model.set_channel(channel)
            representation = view.get("representation")
            if isinstance(representation, str) and representation in self._model.representations():
                self._model.set_representation(representation)
            self._browser.select(channel)
            self._refresh_channel()
        records = s.measure_records
        has_measurements = bool(records)
        if has_measurements:
            self._measure.load_records(records)
        # Measurements live on the single image, so they force that view; otherwise
        # restore whatever multi-pane view the session was last in.
        mode = view.get("mode", "single")
        preset = view.get("preset")
        if not has_measurements and mode == "comparison" and isinstance(preset, str):
            self._show_comparison(preset)
        elif not has_measurements and mode == "contact":
            self._show_contact()
        else:
            self._show_single()

    # -- data export (processed dataset / channel / measurement) --------------

    def _export_data_zarr(self) -> None:
        """Export the current (processed) dataset as a loss-less canonical Zarr store."""
        default = f"{self._model.title}.zarr"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export processed data (Zarr)", default, "Zarr store (*.zarr)"
        )
        if not path:
            return
        store_path = Path(path)
        if store_path.suffix != ".zarr":
            store_path = store_path.with_suffix(".zarr")
        try:
            written = write_zarr(self._model.dataset, store_path, overwrite=True)
        except OSError as exc:
            QtWidgets.QMessageBox.warning(self, "Export failed", str(exc))
            return
        QtWidgets.QMessageBox.information(
            self,
            "Data exported",
            f"Saved the processed dataset (full provenance) to:\n{written}",
        )

    def _export_channel_gsf(self) -> None:
        """Export the channel/representation on screen as a Gwyddion Simple Field grid."""
        channel = self._model.current_channel
        representation = self._model.current_representation
        default = f"{self._model.title}_{channel}_{representation}.gsf"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export channel (GSF)", default, "Gwyddion Simple Field (*.gsf)"
        )
        if not path:
            return
        try:
            gsf_path, provenance_path = export_channel_gsf(
                self._model.dataset, channel, path, representation=representation
            )
        except (OSError, DatasetError) as exc:
            QtWidgets.QMessageBox.warning(self, "Export failed", str(exc))
            return
        QtWidgets.QMessageBox.information(
            self,
            "Channel exported",
            f"Saved {channel} ({representation}):\n{gsf_path}\n\n"
            f"with provenance:\n{provenance_path.name}",
        )

    def _export_measurement_csv(self) -> None:
        """Export the active measurement's numbers as CSV (delegates to the Measure panel)."""
        self._inspect_tabs.setCurrentWidget(self._measure_panel)
        self._measure_panel.export_active_csv()

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


def _safe_int(value: Any, default: int) -> int:
    """Coerce a manifest value to int, falling back to ``default`` (tolerate junk)."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


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
